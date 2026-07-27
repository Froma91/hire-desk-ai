"""
Unit tests for extraction_validator — Property 2.

Property 2: Bedrock extraction validation accepts iff all required keys present.
Validates: Requirements 1.3, 1.6

Uses both Hypothesis (property-based) and explicit example-based tests.
"""

import sys
import os
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from job_analysis_function.validators.extraction_validator import (
    validate_extraction_result,
    ExtractionValidationError,
    REQUIRED_KEYS,
)
from applications_function.models import ExtractionResult


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Strategy for a valid extraction dictionary with all 7 required keys
_valid_extraction_dicts = st.fixed_dictionaries({
    "jobTitle": st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    "company": st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    "location": st.one_of(st.none(), st.text(min_size=1, max_size=100)),
    "skills": st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=50), max_size=10)),
    "responsibilities": st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=50), max_size=10)),
    "languages": st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=50), max_size=10)),
    "experienceLevel": st.one_of(st.none(), st.text(min_size=1, max_size=50)),
})

# Strategy for a dict with one or more required keys removed
@st.composite
def _dict_with_missing_keys(draw):
    """Generate a dict with at least one required key removed."""
    base = draw(_valid_extraction_dicts)
    # Choose 1 to 7 keys to remove
    keys_to_remove = draw(
        st.lists(
            st.sampled_from(sorted(REQUIRED_KEYS)),
            min_size=1,
            max_size=7,
            unique=True,
        )
    )
    for key in keys_to_remove:
        del base[key]
    return base, set(keys_to_remove)


# ===========================================================================
# HYPOTHESIS PROPERTY TESTS
# ===========================================================================


@given(raw=_valid_extraction_dicts)
@settings(max_examples=200)
def test_valid_dict_returns_extraction_result(raw: dict):
    """Property 2a: a dict with all 7 keys returns ExtractionResult."""
    result = validate_extraction_result(raw)
    assert isinstance(result, ExtractionResult)


@given(raw=_valid_extraction_dicts)
@settings(max_examples=200)
def test_identical_inputs_produce_identical_outputs(raw: dict):
    """Property 2b: identical inputs produce identical outputs."""
    result1 = validate_extraction_result(raw)
    result2 = validate_extraction_result(raw)
    assert result1 == result2


@given(raw=_valid_extraction_dicts)
@settings(max_examples=200)
def test_input_dict_not_mutated(raw: dict):
    """Property 2c: the input dictionary is not mutated."""
    original = copy.deepcopy(raw)
    validate_extraction_result(raw)
    assert raw == original


@given(data=_dict_with_missing_keys())
@settings(max_examples=200)
def test_missing_keys_raise_error(data):
    """Property 2d: missing required keys raise ExtractionValidationError."""
    raw, removed_keys = data
    with pytest.raises(ExtractionValidationError) as exc_info:
        validate_extraction_result(raw)
    # The exception must identify exactly the removed keys
    assert exc_info.value.missing_keys == removed_keys


@given(data=_dict_with_missing_keys())
@settings(max_examples=100)
def test_exception_message_contains_only_key_names(data):
    """Property 2e: exception message contains key names but not the full payload."""
    raw, removed_keys = data
    with pytest.raises(ExtractionValidationError) as exc_info:
        validate_extraction_result(raw)
    msg = str(exc_info.value)
    # All missing key names appear in the message
    for key in removed_keys:
        assert key in msg
    # The full payload values should NOT appear (check that no raw value is in the message)
    for key, value in raw.items():
        if isinstance(value, str) and len(value) > 10:
            assert value not in msg


@given(raw=_valid_extraction_dicts, extra_keys=st.dictionaries(
    st.text(min_size=1, max_size=20).filter(lambda k: k not in REQUIRED_KEYS),
    st.text(min_size=1, max_size=20),
    min_size=1,
    max_size=5,
))
@settings(max_examples=100)
def test_extra_keys_do_not_prevent_validation(raw: dict, extra_keys: dict):
    """Property 2f: extra unknown keys do not prevent validation."""
    combined = {**raw, **extra_keys}
    result = validate_extraction_result(combined)
    assert isinstance(result, ExtractionResult)


