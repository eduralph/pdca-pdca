# Adversarial review — issue 593 (stack-mode append-only fold, real-base PRs)

Advisory only. Sources: the patched tree at `$PDCA_TARGET`, `brief.md`, `check-gates.json`, `gate-logs/`.
I re-ran the green leg myself: `tests.test_integrate_stack_bases` and `tests.test_integrate` give 54 tests, all OK.
The red leg in `gate-logs/C4-verify.log` matches the brief. One refutation landed. The other attacks failed (listed at the end).

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/integrate.py:457-475` (`_take_in_base`), reached from `:436-445` (`_gone_branch`).
  When a gone branch's merged head is not on the line, the fold merges `<base_remote>/<base>` into the line and prints "the merged work reaches … through origin/main". It never checks that the base actually holds that head, even when the head is in the clone and the check costs one `merge-base --is-ancestor`. The only guard is the base string in `publish.json` (`:437`), which the host can change after publish.
  **Reproduced** (scratch test, real git, FoldGit shape):
  1. Fold A.
  2. Push a fixup onto fix/A.
  3. Merge fix/A with `--no-ff` into `release` instead of `main` (for example, the PR's base was edited on the host), then delete fix/A.
  4. Have `merged_head` return the fixup SHA, then fold [A, B] with `{TARGET: T1}`.

  Result: the fold succeeds and prints the "reaches … through origin/main" line, but the line's `a.txt` is still `"a\n"`. The fixup is missing, and `main` does not have it either. In the never-carried variant (case-9 shape, merged into `release`), `a.txt` is not on the line at all. The next wave then builds on a base that is missing its prerequisite, with no STOP. That is exactly the failure this fold exists to prevent.
  The same path also opens on fork targets through fetch order. `_prepare_worktree` fetches `base_remote` before `origin` (`integrate.py:520`, `dict.fromkeys((base_remote, "origin", …))`). A PR that is merged, and its fork branch deleted, between those two fetches leaves a base snapshot without the merge.
  Suggested fix:
  - When `cat-file -e <head>` succeeds, require `<head>` to be an ancestor of `<base_ref>` (or of the line after the base merge), and raise otherwise.
  - Fetch the base remote last.

  This needs a human call rather than `[impl]`. Brief (ii-b) step 4 states "the base now holds that work" as a given, and the check changes the out-of-scope squash case from "merge the base" to "raise". The docs repeat the unchecked claim at `template/PCDA/quality-cycle/09-parallel-lanes.md:69` ("the base, which holds that work, is merged in").

- (Informational, not a refutation.) On the red leg, the required cases 7, 8 (deleted branch), 14b, 15 and 16/17 error with `TypeError: fold() got an unexpected keyword argument 'folded_this_run'`, `AttributeError: … merged_head` or `write_stack_base() takes 2 positional arguments` (`gate-logs/C4-verify.log:1995-2270`). They go red because the new API is missing, not because the old behaviour was observed. The brief allows this (errors in the test, not at import). The green-leg assertions are specific, not tautological:
  - `tests/test_integrate_stack_bases.py:415` checks the tip equals t2 and that the base was not merged.
  - `:383` checks the fixup content.
  - `:719` checks no `fix/U-u` branch was pushed.
  - `:702` checks `host_ci_base == t1`.

  So the C4 PASS stands.

## Attacks that did not land

- **Test realism.** The fold tests hand-write `publish.json` (`tests/test_integrate_stack_bases.py:138-160`) instead of calling the real publish. The `"base": "main"` value that `_gone_branch` relies on is tied to production by `test_a_wave_bundle_publishes_against_the_real_base` (`:649-660`, real `publish.publish`). Not a gap.
- **Tip guard false pass (`publish.py:691-727`).** A recorded tip can become an ancestor of a later run's fresh line, through a merged wave>0 PR whose branch contains that tip. In that case the late PR's diff against main is still only its own change, so the guard's permissiveness is harmless. I found no case where it lets an orphaned tip through.
- **Hold signal (`flow.py:642-665`, `:1890`).** I tried coarse mtime, a publish that fails before or at the push, `gh pr create` failing after the push, an exception after the `publish.json` write, and the no-target and dry-run paths. Every one ends up held, folded or skipped as the brief says. The exception case errs toward holding, which the brief accepts.
- **Recorded tip vs re-gate.** `pushed_tip` is read right after `fold` returns, before the re-gate (`flow.py:1906-1911`). The next fold starts from that tip with `checkout -B`, and `--is-ancestor` exit 128 raises instead of being read as "not in line" (`integrate.py:478-488`). I found no in-run push that moves the line between folds and could trip the #591 mismatch check by mistake.
- **Multi-target, dry-run and lock order.** Unchanged in substance. Dry-run never touches git.
