"""DynamoDB repository for Application records."""

import os
import logging
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from models import (
    Application, Status, Priority, StatusEntry, NextAction,
)

logger = logging.getLogger(__name__)

DEMO_USER_ID = "demo-user"

_BOTO_CONFIG = Config(connect_timeout=5, read_timeout=5)


class RepositoryError(Exception):
    """Raised on DynamoDB ClientError or timeout. Maps to HTTP 503."""


class NotFoundError(Exception):
    """Raised when an item does not exist in DynamoDB. Maps to HTTP 404."""


class ApplicationsRepo:
    def __init__(self) -> None:
        self._table_name: str = os.environ["TABLE_NAME"]
        self._dynamodb = boto3.resource("dynamodb", config=_BOTO_CONFIG)
        self._table = self._dynamodb.Table(self._table_name)

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def put(self, app: Application) -> None:
        """Write a new Application. Raises RepositoryError on failure."""
        item = self._to_item(app)
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(applicationId)",
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                raise RepositoryError(
                    f"Application {app.applicationId} already exists"
                ) from e
            raise RepositoryError(f"DynamoDB error: {code}") from e
        except Exception as e:
            raise RepositoryError(
                f"DynamoDB timeout or unexpected error: {e}"
            ) from e

    def get(self, application_id: str) -> Application:
        """Read one Application by ID. Raises NotFoundError if absent."""
        try:
            response = self._table.get_item(
                Key={
                    "userId": DEMO_USER_ID,
                    "applicationId": application_id,
                }
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            raise RepositoryError(f"DynamoDB error: {code}") from e
        except Exception as e:
            raise RepositoryError(
                f"DynamoDB timeout or unexpected error: {e}"
            ) from e

        item = response.get("Item")
        if item is None:
            raise NotFoundError(
                f"Application {application_id} not found"
            )
        return self._from_item(item)

    def list_all(self) -> list[Application]:
        """Return all Applications for demo-user, createdAt descending."""
        try:
            response = self._table.query(
                KeyConditionExpression="userId = :uid",
                ExpressionAttributeValues={":uid": DEMO_USER_ID},
                ScanIndexForward=False,
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            raise RepositoryError(f"DynamoDB error: {code}") from e
        except Exception as e:
            raise RepositoryError(
                f"DynamoDB timeout or unexpected error: {e}"
            ) from e

        items = response.get("Items", [])

        # Handle pagination
        while "LastEvaluatedKey" in response:
            try:
                response = self._table.query(
                    KeyConditionExpression="userId = :uid",
                    ExpressionAttributeValues={":uid": DEMO_USER_ID},
                    ScanIndexForward=False,
                    ExclusiveStartKey=response["LastEvaluatedKey"],
                )
            except ClientError as e:
                code = e.response["Error"]["Code"]
                raise RepositoryError(f"DynamoDB error: {code}") from e
            except Exception as e:
                raise RepositoryError(
                    f"DynamoDB timeout or unexpected error: {e}"
                ) from e
            items.extend(response.get("Items", []))

        applications = [self._from_item(item) for item in items]
        # Sort by createdAt descending in Python (sort key is applicationId UUID,
        # not meaningful for date order)
        applications.sort(key=lambda a: a.createdAt, reverse=True)
        return applications

    def update(self, application_id: str, fields: dict) -> Application:
        """Partial update. Raises NotFoundError if absent.

        Fields whose value is ``None`` are REMOVEd from the item rather than
        stored as a DynamoDB NULL. This prevents persisting attributes such as
        ``nextAction = NULL`` which previously broke every reader that
        deserialised the item.
        """
        # Serialise field values before passing to DynamoDB
        serialised: dict = {}
        for key, value in fields.items():
            if isinstance(value, Status):
                serialised[key] = value.value
            elif isinstance(value, datetime):
                serialised[key] = value.isoformat()
            else:
                serialised[key] = value

        set_parts: list[str] = []
        remove_parts: list[str] = []
        expr_names: dict[str, str] = {}
        expr_values: dict[str, object] = {}

        for i, (key, value) in enumerate(serialised.items()):
            placeholder_name = f"#f{i}"
            expr_names[placeholder_name] = key
            if value is None:
                # Translate a None value into a REMOVE clause so the attribute
                # is dropped instead of being stored as NULL.
                remove_parts.append(placeholder_name)
            else:
                placeholder_value = f":v{i}"
                expr_values[placeholder_value] = value
                set_parts.append(f"{placeholder_name} = {placeholder_value}")

        clauses: list[str] = []
        if set_parts:
            clauses.append("SET " + ", ".join(set_parts))
        if remove_parts:
            clauses.append("REMOVE " + ", ".join(remove_parts))
        update_expr = " ".join(clauses)

        update_kwargs: dict = {
            "Key": {
                "userId": DEMO_USER_ID,
                "applicationId": application_id,
            },
            "UpdateExpression": update_expr,
            "ExpressionAttributeNames": expr_names,
            "ConditionExpression": "attribute_exists(applicationId)",
            "ReturnValues": "ALL_NEW",
        }
        # Only include ExpressionAttributeValues when there is at least one SET
        # value; DynamoDB rejects an empty/unused values map.
        if expr_values:
            update_kwargs["ExpressionAttributeValues"] = expr_values

        try:
            response = self._table.update_item(**update_kwargs)
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                raise NotFoundError(
                    f"Application {application_id} not found"
                ) from e
            raise RepositoryError(f"DynamoDB error: {code}") from e
        except Exception as e:
            raise RepositoryError(
                f"DynamoDB timeout or unexpected error: {e}"
            ) from e

        return self._from_item(response["Attributes"])

    def delete(self, application_id: str) -> None:
        """Delete one Application. Raises NotFoundError if absent."""
        try:
            self._table.delete_item(
                Key={
                    "userId": DEMO_USER_ID,
                    "applicationId": application_id,
                },
                ConditionExpression="attribute_exists(applicationId)",
            )
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                raise NotFoundError(
                    f"Application {application_id} not found"
                ) from e
            raise RepositoryError(f"DynamoDB error: {code}") from e
        except Exception as e:
            raise RepositoryError(
                f"DynamoDB timeout or unexpected error: {e}"
            ) from e

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _to_item(self, app: Application) -> dict:
        item: dict = {
            "userId": app.userId,
            "applicationId": app.applicationId,
            "jobTitle": app.jobTitle,
            "status": app.status.value,
            "createdAt": app.createdAt.isoformat(),
            "updatedAt": app.updatedAt.isoformat(),
        }
        # Optional string fields — only write if not None
        for f in ("company", "location", "experienceLevel"):
            v = getattr(app, f)
            if v is not None:
                item[f] = v
        # List fields — always write (even if empty)
        item["skills"] = app.skills
        item["responsibilities"] = app.responsibilities
        item["languages"] = app.languages
        # statusHistory
        item["statusHistory"] = [
            {"status": e.status.value, "timestamp": e.timestamp.isoformat()}
            for e in app.statusHistory
        ]
        # nextAction — only write if not None
        if app.nextAction is not None:
            na: dict = {
                "label": app.nextAction.label,
                "priority": app.nextAction.priority.value,
            }
            if app.nextAction.explanation is not None:
                na["explanation"] = app.nextAction.explanation
            item["nextAction"] = na
        return item

    def _from_item(self, item: dict) -> Application:
        def parse_dt(s: str) -> datetime:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt

        # nextAction — defensively deserialize.
        #   - attribute missing               → None
        #   - attribute stored as NULL (None) → None
        #   - attribute stored as a map/dict  → build NextAction
        # Never subscript a None value (this was the production defect: a
        # persisted `nextAction = NULL` broke every reader that touched it).
        next_action: Optional[NextAction] = None
        raw_na = item.get("nextAction")
        if isinstance(raw_na, Mapping):
            label = raw_na.get("label")
            raw_priority = raw_na.get("priority")
            priority: Optional[Priority] = None
            if raw_priority is not None:
                try:
                    priority = Priority(raw_priority)
                except ValueError:
                    logger.warning(
                        "repo: _from_item invalid nextAction.priority=%r application_id=%s",
                        raw_priority,
                        item.get("applicationId"),
                    )
                    priority = None
            # Only construct a NextAction when the minimally-required fields
            # are usable; otherwise leave it as None rather than crashing.
            if label is not None and priority is not None:
                next_action = NextAction(
                    label=label,
                    priority=priority,
                    explanation=raw_na.get("explanation"),
                )
            else:
                logger.warning(
                    "repo: _from_item skipping malformed nextAction=%r application_id=%s",
                    raw_na,
                    item.get("applicationId"),
                )

        # statusHistory — defensively parse. A single malformed entry must not
        # break the entire GET /applications or GET /stats response, so skip
        # entries that are not well-formed dicts with a valid status/timestamp.
        status_history: list[StatusEntry] = []
        for e in item.get("statusHistory", []) or []:
            if not isinstance(e, Mapping):
                logger.warning(
                    "repo: _from_item skipping non-dict statusHistory entry=%r application_id=%s",
                    e,
                    item.get("applicationId"),
                )
                continue
            raw_status = e.get("status")
            raw_ts = e.get("timestamp")
            if raw_status is None or raw_ts is None:
                logger.warning(
                    "repo: _from_item skipping incomplete statusHistory entry=%r application_id=%s",
                    e,
                    item.get("applicationId"),
                )
                continue
            try:
                status_history.append(
                    StatusEntry(
                        status=Status(raw_status),
                        timestamp=parse_dt(raw_ts),
                    )
                )
            except (ValueError, TypeError) as exc:
                logger.warning(
                    "repo: _from_item skipping malformed statusHistory entry=%r "
                    "application_id=%s error=%s",
                    e,
                    item.get("applicationId"),
                    exc,
                )
                continue

        return Application(
            userId=item["userId"],
            applicationId=item["applicationId"],
            jobTitle=item["jobTitle"],
            status=Status(item["status"]),
            createdAt=parse_dt(item["createdAt"]),
            updatedAt=parse_dt(item["updatedAt"]),
            company=item.get("company"),
            location=item.get("location"),
            experienceLevel=item.get("experienceLevel"),
            skills=list(item.get("skills", [])),
            responsibilities=list(item.get("responsibilities", [])),
            languages=list(item.get("languages", [])),
            statusHistory=status_history,
            nextAction=next_action,
        )
