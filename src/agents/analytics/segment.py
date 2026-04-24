"""Segment specialist — categorical breakdowns and GROUP BY aggregations."""

import logging

from google.adk.agents.llm_agent import LlmAgent

from agents.descriptions import SEGMENT_AGENT_DESCRIPTION
from core.model import get_generate_config, get_model, get_provider
from core.tools import SEGMENT_TOOLS
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_segment_agent() -> LlmAgent:
    """Create and return the Segment Agent."""
    logger.info("Initializing Segment Agent")
    return LlmAgent(
        name="segment_agent",
        description=SEGMENT_AGENT_DESCRIPTION,
        model=get_model(),
        instruction=load_prompt("segment_agent", provider=get_provider()),
        tools=list(SEGMENT_TOOLS),
        generate_content_config=get_generate_config(),
    )
