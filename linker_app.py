"""Framework-agnostic HTTP controller for Linker.

This is the equivalent of ``Linker.Core.Linker`` in the .NET reference repo: it
holds the request-handling logic (routing intent, telemetry, validation and
error-to-status mapping) with **no dependency on any web framework**.

Adapters translate transport in and out:
  - ``web.py``        -> Flask ``request``  -> ``LinkerRequest`` -> ``LinkerResponse`` -> Flask ``Response``
  - ``serverless.py`` -> OCI Functions ctx  -> ``LinkerRequest`` -> ``LinkerResponse`` -> fdk ``Response``

Both share the exact same ``LinkerApp`` instance behaviour, so business logic and
observability are written once.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Mapping
from urllib.parse import urlparse

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

import views

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("linker.web")

RESERVED_PATHS = {
    "health",
    "healthz",
    "metrics",
    "link",
    "favicon.ico",
    "robots.txt",
}


@dataclass
class LinkerRequest:
    """Normalized inbound request, independent of the hosting framework."""

    method: str = "GET"
    path: str = "/"
    form: Mapping[str, str] = field(default_factory=dict)
    headers: Mapping[str, str] = field(default_factory=dict)
    remote_addr: str = "unknown"
    # Context passed to the feature-flag checker (WSGI environ for Flask,
    # os.environ for serverless).
    flag_context: Mapping[str, str] = field(default_factory=dict)
    # Fallbacks used to build the public base URL when the proxy headers are
    # absent (Flask supplies request.host/request.scheme; serverless supplies
    # config-derived values).
    default_host: str = "localhost"
    default_scheme: str = "http"

    def header(self, name, default=None):
        target = name.lower()
        for key, value in self.headers.items():
            if key.lower() == target:
                return value
        return default


@dataclass
class LinkerResponse:
    """Normalized outbound response, independent of the hosting framework."""

    status: int
    body: str = ""
    content_type: str = "text/plain; charset=utf-8"
    headers: dict = field(default_factory=dict)


def _json_response(payload, status):
    return LinkerResponse(
        status=status,
        body=json.dumps(payload),
        content_type="application/json",
    )


def set_attributes(span, attributes):
    for key, value in attributes.items():
        span.set_attribute(key, value)


def request_metadata(req):
    user_agent = req.header("User-Agent", "unknown")
    return {
        "http.method": req.method,
        "http.client_ip": req.header("X-Forwarded-For", req.remote_addr or "unknown"),
        "http.user_agent.length": len(user_agent),
        "http.host": req.header("Host", req.default_host or "unknown"),
    }


def url_metadata(url):
    parsed = urlparse(url or "")
    return {
        "linker.url.scheme": parsed.scheme or "unknown",
        "linker.url.domain": parsed.netloc.lower() if parsed.netloc else "unknown",
        "linker.url.length": len(url or ""),
        "linker.url.has_query": bool(parsed.query),
    }


def public_base_url(req):
    host = req.header("Host", req.default_host)
    proto = req.header("X-Forwarded-Proto", req.default_scheme)
    return f"{proto}://{host}"


class LinkerApp:
    def __init__(self, service, repository, flag_checker):
        self.service = service
        self.repository = repository
        self.flag_checker = flag_checker

    # --- Actions -----------------------------------------------------------

    def index(self, req):
        with tracer.start_as_current_span("linker.http.index") as span:
            set_attributes(span, request_metadata(req))
            span.set_attribute("http.route", "/")
            span.set_attribute("linker.page", "home")
            span.set_status(Status(StatusCode.OK))

        return LinkerResponse(
            status=200,
            body=views.render_index(),
            content_type="text/html; charset=utf-8",
        )

    def health(self, req):
        with tracer.start_as_current_span("linker.health.basic") as span:
            set_attributes(span, request_metadata(req))
            span.set_attribute("http.route", "/health")
            span.set_attribute("healthcheck.type", "application")
            span.set_attribute("healthcheck.database", False)
            span.set_attribute("healthcheck.status", "ok")
            span.set_status(Status(StatusCode.OK))

        return _json_response({"status": "ok", "app": "linker-python"}, 200)

    def healthz(self, req):
        with tracer.start_as_current_span("linker.healthcheck") as span:
            set_attributes(span, request_metadata(req))
            span.set_attribute("http.route", "/healthz")
            span.set_attribute("healthcheck.type", "database")
            span.set_attribute("healthcheck.database", True)
            span.add_event("healthcheck.started")

            try:
                with tracer.start_as_current_span("linker.healthcheck.db.select_1") as db_span:
                    db_span.set_attribute("db.system", getattr(self.repository, "db_system", "unknown"))
                    db_span.set_attribute("db.operation", "SELECT")
                    db_span.set_attribute("db.statement", "SELECT 1")
                    self.repository.health_check()
                    db_span.set_attribute("db.healthcheck.status", "ok")
                    db_span.add_event("database.ping.ok")
                    db_span.set_status(Status(StatusCode.OK))

                span.set_attribute("healthcheck.status", "ok")
                span.add_event("healthcheck.completed")
                span.set_status(Status(StatusCode.OK))

                return _json_response(
                    {"status": "ok", "database": "ok", "app": "linker-python"},
                    200,
                )
            except Exception as error:
                logger.exception("Database healthcheck failed")
                span.set_attribute("healthcheck.status", "error")
                span.record_exception(error)
                span.add_event("healthcheck.failed", {"error.type": type(error).__name__})
                span.set_status(Status(StatusCode.ERROR, str(error)))

                return _json_response(
                    {
                        "status": "error",
                        "database": "error",
                        "app": "linker-python",
                        "message": str(error),
                    },
                    503,
                )

    def create_link(self, req):
        url = req.form.get("url", "")
        custom_alias_enabled = self.flag_checker("custom_alias", req.flag_context)
        custom_id = req.form.get("alias", "") if custom_alias_enabled else None

        with tracer.start_as_current_span("linker.http.create_link") as span:
            set_attributes(span, request_metadata(req))
            set_attributes(span, url_metadata(url))
            span.set_attribute("http.route", "/link")
            span.set_attribute("feature.custom_alias.enabled", custom_alias_enabled)
            span.set_attribute("linker.alias.requested", bool(custom_id))
            span.add_event("create_link.request.received")

            try:
                with tracer.start_as_current_span("linker.http.create_link.service_call") as service_span:
                    service_span.set_attribute("linker.alias.requested", bool(custom_id))
                    short_id = self.service.create_short_link(url, custom_id=custom_id)
                    service_span.set_attribute("linker.short_id", short_id)
                    service_span.add_event("service.create_short_link.completed")
                    service_span.set_status(Status(StatusCode.OK))
            except ValueError as error:
                logger.warning("Rejected invalid URL from client=%s: %s", req.remote_addr, error)
                span.record_exception(error)
                span.set_attribute("linker.error.type", "validation")
                span.set_attribute("http.status_code", 400)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                return LinkerResponse(status=400, body=str(error))
            except Exception as error:
                logger.error("Failed to create short link due to internal error", exc_info=True)
                span.record_exception(error)
                span.set_attribute("linker.error.type", "internal")
                span.set_attribute("http.status_code", 500)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                return LinkerResponse(status=500, body="Internal Server Error")

            short_url = f"{public_base_url(req)}/r/{short_id}"
            span.set_attribute("http.status_code", 201)
            span.set_attribute("linker.short_id", short_id)
            span.set_attribute("linker.short_url.length", len(short_url))
            span.add_event("create_link.response.created")
            span.set_status(Status(StatusCode.OK))

        logger.info("Created short_id=%s client=%s", short_id, req.remote_addr)
        return LinkerResponse(status=201, headers={"Location": short_url})

    def redirect(self, short_id, req):
        if short_id in RESERVED_PATHS:
            logger.warning("Reserved path received by redirect handler: %s", short_id)
            return LinkerResponse(status=404, body="Not Found")

        with tracer.start_as_current_span("linker.http.redirect") as span:
            set_attributes(span, request_metadata(req))
            span.set_attribute("http.route", "/r/<short_id>")
            span.set_attribute("linker.short_id", short_id)
            span.add_event("redirect.request.received")

            try:
                with tracer.start_as_current_span("linker.http.redirect.service_call") as service_span:
                    service_span.set_attribute("linker.short_id", short_id)
                    url = self.service.find_url(short_id)
                    service_span.set_attribute("linker.redirect.found", url is not None)
                    service_span.set_status(Status(StatusCode.OK))
            except Exception as error:
                logger.error("Failed to resolve short_id=%s due to internal processing error", short_id, exc_info=True)
                span.record_exception(error)
                span.set_attribute("linker.error.type", "internal")
                span.set_attribute("http.status_code", 500)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                return LinkerResponse(status=500, body="Internal Server Error")

            if url is None:
                logger.warning("Short URL not found: short_id=%s client=%s", short_id, req.remote_addr)
                span.set_attribute("http.status_code", 404)
                span.set_attribute("linker.redirect.found", False)
                span.add_event("redirect.not_found")
                span.set_status(Status(StatusCode.ERROR, "Short URL not found"))
                return LinkerResponse(status=404, body="Not Found")

            metadata = url_metadata(url)
            span.set_attribute("http.status_code", 301)
            span.set_attribute("linker.redirect.found", True)
            span.set_attribute("linker.redirect.target_domain", metadata["linker.url.domain"])
            span.add_event("redirect.response.created")
            span.set_status(Status(StatusCode.OK))

        logger.info("Redirect short_id=%s client=%s", short_id, req.remote_addr)
        return LinkerResponse(status=301, headers={"Location": url})
    def metadata(self, short_id, req):
        enabled = self.flag_checker("advanced_operations", req.flag_context)

        with tracer.start_as_current_span("linker.http.metadata") as span:
            set_attributes(span, request_metadata(req))
            span.set_attribute("http.route", "/r/<short_id>")
            span.set_attribute("http.method", "HEAD")
            span.set_attribute("linker.short_id", short_id)
            span.set_attribute("feature.advanced_operations.enabled", enabled)

            if not enabled:
                span.set_attribute("http.status_code", 404)
                span.set_status(Status(StatusCode.ERROR, "Feature disabled"))
                return LinkerResponse(status=404, body="Not Found")

            try:
                url = self.service.find_url(short_id)
            except Exception as error:
                logger.error("Failed to resolve metadata for short_id=%s", short_id, exc_info=True)
                span.record_exception(error)
                span.set_attribute("http.status_code", 500)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                return LinkerResponse(status=500, body="Internal Server Error")

            if url is None:
                span.set_attribute("http.status_code", 404)
                span.set_status(Status(StatusCode.ERROR, "Short URL not found"))
                return LinkerResponse(status=404, body="Not Found")

            span.set_attribute("http.status_code", 200)
            span.set_attribute("linker.metadata.found", True)
            span.set_status(Status(StatusCode.OK))

            return LinkerResponse(
                status=200,
                body=url,
                content_type="text/plain; charset=utf-8",
                headers={"X-Linker-Original-Url": url},
            )

    def delete(self, short_id, req):
        enabled = self.flag_checker("advanced_operations", req.flag_context)

        with tracer.start_as_current_span("linker.http.delete") as span:
            set_attributes(span, request_metadata(req))
            span.set_attribute("http.route", "/r/<short_id>")
            span.set_attribute("http.method", "DELETE")
            span.set_attribute("linker.short_id", short_id)
            span.set_attribute("feature.advanced_operations.enabled", enabled)

            if not enabled:
                span.set_attribute("http.status_code", 404)
                span.set_status(Status(StatusCode.ERROR, "Feature disabled"))
                return LinkerResponse(status=404, body="Not Found")

            try:
                deleted = self.service.delete_short_link(short_id)
            except Exception as error:
                logger.error("Failed to delete short_id=%s", short_id, exc_info=True)
                span.record_exception(error)
                span.set_attribute("http.status_code", 500)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                return LinkerResponse(status=500, body="Internal Server Error")

            if not deleted:
                span.set_attribute("http.status_code", 404)
                span.set_status(Status(StatusCode.ERROR, "Short URL not found"))
                return LinkerResponse(status=404, body="Not Found")

            span.set_attribute("http.status_code", 200)
            span.set_attribute("linker.delete.success", True)
            span.set_status(Status(StatusCode.OK))

            return LinkerResponse(status=200, body="Deleted successfully")
    
    # --- Single-entry dispatch (used by serverless / any non-routing host) --

    def dispatch(self, req):
        method = (req.method or "GET").upper()
        path = req.path or "/"
        if len(path) > 1:
            path = path.rstrip("/") or "/"

        if method == "GET" and path == "/":
            return self.index(req)
        if method == "GET" and path == "/health":
            return self.health(req)
        if method == "GET" and path == "/healthz":
            return self.healthz(req)
        if method == "POST" and path == "/link":
            return self.create_link(req)
        if path.startswith("/r/"):
            short_id = path[len("/r/"):]

            if method == "GET":
                return self.redirect(short_id, req)

            if method == "HEAD":
                return self.metadata(short_id, req)

            if method == "DELETE":
                return self.delete(short_id, req)

        return LinkerResponse(status=404, body="Not Found")
