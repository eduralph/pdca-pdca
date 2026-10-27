# Build notes — #725 hold a bundle whose own base cannot be built

Base: the run's line `pdca-integration/main-r547f8028520f` at `75a886e` (= `stack-base-tip`;
holds #723, #727, #728, #729). Every `path:line` below is on `75a886e` ("base") unless it
says "patched" (the worktree with `patch.diff` applied).

## What changed, and why

### 1. A base that cannot be built holds that bundle, not the run (cases 1, 2, 4, 4b, 5)

- Before: `flow._bundle_bases` re-raised every `IntegrationError` from
  `integrate.build_bundle_base` (base `flow.py:1019-1022`), and `_drive_and_act` turned it
  into `STOPPING — wave k and later waves not run` (base `flow.py:2759-2770`).
- Now: one handler in `_bundle_bases` (patched `flow.py:1027-1031`) keeps the wrapped
  error ("could not build X's own base from …: <cause and fix>") in a `held` dict and goes
  on to the next bundle; held bundles are not pointed (patched `flow.py:1034-1035`). The
  caller (patched `flow.py:2797-2812`) prints ONE line per held bundle
  (`flow: X held — <message>. X is not built this run, nor is any bundle that depends on
  it; the rest of wave k goes on.`), drops it from `runnable`, and continues the wave.
  This is one handler for every cause, as case (5) of the brief asks.
- Dependents: a held bundle is never built, so it is never COMPLETE, and `_runnable`
  already skips a bundle whose prerequisite is not COMPLETE (base `flow.py:778-780`). So no
  new set had to be threaded into `_runnable`'s `held=`; passing it would be a no-op. I
  ruled out also holding its `Conflicts with` partners: the bundle has no work anywhere,
  exactly as a bundle that never reached COMPLETE in its wave, and the existing code does
  not hold that one's partners either (`_runnable` only holds partners of `unpushed` /
  `conflict_held`, base `flow.py:757-762`).
