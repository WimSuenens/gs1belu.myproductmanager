// @ts-ignore
import type { Middleware } from "@microsoft/kiota-http-fetchlibrary";
// @ts-ignore
import type { RequestOption } from "@microsoft/kiota-abstractions";
import type { Gs1BeluAccessTokenProvider } from "./accessTokenProvider.js";

/**
 * Safety net under the proactive skew refresh: if a request still comes back `401` (the token was
 * revoked early, or clock drift outran the skew margin), force a fresh token fetch and retry exactly
 * once. The request adapter attaches the `Authorization` header before the request reaches this
 * middleware, so a retry must overwrite that header itself rather than asking the adapter to
 * re-authenticate.
 */
export class BearerRetryMiddleware implements Middleware {
  next: Middleware | undefined;

  constructor(private readonly tokenProvider: Gs1BeluAccessTokenProvider) {}

  async execute(url: string, requestInit: RequestInit, requestOptions?: Record<string, RequestOption>): Promise<Response> {
    const response = await this.next!.execute(url, requestInit, requestOptions);
    if (response.status !== 401) {
      return response;
    }

    const freshToken = await this.tokenProvider.refresh();
    const headers = new Headers(requestInit.headers);
    headers.set("Authorization", `Bearer ${freshToken}`);
    return this.next!.execute(url, { ...requestInit, headers }, requestOptions);
  }
}
