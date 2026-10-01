## Summary
**User impact:** the size warning, which tells you a change has needed so many build
rounds that it should probably be split, could fire on small changes for reasons the
builder could never fix. A round could be counted against the change only because the
reviewer flagged a check that is postponed on purpose, for example the contribution check,
whose commit message and PR description are not written until publish. Two rounds like
that were enough to trigger the warning and send a modest change to a person as
"probably too big".

This PR stops counting a round when everything recorded about it points at something no
rebuild can change: a postponed check, or (as before) a broken environment. Anything
that might be a real problem with the change still counts.

Reported in [#477](https://github.com/eduralph/pdca-harness/issues/477).

**Base:** the PR targets the integration branch that already carries #598 (#409). This
change does not depend on #598: it touches different lines and applies cleanly to `main`
on its own. Line numbers below are on this PR's branch.

## What to look at
- **The rule.** A past round is left out of the count only when *every* recorded reason
  for it is outside the builder's control. The new reason is "the reviewer's only
  findings are on a check the harness recorded as postponed". The existing reason, a
  broken environment, is unchanged in intent.
- **What still counts.** A real failure; a review finding on any other check; a finding
  that doesn't say which check it is about; a finding the reviewer tagged as fixable by a
  rebuild; a second record for the same check that failed; an advisory reviewer that
  found something fixable or didn't finish; and any record that is missing, unreadable
  or malformed. A round whose only finding is the always-present "is this fit for
  purpose?" item also still counts, because nothing recorded explains why it was rebuilt.
- **Two places it gets stricter.** The broken-environment discount used to ignore a
  blocking check with a missing or unknown result, and it never read the advisory
  reviews. Both now count the round. A plain "a person should judge this" advisory note
  does not, so the discount still works on projects that use advisory reviewers.
- **Expected effect today: small.** Since 07766ed3a235e623c0ecdaea7b9b90358bdb810d
  the reviewer is told not to flag a postponed check, and in the 39 recent archived
  rounds that had one, it never did. This is a guard for when the reviewer ignores that
  instruction. Over all 89 archived rounds on our instance, no count changes.

To try it: the new tests build two-round archives on disk and count them. A round whose
checks all pass except a postponed T4 check, and whose review raises only T4 and the
fit-for-purpose item, now counts as 0 instead of 1.

Run: `cd template && PYTHONPATH=src python3 -m unittest tests.test_size_signal`

## Root cause
`_environment_attributed` (`size_signal.py:167`) only left a round out when a blocking
check had recorded `unverifiable` or `flaky`, and it treated any non-standing review
finding as slice evidence. A review finding on a check that `gates` records `deferred`
(`gates.py:798`) is not something a rebuild can address, but it was counted all the same.

## Fix
All production changes are in `template/src/pdca_harness/size_signal.py`.

- `_environment_attributed` (`:167-229`) is now one rule, "every recorded driver is
  outside the slice", with four conditions as commented early returns (`:219`, `:222`,
  `:225`, `:228`, `:229`). The name is kept from #446 and the docstring says why.
  - (a) every blocking row's result is `pass`, `deferred`, `unverifiable`, or a `fail`
    flagged `flaky` (`_NOT_A_VERDICT`, `:158`). Anything else, including a missing or
    unknown result, counts the round.
  - (b) at least one outside driver is recorded: an environment row, or a review finding
    on a deferred element.
  - (c) the review is real, has no FAIL cell and no `[impl]` tag, and every finding is
    the standing Validation row or on a deferred element.
  - (d) no advisory review has an implementation finding or is a placeholder.
- `_archived_gate_rows` (`:232-251`) returns all rows, not only blocking ones, and
  rejects a record whose rows don't all carry a bool `gating` flag.
- `_deferred_elements` (`:254-279`): an element is deferred only if it has a `deferred`
  row and every other row for it is settled (`_SETTLED`, `:162`, with no `flaky` mark).
  A failing, unverifiable, flaky or malformed sibling keeps it live. A row with no
  readable element that isn't settled defers nothing.
- `_element_of` (`:282-290`) reads a finding's leading element id with
  `assemble._ELEMENT_RE` (`assemble.py:64`), the same pattern Check classifies by.
- `_review_findings` (`:293-333`) reads the review through
  `assemble._items_from_artifact` (`assemble.py:280`), as before. Classification strips
  the `[impl]` tag, so the tag is read from the raw items with `assemble._IMPL_MARKER_RE`
  (`assemble.py:68`) at `:330`. That read can only count a round, never discount one.
- `_advisory_drove_the_iterate` (`:350-372`) reads `check-advisory-*.md` the way
  `assemble.collect_needs_human` does (`assemble.py:326`).
- `_review_drove_the_iterate` (`:336-347`) is no longer on the counting path. It is kept,
  and documented, because `tests/test_attempt_harvest.py` still calls it.

`template/pdca.toml.jinja` is unchanged: its `[driver.size_signal]` comment does not
describe which rounds are discounted.

## Verification
All in `template/tests/test_size_signal.py`, class
`RoundsAreAttributedToTheSliceNotTheEnvironment` (`:545`), through
`size_signal.iteration_rounds`, the function the Check backstop and
`scripts/size-calibrate` both use. Archives are real files in the shape the writers
produce; no mocks.

- **Claim:** a round whose only findings are on a deferred T4 check (plus Validation) is
  not counted, whether or not the T4 row is blocking.
  **Checked:** `size_signal.py:167-229`, `:254-279`.
  **Test:** `:744`, `:751` (end to end through `measure` / `oversize_reasons`), `:758`.
- **Claim:** a finding with no leading element id still counts.
  **Checked:** `size_signal.py:282-290`. **Test:** `:764`.
- **Claim:** builder-actionable or unclear evidence still counts the round: plain fail,
  T3 / C5 / T5 findings, FAIL cell, advisory `[impl]` finding, advisory placeholder,
  placeholder or missing review, missing or malformed gate record, Validation-only.
  **Checked:** `size_signal.py:216-229`, `:293-333`, `:350-372`.
  **Test:** `:773`, `:815`.
- **Claim:** a plain advisory note does not count, on the new path or the environment
  path; an advisory `[impl]` finding counts an environment round.
  **Checked:** `size_signal.py:350-372`. **Test:** `:822`, `:828`, `:836`.
- **Claim:** a blocking row with a missing, null, unknown, `none` or non-string result,
  or a non-bool `gating` flag, counts the round on both paths.
  **Checked:** `size_signal.py:216-219`, `:246-249`. **Test:** `:843`, `:866`.
- **Claim:** a deferred row does not hide a failing, unverifiable, flaky or malformed
  sibling of the same element; a passing sibling leaves it deferred.
  **Checked:** `size_signal.py:254-279`. **Test:** `:880`, `:904`.
- **Claim:** a review finding tagged `[impl]` on a deferred element counts; untagged it
  does not. **Checked:** `size_signal.py:330`. **Test:** `:909`.
- **Claim:** existing behaviour is unchanged, including the #446 tests (`:600-703`) and
  `test_the_calibrator_uses_THIS_definition`.
- **Red/green:** with the production change reverted, 12 tests fail, including five
  environment-path cases: a `null`-result blocking row beside an `unverifiable` row is
  discounted on `main` today. With it applied, all 70 tests in the module pass, and the
  full offline suite passes (2149 driver tests).

## Not in this PR
- How Check classifies a reviewer finding on a deferred check when deciding whether to
  rebuild automatically. That is where the noisy rounds started; it is covered by #408.
- Treating a "tool missing on this machine" finding as environmental. Nothing in the
  archive proves that, so it keeps counting.

Fixes #477
