# Build notes — issue 395, iteration 2 (same-wave conflict caught before publish)

Target: `eduralph/pdca-harness @ main`, base `a6af7f3` (= `origin/main` when built).
Line numbers are in the patched tree (base + `patch.diff`) unless marked "base".
Partial fix: the PR should say `refs #395`, not `closes` (see "For the human" below).

I started from the iteration-1 patch (`iteration-v1/patch.diff`), which the reviewers
judged sound on its main path, and reworked the parts the carry-forward rejected. The
rejected approach was the fail-open trial; it is gone.

## What the carry-forward asked for, and what changed

**1. C5 — a trial that errors must not open the conflicting pair (was: fail-open).**
Iteration 1 caught `IntegrationError`, printed a line and published the whole wave
(iteration-1 `flow.py:1673`). One injected fetch failure therefore pushed both branches.
Now:

- Retry. `integrate.same_wave_holds` tries each target up to `_TRIAL_ATTEMPTS = 2` times
  under one lock, pausing `_FETCH_RETRY_PAUSE` between tries
  (`template/src/pdca_harness/integrate.py:757`, loop at `:812-822`). A fetch that fails
  once — the reviewer's exact injection — is absorbed and the hold still happens.
- Fail closed. If the lock cannot be taken, or both tries fail at a git step, that target
  gets no holds. Every ready bundle of it except the first goes into `untried` with the
  first's name and what failed (`integrate.py:823-827`). The first can never be held by
  the #674 rule (it has no earlier sibling), so publishing it alone cannot make a
  conflicting pair.
- Bookkeeping. The flow puts `untried` into `held_unpushed` before any push
  (`template/src/pdca_harness/flow.py:3152`), names each one on one line with the cause
  and the step (`_announce_untried`, `flow.py:1701`), and skips it in the publish loop
  (`flow.py:3155`). Because it is already in `held_unpushed`, the #593 loop does not print
  a second line for it (`flow.py:3193`). Its hold kind is `"unpushed"`, so the exit code
  is 3 as for any hold, and `_runnable` holds its dependents as for any unpushed bundle.
- A failed try's partial holds are dropped: `found` is only set by a try that returns
  (`integrate.py:817-824`).

