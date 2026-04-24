"""Output schemas per agent type (FAB-2101 D10).

Each agent's canonical output is a Pydantic model. We don't force structured
output at the `generate_content_config` level (that would break tool use in
Gemini); instead we prompt the LLM to emit JSON matching the schema, then
validate post-hoc. Compliance is best-effort — the prompt + schema pair plus
`format=structured|freeform` in `AskResponse` makes drift visible.

User overrides ("as a table", "as JSON", "give me markdown") bypass schema
instruction for that turn — detected in `core.format_override`.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RootReply(BaseModel):
    """Canonical root-agent response shape."""

    summary: str = Field(..., description="One-to-two-sentence plain-language answer.")
    details: list[str] = Field(
        default_factory=list, description="Bulleted supporting findings."
    )
    source_agent: Literal[
        "knowledge_agent", "registry_agent", "analytics_agent", "root_agent"
    ] = Field(..., description="Which sub-agent produced the primary data.")
    next_recommended_analysis: str | None = Field(
        default=None,
        description='Next-step suggestion in the form "Next: <action> via <agent>".',
    )


class KnowledgeReply(BaseModel):
    summary: str
    sources: list[str] = Field(default_factory=list, description="Doc URLs / refs.")


class RegistryReply(BaseModel):
    summary: str
    assets: list[dict[str, Any]] = Field(default_factory=list)


class AnalyticsSchemaReply(BaseModel):
    summary: str
    table: str
    columns: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int | None = None
    data_quality_warnings: list[str] = Field(default_factory=list)


class AnalyticsStatsReply(BaseModel):
    summary: str
    table: str
    column: str | None = None
    statistics: dict[str, Any] = Field(default_factory=dict)
    interpretation: str | None = None


class AnalyticsSegmentReply(BaseModel):
    summary: str
    table: str
    group_by: list[str] = Field(default_factory=list)
    aggregation: str | None = None
    top_n: list[dict[str, Any]] = Field(default_factory=list)


class AnalyticsFraudReply(BaseModel):
    summary: str
    table: str
    method: str | None = None
    outlier_count: int | None = None
    outlier_pct: float | None = None
    bounds: dict[str, Any] | None = None
    recommended_action: str | None = None


# Schema registry used by validate_reply() and prompt injection.
SCHEMAS: dict[str, type[BaseModel]] = {
    "root_agent": RootReply,
    "knowledge_agent": KnowledgeReply,
    "registry_agent": RegistryReply,
    "schema_agent": AnalyticsSchemaReply,
    "stats_agent": AnalyticsStatsReply,
    "segment_agent": AnalyticsSegmentReply,
    "fraud_agent": AnalyticsFraudReply,
}


def validate_reply(agent_name: str, reply_text: str) -> BaseModel | None:
    """Try to parse `reply_text` as JSON matching the schema for `agent_name`.

    Returns a Pydantic instance on success, None on any failure (invalid JSON,
    schema mismatch, unknown agent). Callers use the `None` return as a
    signal that the reply is free-form (e.g. an override was in effect).
    """
    import json

    schema_cls = SCHEMAS.get(agent_name)
    if schema_cls is None:
        return None
    try:
        payload = json.loads(reply_text)
    except (json.JSONDecodeError, TypeError):
        return None
    try:
        return schema_cls(**payload)
    except Exception:
        return None
