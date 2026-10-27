# Build notes — issue 727 (flow-in-batch-dependency-scoped-bases)

Base: `fcae4aa` (the run's line `pdca-integration/main-r547f8028520f`). Every "base" line
number below is on `fcae4aa`; "patched" line numbers are in the worktree with `patch.diff`
applied. Patch: 110,590 bytes, 10 files (2 production, 1 new test, 7 restated suites).

## What changed, and why

**Invariant restored** (brief): an in-batch bundle's base holds exactly the accepted work
of the bundles it is ordered after by a declared edge that this run built, and nothing
else of the run; empty set → the real base. Seams keep today's line base.

### `flow.py`

- **`_closure_members`** (patched `flow.py:913`). Walks `d`'s declared edges: `Depends
  on` + `Depends on (merged)` (transitively) and `Conflicts with` partners built in an
  earlier wave (either side declared it, `waves.conflict_map`, base `waves.py:136`). Only
  bundles this run built count (`built` = accepted this run, not held, with their wave).
  From `d` and each *member* every edge is followed (a member's branch was cut from a base
  holding its own closure, which `build_bundle_base`'s ownership rule needs —
  `integrate._unowned_work`, base `integrate.py:963`). From a built bundle that brought no
  branch to `d`'s target (closed with no patch, other target) only prerequisite edges are
  followed, and only if a prerequisite edge reached it (`Depends on` is transitive; `d`
  declared nothing about what a `Conflicts with` partner builds on). A bundle this run
  did not build is never walked — criterion (6b). An edge to an out-of-drive bundle that
  is not a finished named id is an out-of-batch prerequisite gated by its merge
  (`_runnable`, base `flow.py:681-847`), so its work is already on the real base.
  Returns the members (in accepted order), `[]`, or a seam reason string:
  - a walked bundle declares `Stacks on` or `Onto branch` (legacy, criterion 6);
  - a member's `publish.json` is an `Onto branch` (`"stacked"`) record —
    `_member_cut_point` refuses those (base `integrate.py:896-899`);
  - an edge of any kind from a walked bundle to a **finished named id** (`_finished_named`,
    base `flow.py:963`): carried, or finished with no patch (#728's job to make members);
  - a member that was itself built on the line (its branch holds the whole line below its
    own work, which no base of its own can own). Transitivity of the other rules already
    implies this; it is kept as a direct check.
- **`_bundle_bases`** (patched `flow.py:979`). Builds every base of the wave first
  (`integrate.build_bundle_base`, base `integrate.py:716`, with `carried=carried_heads`
  and `excluded=carried_heads`), then writes records: `publish.write_stack_base(d, branch,
  tip)` for an own base, `publish.clear_stack_base(d)` for `[]`, and
  `_point_at_integration(integ, [d], folded_tips)` (base `flow.py:890`, unchanged) for a
  seam — so a seam bundle gets exactly what it gets on `fcae4aa`. Records per base
  `(branch, {member: head the base took})` and, per seam bundle pointed at a line, a
  snapshot of the heads that line had taken.
- **Call site** (base `flow.py:2549` → patched `flow.py:2703-2716`). Only where the line
  folds for real (`own_bases = hold_unmerged`: publishing on, stack mode, not a dry-run,
  patched `flow.py:2637`); elsewhere `_point_at_integration` as before. A base that cannot
  be built prints one `STOPPING` line naming the bundle and members and stops the run
  (`line_stopped`), as a failed fold does (base `flow.py:2646-2652`). Holds for this are
  #725's.
- **Checks fed per-base heads**: the in-run fold gets `bases=` (published bundles only)
  and `line_prs=` (patched `flow.py:2816-2817`); the end-of-run check runs when the line
  *or* a base took anything (patched `flow.py:2860-2864`). `_line_prs` (patched
  `flow.py:1034`) names the PRs cut from the line after it took a head.
- **`_report_late_rewrites`** (base `flow.py:2701` → patched `flow.py:2876`). Prints one
  line per lost head; the line's unchecked line is today's text plus the PR names
  (`(issue_S after issue_A's)` / `(none)`); a separate unchecked line per cause for heads
  bases took (`flow: could not check whether a branch a bundle's own base took a commit
  from …`), naming branch, head and base. "rewritten" outranks "unchecked" for one name.

### `integrate.py`

- `build_bundle_base(..., merged_heads=None)` (patched `integrate.py:729`, `:880`):
  records the head each member put on the base once the push succeeded.
- `fold(..., bases=None, line_prs=None)` → `_carried_tips(..., bases, line_prs)` (base
  `integrate.py:514`, `:1025` → patched `:525`, `:1067`). Each branch's heads (line +
  each base) are judged once per distinct head (`_holds_took`, patched `:1158`), and a
  lost one raises `_rewrite_stop` (patched `:1118`): the line part is today's text
  byte-for-byte when no PR was cut from the line, plus "Every PR this run cut from L after
  it took H (issue_S) holds those old commits too." when some was; each base part says
  "`A`'s branch … was rewritten after `issue_B`'s own base `<branch>` took `H` …
  `issue_B` was built on `<branch>`, so `issue_B`'s PR holds commits … no longer has";
  the remedy ends "…, and rebuild issue_B's PR / the PRs of … on the rewritten branch".
- `rewritten_carried(..., bases=None, line_prs=None)` (base `integrate.py:1083` → patched
  `:1198`) returns `{name: [report, …]}` and `{name: [(ref, why, head, taker), …]}`. The
  line report (`_late_line_rewrite`, patched `:1271`) keeps today's wording
  (base `integrate.py:1129-1134`) and adds `(issue_S)`; with no PR cut from the line it
  says so instead of the vacuous "every PR this run cut from …". A base report
  (`_base_rewrite`, patched `:1187`) never says "the commit the line took" or "every PR
  this run cut from" (criterion 7). One fetch per target covers line and base records.

`_line_lacks_merge` / `merged.merge_and_head` / `merged.py` are untouched (criterion 8,
#729). No docs touched (#725).

## Alternatives ruled out

- **R1 — don't pass `carried` to `build_bundle_base`.** It would have kept the existing
  (1c) test green unmodified (B's base would take the rewritten tip; only the line would
  be reported). Rejected on the invariant, not cost: B would be built on a head the run's
  line never checked, and #723 added `carried` for exactly this call (base
  `integrate.py:736-739`).
- **R2 — on a base-build failure, fall back to the line.** Rejected: silently rebuilds
  the #630 shape for the bundles whose base is suspect. Stopping matches a failed fold;
  #725 turns both into holds.
- **R3 — carried bundles as members (v2's approach).** Out of scope (#728); it is what
  produced v1/v2's false stops and dropped transitive edges. Here any edge to a finished
  named id keeps the line, so the two v2 adversary repros (finished patchless `N` on
  resume) build `D` on the line holding `A`, not on a base missing it and not stopped.
- **R4 — name the line's PRs by git ancestry** (`took` ancestor of each line-cut tip)
  instead of snapshotting `carried_heads` when a bundle is pointed at the line. Cost of
  ancestry: one `merge-base` per (rewritten branch × line-cut bundle) inside
  `rewritten_carried`, a new `IntegrationError` path there, and no names at all in the
  fetch-failed `unchecked` path. The snapshot costs `_line_prs` (10 lines,
  patched `flow.py:1034-1043`) plus 3 lines in `_bundle_bases`. Same scope as today's
  "after it took {took}".
- **R5 — one combined report line per branch.** Rejected: operators and
  `test_integrate_carried_rewrite_late.py:71-74,206-213` find the line report by its words
  and expect exactly one; a separate line per base keeps the line's report as it was and
  lets each base name its own PR.

## Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner (`engine/scripts/run-verify.sh`,
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set) reported `PDCA-EVIDENCE: C4 PASS — red without the
  fix, green with it`. Red leg (production hunks reverted, tests kept): 11 of 15 new tests
  FAIL on assertions (no load failure); the 4 seam tests pass on the base by design
  (criterion 6 = "unchanged"). To prove those 4 bind the seam rule, I temporarily
  disabled the four seam `return`s in `_closure_members`: all 4 seam tests failed (plus
  the 2 (7) tests whose `S` is a seam), then restored.
- **(b) Production path? Yes.** Every case drives the real `flow._drive_and_act` with real
  `integrate.fold`, `integrate.build_bundle_base`, `_carry_finished`,
  `integrate.rewritten_carried` and real git (bare `origin`, primary checkout, scratch
  clone from `StackFoldGit`). Stubbed only what the brief allows: the build/sign-off leaf
  (`_drive_wave`), `_publish_bundle` (cuts from the recorded stack-base tip, as
  `test_flow_same_wave_conflict.py:131`), `publish.draft_texts`, and `gh`.
- **(c) Fixture includes the fault? Yes.** `Z` is a real two-commit bundle that the line
  really folds (asserted on the line) and that the old code really put on `fix/B`.
  Rewrites are real `git branch -f` / force-pushes on origin after the line and bases
  took the head. The fetch fault is a real failing `integrate._git("fetch")` armed by
  B's base's real push. The discontinued `A` is a real §9 `discontinue` record. Carried
  bundles are carried by the real `_carry_finished` (asserted "flow: carried …").

Other runs: full driver suite `PYTHONPATH=src python -m unittest discover -s tests`:
2569 OK (2 skipped, as on the base). T3 runner `run-suite.sh`: root suite OK (24),
driver suite OK. T2 `run-docs-check.sh`: clean.

## Criterion (8): every restated existing assertion, before → after

All restatements say what the base *contains*; none drops a content check. Where a
non-closure bundle used to be asserted "on the dependent's base" (only true because that
base was the line), it is now asserted on the run's line, which still holds it.

**`test_flow_merged_prereq_on_line.py`** — only `_built_on_line` (base `:191-198`).
Before: `base == self.line`, tip set, D COMPLETE. After: if W was built this run (callers
`:222`, `:230`): base is a branch on origin other than the line, origin's tip of it is
the recorded tip, it holds `fix/W`'s tip, and `rev-list --no-merges tip --not main
fix/W` is empty; else (carried prerequisite: `:269`, `:293` final part) `base ==
self.line` exactly as before. Hold tests and `:269` untouched.

**`test_flow_same_wave_conflict.py`** — `_built_on_line(iid)` (base `:169-178`, base ==
line, tip == line tip) → `_built_on(iid, *closure)`: base == `bundle_base_branch(…,
iid)`, tip == origin's tip of it, tip holds each closure head, nothing else beyond main
but merges. New `_on_line(*ids)`: the line tip holds them. `_run` stores `self.ids`.
- `:208-210` on21 on line holding 10, 12 → on21 own base {12}; 10, 12 on the line; 11
  not on on21 (unchanged).
- `:215-217` on30 on line holding 10, 12, 21 → on30 own base {21, 12}; 10, 12, 21 on the
  line; 11 asserts unchanged.
- `:253-257` 20, 21 on line holding 10, 11, 12; 30 on line → 20 own base {11}; 21 own
  base {12}; 10, 11, 12 on the line; 30 own base {21, 12}.
- `:275-278` on50 on line holding 40, 42, not 41 → on50 own base {42}; 40, 42 on the
  line; 41 not on on50, and (added) not on the line.
- `:309` on21 on line → on21 own base {12} (11 not on it, unchanged).
- `:425-427` on30 on line holding 20, not 22 → on30 own base {20, 10}; 20 on the line;
  22 not on on30, and (added) not on the line.
- Docstring `:12` "recorded line tip" → "recorded stack-base tip".

**`test_flow_resume_stack_prereqs.py`** — new helper `_on_own_base(iid, batch, *prereqs)`.
- `:281-284` W on the line, rejected not on its tip → W own base holding U; rejected not
  on W's tip (rejected not on the line, `:280`, unchanged).
- `:317` E's base == line → E own base holding D.
- `:347-350` W on the line, P not on its tip → W own base holding U; P not on W's tip.
- `:447-453` E and U on the line with X, not P/Q → E unchanged (carried X: a seam, on the
  line); U, which declares no edge, on the plain base (`_on_base("U")`).
- `:475-479` W on the line, P/Q not on its tip → W own base holding U; P/Q not on its tip.

**`test_flow_reissue_after_conflict_hold.py`**
- `:310-311` 12's stack base == line; `line_under_12` = its tip → 12's stack base ==
  `bundle_base_branch(…, "issue_12")`; `line_under_12` = its recorded tip, which (added)
  holds 10's head. Later uses (`:340`, `:451`) unchanged.
- **Input change**: `_held_for_10` gains `on="12"` (`:150`, `:162`, default keeps every
  other caller identical); `test_one_the_fold_merges_after_it_is_named_too` (`:240-252`)
  passes `on="12, 10"`. Before: 21 declared only `Depends on: 12` yet its change sat on
  top of 10's (true only because it was cut from the line holding 10). After: 21 declares
  the 10 it builds on, so its own base holds 10. Without it, 21 is built without 10 and
  conflicts with 10 at the re-issue's carry, which is a different scenario than the test
  is about. All assertions unchanged.

**`test_flow_conflict_partner_hold.py`** — **input (fixture) change**: with
`stub_fold=True` (no git checkout in the temp dir) `integrate.build_bundle_base` is
stubbed too, as the other git step that merges pushed branches (`:151-158`). Assertions
unchanged.

**`test_flow_slice.py`**
- **Input (fixture) change**: `_live(fold=…)` stubs `build_bundle_base` beside the fake
  fold (`:1338`, `:1360`); the 3 spy-fold cases' assertions are unchanged.
- `_update_from_main` (`:1572-1578`) removed (no caller left); `_own_base` added.
- `test_a_three_wave_run_folds_append_only_onto_a_real_origin` (`:1580-1627`): EB cut
  from the line → EB from its own base holding EA only, EC from its own base holding EB
  and EA; "EB~1 (the first fold's tip) is on the line" → the first fold's tip, recorded
  by the fold spy (fixture: a `tips` list), is still on the line; `git log --merges line`
  count of the EA merge == 1 → same count on the line's `--first-parent` chain (EB's
  branch now brings its own base's EA merge); 2 pushes, first forced → the line's pushes
  only (bases push too): 2, first forced, second not.
- `test_a_dependent_carries_every_earlier_wave_branch_not_only_its_prerequisite`
  (`:1629-1661`) renamed `…_carries_only_its_prerequisite_not_every_earlier_wave_branch`.
  It pinned the #630 defect itself. Before: ZB cut from the line; ZZ on ZB; diff = ZA,
  ZB, ZZ; after ZA merges: ZB, ZZ; after ZZ merges two merge bases, fixed by "Update
  branch". After: ZB from its own base holding ZA only; ZZ not on ZB; diff = ZA, ZB;
  after ZA merges: ZB; after ZZ merges one merge base (ZA) and diff ZB with no update.
  This is criterion (1) on a real origin, so it is the inverse of the old assertion.

**`test_integrate_carried_rewrite_late.py`** — in a two-wave run the run's last read of
`fix/A` is now B's own base, not the line's fold.
- **Input change**, `test_a_rewrite_during_the_last_fold_is_reported_and_exits_1`
  (`:258-275`): the rewrite fires just before B's base's push instead of the line's.
  Assertions unchanged (line holds A's head, not the rewrite; exactly one line report, no
  STOPPING; rc 1).
- New `test_a_rewrite_during_the_lines_fold_stops_the_run_at_the_dependents_base` keeps
  the old trigger: the run stops at B's base on one STOPPING line naming B's base, the
  rewrite and A's head; rc 1.
- **Input change**, `test_an_end_of_run_check_that_cannot_fetch_is_named_and_exits_1`
  (`:279-306`): fetches fail after B's base's push instead of the line's. `len(pushed) ==
  1` ("the run's last") → pushes == [line, B's base]. Other assertions unchanged.
- New `test_a_fetch_failing_after_the_lines_fold_stops_the_run_at_the_dependents_base`
  keeps the old arming: stop at B's base naming the fetch; rc 1.

## Behaviour changes the human should know about

- **A base that cannot be built stops the run** (one `STOPPING` line with #723's error,
  e.g. a member rewritten since the line took it, or a fetch failure). Same as a failed
  fold today; holds are #725.
- **Undeclared cross-wave overlaps now stop at the next line fold.** A bundle no longer
  built on unrelated earlier-wave work can conflict with it when the line merges it. That
  is the "cross-wave overlaps" hold the brief gives to #725.
- **Seams are conservative.** Any edge (including `Conflicts with`) from a walked bundle
  to a finished named id keeps the line, even a finished id with no patch; and a bundle
  that itself declares `Stacks on` / `Onto branch` keeps today's base.
- **PR naming scope.** "PRs cut from the line after it took H" names bundles cut from the
  line when its record for that branch was exactly H, as today's wording implies; a PR
  cut at an older head of the same branch is not named.
- **PR shape** (brief): until #726 merges, this PR's diff against `main` also shows #723.

## Housekeeping

- Early in the session I wrote two scratch files outside the allowed roots:
  `/tmp/claude-suite1.txt` (a list of failing test names) and `/tmp/claude-prod.diff` (a
  copy of the production diff, used once for the first red check). I can't remove them
  (no `rm`); after that I used a local commit in the worktree instead (since reset:
  the worktree is `fcae4aa` plus uncommitted changes, and `patch.diff` matches it byte for
  byte).
- No formatter, linter or commit hook is configured in the target (no
  `.pre-commit-config.yaml`, no ruff/flake8 config, only sample hooks); `git diff --check`
  is clean and no added line is longer than 100 characters. The target's commit rule is
  DCO sign-off, which publish adds.
- External dependencies: none beyond Python 3.11+ and git.
