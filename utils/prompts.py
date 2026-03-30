"""Prompt loader utility.

Loads system prompts from prompts/*.md files at runtime.
This allows prompts to be reviewed, edited, and versioned
independently from Python code.
"""

import os
import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

# Resolve prompts directory relative to project root
_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache(maxsize=16)
def load_prompt(agent_name: str) -> str:
    """Load a prompt from the prompts/ directory.

    Args:
        agent_name: Name of the prompt file (without .md extension).
                    E.g., "root_agent" loads "prompts/root_agent.md"

    Returns:
        The prompt content as a string.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    filepath = _PROMPTS_DIR / f"{agent_name}.md"

    if not filepath.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {filepath}. "
            f"Available prompts: {list_prompts()}"
        )

    content = filepath.read_text(encoding="utf-8").strip()
    logger.info("Loaded prompt '%s' (%d chars)", agent_name, len(content))
    return content


def list_prompts() -> list[str]:
    """List all available prompt names."""
    if not _PROMPTS_DIR.exists():
        return []
    return [f.stem for f in _PROMPTS_DIR.glob("*.md")]


def reload_prompt(agent_name: str) -> str:
    """Force-reload a prompt, bypassing the cache.

    Useful for hot-reloading prompts during development.
    """
    load_prompt.cache_clear()
    return load_prompt(agent_name)
