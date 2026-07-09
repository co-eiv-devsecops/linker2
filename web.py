import logging
import os
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, make_response, render_template, request
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from config import DATABASE, HOST, LOG_LEVEL, PORT
from database import SQLiteLinkRepository
from feature_flags import is_enabled
from link_service import LinkService

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("linker.web")
_telemetry_configured = False

RESERVED_PATHS = {
    "health",
    "healthz",
    "metrics",
    "link",
    "favicon.ico",
    "robots.txt",
}


def configure_logging(app):
    logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.propagate = False


def configure_metrics(app):
    resource = Resource.create({"service.name": app.config.get("OTEL_SERVICE_NAME", "linker-python")})
    exporter = OTLPMetricExporter()
    reader = PeriodicExportingMetricReader(exporter)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)


def configure_tracing(app):
    resource = Resource.create({"service.name": app.config.get("OTEL_SERVICE_NAME", "linker-python")})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter())
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


def configure_telemetry(app):
    """Configure OTLP metrics and traces once for the running application."""
    global _telemetry_configured

    if app.config.get("TESTING"):
        return

    if _telemetry_configured:
        return

    if not app.config.get("OTEL_TRACES_ENABLED", True):
        return

    configure_metrics(app)
    configure_tracing(app)
    _telemetry_configured = True


def public_base_url():
    host = request.headers.get("Host", request.host or f"{HOST}:{PORT}")
    proto = request.headers.get("X-Forwarded-Proto", request.scheme or "http")
    return f"{proto}://{host}"


def request_metadata():
    user_agent = request.headers.get("User-Agent", "unknown")
    return {
        "http.method": request.method,
        "http.client_ip": request.headers.get("X-Forwarded-For", request.remote_addr or "unknown"),
        "http.user_agent.length": len(user_agent),
        "http.host": request.headers.get("Host", request.host or "unknown"),
    }


def url_metadata(url):
    parsed = urlparse(url or "")
    return {
        "linker.url.scheme": parsed.scheme or "unknown",
        "linker.url.domain": parsed.netloc.lower() if parsed.netloc else "unknown",
        "linker.url.length": len(url or ""),
        "linker.url.has_query": bool(parsed.query),
    }


def set_attributes(span, attributes):
    for key, value in attributes.items():
        span.set_attribute(key, value)


