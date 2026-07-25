using System;

namespace Gs1Belu.MyProductManager.Download;

/// <summary>
/// Pure derivation of the API host, OAuth token host, and OAuth <c>audience</c> from a
/// <see cref="Gs1BeluEnvironment"/>. There is no caller-supplied host or base URL anywhere in the
/// public surface: a fumbled <c>audience</c> is exactly the GS1 manuals' <c>access_denied</c> failure,
/// so it is derived here, once, instead of being a field a consumer can get wrong.
/// </summary>
internal static class Gs1BeluEnvironmentResolver
{
    private const string ApiSegment = "download";

    internal static string ApiHost(Gs1BeluEnvironment environment) => environment switch
    {
        Gs1BeluEnvironment.Uat => "api-uat.gs1belu.org",
        Gs1BeluEnvironment.Prod => "api.gs1belu.org",
        _ => throw new ArgumentOutOfRangeException(nameof(environment), environment, message: null),
    };

    internal static string TokenHost(Gs1BeluEnvironment environment) => environment switch
    {
        Gs1BeluEnvironment.Uat => "login-uat.gs1belu.org",
        Gs1BeluEnvironment.Prod => "login.gs1belu.org",
        _ => throw new ArgumentOutOfRangeException(nameof(environment), environment, message: null),
    };

    /// <summary>The OAuth <c>audience</c> claim, with the mandatory trailing slash baked in.</summary>
    internal static string Audience(Gs1BeluEnvironment environment) => $"https://{ApiHost(environment)}/";

    internal static Uri TokenEndpoint(Gs1BeluEnvironment environment) => new($"https://{TokenHost(environment)}/oauth/token");

    internal static string BaseUrl(Gs1BeluEnvironment environment, string apiVersion) =>
        $"https://{ApiHost(environment)}/myproductmanager/{ApiSegment}/{apiVersion}";
}
