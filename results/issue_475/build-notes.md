# Build notes — issue 475 / no-new-session-notice-waits-for-the-guard

Iteration 2. Target branch: `eduralph/pdca-harness @ main` (worktree `$PDCA_WORKTREE` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, base `acb214a`). All line numbers below are on
that branch: “base” = the unpatched file, “post-fix” = the file with `patch.diff` applied.

## What changed

One function, `flow._apply_recorded_decision` (`template/src/pdca_harness/flow.py:223`).

**Base:** `flow.py:247-248` printed
`flow: <bundle> — applying the '<action>' sign-off decision already recorded in the bundle;
no new session` and only then called `_apply_decision` (`flow.py:249`) — where the outcome
is actually decided.

**Post-fix** (`flow.py:256-260`):

```python
outcome = _apply_decision(cfg, d, by=by, today=today, apply_now=apply_now)
if outcome == action:
    print(f"flow: {d.name} — applied the '{action}' sign-off decision already recorded "
          f"in the bundle; no new session", file=sys.stderr)
return outcome
```

Five lines of code (plus a docstring rewrite at `flow.py:241-251`). Nothing else moves: the
C6 message (`flow.py:177`), the `"blocked"` return (`flow.py:178`), the fall-through in
`_signoff_and_apply` (`flow.py:270-273`) and in the batch sweep (`flow.py:1376-1390`), and
every state transition are untouched — the patch changes *what is printed and when*, only.

### Why `outcome == action` and not `outcome != "blocked"`

This is iteration 1's rejection, addressed head-on. `_apply_decision` returns the **action
itself** exactly once — after `signoff.record` succeeded (`flow.py:211`) — and a sentinel
in every other case:

| outcome | where | what really happened | who reports it |
|---|---|---|---|
| `action` | `flow.py:211` | §9 recorded (+ transition when `apply_now`) | this notice |
| `None` | `flow.py:161-165` | no SUMMARY.md → decision **dropped**, will re-drive | `flow.py:162-163` |
| `REASSEMBLE` / `None` | `flow.py:173-175` → `_repair_unsignable` (`flow.py:114-130`) | summary quarantined, bundle back to reassemble | `flow.py:127-129` |
| `"blocked"` | `flow.py:176-178` | C6 refused; a fresh session follows | `flow.py:177` |

`leaves.VALID_DECISIONS` is `{accept, iterate-do, iterate-plan, discontinue}`
(`template/src/pdca_harness/leaves.py:84`) and `signoff_decision` returns `""` for anything
outside it (`leaves.py:3346`), so `action` can never be the string `"blocked"` or
`"reassemble"`: the equality is an exact "it was applied" test and cannot collide with a
token named after a sentinel. The three non-apply rows each already print their own line
naming this bundle and this action, so the docstring's "never silent" contract
(`flow.py:241-242`) still holds — what they must not get is a line saying the decision was
*applied*.

## Carry-forward from iteration 1 — item by item

1. **“Gate on genuine success — `if outcome == action:`, not `!= "blocked"`.”** Done,
   `flow.py:257`. Proven binding by mutation: reintroducing `if outcome != "blocked":`
   turns `NotRecorded.test_a_dropped_decision_is_not_announced_as_applied` and
   `…_a_repaired_unsignable_summary_…` red (2 failures, 10 tests ran). The rejected
   approach can no longer pass this suite.
2. **“Fix the docstring, which restates the same false dichotomy.”** The iteration-1 tail
   (“`blocked` is the one outcome that must not get this notice”) is gone. The new tail
   (`flow.py:241-251`) states the rule positively — printed after the apply and only when
   the decision was genuinely recorded — and names all three non-apply outcomes and where
   each reports itself.
3. **“Add the missing red case: an orphaned decision whose bundle also lost or mangled
   SUMMARY.md, reached via `_apply_recorded_decision`.”** New class `NotRecorded`
   (`template/tests/test_signoff_orphan.py:316`), both sub-cases, both driven through
   `flow._signoff_and_apply` (no session in sight): the lost summary
   (`:328`, outcome `None`) and the unsignable one (`:357`, outcome `REASSEMBLE`). Both are
   red on base.
