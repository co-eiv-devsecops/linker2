import sqlite3
import unittest

from link_service import create_short_link, find_url, is_valid_url


def memory_connection():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """
        CREATE TABLE short_url (
            id TEXT PRIMARY KEY,
            url TEXT NOT NULL
        )
        """
    )
    return connection


class LinkServiceTest(unittest.TestCase):
    def test_validates_only_http_urls(self):
        self.assertTrue(is_valid_url("https://example.com/path"))
        self.assertTrue(is_valid_url("http://example.com"))
        self.assertFalse(is_valid_url("ftp://example.com"))
        self.assertFalse(is_valid_url("example.com"))
        self.assertFalse(is_valid_url(""))

    def test_creates_short_link_with_injected_id_generator(self):
        with memory_connection() as connection:
            short_id = create_short_link(connection, " https://example.com ", lambda: "abc123")

            self.assertEqual(short_id, "abc123")
            self.assertEqual(find_url(connection, "abc123"), "https://example.com")

    def test_retries_when_generated_id_already_exists(self):
        ids = iter(["taken", "free"])

        with memory_connection() as connection:
            connection.execute(
                "INSERT INTO short_url (id, url) VALUES (?, ?)",
                ("taken", "https://old.example.com"),
            )

            short_id = create_short_link(connection, "https://new.example.com", lambda: next(ids))

            self.assertEqual(short_id, "free")
            self.assertEqual(find_url(connection, "free"), "https://new.example.com")

    def test_rejects_invalid_url(self):
        with memory_connection() as connection:
            with self.assertRaises(ValueError):
                create_short_link(connection, "not-a-url", lambda: "abc123")


if __name__ == "__main__":
    unittest.main()
