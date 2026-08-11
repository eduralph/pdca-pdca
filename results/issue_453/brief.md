# Brief — issue 453 / signoff-decision-orphaned-by-interrupted-session

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** apply-orphaned-signoff-decision
- **Defect:** the sign-off leaf writes `signoff-decision` durably, but the driver consumes
  it only **in-process**, in the same call that launched the session. If the run dies
  between the leaf's write and the driver's apply — a `^C` during the interactive session
  raises `KeyboardInterrupt`, which `_isolate` deliberately does not contain
  (`template/src/pdca_harness/flow.py:50-69`) — the decision is orphaned on disk with §9
  unrecorded. On every later pass and every later run the bundle is still
  AWAITING_SIGNOFF, so the queue re-presents it and the driver opens a **fresh interactive
  session for a bundle the human already judged**; the decision on disk is never read. The
  reporting instance saw the same decision made at 12:43, re-issued at 19:48 and
  re-affirmed a third time, none recorded (instance report: getwyrd/wyrd-pdca#211).
  Two aggravations: `_drive_wave`'s no-progress exit only fires when the pending queue is
  empty (`flow.py:668-685`), so a wave holding one such bundle re-runs the session every
  pass until `max_passes` runs out; and `autoiterate.write_decision` (`flow.py:271`) writes
  unconditionally, so an auto-iterate pass can silently clobber an orphaned human decision
  with one it did not author.
- **Success criterion:** on a bundle halted at AWAITING_SIGNOFF that already carries a
  valid `signoff-decision` written by an earlier session, BOTH drive paths — the batch
  `flow._drive_wave` and the single-issue `flow._signoff_and_apply` — record §9 and
  transition the bundle **without invoking any sign-off leaf**, and `_maybe_auto_iterate`
  declines (writes no decision, spends no auto-iterate budget) while such a file exists.
  The one exception: an `accept` that C6 refuses (§6 NEEDS-HUMAN still open) still falls
  through to a fresh session, because there the human genuinely must return. Demonstrable
  by C4-verify on the patch alone, via the offline driver suite.
- **Falsifiability:** RED is producible on the ordinary offline driver suite, no topology
  needed — `cd template && PYTHONPATH=src python3 -m unittest tests.test_signoff_orphan`,
  which is exactly what `engine/scripts/run-verify.sh` runs for a `template/tests/*.py`
  test. Pre-fix, a bundle seeded at AWAITING_SIGNOFF with `signoff-decision` = `iterate-do`
  gets a sign-off session anyway; the stub sign-off leaf overwrites the file with `accept`
  (`template/src/pdca_harness/leaves.py:2980`) and the bundle records an *accept* the human
  never gave — an assertion on "no session was invoked / §9 records iterate-do" fails
  loudly. Post-fix it passes. No live tracker, no network, no `gh`: all leaves stubbed, as
  in `template/tests/test_flow_slice.py:31-56`.
- **Invariant to restore:** a decision recorded durably in the bundle is **un-consumed
  input to the driver**, not an in-process by-product of the session that wrote it — every
  path that is about to ask for a decision must first read the one already on disk, and
  the driver must never overwrite a decision it did not author. Source (internal project
  rule, Tier C): *"The state of an issue **is** the set of files in its bundle directory …
  Keeping state in the filesystem is what makes the pipeline resumable and inspectable"* —
  `template/src/pdca_harness/state.py:1-6`, restated normatively in
  `template/PCDA/quality-cycle/08-glossary.md:82` (*"State is the files present in it — no
  database"*). A driver that reads a bundle file only through the variable of the call that
  produced it has made that file non-resumable, which is the property the rule exists for.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 449
- **Ordering note:** 449 rewrites the same `_drive_wave` pass loop and the same `flow_ids`
  / `flow` entry points, so the two must never build blind on the same base. This bundle is
  the smaller, purely-corrective one and is scheduled FIRST (wave 0, alongside 448); 449
  declares `Depends on: 448, 453` and builds on this fix's accepted result in wave 1.
- **Surfaces:** data
- **Difficulty:** medium — three call-sites in one module (`flow.py`), but its effect
  reaches every sign-off path (single-issue, batch wave, auto-iterate), which is what a
  diff-reviewer must hold in view.
- **Scope:** a decision already recorded for a bundle is applied **before** that bundle is
  offered a new sign-off session, on both drive paths, with the same apply-deferred
  semantics the post-session path already uses (`apply_now=False` in the wave sweep,
  `apply_now=True` single-issue); and auto-iterate never authors a decision for a bundle
  whose previous decision is still un-consumed. Each such apply is announced on stderr
  naming the bundle and the action, so a decision applied without a session is never
  silent. Mechanism is Do's — this states the property, not the shape.
  / out of scope: changing the decision grammar or `VALID_DECISIONS`
  (`leaves.py:78`); changing what C6 blocks or how §9 is written (`signoff.record`);
  making `_isolate` contain `KeyboardInterrupt` (the ^C must still stop the run — that is
  its documented contract, `flow.py:56-58`); the no-progress/`max_passes` accounting beyond
  what falls out of the pre-apply; any change to the interactive sign-off prompt.
- **Repro instruction:** on a clean checkout of `eduralph/pdca-harness` @ `main`, in a
  temporary instance with all leaves stubbed (copy the fixture shape of
  `template/tests/test_flow_slice.py:31-56`): drive a bundle to AWAITING_SIGNOFF, write
  `iterate-do\nnot yet — the gate is wrong\n` into `<bundle>/signoff-decision`, then call
  `flow._drive_wave(cfg, [bundle], by="t", today="2026-01-01")` with
  `leaves.run_signoff_batch` patched to record its calls. Observed: the leaf is called, the
  orphaned decision is overwritten, §9 records an `accept`. Expected: no call, §9 records
  the human's `iterate-do`, the bundle leaves AWAITING_SIGNOFF. The same holds for
  `flow._signoff_and_apply` with `leaves.run_signoff` patched.
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; the test is in the
  offline driver suite and needs no tracker, network or container.
- **Test file:** `template/tests/test_signoff_orphan.py` (new module in the offline driver
  suite; the name the reporting instance already pins this behaviour under). The C4 gate
  reverts only the PRODUCTION hunks and keeps the test
  (`engine/scripts/run-verify.sh`, `--exclude=template/tests/*`), so a new test file earns
  its red correctly. **Import modules, never new symbols:** write
  `from pdca_harness import flow, leaves, state` and reach anything this patch adds as
  `flow.<new_name>`. A `from pdca_harness.flow import <new helper>` would raise ImportError
  on the red leg, which run-verify.sh classifies as PDCA-UNVERIFIABLE (exit 77) instead of
  a red — the test would prove nothing.
- **Citations expected:** Do must cite `path:line` on `origin/main` for every change. The
  four sites this fix concerns, verified at `b95aa58`:
  `flow.py:132-210` `_apply_decision` (the deterministic record/transition to reuse — do
  not duplicate it); `flow.py:213-218` `_signoff_and_apply` (runs the leaf
  unconditionally); `flow.py:686-695` the per-chunk session-then-apply in `_drive_wave`;
  `flow.py:668-685` the no-progress exit gated on an empty `pending`; `flow.py:241-276`
  `_maybe_auto_iterate`, whose `autoiterate.write_decision(d, items)` at `flow.py:271` is
  unconditional. **Peer to mirror:** the post-session apply at `flow.py:693-695` — a
  pre-apply must use the same `_isolate(d, …, lambda: _apply_decision(cfg, d, by=by,
  today=today, apply_now=False))` shape and the same `REASSEMBLE` / `"blocked"` / `None`
  return handling the callers already implement (`flow.py:344-354`), rather than a second
  transition path.
- **Prior-art check (triage cycles):** searched by affected file path against
  `origin/main` @ `b95aa58` — `git -C ../pdca-harness log --oneline origin/main -n 12 --
  template/src/pdca_harness/flow.py` shows the recent flow work is the malformed-SUMMARY
  reassembly (`8cdd8a6`, `8e0b6a9`, #330) and §9 matching (`2407965`); none pre-applies an
  existing decision. `gh issue list --state all` (300) and `gh pr list --state closed`
  (200) over *signoff / sign-off / orphan / decision*: #327/#328/#330 hardened §9 *parsing*,
  #174 ordered iterate-plan before deferred iterate-do rebuilds, #42/#45/#50 added the
  discontinue disposition — none reads a pre-existing `signoff-decision`. No open PR
  touches `flow.py` (`gh pr list --state open` is empty). Not previously filed, not
  rejected, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether the independently green focused and offline-driver coverage is sufficient without `copier` — the driver suite passed 1595 tests, but the root render/update suite executed zero tests (all 7 skipped) because `copier` is unavailable, so the recorded root-suite green was not independently reproduced.; T4 Contribution — Decide whether to rely on the frozen contribution-gate result — `commit-msg.txt`, `pr-description.md`, and the configured `scripts/pdca` checker were not among the permitted inputs or target files, so the tracker-id and user-impact-opener assertions could not be independently checked.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 2): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Decide whether the independently green 1,598-test offline-driver suite is sufficient without render/update coverage — `copier` is absent, so the root suite reported green while executing 0 of 7 tests (all skipped by guards such as `tests/test_render_and_run.py:31` and `tests/test_update_compat.py:232`).; T4 Contribution — Decide whether to rely on the frozen contribution-gate PASS — `commit-msg.txt`, `pr-description.md`, and the configured checker are outside the permitted reviewer inputs, so the tracker-id and user-impact-opener claims could not be independently reproduced (`template/src/pdca_harness/leaves.py:65`).
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
