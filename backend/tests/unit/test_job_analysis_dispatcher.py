"""
Focused dispatcher tests for JobAnalysisFunction app.py.

Verifies routing, parameter validation, 404/405 behaviour.
All service calls are mocked — no real DynamoDB or Bedrock.
"""

import sys
import os

# ---------------------------------------------------------------------------
# Lambda-root isolation bootstrap (JobAnalysisFunction / flat layout).
# ---------------------------------------------------------------------------
_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_LAMBDA_ROOT = os.path.join(_BACKEND, "job_analysis_function")
_FLAT = {"app", "models", "handlers", "services", "validators", "repositories", "business_rules"}
for _n in list(sys.modules):
    if _n.split(".")[0] in _FLAT:
        del sys.modules[_n]
if _LAMBDA_ROOT in sys.path:
    sys.path.remove(_LAMBDA_ROOT)
sys.path.insert(0, _LAMBDA_ROOT)

import json
import pytest
from unittest.mock import patch, MagicMock

import app as app_mod
from app import handler


def _make_event(route_key=None, path_params=None, raw_path=None, body=None):
    event = {"requestContext": {"requestId": "t"}}
    if route_key:
        event["routeKey"] = route_key
    if path_params is not None:
        event["pathParameters"] = path_params
    if raw_path:
        event["rawPath"] = raw_path
    if body is not None:
        event["body"] = json.dumps(body) if isinstance(body, dict) else body
    return event


class TestRecommendationRouteValidation:
    """Tests for GET /applications/{id}/recommendation parameter validation."""

    def test_missing_path_parameters_returns_400(self):
        """When pathParameters is empty dict and routeKey has template, returns 400."""
        event = _make_event(
            route_key="GET /applications/{id}/recommendation",
            path_params={},
        )
        resp = handler(event, None)
        assert resp["statusCode"] == 400
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert "application id" in body["error"]["message"].lower()

    def test_none_path_parameters_returns_400(self):
        """When pathParameters is None, returns 400."""
        event = _make_event(
            route_key="GET /applications/{id}/recommendation",
            path_params=None,
        )
        # Remove pathParameters key entirely
        event.pop("pathParameters", None)
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    def test_empty_id_returns_400(self):
        """When pathParameters has id as empty string, returns 400."""
        event = _make_event(
            route_key="GET /applications/{id}/recommendation",
            path_params={"id": ""},
        )
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    def test_whitespace_id_returns_400(self):
        """When pathParameters has id as whitespace, returns 400."""
        event = _make_event(
            route_key="GET /applications/{id}/recommendation",
            path_params={"id": "   "},
        )
        resp = handler(event, None)
        assert resp["statusCode"] == 400

    @patch.object(app_mod, "get_recommendation_handler")
    def test_recommendation_service_not_called_for_invalid_id(self, mock_handler):
        """recommendation_service is NOT called when ID is invalid."""
        event = _make_event(
            route_key="GET /applications/{id}/recommendation",
            path_params={},
        )
        handler(event, None)
        mock_handler.assert_not_called()

    @patch.object(app_mod, "get_recommendation_handler")
    def test_valid_id_passed_to_recommendation_handler(self, mock_handler):
        """A valid id is passed through to get_recommendation_handler."""
        mock_handler.return_value = {"statusCode": 200, "headers": {}, "body": "{}"}
        event = _make_event(
            route_key="GET /applications/{id}/recommendation",
            path_params={"id": "valid-uuid-123"},
        )
        handler(event, None)
        mock_handler.assert_called_once()
        # Verify the event passed to handler has the correct id
        call_event = mock_handler.call_args[0][0]
        assert call_event["pathParameters"]["id"] == "valid-uuid-123"

    @patch.object(app_mod, "get_recommendation_handler")
    def test_valid_id_from_raw_path(self, mock_handler):
        """When routeKey is template but rawPath has actual UUID, extracts correctly."""
        mock_handler.return_value = {"statusCode": 200, "headers": {}, "body": "{}"}
        event = _make_event(
            route_key="GET /applications/{id}/recommendation",
            path_params={},
            raw_path="/applications/abc-123-uuid/recommendation",
        )
        handler(event, None)
        mock_handler.assert_called_once()
        call_event = mock_handler.call_args[0][0]
        assert call_event["pathParameters"]["id"] == "abc-123-uuid"


class TestAnalyzeRoute:
    """Tests for POST /analyze routing."""

    @patch.object(app_mod, "analyze_job")
    def test_post_analyze_routes_to_handler(self, mock_analyze):
        """POST /analyze routes to analyze_job handler."""
        mock_analyze.return_value = {"statusCode": 400, "headers": {}, "body": "{}"}
        event = _make_event(route_key="POST /analyze", body={"jobDescription": "test"})
        handler(event, None)
        mock_analyze.assert_called_once()


class TestErrorResponses:
    """Tests for 404 and 405 responses."""

    def test_unknown_route_returns_404(self):
        """Unknown route returns 404."""
        event = _make_event(route_key="GET /unknown")
        resp = handler(event, None)
        assert resp["statusCode"] == 404
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    def test_get_analyze_returns_405(self):
        """GET /analyze returns 405."""
        event = _make_event(route_key="GET /analyze")
        resp = handler(event, None)
        assert resp["statusCode"] == 405
        body = json.loads(resp["body"])
        assert body["error"]["code"] == "METHOD_NOT_ALLOWED"

    def test_post_recommendation_returns_405(self):
        """POST on /applications/{id}/recommendation returns 405."""
        event = _make_event(
            route_key="POST /applications/some-id/recommendation",
            path_params={"id": "some-id"},
        )
        resp = handler(event, None)
        assert resp["statusCode"] == 405

