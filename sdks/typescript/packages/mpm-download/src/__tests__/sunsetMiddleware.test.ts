import { test } from "node:test";
import assert from "node:assert/strict";
import type { Middleware } from "@microsoft/kiota-http-fetchlibrary";
import { SunsetMiddleware, type SunsetNotice } from "../auth/sunsetMiddleware.js";

function nextReturning(headers: Record<string, string>): Middleware {
  return {
    next: undefined,
    execute: async () => new Response(null, { status: 200, headers }),
  } as Middleware;
}

test("surfaces a future sunset date with the parsed timestamp", async () => {
  const messages: string[] = [];
  const notices: SunsetNotice[] = [];
  const future = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000);
  const middleware = new SunsetMiddleware(
    (message) => messages.push(message),
    (notice) => notices.push(notice),
  );
  middleware.next = nextReturning({ sunset: future.toUTCString() });

  await middleware.execute("https://fake.test/tradeitems", { method: "GET" });

  assert.equal(notices.length, 1);
  assert.ok(notices[0].parsedAt !== null);
  assert.equal(notices[0].isPast, false);
  assert.equal(messages.length, 1);
  assert.match(messages[0], /Plan a version migration/);
});

test("produces no notice when the header is absent", async () => {
  const messages: string[] = [];
  const notices: SunsetNotice[] = [];
  const middleware = new SunsetMiddleware(
    (message) => messages.push(message),
    (notice) => notices.push(notice),
  );
  middleware.next = nextReturning({});

  await middleware.execute("https://fake.test/tradeitems", { method: "GET" });

  assert.equal(messages.length, 0);
  assert.equal(notices.length, 0);
});

test("flags a past sunset date as already sunset", async () => {
  const notices: SunsetNotice[] = [];
  const past = new Date(Date.now() - 24 * 60 * 60 * 1000);
  const middleware = new SunsetMiddleware(undefined, (notice) => notices.push(notice));
  middleware.next = nextReturning({ sunset: past.toUTCString() });

  await middleware.execute("https://fake.test/tradeitems", { method: "GET" });

  assert.equal(notices.length, 1);
  assert.ok(notices[0].parsedAt !== null);
  assert.equal(notices[0].isPast, true);
});

test("surfaces the raw value without throwing when the header is unparseable", async () => {
  const notices: SunsetNotice[] = [];
  const middleware = new SunsetMiddleware(undefined, (notice) => notices.push(notice));
  middleware.next = nextReturning({ sunset: "not-a-date" });

  await middleware.execute("https://fake.test/tradeitems", { method: "GET" });

  assert.equal(notices.length, 1);
  assert.equal(notices[0].raw, "not-a-date");
  assert.equal(notices[0].parsedAt, null);
  assert.equal(notices[0].isPast, false);
});
