"""
Deterministic next-action engine — local copy for JobAnalysisFunction deployment.

Pure function that computes the recommended next action for an application
based on its current status, dates, and status history.

This module performs NO I/O, NO Bedrock calls, NO side effects.
"""

from datetime import datetime
from typing import Optional

from job_analysis_function.models import (
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
        now: Current UTC datetime (timezone-aware).

    Returns:
        A NextAction with label and priority, or None if no action is
        applicable for the current state.

    Rules:
        - Wishlist + older than 7 days + no status change -> "Apply now" (HIGH)
        - Applied + no update in 14 days + no status change -> "Follow up" (MEDIUM)
        - Interview (always) -> "Prepare for interview" (HIGH)
        - Offer (always) -> "Review and respond to offer" (HIGH)
        - Rejected (always) -> "Archive or reapply" (LOW)
        - Any other status -> None
    """
    age_days = (now - app.createdAt).days
    days_since_update = (now - app.updatedAt).days
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
