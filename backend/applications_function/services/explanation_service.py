"""
Explanation service — requests a concise Bedrock explanation for a next action.

This module:
  - Uses boto3 Bedrock Runtime with botocore Config (30s timeout)
  - Reads BEDROCK_MODEL_ID from environment
  - Returns a plain text explanation ≤ 280 characters, or None on any failure
  - NEVER allows a Bedrock failure to propagate as an exception
  - NEVER logs prompts, application data, or Bedrock response text
  - Logs only safe error categories and request IDs

Graceful degradation:
  - Timeout → None
  - BedrockError → None
  - Empty/whitespace response → None
  - Response > 280 chars → None
  - Any other failure → None
"""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError, ConnectTimeoutError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_BEDROCK_TIMEOUT_SECONDS = 30

_BEDROCK_CONFIG = Config(
    connect_timeout=_BEDROCK_TIMEOUT_SECONDS,
    read_timeout=_BEDROCK_TIMEOUT_SECONDS,
)

_ANTHROPIC_VERSION = "bedrock-2023-05-31"
_MAX_TOKENS = 256
_MAX_EXPLANATION_LENGTH = 280

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

def generate_explanation(label: str, status: str) -> Optional[str]:
    """
    Request a concise explanation from Bedrock for a recommended action.

    Args:
        label: The deterministic action label (e.g., "Apply now").
        status: The current application status (e.g., "Wishlist").

    Returns:
        A plain-text explanation ≤ 280 characters, or None if Bedrock
        fails, times out, or returns an invalid response.

    This function NEVER raises an exception. All Bedrock failures are
    caught and result in None (graceful degradation).
    """
    model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    prompt = (
        f"In 280 characters or fewer, explain why a job applicant should "
        f'"{label}" for an application currently in status "{status}". '
        f"Reply with plain text only, no markdown or formatting."
    )

    request_body = json.dumps({
        "anthropic_version": _ANTHROPIC_VERSION,
        "max_tokens": _MAX_TOKENS,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    })

    try:
        response = _get_client().invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=request_body,
        )
    except (ReadTimeoutError, ConnectTimeoutError):
        logger.error("explanation_service: error_type=Timeout")
        return None
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "unknown")
        logger.error(
            "explanation_service: error_type=ClientError code=%s request_id=%s",
            error_code,
            request_id,
        )
        return None
    except Exception as e:
        logger.error("explanation_service: error_type=%s", type(e).__name__)
        return None

    # Log request ID for traceability
    response_metadata = response.get("ResponseMetadata", {})
    request_id = response_metadata.get("RequestId", "unknown")
    logger.info("explanation_service: request_id=%s", request_id)

    # Parse response
    try:
        response_bytes = response["body"].read()
        response_json = json.loads(response_bytes.decode("utf-8"))

        content_blocks = response_json["content"]
        text_content = None
        for block in content_blocks:
            if block.get("type") == "text":
                text_content = block["text"]
                break

        if text_content is None:
            logger.error("explanation_service: error_type=NoTextBlock request_id=%s", request_id)
            return None

    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, TypeError, IndexError) as e:
        logger.error("explanation_service: error_type=ParseError request_id=%s", type(e).__name__)
        return None

    # Validate the explanation
    explanation = text_content.strip()

    # Empty or whitespace-only
    if not explanation:
        logger.warning("explanation_service: empty_response request_id=%s", request_id)
        return None

    # Too long
    if len(explanation) > _MAX_EXPLANATION_LENGTH:
        logger.warning("explanation_service: too_long len=%d request_id=%s", len(explanation), request_id)
        return None

    return explanation
