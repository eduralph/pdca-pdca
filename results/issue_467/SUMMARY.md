# Result — issue 467 / split-children-inherit-release-metadata

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `pdca split <id> --accept` files each child issue with only a title, a body and
  `--parent`. `_create_issue` (`template/src/pdca_harness/split.py:986-1012`) builds exactly
  `gh issue create --repo <repo> --title <t> --body <b> [--parent <n>]`, and `file_children`
  (`split.py:1015-1093`) never reads anything else from the parent issue. `split.py` has no
  reference to `milestone` or `label` at all. So a split drops the parent's release metadata:
  children land with no milestone and no labels, and the milestone count stops matching the
  work in both directions (merged children don't count as progress, live children don't count
  as remaining scope). Observed on getwyrd/wyrd milestone 0.1 Alpha: 8 children of 3 parents
  all filed `milestone=NONE`, a quarter of the milestone missing until fixed by hand.
- Success criterion: with `gh` stubbed (offline):
  (a) when the parent issue has a milestone, every child `gh issue create` call carries
      `--milestone <the parent's milestone title>` (`gh issue create --milestone` takes the
      milestone **by name**; the parent's `gh issue view --json milestone` gives
      `{"number", "title", ...}`, and the title is the value to pass);
  (b) when the parent has labels, every child call carries each of the parent's label
      **names**, one `--label <name>` per label (a name may contain a comma or a space, so it
      must not be comma-joined into one value);
  (c) a parent with no milestone and no labels produces a child argv identical to today's,
      so no flag is invented;
  (d) the parent's metadata is looked up **once**, before the filing loop, not per child, and
      the lookup is best-effort: a lookup that exits non-zero, raises, or returns output that
      is not a JSON object still files **every** child (without the metadata) and prints one
      warning to stderr saying the metadata was not inherited. It never aborts the batch and
      never changes the `UncertainFiling` / partial-filing reporting (`split.py:1053-1092`);
  (e) the `--ids` path and a non-GitHub tracker are untouched: they file nothing, so they do
      no lookup;
  (f) the assertions are on the recorded argv **and** on the returned child-id list, so a
      regression cannot pass by filing fewer children.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: children filed by `file_children` inherit the parent issue's milestone and label
  names, as stated in the criterion. One logical change in `split.py`'s filing path. Updating
  the fake `gh` in existing tests so it answers the new metadata lookup separately is **in
  scope and expected**. The fakes that stub `pdca_harness.split.subprocess` are in
  `template/tests/test_split.py` (`_gh` at `:666-688`, `_run_returning` at `:1035-1039`, and
  the `run` fakes at `:1068`, `:1342`, `:1401`, `:1457`, `:1675`, `:1694`, `:1715`, `:1734`)
  and `template/tests/test_split_stub_guard.py` (`_gh` at `:69-77`). Several count every call
  and index `numbers[n - 1]` by call count, so an extra `gh issue view` call shifts them. They also accept only `(cmd, capture_output, text, cwd)`, so a new
  keyword such as `timeout=` would raise `TypeError`. Adapt the fakes; do not weaken or delete
  any existing assertion (call counts in those tests are about `issue create` calls).
  / out of scope: assignees (deliberately not inherited: who works a child is a new
  decision); backfilling already-filed children; closing the parent; `triage.py`'s own call to
  `split._create_issue` (`triage.py:530`), which must keep working unchanged, so any new
  `_create_issue` parameter needs a default; handling a milestone the tracker rejects at
  create time (e.g. a closed milestone). If Do finds that case is cheap and safe, record it in
  build-notes, but it is not required.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #467: preserve a split parent's milestone and labels on every filed child, including comma- and quote-containing label names, while retaining best-effort lookup and partial-filing behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The offline criteria distinguish complete inheritance, unchanged empty-metadata argv, lookup failure, and non-filing paths; returned IDs prevent success through under-filing (`brief.md:13`, `target/template/tests/test_split_child_metadata.py:240`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes produced 13 assertion failures across 18 tests, including absent milestone/labels and missing warnings; imports succeeded (`reviewer-red.log:105`, `reviewer-red.log:142`). |
