import os


DATABASE = os.environ.get("LINKER_DB", "linker.db")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
