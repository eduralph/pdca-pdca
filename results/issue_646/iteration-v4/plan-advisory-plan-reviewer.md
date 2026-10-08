Bash was unavailable in this run (`apply-seccomp: ... Permission denied`); review done with Read/Grep/Glob only.

# Plan advisory — plan-reviewer (stack-reissue-continues-batch-line, child 1 of #616)

- NEEDS-HUMAN — **The declared target is not the code the brief was written against, and the success criterion can't run there.** The brief says `Repo + branch target: eduralph/pdca-harness @ main` (brief:87), but it says its own line numbers come from `origin/pdca-integration/main @ f594d8e` and that "#591's batch-scoped line name is REQUIRED by this fix and exists only there until PR #639 merges" (brief:4-7). The target checkout I was given (`$PDCA_TARGET`) is the `main` shape, and it lacks everything the criterion calls:
  - `_drive_and_act` has no `batch=` keyword (`flow.py:1743-1754`).
  - `integrate.integration_branch(cfg, base)` takes no id list (`integrate.py:62`), yet criterion (1) calls `integration_branch(cfg, "main", ["P","D"])`.
  - `fold` has no `batch=` either (`integrate.py:219-221`), yet the brief cites `fold(…, batch=run_batch)`.
  - `flow.py` is 2289 lines long, but the brief cites `flow.py:2320-2325` and `:2357-2363`. The in-run fold it cites at `:2052-2081` is really at `flow.py:1983-2007`.

  On `main`, both the red and the green leg of `test_flow_resume_stack_prereqs` would fail with a `TypeError` at the call site, not on an assertion. C4 can't tell red from green, which breaks the brief's own rule "Import modules only… so the red leg fails rather than erroring" (brief:135-136). The "Ordering note" says there is no declared edge on #591 because the run's integration line carries it (brief:88-90). That holds only if this bundle is driven in the same run as #639/#591. Nothing declares that, and no `dependency-state.json` was provided to check it. Either retarget the brief to the integration line or a #639 base, or declare the prerequisite. Otherwise the bundle is stranded if it is driven on its own.

- NEEDS-HUMAN — **The rewording it plans breaks existing tests that the brief doesn't list.** The scope rewrites the "resuming across runs is #616" text at `publish.py:345`, `:696` and `:726` (brief:114-115). Existing tests check that text word for word:
  - `test_integrate_stack_bases.py:842` asserts `"#616"` and `"re-drive it in a new run"` in the late-publish refusal.
  - `:850` and `:915` assert `"#616"`.

  Do will have to edit those tests, and C4 keeps `tests/*.py`. That is review surface the brief never mentions. Also, `drift.py:58-61` states the same cross-run limit ("replaced by a later run's first fold. A known cross-run limit (#616)") and is not in the docs/docstring update list, so it would be left stale once the line is kept.

- NEEDS-HUMAN — **The problem statement can't be checked against the tracker.** The bundle has no `notes.json` and no `sources/` directory; the cwd holds only `brief.md`. I can't confirm that the #616 thread frames the defect as "re-issued `pdca flow <ids>` builds a dependent without its finished prerequisite". I also can't check the claim that iterations v1-v3 were rejected for "fresh line + carry of any out-of-batch prerequisite" (brief:158-159), or whether a maintainer constraint came with that rejection. The human should confirm the thread before sign-off. The code side does support the hazard: the `_runnable` docstring says so at `flow.py:692-698`, and the out-of-batch COMPLETE acceptance is at `flow.py:706-711`.

- NEEDS-HUMAN — **Hidden second behaviour change: unrelated bundles get rebased onto the carried line.** The scope points "every same-target runnable wave-0 bundle — including an unrelated `U`" at the carried line, and accepts that "its PR shows the carried changes until they merge" (brief:103-106). That changes how bundles with no dependency on `P` are published. Today such a bundle's wave-0 stack base is cleared (`flow.py:736-742`). None of criteria (1)-(7) covers `U`'s PR diff, so it is unreviewed. Only (4) mentions `U`, and only to say it builds. Either justify it as part of the one fix or make it a criterion.

- NEEDS-HUMAN — **New PR-state hold policy is close to a second change.** Criteria (4b)-(4d) add new gating logic:
  - comparing the `publish.json` mtime against `SUMMARY.md`;
  - querying the host for CLOSED vs OPEN PR state;
  - treating an unreadable state as a hold.

  None of this exists for in-run prerequisites, so it goes beyond "carry the finished ids onto the line". (4b) relies on file mtimes, which `cp`/`git checkout`/archive moves (`completed/`, #171) can reorder, so the hold could fire or stay silent for reasons unrelated to the defect. Consider moving (4b)-(4d) into their own child, or narrowing them to (4a), which mirrors the existing `held_unpushed` path.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.
