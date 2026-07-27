"""Pins host/audience derivation and the `GS1BELU_ENVIRONMENT` parse (#77's
safety-critical single-sourcing: neither server can drift on which host it talks to
because both build from this one copy)."""

import pytest

from _shared.environment import (
    ConfigError,
    Environment,
    api_host,
    audience,
    base_url,
    parse_environment,
    token_endpoint,
    token_host,
)


def test_uat_hosts():
    assert api_host(Environment.UAT) == "api-uat.gs1belu.org"
    assert token_host(Environment.UAT) == "login-uat.gs1belu.org"


def test_prod_hosts():
    assert api_host(Environment.PROD) == "api.gs1belu.org"
    assert token_host(Environment.PROD) == "login.gs1belu.org"


def test_audience_has_trailing_slash():
    assert audience(Environment.UAT) == "https://api-uat.gs1belu.org/"
    assert audience(Environment.PROD) == "https://api.gs1belu.org/"


def test_token_endpoint():
    assert token_endpoint(Environment.UAT) == "https://login-uat.gs1belu.org/oauth/token"


def test_base_url_derives_per_segment_and_version():
    assert base_url(Environment.PROD, "upload", "v17") == "https://api.gs1belu.org/myproductmanager/upload/v17"
    assert base_url(Environment.UAT, "download", "v17") == "https://api-uat.gs1belu.org/myproductmanager/download/v17"


def test_parse_environment_returns_the_matching_enum_member():
    assert parse_environment({"GS1BELU_ENVIRONMENT": "uat"}) is Environment.UAT
    assert parse_environment({"GS1BELU_ENVIRONMENT": "prod"}) is Environment.PROD


def test_parse_environment_is_case_and_whitespace_insensitive():
    assert parse_environment({"GS1BELU_ENVIRONMENT": " PROD "}) is Environment.PROD


def test_parse_environment_raises_when_missing():
    with pytest.raises(ConfigError):
        parse_environment({})


def test_parse_environment_raises_on_invalid_value():
    with pytest.raises(ConfigError):
        parse_environment({"GS1BELU_ENVIRONMENT": "staging"})
