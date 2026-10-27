# Build notes — issue 395 (same-wave conflict caught before publish)

Target: `eduralph/pdca-harness @ main`, base `a6af7f3` (= `origin/main` when built).
Line numbers below are in the patched tree (base + `patch.diff`) unless marked "base".
Partial fix: the PR should say `refs #395`, not `closes`.

## What changed

**1. One rule for "where publish cuts the branch from" — `publish.py`**

- `publish._checkout_base` (`template/src/pdca_harness/publish.py:767`) holds the
  `checkout_base` rule that was inline at base `publish.py:261-265`: recorded line tip
  when stacked in stack mode, else `origin/<stack_branch>`, else `<base_remote>/<base>`.
- `publish()` now calls it (`publish.py:262`). Same inputs, same result, so publish
  behaviour does not change.
- `publish.cut_base(cfg, d)` (`publish.py:778`) returns `(remote, ref)` for a bundle by
  reading the same files publish reads: `Onto branch` → `<remote>/<branch>` (what
  `_publish_stacked` commits onto); else `_checkout_base`. It returns None where publish
  would refuse (no target; `Stacks on` with no published parent).
- Why extract instead of copying: the trial's would-be commit has to have the same parent
  as the pushed branch. Two copies of the rule would drift apart. Cost: −4/+2 lines in
  `publish()`, +33 lines for the two helpers.

**2. The trial — `integrate.py`**

- `integrate.same_wave_holds` (`template/src/pdca_harness/integrate.py:754`). For each
  target with two or more ready bundles in the wave, in sorted target order (the fold's
  lock order):
  - takes the target's `integ_lock` on the caller's `locks` stack (as `fold` does at base
    `integrate.py:585-594`), then runs `_prepare_worktree` (fetch);
  - starts from where the fold starts: `folded_this_run[target]` (this run's last pushed
    tip) or `<base_remote>/<base>`. It checks out the line branch there (the fold does the
    same `checkout -B`), and that tip is `pre`;
  - builds each bundle's would-be commit with `_would_be` (`integrate.py:828`): detach at
    `cut_base`, `git apply patch.diff`, `add --all`, `commit --no-verify`. These are
    publish's steps without the push, so the commit has the same parent and the same tree
    as the branch publish would push. If any step fails it returns None (publish would
    fail at the same step). It always puts the tree back clean on the line branch, the
    same way `_trial` does;
  - judges the commits in fold order with the fold's own functions: `_trial(pre, kept +
    [head])`. If that merges cleanly, the bundle goes into `kept` (the fold would merge
    it). If it conflicts exactly at `head` with `kept` non-empty, the hold decision is
    `integrate._held_by` — the #674 clash rule, unchanged (base `integrate.py:1785`). Any
    other case (it does not merge onto `pre` alone: a conflict with work already on the
    line) is neither kept nor held. That conflict is #747's, left to the fold, as the brief
    scopes it.
- Why the "keep only what merges onto pre + kept" gate: if a bundle that conflicts with
  `pre` were put in `kept`, every later `_trial(pre, kept + [head])` would stop at that
  bundle, not at `head`. `_held_by` would then return None for every later bundle, and the
  trial would miss real same-wave conflicts. In the fold, such a bundle is either held by
  #747 (and not in `kept`) or the run stops — so leaving it out of `kept` matches the fold.

**3. Flow wiring — `flow.py`**

- `_held_before_publish` (`template/src/pdca_harness/flow.py:1658`) runs the trial under
  one `contextlib.ExitStack` of locks, the same way `_fold_lines` does (base
  `flow.py:1253`). If the trial raises `IntegrationError` (lock, fetch, git step), it
  prints one line and returns `{}`. The wave then publishes exactly as on `main`, and the
  fold judges it. I chose this over stopping the run: the trial is an early answer, and a
  failed trial should never leave things worse than `main`.
- Call site (`flow.py:3095-3116`): it runs after the texts are drafted and T4-gated, and
  before any push. It only covers bundles with `ready[d.name]` True (criterion d). It is
  gated on `k < len(wave_list) - 1`, stack mode and a non-stub publisher — the same
  condition the fold uses (`flow.py:3133`, base `:3078`). So the last wave and one-wave
  runs are unchanged (criterion f).
- Each held bundle is recorded in `held_conflict` (so `_runnable`, the end-of-run report,
  the `holds` collector and the exit code all treat it as a fold-time conflict hold), and
  also in a new `held_unpublished` set (`flow.py:2847`). It is skipped in the publish loop
  (`flow.py:3114`).
- The #593 "pushed no branch" loop skips `held_unpublished` (`flow.py:3151`), so a held,
  unpublished bundle is reported as `"conflict"`, never also as `"unpushed"`.
- The hold stands even if the partner's push then fails (criterion e). Nothing re-reads
  the trial after the publish loop.
- Messages:
  - `_announce_conflict_holds(..., published=False)` (`flow.py:1632`) prints the same
    line the fold prints (so every existing matcher on `"<name> held out of the
    integration fold — "` still works), plus "Found before publishing: no branch pushed,
    no PR opened."
  - `_report_conflict_holds(..., unpublished=...)` (`flow.py:1683`) adds "was not
    published: this run pushed no branch and opened no PR for it" to the end-of-run step
    line.
  - The partner location still says "merged before it in the same wave k". That is the
    fold order the trial applies; I kept the wording identical rather than add a second
    phrasing.

