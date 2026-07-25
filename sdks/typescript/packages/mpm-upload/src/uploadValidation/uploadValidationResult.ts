/** The settled validation verdict once `metaData.status` leaves `pendingValidation`. */
export type UploadValidationStatus =
  | "active" // validated and published to data recipients (no errors, or only non-blocking warnings)
  | "incomplete" // at least one error-severity rule violated; withheld from publication
  | "unknown"; // the API returned a status value this SDK does not yet recognize

/** One entry of `metaData.validationResults[]` (e.g. a GS1 BeLu `VR_FMCGB2C_####` rule). */
export interface UploadValidationIssue {
  severity: string;
  code: string;
  message: string;
}

/**
 * The resolved outcome of `uploadAndAwaitValidation` — the true success/failure signal for an
 * upload, since the POST itself always answers `201` regardless of whether GS1's business-rule
 * validation ultimately accepts the item.
 */
export interface UploadValidationResult {
  gtin: string;
  status: UploadValidationStatus;
  issues: UploadValidationIssue[];
}
