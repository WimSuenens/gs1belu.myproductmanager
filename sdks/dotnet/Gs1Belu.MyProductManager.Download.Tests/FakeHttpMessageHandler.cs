using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

namespace Gs1Belu.MyProductManager.Download.Tests;

/// <summary>
/// The fake HTTP transport the test seam is built on: a queue of canned responses (or response
/// factories, for status-code sequencing) plus a record of every request actually sent, so tests can
/// assert on headers, URLs, and call counts without any real network I/O.
/// </summary>
internal sealed class FakeHttpMessageHandler : HttpMessageHandler
{
    private readonly Queue<Func<HttpRequestMessage, HttpResponseMessage>> _responses = new();

    public List<HttpRequestMessage> Requests { get; } = new();

    public void Enqueue(HttpResponseMessage response) => _responses.Enqueue(_ => response);

    public void Enqueue(Func<HttpRequestMessage, HttpResponseMessage> respond) => _responses.Enqueue(respond);

    protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken)
    {
        Requests.Add(request);
        if (_responses.Count == 0)
        {
            throw new InvalidOperationException($"No fake response queued for {request.Method} {request.RequestUri}.");
        }

        var response = _responses.Dequeue()(request);
        // A real HttpMessageHandler always sets this; Kiota's RetryHandler reads it to know what
        // request to clone and resend, and silently gives up (no retry) if it's null.
        response.RequestMessage ??= request;
        return Task.FromResult(response);
    }
}
