import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aws_lambda


class AwsLambdaAdapterTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "lambda.db")

        self.env_patch = patch.dict(
            os.environ,
            {
                "DB_ENGINE": "sqlite",
                "LINKER_DB": self.db_path,
                "OTEL_TRACES_ENABLED": "false",
                "OTEL_METRICS_ENABLED": "false",
                "LINKER_ENABLE_ADVANCED_OPERATIONS": "true",
            },
            clear=False,
        )
        self.env_patch.start()

        aws_lambda._repository = None
        aws_lambda._service = None
        aws_lambda._app = None

    def tearDown(self):
        self.env_patch.stop()
        self.temp_dir.cleanup()

        aws_lambda._repository = None
        aws_lambda._service = None
        aws_lambda._app = None

    def test_health_endpoint(self):
        response = aws_lambda.handler(
            {
                "rawPath": "/health",
                "requestContext": {
                    "http": {
                        "method": "GET",
                    }
                },
                "headers": {},
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)
        self.assertIn("linker-python", response["body"])

    def test_healthz_endpoint(self):
        response = aws_lambda.handler(
            {
                "rawPath": "/healthz",
                "requestContext": {
                    "http": {
                        "method": "GET",
                    }
                },
                "headers": {},
            },
            None,
        )

        self.assertEqual(response["statusCode"], 200)

    def test_create_and_redirect_link(self):
        create_response = aws_lambda.handler(
            {
                "rawPath": "/link",
                "requestContext": {
                    "http": {
                        "method": "POST",
                    }
                },
                "headers": {
                    "host": "lambda.local",
                    "x-forwarded-proto": "https",
                },
                "body": "url=https://example.com",
                "isBase64Encoded": False,
            },
            None,
        )

        self.assertIn(create_response["statusCode"], [200, 201, 302])

    def test_unknown_route_returns_404(self):
        response = aws_lambda.handler(
            {
                "rawPath": "/unknown",
                "requestContext": {
                    "http": {
                        "method": "GET",
                    }
                },
                "headers": {},
            },
            None,
        )

        self.assertEqual(response["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()