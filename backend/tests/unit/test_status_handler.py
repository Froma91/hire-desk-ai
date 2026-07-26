"""
Unit tests for the status update handler — PATCH /applications/{id}/status.

Mocks the service layer, repository, and business-rules module to isolate
the handler from DynamoDB and external dependencies.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from applications_function.models import (
    Application,
    Status,
    StatusEntry,
    NextAction,
    Priority,
)
from applications_function.repositories.applications_repo import (
    ApplicationsRepo,
    NotFoundError,
    RepositoryError,
)
from applications_function.handlers.status import update_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_app(
    application_id="test-uuid-1234",
    status=Status.WISHLIST,
) -> Application:
    now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    return Application(
        userId="demo-user",
        applicationId=application_id,
        jobTitle="Engineer",
        status=status,
        createdAt=now,
        updatedAt=now,
        company="Acme",
        statusHistory=[StatusEntry(status=status, timestamp=now)],
        nextAction=None,
    )


def _make_event(application_id="test-uuid-1234", status_value="Applied"):
    return {
        "pathParameters": {"id": application_id},
        "body": json.dumps({"status": status_value}),
        "requestContext": {"requestId": "test-req"},
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("applications_function.handlers.status.compute_next_action")
@patch("applications_function.handlers.status._repo")
@patch("applications_function.handlers.status.svc_get_application")
class TestValidStatusUpdate:
    def test_valid_status_update_returns_200(
        self, mock_get_app, mock_repo, mock_compute
    ):
        """A valid status update returns 200 with updated status and nextAction."""
        app = _sample_app()
        mock_get_app.return_value = app

        updated_app = _sample_app(status=Status.APPLIED)
        updated_app.nextAction = NextAction(
            label="Follow up if no response within a week",
            priority=Priority.MEDIUM,
        )
        mock_repo_instance = MagicMock()
        mock_repo_instance.update.return_value = updated_app
        mock_repo.return_value = mock_repo_instance

        mock_compute.return_value = NextAction(
            label="Follow up if no response within a week",
            priority=Priority.MEDIUM,
        )

        response = update_status(_make_event(status_value="Applied"))

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["status"] == "Applied"
        assert body["nextAction"] is not None
        assert body["nextAction"]["label"] == "Follow up if no response within a week"


class TestInvalidStatus:
    def test_invalid_status_returns_400(self):
        """An invalid status value returns 400 VALIDATION_ERROR with field 'status'."""
        response = update_status(_make_event(status_value="InvalidStatus"))

        assert response["statusCode"] == 400
        error = json.loads(response["body"])["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert error["field"] == "status"

    @patch("applications_function.handlers.status.compute_next_action")
    @patch("applications_function.handlers.status._repo")
    @patch("applications_function.handlers.status.svc_get_application")
    def test_invalid_status_no_repo_call(
        self, mock_get_app, mock_repo, mock_compute
    ):
        """Invalid status triggers no repository or service calls."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance

        update_status(_make_event(status_value="InvalidStatus"))

        assert mock_get_app.call_count == 0
        assert mock_repo_instance.update.call_count == 0


@patch("applications_function.handlers.status.compute_next_action")
@patch("applications_function.handlers.status._repo")
@patch("applications_function.handlers.status.svc_get_application")
class TestNextActionRecomputed:
    def test_next_action_recomputed_after_status_change(
        self, mock_get_app, mock_repo, mock_compute
    ):
        """After status change, nextAction is recomputed and included in response."""
        app = _sample_app()
        mock_get_app.return_value = app

        mock_compute.return_value = NextAction(
            label="Follow up", priority=Priority.MEDIUM
        )

        updated_app = _sample_app(status=Status.APPLIED)
        updated_app.nextAction = NextAction(
            label="Follow up", priority=Priority.MEDIUM
        )
        mock_repo_instance = MagicMock()
        mock_repo_instance.update.return_value = updated_app
        mock_repo.return_value = mock_repo_instance

        response = update_status(_make_event(status_value="Applied"))

        assert response["statusCode"] == 200
        body = json.loads(response["body"])
        assert body["nextAction"]["label"] == "Follow up"
        assert body["nextAction"]["priority"] == "Medium"


@patch("applications_function.handlers.status.compute_next_action")
@patch("applications_function.handlers.status._repo")
@patch("applications_function.handlers.status.svc_get_application")
class TestErrorHandling:
    def test_not_found_error_returns_404(
        self, mock_get_app, mock_repo, mock_compute
    ):
        """NotFoundError from service maps to 404 NOT_FOUND."""
        mock_get_app.side_effect = NotFoundError("not found")

        response = update_status(_make_event(status_value="Applied"))

        assert response["statusCode"] == 404
        error = json.loads(response["body"])["error"]
        assert error["code"] == "NOT_FOUND"

    def test_repository_error_returns_503(
        self, mock_get_app, mock_repo, mock_compute
    ):
        """RepositoryError from repo.update maps to 503 SERVICE_UNAVAILABLE."""
        app = _sample_app()
        mock_get_app.return_value = app

        mock_compute.return_value = NextAction(
            label="Follow up", priority=Priority.MEDIUM
        )

        mock_repo_instance = MagicMock()
        mock_repo_instance.update.side_effect = RepositoryError("DynamoDB timeout")
        mock_repo.return_value = mock_repo_instance

        response = update_status(_make_event(status_value="Applied"))

        assert response["statusCode"] == 503
        error = json.loads(response["body"])["error"]
        assert error["code"] == "SERVICE_UNAVAILABLE"

    def test_unexpected_error_returns_500(
        self, mock_get_app, mock_repo, mock_compute
    ):
        """Unexpected RuntimeError maps to 500 INTERNAL_ERROR without leaking details."""
        app = _sample_app()
        mock_get_app.return_value = app

        mock_compute.return_value = NextAction(
            label="Follow up", priority=Priority.MEDIUM
        )

        mock_repo_instance = MagicMock()
        mock_repo_instance.update.side_effect = RuntimeError("boom")
        mock_repo.return_value = mock_repo_instance

        response = update_status(_make_event(status_value="Applied"))

        assert response["statusCode"] == 500
        error = json.loads(response["body"])["error"]
        assert error["code"] == "INTERNAL_ERROR"
        # Internal details must NOT be exposed
        assert "boom" not in response["body"]


class TestMissingFields:
    def test_missing_status_field_returns_400(self):
        """Missing status field in body returns 400."""
        event = {
            "pathParameters": {"id": "test-uuid-1234"},
            "body": json.dumps({}),
            "requestContext": {"requestId": "test-req"},
        }
        response = update_status(event)

        assert response["statusCode"] == 400
        error = json.loads(response["body"])["error"]
        assert error["code"] == "VALIDATION_ERROR"

    def test_missing_application_id_returns_400(self):
        """Missing application ID in path parameters returns 400."""
        event = {
            "pathParameters": {},
            "body": json.dumps({"status": "Applied"}),
            "requestContext": {"requestId": "test-req"},
        }
        response = update_status(event)

        assert response["statusCode"] == 400
        error = json.loads(response["body"])["error"]
        assert error["code"] == "VALIDATION_ERROR"
