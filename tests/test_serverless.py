import io
import sys
import tempfile
import types
import unittest
from pathlib import Path

import serverless
from database import SQLiteLinkRepository
from link_service import LinkService
from linker_app import LinkerApp


class FakeCtx:
    def __init__(self, headers):
        self._headers = headers

    def Headers(self):
        return self._headers


class FakeResponse:
    """Stand-in for fdk.response.Response so we can assert on the outbound values."""

    def __init__(self, ctx, response_data=None, headers=None, status_code=None):
        self.ctx = ctx
        self.body = response_data
        self.headers = headers or {}
        self.status_code = status_code


def install_fake_fdk():
    fdk = types.ModuleType("fdk")
    response_mod = types.ModuleType("fdk.response")
    response_mod.Response = FakeResponse
    fdk.response = response_mod
    sys.modules["fdk"] = fdk
    sys.modules["fdk.response"] = response_mod


class BuildRequestTest(unittest.TestCase):
    def test_extracts_method_path_form_and_proxy_metadata(self):
        ctx = FakeCtx(
            {
                "Fn-Http-Method": "POST",
                "Fn-Http-Request-Url": "/link?x=1",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "acortar.example",
                "X-Forwarded-Proto": "https",
                "X-Forwarded-For": "198.51.100.9",
            }
        )
        data = io.BytesIO(b"url=https%3A%2F%2Fexample.com&alias=mi_alias")

        req = serverless.build_request(ctx, data)

        self.assertEqual(req.method, "POST")
        self.assertEqual(req.path, "/link")
        self.assertEqual(req.form["url"], "https://example.com")
        self.assertEqual(req.form["alias"], "mi_alias")
        self.assertEqual(req.remote_addr, "198.51.100.9")
        self.assertEqual(req.default_host, "acortar.example")
        self.assertEqual(req.default_scheme, "https")

    def test_defaults_when_headers_absent(self):
        req = serverless.build_request(FakeCtx({}), None)

        self.assertEqual(req.method, "GET")
        self.assertEqual(req.path, "/")
        self.assertEqual(req.form, {})

    def test_ignores_non_form_bodies(self):
        ctx = FakeCtx(
            {
                "Fn-Http-Method": "POST",
                "Fn-Http-Request-Url": "/link",
                "Content-Type": "application/json",
            }
        )

        req = serverless.build_request(ctx, io.BytesIO(b'{"url":"x"}'))

        self.assertEqual(req.form, {})


class HandlerTest(unittest.TestCase):
    def setUp(self):
        install_fake_fdk()
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "linker.db"
        self.repository = SQLiteLinkRepository(str(database_path))
        self.repository.initialize()
        self.service = LinkService(self.repository, id_generator=lambda: "abc123")
        self.linker = LinkerApp(
            service=self.service,
            repository=self.repository,
            flag_checker=lambda flag_name, environ=None: False,
        )

    def tearDown(self):
        self.temp_dir.cleanup()
        sys.modules.pop("fdk", None)
        sys.modules.pop("fdk.response", None)

    def _call(self, method, url, body=b"", content_type=None, host="acortar.example"):
        headers = {"Fn-Http-Method": method, "Fn-Http-Request-Url": url, "Host": host}
        if content_type:
            headers["Content-Type"] = content_type
        data = io.BytesIO(body) if body else None
        return serverless.handler(FakeCtx(headers), data, linker=self.linker)

    def test_health_returns_json(self):
        result = self._call("GET", "/health")

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers["Content-Type"], "application/json")

    def test_create_then_redirect(self):
        created = self._call(
            "POST",
            "/link",
            b"url=https%3A%2F%2Fexample.com",
            "application/x-www-form-urlencoded",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.headers["Location"], "https://acortar.example/r/abc123")
        self.assertEqual(self.repository.find_url("abc123"), "https://example.com")

        redirect = self._call("GET", "/r/abc123")
        self.assertEqual(redirect.status_code, 301)
        self.assertEqual(redirect.headers["Location"], "https://example.com")

    def test_invalid_url_returns_400(self):
        result = self._call(
            "POST", "/link", b"url=not-a-url", "application/x-www-form-urlencoded"
        )

        self.assertEqual(result.status_code, 400)

    def test_unknown_route_returns_404(self):
        result = self._call("GET", "/nope")

        self.assertEqual(result.status_code, 404)


if __name__ == "__main__":
    unittest.main()
