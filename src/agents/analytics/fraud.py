"""Fraud specialist — anomaly detection, time-series trends, custom SQL."""

import logging

from google.adk.agents.llm_agent import LlmAgent

from agents.descriptions import FRAUD_AGENT_DESCRIPTION
from core.model import get_generate_config, get_model, get_provider
from core.tools import FRAUD_TOOLS
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_fraud_agent() -> LlmAgent:
    """Create and return the Fraud Agent."""
    logger.info("Initializing Fraud Agent")
    return LlmAgent(
        name="fraud_agent",
        description=FRAUD_AGENT_DESCRIPTION,
        model=get_model(),
        instruction=load_prompt("fraud_agent", provider=get_provider()),
        tools=list(FRAUD_TOOLS),
        generate_content_config=get_generate_config(),
    )
