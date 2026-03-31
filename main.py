"""Weave Agent — Entry Point

Minimal main file. All logic lives in the appropriate modules.

Usage:
    Development (FastAPI):  APP_ENV=local python main.py
    Production (A2A):       APP_ENV=dev python main.py --a2a
"""

import os
import sys
import logging

from utils.logging_config import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

from core.config import configure_environment
configure_environment()

RUN_MODE = "a2a" if "--a2a" in sys.argv else "fastapi"

from core.model import get_provider, get_model
logger.info(
    "Starting Weave Agent (env=%s, mode=%s, provider=%s, model=%s)",
    os.environ.get("APP_ENV", "local"), RUN_MODE, get_provider(), get_model(),
)


def main():
    """Application entry point."""
    from core.config import settings

    host = settings.app.host
    port = int(settings.app.port)

    if RUN_MODE == "a2a":
        from server.app import _create_a2a_app
        a2a_config = _create_a2a_app()
        path = settings.app.path

        logger.info("Starting A2A server at %s:%d%s", host, port, path)
        a2a_config["run_fn"](
            agent=a2a_config["agent"],
            agent_card=a2a_config["agent_card"],
            host=host,
            port=port,
            path=path,
        )
    else:
        import uvicorn
        from server.app import create_app

        app = create_app()
        logger.info("Starting FastAPI server at %s:%d", host, port)
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
