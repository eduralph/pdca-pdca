# issue_728 — build notes (Do)

## Base

Worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, detached at `c423f9d`
("pdca-integrate: issue_727"), the fold of #727's accepted result onto
`pdca-integration/main-r547f8028520f` (the bundle's `stack-base` / `stack-base-tip` name
that line at `c423f9dc…`). `$PDCA_VERIFY_BASE` was not set in my environment; the
worktree was already on the fold. All `path:line` below are on that tree: "base" means
`c423f9d`, "patched" means `c423f9d` + `patch.diff`. `patch.diff` applies cleanly to it
(`git apply --cached --check`).

## What changed (production: `template/src/pdca_harness/flow.py` only)

1. **The closure walk runs over one graph that includes finished bundles**
   (`_closure_members`, patched `flow.py:913-957`). The parameter `built` becomes `graph`:
   the bundles this run built (their wave) plus, at wave -1, the finished named ids the
   carry put on the line and the finished ids with no patch. The `finished` seam is gone
   (base `flow.py:947-949`: `if n in finished: return "... finished in an earlier run"`).
   Edges to anything outside the graph are not followed (patched `flow.py:949`). Members
   are still filtered by `on_target`, which comes from `integrate._fold_candidates` and so
   never holds a patchless bundle: patchless nodes are walked, never members. The seams
   left are exactly `Stacks on` / `Onto branch` on a walked bundle and "a member pointed
   at a seam itself" (both unchanged).
2. **`_bundle_bases` builds that graph and holds carried members to their carried heads**
   (patched `flow.py:960-1006`). Graph: patched `:984-988`. `heads = {**carried,
   **carried_heads}` (`:989`) goes to `integrate.build_bundle_base` as both `carried=` and
   `excluded=` (`:1004-1006`; base `:995` passed `carried_heads` only). So:
   - a carried member rewritten after the carry is refused by `build_bundle_base`'s
     existing #633 check (`integrate.py:836-844` → `_lost` `:1077` →
     `_carried_rewrite` `:1172`, raising `_Rewritten`) — criterion (5);
   - a carried member whose branch brings in work below its recorded cut point is
     refused by `_unowned_work` (`integrate.py:988`) → `_foreign_refusal` (`:1008`,
     raised at `:869`), and the carried bundle whose head reaches that work is named
     because it is now in `excluded` — criterion (4).
3. **`_carry_finished` reports what it carried** (patched `flow.py:1222-1225`, docstring
   `:1264-1266`, fill at `:1345-1346`): new optional out-param `took`, filled with
   `{name: heads[name]}` for each id actually carried (not red, target folded). `heads` is
   the PR head `_finished_head` (`flow.py:1107`) judged clean and that the carry already
   hands its fold as `pr_heads`.
4. **`_drive_and_act` wires it** (patched `flow.py:2614-2622`, `:2707-2710`):
   `carry_took` is filled by the carry and passed as `carried=` to `_bundle_bases`.
5. **The carry's stderr line** (base `flow.py:1332`, patched `:1347-1350`) said "this
   run's … bundles build on it" (the line). Now: "bundles ordered after them build on a
   base that holds them" — true both for own bases and for seams. Every assertion on that
   line matches its unchanged prefix `flow: carried issue_X (finished`.
6. **Briefless guard** (patched `flow.py:985-987`): a finished bundle with no patch and no
   `brief.md` (a pre-#481 split parent can be COMPLETE that way, #597) stays out of the
   graph. Without the guard, the walk's `brief.stacks_on` raises `FileNotFoundError` out of
   the whole run (I reproduced it: the frames run `_drive_and_act` → `_bundle_bases` →
   `_closure_members` → `brief.parse_fields`). #727 never read a finished bundle's brief
   because it returned a seam on the edge itself. Such a bundle declares no edges, so
   leaving it out of the graph gives the same members as walking it.

`integrate.py` is unchanged. #723's refusals already do what (4) and (5) need, as the
brief expected.

## Decisions and what I ruled out

**Which head counts as "carried".** Two sources:
- (chosen) the PR head `_finished_head` returned: the head the carry judged clean,
  accounted origin's line with (`foreign_commit`), and handed the fold as `pr_heads`.
  Cost: +3 lines in `_carry_finished`, no `integrate.py` change.
- (rejected) the fold's own record: pass a fresh dict as `carried=` to the carry's
  `_fold_lines`. That is a 1-line flow change and the fold records it with no code
  change. But `integrate.fold`'s docstring (`integrate.py:460-461`) says "``None`` (the
  pre-wave carry, a direct caller) checks and records nothing". It would go stale or need
  a docstring edit in `fold`, which is outside the functions the brief allows in
  `integrate.py`.
