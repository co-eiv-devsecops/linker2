import secrets
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

CUSTOM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


def is_valid_url(url):
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def is_valid_custom_id(short_id):
    return bool(CUSTOM_ID_PATTERN.fullmatch(short_id or ""))


def generate_id():
    return secrets.token_urlsafe(4).replace("-", "_")


class _ConnectionRepository:
    def __init__(self, connection):
        self.connection = connection

    def link_exists(self, short_id):
        return (
            self.connection.execute(
                "SELECT 1 FROM short_url WHERE id = ?",
                (short_id,),
            ).fetchone()
            is not None
        )

    def save_link(self, short_id, url):
        self.connection.execute(
            "INSERT INTO short_url (id, url) VALUES (?, ?)",
            (short_id, url),
        )

    def find_url(self, short_id):
        row = self.connection.execute(
            "SELECT url FROM short_url WHERE id = ?",
            (short_id,),
        ).fetchone()
        if row is None:
            return None
        return row["url"]


class LinkService:
    def __init__(self, repository, id_generator=generate_id):
        self.repository = repository
        self.id_generator = id_generator

    def create_short_link(self, url, custom_id=None):
        clean_url = (url or "").strip()

        logger.debug("Starting the process of creating a short link for the URL: %s", clean_url)
        
        if not is_valid_url(clean_url):
            logger.warning("Attempt to register a URL with an invalid or empty format: %s", clean_url)
            logger.error("The provided URL does not meet the minimum HTTP/HTTPS requirements.")
            raise ValueError("Invalid or missing URL")

        if custom_id:
            short_id = custom_id.strip()
            if not is_valid_custom_id(short_id):
                logger.error("Business error: The custom alias '%s' does not match the allowed regex pattern.", short_id)
                raise ValueError("Invalid custom alias")
            if self.repository.link_exists(short_id):
                logger.warning("The requested custom alias is already in use: %s", short_id)
                raise ValueError("Custom alias already exists")
        else:
            logger.debug("Generating a unique random identifier and starting the duplicate verification loop")
            while True:
                short_id = self.id_generator()
                if not self.repository.link_exists(short_id):
                    break
        
        try:
            self.repository.save_link(short_id, clean_url)
            logger.info("Successful storage mapping completed: %s -> %s", short_id, clean_url)
            return short_id
        except Exception as e:
            logger.critical("Catastrophic failure while attempting to write to the database repository: %s", str(e))
            raise

    def find_url(self, short_id):
        try:
            return self.repository.find_url(short_id)
        except Exception as e:
            logger.critical("Critical system error while querying short_id=%s: %s", short_id, str(e))
            raise

def create_short_link(connection, url, id_generator=generate_id, custom_id=None):
    service = LinkService(_ConnectionRepository(connection), id_generator=id_generator)
    return service.create_short_link(url, custom_id=custom_id)


def link_exists(connection, short_id):
    return _ConnectionRepository(connection).link_exists(short_id)


def find_url(connection, short_id):
    return _ConnectionRepository(connection).find_url(short_id)
