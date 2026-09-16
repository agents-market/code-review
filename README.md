# agents-market/code-review

**Community example pipeline** — automated PR vulnerability detection using the agentsmarket.world marketplace for AI agent capabilities.

> **Auto-synced** from [`agents-market/main`](https://github.com/agents-market/main) via `repository_dispatch`. Source of truth: `examples/pipelines/code-review-vulnerability-detection.yaml`.

## What this does

When invoked against a GitHub pull request, this pipeline:

1. **Gathers PR context** — uses `github-pr-context@v1` skill to fetch PR title, author, and diff (capped at 8000 lines)
2. **Scans for vulnerabilities** — invokes the configured model (default `MiniMax-M3`) with OWASP Top 10 prompt, returns structured findings (severity, comments, summary, review event)
3. **Posts inline comments** — if severity ≠ none, uses `github-pr-comment@v1` skill to post the top finding as a line-level review comment
4. **Submits the review** — uses `github-review-submit@v1` skill to submit APPROVE / REQUEST_CHANGES / COMMENT on the PR

## Usage

This pipeline is a YAML contract consumed by:

- The `agentsmarket.world` Worker at `https://api.agentsmarket.world/v1/pipelines/invoke`
- The `@agentsmarket/cli` package locally via `agentsmarket invoke --pipeline /v1/skill/agents-market/code-review@v1.0.0`
- Any GitHub Actions consumer via `agents-market/pipeline-action@v1`

### Required inputs

| Input | Type | Description |
|---|---|---|
| `pr_number` | string | GitHub PR number (e.g. `"42"`) |
| `repo` | string | Target repo in `owner/name` format |

### Required env vars

| Var | Description |
|---|---|
| `PR_NUMBER` | Pass-through of `pr_number` input |
| `REPO` | Pass-through of `repo` input |
| `GITHUB_SHA` | Head commit SHA of the PR |

### Required skills (marketplace-fetched)

This pipeline uses three marketplace skills, version-pinned to `@v1`:

| Skill | Purpose |
|---|---|
| `github-pr-context@v1` | Fetch PR metadata + diff |
| `github-pr-comment@v1` | Post inline review comment |
| `github-review-submit@v1` | Submit the final PR review |

Each skill signs every request with EIP-191 (`personal_sign`) and pays the skill provider in USDC on Base via EIP-3009 `transferWithAuthorization`. Operator keypair never leaves your machine.

## Versioning

This repo follows **strict semver**:

- Every push to `main` (via auto-sync) auto-increments the patch version in `.pipeline.yaml` and pushes a new tag.
- Consumers pin to `@v1` (floats to latest 1.x) or `@v1.0.0` (exact).

## Syncing

The single source of truth lives in the main monorepo:

[`agents-market/main/examples/pipelines/code-review-vulnerability-detection.yaml`](https://github.com/agents-market/main/blob/main/examples/pipelines/code-review-vulnerability-detection.yaml)

When the source changes:

1. `agents-market/main`'s `sync-code-review-repo.yml` workflow detects the path change
2. It dispatches `code-review-sync` repository event to this repo
3. This repo's `sync-incoming.yml` workflow writes the payload to `.pipeline.yaml`, bumps version, commits, tags, and pushes

No manual sync needed.

## See also

- [`agents-market/main`](https://github.com/agents-market/main) — the platform, CLI, server, and pipeline-runtime
- [`docs/SKILL.md-spec.md`](https://github.com/agents-market/main/blob/main/docs/SKILL.md-spec.md) — SKILL.md format spec for the marketplace
- [agentsmarket.world](https://agentsmarket.world) — landing page

## License

MIT — see [LICENSE](./LICENSE).
