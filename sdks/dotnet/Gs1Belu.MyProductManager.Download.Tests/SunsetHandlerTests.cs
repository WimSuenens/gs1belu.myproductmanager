using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using Gs1Belu.MyProductManager.Download.Auth;
using Xunit;

namespace Gs1Belu.MyProductManager.Download.Tests;

public class SunsetHandlerTests
{
    [Fact]
    public async Task Surfaces_a_future_sunset_date_with_the_parsed_timestamp()
    {
        var messages = new List<string>();
        var notices = new List<SunsetNotice>();
        var future = DateTimeOffset.UtcNow.AddDays(30);
        var transport = new FakeHttpMessageHandler();
        transport.Enqueue(ResponseWithSunset(future.ToString("R")));
        var handler = new SunsetHandler(messages.Add, notices.Add) { InnerHandler = transport };
        using var client = new HttpClient(handler);

        await client.SendAsync(new HttpRequestMessage(HttpMethod.Get, "https://fake.test/tradeitems"));

        var notice = Assert.Single(notices);
        Assert.NotNull(notice.ParsedAt);
        Assert.False(notice.IsPast);
        var message = Assert.Single(messages);
        Assert.Contains("Plan a version migration", message);
    }

    [Fact]
    public async Task Produces_no_notice_when_the_header_is_absent()
    {
        var messages = new List<string>();
        var notices = new List<SunsetNotice>();
        var transport = new FakeHttpMessageHandler();
        transport.Enqueue(new HttpResponseMessage(HttpStatusCode.OK));
        var handler = new SunsetHandler(messages.Add, notices.Add) { InnerHandler = transport };
        using var client = new HttpClient(handler);

        await client.SendAsync(new HttpRequestMessage(HttpMethod.Get, "https://fake.test/tradeitems"));

        Assert.Empty(messages);
        Assert.Empty(notices);
    }

    [Fact]
    public async Task Flags_a_past_sunset_date_as_already_sunset()
    {
        var notices = new List<SunsetNotice>();
        var past = DateTimeOffset.UtcNow.AddDays(-1);
        var transport = new FakeHttpMessageHandler();
        transport.Enqueue(ResponseWithSunset(past.ToString("R")));
        var handler = new SunsetHandler(null, notices.Add) { InnerHandler = transport };
        using var client = new HttpClient(handler);

        await client.SendAsync(new HttpRequestMessage(HttpMethod.Get, "https://fake.test/tradeitems"));

        var notice = Assert.Single(notices);
        Assert.NotNull(notice.ParsedAt);
        Assert.True(notice.IsPast);
    }

    [Fact]
    public async Task Surfaces_the_raw_value_without_throwing_when_the_header_is_unparseable()
    {
        var notices = new List<SunsetNotice>();
        var transport = new FakeHttpMessageHandler();
        transport.Enqueue(ResponseWithSunset("not-a-date"));
        var handler = new SunsetHandler(null, notices.Add) { InnerHandler = transport };
        using var client = new HttpClient(handler);

        await client.SendAsync(new HttpRequestMessage(HttpMethod.Get, "https://fake.test/tradeitems"));

        var notice = Assert.Single(notices);
        Assert.Equal("not-a-date", notice.Raw);
        Assert.Null(notice.ParsedAt);
        Assert.False(notice.IsPast);
    }

    private static HttpResponseMessage ResponseWithSunset(string value)
    {
        var response = new HttpResponseMessage(HttpStatusCode.OK);
        response.Headers.TryAddWithoutValidation("Sunset", value);
        return response;
    }
}
