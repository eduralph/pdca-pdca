Bash was unavailable in this run (every command failed with `apply-seccomp: write /proc/self/setgroups ... Permission denied`); this review used Read, Grep and Glob only.

# Plan review — flow-builds-each-bundle-on-its-declared-prerequisites

The defect itself holds up against the source. `_point_at_integration` (`flow.py:890-910`) writes the run's one integration branch into every runnable bundle's `stack-base` (`flow.py:906-908`), whatever that bundle declares. My findings are about the prerequisite, the criterion and the grounding, not about the root cause.

- NEEDS-HUMAN — **The tracker record is missing, so the problem statement can't be checked against the thread.** The cwd holds only `brief.md` and `dependency-state.json`. There is no `notes.json` and no `sources/`. The Invariant cites "#630's finding (the comment on #463, 2026-10-10)". The Repro cites "the #630 test from the issue comment". Prior-art cites `iteration-v1/patch.diff` and says the review "reproduced" (7) and (8) against it. None of these is in the inputs, so neither this review nor Check can confirm that (7) and (8) are what that review asked for. Either attach the thread and the v1 review, or quote the load-bearing lines in the brief.

- NEEDS-HUMAN — **`Depends on: 723` points at a bundle that isn't built, and the brief treats its code as already on the base.** `dependency-state.json` says `"723": {"exists": true, "state": "PLANNED"}`. On the target there is no per-bundle base-build function: `integrate.py`'s top-level defs (`:99`–`:980`) contain none, and no file under `template/` mentions `723`. Yet the Falsifiability line says "with the production change reverted (#723's code stays, it is on the base) it loads and fails on assertions". The Scope says "a base built by #723's function", never naming that function. Against `main` as it stands (`Repo + branch target: eduralph/pdca-harness @ main`), Do would be calling an API that doesn't exist yet, and the red→green claim can't be tested. Options: gate this bundle on 723 reaching accepted/merged; or name the exact function and signature 723 must provide and the base this bundle builds on (723's branch versus `main`); or make the dependency a stack edge.

- NEEDS-HUMAN — **The brief's anchors are from a different tree than the target.** The target worktree HEAD is `d6057ebc8c9b`, but the brief keeps saying "On `489e5fb`". Several cited lines don't match the target:
  - `_point_at_integration` is called at `flow.py:2442`, not `:2549`.
  - `_carry_finished` is at `flow.py:1032`, not `:1091`.
  - `_finished_named` is at `flow.py:954`, not `:963`.
  - `integrate._fold_candidates` is at `integrate.py:190`, not `:217`.
  - The wave loop cited as `flow.py:2600-2670` falls inside `flow_batch` (`def` at `:2579`) on this target. `_drive_and_act`'s loop is around `:2216-2578`.

  The `publish.py`, `merged.py` and `_runnable`/`_line_lacks_merge` anchors do match. Do is told to "cite path:line on the target branch for every change". The brief should state which base it was written against: 489e5fb, presumably carrying 693–695, or `main`. Then re-anchor.

- NEEDS-HUMAN — **Criterion (10) names suites that don't exist on the target, so as written it can't be checked.** These are absent from `template/tests/`:
  - `test_flow_reissue_after_conflict_hold.py`
  - `test_flow_hold_exit_code.py`
  - `test_integrate_carried_rewrite_late.py`

  Only the other six exist. "#723's test" has no file name at all. These are presumably from 693/694/695 ("Accepted in this run"), which are not on `main`. That ties into the base question above. Either name the base that carries them or drop them from (10), and give #723's test a path.

- NEEDS-HUMAN — **Criteria (7) and (8) depend on behaviour that belongs to the unbuilt prerequisite, and don't say what "reports" means.** "the run reports the foreign ancestry naming `P` and `X`" and "the run reports the rewrite naming `P`" don't say where (stderr, exit code, a bundle record) or which message. Scope says the failure comes "with the error #723 raises". So whether (7) and (8) pass is decided by 723's error text and exit behaviour, which aren't fixed anywhere in this brief. Pin the observable: for example, the run exits non-zero before the wave, D's state stays unbuilt, and the error text contains `P` and `X`. Otherwise the test can be made to pass loosely.

- NEEDS-HUMAN — **The #655 rework is a second change bundled in.** Scope removes `_line_lacks_merge` (`flow.py:850`, called at `:792`) and `merged.merge_and_head` (`merged.py:149`), rewrites docstrings `merged.py:24` and `:188`, and flips the existing #655 hold tests (criterion 9). It is causally linked: once D isn't cut from the line, asking whether the line lacks P's merge is the wrong question. But it changes hold behaviour for every bundle ("by `merged.merged_into` alone for every bundle"), including bundles whose closure is empty. Meanwhile the brief defers every other doc and docstring change to #725, so deleting this code and editing these docstrings here is inconsistent with that deferral. The human should decide explicitly whether #655's flip belongs in this child or a sibling.

I tried to fault the root cause and could not: the source confirms it at `flow.py:904-910`.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
