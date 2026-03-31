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
                If None, uses InMemorySessionService (dev only).

    Returns:
        A session service instance.

    Raises:
        ImportError: If asyncpg is not installed when db_url is provided.
        Exception: If the database connection fails when db_url is provided.
    """
    if db_url:
        try:
            from google.adk.sessions import DatabaseSessionService
        except ImportError:
            raise ImportError(
                "DatabaseSessionService requires asyncpg. "
                "Install it with: pip install asyncpg"
            ) from None

        logger.info("Using DatabaseSessionService (persistent)")
        return DatabaseSessionService(db_url=db_url)

    logger.info("Using InMemorySessionService (non-persistent, dev only)")
    return InMemorySessionService()
