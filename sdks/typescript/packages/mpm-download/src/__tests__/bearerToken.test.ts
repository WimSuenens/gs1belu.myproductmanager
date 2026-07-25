import { test } from "node:test";
import assert from "node:assert/strict";
import { createTestHarness } from "./testHarness.js";
import { jsonResponse } from "./fakeFetch.js";

function tokenResponse(expiresInSeconds: number, accessToken = "token-1"): Response {
  return jsonResponse(200, { access_token: accessToken, expires_in: expiresInSeconds, token_type: "Bearer" });
}

function emptyPageResponse(): Response {
  return jsonResponse(200, {});
}

test("attaches bearer header to outgoing requests", async () => {
  const harness = createTestHarness();
  harness.tokenTransport.enqueue(tokenResponse(3600));
  harness.apiTransport.enqueue(emptyPageResponse());

  await harness.client.client.tradeitems.get();

  assert.equal(harness.apiTransport.requests.length, 1);
  const headers = new Headers(harness.apiTransport.requests[0].init.headers);
  assert.equal(headers.get("Authorization"), "Bearer token-1");
});

test("concurrent burst coalesces onto a single token fetch", async () => {
  const harness = createTestHarness();
  harness.tokenTransport.enqueue(tokenResponse(3600));
  for (let i = 0; i < 5; i++) {
    harness.apiTransport.enqueue(emptyPageResponse());
  }

  await Promise.all(Array.from({ length: 5 }, () => harness.client.client.tradeitems.get()));

  assert.equal(harness.tokenTransport.requests.length, 1);
  assert.equal(harness.apiTransport.requests.length, 5);
});

test("cached token is reused while still within the skew window", async () => {
  const harness = createTestHarness();
  harness.tokenTransport.enqueue(tokenResponse(3600));
  harness.apiTransport.enqueue(emptyPageResponse());
  harness.apiTransport.enqueue(emptyPageResponse());

  await harness.client.client.tradeitems.get();
  await harness.client.client.tradeitems.get();

  assert.equal(harness.tokenTransport.requests.length, 1);
});

test("token within the skew margin of expiry is refetched", async () => {
  const harness = createTestHarness({ skewMarginMs: 50 });
  harness.tokenTransport.enqueue(tokenResponse(0, "token-1"));
  harness.apiTransport.enqueue(emptyPageResponse());
  await harness.client.client.tradeitems.get();

  harness.tokenTransport.enqueue(tokenResponse(3600, "token-2"));
  harness.apiTransport.enqueue(emptyPageResponse());
  await harness.client.client.tradeitems.get();

  assert.equal(harness.tokenTransport.requests.length, 2);
  const headers = new Headers(harness.apiTransport.requests[1].init.headers);
  assert.equal(headers.get("Authorization"), "Bearer token-2");
});

test("unauthorized response forces a refresh and retries once", async () => {
  const harness = createTestHarness();
  harness.tokenTransport.enqueue(tokenResponse(3600, "token-1"));
  harness.apiTransport.enqueue(() => new Response(null, { status: 401 }));
  harness.tokenTransport.enqueue(tokenResponse(3600, "token-2"));
  harness.apiTransport.enqueue(emptyPageResponse());

  await harness.client.client.tradeitems.get();

  assert.equal(harness.tokenTransport.requests.length, 2);
  assert.equal(harness.apiTransport.requests.length, 2);
  const headers = new Headers(harness.apiTransport.requests[1].init.headers);
  assert.equal(headers.get("Authorization"), "Bearer token-2");
});
