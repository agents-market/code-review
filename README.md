# agents-market/code-review

**Community example pipeline** — automated PR vulnerability detection using the
[agentsmarket.world](https://agentsmarket.world) marketplace for AI agent
capabilities.

> **Auto-synced** from
> [`agents-market/main`](https://github.com/agents-market/main) via
> `repository_dispatch`. Pipeline source of truth:
> `examples/pipelines/code-review-vulnerability-detection.yaml`.

## Status

[![Pipeline security review](https://github.com/agents-market/code-review/actions/workflows/security-review.yml/badge.svg)](https://github.com/agents-market/code-review/actions/workflows/security-review.yml)

This repo dogfoods **`agents-market/pipeline-action@v1`** — every PR is reviewed
by an agentsmarket pipeline via the published GitHub Action.

## Quick start (5 lines)

Add to your own repo's `.github/workflows/`:

```yaml
name: Pipeline security review
on: [pull_request]
permissions:
  contents: read
  pull-requests: read
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: agents-market/pipeline-action@v1
        with:
          pipeline_file: .github/pipelines/my-pipeline.yaml
          mock: 'true'  # remove for real LLM calls
```

Full guide: [`agents-market/pipeline-action/docs/ACTIONS.md`](https://github.com/agents-market/pipeline-action/blob/main/docs/ACTIONS.md).

## What this pipeline does

When invoked against a GitHub pull request, this pipeline:

1. **Gathers PR context** — uses `github-pr-context@v1` skill to fetch PR title,
   author, and diff (capped at 8000 lines)
2. **Scans for vulnerabilities** — invokes the configured model (default
   `MiniMax-M3`) with OWASP Top 10 prompt, returns structured findings
   (severity, comments, summary, review event)
3. **Posts inline comments** — if severity ≠ none, uses `github-pr-comment@v1`
   skill to post the top finding as a line-level review comment
4. **Submits the review** — uses `github-review-submit@v1` skill to submit
   APPROVE / REQUEST_CHANGES / COMMENT on the PR

## Usage

This pipeline is a YAML contract consumed by:

- The `agentsmarket.world` Worker at `https://api.agentsmarket.world/v1/pipelines/invoke`
- The `@agentsmarket/cli` package locally via
  `agentsmarket invoke --pipeline /v1/skill/agents-market/code-review@v1.0.1`
- Any GitHub Actions consumer via `agents-market/pipeline-action@v1` (see Quick start)

### Required inputs

| Input    | Type   | Description                                      |
|----------|--------|--------------------------------------------------|
| `pr_number` | string | GitHub PR number (e.g. `"42"`)                  |
| `repo`      | string | Target repo in `owner/name` format              |

### Required env vars

| Var          | Description                                      |
|--------------|--------------------------------------------------|
| `PR_NUMBER`  | Pass-through of `pr_number` input                |
| `REPO`       | Pass-through of `repo` input                     |
| `GITHUB_SHA` | Head commit SHA of the PR                        |

### Required skills (marketplace-fetched)

This pipeline uses three marketplace skills, version-pinned to `@v1`:

| Skill | Purpose |
|---|---|
| `github-pr-context@v1` | Fetch PR metadata + diff |
| `github-pr-comment@v1` | Post inline review comment |
| `github-review-submit@v1` | Submit the final PR review |

Each skill signs every request with EIP-191 (`personal_sign`) and pays the
skill provider in USDC on Base via EIP-3009 `transferWithAuthorization`.
Operator keypair never leaves your machine.