@given(raw=_valid_extraction_dicts)
@settings(max_examples=100)
def test_none_values_preserved_for_optional_str_fields(raw: dict):
    """Property 2g: None values are preserved for Optional[str] fields."""
    # Force all optional string fields to None
    raw_copy = {**raw, "jobTitle": None, "company": None, "location": None, "experienceLevel": None}
    result = validate_extraction_result(raw_copy)
    assert result.jobTitle is None
    assert result.company is None
    assert result.location is None
    assert result.experienceLevel is None


# ===========================================================================
# EXPLICIT EXAMPLE-BASED TESTS
# ===========================================================================


class TestValidDicts:
    """Tests for valid dictionaries that should return ExtractionResult."""

    def test_all_keys_present_with_values(self):
        """All 7 keys present with non-None values → ExtractionResult."""
        raw = {
            "jobTitle": "Software Engineer",
            "company": "Acme Corp",
            "location": "Paris",
            "skills": ["Python", "AWS"],
            "responsibilities": ["Design systems"],
            "languages": ["English", "French"],
            "experienceLevel": "Senior",
        }
        result = validate_extraction_result(raw)
        assert isinstance(result, ExtractionResult)
        assert result.jobTitle == "Software Engineer"
        assert result.company == "Acme Corp"
        assert result.skills == ["Python", "AWS"]

    def test_all_keys_present_with_none_values(self):
        """All 7 keys present with None values → valid ExtractionResult."""
        raw = {
            "jobTitle": None,
            "company": None,
            "location": None,
            "skills": None,
            "responsibilities": None,
            "languages": None,
            "experienceLevel": None,
        }
        result = validate_extraction_result(raw)
        assert isinstance(result, ExtractionResult)
        assert result.jobTitle is None
        assert result.company is None
        assert result.location is None
        assert result.experienceLevel is None
        # list fields: None → []
        assert result.skills == []
        assert result.responsibilities == []
        assert result.languages == []

    def test_extra_keys_accepted(self):
        """Extra unknown keys do not prevent validation."""
        raw = {
            "jobTitle": "Dev",
            "company": "Co",
            "location": "NY",
            "skills": [],
            "responsibilities": [],
            "languages": [],
            "experienceLevel": "Mid",
            "extraField": "ignored",
            "anotherExtra": 42,
        }
        result = validate_extraction_result(raw)
        assert isinstance(result, ExtractionResult)
        assert result.jobTitle == "Dev"

    def test_required_keys_match_specification(self):
        """The 7 required keys exactly match the specification."""
        expected = {"jobTitle", "company", "location", "skills",
                    "responsibilities", "languages", "experienceLevel"}
        assert REQUIRED_KEYS == expected


