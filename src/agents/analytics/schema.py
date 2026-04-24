"""Schema specialist — table discovery, column profiling, data quality audits.

MCP tools: list_tables, describe_table, missing_value_analysis, sample_data.
"""

import logging

from google.adk.agents.llm_agent import LlmAgent

from agents.descriptions import SCHEMA_AGENT_DESCRIPTION
from core.model import get_generate_config, get_model, get_provider
from core.tools import SCHEMA_TOOLS
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_schema_agent() -> LlmAgent:
    """Create and return the Schema Agent."""
    logger.info("Initializing Schema Agent")
    return LlmAgent(
        name="schema_agent",
        description=SCHEMA_AGENT_DESCRIPTION,
        model=get_model(),
        instruction=load_prompt("schema_agent", provider=get_provider()),
        tools=list(SCHEMA_TOOLS),
        generate_content_config=get_generate_config(),
    )
