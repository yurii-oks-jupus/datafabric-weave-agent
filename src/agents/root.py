"""Root Agent factory — persona-aware.

`persona="weave-base"` → Knowledge + Registry only (unchanged from FAB-1417).
`persona="weave-analytics"` → adds the Analytics wrapper as a third AgentTool.

The analytics sub-tree is imported lazily so weave-base startups don't pay the
SQLAlchemy + analytics-prompt load cost (FAB-2101 D11).
"""

from __future__ import annotations

import logging
from typing import Literal

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from agents.descriptions import ROOT_AGENT_DESCRIPTION
from agents.knowledge import create_knowledge_agent
from agents.registry import create_registry_agent
from core.model import get_generate_config, get_model, get_provider
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)

Persona = Literal["weave-base", "weave-analytics"]
SUPPORTED_PERSONAS: tuple[Persona, ...] = ("weave-base", "weave-analytics")


def build_root_agent(persona: Persona = "weave-base") -> LlmAgent:
    """Build the root agent for the requested persona.

    Raises:
        ValueError: If `persona` isn't one of SUPPORTED_PERSONAS.
    """
    if persona not in SUPPORTED_PERSONAS:
        raise ValueError(
            f"Unsupported persona: {persona!r}. "
            f"Expected one of: {', '.join(SUPPORTED_PERSONAS)}."
        )

    logger.info("Building root agent (persona=%s)", persona)

    tools: list[AgentTool] = [
        AgentTool(create_knowledge_agent()),
        AgentTool(create_registry_agent()),
    ]

    if persona == "weave-analytics":
        from agents.analytics import create_analytics_agent

        tools.append(AgentTool(create_analytics_agent()))

    return LlmAgent(
        name="weave_agent",
        description=ROOT_AGENT_DESCRIPTION,
        model=get_model(),
        instruction=load_prompt("root_agent", provider=get_provider()),
        tools=tools,
        generate_content_config=get_generate_config(),
    )
