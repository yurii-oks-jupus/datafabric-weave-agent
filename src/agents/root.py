"""Root Agent — orchestrates between Knowledge and Registry sub-agents."""

import logging

from google.adk.agents.llm_agent import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from agents.descriptions import ROOT_AGENT_DESCRIPTION
from agents.knowledge import create_knowledge_agent
from agents.registry import create_registry_agent
from core.model import get_model, get_provider, get_generate_config
from utils.prompts import load_prompt

logger = logging.getLogger(__name__)

# Create sub-agents
knowledge_agent = create_knowledge_agent()
registry_agent = create_registry_agent()

# Create root agent
logger.info("Initializing Root Agent")
root_agent = LlmAgent(
    name="weave_agent",
    description=ROOT_AGENT_DESCRIPTION,
    model=get_model(),
    instruction=load_prompt("root_agent", provider=get_provider()),
    tools=[
        AgentTool(knowledge_agent),
        AgentTool(registry_agent),
    ],
    generate_content_config=get_generate_config(),
)