def create_app(config=None, repository=None, link_service=None, flag_checker=is_enabled):
    app = Flask(__name__, template_folder="views")
    app.config.from_mapping(
        DATABASE=DATABASE,
        HOST=HOST,
        PORT=PORT,
        LOG_LEVEL=LOG_LEVEL,
        OTEL_SERVICE_NAME=os.getenv("OTEL_SERVICE_NAME", "linker-python"),
        OTEL_TRACES_ENABLED=os.getenv("OTEL_TRACES_ENABLED", "true").lower() == "true",
    )

    if config:
        app.config.update(config)

    configure_logging(app)
    configure_telemetry(app)

    repository = repository or SQLiteLinkRepository(app.config["DATABASE"])

    if link_service is None:
        repository.initialize()
        link_service = LinkService(repository)

    app.extensions["linker_repository"] = repository
    app.extensions["linker_service"] = link_service
    app.extensions["linker_flag_checker"] = flag_checker

    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'"
        )
        return response
 
    @app.get("/")
    def index():
        with tracer.start_as_current_span("linker.http.index") as span:
            set_attributes(span, request_metadata())
            span.set_attribute("http.route", "/")
            span.set_attribute("linker.page", "home")
            span.set_status(Status(StatusCode.OK))
            return render_template("index.html")

    @app.get("/health")
    def health():
        with tracer.start_as_current_span("linker.health.basic") as span:
            set_attributes(span, request_metadata())
            span.set_attribute("http.route", "/health")
            span.set_attribute("healthcheck.type", "application")
            span.set_attribute("healthcheck.database", False)
            span.set_attribute("healthcheck.status", "ok")
            span.set_status(Status(StatusCode.OK))
            return jsonify({"status": "ok", "app": "linker-python"}), 200

    @app.get("/healthz")
    @app.get("/healthz/")
    def healthz():
        with tracer.start_as_current_span("linker.healthcheck") as span:
            set_attributes(span, request_metadata())
            span.set_attribute("http.route", "/healthz")
            span.set_attribute("healthcheck.type", "database")
            span.set_attribute("healthcheck.database", True)
            span.add_event("healthcheck.started")

            try:
                repository = app.extensions["linker_repository"]

                with tracer.start_as_current_span("linker.healthcheck.db.select_1") as db_span:
                    db_span.set_attribute("db.system", "sqlite")
                    db_span.set_attribute("db.operation", "SELECT")
                    db_span.set_attribute("db.statement", "SELECT 1")
                    repository.health_check()
                    db_span.set_attribute("db.healthcheck.status", "ok")
                    db_span.add_event("database.ping.ok")
                    db_span.set_status(Status(StatusCode.OK))

                span.set_attribute("healthcheck.status", "ok")
                span.add_event("healthcheck.completed")
                span.set_status(Status(StatusCode.OK))

                return jsonify({
                    "status": "ok",
                    "database": "ok",
                    "app": "linker-python",
                }), 200

            except Exception as error:
                logger.exception("Database healthcheck failed")
                span.set_attribute("healthcheck.status", "error")
                span.record_exception(error)
                span.add_event("healthcheck.failed", {"error.type": type(error).__name__})
                span.set_status(Status(StatusCode.ERROR, str(error)))

                return jsonify({
                    "status": "error",
                    "database": "error",
                    "app": "linker-python",
                    "message": str(error),
                }), 503

    @app.post("/link")
    def create_link():
        service = app.extensions["linker_service"]
        flag_checker = app.extensions["linker_flag_checker"]
        url = request.form.get("url", "")
        custom_alias_enabled = flag_checker("custom_alias", request.environ)
        custom_id = request.form.get("alias", "") if custom_alias_enabled else None

        with tracer.start_as_current_span("linker.http.create_link") as span:
            set_attributes(span, request_metadata())
            set_attributes(span, url_metadata(url))
            span.set_attribute("http.route", "/link")
            span.set_attribute("feature.custom_alias.enabled", custom_alias_enabled)
            span.set_attribute("linker.alias.requested", bool(custom_id))
            span.add_event("create_link.request.received")

            try:
                with tracer.start_as_current_span("linker.http.create_link.service_call") as service_span:
                    service_span.set_attribute("linker.alias.requested", bool(custom_id))
                    short_id = service.create_short_link(url, custom_id=custom_id)
                    service_span.set_attribute("linker.short_id", short_id)
                    service_span.add_event("service.create_short_link.completed")
                    service_span.set_status(Status(StatusCode.OK))
            except ValueError as error:
                logger.warning("Rejected invalid URL from client=%s: %s", request.remote_addr, error)
                span.record_exception(error)
                span.set_attribute("linker.error.type", "validation")
                span.set_attribute("http.status_code", 400)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                response = make_response(str(error), 400)
                response.headers["Content-Type"] = "text/plain; charset=utf-8"
                return response
            except Exception as error:
                logger.error("Failed to create short link due to internal error", exc_info=True)
                span.record_exception(error)
                span.set_attribute("linker.error.type", "internal")
                span.set_attribute("http.status_code", 500)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                abort(500)

            short_url = f"{public_base_url()}/r/{short_id}"
            span.set_attribute("http.status_code", 201)
            span.set_attribute("linker.short_id", short_id)
            span.set_attribute("linker.short_url.length", len(short_url))
            span.add_event("create_link.response.created")
            span.set_status(Status(StatusCode.OK))

        logger.info("Created short_id=%s client=%s", short_id, request.remote_addr)
        response = make_response("", 201)
        response.headers["Location"] = short_url
        return response

    @app.get("/r/<short_id>")
    def redirect_short(short_id):
        if short_id in RESERVED_PATHS:
            logger.warning("Reserved path received by redirect handler: %s", short_id)
            abort(404)

        with tracer.start_as_current_span("linker.http.redirect") as span:
            set_attributes(span, request_metadata())
            span.set_attribute("http.route", "/r/<short_id>")
            span.set_attribute("linker.short_id", short_id)
            span.add_event("redirect.request.received")

            try:
                service = app.extensions["linker_service"]
                with tracer.start_as_current_span("linker.http.redirect.service_call") as service_span:
                    service_span.set_attribute("linker.short_id", short_id)
                    url = service.find_url(short_id)
                    service_span.set_attribute("linker.redirect.found", url is not None)
                    service_span.set_status(Status(StatusCode.OK))
            except Exception as error:
                logger.error("Failed to resolve short_id=%s due to internal processing error", short_id, exc_info=True)
                span.record_exception(error)
                span.set_attribute("linker.error.type", "internal")
                span.set_attribute("http.status_code", 500)
                span.set_status(Status(StatusCode.ERROR, str(error)))
                abort(500)

            if url is None:
                logger.warning("Short URL not found: short_id=%s client=%s", short_id, request.remote_addr)
                span.set_attribute("http.status_code", 404)
                span.set_attribute("linker.redirect.found", False)
                span.add_event("redirect.not_found")
                span.set_status(Status(StatusCode.ERROR, "Short URL not found"))
                abort(404)

            metadata = url_metadata(url)
            span.set_attribute("http.status_code", 301)
            span.set_attribute("linker.redirect.found", True)
            span.set_attribute("linker.redirect.target_domain", metadata["linker.url.domain"])
            span.add_event("redirect.response.created")
            span.set_status(Status(StatusCode.OK))

        logger.info("Redirect short_id=%s client=%s", short_id, request.remote_addr)
        response = make_response("", 301)
        response.headers["Location"] = url
        return response

    return app


def run():
    app = create_app()
    logger.info("Linker Python running on http://%s:%s", app.config["HOST"], app.config["PORT"])
    app.run(host=app.config["HOST"], port=app.config["PORT"])


if __name__ == "__main__":
    run()
