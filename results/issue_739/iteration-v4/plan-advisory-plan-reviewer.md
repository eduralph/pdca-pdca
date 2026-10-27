Bash was unavailable in this run (every command failed with `apply-seccomp: write /proc/self/setgroups … Permission denied`); this review used Read, Grep and Glob only.

# Plan review — hold-a-cross-wave-clash-at-the-line-fold (Depends on #738)

- NEEDS-HUMAN — **The tracker record is missing, so the problem statement can't be checked against it.** The cwd has only `brief.md` and `dependency-state.json`. There is no `notes.json` and no `sources/`. The brief rests on "the human's decisions at the #725 re-plan (2026-10-17, decisions 2-4)" and on `results/issue_725/iteration-v1/SUMMARY.md` §6/§9. That file is not in the bundle, and Glob finds no `results/issue_725/**` under `$PDCA_TARGET` either. Three things depend on that record: (a) the flip of a test that #674 deliberately named "still stops the run", (b) exit 1 rather than 3, and (c) "Bases are not pinned to the run's start". None of the three can be traced to the thread. The human should confirm the decisions are recorded where Check can read them.

- NEEDS-HUMAN — **Prerequisite #738 is PLANNED, but the brief treats it as accepted.** `dependency-state.json`: `"738": {"exists": true, "state": "PLANNED"}`. The brief says: "Do builds and the gate verifies on … `pdca-integration/main-r547f8028520f` with #738's accepted work folded on top". The Falsifiability line adds "Case (3) needs #738 on the base (otherwise the run stops earlier…)". Until #738 is accepted and folded, there is no verify base that can turn case (3) green. Both bundles also edit the same `_runnable`/held-set call (`flow.py:2497-2502` on the target). The bundle will strand at Do or Check unless #738 lands first. Otherwise case (3) needs an explicit fallback.

- NEEDS-HUMAN — **The line anchors don't match the target, and the brief contradicts itself on one of them.** The target's HEAD is `2ff8f3b`, not `75a886e`. Where things are on the target:
  - `_held_by` at `integrate.py:1261` (brief: `:1743`).
  - The "all of kept" naming at `:1285` (brief: `:1766`).
  - `_clash` at `:1288` and `_partners` at `:1335` (brief: `:1770` and `:1817`).
  - The `held_out` call in `fold` at `:609-615` (brief: `:640`).
  - The fold block in flow at `flow.py:2638-2652` (brief: `:2862-2879`).
  - `_carry_finished` at `:1091` (brief: `:1259`) and `_announce_conflict_holds` at `:1250` (brief: `:1435`).

  The brief also cites the same test at two lines. Defect says `test_flow_same_wave_conflict.py:399` and criterion (5) says `:413`. The target has it at `:399`, and the earlier-wave test at `:351`, not `:365`. Line 10 says "re-check them on the folded tip", but the criterion pins tests by line number. Pin them by test name only, and state which commit the anchors are on.

- NEEDS-HUMAN — **The path-ownership rule contradicts the case it must keep as a stop.** The rule: "every conflicting path is owned by a bundle branch already on the line". In `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run` (`test_flow_same_wave_conflict.py:378-409`), 22 conflicts in `shared.txt`. 20 is on the line and also changes `shared.txt` (`:380`), so 20 "owns" that path. A literal per-path rule would therefore hold 22 and blame 20. The test comment at `:401-403` says exactly that must not happen: "Holding it would blame 20 and propose a wrong `Conflicts with: 20`". #674 decides by trial merges, not by path ownership (`_held_by`, `integrate.py:1279-1285`). The rule should be restated as a trial-merge test, e.g. `_clash` returning `"batch"`. As written, Do may implement it by paths and flip case (5).

- NEEDS-HUMAN — **"Reuse `_partners`" can't produce the "together" case (4) as specified.** `_partners` (`integrate.py:1349-1360`) names a bundle only when `head` conflicts with `base + that bundle alone` (`at != 1: continue`). If the clash happens only with several bundles together, it returns `{}`. `_clash` then falls through to `"line"`/`"moved"`/`"off"` (`:1320-1328`), and those name no bundle. The "all of kept" fallback the brief cites exists only in `_held_by` (`:1285`). So "Reuse `_clash` / `_partners` rather than adding a second classifier" and case (4) pull in opposite directions. The brief should say which function gets the "together" fallback, and that changing `_clash`'s contract also changes its #694 caller, the pre-wave carry (`_clash` docstring, `:1291-1295`).

- NEEDS-HUMAN — **The flipped test (5) doesn't fit the brief's own wording rule.** The target `:351-366`: 21 has `Depends on: 10` (`:357`) and is cut from `origin/main` (`:359`), so it clashes with 10 on the line. The brief flips it to "21 held and named with `issue_10`". But 10 is 21's own prerequisite, and #674's hold proposes a `Conflicts with` partner. Two things are unclear: whether 21 is told to declare `Conflicts with: 10` against its own dependency, and whether 21 is told to rebuild on 10's line. Case (3) forbids "blame W / tell W's owner to update its branch" for a bundle cut from main. 21 is in exactly that position, but the brief gives no expected wording for it. Specify the stderr text for this flip, or the reviewer can't tell right from wrong.

- NEEDS-HUMAN — **The scope holds more than one fix.** The single "one logical fix" covers five things:
  1. Classifying cross-wave in-batch clashes.
  2. Adding carried finished heads to the partner set (hole 2).
  3. A new "stranded by a moved base" kind, with its own message aimed at the *partner's* owner (hole 3).
  4. A "together" fallback in the shared classifier.
  5. "Bases are not pinned to the run's start", which reads as a behavior requirement but has no test or code location.

  Items 2 and 3 are the separate holes that the iteration-v1 summary lists separately. With difficulty marked high, either split item 3 out, or make item 5 a stated non-change (an assertion only).

- NEEDS-HUMAN — **"The exit code" isn't something `flow._drive_and_act` returns.** It returns `results` and fills `holds` (`flow.py:2694-2698`). The exit code comes from `cli._results_rc(results, holds=…)` (`cli.py:701-731`). Holds alone give 3, and a non-terminal bundle such as a PLANNED dependent gives 1. The criterion should say the tests compute the code through `cli._results_rc`, and should give the expected code for each case. Case (1)'s U is COMPLETE, but whether Y's dependents stay PLANNED (rc 1) or Y is the only one held (rc 3) isn't stated per case.

Root cause checked and confirmed: `fold` holds only when `ours and kept` (same wave) and `_held_by` returns a clash (`integrate.py:609-615`). Anything else raises into `flow.py:2646-2652`, which prints `STOPPING`. That matches the brief's defect.

> **pdca:** Bash was unavailable to this reviewer. The vendor sandbox could not start on this host, so every Bash call it made failed before running (`apply-seccomp: write /proc/self/setgroups (nested userns is capability-restricted; caller must provide CAP_SYS_ADMIN): Permission denied`) and it ran no commands; this review was delivered without Bash.

<!-- pdca:leaf-complete -->
