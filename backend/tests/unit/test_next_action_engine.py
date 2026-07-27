"""
Property test for compute_next_action — Property 11.

Property 11: Next-action engine is deterministic and status-driven.
Validates: Requirements 6.1–6.6, 6.9–6.11

Uses Hypothesis to generate arbitrary Application objects with random
statuses, dates, and status histories, then verifies:
  - Determinism (same inputs → same outputs)
  - Correctness (each branch produces the exact expected result)
  - Boundary conditions (off-by-one detection at 7 and 14 day thresholds)
  - Purity (no mutation, no I/O, explanation always None)
"""

import sys
import os
import copy

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

from datetime import datetime, timezone, timedelta

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

from models import (
    Application,
    NextAction,
    Priority,
    Status,
    StatusEntry,
)
import business_rules.next_action_engine as _engine_module
from business_rules.next_action_engine import compute_next_action


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

_utc_datetimes = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(timezone.utc),
)

_statuses = st.sampled_from(list(Status))

_status_entries = st.builds(
    StatusEntry,
    status=_statuses,
    timestamp=_utc_datetimes,
)

# Status history: 0 to 5 entries
_status_histories = st.lists(_status_entries, min_size=0, max_size=5)

# Generate Application with arbitrary fields
_applications = st.builds(
    Application,
    userId=st.just("demo-user"),
    applicationId=st.uuids().map(str),
    jobTitle=st.text(min_size=1, max_size=30),
    status=_statuses,
    createdAt=_utc_datetimes,
    updatedAt=_utc_datetimes,
    statusHistory=_status_histories,
)


# Ensure now >= createdAt and now >= updatedAt for realistic scenarios
@st.composite
def _app_and_now(draw):
    """Generate an Application and a `now` that is >= both createdAt and updatedAt."""
    app = draw(_applications)
    # Ensure now is after both dates for meaningful age calculations
    latest = max(app.createdAt, app.updatedAt)
    offset_days = draw(st.integers(min_value=0, max_value=60))
    now = latest + timedelta(days=offset_days, hours=draw(st.integers(min_value=0, max_value=23)))
    return app, now


@st.composite
def _app_with_status_and_now(draw, status: Status, min_history: int = 0):
    """Generate an Application with a specific status and a valid `now`."""
    created = draw(_utc_datetimes)
    updated = draw(_utc_datetimes)
    history = draw(st.lists(_status_entries, min_size=min_history, max_size=5))
    app = Application(
        userId="demo-user",
        applicationId=draw(st.uuids().map(str)),
        jobTitle=draw(st.text(min_size=1, max_size=30)),
        status=status,
        createdAt=created,
        updatedAt=updated,
        statusHistory=history,
    )
    latest = max(app.createdAt, app.updatedAt)
    offset_days = draw(st.integers(min_value=0, max_value=60))
    now = latest + timedelta(days=offset_days, hours=draw(st.integers(min_value=0, max_value=23)))
    return app, now


# ---------------------------------------------------------------------------
# Helper: build an Application with specific conditions
# ---------------------------------------------------------------------------


def _make_app(
    status: Status = Status.WISHLIST,
    created_days_ago: int = 0,
    updated_days_ago: int = 0,
    history_len: int = 1,
    now: datetime | None = None,
) -> tuple[Application, datetime]:
    """Create an Application and `now` with precise time deltas."""
    if now is None:
        now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    created = now - timedelta(days=created_days_ago)
    updated = now - timedelta(days=updated_days_ago)

    history = [StatusEntry(status=status, timestamp=created)]
    # Add extra entries if history_len > 1
    for i in range(1, history_len):
        history.append(StatusEntry(status=status, timestamp=created + timedelta(days=i)))

    app = Application(
        userId="demo-user",
        applicationId="test-id",
        jobTitle="Test Job",
        status=status,
        createdAt=created,
        updatedAt=updated,
        statusHistory=history,
    )
    return app, now


# ===========================================================================
# PROPERTY TESTS (Hypothesis-generated)
# ===========================================================================


@given(data=_app_and_now())
@settings(max_examples=300)
def test_determinism_same_inputs_same_outputs(data):
    """Property 11a: identical inputs always produce identical outputs."""
    app, now = data
    result1 = compute_next_action(app, now)
    result2 = compute_next_action(app, now)
    assert result1 == result2


@given(data=_app_and_now())
@settings(max_examples=300)
def test_explanation_always_none(data):
    """Property 11b: explanation is always None in the deterministic engine."""
    app, now = data
    result = compute_next_action(app, now)
    if result is not None:
        assert result.explanation is None


