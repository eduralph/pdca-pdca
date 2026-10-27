## Summary
**User impact:** When two bundles in one batch change the same lines, the run holds one
of them back and, at its end, tells you which bundle it clashes with and how to fix it.
If you then re-run the same batch, the run says something different and wrong about the
same bundle: it calls the clash a "cross-wave overlap" and tells you to re-open or
re-publish a PR that is already open. Following that advice changes nothing, the bundle
stays held along with everything that depends on it, and the bundle it clashes with is
never named.

This PR makes the re-run give the same advice as the first run: it names the bundle(s)
the held one clashes with and the files, and proposes the same fix (declare
`Conflicts with:` and rebuild on a base that holds them). When the clash is with the
base branch itself, or with work no bundle of the batch accounts for, it says so and
blames no bundle.

Reported in [#694](https://github.com/eduralph/pdca-harness/issues/694).

## What to look at
- The new advice text and how each kind of clash is worded: `_clash_why` and the new
  `_CARRY_HINTS` entries in `flow.py`. The fix step is now one shared string, used by
  both the end-of-run message and the re-run message, so they can't drift apart again.
- How the partner is found: `_clash`, `_partners` and `_merge_over` in `integrate.py`.
  This is the part that needs the closest review.
- To reproduce: plan `10` and `11` that both change the same line of one file, plus `20`
  with `Depends on: 11`. Drive all of them: `11` is held and the run's last lines name
  `issue_10`. Then drive `20` again with the same batch. Before this change the line about
  `issue_11` says "cross-wave overlap … get issue_11's PR open"; after it, the line names
  `issue_10` and the file and repeats the first run's step.
  `template/tests/test_flow_reissue_after_conflict_hold.py` does exactly this with real git.

**Base:** this builds on the fixes for #672, #673 and #693, which touch the same code and
are not on `main` yet. Every `path:line` below is on that tree with this change applied.

## Root cause
On a re-run, finished bundles go through the pre-wave carry. When the carry's merge failed
with a text conflict, it reused the in-run merge's "undeclared cross-wave overlap" message
and filed the bundle under the generic "get its PR open" hint. It never asked what the
branch actually conflicted with. Reusing the in-run "held out" check unchanged would not
help either: on a re-run the line already holds the partner from the first run, so that
check finds nothing to blame.

## Fix
- **Find what the branch conflicts with** (`integrate.py`). When the carry's merge records
  a text conflict, `_clash` (`integrate.py:1199`) judges it after the merge pass ends, on
  the line that gets pushed:
  1. Try the branch on the base alone. If that conflicts, the clash is with the base: no
     bundle is named.
  2. Otherwise try it on base + each finished bundle the line carries (merged earlier or
     later in this pass, or already on the line from the first run, in any order). Each
     one it conflicts with is named with the files (`_partners`, `integrate.py:1246`).
  3. A bundle stacked on another must clash in its *own* change to be named. The trial
     first merges the held branch onto what that bundle was built on, letting the held
     branch win every clash, including whole-file ones such as a deleted file
     (`_merge_over`, `integrate.py:1132`, used by `_trial` at `:1331`). Then it merges the
     bundle's head. This way a deletion the bundle only inherited can't hide or fake a
     clash.
  4. If no single bundle accounts for it, the files are named and no bundle is blamed. If
     bundles the merge took back off the line are the cause, they are named as not carried,
     and the step waits until a line carries them.
- **Word the advice** (`flow.py`). `_clash_why` (`flow.py:1029`) turns the result into the
  reason and picks a hint. The shared step `_CONFLICT_STEP` (`flow.py:1004`) is now used
  both by the carry's `"conflict"` hint (`flow.py:1017`) and by the end-of-run message
  `_report_conflict_holds` (`flow.py:1263-1272`).
- **Docs**: the carry section of `docs/07-crosscutting.md:767-795` describes the new
  advice. "Two finished prerequisites that conflict with each other" stays in the list of
  limits, now marked as named with the step.
- Out of scope, unchanged: which of the two clashing bundles gets carried, the in-run
  merge's own conflict message, and the carry's other hints.

**Known limits** (rare, and none of them blames the wrong bundle):
- A branch that clashes with both the base and a partner is reported as a base clash only.
  The next re-run, after updating from the base, names the partner.
- A clash that only several bundles together reproduce is reported as "other work on the
  line", with no bundle named.
- If a later merge in the same pass has already removed the clash, the advice still
  proposes the `Conflicts with` + rebuild step, though a plain re-run would carry the
  bundle. This will be filed as a separate issue.

## Verification
- **Claim:** a re-run after a same-batch conflict hold names the partner and the file and
  gives the first run's step word for word, with no "cross-wave", `pdca publish` or
  "get … PR open" text. The dependent stays unbuilt.
  **Checked:** `flow.py:1197` (the carry maps each clash through `_clash_why`),
  `flow.py:1004`/`:1268` (one shared step string).
  **Test:** `test_a_reissue_after_a_conflict_hold_names_the_partner`
  (`template/tests/test_flow_reissue_after_conflict_hold.py:210`) takes the step from run 1's
  output and asserts it appears in run 2's line.
- **Claim:** when the clash is with the base, no bundle is named and no `Conflicts with` is
  proposed. **Checked:** `integrate.py:1199` (base tried first), `flow.py:1046`.
  **Test:** `test_a_conflict_with_the_base_names_no_partner` (`:516`).
- **Claim:** a partner is named whatever order the ids are asked in, including one already
  on the line from the first run. **Test:**
  `test_a_partner_already_on_the_line_is_named_when_asked_for_after` (`:218`),
  `test_one_the_fold_merges_after_it_is_named_too` (`:240`).
- **Claim:** a stacked bundle is named only for its own change, also when a file was
  deleted below it. **Checked:** `integrate.py:1132-1169` (`_merge_over`), `:1246-1271`.
  **Test:** `:282`, `:355`, `:367` (not named), `:321`, `:385`, `:401`, `:429`, `:442`
  (named).
- **Claim:** a bundle that is held itself, or that the merge took back off the line, is
  never given as the base to rebuild on. **Test:** `:254`, `:471`.
- **Claim:** nothing else changes. **Checked:** every existing case in
  `template/tests/test_flow_resume_stack_prereqs.py` and
  `template/tests/test_flow_same_wave_conflict.py` stays green.
- **Red → green:** with the production changes reverted and the test kept, all 22 cases in
  the new file fail on their assertions, each showing the old "cross-wave overlap … get
  issue_11's PR open" line; with the change, all 22 pass. Full offline suite: 2513 tests OK
  (2 skipped). Docs check: lint, render and link audit OK.

Fixes #694
