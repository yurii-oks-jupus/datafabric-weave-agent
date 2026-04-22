"""Model factory for multi-provider LLM support.

Supports: gemini, anthropic, openai, kimi.
Gemini uses native ADK integration (plain string).
All others route through ADK's LiteLLM adapter.
"""

from __future__ import annotations

import os
import logging
from typing import Literal
from functools import lru_cache

from google.genai import types as genai_types

from core.config import settings

logger = logging.getLogger(__name__)

Provider = Literal["gemini", "anthropic", "openai", "kimi"]


def get_provider() -> Provider:
    """Return the active LLM provider name."""
    return settings.llm.provider


@lru_cache(maxsize=1)
def get_model():
    """Return the model identifier or LiteLlm wrapper for the active provider.

    For Gemini: returns a plain string (ADK handles natively).
    For all others: returns a LiteLlm instance via ADK's LiteLLM adapter.

    Raises:
        ValueError: If the configured provider is not supported.
        ImportError: If litellm is not installed for non-Gemini providers.
    """
    provider = get_provider()
    provider_config = getattr(settings.llm, provider, None)

    if provider_config is None and provider != "gemini":
        raise ValueError(
            f"No config section found for provider '{provider}' in settings.llm. "
            f"Add an 'llm.{provider}' section to conf/config.yaml."
        )

    model_name = provider_config.model if provider_config else settings.llm.model

    if provider == "gemini":
        return model_name

    try:
        from google.adk.models.lite_llm import LiteLlm
    except ImportError:
        raise ImportError(
            f"LLM provider '{provider}' requires the LiteLlm adapter. "
            f"Install it with: pip install litellm"
        ) from None

    if provider in ("anthropic", "openai"):
        return LiteLlm(model=f"{provider}/{model_name}")

    if provider == "kimi":
        api_base = getattr(provider_config, "api_base", "https://api.moonshot.cn/v1")
        api_key = os.environ.get("MOONSHOT_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "Kimi provider requires the MOONSHOT_API_KEY environment variable."
            )
        return LiteLlm(model=f"openai/{model_name}", api_base=api_base, api_key=api_key)

    raise ValueError(
        f"Unsupported LLM provider: '{provider}'. "
        f"Expected one of: gemini, anthropic, openai, kimi."
    )


def get_generate_config() -> genai_types.GenerateContentConfig:
    """Return a GenerateContentConfig with temperature from settings (default: 0.0)."""
    temperature = float(getattr(settings.llm, "temperature", 0.0))
    return genai_types.GenerateContentConfig(temperature=temperature)
