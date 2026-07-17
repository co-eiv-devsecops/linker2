import tempfile
import unittest
from pathlib import Path

from database import SQLiteLinkRepository
from link_service import LinkService
from linker_app import LinkerApp, LinkerRequest
from web import create_app


def make_request(method="GET", path="/r/abc123"):
    return LinkerRequest(method=method, path=path, flag_context={})


def enabled_flags(flag_name, environ=None):
    return flag_name in {"custom_alias", "advanced_operations"}


def disabled_flags(flag_name, environ=None):
    return False


class AdvancedOperationsControllerTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "linker.db"
        self.repository = SQLiteLinkRepository(str(database_path))
        self.repository.initialize()
        self.service = LinkService(self.repository, id_generator=lambda: "abc123")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_metadata_returns_404_when_flag_is_disabled(self):
        app = LinkerApp(self.service, self.repository, disabled_flags)
        self.repository.save_link("abc123", "https://example.com")

        result = app.metadata("abc123", make_request(method="HEAD"))

        self.assertEqual(result.status, 404)

    def test_metadata_returns_original_url_when_flag_is_enabled(self):
        app = LinkerApp(self.service, self.repository, enabled_flags)
        self.repository.save_link("abc123", "https://example.com")

        result = app.metadata("abc123", make_request(method="HEAD"))

        self.assertEqual(result.status, 200)
        self.assertEqual(result.body, "https://example.com")
        self.assertEqual(result.headers["X-Linker-Original-Url"], "https://example.com")

    def test_delete_returns_404_when_flag_is_disabled(self):
        app = LinkerApp(self.service, self.repository, disabled_flags)
        self.repository.save_link("abc123", "https://example.com")

        result = app.delete("abc123", make_request(method="DELETE"))

        self.assertEqual(result.status, 404)
        self.assertEqual(self.repository.find_url("abc123"), "https://example.com")

    def test_delete_removes_short_link_when_flag_is_enabled(self):
        app = LinkerApp(self.service, self.repository, enabled_flags)
        self.repository.save_link("abc123", "https://example.com")

        result = app.delete("abc123", make_request(method="DELETE"))

        self.assertEqual(result.status, 200)
        self.assertIsNone(self.repository.find_url("abc123"))

    def test_delete_returns_404_when_link_does_not_exist(self):
        app = LinkerApp(self.service, self.repository, enabled_flags)

        result = app.delete("missing", make_request(method="DELETE", path="/r/missing"))

        self.assertEqual(result.status, 404)


class AdvancedOperationsWebTest(unittest.TestCase):
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
            flag_checker=enabled_flags,
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_head_returns_metadata_header(self):
        self.repository.save_link("abc123", "https://example.com")

        response = self.client.open("/r/abc123", method="HEAD")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Linker-Original-Url"], "https://example.com")

    def test_delete_removes_link(self):
        self.repository.save_link("abc123", "https://example.com")

        response = self.client.delete("/r/abc123")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.repository.find_url("abc123"))


if __name__ == "__main__":
    unittest.main()