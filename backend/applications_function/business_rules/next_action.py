"""
Deterministic next-action computation (business rules layer).

This module computes the recommended next action based on the current
application status. The rules are deterministic and do not depend on AI.

Full implementation with date-based logic is in task 9.1.
This file provides the minimum compatible integration boundary.
"""

from typing import Optional

from applications_function.models import (
    Application,
    NextAction,
    Priority,
    Status,
)


# ---------------------------------------------------------------------------
# Simple status-based rules (no date logic yet — added in task 9.1)
# ---------------------------------------------------------------------------

_STATUS_RULES: dict[Status, tuple[str, Priority]] = {
    Status.WISHLIST: ("Review job description and prepare application", Priority.MEDIUM),
    Status.APPLIED: ("Follow up if no response within a week", Priority.MEDIUM),
    Status.INTERVIEW: ("Prepare for the interview", Priority.HIGH),
    Status.OFFER: ("Review the offer and respond", Priority.HIGH),
    Status.REJECTED: ("Archive and continue applying elsewhere", Priority.LOW),
}


def compute_next_action(
    status: Status,
    application: Application,
) -> Optional[NextAction]:
    """
    Compute the deterministic next action for an application given its status.

    Args:
        status: The new/current status of the application.
        application: The full application object (for future date-based rules).

    Returns:
        A NextAction with label and priority, or None if no action is applicable.

    Note:
        This is a minimal implementation. Task 9.1 will add:
        - Date-based delay calculations
        - Priority adjustments based on time since last status change
        - More granular action labels
    """
    rule = _STATUS_RULES.get(status)
    if rule is None:
        return None

    label, priority = rule
    return NextAction(label=label, priority=priority, explanation=None)
