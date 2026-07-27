"""
Regression tests for ApplicationsRepo deserialization and update behavior.

Covers the production defect where a persisted ``nextAction = NULL`` broke
every reader (GET /applications, GET /stats) because ``_from_item`` blindly
subscripted the None value. Also covers defensive statusHistory parsing and
the SET/REMOVE UpdateExpression construction.

All DynamoDB/boto3 interactions are mocked; no real AWS calls are made.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Lambda-root isolation bootstrap (ApplicationsFunction / flat layout).
# Purge any flat top-level modules left by another Lambda's test module, then
# put THIS Lambda's root first on sys.path so bare imports resolve correctly.
# ---------------------------------------------------------------------------
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_LAMBDA_ROOT = os.path.join(_BACKEND, "applications_function")
_FLAT = {"app", "models", "handlers", "services", "validators", "repositories", "business_rules"}
for _n in list(sys.modules):
    if _n.split(".")[0] in _FLAT:
        del sys.modules[_n]
if _LAMBDA_ROOT in sys.path:
    sys.path.remove(_LAMBDA_ROOT)
sys.path.insert(0, _LAMBDA_ROOT)

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

import repositories.applications_repo as repo_mod
from repositories.applications_repo import ApplicationsRepo
from models import Application, Status, NextAction, Priority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW_ISO = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc).isoformat()


def _raw_item(application_id="app-1", **overrides) -> dict:
    """Build a raw DynamoDB item (as boto3 resource would deserialise it)."""
    item = {
        "userId": "demo-user",
        "applicationId": application_id,
        "jobTitle": "Engineer",
        "status": "Wishlist",
        "createdAt": _NOW_ISO,
        "updatedAt": _NOW_ISO,
        "skills": [],
        "responsibilities": [],
        "languages": [],
        "statusHistory": [{"status": "Wishlist", "timestamp": _NOW_ISO}],
    }
    item.update(overrides)
    return item


def _make_repo(query_items=None):
    """Construct an ApplicationsRepo backed by a mocked DynamoDB table."""
    mock_table = MagicMock()
    if query_items is not None:
        mock_table.query.return_value = {"Items": list(query_items)}
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    with patch.dict(os.environ, {"TABLE_NAME": "test-table"}):
        with patch.object(repo_mod.boto3, "resource", return_value=mock_resource):
            repo = ApplicationsRepo()
    return repo, mock_table


# ---------------------------------------------------------------------------
# _from_item — nextAction deserialization
# ---------------------------------------------------------------------------

class TestFromItemNextAction:
    def test_next_action_missing_yields_none(self):
        """nextAction attribute absent → nextAction is None, no error."""
        repo, _ = _make_repo()
        item = _raw_item()
        assert "nextAction" not in item
        app = repo._from_item(item)
        assert app.nextAction is None

    def test_next_action_null_yields_none(self):
        """nextAction stored as None (DynamoDB NULL) → nextAction is None, no error."""
        repo, _ = _make_repo()
        item = _raw_item(nextAction=None)
        app = repo._from_item(item)
        assert app.nextAction is None

    def test_next_action_valid_map_constructs_next_action(self):
        """A valid nextAction map deserialises into a NextAction object."""
        repo, _ = _make_repo()
        item = _raw_item(
            nextAction={
                "label": "Follow up",
                "priority": "Medium",
                "explanation": "Reach out to the recruiter",
            }
        )
        app = repo._from_item(item)
        assert app.nextAction == NextAction(
            label="Follow up",
            priority=Priority.MEDIUM,
            explanation="Reach out to the recruiter",
        )

    def test_next_action_map_missing_explanation_is_none(self):
        """nextAction map without explanation → explanation is None."""
        repo, _ = _make_repo()
        item = _raw_item(nextAction={"label": "Apply now", "priority": "High"})
        app = repo._from_item(item)
        assert app.nextAction is not None
        assert app.nextAction.explanation is None
        assert app.nextAction.priority == Priority.HIGH

    def test_next_action_invalid_priority_does_not_crash(self):
        """A malformed priority is skipped rather than raising."""
        repo, _ = _make_repo()
        item = _raw_item(nextAction={"label": "X", "priority": "Bogus"})
        app = repo._from_item(item)
        assert app.nextAction is None


# ---------------------------------------------------------------------------
# _from_item — statusHistory defensive parsing
# ---------------------------------------------------------------------------

class TestFromItemStatusHistory:
    def test_missing_status_history_yields_empty(self):
        """Missing statusHistory → empty list, no error."""
        repo, _ = _make_repo()
        item = _raw_item()
        del item["statusHistory"]
        app = repo._from_item(item)
        assert app.statusHistory == []

    def test_empty_status_history_yields_empty(self):
        """Empty statusHistory → empty list, no error."""
        repo, _ = _make_repo()
        item = _raw_item(statusHistory=[])
        app = repo._from_item(item)
        assert app.statusHistory == []

    def test_malformed_status_history_entries_are_skipped(self):
        """Malformed / null / incomplete entries are skipped without crashing."""
        repo, _ = _make_repo()
        item = _raw_item(
            statusHistory=[
                {"status": "Wishlist", "timestamp": _NOW_ISO},  # valid
                None,                                            # null entry
                "not-a-dict",                                    # wrong type
                {"status": "Applied"},                           # missing timestamp
                {"timestamp": _NOW_ISO},                         # missing status
                {"status": "Nonsense", "timestamp": _NOW_ISO},   # invalid status
            ]
        )
        app = repo._from_item(item)
        # Only the single valid entry survives.
        assert len(app.statusHistory) == 1
        assert app.statusHistory[0].status == Status.WISHLIST


# ---------------------------------------------------------------------------
# list_all — mixture of items must all deserialise
# ---------------------------------------------------------------------------

class TestListAllMixture:
    def test_list_all_with_mixed_next_action(self):
        """list_all reads missing / None / valid nextAction items without raising."""
        items = [
            _raw_item(application_id="missing-na"),
            _raw_item(application_id="null-na", nextAction=None),
            _raw_item(
                application_id="valid-na",
                nextAction={"label": "Prepare for interview", "priority": "High"},
            ),
        ]
        repo, _ = _make_repo(query_items=items)
        apps = repo.list_all()
        assert len(apps) == 3
        by_id = {a.applicationId: a for a in apps}
        assert by_id["missing-na"].nextAction is None
        assert by_id["null-na"].nextAction is None
        assert by_id["valid-na"].nextAction.label == "Prepare for interview"


# ---------------------------------------------------------------------------
# update — SET / REMOVE UpdateExpression construction
# ---------------------------------------------------------------------------

class TestUpdateRemovesNullNextAction:
    def test_update_removes_next_action_when_none(self):
        """When nextAction is None, update issues REMOVE (not SET null)."""
        repo, mock_table = _make_repo()
        # Returned item has no nextAction (it was removed).
        mock_table.update_item.return_value = {"Attributes": _raw_item()}

        now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        fields = {
            "status": Status.APPLIED,
            "statusHistory": [{"status": "Applied", "timestamp": now.isoformat()}],
            "updatedAt": now,
            "nextAction": None,
        }
        repo.update("app-1", fields)

        kwargs = mock_table.update_item.call_args[1]
        expr = kwargs["UpdateExpression"]
        assert "REMOVE" in expr
        assert "SET" in expr

        # The placeholder mapped to nextAction must appear in the REMOVE clause
        # and NOT be assigned a value.
        names = kwargs["ExpressionAttributeNames"]
        na_placeholder = next(p for p, n in names.items() if n == "nextAction")
        remove_segment = expr.split("REMOVE", 1)[1]
        set_segment = expr.split("REMOVE", 1)[0]
        assert na_placeholder in remove_segment
        assert f"{na_placeholder} =" not in set_segment

        # No ExpressionAttributeValues entry should carry a null for nextAction.
        values = kwargs.get("ExpressionAttributeValues", {})
        assert None not in values.values()

        # status / statusHistory / updatedAt remain in the SET clause.
        assert "SET" in set_segment
        set_names = [names[p] for p in names if p in set_segment]
        assert "status" in set_names
        assert "statusHistory" in set_names
        assert "updatedAt" in set_names

    def test_update_sets_next_action_when_present(self):
        """When nextAction is a dict, update issues a plain SET (no REMOVE)."""
        repo, mock_table = _make_repo()
        mock_table.update_item.return_value = {"Attributes": _raw_item()}

        now = datetime(2025, 2, 1, 12, 0, 0, tzinfo=timezone.utc)
        fields = {
            "status": Status.INTERVIEW,
            "updatedAt": now,
            "nextAction": {"label": "Prepare for interview", "priority": "High"},
        }
        repo.update("app-1", fields)

        expr = mock_table.update_item.call_args[1]["UpdateExpression"]
        assert expr.startswith("SET")
        assert "REMOVE" not in expr