- `_Rewritten` (#727): the old code put the member's name in `stop_named` so the end-of-run
  check would not name the rewrite twice (base `flow.py:2686-2688`, `:2768-2769`, `:2914`).
  Kept that for a hold (renamed `base_rewrites`, patched `flow.py:2723-2725`, `:2808-2809`,
  `:2962`), and added `holds[member] = "rewritten"` (patched `flow.py:2975`) so the run
  still exits 1: the line still carries the commits the member's branch lost, which is
  #695's exit-1 condition. Without it, a held run whose line holds a rewritten branch would
  exit 3.
- Fetch failure wording: `_fetch`'s own message ("— the fold cannot see the branches it
  merges", base `integrate.py:2043`) has no fix and talks about a fold. I did not change it
  (`test_integrate_carried_rewrite_late.py:539-547` pins it word for word for the fold).
  Instead `build_bundle_base` rewraps a `_prepare_worktree` failure for its own base, with
  a fix (patched `integrate.py:878-885`), keeping `cause` so #695's end-of-run report
  still says only what failed.

### 2. Exit 3 for a bundle held at its base (case 1)

Criterion (1) says the run exits 3. The held bundle is PLANNED, and `cli._results_rc`
returned 1 for any non-terminal bundle (base `cli.py:728-729`). cli.py is not in the
brief's Scope list, but the success criterion cannot be met without touching it, so I made
the smallest change: a bundle `holds` names with reason `"base"` is not counted as
unfinished (patched `cli.py:700-702`, `:736-738`), and `_drive_and_act` records that reason
(patched `flow.py:2974`). A dependent of a held bundle is not in `holds` and still makes the
run exit 1 — the same as #693's existing rule for a held bundle's dependent
(`test_flow_hold_exit_code.py:260-267`, still green). Flagging this for the human: it is a
change to the exit-code rule, scoped to the new hold reason only.

### 3. Cross-wave overlap at the line fold (case 3, and the `:351` flip)

Choice (the brief left it to Do): extend the fold's `held_out` mode, not the flow's error
handler. Why: the fold already has the trial-merge machinery, the lock, the "drop and go
on, push once" loop (`dropped`/`continue`, base `integrate.py:641-644`) and records holds in
the same `held_out` dict the flow already honours through `_runnable` (`held_conflict`).
Doing it in the flow's `except` would mean re-running the whole fold without the bundle
(a second fold, a second lock scope, a second push decision) — more code and a second path
that could disagree with the first. Concretely: `_Conflict` carries no bundle name (base
`integrate.py:115-123`), so the flow would first have to add one; the integration lock is
already released when `_fold_lines`' `with contextlib.ExitStack()` unwinds on the
exception (base `flow.py:1089-1094`), so the flow's trials would need their own lock and
`_prepare_worktree` (a fetch) before they could run; then a second `_fold_lines` call
without the bundle, in a loop in case a second bundle clashes too. The fold-side change is
the `except` branch (patched `integrate.py:667-685`, 19 lines) plus `_held_across` (48
lines, 18 of them docstring), reusing `_trial`, `_partners`, `_built_on` under the lock the
fold already holds.

- New `integrate._held_across` (patched `integrate.py:1820-1867`), called from the fold
  when `_held_by` (#674, same wave) does not hold the bundle (patched `integrate.py:667-685`).
  Rule, matching the brief's Scope: held when the head conflicts with the line as the wave
  found it (`pre`), merges cleanly onto the fetched base alone, and every conflicting path
  is one it conflicts in with the own change of a bundle already on the line (`_partners`
  and `_built_on`, reused from #694 — they never blame a bundle for what it was built on).
  Partners are named in merge order.
- Anything else is the line's and stops as before, but with a message that fits (the
  invariant's "a fix that works for that cause"; the old text was always "an undeclared
  cross-wave overlap; declare the conflict / re-order", which is wrong for these): it
  merges onto `pre` (it clashes with what the fold took in from the base — the `:399` case),
  it does not merge onto the base itself, or a path no bundle's change accounts for. A
  trial git failure returns None and the fold raises the original conflict.
- Why the base guard uses the fetched base and not the line's cut point: a later bundle's
  own base is built from the base as fetched (`build_bundle_base`), so its branch can carry
  a newer base; judging partners on an older base names a bundle for the base's change.
  I traced that by hand for case (1)'s W if it were folded later: on the line's cut point,
  A would be named as W's partner for `a.txt` though W never touched it; on the fetched
  base, A's own trial fails first and nobody is named (the fold stops — correct, the line
  cannot hold A and the new base together).
- Wording: `_announce_conflict_holds` now says "on the line from an earlier wave" for
  partners outside the wave, and keeps the #674 wording for same-wave ones (patched
  `flow.py:1446-1465`; existing same-wave assertions unchanged and green).

### 4. Docs (criterion 6)

Rewrote every listed site to the dependency-scoped rule and the hold behaviour:
`docs/05-check.md`, `docs/07-crosscutting.md` (waves section: the stack bullet, the hold
paragraphs, the exit-code paragraph, plus two sentences #729 left stale — "the dependent is
cut from that line" and "points that target's bundles at it"), `docs/index.yml`,
`template/pdca.toml.jinja`, `config.py`, `integrate.py` module docstring + `IntegrationError`
+ `fold` + `build_bundle_base` docstrings, `publish.py` (stack-base comments, the PR-base
comment block, `write_stack_base` … `read_stack_base_tip`, `_stack_base_branch`), `gates.py`,
`drift.py`, `_adopt_split_children`, `_runnable`, `_closure_members`, `_drive_and_act`. Also
`template/agents/planner.md.jinja` (the planner prompt said "folded onto the base the next
wave builds on") and two re-gate comments ("before the next wave builds on it").

**Human-only (INTEGRATION §4):** the vendored spec edits in
`template/PCDA/quality-cycle/09-parallel-lanes.md` (lines 57-61, 69, 72, 89) and
`template/PCDA/quality-cycle/08-glossary.md` (the Dependency wave / Depends on /
Integration branch / wave_mode entries, and a new "Bundle base" entry) are drafts for you
to approve. `09-parallel-lanes.md:69` now says which cases still STOP: a conflict that is
not with bundles (base itself, a base taken in, other line work), a moved line, any other
failed fold, a red re-gate.

Wrap-aware check (the brief's loop), run on the patched worktree — output was empty:

```python
import bisect, re, subprocess
pats = ["every earlier-wave branch on the line", "integration branch the next wave builds on",
        "cut each later wave's branches off it", "cut from the line, carries every",
        "carry the earlier waves' work"]
files = subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.split()
for f in files:
    if f.startswith("CHANGELOG") or f.startswith("results/"):
        continue
    try:
        lines = open(f, encoding="utf-8").read().splitlines()
    except (UnicodeDecodeError, OSError):
        continue
    stripped = [re.sub(r"^\s*(#|//|\*)?\s*", "", l) for l in lines]
    joined, starts = "", []
    for s in stripped:
        starts.append(len(joined)); joined += s + " "
    for p in pats:
        for m in re.finditer(re.escape(p), joined):
            a = bisect.bisect_right(starts, m.start()); b = bisect.bisect_right(starts, m.end() - 1)
            print(f"{f}:{a}-{b}: {p}")
```

```
(no output)
```

Before the docs edits the same loop printed the 17 hits the brief lists (with `flow.py:679`
and `flow.py:2852-2853` at their base positions).

## Brief cases vs. this base — two premises that do not hold here

**Case (2) as written cannot run through `build_bundle_base` on this base.** The brief says
"carried P … D's base build refuses …". On `75a886e`, a dependent of a prerequisite that
an earlier run finished (carried by #646's pre-wave carry) is a *seam*: `_closure_members`
returns a str for it (base `flow.py:956-958`), so it is cut from the run's line and its own
base is never built. #728's commit message says so: "carried bundles as members of a
dependent's own base (#735)" is out of scope there. So with carried P:
- (2a) P cut from an old line holding X: D is built on the line (which holds X and P);
  nothing refuses. No hold, no stop — before or after this change.
- (2b) fix/P force-pushed after the carry: the carry passes no `carried` record and P is not
  in `accepted`, so no check reads fix/P again; D is built on the line. No hold, no stop.
Holding D there needs #735 (carried members in a dependent's own base). Out of this brief's
scope ("which base a bundle gets (#724)").

What I tested instead, in #633's sense of "carried" (a fold of THIS run carried it), which
does reach `build_bundle_base` and its refusals:
- (2a) `test_a_prerequisite_cut_from_an_old_line_holds_only_its_dependent`: P's branch cut
  from an earlier run's line holding X (via the harness's `cut_from` override, the same
  technique `test_flow_same_wave_conflict.py:373` uses for 21). D's base refuses P's
  ancestry (#723's cut-point check, `_member_cut_point` rule 4). D held, W built.
  **Gap:** the line names P, not X. Naming X needs #723's `_foreign_refusal` path, which
  needs a member with a trusted cut point below foreign work. In-run that is unreachable:
  a member's own base holds only its own members, which are all D's members too, and a
  member cut from the line is a seam, which makes D a seam (`_closure_members`, `seams`).
  The only way to reach it would be to hand-edit a bundle's `stack-base` record — I did
  not, since that is a fixture curated to produce the message, not production behaviour.
- (2b) `test_a_prerequisite_rewritten_after_the_fold_holds_only_its_dependent`: fix/A
  force-pushed after the wave-0 fold; B's base refuses (`_Rewritten`). B held, W built,
  rewrite named once, run exits 1.

**Case (5) is already held on this base, by the carry, not by a base build.** Carried P and
Q both get folded by the pre-wave carry (D depends on both); Q's merge conflicts with P
and #694 skips Q and holds D, naming P, Q and D on one line (base `flow.py:1377-1404`). So
`test_two_finished_prerequisites_that_clash_hold_only_their_dependent` is green before and
after. The brief's "Pre-change, (1)–(4) fail" does not include (5), so this matches, but
the stated mechanism ("D's base build refuses the member clash") is not what happens here.
An in-batch member clash would be caught by the fold first (same-wave #674, or cross-wave,
this change) and D held by `_runnable` before its base is built. The member-clash refusal
in `build_bundle_base` is still covered by the one handler, by construction.

## Tests that flipped (before → after)

| Test | Before | After |
|---|---|---|
| `test_flow_same_wave_conflict.py` `test_a_conflict_with_earlier_wave_work_still_stops_the_run` (base `:365`; the brief's `:351`) | `wave 1 did not integrate`, `STOPPING`, 21 not held, 30 not built | renamed `…_holds_the_bundle_not_the_run`: no `STOPPING`; 21 held, named with issue_10 "on the line from an earlier wave", never issue_20; 21 not on the line; 30 PLANNED |
| `test_flow_dependency_scoped_bases.py` `test_a_later_base_that_reads_the_rewrite_stops_naming_each_base_and_pr` (base `:503`) | one `STOPPING` line with every part | renamed `…_holds_its_bundle_naming_each_base_and_pr`: no `STOPPING`; the same parts on the one `flow: issue_D held — ` line; still named once; `holds == {"D": "base", "A": "rewritten"}` |
| `test_flow_dependency_scoped_bases.py` `test_a_base_that_stops_the_run_for_a_clash_leaves_the_end_check_on` (base `:521`) | one `STOPPING` line; `holds == {"Z": "rewritten"}` | renamed `test_a_base_that_cannot_be_built_for_a_clash_leaves_the_end_check_on`: the `flow: issue_C held — ` line; `holds == {"Z": "rewritten", "C": "base"}` |
| `test_integrate_carried_rewrite_late.py` `test_a_rewrite_during_the_lines_fold_stops_the_run_at_the_dependents_base` (base `:295`) | `_stopped_at_b`: one `STOPPING` line; exit 1 | renamed `…_holds_the_dependent_at_its_base`; `_held_at_b`: one `flow: issue_B held — ` line, no `STOPPING`; rewrite named once; exit 1 |
| `test_integrate_carried_rewrite_late.py` `test_a_fetch_failing_after_the_lines_fold_stops_the_run_at_the_dependents_base` (base `:350`) | `_stopped_at_b(cause)`; exit 1 | renamed `…_holds_the_dependent_at_its_base`; `_held_at_b(cause, "then re-run")`; exit 1 (A unchecked) |

Stays a stop, as the brief says: `test_a_conflict_only_with_a_base_taken_in_mid_wave_still_stops_the_run`
(base `:413`; the brief's `:399`). I added three assertions on its stop line (it now names
what the fold took in from origin/main and says to update the branch from it, and no longer
says "re-order"). The outcome it pins is unchanged.

## Verification (all through the project's runners)

- C4, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` = this bundle and `PDCA_WORKTREE`
  = the worktree: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, exit 0.
  Green leg: the four test modules in the patch (25 + 8 + 15 + 7 tests) all OK. Red leg
  (production hunks reverted, tests kept): the new module 6 of 7 failed, the flipped ones
  failed, and `…_still_stops_the_run` failed on its new wording assertions.
- Red without the fix, before I wrote any production code: the new module, run with the
  CONTRIBUTING command on the clean base, failed 6 of 7 (all six on `'STOPPING'
  unexpectedly found`), case (5) green.
- T3, `engine/scripts/run-suite.sh`: `PDCA-EVIDENCE: root suite OK, driver suite OK` —
  root 24 tests OK (copier importable, nothing skipped), driver 2601 tests OK (2 skipped,
  both pre-existing skips).
- T2, `engine/scripts/run-docs-check.sh`: `docs lint clean, site render + link audit clean`.
- `patch.diff` checked with `git apply --cached --check` against `75a886e` in a scratch
  index: applies cleanly, and base + patch is byte-identical to the worktree I tested.

Commit-readiness: the target configures no formatter or pre-commit hook (no
`.pre-commit-config.yaml`, no ruff/black config, no `core.hooksPath`). Its CI runs
docs-check (`lint_docs.py` + `render_site.py --check`, green above) and render-check (the
root suite, green above). Every added Python line is ≤ 96 characters (the files' own max is
102). DCO sign-off is added at publish.

Untracked scratch files I left in the worktree root and that are NOT in the patch:
`.full-suite.log`, `.verify.log`, `.pdca-check-index`.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** `run-verify.sh` reverted every production hunk and re-ran:
  six of the seven new cases failed, each on `'STOPPING' unexpectedly found in "flow: wave
  1 — could not build issue_B's own base …"` / `"flow: wave 1 did not integrate (issue_Y's
  branch …"` — the whole-run stop the brief names. The seventh, case (5), is green with the
  fix reverted on purpose: on this base the carry (#694) already holds D (explained above),
  and the brief's "Pre-change, (1)–(4) fail" leaves (5) out. Exit code: I also reverted
  only the `cli.py` hunk (`git apply -R --include=template/src/pdca_harness/cli.py`) and ran
  case (1): it failed on `AssertionError: 1 != 3` with the hold line printed, so the exit
  assertion binds the `cli.py` change on its own. Re-applied; base + patch matched the
  worktree again.
- **(b) Production path? Yes.** The tests call `flow._drive_and_act` and the real
  `integrate.fold` / `integrate.build_bundle_base` / `cli._results_rc`. Stubbed, as in the
  peer suites the brief cites: the build and sign-off leaves (`flow._drive_wave` writes a
  patch and accepts), `flow._publish_bundle` (cuts and pushes the real branch from the
  recorded stack-base tip), `publish.draft_texts`, and `gh`. `integrate.fold` and
  `integrate.build_bundle_base` are wrapped, never replaced: the fold wrapper runs a hook
  after the real fold returns (to move main / force-push a branch at the right moment), and
  the base-build wrapper only makes `git fetch` return 1 while B's base is built (case 4,
  "stubbing the fetch of its base build", as the brief suggests); every other call goes to
  the real function.
- **(c) Fixture includes the fault? Yes.** Each fault is real git on a bare origin: (1) a
  real commit adding a different `a.txt` pushed to main after the wave-0 fold; (2a) P's real
  branch cut from a real old line holding X's commit; (2b) a real force-push of `fix/A`;
  (3) two real branches adding `shared.txt`; (4) a real failing fetch for B's base build
  only; (4b) a real divergent commit on B's base branch plus a real
  `receive.denyNonFastForwards = true` on origin; (5) two real finished branches adding
  different `s.txt`. The unrelated bundle W in each case is in the same run and wave as the
  held one, so "the rest of the run goes on" is measured, not assumed.

## Size

`patch.diff` is 140 KB (`sizing.json` already bands this brief "oversized"; the brief keeps
all stack-rule docs here on purpose). By area: `template/src/*.py` 67 KB — most of it the
docstring and comment rewrites criterion (6) asks for (`flow.py` 28 KB, `integrate.py`
20 KB, `publish.py` 12 KB of diff text); tests 29 KB (the new module 18 KB, three flipped
suites 12 KB); docs, vendored spec, planner prompt and config comments 44 KB
(`09-parallel-lanes.md` alone is 18 KB of diff, because its `stack` bullet is one 5 KB line
shown removed and added). The behavioural code is small: the `_bundle_bases` handler and
its caller in `flow.py`, `_held_across` plus the fold's `except` branch and the fetch rewrap
in `integrate.py`, and four lines in `cli._results_rc`.

## Open items for the human at sign-off

1. Case (2) as the brief wrote it (carried prerequisites as members of D's own base) is not
   reachable on this base — it needs #735. My (2a)/(2b) test the same refusals with
   prerequisites a fold of this run carried. (2a)'s hold line names P but not X (see above).
2. Case (5) is held by the carry on this base, not by a base build; the test pins the
   outcome only.
3. `cli._results_rc` changed (outside the brief's Scope list) so a `"base"` hold exits 3,
   as criterion (1) requires.
4. The vendored spec edits (`09-parallel-lanes.md`, `08-glossary.md`) need your approval
   (INTEGRATION §4).
