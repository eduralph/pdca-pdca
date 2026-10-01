# Adversarial review — issue 409 (iteration 5)

**Evidence re-run.** I rebuilt the red leg in a scratch copy: the test files kept, the 10
production files under `template/src/` reset to `HEAD`. `tests.test_autoiterate` +
`tests.test_size_signal` gave 30 failures + 41 errors. On the patched tree all 157 pass. That
matches `gate-logs/C4-verify.log`. The red failures are real assertion and attribute failures
(no `retire_cleared`, the veto still declining), not import noise.

**Mutation pass (my own, 27 single-line breaks of the fix).** 26 were caught by the new
tests. These include: the first vs last §6 heading in `_needs_human_section`
(`signoff.py:119`) and in `ensure_needs_human_item` (`signoff.py:187`); symmetric-fuzzy
protection; dropping the exact tier (`autoiterate.py:421`); ignoring `protected`; taking the
first of several hits; dropping the ratio or the floor; dropping label stripping; deferring
`no_verdict` rows (`autoiterate.py:322`); the CLI accept path's own C6 check; no retire on
iterate-plan; and `defer` after `bump`. The one survivor (`unrecordable` reading the first
vs the last §6) behaves the same either way. The tests reach production code, not a copy.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/signoff.py:112-115` claims nothing after the
  assembled §6 can hold a second `## 6. NEEDS-HUMAN` heading, because "the flow flattens"
  the §9 iteration delta. The CLI path does not flatten it: `cli.py:1466` passes
  `args.delta` raw to `signoff.record`, which writes it verbatim (`signoff.py:308`). Only
  `flow.py:181-182` flattens. **Reproduced:** a ledger holds `[E1, E2]`, and both rows are
  left OPEN (`- [ ]`) in the real §6. Then
  `pdca signoff X --iterate-do --delta "$(printf 'notes\n## 6. NEEDS-HUMAN (from v1)\n- [x] E1\n- [x] E2')"`
  makes the §9 copy the "last" §6. At the iterate, `autoiterate.retire_cleared`
  (`autoiterate.py:409-410`) reads its ticks, ignores the real §6, and retires BOTH entries
  (`kept: []`). The trigger is narrow: a human has to paste a §6 heading line into
  `--delta`, for example a §6 block copied from an older iteration's SUMMARY. The fix is
  small and the builder can make it: flatten `--delta` in `cli._signoff`, or in
  `signoff.record` itself. The test helper `_section6` (`tests/test_autoiterate.py:95-98`)
  copies the same "last heading" rule, so the suite cannot see this. Left unmarked because
  whether a low-severity hole is worth a sixth rebuild is the human's call.

- NEEDS-HUMAN — The sign-off ruling (stale or recovered infrastructure rows must not need
  hand clearance) is applied only to the two placeholder texts and to gates that could not
  run (`assemble.py:320-337`). The harness-written **decorrelation note** is not covered:
  `leaves.py:3626-3631`, written from `_select_advisory` at `leaves.py:3664-3667`. It is
  re-derived on every Check: `leaves.py:3644` deletes the previous note first. It talks about
  that Check's own run ("confirm the review's independence by hand"), not about the patch.
  Yet it has no leaf-status marker, so it gets `no_verdict=False` and is deferred.
  Confirmed: `autoiterate.deferrable` returns it. Concrete case: round 1 has no
  `loop-telemetry.json`, so the note reads "builder family … unknown" and is deferred. In
  round 2 the family is known and a complement leaf exists, so no note is written. The
  handover §6 still asks the human to confirm the independence of a review of a patch that
  was thrown away. Whether this note belongs to the ruled class is a scope call. Note that
  the plan-advisory placeholder is NOT in that class: it is never re-run on iterate-do, so
  deferring it is correct.

- `check-gates.json` row "C5 added test exercises production, not a copy" reports `pass`,
  but its log (`gate-logs/C5-prod-path.log`) says "patch adds no new test file — nothing to
  assert". The tests went into existing files, so the gate checked nothing. That pass is not
  evidence. The mutation pass above independently shows the tests do run production code,
  so the conclusion holds. Only the gate row's evidence is empty.

## Attempted, could not refute

- The fresh vs rendered drift at retire time. `driver._retire_cleared_deferrals`
  (`driver.py:334-335`) re-derives `fresh` after `_carry_forward_into_brief`. The only
  input that could change is the `[[doctor.checks]]` dependency rows. Their texts share a
  long tail, not a long opening, so `_same_finding` keeps them apart.
- Any leaf text landing after the real §6. §7, §8 and §10 are fixed text written by the
  harness. Gate `path_line` values are single lines. Flow-written §9 deltas are flattened.
  The only hole is the CLI delta above.
- An edited tick retiring a neighbour. An edit of a rendered row still matches its own
  origin, so any near-twin makes two hits and fails closed. An edit that matches only a
  fresh row retires nothing.
- An unreadable ledger on every accept path. Both `_apply_decision` and `cli._signoff` go
  through `flow.accept_blockers`. If §6 is missing, `ensure_needs_human_item` adds nothing,
  but `record` then refuses on `unrecordable`. A ledger entry that is not a string, or a
  dangling symlink, raises `DeferredLedgerUnreadable`.
- `no_verdict` spoofing. A real (closed) artifact never gets a leaf-status label, so its
  rows can never be marked no-verdict. Placeholder reasons are single-line in practice
  (`str(CalledProcessError)` quotes argv with `repr`).
- Clause 1 / clause 4 flow behaviour (the cap at 3 with `rounds = 0`, the backstop at 2 by
  default, `[IMPL, HUMAN, size HUMAN] → False`). These are driven through the real
  `flow._maybe_auto_iterate` and pass for the right reason.
