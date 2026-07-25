using System;
using System.Net.Http;
using Gs1Belu.MyProductManager.Download.Auth;
using Microsoft.Kiota.Abstractions.Authentication;
using Microsoft.Kiota.Http.HttpClientLibrary;

namespace Gs1Belu.MyProductManager.Download.Tests;

/// <summary>
/// The test seam Testing Decisions §"The seam" describes: builds the exact same production auth +
/// middleware pipeline as <see cref="Gs1BeluDownloadClient"/>'s public constructor, but wired to fake
/// HTTP transports (API + token endpoint) instead of the real network. Consumers never see this —
/// it exists only so tests can assert on observable HTTP behavior through the real classes.
/// </summary>
internal sealed class TestHarness
{
    public const string FakeBaseUrl = "https://fake-api.test/myproductmanager/download/v17";

    public FakeHttpMessageHandler ApiTransport { get; } = new();
    public FakeHttpMessageHandler TokenTransport { get; } = new();
    public Gs1BeluAccessTokenProvider TokenProvider { get; }
    public Gs1BeluDownloadClient Client { get; }

    public TestHarness(
        Gs1BeluCredentials? credentials = null,
        TimeSpan? skewMargin = null,
        int rateLimitPerWindow = 1000,
        TimeSpan? rateLimitWindow = null)
    {
        credentials ??= new Gs1BeluCredentials("fake-client-id", "fake-client-secret", "fake-subscription-key");

        TokenProvider = new Gs1BeluAccessTokenProvider(
            credentials,
            new Uri("https://fake-token.test/oauth/token"),
            audience: "https://fake-api.test/",
            allowedHostsValidator: new AllowedHostsValidator(new[] { "fake-api.test" }),
            tokenTransportHandler: TokenTransport,
            skewMargin: skewMargin);

        var authProvider = new BaseBearerTokenAuthenticationProvider(TokenProvider);
        var handlers = new DelegatingHandler[]
        {
            new SubscriptionKeyHandler(credentials.SubscriptionKey),
            new BearerRetryHandler(TokenProvider),
            new RateLimitHandler(rateLimitPerWindow, rateLimitWindow),
        };
        var chainHead = KiotaClientFactory.ChainHandlersCollectionAndGetFirstLink(ApiTransport, handlers)
            ?? throw new InvalidOperationException("Kiota did not return a handler chain.");
        var httpClient = new HttpClient(chainHead);
        var adapter = new HttpClientRequestAdapter(authProvider, httpClient: httpClient) { BaseUrl = FakeBaseUrl };

        Client = new Gs1BeluDownloadClient(adapter);
    }

    public static HttpResponseMessage JsonResponse(System.Net.HttpStatusCode statusCode, string json) => new(statusCode)
    {
        Content = new StringContent(json, System.Text.Encoding.UTF8, "application/json"),
    };
}
