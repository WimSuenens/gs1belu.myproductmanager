# Trusted publishing (GitHub Actions OIDC) for NuGet.org, npmjs.com, and PyPI

Research date: **2026-07-23**. Package-registry OIDC/"trusted publishing" support has been moving fast over the last two years, so treat exact rollout/GA dates and workflow syntax below as a snapshot verified against primary sources on this date — re-check before relying on it for a new integration.

## Comparison summary

| Registry | OIDC trusted publishing | Status as of 2026-07-23 | Since | Official publish mechanism |
|---|---|---|---|---|
| NuGet.org | Yes | Rolling out gradually (not yet available to all accounts) | Documented as of NuGet docs update 2025-07-01 | [`NuGet/login@v1`](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing) action + `dotnet nuget push` |
| npmjs.com | Yes | **GA** | 2025-07-31 | Native OIDC support in `npm publish` (CLI ≥ 11.5.1) |
| PyPI | Yes | GA (oldest of the three) | 2023-04-20 | [`pypa/gh-action-pypi-publish@release/v1`](https://docs.pypi.org/trusted-publishers/using-a-publisher/) |

---

## NuGet.org

### 1. OIDC support status

NuGet.org's Trusted Publishing lets a GitHub Actions (or other CI/CD) workflow exchange a short-lived GitHub OIDC token for a temporary, single-use NuGet API key, instead of a long-lived stored API key. [Trusted Publishing on nuget.org](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing)

Status is notably **not a flat GA for all accounts as of this research date**: the docs page carries an explicit warning — "If you don't see the Trusted Publishing option in your nuget.org account, it might not be available to you yet. We're rolling it out gradually." [Trusted Publishing on nuget.org](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing) The docs page's `ms.date` metadata is 2025-07-01, with a last-updated timestamp of 2026-02-02, confirming the feature has existed and been actively maintained for roughly a year but is still in staged rollout. The .NET Blog also covers this as "New Trusted Publishing enhances security on NuGet.org." [.NET Blog](https://devblogs.microsoft.com/dotnet/enhanced-security-is-here-with-the-new-trust-publishing-on-nuget-org/)

### 2. Exact setup

**Registry-side configuration** (on nuget.org, under your username → **Trusted Publishing**): create a policy specifying, case-insensitively:
- **Repository Owner** (e.g. `contoso`)
- **Repository** (e.g. `contoso-sdk`)
- **Workflow File** — file name only, e.g. `build.yml` (do **not** include the `.github/workflows/` path prefix)
- **Environment** (optional) — set this if your workflow uses `environment: release` and you want the policy restricted to that GitHub Actions environment

A policy is owned by either an individual user or an organization you belong to, and applies to all packages owned by that owner. [Trusted Publishing on nuget.org](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing)

Note on private repos: a newly created policy is only *temporarily* active for 7 days until a successful publish supplies GitHub's repo/owner IDs (this locks the policy to the exact repo, preventing "resurrection attacks" via repo delete+recreate). The 7-day window can be restarted if it lapses without a publish. [Trusted Publishing on nuget.org](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing)

**Required workflow permission block:**

```yaml
permissions:
  id-token: write  # enable GitHub OIDC token issuance for this job
```

**Official action + publish command:**

```yaml
- name: NuGet login (OIDC → temp API key)
  uses: NuGet/login@v1
  id: login
  with:
    user: contoso-bot  # your nuget.org username (profile name), not email

- name: NuGet push
  run: dotnet nuget push artifacts/my-sdk.nupkg --api-key ${{ steps.login.outputs.NUGET_API_KEY }} --source https://api.nuget.org/v3/index.json
```

`NuGet/login@v1` exchanges the GitHub OIDC token for a temporary NuGet API key (valid for **1 hour**, single-use — one OIDC token yields exactly one temporary API key), which is then passed to `dotnet nuget push` via `--api-key`. [Trusted Publishing on nuget.org](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing)

### 3. Provenance / attestation support

NuGet's trust story is primarily **package signing**, which is a separate, older mechanism from Trusted Publishing rather than a byproduct of it. nuget.org requires the primary signature on a package to be an **author signature** with a single valid timestamp, chaining to a root CA trusted by default on Windows (self-issued certs are rejected); a **repository signature** additionally covers integrity for all packages in a repo regardless of author-signing. [Signed Packages Reference](https://learn.microsoft.com/en-us/nuget/reference/signed-packages-reference) The Trusted Publishing docs page does not describe an attestation format analogous to npm provenance or PEP 740 — it frames the security benefit purely in terms of eliminating long-lived credentials (short-lived, single-use temporary API keys). [Trusted Publishing on nuget.org](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing)

### 4. Fallback if OIDC isn't viable

Use a **scoped NuGet API key** rather than Trusted Publishing. NuGet.org supports **Scoped API keys**: each key can be restricted to specific packages or a glob pattern (e.g. a single package name, or a prefix pattern covering a package family), to specific operations (push new packages/versions, push versions only, unlist, etc.), and given an expiration timeframe. [Scoped API keys | Microsoft Learn](https://learn.microsoft.com/en-us/nuget/nuget-org/scoped-api-keys) This lets you avoid an account-wide key. Conventionally the resulting key is stored as a GitHub Actions **repository or environment secret** and passed to `dotnet nuget push --api-key ${{ secrets.NUGET_API_KEY }}`.

---

## npmjs.com

### 1. OIDC support status

npm trusted publishing with OIDC is **generally available (GA) as of 2025-07-31**, per GitHub's own changelog announcement. [npm trusted publishing with OIDC is generally available – GitHub Changelog](https://github.blog/changelog/2025-07-31-npm-trusted-publishing-with-oidc-is-generally-available/) The npm docs describe it as: "Trusted publishing allows you to publish npm packages directly from your CI/CD workflows using OpenID Connect (OIDC) authentication." [Trusted publishing for npm packages | npm Docs](https://docs.npmjs.com/trusted-publishers/)

Supported CI/CD providers (as of this research date): **GitHub Actions** (GitHub-hosted runners), **GitLab CI/CD** (GitLab.com shared runners), and **CircleCI** (CircleCI cloud). Self-hosted/private runners are **not** currently supported for any provider. [Trusted publishing for npm packages | npm Docs](https://docs.npmjs.com/trusted-publishers/)

### 2. Exact setup

**Registry-side configuration** (on npmjs.com, in the package's **Settings** → **Trusted Publisher** section): select the CI/CD provider (GitHub Actions), then specify:
- Organization/user and repository
- Workflow filename
- Environment name (optional, used for GitHub Actions deployment-protection restrictions)
- Allowed actions — choose `npm publish`, `npm provenance publish`/staged publish, or both

[Trusted publishing for npm packages | npm Docs](https://docs.npmjs.com/trusted-publishers/)

**Required workflow permission block:**

```yaml
permissions:
  id-token: write
```

This is the standard GitHub Actions permission that "allows GitHub Actions to generate OIDC tokens." [Trusted publishing for npm packages | npm Docs](https://docs.npmjs.com/trusted-publishers/)

**Minimum npm CLI version: 11.5.1** (Node.js ≥ 22.14.0). No separate action is required — a standard `npm publish` command is used; the npm CLI itself auto-detects the OIDC environment and performs the token exchange when a matching trusted publisher is configured on the registry side. [Trusted publishing for npm packages | npm Docs](https://docs.npmjs.com/trusted-publishers/)

### 3. Provenance / attestation support

Provenance is tightly coupled to trusted publishing on npm: when publishing via trusted publishing from GitHub Actions or GitLab CI/CD (not currently CircleCI), **provenance attestations are generated automatically**, and the `--provenance` flag is no longer needed to opt in. [Trusted publishing for npm packages | npm Docs](https://docs.npmjs.com/trusted-publishers/) This applies to public repositories/public packages.

### 4. Fallback if OIDC isn't viable

Use a **granular access token**, scoped to specific packages and/or scopes rather than the whole account. npm's granular access tokens can be restricted to up to 50 organizations and up to 50 packages/scopes (or a combination), and can optionally be marked to bypass 2FA specifically for CI/automation use. A token's effective permissions can never exceed the creating user's own permissions, and access is automatically revoked from the token if the user's access to a package/org is revoked. [About access tokens | npm Docs](https://docs.npmjs.com/about-access-tokens/) Tokens are created via `npm token create` or at `npmjs.com/settings/~/tokens`, and conventionally stored as a GitHub Actions repository or environment secret. Note: npm has been actively tightening legacy token support — classic (non-granular) token creation has been disabled and classic tokens revoked as part of a broader push toward OIDC/granular tokens (per GitHub's npm security changelogs from late 2025), reinforcing granular, scoped tokens as the only reasonable non-OIDC fallback.

---

## PyPI

### 1. OIDC support status

PyPI is the **earliest and most mature** of the three registries for this: Trusted Publishers (PyPI's name for OIDC-based publishing) launched **2023-04-20** and was GA immediately at launch — "Starting today, PyPI package maintainers can adopt a new, more secure publishing method." [Introducing 'Trusted Publishers' – PyPI Blog](https://blog.pypi.org/posts/2023-04-20-introducing-trusted-publishers/) It "eliminates the need to use username/password combinations or manually generated API tokens to authenticate with PyPI when publishing," using tokens that "never need to be stored or shared, rotate automatically by expiring quickly." [Introducing 'Trusted Publishers' – PyPI Blog](https://blog.pypi.org/posts/2023-04-20-introducing-trusted-publishers/) OIDC identity tokens used in the exchange expire **15 minutes** from creation. [Trusted publishers: Internals and Technical Details – PyPI Docs](https://docs.pypi.org/trusted-publishers/internals/)

### 2. Exact setup

**Registry-side configuration**: on PyPI, go to **Your projects** → **Manage** (for the target project) → **Publishing**, and register a GitHub Actions publisher with:
- **Repository owner** (required)
- **Repository name** (required)
- **Workflow filename** (required)
- **Environment name** (optional but **strongly recommended** — it lets you add extra protections such as requiring manual approval from trusted maintainers before each publish run)

[Adding a Trusted Publisher to an Existing PyPI Project – PyPI Docs](https://docs.pypi.org/trusted-publishers/adding-a-publisher/) Once registered, the specified workflow file in that specific repo becomes authorized to request short-lived PyPI API tokens for that project only. PyPI also supports "pending" trusted publishers, letting you pre-register a publisher for a project that doesn't exist on PyPI yet, so the very first release can use trusted publishing (no manual API-token bootstrap step required). [Adding a Trusted Publisher to an Existing PyPI Project – PyPI Docs](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)

**Required workflow permission block** (job-level is strongly recommended over workflow-level):

```yaml
permissions:
  id-token: write
```

[Publishing with a Trusted Publisher – PyPI Docs](https://docs.pypi.org/trusted-publishers/using-a-publisher/)

**Official GitHub Action:** `pypa/gh-action-pypi-publish@release/v1`. Example:

```yaml
jobs:
  pypi-publish:
    name: upload release to PyPI
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - name: Publish package distributions to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
```

No explicit `username`/`password` (or token) parameters are supplied to the action — GitHub's OIDC identity provider handles the exchange automatically. [Publishing with a Trusted Publisher – PyPI Docs](https://docs.pypi.org/trusted-publishers/using-a-publisher/)

### 3. Provenance / attestation support

PyPI implements **PEP 740** ("Index support for digital attestations"), live since November 2024. Digital attestations are cryptographically signed, publicly verifiable statements about a package's provenance (e.g. which exact source repo/workflow produced it). [PyPI now supports digital attestations – PyPI Blog](https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/) Crucially, PEP 740 attestations are **enabled by default for projects already using Trusted Publishing with the canonical `pypa/gh-action-pypi-publish` action** — "so long as you already use (or upgrade to) `pypa/gh-action-pypi-publish@release/v1` or newer and with a Trusted Publisher, your packages will get build provenance by default," with attestation support built into the action as of v1.11.0+. [PyPI now supports digital attestations – PyPI Blog](https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/) A new **Integrity API** exposes these attestations programmatically per-file. [PyPI now supports digital attestations – PyPI Blog](https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/)

### 4. Fallback if OIDC isn't viable

Use a **project-scoped PyPI API token** rather than an account-wide one: "you can create a token for an entire PyPI account... or alternatively, you can limit a token's scope to a specific project." [PyPI Help](https://pypi.org/help/) PyPI's own guidance is explicit about preferring OIDC first: "If you are publishing to PyPI from a CI provider that supports Trusted Publishing, we strongly recommend using Trusted Publishing instead" of an API token. [PyPI Help](https://pypi.org/help/) When a token must be used, PyPI recommends scoping it "down to the minimum necessary projects" for CI use. [PyPI Help](https://pypi.org/help/) Conventionally, such a token is stored as a GitHub Actions repository or environment secret and passed to `pypa/gh-action-pypi-publish` (or `twine`) via the `password`/token input instead of relying on OIDC.

---

## Sources consulted

- [Trusted Publishing on nuget.org – Microsoft Learn](https://learn.microsoft.com/en-us/nuget/nuget-org/trusted-publishing)
- [New Trusted Publishing enhances security on NuGet.org – .NET Blog](https://devblogs.microsoft.com/dotnet/enhanced-security-is-here-with-the-new-trust-publishing-on-nuget-org/)
- [Scoped API keys – Microsoft Learn](https://learn.microsoft.com/en-us/nuget/nuget-org/scoped-api-keys)
- [Signed Packages Reference – Microsoft Learn](https://learn.microsoft.com/en-us/nuget/reference/signed-packages-reference)
- [Trusted publishing for npm packages – npm Docs](https://docs.npmjs.com/trusted-publishers/)
- [About access tokens – npm Docs](https://docs.npmjs.com/about-access-tokens/)
- [npm trusted publishing with OIDC is generally available – GitHub Changelog](https://github.blog/changelog/2025-07-31-npm-trusted-publishing-with-oidc-is-generally-available/)
- [Publishing to PyPI with a Trusted Publisher – PyPI Docs](https://docs.pypi.org/trusted-publishers/)
- [Publishing with a Trusted Publisher – PyPI Docs](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [Adding a Trusted Publisher to an Existing PyPI Project – PyPI Docs](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
- [Trusted publishers: Internals and Technical Details – PyPI Docs](https://docs.pypi.org/trusted-publishers/internals/)
- [Introducing 'Trusted Publishers' – PyPI Blog](https://blog.pypi.org/posts/2023-04-20-introducing-trusted-publishers/)
- [PyPI now supports digital attestations – PyPI Blog](https://blog.pypi.org/posts/2024-11-14-pypi-now-supports-digital-attestations/)
- [PyPI Help (API tokens)](https://pypi.org/help/)
- [About security hardening with OpenID Connect – GitHub Docs](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)
