from http.server import HTTPServer

from config import HOST, PORT
from database import init_database
from web import LinkerHandler


def run():
    init_database()
    server = HTTPServer((HOST, PORT), LinkerHandler)
    print(f"Linker Python running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    run()
