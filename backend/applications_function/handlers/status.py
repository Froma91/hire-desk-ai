"""
Status update handler for PATCH /applications/{id}/status.

Validates the status value, updates the application's status, appends a
statusHistory entry, recomputes the deterministic nextAction, and persists
everything in a single update call.

Error mapping:
  Invalid status → 400 VALIDATION_ERROR
  NotFoundError  → 404 NOT_FOUND
  RepositoryError → 503 SERVICE_UNAVAILABLE
  other          → 500 INTERNAL_ERROR
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from models import Application, Status, StatusEntry
from services.applications_service import (
    get_application as svc_get_application,
    ValidationError,
    NotFoundError,
    RepositoryError,
    _repo,
)
from business_rules.next_action import compute_next_action

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Valid status values (matches the Status enum)
# ---------------------------------------------------------------------------

_VALID_STATUSES = frozenset(s.value for s in Status)


# ---------------------------------------------------------------------------
# Private helpers (same conventions as handlers/applications.py)
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
# Handler
# ---------------------------------------------------------------------------

def update_status(event: dict) -> dict:
    """
    Handle PATCH /applications/{id}/status.

    Expects JSON body: {"status": "Wishlist|Applied|Interview|Offer|Rejected"}

    Steps:
      1. Parse applicationId from path parameters
      2. Parse and validate status from request body
      3. Fetch the current application
      4. Append a new statusHistory entry with the current UTC timestamp
      5. Update status, statusHistory, updatedAt
      6. Recompute nextAction using deterministic business rules
      7. Persist all changes in a single repo.update() call
      8. Return the full updated application
    """
    request_id = event.get("requestContext", {}).get("requestId", "unknown")

    # 1. Parse applicationId
    application_id = (event.get("pathParameters") or {}).get("id", "")
    if not application_id:
        return _error_response(400, "VALIDATION_ERROR", "Missing application id")

    # 2. Parse and validate status from body
    try:
        data = json.loads(event.get("body") or "{}")
    except (json.JSONDecodeError, TypeError):
        return _error_response(400, "VALIDATION_ERROR", "Invalid request body")

    raw_status = data.get("status")
    if not raw_status or not isinstance(raw_status, str):
        return _error_response(
            400, "VALIDATION_ERROR", "status is required", "status"
        )

    raw_status = raw_status.strip()
    if raw_status not in _VALID_STATUSES:
        return _error_response(
            400,
            "VALIDATION_ERROR",
            f"Invalid status. Must be one of: {', '.join(sorted(_VALID_STATUSES))}",
            "status",
        )

    new_status = Status(raw_status)

    # 3. Fetch the current application
    try:
        app = svc_get_application(application_id)
    except NotFoundError:
        logger.warning(
            "handler: update_status request_id=%s error_type=NotFoundError application_id=%s",
            request_id,
            application_id,
        )
        return _error_response(404, "NOT_FOUND", "Application not found")
    except RepositoryError as e:
        logger.error(
            "handler: update_status request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")

    # 4. Build updated fields
    now = datetime.now(timezone.utc)

    # Append new status history entry
    updated_history = [
        {"status": entry.status.value, "timestamp": entry.timestamp.isoformat()}
        for entry in app.statusHistory
    ]
    updated_history.append({"status": new_status.value, "timestamp": now.isoformat()})

    # 5. Recompute nextAction using deterministic business rules
    next_action = compute_next_action(new_status, app)
    next_action_dict = None
    if next_action is not None:
        next_action_dict = {
            "label": next_action.label,
            "priority": next_action.priority.value,
        }
        if next_action.explanation is not None:
            next_action_dict["explanation"] = next_action.explanation

    # 6. Persist all changes in a single update
    fields = {
        "status": new_status,
        "statusHistory": updated_history,
        "updatedAt": now,
        "nextAction": next_action_dict,
    }

    try:
        updated_app = _repo().update(application_id, fields)
        logger.info(
            "handler: update_status request_id=%s status=200 application_id=%s new_status=%s",
            request_id,
            application_id,
            new_status.value,
        )
        return _ok_response(200, _app_to_dict(updated_app))
    except NotFoundError:
        logger.warning(
            "handler: update_status request_id=%s error_type=NotFoundError application_id=%s",
            request_id,
            application_id,
        )
        return _error_response(404, "NOT_FOUND", "Application not found")
    except RepositoryError as e:
        logger.error(
            "handler: update_status request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")
    except Exception as e:
        logger.error(
            "handler: update_status request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
