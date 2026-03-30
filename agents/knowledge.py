"""Knowledge Agent — searches Fabric documentation via the Docusaurus MCP server."""

import logging

from google.adk.agents.llm_agent import LlmAgent
from google.genai import types as genai_types

from agents.descriptions import KNOWLEDGE_AGENT_DESCRIPTION
from core.config import settings
from core.mcp import get_mcp_connection
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_knowledge_agent(model: str | None = None) -> LlmAgent:
    """Create and return the Knowledge Agent.

    Args:
        model: Override the default model from settings. If None, uses config.
    """
    model = model or settings.vertexai.llm_model
    prompt = load_prompt("knowledge_agent")
    mcp_conn = get_mcp_connection(settings.knowledge_registry_mcp)

    logger.info("Initializing Knowledge Agent (model=%s)", model)

    return LlmAgent(
        name="knowledge_agent",
        description=KNOWLEDGE_AGENT_DESCRIPTION,
        model=model,
        instruction=prompt,
        tools=[mcp_conn],
        generate_content_config=genai_types.GenerateContentConfig(
            temperature=0.0,
        ),
        # NOTE: No BuiltInPlanner — sub-agents should execute directly
    )
