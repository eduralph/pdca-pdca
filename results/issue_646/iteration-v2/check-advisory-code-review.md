# Advisory code review — issue_646 (stack-reissue-continues-batch-line)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.
All `path:line` refs are on the patched tree at `$PDCA_TARGET`.

I found no blocking correctness bug. The four sign-off items are handled:
- the lock now covers the fold, the tip read and the re-gate (`template/src/pdca_harness/flow.py:883-905`);
- a red re-gate stops the run before wave 0;
- a line that already holds a closed or unreadable id is blocked rather than continued (`flow.py:845-875`);
- the wording is qualified.

The gates agree. C4 is red pre-fix and green post-fix. T3 ran 2349 tests: OK.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:873-886`: once the carry triggers, the run continues the earlier run's line as it is. That line can hold the old branch of a bundle that is back in this run's drive set: it was folded last time, then re-opened or iterated, so it is no longer COMPLETE. Before this patch, the first fold started a fresh line, which dropped the stale copy. Now the wave-0 rebuild of that bundle is built on, and later folded onto, a line that already has its rejected branch. That can show up as a fold conflict, or as old commits riding along in its PR. The brief's "continue, never replace" rule makes this a design choice. A human should decide whether the carry should also check that no drive-set bundle is already on the line (`integrate.read_lines` already has the `_holds` machinery to look). No test covers this case.

- `template/src/pdca_harness/flow.py:2255`: the in-run fold after wave 0 folds only `accepted`. Ids carried by `_carry_finished` are not in it, so a fixup pushed to a carried id's PR branch during the run never reaches the line in this run. The new docs paragraph (`docs/07-crosscutting.md`, "Commits pushed onto a stack PR's branch after a fold carried it reach the line at the next fold") reads as if it applies to carried ids too. This is minor. Either pass the carried ids into later folds (`_merge_published` skips work already on the line, so this is cheap), or say in the docstring that carried ids are folded once.

- `template/src/pdca_harness/flow.py:883-905` vs `flow.py:2252-2283`: the carry's block (fold under an `ExitStack` of locks → record `pushed_tip` per target → `integ.update` → optional `gates.run_integration(..., hold_lock=False)` → STOP) is a near copy of the in-run fold block. The lock and re-gate rules are exactly what sign-off had to send back last round. Having two copies invites them to drift apart again. Suggested cleanup: one helper, e.g. `_fold_and_regate(cfg, bundles, folded_this_run, ...) -> str | None` (None means OK, otherwise the stop reason), used from both places.

- `template/src/pdca_harness/merged.py:99-130` vs `merged.py:67-96`: `pr_state` repeats `merged_head`'s whole `gh pr view --json state,headRefOid` call, including the `OSError` guard and the JSON parse. `merged_head` could become a thin wrapper: `st, head, why = pr_state(cfg.find_bundle(dep_id))`, keep its stderr line when `why` is set, and return `head if st == "MERGED" else None`. That leaves one place that reads PR state.

- `template/src/pdca_harness/integrate.py:271-276` vs `integrate.py:420-428`: `read_lines` copies `fold`'s "take the lock or raise IntegrationError with the permissions hint" block word for word. A small `_take_integ_lock(stack, repo, base)` helper would remove the duplicate. This is cosmetic.

- `template/src/pdca_harness/flow.py:858`, `flow.py:2117-2118`: `publish._resolve_target` (a brief parse) runs once per bundle in the `stuck` list and again for every bundle in every wave whenever `blocked` is non-empty. The cost is small, but the carry already resolves targets for its candidates. Caching `{d.name: target}` for the drive set once would remove the repeat parses. Low priority.

No test-quality problems found. The new file drives the real `_drive_and_act`, `fold`, `publish` and re-gate against real git. It imports modules only, so the red leg fails rather than erroring at import. The lock-order test checks nesting depth, which goes beyond checking that the calls happened.
