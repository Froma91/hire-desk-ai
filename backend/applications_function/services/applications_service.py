"""
Service layer for Application CRUD operations.

Sits between Lambda handlers and the DynamoDB repository.
Responsibilities:
  - Input validation (via payload_validator)
  - Server-side value generation (UUID, timestamps, userId)
  - Orchestration of repository calls
  - Raising typed errors that handlers map to HTTP status codes

Does NOT know about HTTP, API Gateway events, or JSON serialisation.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from models import Application, Status, StatusEntry
from repositories.applications_repo import (
    ApplicationsRepo,
    NotFoundError,    # re-exported for handler convenience
    RepositoryError,  # re-exported for handler convenience
)
from validators.payload_validator import (
    validate_application_payload,
)

logger = logging.getLogger(__name__)

DEMO_USER_ID = "demo-user"

_UPDATABLE_FIELDS = frozenset({
    "jobTitle", "company", "location", "experienceLevel",
    "skills", "responsibilities", "languages", "status",
})


class ValidationError(Exception):
    """Raised when payload validation fails. Maps to HTTP 400."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(reason)
        self.field = field
        self.reason = reason


# ---------------------------------------------------------------------------
# Lazy repository factory
# ---------------------------------------------------------------------------

_repo_instance: Optional[ApplicationsRepo] = None


def _repo() -> ApplicationsRepo:
    global _repo_instance
    if _repo_instance is None:
        _repo_instance = ApplicationsRepo()
    return _repo_instance


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def create_application(data: dict) -> Application:
    """
    Validate, generate server-side fields, persist and return a new Application.

    Raises:
        ValidationError: if the payload fails validation.
        RepositoryError: if DynamoDB is unavailable.
    """
    logger.info("create_application: starting")

    # 1. Validate payload
    ok, err = validate_application_payload(data)
    if not ok:
        raise ValidationError(field=err["field"], reason=err["reason"])

    # 2. Generate server-side identifiers and timestamps
    application_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # 3. Resolve status
    raw_status = data.get("status")
    if raw_status is not None and isinstance(raw_status, str) and raw_status.strip():
        try:
            status = Status(raw_status)
        except ValueError:
            raise ValidationError(
                field="status",
                reason="Invalid status value",
            )
    else:
        status = Status.WISHLIST

    # 4. Build Application object
    app = Application(
        userId=DEMO_USER_ID,
        applicationId=application_id,
        jobTitle=data["jobTitle"],
        status=status,
        createdAt=now,
        updatedAt=now,
        company=data.get("company"),
        location=data.get("location"),
        experienceLevel=data.get("experienceLevel"),
        skills=data.get("skills", []),
        responsibilities=data.get("responsibilities", []),
        languages=data.get("languages", []),
        statusHistory=[StatusEntry(status=status, timestamp=now)],
        nextAction=None,
    )

    # 5. Persist
    _repo().put(app)

    # 6. Return the created application
    return app


def list_applications() -> list[Application]:
    """
    Return all Applications for the demo user, ordered by createdAt descending.

    Raises:
        RepositoryError: if DynamoDB is unavailable.
    """
    logger.info("list_applications: starting")
    return _repo().list_all()


def get_application(application_id: str) -> Application:
    """
    Fetch a single Application by ID.

    Raises:
        NotFoundError: if the application does not exist.
        RepositoryError: if DynamoDB is unavailable.
    """
    logger.info("get_application: application_id=%s", application_id)
    return _repo().get(application_id)


def update_application(application_id: str, data: dict) -> Application:
    """
    Partially update an existing Application.

    Validates the supplied fields, builds an update dict, and delegates to
    the repository. jobTitle is optional for partial updates; if absent a
    placeholder is injected before validation and removed afterwards.

    Raises:
        ValidationError: if any supplied field fails validation.
        NotFoundError: if the application does not exist.
        RepositoryError: if DynamoDB is unavailable.
    """
    logger.info("update_application: application_id=%s", application_id)

    # 1. Validate — inject placeholder for jobTitle when absent so the
    #    "required" check in the validator does not reject partial updates.
    validation_data = data.copy()
    if "jobTitle" not in validation_data:
        validation_data["jobTitle"] = "_placeholder_"

    ok, err = validate_application_payload(validation_data)
    if not ok:
        raise ValidationError(field=err["field"], reason=err["reason"])

    # 2. Build the fields dict restricted to updatable keys
    fields: dict = {}
    for key in _UPDATABLE_FIELDS:
        if key in data:
            fields[key] = data[key]

    # 3. Validate and convert status if present
    if "status" in fields:
        raw_status = fields["status"]
        if not isinstance(raw_status, str) or not raw_status.strip():
            raise ValidationError(field="status", reason="Invalid status value")
        try:
            fields["status"] = Status(raw_status)
        except ValueError:
            raise ValidationError(field="status", reason="Invalid status value")

    # 4. Always stamp updatedAt
    fields["updatedAt"] = datetime.now(timezone.utc)

    # 5. Persist and return updated application
    return _repo().update(application_id, fields)


def delete_application(application_id: str) -> None:
    """
    Delete an Application by ID.

    Raises:
        NotFoundError: if the application does not exist.
        RepositoryError: if DynamoDB is unavailable.
    """
    logger.info("delete_application: application_id=%s", application_id)
    _repo().delete(application_id)
