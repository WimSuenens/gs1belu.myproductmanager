using System;
using System.Text.RegularExpressions;

namespace Gs1Belu.MyProductManager.Download;

/// <summary>
/// Client-side format checks restoring the <c>pattern</c> constraints the OpenAPI spec declares on
/// <c>gtin</c>/<c>gln</c> but that Kiota does not enforce on generated models, so a malformed
/// identifier fails fast locally instead of round-tripping to an opaque server error.
/// </summary>
public static class Gs1BeluIdentifierValidation
{
    // schemas/upload/v17.yaml: tradeItem.gtin pattern.
    private static readonly Regex GtinPattern = new("^[0-9]([0-1]|[3-9])([0-9]{12})$", RegexOptions.Compiled);

    // schemas/upload/v17.yaml: party.gln pattern.
    private static readonly Regex GlnPattern = new("^[0-9]{13}$", RegexOptions.Compiled);

    /// <summary>Throws <see cref="ArgumentException"/> unless <paramref name="gtin"/> matches the GS1 GTIN format.</summary>
    public static void AssertValidGtin(string gtin)
    {
        if (gtin is null || !GtinPattern.IsMatch(gtin))
        {
            throw new ArgumentException($"'{gtin}' is not a valid GTIN.", nameof(gtin));
        }
    }

    /// <summary>Throws <see cref="ArgumentException"/> unless <paramref name="gln"/> matches the GS1 GLN format.</summary>
    public static void AssertValidGln(string gln)
    {
        if (gln is null || !GlnPattern.IsMatch(gln))
        {
            throw new ArgumentException($"'{gln}' is not a valid GLN.", nameof(gln));
        }
    }
}
