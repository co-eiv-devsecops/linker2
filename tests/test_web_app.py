import tempfile
import unittest
from pathlib import Path

from database import SQLiteLinkRepository
from link_service import LinkService
from web import create_app


class WebAppTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "linker.db"
        self.repository = SQLiteLinkRepository(str(database_path))
        self.repository.initialize()
        self.service = LinkService(self.repository, id_generator=lambda: "abc123")
        self.app = create_app(
            config={"TESTING": True},
            repository=self.repository,
            link_service=self.service,
            flag_checker=lambda flag_name, environ=None: flag_name == "custom_alias",
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_index_renders_homepage(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Linker Python", response.data)

    def test_health_endpoint_returns_json(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok", "app": "linker-python"})

    def test_create_link_returns_location_header(self):
        response = self.client.post(
            "/link",
            data={"url": "https://example.com"},
            headers={"Host": "example.test", "X-Forwarded-Proto": "https"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["Location"], "https://example.test/r/abc123")
        self.assertEqual(self.repository.find_url("abc123"), "https://example.com")

    def test_create_link_uses_custom_alias_when_enabled(self):
        response = self.client.post(
            "/link",
            data={"url": "https://example.com", "alias": "mi_alias"},
            headers={"Host": "example.test"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.headers["Location"], "http://example.test/r/mi_alias")
        self.assertEqual(self.repository.find_url("mi_alias"), "https://example.com")

    def test_redirects_to_original_url(self):
        self.repository.save_link("abc123", "https://example.com")

        response = self.client.get("/r/abc123")

        self.assertEqual(response.status_code, 301)
        self.assertEqual(response.headers["Location"], "https://example.com")

    def test_redirect_returns_not_found_for_missing_link(self):
        response = self.client.get("/r/missing")

        self.assertEqual(response.status_code, 404)

    def test_create_link_returns_internal_error_when_service_fails(self):
        failing_app = create_app(
            config={"TESTING": True},
            repository=self.repository,
            link_service=type("FailingService", (), {"create_short_link": staticmethod(lambda url, custom_id=None: (_ for _ in ()).throw(RuntimeError("boom"))), "find_url": staticmethod(lambda short_id: None)})(),
            flag_checker=lambda flag_name, environ=None: False,
        )

        response = failing_app.test_client().post("/link", data={"url": "https://example.com"})

        self.assertEqual(response.status_code, 500)

    def test_redirect_returns_internal_error_when_service_fails(self):
        failing_app = create_app(
            config={"TESTING": True},
            repository=self.repository,
            link_service=type("FailingService", (), {"create_short_link": staticmethod(lambda url, custom_id=None: "abc123"), "find_url": staticmethod(lambda short_id: (_ for _ in ()).throw(RuntimeError("boom")))})(),
            flag_checker=lambda flag_name, environ=None: False,
        )

        response = failing_app.test_client().get("/abc123")

        self.assertEqual(response.status_code, 500)

    def test_rejects_invalid_url(self):
        response = self.client.post("/link", data={"url": "not-a-url"})

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Invalid or missing URL", response.data)


if __name__ == "__main__":
    unittest.main()
