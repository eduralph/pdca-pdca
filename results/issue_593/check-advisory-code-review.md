# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: correctness bugs the patch adds, plus reuse / simplification / efficiency. Grounded on
the patched tree at `$PDCA_TARGET`. Gates: C4 red→green, T3 suite green (2269 tests), docs
gates clean.

The round-6 carry-forward is done as asked. `_gone_branch` now checks that the base has the
merged head before taking the base in (`template/src/pdca_harness/integrate.py:451-458`). Git
exit codes other than 0/1 are raised as failed git steps (`integrate.py:497-503`). The base
remote is fetched last (`integrate.py:537-542`). The two `release` repro tests exist and check
that nothing was pushed (`template/tests/test_integrate_stack_bases.py:474-511`). The
fetch-order test would fail if the order were reversed (`test_integrate_stack_bases.py:541-585`).
I found no correctness bug in the fold, the publish cut-point/guard, or `merged_head`. Findings
are minor:

- NEEDS-HUMAN [impl] — The hold does not always cascade "through another" bundle, as brief (iv)
  requires. `template/src/pdca_harness/flow.py:712-713` skips a direct dependent D of a held
  bundle U, but D is not added to `held`. The cascade then relies on D never reaching COMPLETE
  (`flow.py:710`). If D was already COMPLETE on disk when the run started (a resumed batch), a
  later E that depends on D passes `_runnable` and builds on a line that has neither U nor D.
  The not-COMPLETE skip already had this narrow gap, but the new `held` path inherits it. Fix:
  add each bundle `_runnable` skips for a held prerequisite to `held_unpushed`, or check `held`
  through the whole dependency chain. A flow test for U → D(pre-COMPLETE) → E would pin it.
- Reuse (minor, no action needed): `_gone_branch` passes `d.name.removeprefix("issue_")` to
  `merged.merged_head` (`integrate.py:431`), which looks the bundle up again through
  `cfg.find_bundle` and re-reads `publish.json` (`merged.py:71`). `_gone_branch` then reads the
  same record a third time (`integrate.py:442`). Passing the record or path through would be
  simpler. `merged_head`'s `gh pr view` / fail-closed body (`merged.py:72-91`) also copies
  `is_merged`'s (`merged.py:46-58`). The brief froze `is_merged`, so a shared `_pr_view` helper
  can wait.
- Efficiency (minor): a wave>0 publish with `host_ci_checks` now fetches `origin` three times
  before pushing: the guard's `fetch --prune` (`publish.py` `_line_tip_refusal`), then
  `_pinned_base` (`publish.py:956`), then the plan's own fetch step. This is harmless and keeps
  each step self-contained. Noted only.

Nothing else found on either lens.