- The difference only shows if the branch moves in the moment between the carry's
  `gh pr view` and its fold's fetch. If it moved forward, the line holds a descendant of
  the recorded head, and a later rewrite that keeps the PR head but drops the newer
  commits goes unseen at the dependent's base. That rewrite only matters for the line,
  and the line already has no rewrite check for carried bundles (see residuals). If it
  was rewritten in that moment, the dependent's base is refused as "rewritten after this
  run folded it": a stop, never a wrong base.

**`Conflicts with` between two finished bundles.** All finished bundles sit at wave -1,
so the partner rule (`graph[n][1] >= wave`) never follows a partner edge from one
finished bundle to another. Which of the two an earlier run built first is unknown here.
- Following it could silently add unrelated work to a base.
- Not following it can at worst stop the run: if a carried member's branch holds the
  partner's work below its cut point, `_unowned_work` refuses and names the partner.
- Rejected alternative: replay the scheduler's orientation (`waves.py:200-212`:
  name-lower first unless a dependency path orders them). That needs the
  earlier run's dependency graph rebuilt from the finished briefs: about 15 lines plus
  `waves._reaches`, on the guess that the earlier run had the same batch. No criterion
  needs it.
- Partner edges from a built bundle or from `d` to a finished one are followed (wave -1
  is before every wave), as #727 does for earlier waves.

**A finished id with a patch that the run did not carry.** Its edge leaves the graph,
like an out-of-batch prerequisite. It is not a stop. Reasons:
- a direct plain `Depends on` to a held one is already held by `_runnable`
  (`flow.py:803-806`);
- a direct `Depends on (merged)` reaches `_bundle_bases` only once `_runnable` judged it
  merged into the base (`flow.py:780-796`), so stopping there would be a false stop;
- the brief's invariant scopes bases to "the declared closure the run built or carried".

Residual: an id reached only through a finished patchless node, whose target the carry
never triggered for (no drive-set bundle names it in a plain `Depends on`), is not on the
dependent's base. That is the same content as before this change: #727's seam put the
dependent on a line that did not hold it either, or on the real base. Closing it means
extending the carry's trigger, `_carry_finished`'s `dependents` (`flow.py:1270-1275`), to
follow patchless nodes, and `_runnable` to hold through them. That is outside this
brief's scope (`_runnable` belongs to #729). Proposed as a follow-up.

