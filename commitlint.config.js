// Enforces Conventional Commits on PR titles (see .github/workflows/ci.yml's
// `commitlint` job). A squash-merge makes the PR title *the* commit message,
// which is what release-please reads to attribute a change to a package and
// derive its version bump — a malformed title is unattributable, not just
// unstylish.
module.exports = {
  extends: ["@commitlint/config-conventional"],
};