| C3 Change | PASS | Metadata reaches every child without changing the existing uncertainty/partial-filing handler, and default arguments preserve the triage caller (`target/template/src/pdca_harness/split.py:1001`, `target/template/src/pdca_harness/split.py:1130`, `target/template/src/pdca_harness/triage.py:530`). |
| C4 Verification (red→green) | PASS | Restoring the production patch turned the same 18 offline tests green; this establishes the specified subprocess contract, with the external-behavior limitation recorded under Validation (`reviewer-green.log:3`, `gate-logs/C4-verify.log:10`). |
| C5 Causal adequacy | PASS | The previously omitted metadata and incorrect label encoding are addressed at the filing boundary; no capability probe or load-time symptom guard was added, and tests call production filing (`target/template/src/pdca_harness/split.py:996`, `target/template/src/pdca_harness/split.py:1121`, `target/template/tests/test_split_child_metadata.py:240`). |
| T1 Structure | PASS | One filing-path change stays within the existing module and subprocess seam; no dependency, configuration, or unrelated production surface is added (`target/template/src/pdca_harness/split.py:1042`, `target/template/src/pdca_harness/split.py:1063`). |
| T2 Shape | PASS | Independent whitespace check, docs lint, and 22-page site render/link audit passed; frozen docs and host-parity logs agree (`reviewer-docs-render.log:2`, `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver run passed 1,806 tests with two skips; frozen evidence explicitly shows all 24 root render/update tests passing, which could not be rerun locally because copier is absent (`reviewer-suite.log:1103`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit must rerun at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm merged and closed/rejected prior art by affected file path before judging duplication or prior rejection: the brief records merged history by path but closed work by issue reference, and the supplied target contains only one snapshot commit and no remotes (`brief.md:82`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether inheriting every parent label meets release-tracking needs and whether the offline evidence suffices: live GitHub creation/inheritance was not exercised, so exact inherited names rest on a modeled CSV parser plus partial real-gh parser checks (`brief.md:69`, `target/template/tests/test_split_child_metadata.py:54`, `target/template/tests/test_split_child_metadata.py:267`, `reviewer-gh-help.log:5`). |

## Independent evidence and limits

- **Target grounding:** source citations above resolve in `$PDCA_TARGET`, `/tmp/pdca-review-079nr468/target`. The target contains the patch and was usable for both test legs; no target-state caveat was necessary. The tracked diff was byte-identical before and after the stash/pop sequence.
- **Red→green:** retained the regression tests while running `git stash push -- template/src/pdca_harness/split.py`, then `python3 -m unittest discover -s tests -p test_split_child_metadata.py` in `target/template` with `PYTHONPATH=src`. Restored with `git stash pop` and reran the identical command. Full output is in `reviewer-red.log` and `reviewer-green.log`.
- **Other checks:** reran `python3 -m unittest discover -s tests`, the shipped production-import scanner, `git diff --check`, docs lint, and site rendering with `--check`. Temporary output was directed inside this review sandbox. The instance gate wrappers are outside the supplied target; all six named frozen logs were read. The root-suite log demonstrates actual copier render/update execution, so the reviewer's missing copier is a local limitation, not an unmet gate dependency or patch defect.
- **Real CLI probe:** installed `gh` is 2.100.0. `gh issue create --label '<value>' --help` rejects raw `say "hi"`, `area, "quoted"`, and `"`, and accepts their production-encoded forms (`reviewer-gh-help.log`). This exercises flag parsing without filing issues. An attempted `GH_BROWSER=echo gh issue list ... --web` probe with a dummy token reached HTTP 401 for syntactically valid values; it did not reveal decoded names (`reviewer-gh-parser.log`). Accordingly, exact comma-label identity is established by the offline model, not independently observed from a live tracker.
- **Concrete follow-up for Validation:** in an authenticated instance with an approved disposable GitHub parent carrying a milestone and labels `bug`, `area,backend`, and `say "hi"`, run `pdca split <parent-id> --accept` on a reviewed two-child proposal. For each returned ID, run `gh issue view <child-id> --repo <owner/repo> --json milestone,labels,parent`; confirm both children exist, have the intended parent, share its milestone title, and retain each complete label name. This creates real issues and remains a human validation decision.
- **Prior art:** `git log --all --` for all three affected paths returned only snapshot commit `467c2f9`; `git remote -v` returned nothing. The supplied evidence does not independently settle closed/rejected work by path. The available integration template enumerates no additional concrete human-only checks (`target/template/docs/INTEGRATION.md.jinja:80`).

No grounded patch defect found. These verdicts are advisory; acceptance remains the human's decision.

### Advisory — code-review

# Advisory code review — issue #467 (split-children-inherit-release-metadata)

## Correctness bugs introduced by the patch

None found. Specifics checked and confirmed sound:

- `template/src/pdca_harness/split.py:1000-1019` (`_create_issue`) — new `milestone`/
  `labels` are keyword-only with safe defaults (`""`, `None`), so `triage.py:530-535`'s
  five-positional-arg call keeps working unchanged, as the brief requires.
- `template/src/pdca_harness/split.py:996-997` (`_gh_label_value`) — round-trips
  correctly against the pinned reader model in the new test file
  (`test_split_child_metadata.py:307-352`, `_gh_label_field`): a name with a comma, a
  bare `"`, or both, comes back as the one name it started as. Verified by hand for the
  `'"'`-only case and the comma+quote case; both match the test's expected output.
- `template/src/pdca_harness/split.py:1096-1131` (`file_children`) — the metadata lookup
  is gated on `parent_no` and happens once, before the loop, exactly per criterion (d);
  a `can_file` failure raises `TrackerUnavailable` before that point, so the `--ids` path
  and a non-GitHub tracker (criterion e) do zero lookups, confirmed against
  `split.py:930-944` (`can_file`) and `split.py:752` (`accept`, which never calls
  `file_children` at all on the `--ids` path).
- `template/src/pdca_harness/split.py:1039-1084` (`_parent_metadata`) — mirrors
  `sources.py:150-176` (`tracker_issue_reopened`) as claimed: non-zero exit, a raised
  exception, unparseable JSON, and a non-dict JSON value (`null`, `[]`) are all treated
  as "unknown," never crash `.get`, and the `bool` return correctly distinguishes "looked
  up fine, nothing to inherit" from "lookup failed" so the caller warns only in the
  second case.
- `template/tests/test_split_stub_guard.py` was **not** touched, despite the brief
  flagging its `_gh` fake (`:69-77`) as needing adaptation. Checked why: every test in
  that file asserts `self.calls == []` (`:133-134`, `:154`, `:163`) — the stub guard
  refuses before `file_children` is ever reached, and the `--ids` path does no lookup
  either. So that file never exercises a `gh issue view`/`create` pair for real, and
  leaving its fake as-is is correct, not an oversight.
- C4's red-run log (`gate-logs/C4-verify.log`) shows 13 real assertion failures pre-fix
  (missing `--milestone`, zero `gh issue view` calls, no warning line) rather than an
  import error, so the gate is grounded on the intended behavior, not a collection
  failure.

## Reuse / simplification / efficiency

Nothing to flag. The one place I looked for unjustified duplication —
`_parent_metadata` (`split.py:1039-1084`) re-implements the same
subprocess-run/guarded-json-parse pattern as `sources.tracker_issue_reopened`
(`sources.py:150-176`) instead of calling a shared helper — is deliberate and correctly
so: `sources._run_capture` (`sources.py:89-91`) calls `subprocess.run` through the
`sources` module's own reference, not `pdca_harness.split.subprocess`, which is the seam
every existing fake in `test_split.py` patches (per the brief's own citation). Reusing it
would reach past the offline fakes toward a real `gh`. The ~10-line duplication buys
keeping the test seam intact, which is the right trade here.

## Overall

Clean on both lenses. No findings requiring a human or a build iteration.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm merged and closed/rejected prior art by affected file path before judging duplication or prior rejection: the brief records merged history by path but closed work by issue reference, and the supplied target contains only one snapshot commit and no remotes (`brief.md:82`).
- [x] Validation — fitness-to-purpose — Decide whether inheriting every parent label meets release-tracking needs and whether the offline evidence suffices: live GitHub creation/inheritance was not exercised, so exact inherited names rest on a modeled CSV parser plus partial real-gh parser checks (`brief.md:69`, `target/template/tests/test_split_child_metadata.py:54`, `target/template/tests/test_split_child_metadata.py:267`, `reviewer-gh-help.log:5`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
