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

Review issue #467: preserve a split parent's milestone and labels on every newly filed child, with best-effort metadata lookup.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The loss of release accounting has bounded, falsifiable criteria covering every child, lookup failures, and non-filing paths; the comma-label assumption is challenged below (brief.md:13; target/template/tests/test_split_child_metadata.py:110). |
| C2 Reproduction (red pre-fix) | PASS | Stashing only the production fix reproduced seven assertion failures in 11 tests, including missing metadata and warnings, with no import failures (review-red.log:1; target/template/tests/test_split_child_metadata.py:121). |
| C3 Change | FAIL | A parent label containing a comma can become multiple labels or prevent filing because raw names are passed to gh's CSV parser; repeated flags do not preserve such names (target/template/src/pdca_harness/split.py:1005; review-production-label.log:5). |
| C4 Verification (red→green) | PASS | The specified offline red→green is independently reproduced: seven failures before restoring the fix, all 11 tests green afterward; this establishes the mocked argv contract only (review-red.log:1; review-green.log:1; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | The change addresses missing metadata at the filing boundary; JSON/error handling protects an explicitly best-effort lookup, not an eager capability side effect, and the production-import scanner passes (target/template/src/pdca_harness/split.py:1040; target/template/src/pdca_harness/split.py:1098; gate-logs/C5-prod-path.log:10). |
| T1 Structure | PASS | The existing triage caller remains compatible through defaulted keyword arguments, and the partial/uncertain-filing handler retains its reporting responsibilities (target/template/src/pdca_harness/split.py:986; target/template/src/pdca_harness/triage.py:530; target/template/src/pdca_harness/split.py:1115). |
| T2 Shape | PASS | Independent whitespace, docs lint, and 22-page render/link checks pass; both frozen docs gates show the same successful checks (gate-logs/T2-docs.log:10; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | The independent driver suite reports 1,799 tests with two skips; local root rerun exits 77 for unavailable Copier imports, while frozen evidence shows 24 root tests actually passed (review-driver.log:1103; review-root.log:6; gate-logs/T3-suite.log:54). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred substantive audit must rerun at publish (gate-logs/T4-contribution.log:10). |
| T5 Judgment | PASS | Scope remains one filing change plus sanctioned test-fake updates; path-based main history and all 233 closed PRs were checked, with nine matching PR diffs and no prior metadata-inheritance fix found (review-history.log:1; review-prior-art.log:1). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the release-accounting outcome is demonstrated after the label defect is corrected — actual GitHub child creation was not exercised, so the evidence rests on canned gh responses plus a real local flag-parser check, not persisted child metadata (brief.md:69; target/template/tests/test_split_child_metadata.py:82; review-production-label.log:1). |

## Finding

### P2 — Encode each label for gh's CSV parser

At `target/template/src/pdca_harness/split.py:1005`, a parent label such as `area,backend` is emitted verbatim as one `--label` argument. However, gh registers this flag as `StringSliceVarP`, whose parser reads **each occurrence** as CSV. Consequently that argument requests two labels, `area` and `backend`: if either does not exist, filing fails; if both exist, the child gets different labels from its parent. Repeating the flag does not change its value parser. This contradicts the comma-preservation requirement and the comment at `target/template/src/pdca_harness/split.py:996`. Sources: [gh v2.100.0 flag registration](https://github.com/cli/cli/blob/v2.100.0/pkg/cmd/issue/create/create.go#L174), [pflag CSV parsing](https://github.com/spf13/pflag/blob/v1.0.10/string_slice.go#L21).

I exercised the patched `_create_issue` with a captured subprocess call and fed its emitted label value to the installed gh 2.100.0 parser using `--help`, which performs no issue creation. The value `area, "quoted"` exits 1 with a CSV parsing error; encoding it as one CSV field exits 0. See `review-production-label.log:5` and `review-gh-label.log:1`. The plain-comma splitting conclusion follows from the upstream parser; `--help` alone does not display its parsed label list.

Encode each name as one CSV field, including CSV quote escaping, while retaining repeated `--label` flags. Add coverage for comma-containing names and check the downstream parsed names, alongside both returned child IDs. The current test only supplies `bug` and `help wanted` (`target/template/tests/test_split_child_metadata.py:113`), and its fake never parses flag values (`target/template/tests/test_split_child_metadata.py:90`), so the green suite cannot detect this defect.

## Independent checks and limits

- **Target grounding:** the disposable target has the expected production/test changes on its single pre-fix base. Production was stashed for the red run and restored for green; tests remained available in both legs. Source citations above refer to this target. No stale-target caveat arose.
- **Verification command:** from `target/template`, with `PYTHONPATH=src`, run `python3 -m unittest discover -s tests -p test_split_child_metadata.py`. Local red and green output is preserved in `review-red.log` and `review-green.log`.
- **Scanners:** reran `target/template/scripts/checks/test_exercises_production.py` with `PDCA_PROD_PACKAGE=pdca_harness` and `PDCA_BUNDLE` set to the review directory; reran the docs linter, site renderer with `--check`, and `git diff --check`. All passed. The instance-scoped wrappers themselves are not present here; their full frozen logs were read.
- **Runtime:** `python3 -m unittest discover -s tests` in the template passed. `python3 -m tests.run_root_suite` could not exercise Copier under this interpreter. This is a reviewer-host caveat, not a patch failure: the frozen root log explicitly records the render/update cases and their successful 24-test result (`gate-logs/T3-suite.log:39`).
- **Prior art:** queried main commit history separately for all three affected paths. Queried all 233 closed PRs by their changed-file paths, including closed-unmerged work, then inspected all nine matching diffs; all nine were merged and none introduced tracker metadata inheritance. Results are in `review-history.log` and `review-prior-art.log`. No other checkout was consulted.
- **Human-only integration rules:** the available integration template leaves the project-specific list as TODO (`target/template/docs/INTEGRATION.md.jinja:80`); it supplies no additional concrete human-only item.

## Sign-off validation steps

After correcting label encoding, use a disposable GitHub repository and a configured instance with a real, non-stub two-child proposal. Give the parent a milestone and the labels `bug`, `help wanted`, and `area,backend`. Run `pdca split <parent-id> --accept`, then run `gh issue view <child-id> --repo <owner/repo> --json milestone,labels` for **each** returned child. Confirm that both issues exist, have the parent's milestone title, and carry exactly the parent's label names, including the single comma-containing name. The human decision is whether those persisted results preserve release scope and progress accounting; the current offline fixture cannot establish that outcome.

This review is advisory. The C3 finding does not change the frozen deterministic gate results or make an acceptance decision.

### Advisory — code-review

# Check — advisory code review (issue #467)

Lens: correctness bugs the patch introduces, plus reuse/simplification/efficiency. Grounded
on `$PDCA_TARGET/template/src/pdca_harness/split.py` and the two test files the diff touches.

## Findings

Nothing rises to a defect. Specific things I checked and ruled out:

- `_parent_metadata` (`split.py:1025-1061`) is called exactly once before the filing loop
  (`split.py:1097-1101`), not per child — matches the brief's efficiency requirement (d), and
  C4's log confirms the red leg fails 7/11 new tests with the fix reverted while the green leg
  passes all 96+11, so the new test file genuinely exercises the change.
- `_create_issue`'s new `milestone`/`labels` params are keyword-only with defaults
  (`split.py:986-987`), so `triage.py:530-535`'s five-positional-arg call is untouched — verified
  by reading that call site directly, it passes exactly 5 positional args.
- The `--ids` path (`accept`, `split.py:752`) never calls `file_children` at all, so it does no
  lookup — matches criterion (e), and `can_file` failing for a non-GitHub tracker raises before
  `_parent_number`/the lookup ever run, so that path also does no lookup.
- `test_split_stub_guard.py`'s `_gh` fake (`:69-77`) was **not** adapted, unlike the brief's scope
  note flagged as expected — but that's correct, not an oversight: every test in that file either
  hits the stub-guard refusal before `can_file`/`file_children` run at all (asserts
  `self.calls == []`), or exercises the `--ids` path, which per (e) never reaches
  `_parent_metadata`. So there is no `gh issue view` call that fake needed to answer, and the
  T3 suite log confirms all 1799 tests including this file pass unmodified.
- `_parent_metadata`'s error handling (bare `except Exception`, guarded `json.loads`, dict-type
  check on the top-level result and on each label) mirrors `sources.tracker_issue_reopened`
  (`sources.py:150-176`) as the brief asked, including the same non-object-JSON-is-unknown guard
  (`sources.py:173-175`). It doesn't reuse a shared helper (`sources._run_capture`) — but
  `_create_issue` right above it (`split.py:1006-1007`) already inlines its own `subprocess.run`
  rather than sharing one, so the new function matches this file's existing pattern rather than
  introducing new duplication.
- Every `_is_metadata_lookup` check inserted into the existing `test_split.py` fakes runs
  *before* `self.calls.append(...)` in each case, so the pre-existing call-count-indexed
  assertions (`fail_at`, `numbers[n - 1]`, etc.) are not shifted by the new `gh issue view` call.

No `NEEDS-HUMAN` items — the diff is clean on both lenses.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether the release-accounting outcome is demonstrated after the label defect is corrected — actual GitHub child creation was not exercised, so the evidence rests on canned gh responses plus a real local flag-parser check, not persisted child metadata (brief.md:69; target/template/tests/test_split_child_metadata.py:82; review-production-label.log:1).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected: a parent label name containing a comma or a double quote breaks filing. split.py passes each label as a raw `--label <name>`, but gh 2.100.0 parses every `--label` value as CSV (pflag StringSlice), so repeating the flag does not protect a comma: `area,backend` becomes two labels (child creation fails if either is missing, or the child gets the wrong labels), and a name with `"` is a CSV parse error. Because every child gets the same labels, child 1 fails and the whole split aborts, where today it files fine without labels. Next attempt: encode each label name as one CSV field (quote it and double any inner quotes when it contains a comma, quote or newline; plain names such as `bug` and `help wanted` stay byte-identical), keep one `--label` flag per name, and add tests with a comma-containing and a quote-containing label that check the label names as gh's CSV parsing would read them back, alongside the returned child ids. Everything else in the patch (single lookup, best-effort fallback, triage.py compatibility, fake updates) is fine and should be kept.
- By / date: Eduard Ralph / 2026-09-15

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
