import logging
import sqlite3
from contextlib import contextmanager
from abc import ABC, abstractmethod

from config import (
    DATABASE,
    DB_ENGINE,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_PWD,
    MYSQL_USER,
)

logger = logging.getLogger(__name__)


class LinkRepository(ABC):
    @abstractmethod
    def initialize(self):
        raise NotImplementedError

    @abstractmethod
    def link_exists(self, short_id):
        raise NotImplementedError

    @abstractmethod
    def save_link(self, short_id, url):
        raise NotImplementedError

    @abstractmethod
    def find_url(self, short_id):
        raise NotImplementedError

    @abstractmethod
    def health_check(self):
        raise NotImplementedError


class SQLiteLinkRepository(LinkRepository):
    def __init__(self, database=DATABASE, connection_factory=sqlite3.connect):
        self.database = database
        self.connection_factory = connection_factory
        self.db_system = "sqlite"

    def connect(self):
        try:
            connection = self.connection_factory(self.database)
        except sqlite3.Error:
            logger.exception("Failed to connect to SQLite database at %s", self.database)
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
        logger.info("SQLite database initialized at %s", self.database)

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


class MySQLLinkRepository(LinkRepository):
    def __init__(
        self,
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DATABASE,
        user=MYSQL_USER,
        password=MYSQL_PWD,
        connection_factory=None,
    ):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.db_system = "mysql"
        self.connection_factory = connection_factory

    def connect(self):
        try:
            if self.connection_factory is not None:
                return self.connection_factory()

            import mysql.connector

            return mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
                connection_timeout=5,
            )
        except Exception:
            logger.exception(
                "Failed to connect to MySQL database host=%s port=%s database=%s user=%s",
                self.host,
                self.port,
                self.database,
                self.user,
            )
            raise

    @contextmanager
    def connection_scope(self):
        connection = self.connect()
        try:
            yield connection
        finally:
            connection.close()

    def initialize(self):
        with self.connection_scope() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS short_url (
                    id VARCHAR(64) PRIMARY KEY,
                    url TEXT NOT NULL
                )
                """
            )
            connection.commit()
            cursor.close()
        logger.info("MySQL database initialized at %s:%s/%s", self.host, self.port, self.database)

    def link_exists(self, short_id):
        with self.connection_scope() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1 FROM short_url WHERE id = %s", (short_id,))
            row = cursor.fetchone()
            cursor.close()
            return row is not None

    def save_link(self, short_id, url):
        with self.connection_scope() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "INSERT INTO short_url (id, url) VALUES (%s, %s)",
                (short_id, url),
            )
            connection.commit()
            cursor.close()

    def find_url(self, short_id):
        with self.connection_scope() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT url FROM short_url WHERE id = %s", (short_id,))
            row = cursor.fetchone()
            cursor.close()

        if row is None:
            return None

        return row[0]

    def health_check(self):
        with self.connection_scope() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()


def create_repository():
    if DB_ENGINE == "mysql":
        return MySQLLinkRepository()

    return SQLiteLinkRepository(DATABASE)


def get_connection(database=DATABASE):
    return SQLiteLinkRepository(database).connect()


def init_database(database=DATABASE):
    SQLiteLinkRepository(database).initialize()
