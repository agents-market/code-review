---
name: style-review
version: 3.3.7
description: |
  AI-powered code style review for diffs. Identifies naming inconsistencies,
  missing types, unused exports, magic numbers, and codebase-pattern violations.
  Outputs structured findings with severity + line + category + fix suggestion
  + estimated impact. Vertical wedge expansion: code style review as paid AI
  Free to download; a server call costs the tokens it uses.
license: MIT
author: agentsmarket-team
price_usdc: 0
call_price_usdc: 0
tags: [style, code-review, vertical-wedge]
public_preview: AI code style review of diffs. Structured findings (severity + category + fix + impact), aggregate style score 0-10, prioritized refactors. Free to download; a call costs the tokens it uses.
---

# style-review

AI-powered **code style review** for pull request diffs. The fourth wedge in the
agents-market vertical-wedge expansion.

## What it does

Given a unified diff and a few configuration knobs, `style-review` runs a
3-stage AI pipeline:

1. **`profile_style`** — quick scan of the diff to identify style patterns:
   naming, type annotations, exported symbols, numeric/string literals.
2. **`analyze_style`** — for each region, emit structured findings with
   severity (critical / high / medium / low), category (naming, types,
   exports, magic_numbers, comments), description, fix suggestion, and
   estimated impact.
3. **`aggregate_style`** — compute aggregate counts, a `style_score` (0-10),
   ≤5 prioritized recommendations, and a markdown report suitable for a PR
   comment.

## What it does not report

Three remarks are not findings, and the pipeline drops them:

1. **Formatting.** Owned by the repository's formatter, whose configuration the
   pipeline cannot read.
2. **A number in prose is not a magic number.** `magic_numbers` is a rule about
   literals in executable code; a number in a comment is not one.
3. **Comments without a rule.** A `comments` finding must name the rule it
   violates; without one it is taste.

## When to use

- **TypeScript / React projects** adopting strict conventions
- **Monorepos** with shared style rules across packages

The pipeline is intentionally **advisory**: it surfaces findings without
blocking the merge. Pair it with `code-review-security-audit` to cover both
security and style in the same PR.

## Configuration

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `code_diff` | string (1..50000 chars) | **required** | Git diff or unified patch text |
| `language` | enum | `generic` | `typescript` / `javascript` / `python` / `rust` / `go` / `solidity` / `generic` |
| `focus_area` | enum | `all` | `naming` / `types` / `exports` / `magic_numbers` / `all` |
| `severity_threshold` | enum | `low` | `low` / `medium` / `high` / `critical` — drop findings below this floor |
| `category_thresholds` | string | `""` | `category=level` pairs, comma-separated — `none` drops the category, a severity level keeps only that category's findings at or above it |
| `provider` | enum | `minimax` | `minimax` / `openrouter` / `openai` / `anthropic` / `replicate` — the LLM provider for this run |
| `model` | string | `MiniMax-M3` | The LLM model for this run — must be one the chosen provider carries |

## Output envelope

```json
{
  "summary": { "style_score": 4 },
  "recommendations": ["Escape user input in renderPage to prevent XSS (CWE-79)"],
  "markdown_report": "## Style Review\n\n...",
  "findings": [
    {
      "file": "src/utils/format.ts",
      "line": 23,
      "severity": "critical",
      "category": "comments",
      "description": "Unescaped user input passed to renderPage (potential XSS)",
      "fix_suggestion": "Use DOMPurify or React's default escaping",
      "estimated_impact": "Prevents CWE-79 XSS vulnerability",
      "confidence": 0.95
    }
  ]
}
```

Every finding includes explicit `file` + `line` so the wrapper can post inline
PR comments at the right location (see the
[pipeline-action](https://github.com/agents-market/pipeline-action) README).

## The severity scale

`severity` is what a finding costs the reader, and the scale is fixed:

| severity | the reader |
|---|---|
| `low` | can ignore it and lose nothing — a missing type annotation, an abbreviation, an unused export |
| `medium` | has to decide something — rename it, type it, delete it. The remark is right and the code works anyway |
| `high` | the remark is right and the code misleads — a comment that contradicts the code, a name that says the opposite of what the function does, a literal whose unit nobody can tell |
| `critical` | the code is wrong now, in a way the reader has to fix before merge |

A finding's severity does not depend on what else the diff contains: the same
finding gets the same severity every time. The scale moves the calibration, and
that is a choice rather than a bug — the measurements are in the
[changelog](https://github.com/agents-market/github-workflows/blob/main/pipelines/style-review/CHANGELOG.md).

The scale labels a finding, it does not detect it: a remark the pipeline
finds in three runs out of six is still a remark the reader sees half the time.

## The per-category cut-off

`severity_threshold` is one floor for the whole pipeline, and a consumer whose
repository has no unexplained numeric literals still pays for every one the
pipeline finds in a config file. The new `category_thresholds` input is a set
of per-category floors:

```
category_thresholds: "magic_numbers=none,comments=high"
```

`none` drops the category entirely; a severity level keeps only that
category's findings at or above it. The default is empty, which cuts nothing
off — a caller that does not pass the input gets the pipeline it had.

The cut-off removes true findings as well as false ones: a genuine unexplained
literal is a `magic_numbers` finding, and it goes with the rest. That is the
trade the caller is making — a scope, not a filter. It also does not fix the
instability the pipeline is known for: a finding of another class still
appears in one run and not in the next.

## Installation

```bash
agentsmarket pipeline install style-review
# → creates .agentsmarket/pipelines/style-review@<version>/{pipeline.yaml, README.md, metadata.json}
```

Without a version this installs the latest release;
`agentsmarket pipeline info style-review` prints the version to pin.

`MINIMAX_API_KEY` in the environment. The provider is the `provider` input
(`minimax` by default); the model stays MiniMax-M3.

## Usage in GitHub Actions

```yaml
- name: Install pipeline
  run: agentsmarket pipeline install style-review@<version>   # the version you verified
  env:
    AGENTSMARKET_PRIVATE_KEY: ${{ secrets.PUBLISH_KEY }}

- name: Run style review
  uses: agents-market/pipeline-action@0ab99cfca4566494f6d84d4e0b08fd11a3bf6c21 # v0.4.12 (merges input defaults; validates output locally)
  env:
    MINIMAX_API_KEY: ${{ secrets.MINIMAX_API_KEY }}
  with:
    provider: minimax
    model: MiniMax-M3
    pipeline_file: .agentsmarket/pipelines/style-review@<version>/pipeline.yaml
    inputs_json: '{"code_diff": "<the diff>", "language": "typescript", "severity_threshold": "medium", "provider": "minimax", "model": "MiniMax-M3"}'
```

## Sample output

A 44-line probe diff with intentional style violations — 1 critical, 2 high,
3 medium, 1 low, `style_score: 4/10` — is in `examples/demo-reviews/` of
[agents-market/main](https://github.com/agents-market/main).

## Pricing

`$0.001 USDC` per invocation; real cost on MiniMax-M3 is roughly $0.009 USDC
per call. The cost ceiling (default $1.00 per run) is automatic via
`agentsmarket pipeline call`.

## License

MIT — see [`LICENSE`](../../LICENSE) in the repo root.

## Earlier versions

The 3.0.0 breaking change, the 3.2.0 fix and the calibration measurements are
in the [changelog](https://github.com/agents-market/github-workflows/blob/main/pipelines/style-review/CHANGELOG.md).
