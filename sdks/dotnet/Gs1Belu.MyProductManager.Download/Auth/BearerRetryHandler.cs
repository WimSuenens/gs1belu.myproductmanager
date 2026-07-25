using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading;
using System.Threading.Tasks;

namespace Gs1Belu.MyProductManager.Download.Auth;

/// <summary>
/// Safety net under the proactive skew refresh: if a request still comes back <c>401</c> (the token
/// was revoked early, or clock drift outran the skew margin), force a fresh token fetch and retry
/// exactly once. The Kiota request adapter attaches the <c>Authorization</c> header before the
/// request reaches this pipeline handler, so a retry must overwrite that header itself rather than
/// asking the adapter to re-authenticate.
/// </summary>
internal sealed class BearerRetryHandler : DelegatingHandler
{
    private readonly Gs1BeluAccessTokenProvider _tokenProvider;

    public BearerRetryHandler(Gs1BeluAccessTokenProvider tokenProvider)
    {
        _tokenProvider = tokenProvider;
    }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var response = await base.SendAsync(request, cancellationToken).ConfigureAwait(false);
        if (response.StatusCode != HttpStatusCode.Unauthorized)
        {
            return response;
        }

        var freshToken = await _tokenProvider.RefreshAsync(cancellationToken).ConfigureAwait(false);
        using var retryRequest = await CloneAsync(request).ConfigureAwait(false);
        retryRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", freshToken);

        response.Dispose();
        return await base.SendAsync(retryRequest, cancellationToken).ConfigureAwait(false);
    }

    private static async Task<HttpRequestMessage> CloneAsync(HttpRequestMessage request)
    {
        var clone = new HttpRequestMessage(request.Method, request.RequestUri)
        {
            Version = request.Version,
        };
        foreach (var header in request.Headers)
        {
            clone.Headers.TryAddWithoutValidation(header.Key, header.Value);
        }

        if (request.Content is not null)
        {
            var bytes = await request.Content.ReadAsByteArrayAsync().ConfigureAwait(false);
            var content = new ByteArrayContent(bytes);
            foreach (var header in request.Content.Headers)
            {
                content.Headers.TryAddWithoutValidation(header.Key, header.Value);
            }
            clone.Content = content;
        }

        return clone;
    }
}
