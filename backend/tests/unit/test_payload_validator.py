"""
Tests for validate_application_payload.

Property 4: Lambda field validation accepts iff all constraints satisfied.
Validates: Requirements 2.6, 2.7, 8.2, 8.3

Pure pytest example-based tests — no Hypothesis, no mocking (function has no I/O).
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

import pytest
from validators.payload_validator import (
    validate_application_payload,
)

# ---------------------------------------------------------------------------
# Constants mirrored from implementation (used to build boundary payloads)
# ---------------------------------------------------------------------------
_MAX_STRING_LEN = 500
_MAX_ITEM_LEN = 200
_MAX_LIST_SIZE = 30


# ===========================================================================
# 1. Valid payloads (accept)
# ===========================================================================

def test_valid_minimal_payload():
    # Only jobTitle present — all optional fields absent — must accept.
    ok, err = validate_application_payload({"jobTitle": "Software Engineer"})
    assert ok is True
    assert err is None


def test_valid_full_payload():
    # All fields populated within limits — must accept.
    ok, err = validate_application_payload({
        "jobTitle": "Senior Developer",
        "company": "Acme Corp",
        "location": "Paris",
        "experienceLevel": "Senior",
        "skills": ["Python", "AWS"],
        "responsibilities": ["Design systems", "Code review"],
        "languages": ["English", "French"],
    })
    assert ok is True
    assert err is None


def test_valid_optional_fields_none():
    # jobTitle set; all optional strings explicitly None; lists empty — must accept.
    ok, err = validate_application_payload({
        "jobTitle": "Analyst",
        "company": None,
        "location": None,
        "experienceLevel": None,
        "skills": [],
        "responsibilities": [],
        "languages": [],
    })
    assert ok is True
    assert err is None


def test_valid_list_at_exact_limit():
    # One list field with exactly 30 items, each exactly 200 chars — must accept.
    item = "x" * _MAX_ITEM_LEN
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "skills": [item] * _MAX_LIST_SIZE,
    })
    assert ok is True
    assert err is None


def test_valid_string_at_exact_limit():
    # jobTitle of exactly 500 chars — must accept.
    ok, err = validate_application_payload({"jobTitle": "a" * _MAX_STRING_LEN})
    assert ok is True
    assert err is None


# ===========================================================================
# 2. jobTitle rejection
# ===========================================================================

def test_reject_missing_job_title():
    # Payload without jobTitle key — must reject with field == "jobTitle".
    ok, err = validate_application_payload({})
    assert ok is False
    assert err["field"] == "jobTitle"


def test_reject_null_job_title():
    # jobTitle is None — must reject.
    ok, err = validate_application_payload({"jobTitle": None})
    assert ok is False
    assert err["field"] == "jobTitle"


def test_reject_empty_job_title():
    # jobTitle is an empty string — must reject.
    ok, err = validate_application_payload({"jobTitle": ""})
    assert ok is False
    assert err["field"] == "jobTitle"


def test_reject_whitespace_only_job_title():
    # jobTitle contains only whitespace — must reject.
    ok, err = validate_application_payload({"jobTitle": "   "})
    assert ok is False
    assert err["field"] == "jobTitle"


def test_reject_job_title_too_long():
    # jobTitle of 501 chars exceeds the 500-char limit — must reject.
    ok, err = validate_application_payload({"jobTitle": "a" * (_MAX_STRING_LEN + 1)})
    assert ok is False
    assert err["field"] == "jobTitle"


# ===========================================================================
# 3. Optional string field rejection (one test per field)
# ===========================================================================

def test_reject_company_too_long():
    # company of 501 chars — must reject with field == "company".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "company": "c" * (_MAX_STRING_LEN + 1),
    })
    assert ok is False
    assert err["field"] == "company"


def test_reject_location_too_long():
    # location of 501 chars — must reject with field == "location".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "location": "l" * (_MAX_STRING_LEN + 1),
    })
    assert ok is False
    assert err["field"] == "location"


def test_reject_experience_level_too_long():
    # experienceLevel of 501 chars — must reject with field == "experienceLevel".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "experienceLevel": "e" * (_MAX_STRING_LEN + 1),
    })
    assert ok is False
    assert err["field"] == "experienceLevel"


# ===========================================================================
# 4. List field rejection
# ===========================================================================

def test_reject_skills_too_many_items():
    # skills with 31 items — must reject with field == "skills".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "skills": ["Python"] * (_MAX_LIST_SIZE + 1),
    })
    assert ok is False
    assert err["field"] == "skills"


def test_reject_responsibilities_too_many_items():
    # responsibilities with 31 items — must reject with field == "responsibilities".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "responsibilities": ["Task"] * (_MAX_LIST_SIZE + 1),
    })
    assert ok is False
    assert err["field"] == "responsibilities"


def test_reject_languages_too_many_items():
    # languages with 31 items — must reject with field == "languages".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "languages": ["English"] * (_MAX_LIST_SIZE + 1),
    })
    assert ok is False
    assert err["field"] == "languages"


def test_reject_skill_item_too_long():
    # One item of 201 chars in skills — must reject with field == "skills".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "skills": ["s" * (_MAX_ITEM_LEN + 1)],
    })
    assert ok is False
    assert err["field"] == "skills"


def test_reject_responsibility_item_too_long():
    # One item of 201 chars in responsibilities — must reject with field == "responsibilities".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "responsibilities": ["r" * (_MAX_ITEM_LEN + 1)],
    })
    assert ok is False
    assert err["field"] == "responsibilities"


def test_reject_language_item_too_long():
    # One item of 201 chars in languages — must reject with field == "languages".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "languages": ["l" * (_MAX_ITEM_LEN + 1)],
    })
    assert ok is False
    assert err["field"] == "languages"


def test_reject_list_not_a_list():
    # skills is a string instead of a list — must reject with field == "skills".
    ok, err = validate_application_payload({
        "jobTitle": "Dev",
        "skills": "Python",
    })
    assert ok is False
    assert err["field"] == "skills"


# ===========================================================================
# 5. Forbidden key rejection — individual tests
# ===========================================================================

def _base_payload_with(key: str, value="injected") -> dict:
    """Helper: valid base payload plus one forbidden key."""
    return {"jobTitle": "Dev", key: value}


def test_reject_forbidden_key_table_name():
    # TableName is a DynamoDB-level key — must be rejected with reason "Forbidden field".
    ok, err = validate_application_payload(_base_payload_with("TableName"))
    assert ok is False
    assert err["field"] == "TableName"
    assert err["reason"] == "Forbidden field"


def test_reject_forbidden_key_index_name():
    # IndexName is a DynamoDB-level key — must be rejected.
    ok, err = validate_application_payload(_base_payload_with("IndexName"))
    assert ok is False
    assert err["field"] == "IndexName"
    assert err["reason"] == "Forbidden field"


def test_reject_forbidden_key_user_id():
    # userId is a server-generated identifier — must be rejected.
    ok, err = validate_application_payload(_base_payload_with("userId"))
    assert ok is False
    assert err["field"] == "userId"
    assert err["reason"] == "Forbidden field"


def test_reject_forbidden_key_application_id():
    # applicationId is a server-generated identifier — must be rejected.
    ok, err = validate_application_payload(_base_payload_with("applicationId"))
    assert ok is False
    assert err["field"] == "applicationId"
    assert err["reason"] == "Forbidden field"


def test_reject_forbidden_key_created_at():
    # createdAt is a server-managed timestamp — must be rejected.
    ok, err = validate_application_payload(_base_payload_with("createdAt"))
    assert ok is False
    assert err["field"] == "createdAt"
    assert err["reason"] == "Forbidden field"


def test_reject_forbidden_key_updated_at():
    # updatedAt is a server-managed timestamp — must be rejected.
    ok, err = validate_application_payload(_base_payload_with("updatedAt"))
    assert ok is False
    assert err["field"] == "updatedAt"
    assert err["reason"] == "Forbidden field"


def test_reject_forbidden_key_status_history():
    # statusHistory is server-managed state — must be rejected.
    ok, err = validate_application_payload(_base_payload_with("statusHistory"))
    assert ok is False
    assert err["field"] == "statusHistory"
    assert err["reason"] == "Forbidden field"


def test_reject_forbidden_key_next_action():
    # nextAction is server-computed — must be rejected.
    ok, err = validate_application_payload(_base_payload_with("nextAction"))
    assert ok is False
    assert err["field"] == "nextAction"
    assert err["reason"] == "Forbidden field"


@pytest.mark.parametrize("forbidden_key", [
    "KeyConditionExpression",
    "FilterExpression",
    "ProjectionExpression",
    "ExpressionAttributeNames",
    "ExpressionAttributeValues",
])
def test_reject_remaining_forbidden_keys(forbidden_key: str):
    # Remaining DynamoDB expression keys — each must be rejected with reason "Forbidden field".
    ok, err = validate_application_payload(_base_payload_with(forbidden_key))
    assert ok is False
    assert err["field"] == forbidden_key
    assert err["reason"] == "Forbidden field"


# ===========================================================================
# 6. Nested forbidden key
# ===========================================================================

def test_reject_nested_forbidden_key():
    # Forbidden key nested one level deep inside an arbitrary dict value — must reject.
    ok, err = validate_application_payload({"jobTitle": "Dev", "meta": {"userId": "x"}})
    assert ok is False
    assert err["field"] == "userId"


# ===========================================================================
# 7. Return type invariants
# ===========================================================================

def test_success_returns_true_none():
    # Happy-path return must be exactly (True, None), not merely truthy.
    result = validate_application_payload({"jobTitle": "Engineer"})
    assert result == (True, None)


def test_failure_returns_false_dict_with_field_and_reason():
    # Rejected payload must return (False, dict) where the dict has exactly "field" and "reason".
    ok, err = validate_application_payload({"jobTitle": ""})
    assert ok is False
    assert isinstance(err, dict)
    assert set(err.keys()) == {"field", "reason"}
    assert isinstance(err["field"], str)
    assert isinstance(err["reason"], str)
