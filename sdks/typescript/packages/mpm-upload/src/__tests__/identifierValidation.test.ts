import { test } from "node:test";
import assert from "node:assert/strict";
import { assertValidGtin, assertValidGln } from "../identifierValidation.js";

test("assertValidGtin accepts conforming values", () => {
  for (const gtin of ["01234567890128", "00000000000000", "99999999999999"]) {
    assert.doesNotThrow(() => assertValidGtin(gtin));
  }
});

test("assertValidGtin rejects malformed values", () => {
  for (const gtin of ["02234567890128", "1234567890123", "123456789012345", "abcdefghij1234"]) {
    assert.throws(() => assertValidGtin(gtin));
  }
});

test("assertValidGln accepts conforming values", () => {
  for (const gln of ["5412345678901", "0000000000000"]) {
    assert.doesNotThrow(() => assertValidGln(gln));
  }
});

test("assertValidGln rejects malformed values", () => {
  for (const gln of ["541234567890", "54123456789012", "541234567890a"]) {
    assert.throws(() => assertValidGln(gln));
  }
});
