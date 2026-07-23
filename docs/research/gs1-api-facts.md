# GS1 Belgium & Luxembourg "My Product Manager" APIs — Auth & Operational Facts

Extracted from the two vendor manuals and cross-checked against the v17 OpenAPI
specs, for SDK + MCP server design.

Sources:
- `docs/manuals/UploadAPI.pdf` (7 pages) — cited as **[Upload pN]**
- `docs/manuals/DownloadAPI.pdf` (6 pages) — cited as **[Download pN]**
- `docs/schemas/upload/v17.yaml` — cited as **[upload spec]**
- `docs/schemas/download/v17.yaml` — cited as **[download spec]**

---

## 1. Auth key: same or separate for Upload vs Download?

**Not stated explicitly in either manual.** Neither manual says whether the
`Ocp-Apim-Subscription-Key` used for Upload is the same value as the one used
for Download, or whether they are separate Azure APIM products/subscriptions.
Both manuals independently describe the same OAuth2 client-credentials flow
and the same subscription-key header, but never cross-reference each other on
this point. Given this is an Azure API Management deployment with clearly
separate products (`.../upload/vN/...` vs `.../download/vN/...`, separate
`audience` values per environment — see below), it is **likely** they are
separate APIM subscriptions/keys, but this is an inference, not a documented
fact. Design SDKs/MCP config to accept two independent subscription keys
(and, per §6, possibly two independent OAuth client id/secret pairs) rather
than assuming a shared key.

