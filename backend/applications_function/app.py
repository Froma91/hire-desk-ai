"""ApplicationsFunction Lambda entry point — request dispatcher."""

import json
import logging
import re

from applications_function.handlers.applications import (
    create_application,
    list_applications,
    get_application,
    update_application,
    delete_application,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Placeholder for routes whose handlers are not yet implemented
# ---------------------------------------------------------------------------

def _not_implemented(event: dict) -> dict:
    """Placeholder for routes whose handlers are not yet built."""
    return {
        "statusCode": 501,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(
            {"error": {"code": "NOT_IMPLEMENTED", "message": "This endpoint is not yet available"}}
        ),
    }


# ---------------------------------------------------------------------------
# Route table
# ---------------------------------------------------------------------------

_ROUTES: dict[str, callable] = {
    "POST /applications": create_application,
    "GET /applications": list_applications,
    "GET /applications/{id}": get_application,
    "PATCH /applications/{id}": update_application,
    "DELETE /applications/{id}": delete_application,
    "PATCH /applications/{id}/status": _not_implemented,
    "GET /stats": _not_implemented,
    "GET /applications/{id}/recommendation": _not_implemented,
}


# ---------------------------------------------------------------------------
# Route resolution
# ---------------------------------------------------------------------------

def _resolve_route_key(event: dict) -> str:
    """Extract or reconstruct the routeKey from the event."""
    route_key = event.get("routeKey")
    if route_key:
        return route_key

    # Fallback: construct from requestContext.http (local testing)
    http_ctx = event.get("requestContext", {}).get("http", {})
    method = http_ctx.get("method", "").upper()
    path = http_ctx.get("path", "")

    # Match known path patterns and convert to routeKey format
    if path == "/applications" or path == "/applications/":
        return f"{method} /applications"

    if path == "/stats":
        return f"{method} /stats"

    # /applications/{id}/status
    if re.match(r"^/applications/[^/]+/status$", path):
        return f"{method} /applications/{{id}}/status"

    # /applications/{id}/recommendation
    if re.match(r"^/applications/[^/]+/recommendation$", path):
        return f"{method} /applications/{{id}}/recommendation"

    # /applications/{id}
    if re.match(r"^/applications/[^/]+$", path):
        return f"{method} /applications/{{id}}"

    return f"{method} {path}"  # will hit 404 catch-all


# ---------------------------------------------------------------------------
# 404 catch-all
# ---------------------------------------------------------------------------

def _not_found(route_key: str) -> dict:
    """Return 404 for unrecognised routes."""
    return {
        "statusCode": 404,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": {"code": "NOT_FOUND", "message": "Route not found"}}),
    }


# ---------------------------------------------------------------------------
# Lambda entry point
# ---------------------------------------------------------------------------

def handler(event: dict, context) -> dict:
    """
    Lambda entry point. Routes API Gateway HTTP API v2 events
    to the appropriate CRUD handler based on routeKey.
    """
    route_key = _resolve_route_key(event)
    logger.info("dispatch: route_key=%s", route_key)

    handler_fn = _ROUTES.get(route_key)
    if handler_fn is None:
        logger.warning("dispatch: unknown route_key=%s", route_key)
        return _not_found(route_key)

    return handler_fn(event)
