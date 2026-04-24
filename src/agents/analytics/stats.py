"""Stats specialist — descriptive statistics, distributions, correlations."""

import logging

from google.adk.agents.llm_agent import LlmAgent

from agents.descriptions import STATS_AGENT_DESCRIPTION
from core.model import get_generate_config, get_model, get_provider
from core.tools import STATS_TOOLS
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_stats_agent() -> LlmAgent:
    """Create and return the Stats Agent."""
    logger.info("Initializing Stats Agent")
    return LlmAgent(
        name="stats_agent",
        description=STATS_AGENT_DESCRIPTION,
        model=get_model(),
        instruction=load_prompt("stats_agent", provider=get_provider()),
        tools=list(STATS_TOOLS),
        generate_content_config=get_generate_config(),
    )
