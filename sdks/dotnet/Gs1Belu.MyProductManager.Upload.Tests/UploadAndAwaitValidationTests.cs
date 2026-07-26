using System;
using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using Gs1Belu.MyProductManager.Upload.UploadValidation;
using Xunit;

namespace Gs1Belu.MyProductManager.Upload.Tests;

public class UploadAndAwaitValidationTests
{
    private const string ValidGtin = "01234567890128";

    private static void EnqueueAuth(TestHarness harness) =>
        harness.TokenTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"access_token":"token-1","expires_in":3600}"""));

    [Fact]
    public async Task Uploads_then_polls_until_settled_and_returns_the_verdict()
    {
        var harness = new TestHarness();
        EnqueueAuth(harness);
        harness.ApiTransport.Enqueue(new HttpResponseMessage(HttpStatusCode.Created));
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"metaData":{"status":"pendingValidation"}}"""));
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(
            HttpStatusCode.OK,
            """{"metaData":{"status":"active","validationResults":[{"severity":"warning","code":"VR_FMCGB2C_0257","message":"no image provided"}]}}"""));

        var tradeItem = new Models.TradeItem { Gtin = ValidGtin };
        var result = await harness.Client.UploadAndAwaitValidationAsync(tradeItem, pollInterval: TimeSpan.FromMilliseconds(5));

        Assert.Equal(ValidGtin, result.Gtin);
        Assert.Equal(UploadValidationStatus.Active, result.Status);
        var issue = Assert.Single(result.Issues);
        Assert.Equal("VR_FMCGB2C_0257", issue.Code);
        Assert.Equal(3, harness.ApiTransport.Requests.Count);
        Assert.Equal(HttpMethod.Post, harness.ApiTransport.Requests[0].Method);
        Assert.Equal(HttpMethod.Get, harness.ApiTransport.Requests[1].Method);
        Assert.Equal(HttpMethod.Get, harness.ApiTransport.Requests[2].Method);
    }

    [Fact]
    public async Task Incomplete_status_is_reported_without_throwing()
    {
        var harness = new TestHarness();
        EnqueueAuth(harness);
        harness.ApiTransport.Enqueue(new HttpResponseMessage(HttpStatusCode.Created));
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(
            HttpStatusCode.OK,
            """{"metaData":{"status":"incomplete","validationResults":[{"severity":"error","code":"VR_FMCGB2C_0315","message":"missing field"}]}}"""));

        var tradeItem = new Models.TradeItem { Gtin = ValidGtin };
        var result = await harness.Client.UploadAndAwaitValidationAsync(tradeItem, pollInterval: TimeSpan.FromMilliseconds(5));

        Assert.Equal(UploadValidationStatus.Incomplete, result.Status);
    }

    [Fact]
    public async Task Bounded_wait_times_out_if_validation_never_settles()
    {
        var harness = new TestHarness();
        EnqueueAuth(harness);
        harness.ApiTransport.Enqueue(new HttpResponseMessage(HttpStatusCode.Created));
        for (var i = 0; i < 100; i++)
        {
            harness.ApiTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"metaData":{"status":"pendingValidation"}}"""));
        }

        var tradeItem = new Models.TradeItem { Gtin = ValidGtin };

        await Assert.ThrowsAsync<TimeoutException>(() => harness.Client.UploadAndAwaitValidationAsync(
            tradeItem,
            pollInterval: TimeSpan.FromMilliseconds(5),
            timeout: TimeSpan.FromMilliseconds(50)));
    }

    [Fact]
    public async Task Rejects_a_trade_item_with_a_malformed_gtin()
    {
        var harness = new TestHarness();
        var tradeItem = new Models.TradeItem { Gtin = "not-a-gtin" };

        await Assert.ThrowsAsync<ArgumentException>(() => harness.Client.UploadAndAwaitValidationAsync(tradeItem));
    }
}
