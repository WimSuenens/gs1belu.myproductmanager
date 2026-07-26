import { test } from "node:test";
import assert from "node:assert/strict";
import { createTestHarness } from "./testHarness.js";
import { jsonResponse } from "./fakeFetch.js";
import type { TradeItem } from "../../generated/models/index.js";

const VALID_GTIN = "01234567890128";

function enqueueAuth(harness: ReturnType<typeof createTestHarness>): void {
  harness.tokenTransport.enqueue(jsonResponse(200, { access_token: "token-1", expires_in: 3600 }));
}

test("uploads then polls until settled and returns the verdict", async () => {
  const harness = createTestHarness();
  enqueueAuth(harness);
  harness.apiTransport.enqueue(new Response(null, { status: 201 }));
  harness.apiTransport.enqueue(jsonResponse(200, { metaData: { status: "pendingValidation" } }));
  harness.apiTransport.enqueue(
    jsonResponse(200, {
      metaData: {
        status: "active",
        validationResults: [{ severity: "warning", code: "VR_FMCGB2C_0257", message: "no image provided" }],
      },
    }),
  );

  const tradeItem: TradeItem = { gtin: VALID_GTIN };
  const result = await harness.client.uploadAndAwaitValidation(tradeItem, { pollIntervalMs: 5 });

  assert.equal(result.gtin, VALID_GTIN);
  assert.equal(result.status, "active");
  assert.equal(result.issues.length, 1);
  assert.equal(result.issues[0].code, "VR_FMCGB2C_0257");
  assert.equal(harness.apiTransport.requests.length, 3);
  assert.equal(harness.apiTransport.requests[0].init.method, "POST");
  assert.equal(harness.apiTransport.requests[1].init.method, "GET");
  assert.equal(harness.apiTransport.requests[2].init.method, "GET");
});

test("incomplete status is reported without throwing", async () => {
  const harness = createTestHarness();
  enqueueAuth(harness);
  harness.apiTransport.enqueue(new Response(null, { status: 201 }));
  harness.apiTransport.enqueue(
    jsonResponse(200, {
      metaData: { status: "incomplete", validationResults: [{ severity: "error", code: "VR_FMCGB2C_0315", message: "missing field" }] },
    }),
  );

  const tradeItem: TradeItem = { gtin: VALID_GTIN };
  const result = await harness.client.uploadAndAwaitValidation(tradeItem, { pollIntervalMs: 5 });

  assert.equal(result.status, "incomplete");
});

test("bounded wait times out if validation never settles", async () => {
  const harness = createTestHarness();
  enqueueAuth(harness);
  harness.apiTransport.enqueue(new Response(null, { status: 201 }));
  for (let i = 0; i < 100; i++) {
    harness.apiTransport.enqueue(jsonResponse(200, { metaData: { status: "pendingValidation" } }));
  }

  const tradeItem: TradeItem = { gtin: VALID_GTIN };

  await assert.rejects(
    () => harness.client.uploadAndAwaitValidation(tradeItem, { pollIntervalMs: 5, timeoutMs: 50 }),
    /did not leave pendingValidation/,
  );
});

test("rejects a trade item with a malformed gtin", async () => {
  const harness = createTestHarness();
  const tradeItem: TradeItem = { gtin: "not-a-gtin" };

  await assert.rejects(() => harness.client.uploadAndAwaitValidation(tradeItem));
});