class TestMissingKeys:
    """Tests for dictionaries with missing required keys."""

    @pytest.mark.parametrize("missing_key", sorted(REQUIRED_KEYS))
    def test_each_individual_key_missing(self, missing_key: str):
        """Each individual required key tested as missing."""
        raw = {
            "jobTitle": "Dev",
            "company": "Co",
            "location": "NY",
            "skills": ["Python"],
            "responsibilities": ["Code"],
            "languages": ["EN"],
            "experienceLevel": "Senior",
        }
        del raw[missing_key]
        with pytest.raises(ExtractionValidationError) as exc_info:
            validate_extraction_result(raw)
        assert missing_key in exc_info.value.missing_keys
        assert len(exc_info.value.missing_keys) == 1

    def test_multiple_missing_keys(self):
        """Multiple missing keys raise ExtractionValidationError."""
        raw = {"jobTitle": "Dev", "company": "Co"}  # missing 5 keys
        with pytest.raises(ExtractionValidationError) as exc_info:
            validate_extraction_result(raw)
        assert len(exc_info.value.missing_keys) == 5
        assert "skills" in exc_info.value.missing_keys
        assert "responsibilities" in exc_info.value.missing_keys
        assert "languages" in exc_info.value.missing_keys
        assert "location" in exc_info.value.missing_keys
        assert "experienceLevel" in exc_info.value.missing_keys

    def test_all_keys_missing(self):
        """Empty dict raises ExtractionValidationError with all 7 keys."""
        with pytest.raises(ExtractionValidationError) as exc_info:
            validate_extraction_result({})
        assert exc_info.value.missing_keys == REQUIRED_KEYS

    def test_exception_identifies_missing_fields(self):
        """Exception identifies missing field names."""
        raw = {"jobTitle": "Dev"}
        with pytest.raises(ExtractionValidationError) as exc_info:
            validate_extraction_result(raw)
        msg = str(exc_info.value)
        assert "company" in msg
        assert "skills" in msg

    def test_exception_does_not_expose_full_payload(self):
        """Exception message does not contain the full raw payload."""
        raw = {"jobTitle": "Super Secret Job Title That Should Not Leak"}
        with pytest.raises(ExtractionValidationError) as exc_info:
            validate_extraction_result(raw)
        msg = str(exc_info.value)
        # The payload value should NOT be in the error message
        assert "Super Secret Job Title That Should Not Leak" not in msg


class TestNullPreservation:
    """Tests for null value handling vs missing key handling."""

    def test_none_job_title_preserved(self):
        """jobTitle with None value is valid and preserved."""
        raw = {
            "jobTitle": None, "company": "Co", "location": "NY",
            "skills": ["Py"], "responsibilities": ["Code"],
            "languages": ["EN"], "experienceLevel": "Sr",
        }
        result = validate_extraction_result(raw)
        assert result.jobTitle is None

    def test_none_skills_becomes_empty_list(self):
        """skills with None value → empty list (type safety)."""
        raw = {
            "jobTitle": "Dev", "company": "Co", "location": "NY",
            "skills": None, "responsibilities": ["Code"],
            "languages": ["EN"], "experienceLevel": "Sr",
        }
        result = validate_extraction_result(raw)
        assert result.skills == []

    def test_missing_key_vs_none_key(self):
        """A missing key raises; a None key does not."""
        # None key → valid
        raw_with_none = {
            "jobTitle": None, "company": None, "location": None,
            "skills": None, "responsibilities": None,
            "languages": None, "experienceLevel": None,
        }
        result = validate_extraction_result(raw_with_none)
        assert isinstance(result, ExtractionResult)

        # Missing key → error
        raw_missing = {
            "company": None, "location": None,
            "skills": None, "responsibilities": None,
            "languages": None, "experienceLevel": None,
        }  # jobTitle missing
        with pytest.raises(ExtractionValidationError) as exc_info:
            validate_extraction_result(raw_missing)
        assert "jobTitle" in exc_info.value.missing_keys


class TestNoSideEffects:
    """Verify the function performs no I/O or side effects."""

    def test_no_environment_access(self):
        """Function works without environment variables."""
        old = os.environ.pop("TABLE_NAME", None)
        old2 = os.environ.pop("BEDROCK_MODEL_ID", None)
        try:
            raw = {
                "jobTitle": "Dev", "company": "Co", "location": "NY",
                "skills": [], "responsibilities": [], "languages": [],
                "experienceLevel": "Mid",
            }
            result = validate_extraction_result(raw)
            assert isinstance(result, ExtractionResult)
        finally:
            if old is not None:
                os.environ["TABLE_NAME"] = old
            if old2 is not None:
                os.environ["BEDROCK_MODEL_ID"] = old2

    def test_no_boto3_in_module(self):
        """The validator module does not import boto3 or botocore."""
        import job_analysis_function.validators.extraction_validator as mod
        source = open(mod.__file__).read()
        assert "boto3" not in source
        assert "botocore" not in source
        assert "import logging" not in source
        assert "import os" not in source
