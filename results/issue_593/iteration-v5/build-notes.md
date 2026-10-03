# Build notes — issue 593, iteration 5 (stack-mode-append-only-fold-real-base-prs)

Target: eduralph/pdca-harness @ main, base commit `24c7f83`. Worktree:
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, left at `24c7f83` with the patch applied and
uncommitted (its diff equals `patch.diff` byte for byte). Line numbers below are in the
patched tree unless marked "base".

## Starting point, and what I read

The iteration-4 sign-off keeps the design and says "rebuild only to fix these", and its
carry-forward cites lines of the previous patch (`patch.diff:744`). So I applied
`iteration-v4/patch.diff` (clean on `24c7f83`) as the starting point and changed only what
the carry-forward names. Beyond `brief.md` I read: `iteration-v4/patch.diff`,
`iteration-v4/build-notes.md`, `iteration-v4/session-carry-forward`, the two advisory files
(`check-advisory-adversary.md`, `check-advisory-code-review.md`) and SUMMARY §6/§9, because
the carry-forward items are short summaries of those findings. Baseline before any change:
the four touched test modules ran 175 tests, all green, on the v4 code.

To prove the new tests fail on the v4 code (not only on `main`), I kept v4 as a throwaway
local commit, swapped its production files back in, ran the new tests, and swapped mine back.
Those scratch commits were reset away at the end; nothing was pushed.

## Item 1 — a late `pdca publish` of a held wave>0 bundle shipped later waves into main

Cause: the stack-base marker recorded only the integration branch name, so publish cut the PR
branch from `origin/<line>` as it is at publish time (base `publish.py:246`, v4 `:247`). For a
bundle held in wave k and published after the run, the line by then holds every later wave.

Fix:
- The marker gets an optional second line: the line commit the run's last fold pushed, i.e.
  the commit the bundle is built on. `write_stack_base(d, branch, tip=None)`
  (`template/src/pdca_harness/publish.py:618-624`), read by `_stack_marker`
  (`publish.py:635-641`). The first line is still the branch, so `_read_stack_base`
  (`publish.py:644-646`), `read_stack_base`, `_stack_base_branch` (`publish.py:660-669`), Do's
  worktree base and `$PDCA_VERIFY_BASE` are unchanged, as (vi) requires. A marker with no tip
  (dry-run, or written before this change) behaves exactly as before.
- The flow records it: `_point_at_integration(integ, runnable, tips=None)`
  (`template/src/pdca_harness/flow.py:722-741`), called with the run's `folded_tips`
  (`flow.py:1812`). Those tips are read right after each fold (`flow.py` fold call, unchanged
  from v4).
