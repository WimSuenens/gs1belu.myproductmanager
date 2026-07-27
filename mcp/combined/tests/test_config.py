import pytest

from gs1belu_mpm_mcp.config import ConfigError, ServerConfig
from gs1belu_mpm_mcp.environment import Environment

FULL_ENV = {
    "GS1BELU_ENVIRONMENT": "uat",
    "GS1BELU_UPLOAD_CLIENT_ID": "upload-id",
    "GS1BELU_UPLOAD_CLIENT_SECRET": "upload-secret",
    "GS1BELU_UPLOAD_SUBSCRIPTION_KEY": "upload-key",
    "GS1BELU_DOWNLOAD_CLIENT_ID": "download-id",
    "GS1BELU_DOWNLOAD_CLIENT_SECRET": "download-secret",
    "GS1BELU_DOWNLOAD_SUBSCRIPTION_KEY": "download-key",
}


def test_loads_independent_credential_sets_per_sub_server():
    config = ServerConfig.from_env(FULL_ENV)

    assert config.environment is Environment.UAT
    assert config.api_version == "v17"
    assert config.upload_credentials.client_id == "upload-id"
    assert config.download_credentials.client_id == "download-id"
    assert config.upload_credentials != config.download_credentials


def test_defaults_api_version_when_unset():
    config = ServerConfig.from_env(FULL_ENV)
    assert config.api_version == "v17"


def test_honors_explicit_api_version():
    env = {**FULL_ENV, "GS1BELU_API_VERSION": "v18"}
    assert ServerConfig.from_env(env).api_version == "v18"


@pytest.mark.parametrize("missing", list(FULL_ENV.keys()))
def test_raises_on_missing_required_var(missing):
    env = {k: v for k, v in FULL_ENV.items() if k != missing}
    with pytest.raises(ConfigError):
        ServerConfig.from_env(env)


def test_raises_on_invalid_environment_value():
    env = {**FULL_ENV, "GS1BELU_ENVIRONMENT": "staging"}
    with pytest.raises(ConfigError):
        ServerConfig.from_env(env)
