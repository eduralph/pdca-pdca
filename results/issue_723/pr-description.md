## Summary
**User impact:** when a run accepts several fixes for the same target, the harness can only stack them all on one shared branch. A fix that depends on just one or two of the others still ends up built on top of every accepted fix, so its pull request carries (or is tested against) work it has nothing to do with, and there is no way to build it on only what it needs.

This PR adds the building block for that: a function that builds one fix's own base branch from exactly the fixes it depends on, and refuses rather than quietly pulling in anything else. Nothing calls it yet; #724 wires it into the run, and #725 updates the docs.

Reported in [#723](https://github.com/eduralph/pdca-harness/issues/723).

## What to look at
- The new function `build_bundle_base` in `integrate.py`, and its helpers right below it. The run's existing fold is untouched.
- The refusal rule: after merging the chosen fixes, every new commit must belong to one of them. A fix's "own" commits are counted from the point its branch was cut from, as recorded when it was published. If that record is missing or doesn't match the branch, the build refuses and says which fix to re-publish. This means some odd old histories are refused even when they might be fine; that trade-off is deliberate.
- To try it: `cd template && PYTHONPATH=src python3 -m unittest tests.test_integrate_bundle_base` (26 tests, offline, real git).

## Root cause
`integrate.fold` picks its own destination with `integration_branch(cfg, base, batch)` (`template/src/pdca_harness/integrate.py:126`) and folds every accepted bundle of a target onto that one branch (`fold`, `:327` onward). There was no way to name a different destination or to limit which bundles go on it.

## Fix
All changes are in `template/src/pdca_harness/integrate.py`, plus one new test file. `fold`'s body is not edited; the new code calls the module-level helpers `fold` already uses.

- `bundle_base_branch` (new `:145`): the branch name, `integration_branch(...) + "-b" + _flatten_base(<id>)`. `_flatten_base` only ever emits `-h` / `-s`, so `-b` decodes to one (base, batch, bundle). The name has no `/` after `pdca-integration/`, so it is never a ref-path prefix of, or nested under, the line or another bundle's base.
- `build_bundle_base(cfg, d, members, *, batch, carried, excluded) -> (branch, tip)` (new `:716`):
  - takes the same per-target lock and worktree as a fold (`integ_lock`, `_prepare_worktree`, base `:280`, `:538`, `:1565`) and always starts fresh from `<base_remote>/<base>` as fetched;
  - reads each member's tip once and checks it against `carried` with `_carried_rewrite` (base `:739`) before anything is merged;
  - merges each member with `_merge_published` (base `:810`), so a gone branch goes through `_gone_branch` (base `:882`) and every clean merge through the revert check;
  - turns a merge conflict into a clear message (`_member_clash`, new `:929`): a clash with the base names `<remote>/<base>` and says to rebuild the member's branch on it; a clash between two members names both and the files;
  - pushes plainly when origin has no such branch, otherwise `--force-with-lease`; a refused push names the branch and the remedy (delete it on origin, or allow force-pushes on `pdca-integration/*`).
- Ownership (`_member_cut_point` new `:862`, `_unowned_work` new `:963`, `_foreign_refusal` new `:983`): a member's cut point is its recorded `stack-base-tip` (`publish.read_stack_base_tip`, `publish.py:690`) when it has a `stack-base` record (`publish.read_stack_base`, `publish.py:679`), else none. Own work is `rev-list --no-merges <head> --not <base> [<cut>]`, the same shape as `foreign_commit` (base `:252`). Any other non-merge commit on the result raises before the push, naming the commit, the member whose branch brings it in, and any excluded bundle whose head holds it, or saying no bundle of the run owns it. `excluded` only names culprits; it never decides a refusal. No `pdca-integration/*` ref is read to judge ownership.
- Fail-closed cases, each naming the member and "re-publish": a `stack-base` with no tip; a tip that is not an ancestor of the head; an `Onto branch` member (`_published_ref`, base `:195`); no `stack-base` but `publish.json` says `"mode": "stacked-pr"` (`publish.py:429`) or the brief declares `Stacks on:`.

**Note for the caller (#724):** `build_bundle_base` takes the same `integ_lock` that `fold` holds. Calling it from the same process while that lock is held through a re-gate (the `locks=` window) would deadlock, because the file lock is per open file. It also leaves the shared worktree checked out on the bundle-base branch. So a caller must call it outside that window (or add a way to reuse the held lock) and restore the line checkout before re-gating.

## Verification
"base `:N`" is a line on `main` (`2ff8f3b89ec53dfbd00c01345c784f32dcaf38ce`); "new `:N`" is a line after the patch. Test lines are in `template/tests/test_integrate_bundle_base.py`.

| Claim | Where it is checked | Test |
|---|---|---|
| The branch holds every commit of the members, none of an outsider, starts from the fetched base, and leaves the run's line and its recorded tip alone | new `:827`–`:858` | `test_a_bundle_base_holds_exactly…` (`:167`) |
| The name is exactly the line + `-b<id>`, has no extra `/`, and ids `12`, `1-2`, `1/2` give three names | new `:145`; `integration_branch` / `_flatten_base` unchanged (base `:126`, `:154`) | `:194` |
| Create is a plain push, rebuild is a forced push, a refused push names branch and remedy | new `:847`–`:858`, mirrors base `:681`–`:690` | `:225`, `:242` |
| Clashes are refused with the right message (base vs. member); a gone member is judged as the fold judges it | new `:832`–`:841`, `:929`–`:960`; `_gone_branch` base `:882` | `:257`, `:266`, `:281`, `:294` |
| A member bringing in a revert of earlier work is refused on a fresh base | `_keep_merge` base `:850`, via `_merge_published` | `:313` (goes red when the revert check is stubbed out) |
| A rewritten carried member is refused, nothing pushed | new `:811`–`:821`; `_carried_rewrite` base `:739` | `:345` |
| Work that is no member's own is refused (outsider's work under the cut point; base rebuilt; outsider's branch fast-forwarded; work nobody owns) | new `:842`–`:846`, `:963`–`:1022` | 6a–6d, `:360`–`:408` |
| Untrusted cut points fail closed (no tip; tip not in branch; `Onto branch`; stacked with no record, by `publish.json` or `Stacks on:`) | new `:862`–`:925` | 6e i–iv-b, `:421`–`:476` |
| Legitimate builds are not refused (outsider cut from the line after the member; base and topic merged into a member by hand; member stacked on another member's bundle base) | new `:963`–`:980` | 6f–6h, `:494`–`:520` |

- **Red without the fix:** with the production change reverted, all 26 tests load, run, and fail with `AttributeError: … no attribute 'build_bundle_base'` inside the test body. With the patch, all 26 pass.
- **Red without the safety checks:** with only the ownership check stubbed out, 11 refusal tests fail with `IntegrationError not raised` (6a–6e, plus two extra ownership cases). With only the cut-point trust checks stubbed out, each 6e case fails the same way. With `stack-base` detected only through `read_stack_base_tip`, 6e(i) fails on its message. The must-not-raise cases stay green throughout.
- **Nothing else changed:** the full offline suite passes, 2552 tests (the existing 2526 plus these 26), including every `test_integrate_*.py` and `test_flow_*.py` unchanged.

Fixes #723
