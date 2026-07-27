"""
Recommendation handler for GET /applications/{id}/recommendation.

Returns the deterministic next-action recommendation for an application.
Does NOT call Bedrock — explanation is always null at this stage.

Error mapping:
  NotFoundError  → 404 NOT_FOUND
  RepositoryError → 503 SERVICE_UNAVAILABLE
  other          → 500 INTERNAL_ERROR
"""

import json
import logging
from typing import Optional

from models import NextAction
from services.recommendation_service import get_recommendation
from repositories.applications_repo import (
    NotFoundError,
    RepositoryError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers (same conventions as other handlers)
# ---------------------------------------------------------------------------

def _error_response(
    status_code: int,
    code: str,
    message: str,
    field: Optional[str] = None,
) -> dict:
    body: dict = {"code": code, "message": message}
    if field is not None:
        body["field"] = field
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": body}),
    }


def _ok_response(status_code: int, data) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data),
    }


def _next_action_to_dict(next_action: Optional[NextAction]) -> Optional[dict]:
    """Convert a NextAction to a JSON-serialisable dict, or None."""
    if next_action is None:
        return None
    result: dict = {
        "label": next_action.label,
        "priority": next_action.priority.value,
        "explanation": next_action.explanation,  # always None at this stage
    }
    return result


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def get_recommendation_handler(event: dict) -> dict:
    """
    Handle GET /applications/{id}/recommendation.

    Returns:
        200 with {"nextAction": {...} | null, "applicationId": "..."}
        404 if application not found
        503 if DynamoDB is unavailable
        500 for unexpected errors

    When compute_next_action returns None (no recommendation applicable),
    the response is still 200 with nextAction set to null.
    """
    request_id = event.get("requestContext", {}).get("requestId", "unknown")

    # 1. Parse applicationId from path parameters
    application_id = (event.get("pathParameters") or {}).get("id", "")
    if not application_id:
        return _error_response(400, "VALIDATION_ERROR", "Missing application id")

    try:
        # 2. Get recommendation
        app, next_action = get_recommendation(application_id)

        # 3. Build response
        response_body = {
            "applicationId": app.applicationId,
            "status": app.status.value,
            "nextAction": _next_action_to_dict(next_action),
        }

        logger.info(
            "handler: get_recommendation request_id=%s status=200 application_id=%s has_action=%s",
            request_id,
            application_id,
            next_action is not None,
        )
        return _ok_response(200, response_body)

    except NotFoundError:
        logger.warning(
            "handler: get_recommendation request_id=%s error_type=NotFoundError application_id=%s",
            request_id,
            application_id,
        )
        return _error_response(404, "NOT_FOUND", "Application not found")

    except RepositoryError as e:
        logger.error(
            "handler: get_recommendation request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")

    except Exception as e:
        logger.error(
            "handler: get_recommendation request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
