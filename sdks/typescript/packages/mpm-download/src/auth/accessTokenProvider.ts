import { AllowedHostsValidator, type AccessTokenProvider } from "@microsoft/kiota-abstractions";
import type { Gs1BeluCredentials } from "../credentials.js";

// Matches Kiota's own `customFetch` shape (a bare URL string, not the full `RequestInfo | URL`
// union `fetch` itself accepts) so a Kiota-flavored fake in tests is directly interchangeable here.
type FetchFn = (url: string, init: RequestInit) => Promise<Response>;

interface OAuthTokenResponse {
  access_token?: string;
  expires_in?: number;
}

const DEFAULT_SKEW_MARGIN_MS = 60_000;

/**
 * Fetches, caches, and proactively refreshes the OAuth2 client-credentials Bearer token used on
 * every request. The GS1 manuals warn that a client which re-authenticates on every call gets
 * disconnected, so the token is cached in memory and only refetched once it is within a skew margin
 * (60s by default) of its runtime `expires_in` — never a hardcoded 12h/24h figure, since the
 * manuals themselves disagree on which of those it is.
 *
 * Concurrent callers coalesce onto a single in-flight fetch: every caller that arrives while a fetch
 * promise is outstanding just awaits that same promise instead of starting its own.
 */
export class Gs1BeluAccessTokenProvider implements AccessTokenProvider {
  private readonly allowedHostsValidator: AllowedHostsValidator;
  private readonly skewMarginMs: number;
  private readonly fetchFn: FetchFn;

  private cachedToken: string | undefined;
  private cachedExpiresAtMs = 0;
  private inFlight: Promise<string> | null = null;

  constructor(
    private readonly credentials: Gs1BeluCredentials,
    private readonly tokenEndpoint: string,
    private readonly audience: string,
    allowedHosts: string[],
    options?: { fetchFn?: FetchFn; skewMarginMs?: number },
  ) {
    this.allowedHostsValidator = new AllowedHostsValidator(new Set(allowedHosts));
    this.fetchFn = options?.fetchFn ?? fetch;
    this.skewMarginMs = options?.skewMarginMs ?? DEFAULT_SKEW_MARGIN_MS;
  }

  getAllowedHostsValidator(): AllowedHostsValidator {
    return this.allowedHostsValidator;
  }

  async getAuthorizationToken(_url?: string, additionalAuthenticationContext?: Record<string, unknown>): Promise<string> {
    const forceRefresh = additionalAuthenticationContext?.forceRefresh === true;
    return this.getToken(forceRefresh);
  }

  /**
   * Bypasses the cache and fetches a fresh token, still coalesced through the same in-flight
   * promise. Called by the bearer-retry middleware when a request comes back `401`.
   */
  async refresh(): Promise<string> {
    return this.getToken(true);
  }

  private async getToken(forceRefresh: boolean): Promise<string> {
    if (!forceRefresh && this.isCacheValid()) {
      return this.cachedToken as string;
    }

    if (!this.inFlight) {
      this.inFlight = this.fetchToken().finally(() => {
        this.inFlight = null;
      });
    }

    return this.inFlight;
  }

  private isCacheValid(): boolean {
    return this.cachedToken !== undefined && Date.now() < this.cachedExpiresAtMs - this.skewMarginMs;
  }

  private async fetchToken(): Promise<string> {
    const body = new URLSearchParams({
      grant_type: "client_credentials",
      client_id: this.credentials.clientId,
      client_secret: this.credentials.clientSecret,
      audience: this.audience,
    });

    const response = await this.fetchFn(this.tokenEndpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    });

    if (!response.ok) {
      throw new Error(`The GS1 token endpoint responded ${response.status}.`);
    }

    const json = (await response.json()) as OAuthTokenResponse;
    if (!json.access_token) {
      throw new Error("The GS1 token endpoint returned no access_token.");
    }

    this.cachedToken = json.access_token;
    this.cachedExpiresAtMs = Date.now() + (json.expires_in ?? 0) * 1000;
    return this.cachedToken;
  }
}
