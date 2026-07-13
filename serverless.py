"""OCI Functions (Fn Project) adapter for Linker.

Reuses the exact same framework-agnostic controller (``linker_app.LinkerApp``)
as the Flask host (``web.py``). Only the transport translation lives here:

    OCI Functions invoke context -> LinkerRequest -> LinkerResponse -> fdk Response

Deploy with the Fn/OCI CLI (see ``func.yaml`` and ``requirements-serverless.txt``).
Entrypoint: ``serverless:handler``.

The controller is built **lazily and once** (on the first invocation) so that the
database connection and telemetry providers are reused across warm invocations,
while merely importing this module never opens a database connection.
"""

import io
import logging
import os
from urllib.parse import parse_qs, urlparse

import config
from database import create_repository
from feature_flags import is_enabled
from link_service import LinkService
from linker_app import LinkerApp, LinkerRequest
from telemetry import configure_telemetry

logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger("linker.serverless")

_linker = None


def build_linker():
    """Cold-start factory: wire the repository, service, telemetry and controller."""
    repository = create_repository()
    repository.initialize()
    service = LinkService(repository)
    configure_telemetry(
        service_name=config.OTEL_SERVICE_NAME,
        traces_enabled=config.OTEL_TRACES_ENABLED,
    )
    return LinkerApp(service=service, repository=repository, flag_checker=is_enabled)


def get_linker():
    global _linker
    if _linker is None:
        _linker = build_linker()
    return _linker


def _parse_form(body_bytes, content_type):
    if not body_bytes:
        return {}
    if "application/x-www-form-urlencoded" in (content_type or ""):
        parsed = parse_qs(body_bytes.decode("utf-8"))
        return {key: values[0] for key, values in parsed.items() if values}
    return {}


def build_request(ctx, data=None):
    """Translate an OCI Functions invoke context into a framework-agnostic request.

    When fronted by an OCI API Gateway, the original HTTP method and URL are
    forwarded via the ``Fn-Http-*`` request headers; adjust here if your gateway
    is configured differently.
    """
    headers = dict(ctx.Headers() or {})

    method = headers.get("Fn-Http-Method", "GET")
    raw_url = headers.get("Fn-Http-Request-Url", "/")
    path = urlparse(raw_url).path or "/"

    body_bytes = data.getvalue() if data is not None else b""
    form = _parse_form(body_bytes, headers.get("Content-Type"))

    return LinkerRequest(
        method=method,
        path=path,
        form=form,
        headers=headers,
        remote_addr=headers.get("X-Forwarded-For", "unknown"),
        flag_context=os.environ,
        default_host=headers.get("Host", f"{config.HOST}:{config.PORT}"),
        default_scheme=headers.get("X-Forwarded-Proto", "https"),
    )


def handler(ctx, data: io.BytesIO = None, linker=None):
    """OCI Functions entrypoint."""
    linker = linker or get_linker()
    result = linker.dispatch(build_request(ctx, data))

    response_headers = dict(result.headers)
    response_headers["Content-Type"] = result.content_type

    # Imported lazily so the module can be introspected/tested without the fdk runtime.
    from fdk import response

    return response.Response(
        ctx,
        response_data=result.body,
        headers=response_headers,
        status_code=result.status,
    )
