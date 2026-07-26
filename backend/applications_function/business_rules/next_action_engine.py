"""
Deterministic next-action engine.

Pure function that computes the recommended next action for an application
based on its current status, dates, and status history.

This module performs:
  - NO I/O (no DynamoDB, no HTTP, no Lambda invocations)
  - NO Bedrock calls
  - NO logging
  - NO environment variable access
  - NO mutation of the supplied Application object
  - NO side effects of any kind

The `explanation` field is always `None` here. Bedrock-generated explanations
are appended separately by the recommendation handler.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.9, 6.10, 6.11
"""

from datetime import datetime
from typing import Optional

from applications_function.models import (
    Application,
    NextAction,
    Priority,
    Status,
)


def compute_next_action(app: Application, now: datetime) -> Optional[NextAction]:
    """
    Compute the deterministic next action for an application.

    Args:
        app: The Application object (never mutated).
        now: Current UTC datetime (timezone-aware). Used to calculate time-based
             conditions.

    Returns:
        A NextAction with label and priority, or None if no action is
        applicable for the current state.

    Rules:
        - Wishlist + older than 7 days + no status change → "Apply now" (HIGH)
        - Wishlist otherwise → None
        - Applied + no update in 14 days + no status change → "Follow up" (MEDIUM)
        - Applied otherwise → None
        - Interview (always) → "Prepare for interview" (HIGH)
        - Offer (always) → "Review and respond to offer" (HIGH)
        - Rejected (always) → "Archive or reapply" (LOW)
        - Any other status → None
    """
    age_days = (now - app.createdAt).days
    days_since_update = (now - app.updatedAt).days

    # Detect whether a status change has occurred (history length > 1 means at
    # least one transition happened after creation).
    has_status_change = len(app.statusHistory) > 1

    match app.status:
        case Status.WISHLIST:
            if age_days > 7 and not has_status_change:
                return NextAction(label="Apply now", priority=Priority.HIGH, explanation=None)
            return None

        case Status.APPLIED:
            if days_since_update > 14 and not has_status_change:
                return NextAction(label="Follow up", priority=Priority.MEDIUM, explanation=None)
            return None

        case Status.INTERVIEW:
            return NextAction(label="Prepare for interview", priority=Priority.HIGH, explanation=None)

        case Status.OFFER:
            return NextAction(label="Review and respond to offer", priority=Priority.HIGH, explanation=None)

        case Status.REJECTED:
            return NextAction(label="Archive or reapply", priority=Priority.LOW, explanation=None)

        case _:
            return None
