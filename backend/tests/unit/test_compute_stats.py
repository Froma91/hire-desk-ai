"""
Property test for compute_stats — Property 10.

Property 10: Dashboard stats are consistent with application records.
Validates: Requirements 5.1, 5.2, 5.3

Uses Hypothesis to generate arbitrary lists of Application objects
with random statuses and createdAt timestamps, then verifies the
statistical invariants.
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

from datetime import datetime, timezone, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from models import Application, Status
from services.stats_service import compute_stats


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Generate timezone-aware UTC datetimes in a reasonable range
_utc_datetimes = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(timezone.utc),
)

# Generate a valid Status enum value
_statuses = st.sampled_from(list(Status))

# Generate a minimal Application with arbitrary status and createdAt
_applications = st.builds(
    Application,
    userId=st.just("demo-user"),
    applicationId=st.uuids().map(str),
    jobTitle=st.text(min_size=1, max_size=50),
    status=_statuses,
    createdAt=_utc_datetimes,
    updatedAt=_utc_datetimes,
)

# Generate a list of applications (0 to 30 items)
_application_lists = st.lists(_applications, min_size=0, max_size=30)


# ---------------------------------------------------------------------------
# Helper: compute expected currentWeek independently
# ---------------------------------------------------------------------------

def _expected_current_week(applications: list[Application], now: datetime) -> int:
    """Independent calculation of current-week count for verification."""
    days_since_monday = now.weekday()
    monday_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)
    next_monday = monday_start + timedelta(days=7)

    count = 0
    for app in applications:
        created = app.createdAt
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if monday_start <= created < next_monday:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------

@given(applications=_application_lists, now=_utc_datetimes)
@settings(max_examples=200)
def test_total_equals_len(applications: list[Application], now: datetime):
    """Property 10a: total == len(applications)."""
    stats = compute_stats(applications, now)
    assert stats.total == len(applications)


@given(applications=_application_lists, now=_utc_datetimes)
@settings(max_examples=200)
def test_by_status_sum_equals_total(applications: list[Application], now: datetime):
    """Property 10b: sum(byStatus.values()) == total."""
    stats = compute_stats(applications, now)
    assert sum(stats.byStatus.values()) == stats.total


@given(applications=_application_lists, now=_utc_datetimes)
@settings(max_examples=200)
def test_per_status_count_matches_filtered(applications: list[Application], now: datetime):
    """Property 10c: each per-status count equals the filtered count."""
    stats = compute_stats(applications, now)

    for status in Status:
        expected = sum(1 for app in applications if app.status == status)
        assert stats.byStatus[status.value] == expected, (
            f"Mismatch for {status.value}: expected {expected}, got {stats.byStatus[status.value]}"
        )


@given(applications=_application_lists, now=_utc_datetimes)
@settings(max_examples=200)
def test_current_week_matches_week_window(applications: list[Application], now: datetime):
    """Property 10d: currentWeek equals count with createdAt in current week window."""
    stats = compute_stats(applications, now)
    expected = _expected_current_week(applications, now)
    assert stats.currentWeek == expected


@given(applications=_application_lists, now=_utc_datetimes)
@settings(max_examples=100)
def test_by_status_contains_all_five_keys(applications: list[Application], now: datetime):
    """Property 10e: byStatus always contains all five status keys."""
    stats = compute_stats(applications, now)
    expected_keys = {s.value for s in Status}
    assert set(stats.byStatus.keys()) == expected_keys


@given(now=_utc_datetimes)
@settings(max_examples=50)
def test_empty_list_returns_zeros(now: datetime):
    """Property 10f: empty application list returns all zeros."""
    stats = compute_stats([], now)
    assert stats.total == 0
    assert stats.currentWeek == 0
    assert all(v == 0 for v in stats.byStatus.values())
