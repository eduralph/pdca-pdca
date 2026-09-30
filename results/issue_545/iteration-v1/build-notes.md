# Build notes — issue 545 / split-parent-closes-with-children-bound-depth

Target: `eduralph/pdca-harness @ main`, worktree `$PDCA_WORKTREE` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l1` (HEAD `f33a23f`). All `path:line` below are on
that tree with the patch applied.

## What changed

### 1. Split parent in `pdca cleanup` (P1–P9, S2)

- `template/src/pdca_harness/cleanup.py:22-27` — module docstring matrix gains the
  split-parent row (names `split` and `children`; S2).
- `cleanup.py:56` — imports `flow` and `split`. No import cycle: nothing that `flow`
  imports (`flow.py:29-31`) imports `cleanup`; only `cli.py:22` does.
- `cleanup.py:168-173` — new `_bundle_comment(d)`: the `tracker-comment.md` read that used
  to be inline in `_close_issue`, factored out so the split path can use it too.
- `cleanup.py:176-190` — `_close_issue` gains `prefer_bundle_comment: bool = True`. Default
  keeps today's behaviour for every existing caller (held by
  `test_bundle_tracker_comment_file_is_preferred`, `test_cleanup.py:383`, still green). The
  split path passes `False` with a body it has already built.
- `cleanup.py:234-289` — new `_split_parent_row`. Reads children with `split.read_lineage`
  (`split.py:633`, the tolerant file reader; `_recorded_depth` is at `split.py:665`) + `flow._lineage_children` (`flow.py:690`, the
  tolerant value reader — reused as the brief asked, not re-written). Each child's state
  comes from `_issue_state` (`cleanup.py:70`) against the tracker. Outcomes:
  - no children → report "children are unknown … close the issue by hand" (P5);
  - any child OPEN → report "waiting on #…"; any child unreadable / non-numeric / odd
    state → report "child state unknown for #…" (P1, P4). Both can appear in one line;
    neither acts;
  - all CLOSED → close `completed` if any `stateReason.upper() == "COMPLETED"`, else
    `not planned` (P2, P3). Comment is "This issue was split; all of its child issues are
    closed: #601 (completed), #602 (not planned). Closing as completed.", with the
    hand-written `tracker-comment.md` text placed above it when that file exists (P8).
- `cleanup.py:379-384` — in the OPEN branch, `COMPLETE and flow._is_split_parent(d)` is
  checked **before** the recorded-PR checks and the empty-patch close (P9, Design §1).
  `_is_split_parent` (`flow.py:907`) is the existing marker test (terminal state +
  `close-disposition` == `split`, total catch on the read); reused rather than re-read.

DISCONTINUED split parents keep today's path (`cleanup.py` DISCONTINUED branch untouched),
per the brief's scope.

### 2. Depth bound (D1–D4)

- `template/src/pdca_harness/split.py:298` — `MAX_SPLIT_DEPTH = 2`, the one named place.
- `split.py:301-316` — `check_depth(parent, *, force=False)`: reads depth via
  `read_lineage` + `_recorded_depth` (so bad JSON / `"one"` / `null` / `true` → 0, D4) and
  raises `SplitError` naming the recorded depth and `--force` when depth ≥ 2 and not forced.
- `split.py:319`, `:349` — `preflight` gains `force: bool = False` and calls `check_depth`
  right after the "already marked" refusal, before `_parent_plan` and the convergence
  report — i.e. before any `gh issue create` (`cli.py` calls preflight before
  `file_children`).
- `template/src/pdca_harness/cli.py:197-200` — `--force` flag on `split`.
- `cli.py:812-814` — passes `force=bool(getattr(args, "force", False))`. `getattr` default
  is how the ~20 existing tests that build `SimpleNamespace(issue_id, accept, ids)` keep
  working unchanged (Design §5); none were edited.

`split.accept` itself is not changed: it makes the same tracker calls as today (Design §2),
and it has no depth check. The only caller of `preflight` is `cli.py:814`, so the CLI is
the one enforcement point — which is the scope the brief names (`pdca split --accept`).

### 3. Words (S1, S4)

- `template/agents/planner.md.jinja:164-172` — two new paragraphs after the `--accept`
  paragraph: the parent issue "**stays open**" and is closed by `cleanup --apply` once all
  child issues are closed; `--accept` refuses at depth 2+, `--force` overrides and "is the
  human's decision, not yours. Do not pass `--force` unless the human has asked for it in
  so many words; when the refusal appears, show it to the human and stop there." The
  `--force` paragraph contains "human" (S1). Only additions — `TheDoctrineIsConsistent` and
  `ThePlannerIsToldItOwnsTheSplit` untouched and green.
- `template/pdca.toml.jinja:513-516` — splitter comment says the same two things (S4,
  read at sign-off).
- `docs/07-crosscutting.md:673` — new first COMPLETE/OPEN row in the `pdca cleanup` table
  (S4, read at sign-off).

## Evidence

- **C4 (the gate's own script)** — `PDCA_BUNDLE=… PDCA_WORKTREE=… engine/scripts/run-verify.sh`
  from the instance root: green leg `Ran 17 tests … OK`; red leg (every non-test hunk
  reverted) `Ran 17 tests … FAILED (failures=17)` — the 17 failing items are D1 (3), P1–P5
  (P5 × 5 subtests), P8, P9, S1, S2 and the case-insensitivity test. Verdict line:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The module imports in the
  red leg (it only uses symbols that exist on main), so it is a real "ran and failed".
  Green on both legs, as expected: P6, P7 (today's behaviour), D2–D4 (accept works today).
- **S3** — `cd template && PYTHONPATH=src python3 -m unittest tests.test_split
  tests.test_cleanup`: `Ran 146 tests … OK`. No assertion in `test_split.py` or
  `test_cleanup.py` changed (neither file is in the patch).
- **T3 (whole suite, `engine/scripts/run-suite.sh`)** — root suite `Ran 24 tests … OK`;
  driver suite `Ran 2088 tests … OK (skipped=2)`.
- **T2 docs** (`engine/scripts/run-docs-check.sh`, since the patch edits `docs/`) — lint OK,
  site render + link audit OK.
- **Commit-ready** — the target has no `.pre-commit-config.yaml` and no formatter/linter
  configured in the repo; its CI (`.github/workflows/`) runs docs-check and render-check,
  both covered by T2/T3 above. DCO sign-off on the commit is the publish step's job.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. The C4 red leg reverts every production/doc hunk and re-runs the
  module: 17 failures, including exactly the brief's binding cases (P1 closes 500 as "not
  planned" today; P9 closes it "Fixed by …"; P8 posts only the hand-written note; D1 returns
  rc 0 with children on disk). Output quoted above.
- **(b) Production path?** Yes. P-tests call `cleanup.run(cfg, [], apply=…)` with only
  `subprocess.run` / `shutil.which` patched at `cleanup`'s module level (the
  `CleanupBase` pattern). D-tests call `cli._split` with only `split.subprocess` /
  `split.shutil.which` patched (the `TheWholeChainUnmocked` pattern) — the real preflight,
  `file_children`, `accept` and `materialise` run, and child depth is read back from the
  real `split-lineage.json`. S1 reads the real role prompt file; S2 the real module doc.
- **(c) Fixture includes the fault?** Yes. The parent is a real COMPLETE bundle
  (`state.state` asserted COMPLETE in the helper) carrying the real `close-disposition`
  marker and a real lineage record; the open child, the unreadable child (fake `gh`
  returns rc 1 for 602), the merged pre-split PR, and the `tracker-comment.md` are each
  present in the case that covers them. D1 uses real depth-2 and depth-3 records.

## Choices and what I ruled out

- **Body for P8.** Options: (i) append the child list to whatever `_close_issue` picks —
  but with no `tracker-comment.md` the fallback already names the children, so it would
  print them twice unless `_close_issue` learned about split parents; (ii) the chosen
  `prefer_bundle_comment=False` switch + caller-built body: 1 new kwarg, 1 changed line in
  `_close_issue` (`cleanup.py:190`), no split knowledge in the shared helper. The
  idempotency probe in `_close_issue` still compares the exact body, so a retry does not
  repost.
- **Depth check location.** In `preflight` (not only in `cli._split`) so it sits with the
  other ids-independent refusals, as the brief asked; exposed as `check_depth` so it is one
  function. Not added to `split.accept`: that would make `--ids` accepts of forced splits
  need `force` threaded through `accept` too, and `accept` is not where the brief puts it.
- **Stop-early on the first open child.** Not done: all children are queried so the report
  names every open / unknown child at once (one `gh issue view` per child; a split has a
  handful).
- **Child state other than OPEN/CLOSED** (e.g. a future gh value) is treated as unknown →
  no action, matching "unknown never acts".

## Housekeeping

I wrote one scratch file outside the roots, `/tmp/p545.chk` (a copy of `git diff` used
only to confirm `patch.diff` was current). It is harmless; I did not remove it since
cleanup is the harness's job.

## Open questions left for sign-off (from the brief, unchanged)

Threshold (OQ1), the reversal of the issue's first acceptance line and what to do with
#545 (OQ2, OQ6), and the DISCONTINUED case (OQ5) are the human's calls; the code follows
the brief's chosen answers.
