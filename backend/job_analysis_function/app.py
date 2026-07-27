"""JobAnalysisFunction Lambda entry point — request dispatcher."""

import json
import logging

from job_analysis_function.handlers.analysis import analyze_job

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
    """Return 405 when /analyze is called with an unsupported HTTP method."""
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
      Other methods on /analyze → 405 Method Not Allowed
      Any other path → 404 Not Found
    """
    method, path = _resolve_method_and_path(event)

    logger.info("dispatch: method=%s path=%s", method, path)

    # Normalize path (strip trailing slash)
    normalized_path = path.rstrip("/") if path else ""

    # Route: /analyze
    if normalized_path == "/analyze":
        if method == "POST":
            return analyze_job(event, context)
        else:
            logger.warning("dispatch: method_not_allowed method=%s path=%s", method, path)
            return _method_not_allowed()

    # Catch-all: unknown path
    logger.warning("dispatch: unknown_path method=%s path=%s", method, path)
    return _not_found()
