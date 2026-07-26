using System;
using System.Diagnostics;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace Gs1Belu.MyProductManager.Download.Auth;

/// <summary>
/// Optional request/response logging, so a consumer can diagnose auth and API issues without
/// patching the SDK. Dependency-free by design: it reports through a plain delegate rather than
/// pulling in a logging framework the consumer may not already use.
/// </summary>
internal sealed class LoggingHandler : DelegatingHandler
{
    private readonly Action<string> _log;

    public LoggingHandler(Action<string> log)
    {
        _log = log;
    }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        var stopwatch = Stopwatch.StartNew();
        try
        {
            var response = await base.SendAsync(request, cancellationToken).ConfigureAwait(false);
            stopwatch.Stop();
            _log($"{request.Method} {request.RequestUri} -> {(int)response.StatusCode} ({stopwatch.ElapsedMilliseconds} ms)");
            return response;
        }
        catch (Exception ex)
        {
            stopwatch.Stop();
            _log($"{request.Method} {request.RequestUri} -> failed after {stopwatch.ElapsedMilliseconds} ms: {ex.Message}");
            throw;
        }
    }
}
