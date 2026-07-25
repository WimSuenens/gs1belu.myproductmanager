// @ts-ignore
import type { RequestAdapter } from "@microsoft/kiota-abstractions";
// @ts-ignore
import { BaseBearerTokenAuthenticationProvider } from "@microsoft/kiota-abstractions";
// @ts-ignore
import { FetchRequestAdapter, KiotaClientFactory, MiddlewareFactory } from "@microsoft/kiota-http-fetchlibrary";

import { createUploadClient, type UploadClient } from "../generated/uploadClient.js";
import type { TradeItem } from "../generated/models/index.js";
import { Gs1BeluEnvironmentResolver, type Gs1BeluEnvironment } from "./environment.js";
import type { Gs1BeluCredentials } from "./credentials.js";
import { Gs1BeluAccessTokenProvider } from "./auth/accessTokenProvider.js";
import { SubscriptionKeyMiddleware } from "./auth/subscriptionKeyMiddleware.js";
import { BearerRetryMiddleware } from "./auth/bearerRetryMiddleware.js";
import { RateLimitMiddleware } from "./auth/rateLimitMiddleware.js";
import { assertValidGtin } from "./identifierValidation.js";
import { createTradeItemStatusEnvelopeFromDiscriminatorValue, type TradeItemStatusEnvelope } from "./uploadValidation/tradeItemStatusEnvelope.js";
import type { UploadValidationIssue, UploadValidationResult, UploadValidationStatus } from "./uploadValidation/uploadValidationResult.js";

export const DEFAULT_API_VERSION = "v17";

export interface Gs1BeluUploadClientDerivedOptions {
  environment: Gs1BeluEnvironment;
  credentials: Gs1BeluCredentials;
  apiVersion?: string;
}

/**
 * Testability seam: consumers never construct a client this way. Tests build the adapter against a
 * fake HTTP transport and a mocked token endpoint, exactly the hook reserved for this purpose.
 */
export interface Gs1BeluUploadClientAdapterOptions {
  requestAdapter: RequestAdapter;
}

export type Gs1BeluUploadClientOptions = Gs1BeluUploadClientDerivedOptions | Gs1BeluUploadClientAdapterOptions;

function isAdapterOptions(options: Gs1BeluUploadClientOptions): options is Gs1BeluUploadClientAdapterOptions {
  return "requestAdapter" in options;
}

/**
 * The authenticated, ergonomic entry point for the Upload API. The derived-config constructor form
 * takes only `environment` + an `apiVersion` + a credential set — the base URL, token host, and
 * OAuth `audience` are all derived (see {@link Gs1BeluEnvironmentResolver}), so a consumer cannot
 * misconfigure any of them.
 */
export class Gs1BeluUploadClient {
  private readonly requestAdapter: RequestAdapter;

  /** The generated fluent client, authenticated and ready to use for anything beyond the ergonomic helpers. */
  readonly client: UploadClient;

  constructor(options: Gs1BeluUploadClientOptions) {
    this.requestAdapter = isAdapterOptions(options) ? options.requestAdapter : buildRequestAdapter(options);
    this.client = createUploadClient(this.requestAdapter);
  }

  /**
   * Submits `tradeItem` and polls `GET /tradeitems/{gtin}` until `metaData.status` leaves
   * `pendingValidation`, returning the settled verdict. The POST itself always answers `201` with
   * an empty body regardless of data errors — this is the method that actually tells the caller
   * whether GS1 accepted the item.
   */
  async uploadAndAwaitValidation(
    tradeItem: TradeItem,
    options?: { pollIntervalMs?: number; timeoutMs?: number },
  ): Promise<UploadValidationResult> {
    const gtin = tradeItem.gtin;
    if (!gtin) {
      throw new Error("tradeItem.gtin is required.");
    }
    assertValidGtin(gtin);

    await this.client.tradeitems.post(tradeItem);

    const pollIntervalMs = options?.pollIntervalMs ?? 2000;
    const timeoutMs = options?.timeoutMs ?? 120_000;
    const deadline = Date.now() + timeoutMs;

    for (;;) {
      const envelope = await this.getStatusEnvelope(gtin);
      const rawStatus = envelope?.metaData?.status;
      if (rawStatus !== "pendingValidation") {
        return toResult(gtin, envelope);
      }

      if (Date.now() >= deadline) {
        throw new Error(`Validation for GTIN '${gtin}' did not leave pendingValidation within ${timeoutMs}ms.`);
      }

      await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));
    }
  }

  private async getStatusEnvelope(gtin: string): Promise<TradeItemStatusEnvelope | undefined> {
    const requestInfo = this.client.tradeitems.byGtin(gtin).toGetRequestInformation();
    return this.requestAdapter.send(requestInfo, createTradeItemStatusEnvelopeFromDiscriminatorValue, undefined);
  }
}

function buildRequestAdapter(options: Gs1BeluUploadClientDerivedOptions): RequestAdapter {
  const { environment, credentials } = options;
  const apiVersion = options.apiVersion ?? DEFAULT_API_VERSION;

  const tokenProvider = new Gs1BeluAccessTokenProvider(
    credentials,
    Gs1BeluEnvironmentResolver.tokenEndpoint(environment),
    Gs1BeluEnvironmentResolver.audience(environment),
    [Gs1BeluEnvironmentResolver.apiHost(environment)],
  );
  const authProvider = new BaseBearerTokenAuthenticationProvider(tokenProvider);

  const middlewares = [
    ...MiddlewareFactory.getDefaultMiddlewares(),
    new SubscriptionKeyMiddleware(credentials.subscriptionKey),
    new BearerRetryMiddleware(tokenProvider),
    new RateLimitMiddleware(),
  ];
  const httpClient = KiotaClientFactory.create(undefined, middlewares);

  const adapter = new FetchRequestAdapter(authProvider, undefined, undefined, httpClient);
  adapter.baseUrl = Gs1BeluEnvironmentResolver.baseUrl(environment, apiVersion);
  return adapter;
}

function toResult(gtin: string, envelope: TradeItemStatusEnvelope | undefined): UploadValidationResult {
  const rawStatus = envelope?.metaData?.status;
  const status: UploadValidationStatus = rawStatus === "active" ? "active" : rawStatus === "incomplete" ? "incomplete" : "unknown";
  const issues: UploadValidationIssue[] = (envelope?.metaData?.validationResults ?? []).map((issue) => ({
    severity: issue.severity ?? "",
    code: issue.code ?? "",
    message: issue.message ?? "",
  }));
  return { gtin, status, issues };
}
