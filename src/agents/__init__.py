"""Agents package — exposes the persona-aware root factory.

`build_root_agent(persona)` is lazy; callers must call
`core.config.configure_environment()` first.
"""

from agents.root import build_root_agent

__all__ = ["build_root_agent"]
