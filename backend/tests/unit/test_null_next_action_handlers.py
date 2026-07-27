"""
Handler-level regression tests for the nextAction = NULL production defect.

Wires a real ApplicationsRepo (backed by a mocked DynamoDB table) into the
service singleton so that _from_item runs for real against raw items that
include NULL / missing / valid nextAction values. Confirms that both
GET /applications and GET /stats return HTTP 200 instead of 500.

No real AWS calls are made.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Lambda-root isolation bootstrap (ApplicationsFunction / flat layout).
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
import services.applications_service as svc_module
from handlers.applications import list_applications
from handlers.stats import get_stats


_NOW_ISO = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc).isoformat()


def _raw_item(application_id="app-1", **overrides) -> dict:
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


@pytest.fixture
def repo_with_null_items():
    """Install a real repo (mocked table) with mixed nextAction items."""
    items = [
        _raw_item(application_id="missing-na"),
        _raw_item(application_id="null-na", nextAction=None),
        _raw_item(
            application_id="valid-na",
            nextAction={"label": "Prepare for interview", "priority": "High"},
        ),
    ]
    mock_table = MagicMock()
    mock_table.query.return_value = {"Items": items}
    mock_resource = MagicMock()
    mock_resource.Table.return_value = mock_table
    with patch.dict(os.environ, {"TABLE_NAME": "test-table"}):
        with patch.object(repo_mod.boto3, "resource", return_value=mock_resource):
            repo = ApplicationsRepo()
    svc_module._repo_instance = repo
    yield repo
    svc_module._repo_instance = None


def _make_event():
    return {"requestContext": {"requestId": "test-req"}}


def test_get_applications_200_with_null_next_action(repo_with_null_items):
    """GET /applications returns 200 even when items include NULL nextAction."""
    response = list_applications(_make_event())
    assert response["statusCode"] == 200
    data = json.loads(response["body"])
    assert len(data) == 3
    by_id = {a["applicationId"]: a for a in data}
    assert by_id["missing-na"]["nextAction"] is None
    assert by_id["null-na"]["nextAction"] is None
    assert by_id["valid-na"]["nextAction"]["label"] == "Prepare for interview"


def test_get_stats_200_with_null_next_action(repo_with_null_items):
    """GET /stats returns 200 even when items include NULL nextAction."""
    response = get_stats(_make_event())
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["total"] == 3
    assert sum(body["byStatus"].values()) == 3
