import os

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if load_dotenv is not None:
    load_dotenv()


DATABASE = os.environ.get("LINKER_DB", "linker.db")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
