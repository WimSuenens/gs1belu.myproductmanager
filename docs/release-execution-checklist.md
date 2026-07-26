# Release execution checklist

Everything release-please and the three `publish-*.yml` workflows need to actually
fire is **configured** by [#53](https://github.com/WimSuenens/gs1belu.myproductmanager/issues/53).
None of it is **activated** yet — that's a deliberate scope line (see the issue's
"Out of Scope" section): a live OIDC publish can't be exercised in CI without really
publishing, so the human steps below are a one-time, manual, checked-off-by-hand
sequence, not something a merge triggers automatically.

Until every item below is done, the workflows fail **safely and visibly** (a red X
in the Actions tab, an auth error) rather than silently publishing something wrong.
Nothing here can be skipped by accident — each publish job needs its own
registry-side trust relationship before it can authenticate at all.

## 1. Repository

- [x] Public (`gh repo view --json visibility` → `PUBLIC`). Required for npm's
      automatic provenance and generally for OIDC Trusted Publishing everywhere.
- [x] Root `LICENSE` (MIT) present.

## 2. The GitHub App (gates `release-please.yml` — do this first)

`release-please.yml` mints a short-lived installation token via
`actions/create-github-app-token` and uses it to push the per-package
`<component>-v<version>` tags — the default `GITHUB_TOKEN` is deliberately never
used here, since GitHub's anti-recursion guard silently drops workflow triggers
for tags it pushes.

- [ ] Register a GitHub App (Settings → Developer settings → GitHub Apps, or an
      org-owned app) with **Contents: Read & write** and **Pull requests: Read &
      write** permissions on this repository only.
- [ ] Install the app on this repository.
- [ ] Set repo **variable** `RELEASE_PLEASE_APP_ID` = the app's App ID.
- [ ] Set repo **secret** `RELEASE_PLEASE_APP_PRIVATE_KEY` = the app's generated
      private key (`.pem` contents).

Once both exist, every push to `main` runs `release-please.yml` successfully and
it maintains a standing release PR with the pending per-package version bumps.
**Merging that release PR** (a separate, later, deliberate action — not this one)
is what pushes the tags and fires the publish workflows below.

## 3. npm (`publish-npm.yml` — `mpm-upload-v*` / `mpm-fetch-v*`)

- [ ] Create the `@gs1belu` org on npmjs.com (if it doesn't already exist).
- [ ] **Publish each package once manually first**, with a classic/granular
      token (`npm publish` from your machine or a one-off local run of the
      commands in `publish-npm.yml`). npm's trusted-publisher config lives on
      the *package's own* Settings page, which only exists once the package
      has been published at least once — unlike PyPI, npm has no "pending
      publisher, reserve the name in advance" flow. (Not fully confirmed in
      npm's own docs at time of writing — verify this against the current
      npmjs.com UI before relying on it; if it turns out a brand-new,
      never-published scope *can* be pre-registered, skip the manual publish.)
- [ ] Then, for each package: npmjs.com → the package page → **Settings** →
      **Trusted Publisher** → **GitHub Actions** → fill in Organization/user
      `WimSuenens`, Repository `gs1belu.myproductmanager`, Workflow filename
      `publish-npm.yml` (filename only), Environment name **left blank** (this
      workflow doesn't declare a GitHub Actions `environment:`), Allowed
      actions: `npm publish`.
- [ ] Nothing else — no token, no secret, once configured. OIDC only
      (`id-token: write` is already wired in the workflow).
- Fallback (only if Trusted Publishing isn't available yet): store a granular
  access token, scoped to exactly these two packages, as secret
  `NPM_GRANULAR_TOKEN`, and swap in the commented fallback step in
  `publish-npm.yml`.

## 4. NuGet (`publish-csharp.yml` — `Gs1Belu.MyProductManager.{Upload,Download}-v*`)

- [ ] Confirm/create a nuget.org account; check the intended username is
      available.
- [ ] Set repo **secret** `NUGET_USER` = that nuget.org **username** (your
      profile name, not your email) — nuget.org's own docs recommend storing
      this as a secret even though it isn't independently sensitive.
- [ ] On nuget.org: click your username → **Trusted Publishing** → add a policy
      with Repository Owner `WimSuenens`, Repository `gs1belu.myproductmanager`,
      Workflow File `publish-csharp.yml` (filename only, no path), Environment
      left blank (this workflow doesn't use a GitHub Actions environment). One
      policy covers both `Gs1Belu.MyProductManager.Upload` and `.Download`,
      since it's owner-scoped, not package-scoped.
- [ ] If nuget.org shows the policy as "pending" for 7 days (typical for a
      private repo — shouldn't apply here since the repo is already public),
      just run the workflow once within that window to activate it permanently.
- Fallback (only if Trusted Publishing isn't yet available for this account):
  mint a scoped API key on nuget.org, store it as secret `NUGET_API_KEY`, and
  swap in the commented fallback step in `publish-csharp.yml` (drop-in — only
  the `--api-key` source changes).

## 5. PyPI + MCP Registry (`publish-mcp.yml` — `mcp-v*`)

- [ ] Log into pypi.org → account sidebar → **Publishing** (not a project
      sidebar — the project doesn't exist yet) → **GitHub Actions** tab → fill
      in PyPI project name `gs1belu-mpm-mcp`, GitHub owner `WimSuenens`,
      Repository `gs1belu.myproductmanager`, Workflow filename
      `publish-mcp.yml`, Environment name `pypi` (matches the `environment:`
      block already in `publish-mcp.yml`) → **Add**. This registers a
      **pending publisher** — it doesn't reserve the name until first use; the
      first successful publish converts it to a normal publisher automatically.
      No PyPI account token needed — OIDC only, keyless from the very first
      publish (v0.1.0).
- [ ] No separate registration needed for the MCP Registry step: `mcp-publisher
      login github-oidc` authenticates as this repository via GitHub OIDC, which
      is sufficient to claim the `io.github.wimsuenens/gs1belu-mpm` namespace on
      first publish.
- [ ] Periodically re-check the pinned `mcp-publisher` version in
      `publish-mcp.yml` (`MCP_PUBLISHER_VERSION`) against
      https://github.com/modelcontextprotocol/registry/releases and bump it
      deliberately, same discipline as `sdks/kiota.version`.

## 6. First real release

Once §2 is done, the next push to `main` (or the merge of this very PR) opens the
first standing release PR. Once §3–§5 are done for whichever package(s) you want
to actually publish:

1. Merge the standing release PR.
2. release-please pushes the tag(s) for whatever changed.
3. The matching `publish-*.yml` fires and publishes for real.

You can do §2 first and §3–§5 later, package by package — nothing forces all
three registries to go live at once. A package whose registry trust isn't set up
yet will just fail its publish job with an auth error when its tag is pushed,
with no effect on the other packages.
