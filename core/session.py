"""Session service configuration.

Provides a factory to create the appropriate session service
based on the deployment environment.
"""

import logging

from google.adk.sessions import InMemorySessionService

logger = logging.getLogger(__name__)


def create_session_service(db_url: str | None = None):
    """Create the appropriate session service.

    Args:
        db_url: PostgreSQL connection string for persistent sessions.
                If None, falls back to InMemorySessionService (dev only).

    Returns:
        A session service instance.
    """
    if db_url:
        try:
            from google.adk.sessions import DatabaseSessionService

            logger.info("Using DatabaseSessionService (persistent)")
            return DatabaseSessionService(db_url=db_url)
        except ImportError:
            logger.warning(
                "DatabaseSessionService not available. "
                "Install asyncpg: pip install asyncpg. "
                "Falling back to InMemorySessionService."
            )
            return InMemorySessionService()
        except Exception as e:
            logger.error("Failed to create DatabaseSessionService: %s", e)
            logger.warning("Falling back to InMemorySessionService.")
            return InMemorySessionService()
    else:
        logger.info("Using InMemorySessionService (non-persistent, dev only)")
        return InMemorySessionService()
