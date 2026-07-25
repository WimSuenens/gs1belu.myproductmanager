// @ts-ignore
import type { Middleware } from "@microsoft/kiota-http-fetchlibrary";
// @ts-ignore
import type { RequestOption } from "@microsoft/kiota-abstractions";

/**
 * Optional request/response logging, so a consumer can diagnose auth and API issues without
 * patching the SDK. Dependency-free by design: it reports through a plain callback rather than
 * pulling in a logging framework the consumer may not already use.
 */
export class LoggingMiddleware implements Middleware {
  next: Middleware | undefined;

  constructor(private readonly log: (message: string) => void) {}

  async execute(url: string, requestInit: RequestInit, requestOptions?: Record<string, RequestOption>): Promise<Response> {
    const start = Date.now();
    try {
      const response = await this.next!.execute(url, requestInit, requestOptions);
      this.log(`${requestInit.method ?? "GET"} ${url} -> ${response.status} (${Date.now() - start} ms)`);
      return response;
    } catch (error) {
      this.log(`${requestInit.method ?? "GET"} ${url} -> failed after ${Date.now() - start} ms: ${(error as Error).message}`);
      throw error;
    }
  }
}
