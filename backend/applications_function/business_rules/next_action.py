"""
Backward-compatibility adapter for the next-action engine.

The status handler (handlers/status.py) imports `compute_next_action` from
this module with the call signature:

    compute_next_action(status: Status, application: Application)

This adapter bridges that call to the canonical engine in
`next_action_engine.py` which uses the spec-defined signature:

    compute_next_action(app: Application, now: datetime)

The adapter patches `app.status` to the provided `status` value before
delegating to the engine, because the handler calls this function with the
NEW status while the Application object still carries the OLD status.

This file will be removed or inlined once the status handler is updated
to call the engine directly.
"""

from dataclasses import replace
from datetime import datetime, timezone
from typing import Optional

from models import (
    Application,
    NextAction,
    Priority,
    Status,
)
from business_rules.next_action_engine import (
    compute_next_action as engine_compute_next_action,
)


def compute_next_action(
    status: Status,
    application: Application,
) -> Optional[NextAction]:
    """
    Compatibility adapter: translates (status, application) → (app, now).

    The handler passes the NEW status as the first argument while the
    Application object still has the OLD status set. We create a shallow
    copy with the updated status so the engine can read `app.status`
    correctly.

    Args:
        status: The new status that should be evaluated.
        application: The Application object (not mutated).

    Returns:
        A NextAction with label and priority, or None.
    """
    now = datetime.now(timezone.utc)
    patched_app = replace(application, status=status)
    return engine_compute_next_action(patched_app, now)
