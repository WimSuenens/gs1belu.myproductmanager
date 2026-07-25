using System.Collections.Generic;

namespace Gs1Belu.MyProductManager.Upload.UploadValidation;

/// <summary>The settled validation verdict once <c>metaData.status</c> leaves <c>pendingValidation</c>.</summary>
public enum UploadValidationStatus
{
    /// <summary>Validated and published to data recipients (no errors, or only non-blocking warnings).</summary>
    Active,

    /// <summary>At least one <c>error</c>-severity rule violated; withheld from publication.</summary>
    Incomplete,

    /// <summary>The API returned a status value this SDK does not yet recognize.</summary>
    Unknown,
}

/// <summary>One entry of <c>metaData.validationResults[]</c> (e.g. a GS1 BeLu <c>VR_FMCGB2C_####</c> rule).</summary>
public sealed record UploadValidationIssue(string Severity, string Code, string Message);

/// <summary>
/// The resolved outcome of <see cref="Gs1BeluUploadClient.UploadAndAwaitValidationAsync"/> — the true
/// success/failure signal for an upload, since the POST itself always answers <c>201</c> regardless
/// of whether GS1's business-rule validation ultimately accepts the item.
/// </summary>
public sealed record UploadValidationResult(string Gtin, UploadValidationStatus Status, IReadOnlyList<UploadValidationIssue> Issues);
