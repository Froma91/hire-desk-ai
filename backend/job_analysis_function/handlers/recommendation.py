"""Recommendation handler for GET /applications/{id}/recommendation."""

import json
import logging
from typing import Optional

from job_analysis_function.models import NextAction
from job_analysis_function.services.recommendation_service import (
    get_recommendation, NotFoundError, RepositoryError,
)

logger = logging.getLogger(__name__)


def _error_response(status_code: int, code: str, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": {"code": code, "message": message}}),
    }


def _ok_response(status_code: int, data: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data),
    }


def _next_action_to_dict(na: Optional[NextAction]) -> Optional[dict]:
    if na is None:
        return None
    return {"label": na.label, "priority": na.priority.value, "explanation": na.explanation}


def get_recommendation_handler(event: dict, context) -> dict:
    """Handle GET /applications/{id}/recommendation."""
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    application_id = (event.get("pathParameters") or {}).get("id", "")

    if not application_id:
        return _error_response(400, "VALIDATION_ERROR", "Missing application id")

    try:
        app, next_action = get_recommendation(application_id)
        return _ok_response(200, {
            "applicationId": app.applicationId,
            "status": app.status.value,
            "nextAction": _next_action_to_dict(next_action),
        })
    except NotFoundError:
        logger.warning("handler: get_recommendation request_id=%s error_type=NotFoundError", request_id)
        return _error_response(404, "NOT_FOUND", "Application not found")
    except RepositoryError:
        logger.error("handler: get_recommendation request_id=%s error_type=RepositoryError", request_id)
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")
    except Exception as e:
        logger.error("handler: get_recommendation request_id=%s error_type=%s", request_id, type(e).__name__)
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
