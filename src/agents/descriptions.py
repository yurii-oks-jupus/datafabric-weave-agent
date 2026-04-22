"""Short descriptions used for agent routing. Keep these concise —
the full system prompts live in prompts/{provider}/ files."""

ROOT_AGENT_DESCRIPTION = (
    "Orchestrator that routes user queries to the appropriate specialist agent. "
    "Delegates documentation questions to the Knowledge Agent and data/metadata "
    "questions to the Fabric Registry Agent."
)

KNOWLEDGE_AGENT_DESCRIPTION = (
    "Documentation search agent with semantic search capabilities. "
    "Searches across Docusaurus documentation and retrieves complete "
    "documents with source citations."
)

REGISTRY_AGENT_DESCRIPTION = (
    "Asset Registry Agent that searches for data assets based on user queries. "
    "Returns concise, schema-compliant results including matching assets, "
    "attributes, and related counts."
)
