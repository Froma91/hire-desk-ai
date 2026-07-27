"""
Tests for the APP recommendation service and explanation service (Property 12).

Part 2 of the former test_analysis_handler.py — split out so this module
targets the ApplicationsFunction flat layout exclusively.

Property 12: recommendation explanation enrichment degrades gracefully — the
deterministic label/priority is never altered by Bedrock, and a Bedrock failure
yields explanation=None while the recommendation still succeeds.

All Bedrock and DynamoDB interactions are mocked. No real AWS calls are made.
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

import io
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from models import (
    Application,
    Status,
    StatusEntry,
    NextAction,
    Priority,
)
from repositories.applications_repo import (
    NotFoundError,
    RepositoryError,
)

import services.explanation_service as explanation_mod
from services.explanation_service import generate_explanation

import services.recommendation_service as recommendation_mod
from services.recommendation_service import get_recommendation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sample_app(status=Status.INTERVIEW):
    now = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    return Application(
        userId="demo-user",
        applicationId="test-app-id",
        jobTitle="Engineer",
        status=status,
        createdAt=now - timedelta(days=10),
        updatedAt=now - timedelta(days=5),
        company="Acme",
        statusHistory=[StatusEntry(status=status, timestamp=now)],
    )


# ---------------------------------------------------------------------------
# Explanation validation tests (test generate_explanation directly)
# ---------------------------------------------------------------------------

@patch.object(explanation_mod, "_get_client")
def test_valid_explanation_attached(mock_get_client):
    """Mock Bedrock returns valid text <= 280 chars, call generate_explanation, assert returns the text."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    explanation_text = "Apply now because the role aligns perfectly with your skills."
    response_body = json.dumps({
        "content": [{"type": "text", "text": explanation_text}]
    }).encode("utf-8")
    mock_client.invoke_model.return_value = {
        "body": io.BytesIO(response_body),
        "ResponseMetadata": {"RequestId": "test-req-id"},
    }

    result = generate_explanation("Apply now", "Wishlist")
    assert result == explanation_text


@patch.object(explanation_mod, "_get_client")
def test_explanation_over_280_chars_returns_none(mock_get_client):
    """Mock returns 281-char text, assert returns None."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    long_text = "A" * 281
    response_body = json.dumps({
        "content": [{"type": "text", "text": long_text}]
    }).encode("utf-8")
    mock_client.invoke_model.return_value = {
        "body": io.BytesIO(response_body),
        "ResponseMetadata": {"RequestId": "test-req-id"},
    }

    result = generate_explanation("Apply now", "Wishlist")
    assert result is None


@patch.object(explanation_mod, "_get_client")
def test_empty_explanation_returns_none(mock_get_client):
    """Mock returns '   ' (whitespace), assert returns None."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    response_body = json.dumps({
        "content": [{"type": "text", "text": "   "}]
    }).encode("utf-8")
    mock_client.invoke_model.return_value = {
        "body": io.BytesIO(response_body),
        "ResponseMetadata": {"RequestId": "test-req-id"},
    }

    result = generate_explanation("Apply now", "Wishlist")
    assert result is None


@patch.object(explanation_mod, "_get_client")
def test_timeout_returns_none(mock_get_client):
    """Mock raises ReadTimeoutError(endpoint_url='x'), assert returns None."""
    from botocore.exceptions import ReadTimeoutError

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.invoke_model.side_effect = ReadTimeoutError(endpoint_url="https://bedrock.example.com")

    result = generate_explanation("Apply now", "Wishlist")
    assert result is None


@patch.object(explanation_mod, "_get_client")
def test_client_error_returns_none(mock_get_client):
    """Mock raises ClientError(...), assert returns None."""
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.invoke_model.side_effect = ClientError(
        error_response={"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"},
                        "ResponseMetadata": {"RequestId": "err-req-id"}},
        operation_name="InvokeModel",
    )

    result = generate_explanation("Apply now", "Wishlist")
    assert result is None


@patch.object(explanation_mod, "_get_client")
def test_unexpected_failure_returns_none(mock_get_client):
    """Mock raises RuntimeError('boom'), assert returns None."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.invoke_model.side_effect = RuntimeError("boom")

    result = generate_explanation("Apply now", "Wishlist")
    assert result is None


# ---------------------------------------------------------------------------
# Recommendation service integration tests
# ---------------------------------------------------------------------------

@patch.object(recommendation_mod, "generate_explanation")
@patch.object(recommendation_mod, "compute_next_action")
@patch.object(recommendation_mod, "_repo")
def test_deterministic_recommendation_returned_when_explanation_fails(mock_repo, mock_compute, mock_explain):
    """Mock generate_explanation returns None, assert returned NextAction has correct label/priority but explanation=None."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.return_value = _sample_app()
    mock_compute.return_value = NextAction(label="Follow up", priority=Priority.HIGH)
    mock_explain.return_value = None

    app, action = get_recommendation("test-app-id")

    assert action is not None
    assert action.label == "Follow up"
    assert action.priority == Priority.HIGH
    assert action.explanation is None


@patch.object(recommendation_mod, "generate_explanation")
@patch.object(recommendation_mod, "compute_next_action")
@patch.object(recommendation_mod, "_repo")
def test_label_priority_not_modified_by_bedrock(mock_repo, mock_compute, mock_explain):
    """Mock generate_explanation returns 'some text', assert label and priority match the engine's output exactly."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.return_value = _sample_app()
    mock_compute.return_value = NextAction(label="Prepare for interview", priority=Priority.MEDIUM)
    mock_explain.return_value = "Good reason to prepare."

    app, action = get_recommendation("test-app-id")

    assert action is not None
    assert action.label == "Prepare for interview"
    assert action.priority == Priority.MEDIUM
    assert action.explanation == "Good reason to prepare."


@patch.object(recommendation_mod, "generate_explanation")
@patch.object(recommendation_mod, "compute_next_action")
@patch.object(recommendation_mod, "_repo")
def test_no_bedrock_call_when_next_action_is_none(mock_repo, mock_compute, mock_explain):
    """Mock compute_next_action returns None, assert generate_explanation NOT called."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.return_value = _sample_app()
    mock_compute.return_value = None

    app, action = get_recommendation("test-app-id")

    assert action is None
    mock_explain.assert_not_called()


@patch.object(recommendation_mod, "generate_explanation")
@patch.object(recommendation_mod, "compute_next_action")
@patch.object(recommendation_mod, "_repo")
def test_not_found_error_propagates(mock_repo, mock_compute, mock_explain):
    """Mock repo raises NotFoundError, assert it propagates (not caught by graceful fallback)."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.side_effect = NotFoundError("Application not found")

    with pytest.raises(NotFoundError):
        get_recommendation("nonexistent-id")


@patch.object(recommendation_mod, "generate_explanation")
@patch.object(recommendation_mod, "compute_next_action")
@patch.object(recommendation_mod, "_repo")
def test_repository_error_propagates(mock_repo, mock_compute, mock_explain):
    """Mock repo raises RepositoryError, assert it propagates."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.side_effect = RepositoryError("DynamoDB unavailable")

    with pytest.raises(RepositoryError):
        get_recommendation("test-app-id")