- Publish cuts a wave>0 bundle from that commit when recorded (`publish.py:254-257`). In-run
  it is the same commit as `origin/<line>` (folds only happen after a wave's publish), so
  nothing changes for a normal run; a late publish no longer picks up later waves.

Regression (real git, real `publish.publish`):
`template/tests/test_flow_slice.py:1703-1732`
(`test_a_held_bundle_published_later_is_cut_from_the_line_it_was_built_on`). Waves
{LA} → {LU, LJ} → {LK} → {LL} against a bare origin that refuses non-fast-forwards; LU's
publish fails (held); the run folds [LA, LJ] then [LA, LJ, LK]; then LU is published for real
with `open_pr=False`. Asserts LK's tip is not an ancestor of LU's PR branch and
`main...<LU branch>` is exactly `issue_LA.txt, issue_LU.txt`.
- On the v4 code: `AssertionError: True is not false : LU's PR branch carries LK`. With the
  two assertions swapped (probe, undone) the diff is
  `['issue_LA.txt', 'issue_LJ.txt', 'issue_LK.txt', 'issue_LU.txt']` — the sign-off's repro.
- Undoing only the publish cut (`publish.py:254` → `if False:`) or only the flow passing the
  tips (`flow.py:1812` without `folded_tips`): same failure (probes, undone).
- On `main` it fails at `assertTrue(self._in_line(lk))`: the old fold re-applies patches, so
  LK's own commit is never on the line.

Options weighed (line counts are the patch's):
- (A, chosen) a second line in the existing marker: ~10 lines in publish.py, ~7 in flow.py.
  One write replaces branch and tip together, so they cannot get out of step.
- (B) a separate `stack-tip` file: the same reader/writer, plus `clear_stack_base` removing
  two files and `write_stack_base(d, branch)` deleting a stale tip so an older run's tip can't
  pair with a newer branch (~6 more lines and a pairing rule kept by hand). Rejected.
- (C) also build Do and the verifier on the tip (`worktree._target`, gates.py `:568-570`):
  2 more lines, but `$PDCA_VERIFY_BASE` would become a SHA instead of `origin/<branch>`, which
  (vi) says stays unchanged and `tests/test_verify_base.py` pins. In a run, Do and Check
  already see that same commit. Not done; see Known limits.
- A test-only pin that the tip never leaks to the other readers:
  `test_flow_slice.py:1237-1248` (`test_stack_base_file_round_trips`).

## Item 2 — the hold keyed on any non-zero publish exit code

Cause: v4 held a bundle whenever publish returned non-zero (v4 `flow.py:1835-1837`). Publish
returns 1 after pushing the branch and writing a fresh `publish.json` when `gh pr create`
fails (base `publish.py:355-400`: the push is the last step of `:355-361`, `gh pr create`
runs at `:366-381`, the record is written at `:394`, then `return 1` at `:399-400`), e.g. an
iterated bundle whose old draft PR is still open.

Fix: `_publish_bundle` now returns whether this call pushed a branch
(`flow.py:642-664`): rc 0 (a real publish exits 0 only after its push), or a `publish.json`
that this call rewrote, compared by `(mtime_ns, bytes)` before and after
(`_record_stamp`, `flow.py:667-674`). Publish writes that record only after the push
succeeds, on both the new-PR path (base `publish.py:394`) and the `Onto branch` path
(base `publish.py:510`). Iteration 2's guard stays: a record an earlier run left is not
rewritten by a failed publish, so it never counts; texts-not-ready still holds
(`flow.py:1863-1867`). Renamed the set to `not_pushed` (`flow.py:1710-1712`), the hold
message to "pushed no branch this run" (`flow.py:1894`), and updated the wording in
`_runnable`'s docstring, `integrate.unpublished`'s docstring, docs 07 `:662-666`, spec 09
`:69` and `pdca.toml.jinja:122-123`.

Regression: `test_flow_slice.py:1674-1701`
(`test_a_re_publish_whose_pr_create_failed_is_folded_and_its_dependents_build`), next to the
stale-republish test. An earlier run's branch and record (with an open PR URL) exist; this
run's publish re-pushes the branch with `--force-with-lease` (as publish does), writes a fresh
record, returns 1. Asserts PD (depends on PP) is COMPLETE, no STOP, the new tip is on the line
and the old commit is not. v4: `'PLANNED' != 'COMPLETE'`. Undoing only the stamp check
(`return rc == 0`, probe): same failure. `main`: "this run's pushed branch was not folded".
The existing stale-republish test (`:1649-1672`) still holds the bundle; its setup moved into
a shared helper `_earlier_attempt` (`:1520-1533`). `_push_branch` now pushes with
`--force-with-lease` like publish (`:1513`); every other test pushes new branches, unaffected.

Options weighed:
- (A, chosen) the record stamp: ~12 lines in flow.py, no contract change.
- (B) a new publish exit code (2) for "pushed, PR not opened": ~2 lines, but it changes the
  exit code of `pdca publish` (`cli.py:488`) and `pdca signoff --accept` (`cli.py:1492-1497`)
  for that failure, a user-visible contract nothing here asks to change. Rejected.
- (C) delete `publish.json` before publishing and restore it on failure: mutates the bundle
  mid-publish, and a crash in between loses the record of the still-open PR that
  `cli._publish_flag` and `merged.is_merged` read. Rejected.
- Content-only comparison: an identical earlier record (same branch, date, empty `pr_url`)
  would read as "not pushed". Adding `mtime_ns` closes that; if both ever matched, the result
  is a conservative hold, never a wrong fold.

## Item 3 — needless STOP on a gone-and-merged branch already on the line

Cause: v4 merged the base into the line for any gone-and-merged branch (v4 `integrate.py`
`:376-377`, `:398-413`), even when this run had already folded that bundle, so an unrelated
clash on the base stopped the run.

Fix: `_gone_branch` (`template/src/pdca_harness/integrate.py:399-424`). On a line this run
alone built — a continued fold of a listed target (`this_runs_line`, passed at
`integrate.py:353-354`) — it skips a bundle whose `pdca-integrate: <bundle>` merge is on the
line's first-parent history past the base (`_merges_past`, `integrate.py:427-436`). Every
fold merge sits on that chain, and within one run each bundle is published at most once
(the `published` set, `flow.py:1709`, `:1831`, `:1868`), so that merge is of this run's
branch. Only otherwise does it
take the base in (`_take_in_base`, `integrate.py:439-455`). A `git log` failure there is a
failed git step (raises), same as v4's `_in_line` rule.

Why not on an "auto" line (`folded_this_run=None`, direct callers): that line may be an
earlier run's, whose `pdca-integrate:` merge could be an older, rejected attempt of the same
bundle. There the fold still takes the base in, which can only stop loudly, never skip
silently.

Regression: `template/tests/test_integrate_stack_bases.py:305-324`, the sign-off's exact
recipe: fold [A, C] → T1; merge `fix/A` into main with a merge commit, delete it; land a
clashing `c.txt` on main; fold [A, C] with `{TARGET: T1}`. Asserts success, the "already
carries it" line, and the line tip is still T1 (no base merge). v4 and the probe
(`integrate.py:414` → `if False and …`): `IntegrationError … conflicts in c.txt`. `main`:
`TypeError` on the new keyword (accepted by the brief for cases that pass it).

Option weighed: have the flow pass the names it already folded. That needs a second fold
keyword or a different value type for `folded_this_run`, both of which the brief fixes, plus
~10 lines of bookkeeping, and the fold would trust a list instead of reading the line itself.
Rejected.

## Item 4 — an `Onto branch` record on the merged-and-gone path

Fix: `_published_ref` now returns `(remote, ref, onto)` (`integrate.py:105-124`); `onto` is
True only for a `"stacked"` record. `_gone_branch` raises for such a record instead of taking
the base in (`integrate.py:418-423`), naming the bundle, the ref and "Onto branch". Order: the
"already on this run's line" skip comes first. Such a record's work is then on the line
whatever base the other PR merged into, so no claim about the base is made, and raising
there would be the same needless stop item 3 removes. The raise covers exactly the code
review's case: the fold claiming the base carries work it may not.

Regression: `test_integrate_stack_bases.py:326-352`. Upstream branch `feat`, record
`{"mode": "stacked", …}`; fold → T1; delete `feat` on upstream; a continued fold skips it
(tip still T1); a new run's first fold raises naming `issue_S`, `upstream/feat` and
"Onto branch", nothing pushed. v4 and the probe (`if onto:` → `if False:`):
`IntegrationError not raised`.

## Item 5 — stale text

- `gates.py:535-541`: publish cuts the PR branch from the line commit it was built on; the PR
  targets the real base.
- `publish.py:42-46` (marker comment), `:618-624` (`write_stack_base`), `:627-632`
  (`clear_stack_base`), `:660-669` (`_stack_base_branch`): no longer say the PR opens against
  or "on" the integration branch.
- Also checked: `waves.py:73` and `brief.py:232` describe the legacy `Stacks on` PR, which
  still uses `--base <parent>` (unchanged by design); `drift.py:53` describes where the patch
  was applied, still true. Left as they are.

## Optional code-review cleanups (all done)

- Prune only remotes holding PR branches: `_prepare_worktree` (`integrate.py:486-509`) fetches
  `origin` and the `"stacked"` records' remotes with `--prune`, the base remote without.
  (Own-repo: the base remote is `origin`, which holds PR branches, so it is pruned.)
- Slug carried through `_targeted`/`_fold_candidates` (`integrate.py:127-135`, `:200-208`),
  so the dry-run fallback (`integrate.py:269-277`) no longer re-resolves the target.
- Stack marker read once in publish (`publish.py:233-234`); the legacy parent lookup is split
  into `_stacks_on_branch` (`publish.py:672-678`), and `_stack_base_branch` keeps its contract.
- Strengthened `test_a_gone_branch_whose_pr_merged_is_skipped`
  (`test_integrate_stack_bases.py:293-303`): asserts the stderr line and that the pushed line
  is the base. It passes on v4 (that behaviour was already right) and fails on `main`.

Test spy updated: `test_flow_adopt_split.py:268-270` forwards the new third argument of
`_point_at_integration`, as the brief asks for spies on `fold`.

## Gates run with the project's runners

- C4 `engine/scripts/run-verify.sh` (PDCA_BUNDLE + PDCA_WORKTREE): `PDCA-EVIDENCE: C4 PASS —
  red without the fix, green with it`. Green: 29 / 108 / 14 / 28 tests OK
  (test_flow_adopt_split, test_flow_slice, test_integrate, test_integrate_stack_bases). Red:
  test_flow_adopt_split 29 OK (spy signature only), test_flow_slice 9 failures + 1 error,
  test_integrate 1 failure, test_integrate_stack_bases 17 failures + 9 errors. All five new
  tests, the strengthened one and the round-trip pin (the 1 error in test_flow_slice) are in
  the red set. In test_integrate_stack_bases the two cases that pass on both legs do so by
  design (`test_the_fork_path_is_unchanged`, `test_a_legacy_stacks_on_parent_keeps_its_branch_base`).
- T3 `engine/scripts/run-suite.sh`, run twice, the second time on the final tree after the
  last test-only edit: root suite 24 tests OK (copier ran), driver suite 2253 tests OK
  (2 skipped, pre-existing); `PDCA-EVIDENCE: root suite OK, driver suite OK` both times.
- T2 `engine/scripts/run-docs-check.sh`: docs lint clean, site render + link audit clean
  (the host-CI row runs the same two checkers).
- C5 `engine/scripts/run-prod-path.py`: "1 added driver-suite test(s) import the production
  package 'pdca_harness'".
- T4 is deferred to publish (no contribution texts at Do).

## Refuting my own tests

(a) Genuine red? Yes. The C4 gate reverted every production hunk and the new tests failed or
errored, with no import failure (the new module imports only `integrate, publish, signoff`,
present on `main`). Against the v4 code each new test fails for its item's reason (quoted
above). And each fix undone alone on top of the final code makes its own test fail: item 1
(publish cut, and separately the flow passing tips), item 2, item 3, item 4.

(b) Production path? Yes. Every case calls the real `integrate.fold`, the real
`flow.flow_ids` driving the real fold, or the real `publish.publish` (item 1's late publish
runs its real git steps: fetch, `checkout -B` at the recorded commit, apply, signed commit,
`--force-with-lease` push) against real git. Replaced: `merged.is_merged` (shells `gh`; no
network), the Do/Check drive (`_accept_wave` accepts with a real patch), the in-flow publish
(cuts, commits signed off and pushes the branch the way publish does, writing the same record
shape), and `_warn_if_squash_only` (a `gh repo view` warning). These are inputs to the code
under test.

(c) Fixture includes the fault? Yes. Item 1: a real held bundle, real later folds that grow
the line past it, a real publish afterwards. Item 2: a real earlier branch and record, a real
forced re-push, rc 1 after the record is written (publish's real failure shape). Item 3: a
real merge into main, a really deleted branch with a stale tracking ref (`fetch.prune false`,
so the fold's own `--prune` removes it), and a real conflicting `c.txt` on main. Item 4: a
real second remote whose branch is really deleted after the first fold.

## Commit-ready

The target has no formatter or linter config (no pyproject/setup.cfg/flake8/ruff/pre-commit
in the root or `template/`), and no git hooks are installed. CONTRIBUTING.md asks for DCO
sign-off and green suites (both above). No added Python line is over 100 columns (the base
files go to 106).

## Size

`patch.diff` is 151,704 bytes = 148.1 KiB over 15 files, above this instance's
`[driver.size_signal] patch_kb = 125` (v4 was 123.7 KiB). The rounds rule fires anyway: three
iterate-to-Do rounds since the v1 re-plan (v2, v3, v4) against `rounds = 3`, so sign-off sees
the size item whatever the byte count. I did not trim tests to get under the line. Of the
~25 KB added since v4, ~15.5 KB is production and comment hunks (flow.py +4.2, publish.py
+6.1, integrate.py +3.5, gates.py +1.6; much of it diff context around small edits), ~9.2 KB
is tests (the five regressions, the round-trip pin, the shared helper, the spy), and ~0.3 KB
docs. The Plan decision "no split" still applies: every remaining item is a fix inside the
same accepted design.

## Known limits, for sign-off

- Re-Do or re-gate of a wave>0 bundle after the run: Do's worktree and the verifier use
  `origin/<line>` (unchanged, per (vi)), which may have moved, while publish cuts from the
  recorded commit. If the rebuilt patch does not apply there, publish fails loudly at
  `git apply`; it never cuts from the moved line. Inside a run the two are the same commit.
- Gone-and-merged on a continued line is recognised by its `pdca-integrate: <bundle>` merge.
  A bundle the line carries without a merge of its own (its branch was already an ancestor
  when folded, e.g. two `Onto branch` records on one PR branch) falls through to the base
  merge (its work does reach the line, though that merge can hit a needless clash and stop)
  or, for an `Onto branch` record, to an IntegrationError. Never a silent skip.
- If a folded PR got extra commits after the fold and then merged with its branch deleted,
  the skip keeps the folded tip's work on the line; the extra commits reach later waves only
  through the base.
- If publish pushes and then raises before writing its record (e.g. `gh` missing at
  `gh pr create`), the bundle is held although its branch was pushed: conservative, never a
  wrong fold.
- `merged.is_merged` shells `gh` without a guard, as `merge.py` does; `gh` is a required
  doctor row here.
- Carried from the brief, still owed at sign-off: the live-host check on a disposable GitHub
  repo (External dependencies), the vendored-spec edits to 09 and 08 (NEEDS-HUMAN by
  INTEGRATION §4).
