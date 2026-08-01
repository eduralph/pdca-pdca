## Summary
**User impact:** When an outside reviewer leaves findings on a published pull
request, that feedback currently goes nowhere unless a maintainer copies it
somewhere by hand — so the same kind of mistake can ship again and again
without anyone noticing the pattern.

This PR adds a `pdca triage <pr>` command that pulls a published PR's review
feedback, sorts each finding into a class, files or logs a follow-up for each
one, and records every finding so a repeat of the same class of mistake is
flagged automatically.

Reported in [#316](https://github.com/eduralph/pdca-harness/issues/316).

## What to look at
- The new command: `pdca triage <pr>` accepts a PR URL, `OWNER/REPO#N`, or a
  bare number with `--repo`. On a merged PR with review feedback it prints
  each finding with its class and route, files a tracker issue for a
  bug-class finding (with a note the next planning pass picks up), appends
  candidate entries to `process/act-log.md` for the rest, and records
  everything in the Act ledger. Re-running the same PR ingests only new
  findings and never files the same issue twice.
- Classification is deliberately plain keyword matching — deterministic,
  cheap, auditable. Anything no keyword reaches is kept visible as
  "unclassified" for a human rather than force-fitted into a class; an
  optional config hook can send that remainder to a model, and it is off by
  default.
- To exercise it without a live PR: the shipped test suite drives the command
  end to end against canned `gh` output
  (`cd template && PYTHONPATH=src python3 -m unittest tests.test_triage`).

## Root cause
Nothing in the engine reads a published PR back: `cli.py`'s verb set has no
ingest command (template/src/pdca_harness/cli.py:156-373 on `main`), so
`act.register_signals` (template/src/pdca_harness/act.py:479) only ever
receives signals a human transcribed, and external findings never gain the
ledger entry that recurrence detection (act.py:510) matches against.

## Fix
- New module `template/src/pdca_harness/triage.py`:
  - **Pull** — `gh api` with explicit pagination (`_api_list`,
    triage.py:143-166), applied to both the reviews and the comments
    endpoints (triage.py:469-470); any failed or partial pull aborts with
    nothing ingested (fail closed).
  - **Classify** — severity-first keyword table (BUG > TEST-GAP >
    CONVENTION > NOISE; `classify`, triage.py:245), per-class keywords
    overridable from the instance rubric's class list (`class_keywords`,
    triage.py:224). Unmatched findings register as `codex-pr:unclassified`
    and are listed for the human — a visible fifth bucket by design — with
    the off-by-default `[triage].model_cmd` hook for that remainder.
  - **Route** — a BUG on a merged PR files a tracker issue whose body
    carries a carry-forward note; CONVENTION / NOISE / TEST-GAP append
    candidate entries to the act log. The act log is the ceiling: the
    command proposes and never edits `pdca.toml` or the rubric.
  - **Register** — every finding goes through `act.register_signals` under
    a stable class-keyed signal (`codex-pr:<class>-<keyword>`), so
    `act.recurrences` flags a class that reappears after its process delta
    was applied.
- Re-run safety: a per-PR record (`process/triage/pr-<repo>-<n>.json`)
  dedupes re-runs and doubles as a recovery journal — findings are written
  `pending` before the Act session lock is taken (triage.py:545-553), the
  no-new-findings fast path exits only when nothing is pending
  (triage.py:497-506), and the flags clear only after the ledger write and
  act-log append are durable (triage.py:586-592). A run interrupted after
  filing (a held lock, a crash) is finished by the next run; issues are
  never re-filed.
- `act.py`: `register_signals`/`_recurring` gain a `min_count` parameter
  (default 2 keeps every existing caller's behavior; triage registers at
  first sight, because an external finding already cost a shipped defect
  plus a review round).
- `cli.py`: the `triage` subparser (cli.py:318) and dispatch (cli.py:462);
  `config.py`: the `[triage].model_cmd` key (default `""` — the model pass
  never runs unless asked for).

## Verification
- **Claim:** `pdca triage <pr>` (a) pulls the PR's reviews and review
  comments, (b) classifies each finding into the four classes, (c) routes by
  class — BUG on a merged PR files an issue with a carry-forward note,
  CONVENTION / NOISE / TEST-GAP append act-log candidates — and (d) registers
  every finding class-keyed so `recurrences()` reports a reappearance.
- **Checked:** template/src/pdca_harness/cli.py:156-373 on `main` — no
  `triage` verb exists, so the feature is purely additive;
  template/src/pdca_harness/act.py:479 and :510 on `main` — the ledger API
  composed with; the added `min_count` defaults to 2, so no existing
  caller's behavior changes.
- **Test:** template/tests/test_triage.py (17 tests) — red on `main` (the
  module does not exist; the CLI rejects the verb), green with this patch.
  Covers: pagination past 100 items on both endpoints with the decisive
  findings only on page 2 (test_triage.py:157); interrupted-run recovery
  under a genuinely held session lock — the first run exits non-zero after
  filing and recording, the re-run registers all four class-keyed signals,
  appends the recovered log entry crediting the already-filed issue, and
  files nothing new (test_triage.py:252); re-run dedupe, unmerged-PR
  no-file, fail-closed abort on an unreadable endpoint, and a recurrence
  flagged across two PRs after the signal was marked applied.
- Both existing suites pass on the patched tree: render/update-compat
  (7 tests) and the offline driver suite (1331 tests, 2 pre-existing
  skips).

Fixes #316
