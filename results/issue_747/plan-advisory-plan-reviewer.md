Bash was unavailable in this run (every command failed with `apply-seccomp: write /proc/self/setgroups … Permission denied`); this review was done with Read, Grep and Glob only.

# Plan review — hold-a-single-partner-cross-wave-clash-at-the-line-fold

- NEEDS-HUMAN — **The thread could not be checked: there is no `notes.json` or `sources/` in the bundle.** The only input present is `brief.md`. So none of these can be verified against the tracker: the problem statement, the "human's decisions at the #725 re-plan (2026-10-17, decisions 2-4)", the "#739 iteration-v4 split decision" (Invariant line), and the prior-art claims about `iteration-v1/patch.diff` and `_held_on_line`. Before sign-off, a human should confirm the thread backs rule (a)-(e). In particular, check that someone decided "partners fully explain the clash" (rule e) rather than "any partner conflicts".

- NEEDS-HUMAN — **None of the brief's anchors match the target source.** The brief says "`path:line` anchors are on `9f7c446` (the line tip with #738 folded)". The `$PDCA_TARGET` I was given is a different tree:
  - `_held_by` is at `integrate.py:1261`, not `:1747`.
  - `_clash` is at `:1288`, not `:1774`.
  - `_partners` is at `:1335`, not `:1821`.
  - The fold's conflict branch / `_held_by` call is at `integrate.py:609-615`, not `:640-647` / `:644`.
  - `_carry_finished` is at `flow.py:1091`, not `:1356`.
  - `_announce_conflict_holds` is at `flow.py:1250`, not `:1532`.
  - The fold block and `STOPPING` are at `flow.py:2638-2652`, not `:2991-2997`.
  - `cli._results_rc` is at `cli.py:701`, not `:707`.
  - `StackFoldGit` (`test_integrate_stack_bases.py:123`) and the spec-load in `test_flow_same_wave_conflict.py:36-39` do match.

  The target has no reference to #738 at all (grep `#738` → no matches). So "`held_conflict`, as extended by #738" cannot be grounded. If Do builds on `9f7c446`, the brief needs a target that actually contains #738's work. Otherwise the planner grounded the brief on a tree nobody can check here.

- NEEDS-HUMAN — **The brief gives three different line ranges for the flow's fold block.** Scope says "in the fold block (`:2862-2879`)". Citations say "the flow's fold block (`flow.py:2980-2999`)". Defect says `STOPPING` is at "`flow.py:2991-2997`". On one commit these cannot all be the same block. Do will be told to edit at one range and to mirror at another. Pin a single range, or pin a function and comment instead.

- NEEDS-HUMAN — **Case (2) needs a change to the fold API, which the brief puts out of scope.** The brief scopes "the fold API (#723)" out, but case (2) cannot be met without new plumbing:
  - Carried finished bundles never reach the in-run fold. It is called with `[d for d in accepted …]` (`flow.py:2640-2645`), and `accepted` only grows by each wave's `complete` (`flow.py:2604`).
  - `_carry_finished` records no head that the in-run fold receives. Its docstring says "the carry passes none" for `carried` (`flow.py:930-933`).
  - `fold` / `_fold_lines` have no parameter for "finished heads on the line" (`integrate.py:327-338`, `flow.py:913-923`).

  So "add the carried finished heads to the partner set" means one of two things:
  - **A new kwarg on `fold` / `_fold_lines`.** That is the fold API.
  - **Passing F into the in-run fold's bundle list.** Then F lands in `took` and `carried.update(took)` (`integrate.py:691-692`). That newly puts F under the #633/#695 rewrite checks, a behaviour change the brief doesn't mention.

  The brief should name which route, and accept the extra change it brings.

- NEEDS-HUMAN — **Case (4)'s negative assertion conflicts with the scope.** Case (4) requires the output "does NOT contain `Conflicts with: 10`". But every hold in `held_conflict` gets a second line at the end of the run from `_report_conflict_holds` (`flow.py:1263-1272`, called at `:2681`), built from `_CONFLICT_STEP = "declare \`Conflicts with: {ids}\` …"` (`flow.py:1004-1005`). The existing tests assert on the whole stderr (`self.err`, e.g. `test_flow_same_wave_conflict.py:362-366, 411`). So either:
  - the assertion is limited to "its stderr line" (then say so, because a reviewer can't check it otherwise), or
  - `_report_conflict_holds` / `_CONFLICT_STEP` must change too. Scope lists only `_announce_conflict_holds`.

  The same gap affects cases (1) and (2). The existing announce line hard-codes "merged before it in the same wave {k}" (`flow.py:1257-1258`), which is false for a cross-wave partner. The brief gives no wording for the non-prerequisite cross-wave advice, so cases (1) and (2) check only the partner name, and the advice text goes unverified.

- NEEDS-HUMAN — **Case (2)'s fixture is underspecified, and may land in case (4)'s wording.** `_carry_finished` only carries a finished id when "a drive-set bundle's plain `Depends on` names one the fold can carry" (`flow.py:1096-1098`). If F is carried because Y declares `Depends on: F`, then F is Y's own prerequisite, and the brief's partner-is-a-prerequisite wording (case 4) applies, not a plain hold. The brief should name which bundle depends on F, and which advice case (2) expects.

- NEEDS-HUMAN — **Rule (e) is not defined when a remaining line bundle was built on a partner.** "base + the line *without* them + the head merges cleanly" does not say how to build "the line without them" when another bundle on the line was cut from a partner's branch, and so carries its commits. `_partners` already deals with exactly this through `under` / `_built_on` (`integrate.py:1340-1358`). Rule (e) as written would put the partner's commits back, fail, and stop. That is safe, but it is an extra stop the brief doesn't list, and child-2 will inherit the ambiguity. State whether (e) replays bundle heads, or uses `under`.

- NEEDS-HUMAN — **"Depends on" is undeclared even though the brief relies on #738's work.** The brief has no `Depends on` / `Stacks on` field and there is no `dependency-state.json`. Yet the Ordering note says this child builds on #738's accepted work folded at `9f7c446`, and edits the same held sets and `_runnable` call. If #738's state changes (re-opened, re-folded), nothing records this child's dependence on it. Declare it, or confirm the run's line is pinned.

Attempted to fault the root cause too. The stated defect is consistent with the target: the in-run fold passes no `skipped`, so any conflict `_held_by` rejects is re-raised (`integrate.py:609-618`) and printed as `STOPPING` (`flow.py:2646-2652`). The flip test it names exists as described (`test_flow_same_wave_conflict.py:351-366`). Rule (b) is consistent with the base-taken-in-mid-wave stop guard (`:399-412`).

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
