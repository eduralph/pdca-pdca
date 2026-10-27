# Build notes — issue 395 / same-wave-conflict-refused-at-accept

Target: `eduralph/pdca-harness @ main`, worktree base `a6af7f3` (the brief's origin/main).
Line numbers below are in the patched worktree (`$PDCA_WORKTREE`) unless marked "main",
which means the unpatched base `a6af7f3`.

Inputs read: `brief.md`; the one optional input it names, `iteration-v5/patch.diff`, for the
trial mechanics only; and the target code the brief cites. The stray
`test_flow_same_wave_prepublish.py` in the bundle was not opened and is not in the patch.

## What changed

1. **Accept-time refusal** — `template/src/pdca_harness/flow.py`
   - `_AcceptTrial` (flow.py:137): the wave's bundles, its index `k`, the run's
     `folded_tips`, and the batch that names the line.
   - `_apply_decision(..., trial=None)` (flow.py:150). After the C6 check (main
     flow.py:177-179, now flow.py:200-202), and before `signoff.record`, an accept is
     refused when `_refused_for_wave` says so (flow.py:206). It returns `"blocked"`, the
     same outcome C6 returns, so both callers already handle it. The decision file stays
     on disk, as for a C6 refusal. Once any decision is recorded, the refusal record is
     removed (flow.py:223).
   - `_refused_for_wave` (flow.py:271). The accepted siblings are the bundles of
     `trial.wave` that are COMPLETE right now. It calls `integrate.same_wave_clash`
     (flow.py:300). If the check raises (`IntegrationError` / `OSError` / `ValueError`),
     it falls back to `integrate.same_wave_overlap` (flow.py:305). On a clash it adds the
     §6 row with `signoff.ensure_needs_human_item` (flow.py:319), the same call
     `accept_blockers` uses (main flow.py:235-237), then reads C6 again. If the row is
     open, it refuses, writes the record (flow.py:322) and prints the line. If the row was
     already there and ticked, that is the human's override and the accept goes on.
   - Both accept routes in `_drive_wave` pass `trial`: the pre-apply (flow.py:2729, via
     `_apply_recorded_decision` flow.py:435/472) and the post-session apply (flow.py:2743).
   - `_drive_and_act` builds the trial only when the fold after the wave will hold
     same-wave conflicts. The condition is the fold's own: `k < len(wave_list) - 1 and
     do_publish` (flow.py:3307), stack mode, and not a dry run (`held_out=None if dry`,
     flow.py:3344). See flow.py:3246-3251.
2. **The trial** — `template/src/pdca_harness/integrate.py`
   - `same_wave_clash` (integrate.py:755) uses the fold's #674 rule, not a new one. Each
     bundle's would-be commit (`_would_be`, integrate.py:876) is its `patch.diff`
     committed on the ref publish cuts from (`publish.cut_base`). The commits are merged
     in name order onto the line as the wave found it (`folded_tips[target]`, else
     `<base_remote>/<base>`), and a merge that conflicts is judged by the fold's own
     `_held_by` (main integrate.py:1785) over `_trial` (main integrate.py:2095); see
     `_wave_holds`, integrate.py:913. It runs in the target's integration worktree under
     `integ_lock`, entered on a `contextlib.ExitStack` the way `fold` /
     `flow._fold_lines` (main flow.py:1253) enter it. Building and judging both sit inside
     one `try/finally` that puts the tree back on the line branch at the start commit,
     clean, on every exit, raising ones included (`_back_on`, integrate.py:940).
     `_would_be` also restores the branch in its own `finally`.
   - "A conflict" (the brief's stated choice): the accepted siblings plus the candidate,
     folded in name order, make the fold hold more bundles than the siblings alone
     (`len(held) <= len(alone)` → no clash). The row's partners are each newly held
     bundle's partners when that bundle is the candidate, else the newly held sibling
     itself. That is how leg (c) names issue_11 on issue_10's row.
   - `same_wave_overlap` (integrate.py:846), the fallback for when the trial cannot run:
     siblings on the same target whose `patch.diff` touches a path the candidate's does
     (`waves.diff_files`). It also counts the directory/file case (one patch adds `x`, the
     other `x/y`), because git conflicts there too.
3. **One rule for where publish cuts** — `template/src/pdca_harness/publish.py`. Main
   publish.py:261-265 became `_checkout_base` (publish.py:767), and publish calls it
   (publish.py:262). `cut_base` (publish.py:779) returns `(remote publish fetches, ref)`
   for any bundle, including an `Onto branch`. Publish's behaviour does not change: same
   expression, same inputs.
4. **The bound on re-offers** (leg h) — record `state.SAME_WAVE_REFUSAL =
   "same-wave-refusal.json"` (state.py:69), added to `DOWNSTREAM_OF_BRIEF` (state.py:158).
   - Written at a trial refusal, with `sessions: 0`. `_session_offered` (flow.py:382)
     adds one to the count just before a session covering the bundle (flow.py:2734).
   - `_parked` (flow.py:390): the record exists, `sessions >= 1`, the bundle is still
     AWAITING_SIGNOFF, and the record's row is still open. Parked bundles leave `pending`
     (flow.py:2695) and count as settled for the wave's end check (flow.py:2744).
     `_report_parked` (flow.py:409) prints the wave-end line naming the partner, the
     files and the step, without the pass-budget hint. `_warn_abandoned` leaves them out
     on both of its exits.
   - `_drive_wave` drops every wave bundle's record when it starts (flow.py:2675). The
     count therefore belongs to the current wave, and a later run offers the bundle a
     session again. Without that drop, a re-run would park the bundle with no session at
     all; the mutation check below shows it.
   - A plain C6 refusal writes no record, so it is offered a session every pass, as
     today.
5. **Docs** — `docs/07-crosscutting.md`. The same-wave paragraphs (docs:719-764) cover
   the accept-time refusal, first-accepted-wins, the one-more-session bound, the
   fallback, the row living only in SUMMARY §6, the override, the fold as last check
   (override / branch changed / the #747 line-plus-sibling case, still published), and
   the last-wave / one-wave exemption. The exit-code paragraph (docs:766-780) says a
   refused bundle is unfinished: exit 1 (in a run of one id it counts as stopped for
   sign-off, cli.py:798 on main).

## The v5 mechanics: what I reused and what I fixed

I reused `_would_be`'s step list (checkout --detach / apply / add --all / commit
--no-verify) and its restore-in-`finally`, plus the `cut_base` / `_checkout_base`
extraction. The two open findings:

- **The retry that threw away a good first result.** No retry at all now. The fold
  fetches under the same lock with no retry (`fold` → `_prepare_worktree`, main
  integrate.py:594 → `_fetch` attempts=1). A failed trial goes to the fallback, which
  refuses only where a conflict is possible. Cost avoided: v5's `_Unbuilt`
  (v5 patch.diff:544-547), `_TRIAL_ATTEMPTS` (:556-560), the retry loop and `untried`
  bookkeeping in `same_wave_holds` (:620-642) and `_announce_untried` (:277-295) — about
  50 lines, and the bug class that came with them.
- **The build loop outside the `try/finally` reset.** The would-be commits are built
  inside the `try` whose `finally` is `_back_on` (integrate.py:827-833).

Not carried over: `conflict-hold.json`, `held_conflict` entries for unpublished bundles,
and every re-run hint / `_terminal_hint` / `_carry_finished` change.

## Alternatives ruled out

- **"The candidate itself is held" instead of the count rule.** It refuses nothing when
  the candidate sorts first: in leg (c), issue_10 would be accepted and the fold would
  later hold issue_11. A mutation check confirmed leg (c) fails under that rule and only
  (c).
- **Skip the trial unless a path is shared.** This would save about 2 fetches, N commit
  builds and up to 2N merges per accept, but it is a second rule, it misses
  directory/file conflicts, and the brief says not to invent one. It is used only as the
  fallback.
- **Mark "offered once" in memory, or in the decision file.** Ruled out by the brief: no
  hidden state, and the decision file stays as for C6.
- **Put the row into a Check artifact so `assemble.collect_needs_human` sees it.** Ruled
  out by (f): it would get an IMPL/HUMAN kind and reach auto-iterate.
- **Hold every sibling but the first when the trial cannot run** (v5). Replaced by the
  shared-path rule the brief specifies.

## Test → success criterion

`template/tests/test_flow_same_wave_accept_trial.py`. It imports only modules, loads
`test_flow_same_wave_conflict.py` by path (and through it the `StackFoldGit` fixture of
`test_integrate_stack_bases.py`), and borrows `_on_base` / `_plan` / `_patch` / `_gh_stub` /
`setUp` / `_publish_bundle` from it method by method, as
`test_flow_reissue_after_conflict_hold.py` does. Stubs: `flow._build_all` (writes
`patch.diff`, a clean gate record and review, and the SUMMARY through the real
`assemble.assemble_summary`), `leaves.run_signoff_batch`, `flow._publish_bundle` (the peer
stub, plus the `gh pr create` publish runs after the push), `publish.draft_texts`, and
`gh`. Not stubbed: `flow._drive_wave`. The test never calls `signoff.record(... "accept")`.
Wave 0 is 10/11/12 and wave 1 is 20 (depends on 12), so a fold follows wave 0 in every leg
but (g).

| Leg | Test (line) |
|---|---|
| (a) | `test_a_conflicting_accept_is_refused_and_its_sibling_published` (233); also checks the integration tree is clean on the line when 11's session opens |
| (b) | `test_a_shared_file_that_merges_cleanly_is_accepted` (255) |
| (c) | `test_the_refusal_does_not_depend_on_which_accept_comes_first` (271) |
| (d) | `test_ticking_the_row_accepts_it_and_the_fold_holds_it` (291) |
| (e) | `test_a_trial_that_cannot_run_refuses_only_a_bundle_sharing_a_file` (306): `git apply` of the would-be commit build fails through `integrate._git`; 11 changes line 8 here, so only the shared path refuses it; also checks the tree after the raising trial |
| (f) | `test_a_reassembled_summary_drops_the_row_and_the_next_accept_refuses_again` (333): the session ticks, reassembles with `assemble.assemble_summary`, writes accept; row back, unticked; not in `collect_needs_human` |
| (h) | `test_a_refused_bundle_gets_one_more_session_then_the_wave_ends` (362): `max_passes=20`, sessions naming 11 ≤ 2, wave-end line names `issue_10`, `` `Conflicts with: 10` ``, `iterate-plan`, no `max_passes`; the marker file holds `sessions: 1` |
| extra | `test_a_later_run_offers_the_refused_bundle_a_session_again` (384): the count does not outlive the wave |
| extra | `test_a_plain_c6_refusal_is_still_offered_a_session_every_pass` (398): today's C6 behaviour, unchanged (3 sessions over 3 passes) |
| (g) | `test_on_the_last_wave_both_are_accepted_and_published` (412) |

## Refuting my own test

- **(a) Genuine red? Yes.** Through the project's C4 gate (`engine/scripts/run-verify.sh`,
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout`), the green leg ran 10 tests, all OK.
  The red leg (production hunks reverted, test kept) ran 10 tests: 7 FAIL on assertions,
  no import error. In (a), (c), (h) and the re-run leg the refused bundle reaches
  `COMPLETE` on main. In (d), `sessions_had["11"]` is None, because no session follows a
  refusal. In (e) the trial's commit build is never attempted. In (f) the reassembly
  session never runs. Verdict: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with
  it`. The 3 tests green on main are the "nothing changes" legs (b), (g) and plain-C6,
  which by design pass on both sides. Three mutation checks, each reverted afterwards:
  - dropping the wave-start record reset fails the re-run leg (the bundle is parked with
    no session);
  - making `_parked` always False makes (h) offer issue_11 20 sessions and fail;
  - narrowing the rule to "candidate held" fails (c) only.
- **(b) Production path? Yes.** The real `flow._drive_and_act` → `_drive_wave` →
  `_apply_recorded_decision` / `_apply_decision` → `_refused_for_wave` →
  `integrate.same_wave_clash` (real `git` in the real integration worktree, under the
  real `integ_lock`) → `signoff.ensure_needs_human_item` / `open_needs_human`. Then the
  real publish loop, the real fold (which holds 11 in (d)), and the real `_bundle_bases`
  for wave 1. Only Do/Check, the sign-off leaf, publish's mechanics and `gh` are stubbed,
  and none of them is code this change touches.
- **(c) Fixture includes the fault? Yes.** 10 and 11 really change line 2 of the same
  file on a real bare origin, and the conflict is found by real merges of really-built
  commits. (e) injects a real failure into the trial's own git step instead of skipping
  it. The partner (10) is accepted and published in the same wave; it is not curated out.

## Suites and commit readiness

- T3 (`engine/scripts/run-suite.sh`, both target suites, under `timeout`), first run:
  root 24 tests OK, driver 2639 tests OK (skipped=2), `rc=0`. Re-run on the final tree
  (after the `contextlib.suppress` guard at flow.py:2674, the "this wave" wording in
  `_report_parked`, and the two added test checks): root 24 OK, driver 2640 OK
  (skipped=2), `PDCA-EVIDENCE: root suite OK, driver suite OK`, `rc=0`.
- T2 (`engine/scripts/run-docs-check.sh`): `lint_docs: OK`, `render_site: link audit OK`.
- The target configures no formatter, linter or pre-commit hook (no
  `.pre-commit-config.yaml`, no hooks in the repo's `.git/hooks`, nothing in
  CONTRIBUTING.md beyond DCO sign-off and the two suites). Its CI runs the docs check
  above and the suites. Publish's own `git commit -s` adds the DCO trailer.
- The PR should say `refs #395`, not `closes`: this is a partial fix (brief, Goal).

## Known limits (left as they are, with the fold as the last check)

- The fold condition is read when the wave starts. A split adopted during the wave can
  add later waves after `_drive_wave` returns. A wave that was last then gets a fold but
  had no trial, and #674 holds as on main. A reschedule that removes the later waves
  makes a refusal unnecessary but harmless: the bundle stays AWAITING_SIGNOFF.
- The trial starts the line at `folded_tips[target]`, else the base. The fold's "fresh"
  start in a later wave would first re-merge earlier-wave branches of that target. That
  happens only if an earlier wave had accepted bundles on the target but no fold ran for
  it, which an in-run fold never does (it folds every target).
- The base moving between accept and publish, a branch changed after accept, and the #747
  line-plus-sibling conflict are left to the fold, after publish (documented).
- A session that raises still counts as the one more session.
- Cost per accept with an accepted sibling on the same target: 2 fetches, N commit
  builds, about 2N trial merges plus `_held_by`'s trials, under the integration lock.
