import logging
from flask import Flask, abort, jsonify, make_response, render_template, request

from config import DATABASE, HOST, LOG_LEVEL, PORT
from database import SQLiteLinkRepository
from feature_flags import is_enabled
from link_service import LinkService

logger = logging.getLogger(__name__)


def configure_logging(app):
    logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.handlers = logger.handlers
    app.logger.setLevel(app.config["LOG_LEVEL"])
    app.logger.propagate = False


def public_base_url():
    host = request.headers.get("Host", request.host or f"{HOST}:{PORT}")
    proto = request.headers.get("X-Forwarded-Proto", request.scheme or "http")
    return f"{proto}://{host}"


def create_app(config=None, repository=None, link_service=None, flag_checker=is_enabled):
    app = Flask(__name__, template_folder="views")
    app.config.from_mapping(
        DATABASE=DATABASE,
        HOST=HOST,
        PORT=PORT,
        LOG_LEVEL=LOG_LEVEL,
    )
    if config:
        app.config.update(config)

    configure_logging(app)

    repository = repository or SQLiteLinkRepository(app.config["DATABASE"])
    if link_service is None:
        repository.initialize()
        link_service = LinkService(repository)

    app.extensions["linker_repository"] = repository
    app.extensions["linker_service"] = link_service
    app.extensions["linker_flag_checker"] = flag_checker

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "app": "linker-python"})

    @app.post("/link")
    def create_link():
        service = app.extensions["linker_service"]
        flag_checker = app.extensions["linker_flag_checker"]
        url = request.form.get("url", "")
        custom_id = request.form.get("alias", "") if flag_checker("custom_alias", request.environ) else None

        try:
            short_id = service.create_short_link(url, custom_id=custom_id)
        except ValueError as error:
            logger.warning("Rejected invalid URL from client=%s: %s", request.remote_addr, error)
            response = make_response(str(error), 400)
            response.headers["Content-Type"] = "text/plain; charset=utf-8"
            return response
        except Exception:
            logger.error("Failed to create short link for url=%s due to internal error", url, exc_info=True)
            abort(500)

        logger.info("Created short_id=%s -> %s client=%s", short_id, url, request.remote_addr)
        short_url = f"{public_base_url()}/{short_id}"
        response = make_response("", 201)
        response.headers["Location"] = short_url
        return response

    @app.get("/<short_id>")
    def redirect_short(short_id):
        try:
            service = app.extensions["linker_service"]
            url = service.find_url(short_id)
        except Exception:
            logger.error("Failed to resolve short_id=%s due to internal processing error", short_id, exc_info=True)
            abort(500)

        if url is None:
            logger.warning("Short URL not found: short_id=%s client=%s", short_id, request.remote_addr)
            abort(404)

        logger.info("Redirect short_id=%s -> %s client=%s", short_id, url, request.remote_addr)
        response = make_response("", 301)
        response.headers["Location"] = url
        return response

    return app


def run():
    app = create_app()
    logger.info("Linker Python running on http://%s:%s", app.config["HOST"], app.config["PORT"])
    app.run(host=app.config["HOST"], port=app.config["PORT"])


if __name__ == "__main__":
    run()
