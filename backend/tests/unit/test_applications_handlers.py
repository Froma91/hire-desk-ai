"""
Unit tests for CRUD handlers — mock ApplicationsRepo to isolate DynamoDB.

Properties tested:
  Property 5: applicationId is server-generated UUID (Requirements 3.1, 3.3)
  Property 6: partial update preserves unmodified fields (Requirements 3.5)
  Property 7: list ordered by createdAt descending (Requirements 3.2)

Requirements: 3.1–3.10
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
import uuid
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta

import services.applications_service as svc_module
from repositories.applications_repo import (
    ApplicationsRepo,
    NotFoundError,
    RepositoryError,
)
from models import Application, Status, StatusEntry
from handlers.applications import (
    create_application,
    list_applications,
    get_application,
    update_application,
    delete_application,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sample_app(
    application_id="test-uuid-1234",
    job_title="Software Engineer",
    status=Status.WISHLIST,
    company="Acme Corp",
    created_at=None,
) -> Application:
    now = created_at or datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    return Application(
        userId="demo-user",
        applicationId=application_id,
        jobTitle=job_title,
        status=status,
        createdAt=now,
        updatedAt=now,
        company=company,
        location="Paris",
        experienceLevel="Senior",
        skills=["Python", "AWS"],
        responsibilities=["Design systems"],
        languages=["English", "French"],
        statusHistory=[StatusEntry(status=status, timestamp=now)],
        nextAction=None,
    )


def _make_event(body=None, path_params=None):
    event = {"requestContext": {"requestId": "test-req-001"}}
    if body is not None:
        event["body"] = json.dumps(body) if isinstance(body, dict) else body
    if path_params is not None:
        event["pathParameters"] = path_params
    return event


# ---------------------------------------------------------------------------
# Fixture — mock repo singleton
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def mock_repo():
    """Replace the lazy repo singleton with a MagicMock for every test."""
    mock = MagicMock(spec=ApplicationsRepo)
    svc_module._repo_instance = mock
    yield mock
    svc_module._repo_instance = None


# ---------------------------------------------------------------------------
# 1. Create — happy path (201 + UUID)
# ---------------------------------------------------------------------------


class TestCreateApplication:
    def test_create_happy_path_returns_201_with_uuid(self, mock_repo):
        """
        Property 5: applicationId is server-generated UUID absent from request body.
        **Validates: Requirements 3.1, 3.3**
        """
        body = {"jobTitle": "Engineer", "company": "Acme"}
        event = _make_event(body=body)

        response = create_application(event)

        assert response["statusCode"] == 201
        data = json.loads(response["body"])

        # applicationId is a valid UUID v4
        parsed_uuid = uuid.UUID(data["applicationId"], version=4)
        assert str(parsed_uuid) == data["applicationId"]

        # applicationId was NOT in the request body (Property 5: server-generated)
        assert "applicationId" not in body

        # Default values
        assert data["userId"] == "demo-user"
        assert data["status"] == "Wishlist"
        assert len(data["statusHistory"]) == 1

        # Repo was called
        assert mock_repo.put.call_count == 1

    def test_create_validation_error_missing_job_title(self, mock_repo):
        """Missing jobTitle → 400 VALIDATION_ERROR."""
        event = _make_event(body={})

        response = create_application(event)

        assert response["statusCode"] == 400
        error = json.loads(response["body"])["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert error["field"] == "jobTitle"

        # Repo never called
        assert mock_repo.put.call_count == 0


# ---------------------------------------------------------------------------
# 2. List — happy path (200, ordered)
# ---------------------------------------------------------------------------


class TestListApplications:
    def test_list_happy_path_returns_200_ordered(self, mock_repo):
        """
        Property 7: list ordered by createdAt descending.
        **Validates: Requirements 3.2**
        """
        now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        older = now - timedelta(days=2)

        app_newer = _sample_app(application_id="newer-id", created_at=now)
        app_older = _sample_app(application_id="older-id", created_at=older)

        mock_repo.list_all.return_value = [app_newer, app_older]

        event = _make_event()
        response = list_applications(event)

        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert len(data) == 2
        # First item has newer createdAt
        assert data[0]["createdAt"] > data[1]["createdAt"]

    def test_list_repository_error_returns_503(self, mock_repo):
        """RepositoryError maps to 503 SERVICE_UNAVAILABLE."""
        mock_repo.list_all.side_effect = RepositoryError("DynamoDB timeout")

        event = _make_event()
        response = list_applications(event)

        assert response["statusCode"] == 503
        error = json.loads(response["body"])["error"]
        assert error["code"] == "SERVICE_UNAVAILABLE"


# ---------------------------------------------------------------------------
# 3. Get — happy path (200) + not found (404)
# ---------------------------------------------------------------------------


class TestGetApplication:
    def test_get_happy_path_returns_200(self, mock_repo):
        """Get existing application returns 200."""
        app = _sample_app(application_id="test-uuid")
        mock_repo.get.return_value = app

        event = _make_event(path_params={"id": "test-uuid"})
        response = get_application(event)

        assert response["statusCode"] == 200
        data = json.loads(response["body"])
        assert data["applicationId"] == "test-uuid"

    def test_get_not_found_returns_404(self, mock_repo):
        """NotFoundError from repo → 404."""
        mock_repo.get.side_effect = NotFoundError("not found")

        event = _make_event(path_params={"id": "nonexistent-id"})
        response = get_application(event)

        assert response["statusCode"] == 404
        error = json.loads(response["body"])["error"]
        assert error["code"] == "NOT_FOUND"

    def test_get_missing_path_parameter_returns_400(self, mock_repo):
        """Missing pathParameters → 400."""
        event = _make_event()  # no path_params
        response = get_application(event)

        assert response["statusCode"] == 400
        error = json.loads(response["body"])["error"]
        assert "application id" in error["message"].lower()


# ---------------------------------------------------------------------------
# 4. Update — partial fields (200, Property 6) + errors
# ---------------------------------------------------------------------------


class TestUpdateApplication:
    def test_update_partial_fields_preserves_unmodified(self, mock_repo):
        """
        Property 6: partial update preserves unmodified fields.
        **Validates: Requirements 3.5**
        """
        updated_app = _sample_app(company="NewCo")
        mock_repo.update.return_value = updated_app

        event = _make_event(
            body={"company": "NewCo"},
            path_params={"id": "test-uuid-1234"},
        )
        response = update_application(event)

        assert response["statusCode"] == 200
        assert mock_repo.update.call_count == 1

        # Inspect the fields dict passed to repo.update
        call_args = mock_repo.update.call_args
        fields = call_args[1]["fields"] if "fields" in (call_args[1] or {}) else call_args[0][1]

        # Must contain company and updatedAt
        assert "company" in fields
        assert "updatedAt" in fields

        # Must NOT contain unmodified fields (Property 6)
        assert "jobTitle" not in fields
        assert "skills" not in fields
        assert "responsibilities" not in fields

    def test_update_not_found_returns_404(self, mock_repo):
        """NotFoundError from repo → 404."""
        mock_repo.update.side_effect = NotFoundError("not found")

        event = _make_event(
            body={"company": "NewCo"},
            path_params={"id": "nonexistent-id"},
        )
        response = update_application(event)

        assert response["statusCode"] == 404

    def test_update_validation_error_field_too_long(self, mock_repo):
        """Field exceeding max length → 400."""
        event = _make_event(
            body={"company": "x" * 501},
            path_params={"id": "test-uuid-1234"},
        )
        response = update_application(event)

        assert response["statusCode"] == 400
        error = json.loads(response["body"])["error"]
        assert error["field"] == "company"

    def test_update_empty_body_returns_400(self, mock_repo):
        """Empty update body → 400."""
        event = _make_event(
            body={},
            path_params={"id": "test-uuid-1234"},
        )
        response = update_application(event)

        assert response["statusCode"] == 400
        error = json.loads(response["body"])["error"]
        assert "empty" in error["message"].lower()


# ---------------------------------------------------------------------------
# 5. Delete — happy path (204) + not found (404)
# ---------------------------------------------------------------------------


class TestDeleteApplication:
    def test_delete_happy_path_returns_204(self, mock_repo):
        """Successful delete returns 204."""
        event = _make_event(path_params={"id": "test-uuid-1234"})
        response = delete_application(event)

        assert response["statusCode"] == 204
        assert mock_repo.delete.call_count == 1

    def test_delete_not_found_returns_404(self, mock_repo):
        """NotFoundError from repo → 404."""
        mock_repo.delete.side_effect = NotFoundError("not found")

        event = _make_event(path_params={"id": "nonexistent-id"})
        response = delete_application(event)

        assert response["statusCode"] == 404


# ---------------------------------------------------------------------------
# 6. Property 5 — applicationId is UUID and absent from request
# ---------------------------------------------------------------------------


class TestPropertyServerGeneratedUUID:
    def test_application_id_is_uuid_v4_and_absent_from_request(self, mock_repo):
        """
        Property 5: applicationId is server-generated UUID absent from request body.
        **Validates: Requirements 3.1, 3.3**
        """
        body = {"jobTitle": "Data Scientist", "company": "BigData Inc"}
        event = _make_event(body=body)

        response = create_application(event)
        assert response["statusCode"] == 201

        data = json.loads(response["body"])
        app_id = data["applicationId"]

        # Valid UUID v4
        parsed = uuid.UUID(app_id, version=4)
        assert str(parsed) == app_id

        # Not present in original request values
        assert app_id not in body.values()
        assert "applicationId" not in body
