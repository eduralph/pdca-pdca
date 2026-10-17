# issue_728 — build notes (Do, iteration 2)

## Base

Worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt`, detached at `c423f9d`
("pdca-integrate: issue_727"): the fold of #727's accepted result onto
`pdca-integration/main-r547f8028520f`. That matches this bundle's `stack-base` /
`stack-base-tip` files (`c423f9dc…`). `$PDCA_VERIFY_BASE` was not set in my environment; the
worktree was already on that fold. Below, "base" means `c423f9d` and "patched" means
`c423f9d` + `patch.diff`. `patch.diff` applies cleanly to `c423f9d` (`git apply --cached
--check` on a scratch index read from `HEAD`).

I started from iteration 1's `patch.diff` (applied cleanly) and changed it for the three
carry-forward findings below. Production stays `template/src/pdca_harness/flow.py` only;
`integrate.py` and `_runnable` are untouched.

## The carry-forward findings, and what changed for each

### Finding 1 — false STOPPING through `Conflicts with` between two carried bundles

Iteration 1 never followed a `Conflicts with` edge from one finished id to another (both
sit at wave -1). In `[J, K, W]` with `K Conflicts with: J`, run 1 builds K on a base
holding J. On the re-issue W's members were `[K]` only, J's commit sat below K's cut point,
and `_unowned_work` refused W's base. The docstring's reason ("which of the two an earlier
run built first is not known here") was wrong: the recorded cut points show it.

Fix:
- New `_finished_after` (patched `flow.py:1033-1071`). For each finished bundle in the walk's
  graph that has a recorded stack-base tip (its cut point), it lists the finished partners
  an earlier run built before it:
  - a carried partner counts when **some of its own work** is below that cut point. "Own
    work" means the non-merge commits its head adds over the target base and its own
    recorded tip. That is the same definition `_unowned_work` uses (`integrate.py:988`).
  - a partner with no patch counts when **all its own recorded tip added over the base**
    is below that cut point, and there is something. That is what it was built on, and
    the bundle's branch brings it in too.
  - a bundle with no recorded tip (built on the base itself) lists none.
- New `_holds_work` (patched `flow.py:1074-1085`): two `git rev-list --no-merges` calls,
  `some`/`every`. A commit the clone does not have returns False, so the edge is not
  followed. At worst the base is then refused for work no member owns; it is never built
  on unrelated work. A git failure raises `IntegrationError` (via `integrate._out`).
- `_closure_members` takes `after` (patched `flow.py:913-961`). A partner edge is skipped
  when the partner was built after the bundle it is reached from, **unless** `after` names
  it (patched `:954-956`). Only finished→finished pairs can appear in `after`, so edges
  from or to this run's bundles behave exactly as in #727.
- `_bundle_bases` computes `after` once per wave (patched `:996`) and passes it on
  (`:1003-1004`).

Why "some own work" and not "the partner's head is an ancestor of the cut point" (the
reviewer's suggestion): the reviewer's rule is a special case of mine. Mine also covers a
partner whose branch moved forward (a fast-forward, e.g. a review fixup) after the member
was cut. There the old head is below the cut and the new head is not. With the head rule
that case is a false STOP again. The cost is 2 `rev-list` calls per finished partner pair
instead of 1 `merge-base`. There are usually zero such pairs, and each pair is read once
per wave.

### Finding 2 — a prerequisite reached only through a patchless bundle was never carried

The carry started only from a drive-set bundle's **direct** plain `Depends on` to a fold
candidate (base `flow.py:1254-1259`). In `[A, N, D]` (N closed with no patch, `Depends on:
A`; D `Depends on: N`) nothing was carried, the walk left the graph at A, and D was built
on main without A. That was true before iteration 1 as well.

Fix:
- New `_plain_prereqs` (patched `flow.py:1285-1304`). It returns the names a bundle's plain
  `Depends on` reaches: directly, and through any finished named id with no patch
  (transitively). The patchless ones themselves are never returned. A missing brief names
  nothing.
- `_carry_finished` builds `dependents` with it (patched `:1359-1364`), so D's edge
  through N makes A's target carried.

### Finding 3 — the hold through a patchless bundle (the same gap, from the adversary)

If A is reached through N but is **held** (not clean), `_runnable` checks only D's direct
edge, to N, which is COMPLETE. So D was built anyway, on a base without A. The carry's
line said "holding issue_D", which was false.

Fix: at the end of `_carry_finished` (patched `flow.py:1454-1456`), every finished id with
no patch whose plain `Depends on` reaches (through other patchless ids) an id in `held`
goes into `held` too. `_runnable`'s existing branch (`flow.py:803-806`, unchanged) then
holds D: "flow: issue_D skipped — prerequisite(s) not ready (N); not built on a base
missing them." The carry's line for A already names D ("holding issue_D this run"),
because `dependents` now reaches through N.

Rejected alternative, with its cost: hold D inside `_closure_members` when the walk leaves
the graph at a finished id that was not carried. `_closure_members` returns
`list[Path] | str` today. A hold is a third outcome, and `_bundle_bases` returns `None`
while `runnable` is fixed before it runs. Sketch: a hold value in `_closure_members` (+3
lines); `_bundle_bases` returns the held names (+6); `_drive_and_act` drops them from
`runnable` after the call and prints its own reason (+6); docstrings (+6). That is about
20 lines and a new stderr message. The chosen change is 3 lines of code plus 4 docstring
lines, and it reuses `_runnable`'s existing hold and the carry's existing message. It also
keeps `_runnable`'s code untouched, which the brief leaves to #729.

### Finding 4 — test changes outside the brief's list must be listed

All of them are below, under "Restated assertions", with before and after. That includes
the ones the reviewer named (`test_flow_dependency_scoped_bases.py`, and the `merged` file's
`:232`, `:240`, `:318` callers on iteration 1's numbering).

## Everything production changes (`template/src/pdca_harness/flow.py`)

1. `_closure_members` (base `:913-958` → patched `:913-961`): parameter `built` → `graph`,
   plus `after`. The `finished` seam is gone (base `:947-949`: `if n in finished: return
   "... finished in an earlier run"`). Edges to names outside `graph` are not followed
   (patched `:952`). Members are still filtered by `on_target`, which comes from
   `integrate._fold_candidates` and so never holds a patchless bundle: patchless nodes are
   walked but are never members. The remaining seams are exactly a walked `Stacks on` /
   `Onto branch` bundle, and a member pointed at a seam itself. That is the brief's
   "narrowing #727's carried-closure fallback".
2. `_bundle_bases` (base `:961-1012` → patched `:964-1030`): builds the graph (patched
   `:992-994`): carried finished ids plus patchless finished ids that have a brief, at wave
   -1, then this run's bundles. It computes `after` (`:996`) and passes `heads = {**carried,
   **carried_heads}` (`:995`) to `integrate.build_bundle_base` as both `carried=` and
   `excluded=` (`:1013`; base `:995` passed `carried_heads` only). So:
   - a carried member rewritten after the carry is refused by #723's existing check
     (`integrate.py:838-844` → `_lost` `:1077` → `_carried_rewrite` `:1172`, raising
     `_Rewritten`). This is criterion (5).
   - a carried member whose branch brings in work from below its recorded cut point is
     refused by `_unowned_work` (`integrate.py:988`, called at `:867`) → `_foreign_refusal`
     (`:1008`, raised at `:869`), which now names the carried owner. This is criterion (4).
3. Briefless guard (patched `:991-993`): a patchless finished bundle with no `brief.md` (a
   pre-#481 split parent, #597) stays out of the graph. Without it, `brief.stacks_on` raises
   `FileNotFoundError` out of the whole run (ablation below). It declares no edges, so
   leaving it out changes no members.
4. `_finished_after` and `_holds_work`: new (finding 1).
5. `_plain_prereqs`: new (finding 2).
6. `_carry_finished` (base `:1212` → patched `:1307`):
   - `through` + `dependents` via `_plain_prereqs` (`:1359-1364`), finding 2;
   - new optional out-param `took` (`:1310`, filled at `:1435-1436`): each id actually
     carried, with the PR head `_finished_head` judged clean and the fold was handed as
     `pr_heads`;
   - hold through patchless ids (`:1454-1456`), finding 3;
   - docstring: two new paragraphs (`:1349-1356`).
   - The "carried" stderr line (base `:1330-1332`): "this run's … bundles build on it" →
     "bundles ordered after them build on a base that holds them" (patched `:1437-1440`).
     That is true for both own bases and seams. Every test that reads this line matches its
     unchanged prefix `flow: carried issue_X (finished`.
7. `_drive_and_act`: `carry_took` filled by the carry (patched `:2710`, `:2715`) and passed
   to `_bundle_bases` as `carried=` (`:2802`); comments updated (`:2707-2708`, `:2795-2797`).

Not touched, per the brief's scope: `integrate.py`; `_runnable`
(`flow.py:681-847`), including its merged-prerequisite branch and `_line_lacks_merge`
(#729); `_cascade_not_clean`; the stack-rule docs (#725).

## Decisions and what I ruled out

**Which head counts as "carried"** (same as iteration 1): the PR head `_finished_head`
returned. That is the head the carry judged clean and accounted origin's line with, and
handed its fold as `pr_heads`. The alternative was to pass a fresh dict as `carried=` to
the carry's own `_fold_lines`: a 1-line flow change. But `integrate.fold`'s docstring
(`integrate.py:460-461`) says the pre-wave carry "checks and records nothing", so it would
need an edit in `fold`, outside the functions the brief allows in `integrate.py`.

**Which partner was built first**, between two finished ids:
- chosen: read the earlier run's own record (cut points), above. About 27 code lines in
  `_finished_after` + `_holds_work`.
- rejected: replay the scheduler's orientation (`waves.py:200-212`: name-lower first unless
  a dependency path orders them). That needs the earlier run's `deps` rebuilt from the
  finished briefs (`waves.py:190-212`, about 20 lines, plus `waves._reaches`). It is also a
  guess: the earlier run may have had another batch, or the two ids may come from
  different runs. The cut points record what actually happened.
- rejected: follow every finished→finished partner edge. This puts unrelated work on a
  base. The new test `…_built_after_a_carried_member_is_not_on_the_base` goes red under
  that variant (ablation below).

**Through which edges the carry walks a patchless node**: plain `Depends on` only, the same
edges the carry already starts from (#646). The walk in `_closure_members` also follows
`Depends on (merged)`. A `Depends on (merged)` reached through a patchless node is not
carried and not gated on its merge (residual below).

**`after` is computed per wave**, not once before wave 0. That keeps it next to its only
reader. The cost is a few `rev-list` calls per finished partner pair per wave; there are
usually none.

## Restated assertions and other test changes (before → after)

Every change to an existing test file, line numbers on base → patched. "Own base" means:
the recorded stack base is `integrate.bundle_base_branch(…, "issue_<id>")` (never the
line), the recorded tip is origin's tip of it, and the bundle is COMPLETE.

### `template/tests/test_flow_resume_stack_prereqs.py` (the brief's `:183`, `:262`, `:449`, `:538` anchors on `fcae4aa`)

| Base | Before | Patched | After |
|---|---|---|---|
| `:15-17` module docstring | "the run still pushes once (#672)" | `:15-21` | "pushes its line once"; new paragraph: since #728 a dependent of a carried id is on its own base, the line still carries every carried id |
| `:122-128` `_publish_bundle` (fixture, not an assertion) | `fx._publish` rewrites the brief, dropping `Depends on` | `:126-135` | the brief is restored after `fx._publish`. Real publish never writes the brief (`publish.py` writes only `publish.json` and the stack-base files). #727's own fixture leaves it alone (`test_flow_dependency_scoped_bases.py:135-164`). Without this, test (3)'s E walked to D but not on to P and stopped on P's commit as unowned. Before #728 that was hidden: D was a seam, so E went to the line too. |
| `:197` test name | `…_is_on_the_line_its_dependent_builds_on` | `:204` | `…_is_on_the_base_its_dependent_builds_on` |
| `:202-207` test (1) | `base == line`, `line_tip` not None, `tip == line_tip`, fix/P on `line_tip`, D COMPLETE | `:210-213` | `_on_own_base("D", …, "P")` (own base, tip = origin tip, fix/P on it, COMPLETE); `line_tip` not None and fix/P on it, kept |
| `:221`, `:225` test (2) | `_built("D")[:2] == (line, old)`; D COMPLETE | `:227-228` | `_on_own_base("D", …, "P")`; the line D was built beside is still at `old` (`_built("D")[2] == old`). Kept: `old` ancestor of the line, pushes non-empty, no `--force` (D's base is a plain push of a new branch) |
| `:229` test (3) comment | "E builds on a line holding P and D" | `:235-236` | "D and E are each built on a base of their own: D's holds P, E's P and D" |
| `:235-243` test (3) | D `(line, carried)`; `len(pushes) == 2`; `pushes[1]` not forced; E `(line, e_line)`; `carried`, fix/P, fix/D on `e_line`; E COMPLETE | `:243-254` | `_on_own_base("D", batch, "P")`; `carried` = the line tip then; pushes **to the line** are exactly 2 and the 2nd is not forced; the **other** pushes are exactly D's then E's own bases, in that order (as strict as `len == 2` was); `_on_own_base("E", batch, "P", "D")`; `carried`, fix/P, fix/D on `e_line`, kept |
| `:275-279` test (4c), the brief's `:262` | B `(line, line_tip)`; fix/Q on `line_tip`; fix/P not on the line; B COMPLETE | `:286-289` | `_on_own_base("B", …, "Q")`; fix/P **not on B's base** (the excluded one, now checked on the base); fix/Q on the line tip then, kept; fix/P not on the line, kept |
| `:458-463` `…_clean_finished_id_beside_them…`, the brief's `:449` | E `(line, line_tip)`; fix/X on tip; fix/P, fix/Q not on tip; E COMPLETE | `:468-471` | `_on_own_base("E", …, "X")`; fix/P, fix/Q not on E's base tip, kept |
| `:538-551` `_carried_beside`, the brief's `:538` | `len(pushes) == 1`; one carried line naming X; E `(line, line_tip)`; fix/X on tip; E COMPLETE; returns the line tip | `:546-558` | pushes are exactly `[line, E's own base]` (the line once: no fix-up push); same carried-line checks; returns `_on_own_base("E", batch, "X")`. Its six callers' `_off_the_line(commit, e_tip)` now check the line **and** E's own base |

The brief's `:348` anchor (test (8), W) was already an own base on `c423f9d` (#727: W
`Depends on: U`, built this run). Unchanged here.

### `template/tests/test_flow_merged_prereq_on_line.py` (the brief's `:269` anchor)

| Base | Before | Patched | After |
|---|---|---|---|
| `:191-210` helper `_built_on_line()` | if W was built this run: own base `{line}-bD`, tip = origin tip, fix/W on it, nothing beyond main but merges and fix/W; **else** (a carried prerequisite) `base == line` | `:191-205` `_built_on_own_base(prereq)` | always own base `{line}-bD`, tip = origin tip, fix/`<prereq>` on it, nothing beyond main but merges and fix/`<prereq>`; D COMPLETE |
| `:239` caller (test 3) | `_built_on_line()` (W built: own base) | `:235` | `_built_on_own_base("W")`, the same checks |
| `:247` caller (test 4) | `_built_on_line()` (W built: own base) | `:243` | `_built_on_own_base("W")`, the same checks |
| `:285-286` comment | "D … is cut from that line" | `:281-283` | "judged on that line …, on a base of its own holding the carried P (#728), which starts at main and so has the merge" |
| `:297-300`, the brief's `:269` (`tip == old`) | `_built_on_line()` (base == line); `tip == old`; fix/P on tip; merge commit **not** on tip | `:294-298` | `_built_on_own_base("P")`; the merge commit **is** on D's tip; the line is still at `old`; fix/P on `old`; merge commit not on `old` |
| `:309` comment | "D is built on it" | `:307-308` | "D is built — on a base of its own holding W (#728), which starts at main too" |
| `:322` caller (way-out test, 3rd run: W carried) | `_built_on_line()` → else-branch, `base == line` | `:321` | `_built_on_own_base("W")`. Kept: tip ≠ `old`, merge commit and fix/W on tip |

The **one assertion whose truth value flips** is the merge commit on D's tip (base `:300`).
It was a fact about the line D was cut from: the line #655's gate judged, which lacks P's
merge. D's own base starts from freshly fetched main, which has the merge, so D's base
holds it. The line facts are kept unchanged as line facts (`:296-298`). The excluded-work
check is stronger than before: "beyond main, nothing but merges and fix/P".

### `template/tests/test_flow_dependency_scoped_bases.py` (#727's suite; the brief predates it)

| Base | Before | Patched | After |
|---|---|---|---|
| `:373` header | `(6) seams keep the line, exactly as before, and are built` | `:373`, `:405` | new header `(6a) a bundle the run carried is a member like one it built (#728)` over the two tests below; the `(6)` header moves down to `:405`, above the unchanged `Onto branch` / `Stacks on` seam tests |
| `:375-390` `test_a_dependent_of_a_carried_bundle_keeps_the_line` | `_on_line("D")`; every commit of P's and X's branches on that tip | `:375-388` `…_is_built_on_a_base_holding_it` | `_own_base("D", "P", "X")`: own base, tip = origin tip, every commit of P's and X's branches, COMPLETE |
| `:392-407` `test_a_conflicts_with_partner_that_was_carried_keeps_the_line` | `_on_line("D")`; K's and X's commits on it | `:390-403` `…_carried_is_on_the_base` | `_own_base("D", "K", "X")` |

These two tests pinned exactly the fallback the brief removes. The comments changed to
match (`:377-378`, `:392`).

Unchanged: every assertion in `test_integrate_carried_rewrite_late.py`, and every other
existing test file.

## The new test — `template/tests/test_flow_carried_prereq_bases.py` (11 tests)

Real git on `StackFoldGit` through `flow._drive_and_act`, like #727's suite. The fixture
keeps briefs as they are. `gh` answers OPEN unless a case sets `self.gh[id]`. Only modules
are imported.

| Test (patched line) | For | Red on the base (`c423f9d`) because | Ablation that turns it red |
|---|---|---|---|
| `…holds_only_its_own_prerequisite` `:228` | criterion (1) | fix/D holds X's commit (D built on the line) | full revert |
| `…patchless_bundle_carries_its_prerequisite` `:251` | criterion (2) | D's recorded base is the line | full revert |
| `…reached_only_through_a_patchless_bundle_is_carried` `:271` | finding 2 (`[A, N, D]`, no W) | nothing carried: `flow: carried issue_A` missing; D on main | carry trigger direct only |
| `…held_prerequisite_reached_through_a_patchless_bundle_holds_the_dependent` `:287` | finding 3 | D built on main (`('', '')`) | carry trigger direct only; or no hold through patchless ids |
| `…patchless_bundle_is_not_stopped` `:312` | criterion (3) | D's recorded base is the line | full revert |
| `…no_brief_declares_no_edge_to_walk` `:335` | guard (#597) | green on the base (the base never read a finished brief) | no briefless guard: `FileNotFoundError` |
| `…partner_built_before_a_carried_member_is_on_the_base` `:352` | finding 1, with W `Depends on: K` and Y `Conflicts with: K` | W, Y built on the line | no partner rule: STOP (iteration 1's false stop) |
| `…partner_built_after_a_carried_member_is_not_on_the_base` `:374` | precision of the partner rule | W built on the line, which holds L | follow every finished partner: W's base holds L |
| `…patchless_partner_built_before…` `:395` | partner rule, patchless partner | W built on the line | patched partners only: STOP (A's commit unowned) |
| `…cut_from_a_line_holding_another_stops_its_dependent` `:418` | criterion (4) | D built on the line | build not given carried heads: the STOP line lacks issue_X |
| `…rewritten_after_the_carry_stops_its_dependent` `:438` | criterion (5), a guard per the brief | also red on the base: D built on the line, nothing checks a carried branch | build not given carried heads: D built on the rewritten branch |

Actual stderr after the fix:
- (4): "flow: wave 0 — could not build issue_D's own base from issue_P: …-bD would hold
  77ec0666d0d2, which is not origin/main's and not any member's own work: issue_P's branch
  origin/fix/P brings it in from below dc7e7edb1f21, the cut point recorded when issue_P
  was published. It is in the published head of issue_X, which issue_D does not build on.
  … STOPPING — wave 0 and later waves not run."
- (5): "… could not build issue_D's own base from issue_P: issue_P's branch origin/fix/P
  was rewritten after this run folded it onto … the commit the line took from it. …"
- finding 3: "flow: issue_A (finished in an earlier run) is not carried onto …: its PR is
  CLOSED — holding issue_D this run; …" then "flow: issue_D skipped — prerequisite(s) not
  ready (N); not built on a base missing them."

## Refuting my own test

- **(a) Genuine red?** Yes. The C4 gate (`engine/scripts/run-verify.sh`, run with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` under `timeout 2400`) reverted the production hunks. The new
  file went 10 of 11 red: every test except the briefless guard, which is a guard and is
  green on the base too. The restated files went 2 + 2 + 14 red. The gate printed
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, and afterwards the worktree
  diff was byte-identical to `patch.diff`. I also turned off one part of the fix at a time
  (a script that edits `flow.py`, runs the module, and restores it; checked identical
  after). Each part turns its own test red, as the table above shows: no partner rule;
  patched partners only; follow every finished partner; carry trigger direct only; no hold
  through patchless ids; no briefless guard; carried heads not passed to the build.
- **(b) Production path?** Yes. Every case drives `flow._drive_and_act`: the real carry
  (`_carry_finished` with a real `integrate.fold`), real `_runnable`, real `_bundle_bases` /
  `_finished_after`, and real `integrate.build_bundle_base`, which pushes real branches to
  a bare origin. Stubbed: the build/sign-off leaf (`flow._drive_wave` writes a patch, a
  close marker, or nothing, and accepts), `flow._publish_bundle` (cuts and pushes
  `fix/<id>` from the recorded stack-base tip, as publish does), `gh` (state + head), and
  `publish.draft_texts`. That is the same set of stubs #727's suite uses.
- **(c) Fixture includes the fault?** Yes.
  - The patchless N/B and every carried id come from a **real first run**, not hand-built
    state. N/B really close with no patch, and the partner order really comes from that
    run's scheduler. The tests assert what it recorded: K's cut point holds J; K has no
    record when K was built first; B's record is its own base; P was cut from a base
    holding A.
  - Finding 3 really closes A's PR (`gh` answers CLOSED) and deletes the earlier line, so
    the carry really holds A.
  - (4) really cuts P from a real earlier line that holds X (`integrate.fold`).
  - (5) really force-pushes `fix/P` after the carry's fold.
  - (1) carries two clean bundles, so the unrelated one is really on the line.

## Gates run (the project's runners)

- `engine/scripts/run-suite.sh` (T3; `PDCA_WORKTREE` set; `timeout 2400`) on the final
  tree: root suite `Ran 24 … OK`; driver suite `Ran 2592 … OK (skipped=2)`;
  `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- `engine/scripts/run-verify.sh` (C4): PASS on the final `patch.diff`, as above.
- Formatter / hooks: the target has no pre-commit config, no formatter or linter config,
  and no installed hooks (only `.sample` files); its CI runs only docs and render checks.
  No linter is installed here either. I checked by hand: no added line is over 99 columns
  (`flow.py` already had 5 lines over 99, and still has 5); every changed file compiles;
  there are no unused imports (an `ast` check of all five files).

## Residuals for sign-off

- **Users will see this:** a re-issued run whose carried bundle was cut from a line that
  also held unrelated work (before #727, or as a seam) now STOPs that bundle's dependent.
  The stop names the bundle and the owner of the work (criterion 4). Before, the dependent
  was built on the line holding everything. The same applies to a carried bundle whose cut
  point cannot be trusted (`integrate._member_cut_point`: stacked with no record, or no
  recorded tip): its dependent now stops with "Re-publish …". #727 already stopped this-run
  members the same way.
- **Not covered: a `Depends on (merged)` edge, or an edge to an id the run was not asked
  for, reached through a patchless node.** The carry and the new hold follow plain
  `Depends on` from finished named ids. `_runnable` judges only a bundle's own edges (#186
  merge gate, #647 wait, #655 line check), and its code is #729's. So D → N → `Depends on
  (merged): A`, with A unmerged, is still built without A. Same as before this change.
- **`_cascade_not_clean` does not walk through patchless nodes.** Example: Q `Depends on:
  N` (no patch), N `Depends on: P`, and P's PR is closed. Q is still judged clean and
  carried, so the line gets P's work through Q. That line behaviour predates this change.
  Q's dependent now STOPs with "No bundle of the run owns it" instead of being built on
  that line. I left it out to keep #652's held-line wording unchanged; it is a candidate
  follow-up.
- **No end-of-run rewrite check for carried branches** (true before this change too).
  `rewritten_carried` judges only the run's `accepted` bundles, so a carried branch
  rewritten after a dependent's base took it is not reported at the end of the run. The
  new check runs only when a later base takes that member (criterion 5).
- **Docs:** `docs/07-crosscutting.md:749-752` still says the carry "points that target's
  bundles at" the line. It does not describe own bases (#727) or the trigger through a
  patchless node. Stack-rule docs are #725's per the brief, so I did not edit them.
- **Housekeeping:** my scratch scripts and logs are in `$PDCA_WORKTREE/.scratch-728/`. It
  is untracked, not in the patch, and outside `template/` (copier's `_subdirectory`), so
  the render suite never sees it. I deleted nothing; the harness reclaims the worktree. The
  fixtures' own `tempfile.mkdtemp()` dirs are cleaned by their `tearDown`.
