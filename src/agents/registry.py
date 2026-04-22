"""Registry Agent — queries Fabric asset metadata via the Asset Registry MCP server."""

import logging

from google.adk.agents.llm_agent import LlmAgent

from agents.descriptions import REGISTRY_AGENT_DESCRIPTION
from core.config import settings
from core.model import get_model, get_provider, get_generate_config
from core.mcp import get_mcp_connection
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_registry_agent() -> LlmAgent:
    """Create and return the Fabric Registry Agent."""
    prompt = load_prompt("registry_agent", provider=get_provider())
    mcp_conn = get_mcp_connection(settings.asset_registry_mcp)

    logger.info("Initializing Registry Agent (model=%s)", get_model())

    return LlmAgent(
        name="fabric_registry_agent",
        description=REGISTRY_AGENT_DESCRIPTION,
        model=get_model(),
        instruction=prompt,
        tools=[mcp_conn],
        generate_content_config=get_generate_config(),
    )
