import { test } from "node:test";
import assert from "node:assert/strict";
import { createTestHarness } from "./testHarness.js";
import { jsonResponse } from "./fakeFetch.js";

function enqueueAuth(harness: ReturnType<typeof createTestHarness>): void {
  harness.tokenTransport.enqueue(jsonResponse(200, { access_token: "token-1", expires_in: 3600 }));
}

test("yields every item across every page and stops at the terminal page", async () => {
  const harness = createTestHarness();
  enqueueAuth(harness);
  harness.apiTransport.enqueue(
    jsonResponse(200, {
      _embedded: { tradeItems: [{ gtin: "00000000000001" }, { gtin: "00000000000002" }] },
      _links: { next: { href: "https://fake-api.test/myproductmanager/download/v17/tradeitems?cursor=abc" } },
    }),
  );
  harness.apiTransport.enqueue(jsonResponse(200, { _embedded: { tradeItems: [{ gtin: "00000000000003" }] } }));

  const gtins: (string | null | undefined)[] = [];
  for await (const item of harness.client.listAllTradeItems()) {
    gtins.push(item.gtin);
  }

  assert.deepEqual(gtins, ["00000000000001", "00000000000002", "00000000000003"]);
  assert.equal(harness.apiTransport.requests.length, 2);
  assert.match(harness.apiTransport.requests[1].url, /cursor=abc/);
});

test("stops immediately when the first page has no next link", async () => {
  const harness = createTestHarness();
  enqueueAuth(harness);
  harness.apiTransport.enqueue(jsonResponse(200, { _embedded: { tradeItems: [{ gtin: "00000000000001" }] } }));

  const items = [];
  for await (const item of harness.client.listAllTradeItems()) {
    items.push(item);
  }

  assert.equal(items.length, 1);
  assert.equal(harness.apiTransport.requests.length, 1);
});

test("empty result set yields nothing", async () => {
  const harness = createTestHarness();
  enqueueAuth(harness);
  harness.apiTransport.enqueue(jsonResponse(200, { _embedded: { tradeItems: [] } }));

  const items = [];
  for await (const item of harness.client.listAllTradeItems()) {
    items.push(item);
  }

  assert.equal(items.length, 0);
});