4. **“The two new assertions re-derive inline what `_Base._announced` already computes.”**
   All six notice assertions now go through `_announced` (`test_signoff_orphan.py:122`); its
   parameter is renamed `action` → `needle` and its docstring widened, because the helper
   was already being passed message fragments (`"not auto-iterating"`, base `:308`).
5. **“Keep as-is: the reordering and the C6-refused cases on both drive paths.”** Kept
   verbatim in shape — the reorder stands, and both C6 assertions stay
   (`test_signoff_orphan.py:212` batch, `:290` single).

## What the test asserts (both directions)

`template/tests/test_signoff_orphan.py`, +1 constant, +1 class, +6 assertions:

* **Must not claim it** — C6-refused accept, batch (`:212`) and single-issue (`:290`);
  dropped decision (`:353`); repaired summary (`:387`).
* **Must still claim it** — `iterate-do` applied without a session, batch (`:163`) and
  single-issue (`:269`); `accept` C6 *permits*, applied without a session (`:187`). These
  are the Success criterion's second half, and they are what makes “just delete the notice”
  fail (mutation below). `iterate-plan` / `discontinue` take the identical
  `outcome == action` branch, so they are covered by construction, not by a fourth fixture.

The two `NotRecorded` fixtures assert the *honest* line is still printed (`"skipping
record"` at `:351`, `"to reassemble"` at `:385`) and that behaviour is unchanged (return
value, no session, decision dropped, `state.state(d)` equal to what it was, summary
quarantined) — so the tests bind the message change without licensing a behaviour change.
The unsignable fixture asserts `signoff.unrecordable(summary)` is non-empty *before*
driving (`:367`), so it cannot silently degrade into "a summary that was fine after all".

## Alternatives ruled out (with costs)

