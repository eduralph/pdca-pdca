## Summary

**User impact:** A sign-off you have already given can be thrown away and asked for
again. If the run is interrupted after you answer — a Ctrl-C, a crash, a dropped SSH
session — your answer is stranded: nothing is recorded, the issue is still shown as
waiting for sign-off, and the next run opens a **fresh sign-off session for an issue
you have already judged**. Answering again does not help, because each new session
overwrites the previous answer; one instance reported making the same call three times,
none of them recorded. In a batch run this repeats on every pass until the run gives up,
and an automatic rebuild can quietly replace your answer with one you never gave.

This change makes the driver read the answer already saved for an issue *before* it
offers a new sign-off session, so an interrupted run resumes where you left off instead
of asking again.

Reported in [#453](https://github.com/eduralph/pdca-harness/issues/453).

## What to look at

One module: `template/src/pdca_harness/flow.py`. There are two places a run can ask for
a sign-off — the batch drive over a group of issues and the single-issue drive behind
`pdca flow <id>` — plus the automatic-rebuild path. All three now consult the saved
answer first, through one small shared helper; nothing else about how a decision is
recorded changed.

To try it: drive an issue to the sign-off halt, answer, then Ctrl-C the run before it
finishes. Re-run it. Previously you were asked again and your first answer was lost;
now the run applies it, prints which issue and which answer it applied, and moves the
issue on without opening a session. The one deliberate exception is an acceptance that
is refused because unresolved items are still open — that still asks you again, since
there you really do have to come back.

## Root cause

The answer is written into the issue's directory as a file, so it survives the process,
but the driver only ever read it back through the in-memory return value of the same
call that opened the session. A run that ended between the write and the apply therefore
left the answer on disk with nothing consuming it, and every later pass took the issue's
unchanged "waiting for sign-off" status at face value and opened another session over
it.

## Fix

A saved answer is treated as un-consumed *input* to the driver rather than a by-product
of the session that produced it. A single helper reads it and, when there is one,
routes it through the existing record-and-transition path — same guard, same author of
the record, same clean-up of the answer file — and announces the issue and the action on
stderr. The batch drive pre-applies every already-answered issue and then offers a
session only to the ones still undecided; the single-issue drive does the same before
opening its session; the automatic rebuild declines outright (and spends no budget)
while an unconsumed answer exists, so it can never author a decision over one it did not
write. Only two outcomes still lead to a session: nothing was saved, or the acceptance
was refused for open items.

## Verification

- **Claim:** an issue that already carries a saved sign-off answer is recorded and moved
  on by *both* drive paths without any sign-off session being opened, and the automatic
  rebuild writes no answer and spends no budget while one is waiting; an acceptance
  refused for open items is the only case that still asks again.
- **Checked:** `template/src/pdca_harness/flow.py:213-218` on `main` — the single-issue
  path ran the session unconditionally; `flow.py:686-695` — the batch path fed every
  pending issue straight into a session and only then applied; `flow.py:271` — the
  automatic rebuild wrote its answer unconditionally; `flow.py:132-210` — the
  record-and-transition path all three now reach instead, unchanged by this PR, so the
  guard and the record's author are exactly as before.
- **Checked:** `template/src/pdca_harness/flow.py:50-69` on `main` — the isolation
  wrapper deliberately does not swallow `KeyboardInterrupt`, which is why a Ctrl-C
  strands the answer; that contract is untouched here, the fix is to read the file on
  the next pass rather than to catch the interrupt.
- **Test:** `template/tests/test_signoff_orphan.py` (new, 8 cases) — fails pre-fix,
  passes post-fix. Run with `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_signoff_orphan`. With the production change reverted and the test kept,
  6 of the 8 fail, reporting that a session was opened for an already-answered issue and
  what the session recorded in its place; the 2 that stay green are the refused-
  acceptance cases, which assert a session *is* opened and so hold on both sides. The
  fixture is a genuinely halted issue carrying the stranded answer, and each stand-in
  session does what the real one does (writes its own answer), so the overwrite actually
  happens on the failing run rather than being curated away.
- **Suites:** the offline driver suite is green at 1599 tests (1591 before, plus the 8
  new); the template render and update-compatibility suites are green at 7 tests.

Fixes #453
