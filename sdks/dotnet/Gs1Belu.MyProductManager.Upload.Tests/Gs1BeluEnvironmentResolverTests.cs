using Xunit;

namespace Gs1Belu.MyProductManager.Upload.Tests;

public class Gs1BeluEnvironmentResolverTests
{
    [Fact]
    public void Uat_derives_the_uat_hosts_and_audience()
    {
        Assert.Equal("api-uat.gs1belu.org", Gs1BeluEnvironmentResolver.ApiHost(Gs1BeluEnvironment.Uat));
        Assert.Equal("login-uat.gs1belu.org", Gs1BeluEnvironmentResolver.TokenHost(Gs1BeluEnvironment.Uat));
        Assert.Equal("https://api-uat.gs1belu.org/", Gs1BeluEnvironmentResolver.Audience(Gs1BeluEnvironment.Uat));
        Assert.Equal("https://login-uat.gs1belu.org/oauth/token", Gs1BeluEnvironmentResolver.TokenEndpoint(Gs1BeluEnvironment.Uat).ToString());
        Assert.Equal("https://api-uat.gs1belu.org/myproductmanager/upload/v17", Gs1BeluEnvironmentResolver.BaseUrl(Gs1BeluEnvironment.Uat, "v17"));
    }

    [Fact]
    public void Prod_derives_the_prod_hosts_and_audience()
    {
        Assert.Equal("api.gs1belu.org", Gs1BeluEnvironmentResolver.ApiHost(Gs1BeluEnvironment.Prod));
        Assert.Equal("login.gs1belu.org", Gs1BeluEnvironmentResolver.TokenHost(Gs1BeluEnvironment.Prod));
        Assert.Equal("https://api.gs1belu.org/", Gs1BeluEnvironmentResolver.Audience(Gs1BeluEnvironment.Prod));
        Assert.Equal("https://login.gs1belu.org/oauth/token", Gs1BeluEnvironmentResolver.TokenEndpoint(Gs1BeluEnvironment.Prod).ToString());
    }

    [Fact]
    public void Audience_always_carries_the_mandatory_trailing_slash()
    {
        Assert.EndsWith("/", Gs1BeluEnvironmentResolver.Audience(Gs1BeluEnvironment.Uat));
        Assert.EndsWith("/", Gs1BeluEnvironmentResolver.Audience(Gs1BeluEnvironment.Prod));
    }

    [Fact]
    public void BaseUrl_honors_a_non_default_apiVersion()
    {
        Assert.Equal("https://api.gs1belu.org/myproductmanager/upload/v18", Gs1BeluEnvironmentResolver.BaseUrl(Gs1BeluEnvironment.Prod, "v18"));
    }
}
