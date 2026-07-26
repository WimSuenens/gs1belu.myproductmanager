using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using Gs1Belu.MyProductManager.Upload.Auth;
using Xunit;

namespace Gs1Belu.MyProductManager.Upload.Tests;

public class LoggingHandlerTests
{
    [Fact]
    public async Task Logs_the_method_url_and_resolved_status_of_a_successful_request()
    {
        var messages = new List<string>();
        var transport = new FakeHttpMessageHandler();
        transport.Enqueue(new HttpResponseMessage(HttpStatusCode.NoContent));
        var handler = new LoggingHandler(messages.Add) { InnerHandler = transport };
        using var client = new HttpClient(handler);

        await client.SendAsync(new HttpRequestMessage(HttpMethod.Get, "https://fake.test/tradeitems"));

        var message = Assert.Single(messages);
        Assert.Contains("GET", message);
        Assert.Contains("https://fake.test/tradeitems", message);
        Assert.Contains("204", message);
    }

    [Fact]
    public async Task Logs_a_failure_and_rethrows_when_the_downstream_call_throws()
    {
        var messages = new List<string>();
        var transport = new FakeHttpMessageHandler();
        transport.Enqueue(_ => throw new HttpRequestException("boom"));
        var handler = new LoggingHandler(messages.Add) { InnerHandler = transport };
        using var client = new HttpClient(handler);

        await Assert.ThrowsAsync<HttpRequestException>(() => client.SendAsync(new HttpRequestMessage(HttpMethod.Get, "https://fake.test/tradeitems")));

        var message = Assert.Single(messages);
        Assert.Contains("failed", message);
        Assert.Contains("boom", message);
    }
}
