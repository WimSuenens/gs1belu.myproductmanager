import type { Middleware } from "@microsoft/kiota-http-fetchlibrary";
import type { RequestOption } from "@microsoft/kiota-abstractions";

/**
 * Paces requests to stay under the API's 10 req/s cap. A sliding window of recent request
 * timestamps is kept; a request that would exceed the cap waits until the oldest timestamp in the
 * window ages out, rather than firing and risking a throttle response.
 */
export class RateLimitMiddleware implements Middleware {
  next: Middleware | undefined;
  private recentRequestTimestamps: number[] = [];

  constructor(private readonly maxRequestsPerWindow = 10, private readonly windowMs = 1000) {}

  async execute(url: string, requestInit: RequestInit, requestOptions?: Record<string, RequestOption>): Promise<Response> {
    await this.waitForSlot();
    return this.next!.execute(url, requestInit, requestOptions);
  }

  private async waitForSlot(): Promise<void> {
    for (;;) {
      const now = Date.now();
      this.recentRequestTimestamps = this.recentRequestTimestamps.filter((timestamp) => now - timestamp < this.windowMs);

      if (this.recentRequestTimestamps.length < this.maxRequestsPerWindow) {
        this.recentRequestTimestamps.push(now);
        return;
      }

      const delay = this.windowMs - (now - this.recentRequestTimestamps[0]);
      if (delay > 0) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }
}
