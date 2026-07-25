// @ts-ignore
import { BaseBearerTokenAuthenticationProvider } from "@microsoft/kiota-abstractions";
// @ts-ignore
import { FetchRequestAdapter, KiotaClientFactory } from "@microsoft/kiota-http-fetchlibrary";
import { Gs1BeluAccessTokenProvider } from "../auth/accessTokenProvider.js";
import { SubscriptionKeyMiddleware } from "../auth/subscriptionKeyMiddleware.js";
import { BearerRetryMiddleware } from "../auth/bearerRetryMiddleware.js";
import { RateLimitMiddleware } from "../auth/rateLimitMiddleware.js";
import { Gs1BeluDownloadClient } from "../gs1BeluDownloadClient.js";
import type { Gs1BeluCredentials } from "../credentials.js";
import { FakeFetch } from "./fakeFetch.js";

export const FAKE_BASE_URL = "https://fake-api.test/myproductmanager/download/v17";

export interface TestHarnessOptions {
  credentials?: Gs1BeluCredentials;
  skewMarginMs?: number;
  rateLimitPerWindow?: number;
  rateLimitWindowMs?: number;
}

/**
 * The test seam Testing Decisions §"The seam" describes: builds the exact same production auth +
 * middleware pipeline as `Gs1BeluDownloadClient`'s derived-config constructor form, but wired to
 * fake HTTP transports (API + token endpoint) instead of the real network. Consumers never see
 * this — it exists only so tests can assert on observable HTTP behavior through the real classes.
 */
export function createTestHarness(options: TestHarnessOptions = {}) {
  const credentials: Gs1BeluCredentials = options.credentials ?? {
    clientId: "fake-client-id",
    clientSecret: "fake-client-secret",
    subscriptionKey: "fake-subscription-key",
  };
  const apiTransport = new FakeFetch();
  const tokenTransport = new FakeFetch();

  const tokenProvider = new Gs1BeluAccessTokenProvider(
    credentials,
    "https://fake-token.test/oauth/token",
    "https://fake-api.test/",
    ["fake-api.test"],
    { fetchFn: tokenTransport.fetch, skewMarginMs: options.skewMarginMs },
  );
  const authProvider = new BaseBearerTokenAuthenticationProvider(tokenProvider);

  const middlewares = [
    new SubscriptionKeyMiddleware(credentials.subscriptionKey),
    new BearerRetryMiddleware(tokenProvider),
    new RateLimitMiddleware(options.rateLimitPerWindow ?? 1000, options.rateLimitWindowMs),
  ];
  const httpClient = KiotaClientFactory.create(apiTransport.fetch, middlewares);
  const adapter = new FetchRequestAdapter(authProvider, undefined, undefined, httpClient);
  adapter.baseUrl = FAKE_BASE_URL;

  const client = new Gs1BeluDownloadClient({ requestAdapter: adapter });

  return { client, apiTransport, tokenTransport, tokenProvider };
}
