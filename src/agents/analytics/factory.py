"""Analytics wrapper — builds the analytics root agent as a single unit.

Root.py attaches `create_analytics_agent()` as one AgentTool when persona is
`weave-analytics`. The wrapper itself routes to four specialist sub-agents:
schema, stats, segment, fraud.
"""

import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from agents.analytics.fraud import create_fraud_agent
from agents.analytics.schema import create_schema_agent
from agents.analytics.segment import create_segment_agent
from agents.analytics.stats import create_stats_agent
from agents.descriptions import ANALYTICS_AGENT_DESCRIPTION
from core.model import get_generate_config, get_model, get_provider
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)


def create_analytics_agent() -> LlmAgent:
    """Create and return the Analytics wrapper agent.

    The wrapper exposes the four SQL specialists to weave's root via a single
    AgentTool. All child agents are instantiated lazily inside this factory
    so import cost stays zero when the weave-base persona is active.
    """
    logger.info("Initializing Analytics wrapper agent")

    schema_agent = create_schema_agent()
    stats_agent = create_stats_agent()
    segment_agent = create_segment_agent()
    fraud_agent = create_fraud_agent()

    return LlmAgent(
        name="analytics_agent",
        description=ANALYTICS_AGENT_DESCRIPTION,
        model=get_model(),
        instruction=load_prompt("analytics_agent", provider=get_provider()),
        tools=[
            AgentTool(schema_agent),
            AgentTool(stats_agent),
            AgentTool(segment_agent),
            AgentTool(fraud_agent),
        ],
        generate_content_config=get_generate_config(),
    )
