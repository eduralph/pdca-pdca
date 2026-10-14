# Build notes — issue 633 / fold-refuses-a-rewritten-carried-branch (iteration 2)

Target: `eduralph/pdca-harness` `main` @ `41210bc` (worktree `pdca-harness.pdca-wt-l0`).
That is origin/main today. It already holds #623 (`3ff7b49`) and #631 (`41210bc`), as the
brief's ordering note expects, so the brief's `b5f5c29` line numbers have moved. Line
numbers below are post-patch in that worktree unless marked "base" (= `41210bc`).

## What the carry-forward asked for, and how this attempt answers it

Attempt 1 checked each carried branch up front (fetch + ancestry check, outside the
integration lock), then skipped the fold's own fetch for those targets and let the merge
read `origin/<branch>` again. Check found two problems:

1. **C5 race (reviewer).** The merge re-read a mutable ref. With two bases in one
   checkout, the second target's fetch refreshes the first target's branches, so a
   rewrite landing between "checked" and "merged" was merged unchecked: both A histories
   on the line, and the record overwritten with the rewritten head.
2. **Lock snapshot (sign-off).** With the fold's fetch skipped, the moved-line check
   (#591) and the merges read a snapshot fetched before `integ_lock` was taken. A line
   another run moved meanwhile was only refused by the unforced push, with the generic
   "could not push" message instead of the #591 one.

This attempt fixes both:

- **The merged commit is the checked commit.** `_carried_tips` (`integrate.py:526-563`)
  resolves each carried branch's tip ONCE, after a fetch, checks it, and returns the SHA.
  The merge loop uses that SHA for carried bundles and never reads the branch again
  (`integrate.py:491-492`); `_merge_published` now takes the resolved `head` instead of
  calling `_rev` itself (`integrate.py:566-575`; base `:494-502`). Nothing that happens
  after the check (a fetch for a later target, or a `pdca publish` pushing from the same
  primary checkout, which updates `refs/remotes/origin/<branch>` without any fetch,
  `publish.py:319`) can change what is merged. A rewrite that lands after the check is
  not merged by this fold; the record keeps the checked head, so the next fold refuses it.
- **The fold's own fetch is back under the lock.** There is no `fetched` skip and no
  `fetch=` keyword any more: `_prepare_worktree` fetches exactly as on base
  (`integrate.py:459-460`, `:878-883`), after `integ_lock` is taken (`:451`), so the
  moved-line check (`:461-471`) reads a snapshot taken under the lock, as before #633.
  The cost is the one the sign-off named: one extra fetch per target per fold that has
  carried heads (the up-front one in `_carried_tips`).
- **Every check finishes before any target merges or pushes.** `_carried_tips` runs over
  all targets, in the same sorted order as the main loop, before the loop starts
  (`integrate.py:410-414`). Because the merge uses the checked SHA, no later re-check is
  needed, so there is no case where target 1 pushes and target 2 then refuses a rewrite.

I did not follow the sign-off's literal recipe ("call `_refuse_rewritten` again for that
group's carried bundles after that fetch, and merge"). Its aim was "the merge then uses
the same snapshot the check passed". Pinning the SHA gets that more strictly, for two
reasons that are not about cost:
- A re-check after each target's own fetch still runs per target. With two targets, a
  rewrite of a target-2 branch that lands after target 1 pushed is caught only then:
  target 1 has already pushed. Merging the up-front-checked SHAs never splits a fold that
  way.
- Without pinning, a re-check followed by a merge of the ref still reads the ref twice, so
  a push from the shared checkout between the two reads (publish pushes from it) can swap
  the commit again. Pinning has no such window.
The extra code a re-check would need is small (a `_rev` + `_in_line` per carried bundle in
the loop, about 8 lines); I left it out because it changes the semantics above, not to
save lines.

## What changed

### `template/src/pdca_harness/integrate.py`

- `fold(..., carried: dict[str, str] | None = None)` (`:296`), filled in place like
  `skipped` (base `:290`, `:351-360`). Docstring paragraph `:369-379`; the sentence about
  moved branches (base `:325-326`) now says only a forward move is merged (`:331-333`).
- Up-front check (`:410-414`): `checked = _carried_tips(...)` when `carried` is non-empty
  and this is not a dry-run. It sits right after the `refs` resolution and grouping
  (`:385-408`), outside the per-bundle `skipped` try/except (`:493-499`), as the brief
  asks.
- `_carried_tips` (`:526-563`): per target with carried bundles (sorted), `_fetch` the
  checkout (only the carried bundles' remotes; origin and the base remote are always
  included by `_fetch`), then for each carried bundle `tip = _rev(repo, ref)`. A branch
  that does not resolve returns None and is left to `_gone_branch` (criterion 3). Else
  `tip == took` or `_in_line(repo, took, ..., of=tip)`; `_in_line` raises on git's exit
  128, never reading it as "no" (base `:733-744`). Anything else raises
  `IntegrationError`. Never decided by a commit message.
- The message names the bundle, the ref (`origin/fix/A`), the line, both short SHAs and
  the word "rewritten"; says which actions cause it (re-publish, force-push, "Update with
  rebase"); says only fast-forwards (including the merge-style "Update branch") reach the
  line; says nothing was merged or pushed; and gives the brief's two ways out: restore the
  branch to the head or a descendant and re-issue, or let the run stop and re-issue.
- Merge loop (`:489-502`): `head` = the checked SHA for a carried bundle, else `_rev(wt,
  ref)` exactly as `_merge_published` did on base (`:502`). After a successful
  `_merge_published` (try/else), a non-None head goes into `took`.
- Recording (`:520-521`): `carried.update(took)` only after that target's push succeeded.
  A failed fold records nothing, a skipped bundle is never recorded, and a gone branch
  (head None) is not recorded.
- `IntegrationError` docstring lists the new cause (`:70-73`). Module docstring paragraph
  (base `:39-40`) now says only commits that extend a branch reach the line and a rewrite
  stops the next fold (`:39-45`).

### `template/src/pdca_harness/flow.py`

- `_fold_lines` takes `carried` and passes it to `integrate.fold` (`:796`, doc `:805-808`,
  call `:816-817`).
- `_drive_and_act` creates one `carried_heads: dict[str, str] = {}` per run next to
  `folded_tips` (`:2146-2148`) and passes it to the in-run fold (`:2349-2352`).
- The #646 carry call (`flow.py:981-983`) is untouched: it passes no mapping, so it never
  checks (criterion 2b). Not touched, per the ordering note: `_runnable`, the
  "pushed no branch" announcement (`:2340-2345`), `_carry_finished`.

### `docs/07-crosscutting.md:666-671`

The sentence at base `:665-666` now says commits reach the line only when they extend the
branch; a rewrite stops the run before it merges or pushes; what to do. Re-wrapped so the
hunk ends on the original "If a PR merges and its" line break.

## Tests (`template/tests/test_integrate_stack_bases.py`, appended to `StackFoldGit`)

Section `:1151-1385`; module docstring note `:27-29`; `state` added to the import (`:51`).

| Test | Line | Criterion | Red leg (fix reverted) |
|---|---|---|---|
| `test_a_carried_branch_rewritten_mid_run_stops_the_fold` | 1185 | (1): brief's exact sequence, non-conflicting rewrite (`a2.txt`); asserts `issue_A`, `fix/A`, `rewritten`, `Restore`, `re-issue`; no `git merge`/`git push` ran; line still `t1`; one `carried` dict for both folds | FAIL: `IntegrationError not raised` |
| `test_a_conflicting_rewrite_is_named_a_rewrite_not_an_overlap` | 1210 | (1b): rewrite edits `a.txt`; `rewritten` in, `cross-wave overlap` out | FAIL: got the old "...an undeclared cross-wave overlap..." |
| `test_a_fast_forward_of_a_carried_branch_is_merged_and_recorded` | 1224 | (2) with the record on: fixup merged, record moves to the new heads, no-op fold passes | passes (pins non-regression) |
| `test_the_carry_with_no_record_merges_a_rewritten_branch_as_before` | 1244 | (2b): `skipped={}`, no `carried` → merged as on base | passes (pins non-regression) |
| `test_a_carried_branch_deleted_after_its_merge_is_judged_as_gone` | 1255 | (3) with the record on: `_gone_branch` still decides | passes (pins non-regression) |
| `test_a_rewrite_between_two_targets_fetches_never_reaches_the_line` | 1275 | Check C5 repro: `main` + `zbase` in one checkout; force-push of fix/A injected just before the 2nd real fetch; R never on main's line, record stays at the checked head, next fold refuses | FAIL at the next fold: `IntegrationError not raised` |
| `test_a_line_moved_before_a_carried_fold_takes_its_lock_is_refused_as_moved` | 1315 | Sign-off finding: line moved by "another run" just before the lock is taken; must get the #591 moved-line refusal naming both tips | passes (the bug it guards against was attempt 1's, not base's) |
| `test_a_run_stops_when_a_branch_it_carried_is_rewritten` | 1343 | Flow plumbing, end to end: real `flow._drive_and_act`, 3 waves, real git; fix/A re-published while wave 1 builds; run stops after wave 1, C never built, line left at the post-wave-0 tip | FAIL: run did not stop |

The flow test replaces attempt 1's "same dict object" check, which the advisory review
noted proved only identity. This one proves the record actually crosses folds in a real
run.

## Red → green (project runner)

C4 gate, `engine/scripts/run-verify.sh`, run from the instance root with `PDCA_BUNDLE` and
`PDCA_WORKTREE` set (wrapped in `timeout`), on the final patch:

- Green leg: `Ran 62 tests ... OK`.
- Red leg (production hunks of `integrate.py` and `flow.py` reverted, test kept):
  `Ran 62 tests ... FAILED (failures=4)` — the four rows marked FAIL above, all on
  assertions, no `_FailedTest`, no `TypeError`.
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.

Also run on the patched tree:
- T3 script `engine/scripts/run-suite.sh`: root suite `Ran 24 tests ... OK` (copier
  render/update cases included), driver suite `Ran 2431 tests ... OK (skipped=2)`. This ran
  before my last two text-only edits (the error message's wording, the docs re-wrap).
- After those edits: `test_integrate`, `test_integrate_clean_tree`,
  `test_integrate_stack_bases`, `test_flow_resume_stack_prereqs`, `test_flow_slice`,
  `test_flow_adopt_split`, `test_flow_out_of_batch_prereq_hold`: `Ran 270 tests ... OK`;
  C4 re-run as above.
- T2 script `engine/scripts/run-docs-check.sh`: `docs lint clean, site render + link
  audit clean`.

### Mutation checks (do the new tests catch the two Check findings?)

Each mutation was applied by hand, run, and reverted; the worktree was then compared
byte-for-byte with `patch.diff`.
- **No pinning** (merge loop reads `_rev(wt, ref)` for every bundle, i.e. merges the ref
  as it is after the fold's later fetches): `test_a_rewrite_between_two_targets...` FAILS
  with `True is not false : the rewrite reached the line` — the reviewer's C5 observation.
- **No under-lock fetch** (`_prepare_worktree` skips `_fetch`, as attempt 1 did for
  checked targets): `test_a_line_moved_before_a_carried_fold...` FAILS with the message
  `could not push pdca-integration/main to origin (an unforced fast-forward was refused —
  did another run move it? #591)...` — exactly the sign-off's description.

## Self-refutation

- **(a) Genuine red? Yes.** The C4 script reverted the production hunks and re-ran the
  module: 4 failures on assertions — the silent merge (`IntegrationError not raised`),
  the overlap misdiagnosis (message quoted above), the race case's next fold not
  refusing, and the flow run not stopping. No load error.
- **(b) Production path? Yes.** Every test calls the real `integrate.fold`; the flow test
  calls the real `flow._drive_and_act`, whose real `_fold_lines` and real fold do the
  work. Stand-ins are only at the edges, the way the file's other tests already do it:
  `merged.merged_head` (the host lookup) in the gone-branch test; `integrate._git` wrapped
  by spies that call the real function (one also performs a real force-push between
  fetches); `integrate.integ_lock` wrapped to move the line and then take the real lock;
  in the flow test `_drive_wave` (the model leaves), `_publish_bundle` (swapped for the
  fixture's real-git publish, as `test_flow_resume_stack_prereqs.py:115-121` does) and
  `publish.draft_texts`.
- **(c) Fixture includes the fault? Yes.** `fix/A` really is force-pushed on the bare
  origin to a commit cut from `origin/main` that lacks the folded head — asserted in
  `_fold_then_rewrite_a` (`assertFalse(self._ancestor(head, rebuilt))`), the same shape
  as `publish`'s `--force-with-lease` re-publish (`publish.py:312-319`). Both the
  non-conflicting and the conflicting rewrite are covered. The race test uses two real
  targets sharing one real checkout and injects the real force-push between two real
  fetches; the flow test rewrites fix/A in the middle of a real run.

## Alternatives ruled out

- **Attempt 1's design** (up-front fetch, skip the fold's fetch, merge the ref): rejected
  by Check, see above.
- **The sign-off's recipe as written** (re-check after each target's locked fetch, merge
  the ref): see "I did not follow..." above. Rejected on semantics, not cost.
- **Take every target's lock first, then fetch + check + pin under the locks, then
  build.** Strictest (no unlocked fetch, no extra fetch). Rejected on size and blast
  radius: the per-target loop (`integrate.py:422-522`) would split into two passes. From
  a sketch (not built): the lock-to-push body (`:449-521`, about 75 lines) re-indented
  under one fold-wide lock scope, the dry-run branch moved out, plus a first pass of about
  25 lines, so the `fold` diff grows from about 30 changed lines to over 100; and
  `locks=None` callers would hold every target's lock for
  the whole fold instead of per target, contradicting the documented contract ("``None``
  keeps the per-group scope", `integrate.py:355-356`). That is a #297 locking change this
  brief does not ask for.
- **Hold the target's lock just around the up-front fetch** (about 5 lines). Rejected: it
  only serializes against folds of the same target. `publish` (`publish.py:299`),
  `carry_view` (`integrate.py:205-213`) and folds of other bases fetch the same checkout
  without that lock, so overlap stays possible. It would also make a fold wait for the
  lock twice, and a held lock covers another run's whole re-gate (`flow.py:814-826`).

## Residual risks (for the human)

- **The up-front fetch runs outside the integration lock.** It can overlap another
  process's fetch of the same checkout; git may then fail one with a ref-lock error, and
  the fold stops with "could not fetch" (fail-closed; re-issue). On base the same
  exposure already exists (`carry_view` and `publish` fetch unlocked, and the lock is per
  base). This patch adds one such fetch per continue-fold that has carried heads, which is
  every in-run fold after the first. The sign-off's own recipe keeps this fetch too.
- **A rewrite that lands mid-fold is caught one fold later.** The fold merges the
  commit it checked; the newer rewrite is refused at the next fold. On the run's last
  fold (after the second-to-last wave) there is no next fold, so such a rewrite would go
  unnoticed by this run. On base, a rewrite landing a moment after the fold's fetch is
  missed the same way; this only moves the cut-off a few seconds earlier.
- **"Let the run stop and re-issue it"** is the brief's wording. If the branch is not
  restored, the re-issued run's pre-wave carry judges the old line. `foreign_commit` may
  accept A's old commit (B's branch, cut from the line, still holds it), and the carry
  then merges the rewritten A onto it. The brief puts that carry behaviour out of scope
  (#646 judgment, #653). Restoring the branch is the clean way out, and the message says
  so first.
- **Behaviour change, accepted in the brief.** A contributor's "Update with rebase" or
  force-push on a carried PR branch now stops the run. Only fast-forwards, including
  GitHub's merge-style "Update branch", are carried.

## Commit-readiness

The target has no formatter or pre-commit config (no `.pre-commit-config.yaml`; no
ruff/black/flake8 settings in `template/pyproject.toml.jinja`). CI checks docs only
(`.github/workflows/docs-check.yml:33,36`); both pass (T2 above). `git diff --check` is
clean. No added line is over 99 characters (the longest existing code lines in these
files run to 99-106).

## Conflicts to expect

Hunks: `integrate.py` module docstring, `IntegrationError` docstring, `fold`'s signature,
docstring, pre-loop and merge loop and post-push lines, the new `_carried_tips`,
`_merge_published`'s signature, docstring and first lines; `flow.py` `_fold_lines` and two
lines in `_drive_and_act`; the docs sentence; the end of `StackFoldGit`. 629 and 653
(flow.py) touch `_runnable`, the announcement before the in-run fold, and
`_carry_finished`; none of those lines are touched here.

## Housekeeping

- I wrote one scratch file outside the allowed roots by mistake:
  `/tmp/pdca633-check.diff`, a copy of `git diff` made while checking that the worktree
  matched `patch.diff`. It is harmless and I did not delete it (cleanup belongs to the
  harness).
- The C4 log of my first gate run is an untracked `.c4-run.log` at the worktree root. It
  is not in `patch.diff` and no gate reads it.
- Nothing was pushed, and no PR was opened.
