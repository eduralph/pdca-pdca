## Summary
**User impact:** In a stacked run, if the base for one fix could not be built, the whole
run stopped. Every fix still waiting was left unbuilt, even ones with no link to the
failure. Common triggers are ordinary: `main` moved and now clashes with a prerequisite,
someone force-pushed a prerequisite's branch, a fetch failed, or origin refused a push.
One bad fix blocked the whole batch until the user sorted it out and re-ran.

This PR holds back only the fix whose base failed, plus the fixes that depend on it or
conflict with it. The rest of the run goes on. Each hold prints one line that says what
went wrong and how to fix it.

Reported in [#738](https://github.com/eduralph/pdca-harness/issues/738).

## What to look at
- **What happens on a failure now.** The fix is held. A fix that depends on it is
  skipped. A fix tied to it by `Conflicts with` is held with its own line. Everything
  else in that wave is built and published as usual.
- **The hold line.** It names the cause and a fix that fits that cause: "rebuild
  issue_A's branch on the new origin/main", the restore or re-publish step for a
  rewritten branch, or "check the remote … then re-run" for a failed fetch only. If the
  cause is a rewritten prerequisite and a fold still follows this wave, the line also
  warns that the next fold will stop the run unless the branch is restored first.
- **What still stops the run, on purpose.** A shared integration worktree that cannot be
  reset, a branch that cannot be put back after a trial merge, and a rewritten
  prerequisite at the next fold. If some fix in the same wave was already held, its line
  is printed before the stop line, so its cause is not lost.
- **Exit codes.** Only holds left: 3. A skipped dependent or held partner left unbuilt:
  1. A rewritten prerequisite the line still carries at the end: 1, as today.

To try it, run the new test module (all real git, offline):

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_bundle_base_holds
```

This builds on #727, #728 and #729 (fixes get a base of their own), which are on the
branch it was built and tested on.

## Root cause
`_bundle_bases` re-raised every `IntegrationError` from `integrate.build_bundle_base`,
and the wave loop turned any of them into `STOPPING`. There was no hold for a bundle
whose own base failed, so a per-bundle problem acted like a run-level one.

## Fix
- `flow._bundle_bases` catches the base failure for one bundle and records it in a
  `held` map (whose base, the error). Only `IntegrationTreeError` and `_LineBroken`
  still re-raise; the wave loop's `STOPPING` handler now covers just those two, and
  first prints the lines for bundles already held in that wave.
- New `_BASE_HOLD_STEPS` / `_base_hold_why` pick the fix text from the error's `cause`.
  The fetch fix is given only for a fetch failure. `integrate.py`'s message text is
  unchanged, since the fold and the carry share it.
- New `_announce_base_holds` prints one stderr line per hold. The "next fold stops the
  run" warning is given only when something of the wave is still left to build and a
  later wave remains, which is when a fold really follows.
- `_runnable` gets an `unbuilt` set (the base-held bundles), used for prerequisites and
  `Conflicts with` partners the same way unpushed holds are.
- `stop_named` is gone. The end-of-run rewrite check now sees every accepted bundle, so
  a hold never hides a rewritten prerequisite from it.
- `cli._results_rc`: new `_BASE_HOLD = "base"` reason. A PLANNED bundle passes rule 1
  only if `holds` maps it to `"base"`. Docstring and `_RC_HELD` comment updated.
- `integrate._Rewritten`: docstring only.
- Two existing tests that pinned the old stop now assert the hold. No expected exit code
  changed.

Known limit: the "next fold" warning is decided before the wave builds. If a bundle in
that wave splits and the rest of the schedule is re-levelled, the warning can end up
missing or wrong. The run still stops at the fold with today's message. This is rare
and left for a follow-up.

## Verification
Line numbers are on the branch this was built on (`main` plus #723, #727, #728, #729),
with this patch.

- **Claim:** a base failure holds only that bundle; the rest of the wave completes.
  - **Checked:** `template/src/pdca_harness/flow.py:1047-1054`: any other
    `IntegrationError` goes into `held`; only `IntegrationTreeError` / `_LineBroken`
    re-raise. `flow.py:2883-2890`: held bundles are taken out of `runnable`, then
    announced.
  - **Test:** `template/tests/test_flow_bundle_base_holds.py`: moved base, failed fetch,
    refused push, missing checkout, worktree not made, git step failed. Each asserts B
    held, W COMPLETE, no `STOPPING`, exit 3.
- **Claim:** each hold line names the cause and a fix that fits it.
  - **Checked:** `flow.py:1079-1098` (`_BASE_HOLD_STEPS`, `_base_hold_why`),
    `flow.py:1101-1131` (`_announce_base_holds`).
  - **Test:** same file. The fetch case asserts `fetch` and `re-run` and no "rebuild";
    the push case keeps `could not push` plus the branch name and asserts no
    `check the remote`.
- **Claim:** dependents are skipped and `Conflicts with` partners are held.
  - **Checked:** `flow.py:759-779`, `:864-869` (`_runnable` with `unbuilt`),
    `flow.py:2805-2820` (`held_base` passed in).
  - **Test:** the partner case and the dependent case: each stays PLANNED, exit 1.
- **Claim:** a rewritten prerequisite holds its dependent, warns of the next fold only
  when a fold follows, and still fails the run at the end.
  - **Checked:** `flow.py:2888` (`fold_next=bool(runnable) and k < len(wave_list) - 1`),
    `flow.py:3047` (`"base"` holds written before the late `"rewritten"` ones).
  - **Test:** rewrite on the last wave (holds `A: "rewritten"`, exit 1); rewrite mended
    before the run ends (exit 3); rewrite before the last wave (warns `next fold` and
    `restore`, the fold stops the run, exit 1); rewrite with nothing left in the wave
    (no warning, only one fold); a PR stacked on the rewritten prerequisite is named by
    the end-of-run check.
- **Claim:** a broken shared worktree or a branch that cannot be put back still stops
  the run, and any hold already made in that wave is named first.
  - **Checked:** `flow.py:2877-2882`.
  - **Test:** worktree reset fails (`STOPPING` is the base line, B not held); branch not
    put back after a trial merge (`STOPPING`, holds empty); fetch fails for B, then W's
    reset fails (B's line with `could not fetch` comes before W's `STOPPING`).
- **Claim:** exit codes follow the contract above.
  - **Checked:** `template/src/pdca_harness/cli.py:699` (`_BASE_HOLD`),
    `cli.py:741-746` (rule-1 exemption for `"base"` only).
  - **Test:** every case computes `cli._results_rc(results, holds=holds)` and asserts
    the code.
- **Red/green:** with the production change reverted, 14 of the new file's 16 tests
  fail (each stops with `STOPPING` at B's base). The other two are the deliberate
  keep-behaviour guards (worktree reset, branch not put back), which pass both ways.
- **Full suite:** root suite 24 tests OK; driver suite 2610 tests OK (2 skipped).
  `test_flow_dependency_scoped_bases`, `test_integrate_carried_rewrite_late` and the
  other bundle-base, conflict and hold-exit-code suites pass with no expected exit code
  changed.

Fixes #738