**Not touched (per scope):** `_runnable` and its merged-prerequisite branch
(`flow.py:681-847`, #729); `line_cut` for seams (`flow.py:1016`) still records only
in-run line heads, since adding carried heads there changes no check (the end check
judges `accepted` only).

## Restated assertions (before → after)

All are about where a dependent of a carried bundle was built. Each is restated in
content: own base branch, holding the same prerequisite commits and lacking the same
excluded ones. Line assertions (`_has(self.line)`, line tips, carry messages) are kept.

`template/tests/test_flow_resume_stack_prereqs.py` (base → patched):

| Base line | Before | After (patched) |
|---|---|---|
| `:203-207` (test 1) | `base == line`, `tip == line_tip`, fix/P on line_tip, COMPLETE | `:210` `_on_own_base("D", …, "P")` (own branch, tip = origin tip, fix/P ancestor, COMPLETE); line_tip not None and holds fix/P kept (`:211-213`) |
| `:221,225` (test 2) | `_built("D")[:2] == (line, old)`, COMPLETE | `:227` `_on_own_base("D", …, "P")`; `:228` the line D was built beside is still `old`; no-force/`old` ancestor checks kept |
| `:236` (test 3) | D `(line, carried)` | `:243` `_on_own_base("D", batch, "P")`; `carried` = line tip then (`:244`) |
| `:237-238` (test 3) | `len(pushes) == 2`, `pushes[1]` no `--force` | `:245-247` the pushes **to the line** are 2 and the 2nd has no `--force`; plus `:248-250` the other pushes are exactly D's then E's own bases |
| `:240,243` (test 3) | E `(line, e_line)`, COMPLETE | `:251` `_on_own_base("E", batch, "P", "D")`; `e_line` ancestry checks of carried/P/D kept as line assertions (`:252-254`) |
| `:276,279` (test 4c) | B `(line, line_tip)`, fix/Q on line_tip, COMPLETE | `:286` `_on_own_base("B", …, "Q")` + `:287` B's base lacks fix/P; `:288` fix/Q on the line tip then; `:289` line lacks fix/P kept |
| `:458-463` | E `(line, line_tip)`, fix/X on tip, P/Q not on tip, COMPLETE | `:469` `_on_own_base("E", …, "X")`; P/Q not on E's base kept (`:470-471`) |
| `:543` (`_carried_beside`) | `len(pushes) == 1` | `:552-554` pushes are exactly `[line, E's own base]` (line once, as before) |
| `:546-551` (`_carried_beside`) | E `(line, line_tip)`, fix/X on tip, COMPLETE; returns line tip | `:558` returns `_on_own_base("E", batch, "X")` (E's base tip); callers' `_off_the_line(commit, e_tip)` now check line **and** E's base |

Also in that file (not in the brief's list; flagging it):
- **Fixture fix** `_publish_bundle` (base `:122-128`, patched `:126-135`). The fixture's
  `fx._publish` rewrites `brief.md` without its `Depends on` line. Real publish never
  writes the brief: `publish.py` writes only `publish.json` and the stack-base files
  (`publish.py:440,556,656,658`). #727's own fixture leaves the brief alone
  (`test_flow_dependency_scoped_bases.py:135-164`). With the edge erased, test 3's E
  (`Depends on: D`, D built on carried P) walked to D but not to P, and the run stopped
  on P's commit as unowned. Before this change that was hidden: D was a seam, so E fell
  back to the line too. The fix keeps the brief as it was.
- Test rename at `:204`: `…_is_on_the_line_its_dependent_builds_on` →
  `…_is_on_the_base_its_dependent_builds_on`. Module docstring: "pushes once" becomes
  "pushes its line once", and a new paragraph (`:17-21`).

`template/tests/test_flow_merged_prereq_on_line.py`:
- Helper `_built_on_line()` (base `:191-210`) had an `else: base == self.line` branch for
  a carried prerequisite. It becomes `_built_on_own_base(prereq)` (patched `:191-206`):
  always own base `{line}-bD`, tip = origin tip, holds `fix/<prereq>`, and beyond main
  only merges and that branch. The callers at base `:239`, `:247` and `:322` pass `"W"`,
  same checks as before. Base `:297` passes `"P"`.
- Base `:298` `tip == old` (the brief's `:269` anchor on `fcae4aa`) and `:300` `merge_oid
  not on tip`. These were facts about the line D was cut from. They are kept as line
  facts: patched `:296` the line is still at `old`, `:297` fix/P is on `old`, `:298`
  merge_oid is not on `old`. That is what #655's check judged D against. D's own base
  starts at main, so it does hold the merge, and the test now says so (patched `:295`).
  This is the one assertion whose truth value flips (merge on D's base). I'm noting it
  so the reviewer sees it's deliberate.
- The two comments on how D is built were updated (`:281-283`, `:306-308`).

`template/tests/test_flow_dependency_scoped_bases.py` (#727's suite; not in the brief's
list, because the brief was written before #727's tests existed — flagging it):
- Base `:375-390` `test_a_dependent_of_a_carried_bundle_keeps_the_line`: `_on_line("D")` +
  P, X on tip → patched `:375-388`
  `test_a_dependent_of_a_carried_bundle_is_built_on_a_base_holding_it`:
  `_own_base("D", "P", "X")` (same COMPLETE and full P/X content checks).
- Base `:392-407` `test_a_conflicts_with_partner_that_was_carried_keeps_the_line`:
  `_on_line("D")` + K, X on tip → patched `:390-403`
  `…_carried_is_on_the_base`: `_own_base("D", "K", "X")`.
- These two tests pinned exactly the fallback the brief removes. They move under a new
  header `(6a)` (patched `:373`). The `(6)` seam header (now `:405`) and the
  `Onto branch` / `Stacks on` seam tests below it are unchanged.

Unchanged: everything in `test_integrate_carried_rewrite_late.py`, and `:348` on
`fcae4aa` (test 8's W, already an own base since #727).

## The new test — `template/tests/test_flow_carried_prereq_bases.py`

It uses real git on `StackFoldGit` through `flow._drive_and_act`, like #727's suite. Its
`_publish_bundle` leaves the brief alone. Only modules are imported.

| Criterion | Test | Pre-fix (red) | Post-fix |
|---|---|---|---|
| (1) | `test_each_dependent_of_a_carried_bundle_holds_only_its_own_prerequisite` | fails first on `fix/D` holding X (D built on the line) | D's base and fix/D hold P not X; E's the reverse; both COMPLETE; the line holds both |
| (2) | `test_a_resume_through_a_finished_patchless_bundle_carries_its_prerequisite` | D's recorded base is the line | D, W on own bases holding A; fix/D holds A; COMPLETE |
| (3) | `test_a_resume_through_a_finished_patchless_bundle_is_not_stopped` | D's recorded base is the line | carried A, P; D's own base and fix/D hold A and P; no STOPPING. Run 1 shows P was cut from its own base holding A, so the false-stop setup is real |
| (4) | `test_a_carried_prerequisite_cut_from_a_line_holding_another_stops_its_dependent` | D built (on the line) | D PLANNED, no stack-base record, no `-bD` on origin; one STOPPING line naming issue_P and issue_X |
| (5) guard | `test_a_carried_prerequisite_rewritten_after_the_carry_stops_its_dependent` | also red on the base: D is built on the line, and nothing checks a carried branch | D PLANNED; one STOPPING line naming issue_P and "was rewritten" |
| guard | `test_a_finished_bundle_with_no_brief_declares_no_edge_to_walk` | green on the base (#727 never read the brief) | green; red with only the briefless guard removed (`FileNotFoundError`) |

Actual STOPPING lines post-fix:
- (4): "could not build issue_D's own base from issue_P: …-bD would hold 43c3823038b6,
  which is not origin/main's and not any member's own work: issue_P's branch
  origin/fix/P brings it in from below f078db81b2d2, the cut point recorded when issue_P
  was published. It is in the published head of issue_X, which issue_D does not build
  on. …".
- (5): "could not build issue_D's own base from issue_P: issue_P's branch origin/fix/P
  was rewritten after this run folded it onto … the commit the line took from it. …".

## Refuting my own test

- **(a) Genuine red?** Yes. I reverted only `flow.py` (`git checkout` of that file) and
  ran the module: 5 of 5 then-existing tests failed. Their assertions are quoted in the
  table: (1)-(3) because the dependent was built on the line, (4) and (5) because D was
  built instead of stopped. The C4 gate (`engine/scripts/run-verify.sh`, run with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` under `timeout 1800`) reverted the production hunks and
  got 5 of 6 red in the new file (the briefless guard stays green, as expected), plus
  2 + 2 + 14 red in the restated files. It printed `PDCA-EVIDENCE: C4 PASS — red
  without the fix, green with it`, rc 0. The worktree came back byte-identical to
  `patch.diff`.
- **(b) Production path?** Yes. Every case drives `flow._drive_and_act`, the real carry
  (`_carry_finished` with a real fold), `_bundle_bases`, and the real
  `integrate.build_bundle_base`, which pushes real branches to a bare origin. Only these
  are stubbed: the build/sign-off leaf (`flow._drive_wave` writes a patch and accepts),
  `flow._publish_bundle` (cuts and pushes a branch from the recorded stack-base tip, as
  publish does), `gh` (OPEN, head = branch tip) and `publish.draft_texts`. This is the
  same seam set as #727's suite.
- **(c) Fixture includes the fault?**
  - (2)/(3) build the finished patchless N and the carried A/P with a real first run,
    not by hand. N really closes with no patch, and P really was built on its own base
    holding A (asserted).
  - (4) really cuts P from a real earlier-run line holding X (`integrate.fold`) and
    records that stack base.
  - (5) really force-pushes `fix/P` on origin after the carry's fold.
  - (1) carries two clean bundles, so the unrelated one is present on the line.

## Gates run (the project's runners)

- `engine/scripts/run-suite.sh` (T3, `PDCA_WORKTREE` set, `timeout 1500`) on the final
  tree: root suite `Ran 24 … OK`; driver suite `Ran 2587 … OK (skipped=2)`;
  `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- `engine/scripts/run-verify.sh` (C4): PASS, as above.
- Formatter / hooks: the target has no pre-commit config, no formatter or linter config,
  no installed hooks (`.git/hooks` has only samples), and CI runs only the docs lint and
  render checks. I checked by hand: no added line is over 100 columns (`flow.py` already
  had 5 lines over 99; still 5), all changed files compile (`py_compile`), and no unused
  imports in the new test.

## Residuals for sign-off

- **Users will see this:** a re-issued run whose carried bundle was cut, before #727, from
  a line that also held unrelated work now STOPs that bundle's dependent, naming the
  bundle and the owner of the work (criterion 4's message, with "add X to D's members,
  or rebuild P's branch"). Before, the dependent was built on the line holding
  everything.
- No end-of-run check covers carried branches (true before this change too). `_carried_tips` and `rewritten_carried` judge only `accepted` bundles. So a
  carried branch rewritten after a dependent's base took it, or after the line took it,
  is not reported at the end of the run. The new check runs only when a later base takes
  that member (criterion 5).
- The uncarried-prerequisite-through-a-patchless-node case and the finished-partner
  order are described under "Decisions" above.
- Housekeeping: my first suite run wrote its log to `/tmp/claude-728-suite1.log`, which
  is outside the harness's roots. I did not delete it (cleanup is the harness's). Later
  runs piped output and wrote nothing. The fixtures' own `tempfile.mkdtemp()` dirs are
  the existing test fixtures' and clean themselves up.
