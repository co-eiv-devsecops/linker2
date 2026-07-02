import secrets
from urllib.parse import urlparse


def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def generate_id():
    return secrets.token_urlsafe(4).replace("-", "_")


def create_short_link(connection, url, id_generator=generate_id):
    clean_url = url.strip()
    if not is_valid_url(clean_url):
        raise ValueError("Invalid or missing URL")

    while True:
        short_id = id_generator()
        exists = connection.execute(
            "SELECT 1 FROM short_url WHERE id = ?",
            (short_id,),
        ).fetchone()
        if not exists:
            break

    connection.execute(
        "INSERT INTO short_url (id, url) VALUES (?, ?)",
        (short_id, clean_url),
    )
    return short_id


def find_url(connection, short_id):
    row = connection.execute(
        "SELECT url FROM short_url WHERE id = ?",
        (short_id,),
    ).fetchone()
    if row is None:
        return None
    return row["url"]
