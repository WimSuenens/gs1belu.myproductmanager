using System.Collections.Generic;
using System.Net;
using System.Threading.Tasks;
using Xunit;

namespace Gs1Belu.MyProductManager.Download.Tests;

public class ListAllTradeItemsTests
{
    private static void EnqueueAuth(TestHarness harness) =>
        harness.TokenTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"access_token":"token-1","expires_in":3600}"""));

    [Fact]
    public async Task Yields_every_item_across_every_page_and_stops_at_the_terminal_page()
    {
        var harness = new TestHarness();
        EnqueueAuth(harness);
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(
            HttpStatusCode.OK,
            """{"_embedded":{"tradeItems":[{"gtin":"00000000000001"},{"gtin":"00000000000002"}]},"_links":{"next":{"href":"https://fake-api.test/myproductmanager/download/v17/tradeitems?cursor=abc"}}}"""));
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(
            HttpStatusCode.OK,
            """{"_embedded":{"tradeItems":[{"gtin":"00000000000003"}]}}"""));

        var gtins = new List<string?>();
        await foreach (var item in harness.Client.ListAllTradeItemsAsync())
        {
            gtins.Add(item.Gtin);
        }

        Assert.Equal(new[] { "00000000000001", "00000000000002", "00000000000003" }, gtins);
        Assert.Equal(2, harness.ApiTransport.Requests.Count);
        Assert.Contains("cursor=abc", harness.ApiTransport.Requests[1].RequestUri!.Query);
    }

    [Fact]
    public async Task Stops_immediately_when_the_first_page_has_no_next_link()
    {
        var harness = new TestHarness();
        EnqueueAuth(harness);
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(
            HttpStatusCode.OK,
            """{"_embedded":{"tradeItems":[{"gtin":"00000000000001"}]}}"""));

        var items = new List<Models.TradeItem>();
        await foreach (var item in harness.Client.ListAllTradeItemsAsync())
        {
            items.Add(item);
        }

        Assert.Single(items);
        Assert.Single(harness.ApiTransport.Requests);
    }

    [Fact]
    public async Task Empty_result_set_yields_nothing()
    {
        var harness = new TestHarness();
        EnqueueAuth(harness);
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"_embedded":{"tradeItems":[]}}"""));

        var items = await harness.Client.ListAllTradeItemsAsync().ToListAsync();

        Assert.Empty(items);
    }
}

internal static class AsyncEnumerableTestExtensions
{
    public static async Task<List<T>> ToListAsync<T>(this IAsyncEnumerable<T> source)
    {
        var result = new List<T>();
        await foreach (var item in source)
        {
            result.Add(item);
        }

        return result;
    }
}
