import tempfile

import unittest

from pathlib import Path
 
from database import SQLiteLinkRepository

from link_service import LinkService

from web import create_app
 
 
class HealthCheckTest(unittest.TestCase):

    def setUp(self):

        self.temp_dir = tempfile.TemporaryDirectory()

        database_path = Path(self.temp_dir.name) / "linker.db"
 
        self.repository = SQLiteLinkRepository(str(database_path))

        self.repository.initialize()
 
        self.service = LinkService(

            self.repository,

            id_generator=lambda: "abc123"

        )
 
        self.app = create_app(

            config={

                "TESTING": True,

                "DB_ENGINE": "sqlite"

            },

            repository=self.repository,

            link_service=self.service,

            flag_checker=lambda flag_name, environ=None: False,

        )
 
        self.client = self.app.test_client()
 
    def tearDown(self):

        self.temp_dir.cleanup()
 
    def test_healthz_executes_database_check(self):

        response = self.client.get("/healthz")
 
        self.assertEqual(response.status_code, 200)

        self.assertEqual(

            response.get_json(),

            {

                "status": "ok",

                "database": "ok",

                "app": "linker-python"

            }

        )
 
    def test_healthz_returns_503_when_database_fails(self):

        class FailingRepository:

            def health_check(self):

                raise RuntimeError("database unavailable")
 
        app = create_app(

            config={

                "TESTING": True,

                "DB_ENGINE": "sqlite"

            },

            repository=FailingRepository(),

            link_service=self.service,

            flag_checker=lambda flag_name, environ=None: False,

        )
 
        response = app.test_client().get("/healthz")
 
        self.assertEqual(response.status_code, 503)

        self.assertEqual(response.get_json()["database"], "error")
 
 
if __name__ == "__main__":

    unittest.main()
 