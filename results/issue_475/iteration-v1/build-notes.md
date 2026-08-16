# Build notes — issue 475 / no-new-session-notice-waits-for-the-guard

## What changed and why

`flow._apply_recorded_decision` (target base `template/src/pdca_harness/flow.py:223-249`)
printed the "no new session" notice at `:247-248`, **before** calling `_apply_decision`
(`:249`). `_apply_decision` is where the C6 accept-guard lives (`:176-178`): an `accept`
with §6 NEEDS-HUMAN still open prints "cannot accept, §6 NEEDS-HUMAN still open (C6)" and
returns `"blocked"`, which is the one outcome `_signoff_and_apply` (`:258-262`) and the
batch sweep (`:1366-1379`, unmodified) let fall through to a fresh session. So the operator
read "no new session" one line before the guard opened one anyway.

Fix (`flow.py:249-256` post-patch): call `_apply_decision` first, capture its `outcome`,
and print the notice **only when `outcome != "blocked"`** — i.e. only once the apply has
actually gone through without a session. This is "move the notice past the decision" (the
first of the two options the brief's Invariant section names), not a reword, because
moving it is the smaller, more literal fix: the message's claim was already correct in
every non-blocked case, it was only asserted at the wrong time.

- Chose **move past decision + gate on outcome**, not **reword to not assert an outcome**.
  A reworded, hedged notice ("attempting to apply…") would have to be printed in the
  blocked case too, or the "Never silent: an apply with no session names the bundle and
  the action on stderr" contract (`flow.py:238-242` docstring, cited in the brief) breaks
  for the cases where the apply really does happen without a session — the reviewer would
  have had to check both the C6 print (`:176-178`) and a hedged pre-notice line up to see
  whether "attempting" ever completed. Moving the same, still-confident phrasing past the
  decision keeps the docstring's promise literally true and needs no extra branch beyond
  the one-line `if outcome != "blocked":` gate.
- Ruled out: suppressing the print via a `try`/`except` around `_apply_decision`raising —
  not applicable, `_apply_decision` never raises for the C6 path, it returns `"blocked"`
  as a normal value (`flow.py:176-178`), so branching on the return value is the direct
  fit, not an exception-based workaround.
- Left everything the brief scoped out untouched: the C6 guard and its message
  (`flow.py:176-178`), the `"blocked"` fall-through contract (`:258-262`, `:1366-1379`),
  `_apply_decision`'s repair paths (`:161-192`), and the interactive sign-off leaf. The
  diff touches only the two lines inside `_apply_recorded_decision` that decide when to
  print, plus its docstring, plus the two brief-named test methods.

## Wording

Old: `"applying the '<action>' sign-off decision already recorded in the bundle; no new
session"` (present/continuous, printed before the fact).
New: `"applied the '<action>' sign-off decision already recorded in the bundle; no new
session"` (past tense, printed after `_apply_decision` returns and only when it did not
return `"blocked"`) — matches the voice the brief's citations use: `flow.py:154`
("sign-off recorded no decision") and `:162-163` ("decision '<action>' but no SUMMARY.md
…; skipping record, will re-drive") are both printed after the condition they describe is
established. Same field content (bundle name, action, "no new session"), so
`_Base._announced(d, action)` (test file `:111-115`) still matches it for the
already-passing "notice still fires on a real apply" tests
(`DriveWave.test_applies_orphaned_decision_without_a_session` `:121-147`,
`SignoffAndApply.test_applies_orphaned_decision_without_a_session` `:215-239`), so those
keep proving a fix that just deletes the notice would fail them.

## Test

Appended two assertions (test file, target branch) to the two tests the brief names:
- `DriveWave.test_c6_refused_accept_still_gets_a_fresh_session` (`:168-189`, assertion
  added at `:186-189`)
- `SignoffAndApply.test_c6_refused_accept_still_gets_a_fresh_session` (`:245-261`,
  assertion added at `:262-265`)

Each now also asserts `self.err` (the redirected stderr, `_Base.setUp` `:94`) carries no
line naming the bundle AND containing "no new session" — i.e. the C6-refused case must not
claim a session won't open. Both existing companion tests
(`test_applies_orphaned_decision_without_a_session` in both classes) already assert, via
`_announced`, that the notice IS still printed when a decision really is applied without a
session — so a fix that just deletes the notice (rather than moving it past the guard)
would fail those two, and a fix that never suppresses it for `"blocked"` would fail the two
I added. No new test class, no new fixture — used the module's own `_halted_bundle` /
`_session_writes_accept` / `self.err` machinery already in place for this exact scenario.

## Runner

Per the brief's repro instructions (§Repro instruction) and `template/`'s own convention,
ran the module directly through stdlib unittest, offline, pure Python ≥3.11, no network:

    PYTHONPATH=src python3 -m unittest tests.test_signoff_orphan -v

- **Post-fix:** `Ran 8 tests … OK` (all 8 tests in the module, including the 2 new
  assertions and the 6 already-present ones, e.g. the batch-mixed-bundle and end-to-end
  `pdca flow` tests).
- **Pre-fix (fix reverted, test kept — mirrors C4's red leg which reverts only `flow.py`):**
  reverted `template/src/pdca_harness/flow.py` alone (`git stash push -- …flow.py`), kept
  the test edits, reran the same command: `FAILED (failures=2)`, both exactly the two
  appended assertions, e.g.
  `AssertionError: ["flow: issue_ORPHANSOLOC6 — applying the 'accept' sign-off decision
  already recorded in the bundle; no new session"] is not false : stderr claimed no new
  session would be opened, then C6 opened one anyway` — the literal defect from the brief.
  Restored the fix (`git stash pop`) and reran: back to `OK`.
- Also ran the **whole** `template/tests` suite post-fix (`PYTHONPATH=src python3 -m
  unittest discover -s tests`, from `template/`): `Ran 1758 tests … OK (skipped=2)` — no
  regressions elsewhere on the sign-off/flow surface.
- Did not use a hand-rolled container invocation; this is the exact command the brief's
  own §Repro instruction specifies, which is `template/`'s own offline stdlib-unittest
  entry point (no GUI/display dependency, nothing to keep import-light — the module only
  imports stdlib + the package under test).

## Self-refutation (forced questions)

**(a) Genuine red?** Yes. With `flow.py` reverted to its pre-patch state and the test
edits kept, both appended assertions fail with the exact message the brief describes
(shown above) — `FAILED (failures=2)`. Confirmed by actually running `git stash` /
`unittest` / `git stash pop` in this session, not asserted from reading the diff.

**(b) Production path?** Yes. The test drives `flow._drive_wave` and
`flow._signoff_and_apply` directly (no mock of `_apply_recorded_decision` itself), which
are the real single-issue and batch entry points named in the brief's Success criterion —
the same functions `pdca-pdca flow` and the batch sweep call in production. Only the
*leaf* (`leaves.run_signoff` / `leaves.run_signoff_batch`) is mocked, which is the existing
pattern the whole test module already uses to keep the slice offline (per the brief's
Falsifiability section — "the offline driver suite exercises the whole path with stub
leaves").

**(c) Fixture includes the fault?** Yes. `_halted_bundle(id, "accept\n")` writes a real
`signoff-decision` file and deliberately leaves §6 NEEDS-HUMAN open (comment at test file
`:171`/`:242`: "§6 deliberately left open"), so `signoff.open_needs_human` — the real C6
predicate `_apply_decision` calls at `flow.py:176` — genuinely returns true and the guard
genuinely fires and returns `"blocked"`, which is what drives the fall-through this bundle
is about. Nothing curates the open §6 item out.

## External dependencies

None. Confirms the brief's "External dependencies: none".