**2. Adversary — a re-issue after a trial hold gave the "open" hint.** A trial-held
bundle ends COMPLETE with no `publish.json`, so the #646 carry called `_finished_head`,
which says "no PR on record" with the `"open"` hint: "get issue_11's PR open … `pdca
publish 11`, or re-drive issue_11" (base `flow.py:1291-1292`, `:1317`). Following it
opens the PR this change exists to prevent. Now:

- When the trial holds a bundle, the flow records the hold in the bundle:
  `conflict-hold.json` with the partners and the files (`state.CONFLICT_HOLD`,
  `template/src/pdca_harness/state.py:68`; writer `publish.write_conflict_hold`,
  `template/src/pdca_harness/publish.py:707`; written at `flow.py:3148`).
- The carry reads it first (`flow.py:1514-1525`) and names the bundle with its partners,
  the files and the `"conflict"` hint, i.e. `_CONFLICT_STEP` (base `flow.py:1313`):
  "an earlier run held it before publishing it, as its change conflicts with issue_10's,
  of its own wave (shared.txt), so it has no PR — holding issue_20 this run; proposed,
  for you to confirm: declare `Conflicts with: 10` in issue_11's brief, then rebuild
  issue_11 on a base that holds issue_10, then re-issue." The record wins over the
  carry-view failure and the untrusted-line override too (`flow.py:1546-1547`), so the
  "open" hint is never given for such a bundle. Reason text: `_held_before_why`,
  `flow.py:1370`.
- Lifecycle. Publish removes the record once it has pushed the branch, on both publish
  paths (`publish.py:446`, `:563`). An iterate archives it with the attempt
  (`state.py:158`, in `DOWNSTREAM_OF_BRIEF`), so a rebuilt attempt is tried afresh.
- The flow.py docstring at base `:1460-1461` ("never the `open` hint") now covers this
  case explicitly (`flow.py:1469-1473`).

**3. Code review — the error path had no test.** The error path changed (it is fail-closed
now), and both halves are tested: one failure → retried → still held; two failures →
first published, the other held as unpushed. See the test table.

**4. Code review — drop `create=True`.** Done:
`template/tests/test_flow_reissue_after_conflict_hold.py:127-128` patches
`flow._held_before_publish` without it (returning the new `({}, {})` shape). The
docstring (`:114-123`) now says honestly when the mocked state still happens (a branch
changed after the trial, a pair on a run's last wave that a re-issue's carry then
judges, a run from before #395) and points to the new file for the trial-on re-issue.

**Also fixed (minor iteration-1 findings, cheap):**

- Linear trial. Iteration 1 replayed `pre + kept + head` for every bundle (about N²/2
  merges). `_same_wave_trial` now merges each would-be commit once onto the line, as the
  fold does, and calls `_held_by` only on a conflict (`integrate.py:855-866`). It puts the
  line back at `pre` in a `finally` (`integrate.py:869`).
- One rule for the cut point. `_checkout_base` now returns `(checkout_base,
  cut_from_tip)` (`publish.py:797-806`), and `publish()` takes both from it
  (`publish.py:261`), so the two can no longer drift. Same inputs, same values as base
  `publish.py:261-265`.
- Wording. A trial-hold line said the partner was "merged before it", which is false
  before publish (and in case (e) the partner is never pushed). It now says "ahead of it
  in the same wave k" (`flow.py:1665`); fold-time lines are unchanged.

## Unchanged from iteration 1 (judged sound by all three reviews)

- `publish.cut_base` (`publish.py:809`) gives the remote and the ref publish cuts from;
  `_would_be` (`integrate.py:873`) builds publish's commit locally (checkout, apply,
  `add --all`, commit), never pushed, so it has the same parent and tree.
- The trial runs only where the fold runs after: `k < len(wave_list) - 1`, stack mode,
  non-stub publisher (`flow.py:3139-3143`, base `:3078`). Only `ready` bundles are tried
  (criterion d). A hold stands if the partner's push fails (criterion e).
- `held_unpublished` keeps a trial-held bundle out of the #593 "pushed no branch" line
  (`flow.py:2882`, `:3193`) and adds "was not published" to the end-of-run line
  (`flow.py:1715`, `:3253`).
- The lock scope is one `contextlib.ExitStack`, as `_fold_lines` does (base `flow.py:1253`):
  `_held_before_publish`, `flow.py:1682`.
- Docs: the same-wave paragraph of `docs/07-crosscutting.md` (`:719-747`) now also says the
  trial is retried, what happens when it cannot run, and what a re-issue says.

## Alternatives I ruled out (with the cost)

- **Stop the run when the trial cannot run** (about 6 lines: print, `line_stopped`,
  `break`). Every bundle of the wave goes unpublished, including ones that cannot
  conflict, and a re-issue skips them as finished, so the human must `pdca publish` each
  by hand — with no trial at all. Holding only the bundles after the first (about 15
  lines) keeps the guarantee and publishes more.
- **Narrow the fail-closed set by shared files** (`waves.diff_files`, about 6 more
  lines). Not sound: bundles of a later wave are cut from bases of their own (#727) that
  carry other work, so disjoint patches do not prove a clean merge. That could publish a
  conflicting pair, which is the C5 finding.
- **Retry inside `_fetch` (`attempts=2`, #695's mechanism, about 3 lines).** It only covers
  the fetch, not a git step that fails in the tree. The per-try loop (about 12 lines)
  covers both.
- **Re-run the trial in the carry instead of recording the hold** (the adversary's second
  suggestion). The carry does not know which finished ids were in one wave, so it cannot
  apply the #674 rule without a record of the wave anyway, and the old cut point may be
  gone by then (a later run's first fold replaces the line). The record is about 62 lines
  in all (state 9, publish 31, flow about 22) and stores what the trial found.
- **A patch hash in the record to spot a stale one.** The archive list does this in one
  line (`state.py:158`), and publish clears the record on push.

## Existing tests I changed, and why

The change moves when a same-wave hold happens, so three files asserted things that are
no longer true. Same changes as iteration 1, except the re-issue file.

- `template/tests/test_flow_same_wave_conflict.py`: cases that read the held bundle's
  pushed branch now assert it was never pushed (`:232`, `:296`, `:330`) and check the
  line's content instead. The two "base taken in mid-wave" cases now get their conflict
  from a fixup pushed after publish (`:428`), so the fold's own #674 backstop is still
  tested at flow level (no other test covers `held_out` with a base taken in mid-wave).
- `template/tests/test_flow_hold_exit_code.py:215-220`: `_ancestor_of_line` is False when
  origin has no branch of the bundle. The exit codes asserted are unchanged.
- `template/tests/test_flow_reissue_after_conflict_hold.py`: see item 4 above.

## The new test — `template/tests/test_flow_same_wave_prepublish.py`

Drives `flow._drive_and_act` on the real-git `StackFoldGit` fixture (bare `origin`),
fixture and `_edit` reused from `test_flow_same_wave_conflict.py`. Publish is the real
`publish.publish`; only `gh` is stubbed (records calls; `gh pr create` returns a URL,
`gh pr view` reports OPEN with the branch's tip on origin). A push failure is a real
`pre-receive` refusal. A fetch failure is `integrate._fetch` raising, for the first N calls
of a run only. Imports modules only.

| case | what | without the fix | with it |
|---|---|---|---|
| `…is_held_before_it_is_published` (:228) | (a) | FAIL — 11's branch on origin | pass |
| `…in_a_later_wave_is_held_before_it_is_published` (:256) | (a) on wave 1, cut from bases of their own (#727) | FAIL | pass |
| `…shared_file_on_different_lines_publishes_both` (:286) | (b) | pass | pass |
| `…conflict_with_work_on_the_line_still_publishes…` (:300) | (c), held by #747 as on main, rc 3 | pass | pass |
| `…partner_whose_texts_failed_t4_holds_nothing` (:326) | (d) | pass | pass |
| `…hold_stands_when_the_partners_push_fails` (:339) | (e) | FAIL | pass |
| `…in_the_last_wave_publishes_both` (:358), `…in_a_one_wave_run…` (:373) | (f), rc 0 as on main | pass | pass |
| `…trial_whose_fetch_fails_once_tries_again_and_still_holds` (:387) | C5: one failed fetch | FAIL — fold stops, both pushed | pass |
| `…trial_that_cannot_run_publishes_only_the_first_bundle…` (:410) | C5: both tries fail | FAIL | pass |
| `…reissue_after_a_trial_hold_names_the_partner_and_opens_no_pr` (:441) | adversary finding, trial on | FAIL | pass |
| `…trial_hold_published_by_hand_is_judged_by_its_pr` (:462) | record cleared on publish | FAIL (run 1 pushes 11) | pass |

## Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner (`PDCA_BUNDLE=… PDCA_WORKTREE=…
  ./engine/scripts/run-verify.sh` from the instance root) reverted the production hunks
  and re-ran all four touched test files. New file: `Ran 12 … FAILED (failures=7)` —
  the seven FAIL rows above, each on an assertion (`_not_published("11")` / `("21")`:
  the branch exists on origin), no import failure. With the fix all four files pass.
  Final line: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The re-issue
  file errors 24/24 on the red leg (the mock now names a symbol the fix adds, as the
  review asked); the gate counts that as a run, not a load failure.
  I also reverted single pieces of the fix, one at a time, and re-ran the new file
  (scratch script `.pdca-scratch/mutate.py`):
  - carry ignores the record → the re-issue case fails, and its message is exactly the
    adversary's: "no PR with a pushed branch on record (publish.json) — … get issue_11's
    PR open … `pdca publish 11`, or re-drive issue_11";
  - one try instead of two → the one-failure case fails (11 becomes unpushed, not held);
  - untried bundles published anyway (fail-open) → the both-fail case fails;
  - publish does not clear the record → the published-by-hand case fails;
  - the flow writes no record → the re-issue case fails.
- **(b) Production path? Yes.** The trial, its git steps, the record, the carry and the
  hold bookkeeping all run unpatched inside `flow._drive_and_act`. Publish is the real
  `publish.publish`, pushing to a bare repo; the "published by hand" case calls it
  directly. The stubs are the model leaves (build, sign-off, drafting), the `gh` binary,
  and — in two cases — the first one or two `integrate._fetch` calls. Everything is judged
  from origin's refs and the recorded `gh` argv.
- **(c) Fixture includes the fault? Yes.** The pairs really conflict (one line of
  `shared.txt` changed two ways, no `Conflicts with`). The push failure is a real hook
  refusal. The fetch failure is raised where a failed `git fetch` raises, and the cases
  check it was consumed (`fetch_fails == 0`). The re-issue runs the trial on in both runs
  — nothing is mocked out.

## Other evidence

- Full offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover
  -s tests`): `Ran 2641 tests … OK (skipped=2)` before the later-wave case was added;
  then via the project's T3 script (`./engine/scripts/run-suite.sh`): root
  render/update-compat suite `Ran 24 … OK`, driver suite `Ran 2642 … OK (skipped=2)`.
  The base had 2630 driver tests; 12 are new.
