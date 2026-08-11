# Build notes — issue 453 / apply-orphaned-signoff-decision

## What changed, and why

Three call-sites in `template/src/pdca_harness/flow.py`, all on `origin/main` @ `b95aa58`:

1. **`_signoff_and_apply` (`flow.py:213-236` post-patch, was `flow.py:213-218`).**
   Before opening the interactive sign-off leaf, check `leaves.signoff_decision(d)`. If a
   valid decision is already durable on disk, apply it via the existing `_apply_decision`
   (unchanged, reused as-is — `flow.py:132-210`) and return, *without* calling
   `leaves.run_signoff`. The one exception the brief names explicitly: if `_apply_decision`
   returns `"blocked"` (C6 refused an `accept`), fall through to a fresh session anyway —
   the human genuinely must return. Announces the pre-apply on stderr, naming the bundle.

2. **`_maybe_auto_iterate` (`flow.py:241-...`, new guard right after the existing
   `AWAITING_SIGNOFF` check at the old `flow.py:241-242`).** Added: if
   `leaves.signoff_decision(d)` is already set, return `False` immediately — before
   `assemble.collect_needs_human`, before `autoiterate.count`, before
   `autoiterate.write_decision`. This directly addresses the brief's second aggravation
   (`autoiterate.write_decision` at the old `flow.py:271` was unconditional and could
   clobber an orphaned human decision it did not author) and satisfies the success
   criterion's explicit auto-iterate clause: "writes no decision, spends no auto-iterate
   budget."

3. **`_drive_wave` (`flow.py:639-701` pre-patch, the pending/chunk block at
   `flow.py:686-695`).** After computing `pending` (unchanged — the "no-progress" gate at
   the old `flow.py:668-685` is untouched, per the brief's explicit out-of-scope note:
   "the no-progress/max_passes accounting beyond what falls out of the pre-apply"), split
   `pending` into "has a decision already → pre-apply it now" and "needs a session,"
   using the *exact* shape the brief's citation names as the peer to mirror
   (`flow.py:693-695`): `_isolate(d, ..., lambda: _apply_decision(cfg, d, by=by,
   today=today, apply_now=False))`. Only the second group is chunked into
   `leaves.run_signoff_batch`. Same `"blocked"` exception as above.

No new public/private symbol was added to `flow.py` — every change is inside an existing
function, calling only functions the module already imports (`leaves.signoff_decision`,
the existing `_apply_decision`). This matters for the brief's "Import modules, never new
symbols" instruction to the test: `test_signoff_orphan.py` only ever calls
`flow._drive_wave` / `flow._signoff_and_apply` / `flow._maybe_auto_iterate`, all of which
already existed pre-patch, so there is no `ImportError` risk on the red leg (confirmed —
see "Genuine red?" below, the red leg ran and failed normally, never errored).

## Why `_apply_decision` itself is untouched

`_apply_decision` (`flow.py:132-210`) already IS the deterministic record/transition the
brief says to reuse, not duplicate ("Peer to mirror" in Citations expected). It already
handles the C6 guard, the unrecordable-SUMMARY repair path, the `REASSEMBLE` sentinel, and
the `apply_now` semantics correctly. The defect was never in that function — it was that
none of the three callers ever checked for an *existing* decision before asking for a new
one. So the fix is entirely "read-before-ask," not a second transition path.

## Alternatives considered and ruled out

**A shared helper function, e.g. `_pre_apply_pending(cfg, d, ...)`, wrapping the
"check-then-apply" logic once.** I drafted this first, but ruled it out for two reasons:
(1) the brief's citation explicitly asks the pre-apply to use the *same*
`_isolate(d, ..., lambda: _apply_decision(...))` shape the post-session apply already
uses — introducing a wrapper function around that shape adds a layer of indirection the
citation doesn't ask for, and (2) `_signoff_and_apply` (single-issue) never uses
`_isolate` around its apply call (by design — see `_apply_decision`'s own docstring:
"the single-issue flow has no `_isolate` around this call"), while `_drive_wave` (batch)
always does; a single shared helper would either have to take an `isolate: bool` flag
(more surface area than three inlined `if leaves.signoff_decision(d):` checks) or drop the
isolation semantics one caller needs. Cost: the shared-helper version was ~10 lines
shorter in total but added one new function signature, one more thing for a reviewer to
trace through, and risked diverging from the cited peer shape. Inlining is the smaller
diff that stays closest to `flow.py:693-695`.

