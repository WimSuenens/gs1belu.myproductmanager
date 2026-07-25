using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace Gs1Belu.MyProductManager.Download.Auth;

/// <summary>
/// Paces requests to stay under the API's 10 req/s cap. A sliding window of recent request
/// timestamps is kept under a lock; a request that would exceed the cap waits until the oldest
/// timestamp in the window ages out, rather than firing and risking a throttle response.
/// </summary>
internal sealed class RateLimitHandler : DelegatingHandler
{
    private readonly int _maxRequestsPerWindow;
    private readonly TimeSpan _window;
    private readonly Queue<DateTimeOffset> _recentRequestTimestamps = new();
    private readonly SemaphoreSlim _gate = new(1, 1);

    public RateLimitHandler(int maxRequestsPerWindow = 10, TimeSpan? window = null)
    {
        _maxRequestsPerWindow = maxRequestsPerWindow;
        _window = window ?? TimeSpan.FromSeconds(1);
    }

    protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        await WaitForSlotAsync(cancellationToken).ConfigureAwait(false);
        return await base.SendAsync(request, cancellationToken).ConfigureAwait(false);
    }

    private async Task WaitForSlotAsync(CancellationToken cancellationToken)
    {
        while (true)
        {
            TimeSpan delay;
            await _gate.WaitAsync(cancellationToken).ConfigureAwait(false);
            try
            {
                var now = DateTimeOffset.UtcNow;
                while (_recentRequestTimestamps.Count > 0 && now - _recentRequestTimestamps.Peek() >= _window)
                {
                    _recentRequestTimestamps.Dequeue();
                }

                if (_recentRequestTimestamps.Count < _maxRequestsPerWindow)
                {
                    _recentRequestTimestamps.Enqueue(now);
                    return;
                }

                delay = _window - (now - _recentRequestTimestamps.Peek());
            }
            finally
            {
                _gate.Release();
            }

            if (delay > TimeSpan.Zero)
            {
                await Task.Delay(delay, cancellationToken).ConfigureAwait(false);
            }
        }
    }
}
