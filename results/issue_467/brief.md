# Brief — issue 467 / split-children-inherit-release-metadata

- **Slug:** split-children-inherit-release-metadata
- **Defect:** `pdca split <id> --accept` files each child issue with only a title, a body and
  `--parent`. `_create_issue` (`template/src/pdca_harness/split.py:986-1012`) builds exactly
  `gh issue create --repo <repo> --title <t> --body <b> [--parent <n>]`, and `file_children`
  (`split.py:1015-1093`) never reads anything else from the parent issue. `split.py` has no
  reference to `milestone` or `label` at all. So a split drops the parent's release metadata:
  children land with no milestone and no labels, and the milestone count stops matching the
  work in both directions (merged children don't count as progress, live children don't count
  as remaining scope). Observed on getwyrd/wyrd milestone 0.1 Alpha: 8 children of 3 parents
  all filed `milestone=NONE`, a quarter of the milestone missing until fixed by hand.
- **Success criterion:** with `gh` stubbed (offline):
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
- **Falsifiability:** RED on the offline driver suite: pre-fix, the argv for a parent with a
  milestone and labels has no `--milestone` / `--label` (fails a, b), and a failing lookup
  produces no warning (fails d). The fake `gh` sees every subprocess call the filing path
  makes, so the red is a real assertion failure, not an import error: the test calls only
  pre-existing API (`split.parse`, `split.file_children`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** none
- **Ordering note:** run 3 of plan-0.60-bug-order.md, one wave with 534, 480, 527 and 529.
  Only this bundle edits `split.py` (480 edits `leaves.py` only, 534 the hook/handoff files).
  #466 (stub splitter never reaches the tracker) is already merged (`9a19cb5`), so this builds
  on it. #481 (run 4) and #545 (run 7) come later and also touch the accept path.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** children filed by `file_children` inherit the parent issue's milestone and label
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
- **Repro instruction:** on `main`, in `template/`: build the `FilingChildIssues` fixture
  (`test_split.py:638-662`) (a `github` tracker at `https://github.com/acme/widgets`, parent
  bundle `issue_500` with a two-child `split-proposal.md`), patch `pdca_harness.split` as
  `_patched` does (`test_split.py:690-694`) with a fake that answers
  `gh issue view 500 ... --json milestone,labels` with
  `{"milestone": {"number": 12, "title": "Milestone 0.60.0"}, "labels": [{"name": "bug"}, {"name": "help wanted"}]}`
  and `gh issue create` with an issue URL. Call `split.file_children(parent, children, cfg)`:
  neither create argv contains `--milestone` or `--label`.
- **External dependencies:** none — offline, gh is faked; base toolchain only (python3 ≥ 3.11)
- **Test file:** template/tests/test_split_child_metadata.py (new), plus the sanctioned fake
  updates in `template/tests/test_split.py` and `template/tests/test_split_stub_guard.py`.
- **Citations expected:** Do cites path:line on `main` for every change. Peer callsites: the
  best-effort parent lookup should mirror `sources.tracker_issue_reopened`
  (`template/src/pdca_harness/sources.py:150-176`): `gh issue view <n> --json <fields>
  --repo <repo>` with the repo always explicit, non-zero exit ⇒ unknown, `json.loads` guarded,
  and a non-object result (`null`, `[]`) treated as unknown. The repo and parent number are
  already in hand in `file_children`: `can_file()` returns the repo (`split.py:1031`) and
  `_parent_number(parent)` the number (`:1034`); a parent with no number already files flat
  (`:1035-1042`) and so has no metadata to look up. The lookup must go through a seam the
  offline fakes intercept (the existing tests patch `pdca_harness.split.subprocess` /
  `pdca_harness.split.shutil`, `test_split.py:690-694`), so no test can reach a real `gh`.
- **Prior-art check (triage cycles):** by path on origin/main (fetched 2026-09-15):
  `git log -- template/src/pdca_harness/split.py` shows `9a19cb5` (#466 stub guard),
  `a2eefe1`, `5c83070` (lineage), `3a3d8ce`, `5f3ee1d`, `30a915e`; none reads or passes
  milestone/labels. No open PR touches `split.py` (open: #542, #543). No closed/merged PR
  references #467 (search hits #415/#430 were line numbers). `gh search issues "milestone
  split"` finds nothing else.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected: a parent label name containing a comma or a double quote breaks filing. split.py passes each label as a raw `--label <name>`, but gh 2.100.0 parses every `--label` value as CSV (pflag StringSlice), so repeating the flag does not protect a comma: `area,backend` becomes two labels (child creation fails if either is missing, or the child gets the wrong labels), and a name with `"` is a CSV parse error. Because every child gets the same labels, child 1 fails and the whole split aborts, where today it files fine without labels. Next attempt: encode each label name as one CSV field (quote it and double any inner quotes when it contains a comma, quote or newline; plain names such as `bug` and `help wanted` stay byte-identical), keep one `--label` flag per name, and add tests with a comma-containing and a quote-containing label that check the label names as gh's CSV parsing would read them back, alongside the returned child ids. Everything else in the patch (single lookup, best-effort fallback, triage.py compatibility, fake updates) is fine and should be kept.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