* **Reword the notice in place** (the brief's other option): drop the "no new session"
  clause from the pre-apply line — a 1-line diff, smaller than mine. Rejected: it fails the
  Success criterion's second half, which requires that on a decision that *is* applied the
  operator is still told "in the same terms" that no new session was opened. Recovering
  that needs a second, post-apply notice — i.e. the same reorder plus an extra line kept
  before the guard (7 lines, not 5). Iteration 1's sign-off also said the reorder is
  correct and must be kept.
* **Return a richer result from `_apply_decision`** (e.g. `(outcome, applied: bool)` or a
  dataclass), so callers never compare strings. Cost is checkable, not adjectival: that
  string is produced at 7 lines (`flow.py:130, 155, 165, 175, 178, 192, 211`), read at 6
  more (`flow.py:270, 273, 340-341, 426, 432, 1380`) and asserted directly by 11 test lines
  across 4 modules (`test_flow_slice.py:243, 253`; `test_handoff.py:418`;
  `test_signoff_authority.py:369, 371, 385, 398, 421, 423, 449`;
  `test_signoff_orphan.py:380`) — ~24 lines in 5 files, versus 5 code lines in 1 function
  here. The sentinel contract is also deliberately documented as-is at
  `flow.py:214-220`; rewriting it is a refactor this defect does not need. Note this is a
  restore-the-invariant slice, so minimality is not the deciding axis anyway — the reorder
  is what restores it; this option would restore it too, just far wider.
* **Suppress the notice inside `_apply_decision` instead** (pass a flag): pushes a caller's
  reporting concern into the C6-guarded record path, which `_maybe_auto_iterate`
  (`flow.py:340`) and the post-session applies (`flow.py:1390`) also use — it would make
  three callers carry a flag for one caller's message. No.
* **`_maybe_auto_iterate`'s own pre-apply notice** (`flow.py:336-339`, "auto-iterate n/N:
  … no human judgment needed") — considered and left alone. It reports a classification the
  driver has already made and already written (`autoiterate.write_decision`,
  `flow.py:335`); it asserts no outcome a downstream guard owns. It is also explicitly out
  of the brief's Scope ("one function, one message").

## Refuting my own test (forced)

**(a) Genuine red?** Yes. The project's C4 gate reverts exactly the production hunks and
keeps every `template/tests/*.py` hunk
(`/home/eddie/pdca/pdca-pdca/engine/scripts/run-verify.sh:214-217`):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_signoff_orphan.py
Ran 10 tests in 0.023s / OK
== C4 red leg: bundle test(s) with the production change reverted
FAIL: DriveWave.test_c6_refused_accept_still_gets_a_fresh_session
FAIL: NotRecorded.test_a_dropped_decision_is_not_announced_as_applied
FAIL: NotRecorded.test_a_repaired_unsignable_summary_is_not_announced_as_applied
FAIL: SignoffAndApply.test_c6_refused_accept_still_gets_a_fresh_session
Ran 10 tests in 0.023s / FAILED (failures=4)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

10 tests **ran** on the red leg (no `unittest.loader._FailedTest`), because the patch
introduces no new symbol for a test to import — `flow.REASSEMBLE` (`flow.py:91`) and
`signoff.SIGNOFF_HEADING` / `unrecordable` already exist on base. Two extra mutants, run
in-place and restored (`git diff` re-verified byte-identical to `patch.diff` after each):
delete the notice entirely → 3 failures; restore iteration 1's `!= "blocked"` gate → 2
failures.

**(b) Production path?** Yes. The tests import the real package
(`from pdca_harness import assemble, autoiterate, driver, flow, leaves, signoff, state`,
`test_signoff_orphan.py:39`) and call the production entry points being changed:
`flow._signoff_and_apply`, `flow._drive_wave`, `flow.flow`. The only patched objects are
`leaves.run_signoff` / `run_signoff_batch` — the *interactive human session* the harness
must not open — never the code under test. The bundles are built by really driving stub
Plan→Do→Check to an AWAITING_SIGNOFF halt (`_halted_bundle`, `:110-120`), so the SUMMARY,
§6 and states are the real assembled artifacts.

**(c) Fixture includes the fault?** Yes, in all three shapes. The C6 fixtures leave §6
genuinely unticked, so the real `signoff.open_needs_human` refuses and the mocked human
really does come back and clobber (`_session_writes_accept`) — the tests assert the session
*was* opened (`:206`, `:286`), i.e. the fault is present, not curated out. The dropped
fixture really unlinks `SUMMARY.md`; the repaired fixture really truncates §9 away and
asserts `signoff.unrecordable()` is non-empty before driving, then asserts the quarantine
file exists afterwards. No fixture excludes the failing element.

## Evidence / runners

Run through the project's configured gate commands (both have the driver's timeout when
Check runs them; bounded with `timeout` here too):

* `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS
  — red without the fix, green with it`.
* `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh` → `PDCA-EVIDENCE: root suite OK, driver
  suite OK` (7 root tests; **1760** driver tests, 2 skipped) — no other test or doc depends
  on the old wording (`grep -rn "no new session"` matches only `flow.py`).
* `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` (C5) → "patch adds no
  new test file — nothing to assert" (the brief directs the cases into the existing
  module).

**Commit-readiness:** the target has no formatter/linter config and no git hooks
(`core.hooksPath` unset, no non-sample hooks, no `pyproject.toml` / `ruff.toml` /
`.pre-commit-config.yaml`); its CI is docs-check / render-check / require-linked-issue.
Docs are untouched, both suites are green, both touched files byte-compile, and every added
line stays within each file's own longest-line convention (`flow.py` ≤ 102, the test file
≤ 92 — measured against base).

**External dependencies:** none beyond the brief's declaration — pure stdlib Python, offline.
Nothing was blocked, so no NEEDS-HUMAN external-dependency marker is warranted.
