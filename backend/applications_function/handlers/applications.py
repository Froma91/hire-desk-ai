"""
CRUD handlers for APPLICATION resources.

Each handler:
  - Parses the API Gateway HTTP API (v2) event
  - Delegates to the service layer
  - Returns an HTTP response dict (statusCode, headers, body)

Error mapping:
  ValidationError  → 400
  NotFoundError    → 404
  RepositoryError  → 503
  other            → 500
"""

import json
import logging
from typing import Optional

from applications_function.models import Application
from applications_function.services.applications_service import (
    create_application as svc_create,
    list_applications as svc_list,
    get_application as svc_get,
    update_application as svc_update,
    delete_application as svc_delete,
    ValidationError,
    NotFoundError,
    RepositoryError,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _app_to_dict(app: Application) -> dict:
    """Convert an Application dataclass to a JSON-serialisable dict."""
    next_action = None
    if app.nextAction is not None:
        na = app.nextAction
        next_action = {
            "label": na.label,
            "priority": na.priority.value,
            "explanation": na.explanation if na.explanation is not None else None,
        }

    return {
        "userId": app.userId,
        "applicationId": app.applicationId,
        "jobTitle": app.jobTitle,
        "company": app.company,
        "location": app.location,
        "skills": app.skills,
        "responsibilities": app.responsibilities,
        "languages": app.languages,
        "experienceLevel": app.experienceLevel,
        "status": app.status.value,
        "createdAt": app.createdAt.isoformat(),
        "updatedAt": app.updatedAt.isoformat(),
        "statusHistory": [
            {"status": entry.status.value, "timestamp": entry.timestamp.isoformat()}
            for entry in app.statusHistory
        ],
        "nextAction": next_action,
    }


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


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def create_application(event: dict) -> dict:
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    try:
        data = json.loads(event.get("body") or "{}")
        app = svc_create(data)
        logger.info(
            "handler: create_application request_id=%s status=201",
            request_id,
        )
        return _ok_response(201, _app_to_dict(app))
    except ValidationError as e:
        logger.warning(
            "handler: create_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(400, "VALIDATION_ERROR", e.reason, e.field)
    except RepositoryError as e:
        logger.error(
            "handler: create_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")
    except Exception as e:
        logger.error(
            "handler: create_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")


def list_applications(event: dict) -> dict:
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    try:
        apps = svc_list()
        logger.info(
            "handler: list_applications request_id=%s status=200",
            request_id,
        )
        return _ok_response(200, [_app_to_dict(a) for a in apps])
    except RepositoryError as e:
        logger.error(
            "handler: list_applications request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")
    except Exception as e:
        logger.error(
            "handler: list_applications request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")


def get_application(event: dict) -> dict:
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    application_id = (event.get("pathParameters") or {}).get("id", "")
    if not application_id:
        return _error_response(400, "VALIDATION_ERROR", "Missing application id")
    try:
        app = svc_get(application_id)
        logger.info(
            "handler: get_application request_id=%s status=200",
            request_id,
        )
        return _ok_response(200, _app_to_dict(app))
    except NotFoundError as e:
        logger.warning(
            "handler: get_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(404, "NOT_FOUND", "Application not found")
    except RepositoryError as e:
        logger.error(
            "handler: get_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")
    except Exception as e:
        logger.error(
            "handler: get_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")


def update_application(event: dict) -> dict:
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    application_id = (event.get("pathParameters") or {}).get("id", "")
    if not application_id:
        return _error_response(400, "VALIDATION_ERROR", "Missing application id")
    try:
        data = json.loads(event.get("body") or "{}")
        if not data:
            return _error_response(400, "VALIDATION_ERROR", "Request body must not be empty")
        app = svc_update(application_id, data)
        logger.info(
            "handler: update_application request_id=%s status=200",
            request_id,
        )
        return _ok_response(200, _app_to_dict(app))
    except ValidationError as e:
        logger.warning(
            "handler: update_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(400, "VALIDATION_ERROR", e.reason, e.field)
    except NotFoundError as e:
        logger.warning(
            "handler: update_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(404, "NOT_FOUND", "Application not found")
    except RepositoryError as e:
        logger.error(
            "handler: update_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")
    except Exception as e:
        logger.error(
            "handler: update_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")


def delete_application(event: dict) -> dict:
    request_id = event.get("requestContext", {}).get("requestId", "unknown")
    application_id = (event.get("pathParameters") or {}).get("id", "")
    if not application_id:
        return _error_response(400, "VALIDATION_ERROR", "Missing application id")
    try:
        svc_delete(application_id)
        logger.info(
            "handler: delete_application request_id=%s status=204",
            request_id,
        )
        return {
            "statusCode": 204,
            "headers": {"Content-Type": "application/json"},
            "body": "",
        }
    except NotFoundError as e:
        logger.warning(
            "handler: delete_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(404, "NOT_FOUND", "Application not found")
    except RepositoryError as e:
        logger.error(
            "handler: delete_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")
    except Exception as e:
        logger.error(
            "handler: delete_application request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
