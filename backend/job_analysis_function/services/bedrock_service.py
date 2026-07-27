"""
Bedrock service — invokes Claude 3 Haiku to extract structured job information.

This module:
  - Uses boto3 Bedrock Runtime with botocore Config (30s timeout)
  - Reads BEDROCK_MODEL_ID from the environment variable
  - Calls invoke_model with the Claude Messages API format
  - Parses the Claude response envelope
  - Validates the result via validate_extraction_result()
  - Returns ExtractionResult on success
  - Raises BedrockTimeoutError on read/connect timeouts
  - Raises BedrockError on ClientError or malformed responses
  - Allows ExtractionValidationError to propagate unchanged
  - NEVER logs job description content, model response content,
    extracted data, AWS credentials, request/response bodies, or stack traces
  - Logs only Bedrock request ID (when available) and safe error type

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6
"""

import json
import logging
import os
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError, ConnectTimeoutError

from models import ExtractionResult
from validators.extraction_validator import (
    validate_extraction_result,
    ExtractionValidationError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BEDROCK_TIMEOUT_SECONDS = 30

_BEDROCK_CONFIG = Config(
    connect_timeout=_BEDROCK_TIMEOUT_SECONDS,
    read_timeout=_BEDROCK_TIMEOUT_SECONDS,
)

# Claude Messages API version
_ANTHROPIC_VERSION = "bedrock-2023-05-31"

# Maximum tokens for the response
_MAX_TOKENS = 2048


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------

class BedrockTimeoutError(Exception):
    """Raised when Bedrock invocation times out (read or connect)."""


class BedrockError(Exception):
    """Raised on Bedrock invocation failure or malformed model response."""


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a job description parser. Extract structured information from the job description provided by the user.

Return ONLY a valid JSON object with exactly these keys:
- jobTitle (string or null)
- company (string or null)
- location (string or null)
- skills (array of strings, or empty array)
- responsibilities (array of strings, or empty array)
- languages (array of strings, or empty array)
- experienceLevel (string or null)

Do not include any other text, explanation, or markdown formatting. Return only the JSON object."""


# ---------------------------------------------------------------------------
# Lazy client (mockable, no network call at import time)
# ---------------------------------------------------------------------------

_bedrock_client = None


def _get_client():
    """Lazy-initialize the Bedrock Runtime client."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            config=_BEDROCK_CONFIG,
        )
    return _bedrock_client


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_job_description(job_description: str) -> ExtractionResult:
    """
    Analyze a job description using Amazon Bedrock (Claude 3 Haiku).

    Args:
        job_description: The raw job description text to analyze.

    Returns:
        A validated ExtractionResult instance.

    Raises:
        BedrockTimeoutError: On read or connect timeout (> 30s).
        BedrockError: On Bedrock invocation failure or malformed response.
        ExtractionValidationError: When the model response is missing required keys
            (propagated unchanged from validate_extraction_result).
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    # Build the Claude Messages API request body
    request_body = json.dumps({
        "anthropic_version": _ANTHROPIC_VERSION,
        "max_tokens": _MAX_TOKENS,
        "system": _SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": job_description,
            }
        ],
    })

    # Invoke the model
    try:
        response = _get_client().invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=request_body,
        )
    except ReadTimeoutError as e:
        logger.error("bedrock_service: timeout_type=ReadTimeout")
        raise BedrockTimeoutError("Bedrock read timeout") from e
    except ConnectTimeoutError as e:
        logger.error("bedrock_service: timeout_type=ConnectTimeout")
        raise BedrockTimeoutError("Bedrock connect timeout") from e
    except ClientError as e:
        # Log only the error code, never the full exception or request body
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "unknown")
        logger.error(
            "bedrock_service: error_type=ClientError code=%s request_id=%s",
            error_code,
            request_id,
        )
        raise BedrockError("Bedrock invocation failed") from e
    except Exception as e:
        logger.error("bedrock_service: error_type=%s", type(e).__name__)
        raise BedrockError("Bedrock invocation failed") from e

    # Log the request ID for traceability (safe — no content logged)
    response_metadata = response.get("ResponseMetadata", {})
    request_id = response_metadata.get("RequestId", "unknown")
    logger.info("bedrock_service: request_id=%s", request_id)

    # Parse the response body
    try:
        response_bytes = response["body"].read()
        response_json = json.loads(response_bytes.decode("utf-8"))
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error("bedrock_service: error_type=ResponseParseError request_id=%s", request_id)
        raise BedrockError("Failed to parse Bedrock response") from e

    # Extract content from the Claude Messages API response envelope
    # Response format: {"content": [{"type": "text", "text": "..."}], ...}
    try:
        content_blocks = response_json["content"]
        text_content = None
        for block in content_blocks:
            if block.get("type") == "text":
                text_content = block["text"]
                break

        if text_content is None:
            raise KeyError("No text content block found")
    except (KeyError, TypeError, IndexError) as e:
        logger.error("bedrock_service: error_type=MalformedResponse request_id=%s", request_id)
        raise BedrockError("Malformed Bedrock response structure") from e

    # Parse the extracted text as JSON
    try:
        extraction_dict = json.loads(text_content)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("bedrock_service: error_type=InvalidJSON request_id=%s", request_id)
        raise BedrockError("Model response is not valid JSON") from e

    if not isinstance(extraction_dict, dict):
        logger.error("bedrock_service: error_type=NotADict request_id=%s", request_id)
        raise BedrockError("Model response is not a JSON object")

    # Validate and return — ExtractionValidationError propagates unchanged
    return validate_extraction_result(extraction_dict)
