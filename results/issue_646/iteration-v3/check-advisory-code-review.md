# Advisory code review — issue #646 (stack-reissue-continues-batch-line)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.

I found no correctness bug that needs a human decision or a rebuild. I checked:

- The lock scope. `_fold_and_regate` holds the lock through fold, `pushed_tip` and re-gate.
- `LineRefused` is re-raised before the general `IntegrationError` handler, so the two are not mixed up.
- The `vouch` path in `fold`: it is only reached when `start == "auto"`, it skips a missing line, and a push of a vouched line with nothing to fold is unforced.
- The `integ.update` change. It is the same as the old rebinding, because every in-run fold is cumulative.
- The `_runnable` widening is limited to plain `Depends on`.
- A blocked target is kept out of later waves too, so no later fold can force-push over a refused line.

All gates pass (T3: 2356 tests OK). The findings below are small cleanups and one weak spot in a message.

- `template/src/pdca_harness/merged.py:152` — Reuse: the new `_gh` / `_json` / `_head` helpers repeat the `gh pr view … --json state,headRefOid` call, the `OSError` guard and the JSON parsing that `merged_head` already does (`merged.py:66-95`). `merged_head` could be rewritten on top of `_gh`/`_json`/`_head`, or on `pr_state` itself (MERGED ⇒ head), so the missing-`gh` guard lives in one place. Behaviour would not change. This is a cleanup, not a defect.
- `template/src/pdca_harness/flow.py:899-902` — Duplication: the `pr == "NONE"` branch re-reads `publish.json` and recomputes the repo fallback and `OWNER:BRANCH` (`publish._pr_head`). `merged.pr_state` just computed the same values (`merged.py:129-133`) and put them in `note`. The two repo fallbacks agree today (`rec["repo"] or` the brief's target), but they are written twice. Returning `head_spec` and the repo from `pr_state`, for example in a small record, would remove the second copy.
- `template/src/pdca_harness/flow.py:968-969` — Message weak spot, not a safety issue. A carried bundle whose branch was force-pushed with a rebuild leaves its old commits on the line. `integrate.holds` measures against the *current* head, so it returns an empty set for that bundle, and `_say_refused` skips it. The refusal line then names no bundle and offers only "delete the line". It is still correct to fail closed here, and the merge commit's subject (`pdca-integrate: issue_P`) in "brought in by …" points the reader to the bundle. A clause such as "it may hold an earlier version of P" would be clearer. Cosmetic: no NEEDS-HUMAN.
- `template/src/pdca_harness/integrate.py:583` — Efficiency, refusal path only: `entries` runs one `git rev-list` per first-parent commit of the line. That is fine at real line lengths (a handful of folds) and only runs when the line is refused. No action needed.
