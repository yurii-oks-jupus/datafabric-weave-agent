"""Prompt loader utility — provider-aware.

Loads system prompts from prompts/ directory with per-provider resolution.
Supports .xml (Anthropic) and .md (all others) formats.
Supports {{include:path}} directives for composable sub-prompts.

Resolution chain (first match wins):
  1. prompts/{provider}/{agent_name}.xml  (e.g. Anthropic XML)
  2. prompts/{provider}/{agent_name}.md   (e.g. OpenAI/Kimi Markdown)
  3. prompts/default/{agent_name}.md      (universal fallback)
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from functools import lru_cache

if TYPE_CHECKING:
    from core.model import Provider

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
_INCLUDE_PATTERN = re.compile(r"\{\{include:(.+?)\}\}")


def _resolve_includes(content: str, base_dir: Path) -> str:
    """Resolve {{include:path}} directives relative to base_dir.

    Raises:
        FileNotFoundError: If an included file does not exist.
    """
    def _replace(match):
        rel_path = match.group(1).strip()
        include_path = (base_dir / rel_path).resolve()

        if not include_path.is_relative_to(_PROMPTS_DIR):
            raise FileNotFoundError(
                f"Include path escapes prompts directory: {rel_path} "
                f"(resolved to {include_path})"
            )

        if not include_path.exists():
            raise FileNotFoundError(
                f"Include file not found: {include_path} "
                f"(referenced from {base_dir})"
            )

        return include_path.read_text(encoding="utf-8").strip()

    return _INCLUDE_PATTERN.sub(_replace, content)


@lru_cache(maxsize=64)
def load_prompt(agent_name: str, provider: Provider | None = None) -> str:
    """Load a prompt with provider-aware resolution.

    Args:
        agent_name: Name of the prompt file (without extension).
        provider: LLM provider name. If None, uses default resolution.

    Returns:
        The prompt content as a string.

    Raises:
        FileNotFoundError: If no prompt file is found in any location.
        ValueError: If agent_name contains path traversal characters.
    """
    if ".." in agent_name or "/" in agent_name:
        raise ValueError(f"Invalid agent_name: {agent_name!r}")

    candidates = []

    if provider:
        candidates.append(_PROMPTS_DIR / provider / f"{agent_name}.xml")
        candidates.append(_PROMPTS_DIR / provider / f"{agent_name}.md")

    candidates.append(_PROMPTS_DIR / "default" / f"{agent_name}.md")

    for filepath in candidates:
        if filepath.exists():
            resolved = filepath.resolve()
            content = resolved.read_text(encoding="utf-8").strip()
            content = _resolve_includes(content, resolved.parent)
            logger.info(
                "Loaded prompt '%s' for provider '%s' from %s (%d chars)",
                agent_name, provider or "default", filepath.relative_to(_PROMPTS_DIR), len(content),
            )
            return content

    searched = [str(c.relative_to(_PROMPTS_DIR)) for c in candidates]
    raise FileNotFoundError(
        f"Prompt '{agent_name}' not found. Searched: {searched}"
    )
