## Summary

**User impact:** Splitting an oversized work item makes the problem look worse instead
of better: every piece the split produces is immediately flagged as oversized again,
with advice to split it further — even when the piece's actual scope is a single
function. The size estimate was counting the bookkeeping the split itself writes into
each piece (the "conflicts with its siblings" scheduling notes, plus the parent's
difficulty and dependency lines copied down) as if a person had declared them, so the
flag fired on every split result before anyone looked at what the piece actually
contains.

This change stops the estimate from scoring the split's own bookkeeping. Everything a
person actually declared still counts exactly as before.

Reported in [#457](https://github.com/eduralph/pdca-harness/issues/457).

## What to look at

One new function in `template/src/pdca_harness/sizing.py`, imported by
`template/scripts/size-calibrate` so the estimator and the calibration script agree on
what a "conflict" is; one docs section (`### The estimate` in
`docs/07-crosscutting.md`); one new test module. No weight or cutoff changes, and no
new configuration.

To try it: accept a split whose children conflict with each other, then look at the
size estimate for one of the children. Previously it scored 9 against the oversized
cutoff of 7 with "2 conflict(s) declared" among the reasons — purely from what the
split wrote. Now the sibling entries neither move the score nor appear in the reasons,
while a conflict naming any *other* item still scores at full weight.

Three behaviours are deliberate and easy to mistake for oversights. A child declaring
a conflict with its *parent* still scores at full weight — the parent is not a
sibling, so that is treated as a real declaration. Children that all conflict pairwise
no longer score as churn, but the estimate still *says* so via an exposed
`sibling_conflicts` count: a mutual-conflict split is the splitter's own statement
that the split separated nothing, and a convergence reader must be able to see it. And
the lineage record the exclusion reads is a hand-editable file, so a corrupted or
malformed one quietly restores the old full-weight scoring rather than crashing the
estimate.

## Root cause

`sizing.estimate` counted every `Conflicts with` id identically
(`template/src/pdca_harness/sizing.py:241` on `main`), but `split.materialise` writes
a `Conflicts with` entry into every child naming its siblings
(`template/src/pdca_harness/split.py:493-499`) and `split.rewrite_ordering` turns
those labels into real ids (`split.py:333-358`) — the ordering fields between children
are the point of a split. Together with `difficulty_high` inherited from the parent
and `ext_deps` copied down (`sizing.py:89-95`), a materialised child scored 3+3+3 = 9
against the oversized cutoff of 7 (`sizing.py:126-127`, banding at `:277-278`),
regardless of scope, and the one de-escalating term (`is_plan_pointer`) is one a split
child never has. The correlation behind the `conflicts_with` weight was measured over
organic bundles, so the estimator was scoring the process's own scheduling metadata
against a weight calibrated for something else.

## Fix

One shared function, `sizing.sibling_conflict_count` (`sizing.py:238-279` in this PR),
reads the lineage record beside the brief and counts how many declared conflict ids
are the bundle's own siblings. `estimate` subtracts exactly that
(`sizing.py:317-325`), so the weighted feature counts organic conflicts only and the
excluded entries leave the human-readable reasons. The count is exposed as
`SizeEstimate.sibling_conflicts` (`sizing.py:205-215`) and carried through `combine`
(`sizing.py:557-565`) so a model escalation cannot drop it.

`scripts/size-calibrate` imports that same function (`size-calibrate:79-84`) and
splits the declared set once (`:304-307`): its `conflicts_with` column is now the same
organic count the engine scores, with the excluded amount reported beside it as
`sibling_conflicts` — deliberately not a correlated feature, since it is metadata the
split writes into its own children (`:230-245`, `:328-334`). Without this, the shared
feature name would denote two different quantities and the next retune of the weight
would be fitted to a number the engine no longer uses for split children.

The exclusion is total by construction: the record is hand-editable, so both sides of
the membership test are narrowed to strings before anything is hashed
(`sizing.py:277-279`); whatever that drops is simply not a sibling and keeps scoring
at full weight — the direction that under-corrects rather than silently discarding a
conflict someone declared.

One pre-existing asymmetry is disclosed rather than changed: the engine counts
declarations while the calibrator counts unique ids. This PR neither introduces nor
removes that — it only guarantees both sides subtract the *same* sibling exclusion;
unifying the counting belongs with the weight-retune loop, not here.

## Verification

- **Claim:** a child whose only conflicts are its own siblings scores below the
  oversized cutoff. **Checked:** `sizing.py:89-95`, `:126-127`, `:241`, `:277-278` on
  `main` — why every such child scored 9 ≥ 7; `sizing.py:317-325` in this PR — the
  subtraction. **Test:**
  `template/tests/test_sizing_split_child.py` —
  `test_a_child_whose_only_conflicts_are_siblings_scores_below_the_cutoff`, against a
  child produced by `split.accept` itself (real lineage record, real rewritten ids),
  with an anti-vacuity companion proving the same fixture reaches 9 under the old
  formula.
- **Claim:** organic conflicts still score at full weight, and a bundle with no
  lineage scores byte-identically to before — reasons included. **Checked:**
  `sizing.py:277-279` in this PR — only lineage-proven string sibling ids are ever
  excluded. **Test:** an organic conflict added inside a split child scores exactly
  what it scores standalone; a lineage-free brief's full `reasons` list is pinned; and
  the module re-runs the *pre-existing* `template/tests/test_sizing.py` calibration
  fixtures (`Structural`, `Combine`, `SecondReviewFixes`, `ThirdReviewFixes`)
  in-process, failing if any of them moves.
- **Claim:** the excluded count is exposed as data and counts conflicts, not mere
  presence of lineage. **Checked:** `sizing.py:205-215` (the field) and `:557-565`
  (carried through `combine`) in this PR. **Test:** two children that each name only
  the other each expose a count of 1; a quiet child with lineage but no conflicts
  exposes 0; a model escalation preserves the count.
- **Claim:** the estimator and `size-calibrate` mine the same quantity under the
  shared feature name. **Checked:** `size-calibrate:79-84`, `:304-307`, `:328-334` in
  this PR — the script imports the estimator's own function. **Test:** asserted by
  object identity (`assertIs`), so a second copy of the rule cannot satisfy it; the
  two agree on a real split child; and the column is unchanged for a lineage-free
  bundle, i.e. for the whole corpus the published calibration was derived from.
- **Claim:** a malformed lineage record degrades the hint, never crashes the
  estimate. **Checked:** `sizing.py:277-279` in this PR — both sides narrowed to
  `str`. **Test:** eight malformed `siblings` values (including an unhashable list
  member, a bare string, a mapping, a bool) are swept through the real
  `sizing.estimate` and again through the helper itself; a usable sibling id beside
  junk is still excluded.
- **Test:** `template/tests/test_sizing_split_child.py` (new, 17 cases) — fails
  pre-fix, passes post-fix. Run with `cd template && PYTHONPATH=src python3 -m
  unittest tests.test_sizing_split_child`. With the production changes reverted and
  the test kept, the run fails (10 failures, 20 errors), headlined by the reported
  symptom verbatim: `9 not less than 7 … ['difficulty=high', '2 conflict(s)
  declared', '1 external dependency token(s)']`; with them restored, 17/17 pass.
- **Suites:** the offline driver suite is green at 1639 tests (+17 = exactly this
  module); the template render and `copier update` compatibility suites ran their 7
  tests green with copier 9.17 actually installed, so they exercised a real render of
  the changed `template/` files. Docs lint and the site render/link audit are green
  over the reworded `docs/07-crosscutting.md:129-140` and `:176-179`. The calibration
  script was also smoke-run read-only over a live instance of 35 settled bundles:
  the table renders, `sibling_conflicts` is absent from the correlated features, and
  the CSV emits the organic and excluded columns side by side.

Fixes #457
