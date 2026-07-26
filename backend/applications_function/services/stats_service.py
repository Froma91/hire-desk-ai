"""
Stats service — pure deterministic computation of dashboard statistics.

This module contains NO logging, NO AWS calls, NO repository access,
and NO side effects. It accepts data and a timestamp, and returns stats.
"""

from datetime import datetime, timezone, timedelta

from applications_function.models import Application, DashboardStats, Status


def compute_stats(applications: list[Application], now: datetime) -> DashboardStats:
    """
    Compute dashboard statistics from a list of applications.

    Args:
        applications: List of Application objects (not mutated).
        now: Current UTC datetime (timezone-aware). Used to define the
             current week boundary.

    Returns:
        DashboardStats with:
          - total: number of applications
          - byStatus: count per status (all five statuses present, including zeros)
          - currentWeek: number of applications created in the current
                         ISO week (Monday 00:00:00 UTC to Sunday 23:59:59 UTC)

    The current week window is defined as:
      - Start: Monday 00:00:00 UTC of the ISO week containing `now`
      - End: exclusive next Monday 00:00:00 UTC

    This function is pure and deterministic — it performs no I/O and does
    not mutate the supplied list.
    """
    # Total count
    total = len(applications)

    # Count by status — initialize all five statuses to 0
    by_status: dict[str, int] = {status.value: 0 for status in Status}
    for app in applications:
        by_status[app.status.value] += 1

    # Current week calculation (ISO week: Monday = 0)
    # Find the Monday 00:00:00 UTC of the week containing `now`
    days_since_monday = now.weekday()
    monday_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_monday)

    # Next Monday 00:00:00 UTC (exclusive end of current week)
    next_monday = monday_start + timedelta(days=7)

    # Count applications created within [monday_start, next_monday)
    current_week = 0
    for app in applications:
        created = app.createdAt
        # Handle naive datetimes by assuming UTC
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if monday_start <= created < next_monday:
            current_week += 1

    return DashboardStats(
        total=total,
        byStatus=by_status,
        currentWeek=current_week,
    )
