<!-- pdca:split-proposal v1 -->
# Split proposal — issue 464

<!-- Hand-written in the Plan session, from the human's rulings of 2026-10-30. The splitter
     leaf is interactive and cannot get a terminal from inside this session. -->

## Why this slice is oversized

Four build rounds did not converge. Findings per round were 4, 4, 8 and 6, and the patch
grew from 45 KB to 137 KB. `sizing.json` found five separate outcomes. Three things were
being built as one:

1. Reporting a mistyped `wave_mode`. This is true of any value and needs no new mode.
2. The `"none"` mode for independent bundles: nothing happens at a wave boundary, and each
   accepted bundle has a draft PR against its real base.
3. Dependencies under `"none"`: holding a dependent until its prerequisite has merged.
   Most of the review findings were here.

Rulings from the human, 2026-10-30, which these children carry:

- The mistyped-value warning stays in this issue, as its own child.
- A chain waiting on a merge exits 3, with every link held.
- A prerequisite that can never land on the dependent's base is refused up front (exit 2),
  not held.
- The manual merge and re-run workflow is accepted. An older `publish.json` with no patch
  digest is trusted, with a one-line note saying its contents cannot be confirmed.

`"none"` does not become the default in any child. That remains a separate decision.

## Wave sketch

Fully serial, three waves, because the three really do build on each other:

- **Wave 1: child-1.** No dependency.
- **Wave 2: child-2**, `Depends on: child-1`. It adds `"none"` to the allowed values that
  child-1 creates.
- **Wave 3: child-3**, `Depends on: child-2`. It replaces child-2's up-front refusal with
  the hold and reads the publish record child-2 makes trustworthy.

Child-2 is safe to ship alone: it refuses any `"none"` batch with a dependency, so no
dependent can be built without its prerequisite's work.

Conflicts outside this split cannot be declared here, because ordering fields accept
sibling labels only. They are added to the child briefs once tracker ids exist; each
child's `Ordering note` names them.

