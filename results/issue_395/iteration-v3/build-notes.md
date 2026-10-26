# Build notes — issue 395, iteration 3 (same-wave conflict caught before publish)

Target: `eduralph/pdca-harness @ main`, base `a6af7f3` (= `origin/main` when built).
Line numbers are in the patched tree (base + `patch.diff`) unless marked "base".
Partial fix: the PR should say `refs #395`, not `closes` (see "For the human" below).

I started from the iteration-2 patch (`iteration-v2/patch.diff`), whose main path the
reviewers found sound, and changed the two parts the round-2 carry-forward rejected. The
rejected behaviour (a would-be commit that fails to build silently drops out of the trial;
a hold record that outlives its partner) is gone. Everything else from iteration 2 is kept.

## 1. C5 — a would-be commit that fails to build no longer drops out of the trial

**The defect.** Iteration 2's `_would_be` returned `None` on any failed step, and the
trial filtered those bundles out (iteration-2 `integrate.py:850`, `:890`). The rest were
tried without them, and the dropped bundle was then published untried. One failed
`git add --all` in the integration checkout was enough to push both branches of a
conflicting pair (review-trial-stage-failure.log). The assumption behind it ("publish fails
at the same step") is false: publish runs later, in the primary checkout.

**The fix.**

- `_would_be` (`template/src/pdca_harness/integrate.py:901`) now raises `_Unbuilt`
  (`integrate.py:128`, an `IntegrationError`) naming the step that failed: check out the
  cut point, apply the patch, `git add --all`, `git commit`, or read the new commit
  (`integrate.py:916-932`). It never returns `None`.
- `_same_wave_trial` (`integrate.py:847`) records each such bundle in `unbuilt` (name →
  what failed) and does not merge it (`integrate.py:871-876`). If no bundle's commit could
  be built at all, the try raises, as any other failed git step does (`integrate.py:877`).
  It returns `(held, unbuilt)`.
- `same_wave_holds` (`integrate.py:766`) tries again when a try left any bundle unbuilt
  (`integrate.py:835`), just as it already did for a try that raised. So a one-off failure
  (the reviewer's exact injection) is absorbed, and the hold happens as normal.
- After the last try, a bundle still unbuilt is put in `untried` and is **not published**.
  The others are tried without it (`integrate.py:842-844`). This is sound: an unpublished
  bundle cannot be one of two conflicting PRs, and the fold later skips it as unpushed
  (`integrate.unpublished`), so the fold's own check runs over the same set the trial did.
- `untried` values are now `(the bundles it could not be tried against, what failed)` —
  `[first]` for the whole-target case as before, the bundles published beside it for the
  per-bundle case. The flow line names them (`_announce_untried`,
  `template/src/pdca_harness/flow.py:1723`). Bookkeeping is unchanged: `held_unpushed`,
  hold kind `"unpushed"`, exit code 3.

**Alternatives I ruled out, with the cost.**

- *Make an unbuilt bundle fail the whole target closed (publish only the first).* About 6
  changed lines instead of about 25: `_would_be` raises a plain `IntegrationError` and the
  filter goes. Behaviour cost: one bundle whose patch does not apply at its cut point (an
  `Onto branch` PR branch that moved, a `Stacks on` prerequisite's branch that moved)
  would withhold every other ready bundle of its target except the first. On `main` only
  that bundle fails to publish. The mutation run below shows the per-bundle case catches
  this choice (`unbuilt-fails-whole-target` → 1 failure). It would not have saved the
  fixture changes in §3 either: those fixtures would fail closed the same way.
- *Exclude a bundle whose `git apply` fails (publish fails the same way), withhold only
  other failures.* About 10 lines. It keeps a silent drop for one step: an injected
  `git apply` failure in the integration checkout — the same method the reviewer used for
  `git add` — would still push both conflicting branches. That is the hole the finding
  names, so I did not keep it.

## 2. Adversary — a hold record no longer outlives its partners

**The defect.** Iteration 2's carry let `conflict-hold.json` win over every other verdict.
After the partner's PR was closed without merging, a re-issue still told the human to
rebuild the held bundle on a base that holds the partner — which no base will — and never
said `pdca publish <id>`.

**The fix.** `_held_before` (`flow.py:1380`) judges the record each time the carry reads
it (`flow.py:1539`):

- While **some** partner may still land, the hold stands, with the conflict step, as in
  iteration 2. "May still land" is anything but a PR that reads CLOSED: an open or merged
  PR, no PR yet (its push failed), or a PR whose state cannot be read.
- Once **every** partner's PR reads CLOSED (`_pr_closed`, `flow.py:1370`, via
  `merged.pr_state`), the bundle gets the `"open"` hint, and the reason says why: "…, but
  that PR is closed unmerged now, so that hold no longer stands; it has no PR". The `open`
  hint names `pdca publish <id>`.
- Either way the bundle is never carried and its old `publish.json` is never consulted: the
  record proves its current attempt pushed nothing (publish clears the record on push,
  `publish.py:446`, `:563`; an iterate archives it, `state.py:158`). This avoids judging the
  bundle by an older attempt's PR, which `publish.json` can still name after an iterate.

**Why "every partner closed" and not the adversary's "no partner is a clean finished id".**
In criterion (e) the partner's push failed, so on a re-issue it has no PR and is not
clean. With the "clean" rule the held bundle would get "`pdca publish 11`" right beside
the partner's own "`pdca publish 10`" — following both opens exactly the two conflicting
PRs this change exists to prevent. Criterion (e) says the partner "will be re-published".
So only a closed PR releases the hold. Both readings are pinned by tests (below), and the
mutation run shows each rule change is caught.

## 3. Existing tests I changed this round, and why

The C5 fix exposed fixtures whose stub publisher and the trial disagreed about what
publish would push. With iteration 2's silent drop they passed for the wrong reason.

- `template/tests/test_flow_same_wave_conflict.py:155-165`: the case that moves 21's cut
  point (`cut_from["21"] = "origin/main"`) now moves it for the trial too, by patching
  `publish.cut_base` for that id. Real publish and the trial share one rule
  (`publish._checkout_base`, `publish.py:797`); the stub publisher's override must reach
  both. Without it, 21's patch (written against `origin/main`) does not apply at the
  recorded tip, so the trial now (correctly) withholds 21 and the case's fold-time #747
  hold never happens.
- `template/tests/test_flow_cross_wave_fold_holds.py` and
  `template/tests/test_flow_cross_wave_joint_holds.py`: their build stub wrote a
  placeholder `patch.diff` (a "new file" patch per changed file, `sb._new_file_patch`) that
  does not apply to files already on the base; only the stub publisher wrote the real diff.
  The build stub now writes the real diff, made where publish cuts the branch (`_change`,
  `_cut`: fold-holds `:117`, `:177`; joint-holds `:119`, `:173`), and the fold-holds file
  gets the same `cut_base` hook for its three `cut_from` cases (`:209`). These 15 #747/#748
  cases now run with the trial **on** and pass unchanged: the trial holds nothing in them
  and the fold decides, as on `main`. That is extra evidence for criterion (c).
- `template/tests/test_flow_slice.py:1370-1372`: `_live` already replaced the fold and the
  bundle-base merge; it now replaces the trial too. With no real checkout, the trial
  failed closed and withheld HU *before* its faked publish failure, so
  `test_an_unpublished_bundle_holds_only_its_dependents` was exercising the trial instead
  of the #593 publish-failure path it describes (this was already true in iteration 2; I
  found it by logging every trial hold over the full suite). The case now also asserts
  HU's publish ran (`:1433`).

Each of these hooks is guarded by `hasattr` so the C4 red leg (production reverted, where
the symbol does not exist) runs these files exactly as `main` does. A rename does not hide
behind the guard: I renamed `cut_base` and `same_wave_holds` in a scratch copy, and every
case that relies on a hook failed (4 `cut_from` cases; the HU case with
`'HU' not found in ['HI', 'HJ']`). `test_flow_reissue_after_conflict_hold.py` keeps
iteration 2's unguarded mock, as round 1's review asked; its 24 red-leg errors are the
`AttributeError` the adversary already judged harmless.

## 4. Docs

`docs/07-crosscutting.md:719-745`: the same-wave paragraph now says the run tries once
more when something fails, that a bundle whose commit still cannot be built is held alone
and the rest tried without it, and that a re-issue asks for the held bundle's PR once each
of its partners' PRs is closed. I also replaced "so the wave never opens two PRs that
conflict with each other" with a true sentence: "A bundle whose change also conflicts with
work already on the line is still published; the fold judges it" (`:728-730`; the comment
at `flow.py:3155` says "so the wave opens no PR that rule would hold"). The deferred scope
question (widen the trial to the fold's `_held_by_line`, or not) is still yours; I only
made the text match what the code does.

## 5. The new test — `template/tests/test_flow_same_wave_prepublish.py`

Real git (`StackFoldGit`, bare `origin`), real `publish.publish`, `gh` stubbed, driven
through `flow._drive_and_act`. A fetch failure is `integrate._fetch` raising; a git step
failing in the integration checkout is `integrate._git` returning 1 for the calls a case
picks (`:132`) — publish's own git steps never go through it. A closed PR is the `gh`
stub answering CLOSED (`:89`). Modules-only imports.

| case (line) | what | on `main` | iteration 2 | now |
|---|---|---|---|---|
| `…is_held_before_it_is_published` (:252) | (a) | FAIL — 11 pushed | pass | pass |
| `…in_a_later_wave_is_held…` (:280) | (a), bases of their own | FAIL | pass | pass |
| `…shared_file_on_different_lines…` (:310) | (b) | pass | pass | pass |
| `…conflict_with_work_on_the_line…` (:324) | (c), rc 3 as on main | pass | pass | pass |
| `…partner_whose_texts_failed_t4…` (:350) | (d) | pass | pass | pass |
| `…hold_stands_when_the_partners_push_fails` (:363) | (e) | FAIL | pass | pass |
| `…in_the_last_wave…` (:382), `…one_wave_run…` (:397) | (f), rc 0 as on main | pass | pass | pass |
| `…fetch_fails_once…` (:411) | retry | FAIL | pass | pass |
| `…cannot_run_publishes_only_the_first…` (:434) | whole-target fail-closed | FAIL | FAIL (wording only) | pass |
| **`…staging_fails_once_is_built_again…` (:463)** | **C5: `git add` fails once** | FAIL — 11 pushed | **FAIL — 11 pushed** | pass |
| **`…cannot_be_built_is_not_published_beside_the_rest` (:488)** | **C5: 11's commit fails twice** | FAIL — 11 pushed | **FAIL — 11 pushed** | pass |
| `…reissue_after_a_trial_hold_names_the_partner…` (:522) | re-issue, partner open | FAIL | pass | pass |
| `…published_by_hand_is_judged_by_its_pr` (:543) | record cleared on push | FAIL | pass | pass |
| **`…reissue_once_the_partners_pr_closed…` (:560)** | **stale record** | FAIL | **FAIL — conflict step** | pass |
| **`…keeps_the_hold_while_one_of_its_partners_may_land` (:582)** | two partners, one closed | FAIL | pass | pass |
| **`…while_the_partner_has_no_pr_keeps_the_hold` (:612)** | partner unpushed (e) | FAIL | pass | pass |

Bold rows are new this round. The last two pass on iteration 2 (it never released a hold);
they pin which holds must stand, and each catches a rule change (mutations below).

## 6. Refuting my own test (forced)

- **(a) Genuine red? Yes.** The project's C4 runner
  (`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` from the instance root)
  reverted the production hunks and re-ran all seven touched test files: the new file
  `Ran 17 … FAILED (failures=12)`, all on assertions (mostly `_not_published("11")`:
  11's branch is on origin), no `_FailedTest` load failure; `test_flow_same_wave_conflict`
  3 failures; the re-issue file 24 `AttributeError`s (see §3); the other four files pass
  on the reverted tree, as on `main`. With the fix, all seven pass. Final line:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  Against the **iteration-2** production code (built in `.pdca-scratch/v2root` from a
  temporary git index), the two C5 cases fail with 11's branch on origin, and the
  stale-record case fails because 11 still gets the conflict step — the carry-forward
  findings, reproduced. Single-piece mutations (`.pdca-scratch/mutate.py`), each caught
  by at least one case: no retry for an unbuilt bundle (2 failures); an unbuilt bundle
  failing the whole target closed (1); a missing PR counted as closed (1); "any" partner
  closed instead of "every" (1 — the case at :582 was added after this mutation first
  survived); an unbuilt bundle published anyway (1).
- **(b) Production path? Yes.** The trial, `_would_be`, the retry, the untried and hold
  bookkeeping, the record and the carry's `_held_before` all run unpatched inside
  `flow._drive_and_act`. Publish is the real `publish.publish` pushing to a bare repo. The
  stubs are the build/sign-off leaves, drafting, the `gh` binary, and in some cases the
  first calls of `integrate._fetch` / selected `integrate._git` calls (the fault being
  injected). Outcomes are read from origin's refs and the recorded `gh` argv.
- **(c) Fixture includes the fault? Yes.** The pairs really conflict (one line of
  `shared.txt` changed two ways; for the two-partner case, two lines). The staging fault
  is a real failing `git add --all` in the integration checkout, and the cases check it
  fired (`git_failed`). The closed partner is the `gh` state publish and the carry read in
  production. The unpushed partner is a real `pre-receive` refusal.

## 7. Other evidence (final tree, `patch.diff` sha256 `ba3070d9…9d97`)

- T3 (`./engine/scripts/run-suite.sh`): root render/update-compat suite `Ran 24 … OK`;
  driver suite `Ran 2647 … OK (skipped=2)` (base 2630, plus 17 new).
- T2 (`./engine/scripts/run-docs-check.sh`) and host-CI parity
  (`engine/scripts/run-host-ci.sh` from the patched tree): docs lint clean, site render +
  link audit clean.
- C5 prod-path (`run-prod-path.py`): "1 added driver-suite test(s) import the production
  package 'pdca_harness'".
- `git apply --cached --check patch.diff` on `a6af7f3` (temporary index): clean. The
  worktree diff equals `patch.diff` byte for byte after the C4 run. `git diff --check`:
  clean.
- Over one full-suite run I logged every non-empty trial hold or untried set (a temporary
  edit, removed): all hits were in the cases meant to hit them, plus the `test_flow_slice`
  HU case fixed in §3.

## 8. Commit-readiness

The target has no formatter, linter, pre-commit config or active git hooks
(`.pre-commit-config.yaml`, ruff/flake8 config, `core.hooksPath`, `.git/hooks`: none).
Its rules (`AGENTS.md`, `CONTRIBUTING.md`) are DCO sign-off and a conventional subject,
which publish handles. Added lines stay within 96 columns (the touched files already go
up to 106).

## 9. For the human at sign-off

- **Refs vs Closes** (unchanged from iteration 2). The brief wants `refs #395`. The
  target's required check (`.github/workflows/require-linked-issue.yml`) passes only with
  a closing keyword or an issue linked in the PR's Development sidebar, and this
  instance's `[tracker].issue_trailer` is `Fixes #{id}`. Decide before publish.
- **New policy you may want to weigh:** a bundle whose would-be commit cannot be built
  (twice) is held alone, as unpushed, and its siblings publish. Where its patch genuinely
  does not apply at its cut point, this ends as on `main` (publish would fail there too),
  only named earlier. The whole-target fail-closed policy (deferred T5 item) is unchanged.
- **The stale-record rule** releases a hold only when every partner's PR reads CLOSED. A
  partner whose bundle was deleted, or whose PR state `gh` cannot read, keeps the hold.
- **Still deferred to you** (not build work): the mixed case where a bundle conflicts
  with a sibling and with the line (the trial leaves it to the fold, so both PRs open —
  the docs now say so, §4); the blast radius of the whole-target fail-closed; criterion
  (e) holding more than `main` when the partner's push fails for a reason the trial
  cannot see; the last wave.
- A re-issue after a fail-closed or unbuilt hold gives the plain `open` hint
  (`pdca publish <id>`): no conflict was found, so there is nothing to name. The run-1 line
  tells you to check the change merges with the named bundles before publishing it.

## 10. Known limits (by design)

- The trial's start is the tip this run last pushed; the fold's own check stays and has
  the last word for a branch that changed after the trial.
- The trial does not apply the fold's #623/#673 "would undo work" refusals or #747/#748
  line holds; those stay at the fold.
- `_would_be` still repeats publish's apply → add → commit steps (round-2 code-review
  note). Drift between them now fails closed (the bundle is withheld), not open.
- `Conflicts with: 464`: 464 edits the same publish/fold block (`flow.py:3130-3267`).
  Expect a textual conflict there if both land.

## Scratch

`.pdca-scratch/` in the worktree holds the run logs (C4, T3, suite runs), the mutation
script, the iteration-2 and `main` production copies used for the red comparisons, and
the temporary git indexes. It is untracked and not in `patch.diff`.

No external dependency was missing. No NEEDS-HUMAN external-dependency item.
