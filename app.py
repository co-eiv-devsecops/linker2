import logging

from config import LOG_LEVEL
from web import run

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    run()
