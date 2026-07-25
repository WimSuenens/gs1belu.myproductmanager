using System.Net;
using System.Threading.Tasks;
using Xunit;

namespace Gs1Belu.MyProductManager.Upload.Tests;

public class SubscriptionKeyTests
{
    [Fact]
    public async Task Subscription_key_is_sent_as_a_header_never_in_the_query_string()
    {
        var harness = new TestHarness();
        harness.TokenTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, """{"access_token":"token-1","expires_in":3600}"""));
        harness.ApiTransport.Enqueue(TestHarness.JsonResponse(HttpStatusCode.OK, "{}"));

        await harness.Client.Client.Tradeitems["gtin-1"].GetAsync();

        var request = Assert.Single(harness.ApiTransport.Requests);
        Assert.True(request.Headers.TryGetValues("Ocp-Apim-Subscription-Key", out var values));
        Assert.Equal("fake-subscription-key", Assert.Single(values));
        Assert.DoesNotContain("fake-subscription-key", request.RequestUri!.Query);
    }
}
