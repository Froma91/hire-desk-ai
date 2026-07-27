"""
Explanation service — Bedrock explanation generator for JobAnalysisFunction.

Returns a plain text explanation <= 280 characters, or None on any failure.
NEVER allows a Bedrock failure to propagate as an exception (graceful degradation).
"""

import json
import logging
import os
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ReadTimeoutError, ConnectTimeoutError

logger = logging.getLogger(__name__)

_BEDROCK_TIMEOUT_SECONDS = 30
_BEDROCK_CONFIG = Config(connect_timeout=_BEDROCK_TIMEOUT_SECONDS, read_timeout=_BEDROCK_TIMEOUT_SECONDS)
_ANTHROPIC_VERSION = "bedrock-2023-05-31"
_MAX_TOKENS = 256
_MAX_EXPLANATION_LENGTH = 280

_bedrock_client = None


def _get_client():
    """Lazy-initialize the Bedrock Runtime client."""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", config=_BEDROCK_CONFIG)
    return _bedrock_client


def generate_explanation(label: str, status: str) -> Optional[str]:
    """
    Request a concise explanation from Bedrock for a recommended action.

    Returns a plain-text explanation <= 280 characters, or None on failure.
    This function NEVER raises an exception.
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
        "messages": [{"role": "user", "content": prompt}],
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
        logger.error("explanation_service: error_type=ClientError code=%s", error_code)
        return None
    except Exception as e:
        logger.error("explanation_service: error_type=%s", type(e).__name__)
        return None

    # Parse response
    try:
        response_bytes = response["body"].read()
        response_json = json.loads(response_bytes.decode("utf-8"))
        text_content = None
        for block in response_json.get("content", []):
            if block.get("type") == "text":
                text_content = block["text"]
                break
        if text_content is None:
            return None
    except (KeyError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None

    explanation = text_content.strip()
    if not explanation or len(explanation) > _MAX_EXPLANATION_LENGTH:
        return None
    return explanation
