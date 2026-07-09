"""Intentionally insecure static-analysis fixtures.

This module is never imported or executed by the Linker application. It exists
only to exercise security tooling in a temporary pull request.
"""

import sqlite3
import subprocess


def unsafe_user_lookup(connection: sqlite3.Connection, username: str):
    """Deliberate SQL injection fixture."""
    query = f"SELECT id FROM users WHERE username = '{username}'"
    return connection.execute(query).fetchone()


def unsafe_ping(host: str):
    """Deliberate command injection fixture."""
    return subprocess.run(
        f"ping -c 1 {host}",
        shell=True,
        check=False,
        capture_output=True,
    )


def unsafe_file_read(filename: str):
    """Deliberate path traversal fixture."""
    with open(f"/tmp/uploads/{filename}", encoding="utf-8") as file:
        return file.read()