@given(data=_app_and_now())
@settings(max_examples=200)
def test_application_not_mutated(data):
    """Property 11c: the supplied Application is not mutated."""
    app, now = data
    original = copy.deepcopy(app)
    compute_next_action(app, now)
    assert app == original


@given(data=_app_and_now())
@settings(max_examples=300)
def test_result_type_is_next_action_or_none(data):
    """Property 11d: return value is always NextAction or None."""
    app, now = data
    result = compute_next_action(app, now)
    assert result is None or isinstance(result, NextAction)


@given(data=_app_with_status_and_now(Status.INTERVIEW))
@settings(max_examples=200)
def test_interview_always_returns_action(data):
    """Property 11e: Interview status always returns an action."""
    app, now = data
    result = compute_next_action(app, now)
    assert result is not None
    assert result.label == "Prepare for interview"
    assert result.priority == Priority.HIGH


@given(data=_app_with_status_and_now(Status.OFFER))
@settings(max_examples=200)
def test_offer_always_returns_action(data):
    """Property 11f: Offer status always returns an action."""
    app, now = data
    result = compute_next_action(app, now)
    assert result is not None
    assert result.label == "Review and respond to offer"
    assert result.priority == Priority.HIGH


@given(data=_app_with_status_and_now(Status.REJECTED))
@settings(max_examples=200)
def test_rejected_always_returns_action(data):
    """Property 11g: Rejected status always returns an action."""
    app, now = data
    result = compute_next_action(app, now)
    assert result is not None
    assert result.label == "Archive or reapply"
    assert result.priority == Priority.LOW


@given(data=_app_with_status_and_now(Status.WISHLIST, min_history=2))
@settings(max_examples=200)
def test_wishlist_with_status_change_returns_none(data):
    """Property 11h: Wishlist with status history > 1 always returns None."""
    app, now = data
    result = compute_next_action(app, now)
    assert result is None


@given(data=_app_with_status_and_now(Status.APPLIED, min_history=2))
@settings(max_examples=200)
def test_applied_with_status_change_returns_none(data):
    """Property 11i: Applied with status history > 1 always returns None."""
    app, now = data
    result = compute_next_action(app, now)
    assert result is None


# ===========================================================================
# EXPLICIT BOUNDARY TESTS (off-by-one detection)
# ===========================================================================


class TestWishlistBoundaries:
    """Explicit boundary tests for the Wishlist 7-day threshold."""

    def test_wishlist_exactly_7_days_returns_none(self):
        """At exactly 7 days (not > 7), should return None."""
        app, now = _make_app(status=Status.WISHLIST, created_days_ago=7, updated_days_ago=7)
        result = compute_next_action(app, now)
        assert result is None

    def test_wishlist_8_days_returns_apply_now(self):
        """At 8 days (> 7), should return 'Apply now'."""
        app, now = _make_app(status=Status.WISHLIST, created_days_ago=8, updated_days_ago=8)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Apply now"
        assert result.priority == Priority.HIGH
        assert result.explanation is None

    def test_wishlist_6_days_returns_none(self):
        """At 6 days (< 7), should return None."""
        app, now = _make_app(status=Status.WISHLIST, created_days_ago=6, updated_days_ago=6)
        result = compute_next_action(app, now)
        assert result is None

    def test_wishlist_30_days_no_change_returns_apply_now(self):
        """Long-standing Wishlist with no status change -> Apply now."""
        app, now = _make_app(status=Status.WISHLIST, created_days_ago=30, updated_days_ago=30)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Apply now"

    def test_wishlist_old_but_has_status_change_returns_none(self):
        """Wishlist > 7 days BUT has status change -> None."""
        app, now = _make_app(status=Status.WISHLIST, created_days_ago=10, updated_days_ago=10, history_len=2)
        result = compute_next_action(app, now)
        assert result is None

    def test_wishlist_0_days_returns_none(self):
        """Just created Wishlist -> None."""
        app, now = _make_app(status=Status.WISHLIST, created_days_ago=0, updated_days_ago=0)
        result = compute_next_action(app, now)
        assert result is None


