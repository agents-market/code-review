# style-review — changelog

What the published README does not carry: the earlier breaking changes and the
measurements behind the current calibration. The README is the contract; this
file is the history.

## 3.3.x — the severity scale and the per-category cut-off

**The scale moves the calibration, and that is a choice rather than a bug.** On
the same corpus, the findings of a run were 37 `low` and 6 `medium` before the
scale, and 26 `low`, 3 `medium` and 11 `high` after it: a comment that
contradicts the code and a literal whose unit nobody can tell are `high` now,
because that is what they cost the reader.

**The cut-off, measured.** On the case corpus in `fixtures/style-review` (108
runs, MiniMax-M3, temperature 0, $0.94): with `magic_numbers=none`, every
`magic_numbers` finding is gone — 8 of 36 runs in the control arm, 0 of 36 in
the cut arm — and no finding is renamed into another category to get around the
cut. The other categories are unaffected, and the run is marginally cheaper.

## 3.2.0 — one issue, one comment

**The aggregate stage emitted its own copy of the findings array**, re-derived
from the analyze stage's output. The two copies disagreed on line numbers, so
the consumer's merge — which drops a finding that repeats at the same file and
line — kept both, and the reader got every issue twice. A measured run on a
106-line diff produced 22 comments for about eleven issues; the same complaint
("no type annotation") appeared five times, at 99% confidence each.

The aggregate stage now copies the analyze stage's findings verbatim, and the
analyze stage is told that two findings with one cause are one finding.

## 3.0.0 — breaking change

**The pipeline no longer counts findings.** `summary` is now `{style_score}` and
nothing else, and `profile_style` no longer returns `stats`.

Why: a model asked to count a list it is writing gets it wrong — one run in ten
said "8 findings" over ten — and a wrong count is worse than no count. Count the
`findings` array yourself, or read `findings_count_json` from the action, which
computes it in code.
