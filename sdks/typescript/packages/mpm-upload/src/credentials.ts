/**
 * The credential set for one API client (Upload and Download credentials are never shared).
 */
export interface Gs1BeluCredentials {
  /** The OAuth2 client-credentials client id. */
  clientId: string;
  /** The OAuth2 client-credentials client secret. */
  clientSecret: string;
  /** The static `Ocp-Apim-Subscription-Key` value. */
  subscriptionKey: string;
}
