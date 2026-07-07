import secrets
import re
import logging
import time
from urllib.parse import urlparse
from opentelemetry import metrics

logger = logging.getLogger(__name__)

CUSTOM_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")


meter = metrics.get_meter(__name__)

# Counters
links_created_counter = meter.create_counter(
    "links_created_total",
    description="Total number of successfully created short links"
)
links_failed_counter = meter.create_counter(
    "links_failed_total",
    description="Total number of failed attempts to create a short link"
)

# Histograms
link_creation_duration = meter.create_histogram(
    "link_creation_duration_seconds",
    description="Total processing time for link creation"
)
url_length_histogram = meter.create_histogram(
    "original_url_length_characters",
    description="Distribution of character counts in original URLs"
)

# Observable Gauges 
service_start_time = time.time()
last_creation_timestamp = 0

def get_uptime_callback(options):
    yield metrics.Observation(time.time() - service_start_time)

def get_last_link_timestamp_callback(options):
    yield metrics.Observation(last_creation_timestamp)

uptime_gauge = meter.create_observable_gauge(
    "service_uptime_seconds",
    callbacks=[get_uptime_callback],
    description="Elapsed time in seconds since the service module started"
)
last_link_gauge = meter.create_observable_gauge(
    "last_link_created_timestamp",
    callbacks=[get_last_link_timestamp_callback],
    description="Epoch timestamp of the last time a link was created"
)


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
        global last_creation_timestamp
        start_process_time = time.time()

        clean_url = (url or "").strip()
        url_length_histogram.record(len(clean_url))

        logger.debug("Starting the process of creating a short link for the URL: %s", clean_url)
        
        if not is_valid_url(clean_url):
            logger.warning("Attempt to register a URL with an invalid or empty format: %s", clean_url)
            logger.error("The provided URL does not meet the minimum HTTP/HTTPS requirements.")
            links_failed_counter.add(1, {"reason": "invalid_url"})
            raise ValueError("Invalid or missing URL")

        if custom_id:
            short_id = custom_id.strip()
            if not is_valid_custom_id(short_id):
                logger.error("Business error: The custom alias '%s' does not match the allowed regex pattern.", short_id)
                links_failed_counter.add(1, {"reason": "invalid_alias_format"})
                raise ValueError("Invalid custom alias")
            if self.repository.link_exists(short_id):
                logger.warning("The requested custom alias is already in use: %s", short_id)
                links_failed_counter.add(1, {"reason": "alias_conflict"})
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
            links_created_counter.add(1, {"type": "custom" if custom_id else "auto"})
            last_creation_timestamp = time.time() 
            link_creation_duration.record(time.time() - start_process_time) 
            return short_id
        except Exception as e:
            logger.critical("Catastrophic failure while attempting to write to the database repository: %s", str(e))
            links_failed_counter.add(1, {"reason": "database_error"})
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
