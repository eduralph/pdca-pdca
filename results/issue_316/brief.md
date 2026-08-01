# Design proposal — issue 316 / pdca-triage

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** pdca-triage
- **Kind:** enhancement (design proposal)
- **Goal:** a `pdca triage` subcommand that ingests a published PR's external review
  findings into the Act ledger — pull via `gh api`, classify (BUG / CONVENTION / NOISE /
  TEST-GAP), route by class, and register every finding via `act.register_signals` with
  class-keyed signal names so `recurrences()` flags a class that reappears after its
  process delta was applied. Today the pipeline stops at the draft PR and the Act ledger
  only receives what a human remembers to register.
- **Success criterion:** `pdca triage <pr>` (gh subprocess stubbed in tests): (a) pulls
  the PR's review comments/reviews; (b) assigns each finding one of the four classes via
  keyword heuristics keyed to the instance rubric's class list; (c) routes by class —
  BUG on a merged PR → tracker issue + carry-forward note, CONVENTION → candidate gate
  row / rubric line appended to the act log, NOISE → candidate rubric-exclusion entry;
  (d) registers every finding through `act.register_signals` with class-keyed names
  (e.g. `codex-pr:option-default-vs-omit`) such that `recurrences()` reports a
  recurrence when the same class-keyed signal reappears. Demonstrable by C4-verify: the
  shipped test drives the command against canned `gh` output and asserts (a)–(d); red on
  current `main` (no `triage` subparser exists — verified against `cli.py`'s
  `add_parser` set).
- **Falsifiability:** the offline driver suite on this host. RED now: invoking the new
  subcommand fails on current `main` because the parser rejects it; the classification
  and registration assertions have no code to satisfy them. No live GitHub needed — the
  tests stub `gh` exactly as `template/tests/` stubs publish's subprocesses.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** none
- **Conflicts with:** 317
- **Ordering note:** 317 also adds a `cli.py` subparser in the same registration block —
  textual collision, different waves. No dependency.
- **Difficulty:** medium
- **Scope:** the `pdca triage` verb: a new engine module + `cli.py` wiring, keyword
  classification with the class list read from the instance rubric where configured, the
  per-class routing above, and `register_signals` integration. The optional single model
  pass for the unclassified remainder is in scope only as a config-gated hook (off by
  default); keyword-only must be complete and useful on its own. / out of scope: the
  pre-publish review stage (#315); auto-*applying* any routed delta (the command
  proposes — appending candidates to the act log is the ceiling; it never edits
  `pdca.toml` or files gate rows itself); tracker-side automation beyond filing the BUG
  issue via the existing gh machinery.
- **External dependencies:** none — tests stub the gh CLI; live use relies on the gh
  binary the instance's tracker integration already requires (no backticked token on
  purpose: nothing new to register).
- **Test file:** template/tests/test_triage.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the ledger API to compose with — `act.register_signals`
  (`act.py:479`) and `act.recurrences` (`act.py:510`); the gh invocation pattern to
  mirror — `publish.py`'s gh machinery; the subparser registration block —
  `cli.py:156-373`.
- **Prior-art check (triage cycles):** no `triage` subparser in `cli.py`;
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/act.py
  template/src/pdca_harness/cli.py` shows no ingest work; commit grep `#316` empty. Not
  fixed, not in flight (wyrd plans an instance script first; nothing upstream).
- **Disposition hint:** new-feature

## Motivation

External reviewer findings on published PRs are the highest-value signal the outer
improvement loop has, and today they are invisible to it: nothing flows back unless a
human transcribes it. Registering them class-keyed makes the existing ledger the
recurrence tracker for external findings.

## Design

See Scope/criterion. Classification is deliberately heuristic-first: deterministic,
cheap, auditable; the model pass is a gated add-on for the remainder, never the primary
path.

## Alternatives considered

- Instance script only (wyrd's plan): proves the shape but every instance re-implements
  classification and `register_signals` plumbing; the recurrence property is engine
  value.
- Doing it inside publish: wrong beat — findings arrive after publish, over days.

## Impact & compatibility

Purely additive verb; no existing path changes. Instances without a rubric get the
built-in class list.

## Open questions

- The exact class-keyed signal-name grammar (`codex-pr:<slug>`) — Do proposes; must stay
  stable across runs so recurrence matching works.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the advisory reviewer's two substantiated implementation defects (brief unchanged, approach sound): 1. C3/T3 — unreachable registration recovery: the "no new findings" early return sits BEFORE registration, so after a held Act lock (record written, exit 1) a re-run exits 0 without ever registering — ledger stays permanently empty (triage.py:448/:497). Reproduced dynamically by the reviewer. Fix: re-runs must re-derive registration from the full record history even when no NEW findings exist (make the self-heal claim in build-notes actually true), and cover the lock-contention-then-rerun path in the shipped test. 2. C5 — missing pagination: reviews/comments fetched once with per_page=100 (triage.py:422); PRs with >100 items silently drop findings, violating "register every finding". Fix: paginate both endpoints (or use gh api --paginate) and test the multi-page case.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — /tmp/tmp382nti4b/results/issue_500/split-proposal.md
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
