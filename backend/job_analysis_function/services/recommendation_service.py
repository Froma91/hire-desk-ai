"""
Recommendation service for JobAnalysisFunction.

Self-contained: reads from DynamoDB directly (no cross-Lambda imports).
Computes deterministic next action and optionally enriches with Bedrock explanation.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from models import (
    Application, Status, Priority, StatusEntry, NextAction,
)
from services.next_action_engine import compute_next_action
from services.explanation_service import generate_explanation

logger = logging.getLogger(__name__)

_BOTO_CONFIG = Config(connect_timeout=5, read_timeout=5)
DEMO_USER_ID = "demo-user"


class NotFoundError(Exception):
    """Application not found in DynamoDB."""


class RepositoryError(Exception):
    """DynamoDB access failure."""


_dynamodb_resource = None


def _get_table():
    """Lazy-initialize the DynamoDB table resource."""
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb", config=_BOTO_CONFIG)
    table_name = os.environ["TABLE_NAME"]
    return _dynamodb_resource.Table(table_name)


def _parse_dt(s: str) -> datetime:
    """Parse an ISO datetime string, defaulting to UTC if no timezone."""
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _from_item(item: dict) -> Application:
    """Convert a DynamoDB item dict to an Application dataclass."""
    next_action: Optional[NextAction] = None
    if "nextAction" in item:
        na = item["nextAction"]
        next_action = NextAction(
            label=na["label"],
            priority=Priority(na["priority"]),
            explanation=na.get("explanation"),
        )

    status_history = [
        StatusEntry(status=Status(e["status"]), timestamp=_parse_dt(e["timestamp"]))
        for e in item.get("statusHistory", [])
    ]

    return Application(
        userId=item["userId"],
        applicationId=item["applicationId"],
        jobTitle=item["jobTitle"],
        status=Status(item["status"]),
        createdAt=_parse_dt(item["createdAt"]),
        updatedAt=_parse_dt(item["updatedAt"]),
        company=item.get("company"),
        location=item.get("location"),
        experienceLevel=item.get("experienceLevel"),
        skills=list(item.get("skills", [])),
        responsibilities=list(item.get("responsibilities", [])),
        languages=list(item.get("languages", [])),
        statusHistory=status_history,
        nextAction=next_action,
    )


def get_recommendation(application_id: str) -> tuple[Application, Optional[NextAction]]:
    """
    Retrieve application from DynamoDB, compute next action, enrich with explanation.

    Raises:
        NotFoundError: application does not exist.
        RepositoryError: DynamoDB access failure.
    """
    try:
        response = _get_table().get_item(
            Key={"userId": DEMO_USER_ID, "applicationId": application_id}
        )
    except ClientError as e:
        code = e.response["Error"]["Code"]
        raise RepositoryError(f"DynamoDB error: {code}") from e
    except Exception as e:
        raise RepositoryError("DynamoDB error") from e

    item = response.get("Item")
    if item is None:
        raise NotFoundError(f"Application {application_id} not found")

    app = _from_item(item)
    now = datetime.now(timezone.utc)
    next_action = compute_next_action(app, now)

    if next_action is None:
        return app, None

    # Attempt Bedrock explanation enrichment (graceful degradation)
    explanation = generate_explanation(label=next_action.label, status=app.status.value)

    enriched = NextAction(
        label=next_action.label,
        priority=next_action.priority,
        explanation=explanation,
    )
    return app, enriched
