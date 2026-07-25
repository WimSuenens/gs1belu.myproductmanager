using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Kiota.Abstractions.Authentication;

namespace Gs1Belu.MyProductManager.Upload.Auth;

/// <summary>
/// Fetches, caches, and proactively refreshes the OAuth2 client-credentials Bearer token used on
/// every request. The GS1 manuals warn that a client which re-authenticates on every call gets
/// disconnected, so the token is cached in memory and only refetched once it is within a skew
/// margin (60s by default) of its runtime <c>expires_in</c> — never a hardcoded 12h/24h figure,
/// since the manuals themselves disagree on which of those it is.
///
/// Concurrent callers coalesce onto a single in-flight fetch: the fetch happens while
/// <see cref="_fetchLock"/> is held, so a burst of callers blocks on the lock and then replays the
/// now-populated cache instead of each issuing its own token request.
/// </summary>
internal sealed class Gs1BeluAccessTokenProvider : IAccessTokenProvider
{
    private static readonly TimeSpan DefaultSkewMargin = TimeSpan.FromSeconds(60);
    private const string ForceRefreshKey = "forceRefresh";

    private readonly Gs1BeluCredentials _credentials;
    private readonly Uri _tokenEndpoint;
    private readonly string _audience;
    private readonly TimeSpan _skewMargin;
    private readonly HttpClient _tokenHttpClient;
    private readonly SemaphoreSlim _fetchLock = new(1, 1);

    private string? _cachedToken;
    private DateTimeOffset _cachedExpiresAt = DateTimeOffset.MinValue;

    public Gs1BeluAccessTokenProvider(
        Gs1BeluCredentials credentials,
        Uri tokenEndpoint,
        string audience,
        AllowedHostsValidator allowedHostsValidator,
        HttpMessageHandler? tokenTransportHandler = null,
        TimeSpan? skewMargin = null)
    {
        _credentials = credentials;
        _tokenEndpoint = tokenEndpoint;
        _audience = audience;
        _skewMargin = skewMargin ?? DefaultSkewMargin;
        _tokenHttpClient = tokenTransportHandler is null ? new HttpClient() : new HttpClient(tokenTransportHandler, disposeHandler: false);
        AllowedHostsValidator = allowedHostsValidator;
    }

    public AllowedHostsValidator AllowedHostsValidator { get; }

    public Task<string> GetAuthorizationTokenAsync(
        Uri uri,
        Dictionary<string, object>? additionalAuthenticationContext = null,
        CancellationToken cancellationToken = default)
    {
        var forceRefresh = additionalAuthenticationContext is not null
            && additionalAuthenticationContext.TryGetValue(ForceRefreshKey, out var flag)
            && flag is true;
        return GetTokenAsync(forceRefresh, cancellationToken);
    }

    /// <summary>
    /// Bypasses the cache and fetches a fresh token, still coalesced through the same single-flight
    /// lock. Called by <see cref="BearerRetryHandler"/> when a request comes back <c>401</c>.
    /// </summary>
    public Task<string> RefreshAsync(CancellationToken cancellationToken = default) => GetTokenAsync(forceRefresh: true, cancellationToken);

    private async Task<string> GetTokenAsync(bool forceRefresh, CancellationToken cancellationToken)
    {
        if (!forceRefresh && IsCacheValid())
        {
            return _cachedToken!;
        }

        await _fetchLock.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            if (!forceRefresh && IsCacheValid())
            {
                return _cachedToken!;
            }

            return await FetchTokenAsync(cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            _fetchLock.Release();
        }
    }

    private bool IsCacheValid() => _cachedToken is not null && DateTimeOffset.UtcNow < _cachedExpiresAt - _skewMargin;

    private async Task<string> FetchTokenAsync(CancellationToken cancellationToken)
    {
        using var request = new HttpRequestMessage(HttpMethod.Post, _tokenEndpoint)
        {
            Content = new FormUrlEncodedContent(new Dictionary<string, string>
            {
                ["grant_type"] = "client_credentials",
                ["client_id"] = _credentials.ClientId,
                ["client_secret"] = _credentials.ClientSecret,
                ["audience"] = _audience,
            }),
        };

        using var response = await _tokenHttpClient.SendAsync(request, cancellationToken).ConfigureAwait(false);
        response.EnsureSuccessStatusCode();

        using var responseStream = await response.Content.ReadAsStreamAsync().ConfigureAwait(false);
        var body = await JsonSerializer.DeserializeAsync<OAuthTokenResponse>(responseStream, cancellationToken: cancellationToken)
            .ConfigureAwait(false);
        if (body is null || string.IsNullOrEmpty(body.AccessToken))
        {
            throw new InvalidOperationException("The GS1 token endpoint returned no access_token.");
        }

        _cachedToken = body.AccessToken;
        _cachedExpiresAt = DateTimeOffset.UtcNow.AddSeconds(body.ExpiresIn);
        return _cachedToken;
    }

    private sealed class OAuthTokenResponse
    {
        [JsonPropertyName("access_token")]
        public string AccessToken { get; set; } = string.Empty;

        [JsonPropertyName("expires_in")]
        public long ExpiresIn { get; set; }
    }
}
