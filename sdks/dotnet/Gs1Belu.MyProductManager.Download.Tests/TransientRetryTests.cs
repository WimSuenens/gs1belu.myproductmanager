using System.Net;
using System.Net.Http;
using System.Threading.Tasks;
using Xunit;

namespace Gs1Belu.MyProductManager.Download.Tests;

public class TransientRetryTests
{
    [Fact]
    public async Task A_transient_503_is_retried_by_the_default_pipeline_and_eventually_succeeds()
    {
        var harness = new TestHarness();
        harness.TokenTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"access_token":"token-1","expires_in":3600}"""));
        harness.ApiTransport.Enqueue(_ =>
        {
            var response = new HttpResponseMessage(HttpStatusCode.ServiceUnavailable);
            response.Headers.Add("Retry-After", "0");
            return response;
        });
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, "{}"));

        await harness.Client.Client.Tradeitems.GetAsync();

        Assert.Equal(2, harness.ApiTransport.Requests.Count);
        var secondRequestSubscriptionKey = harness.ApiTransport.Requests[1].Headers.GetValues("Ocp-Apim-Subscription-Key");
        Assert.Equal("fake-subscription-key", Assert.Single(secondRequestSubscriptionKey));
    }
}
