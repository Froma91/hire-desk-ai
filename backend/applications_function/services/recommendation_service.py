"""
Recommendation service — retrieves an application and computes its next action.

This service sits between the handler and the repository/engine layers.
It does NOT call Bedrock — the explanation field is always None at this stage.

Testable by mocking the repository and current time.
"""

from datetime import datetime, timezone
from typing import Optional

from applications_function.models import Application, NextAction
from applications_function.repositories.applications_repo import (
    NotFoundError,
    RepositoryError,
)
from applications_function.business_rules.next_action_engine import compute_next_action
from applications_function.services.applications_service import _repo


def get_recommendation(application_id: str) -> tuple[Application, Optional[NextAction]]:
    """
    Retrieve an application and compute its deterministic next action.

    Args:
        application_id: The application's UUID.

    Returns:
        A tuple of (Application, NextAction | None).
        The Application is never mutated.
        explanation is always None (no Bedrock at this stage).

    Raises:
        NotFoundError: if the application does not exist.
        RepositoryError: if DynamoDB is unavailable.
    """
    # 1. Retrieve the application
    app = _repo().get(application_id)

    # 2. Compute next action using current UTC time
    now = datetime.now(timezone.utc)
    next_action = compute_next_action(app, now)

    # 3. Return without mutating the application
    return app, next_action
