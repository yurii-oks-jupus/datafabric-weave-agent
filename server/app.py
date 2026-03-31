"""Unified application server.

create_app() returns a FastAPI instance for the /ask endpoint (dev/legacy).
_create_a2a_app() returns A2A protocol components for production.
"""

import uuid
import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from google.adk.runners import Runner
from google.genai import types as genai_types

from agents import root_agent
from core.config import settings
from core.model import get_provider
from core.session import create_session_service
from core.cache import ResponseCache

logger = logging.getLogger(__name__)

response_cache = ResponseCache(max_size=500, ttl_seconds=86400)


class AskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)
    session_id: str | None = None
    user_id: str | None = None


class AskResponse(BaseModel):
    session_id: str
    user_id: str
    reply: str


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    db_url = getattr(settings, "session_db_url", None)
    session_svc = create_session_service(db_url)

    app_name = "weave_agent"

    runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_svc,
    )

    app = FastAPI(title="Weave — Data Fabric Agent", version="0.1.0")

    @app.get("/datafabric-weave-agent/health")
    async def health():
        return JSONResponse({
            "status": "ok",
            "llm_provider": get_provider(),
            "llm_model": settings.llm.model,
            "cache_stats": response_cache.stats,
        })

    @app.post("/datafabric-weave-agent/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        user_id = req.user_id or "default_user"
        session_id = req.session_id or str(uuid.uuid4())

        cached = response_cache.get_exact(req.message)
        if cached:
            logger.info("Cache HIT for query: %s", req.message[:50])
            return AskResponse(
                session_id=session_id, user_id=user_id, reply=cached
            )

        existing = await session_svc.get_session(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
        if existing is None:
            await session_svc.create_session(
                app_name=app_name, user_id=user_id, session_id=session_id
            )
            logger.info("Created session %s for user %s", session_id, user_id)

        user_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=req.message)],
        )

        reply_parts = []
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message,
            ):
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if part.text:
                            reply_parts.append(part.text)
        except Exception as exc:
            logger.exception("Agent run failed for session=%s: %s", session_id, exc)
            raise HTTPException(
                status_code=500,
                detail="An internal error occurred while processing your request.",
            )

        reply = reply_parts[-1].strip() if reply_parts else "(no response)"

        if reply_parts:
            response_cache.put(req.message, reply)

        logger.info("session=%s reply_len=%d", session_id, len(reply))
        return AskResponse(session_id=session_id, user_id=user_id, reply=reply)

    return app


def _create_a2a_app():
    """Create A2A protocol application."""
    from server.agent_card import create_agent_card
    from cib_agentic_hub.a2a.adk_a2a_server import run_adk_a2a_server

    agent_card = create_agent_card()

    logger.info("Creating A2A application")
    return {
        "agent": root_agent,
        "agent_card": agent_card,
        "run_fn": run_adk_a2a_server,
    }
