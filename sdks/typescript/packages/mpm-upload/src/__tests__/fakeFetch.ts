export interface RecordedRequest {
  url: string;
  init: RequestInit;
}

/**
 * The fake HTTP transport the test seam is built on: a queue of canned responses (or response
 * factories, for status-code sequencing) plus a record of every request actually sent, so tests can
 * assert on headers, URLs, and call counts without any real network I/O. Matches Kiota's own
 * `customFetch` shape so it plugs directly into `KiotaClientFactory.create` / the token provider.
 */
export class FakeFetch {
  readonly requests: RecordedRequest[] = [];
  private readonly responses: Array<(request: RecordedRequest) => Response> = [];

  enqueue(respond: Response | ((request: RecordedRequest) => Response)): void {
    this.responses.push(typeof respond === "function" ? respond : () => respond);
  }

  fetch = async (url: string, init: RequestInit): Promise<Response> => {
    const request: RecordedRequest = { url, init };
    this.requests.push(request);
    const respond = this.responses.shift();
    if (!respond) {
      throw new Error(`No fake response queued for ${init.method ?? "GET"} ${url}`);
    }
    return respond(request);
  };
}

export function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}
