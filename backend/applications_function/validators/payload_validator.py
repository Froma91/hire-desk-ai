"""Payload validator for Application create/update requests."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# DynamoDB and server-side identifiers that must never be supplied by the client.
FORBIDDEN_KEYS: frozenset[str] = frozenset({
    "TableName", "IndexName", "KeyConditionExpression",
    "FilterExpression", "ProjectionExpression", "ExpressionAttributeNames",
    "ExpressionAttributeValues", "userId", "applicationId",
    "createdAt", "updatedAt", "statusHistory", "nextAction",
})

_STRING_FIELDS: tuple[str, ...] = ("jobTitle", "company", "location", "experienceLevel")
_LIST_FIELDS: tuple[str, ...] = ("skills", "responsibilities", "languages")

_MAX_STRING_LEN = 500
_MAX_ITEM_LEN = 200
_MAX_LIST_SIZE = 30


def validate_application_payload(
    data: dict,
) -> tuple[bool, Optional[dict]]:
    """
    Validate an Application create or partial-update payload.

    Returns (True, None) when all checks pass.
    Returns (False, {"field": str, "reason": str}) on the first failing check.

    Property 4: Lambda field validation accepts iff all constraints satisfied.
    Validates: Requirements 2.6, 2.7, 8.2, 8.3
    """
    # ------------------------------------------------------------------
    # 1. Forbidden key check — top-level and one level deep
    # ------------------------------------------------------------------
    for key in data:
        if key in FORBIDDEN_KEYS:
            logger.warning("Forbidden field in payload: field=%s", key)
            return False, {"field": key, "reason": "Forbidden field"}

    for key, value in data.items():
        if isinstance(value, dict):
            for nested_key in value:
                if nested_key in FORBIDDEN_KEYS:
                    logger.warning(
                        "Forbidden nested field in payload: parent=%s field=%s",
                        key, nested_key,
                    )
                    return False, {
                        "field": nested_key,
                        "reason": "Forbidden field",
                    }

    # ------------------------------------------------------------------
    # 2. jobTitle — required, non-empty, ≤ 500 chars
    # ------------------------------------------------------------------
    job_title = data.get("jobTitle")
    if job_title is None or (isinstance(job_title, str) and not job_title.strip()):
        return False, {
            "field": "jobTitle",
            "reason": "jobTitle is required and must be non-empty",
        }
    if isinstance(job_title, str) and len(job_title) > _MAX_STRING_LEN:
        return False, {
            "field": "jobTitle",
            "reason": f"jobTitle must not exceed {_MAX_STRING_LEN} characters",
        }

    # ------------------------------------------------------------------
    # 3. Optional string fields — ≤ 500 chars when present
    # ------------------------------------------------------------------
    for field in ("company", "location", "experienceLevel"):
        value = data.get(field)
        if value is not None and isinstance(value, str) and len(value) > _MAX_STRING_LEN:
            return False, {
                "field": field,
                "reason": f"{field} must not exceed {_MAX_STRING_LEN} characters",
            }

    # ------------------------------------------------------------------
    # 4. List fields — ≤ 30 items, each item a str ≤ 200 chars
    # ------------------------------------------------------------------
    for field in _LIST_FIELDS:
        value = data.get(field)
        if value is None:
            continue
        if not isinstance(value, list):
            return False, {
                "field": field,
                "reason": f"{field} must be a list",
            }
        if len(value) > _MAX_LIST_SIZE:
            return False, {
                "field": field,
                "reason": f"{field} must not contain more than {_MAX_LIST_SIZE} items",
            }
        for item in value:
            if not isinstance(item, str) or len(item) > _MAX_ITEM_LEN:
                return False, {
                    "field": field,
                    "reason": (
                        f"Each item in {field} must be a string "
                        f"of at most {_MAX_ITEM_LEN} characters"
                    ),
                }

    return True, None
