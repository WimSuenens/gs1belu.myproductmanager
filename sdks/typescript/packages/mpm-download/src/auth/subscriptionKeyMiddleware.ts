import type { Middleware } from "@microsoft/kiota-http-fetchlibrary";
import type { RequestOption } from "@microsoft/kiota-abstractions";

const HEADER_NAME = "Ocp-Apim-Subscription-Key";

/**
 * Stamps the static `Ocp-Apim-Subscription-Key` header on every request. The subscription key is
 * deliberately never sent as the spec's alternative query-string parameter, since a secret in the
 * URL ends up in logs and proxy caches.
 */
export class SubscriptionKeyMiddleware implements Middleware {
  next: Middleware | undefined;

  constructor(private readonly subscriptionKey: string) {}

  async execute(url: string, requestInit: RequestInit, requestOptions?: Record<string, RequestOption>): Promise<Response> {
    const headers = new Headers(requestInit.headers);
    headers.set(HEADER_NAME, this.subscriptionKey);
    requestInit.headers = headers;
    return this.next!.execute(url, requestInit, requestOptions);
  }
}
