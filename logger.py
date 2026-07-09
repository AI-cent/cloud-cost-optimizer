"""
Centralised logging configuration.
Call setup_logging() once at app startup.
Writes to both console (INFO+) and app.log (DEBUG+).
"""
import logging
import logging.handlers
import sys
from pathlib import Path

LOG_FILE = Path(__file__).parent / "app.log"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging():
    root = logging.getLogger()
    if root.handlers:
        return  # already configured (e.g. during tests)

    root.setLevel(logging.DEBUG)

    # ── Console handler — INFO and above ─────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    # ── File handler — DEBUG and above, rotating at 5 MB, 3 backups ─────────
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root.addHandler(console)
    root.addHandler(file_handler)

    # Silence noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("multipart.multipart").setLevel(logging.WARNING)
