import logging
from http.server import HTTPServer

from config import HOST, LOG_LEVEL, PORT
from database import init_database
from web import LinkerHandler

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def run():
    init_database()
    server = HTTPServer((HOST, PORT), LinkerHandler)
    logger.info("Linker Python running on http://%s:%s", HOST, PORT)
    server.serve_forever()


if __name__ == "__main__":
    run()
