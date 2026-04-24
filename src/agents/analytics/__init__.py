"""Analytics persona — wraps four SQL-specialist sub-agents as one AgentTool.

Imported by `agents.root` only when persona="weave-analytics". Does not load
when persona="weave-base", so weave's base runtime cost is unchanged.

Stage 5 deliverable (FAB-2101 Sprint 2.1.4). Stage 6 wires it into the root
factory behind the persona switch.
"""

from agents.analytics.factory import create_analytics_agent

__all__ = ["create_analytics_agent"]
