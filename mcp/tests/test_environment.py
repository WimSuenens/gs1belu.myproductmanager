from gs1belu_mpm_mcp.environment import (
    Environment,
    api_host,
    audience,
    base_url,
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
    assert (
        base_url(Environment.PROD, "upload", "v17")
        == "https://api.gs1belu.org/myproductmanager/upload/v17"
    )
    assert (
        base_url(Environment.UAT, "download", "v17")
        == "https://api-uat.gs1belu.org/myproductmanager/download/v17"
    )
