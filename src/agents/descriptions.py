"""Short descriptions used for agent routing. Keep these concise —
the full system prompts live in prompts/{provider}/ files."""

ROOT_AGENT_DESCRIPTION = (
    "Orchestrator that routes user queries to the appropriate specialist agent. "
    "Delegates documentation questions to the Knowledge Agent, data/metadata "
    "questions to the Fabric Registry Agent, and (when the analytics persona is "
    "active) SQL EDA questions to the Analytics Agent."
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

# ------------------------------------------------------------------
# Analytics persona (FAB-2101). Active only when persona=weave-analytics.
# ------------------------------------------------------------------

ANALYTICS_AGENT_DESCRIPTION = (
    "Financial transaction EDA orchestrator. Routes SQL-backed analytics "
    "questions to four specialist sub-agents: schema discovery, descriptive "
    "statistics, segmentation (GROUP BY), and fraud/anomaly detection. "
    "Handles general questions about the transactions dataset and delegates "
    "to the appropriate specialist for detailed analysis."
)

SCHEMA_AGENT_DESCRIPTION = (
    "Specialist agent for database schema exploration and data quality audits. "
    "Handles queries about what tables exist, what columns they contain, "
    "data types, null/missing value analysis, and raw data previews."
)

STATS_AGENT_DESCRIPTION = (
    "Specialist agent for statistical analysis of numeric data. "
    "Handles descriptive statistics (mean, median, std, quartiles), "
    "distribution analysis (histograms, skewness), and Pearson correlation."
)

SEGMENT_AGENT_DESCRIPTION = (
    "Specialist agent for segmentation and categorical analysis. "
    "Handles spend by category/region/channel, customer rankings, fraud rates "
    "by segment, and GROUP BY aggregations."
)

FRAUD_AGENT_DESCRIPTION = (
    "Specialist agent for fraud detection, anomaly analysis, trend analysis, "
    "and custom SQL investigations. Handles outlier transactions, monthly/weekly "
    "fraud trends, account-takeover pattern detection, and bespoke SQL."
)