- T2 (`./engine/scripts/run-docs-check.sh`) and host-CI parity
  (`engine/scripts/run-host-ci.sh` from the patched tree): docs lint clean, site render +
  link audit clean.
- C5 prod-path (`run-prod-path.py`): "1 added driver-suite test(s) import the production
  package 'pdca_harness'".
- `git apply --cached --check patch.diff` on `a6af7f3`: clean. The worktree diff matches
  `patch.diff` byte for byte.

## Commit-readiness

The target has no formatter, linter or pre-commit config and no git hooks
(`.pre-commit-config.yaml`, ruff/flake8 config, `core.hooksPath`: none). Its rules
(`AGENTS.md`, `CONTRIBUTING.md`) are DCO sign-off and a conventional subject, which
publish handles. `git diff --check` is clean. New lines stay within 96 columns; the
touched files already go up to 106.

## For the human at sign-off

- **Refs vs Closes.** The brief says the PR must say `refs #395`. The target's only
  required check (`.github/workflows/require-linked-issue.yml`) passes only with a
  closing keyword or an issue linked in the PR's Development sidebar. So with `Refs #395`
  the PR needs #395 linked by hand in the sidebar, or the check fails. Also, this
  instance's `[tracker].issue_trailer` is `Fixes #{id}`, which the publisher would write.
  Worth deciding before publish.
