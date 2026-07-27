"""Pins role isolation (#77's user stories 4/6): this server reads only
`GS1BELU_DOWNLOAD_*`, never `GS1BELU_UPLOAD_*`."""

import pytest

from gs1belu_mpm_download.config import ConfigError, ServerConfig

FULL_ENV = {
    "GS1BELU_ENVIRONMENT": "uat",
    "GS1BELU_DOWNLOAD_CLIENT_ID": "download-id",
    "GS1BELU_DOWNLOAD_CLIENT_SECRET": "download-secret",
    "GS1BELU_DOWNLOAD_SUBSCRIPTION_KEY": "download-key",
}


def test_loads_the_download_credential_set():
    config = ServerConfig.from_env(FULL_ENV)

    assert config.environment.value == "uat"
    assert config.api_version == "v17"
    assert config.credentials.client_id == "download-id"
    assert config.credentials.client_secret == "download-secret"
    assert config.credentials.subscription_key == "download-key"


def test_never_reads_upload_prefixed_vars():
    env = {**FULL_ENV, "GS1BELU_UPLOAD_CLIENT_ID": "should-never-be-read"}
    config = ServerConfig.from_env(env)
    assert config.credentials.client_id == "download-id"


def test_defaults_api_version_when_unset():
    assert ServerConfig.from_env(FULL_ENV).api_version == "v17"


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
