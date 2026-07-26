# Gs1Belu.MyProductManager.Download

Kiota-generated C# client for the GS1 Belgium & Luxembourg **My Product Manager**
Download API (v17), with a hand-written authenticated ergonomic surface on top.

> [!IMPORTANT]
> **Unofficial.** This project is a community effort and is not affiliated with,
> endorsed by, or supported by GS1 in any way. "GS1" and "My Product Manager" are
> the property of their respective owners. Use at your own risk.

## Install

```sh
dotnet add package Gs1Belu.MyProductManager.Download
```

## Usage

```csharp
using Gs1Belu.MyProductManager.Download;

var credentials = new Gs1BeluCredentials(clientId, clientSecret, subscriptionKey);
var client = new Gs1BeluDownloadClient(Gs1BeluEnvironment.Uat, credentials);

await foreach (var tradeItem in client.ListAllTradeItemsAsync(q => q.InformationProviderGLN = gln))
{
    Console.WriteLine(tradeItem.Gtin);
}
```

`ListAllTradeItemsAsync` auto-follows the HAL `_links.next` pages GS1 returns, so
you never re-derive pagination yourself.

## Sunset monitoring

GS1 can announce an API-version retirement in-band via the `Sunset` header (RFC
8594). Pass `onSunset` (and/or `logger`) to get warned the moment a response
carries one — including when the announced date is already in the past:

```csharp
var client = new Gs1BeluDownloadClient(Gs1BeluEnvironment.Uat, credentials,
    onSunset: notice => Console.WriteLine($"Sunset at {notice.ParsedAt}, isPast={notice.IsPast}"));
```

This never alters, retries, or fails a request — it only observes and reports.

## Links

- [Source & full docs](https://github.com/WimSuenens/gs1belu.myproductmanager/tree/main/sdks/dotnet/Gs1Belu.MyProductManager.Download)
- [Monorepo root](https://github.com/WimSuenens/gs1belu.myproductmanager)
- License: MIT
