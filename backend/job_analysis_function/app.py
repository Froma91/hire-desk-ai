"""JobAnalysisFunction Lambda entry point — request dispatcher."""

import json
import logging
import re

from job_analysis_function.handlers.analysis import analyze_job
from job_analysis_function.handlers.recommendation import get_recommendation_handler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Safe HTTP responses (dispatcher-generated)
# ---------------------------------------------------------------------------

def _not_found() -> dict:
    """Return 404 for an unknown path."""
    return {
        "statusCode": 404,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": {"code": "NOT_FOUND", "message": "Route not found"}}),
    }


def _method_not_allowed() -> dict:
    """Return 405 when a recognised path is called with an unsupported HTTP method."""
    return {
        "statusCode": 405,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": {"code": "METHOD_NOT_ALLOWED", "message": "Method not allowed"}}),
    }


# ---------------------------------------------------------------------------
# Route resolution
# ---------------------------------------------------------------------------

def _resolve_method_and_path(event: dict) -> tuple[str, str]:
    """
    Extract HTTP method and path from the API Gateway HTTP API v2 event.

    Checks routeKey first (production), falls back to requestContext.http
    (local testing with sam local invoke).
    """
    # Primary: use routeKey if present (format: "POST /analyze")
    route_key = event.get("routeKey")
    if route_key and " " in route_key:
        parts = route_key.split(" ", 1)
        return parts[0].upper(), parts[1]

    # Fallback: requestContext.http.method and rawPath (or path)
    http_ctx = event.get("requestContext", {}).get("http", {})
    method = http_ctx.get("method", "").upper()
    path = event.get("rawPath") or http_ctx.get("path", "")

    return method, path


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def handler(event: dict, context) -> dict:
    """
    Lambda entry point for JobAnalysisFunction.

    Routes:
      POST /analyze → analyze_job handler
      GET /applications/{id}/recommendation → get_recommendation_handler
      Wrong method on recognised paths → 405
      Unknown paths → 404
    """
    method, path = _resolve_method_and_path(event)

    logger.info("dispatch: method=%s path=%s", method, path)

    # Normalize path (strip trailing slash)
    normalized = path.rstrip("/") if path else ""

    # Route: POST /analyze
    if normalized == "/analyze":
        if method == "POST":
            return analyze_job(event, context)
        return _method_not_allowed()

    # Route: GET /applications/{id}/recommendation
    if re.match(r"^/applications/[^/]+/recommendation$", normalized):
        if method == "GET":
            # Extract applicationId from pathParameters or path
            path_params = event.get("pathParameters") or {}
            application_id = path_params.get("id") or path_params.get("applicationId") or ""

            # If not in pathParameters, try to extract from the actual path
            # (but NOT from a routeKey template like "/applications/{id}/recommendation")
            if not application_id or application_id.startswith("{"):
                # Try rawPath or requestContext.http.path for actual values
                raw_path = event.get("rawPath") or ""
                http_path = event.get("requestContext", {}).get("http", {}).get("path", "")
                actual_path = raw_path or http_path
                if actual_path and not actual_path.startswith("/applications/{"):
                    parts = actual_path.rstrip("/").split("/")
                    if len(parts) >= 4 and parts[3] == "recommendation":
                        application_id = parts[2]

            # Validate application ID — must be non-empty, non-whitespace, non-placeholder
            if not application_id or not application_id.strip() or application_id.startswith("{"):
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": {"code": "VALIDATION_ERROR", "message": "Missing application id"}}),
                }

            # Populate pathParameters for the handler
            if event.get("pathParameters") is None:
                event["pathParameters"] = {}
            event["pathParameters"]["id"] = application_id

            return get_recommendation_handler(event, context)
        return _method_not_allowed()

    # Catch-all: unknown path
    logger.warning("dispatch: unknown_path method=%s path=%s", method, path)
    return _not_found()
