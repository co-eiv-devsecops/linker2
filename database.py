import sqlite3

from config import DATABASE


def get_connection(database=DATABASE):
    connection = sqlite3.connect(database)
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
