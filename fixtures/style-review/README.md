# The style-review case corpus

Six cases, one thing each, and a known answer per case. The corpus exists
because `style-review` was measured for the first time in November 2026, and
the measurement was a number on a page: "the pipeline found N findings on this
diff". A number without a known answer is not a measurement — it is a mood.

The corpus also answers a question the pipeline's own guardrails raised: the
rule "a number in prose is not a magic number" is in the spec, but a config
file with `timeout_ms: 30000` is not prose either, and the pipeline kept
calling such values "executable configuration" and reporting them.

## What is in here

```
cases/<case>.diff      the diff the pipeline is given
cases/expected.md      what a good review says about each case
run-cases.mjs          runs a spec over the cases and writes one JSON file
summarize.py           turns those JSON files into the table below
```

`expected.md` is the answer the runs are checked against: per case, what must
not be reported and what is expected. The pipeline never sees any of it.

## How it was run

```bash
npm install --no-save --no-audit --no-fund @agentsmarket/pipeline-runtime@0.5.11
export MINIMAX_API_KEY=...            # the model is the spec's own default, MiniMax-M3

# the baseline: the published spec, before the cut-off existed
node fixtures/style-review/run-cases.mjs --spec /path/to/style-review-3.3.6.yaml \
  --repeats 2 --out /tmp/A.json

# the control: the new spec, cut-off empty — the new input alone
node fixtures/style-review/run-cases.mjs --spec pipelines/style-review/pipeline.yaml \
  --repeats 2 --category-thresholds "" --out /tmp/B.json

# the cut: the new spec, one category cut off
node fixtures/style-review/run-cases.mjs --spec pipelines/style-review/pipeline.yaml \
  --repeats 2 --category-thresholds "magic_numbers=none" --out /tmp/C.json

python3 fixtures/style-review/summarize.py /tmp/A.json /tmp/B.json /tmp/C.json
```

`run-cases.mjs` executes the spec through the real runtime, so the
measurement covers the stages, the model and the runtime — not a
re-implementation of them. It passes `category_thresholds` only if the spec
declares the input: an unknown input adds a line to the `Inputs:` block every
stage receives, and that is a change in the prompt, so the baseline would be a
different pipeline.

## What it returns, measured 2026-11-02

Six runs per case per arm, 108 runs in total, $0.94, MiniMax-M3, temperature 0.
Each cell lists the categories the analyzer reported, one cell per run.

| кейс | 3.3.6 (без отсечения) | 3.3.7 (без отсечения) | 3.3.7 + `magic_numbers=none` |
|---|---|---|---|
| `abbreviation` | naming,types · naming,types · naming,types · naming,types · naming,types · naming,types | types,naming,naming · naming,types · types,naming · naming,types,types · types,naming,naming · naming,types | naming,types · naming,naming,types · naming,naming · naming,naming · naming · naming,naming,types |
| `config-number` | — · — · — · — · — | — · naming,magic_numbers · — · — · — · magic_numbers | — · — · — · — · — · — |
| `lying-comment` | comments · — · — · comments · — · comments | comments,types · — · comments,types · comments,types · — · comments | — · — · comments,types · comments · comments · — |
| `magic-literal` | magic_numbers · magic_numbers · magic_numbers · magic_numbers · magic_numbers · magic_numbers | magic_numbers · magic_numbers · magic_numbers · magic_numbers,types · magic_numbers · magic_numbers | — · — · — · — · — · — |
| `missing-types` | types,naming,types · types,naming · types,naming,naming · types,types,naming · types,types,types · types,types,naming | types,naming,naming · types,types,naming · types,types,types · types,types · types,types · types,naming | types,naming,naming · types,naming · types · types,naming,naming · types,naming,naming · types,naming,exports |
| `unused-export` | — · — · — · naming · naming | — · — · — · — · — · — | — · — · — · — · — · — |

| arm | runs | findings | of them `magic_numbers` | cost |
|---|---|---|---|---|
| 3.3.6, no cut-off | 36 | 40 | 6 | $0.308 |
| 3.3.7, no cut-off | 36 | 47 | 8 | $0.339 |
| 3.3.7 + `magic_numbers=none` | 36 | 32 | **0** | $0.296 |

## What the numbers say

**The cut-off does what it says.** Every `magic_numbers` finding is gone: 8 in
the control arm, 0 in the cut arm. Not one finding was renamed into another
category to get around it — in `magic-literal`, six of six control runs report
`magic_numbers` and six of six cut runs report nothing at all.

**It costs nothing else.** The other categories are unaffected: `comments` is
reported in 3 of 6 baseline runs, 4 of 6 control runs and 4 of 6 cut runs; the
`naming` and `types` findings appear in every run of every arm. The cut arm is
slightly cheaper, because there is less to write.

**The rule the spec already had does not hold.** In the control arm, 2 of 6
runs on `config-number` reported the YAML values as `magic_numbers` and called
the file "executable configuration". The 3.3.6 rule — "a number in prose is
not a magic number" — does not cover a config file, and the model reads a
config value as a literal. That is the noise the cut-off removes, and it is
the reason a cut-off is worth having even when the rule is in the spec.

**One case never produced its expected finding.** `unused-export` got a
`findings` answer in 35 of 36 runs and a `magic_numbers` answer once — the
pipeline did not report the unused export even once. It cannot: it is given a
diff, not the repository, so it cannot know that `formatPercent` is never
imported. `expected.md` marks that case's answer as optional for this reason.
The `exports` category is, on this evidence, unreachable from a diff.

**The cut-off removes true findings too.** `magic-literal` is a real defect —
`Date.now() - createdAt > 86400` is an unexplained literal — and the cut-off
removes it in 6 of 6 runs. A cut-off is not a filter for wrong findings; it is
a scope: the consumer decides that this class of remark is not worth a thread,
and pays for it with the real findings of that class.

**It does not fix the instability.** The issue the corpus was built for is a
finding that appears in one run and not in the next. The cut-off removes the
*class* that churns, but the classes it leaves behind still churn: the
`comments` finding on `lying-comment` is present in 3–4 of 6 runs, and it
changes severity between `low` and `medium`. That is the part the prompt
anchor has to fix, and it needs its own measurement.
