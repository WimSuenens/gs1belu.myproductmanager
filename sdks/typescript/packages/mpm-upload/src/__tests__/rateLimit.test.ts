import { test } from "node:test";
import assert from "node:assert/strict";
import { createTestHarness } from "./testHarness.js";
import { jsonResponse } from "./fakeFetch.js";

test("a request beyond the cap is paced until the window frees a slot", async () => {
  const harness = createTestHarness({ rateLimitPerWindow: 2, rateLimitWindowMs: 200 });
  harness.tokenTransport.enqueue(jsonResponse(200, { access_token: "token-1", expires_in: 3600 }));
  for (let i = 0; i < 3; i++) {
    harness.apiTransport.enqueue(jsonResponse(200, {}));
  }

  const start = Date.now();
  await harness.client.client.tradeitems.byGtin("gtin-1").get();
  await harness.client.client.tradeitems.byGtin("gtin-2").get();
  await harness.client.client.tradeitems.byGtin("gtin-3").get();
  const elapsed = Date.now() - start;

  assert.ok(elapsed >= 180, `expected the 3rd call in a 2-per-200ms window to be paced, took ${elapsed}ms`);
});
