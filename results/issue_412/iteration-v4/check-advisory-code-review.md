# Advisory code review — issue 412 (merge-mode atomic merge group), round 4

Scope: the source changes in `patch.diff`, read on the patched tree at `$PDCA_TARGET`. Gates: C4 is red before the fix (37 of 41 tests fail) and green after it. T3 runs 2671 tests and passes. I found no new correctness bug that I could pin to a failing case. The round-3 findings are dealt with in code:
- Conflict build order now comes from one shared helper, `_build_order`, at `waves.py:478`.
- The `_member` copy is gone; `merge.py` now uses `waves.member_path`.
- `_merge_one`'s checks before readying a PR now live in one function, `_premerge`, at `merge.py:642`.
- The "already merged" vs. "no repo" order matches `_merge_one` again.

What remains are small cleanups and one scope question.

## Findings

- `template/src/pdca_harness/merge.py:245` and `template/src/pdca_harness/merge.py:729` — when a group is released, each member runs `_premerge` twice. Once is ahead of time, from `group_blocker`; the second is inside `_merge_one`. Each run makes a `merged.is_merged` call, which is a `gh pr view` round trip. So every group member costs one extra `gh` call at the boundary, and `_report_groups` adds one more per member at the end of the run. Nothing breaks, because the answers agree. If it matters, `merge_wave` could keep the `_premerge` verdicts that `group_blocker` already computed. Advisory only.
- `template/src/pdca_harness/waves.py:198` — `merge_groups` globs every `issue_*` folder under `results/` and `results/completed/` and reads each brief, every time it is called. In merge mode it is called by every `check_dep_graph` (so every `compute_waves`) and by `partition_schedulable` (`waves.py:667`). In `_drive_and_act` it runs at the start of every wave (`flow.py:3026`), at every boundary (`flow.py:3186`) and once at the end (`flow.py:3270`). The cost grows with waves × all bundles ever on disk, and most of those are archived ones that never change. That is fine at today's sizes, and stack mode never calls it. Reading it once per run, and again only after a split adds bundles, would be enough. Advisory only.
- `template/src/pdca_harness/flow.py:3002` and `template/src/pdca_harness/merge.py:272` — both new hunks contain the same "target, or `("", "")` when the brief is gone" expression: `publish._resolve_target(p)[:2] if (p / "brief.md").is_file() else ("", "")`. A small shared helper, for example next to `waves.member_path`, would stop the two copies drifting apart, which is the same kind of drift the round-3 `_member` finding was about. Advisory only.
- `template/src/pdca_harness/waves.py:198` with `template/src/pdca_harness/waves.py:295` — NEEDS-HUMAN [human] — `merge_groups` reads every brief on disk, archived ones included. A `Merges with: A` line in any bundle that ended DISCONTINUED or RESOLVED therefore stops every later merge-mode run that includes A, up front, with rc 2, and that lasts forever. The remedy text says to "remove the `Merges with` edge … in whichever brief declares it", which means editing a frozen, possibly archived bundle. The same applies to `_ring_refusal` (`waves.py`, the "if …'s PR has already merged, remove the `Merges with` edge" remedy). The up-front check cannot ask `gh` whether an archived member's PR has merged, so it refuses a ring through a long-merged member, and the only way out it offers is editing that member's brief. This follows on purpose from the round-2/3 fix (a one-sided declaration must keep binding), and success criterion (b) wants a DISCONTINUED member to hold its group. But how long an old declaration should keep binding (forever, or only while the declarer is in flight or unmerged) is a scope decision for the maintainer, not a builder fix.

The diff has no other correctness or reuse problems that I could confirm.

<!-- pdca:leaf-complete -->
