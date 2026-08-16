# Brief — issue 497 / single-id-rc-and-stdout-already-agree

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** single-id-rc-and-stdout-already-agree
- **Defect:** As reported: `pdca flow <id>` could print `COMPLETE` and exit **1**, naming
  nothing that failed — `_report_single` printed only `results[iid]` while deriving the exit code
  from the **whole** results map, which since split adoption also carries children the single-id
  report never mentioned. An operator, or `pdca flow 500 && …` automation, read a success line
  and got a failure code with no way from stdout to learn which bundle caused it.
  **Verified against the target base: this defect is already fixed on `origin/main`, and the
  issue can be closed.** It was resolved by the #473 slice (PR #479, `flow: recover stranded
  split children; fund and report adopted waves`, merged 2026-08-10, commit `389bf1a`), which
  took the second of the two options the issue itself named — "keep the whole-map rc and report
  the adopted children on stdout now":
  * `cli._report_single` (`template/src/pdca_harness/cli.py:659-692`) now prints the named id
    first and then **every other entry in the map** in the identical `state<TAB>path` shape via
    `_report_entry` (`:644-657`), before returning `_results_rc(results, …)`. Its docstring names
    the exact failure this issue reports, including the recovery shape where the named id's
    `COMPLETE` was written by an earlier run.
  * Printing is unconditional, not failure-gated — deliberately, because a single-id run counts
    `AWAITING_SIGNOFF` as a successful end (`_results_rc`, `:630-641`), so a child waiting for
    the human would otherwise be invisible at rc 0.
  * The behaviour is pinned by three cases in `template/tests/test_flow_adopt_recovery.py`:
    `test_the_single_id_stdout_names_the_adopted_bundle_that_failed_the_run` (`:598`, asserts
    rc 1 **and** the full three-line stdout),
    `test_a_recovery_run_never_reports_an_earlier_runs_success_as_its_own` (`:620`),
    `test_stdout_names_an_adopted_child_left_waiting_for_the_human` (`:640`, the rc-0 shape, §6
    items included), with
    `test_a_single_id_run_that_adopts_nothing_still_prints_exactly_one_line` (`:667`) keeping the
    ordinary one-line contract. **Run at Plan on the current base:**
    `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery` →
    `Ran 14 tests … OK`.
  The asymmetry the issue notes in passing — a **held** child leaves the run at rc 0 while an
  **adopted but unfinished** child makes it rc 1 — is now an explicit, uniformly applied rule
  rather than an accident: a child the run could not schedule is dropped from the results map
  and named on stderr with a resume hint, so the run neither claims it nor counts it
  (`test_flow_adopt_split.py:885-935`, "the run reports the work it did and nothing else"), while
  a bundle the run **drove** and left un-terminal does count. That is a coherent contract, it is
  documented where it is implemented, and both hold shapes were deliberately made to agree. If
  the human wants "this run created work it could not finish" to be a single verdict across both
  shapes, that is a **new** slice with a design decision in it — not this bug.
- **Success criterion:** At sign-off the human confirms, against `origin/main` of
  eduralph/pdca-harness, that (a) `_report_single` reports every entry of the results map in the
  documented `state<TAB>path` shape, (b) the exit code and stdout therefore answer for the same
  set of bundles, and (c) the three pinning cases above pass — and closes the tracker issue as
  fixed by PR #479 / `389bf1a`, recording the held-versus-adopted rc contract as intended
  behaviour rather than a residual defect. No patch is produced by this cycle.
- **Falsifiability:** The claim being tested here is "the reported defect is absent on the target
  base", and it is falsifiable in one offline command on the base toolchain — no network, no
  services: `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery -v`.
  If `_report_single` still printed only the named id, `:598` and `:620` — which assert the
  **whole** stdout list, not a membership test — would fail. They pass (14/14 at Plan). The
  reproduction the issue gives (`pdca flow 500 --max-passes 3`, 500 splitting into 601/602 with
  the pool stopping before 602's wave) is the very scenario those cases construct, and #473 also
  re-sized the pool so an adopted wave is funded (`test_flow_adopt_split.py:440-461`).
  This bundle takes the **close fast path** (`[driver].close_dispositions`, docs 04): the builder
  and reviewer leaves are skipped, no `patch.diff` exists, and the gates are N/A — which is the
  correct shape for a verification-only close and not a gap in the evidence.
- **Invariant to restore:** None — nothing is broken on the target base. The invariant the
  original defect violated ("a run's machine-readable stdout must answer for exactly the set of
  bundles its exit code is derived from") holds today, and is documented at its implementation
  (`cli.py:659-692`) and pinned by the three cases named above.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves, and a
  wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds. It is also
  moot here — a close-disposition bundle produces no patch, so it can collide with nothing. Note
  for the run plan: this id was listed there as a fix needing an rc-scoping decision at Plan;
  the decision was made upstream by #473 before this run, so it lands as a close instead and
  `cli.py` is untouched by this run.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Confirm the fix on the target base and close the tracker issue with the evidence
  above. **Out of scope:** any code change (the code is correct); re-litigating the
  held-versus-adopted rc contract, which is a separate design slice if the human wants it;
  `_results_rc`'s single-id `AWAITING_SIGNOFF` allowance (#468, deliberate); the stdout contract
  for bundles the run never drove.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline:
  1. `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery -v` →
     `Ran 14 tests … OK`, including `:598`, `:620`, `:640`, `:667`.
  2. Read `template/src/pdca_harness/cli.py:659-692` — the docstring names this exact defect
     ("Reporting only `iid` then printed `COMPLETE` while exiting 1"), and the body prints
     `_report_entry` for the named id and then for every other key before returning
     `_results_rc(results, ok=(*_FLOW_OK, state.AWAITING_SIGNOFF))`.
  3. `git -C <target> log --oneline origin/main -- template/src/pdca_harness/cli.py` → `389bf1a`
     (PR #479, issue #473) is the commit that changed it; `git show 389bf1a` shows the report
     loop and the new cases arriving together.
- **External dependencies:** none — the confirmation is one offline unittest run on the base
  toolchain.
- **Test file:** none — this is a verification-only close: the behaviour is already pinned by
  `template/tests/test_flow_adopt_recovery.py:598`, `:620`, `:640` and `:667`, and adding a
  fourth copy of the same assertion would be duplication, not coverage.
- **Citations expected:** not applicable (no change is produced). The evidence a reviewer or the
  human should re-check is: `template/src/pdca_harness/cli.py:644-692`,
  `template/tests/test_flow_adopt_recovery.py:598-692`,
  `template/tests/test_flow_adopt_split.py:885-935` (the held-child contract), and commit
  `389bf1a` / PR #479.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/cli.py` — `a2eefe1`, `389bf1a` (PR #479, **the fix**), `96c9704`,
  `4814b3d` (#468, the one results map both shapes report from). `gh pr list -R
  eduralph/pdca-harness --state open` → **no open PRs**. Closed/merged: #479 (issue #473) and
  #470 (#468) are the two relevant slices, both merged before this run. The issue itself is
  still OPEN on the tracker, which is the only thing this cycle changes.
- **Disposition hint:** likely-close

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