**4. Docs**

`docs/07-crosscutting.md:723-732`: the same-wave paragraph now says the hold is found
before publish on every wave but the last, says only bundles with passing texts are
tried, says the hold stands if the partner's push fails, says the fold still checks, and
says the last wave is unchanged.

## Existing tests I changed, and why

The change moves when a same-wave hold happens, so three existing files asserted things
that are no longer true.

- `template/tests/test_flow_same_wave_conflict.py`
  - Cases 1, 3 and 4 looked up the held bundle's pushed branch (`self._head("11")` → `git
    rev-parse refs/heads/fix/11`). That branch now never exists. They now assert
    `not self.fx._has("fix/11")`, and they check the line's file content so it is still
    shown that the held work is off the line.
  - The two "base taken in mid-wave" cases test the fold's own #674 decision when the base
    is merged in mid-wave. With the trial, the l2 variant would have been held before
    publish, so the fold's code path would no longer be tested at flow level. No other
    test covers `held_out` with a base taken in mid-wave (`grep held_out tests/` → only
    this file). So I changed the fixture to the real backstop case: 22's patch changes
    line 5 (the trial sees no conflict, all three publish), then a fixup pushed onto
    `fix/22` after publish adds the conflicting line (`:430`). The fold's decision and
    every assertion are unchanged. It now also covers the brief's "a branch can change
    between the trial and the fold".
- `template/tests/test_flow_reissue_after_conflict_hold.py` (#694): every case needs run 1
  to leave 11 COMPLETE **with its PR open**, then judges the run-2 carry. That state still
  happens (a fold backstop hold, or a run from before #395), but the trial no longer
  produces it from a plain same-wave pair. `_run` patches `flow._held_before_publish` to
  return `{}` (`:123`, `create=True` so the file behaves the same with the fix reverted).
  The docstring says why. Nothing the file asserts about run 2 changed.
- `template/tests/test_flow_hold_exit_code.py`: `_ancestor_of_line` now returns False when
  origin has no branch of the bundle (`:218`). The exit codes asserted (3, 1, 0) are
  unchanged.

## The new test — `template/tests/test_flow_same_wave_prepublish.py`

It drives `flow._drive_and_act` on the real-git `StackFoldGit` fixture (bare `origin`,
primary checkout). Fixture loading and `_edit` are reused from
`test_flow_same_wave_conflict.py`, loaded by path as the #694 suite does. Build, sign-off
and drafting the texts are stubbed. **Publish is not stubbed**: the production
`publish.publish` cuts, commits and pushes to the bare origin. Only `gh` is stubbed (it
records calls and answers `gh pr create` with a URL). It imports modules only.

| case | criterion | on `main` | with fix |
|---|---|---|---|
| `test_a_same_wave_conflict_is_held_before_it_is_published` (:161) | (a) | **FAIL** — `fix/11-11` is on origin | pass |
| `test_a_shared_file_on_different_lines_publishes_both` (:191) | (b) | pass | pass |
| `test_a_conflict_with_work_on_the_line_still_publishes_and_the_fold_holds_it` (:205) | (c) | pass (confirms `main` holds it via #747, kind `conflict`, rc 3) | pass |
| `test_a_partner_whose_texts_failed_t4_holds_nothing` (:231) | (d) | pass | pass |
| `test_a_hold_stands_when_the_partners_push_fails` (:244) | (e) | **FAIL** — `fix/11-11` is on origin | pass |
| `test_a_same_wave_conflict_in_the_last_wave_publishes_both` (:263) | (f) | pass (rc 0) | pass |
| `test_a_same_wave_conflict_in_a_one_wave_run_publishes_both` (:278) | (f) | pass (rc 0) | pass |

(b), (c), (d) and (f) are no-regression legs. They pass on both sides on purpose, and (c)
and (f) pin "same as `main`" to the value `main` actually gives.

## Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner
  (`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`, run from the instance
  root) reverted the production hunks and re-ran all four touched test files.
  `test_flow_same_wave_prepublish`: `Ran 7 … FAILED (failures=2)`. The two failures are
  (a) at :167 and (e) at :251, both `_not_published("11")`: `fix/11-11` exists on origin
  without the fix. No import failure. With the fix, all four files pass. Final line:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. I also did one manual
  revert of `template/src` and got the same two failures.
- **(b) Production path? Yes.** The trial, its git steps and the hold bookkeeping run
  unpatched inside `flow._drive_and_act`. Publish is the real `publish.publish` →
  `git push` to a bare repo, and `gh pr create` is recorded from the real argv. The only
  stubs are the model leaves (build/sign-off/drafting) and the `gh` binary, the same
  boundary the existing #674 suite uses. Pushes are judged from origin's refs, not from a
  mock.
- **(c) Fixture includes the fault? Yes.** (a) has a real textual conflict: the same line
  of `shared.txt` changed two ways, with no `Conflicts with`. (e) has a real push failure:
  a `pre-receive` hook on the bare origin refuses `refs/heads/fix/10-10`, and publish
  reports `step failed: git … push`. Nothing is curated out. The conflicting bundle is in
  the wave and is offered to publish.

## Other evidence

- Full offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover
  -s tests`): `Ran 2637 tests … OK (skipped=2)`. The baseline before the change was 2630
  OK, plus the 7 new cases.
