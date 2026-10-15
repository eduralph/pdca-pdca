# Advisory code review — issue 672

Lens: bugs the patch introduces, plus reuse and simplification. Line numbers are on the patched tree at `$PDCA_TARGET`.

## Correctness

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:894-912` (`_holds_work_of`), called at `:549-555`. The check counts any merge base of the two tips that is missing from the line as "the skipped bundle's work". But the line does not always start from the base. When origin already has the line, the carry passes `folded_this_run={tgt: tip}` (`flow.py:1115`), so the fold uses `start == "continue"` and checks out origin's existing line tip (`integrate.py:507-518`). That tip can be behind `origin/<base>`. Suppose a skipped `P` and an unrelated finished `Y` (no shared commits with `P`) have both been updated from the newer base, for example with GitHub's "Update branch". Their merge base is then a base commit the line lacks. `Y` gets skipped and held with "its branch holds work of issue_P", which is a false hold with the wrong cause. The brief says base commits are not a skipped id's work ("work of a skipped id that is already on the base … is not 'not clean' work"). Suggested fix: also treat a merge base that is an ancestor of `{base_remote}/{base}` as shared base history, not the skipped bundle's work. `_in_line(..., of=base_ref)` already supports this. A test should cover it: a pre-existing origin line, then an unrelated finished id updated from a newer base after a conflicting `P`. The two new tests only use a fresh line, where this cannot happen.
- `template/src/pdca_harness/integrate.py:564-570`: a bundle skipped as `_HoldsSkipped` is added to `dropped` too, so containment spreads down chains (R holds Q's work, Q holds P's work), and each one names its direct cause. A git failure inside `_holds_work_of` raises a plain `IntegrationError`, so the bundle is skipped with an `open` hint and no `skip_causes` entry. That fails safe (nothing unchecked is merged). No action needed.
- `template/src/pdca_harness/flow.py:1121-1126`: the `within` ids get the `built_on` hint and `causes` entries, so `_CARRY_HINTS["built_on"]` (`flow.py:1001-1002`) names the skipped id. This matches how the pre-fold cascade names a cause. Fine.

## Tests

- `template/tests/test_flow_resume_stack_prereqs.py:474-524`: both cases check that P's and Q's tips are not ancestors of the line or of E's tip, and that there is exactly one push, as the brief asks. Case (2) rewrites Q's brief without the edge and re-accepts it before the run, so it does exercise the ancestry path rather than the declared edge. I see no gap beyond the continue-mode case above.

## Reuse / simplification

- `template/src/pdca_harness/flow.py:1057-1062`: re-wrapping the docstring left a short broken line ("A target the carry did not / put to use is not seeded, so the / run's first fold…"). Cosmetic: reflow the paragraph.
- `template/src/pdca_harness/integrate.py:902-903` calls `subprocess.run` directly instead of the `_git` helper. That is justified because it needs stdout (`merge-base --all`), the same way `_merge` reads conflict paths at `:930-931`. Each later bundle costs one `merge-base` plus one `--is-ancestor` per merge base, for each skipped bundle. The carry handles only a few bundles, so the cost does not matter.

Apart from the first bullet, both lenses look clean.

<!-- pdca:leaf-complete -->
