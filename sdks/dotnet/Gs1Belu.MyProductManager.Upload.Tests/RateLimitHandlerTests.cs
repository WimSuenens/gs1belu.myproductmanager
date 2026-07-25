using System;
using System.Diagnostics;
using System.Net;
using System.Threading.Tasks;
using Xunit;

namespace Gs1Belu.MyProductManager.Upload.Tests;

public class RateLimitHandlerTests
{
    [Fact]
    public async Task A_request_beyond_the_cap_is_paced_until_the_window_frees_a_slot()
    {
        var harness = new TestHarness(rateLimitPerWindow: 2, rateLimitWindow: TimeSpan.FromMilliseconds(200));
        harness.TokenTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"access_token":"token-1","expires_in":3600}"""));
        for (var i = 0; i < 3; i++)
        {
            harness.ApiTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, "{}"));
        }

        var stopwatch = Stopwatch.StartNew();
        await harness.Client.Client.Tradeitems["gtin-1"].GetAsync();
        await harness.Client.Client.Tradeitems["gtin-2"].GetAsync();
        await harness.Client.Client.Tradeitems["gtin-3"].GetAsync();
        stopwatch.Stop();

        Assert.True(
            stopwatch.ElapsedMilliseconds >= 180,
            $"expected the 3rd call in a 2-per-200ms window to be paced, took {stopwatch.ElapsedMilliseconds}ms");
    }
}
