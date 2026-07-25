namespace Gs1Belu.MyProductManager.Upload;

/// <summary>
/// The credential set for one API client (Upload and Download credentials are never shared).
/// </summary>
/// <param name="ClientId">The OAuth2 client-credentials client id.</param>
/// <param name="ClientSecret">The OAuth2 client-credentials client secret.</param>
/// <param name="SubscriptionKey">The static <c>Ocp-Apim-Subscription-Key</c> value.</param>
public sealed record Gs1BeluCredentials(string ClientId, string ClientSecret, string SubscriptionKey);
