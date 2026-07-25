/**
 * Client-side format checks restoring the `pattern` constraints the OpenAPI spec declares on
 * `gtin`/`gln` but that Kiota does not enforce on generated models, so a malformed identifier fails
 * fast locally instead of round-tripping to an opaque server error.
 */

// schemas/upload/v17.yaml: tradeItem.gtin pattern.
const GTIN_PATTERN = /^[0-9]([0-1]|[3-9])([0-9]{12})$/;

// schemas/upload/v17.yaml: party.gln pattern.
const GLN_PATTERN = /^[0-9]{13}$/;

/** Throws unless `gtin` matches the GS1 GTIN format. */
export function assertValidGtin(gtin: string): void {
  if (typeof gtin !== "string" || !GTIN_PATTERN.test(gtin)) {
    throw new Error(`'${gtin}' is not a valid GTIN.`);
  }
}

/** Throws unless `gln` matches the GS1 GLN format. */
export function assertValidGln(gln: string): void {
  if (typeof gln !== "string" || !GLN_PATTERN.test(gln)) {
    throw new Error(`'${gln}' is not a valid GLN.`);
  }
}
