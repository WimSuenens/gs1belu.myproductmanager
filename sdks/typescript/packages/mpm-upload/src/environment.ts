/**
 * The GS1 Belgium & Luxembourg My Product Manager deployment to target. Selects the API host, the
 * OAuth token host, and the OAuth `audience` together — see {@link Gs1BeluEnvironmentResolver}.
 */
export type Gs1BeluEnvironment = "uat" | "prod";

const API_SEGMENT = "upload";

/**
 * Pure derivation of the API host, OAuth token host, and OAuth `audience` from a
 * {@link Gs1BeluEnvironment}. There is no caller-supplied host or base URL anywhere in the public
 * surface: a fumbled `audience` is exactly the GS1 manuals' `access_denied` failure, so it is
 * derived here, once, instead of being a field a consumer can get wrong.
 */
export const Gs1BeluEnvironmentResolver = {
  apiHost(environment: Gs1BeluEnvironment): string {
    return environment === "uat" ? "api-uat.gs1belu.org" : "api.gs1belu.org";
  },

  tokenHost(environment: Gs1BeluEnvironment): string {
    return environment === "uat" ? "login-uat.gs1belu.org" : "login.gs1belu.org";
  },

  /** The OAuth `audience` claim, with the mandatory trailing slash baked in. */
  audience(environment: Gs1BeluEnvironment): string {
    return `https://${this.apiHost(environment)}/`;
  },

  tokenEndpoint(environment: Gs1BeluEnvironment): string {
    return `https://${this.tokenHost(environment)}/oauth/token`;
  },

  baseUrl(environment: Gs1BeluEnvironment, apiVersion: string): string {
    return `https://${this.apiHost(environment)}/myproductmanager/${API_SEGMENT}/${apiVersion}`;
  },
};
