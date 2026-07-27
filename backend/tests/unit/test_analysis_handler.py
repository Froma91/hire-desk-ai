"""
Tests for the analysis handler and recommendation explanation enrichment.

Part 1: Analysis handler (POST /analyze) — error mapping and response format.
Part 2: Recommendation explanation (Property 12) — graceful degradation.

All Bedrock, DynamoDB, and network interactions are mocked.
No real AWS calls are made.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import io
import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from applications_function.models import (
    Application,
    Status,
    StatusEntry,
    NextAction,
    Priority,
    ExtractionResult,
)
from applications_function.repositories.applications_repo import (
    NotFoundError,
    RepositoryError,
)


# ===========================================================================
# PART 1: Analysis handler tests
# ===========================================================================

from job_analysis_function.handlers.analysis import analyze_job
from job_analysis_function.services.bedrock_service import BedrockTimeoutError, BedrockError
from job_analysis_function.validators.extraction_validator import ExtractionValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_analyze_event(body=None, raw_body=None):
    event = {"requestContext": {"requestId": "test-req"}}
    if raw_body is not None:
        event["body"] = raw_body
    elif body is not None:
        event["body"] = json.dumps(body)
    return event


_SAMPLE_RESULT = ExtractionResult(
    jobTitle="Software Engineer",
    company="Acme Corp",
    location="Paris",
    skills=["Python", "AWS"],
    responsibilities=["Design systems"],
    languages=["English"],
    experienceLevel="Senior",
)

_NULL_RESULT = ExtractionResult(
    jobTitle=None,
    company=None,
    location=None,
    skills=[],
    responsibilities=[],
    languages=[],
    experienceLevel=None,
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_success_returns_200(mock_analyze):
    """Mock returns _SAMPLE_RESULT, assert statusCode=200, body is valid JSON."""
    mock_analyze.return_value = _SAMPLE_RESULT
    event = _make_analyze_event(body={"jobDescription": "A job posting for an engineer."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert isinstance(body, dict)


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_response_contains_all_seven_fields(mock_analyze):
    """Parse response body, assert all 7 keys present."""
    mock_analyze.return_value = _SAMPLE_RESULT
    event = _make_analyze_event(body={"jobDescription": "A job posting for an engineer."})

    response = analyze_job(event, None)
    body = json.loads(response["body"])

    expected_keys = {"jobTitle", "company", "location", "skills", "responsibilities", "languages", "experienceLevel"}
    assert set(body.keys()) == expected_keys


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_null_fields_serialized_correctly(mock_analyze):
    """Mock returns _NULL_RESULT, assert body has null values for Optional fields and empty arrays for list fields."""
    mock_analyze.return_value = _NULL_RESULT
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)
    body = json.loads(response["body"])

    assert body["jobTitle"] is None
    assert body["company"] is None
    assert body["location"] is None
    assert body["experienceLevel"] is None
    assert body["skills"] == []
    assert body["responsibilities"] == []
    assert body["languages"] == []


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_bedrock_timeout_maps_to_408(mock_analyze):
    """Mock raises BedrockTimeoutError, assert statusCode=408, code='ANALYSIS_TIMEOUT'."""
    mock_analyze.side_effect = BedrockTimeoutError("timeout")
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 408
    body = json.loads(response["body"])
    assert body["error"]["code"] == "ANALYSIS_TIMEOUT"


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_extraction_validation_error_maps_to_422(mock_analyze):
    """Mock raises ExtractionValidationError({'company'}), assert statusCode=422, code='ANALYSIS_FAILED'."""
    mock_analyze.side_effect = ExtractionValidationError({"company"})
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 422
    body = json.loads(response["body"])
    assert body["error"]["code"] == "ANALYSIS_FAILED"


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_bedrock_error_maps_to_502(mock_analyze):
    """Mock raises BedrockError('fail'), assert statusCode=502, code='ANALYSIS_FAILED'."""
    mock_analyze.side_effect = BedrockError("fail")
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 502
    body = json.loads(response["body"])
    assert body["error"]["code"] == "ANALYSIS_FAILED"


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_unexpected_error_returns_500(mock_analyze):
    """Mock raises RuntimeError('boom'), assert statusCode=500, code='INTERNAL_ERROR'."""
    mock_analyze.side_effect = RuntimeError("boom")
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["error"]["code"] == "INTERNAL_ERROR"


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_bedrock_not_called_on_invalid_payload(mock_analyze):
    """Call with {} (missing jobDescription), assert mock NOT called."""
    event = _make_analyze_event(body={})

    response = analyze_job(event, None)

    assert response["statusCode"] == 400
    mock_analyze.assert_not_called()


@patch("job_analysis_function.handlers.analysis.analyze_job_description")
def test_no_internal_details_in_error_responses(mock_analyze):
    """For each error case, assert response body does not contain internal details."""
    error_cases = [
        BedrockTimeoutError("arn:aws:bedrock:us-east-1:123456:model/anthropic.claude"),
        BedrockError("boto3 session failed with Traceback"),
        ExtractionValidationError({"company"}),
        RuntimeError("boom from arn:aws:lambda"),
    ]
    forbidden_patterns = [
        "arn:aws",
        "boto",
        "Traceback",
        "RuntimeError",
        "anthropic.claude",
        "File \"",
    ]

    for error in error_cases:
        mock_analyze.side_effect = error
        event = _make_analyze_event(body={"jobDescription": "A job posting."})

        response = analyze_job(event, None)
        body_str = response["body"]

        for pattern in forbidden_patterns:
            assert pattern not in body_str, (
                f"Found '{pattern}' in error response for {type(error).__name__}"
            )


# ===========================================================================
# PART 2: Recommendation explanation tests (Property 12)
# ===========================================================================

from applications_function.services.explanation_service import generate_explanation
from applications_function.services.recommendation_service import get_recommendation


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

@patch("applications_function.services.explanation_service._get_client")
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


@patch("applications_function.services.explanation_service._get_client")
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


@patch("applications_function.services.explanation_service._get_client")
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


@patch("applications_function.services.explanation_service._get_client")
def test_timeout_returns_none(mock_get_client):
    """Mock raises ReadTimeoutError(endpoint_url='x'), assert returns None."""
    from botocore.exceptions import ReadTimeoutError

    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.invoke_model.side_effect = ReadTimeoutError(endpoint_url="https://bedrock.example.com")

    result = generate_explanation("Apply now", "Wishlist")
    assert result is None


@patch("applications_function.services.explanation_service._get_client")
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


@patch("applications_function.services.explanation_service._get_client")
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

@patch("applications_function.services.recommendation_service.generate_explanation")
@patch("applications_function.services.recommendation_service.compute_next_action")
@patch("applications_function.services.recommendation_service._repo")
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


@patch("applications_function.services.recommendation_service.generate_explanation")
@patch("applications_function.services.recommendation_service.compute_next_action")
@patch("applications_function.services.recommendation_service._repo")
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


@patch("applications_function.services.recommendation_service.generate_explanation")
@patch("applications_function.services.recommendation_service.compute_next_action")
@patch("applications_function.services.recommendation_service._repo")
def test_no_bedrock_call_when_next_action_is_none(mock_repo, mock_compute, mock_explain):
    """Mock compute_next_action returns None, assert generate_explanation NOT called."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.return_value = _sample_app()
    mock_compute.return_value = None

    app, action = get_recommendation("test-app-id")

    assert action is None
    mock_explain.assert_not_called()


@patch("applications_function.services.recommendation_service.generate_explanation")
@patch("applications_function.services.recommendation_service.compute_next_action")
@patch("applications_function.services.recommendation_service._repo")
def test_not_found_error_propagates(mock_repo, mock_compute, mock_explain):
    """Mock repo raises NotFoundError, assert it propagates (not caught by graceful fallback)."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.side_effect = NotFoundError("Application not found")

    with pytest.raises(NotFoundError):
        get_recommendation("nonexistent-id")


@patch("applications_function.services.recommendation_service.generate_explanation")
@patch("applications_function.services.recommendation_service.compute_next_action")
@patch("applications_function.services.recommendation_service._repo")
def test_repository_error_propagates(mock_repo, mock_compute, mock_explain):
    """Mock repo raises RepositoryError, assert it propagates."""
    mock_repo_instance = MagicMock()
    mock_repo.return_value = mock_repo_instance
    mock_repo_instance.get.side_effect = RepositoryError("DynamoDB unavailable")

    with pytest.raises(RepositoryError):
        get_recommendation("test-app-id")
