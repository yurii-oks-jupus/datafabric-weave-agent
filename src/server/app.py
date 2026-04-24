"""Unified application server.

create_app() returns a FastAPI instance for the /ask endpoint (dev/legacy).
_create_a2a_app() returns A2A protocol components for production.

FAB-2101 adds a persona switch — the same /ask endpoint routes to either
`weave-base` (Knowledge + Registry) or `weave-analytics` (adds the Analytics
specialist wrapper). Per-persona Runners are cached at startup so a switch
is a dict lookup, not an agent rebuild.
"""

import logging
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from google.adk.runners import Runner
from google.genai import types as genai_types
from pydantic import BaseModel, Field

from agents import build_root_agent
from agents.root import SUPPORTED_PERSONAS, Persona
from core.cache import ResponseCache
from core.config import settings
from core.format_override import detects_format_override
from core.model import get_provider
from core.session import create_session_service

logger = logging.getLogger(__name__)

response_cache = ResponseCache(max_size=500, ttl_seconds=86400)


class AskRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10_000)
    session_id: str | None = None
    user_id: str | None = None
    persona: Persona | None = Field(
        default=None,
        description="Override the default persona for this request (FAB-2101).",
    )


class AskResponse(BaseModel):
    session_id: str
    user_id: str
    reply: str
    cache: str = Field(
        default="miss",
        description="Cache status for this reply: 'hit' or 'miss' (FAB-2101 Sprint 3.2.5).",
    )
    format: str = Field(
        default="structured",
        description=(
            "'structured' if the reply validates against the root schema; "
            "'freeform' if a format override was detected or parsing failed "
            "(FAB-2101 Sprint 3.3)."
        ),
    )


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    db_url = getattr(settings, "session_db_url", None)
    session_svc = create_session_service(db_url)

    app_name = "weave_agent"
    default_persona: Persona = getattr(settings.app, "default_persona", "weave-base")

    # Build one Runner per supported persona at startup. Personas not used by
    # the default are built lazily on first request (see _get_runner).
    runners: dict[Persona, Runner] = {
        default_persona: Runner(
            agent=build_root_agent(default_persona),
            app_name=app_name,
            session_service=session_svc,
        )
    }

    def _get_runner(persona: Persona) -> Runner:
        if persona not in runners:
            logger.info("Lazy-building Runner for persona=%s", persona)
            runners[persona] = Runner(
                agent=build_root_agent(persona),
                app_name=app_name,
                session_service=session_svc,
            )
        return runners[persona]

    app = FastAPI(title="Weave — Data Fabric Agent", version="0.1.0")

    @app.get("/datafabric-weave-agent/health")
    async def health():
        return JSONResponse(
            {
                "status": "ok",
                "llm_provider": get_provider(),
                "llm_model": settings.llm.model,
                "default_persona": default_persona,
                "supported_personas": list(SUPPORTED_PERSONAS),
                "ready_personas": sorted(runners.keys()),
                "cache_stats": response_cache.stats,
            }
        )

    @app.post("/datafabric-weave-agent/ask", response_model=AskResponse)
    async def ask(req: AskRequest):
        # Latency instrumentation (FAB-2101 Sprint 3.1.4). One log line per request
        # captures request_id, persona, tool-call count, cache status, and total ms.
        request_id = str(uuid.uuid4())[:8]
        t_start = time.perf_counter()
        user_id = req.user_id or "default_user"
        session_id = req.session_id or str(uuid.uuid4())
        persona: Persona = req.persona or default_persona

        if persona not in SUPPORTED_PERSONAS:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Unsupported persona: {persona!r}. "
                    f"Expected one of: {', '.join(SUPPORTED_PERSONAS)}."
                ),
            )

        cached = response_cache.get_exact(req.message, session_id=session_id)
        if cached:
            total_ms = int((time.perf_counter() - t_start) * 1000)
            logger.info(
                "req=%s persona=%s cache=hit tool_calls=0 total_ms=%d",
                request_id, persona, total_ms,
            )
            return AskResponse(
                session_id=session_id, user_id=user_id, reply=cached, cache="hit"
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

        runner = _get_runner(persona)

        reply_parts = []
        tool_calls = 0
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=user_message,
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, "function_call", None) is not None:
                            tool_calls += 1
                if event.is_final_response() and event.content:
                    for part in event.content.parts:
                        if part.text:
                            reply_parts.append(part.text)
        except Exception as exc:
            total_ms = int((time.perf_counter() - t_start) * 1000)
            logger.exception(
                "req=%s persona=%s cache=miss tool_calls=%d total_ms=%d status=error: %s",
                request_id, persona, tool_calls, total_ms, exc,
            )
            raise HTTPException(
                status_code=500,
                detail="An internal error occurred while processing your request.",
            ) from exc

        reply = reply_parts[-1].strip() if reply_parts else "(no response)"

        # FAB-2101 Sprint 3.3: consistency is enforced by the prompt
        # (structured sections: summary → details → source → next step).
        # Override = user asked for a different format this turn. We surface
        # the classification for observability but do not mutate the reply.
        response_format = "freeform" if detects_format_override(req.message) else "structured"

        if reply_parts:
            response_cache.put(req.message, reply, session_id=session_id)

        total_ms = int((time.perf_counter() - t_start) * 1000)
        logger.info(
            "req=%s persona=%s cache=miss tool_calls=%d total_ms=%d "
            "reply_len=%d format=%s session=%s",
            request_id, persona, tool_calls, total_ms, len(reply),
            response_format, session_id,
        )
        return AskResponse(
            session_id=session_id,
            user_id=user_id,
            reply=reply,
            cache="miss",
            format=response_format,
        )

    return app


def _create_a2a_app():
    """Create A2A protocol application."""
    from cib_agentic_hub.a2a.adk_a2a_server import run_adk_a2a_server

    from server.agent_card import create_agent_card

    # A2A mode pins the default persona — callers pick personas via the card.
    default_persona: Persona = getattr(settings.app, "default_persona", "weave-base")
    agent_card = create_agent_card()

    logger.info("Creating A2A application (default_persona=%s)", default_persona)
    return {
        "agent": build_root_agent(default_persona),
        "agent_card": agent_card,
        "run_fn": run_adk_a2a_server,
    }
