"""Dynaconf settings loader.

Reads from conf/config.yaml with environment-based switching via APP_ENV.
"""

import os
import certifi

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="APP",
    settings_files=["./conf/config.yaml"],
    load_dotenv=True,
    environments=True,
    env_switcher="APP_ENV",
)


def configure_environment():
    """Set up environment variables based on APP_ENV.

    Call this once at application startup, before importing agents.
    """
    app_env = os.environ.get("APP_ENV", "local")

    if app_env == "local":
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = settings.vertexai.google_application_credentials
        os.environ["HTTPS_PROXY"] = settings.proxy.cloud_proxy
        os.environ["HTTP_PROXY"] = settings.proxy.cloud_proxy
        os.environ["NO_PROXY"] = settings.proxy.no_proxy
        os.environ["SSL_CERT_FILE"] = certifi.where()
        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
    else:
        os.environ["SSL_CERT_FILE"] = os.getenv("SSL_CERT_FILE", certifi.where())
        os.environ["REQUESTS_CA_BUNDLE"] = os.getenv("REQUESTS_CA_BUNDLE", certifi.where())

    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ["GOOGLE_CLOUD_PROJECT"] = settings.vertexai.project
    os.environ["GOOGLE_CLOUD_LOCATION"] = settings.vertexai.location

    # Disable OpenTelemetry locally to avoid noisy logs
    if app_env == "local":
        os.environ["OTEL_SDK_DISABLED"] = "true"
