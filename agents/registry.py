"""Registry Agent — queries Fabric asset metadata via the Asset Registry MCP server."""

import logging

from google.adk.agents.llm_agent import LlmAgent
from google.genai import types as genai_types

from agents.descriptions import REGISTRY_AGENT_DESCRIPTION
from core.config import settings
from core.mcp import get_mcp_connection
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_registry_agent(model: str | None = None) -> LlmAgent:
    """Create and return the Fabric Registry Agent.

    Args:
        model: Override the default model from settings. If None, uses config.
    """
    model = model or settings.vertexai.llm_model
    prompt = load_prompt("registry_agent")
    mcp_conn = get_mcp_connection(settings.asset_registry_mcp)

    logger.info("Initializing Registry Agent (model=%s)", model)

    return LlmAgent(
        name="fabric_registry_agent",
        description=REGISTRY_AGENT_DESCRIPTION,
        model=model,
        instruction=prompt,
        tools=[mcp_conn],
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0.0,
        ),
        # NOTE: No BuiltInPlanner — sub-agents should execute directly
    )
