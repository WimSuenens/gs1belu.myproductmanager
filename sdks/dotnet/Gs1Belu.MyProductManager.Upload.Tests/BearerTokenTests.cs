using System;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using Xunit;

namespace Gs1Belu.MyProductManager.Upload.Tests;

public class BearerTokenTests
{
    private static HttpResponseMessage TokenResponse(int expiresInSeconds, string accessToken = "token-1") =>
        TestHarness.JsonResponse(HttpStatusCode.OK, $$"""{"access_token":"{{accessToken}}","expires_in":{{expiresInSeconds}},"token_type":"Bearer"}""");

    private static HttpResponseMessage EmptyTradeItemResponse() => TestHarness.JsonResponse(HttpStatusCode.OK, "{}");

    [Fact]
    public async Task Attaches_bearer_header_to_outgoing_requests()
    {
        var harness = new TestHarness();
        harness.TokenTransport.Enqueue(TokenResponse(3600));
        harness.ApiTransport.Enqueue(EmptyTradeItemResponse());

        await harness.Client.Client.Tradeitems["gtin-1"].GetAsync();

        var authHeader = Assert.Single(harness.ApiTransport.Requests).Headers.Authorization;
        Assert.NotNull(authHeader);
        Assert.Equal("Bearer", authHeader!.Scheme);
        Assert.Equal("token-1", authHeader.Parameter);
    }

    [Fact]
    public async Task Concurrent_burst_coalesces_onto_a_single_token_fetch()
    {
        var harness = new TestHarness();
        harness.TokenTransport.Enqueue(TokenResponse(3600));
        for (var i = 0; i < 5; i++)
        {
            harness.ApiTransport.Enqueue(EmptyTradeItemResponse());
        }

        var calls = Enumerable.Range(0, 5).Select(i => harness.Client.Client.Tradeitems[$"gtin-{i}"].GetAsync());
        await Task.WhenAll(calls);

        Assert.Single(harness.TokenTransport.Requests);
        Assert.Equal(5, harness.ApiTransport.Requests.Count);
    }

    [Fact]
    public async Task Cached_token_is_reused_while_still_within_the_skew_window()
    {
        var harness = new TestHarness();
        harness.TokenTransport.Enqueue(TokenResponse(3600));
        harness.ApiTransport.Enqueue(EmptyTradeItemResponse());
        harness.ApiTransport.Enqueue(EmptyTradeItemResponse());

        await harness.Client.Client.Tradeitems["gtin-1"].GetAsync();
        await harness.Client.Client.Tradeitems["gtin-2"].GetAsync();

        Assert.Single(harness.TokenTransport.Requests);
    }

    [Fact]
    public async Task Token_within_the_skew_margin_of_expiry_is_refetched()
    {
        // expires_in=0 puts the token inside any positive skew margin immediately, so the very next
        // call must refetch rather than reuse the cache.
        var harness = new TestHarness(skewMargin: TimeSpan.FromMilliseconds(50));
        harness.TokenTransport.Enqueue(TokenResponse(expiresInSeconds: 0, accessToken: "token-1"));
        harness.ApiTransport.Enqueue(EmptyTradeItemResponse());
        await harness.Client.Client.Tradeitems["gtin-1"].GetAsync();

        harness.TokenTransport.Enqueue(TokenResponse(expiresInSeconds: 3600, accessToken: "token-2"));
        harness.ApiTransport.Enqueue(EmptyTradeItemResponse());
        await harness.Client.Client.Tradeitems["gtin-2"].GetAsync();

        Assert.Equal(2, harness.TokenTransport.Requests.Count);
        Assert.Equal("token-2", harness.ApiTransport.Requests[1].Headers.Authorization!.Parameter);
    }

    [Fact]
    public async Task Unauthorized_response_forces_a_refresh_and_retries_once()
    {
        var harness = new TestHarness();
        harness.TokenTransport.Enqueue(TokenResponse(3600, accessToken: "token-1"));
        harness.ApiTransport.Enqueue(_ => new HttpResponseMessage(HttpStatusCode.Unauthorized));
        harness.TokenTransport.Enqueue(TokenResponse(3600, accessToken: "token-2"));
        harness.ApiTransport.Enqueue(EmptyTradeItemResponse());

        await harness.Client.Client.Tradeitems["gtin-1"].GetAsync();

        Assert.Equal(2, harness.TokenTransport.Requests.Count);
        Assert.Equal(2, harness.ApiTransport.Requests.Count);
        Assert.Equal("token-2", harness.ApiTransport.Requests[1].Headers.Authorization!.Parameter);
    }
}
