"""Pins role isolation (#77's user stories 3/5): this server reads only
`GS1BELU_UPLOAD_*`, never `GS1BELU_DOWNLOAD_*`."""

import pytest

from gs1belu_mpm_upload.config import ConfigError, ServerConfig

FULL_ENV = {
    "GS1BELU_ENVIRONMENT": "uat",
    "GS1BELU_UPLOAD_CLIENT_ID": "upload-id",
    "GS1BELU_UPLOAD_CLIENT_SECRET": "upload-secret",
    "GS1BELU_UPLOAD_SUBSCRIPTION_KEY": "upload-key",
}


def test_loads_the_upload_credential_set():
    config = ServerConfig.from_env(FULL_ENV)

    assert config.environment.value == "uat"
    assert config.api_version == "v17"
    assert config.credentials.client_id == "upload-id"
    assert config.credentials.client_secret == "upload-secret"
    assert config.credentials.subscription_key == "upload-key"


def test_never_reads_download_prefixed_vars():
    env = {**FULL_ENV, "GS1BELU_DOWNLOAD_CLIENT_ID": "should-never-be-read"}
    config = ServerConfig.from_env(env)
    assert config.credentials.client_id == "upload-id"


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
