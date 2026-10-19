# Adversarial review — issue_738 (iteration 6)

Line numbers are on the patched tree at `$PDCA_TARGET`.

## The evidence: could not refute

- **Red→green holds up.** I re-ran the green leg: `tests.test_flow_bundle_base_holds` gives 16 OK. `gate-logs/C4-verify.log` shows the red leg: 14 of 16 fail. Each of the 14 fails for the expected reason (`STOPPING` printed at B's base before W/S/X is built, or W's `reset` never reached). The 2 that pass on both legs are the planned keep-behaviour guards: case (8) `_reset_tree`, and sign-off item 3's `_LineBroken`. The `_LineBroken` guard still catches a patch that leaves `_LineBroken` out of the re-raise tuple at `flow.py:1050`: B would then be held and the test's `STOPPING` / "no issue_B held" assertions would fail.
- **The tests run production code, not a copy.** They drive `flow._drive_and_act` on the real `StackFoldGit` fixture. Each fault is injected at an `integrate._git` call (fetch, push, reset, `checkout -B`, the `_trial` checkout) or on disk, and only while `build_bundle_base` runs for one bundle. So integrate's own raise fires with its own words (e.g. `integrate.py:2046-2048` for the fetch). No stub touches the new `except` at `flow.py:1047-1054`.
- **No exit codes changed in the existing suites.** The edits to `test_flow_dependency_scoped_bases.py` and `test_integrate_carried_rewrite_late.py` turn `STOPPING` assertions into hold assertions and add `"base"` keys to the holds maps. Every rc they assert is still 1, and the iteration-v4 flip at `:317` is not reintroduced.

## The fix: what I attacked

- **I could not break these:**
  - The fetch fix appears only for a fetch cause. The `could not fetch ` prefix in `_BASE_HOLD_STEPS` (`flow.py:1080`) matches only `_fetch`'s `cause=`; nothing else in the build path uses that prefix.
  - A clash hold leaves the shared worktree mid-merge on B's base branch, but every later build and fold resets the tree first (`integrate.py:855`, `:598`, `:677`). My probe (case 1 plus a wave-2 `V`) built W normally after B's hold.
  - Two holds in one wave give two lines, the wave is skipped with no fold, and the exit code is 3 (probe).
  - A fold after a rewrite hold still checks `fix/A` even if W fails its drive: `accepted` still holds A, so `integrate.py:501` does not return early and `_carried_tips` runs (`integrate.py:533`). So the "next fold" warning is true whenever it prints on the normal path.
- **Note (out of scope, #739):** probe = case (1) plus `V` (`Depends on: W`) in wave 2. The fold after wave 1 stops with `issue_W's branch origin/fix/W does not merge cleanly onto pdca-integration/main-… (conflicts in a.txt)`. The cause: W's own base was built from the moved `main`, so W's branch carries `main`'s new `a.txt` onto a line that already has A's. So in any run with a later wave, a moved-main hold buys only the rest of the current wave, and B's hold line (`flow.py:1129-1131`) gives no warning (the warning exists only for `_Rewritten`). The brief's Scope assigns "a moved base stranding a line bundle at a later fold" to #739. This is not a defect in this diff; I record it so #739 starts from a concrete repro.
- **Note (low):** the exemption at `cli.py:741-742` passes a `"base"`-held key in *any* state. The brief only describes a PLANNED one, and the new docstring says "(PLANNED, for one not built yet)". `flow_ids` drives every non-terminal id (`flow.py:3320-3360`), so a bundle that is already BUILT, CHECKED or AWAITING_SIGNOFF from an earlier run, whose base then fails, now gives 3 instead of the batch rule's 1. It is hard to reach (the bundle's in-batch prerequisite has to reach COMPLETE during this run), and the human already kept this mechanism at the v5 sign-off, so I am not raising it as an item.
- NEEDS-HUMAN [human] — The "next fold stops the run" warning is decided before the wave drives. `fold_next` is computed at `flow.py:2885-2888`, before `_drive_wave` (`:2897`) and `_adopt_split_children` (`:2905`). Adoption can replace `wave_list[k + 1:]` (`flow.py:2262`), and the fold reads `len(wave_list)` live at `flow.py:2954`. So the comment at `:2885-2886` ("the fold below reads `k < len(wave_list) - 1` the same way") is wrong whenever adoption runs, and `flow.py:2768-2772` warns against exactly this cached count. Two failing cases:
  - **No warning, but the run stops.** B (`Depends on: A`, `fix/A` rewritten) and W are in the **last** wave, so B's line warns of no fold. W splits during its drive, and its children are spliced in as a new wave. The fold after this wave now runs, `_carried_tips` refuses `fix/A`, and the run prints `STOPPING`. B's line never said a fold would come.
  - **Warning, but no fold runs.** Wave k is not last, and its only later bundle is `V` (`Depends on: B`). W splits, but `_reschedule` holds all of its children. It also holds V, because B is neither in the schedulable set nor COMPLETE (`waves.py:283-289`). The tail becomes `[]` and no fold runs, yet B's line said "the next fold stops the run". That is the false promise sign-off item 1 set out to remove.
  
  The same gap exists without a split. When a whole wave is held, `flow.py:2889-2890` skips its fold. A later wave can still have runnable bundles, through a `Conflicts with` edge to a bundle `_runnable` only *skipped* (not held), and that later wave's fold stops on the rewrite with no warning. These cases are rare. The line has to print before the drive to be useful, so it can never fully predict adoption. Since the sign-off said "no other changes", a human should decide whether this is acceptable or whether a follow-up line belongs at the fold.

## The verdict

- `check-gates.json` claims nothing beyond what the logs show. C2 is "no gate configured", so the red proof rests on C4 alone, and C4's red leg is solid. T4 is deferred to publish, not passed. I found no claim the gates or brief overstate, apart from the `fold_next` comment above.

Attempted to refute: the red→green proof, whether the tests run production code, the fetch-only fix wording, worktree state after a held clash, a fold after a rewrite hold, two holds in one wave, partner holds, and the existing-suite exit codes. Could not refute any of them. One timing edge in the "next fold" warning, raised above for the human.

<!-- pdca:leaf-complete -->
