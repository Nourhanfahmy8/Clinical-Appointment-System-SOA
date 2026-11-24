"""MediBook service skeleton — see config.py for name, port and settings."""

import logging

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

import config

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# HTTP status -> error code, for anything Flask raises itself (PRD 8.2)
HTTP_ERROR_CODES = {
    400: "VALIDATION_ERROR",
    401: "INVALID_CREDENTIALS",
    404: "NOT_FOUND",
    405: "VALIDATION_ERROR",
    409: "INVALID_STATUS",
}


def error(code, message, status):
    """The project's single error shape."""
    return jsonify({"error": {"code": code, "message": message}}), status


@app.get("/health")
def health():
    return jsonify({"service": config.SERVICE_NAME, "status": "UP"})


@app.errorhandler(Exception)
def handle_unexpected(exc):
    """Never answer with an HTML error page (PRD ground rule 5)."""
    if isinstance(exc, HTTPException):
        code = HTTP_ERROR_CODES.get(exc.code, "INTERNAL_ERROR")
        return error(code, exc.description, exc.code)

    app.logger.exception("unhandled error")
    return error("INTERNAL_ERROR", "Unexpected server error", 500)


if __name__ == "__main__":
    app.run(host="localhost", port=config.SERVICE_PORT)
