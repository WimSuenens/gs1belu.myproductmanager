using System;
using System.Linq;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;
using Gs1Belu.MyProductManager.Upload.Auth;
using Gs1Belu.MyProductManager.Upload.UploadValidation;
using Microsoft.Kiota.Abstractions;
using Microsoft.Kiota.Abstractions.Authentication;
using Microsoft.Kiota.Http.HttpClientLibrary;

namespace Gs1Belu.MyProductManager.Upload;

/// <summary>
/// The authenticated, ergonomic entry point for the Upload API. The public constructor takes only
/// <see cref="Gs1BeluEnvironment"/> + an <paramref name="apiVersion"/> + a credential set — the base
/// URL, token host, and OAuth <c>audience</c> are all derived (see
/// <see cref="Gs1BeluEnvironmentResolver"/>), so a consumer cannot misconfigure any of them.
/// </summary>
public sealed class Gs1BeluUploadClient
{
    public const string DefaultApiVersion = "v17";

    private readonly IRequestAdapter _requestAdapter;

    /// <summary>The generated fluent client, authenticated and ready to use for anything beyond the ergonomic helpers.</summary>
    public UploadClient Client { get; }

    public Gs1BeluUploadClient(Gs1BeluEnvironment environment, Gs1BeluCredentials credentials, string apiVersion = DefaultApiVersion)
        : this(BuildRequestAdapter(environment, credentials, apiVersion))
    {
    }

    /// <summary>
    /// Testability seam: wraps a caller-supplied <see cref="IRequestAdapter"/> directly, skipping all
    /// derivation. Consumers never see this constructor's shape — tests build the adapter against a
    /// fake HTTP transport and a mocked token endpoint, exactly the hook reserved for this purpose.
    /// </summary>
    internal Gs1BeluUploadClient(IRequestAdapter requestAdapter)
    {
        _requestAdapter = requestAdapter;
        Client = new UploadClient(requestAdapter);
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
    /// Submits <paramref name="tradeItem"/> and polls <c>GET /tradeitems/{gtin}</c> until
    /// <c>metaData.status</c> leaves <c>pendingValidation</c>, returning the settled verdict. The
    /// POST itself always answers <c>201</c> with an empty body regardless of data errors — this is
    /// the method that actually tells the caller whether GS1 accepted the item.
    /// </summary>
    /// <param name="tradeItem">The trade item to upsert. <see cref="Models.TradeItem.Gtin"/> is required.</param>
    /// <param name="pollInterval">Delay between polls. Defaults to 2 seconds.</param>
    /// <param name="timeout">Bounded wait before giving up. Defaults to 2 minutes.</param>
    public async Task<UploadValidationResult> UploadAndAwaitValidationAsync(
        Models.TradeItem tradeItem,
        TimeSpan? pollInterval = null,
        TimeSpan? timeout = null,
        CancellationToken cancellationToken = default)
    {
        _ = tradeItem ?? throw new ArgumentNullException(nameof(tradeItem));
        var gtin = tradeItem.Gtin ?? throw new ArgumentException("TradeItem.Gtin is required.", nameof(tradeItem));
        Gs1BeluIdentifierValidation.AssertValidGtin(gtin);

        await Client.Tradeitems.PostAsync(tradeItem, cancellationToken: cancellationToken).ConfigureAwait(false);

        var interval = pollInterval ?? TimeSpan.FromSeconds(2);
        var boundedWait = timeout ?? TimeSpan.FromMinutes(2);
        var deadline = DateTimeOffset.UtcNow + boundedWait;

        while (true)
        {
            var envelope = await GetStatusEnvelopeAsync(gtin, cancellationToken).ConfigureAwait(false);
            var rawStatus = envelope?.MetaData?.Status;
            if (!string.Equals(rawStatus, "pendingValidation", StringComparison.Ordinal))
            {
                return ToResult(gtin, envelope);
            }

            if (DateTimeOffset.UtcNow >= deadline)
            {
                throw new TimeoutException($"Validation for GTIN '{gtin}' did not leave pendingValidation within {boundedWait}.");
            }

            await Task.Delay(interval, cancellationToken).ConfigureAwait(false);
        }
    }

    private Task<TradeItemStatusEnvelope?> GetStatusEnvelopeAsync(string gtin, CancellationToken cancellationToken)
    {
        var requestInfo = Client.Tradeitems[gtin].ToGetRequestInformation();
        return _requestAdapter.SendAsync(requestInfo, TradeItemStatusEnvelope.CreateFromDiscriminatorValue, errorMapping: null, cancellationToken: cancellationToken);
    }

    private static UploadValidationResult ToResult(string gtin, TradeItemStatusEnvelope? envelope)
    {
        var status = envelope?.MetaData?.Status switch
        {
            "active" => UploadValidationStatus.Active,
            "incomplete" => UploadValidationStatus.Incomplete,
            _ => UploadValidationStatus.Unknown,
        };
        var issues = envelope?.MetaData?.ValidationResults?
            .Select(i => new UploadValidationIssue(i.Severity ?? string.Empty, i.Code ?? string.Empty, i.Message ?? string.Empty))
            .ToArray() ?? Array.Empty<UploadValidationIssue>();
        return new UploadValidationResult(gtin, status, issues);
    }
}
