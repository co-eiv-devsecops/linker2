import logging
import os

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.INFO)

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()
DATABASE = os.getenv("LINKER_DB", os.getenv("SQLITE_DATABASE", "linker.db"))

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "linker_db")
MYSQL_USER = os.getenv("MYSQL_USER", "linker_user")
MYSQL_PWD = os.getenv("MYSQL_PWD", "")

OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "linker-python")
OTEL_TRACES_ENABLED = os.getenv("OTEL_TRACES_ENABLED", "true").lower() == "true"
OTEL_METRICS_ENABLED = os.getenv("OTEL_METRICS_ENABLED", "true").lower() == "true"
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
OTEL_EXPORTER_OTLP_HEADERS = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")
