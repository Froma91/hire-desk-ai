"""
Recommendation service — retrieves an application and computes its next action
with optional Bedrock explanation enrichment.

This service:
  - Retrieves the application via ApplicationsRepo
  - Calls compute_next_action(app, now) for deterministic recommendation
  - If a NextAction exists, attempts to enrich it with a Bedrock explanation
  - On Bedrock failure, returns the deterministic recommendation with explanation=None
  - RepositoryError and NotFoundError propagate normally (never hidden)
  - NEVER logs full Application, job-description content, or Bedrock response text

Testable by mocking the repository, current time, and explanation_service.
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
from applications_function.services.explanation_service import generate_explanation


def get_recommendation(application_id: str) -> tuple[Application, Optional[NextAction]]:
    """
    Retrieve an application, compute its deterministic next action, and
    optionally enrich it with a Bedrock-generated explanation.

    Args:
        application_id: The application's UUID.

    Returns:
        A tuple of (Application, NextAction | None).
        The Application is never mutated.
        If a NextAction exists:
          - explanation is a ≤ 280 char string when Bedrock succeeds
          - explanation is None when Bedrock fails or returns invalid content

    Raises:
        NotFoundError: if the application does not exist.
        RepositoryError: if DynamoDB is unavailable.
    """
    # 1. Retrieve the application
    app = _repo().get(application_id)

    # 2. Compute next action using current UTC time
    now = datetime.now(timezone.utc)
    next_action = compute_next_action(app, now)

    # 3. If no action, return immediately (no Bedrock call)
    if next_action is None:
        return app, None

    # 4. Attempt Bedrock explanation enrichment (graceful degradation)
    explanation = generate_explanation(
        label=next_action.label,
        status=app.status.value,
    )

    # 5. Attach explanation (may be None if Bedrock failed)
    #    Create a new NextAction to avoid mutating the engine's output
    enriched_action = NextAction(
        label=next_action.label,
        priority=next_action.priority,
        explanation=explanation,
    )

    return app, enriched_action
