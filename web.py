import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from config import PORT
from database import get_connection
from feature_flags import is_enabled
from link_service import create_short_link, find_url
from views import render_index

logger = logging.getLogger(__name__)


class LinkerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/":
            self.send_html(render_index())
            return

        if path == "/health":
            self.send_json({"status": "ok", "app": "linker-python"})
            return

        short_id = path.strip("/")
        if not short_id or "/" in short_id:
            self.send_error(404, "Not Found")
            return

        try:
            with get_connection() as connection:
                url = find_url(connection, short_id)
        except Exception:
            logger.exception("Failed to resolve short_id=%s", short_id)
            self.send_error(500, "Internal Server Error")
            return

        if url is None:
            logger.warning("Short URL not found: short_id=%s client=%s", short_id, self.client_address[0])
            self.send_error(404, "Short URL not found")
            return

        logger.info("Redirect short_id=%s -> %s client=%s", short_id, url, self.client_address[0])
        self.send_response(301)
        self.send_header("Location", url)
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/link":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8")
        params = parse_qs(body)
        url = params.get("url", [""])[0]
        custom_id = params.get("alias", [""])[0] if is_enabled("custom_alias") else None

        try:
            with get_connection() as connection:
                short_id = create_short_link(connection, url, custom_id=custom_id)
        except ValueError as error:
            logger.warning("Rejected invalid URL from client=%s: %s", self.client_address[0], error)
            self.send_text(str(error), status=400)
            return
        except Exception:
            logger.exception("Failed to create short link for url=%s", url)
            self.send_error(500, "Internal Server Error")
            return

        logger.info("Created short_id=%s -> %s client=%s", short_id, url, self.client_address[0])
        short_url = self.public_base_url() + "/" + short_id
        self.send_response(201)
        self.send_header("Location", short_url)
        self.end_headers()

    def public_base_url(self):
        host = self.headers.get("Host", f"localhost:{PORT}")
        proto = self.headers.get("X-Forwarded-Proto", "http")
        return f"{proto}://{host}"

    def send_html(self, content, status=200):
        self.send_content(content, "text/html; charset=utf-8", status)

    def send_json(self, data, status=200):
        self.send_content(json.dumps(data), "application/json; charset=utf-8", status)

    def send_text(self, content, status=200):
        self.send_content(content, "text/plain; charset=utf-8", status)

    def send_content(self, content, content_type, status):
        encoded = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):
        logger.info("%s - - %s", self.address_string(), format % args)
