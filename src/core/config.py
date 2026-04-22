"""Dynaconf settings loader.

Reads from conf/config.yaml with environment-based switching via APP_ENV.
"""

import os
import logging
import certifi

from dynaconf import Dynaconf

logger = logging.getLogger(__name__)

settings = Dynaconf(
    envvar_prefix="APP",
    settings_files=["./conf/config.yaml"],
    load_dotenv=True,
    environments=True,
    env_switcher="APP_ENV",
)

_SUPPORTED_PROVIDERS = ("gemini", "anthropic", "openai", "kimi")

# API key env var name per provider
_PROVIDER_API_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
}


def configure_environment() -> None:
    """Set up environment variables based on APP_ENV and LLM provider.

    Must be called once at application startup before any agent modules
    are imported, because agent construction reads environment variables
    (e.g., GOOGLE_CLOUD_PROJECT, API keys) that this function sets.
    """
    app_env = os.environ.get("APP_ENV", "local")
    provider = settings.llm.provider

    # Validate provider early
    if provider not in _SUPPORTED_PROVIDERS:
        raise EnvironmentError(
            f"Unsupported LLM provider: '{provider}'. "
            f"Expected one of: {', '.join(_SUPPORTED_PROVIDERS)}. "
            f"Check 'llm.provider' in conf/config.yaml."
        )

    # SSL / proxy
    if app_env == "local":
        os.environ["HTTPS_PROXY"] = settings.proxy.cloud_proxy
        os.environ["HTTP_PROXY"] = settings.proxy.cloud_proxy
        os.environ["NO_PROXY"] = settings.proxy.no_proxy
        os.environ["SSL_CERT_FILE"] = certifi.where()
        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
        os.environ["OTEL_SDK_DISABLED"] = "true"
    else:
        os.environ["SSL_CERT_FILE"] = os.getenv("SSL_CERT_FILE", certifi.where())
        os.environ["REQUESTS_CA_BUNDLE"] = os.getenv("REQUESTS_CA_BUNDLE", certifi.where())

    # Gemini-specific setup
    if provider == "gemini":
        if app_env == "local":
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.vertexai.google_application_credentials
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        os.environ["GOOGLE_CLOUD_PROJECT"] = settings.vertexai.project
        os.environ["GOOGLE_CLOUD_LOCATION"] = settings.vertexai.location

    # Validate API key for non-Gemini providers (all environments)
    env_var = _PROVIDER_API_KEY_ENV.get(provider)
    if env_var:
        api_key = os.environ.get(env_var, "").strip()
        if not api_key:
            raise EnvironmentError(
                f"LLM provider '{provider}' requires the {env_var} environment variable. "
                f"Set it before starting the application."
            )

    logger.info("Environment configured (env=%s, provider=%s)", app_env, provider)
