import type { Parsable, ParseNode } from "@microsoft/kiota-abstractions";

/**
 * A hand-written response model for `GET /tradeitems/{gtin}`'s `metaData` envelope. The committed
 * effective spec's `tradeItem` schema (shared by POST body and GET response) does not declare a
 * `metaData` field at all — confirmed against `schemas/upload/v17.yaml` — even though the vendor
 * manual documents this field's runtime behavior in prose. Kiota can therefore not generate it.
 * These types are deserialized directly via `requestAdapter.send()` against the same
 * `toGetRequestInformation()` the generated client builds, rather than by hand-editing
 * `generated/` (forbidden — see the #31 regen-sync guarantee).
 */
export interface TradeItemValidationIssueEnvelope extends Parsable {
  severity?: string | null;
  code?: string | null;
  message?: string | null;
}

export interface TradeItemMetaDataEnvelope extends Parsable {
  /** Raw wire value: `pendingValidation`, `active`, or `incomplete`. */
  status?: string | null;
  validationResults?: TradeItemValidationIssueEnvelope[] | null;
}

export interface TradeItemStatusEnvelope extends Parsable {
  metaData?: TradeItemMetaDataEnvelope | null;
}

export function createTradeItemValidationIssueEnvelopeFromDiscriminatorValue(_parseNode: ParseNode | undefined) {
  return deserializeIntoTradeItemValidationIssueEnvelope;
}

export function deserializeIntoTradeItemValidationIssueEnvelope(
  instance: Partial<TradeItemValidationIssueEnvelope> = {},
): Record<string, (node: ParseNode) => void> {
  return {
    severity: (n) => {
      instance.severity = n.getStringValue();
    },
    code: (n) => {
      instance.code = n.getStringValue();
    },
    message: (n) => {
      instance.message = n.getStringValue();
    },
  };
}

export function createTradeItemMetaDataEnvelopeFromDiscriminatorValue(_parseNode: ParseNode | undefined) {
  return deserializeIntoTradeItemMetaDataEnvelope;
}

export function deserializeIntoTradeItemMetaDataEnvelope(
  instance: Partial<TradeItemMetaDataEnvelope> = {},
): Record<string, (node: ParseNode) => void> {
  return {
    status: (n) => {
      instance.status = n.getStringValue();
    },
    validationResults: (n) => {
      instance.validationResults = n.getCollectionOfObjectValues(createTradeItemValidationIssueEnvelopeFromDiscriminatorValue) as
        | TradeItemValidationIssueEnvelope[]
        | undefined;
    },
  };
}

export function createTradeItemStatusEnvelopeFromDiscriminatorValue(_parseNode: ParseNode | undefined) {
  return deserializeIntoTradeItemStatusEnvelope;
}

export function deserializeIntoTradeItemStatusEnvelope(
  instance: Partial<TradeItemStatusEnvelope> = {},
): Record<string, (node: ParseNode) => void> {
  return {
    metaData: (n) => {
      instance.metaData = n.getObjectValue(createTradeItemMetaDataEnvelopeFromDiscriminatorValue) as TradeItemMetaDataEnvelope | undefined;
    },
  };
}
