import tempfile
import unittest
from pathlib import Path

from database import SQLiteLinkRepository, init_database


class SQLiteLinkRepositoryTest(unittest.TestCase):
    def test_initializes_schema_and_persists_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "linker.db"
            repository = SQLiteLinkRepository(str(database_path))

            init_database(str(database_path))
            repository.save_link("abc123", "https://example.com")

            self.assertTrue(repository.link_exists("abc123"))
            self.assertEqual(repository.find_url("abc123"), "https://example.com")
            self.assertIsNone(repository.find_url("missing"))


if __name__ == "__main__":
    unittest.main()