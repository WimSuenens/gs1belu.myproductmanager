import { test } from "node:test";
import assert from "node:assert/strict";
import type { Middleware } from "@microsoft/kiota-http-fetchlibrary";
import { LoggingMiddleware } from "../auth/loggingMiddleware.js";

test("logs the method, url, and resolved status of a successful request", async () => {
  const messages: string[] = [];
  const middleware = new LoggingMiddleware((message) => messages.push(message));
  middleware.next = {
    next: undefined,
    execute: async () => new Response(null, { status: 204 }),
  } as Middleware;

  await middleware.execute("https://fake.test/tradeitems", { method: "GET" });

  assert.equal(messages.length, 1);
  assert.match(messages[0], /GET https:\/\/fake\.test\/tradeitems -> 204/);
});

test("logs a failure and rethrows when the downstream call rejects", async () => {
  const messages: string[] = [];
  const middleware = new LoggingMiddleware((message) => messages.push(message));
  middleware.next = {
    next: undefined,
    execute: async () => {
      throw new Error("boom");
    },
  } as Middleware;

  await assert.rejects(() => middleware.execute("https://fake.test/tradeitems", { method: "GET" }), /boom/);
  assert.equal(messages.length, 1);
  assert.match(messages[0], /GET https:\/\/fake\.test\/tradeitems -> failed.*boom/);
});
