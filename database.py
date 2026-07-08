import logging
import sqlite3
from contextlib import contextmanager

from config import DATABASE

logger = logging.getLogger(__name__)


class SQLiteLinkRepository:
    def __init__(self, database=DATABASE, connection_factory=sqlite3.connect):
        self.database = database
        self.connection_factory = connection_factory

    def connect(self):
        try:
            connection = self.connection_factory(self.database)
        except sqlite3.Error:
            logger.exception("Failed to connect to database at %s", self.database)
            raise

        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def connection_scope(self):
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self):
        with self.connection_scope() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS short_url (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL
                )
                """
            )
            connection.commit()
        logger.info("Database initialized at %s", self.database)

    def link_exists(self, short_id):
        with self.connection_scope() as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM short_url WHERE id = ?",
                    (short_id,),
                ).fetchone()
                is not None
            )

    def save_link(self, short_id, url):
        with self.connection_scope() as connection:
            connection.execute(
                "INSERT INTO short_url (id, url) VALUES (?, ?)",
                (short_id, url),
            )
            connection.commit()

    def find_url(self, short_id):
        with self.connection_scope() as connection:
            row = connection.execute(
                "SELECT url FROM short_url WHERE id = ?",
                (short_id,),
            ).fetchone()

        if row is None:
            return None

        return row["url"]
    
    def health_check(self):
        with self.connection_scope() as connection:
            connection.execute("SELECT 1").fetchone()


def get_connection(database=DATABASE):
    return SQLiteLinkRepository(database).connect()


def init_database(database=DATABASE):
    SQLiteLinkRepository(database).initialize()
