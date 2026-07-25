using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace Gs1Belu.MyProductManager.Upload.Auth;

/// <summary>
/// Stamps the static <c>Ocp-Apim-Subscription-Key</c> header on every request. The subscription
/// key is deliberately never sent as the spec's alternative query-string parameter, since a secret
/// in the URL ends up in logs and proxy caches.
/// </summary>
internal sealed class SubscriptionKeyHandler : DelegatingHandler
{
    private const string HeaderName = "Ocp-Apim-Subscription-Key";
    private readonly string _subscriptionKey;

    public SubscriptionKeyHandler(string subscriptionKey)
    {
        _subscriptionKey = subscriptionKey;
    }

    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        request.Headers.Remove(HeaderName);
        request.Headers.Add(HeaderName, _subscriptionKey);
        return base.SendAsync(request, cancellationToken);
    }
}
