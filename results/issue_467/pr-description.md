## Summary
**User impact:** when you split an issue into child issues with `pdca split <id> --accept`,
the children are created with no milestone and no labels, even when the parent has both.
The children fall out of the release they belong to: finished children don't count as
milestone progress, open ones don't show as remaining work, and label filters miss them.
On one real milestone, 8 children of 3 parents were all filed with no milestone, about a
quarter of the milestone's work, and had to be fixed by hand.

This PR makes every child issue get the parent's milestone and labels when it is filed.

Reported in [#467](https://github.com/eduralph/pdca-harness/issues/467).

## What to look at
The split now reads the parent issue's milestone and labels once, before it files any
child, and gives them to every child. If that read fails, the children are still filed
(without the metadata) and one warning tells you to set them by hand, so a split never
fails because of it. Assignees are not copied on purpose: who works on a child is a new
decision.

One detail needs a careful look. gh reads every `--label` value as a comma-separated list,
so a label named `area,backend` would turn into two labels, and a label containing `"` makes
gh exit with a parse error. Names like that are quoted so gh reads them back as one name.
Plain names such as `bug` and `help wanted` are passed unchanged.

To try it: in a throwaway repo, create labels `bug`, `help wanted` and `area,backend` and
an open milestone. Open a parent issue with all of them, write a two-child split proposal
for it, and run `pdca split <parent> --accept`. Then, for each child,
`gh issue view <child> --repo <owner/repo> --json milestone,labels` should show the
parent's milestone and exactly those three labels, with `area,backend` as one label.

## Root cause
`_create_issue` built `gh issue create` with only `--repo`, `--title`, `--body` and
`--parent`, and `file_children` never read anything else from the parent issue
(`template/src/pdca_harness/split.py:984-1012` and `:1015-1093` on `main`). Nothing in
`split.py` referred to a milestone or a label.

## Fix
- **`_parent_metadata(repo, parent_no, root)`** (new): one call to
  `gh issue view <n> --json milestone,labels --repo <repo>`. It returns the milestone
  *title* (`gh issue create --milestone` takes a name, not a number), the label names, and
  whether the lookup worked. It follows the existing best-effort lookup in
  `sources.tracker_issue_reopened` (`template/src/pdca_harness/sources.py:150-176`): the
  repo is always explicit, a non-zero exit or a raised error means "unknown", `json.loads`
  is guarded, and JSON that is not an object (`null`, `[]`) counts as unknown. It catches
  `Exception`, not `BaseException`, so Ctrl-C still stops the split before anything is
  filed.
- **`file_children`** calls it once, before the filing loop, and only when the parent has
  a tracker number. On failure it prints one warning line and files every child without
  the metadata. The partial-filing and interrupt handling in the loop is unchanged.
- **`_create_issue`** takes keyword-only `milestone=""` and `labels=None`. With the
  defaults the argv is exactly what it was, so the PR-triage caller
  (`template/src/pdca_harness/triage.py:530-535`, five positional arguments) keeps working
  untouched. It adds `--milestone <title>` when there is one, and one `--label` per name.
- **`_gh_label_value(name)`** (new): quotes a name that contains a comma, a double quote or
  a line break, doubling any quotes inside it, so gh's CSV parser reads it back as that one
  name. Any other name is returned as-is. The milestone is not encoded, because
  `--milestone` is a plain string flag and quotes would become part of the name gh looks up.
- **Existing test fakes** in `template/tests/test_split.py` now answer the new
  `gh issue view` call separately. Several of them count calls and index by that count, so
  the extra call would have shifted them. No existing assertion was changed or removed.
  `test_ctrl_c_stays_an_interrupt` also answers the lookup now, so its Ctrl-C still hits
  the first `gh issue create`, inside the handler it is meant to test.

Not in this PR: backfilling children that were already filed, copying assignees, and
recovering from a milestone GitHub rejects at create time (such as a closed milestone).
In that last case the split still fails at the first child with nothing filed, as it does
today, and you can clear the parent's milestone and run it again.

## Verification
- **Claim:** every child gets the parent's milestone title and one `--label` per parent
  label name, and gh reads each value back as exactly that name.
  - **Checked:** `template/src/pdca_harness/split.py:986-998` (label encoding) and
    `:1019-1022` (flags added in `_create_issue`), on the PR branch.
  - **Test:** `test_milestone_and_labels_reach_every_child`,
    `test_a_comma_in_a_label_name_stays_one_label`,
    `test_a_double_quote_in_a_label_name_stays_one_label`,
    `test_a_plain_label_name_goes_out_byte_for_byte`,
    `test_the_milestone_title_goes_out_verbatim`.
- **Claim:** the test's fake gh parses `--label` the way real gh does, so the label checks
  are not just checking the code against itself.
  - **Checked:** `TheFakeGhReadsLabelsLikeGh` pins the fake's parser to output seen from
    gh 2.100.0: 8 values it reads (for example `area,backend` gives two labels, while
    `"area,backend"` gives one) and 4 it refuses with a parse error. The class docstring
    gives the two offline gh commands to re-check this. The argv the patched code builds
    was also given to real gh's `issue list --label … --web`, which read back the same six
    names, including `area,backend`, `say "hi"` and `"`.
- **Claim:** a parent with no milestone and no labels produces the same argv as before, so
  no flag is invented.
  - **Test:** `test_no_milestone_no_labels_matches_todays_argv`,
    `test_a_null_milestone_and_no_labels_invent_no_flag`.
- **Claim:** the parent is looked up once, before any child is filed, with the repo passed
  explicitly. A failed lookup still files every child and prints exactly one warning.
  - **Checked:** `template/src/pdca_harness/split.py:1042-1083` (`_parent_metadata`) and
    `:1113-1124` (the single call and warning in `file_children`), on the PR branch.
  - **Test:** `test_the_lookup_happens_once_before_the_children`; a non-zero exit, a raised
    error, `null`/`[]`, and non-JSON output each have a test that files both children and
    checks for one warning line. `test_ctrl_c_during_the_lookup_stays_an_interrupt` checks
    that nothing is filed after Ctrl-C.
- **Claim:** the `--ids` path and non-GitHub trackers make no gh call at all.
  - **Test:** `test_ids_path_does_no_lookup`, `test_a_non_github_tracker_does_no_lookup`
    (their fake gh raises if called).
- **Claim:** a change cannot pass these tests by filing fewer children.
  - **Test:** every filing test asserts the returned child ids (`["601", "602"]`) together
    with the argv; `test_every_child_is_filed_AND_carries_the_metadata_together` checks both
    at once.
- **Red/green:** `template/tests/test_split_child_metadata.py` (new, 18 tests). With the
  `split.py` changes reverted to `main`: 13 failures across 12 tests, and no import errors.
  With the fix: 18 pass. The tests also fail on an earlier version of this fix that passed
  label names raw: `['bug', 'area', 'backend'] != ['bug', 'area,backend']`, and gh refusing
  `say "hi"` with `bare " in non-quoted-field`.
- **Full offline suite:** `test_split.py` 96 OK; driver suite 1806 tests OK (2 skipped, the
  same 2 as before this change).
- **Not covered:** no child issue was created on live GitHub. The offline tests cover the
  argv and how gh parses it, not what GitHub stores. The manual steps under
  "What to look at" cover that.

Fixes #467
