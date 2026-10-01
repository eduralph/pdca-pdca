# Design proposal — issue 371 / gate-confirm-failed-gating-row

- **Slug:** gate-confirm-failed-gating-row
- **Kind:** enhancement (design proposal)
- **Goal:** a single transient red on a gating gate row no longer parks the bundle as if the
  patch were broken. A failed gating row is re-run once; both verdicts are recorded; a
  fail→pass is recorded `pass` + `flaky` and routed to the human as a HUMAN §6 item.
- **Success criterion:** all hold in `template/tests/test_gate_confirm.py`, run by the C4
  gate, driving the real `gates._run_one` with small shell commands (e.g. a command that
  fails on its first run and passes on its second, using a marker file in a temp dir):
  (1) **fail → pass:** a gating row whose command exits non-zero, then 0 on the confirm run,
  is recorded `result = "pass"`, `flaky = true`, `attempts = ["fail", "pass"]`; the
  command ran exactly twice.
  (2) **fail → fail:** recorded `fail`, `attempts = ["fail", "fail"]`, no truthy `flaky`;
  the row's evidence (`path_line`) comes from the confirm run.
  (3) **fail → no pass:** when the confirm run times out (the row's `timeout_secs`),
  declares itself unverifiable, reports `deferred` (exit 0 + `PDCA-DEFERRED` on a
  deferrable row, `gates.py:795-798`), or raises an exception (`gates.py:599`), the first
  `fail` stands with the FIRST run's `path_line`, no truthy `flaky`; `attempts` records the
  second outcome as its own classification (`"unverifiable"`, `"deferred"`, `"error"` for the
  exception). Only a clean `pass` on the confirm run turns the row into `pass` + `flaky`.
  (4) **Bounds:** exactly one confirm run; a NON-gating failing row runs once; a passing row
  runs once (no cost on green); a `cmd_error` row (misconfigured delegation,
  `gates.py:508`) and a command that raised before producing an exit code
  (`gates.py:599`) are not confirmed; `[gates] confirm_gating_fail = false` in the project
  config turns confirmation off; a per-row `confirm_fail = false` turns it off for that row
  alone — honoured on a `[[gates.checks]]` entry AND on a `[gates] host_ci` entry (the key
  survives `_normalize_host_ci`, `config.py:860-890`; tested for both tables).
  (4b) **Check-time only:** confirmation runs only on the Check matrix — `run_gates` and its
  revalidate twin `run_gates_dry` (so a re-gate reproduces the frozen verdict). Every other
  `_run_one` caller runs a failing row exactly once and keeps today's behaviour: the publish
  host-CI gate (`publish.py:930`, a non-zero exit still refuses the push, the literal #311
  contract `config.py:870-871`), the between-waves integration re-gate
  (`gates.run_integration`), and the working-tree re-gate (`run_working_tree`). Tested: a
  fail→pass command driven through `publish`'s host-CI path (or `_run_one` with the
  confirm switch off, which is what those callers pass) records `fail` after ONE run.
  (5) **Evidence:** with a `log_dir`, the row's `gate-logs/<rule_id>.log` holds BOTH runs'
  output, each run under its own block with that run's attempt number, `# exit:` and
  `# outcome:` lines; the file's top-level `# outcome:` header (`gates.py:657-658`) shows
  the row's recorded (combined) result (the #370 contract: the full basis is readable from
  bundle files).
  (6) **Routing:** a row with truthy `flaky` becomes one §6 item via
  `assemble.collect_needs_human`, kind HUMAN (never IMPL, whatever its element), naming
  the check and both outcomes; `overall` counts the row as the pass it recorded.
