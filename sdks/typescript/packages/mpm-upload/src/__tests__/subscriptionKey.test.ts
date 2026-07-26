import { test } from "node:test";
import assert from "node:assert/strict";
import { createTestHarness } from "./testHarness.js";
import { jsonResponse } from "./fakeFetch.js";

test("subscription key is sent as a header, never in the query string", async () => {
  const harness = createTestHarness();
  harness.tokenTransport.enqueue(jsonResponse(200, { access_token: "token-1", expires_in: 3600 }));
  harness.apiTransport.enqueue(jsonResponse(200, {}));

  await harness.client.client.tradeitems.byGtin("gtin-1").get();

  assert.equal(harness.apiTransport.requests.length, 1);
  const request = harness.apiTransport.requests[0];
  const headers = new Headers(request.init.headers);
  assert.equal(headers.get("Ocp-Apim-Subscription-Key"), "fake-subscription-key");
  assert.doesNotMatch(request.url, /fake-subscription-key/);
});
