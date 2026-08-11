# Build notes — issue 453 / apply-orphaned-signoff-decision

> Withheld from the reviewer (independence contract, `template/src/pdca_harness/leaves.py:65-68`).
> For the human at Check sign-off.

Target: `eduralph/pdca-harness` @ `main`, worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`
at `b95aa58`. Pre-fix citations are that base; post-fix citations are the patched file.

---

## 1. What the change is

One invariant, restored in one place and routed to from the three sites that used to
violate it: **a decision recorded durably in a bundle is un-consumed *input* to the driver**,
so every path that is about to *ask* for a decision must first *read* the one already on
disk, and the driver must never overwrite a decision it did not author
(`template/src/pdca_harness/state.py:1-6`).

| # | Site (pre-fix, `b95aa58`) | Change (post-fix line) |
|---|---|---|
| 1 | — | **new** `UNDECIDED` sentinel + `_apply_recorded_decision()` — the single read-before-asking implementation (`flow.py:213-248`) |
| 2 | `flow.py:213-218` `_signoff_and_apply` runs the leaf unconditionally | routes through #1 first; only `UNDECIDED` or `"blocked"` still opens a session (`flow.py:251-261`) |
| 3 | `flow.py:241-242` / `:271` `_maybe_auto_iterate` → unconditional `autoiterate.write_decision` | declines, loudly, while a decision is un-consumed — before any classification, so no budget is spent either (`flow.py:286-295`) |
| 4 | `flow.py:686-695` `_drive_wave` chunks **`pending`** straight into sessions | pre-applies every already-decided bundle first, then chunks only `needing_session` (`flow.py:741-758`) |

Shape decisions, and why:

- **Reuse `_apply_decision` (`flow.py:132-210`), never a second transition path.** Every
  pre-apply goes through the same C6 accept-guard, the same `signoff.record` §9 author, the
  same rationale capture and the same `signoff-decision` unlink as a post-session apply.
  Nothing about *how* a decision is recorded changed — only *when the driver reads it*.
- **Same peer shape in the wave** as the post-session apply the brief names
  (`flow.py:693-695` pre-fix): `_isolate(d, …, lambda: _apply_decision(…, apply_now=False))`.
  Deferred (`apply_now=False`) so an `iterate-do` doesn't rebuild mid-review; isolated so one
  bad bundle can't kill the sweep. Single-issue keeps `apply_now=True` (`flow.py:257`).
- **Tri-state, not a boolean.** `UNDECIDED` (`flow.py:219`) is deliberately distinct from
  `None` and `REASSEMBLE`: those two mean a decision *was* on disk but the bundle was
  repaired/downgraded (its SUMMARY was moved aside), so re-asking would ask about an
  artifact that no longer exists. Only `UNDECIDED` and `"blocked"` still owe a session —
  `"blocked"` being the brief's one exception (C6 refused an accept, §6 still open, the human
  genuinely must come back).
- **A pre-apply that *raises*** is `_isolate`'s `None` → the bundle is loudly skipped for
  that pass (`_isolate` names it and the state it was left in, `flow.py:60-69`), exactly like
  the post-session apply, rather than being handed a session over a decision the driver could
  not read. Handing it a session was the alternative; it risks the very clobber this issue is
  about, and it can double-record if the raise happened *after* `signoff.record` succeeded.
- **Never silent:** each apply-without-a-session prints the bundle **and** the action
  (`flow.py:246-247`); each auto-iterate decline prints the bundle and why
  (`flow.py:293-294`). Both are asserted by the test.

Out of scope and untouched, as the brief requires: `VALID_DECISIONS` (`leaves.py:78`), what
C6 blocks / how §9 is written (`signoff.record`), `_isolate`'s `KeyboardInterrupt` contract
(`flow.py:56-58` — the `^C` must still stop the run), the interactive prompt, and the
no-progress/`max_passes` accounting beyond what falls out of the pre-apply (a wave whose
bundles are all already-decided now transitions them on the pass that finds them, so the
`pending`-empty no-progress exit is reached the ordinary way).

## 2. Alternatives, with their cost

- **Guard the symptom instead — make `_drive_wave`'s no-progress exit fire when `pending`
  is non-empty but unchanged** (`flow.py:668-685` pre-fix). ~6 lines, the cheapest diff by
  far, and *wrong*: the wave would merely stop re-presenting the bundle sooner. The decision
  on disk is still never read, §9 is still unrecorded, the human's call is still lost on the
  next run, and auto-iterate can still clobber it. The brief names an **Invariant to
  restore**, so the target is the smallest change that restores it, not the smallest diff
  (`docs/principles.md` §1.2, §2) — a guard that leaves the file unread restores nothing.
- **Fix only `_drive_wave`** (the site the instance report hit). 7 executable lines instead
  of ~21. Fails the Success criterion outright: `flow._signoff_and_apply` (`pdca flow <id>`,
  the single-issue resume a human runs after a `^C`) and `_maybe_auto_iterate` are named in
  it explicitly. The remaining 14 lines are 3 in `_signoff_and_apply`, 5 in the auto-iterate
  guard, 6 in the shared helper.
- **Contain `KeyboardInterrupt` in `_isolate`** so the decision is applied before the run
  dies. Explicitly out of scope, and wrong: the `^C` must stop the run (`flow.py:56-58`).
  It also fixes nothing for a `kill`, a crash, or a dropped SSH session — the file is still
  orphaned; only *reading* it on the next pass makes the bundle resumable.
- **Inline the read at each of the two drive paths** (no shared helper — the shape of the
  previous two iterations). Same behaviour, but it writes the same announce f-string twice
  and re-derives the "`blocked` ⇒ fall through, everything else ⇒ don't ask" rule in each
  caller (12 + 15 added lines there vs. 6 + 3 + 7 here). Since the invariant is *"every path
  that is about to ask must first read"*, one implementation of it is the honest expression:
  two copies can drift when `_apply_decision` grows a new return case — which it did once
  already (`REASSEMBLE`, #330).

## 3. Carry-forward from iterations 1 and 2 — both items answered with evidence

Neither round rejected the *approach*: Check returned C1–C5, T1, T2, T5 all PASS on the
patch (`iteration-v2/check-review.md:5-14`). Both auto-iterate rounds were spent on two
**environment/process** rows the reviewer emitted, which no change to `flow.py` can clear.
They are answered here so the human can close them in seconds rather than burn round 3.

**T3 Runtime — "`copier` is absent, so the root suite reported green while executing 0 of 7
tests".** That is true of the *reviewer's own sandbox*, not of the gate. The T3 gate runs
the suites under the instance venv (`engine/scripts/run-suite.sh:14-15`,
`PY="$(pwd)/.venv/bin/python3"`), where `copier` **is** importable — and that is not
incidental, `pdca.toml:809-814` already registers it as a `required = true` doctor row for
exactly this failure mode. Verified twice:

- `.venv/bin/python3 -c 'import copier'` → `copier 9.17.0` (bare `python3` → ImportError,
  which is what the reviewer saw).
- This iteration's own full run, `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh`:
  `== T3: template-repo suite (render + update-compat) … Ran 7 tests in 20.605s … OK` —
  seven tests *executed*, zero skipped (the only `skipped=2` in the log belongs to the
  driver suite and is pre-existing), then `Ran 1599 tests … OK (skipped=2)` for the offline
  driver suite, verdict `== T3: root suite OK, driver suite OK`.
- The frozen iteration-2 gate log says the same: `gate-logs/T3-suite.log:1-20` — `Ran 7
  tests in 21.333s / OK`, each render/update-compat case listed `ok`.

So the render + update-compat coverage *did* run against this patch, including
`test_render_then_slice` (renders the template and runs the rendered instance). No
`NEEDS-HUMAN external dependency` marker is emitted for `copier`: it is present, it is
registered, and nothing was blocked — emitting one would manufacture a false §6 item. What
*is* real is that the **reviewer** cannot reproduce the gate because its sandbox has no
`.venv`; that is a process gap for Act (§10 candidate below), not a defect in this patch.
Re-check at sign-off: `PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l0 ./engine/scripts/run-suite.sh`.

**T4 Contribution — "`commit-msg.txt`, `pr-description.md` and the checker are outside the
permitted reviewer inputs, so the claims could not be independently reproduced".** Correct,
and structurally so, for two independent reasons — neither specific to this bundle:

1. `REVIEWER_INPUTS = ["patch.diff", "brief.md", "check-gates.json"]`
   (`template/src/pdca_harness/leaves.py:68`) — by design, the reviewer never sees publish
   artifacts.
2. More to the point, **at Check time those artifacts do not exist yet.** The gate is
   `./scripts/pdca contribcheck` (`pdca.toml:975`), and its first act after finding a patch
   is `if not pr_path.is_file(): return 0  # artifacts not drafted yet (Check-time gate,
   pre-publish) — nothing to lint` (`src/pdca_harness/cli.py:1034-1036`). The frozen T4 PASS
   is therefore a *default-open* pass on **every** bundle in this instance; there is no
   tracker-id or user-impact claim behind it to rely on. The real lint happens once publish
   drafts `commit-msg.txt` / `pr-description.md` (`cli.py:1037-1055`).

The honest disposition for the human: T4 carries no evidence either way at this point in the
cycle, and cannot, until publish has drafted the artifacts.

## 4. Refuting my own test (forced, recorded)

Run through the project's own runner — `./engine/scripts/run-verify.sh` with `$PDCA_BUNDLE`
/ `$PDCA_WORKTREE` set (the configured C4 gate; it reverts only the production hunks,
`--exclude=template/tests/*`, and keeps the test).

- **(a) Genuine red?** **Yes**, and mechanically, not by assertion. Green leg:
  `Ran 8 tests in 0.016s / OK`. Red leg (production hunks reverted, test kept):
  `Ran 8 tests / FAILED (failures=6)` — `DriveWave.test_applies_orphaned_decision_without_a_session`,
  `DriveWave.test_only_the_undecided_bundle_of_a_wave_is_offered_a_session`,
  `DriveWave.test_orphaned_accept_reaches_complete_without_a_session`,
  `SignoffAndApply.test_applies_orphaned_decision_without_a_session`,
  `SignoffAndApply.test_flow_completes_an_orphaned_accept_without_reopening_signoff`,
  `AutoIterate.test_declines_while_a_human_decision_is_unconsumed`. Verdict line:
  `C4 PASS: red without the fix, green with it`. The two that stay green on the red leg are
  the two C6-refusal tests — they assert a session *is* opened, which is correct on both
  legs; they pin the brief's exception, not the defect.
  A sample red message shows the real-world harm in words: *"a fresh sign-off session was
  opened for a bundle that already carried a decision on disk; §9 now records 'merged-wider'"*
  — i.e. pre-fix the bundle records the stub session's `accept` where the human wrote
  `iterate-do`.
- **(b) Production path?** **Yes.** The test imports modules only
  (`from pdca_harness import assemble, autoiterate, driver, flow, leaves, signoff, state`) and
  calls the production functions this patch changes: `flow._drive_wave`,
  `flow._signoff_and_apply`, `flow._maybe_auto_iterate`, and the public entry `flow.flow`.
  Bundles are produced by production code too — `flow._plan_if_unplanned` +
  `driver.run_issue` with the shipped stub leaves — so §6, the gate rows and the SUMMARY are
  the real assembled artifacts, and §9 is written by the real `signoff.record`. The only
  substitution is the *interactive model session* itself (`leaves.run_signoff` /
  `run_signoff_batch`), which is the standard offline idiom in this suite
  (`template/tests/test_flow_slice.py:82-91`) and is precisely the thing under test: whether
  it gets invoked at all. No helper this patch adds is imported by name (a
  `from …flow import _apply_recorded_decision` would make the red leg an ImportError → exit
  77 PDCA-UNVERIFIABLE, not a red).
- **(c) Fixture includes the fault?** **Yes**, and it reproduces the damage rather than
  curating it out. The fixture is a genuinely halted `AWAITING_SIGNOFF` bundle carrying the
  orphaned `signoff-decision` file — the failing element itself — with §9 unrecorded. Each
  session spy *does what the real stub session does* (`_session_writes_accept`, mirroring
  `leaves._stub_signoff`, `leaves.py:2974-2980`): clears §6 and writes its own `accept` over
  the human's decision, so on the red leg the clobber actually happens and the assertions see
  it. The auto-iterate case injects a real `- NEEDS-HUMAN [impl] —` advisory finding and
  asserts `autoiterate.eligible(...)` is True *before* driving, so the bundle is genuinely
  auto-iterable and the pre-fix run really does overwrite the human's `accept` and spend a
  budget round — no mocked classifier verdict.

## 5. Full-suite state

`./engine/scripts/run-suite.sh` on the patched worktree: root suite `Ran 7 … OK`, offline
driver suite `Ran 1599 tests … OK (skipped=2)` (1591 before + the 8 new). `compileall` clean,
`git diff --check` clean. The target has no formatter/linter hook (no ruff/black/pre-commit
config; its CI is docs-lint, render-check and require-linked-issue) — the render-check
equivalent is the root suite above, which passed against the working tree. Commit style for
publish: conventional prefix + `git commit -s` (DCO), `Fixes #453`.

## 6. Act candidates

- The **reviewer sandbox lacks the instance venv**, so any gate whose command resolves
  `.venv/bin/python3` (`run-suite.sh:14`, `run-verify.sh:29`) is un-reproducible for the
  reviewer, which reliably yields a T3 NEEDS-HUMAN row. Two frozen cycles' auto-iterate
  budget was spent on that row alone here.
- The **T4 contribution row is default-open before publish** (`cli.py:1034-1036`), so its
  Check-time PASS is evidence-free on every bundle; a reviewer that notices this must emit
  NEEDS-HUMAN. Either scope the row post-publish or label the pre-publish pass as
  "not applicable yet" so it cannot be read as a claim.