- Root render/update-compat suite (instance venv with copier): `Ran 24 tests … OK`.
- `docs/publishing/tools/lint_docs.py`: OK. `render_site.py --check`: link audit OK.
- `git apply --cached --check patch.diff` on `a6af7f3`: clean. The worktree diff matches
  `patch.diff` byte for byte after the C4 run.
- Commit-readiness: the target has no formatter or pre-commit config. CONTRIBUTING asks
  for DCO `-s`, which publish adds. The new lines stay within 96 columns, as the files
  around them do.

## Known limits (not fixed here, by design)

- The trial's `pre` is the tip this run last pushed. If an earlier-wave PR branch got a
  fast-forward fixup since that fold, the fold merges the fixup first and its `pre`
  differs. The trial could then disagree with the fold in rare cases. The fold's own
  check stays and is the last word on what lands on the line.
- The trial does not apply the fold's #623/#673 "would undo work" refusals. Those are
  not same-wave conflicts. The fold still stops on them as before.
- Cost: one extra fetch per target per non-final wave that has two or more ready bundles,
  plus a few local commits and trial merges. The trial commits are unreferenced objects
  in the checkout, as `_trial(made=)` already leaves today, and git gc removes them.
- Out of scope per the brief, to file at publish: the last wave (a hold there would
  change today's exit code); automatic re-sequencing of a held bundle into a later wave;
  the Plan-exit file-set advisory.
- `Conflicts with: 464`: 464 edits the same publish/fold block (`flow.py:3095-3200`).
  Expect a textual conflict there if both land.

## Scratch

`.pdca-scratch/` in the worktree holds test-run logs (baseline, after, verify). It is
untracked and not in `patch.diff`.

No external dependency was missing. No NEEDS-HUMAN item.