<!-- pdca:child child-1 -->
- **Slug:** wave-mode-unknown-value-note
- **Kind:** bug
- **Defect / goal:** `Config.load` keeps any `[driver].wave_mode` value as given (`template/src/pdca_harness/config.py:733`). Every check compares against `"merge"`, so a typo behaves as `"stack"` with no message.
- **Success criterion:** `Config.load` with `wave_mode = "bogus"` prints one stderr line naming the bad value and the allowed values, and gives `cfg.wave_mode == "stack"`. `"stack"`, `"merge"` and an absent key print nothing and keep their value. `"Merge"` and a non-string value such as `1` count as unknown: they print the note, fall back to `"stack"`, and raise nothing. Matching stays exact on purpose, because today `"Merge"` does not enable merge mode, and folding case would start merging PRs for that instance.
- **Falsifiability:** RED offline with the plain unittest runner: today `cfg.wave_mode` is `"bogus"` and stderr is empty.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** Load a `pdca.toml` with `[driver] wave_mode = "bogus"`. Read `cfg.wave_mode` and stderr.
- **Scope (one logical fix) / out of scope:** Validating the value at load, and updating the comment at `config.py:733`. / out of scope: the `"none"` value; any change to what `"stack"` or `"merge"` do.
- **External dependencies:** none
- **Test file:** `template/tests/test_config_wave_mode.py` (new).
- **Citations expected:** path:line on main for every change. Peer callsite: validate as `merge_requires` does, `template/src/pdca_harness/config.py:738-742` (print a note, fall back), without its `.strip().lower()`.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log -i --grep=wave_mode origin/main` shows no validation of the value. `gh pr list --state closed --search "wave_mode none"` finds #619 and #484, neither of which validates it. Result: no prior art.
- **Surfaces:** data
- **Difficulty:** low
- **Disposition hint:** likely-fix
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** wave-mode-none-core
- **Kind:** enhancement
- **Defect / goal:** `wave_mode` has no value that does nothing at the wave boundary: `"stack"` folds onto a pushed integration line and `"merge"` readies and merges PRs nobody has looked at. Add `"none"`: each accepted bundle has a draft PR against its real target base, as in a single-bundle run. No integration line is created or pushed, and nothing is folded, readied or merged. The carry of finished ids (#646) does not run. Waves still set build order, including `Conflicts with` pairs, whose later member is built on the plain base. An accepted bundle left with no PR of its accepted work is never reported as a clean run, on the first run or a re-run.
- **Success criterion:** On the real-git fixture with `gh` stubbed and the publisher in `command` mode, under `wave_mode = "none"`: (a) independent A and C publish with `gh pr create --base <target base>`, no `pdca-integration/*` branch reaches origin, and neither `gh pr ready` nor `gh pr merge` is called; the run exits 0. (b) `Config.load` accepts `"none"` with no note. (c) A batch where any bundle declares `Depends on`, `Depends on (merged)` or `Stacks on` is refused before anything is built, exit 2, with a message naming the bundle, the edge, and `"stack"` or `"merge"` as the way out. (d) `pdca publish` of a bundle with a leftover `stack-base` file cuts from and opens its PR against the target base. (e) A bundle whose `gh pr create` fails exits 3 with hold kind `"no-pr"`, and so does the same command re-run, including `pdca flow <id> <new-id>`; it does not exit 0. The same holds for an iterated bundle whose texts fail, so its accepted rebuild is on no PR while the old PR still holds rejected work. (f) An iterated bundle whose old draft PR is still open keeps that PR in `publish.json` when `gh pr create` refuses a second one. (g) `pdca waves` under `"none"` prints `none mode` and not "each wave builds on the prior's accepted work". (h) A dry-run (stub publisher or `--no-publish`) asks no host and reports nothing about missing PRs. (i) `"stack"` and `"merge"` suites stay green.
- **Falsifiability:** RED on `StackFoldGit` (`template/tests/test_integrate_stack_bases.py:123`, bare `origin`, `gh` stubbed). Today `"none"` runs as stack mode, because the checks read `!= "merge"` (`flow.py:2888`, `:2901`; else-branch of `:3080`), so the fold pushes an integration line and leg (a) fails.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** Run two independent bundles under `wave_mode = "none"` over `StackFoldGit` and list origin's branches.
- **Scope (one logical fix) / out of scope:** The value end to end for dependency-free batches; the up-front refusal; a publish record that says whether it holds the accepted work, which means a patch digest in `publish.json`, and an older record with no digest is trusted with a one-line stderr note; the `pdca.toml.jinja` comment block (`:115-138`) and the `wave_mode` section of `docs/07-crosscutting.md` (`:644` onward). / out of scope: any dependency hold (child-3); making `"none"` the default; any change to `"stack"` or `"merge"` behaviour.
- **External dependencies:** none
- **Test file:** `template/tests/test_flow_wave_mode_none.py` (new). Import only modules (`from pdca_harness import cli, config, flow, integrate, publish, state`), never a symbol the change adds. Load `StackFoldGit` by file path as `template/tests/test_flow_same_wave_conflict.py:36-39` does, so the red leg fails on assertions and not on import. Because `template/pdca.toml.jinja` changes, Do also runs the root suites (`python3 -m unittest discover -s tests`, needs copier) per INTEGRATION §3.
- **Citations expected:** path:line on main for every change. Wave-boundary checks: `flow.py:2888` (`_carry_finished`), `:2901` (`hold_unmerged` / `own_bases`, both must be False so `_base_plans` / `_bundle_bases` do not run), `:3080` (fold or merge). Refuse as the merge-mode group check does, `waves.py:149` (strict) and `:379` (the tolerant path, which holds with the same reason); `DependencyGraphError` becomes exit 2 at `cli.py:673-679`. Exit rule: `cli._results_rc`, `cli.py:707`. Publish: `publish.py:238-251` (`wave_base`), `:429` (failed `gh pr create`), `_existing_pr` at `:580`. Terminal-bundle paths on a re-run: `flow.py:1739`, `:3459`. Summary line: `cli.py:1099-1100`. Drive the test like `template/tests/test_flow_same_wave_conflict.py`.
- **Prior-art check (triage cycles):** Searched `config.py`, `flow.py`, `publish.py`, `waves.py`, `cli.py` on `origin/main`: no third mode was ever added. #619 (merged) already opens stack-mode PRs against the real base, but still folds and pushes a line. Closed-unmerged PRs #638, #639, #648, #649, #598, #599, #600 were carried by #657/#615 and add no mode. Result: no prior art for the mode.
- **Ordering note:** Outside this split, conflicts with 654 and 626 (the carry gated at `flow.py:2888`), 839 and 840 (the merge branch at `:3080`), and 782 (the publish block before it). None is a build-on prerequisite.
- **Surfaces:** data
- **Difficulty:** high
- **Disposition hint:** new-feature
- **Depends on:** child-1
<!-- pdca:end child-2 -->

<!-- pdca:child child-3 -->
- **Slug:** wave-mode-none-dependency-hold
- **Kind:** enhancement
- **Defect / goal:** Under `"none"` a batch with dependencies is refused outright, so its independent part cannot run. Replace the refusal: a dependent is held until its prerequisite has merged into the dependent's own target base, for all three edge kinds, in the batch or out of it. The human merges and re-runs. A prerequisite that can never land on that base is refused up front, because no merge could release the hold.
- **Success criterion:** On the same fixture under `"none"`, with A and C independent and B dependent on A: (a) A and C publish, and B stays PLANNED with hold kind `"unmerged"`. One stderr line names A, B's base and the way out (merge the PR, re-run) and does not contain "line of this run" or "carries them". `pdca flow` exits 3. (b) Once A's PR reads MERGED and the fetched base has it, a re-run builds B from the base and publishes it against the base. (c) If A's PR reads MERGED but `origin/<base>` as fetched lacks it, B is still held and the run exits 3. (d) `Stacks on` and `Depends on (merged)` behave as (a) and (b). A `Stacks on` bundle is cut from and opened against the target base, and an archived merged parent in `completed/` releases it just as it does for `Depends on`. (e) In a chain A→B→C every waiting link is held as `"unmerged"` and the run exits 3, not 1; C's line names what it waits for. (f) A prerequisite on another repo or branch, one published with `Onto branch`, or a `Depends on (merged)` prerequisite with no target is refused before anything is built, exit 2, naming the edge and the reason, in both real runs and dry-runs. A plain `Depends on` prerequisite with no target counts as ready. (g) A prerequisite with no PR on record is not reported as waiting for a merge: the run exits 1 and says to publish it first. (h) If `gh` cannot read the PR state, the run exits 1 and says so; it does not report a normal hold. (i) A PR opened by hand and merged releases the dependent: when no PR is on record but a branch is, the host's answer for that branch counts. (j) An older record with no digest is trusted, with the note. (k) A dry-run asks no host and holds nothing, but (f) still refuses. (l) `"stack"` and `"merge"` suites stay green.
- **Falsifiability:** RED on `StackFoldGit`, `gh` stubbed. With child-2 on the base, the batch in leg (a) is refused with exit 2, so B is never held and A is never published.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** Run A and B (`Depends on: A`) under `wave_mode = "none"` over `StackFoldGit`.
- **Scope (one logical fix) / out of scope:** The hold, its exit code, the release, the can-never-land refusal, and `Stacks on` under `"none"`; the matching lines in `pdca.toml.jinja` and `docs/07-crosscutting.md`. / out of scope: letting some bundles stack inside a `"none"` run; making `"none"` the default; any change to `"stack"` or `"merge"` behaviour.
- **External dependencies:** none
- **Test file:** `template/tests/test_flow_wave_mode_none_hold.py` (new). Same import and fixture rules as `template/tests/test_flow_wave_mode_none.py`. Because `template/pdca.toml.jinja` changes, Do also runs the root suites per INTEGRATION §3.
- **Citations expected:** path:line on main for every change, re-resolved on the fold of child-2. Peer callsites: `flow._runnable` at `flow.py:786-841`, whose out-of-batch hold is the model but does not cover an in-batch prerequisite; the `line is None` skip at `:807-809`, which must not bypass `_base_lacks_merge`; `merged.merged_into` at `merged.py:72` and `pr_state` to tell unreadable from OPEN; `cli._results_rc` at `cli.py:707`, where only `_BASE_HOLD` counts as held before built; `waves.py:111` and `:370`, the `Stacks on` lookup; `waves.py:149` and `:379`, the refusal; `publish.py:238` and the `pr_base` line, plus `_stacks_on_branch` at `publish.py:762`, with its other callers `worktree.py:96` and `drift.py:67`; `integrate.unpublished` at `integrate.py:255` for what counts as having no target.
- **Prior-art check (triage cycles):** Searched `flow.py`, `merged.py`, `waves.py`, `publish.py`, `cli.py` on `origin/main`. #647 and #729 hold out-of-batch prerequisites in stack mode, and #738 adds the `"base"` hold; these are the code to extend. Nothing holds an in-batch prerequisite on a merge. Result: no prior art for this hold.
- **Ordering note:** Outside this split, conflicts with 654, 626, 839 and 840 (`flow._runnable` and the wave-boundary checks) and 782.
- **Surfaces:** data
- **Difficulty:** high
- **Disposition hint:** new-feature
- **Depends on:** child-2
<!-- pdca:end child-3 -->
