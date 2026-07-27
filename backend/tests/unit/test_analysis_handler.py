"""
Tests for the analysis handler (POST /analyze) — JobAnalysisFunction.

Covers error mapping and response format for the analysis handler.
All Bedrock and network interactions are mocked. No real AWS calls are made.

(The APP recommendation/explanation service tests that previously lived here
were moved to test_recommendation_service_app.py so each test module targets a
single Lambda root and the two flat layouts never collide in sys.modules.)
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

from models import ExtractionResult

import handlers.analysis as analysis_mod
from handlers.analysis import analyze_job
from services.bedrock_service import BedrockTimeoutError, BedrockError
from validators.extraction_validator import ExtractionValidationError


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

@patch.object(analysis_mod, "analyze_job_description")
def test_success_returns_200(mock_analyze):
    """Mock returns _SAMPLE_RESULT, assert statusCode=200, body is valid JSON."""
    mock_analyze.return_value = _SAMPLE_RESULT
    event = _make_analyze_event(body={"jobDescription": "A job posting for an engineer."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert isinstance(body, dict)


@patch.object(analysis_mod, "analyze_job_description")
def test_response_contains_all_seven_fields(mock_analyze):
    """Parse response body, assert all 7 keys present."""
    mock_analyze.return_value = _SAMPLE_RESULT
    event = _make_analyze_event(body={"jobDescription": "A job posting for an engineer."})

    response = analyze_job(event, None)
    body = json.loads(response["body"])

    expected_keys = {"jobTitle", "company", "location", "skills", "responsibilities", "languages", "experienceLevel"}
    assert set(body.keys()) == expected_keys


@patch.object(analysis_mod, "analyze_job_description")
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


@patch.object(analysis_mod, "analyze_job_description")
def test_bedrock_timeout_maps_to_408(mock_analyze):
    """Mock raises BedrockTimeoutError, assert statusCode=408, code='ANALYSIS_TIMEOUT'."""
    mock_analyze.side_effect = BedrockTimeoutError("timeout")
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 408
    body = json.loads(response["body"])
    assert body["error"]["code"] == "ANALYSIS_TIMEOUT"


@patch.object(analysis_mod, "analyze_job_description")
def test_extraction_validation_error_maps_to_422(mock_analyze):
    """Mock raises ExtractionValidationError({'company'}), assert statusCode=422, code='ANALYSIS_FAILED'."""
    mock_analyze.side_effect = ExtractionValidationError({"company"})
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 422
    body = json.loads(response["body"])
    assert body["error"]["code"] == "ANALYSIS_FAILED"


@patch.object(analysis_mod, "analyze_job_description")
def test_bedrock_error_maps_to_502(mock_analyze):
    """Mock raises BedrockError('fail'), assert statusCode=502, code='ANALYSIS_FAILED'."""
    mock_analyze.side_effect = BedrockError("fail")
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 502
    body = json.loads(response["body"])
    assert body["error"]["code"] == "ANALYSIS_FAILED"


@patch.object(analysis_mod, "analyze_job_description")
def test_unexpected_error_returns_500(mock_analyze):
    """Mock raises RuntimeError('boom'), assert statusCode=500, code='INTERNAL_ERROR'."""
    mock_analyze.side_effect = RuntimeError("boom")
    event = _make_analyze_event(body={"jobDescription": "A job posting."})

    response = analyze_job(event, None)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["error"]["code"] == "INTERNAL_ERROR"


@patch.object(analysis_mod, "analyze_job_description")
def test_bedrock_not_called_on_invalid_payload(mock_analyze):
    """Call with {} (missing jobDescription), assert mock NOT called."""
    event = _make_analyze_event(body={})

    response = analyze_job(event, None)

    assert response["statusCode"] == 400
    mock_analyze.assert_not_called()


@patch.object(analysis_mod, "analyze_job_description")
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
