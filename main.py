"""Weave Agent — Entry Point

Minimal main file. All logic lives in the appropriate modules.

Usage:
    Development (FastAPI):  APP_ENV=local python main.py
    Production (A2A):       APP_ENV=dev python main.py --a2a
"""

import os
import sys
import logging

# Step 1: Set up logging first
from utils.logging_config import setup_logging
setup_logging()

logger = logging.getLogger(__name__)

# Step 2: Configure environment (SSL, proxy, Vertex AI)
from core.config import configure_environment
configure_environment()

# Step 3: Determine run mode
RUN_MODE = "a2a" if "--a2a" in sys.argv else "fastapi"

logger.info("Starting Weave Agent (env=%s, mode=%s)", os.environ.get("APP_ENV", "local"), RUN_MODE)


def main():
    """Application entry point."""
    from core.config import settings

    host = getattr(settings.app, "host", "0.0.0.0")
    port = int(getattr(settings.app, "port", 8080))

    if RUN_MODE == "a2a":
        # A2A Protocol mode
        from server.app import _create_a2a_app
        a2a_config = _create_a2a_app()
        path = getattr(settings.app, "path", "/datafabric-weave-agent")

        logger.info("Starting A2A server at %s:%d%s", host, port, path)
        a2a_config["run_fn"](
            agent=a2a_config["agent"],
            agent_card=a2a_config["agent_card"],
            host=host,
            port=port,
            path=path,
        )
    else:
        # FastAPI mode (development + legacy)
        import uvicorn
        from server.app import create_app

        app = create_app(mode="fastapi")
        logger.info("Starting FastAPI server at %s:%d", host, port)
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