- **Criterion (e) holds more than `main` in one case** (deferred finding, your call): if
  the partner's push fails for a reason the trial cannot see (host CI, the line-tip
  refusal, a commit hook — the trial commits with `--no-verify`), B is held for a partner
  that never reaches the line. This is what (e) asks for.
- **Fail-closed holds the rest of the target's wave** when the trial cannot run, even
  bundles that touch other files. In practice that failure means a broken integration
  checkout or no network, where the fold right after would stop the run anyway.
- **A re-issue after a fail-closed hold gives the plain "open" hint** (`pdca publish <id>`):
  no conflict was found, so there is nothing to name. The run-1 line tells you to check
  the change merges with the first bundle's before publishing it.

## Known limits (by design)

- The trial's `pre` is the tip this run last pushed. If an earlier-wave PR branch got a
  fast-forward fixup since that fold, the fold merges it first, so the two can disagree in
  rare cases. The fold's own check stays and has the last word.
- The trial does not apply the fold's #623/#673 "would undo work" refusals; those stop the
  run at the fold as before.
- The last wave is unchanged (out of scope; follow-up issue at publish), and so is
  automatic re-sequencing of a held bundle.
- `Conflicts with: 464`: 464 edits the same publish/fold block (`flow.py:3105-3200`).
  Expect a textual conflict there if both land.

## Scratch

`.pdca-scratch/` in the worktree holds the run logs (C4 twice, full suite, T3), the
mutation script and a temporary index used for the apply check. It is untracked and not
in `patch.diff`.

No external dependency was missing. No NEEDS-HUMAN external-dependency item.
