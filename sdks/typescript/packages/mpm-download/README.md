# @gs1belu/mpm-fetch

Kiota-generated TypeScript client for the GS1 Belgium & Luxembourg **My Product
Manager** Download API (v17), with a hand-written authenticated ergonomic surface
on top.

> [!IMPORTANT]
> **Unofficial.** This project is a community effort and is not affiliated with,
> endorsed by, or supported by GS1 in any way. "GS1" and "My Product Manager" are
> the property of their respective owners. Use at your own risk.

## Install

```sh
npm install @gs1belu/mpm-fetch
```

## Usage

```ts
import { Gs1BeluDownloadClient } from "@gs1belu/mpm-fetch";

const client = new Gs1BeluDownloadClient({
  environment: "uat",
  credentials: { clientId, clientSecret, subscriptionKey },
});

for await (const tradeItem of client.listAllTradeItems({ informationProviderGLN: gln })) {
  console.log(tradeItem.gtin);
}
```

`listAllTradeItems` auto-follows the HAL `_links.next` pages GS1 returns, so you
never re-derive pagination yourself.

## Sunset monitoring

GS1 can announce an API-version retirement in-band via the `Sunset` header (RFC
8594). Pass `onSunset` (and/or `logger`) to get warned the moment a response
carries one — including when the announced date is already in the past:

```ts
const client = new Gs1BeluDownloadClient({
  environment: "uat",
  credentials: { clientId, clientSecret, subscriptionKey },
  onSunset: (notice) => console.warn(`Sunset at ${notice.parsedAt}, isPast=${notice.isPast}`),
});
```

This never alters, retries, or fails a request — it only observes and reports.

## Links

- [Source & full docs](https://github.com/WimSuenens/gs1belu.myproductmanager/tree/main/sdks/typescript/packages/mpm-download)
- [Monorepo root](https://github.com/WimSuenens/gs1belu.myproductmanager)
- License: MIT
