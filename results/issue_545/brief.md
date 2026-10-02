# Design proposal — issue 545 / split-parent-closes-with-children-bound-depth

> The Plan artifact for the **exception**: a change significant enough to warrant a
> GEPS-style design proposal (major architecture / public API / data model / UX, or
> anything needing design buy-in before implementation). Authored interactively at Plan
> (the planner leaf) with the human. Do reads ONLY this file and implements it; Check runs
> the regular gated check on the code.
>
> Keep the `- **Label:** value` lines — they are parsed by the driver (Do reads the
> spec from them; the driver/SUMMARY read slug/criterion/branch). The prose `##`
> sections are the design rationale: the reviewer and the human read them at
> sign-off, and they are what you carry upstream into any design-proposal process.

- **Slug:** split-parent-closes-with-children-bound-depth
- **Kind:** enhancement (design proposal)
- **Goal:** A split parent's tracker issue stays open while its children are being worked on, and is closed as "completed", with a comment naming every child, once all of its children are closed. A split parent whose bundle is COMPLETE is never closed — for any reason, including a recorded merged PR — while a child is still open; today `pdca cleanup --apply` closes it as "not planned". (A split parent whose bundle ended DISCONTINUED is out of scope and keeps today's close — see Scope and Open question 5.) Separately, `pdca split <id> --accept` refuses, by default, to split a bundle that is already two splits deep (recorded depth 2 or more); `--force` overrides the refusal. **This differs from the tracker issue's text on purpose:** the issue asks for the parent to be closed at `split --accept`; the maintainer decided at Plan that the parent stays open until its children are done. That decision is recorded only in this brief — the tracker thread has no comments — and it leaves the issue's own complaint (open parents count as open work in the milestone) standing. So this slice does not fully resolve #545 as the issue is written today; what happens to #545 is the human's to settle at sign-off (Open question 6).
- **Success criterion:** The new test file shows all of the following, with `gh` faked. **Parent close — driven through `cleanup.run(…, apply=True)`** on a bundle that is COMPLETE, carries `close-disposition` = `split`, has a `split-lineage.json` naming children 601 and 602, and whose tracker issue is OPEN: **(P1)** one child issue OPEN, the other CLOSED → no `gh issue close` and no `gh issue comment` call is made for the parent; the report line for the parent names the child still open; rc 0. **(P2)** both children CLOSED, at least one with reason completed → exactly one `gh issue close <parent>` call, carrying `--repo <owner/repo>`, `--reason completed`, and a `--comment` whose text contains `#601` and `#602`. **(P3)** both children CLOSED and neither completed (both "not planned") → exactly one close call for the parent with `--reason "not planned"` and a comment naming `#601` and `#602`. **(P4)** a child's issue state cannot be read (the `gh issue view` for it fails) → no close call for the parent; the report line says the child's state is unknown. **(P5)** the parent's lineage record is missing, not valid JSON, or names no children → no close call; the report line says the children are unknown and the issue must be closed by hand. **(P6)** without `--apply` (dry run), case P2 prints a `would:` line and makes no close call. **(P7)** a COMPLETE bundle with an empty patch and NO split marker is still closed as "not planned", exactly as today. **(P8)** case P2 again, but the parent bundle also holds a non-empty `tracker-comment.md` whose text names no child → the one close call's `--comment` still contains `#601` and `#602` (today `_close_issue` would post the file's text alone). **(P9)** the parent also carries a `publish.json` with a `pr_url` whose PR reads MERGED, and one child issue is OPEN → no `gh issue close` and no `gh issue comment` call for the parent; the report line names the child still open (today this parent is closed as completed with "Fixed by …"). **Depth — driven through `cli._split`:** **(D1)** `--accept` on a parent whose `split-lineage.json` records `depth` 2, and on one that records `depth` 3, returns non-zero without `--force`; no `gh issue create` call was made, no child bundle exists, the parent has no `close-disposition` marker, and stderr names the recorded depth and `--force`. **(D2)** The same two parents with `--force` are accepted (rc 0, children on disk with `depth` 3 and 4). **(D3)** A parent with no lineage record (depth 0), and a parent that records `depth` 1, are both accepted without `--force`, as today; the depth-1 parent's children record `depth` 2. **(D4)** A parent whose lineage file is not valid JSON, or whose `depth` is not a usable number (`"one"`, `null`, `true`), is treated as depth 0 and accepted. **Words — text checks in the same new test file:** **(S1)** the planner role prompt (read the way `ThePlannerIsToldItOwnsTheSplit._role` does, `template/tests/test_split.py:982-987`, so it works on the template and on a rendered instance) contains `--force` and the phrase `stays open`; and the blank-line-separated paragraph that contains `--force` also contains the word `human` — the prompt must tell the planner that `--force` is the human's decision and that the planner does not pass it unless the human has asked for it in so many words. **(S2)** `cleanup.__doc__` (the module's reconciliation matrix) contains both `split` and `children`. **Held outside the new file:** **(S3)** `cd template && PYTHONPATH=src python3 -m unittest tests.test_split` still passes, and the assertions in `TheDoctrineIsConsistent` (`test_split.py:464`) and `ThePlannerIsToldItOwnsTheSplit` (`test_split.py:977`) are not loosened or removed to get there. C4 runs only test files the patch touches, so this one is held by the advisory T3 suite run and by Do recording the command's result; the human reads that result at sign-off. **(S4)** the two remaining text edits — the table in the target's `docs/07-crosscutting.md` and the comment in `template/pdca.toml.jinja` — have no test (a template test cannot see the target's `docs/`); they are checked by reading the diff at sign-off, together with the prompt wording, which is already a human-judged item.
- **Falsifiability:** RED is reachable in the offline driver suite on the target's `main`, with the C4 gate's own command (`cd template && PYTHONPATH=src python3 -m unittest tests.test_split_parent_lifecycle`, which is what the C4 gate runs for a `template/tests/*.py` file the patch touches — the gate is the `pdca-pdca` instance's own `engine/scripts/run-verify.sh` (`run_tests`, `:175-194`), not the unfilled skeleton at the target's `template/engine/scripts/run-verify.sh`). Its red leg reverts every hunk outside `tests/` and `template/tests/` (`:216-219`), so the prompt and docstring edits are reverted too and S1/S2 go red with the rest — neither `--force` / `stays open` in the planner prompt nor `split` / `children` in `cleanup.py` exists on `main` today (checked by grep on the revision pass). Both reds were checked at Plan on the gate's interpreter. Parent close: a throwaway probe built on the `test_cleanup.py` fixture set up the P1 case, and today's code issued `gh issue close 500 --repo example-org/example-repo --reason "not planned" --comment "Closed as not planned: the review concluded a close/no-fix disposition (see the cycle records)."` while child 601 was still open — so P1, P2 and P4 fail on their assertions without the fix. Depth: today a depth-2 parent is accepted with rc 0 (there is no check), so D1 fails. With the production hunks reverted the tests still import and run — they use only `cleanup.run`, `cli._split`, `split.read_lineage`, `split.LINEAGE`, `state.CLOSE_MARKER` and `Config`, all of which exist today — so this is a real "ran and failed" red, not an import failure. No live tracker, network or real `gh` is needed or allowed.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No dependency on, and no shared file with, issue 496 (which only adds tests to `template/tests/test_flow_adopt_split.py`). The two can build in the same wave.
- **Surfaces:** data
- **Scope:** Two behaviours, one issue. (1) In `pdca cleanup`, a finished split parent (COMPLETE, `close-disposition` = `split`) with an open tracker issue follows its own rule — wait while any child issue is open or unreadable; close as "completed" once all children are closed and at least one was completed; close as "not planned" if all children are closed and none was completed; the closing comment names every child, whether or not the bundle has a `tracker-comment.md` — instead of falling into the generic "empty patch → not planned" action. For a COMPLETE bundle with the split marker this rule decides first, ahead of the recorded-PR checks as well: a split parent that still carries a merged PR from an attempt made before the split waits on its children like any other. (2) `pdca split --accept` refuses to split a bundle whose recorded lineage depth is 2 or more unless `--force` is given; add that `--force` flag to the `split` subcommand. (3) Documentation: the reconciliation table in the target's `docs/07-crosscutting.md` (the `pdca cleanup` section, `:667-675`) and the matrix in `cleanup.py`'s module docstring (`cleanup.py:10-27`) gain the split-parent row; `template/agents/planner.md.jinja:153` and `template/pdca.toml.jinja:509` say that the parent issue stays open until its children are done and that a bundle two splits deep is not split again without `--force`. The planner prompt must also say that `--force` is the human's decision: the same block tells the planner agent to run `split <id> --accept` itself (`planner.md.jinja:139-162`), so without that sentence the agent that meets the refusal could simply re-run with `--force` and the bound would hold nothing. What holds item (3): criteria S1–S4. / out of scope: any tracker call for the parent at `split --accept` (it neither closes nor labels the parent — see Open questions for the label); closing a parent automatically from inside a `pdca flow` run (the trigger is `pdca cleanup` only); a split parent that ended DISCONTINUED rather than COMPLETE (today's "discontinued → not planned" action is left as is); changing the close reason of parents that were already closed before this change; a new `[tracker]` config key; how the flow adopts children; refusing or warning on the draft step `pdca split <id>` (no `--accept`); a second copy of the depth in `notes.json` — the depth is already recorded (Design §3); the WIP cap (#544) and `flow --only` (#546).
- **Difficulty:** medium
- **External dependencies:** none
- **Test file:** template/tests/test_split_parent_lifecycle.py — a NEW file. The C4 gate keeps test files and reverts production files, so either a new or an appended test would earn its red; a new file is chosen so the gate runs only these cases.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer callsites Do MAY open: **(a)** where the new rule must sit and what it must pre-empt — the `remote state == "OPEN"` / `COMPLETE` branch of `cleanup._plan_bundle`, `template/src/pdca_harness/cleanup.py:307-344`; the generic empty-patch close at `:329-335` is the action a split parent must no longer reach. **(b)** how an issue is closed with a comment — `cleanup._close_issue`, `cleanup.py:162-199`; reuse it (repo always passed explicitly, a failed close reported and never raised). Note it prefers a bundle's `tracker-comment.md` as the body (`cleanup.py:174-177`; held for ordinary bundles by `test_bundle_tracker_comment_file_is_preferred`, `template/tests/test_cleanup.py:383`, which must keep passing): for a split parent the comment that names the children must be what is posted even when that file exists — criterion P8. Where the split rule sits relative to the recorded-PR checks at `cleanup.py:313-328`: before them — criterion P9; the fixture's `_staged(…, pr_url=…)` and `pr_states` (`test_cleanup.py:103-114`, `:387`) set that case up. **(c)** how an issue's state is read, fail-closed — `cleanup._issue_state`, `cleanup.py:70-85` (returns `state` and `stateReason`; `None` means unknown, and unknown never acts). **(d)** how a split parent and its children are recognised — `split.read_lineage` (`template/src/pdca_harness/split.py:605-634`, the one tolerant reader) and the marker test in `flow._is_split_parent` (`template/src/pdca_harness/flow.py:907-930`). A tolerant reader of the record's `children` list already exists — `flow._lineage_children`, `flow.py:690` (never raises on `{"children": 7}` or a null entry); use that behaviour rather than write a second, different one, and if importing it into `cleanup.py` is not possible say why in `build-notes.md`. **(e)** where an ids-independent refusal must sit so it runs before anything is filed — `split.preflight`, `split.py:294-327`, called from `cli.py:805-808`; and how depth is read — `split._recorded_depth`, `split.py:637-654`. **(f)** test fixtures to mirror — `CleanupBase` in `template/tests/test_cleanup.py:49-116` (argv-keyed fake `gh`, `issue_states`, `_run`, `_closes`) for P1–P7; `TheWholeChainUnmocked` in `template/tests/test_split.py:1397-1448` (fake `gh` on `pdca_harness.split`, run driven through `cli._split`) for D1–D4. **Which tree a path is in:** every `template/…` and `docs/07-crosscutting.md` path in this brief is in the target repo. `engine/scripts/run-verify.sh` and `docs/INTEGRATION.md` are this `pdca-pdca` instance's own files (the gate and its rules); the target has neither under those names and Do does not need to open them.
- **Prior-art check (triage cycles):** By path (run at Plan from the instance root, where `../pdca-harness` is the target checkout), `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/split.py template/src/pdca_harness/cli.py`: `5ced9bd` (#481, parent keeps a brief), `f0bac00` (#467, children inherit milestone/labels), `9a19cb5` (#466), `a2eefe1` (#459), `5c83070` (#456 — this one already records `depth` in `split-lineage.json`), `3a3d8ce`, `f81c4a0` (#566). None refuses on depth. `cleanup.py` has no reference to the split marker or the lineage record anywhere in the file. Closed-unmerged PRs touching `split.py`, `cli.py`, `cleanup.py`, `test_split.py` (INTEGRATION §5 command): none. Open PRs: none. `gh search issues --repo eduralph/pdca-harness "split depth"` / `"split parent close"`: only #545 itself open; #448, #459, #481 closed and not the same change.
- **Disposition hint:** new-feature
- **Plan-review response:** Six findings changed the brief. The Goal now claims only what Scope delivers (COMPLETE parents; DISCONTINUED stays out, Open question 5). Scope item (3) has criteria (S1–S4), including the rule that `--force` is the human's decision, so the prompt edit cannot undo the refusal it documents. P8 holds the `tracker-comment.md` case. P9 and Design §1 settle precedence: the split rule decides before the recorded-PR checks — this follows from the maintainer's "stays open until its children are done", but it is a new statement and the human should confirm it. The instance-vs-target paths are labelled and the existing children reader is cited. Three findings stand, each the human's call and each now written down where sign-off will see it: (a) the reversal of the issue's first acceptance line and what becomes of #545 — Open question 6; (b) the depth threshold — Design §4 now quotes the clause of the issue that argues for the stricter reading, Open question 1; (c) one bundle or two — Open question 7; this pass may not create bundles, and the two halves share no file, so splitting later costs nothing extra.

## Motivation

`pdca split --accept` files each child as a GitHub sub-issue of the parent. Two things
then go wrong.

**The parent's tracker status is wrong at both ends.** While the children are being
built the parent sits open with nothing saying when it will close. And when someone runs
`pdca cleanup --apply` after the parent's sign-off, the parent is closed as "not planned"
with the comment "the review concluded a close/no-fix disposition" — because a split
parent has no patch, and `cleanup` treats every finished bundle with no patch as a
no-fix close (`cleanup.py:329-335`). That is false twice over: the work was not dropped,
it moved into the children, and they may still be open. The right record is the one the
maintainer asked for at Plan: the parent stays open while its children are in progress,
and is closed as **completed** once they are all done.

**Splits nest without limit.** In the Wyrd instance one slice was split three levels
deep (#654 → #692 → #717 → #771/#772). Source: the issue body and `getwyrd/wyrd-pdca`
`docs/2026-09-11-backlog-reversal-proposal.md` §1–§2. Splitting takes minutes; building a
wave takes hours to days, so without a bound the cycle opens issues faster than it
closes them.

The tracker issue itself proposed closing the parent at `split --accept`, so that open
parents stop counting as open work in the milestone. The maintainer chose the other
direction at Plan: a parent that is closed before its children land reads as finished or
dropped when it is neither. This proposal therefore does **not** reduce the milestone's
open count while children are in flight; see Open questions for the label that could.

## Design

**1. The split-parent rule in `pdca cleanup`.** `cleanup` is the command that already
reconciles bundles against the tracker, and the one that already closes an issue as
"completed" when its PR has merged. It gains one case: the bundle is COMPLETE, its close
marker says `split`, and its tracker issue is OPEN. The case is checked first among the
COMPLETE-and-OPEN actions — before the recorded-PR checks (`cleanup.py:313-328`) and
before the generic empty-patch case (`:329-335`). The PR checks matter because
`split.accept` archives the rejected attempt's patch and summary but not `publish.json`
(it is not in `state.DOWNSTREAM_OF_BRIEF`, `state.py:116`), so a parent that was
published once and split afterwards can still carry a `pr_url`; if that PR merged,
today's code closes the parent as "Fixed by …" with its children still open. For that
bundle it reads the children from the lineage record and each
child's issue state from the tracker:

| Children's issues | Action on the parent |
|---|---|
| any child OPEN | report only — "waiting on #…"; no tracker change |
| any child's state unreadable, or a child id that is not a tracker number | report only — state unknown; no tracker change |
| no readable children record, or an empty one | report only — close by hand |
| all CLOSED, at least one as completed | close as `completed`, comment names every child |
| all CLOSED, none completed | close as `not planned`, comment names every child |

The children's state comes from the **tracker**, not from the local child bundles: a
child bundle may be archived, cleaned up, or never have existed in this checkout (the
`--ids` path), while its issue is the thing a merged PR closes.

A child that was itself split needs no special case. Its own issue stays open until its
children are done and is then closed by this same rule, so the grandparent simply waits
on it. `cleanup` visits bundles in name order, so a chain may need one `cleanup --apply`
run per level; that is acceptable and should be said in the report line ("waiting on
#601") rather than worked around.

"Completed" is read from the child issue's `stateReason`. The real `gh` prints it in
upper case (`COMPLETED`, `NOT_PLANNED` — checked at Plan with `gh issue list … --json
stateReason` on the target repo, gh 2.101.0), while the existing test fixture uses lower
case (`test_cleanup.py:26-27`). Compare without regard to case, and have the new tests
cover the upper-case form.

The closing comment always names every child. `_close_issue` posts a bundle's
`tracker-comment.md` in place of the fallback text when that file exists
(`cleanup.py:174-177`); for a split parent the posted comment must still contain each
child's `#<id>` in that case (P8). How the hand-written text and the child list are
combined is Do's choice.

Everything else in `cleanup` stays as it is: dry run by default, one row per bundle,
unknown never acts, one failing row never stops the sweep.

**2. Nothing changes at `split --accept` for the parent's issue.** No close, no comment,
no label. `split.accept` and the CLI's `--accept` path make exactly the tracker calls
they make today.

**3. Depth.** Nothing new is recorded. `materialise` already writes `depth` = parent's
depth + 1 into each child's `split-lineage.json` (`split.py:717`, `:729`; shipped with
#456), and `_recorded_depth` (`split.py:637-654`) already reads it safely. The issue's
"record `split_depth` in the child bundle's notes" is met by that record; a second copy in
`notes.json` would be two sources for one fact.

The new part is the refusal: `--accept` on a bundle whose recorded depth is ≥ 2 exits
non-zero unless `--force` is passed. It is an ids-independent refusal, so it runs with
the others, before any issue is filed and before anything is written. A record that is
not valid JSON, or a `depth` that is not a usable number, counts as depth 0 and is not
refused — the same "a damaged hint never blocks the run" rule the lineage reader follows.
(A lineage path the OS cannot read at all is already refused by `split.accept`,
`split.py:893-904`; that stays as it is.)
The message names the recorded depth, says a slice this deep is meant to be built or
dropped rather than split again, and names `--force`.

`--force` is a new flag on the `split` subcommand (`cli.py:187-196`). It overrides only
the depth refusal — not the "already marked" refusal, not proposal validation, not the
stub-proposal guard.

**4. Threshold.** Depth ≥ 2 refuses; depth 0 and 1 are accepted. With the existing
numbering (a child of an unsplit parent is depth 1) that allows original → children →
grandchildren, and refuses to split a grandchild. This is the issue's text taken as
written ("refuse `split --accept` at depth ≥ 2", "`split --accept` on a depth-2 bundle
exits non-zero") and it stops the three-level chain the issue cites (#717 was depth 2
when it was split into #771/#772). The maintainer chose this reading at Plan over the
stricter "a child is never split again".

The issue's text pulls both ways, and the other half should be on the table at sign-off.
The same sentence that says "at depth ≥ 2" ends "**so a slice is split at most once by
default**". Under the existing numbering those two do not agree: a depth-1 bundle is
already the product of one split, and D3 lets it be split again without `--force`, so
by default a slice can be split twice. The stricter reading (refuse at depth ≥ 1) matches
"at most once"; the chosen one (refuse at depth ≥ 2) matches the number and the
acceptance line. D3 turns the chosen reading into a test, so changing it later means
changing D1–D3 as well as the constant. Keep the threshold in one named place so a
later change of mind is a one-line edit.

**5. Existing tests to keep in view.**
- About twenty existing tests call `cli._split` with a bare
  `SimpleNamespace(issue_id=…, accept=True, ids=…)` that has no `force` attribute (for
  example `test_split.py:612`, `:1165`, `:1448`; `test_flow_single_driver.py:261`;
  `test_split_hint_live_run.py:210`). The CLI must treat a missing `force` as false, or
  those tests must be updated — either way none may start failing.
- `test_complete_close_disposition_closes_not_planned` (`test_cleanup.py:356`) holds the
  generic empty-patch close for a bundle with no split marker. It must keep passing
  unchanged (criterion P7 is the same guarantee from the new file).
- Two suites hold prompt wording: `TheDoctrineIsConsistent` (`test_split.py:464`) and
  `ThePlannerIsToldItOwnsTheSplit` (`test_split.py:977`). The prompt edit adds sentences
  and should not need either suite changed; both must stay green with their assertions
  as they are (criterion S3). If an edit genuinely cannot be made without changing one of
  them, stop and say so in `build-notes.md` rather than loosening the assertion.

## Alternatives considered

- **Close the parent at `split --accept`** (what the tracker issue proposes). It takes
  the parent out of the milestone's open count at once, but a parent closed before its
  children land reads as finished or dropped. Rejected by the maintainer at Plan.
- **Close at `--accept` as "not planned", then change the reason to "completed" when the
  children are done.** Keeps the open count down and ends with the right record, but
  needs a direct API call to change the reason of a closed issue and shows a wrong
  status in between. Rejected by the maintainer at Plan in favour of leaving it open.
- **Close the parent from inside the flow when the last child is accepted.** A child is
  done when its PR merges, which a human usually does outside the run, so the run cannot
  know. `cleanup` is the command that already reads that state.
- **Decide "children done" from local child bundles.** Simpler, but wrong when a child
  bundle is archived or absent; the tracker is the source of truth for issue state.
- **A configurable depth limit.** A number in `pdca.toml` is more surface than the need
  calls for; `--force` is the escape.

## Impact & compatibility

- **Behaviour change in `pdca cleanup --apply`:** a finished split parent is no longer
  closed as "not planned" while its children are open. It is reported as waiting, and
  closed as "completed" on a later run once they are all closed. Parents that an earlier
  `cleanup` already closed as "not planned" are not touched.
- **The closing step is not automatic.** It happens the next time someone runs
  `pdca cleanup --apply` after the last child's issue has closed.
- **Behaviour change:** splitting a bundle at depth 2 or more now needs `--force`.
  Splitting an original issue or a direct child works as before. The flow still adopts
  and drives deeper splits that already exist or that were forced — adoption reads the
  lineage and is untouched.
- **Open parents still count as open work** in the milestone until their children are
  done. The tracker issue's original complaint is not addressed by this slice. A PR for
  this slice that closes #545 would close an issue whose problem statement is still true
  (Open question 6).
- **A split parent with a merged PR from before the split** is no longer closed as
  "Fixed by …" while its children are open; it waits and is closed with the comment that
  names them.
- **No template question changes** in `copier.yml`, so no `copier update` compatibility
  concern. The role-prompt edit (`template/agents/planner.md.jinja`) is a human-judged
  item at sign-off per `docs/INTEGRATION.md` §4.
- **Supplementary evidence (not the binding criterion):** the full offline suite and the
  root render suite stay green (T3, advisory).

## Open questions

1. **Depth threshold — chosen at Plan, to be confirmed at sign-off.** The maintainer
   chose: refuse at recorded depth ≥ 2 (a child may be split once more; a grandchild may
   not). The plan review pointed out that the issue also says "so a slice is split at
   most once by default", which this reading does not give (Design §4). Confirm the
   choice with that clause in view.
2. **When the parent closes — chosen at Plan, to be confirmed at sign-off.** The
   maintainer chose: the parent stays open until all children are done, then closes as
   "completed". This reverses the issue's first acceptance line and is written down
   nowhere but this brief.
3. **A `split` label on the open parent.** GitHub has no custom issue status, so an open
   split parent looks like any other open issue. A `split` label added at `--accept`
   would mark it as a container and let milestone views filter it out
   (`-label:split`). Not in this slice; it would add tracker calls at `--accept`.
4. **All children dropped.** This brief closes the parent as "not planned" when every
   child was closed without being completed (P3). The alternative is to leave it open
   for a human.
5. **A split parent that ended DISCONTINUED.** Left on today's path (closed as "not
   planned", `cleanup.py:339-344`). Should it follow the split rule too? The flow treats
   such a parent as a live split — DISCONTINUED is in `_TERMINAL` (`flow.py:687`), which
   is all `_is_split_parent` asks for (`flow.py:924-928`) — so its children can be
   adopted and driven while `cleanup` closes the parent. The Goal is worded to exclude
   this case; bringing it in would be one more branch and one more test.
6. **What happens to #545.** This slice delivers the issue's second acceptance line (the
   depth bound) and the opposite of its first. Three ways to leave the tracker honest:
   rewrite #545's text to the decision taken here and let the PR close it; keep #545 open
   for the milestone-count complaint and have the PR reference it without closing it; or
   close it and file the `split` label (question 3) as its own issue. Whichever is
   chosen, the decision to reverse the acceptance line should be posted on the #545
   thread, since today it exists only in this brief. Note that `pdca cleanup` closes an
   issue whose recorded PR has merged, so "keep it open" needs a deliberate step.
7. **One bundle or two.** The parent-close rule (`cleanup.py`, P1–P9) and the depth bound
   (`split.py` + `cli.py`, D1–D4) share no production file and no fixture. They are kept
   together because the issue asks for both. Splitting them would let the depth bound
   land against #545 on its own while the parent-close decision is confirmed. Human's
   call; if taken, it is done with `split` at Plan, not by Do.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild to fix the implementation issues found at Check. The design in the brief is kept as is (depth >= 2, parent stays open until children are done, one bundle); the design questions in §6 were not settled this round and stay open for the next sign-off. 1. Partly damaged child list closes the parent too early (reviewer C3 FAIL). cleanup._split_parent_row uses flow._lineage_children, which silently drops non-string/blank entries. A lineage record like ["601", null] or ["601", 602] with #601 closed makes cleanup close the parent naming only #601. In cleanup, the whole recorded children list must be usable before a close is allowed: if ANY entry is not a non-blank string, report "children unknown — close by hand" and take no action. Keep flow's tolerant reader unchanged for the flow. Add regression tests for the mixed valid/invalid cases (["601", null], ["601", 602]). 2. Prompt and config text overpromise (reviewer T2 FAIL). template/agents/planner.md.jinja (~:164) and template/pdca.toml.jinja (~:513) say cleanup closes the parent "as completed" once all children are closed. Qualify both to match the code and the docs table: completed if at least one child was completed, else not planned; COMPLETE parents only. 3. Code-review nits: rewrap the 120-char _close_issue docstring line (cleanup.py ~:186); for a non-numeric child id, say "close by hand" in the report like the empty-children line does; rename test_d1_a_bare_namespace_without_force_is_refused_too (it passes force=False, so it is not bare) or drop the kwarg; in P8 also assert the hand-written note is kept in the comment.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rebuild to fix the implementation issues found at Check. The design in the brief is kept as is (depth >= 2, parent stays open until children are done, one bundle); the design questions in §6 were not settled this round and stay open for the next sign-off.

  1. Partly damaged child list closes the parent too early (reviewer C3 FAIL). cleanup._split_parent_row uses flow._lineage_children, which silently drops non-string/blank entries. A lineage record like ["601", null] or ["601", 602] with #601 closed makes cleanup close the parent naming only #601. In cleanup, the whole recorded children list must be usable before a close is allowed: if ANY entry is not a non-blank string, report "children unknown — close by hand" and take no action. Keep flow's tolerant reader unchanged for the flow. Add regression tests for the mixed valid/invalid cases (["601", null], ["601", 602]).
  2. Prompt and config text overpromise (reviewer T2 FAIL). template/agents/planner.md.jinja (~:164) and template/pdca.toml.jinja (~:513) say cleanup closes the parent "as completed" once all children are closed. Qualify both to match the code and the docs table: completed if at least one child was completed, else not planned; COMPLETE parents only.
  3. Code-review nits: rewrap the 120-char _close_issue docstring line (cleanup.py ~:186); for a non-numeric child id, say "close by hand" in the report like the empty-children line does; rename test_d1_a_bare_namespace_without_force_is_refused_too (it passes force=False, so it is not bare) or drop the kwarg; in P8 also assert the hand-written note is kept in the comment.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
