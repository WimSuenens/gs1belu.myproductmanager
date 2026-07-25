using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using Gs1Belu.MyProductManager.Download.Auth;
using Gs1Belu.MyProductManager.Download.Tradeitems;
using Microsoft.Kiota.Abstractions;
using Microsoft.Kiota.Abstractions.Authentication;
using Microsoft.Kiota.Http.HttpClientLibrary;

namespace Gs1Belu.MyProductManager.Download;

/// <summary>
/// The authenticated, ergonomic entry point for the Download API. The public constructor takes only
/// <see cref="Gs1BeluEnvironment"/> + an <paramref name="apiVersion"/> + a credential set — the base
/// URL, token host, and OAuth <c>audience</c> are all derived (see
/// <see cref="Gs1BeluEnvironmentResolver"/>), so a consumer cannot misconfigure any of them.
/// </summary>
public sealed class Gs1BeluDownloadClient
{
    public const string DefaultApiVersion = "v17";

    private readonly IRequestAdapter _requestAdapter;

    /// <summary>The generated fluent client, authenticated and ready to use for anything beyond the ergonomic helpers.</summary>
    public DownloadClient Client { get; }

    public Gs1BeluDownloadClient(Gs1BeluEnvironment environment, Gs1BeluCredentials credentials, string apiVersion = DefaultApiVersion)
        : this(BuildRequestAdapter(environment, credentials, apiVersion))
    {
    }

    /// <summary>
    /// Testability seam: wraps a caller-supplied <see cref="IRequestAdapter"/> directly, skipping all
    /// derivation. Consumers never see this constructor's shape — tests build the adapter against a
    /// fake HTTP transport and a mocked token endpoint, exactly the hook reserved for this purpose.
    /// </summary>
    internal Gs1BeluDownloadClient(IRequestAdapter requestAdapter)
    {
        _requestAdapter = requestAdapter;
        Client = new DownloadClient(requestAdapter);
    }

    private static IRequestAdapter BuildRequestAdapter(Gs1BeluEnvironment environment, Gs1BeluCredentials credentials, string apiVersion)
    {
        var allowedHosts = new AllowedHostsValidator(new[] { Gs1BeluEnvironmentResolver.ApiHost(environment) });
        var tokenProvider = new Gs1BeluAccessTokenProvider(
            credentials,
            Gs1BeluEnvironmentResolver.TokenEndpoint(environment),
            Gs1BeluEnvironmentResolver.Audience(environment),
            allowedHosts);
        var authProvider = new BaseBearerTokenAuthenticationProvider(tokenProvider);

        var handlers = KiotaClientFactory.CreateDefaultHandlers();
        handlers.Add(new SubscriptionKeyHandler(credentials.SubscriptionKey));
        handlers.Add(new BearerRetryHandler(tokenProvider));
        handlers.Add(new RateLimitHandler());

        var chainHead = KiotaClientFactory.ChainHandlersCollectionAndGetFirstLink(
            KiotaClientFactory.GetDefaultHttpMessageHandler(),
            handlers.ToArray())
            ?? throw new InvalidOperationException("Kiota did not return a handler chain.");
        var httpClient = new HttpClient(chainHead);

        return new HttpClientRequestAdapter(authProvider, httpClient: httpClient)
        {
            BaseUrl = Gs1BeluEnvironmentResolver.BaseUrl(environment, apiVersion),
        };
    }

    /// <summary>
    /// Iterates every trade item across every page, auto-following the HAL <c>_links.next</c> href
    /// the server returns — including whatever query parameters the server chose to carry forward —
    /// rather than re-deriving pagination ourselves. This side-steps the manuals' documented
    /// page-size conflict (100 vs. 1000): the caller never sees a page size unless they set one.
    /// </summary>
    /// <param name="configureQuery">Optional initial query parameters (e.g. <c>informationProviderGLN</c>, <c>limit</c>).</param>
    public async IAsyncEnumerable<Models.TradeItem> ListAllTradeItemsAsync(
        Action<TradeitemsRequestBuilder.TradeitemsRequestBuilderGetQueryParameters>? configureQuery = null,
        [EnumeratorCancellation] CancellationToken cancellationToken = default)
    {
        var page = await Client.Tradeitems.GetAsync(
            configureQuery is null ? null : config => configureQuery(config.QueryParameters),
            cancellationToken).ConfigureAwait(false);

        while (page is not null)
        {
            foreach (var item in page.Embedded?.TradeItems ?? Enumerable.Empty<Models.TradeItem>())
            {
                yield return item;
            }

            var nextHref = page.Links?.Next?.Href;
            if (string.IsNullOrEmpty(nextHref))
            {
                yield break;
            }

            var requestInfo = new RequestInformation { HttpMethod = Method.GET, URI = new Uri(nextHref) };
            page = await _requestAdapter.SendAsync(requestInfo, Models.TradeItemResponse.CreateFromDiscriminatorValue, errorMapping: null, cancellationToken)
                .ConfigureAwait(false);
        }
    }
}
