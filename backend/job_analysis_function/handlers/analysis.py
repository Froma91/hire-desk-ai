"""
Analysis handler for POST /analyze.

Parses the job description from the request, invokes Bedrock via
bedrock_service.analyze_job_description(), and returns the validated
ExtractionResult as JSON.

Error mapping:
  Invalid request payload     -> 400 VALIDATION_ERROR
  BedrockTimeoutError         -> 408 ANALYSIS_TIMEOUT
  ExtractionValidationError   -> 422 ANALYSIS_FAILED
  BedrockError                -> 502 ANALYSIS_FAILED
  Unexpected exception        -> 500 INTERNAL_ERROR

Privacy:
  - NEVER logs jobDescription, request body, extracted result, or model response
  - Logs only safe error categories and request IDs handled by bedrock_service
"""

import json
import logging
from typing import Optional

from applications_function.models import ExtractionResult
from job_analysis_function.services.bedrock_service import (
    analyze_job_description,
    BedrockTimeoutError,
    BedrockError,
)
from job_analysis_function.validators.extraction_validator import (
    ExtractionValidationError,
)

logger = logging.getLogger(__name__)

# Maximum allowed length for jobDescription
_MAX_JOB_DESCRIPTION_LENGTH = 10_000


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _error_response(
    status_code: int,
    code: str,
    message: str,
    field: Optional[str] = None,
) -> dict:
    """Build the standard safe error envelope."""
    body: dict = {"code": code, "message": message}
    if field is not None:
        body["field"] = field
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": body}),
    }


def _ok_response(status_code: int, data: dict) -> dict:
    """Build a success response with JSON body."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data),
    }


def _extraction_result_to_dict(result: ExtractionResult) -> dict:
    """
    Serialize ExtractionResult to a JSON-compatible dict.
    Preserves null values correctly for all seven fields.
    """
    return {
        "jobTitle": result.jobTitle,
        "company": result.company,
        "location": result.location,
        "skills": result.skills,
        "responsibilities": result.responsibilities,
        "languages": result.languages,
        "experienceLevel": result.experienceLevel,
    }


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def analyze_job(event: dict, context) -> dict:
    """
    Handle POST /analyze.

    Expects JSON body: {"jobDescription": "..."}

    Steps:
      1. Parse and validate the request body
      2. Call bedrock_service.analyze_job_description(job_description)
      3. Return 200 with the complete ExtractionResult

    Args:
        event: API Gateway HTTP API v2 event.
        context: Lambda context (unused but required by the Lambda contract).

    Returns:
        HTTP response dict with statusCode, headers, and body.
    """
    request_id = event.get("requestContext", {}).get("requestId", "unknown")

    # ------------------------------------------------------------------
    # 1. Parse request body
    # ------------------------------------------------------------------
    raw_body = event.get("body")

    # Reject missing body
    if raw_body is None or raw_body == "":
        return _error_response(400, "VALIDATION_ERROR", "Request body is required")

    # Parse JSON
    try:
        data = json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "VALIDATION_ERROR", "Request body must be valid JSON")

    # ------------------------------------------------------------------
    # 2. Validate jobDescription field
    # ------------------------------------------------------------------
    job_description = data.get("jobDescription")

    # Require jobDescription to be present
    if job_description is None:
        return _error_response(
            400, "VALIDATION_ERROR", "jobDescription is required", "jobDescription"
        )

    # Require jobDescription to be a string
    if not isinstance(job_description, str):
        return _error_response(
            400, "VALIDATION_ERROR", "jobDescription must be a string", "jobDescription"
        )

    # Reject empty or whitespace-only
    if not job_description.strip():
        return _error_response(
            400, "VALIDATION_ERROR", "jobDescription must not be empty", "jobDescription"
        )

    # Reject too long
    if len(job_description) > _MAX_JOB_DESCRIPTION_LENGTH:
        return _error_response(
            400,
            "VALIDATION_ERROR",
            f"jobDescription must not exceed {_MAX_JOB_DESCRIPTION_LENGTH} characters",
            "jobDescription",
        )

    # ------------------------------------------------------------------
    # 3. Call Bedrock service
    # ------------------------------------------------------------------
    try:
        result = analyze_job_description(job_description)

        logger.info(
            "handler: analyze_job request_id=%s status=200",
            request_id,
        )
        return _ok_response(200, _extraction_result_to_dict(result))

    except BedrockTimeoutError:
        logger.error(
            "handler: analyze_job request_id=%s error_type=BedrockTimeoutError",
            request_id,
        )
        return _error_response(408, "ANALYSIS_TIMEOUT", "Analysis timed out. Please try again.")

    except ExtractionValidationError:
        logger.error(
            "handler: analyze_job request_id=%s error_type=ExtractionValidationError",
            request_id,
        )
        return _error_response(422, "ANALYSIS_FAILED", "Analysis produced incomplete results. Please try again.")

    except BedrockError:
        logger.error(
            "handler: analyze_job request_id=%s error_type=BedrockError",
            request_id,
        )
        return _error_response(502, "ANALYSIS_FAILED", "Analysis service is temporarily unavailable.")

    except Exception:
        logger.error(
            "handler: analyze_job request_id=%s error_type=UnexpectedError",
            request_id,
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