**Key presentation** — both manuals and both OpenAPI specs agree:
- Header form is primary/preferred: `Ocp-Apim-Subscription-Key: <key>`
  [Upload p3, "your subscription key must be included as the value of the
  Ocp-Apim-Subscription-Key header"] [Download p4, identical wording].
- The OpenAPI specs additionally define a query-param alternative
  `subscription-key` (in: query) as a second `securitySchemes` entry, with
  `security: [apiKeyHeader: [], apiKeyQuery: []]` — i.e. either satisfies
  the security requirement [upload spec lines 573–583; download spec lines
  531–542]. The manuals **only ever show the header form** in examples/screen
  captures — the query-param option is not mentioned in either manual, so the
  header form should be treated as the documented/preferred mechanism, with
  query-param as an undocumented-in-manual fallback defined only in the spec.

Separately from the subscription key: both APIs also require an OAuth2
**Bearer access token** (see §6) sent via the `Authorization` header — the
subscription key is not a substitute for OAuth, both are required together
[Upload p3 screenshot shows both `Ocp-Apim-Subscription-Key` and
`Authorization: Bearer …` headers set on the same request; Download p4 same].

---

## 2. Environments

Both manuals confirm **two environments**: UAT (test/acceptance) and PRD
(production). Sandbox does exist — it's called UAT, not "sandbox."

### Upload API [Upload p1]
- UAT Authorization endpoint: `https://login-uat.gs1belu.org/oauth/token`
- UAT API endpoint: `https://api-uat.gs1belu.org/myproductmanager/upload/v6/tradeitems`
  (manual example uses v6; current spec is v17 — see versioning note below)
- PROD Authorization endpoint: `https://login.gs1belu.org/oauth/token`
- PROD API endpoint: `https://api.gs1belu.org/myproductmanager/upload/v6/tradeitems`

Note: elsewhere in the same manual the API endpoint example is shown as
`.../upload/v3/tradeitems` [Upload p3] and `.../upload/v1/tradeitems` in a
`Location` header example [Upload p4] — the manual is inconsistent about
which contract version it illustrates; treat the version segment as a
placeholder, not a fixed value. The **current OpenAPI spec pins the server
URL to v17**: `https://api.gs1belu.org/myproductmanager/upload/v17`
[upload spec line 6] — no UAT server is listed in the spec's `servers:`
block, only PROD, so the UAT hostname pattern must be inferred by substring
substitution (`api.` → `api-uat.`) per the manual.

### Download API [Download p1]
- UAT Authorization endpoint: `https://login-uat.gs1belu.org/oauth/token`
- UAT API endpoint: `https://api-uat.gs1belu.org/myproductmanager/download/v2/tradeitems`
- PROD Authorization endpoint: `https://login.gs1belu.org/oauth/token`
- PROD API endpoint: `https://api.gs1belu.org/myproductmanager/download/v2/tradeitems`

Current OpenAPI spec: `https://api.gs1belu.org/myproductmanager/download/v17`
[download spec line 7] — again PROD only in the spec's `servers:` list.

**Design implication:** the SDK/MCP config should expose both `environment`
(uat/prod) and `apiVersion` as independent settings, since the manual
explicitly frames the version segment in the path as consumer-selectable
["the API endpoint contains the version of the JSON contract... so you can
define the used contract yourself" — Upload p2].

---

## 3. Rate limits

Two slightly different tables appear (one per manual); Upload's is more
complete:

**From Upload manual [Upload p4]:**
- Download: 10 calls/second (600/min window); 50,000 calls/day
- Upload: 10 calls/second (600/min window); 10,000 calls/day

**From Download manual [Download p4]:**
- Download: 10 calls/second (600/min window) — **no daily cap stated here**
- Upload: 10 calls/second (600/min window); 10,000 calls/day

The Download manual omits the 50k/day figure for Download that the Upload
manual states; treat **10 req/s (600/min) as the confirmed per-second limit
for both APIs**, **10,000 calls/day as the confirmed Upload daily cap**, and
**50,000 calls/day as the Download daily cap per the Upload manual's table**
(not independently confirmed in the Download manual itself, but no
contradicting figure is given either). No mention of burst allowances,
HTTP 429 response semantics, `Retry-After` headers, or how limits reset
(rolling vs fixed window) beyond "600/min window." Neither the manuals nor
the OpenAPI specs document a `429 Too Many Requests` response schema — this
is an operational fact worth flagging to the API owner but the specs only
model 400/401/403/404 (see §5).

---

## 4. Pagination (Download GET /tradeitems)

**Discrepancy between manual and spec on max page size — flag this.**

- **Manual** [Download p6]: response is HAL format. `_links` contains
  `self` and `next`. Page size adjustable via `limit` query parameter.
  **"The maximum for the page size is limited to 100."** Worked example
  shows `limit=10`, `cursor=5d1e3dba81020c1bb4e47c87` in the `next` link,
  and a top-level `count` field alongside `_embedded.tradeItems[]`.
- **OpenAPI spec** [download spec line 14]: `description: ...Result will be
  limited to pages of 1000 items. Paging response will be in HAL format.`
- **Spec parameters** [download spec lines 22–36]: `cursor` (string, "An ID
  for the next page") and `limit` (number, "The number of tradeitems shown
  in the next page") are both optional query params with no documented
  default or max asserted in the schema itself (no `maximum:` constraint on
  `limit` in the YAML).

These two numbers (100 vs 1000) directly conflict. **Do not hardcode either
value into SDK defaults without confirming with GS1** — expose `limit` as a
pass-through parameter and drive pagination purely off the presence/absence
of `_links.next.href`, rather than assuming a fixed page size. The response
schema [download spec lines 171–192] only formally defines `_links.next.href`
and `_embedded.tradeItems[]`; the manual's example additionally shows a
`_links.self` and top-level `count` field that are **not** in the formal
schema (`additionalProperties: false` on `_links` and its `next` object
would in fact reject a `self` sibling if strictly validated — worth noting
as a spec/example mismatch).

Cursor mechanic: opaque `cursor` string appended as a query parameter,
obtained only from the previous page's `_links.next.href` — clients should
treat it as an opaque token, not construct it themselves [Download p6].

---

## 5. Errors

### problemDetails (RFC 7807-style) — both APIs
Defined identically in both specs [download spec lines 150–170; upload spec
lines 213–237]:
```
type: string (nullable)
title: string (nullable)
status: integer/int32 (nullable)
detail: string (nullable)
instance: string (nullable)
extensions: object, additionalProperties: object, nullable, readOnly   # upload spec only
```
Note: the Upload spec's `problemDetails` additionally has an `extensions`
field (not present in the Download spec's `problemDetails`, which instead
has a bare `additionalProperties: type: object` at the schema level) — a
small but real asymmetry between the two specs' error models. Used for
`401`/`403` on Upload POST, `400`/`401`/`403`/`404` on Upload GET single
item, and `400`/`401`/`403` on Download GET list [both specs' `paths`
sections]. **Neither manual narrates the problemDetails fields in prose** —
this is spec-only knowledge, not manual-documented. The only error-shape
content actually written in the manuals is the FAQ's raw OAuth error JSON:
`{"error":"access_denied","error_description":"Non-global clients are not
allowed access to APIv1"}` [Upload p7, Download p6] — caused by omitting
(or malforming) the `audience` claim (must have a trailing `/`, e.g.
`"https://api-uat.gs1belu.org/"`) in the token request.

### validationResult — Upload only
[upload spec lines 238–257], returned as the `400` body on `POST
/tradeitems`:
```
status: integer
details: array of {
  severity: string   (required)
  code: string        (required)
  message: string     (required)
}
```
This matches the manual's prose closely, EXCEPT the manual describes this
`validationResult` shape as living **inside the `metaData` section of a
successful GET response**, not as the direct `400` response body documented
in the spec:
- Upload always responds `201 Created` with an **empty body** regardless of
  data errors, plus a `Location` header pointing to where the created/updated
  item (and its validation status) can be fetched via GET [Upload p4]. This
  means **validation is asynchronous and out-of-band from the POST response**
  — the `400`/`validationResult` schema in the spec appears to be for
  synchronous/structural request errors (e.g. malformed JSON), not for GS1's
  business-rule validation, which only ever surfaces via the follow-up GET.
- The GET response's `metaData.status` field takes one of three values
  documented in prose [Upload p5]:
  - `pendingValidation` — still processing; retry later. Previously-accepted
    data remains available to recipients during this state.
  - `active` — validated, published to data recipients (no errors, or only
    non-blocking warnings).
  - `incomplete` — at least one rule violated with `severity: "error"`; item
    is NOT published to recipients.
- `metaData.validationResults[]` items have `severity` (`"error"` |
  `"warning"`), `code` (e.g. `VR_FMCGB2C_0257`, `VR_FMCGB2C_0315` — GS1
  Belgium/Lux-specific rule codes, format `VR_FMCGB2C_####`), and `message`
  (human-readable, sometimes containing embedded dates/thresholds, e.g. "no
  image is provided... every product should have at least one image... unless
  discontinued before 1/09/2021") [Upload p5].
- Severity semantics: `error` = blocking, item becomes `incomplete` and is
  withheld from publication. `warning` = non-blocking now but "scheduled to
  be elevated to blocking after a certain grace period" (grace period
  duration not specified) [Upload p5]. **Design implication:** SDK/MCP
  should surface `metaData.status` and `validationResults[]` prominently
  after upload — the true success/failure signal is NOT the HTTP status code
  of the POST (which is always 201) but the subsequent GET's `metaData`.
- No documented severity beyond `error`/`warning` (no `info`, no numeric
  severity scale). No catalogue of all `VR_FMCGB2C_*` codes is included in
  either manual — only the two examples shown.

### Sunset header (Download only)
Download API documents use of the `Sunset` header per RFC 8594 to signal
when an old API version will stop responding — "best practice is to
implement monitoring on this header, as well as preparing to process dates
in the past" [Download p4]. Not mentioned in the Upload manual (may still
apply there; simply undocumented). SDK/MCP should read and surface this
header if present, for both APIs to be safe.

---

## 6. Onboarding / auth prerequisites

- **Auth flow**: OAuth 2.0 client-credentials grant against
  `login[-uat].gs1belu.org/oauth/token`, using a `client_id` +
  `client_secret` issued per application/consumer, plus a required
  `audience` claim (`https://api[-uat].gs1belu.org/` — trailing slash
  mandatory) [Upload p2–3, p7; Download p2–3, p6]. Token response:
  `access_token`, `scope: "write:tradeitem compose:cic"` (same scope string
  shown in both manuals' examples — note it says "write" even in the
  Download example, which is odd but is what the manual literally shows),
  `expires_in: 86400` (seconds = 24h in the raw example), `token_type:
  "Bearer"` [Upload p3, Download p3].
  - **Discrepancy**: prose in both manuals says the access token is "valid
    for 12 hours" and must be cached/reused for that period [Upload p2 step
    4, bolded: "Users that don't respect this rule will be disconnected";
    Download p2 step 4]. But the captured example response shows
    `expires_in: 86400` (24 hours) and the Download manual's sequence
    diagram literally labels the caching step "Cache the access token for
    24h" [Download p2 diagram] while its own prose two lines above says
    12 hours. **This is an internal inconsistency in GS1's own manuals** —
    SDK token-cache logic should trust the `expires_in` value returned by
    the token endpoint at runtime rather than hardcoding either 12h or 24h,
    and should proactively refresh (not just react to 401s) since manuals
    explicitly warn that not caching/reusing tokens gets a client
    disconnected.
  - Whether Upload and Download use the **same client_id/client_secret** or
    separate ones per API/product is **not stated** — same gap as the
    subscription-key question in §1. The two manuals independently show
    near-identical Postman captures with different `audience` values
    (`https://api.gs1belu.org/` in both actually — Download's captured
    audience example literally reads `https://api.gs1belu.org/` even though
    the surrounding text is about UAT in the FAQ using `-uat`), suggesting
    the mechanism is identical but credential scoping per-product is
    unconfirmed.
- **GLN prerequisites**: A GLN (13-digit, worldwide-unique) identifies the
  "party providing the product information" (`informationProviderGLN`) and
  is required as `required: [gln]` on the `party` schema used for both
  `informationProvider` and `brandOwner` in both specs [upload/download spec
  `party` schema]. Manuals don't describe an explicit "GLN registration"
  onboarding step or prerequisite process (e.g., how a supplier's GLN gets
  whitelisted) — only that `informationProviderGLN` is a valid Download
  filter [Download p5] and that `informationProvider`/`brandOwner` with
  `gln` are required fields on the trade item payload [both specs]. No
  explicit statement that the GLN must match the credential's registered
  organisation, though this is implied by "the party who is providing the
  product information."
- **How to obtain a subscription key**: **Not described in either manual.**
  Both manuals assume the reader already has a `client_id`/`client_secret`
  and subscription key in hand; neither documents the registration/sign-up
  process, an Azure APIM developer portal, or a contact/request procedure.
  Only a pointer to further docs is given: Upload manual links to "How can I
  create product data in My Product Manager? | GS1 Belgium & Luxembourg
  (gs1belu.org)" for latest contract info [Upload p2], and Download manual
  points to `https://www.gs1belu.org/nl/my-product-manager` [Download p2] —
  neither URL was fetched as part of this local-document task (out of scope:
  task specified local PDF extraction only).
- **Idempotency of the upsert**: Confirmed **only in the OpenAPI spec, not
  in the manual prose**. `POST /tradeitems` `operationId: upsert-tradeitem`,
  description: "Idempotent upload for a single trade item. This operation
  will insert a new trade item when not existing or will update the existing
  trade item." [upload spec lines 12–14]. Idempotency key appears to be the
  trade item's `gtin` (a required field on every upload) combined implicitly
  with the authenticated `informationProvider` — the manual's "Consulting
  Uploaded Data" section shows the `Location` header pointing to
  `.../tradeitems/{gtin}` as the identifier used to re-fetch [Upload p4],
  and the single-item GET endpoint is `/tradeitems/{gtin}` [upload spec
  lines 102–116]. No separate idempotency-key header (e.g.
  `Idempotency-Key`) is mentioned or modeled anywhere — re-POSTing the same
  GTIN payload is itself the idempotent operation, not a header-based
  mechanism.
- **Publication settings** (Upload only, tangential to auth but relevant to
  onboarding): which data recipients can see a supplier's uploaded data is
  **not configurable via the Upload API at all** — must be set through the
  My Product Manager web UI, though a "Default" publication setting can be
  configured there to apply to every new trade item created via the API
  [Upload p6]. This is a hard gap for any MCP/SDK design: publication access
  control is out-of-band and cannot be automated via API.
- **Content-Type**: `POST` requests must include `Content-Type:
  application/json` [Upload p3].

---

## Open questions (not resolved by manuals or specs)

1. Are Upload and Download subscription keys / OAuth credentials the same
   or different per-product APIM subscriptions? (§1, §6)
2. True max/default page `limit` for Download pagination — manual says 100,
   spec prose says 1000. (§4)
3. Grace period duration before a `warning`-severity validation rule becomes
   blocking. (§5)
4. True access-token TTL — manual prose says 12h, captured example +
   Download's own diagram say 24h (`expires_in: 86400`). (§6)
5. Whether `429 Too Many Requests` has a documented body/shape, and whether
   `Retry-After` is honored — not in manuals or specs.
6. How a new consumer actually registers to get `client_id`/`client_secret`
   + subscription key (process not documented locally; only external portal
   links given, not fetched in this task).
