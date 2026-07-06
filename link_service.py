import secrets
import re
from urllib.parse import urlparse


CUSTOM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_valid_custom_id(short_id):
    return bool(CUSTOM_ID_PATTERN.fullmatch(short_id or ""))


def generate_id():
    return secrets.token_urlsafe(4).replace("-", "_")


def create_short_link(connection, url, id_generator=generate_id, custom_id=None):
    clean_url = url.strip()
    if not is_valid_url(clean_url):
        raise ValueError("Invalid or missing URL")

    if custom_id:
        short_id = custom_id.strip()
        if not is_valid_custom_id(short_id):
            raise ValueError("Invalid custom alias")
        if link_exists(connection, short_id):
            raise ValueError("Custom alias already exists")
    else:
        while True:
            short_id = id_generator()
            if not link_exists(connection, short_id):
                break

    connection.execute(
        "INSERT INTO short_url (id, url) VALUES (?, ?)",
        (short_id, clean_url),
    )
    return short_id


def link_exists(connection, short_id):
    return (
        connection.execute(
            "SELECT 1 FROM short_url WHERE id = ?",
            (short_id,),
        ).fetchone()
        is not None
    )


def find_url(connection, short_id):
    row = connection.execute(
        "SELECT url FROM short_url WHERE id = ?",
        (short_id,),
    ).fetchone()
    if row is None:
        return None
    return row["url"]
