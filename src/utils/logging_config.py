"""Structured logging setup for Cloud Run.

Configures logging with:
  - JSON-formatted output for production (Cloud Run log analysis)
  - Human-readable output for local development
"""

import os
import sys
import logging


def setup_logging():
    """Configure logging based on environment."""
    app_env = os.environ.get("APP_ENV", "local")

    if app_env == "local":
        fmt = "%(asctime)s %(levelname)-8s [%(name)s:%(lineno)d] %(message)s"
        datefmt = "%H:%M:%S"
    else:
        # Structured format for Cloud Run
        fmt = '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","line":%(lineno)d,"message":"%(message)s"}'
        datefmt = "%Y-%m-%dT%H:%M:%S"

    logging.basicConfig(
        format=fmt,
        datefmt=datefmt,
        level=logging.INFO,
        stream=sys.stdout,
        force=True,  # Override any previous basicConfig
    )

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