**Distinguishing every `_apply_decision` return value (`None` two different ways) for
`_drive_wave`'s `needing_session` split.** `_apply_decision` returns `None` both when there
was no decision to read AND (separately) when a decision existed but was dropped because
`SUMMARY.md` was missing (`flow.py:160-164`). I considered a three-way return (add a
distinct sentinel for "decision consumed but unrecordable") so the caller could tell those
apart. Ruled out: out of scope per the brief ("out of scope: ... changing what C6 blocks
or how §9 is written") — the missing-SUMMARY repair path is an existing edge case
unrelated to #453, and folding both into "needs a session in this pass" reproduces exactly
what the *pre-existing* code already did in that corner (a session always ran when nothing
valid was recorded), so behavior there is unchanged, not regressed.

## The three refutation questions

**(a) Genuine red?** Yes. With `template/src/pdca_harness/flow.py` reverted (`git stash`
on just that file) and the new test file in place, `cd template && PYTHONPATH=src python3
-m unittest tests.test_signoff_orphan -v` fails 3 of 4 tests (the C6-blocked-exception test
passes both before and after, since that behavior — a fresh session on a C6-refused accept
— is unchanged by this fix). The 3 failures are real assertion failures (`AssertionError:
Lists differ: [...] != []` — a session WAS opened) — not import errors, not collection
errors. Restoring the fix (`git stash pop`) makes all 4 pass. Verified twice more from a
completely clean `git worktree add /tmp/453_apply_check origin/main` + `git apply
patch.diff` (bypassing my working tree entirely) — clean apply, same 4/4 green.

**(b) Production path?** Yes. The test calls `flow._drive_wave`, `flow._signoff_and_apply`,
and `flow._maybe_auto_iterate` directly — the exact three functions the patch changes —
with all six leaves in `stub` mode (the project's own offline-driver convention, same
`_stub_config` shape as `template/tests/test_flow_slice.py:32-55`). No mock of
`_apply_decision`, `signoff.record`, or `state.state`; those run for real against a real
temp bundle directory with a real `SUMMARY.md` the stub Check assembled. The only things
monkeypatched are `leaves.run_signoff` / `leaves.run_signoff_batch` /
`assemble.collect_needs_human` — and only as *spies/tripwires* to prove they are (or, in
the C6-exception test, correctly aren't) called, never to fake the decision-application
logic itself.

**(c) Fixture includes the fault?** Yes. Each test drives a bundle through the real stub
Plan→Do→Check pipeline to a genuine `AWAITING_SIGNOFF` halt (`driver.run_issue`, not a
hand-built `SUMMARY.md`), then writes the orphaned `signoff-decision` file directly — the
exact artifact-on-disk state an interrupted `^C`'d session leaves per the brief's
mechanism (`flow.py:50-69`'s `_isolate` not containing `KeyboardInterrupt`). This is not a
curated-out fixture: the orphaned file is present and readable throughout, and the
pre-fix run's failure output shows the (would-be) stub session actually running and
writing over the file's rationale line — the exact bug reported.

## Runner used

`cd template && PYTHONPATH=src python3 -m unittest tests.test_signoff_orphan[.ClassName]`
and, for regression, `cd template && PYTHONPATH=src python3 -m unittest discover -s
tests` — both exactly as the brief's Falsifiability section names (`engine/scripts/
run-verify.sh` is an unfilled per-project skeleton in this repo, so there is no separate
wrapper to go through beyond the command the brief itself quotes as what it *would* run).
Full offline suite: 1595 tests, `OK (skipped=2)`, no regressions from this patch.

## Commit-readiness

No formatter/lint config exists at the target repo root (no `pyproject.toml`,
`.pre-commit-config.yaml`, or `ruff`/`black`/`flake8` invocation in `.github/workflows/*`
or `Makefile` at the repo root — the only `pyproject.toml.jinja` /
`Makefile` are scaffolding templates rendered *into* generated instances, not this repo's
own tooling). Line lengths in the diff (max 93 chars on an added line) are within the
file's existing range (many pre-existing lines run to 100-106 chars with the module's
em-dash-heavy prose style). `python3 -c "import ast; ast.parse(...)"` confirms both files
parse cleanly.

## Scope check against the brief's "out of scope" list

- Did not touch `VALID_DECISIONS` (`leaves.py:78`) or the decision grammar.
- Did not touch what C6 blocks or how §9 is written (`signoff.record`) — reused
  `_apply_decision` unmodified.
- Did not touch `_isolate`'s `KeyboardInterrupt` handling (`flow.py:56-58`) — still
  propagates, so `^C` still stops the run.
- Did not touch the no-progress/`max_passes` accounting beyond what the pre-apply causes
  to fall out naturally (an orphaned-then-applied bundle simply isn't in `needing_session`,
  so no chunk is ever built for it that pass — the existing "no progress" check at
  `flow.py:668-685`/old-numbering is untouched).
- Did not touch the interactive sign-off prompt (`_signoff_prompt` / `_signoff_batch_prompt`).
