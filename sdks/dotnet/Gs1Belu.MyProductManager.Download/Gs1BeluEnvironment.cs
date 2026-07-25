namespace Gs1Belu.MyProductManager.Download;

/// <summary>
/// The GS1 Belgium &amp; Luxembourg My Product Manager deployment to target. Selects the API host,
/// the OAuth token host, and the OAuth <c>audience</c> together — see <see cref="Gs1BeluEnvironmentResolver"/>.
/// </summary>
public enum Gs1BeluEnvironment
{
    Uat,
    Prod,
}
