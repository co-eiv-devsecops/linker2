import base64
import os
from urllib.parse import parse_qs

from database import create_repository
from feature_flags import is_enabled
from link_service import LinkService
from linker_app import LinkerApp, LinkerRequest


_repository = None
_service = None
_app = None


def get_app():
    global _repository, _service, _app

    if _app is None:
        _repository = create_repository()
        _repository.initialize()
        _service = LinkService(_repository)
        _app = LinkerApp(
            service=_service,
            repository=_repository,
            flag_checker=is_enabled,
        )

    return _app


def build_request(event):
    headers = event.get("headers") or {}

    request_context = event.get("requestContext") or {}
    http_context = request_context.get("http") or {}

    method = http_context.get("method") or event.get("httpMethod") or "GET"
    path = event.get("rawPath") or event.get("path") or "/"

    body = event.get("body") or ""

    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode("utf-8")

    form = {}
    if body:
        parsed = parse_qs(body)
        form = {key: values[0] for key, values in parsed.items()}

    return LinkerRequest(
        method=method,
        path=path,
        form=form,
        headers=headers,
        remote_addr=headers.get("x-forwarded-for", "lambda"),
        flag_context=os.environ,
        default_host=headers.get("host", "lambda.local"),
        default_scheme=headers.get("x-forwarded-proto", "https"),
    )


def to_lambda_response(result):
    headers = {
        "Content-Type": result.content_type,
        **result.headers,
    }

    return {
        "statusCode": result.status,
        "headers": headers,
        "body": result.body,
    }


def handler(event, context):
    app = get_app()
    req = build_request(event)

    result = app.dispatch(req)

    return to_lambda_response(result)