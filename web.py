"""Flask adapter for Linker.

Thin hosting layer: it builds the Flask app, wires telemetry/config, and
translates Flask ``request``/``Response`` to and from the framework-agnostic
controller in ``linker_app``. All request-handling logic lives in the
controller so it can be reused by other hosts (e.g. ``serverless.py``).
"""

import logging
import os

from flask import Flask, Response, request

from config import DATABASE, HOST, LOG_LEVEL, PORT
from database import SQLiteLinkRepository
from feature_flags import is_enabled
from link_service import LinkService
from linker_app import LinkerApp, LinkerRequest
from telemetry import configure_telemetry

logger = logging.getLogger(__name__)


def configure_logging(app):
    logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.propagate = False


def build_request():
    """Translate the current Flask request into a framework-agnostic request."""
    return LinkerRequest(
        method=request.method,
        path=request.path,
        form=request.form,
        headers=request.headers,
        remote_addr=request.remote_addr or "unknown",
        flag_context=request.environ,
        default_host=request.host,
        default_scheme=request.scheme,
    )


def to_flask_response(result):
    response = Response(result.body, status=result.status)
    response.headers["Content-Type"] = result.content_type
    for key, value in result.headers.items():
        response.headers[key] = value
    return response


def create_app(config=None, repository=None, link_service=None, flag_checker=is_enabled):
    app = Flask(__name__)
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
    configure_telemetry(
        service_name=app.config.get("OTEL_SERVICE_NAME", "linker-python"),
        traces_enabled=app.config.get("OTEL_TRACES_ENABLED", True),
        testing=app.config.get("TESTING", False),
    )

    repository = repository or SQLiteLinkRepository(app.config["DATABASE"])

    if link_service is None:
        repository.initialize()
        link_service = LinkService(repository)

    linker = LinkerApp(service=link_service, repository=repository, flag_checker=flag_checker)

    app.extensions["linker_repository"] = repository
    app.extensions["linker_service"] = link_service
    app.extensions["linker_app"] = linker
    app.extensions["linker_flag_checker"] = flag_checker

    @app.get("/")
    def index():
        return to_flask_response(linker.index(build_request()))

    @app.get("/health")
    def health():
        return to_flask_response(linker.health(build_request()))

    @app.get("/healthz")
    @app.get("/healthz/")
    def healthz():
        return to_flask_response(linker.healthz(build_request()))

    @app.post("/link")
    def create_link():
        return to_flask_response(linker.create_link(build_request()))

    @app.get("/r/<short_id>")
    def redirect_short(short_id):
        return to_flask_response(linker.redirect(short_id, build_request()))

    return app


def run():
    app = create_app()
    logger.info("Linker Python running on http://%s:%s", app.config["HOST"], app.config["PORT"])
    app.run(host=app.config["HOST"], port=app.config["PORT"])


if __name__ == "__main__":
    run()
