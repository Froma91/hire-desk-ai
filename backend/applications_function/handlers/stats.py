"""
Stats handler for GET /stats.

Retrieves all applications for demo-user, computes dashboard statistics,
and returns the result as JSON.

Error mapping:
  RepositoryError → 503 SERVICE_UNAVAILABLE
  other           → 500 INTERNAL_ERROR
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from applications_function.models import DashboardStats
from applications_function.services.applications_service import (
    _repo,
    RepositoryError,
)
from applications_function.services.stats_service import compute_stats

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers (same conventions as other handlers)
# ---------------------------------------------------------------------------

def _error_response(
    status_code: int,
    code: str,
    message: str,
    field: Optional[str] = None,
) -> dict:
    body: dict = {"code": code, "message": message}
    if field is not None:
        body["field"] = field
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": body}),
    }


def _ok_response(status_code: int, data) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data),
    }


def _stats_to_dict(stats: DashboardStats) -> dict:
    """Convert DashboardStats dataclass to a JSON-serialisable dict."""
    return {
        "total": stats.total,
        "byStatus": stats.byStatus,
        "currentWeek": stats.currentWeek,
    }


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

def get_stats(event: dict) -> dict:
    """
    Handle GET /stats.

    Steps:
      1. Retrieve all applications for demo-user via repo.list_all()
      2. Compute statistics using compute_stats(applications, now)
      3. Return HTTP 200 with DashboardStats JSON
    """
    request_id = event.get("requestContext", {}).get("requestId", "unknown")

    try:
        # 1. Retrieve all applications
        applications = _repo().list_all()

        # 2. Compute statistics with current UTC time
        now = datetime.now(timezone.utc)
        stats = compute_stats(applications, now)

        # 3. Return 200 with complete DashboardStats JSON
        logger.info(
            "handler: get_stats request_id=%s status=200 total=%d",
            request_id,
            stats.total,
        )
        return _ok_response(200, _stats_to_dict(stats))

    except RepositoryError as e:
        logger.error(
            "handler: get_stats request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable")

    except Exception as e:
        logger.error(
            "handler: get_stats request_id=%s error_type=%s message=%s",
            request_id,
            type(e).__name__,
            str(e),
        )
        return _error_response(500, "INTERNAL_ERROR", "An unexpected error occurred")
