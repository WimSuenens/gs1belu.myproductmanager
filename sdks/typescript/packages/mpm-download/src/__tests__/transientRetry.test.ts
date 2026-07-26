import { test } from "node:test";
import assert from "node:assert/strict";
import { createTestHarness } from "./testHarness.js";
import { jsonResponse } from "./fakeFetch.js";

test("a transient 503 is retried by the default pipeline and eventually succeeds", async () => {
  const harness = createTestHarness();
  harness.tokenTransport.enqueue(jsonResponse(200, { access_token: "token-1", expires_in: 3600 }));
  harness.apiTransport.enqueue(() => new Response(null, { status: 503, headers: { "Retry-After": "0" } }));
  harness.apiTransport.enqueue(jsonResponse(200, {}));

  const result = await harness.client.client.tradeitems.get();

  assert.equal(harness.apiTransport.requests.length, 2);
  assert.ok(result !== undefined);
  const secondRequestHeaders = new Headers(harness.apiTransport.requests[1].init.headers);
  assert.equal(secondRequestHeaders.get("Ocp-Apim-Subscription-Key"), "fake-subscription-key");
});
