# Splitting the MCP server: two servers per repo + deprecating the combined one

Research for map #73 (split `gs1belu-mpm-mcp` into independent **Upload** and **Download** MCP
servers). Question: can **one GitHub repo publish two independent servers** to the official MCP
Registry, and how do we **deprecate/supersede** the already-planned combined registry entry
(`io.github.wimsuenens/gs1belu-mpm`) and its PyPI package? Primary sources only; each claim cited.
Research date: **2026-07-27**.

Some facts here were first captured for the single-server plan in
[`mcp-landscape.md`](./mcp-landscape.md) and [`registry-oidc.md`](./registry-oidc.md); every claim
carried forward has been re-verified against the live primary source below.

---

## 1. One repo, two independent registry servers — yes, no per-repo limit

**Namespace auth grants the whole personal namespace, not a single server.** The registry's
authentication model ties a login to a GitHub *user/org account*, and authorizes the entire
`io.github.<username>/*` namespace — any server name matching that pattern — not one server ID and
not one repository. The publishing quickstart's own error text confirms the only name constraint:
*"With GitHub auth, your server name must start with `io.github.your-username/`."*
[[quickstart.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
[[authentication.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/authentication.mdx)

**No one-server-per-repo constraint exists.** Nothing in the registry requirements ties a server
name to a repository. The quickstart's own worked example proves the decoupling: the repository is
`mcp-weather-server` but the published server name is `io.github.my-username/weather` — the server
ID need not match the repo name.
[[quickstart.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
So `io.github.wimsuenens/gs1belu-mpm-upload` and `io.github.wimsuenens/gs1belu-mpm-download` can
both be published from this single repo — each is just its own `server.json` published under the
same namespace grant.

**Per-package ownership marker is per-server, not per-repo.** Ownership verification is checked
per package, independently of the namespace login. For PyPI/NuGet the package **README** must
carry an `mcp-name: <server-name>` line (plain text or an HTML comment); for npm it is the
`mcpName` field in `package.json`.
[[quickstart.mdx troubleshooting]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
[[official-registry-requirements.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)
Two servers therefore need **two packages, each with its own README marker** naming its own server
(`mcp-name: io.github.wimsuenens/gs1belu-mpm-upload` in the upload package's README, and the
download equivalent in the download package's). The marker binds a *package* to a *server name*; it
imposes no repo-level uniqueness.

**GitHub OIDC in CI scopes to the repo *owner*, granting the whole namespace.** The GitHub Actions
flow authenticates with `./mcp-publisher login github-oidc` (no stored secret needed). The
resulting registry token is scoped to the account namespace, not a single server: for an org login
the token *"can publish — and overwrite — **any** server under `io.github.<org>/*`, not just the
one in this repository"* — the same breadth applies to a personal namespace keyed off the repo
owner.
[[github-actions.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx)
Practically: one workflow in this repo can publish both `server.json` files by running
`mcp-publisher publish` once per file after a single OIDC login. (Consistent with the SDK-side
precedent of per-package publish jobs — map #1 #10/#13.)

**Conclusion (sub-question 1):** Yes. One repo → two server IDs under `io.github.wimsuenens/*`,
each with its own `server.json` and its own package README `mcp-name` marker, published by one
OIDC-authenticated workflow. No registry rule caps servers per repo or per namespace.

---

## 2. Deprecating / superseding the combined registry entry — `status`, not deletion

**The `server.json` document has no lifecycle field.** `status` is **registry-managed metadata**,
returned in the API response's `_meta`, not a field you write into `server.json`. The generic
`server.json` schema exposes no status/deprecation/replacement field.
[[generic-server-json.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md)
[[registry-aggregators.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx)

**Lifecycle is a `status` enum with three values**, set after publication:
- `active` — "Server is active and visible in default listings"
- `deprecated` — "Server is deprecated but still visible with a warning message"
- `deleted` — "Server is hidden from default listings (use `include_deleted=true` to show)"

[[official-registry-api.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md)

**Publishers set it themselves — no admin required.** Status is changed via
`PATCH /v0.1/servers/{serverName}/status` (all versions) or
`PATCH /v0.1/servers/{serverName}/versions/{version}/status` (single version), with a body of
`status` (required) and `statusMessage` (optional, <=500 chars, disallowed when `status` is
`active`). Authorization is *"`publish` or `edit` permission for the server namespace"* — i.e. the
namespace owner, not only registry admins.
[[official-registry-api.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md)
The `mcp-publisher` CLI wraps this as a `status` subcommand, e.g.:

```bash
mcp-publisher status --status deprecated \
  --message "Superseded by io.github.wimsuenens/gs1belu-mpm-upload and .../gs1belu-mpm-download" \
  io.github.wimsuenens/gs1belu-mpm 1.0.0
```

[[cli/commands.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/cli/commands.md)
(Admin-only takedown/edit tooling also exists — `PUT .../versions/{version}` and
`tools/admin/takedown.sh` — but those require a `@modelcontextprotocol.io` admin account and are
not the self-service path.)
[[admin-operations.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/administration/admin-operations.md)

**There is no structured "superseded-by / replacement pointer" field.** The registry models
deprecation as a status plus a free-text `statusMessage`; it has no machine-readable field pointing
at successor server IDs. The migration pointer therefore lives in the `statusMessage` string (and
in the deprecated package's README/description).
[[official-registry-api.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md)

**Conclusion (sub-question 2):** Publish the two successors first, then `PATCH` the combined
`io.github.wimsuenens/gs1belu-mpm` to `status=deprecated` with a `statusMessage` naming both
successor server IDs. Keep it `deprecated` (still discoverable with a warning), not `deleted`
(hidden; semantically reserved for moderation/spam/malware takedowns per the aggregator docs).
[[registry-aggregators.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx)

---

## 3. Deprecating the combined PyPI package while keeping it installable

Three mechanisms, addressing different needs; for a superseded-but-working package the answer is
**archive the project (+ a final pointer release)**, not yank.

**(a) Yank (PEP 592) — wrong tool here.** Yanking marks *a specific release/file* as should-not-be-
installed **without deleting it**. Resolution semantics: *"Yanked files are always ignored, unless
they are the only file that matches a version specifier that 'pins' to an exact version using
either `==` (without any modifiers that make it a range, such as `.*`) or `===`"* — or the only file
a lock file pins. Installers **SHOULD** warn when installing a yanked file. So `pip install pkg`
skips a yanked release, but `pip install pkg==1.2.3` (exact pin) or a lockfile pin still gets it.
[[PEP 592]](https://peps.python.org/pep-0592/)
Yank is designed for *broken* releases, not for signalling "this project is superseded" — and it is
per-release, not a project-level status. Using it to retire a *working* combined package would
punish clean-pin consumers for no correctness reason.

**(b) Project archival (PyPI, since 2025-01-30) — the right primary mechanism.** PyPI now lets an
owner mark a whole **project** as archived: *"Archiving a project does not remove it from the index,
and does not prevent users from installing it"* — it stays fully installable. Archival *"prevents
new uploads to the project,"* shows an archived notice on the project page, is reversible
(*"project owners can always unarchive"*), and is explicitly *"not deletion ... PyPI has no plans to
delete or prune archived distributions."*
[[PyPI blog: project archival]](https://blog.pypi.org/posts/2025-01-30-archival/)
This is the cleanest "deprecated but installable" signal: it retains the name (blocking
name-resurrection supply-chain attacks) without breaking any existing pin.

**(c) Pointing users to the replacements — final release + README.** PyPI has **no structured
"superseded-by" field** (a broader project-status API beyond archival is still future work per the
archival announcement). Best practice: cut **one final version** of `gs1belu-mpm` whose README/long
description prominently states it is deprecated and names the two replacement packages
(`gs1belu-mpm-upload`, `gs1belu-mpm-download`) with install instructions, optionally set the
`Development Status :: 7 - Inactive` Trove classifier, **then archive the project**. The README is
the PyPI description, so the pointer is visible on the project page; archival adds the machine-
visible status marker.
[[PyPI blog: project archival]](https://blog.pypi.org/posts/2025-01-30-archival/)
[[PyPI classifiers]](https://pypi.org/classifiers/)

**Conclusion (sub-question 3):** Don't yank the combined package. Publish a final
deprecation-pointer release, then **archive** the `gs1belu-mpm` PyPI project — it stays installable
and pinnable, new uploads are blocked, the name is retained, and the README points to the two
successors. (Reserve yank for genuinely broken individual releases.)

---

## 4. OIDC Trusted Publishing impact of two new package names

**Trusted Publishers are per-project, so each new package name needs its own config.** A PyPI
trusted publisher authorizes a specific workflow to mint short-lived tokens *for that project only*
— *"Projects on PyPI can be configured to trust a particular configuration on a particular CI
service, making that configuration an OIDC publisher for that project."*
[[PyPI: trusted publishers]](https://docs.pypi.org/trusted-publishers/)
Adding `gs1belu-mpm-upload` and `gs1belu-mpm-download` therefore means **two new trusted-publisher
registrations**, one per package name (the existing `gs1belu-mpm` config does not cover them).

**Bootstrapping brand-new names: pending publishers, one per name.** Because neither new project
exists on PyPI yet, register a **pending publisher** for each — created from the account sidebar,
where *"you also need to provide the name of the PyPI project that will be created."* A pending
publisher *"does not create a project or reserve a project's name until it is actually used to
publish"* (race risk: if someone else claims the name first, the pending publisher is invalidated),
and it *auto-converts to a normal publisher on first publish*.
[[PyPI: creating a project through OIDC]](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
So: two pending publishers (upload + download), each naming its project, its repo
(`WimSuenens/gs1belu.myproductmanager`), workflow filename, and — strongly recommended — an
environment. Publishing the two names early to claim them mitigates the name-race.

**Attestations (PEP 740) come for free, per project.** PyPI implements PEP 740 digital
attestations, and they are **enabled by default** for any project published via a Trusted Publisher
using `pypa/gh-action-pypi-publish@release/v1` (v1.11.0+) — no extra config, no `--provenance` flag.
Each new package automatically gets build provenance once it publishes through its trusted
publisher.
[[PyPI blog: digital attestations]](https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/)
[[PEP 740]](https://peps.python.org/pep-0740/)

**Conclusion (sub-question 4):** Yes — each new package name needs its own trusted-publisher (or
pending-publisher) registration; there is no account-wide grant. The GitHub Actions permission
(`id-token: write`) and the publish action are unchanged; attestations are automatic per project.
The registry-side `io.github.wimsuenens/*` namespace grant (section 1) is entirely separate from
these PyPI per-project publisher configs — two independent authorization systems.

---

## Summary decision table

| Concern | Decision | Primary source |
|---|---|---|
| Two servers from one repo | Yes — two `server.json` under `io.github.wimsuenens/*`, each with its own README `mcp-name`; no per-repo cap | quickstart.mdx, authentication.mdx |
| CI publishing both | One `github-oidc` login -> `mcp-publisher publish` per file; token covers the whole namespace | github-actions.mdx |
| Retire combined registry entry | `PATCH .../status` -> `deprecated` + `statusMessage` naming successors (self-service; not `deleted`) | official-registry-api.md, cli/commands.md |
| Registry replacement pointer | None structured — free-text `statusMessage` only | official-registry-api.md |
| Retire combined PyPI package | Final pointer release + **archive** the project (stays installable; not yank) | PyPI archival blog |
| Yank | Reserve for broken individual releases; skipped by resolvers except exact `==`/`===` pins & lockfiles | PEP 592 |
| New PyPI packages + OIDC | Per-project trusted/pending publisher for each new name; attestations automatic | PyPI trusted-publishers docs, PEP 740 |

---

## Open questions

- **Version-scoped vs. all-versions deprecation.** The API offers both
  `PATCH .../versions/{version}/status` and `PATCH .../servers/{serverName}/status`. For a full
  product retirement the all-versions PATCH is the intent, but this hasn't been exercised against a
  live registry entry — confirm the CLI `status` subcommand targets all versions when the version
  arg is omitted.
  [[official-registry-api.md]](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md)
- **Registry is still "preview."** The registry remains labelled preview with possible data resets
  / breaking changes before GA (per `mcp-landscape.md` section 2.1); the `v0.1` status API could
  still shift. Re-verify endpoint paths at execution time.
- **Client surfacing of `deprecated`.** How prominently MCP clients/aggregators show the
  `deprecated` warning + `statusMessage` to end users is client-dependent and not guaranteed by the
  registry; the PyPI README pointer and archival notice are the more reliable user-facing signals.
- **Downstream aggregators lag.** Aggregators are only *advised* to keep each server's `status` in
  sync; a deprecated combined server may still appear `active` in third-party mirrors for a while.
  [[registry-aggregators.mdx]](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx)

---

## Sources

- [modelcontextprotocol/registry: quickstart.mdx](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx)
- [modelcontextprotocol/registry: authentication.mdx](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/authentication.mdx)
- [modelcontextprotocol/registry: github-actions.mdx](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx)
- [modelcontextprotocol/registry: official-registry-requirements.md](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/official-registry-requirements.md)
- [modelcontextprotocol/registry: generic-server-json.md](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md)
- [modelcontextprotocol/registry: official-registry-api.md](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md)
- [modelcontextprotocol/registry: cli/commands.md](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/cli/commands.md)
- [modelcontextprotocol/registry: admin-operations.md](https://github.com/modelcontextprotocol/registry/blob/main/docs/administration/admin-operations.md)
- [modelcontextprotocol/registry: registry-aggregators.mdx](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/registry-aggregators.mdx)
- [PEP 592 – Adding "Yank" Support to the Simple API](https://peps.python.org/pep-0592/)
- [PEP 740 – Index support for digital attestations](https://peps.python.org/pep-0740/)
- [PyPI Blog: PyPI now supports project archival (2025-01-30)](https://blog.pypi.org/posts/2025-01-30-archival/)
- [PyPI Blog: PyPI now supports digital attestations (2024-11-14)](https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/)
- [PyPI Docs: Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [PyPI Docs: Creating a PyPI project with a Trusted Publisher (pending publishers)](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [PyPI classifiers list](https://pypi.org/classifiers/)
