import logging
import sqlite3

from config import DATABASE

logger = logging.getLogger(__name__)


def get_connection(database=DATABASE):
    try:
        connection = sqlite3.connect(database)
    except sqlite3.Error:
        logger.exception("Failed to connect to database at %s", database)
        raise
    connection.row_factory = sqlite3.Row
    return connection


def init_database(database=DATABASE):
    with get_connection(database) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS short_url (
                id TEXT PRIMARY KEY,
                url TEXT NOT NULL
            )
            """
        )
    logger.info("Database initialized at %s", database)
