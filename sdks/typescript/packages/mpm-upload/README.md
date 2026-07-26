# @gs1belu/mpm-upload

Kiota-generated TypeScript client for the GS1 Belgium & Luxembourg **My Product
Manager** Upload API (v17), with a hand-written authenticated ergonomic surface
on top.

> [!IMPORTANT]
> **Unofficial.** This project is a community effort and is not affiliated with,
> endorsed by, or supported by GS1 in any way. "GS1" and "My Product Manager" are
> the property of their respective owners. Use at your own risk.

## Install

```sh
npm install @gs1belu/mpm-upload
```

## Usage

```ts
import { Gs1BeluUploadClient } from "@gs1belu/mpm-upload";

const client = new Gs1BeluUploadClient({
  environment: "uat",
  credentials: { clientId, clientSecret, subscriptionKey },
});

const result = await client.uploadAndAwaitValidation(tradeItem);
// result.status is "active" / "incomplete" / "unknown", with any validation issues attached.
```

`uploadAndAwaitValidation` submits the item and polls `GET /tradeitems/{gtin}`
until GS1's validation settles out of `pendingValidation` — the raw `POST` alone
never tells you whether the item was accepted.

## Sunset monitoring

GS1 can announce an API-version retirement in-band via the `Sunset` header (RFC
8594). Pass `onSunset` (and/or `logger`) to get warned the moment a response
carries one — including when the announced date is already in the past:

```ts
const client = new Gs1BeluUploadClient({
  environment: "uat",
  credentials: { clientId, clientSecret, subscriptionKey },
  onSunset: (notice) => console.warn(`Sunset at ${notice.parsedAt}, isPast=${notice.isPast}`),
});
```

This never alters, retries, or fails a request — it only observes and reports.

## Links

- [Source & full docs](https://github.com/WimSuenens/gs1belu.myproductmanager/tree/main/sdks/typescript/packages/mpm-upload)
- [Monorepo root](https://github.com/WimSuenens/gs1belu.myproductmanager)
- License: MIT