class TestAppliedBoundaries:
    """Explicit boundary tests for the Applied 14-day threshold."""

    def test_applied_exactly_14_days_returns_none(self):
        """At exactly 14 days since update (not > 14), should return None."""
        app, now = _make_app(status=Status.APPLIED, created_days_ago=14, updated_days_ago=14)
        result = compute_next_action(app, now)
        assert result is None

    def test_applied_15_days_returns_follow_up(self):
        """At 15 days since update (> 14), should return 'Follow up'."""
        app, now = _make_app(status=Status.APPLIED, created_days_ago=20, updated_days_ago=15)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Follow up"
        assert result.priority == Priority.MEDIUM
        assert result.explanation is None

    def test_applied_13_days_returns_none(self):
        """At 13 days since update (< 14), should return None."""
        app, now = _make_app(status=Status.APPLIED, created_days_ago=20, updated_days_ago=13)
        result = compute_next_action(app, now)
        assert result is None

    def test_applied_old_but_has_status_change_returns_none(self):
        """Applied > 14 days BUT has status change -> None."""
        app, now = _make_app(status=Status.APPLIED, created_days_ago=30, updated_days_ago=20, history_len=2)
        result = compute_next_action(app, now)
        assert result is None

    def test_applied_1_day_returns_none(self):
        """Recently applied -> None."""
        app, now = _make_app(status=Status.APPLIED, created_days_ago=5, updated_days_ago=1)
        result = compute_next_action(app, now)
        assert result is None


class TestInterviewExplicit:
    """Explicit tests for Interview (always returns action regardless of dates)."""

    def test_interview_fresh_returns_action(self):
        """Interview just set -> always returns action."""
        app, now = _make_app(status=Status.INTERVIEW, created_days_ago=0, updated_days_ago=0)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Prepare for interview"
        assert result.priority == Priority.HIGH

    def test_interview_old_returns_action(self):
        """Interview set 30 days ago -> still returns action."""
        app, now = _make_app(status=Status.INTERVIEW, created_days_ago=30, updated_days_ago=30)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Prepare for interview"

    def test_interview_with_status_changes_returns_action(self):
        """Interview with multiple history entries -> still returns action."""
        app, now = _make_app(status=Status.INTERVIEW, created_days_ago=10, updated_days_ago=5, history_len=3)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Prepare for interview"


class TestOfferExplicit:
    """Explicit tests for Offer (always returns action)."""

    def test_offer_returns_review_and_respond(self):
        """Offer always returns 'Review and respond to offer'."""
        app, now = _make_app(status=Status.OFFER, created_days_ago=2, updated_days_ago=1)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Review and respond to offer"
        assert result.priority == Priority.HIGH
        assert result.explanation is None


class TestRejectedExplicit:
    """Explicit tests for Rejected (terminal - always returns action)."""

    def test_rejected_returns_archive_or_reapply(self):
        """Rejected always returns 'Archive or reapply'."""
        app, now = _make_app(status=Status.REJECTED, created_days_ago=5, updated_days_ago=2)
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Archive or reapply"
        assert result.priority == Priority.LOW
        assert result.explanation is None


class TestTimezoneHandling:
    """Verify timezone-aware UTC datetimes are handled correctly."""

    def test_utc_aware_datetimes_work(self):
        """Function handles timezone-aware UTC datetimes without error."""
        now = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        app = Application(
            userId="demo-user",
            applicationId="tz-test",
            jobTitle="TZ Job",
            status=Status.WISHLIST,
            createdAt=datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            updatedAt=datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            statusHistory=[
                StatusEntry(
                    status=Status.WISHLIST,
                    timestamp=datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
                )
            ],
        )
        # 14 days old -> > 7 -> should return "Apply now"
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Apply now"

    def test_empty_status_history_treated_as_no_change(self):
        """Empty statusHistory (len 0) means has_status_change is False."""
        now = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
        app = Application(
            userId="demo-user",
            applicationId="empty-hist",
            jobTitle="Job",
            status=Status.WISHLIST,
            createdAt=now - timedelta(days=10),
            updatedAt=now - timedelta(days=10),
            statusHistory=[],  # empty
        )
        # age > 7, no status change (empty history -> len <= 1) -> "Apply now"
        result = compute_next_action(app, now)
        assert result is not None
        assert result.label == "Apply now"


class TestNoIOOrAWSAccess:
    """Verify the function performs no I/O or AWS access."""

    def test_no_environment_variable_access(self):
        """Function works without any environment variables set."""
        # Remove TABLE_NAME if it exists
        old = os.environ.pop("TABLE_NAME", None)
        try:
            app, now = _make_app(status=Status.INTERVIEW)
            result = compute_next_action(app, now)
            assert result is not None
        finally:
            if old is not None:
                os.environ["TABLE_NAME"] = old

    def test_no_boto3_import_in_module(self):
        """The engine module does not import boto3 or botocore."""
        # Use the reference bound at import time (correct Lambda root was on
        # sys.path then); re-importing at run time is not collision-safe.
        engine_module = _engine_module
        source = open(engine_module.__file__).read()
        assert "boto3" not in source
        assert "botocore" not in source
        assert "import os" not in source
        assert "import logging" not in source
