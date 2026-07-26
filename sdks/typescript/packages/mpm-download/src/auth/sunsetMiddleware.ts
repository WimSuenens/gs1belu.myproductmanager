import type { Middleware } from "@microsoft/kiota-http-fetchlibrary";
import type { RequestOption } from "@microsoft/kiota-abstractions";

/**
 * The observation the `Sunset` header carries: the raw value as sent, the parsed instant (if it
 * parsed as an HTTP-date), and whether that instant has already passed.
 */
export interface SunsetNotice {
  raw: string;
  parsedAt: Date | null;
  isPast: boolean;
}

/**
 * Observes the `Sunset` header (RFC 8594) GS1 uses to announce that an API version will stop
 * responding — the Download manual documents this as best practice to monitor, including
 * preparing for a date already in the past. Dependency-free and purely observational, a sibling of
 * `LoggingMiddleware`: it never alters, retries, or fails a request, and reports through the same
 * plain-callback seam. A response without the header costs nothing beyond the lookup.
 */
export class SunsetMiddleware implements Middleware {
  next: Middleware | undefined;

  constructor(
    private readonly log?: (message: string) => void,
    private readonly onSunset?: (notice: SunsetNotice) => void,
  ) {}

  async execute(url: string, requestInit: RequestInit, requestOptions?: Record<string, RequestOption>): Promise<Response> {
    const response = await this.next!.execute(url, requestInit, requestOptions);

    const raw = response.headers.get("sunset");
    if (raw === null) {
      return response;
    }

    const parsedMs = Date.parse(raw);
    const parsedAt = Number.isNaN(parsedMs) ? null : new Date(parsedMs);
    const notice: SunsetNotice = { raw, parsedAt, isPast: parsedAt !== null && parsedAt.getTime() <= Date.now() };

    this.log?.(formatSunsetMessage(notice));
    this.onSunset?.(notice);

    return response;
  }
}

function formatSunsetMessage(notice: SunsetNotice): string {
  if (notice.parsedAt === null) {
    return `Sunset: GS1 announced an API-version sunset but the header value could not be parsed as an HTTP-date: "${notice.raw}".`;
  }

  if (notice.isPast) {
    return `Sunset: this API version's announced sunset (${notice.parsedAt.toISOString()}) is already in the past — it may stop responding at any time.`;
  }

  const days = Math.floor((notice.parsedAt.getTime() - Date.now()) / (24 * 60 * 60 * 1000));
  return `Sunset: GS1 announced this API version will stop responding at ${notice.parsedAt.toISOString()} (in ${days} days). Plan a version migration.`;
}
