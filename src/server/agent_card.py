"""A2A Agent Card definition for Weave.

The Agent Card is the public metadata that allows other agents
to discover and understand Weave's capabilities.
"""

from a2a import types as a2a_types
from core.config import settings


def create_agent_card() -> a2a_types.AgentCard:
    """Build the A2A Agent Card for the Weave agent."""

    return a2a_types.AgentCard(
        name="Weave — Data Fabric Assistant",
        description=(
            "AI assistant for HSBC Data Fabric. Answers questions about "
            "Fabric documentation, data products, assets, and attributes."
        ),
        url=settings.app.a2a_url,
        version="0.1.0",
        capabilities=a2a_types.AgentCapabilities(streaming=True),
        default_input_modes=["text", "text/plain"],
        default_output_modes=["text", "text/plain"],
        skills=[
            a2a_types.AgentSkill(
                id="fabric-knowledge",
                name="Fabric Documentation Search",
                description=(
                    "Search and retrieve information from Data Fabric "
                    "documentation including onboarding guides, FAQs, "
                    "and architecture references."
                ),
                tags=["documentation", "search", "knowledge", "onboarding"],
            ),
            a2a_types.AgentSkill(
                id="fabric-registry",
                name="Data Product Explorer",
                description=(
                    "Query metadata about data products, assets, and "
                    "attributes registered in the Fabric platform."
                ),
                tags=["data-asset", "metadata", "sql", "registry"],
            ),
            a2a_types.AgentSkill(
                id="fabric-analytics",
                name="Financial Transaction EDA",
                description=(
                    "SQL-backed exploratory data analysis over a transactions "
                    "table: schema discovery, descriptive statistics, "
                    "segmentation, and fraud/anomaly detection. Available when "
                    "persona=weave-analytics (FAB-2101)."
                ),
                tags=["analytics", "sql", "eda", "fraud", "statistics"],
            ),
        ],
    )
