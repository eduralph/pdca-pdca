## Summary
**User impact:** When a run picked up a sign-off decision you had already recorded, it
told you it was applying that decision and that no new sign-off session would be opened
— and then, on the very next line, opened one anyway (or reported that the decision had
not been recorded at all). What you were reading was the opposite of what the run did,
on exactly the path that asks you to come back and judge the bundle again.

This moves that notice so it is printed *after* the decision has been applied, and only
when it really was applied — so the line that follows can no longer contradict it.

Reported in [#475](https://github.com/eduralph/pdca-harness/issues/475).

## What to look at
One function — `_apply_recorded_decision` in `template/src/pdca_harness/flow.py`: five
lines of code plus its docstring. Nothing about *what* the run does changes, only what
it prints and when.

To exercise it, from `template/` (offline, stdlib only):

    PYTHONPATH=src python3 -m unittest tests.test_signoff_orphan -v

The interesting cases are the ones where the apply does not happen and the operator is
told so a line later: an `accept` the C6 guard refuses while §6 NEEDS-HUMAN is still
open (a fresh session follows — that is by design), a bundle whose `SUMMARY.md` is gone
(decision dropped, will re-drive), and an unsignable `SUMMARY.md` (quarantined, bundle
back to reassemble). None of those may be reported as applied; each already reports
itself.

## Root cause
The notice was printed before `_apply_decision` was called — i.e. before the outcome
existed — so it asserted a result that a later step still owned. Every outcome other
than a successful record then withdrew it one line later, most visibly the C6
accept-guard, which prints its refusal and returns `"blocked"`, the one outcome that
deliberately falls through to a fresh session.

## Fix
The notice moves below the call and is guarded by `outcome == action`. `_apply_decision`
returns the action itself only after the sign-off was recorded, and a sentinel (`None`,
`REASSEMBLE`, `"blocked"`) in every other case; `leaves.VALID_DECISIONS` contains none of
the sentinel names, so the equality is an exact "it was applied" test and cannot collide
with a decision named after one. The docstring's "never silent" contract still holds:
each non-apply outcome already prints its own line naming the bundle and the action —
what they must not get is a line saying the decision was applied.

## Verification
- **Claim:** on a bundle carrying a recorded `accept` that C6 refuses, the run no longer
  claims that no new session will be opened — while the refusal message, the
  fall-through, the return value and every state transition stay exactly as they are.
- **Checked:** `template/src/pdca_harness/flow.py:245-249` on `main` — the notice is
  unconditional and precedes the apply; `flow.py:177-178` is the C6 refusal returning
  `"blocked"` right after it, and `flow.py:258-262` (single issue) / `flow.py:1367-1371`
  (batch sweep) are where `"blocked"` opens the fresh session. Both drive paths go
  through this one function, so both are covered by the same five lines.
- **Claim:** a decision that *is* applied without a session is still reported in the same
  terms, so "just delete the notice" is not a fix.
- **Checked:** `flow.py:211` on `main` — the single `return action`, reached only once the
  record succeeded — and `template/src/pdca_harness/leaves.py:84`, where
  `VALID_DECISIONS` is `{accept, iterate-do, iterate-plan, discontinue}`: no valid action
  can equal a sentinel.
- **Claim:** the two outcomes where the decision is explicitly *not* recorded stop being
  announced as applied as well.
- **Checked:** `flow.py:161-165` on `main` (no `SUMMARY.md` → "skipping record, will
  re-drive") and `flow.py:124-130` (unsignable summary quarantined → "bundle returned to
  … to reassemble") — each already prints its own honest line, which the applied-notice
  then contradicted.
- **Test:** `template/tests/test_signoff_orphan.py` — six assertions: the existing
  C6-refused cases on both drive paths (`:168` batch, `:241` single issue on `main`), a
  new `NotRecorded` class covering the dropped and the quarantined outcomes, and three
  positive assertions that a genuine apply is still announced. Fails on `main` (4 of 10),
  passes with this change; the full offline suite stays green (7 root tests, 1760 driver
  tests). `grep -rn "no new session"` matches only `flow.py`, so no other test or doc
  depends on the old placement.

Fixes #475
