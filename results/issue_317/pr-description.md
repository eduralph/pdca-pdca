## Summary
**User impact:** A finished result bundle exists only as files on the machine that
ran the cycle. Unless someone remembers to commit them — and the forgetting is
silent — the record of what was decided and why lives nowhere else. Observed in
practice: four finished bundles sat uncommitted for five days, one of them the
only record explaining an abandoned-but-still-open upstream PR.

This PR adds `pdca record [<ids>…]`, which commits every finished bundle to the
instance repo in one batch commit — with an opt-in mode that also opens one draft
PR for the batch. It is off by default; nothing changes for existing instances.

Reported in [#317](https://github.com/eduralph/pdca-harness/issues/317).

## What to look at
- `template/src/pdca_harness/record.py` (new) — `select()` picks the finished
  bundles, `record()` runs the git/gh steps, `after_publish()` is the hook publish
  calls.
- `template/src/pdca_harness/state.py` — the new `TERMINAL` set, defined next to
  the state names so no consumer re-spells them.
- To try it: set `[records] mode = "commit"` in `pdca.toml`, then run
  `pdca record --dry-run` — it prints the exact git commands without running them.
  With the default config, `pdca record` refuses with a configure-me hint and runs
  nothing.

## Root cause
No part of the engine ever commits a bundle to the instance repo, so recording is
a manual habit; the existing `HALTED` set (`state.py:31` on `main`) is the wrong
predicate for it because it mixes "cycle over" (COMPLETE, DISCONTINUED, RESOLVED)
with "halted for a human" (UNPLANNED, AWAITING_SIGNOFF), whose files still change.
An instance-side script would have to re-enumerate the states and drift.

## Fix
- `state.TERMINAL = frozenset({COMPLETE, DISCONTINUED, RESOLVED})` — the
  terminal-finished trio, owned by the module that owns the state names.
- New `record.py`: `select()` tests membership via `state.TERMINAL` only (an
  explicit non-terminal id is reported and excluded — the predicate is the safety
  property and an id does not override it); `record()` stages and commits the
  batch as one pathspec-scoped commit (never sweeping the operator's unrelated
  staged work), with a staged-changes probe so re-running on an already-recorded
  batch is a quiet success. `mode = "pr"` adds `git branch -f` +
  `push --force-with-lease` + one `gh pr create --draft` — deliberately no
  `checkout -B` (the publish shape at `publish.py:257` runs in a dedicated
  checkout; flipping the instance repo's own branch would strip the just-committed
  files from the working tree).
- `[records]` config table (`mode = off|commit|pr` default off, `branch`,
  `subject`, `issue = ask|<N>`); an unknown mode fails closed to "off", loudly —
  inventing commits is the unsafe direction. `issue = "ask"` prompts only when
  interactive; a headless run downgrades to commit-only and says so, so it can
  never hang on `input()`.
- `cli.py`: the `record` subparser (ids…, `--dry-run`) + dispatch.
- `publish.py`: a call-in on both publishing paths, strictly after each path's
  `publish.json` write (`publish.py:374` / `:487` on `main`) and best-effort — a
  recording problem reports a manual fallback and never turns a completed publish
  into a failure. A no-op under the default "off".

## Verification
- **Claim:** selection is exactly the terminal-finished states, single-sourced.
  **Checked:** `state.py:31` on `main` — `HALTED` includes the halted-for-a-human
  states, hence the separate set; `test_record.py` asserts `TERMINAL` equals the
  trio, that the new module's source contains `state.TERMINAL` and no re-spelled
  state name, and that the selection follows the state files (an
  awaiting-sign-off bundle joins the selection the moment its sign-off is
  recorded).
- **Claim:** one batch commit / one batch PR; commit mode never touches a remote.
  **Checked:** the git steps mirror the deterministic shape at
  `publish.py:254-266` on `main`; the tests count exactly one `add`, one
  `commit` (both listing every bundle's pathspec), and in pr mode one `branch`,
  one `push --force-with-lease`, one `gh pr create --draft`, with git/gh stubbed
  the same way the existing publish slice stubs them.
- **Claim:** the default is byte-identical to today. **Checked:** dataclass
  default "off", `after_publish` returns before doing anything, the explicit verb
  refuses with rc 2 running no subprocess; a publish under the default config
  issues no git command against the instance root.
- **Test:** `template/tests/test_record.py` — 15 cases; red with the production
  hunks reverted (`pdca_harness.record` does not exist; the parser rejects
  `record`), green with the patch. Full offline driver suite: 1443 tests OK
  (skipped=2); template-repo render suite: 7 tests OK.

Fixes #317