- **Falsifiability:** RED today on this host. `_run_one` (`gates.py:498`) runs the command
  once (`progress.run_with_heartbeat`, `gates.py:588`), so the fail→pass command records
  `fail` and clauses 1, 5, 6 fail; `Config` has no `confirm_gating_fail`, so clause 4's
  opt-out test fails. Suite:
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_gate_confirm`, run by
  `./engine/scripts/run-verify.sh` (gating C4; a new test file stays in place on the red
  leg). Import modules only (`from pdca_harness import assemble, gates`), never a new symbol
  at module top, so the red leg fails on assertions rather than reading as
  PDCA-UNVERIFIABLE.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 409
- **Conflicts with:** 408
- **Ordering note:** The Depends-on 409 is for ORDERING ONLY, not a correctness
  prerequisite: this bundle's criterion (clause 6 asserts kind HUMAN) holds on main alone.
  It is kept because the two bundles edit the same `assemble.py` and
  `template/pdca.toml.jinja`, and building on 409's folded result avoids a blind collision.
  If 409 stalls, this bundle can be re-briefed onto main with no change to its criterion.
  Background: the issue's promise is that the flaky §6 item is
  HUMAN "so auto-iterate defers it instead of spending a rebuild round", and deferral is what
  #409 adds (today a HUMAN item vetoes auto-iterate outright). Building after 409 also
  separates the shared `assemble.py` and `template/pdca.toml.jinja` edits.
  Conflicts with 408 on `assemble.py` (the scheduler puts this first, 408 after). The only file
  overlap with 477 is `template/pdca.toml.jinja`, in separate sections (`[gates]` here, the
  size-signal comment there), which the wave fold merges hunk by hunk; so the two share a wave. Computed batch order (`pdca-pdca waves 408 409 371 477`): [409] → [371, 477] → [408].
- **Scope:** the confirm-once rule for failed gating rows in `gates._run_one`, switched on
  by an explicit keyword (default off) that only the Check path passes — `run_gates` and
  `run_gates_dry` via `_run_checks` (both its `[[gates.checks]]` rows and its host-CI rows,
  `gates.py:396`, `:425`); publish's host-CI gate, `run_integration` and
  `run_working_tree` do NOT confirm (clause 4b); the row keys
  `attempts` and `flaky`; the gate log carrying both runs; `[gates] confirm_gating_fail`
  (default true) in `config.py`; the per-row `confirm_fail` key; the §6 routing in
  `assemble.py` next to `_unverifiable_items`; documentation of both keys in
  `template/pdca.toml.jinja` `[gates]` and the gate docs (`docs/05-check.md`). / out of
  scope: re-sampling model leaves (reviewer, advisories); more than one confirm; retrying
  non-gating rows; confirming at publish, integration or working-tree re-gates (a red there
  blocks as today); any change to `size_signal.py` (it already reads a truthy `flaky` as
  environment-attributed, `size_signal.py:181-183`, and needs nothing new); changing the
  auto-iterate decision itself (#409).
- **Difficulty:** medium
- **External dependencies:** none
- **Test file:** template/tests/test_gate_confirm.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites on `main` @ 9405658 (this bundle builds on a later wave's folded base, so
  lines will have moved — locate by symbol): `_run_one` `gates.py:498` (cmd_error branch `:508`,
  single run `:588`, timeout → unverifiable `:592-596`, `_classify` `:736`, exception
  branch `:599`, row build `:603`, log write `:608-627`); `_write_gate_log` `:631` (extend
  it for two attempts rather than writing a second file); `_finalize` `:815` (`overall`
  from gating `fail` only); `_row` `:827`. Config: mirror `gates_default_timeout_secs`
  (field `config.py:274`, parse `:571-575`) for the new boolean. §6: add the flaky items
  beside `_unverifiable_items` (`assemble.py:456`), wired where it is used in
  `collect_needs_human` (`assemble.py:280`), HUMAN like that line. Consumer contract
  already on main: `size_signal._environment_attributed` (`size_signal.py:151-185`).
  Test Config builder to copy: `template/tests/test_gate_logs.py:52`.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -n 8 -- template/src/pdca_harness/gates.py` → 6d4f359, 5c7d010, 07766ed, 56250bb,
  1ed6868, e79d109, f262fb0 (#370 gate logs), 228e80b (#368 timeout) — none confirm a
  failed row. `confirm_gating_fail` / `confirm_fail` absent from the repo; `flaky` appears
  only in the size-signal consumer (363ac72, #446). Closed-unmerged PRs touching
  `gates.py`/`assemble.py`/`config.py`: none. No open PRs. A downstream instance
  (getwyrd/wyrd-pdca) staged this locally, not upstream.
- **Disposition hint:** new-feature

## Motivation

A gating row is one sample. getwyrd/wyrd-pdca `issue_648` (2026-07-31, round 7): `C4-ci`
recorded `cargo test` exit 101 about 90 s into a 7-minute step. The six earlier rounds, the
C4-verify run seconds later, the reviewer's own run, and a later manual re-run were all
green. That one sample cost the round its verdict, and with the auto-iterate budget spent it
went straight to the human's §6. The harness already treats "the oracle gave no answer" as
`unverifiable`, not `fail` (#46, #368). A fail contradicted by an immediate pass of the same
command is the same situation one step later.

## Design

In `_run_one`, after the first run classifies `fail` for a gating row with a real exit code
and confirmation enabled (caller switch from the Check path, project flag, and row flag),
run the same command once more with the same env/cwd/timeout, and combine: fail→pass ⇒
`pass` + `flaky`; fail→fail ⇒ `fail` with the confirm run's evidence; fail→anything else
(timeout, unverifiable, deferred, exception) ⇒ first `fail` stands with the first run's
evidence. Always
record `attempts`. The log file holds both runs. `assemble` lifts `flaky` rows into §6 as
HUMAN so C6 makes the human acknowledge the flake before accept.

## Alternatives considered

- Retry N times / until green: hides real intermittent defects; one confirm keeps both
  samples visible.
- Treat fail→pass as `unverifiable`: would drop it out of `overall` but also lose the green
  evidence. `pass` + `flaky` + a §6 item keeps both.

## Impact & compatibility

Default on: a genuinely red gating row now runs twice at Check (one extra run of an
already-red gate). Why default-on is safe for an existing instance that upgrades without
reading the note (its `pdca.toml` is kept by `copier update`): a fail→pass is never a silent
pass. It only happens at Check, and there the `flaky` row always becomes a HUMAN §6 item
naming both outcomes, which C6 blocks accept on until the human clears it. Publish and the
integration re-gate never confirm (clause 4b), so a lucky second sample cannot let a push
through. The worst case for a model-backed row left on default is one human look at a
§6 item, not a lost blocker. Instances with model-backed gate rows SHOULD still set
`confirm_fail = false` to avoid that re-sample; the upgrade note in `pdca.toml.jinja` says
so. New row keys are additive.

## Open questions

- None blocking.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

Plan-review response: all five findings addressed in the brief — confirmation limited to
Check (`run_gates` / `run_gates_dry`), with publish, integration and working-tree re-gates
unchanged (new clause 4b + Scope); deferred / exception confirm outcomes and clause 3's
`path_line` and log headers pinned (clauses 3, 5); `confirm_fail` honoured and tested on
`host_ci` entries (clause 4); default-on justified by the Check-only + HUMAN §6 routing
(Impact); Depends-on 409 stated as ordering-only (Ordering note).

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The implementation is accepted as correct; only the clause-4b guard test is too weak. `template/tests/test_gate_confirm.py:301-311` (`test_publish_host_ci_rows_run_once`) hand-copies publish's `gates._run_one(...)` call instead of driving publish, so it only re-checks that `_run_one` defaults to `confirm=False` (already covered at `:292`). Adding `confirm=True` at `template/src/pdca_harness/publish.py:930` would leave it green — the exact regression clause 4b exists to prevent. Next attempt: make the test drive the real publish host-CI path with a fail→pass command and assert it records `fail` after ONE run (or, at minimum, assert the `publish.py:930` call does not pass `confirm`). Keep the rest of the patch as is; the minor code-review clean-ups (`_flaky_items` list indexing, dead `rc`/`output` args to `_write_gate_log`) are optional.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The implementation is accepted as correct; only the clause-4b guard test is too weak.
  `template/tests/test_gate_confirm.py:301-311` (`test_publish_host_ci_rows_run_once`) hand-copies
  publish's `gates._run_one(...)` call instead of driving publish, so it only re-checks that
  `_run_one` defaults to `confirm=False` (already covered at `:292`). Adding `confirm=True` at
  `template/src/pdca_harness/publish.py:930` would leave it green — the exact regression clause 4b
  exists to prevent. Next attempt: make the test drive the real publish host-CI path with a
  fail→pass command and assert it records `fail` after ONE run (or, at minimum, assert the
  `publish.py:930` call does not pass `confirm`). Keep the rest of the patch as is; the minor
  code-review clean-ups (`_flaky_items` list indexing, dead `rc`/`output` args to `_write_gate_log`)
  are optional.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
