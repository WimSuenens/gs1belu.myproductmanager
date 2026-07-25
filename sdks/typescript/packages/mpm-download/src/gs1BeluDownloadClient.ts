// @ts-ignore
import { BaseBearerTokenAuthenticationProvider, HttpMethod, RequestInformation, type RequestAdapter } from "@microsoft/kiota-abstractions";
// @ts-ignore
import { FetchRequestAdapter, KiotaClientFactory, MiddlewareFactory } from "@microsoft/kiota-http-fetchlibrary";

import { createDownloadClient, type DownloadClient } from "../generated/downloadClient.js";
import { createTradeItemResponseFromDiscriminatorValue, type TradeItem, type TradeItemResponse } from "../generated/models/index.js";
import type { TradeitemsRequestBuilderGetQueryParameters } from "../generated/tradeitems/index.js";
import { Gs1BeluEnvironmentResolver, type Gs1BeluEnvironment } from "./environment.js";
import type { Gs1BeluCredentials } from "./credentials.js";
import { Gs1BeluAccessTokenProvider } from "./auth/accessTokenProvider.js";
import { SubscriptionKeyMiddleware } from "./auth/subscriptionKeyMiddleware.js";
import { BearerRetryMiddleware } from "./auth/bearerRetryMiddleware.js";
import { RateLimitMiddleware } from "./auth/rateLimitMiddleware.js";

export const DEFAULT_API_VERSION = "v17";

export interface Gs1BeluDownloadClientDerivedOptions {
  environment: Gs1BeluEnvironment;
  credentials: Gs1BeluCredentials;
  apiVersion?: string;
}

/**
 * Testability seam: consumers never construct a client this way. Tests build the adapter against a
 * fake HTTP transport and a mocked token endpoint, exactly the hook reserved for this purpose.
 */
export interface Gs1BeluDownloadClientAdapterOptions {
  requestAdapter: RequestAdapter;
}

export type Gs1BeluDownloadClientOptions = Gs1BeluDownloadClientDerivedOptions | Gs1BeluDownloadClientAdapterOptions;

function isAdapterOptions(options: Gs1BeluDownloadClientOptions): options is Gs1BeluDownloadClientAdapterOptions {
  return "requestAdapter" in options;
}

/**
 * The authenticated, ergonomic entry point for the Download API. The derived-config constructor
 * form takes only `environment` + an `apiVersion` + a credential set — the base URL, token host,
 * and OAuth `audience` are all derived (see {@link Gs1BeluEnvironmentResolver}), so a consumer
 * cannot misconfigure any of them.
 */
export class Gs1BeluDownloadClient {
  private readonly requestAdapter: RequestAdapter;

  /** The generated fluent client, authenticated and ready to use for anything beyond the ergonomic helpers. */
  readonly client: DownloadClient;

  constructor(options: Gs1BeluDownloadClientOptions) {
    this.requestAdapter = isAdapterOptions(options) ? options.requestAdapter : buildRequestAdapter(options);
    this.client = createDownloadClient(this.requestAdapter);
  }

  /**
   * Iterates every trade item across every page, auto-following the HAL `_links.next` href the
   * server returns — including whatever query parameters the server chose to carry forward —
   * rather than re-deriving pagination ourselves. This side-steps the manuals' documented
   * page-size conflict (100 vs. 1000): the caller never sees a page size unless they set one.
   */
  async *listAllTradeItems(queryParameters?: TradeitemsRequestBuilderGetQueryParameters): AsyncGenerator<TradeItem> {
    let page: TradeItemResponse | undefined = await this.client.tradeitems.get(
      queryParameters ? { queryParameters } : undefined,
    );

    while (page) {
      for (const item of page.embedded?.tradeItems ?? []) {
        yield item;
      }

      const nextHref = page.links?.next?.href;
      if (!nextHref) {
        return;
      }

      const requestInfo = new RequestInformation();
      requestInfo.httpMethod = HttpMethod.GET;
      requestInfo.URL = nextHref;
      page = await this.requestAdapter.send(requestInfo, createTradeItemResponseFromDiscriminatorValue, undefined);
    }
  }
}

function buildRequestAdapter(options: Gs1BeluDownloadClientDerivedOptions): RequestAdapter {
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
