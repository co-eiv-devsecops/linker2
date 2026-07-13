import json
import tempfile
import unittest
from pathlib import Path

from database import SQLiteLinkRepository
from link_service import LinkService
from linker_app import LinkerApp, LinkerRequest, LinkerResponse


def make_request(method="GET", path="/", form=None, headers=None, flag_context=None):
    return LinkerRequest(
        method=method,
        path=path,
        form=form or {},
        headers=headers or {},
        remote_addr="203.0.113.7",
        flag_context=flag_context or {},
    )


class LinkerAppTest(unittest.TestCase):
    """The controller is exercised directly, with no web framework involved."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "linker.db"
        self.repository = SQLiteLinkRepository(str(database_path))
        self.repository.initialize()
        self.service = LinkService(self.repository, id_generator=lambda: "abc123")
        self.app = LinkerApp(
            service=self.service,
            repository=self.repository,
            flag_checker=lambda flag_name, environ=None: flag_name == "custom_alias",
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_index_returns_html(self):
        result = self.app.index(make_request(path="/"))

        self.assertEqual(result.status, 200)
        self.assertIn("text/html", result.content_type)
        self.assertIn("Linker Python", result.body)

    def test_health_returns_json_payload(self):
        result = self.app.health(make_request(path="/health"))

        self.assertEqual(result.status, 200)
        self.assertEqual(result.content_type, "application/json")
        self.assertEqual(json.loads(result.body), {"status": "ok", "app": "linker-python"})

    def test_healthz_runs_database_check(self):
        result = self.app.healthz(make_request(path="/healthz"))

        self.assertEqual(result.status, 200)
        self.assertEqual(json.loads(result.body)["database"], "ok")

    def test_healthz_returns_503_when_database_fails(self):
        class FailingRepository:
            db_system = "sqlite"

            def health_check(self):
                raise RuntimeError("database unavailable")

        app = LinkerApp(
            service=self.service,
            repository=FailingRepository(),
            flag_checker=lambda flag_name, environ=None: False,
        )

        result = app.healthz(make_request(path="/healthz"))

        self.assertEqual(result.status, 503)
        self.assertEqual(json.loads(result.body)["database"], "error")

    def test_create_link_builds_location_from_proxy_headers(self):
        result = self.app.create_link(
            make_request(
                method="POST",
                path="/link",
                form={"url": "https://example.com"},
                headers={"Host": "example.test", "X-Forwarded-Proto": "https"},
            )
        )

        self.assertEqual(result.status, 201)
        self.assertEqual(result.headers["Location"], "https://example.test/r/abc123")
        self.assertEqual(self.repository.find_url("abc123"), "https://example.com")

    def test_create_link_defaults_scheme_to_http(self):
        result = self.app.create_link(
            make_request(
                method="POST",
                path="/link",
                form={"url": "https://example.com", "alias": "mi_alias"},
                headers={"Host": "example.test"},
            )
        )

        self.assertEqual(result.status, 201)
        self.assertEqual(result.headers["Location"], "http://example.test/r/mi_alias")
        self.assertEqual(self.repository.find_url("mi_alias"), "https://example.com")

    def test_create_link_ignores_alias_when_flag_disabled(self):
        app = LinkerApp(
            service=self.service,
            repository=self.repository,
            flag_checker=lambda flag_name, environ=None: False,
        )

        result = app.create_link(
            make_request(
                method="POST",
                path="/link",
                form={"url": "https://example.com", "alias": "mi_alias"},
                headers={"Host": "example.test"},
            )
        )

        self.assertEqual(result.status, 201)
        self.assertEqual(result.headers["Location"], "http://example.test/r/abc123")

    def test_create_link_rejects_invalid_url(self):
        result = self.app.create_link(
            make_request(method="POST", path="/link", form={"url": "not-a-url"})
        )

        self.assertEqual(result.status, 400)
        self.assertIn("Invalid or missing URL", result.body)

    def test_create_link_returns_500_when_service_fails(self):
        class FailingService:
            def create_short_link(self, url, custom_id=None):
                raise RuntimeError("boom")

            def find_url(self, short_id):
                return None

        app = LinkerApp(
            service=FailingService(),
            repository=self.repository,
            flag_checker=lambda flag_name, environ=None: False,
        )

        result = app.create_link(
            make_request(method="POST", path="/link", form={"url": "https://example.com"})
        )

        self.assertEqual(result.status, 500)

    def test_redirect_returns_301_for_known_id(self):
        self.repository.save_link("abc123", "https://example.com")

        result = self.app.redirect("abc123", make_request(path="/r/abc123"))

        self.assertEqual(result.status, 301)
        self.assertEqual(result.headers["Location"], "https://example.com")

    def test_redirect_returns_404_for_unknown_id(self):
        result = self.app.redirect("missing", make_request(path="/r/missing"))

        self.assertEqual(result.status, 404)

    def test_redirect_rejects_reserved_path(self):
        result = self.app.redirect("health", make_request(path="/r/health"))

        self.assertEqual(result.status, 404)

    def test_redirect_returns_500_when_service_fails(self):
        class FailingService:
            def create_short_link(self, url, custom_id=None):
                return "abc123"

            def find_url(self, short_id):
                raise RuntimeError("boom")

        app = LinkerApp(
            service=FailingService(),
            repository=self.repository,
            flag_checker=lambda flag_name, environ=None: False,
        )

        result = app.redirect("abc123", make_request(path="/r/abc123"))

        self.assertEqual(result.status, 500)


class DispatchTest(unittest.TestCase):
    """The single-entry dispatch used by non-routing hosts (serverless)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "linker.db"
        self.repository = SQLiteLinkRepository(str(database_path))
        self.repository.initialize()
        self.service = LinkService(self.repository, id_generator=lambda: "abc123")
        self.app = LinkerApp(
            service=self.service,
            repository=self.repository,
            flag_checker=lambda flag_name, environ=None: False,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dispatch_routes_index(self):
        result = self.app.dispatch(make_request(method="GET", path="/"))
        self.assertEqual(result.status, 200)
        self.assertIn("Linker Python", result.body)

    def test_dispatch_routes_health(self):
        result = self.app.dispatch(make_request(method="GET", path="/health"))
        self.assertEqual(result.status, 200)

    def test_dispatch_normalizes_trailing_slash_for_healthz(self):
        result = self.app.dispatch(make_request(method="GET", path="/healthz/"))
        self.assertEqual(result.status, 200)
        self.assertEqual(json.loads(result.body)["database"], "ok")

    def test_dispatch_routes_create_and_redirect(self):
        create = self.app.dispatch(
            make_request(
                method="POST",
                path="/link",
                form={"url": "https://example.com"},
                headers={"Host": "acortar.test"},
            )
        )
        self.assertEqual(create.status, 201)
        location = create.headers["Location"]
        self.assertTrue(location.endswith("/r/abc123"))

        redirect = self.app.dispatch(make_request(method="GET", path="/r/abc123"))
        self.assertEqual(redirect.status, 301)
        self.assertEqual(redirect.headers["Location"], "https://example.com")

    def test_dispatch_returns_404_for_unknown_route(self):
        result = self.app.dispatch(make_request(method="GET", path="/totally/unknown"))
        self.assertEqual(result.status, 404)

    def test_dispatch_returns_404_for_bare_short_id(self):
        # Short links are only served under the /r/ prefix.
        self.repository.save_link("abc123", "https://example.com")
        result = self.app.dispatch(make_request(method="GET", path="/abc123"))
        self.assertEqual(result.status, 404)


if __name__ == "__main__":
    unittest.main()
