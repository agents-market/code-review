# Verdict memory — design

**Status:** built on `feat/verdict-memory`. **Written:** 2026-11-05.

A finding a human decided about comes back on the next push. The thread sync
stopped the *same* finding being said twice on the same line; it never knew
what a human had concluded about it. This is the layer that remembers the
conclusion, and the decision it still needs is in
[Where this leaves the decision](#where-this-leaves-the-decision).

## The problem

`web3eco/blockchain#83`, four pushes, four runs:

| what | how often |
|---|---|
| `.github/dependabot.yml.reference:26` reported | 3 times |
| `.github/dependabot.yml:1` reported | 2 times |
| `.github/dependabot.yml:33` reported | 2 times |

14 of the 22 inline threads were about `.github/dependabot.yml.reference` — a
frozen archival copy that Dependabot does not read. Eight of them got a "not
fixing, by design" reply. The finding came back anyway.

The workflow layer could not help. It knew what it had already *said*; nobody
had told it what a human had *decided*. GitHub Copilot does not have this
problem because it carries the review conversation forward — the reply is
part of the state it reads. Our pipeline re-reads the diff from zero, and a
reply in a thread is not state it can see.

So the decision has to be written somewhere the next run reads. The questions
are: what is the key, where does the decision live, and who writes it.

## What the key can be — measured, not guessed

`code-review-security-audit` 3.4.7, three real diffs from `web3eco`, two runs
each, `temperature: 0`, one model. The question: when the same defect is
found twice, what is the same?

| the key | repeats / union |
|---|---|
| file + line + class | 0 / 26 = **0 %** |
| file + line | 1 / 24 = 4 % |
| file + class | 7 / 16 = 44 % |
| file | 7 / 11 = 64 % |

**Not one finding repeated with the same line.** So a verdict keyed by a
coordinate expires every time an unrelated edit moves the code above it, and
the human would have to write it down again after every touch above it.

`(file, class)` is the key the sync already uses for a thread — one comment per
(file, class) — so it is the granularity the product already reasons in. A
verdict on it hides no more than the comment already hid.

## Where the verdict lives

Three places were possible, and two of them are the ones the issue names:

| where | what it is | why not |
|---|---|---|
| **a file in the repository** | a versioned file the human writes, reviewed in a pull request | — |
| an artifact of the check run | uploaded, read back next time | not visible to a human; lost when the run is cleaned up; the human cannot write it |
| the comments on the pull request | parsed out of the thread | expensive, fragile, and it dies with the pull request — the thread is closed when the finding moves, which is exactly the case that has to survive |

The file wins on the third reason in particular: the thread is closed when the
finding moves, so a verdict that lives in the thread is gone by the next push.

**JSON, not YAML.** The step runs on a runner with no packages — the module is
fetched with a sparse checkout and nothing else — so there is no YAML parser
there, and a hand-written one is a bug factory.

## The design

### The key

| the key | it covers |
|---|---|
| `path` | every finding in that file |
| `path::CLASS` | every finding of that class in that file |

`CLASS` is the class the sync uses — the CWE id of a security finding, the
category tag of a style finding — folded through `CANON`, so a verdict filed
under `CWE-330` covers a `CWE-338` finding, because they are one weakness.

The file is the whole-file case, and it is the case the measurement points at:
`.github/dependabot.yml.reference` is inert as a *file*, not as one weakness in
it.

### The file

```json
{
  ".github/dependabot.yml.reference": {
    "verdict": "accepted",
    "reason": "frozen archival copy; Dependabot does not read it"
  },
  "src/api/user.ts::CWE-89": {
    "verdict": "accepted",
    "reason": "the string is a column name, not a query",
    "until": "2026-12-01"
  }
}
```

| field | meaning |
|---|---|
| `verdict` | what the human decided. `accepted` by default. Recorded, not acted upon: any verdict covers the finding. |
| `reason` | why. Shown to the reader next to the finding. |
| `until` | a date. After it the verdict covers nothing and the finding is reported again. |

An accepted risk is not a sentence for ever. The date is the way out, and a
date nobody can read is treated as passed — a verdict that hides a finding
forever because of a typo is the worse failure.

**A file that does not parse hides nothing.** An unreadable verdict leaves
every finding reported, and the run says what it could not read.

### What a verdict does

- the finding is **not posted**;
- the comment that is already there **stays** — it is the record of the
  decision, and closing it would erase the reason the finding is not reported;
- the run says so: the log line counts the findings a verdict covered, the
  summary comment lists them with their reasons, and the summary gives the
  key of every finding no verdict covers.

The last one is not a nicety: the class of a *style* finding is not in the
comment the reader sees — the tag is stripped from the reader's text — so
without the key the human cannot write a verdict down at all.

### Where the file is read

The caller reads it and passes the content in. The reusable workflow
(`.github/workflows/thread-sync.yml`) takes a `verdicts` input; the reference
consumer (`.github/workflows/ai-review.yml`) reads
`.github/ai-review-verdicts.json` out of its checkout and passes it on.

The caller reads it, because the reusable workflow cannot: it is called from
another repository, and a checkout of the caller's repository does not work on
a pull request from a fork.

The reference consumer reads the file out of the *merge commit* of the pull
request, so a pull request that adds a verdict has it in force at once.

## Verification

`scripts/check-thread-sync.mjs`, thirty-eight new checks, run by the consumer
smoke test:

1. a verdict file parses; a file that does not parse hides nothing and is
   reported;
2. the class of a key is folded through the CANON map;
3. a finding a verdict covers is not posted, and the comment that is already
   there stays;
4. a verdict covers the finding wherever it moved to — the line is not part of
   the key;
5. a verdict on the file covers every class in it, and no other file;
6. an expired verdict covers nothing; an unreadable date covers nothing and is
   reported;
7. the whole step, against the stand-in for the GitHub API: a covered finding
   is not posted, the log line counts the verdicts, the summary names the
   verdict and its reason;
8. the report gives the key to file, and the contract and both callers know
   about the verdict layer.

The end-to-end proof is a pull request on a consumer: a verdict in the file,
a finding that would be reported, and a run that does not report it.

## What this does not do

- **The model still finds the finding.** The verdict suppresses the *report*,
  not the finding: the pipeline still reads the diff and still spends the
  tokens. The cost per run does not drop; the noise does. Making the model
  skip the work is a different change — the verdicts would have to become a
  pipeline input, which is a new pipeline version and a runtime change.
- **A reply in a thread does not become a verdict.** The human writes the
  file. A bridge — the sync reading the reply and opening a pull request with
  the verdict — needs `contents: write` on the consumer's repository and a
  commit written by a workflow, and that is the owner's call, not a detail.
- **A verdict covers a class, not an instance.** A verdict on
  `path::CWE-89` covers every SQL finding in that file, including one the
  human did not have in mind. That is the granularity the sync already uses.
  The `until` date is the way out.

## Where this leaves the decision

One thing is the owner's: **where a verdict lives.** This design puts it in a
file in the consumer's repository — versioned, reviewed in a pull request, and
visible to a human. The alternatives (an artifact of the check run, the
comments on the pull request) are worse for the reasons in
[Where the verdict lives](#where-the-verdict-lives).

If the owner wants a different place, the change is contained: the file is read
by the caller and the content is passed into `syncThreads`, so the module
would read the same structure from another source.
