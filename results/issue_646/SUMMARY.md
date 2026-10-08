# Result — issue 646 / stack-reissue-carries-clean-finished-prereqs

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: In stack mode the recovery for a run that stopped part-way (an integrity stop,
  the pass budget, a crash, Ctrl-C) is to re-issue the same `pdca flow <ids>`. That resumed
  run builds a dependent on a base missing its prerequisite when the prerequisite finished in
  the earlier run:
  - the finished id is skipped as already terminal (`template/src/pdca_harness/flow.py:2320-2325`),
    so it is not in the drive set and never enters `accepted` or the in-run fold
    (`flow.py:2053`, `:2067-2071`);
  - `_runnable` (`flow.py:681`) sees it as out-of-batch (`flow.py:706`, `batch_names` is the
    drive set) and accepts it because it is COMPLETE (`flow.py:710`). COMPLETE only means a
    draft PR was opened;
  - nothing has been folded yet, so `_point_at_integration` clears the dependent's stack base
    (`flow.py:722-742`) and the dependent is cut from the plain target base.
  The dependent is built, C4-verified and published without its prerequisite, and nothing
  reports it. The earlier run's line is usually still on `origin` under the same name (the
  batch key comes from the ids as asked for, skipped ones included: `flow.py:2360-2363`,
  `integrate.py:67`), holding the prerequisite, but the resumed run never uses it. Its first
  in-run fold force-replaces that line (`integrate.py:344-345`, `:390`, `:401`).
- Success criterion: With the patch, in stack mode with publishing on (non-stub
  publisher), real git against a bare `origin`, a re-issued run driven as
  `flow._drive_and_act(cfg, [<drive set>], …, batch=[<all requested ids>])` (the shape
  `flow_ids` produces when finished ids are skipped). Terms: a **finished named id** is a
  requested id that is COMPLETE and was skipped as terminal. It is **carryable** when it has a
  non-empty `patch.diff` and a resolvable target (exactly `integrate._fold_candidates`,
  `integrate.py:158`). It is **state-clean** when its PR state reads OPEN, or MERGED with
  its head already reachable from the target base or the line, AND its head commit resolves.
  These are checked before any fold. It is **clean** when it is state-clean AND the carry
  fold merges it onto the line without error (conflict, `_gone_branch` raise, any per-id
  `IntegrationError`) AND, when `[driver].regate_between_waves` is on, the carried line's
  re-gate is not red.
  (1) **Clean carry.** `P` finished, carryable, PR OPEN, branch pushed; `D` in the drive set
  with `- **Depends on:** P`. Before `D`'s wave is driven, origin's line
  `integrate.integration_branch(cfg, "main", ["P", "D"])` contains `P`'s branch head, and
  `D`'s stack base (`publish.read_stack_base`) names that line with
  `publish.read_stack_base_tip` equal to the line's tip. Pre-fix `D`'s stack base is cleared
  and no line holds `P`. This is the RED.
  (2) **Continue, never replace.** When origin already has that line (the earlier run's,
  holding only `P` on top of the base), the run continues it: the old tip is an ancestor of
  the new tip, and the push is not forced (the test's bare origin has
  `receive.denyNonFastForwards=true` and the run still succeeds).
  (3) **Append-only across waves.** With a second driven bundle `E` (`Depends on: D`), the
  fold after wave 0 continues the same line without force and without `IntegrationError`.
  The line then holds `P` and `D`, and `E`'s stack base names it.
  (4) **Not clean ⇒ hold only its dependents, run goes on.** For a carryable finished `P`
  that is NOT clean, for ANY reason, the run: does not put `P` on the line; leaves exactly
  `P`'s plain-`Depends on` dependents in the drive set PLANNED and unbuilt; prints ONE stderr
  line naming `P`, the held dependents and the reason; and builds an unrelated bundle `U` in
  the same run. The run never stops as a whole because of a finished id. The test covers
  three representative reasons: (a) PR state CLOSED; (b) PR state unreadable (`gh` missing,
  i.e. `OSError`, never a traceback); (c) two state-clean finished ids `P` and `Q` that
  conflict with each other: the one tried second (requested order) is held with its
  dependents, the first is carried, and its dependent builds on the line. The (4) tests run
  against an origin with NO earlier line, so (5) does not fire. When origin DOES have an
  earlier line holding a not-clean id's commits (the usual "its PR was closed after the
  earlier run" case), rule (5) wins: that line is untrusted, and the whole target is held as
  (5) says. This is deliberate. Building `P`'s dependent on a line that still holds a closed
  PR's code would ship that code in the dependent's PR. The other reasons not tested here
  (head unresolvable, MERGED head not reachable, red re-gate) go through the same single
  hold path; the review checks that there is one path and no per-reason branch. Only the
  red re-gate gets a test of its own, (8).
  (5) **Untrusted existing line ⇒ hold, don't build on it, don't overwrite it from the
  carry.** When origin's existing line has a non-merge commit that is reachable neither from
  the target base nor from the head of a STATE-clean finished named id (e.g. an old, rejected
  commit of another bundle, or the commits of a finished id whose PR is now CLOSED), the run
  carries nothing onto that target. It holds the
  plain-`Depends on` dependents of that target's carryable finished named ids, points no
  bundle at the line, and names the line on stderr with the advice to delete it on origin and
  re-issue. An unrelated `U` on that target builds on the plain base as today. The carry
  itself pushes nothing to that line. **Later in the run:** the carry leaves that target out
  of `folded_tips`, so the run's first in-run fold of it is today's fresh, forced fold. It
  replaces the untrusted line with base + this run's accepted bundles, and a later wave
  builds on that new line. This is today's one-run rule (`integrate.py:30-34`), not a
  regression. The hint text covers it ("delete `<line>` on origin unless this run's own fold
  already replaced it, then re-issue"). The (5) test has a wave-1 bundle `W` (`Depends on: U`)
  and asserts: `D` held and unbuilt; `U` built on the plain base; after wave 0, origin's line
  no longer holds the untrusted commit; `W`'s stack base names the new line.
  (6) **Trigger.** The carry happens only when some drive-set bundle's plain `Depends on`
  names a finished id that is carryable. If `P` is COMPLETE with an empty or missing
  `patch.diff`, nothing is folded and `D` builds on the base as today, EVEN when another,
  unrelated finished id `Q` is carryable. In that case `Q` is not carried and nothing is
  held because of `Q`. When the carry does trigger, every carryable finished named id on
  that target goes through the same clean/not-clean rule, and every runnable wave-0 bundle
  of that target, including an unrelated `U`, is pointed at the line (its PR still targets
  `main`, #593).
  (7) **Unchanged.** A run with no finished named id that a drive-set bundle depends on
  behaves exactly as today (no pre-wave fold, stale stack bases cleared). `Stacks on` and
  `Depends on (merged)` edges do not trigger the carry and keep their behaviour (#123,
  #186). A dry-run (stub publisher) asks no host, holds nothing, and only prints the plan.
  `--no-publish` and merge mode are untouched. The (7) test asserts only the first sentence
  (no pre-wave fold, stale stack base cleared) and the dry-run sentence. The `Stacks on`,
  `Depends on (merged)`, `--no-publish` and merge-mode claims are kept by the existing suites
  passing unchanged (`test_integrate_stack_bases.py`, the merge-mode and flow tests), not by
  new tests here.
  (8) **Red re-gate on the carried line.** With `regate_between_waves` on and the re-gate
  stubbed to return `{"overall": "fail"}` for the carried line: every id carried onto that
  target is treated as not clean (one stderr line, dependents held), no bundle is pointed at
  the line, `U` builds on the plain base, and the run goes on. The run does not `break` the
  way the in-run red re-gate does. The carry leaves that target out of `folded_tips`, so, as
  in (5), the run's first in-run fold of it starts fresh and force-replaces the red line. A
  wave-1 bundle never builds on the red line. Assert that a wave-1 `W` (`Depends on: U`)
  gets a line whose history does not include `P`'s head.
  **When does a fold force-push?** With the patch: a target the carry put to use (at least
  one id carried AND the re-gate not red) is seeded into `folded_tips` with the carried tip.
  Every later fold of that target in the run continues it without force. A target the carry
  did not put to use (no trigger, nothing clean, untrusted line, red re-gate) is NOT seeded,
  and its first in-run fold is today's fresh, forced fold. So a force-push in (5), (6), (7)
  or (8) is expected, and a force-push in (1)-(3) is a regression.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a re-issued stack-mode `pdca flow <ids>` put its CLEAN finished named ids
  (definition in the Success criterion) onto its batch's integration line before wave 0. It
  continues origin's line when that line exists and is trusted (append-only, no force), starts
  it fresh only when it does not exist, and then points the run's bundles at it exactly as
  later waves already are. **ONE rule for everything else:** a finished named id that is not
  clean, for any reason, holds only its own plain-`Depends on` dependents, is named with its
  reason on one stderr line, and the rest of the run goes on. An existing line that holds
  commits not accounted for by the base plus the clean ids' heads is not built on and not
  touched by the carry (criterion 5). Ids are tried in the order they were requested. A
  failure on one id (merge conflict, `IntegrationError`, unreadable state) holds that id and
  the next is tried. Keep the round-1 requirements, which sign-off accepted: the carry holds
  the integration lock across its fold AND the tip read, and when
  `[driver].regate_between_waves` is on it re-gates the carried line under that lock.
  **How to try ids one at a time (decided here, not by Do):** ONE `integrate.fold` call per
  target, covering all of that target's state-clean carryable ids, under one
  `contextlib.ExitStack` passed as `locks`, followed by the re-gate under the same stack,
  exactly as in the in-run block (`flow.py:2060-2095`). Do NOT call `fold` once per id under
  a shared `locks` stack: `integ_lock` opens the `.lock` file again on each call
  (`integrate.py:213`), so a second call on the same target blocks on the process's own
  flock. To get per-id skipping, add ONE keyword parameter to `fold` (for example
  `skipped: dict[str, str] | None = None`). When it is given, an `IntegrationError` raised
  while merging ONE bundle (`_merge_published`, including its `_gone_branch` raise) is
  recorded as `skipped[d.name] = str(exc)` and the loop moves on. `_merge` already aborts a
  failed merge (`integrate.py:548`), so the worktree is clean for the next id. Failures
  that are not per-bundle (lock, worktree preparation, "origin's line moved", push) still
  raise and hold every id of that target. When every bundle of a target was skipped, push
  nothing and return no entry for that target. When `skipped` is `None` (the in-run call),
  `fold` behaves exactly as today. **Start mode for the carry:** the trust check (5) reads
  origin's line tip `T`. If the line exists and is trusted, pass
  `folded_this_run={target: T}`, so `fold` continues from `T` without force and refuses if
  origin moved off `T` in the meantime (`integrate.py:380-386`). If the line is absent, leave
  the target out, so `fold` starts fresh. A shared helper used by both the carry and the
  in-run block (lock stack + fold + tip read + re-gate) is the preferred way to reuse the
  path. Only the RESULT HANDLING differs. In-run: an error or red re-gate ⇒ `break`, as
  today, unchanged. Carry: a whole-target `IntegrationError` or a red re-gate ⇒ every id
  of that target is not clean (held, one stderr line each), the target is not seeded into
  `folded_tips` or `integ`, and the run goes on. A red re-gate on the carried line counts as
  "not clean" for every id carried on that target: their dependents are held and no bundle
  of that target is pointed at the line (criterion 8). Advice text: keep it to the reason
  plus one of three hints. For a merged head the line cannot verify: remove the
  `Depends on: <P>` edge from the dependent's brief, then re-issue. For an untrusted line:
  delete `<line>` on origin unless this run's own fold already replaced it, then re-issue.
  For everything else: get `<P>`'s PR open with its branch on origin (re-open it,
  `pdca publish <id>`, or re-drive `<P>`), then re-issue. Update the stack-mode paragraph in
  `docs/07-crosscutting.md:658-677`, the "#616" wording in `publish.py:345`, `:696`, `:726`,
  and the "known cross-run limit (#616)" docstring in `drift.py:58-61`, so they describe the
  carried line and its limits. **Wording constraint:** `_line_tip_refusal`'s behaviour does
  NOT change, and a line that was not carried is still force-replaced by a later run's first
  fold. So the new wording must keep "re-drive it in a new run" as the advice and must not
  say that the refusal can no longer happen. Drop only the "#616 will fix this" pointer, and
  say that a re-issue continues the line only when it carries a finished prerequisite. Update the
  existing assertions that pin the old wording, `template/tests/test_integrate_stack_bases.py:834-852`
  (asserts `"#616"` and `"re-drive it in a new run"`) and `:1012` (asserts `"#616"`), in the
  same patch.
  **Known limits (accepted at sign-off of iteration 4; document them in the docs paragraph,
  do NOT handle them):** a squash- or rebase-merged prerequisite whose branch is gone; a closed
  PR that a newer PR replaced; an empty `pr_url` (no lookup by branch name); a rejected or
  force-pushed-over commit left on the old line; two finished ids that conflict; an earlier
  line that still holds a finished id whose PR was later closed (criterion 5 holds the whole
  target); and an accepted-but-unpublished bundle stranded by `_line_tip_refusal`
  (`publish.py:691-726`) because a later run's fresh fold replaced the line it was built on.
  The issue body's "`_line_tip_refusal` returns `""` for `H`" assertion is dropped from this
  child. It holds only when the carry continues the line, and this brief does not promise it
  in general. Each of these holds dependents (or the publish) until a person acts. None of
  them stops the run.
  / out of scope: any recovery logic for a non-clean case (looking a PR up by its head branch,
  repairing or rebuilding the line, auditing the line per id beyond the single check in (5),
  per-case recovery flows); a prerequisite that is NOT one of the requested ids, including the
  `flow_batch` sweep path (#647); `merged.is_merged`'s "merged where" rule (#647);
  `Depends on (merged)` semantics (#186); `Stacks on`; merge mode (#531); split children
  adopted mid-run by an earlier run (name the gap in a docstring); a line on origin that an
  outside party rewrote beyond what (5) detects; pruning old integration branches (#454).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #646: make a re-issued stack-mode flow carry clean, finished named prerequisites before building their dependents, while holding dependents of prerequisites it cannot carry.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The recovery contract distinguishes trusted continuation, per-prerequisite holds, and fresh replacement after an unusable carry; the scenarios are falsifiable and the limitations explicit (brief.md:35; target/docs/07-crosscutting.md:679). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing production changes while retaining the tests produced 10 assertion failures in 13 cases, including the dependent missing its prerequisite's stack base (review-red.log:1; review-red.log:134; target/template/tests/test_flow_resume_stack_prereqs.py:176). |
| C3 Change | PASS | Within the specified recovery scope, failed prerequisites hold their dependents while unrelated work proceeds; successful carries retain their tips for later waves, and the 59 targeted tests pass (target/template/src/pdca_harness/flow.py:885; target/template/src/pdca_harness/flow.py:2114; review-green.log:25). |
| C4 Verification (red→green) | PASS | The offline regression is independently reproduced red→green: 13 tests with 10 failures before restoration, then 59 targeted tests passing with the patch restored; this establishes the Git/flow behavior, not live host integration (review-red.log:132; review-green.log:25; gate-logs/C4-verify.log:10). |
| C5 Causal adequacy | PASS | The originally skipped finished prerequisites now enter the pre-wave fold, addressing the missing base ancestry directly; the tests call production flow and Git, and the missing-gh exception is an operational hold rather than a probe masking eager initialization (target/template/src/pdca_harness/flow.py:2105; target/template/tests/test_flow_resume_stack_prereqs.py:145; target/template/src/pdca_harness/merged.py:96). |
| T1 Structure | PASS | Carry and in-run folds share a lock scope through tip capture and re-gating; per-bundle skipping remains opt-in, preserving ordinary fold failure semantics (target/template/src/pdca_harness/flow.py:768; target/template/src/pdca_harness/integrate.py:435). |
| T2 Shape | PASS | Independently rerun docs lint, 22-page rendering/link audit, and whitespace checks pass; frozen host-CI-parity evidence covers the same documentation checks (review-docs-lint.log:1; review-docs-render.log:3; review-provenance.log:9; gate-logs/host-ci-docs.log:10). |
| T3 Runtime | PASS | The independent driver run passes 2,338 tests with two skips; the frozen root log shows all 24 tests passing, including render/update cases, although this reviewer interpreter lacks Copier (review-driver.log:1798; gate-logs/T3-suite.log:38; gate-logs/T3-suite.log:54; review-root.log:6). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted at Check; their substantive audit is deferred to the mandatory publish-time rerun (gate-logs/T4-contribution.log:10). |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path merged/closed/rejected prior art and accept the stacked-base ordering risk—this target has one synthetic base commit and no remotes, so the brief's historical search and prerequisite landing cannot be independently settled here (review-provenance.log:1; brief.md:155; brief.md:279). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the bounded recovery policy and offline host simulation are sufficient for release—real gh/host PR-state behavior was not exercised, and known non-clean cases still require operator action (target/template/tests/test_flow_resume_stack_prereqs.py:90; target/template/src/pdca_harness/merged.py:103; target/docs/07-crosscutting.md:695). |

No confirmed patch defect was found within the specified offline scope. This review is advisory and does not authorize acceptance or publication.

Independent execution used the supplied disposable target only. Production changes under `template/src` were stashed, the new regression module was run unchanged, and the stash was restored before the green run. The target's original patch remains applied. Source citations above refer to that patched target; frozen evidence and reviewer logs are identified separately. No stale-target caveat was needed.

The checks run were:

- From `target/template`, `PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs` for red, then `PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs tests.test_integrate_stack_bases` for green.
- From `target/template`, `PYTHONPATH=src python3 -m unittest discover -s tests`: exit 0, 2,338 tests, two skips.
- From `target`, `python3 -m tests.run_root_suite`: exit 77 because this interpreter cannot import Copier. The frozen `gate-logs/T3-suite.log:38` explicitly shows render and update cases executing, followed by 24 tests and `OK` at line 54. This is a reviewer-host limitation, not a patch failure or a claim that skipped cases were verified locally.
- Docs lint and renderer `--check`, the shipped production-import scanner against this bundle's patch, and `git diff --check`: all passed. The instance-scoped wrapper paths were adjudicated using their supplied logs; no missing-wrapper finding is raised.

The remaining human decisions are:

- [ ] Confirm prior art across every affected path, including merged history and closed/rejected work. The brief records a path-based search for flow.py, integrate.py, and merged.py and names rejected attempts, but this isolated one-commit target cannot corroborate that search or extend it to the other affected paths. The independent `git log --all -- <affected paths>` and remote inventory are captured in `review-provenance.log:1`.
- [ ] Accept the base dependency described in `brief.md:155`: this patch was built on the integration base containing #531, #590, and #591 rather than main alone. Confirm their disposition and whether a prerequisite change requires rebuilding this patch; no current landing status is established by this artifact bundle.
- [ ] Accept or discharge the unexercised live host dependency. Although `brief.md:249` declares no external dependencies and the offline Git topology reproduces the forbidden failure, the new PR-state query uses mocked gh responses (`target/template/tests/test_flow_resume_stack_prereqs.py:90`). Live authentication, host responses, and their correspondence with fetched branch heads were not verified. The carried-line red re-gate test also supplies a controlled failing result; it establishes hold behavior, not a live service integration result.
- [ ] Accept fitness-to-purpose of the documented recovery limits: non-clean prerequisites hold dependents, and an untrusted or red carried line may subsequently be replaced by the run's first fresh fold. The independent tests exercised those outcomes; the decision is whether that operator recovery policy is suitable, rather than whether to investigate it.

The available integration document is the unrendered template, `target/template/docs/INTEGRATION.md.jinja:80`; its project-defined human-only items remain TODO, so it supplies no additional concrete project-specific verdict criterion.

### Advisory — adversary

# Adversarial review — issue 646 (stack re-issue carries finished prerequisites)

Evidence re-run at `$PDCA_TARGET`: the new file passes 13/13 with the patch. With only the
production hunks backed out (scratch copy), 10/13 fail on assertions. The 3 that pass pre-fix
are the two (6) cases and the (7) no-trigger case, which assert "unchanged" behaviour, so that
is expected. The tests drive the real `flow._drive_and_act` → `integrate.fold` against real
git (bare origin). Only the build/sign-off leaves, `_publish_bundle` and `gh` are stubbed. The
C4 claim in `check-gates.json` holds. Three scenarios outside the closed test list break the fix:

- NEEDS-HUMAN — **A closed prerequisite's code still reaches a dependent through a stacked
  finished id.** `template/src/pdca_harness/flow.py:870-879` judges each finished id only on
  its own PR state. `foreign_commit` (`template/src/pdca_harness/integrate.py:196-207`) then
  counts every commit reachable from a state-clean head as "accounted for". Case (reproduced
  on the fixture): the earlier run folded `P` (wave 0), then published `Q` (`Depends on: P`)
  cut from that line and folded it. The run stopped before `D` (`Depends on: Q`). `P`'s PR
  was then closed. Re-issue `[P, Q, D]`: the carry prints `issue_P … its PR is CLOSED —
  holding no bundle`, carries `Q`, and builds `D` on a line whose history holds `P`'s head.
  The same happens after following the hint and deleting the old line: `Q`'s own head brings
  `P`'s commits in. This contradicts the brief's own rule at `brief.md:65-68` ("When origin
  DOES have an earlier line holding a not-clean id's commits … rule (5) wins … Building `P`'s
  dependent on a line that still holds a closed PR's code would ship that code"). The brief's
  (5) wording ("reachable … from the head of a STATE-clean finished named id") allows it, so
  this is a spec gap, not a builder slip. A human has to decide whether "not clean" cascades
  across finished ids: a finished id whose plain `Depends on` names a not-clean finished id
  is itself not clean, the way `_runnable`'s skip cascades.

- NEEDS-HUMAN — **The commit the carry approves is not the commit it folds.**
  `_finished_head` (`template/src/pdca_harness/flow.py:805-816`) checks the PR's
  `headRefOid`. The fold then merges the branch's *current* tip
  (`template/src/pdca_harness/integrate.py:468`, `head = _rev(wt, ref)`). Case (reproduced):
  `P`'s PR is MERGED at `H` (on `main`), then someone pushes `X` onto `fix/P`. GitHub allows
  this, and `X` is in no PR. The carry reports `P` clean, merges `X` onto the line, and `D`
  is built on unreviewed `X`. The same split exists for an OPEN PR whose branch moves between
  the `gh` read and the fold. No test covers the MERGED path: the `gh` stub
  (`template/tests/test_flow_resume_stack_prereqs.py:690-701`) always reports head == branch
  tip. Possible fixes: fold the approved head, or call branch tip ≠ PR head "not clean". The
  in-run fold merges branch tips on purpose (#593), so a human should pick which.

- NEEDS-HUMAN — **A continued line keeps the earlier run's base, so dependents build on an
  old `main`.** Continuing starts from origin's old tip (`template/src/pdca_harness/integrate.py:430`
  with `folded_this_run={tgt: tip}` from `flow.py:889-891`). Nothing brings in commits that
  landed on `main` since the earlier run. Case (reproduced): earlier line = `main@B0 + P`, then
  a commit `M` lands on `main`. On re-issue, `D` is built and C4-verified on a base without
  `M`. Pre-fix, `D` had `M` but not `P`. Now it has `P` but not `M`. Criterion (2) requires
  this trade-off, but a run that resumes days later makes it much larger than within one run.
  It is not among the known limits in `docs/07-crosscutting.md:695-702`. Sign-off should
  accept it explicitly, or the docs should name it.

Attempted and could not refute:
- the per-id `skipped=` path leaves a clean tree: every failure in `_merge` / `_take_in_base`
  aborts first (`integrate.py:583-594`);
- `integ.update` replacing `integ = {…}` (`flow.py:2256`) changes nothing for a run without a
  carry: `accepted` is cumulative, so a folded target never drops out;
- `_runnable`'s `dep in plain_deps` (`flow.py:717`) parses the same `_id_list` as
  `declared_deps`, so no id-format mismatch lets a held prerequisite through;
- request order is kept (`_finished_named` reads the raw `batch`, not the sorted `run_batch`);
- one `fold` per target under one `ExitStack`: no self-deadlock;
- the trust read in `carry_view` (`integrate.py:185-193`) happens outside the lock, but the
  fold re-checks origin's tip under the lock and refuses on a move. A concurrent fetch in the
  same checkout can at worst fail closed (ids held with a git error).

### Advisory — code-review

# Advisory code review — issue 646 (stack-reissue-carries-clean-finished-prereqs)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Advisory only.

Overall: no blocking correctness bug found. The carry follows the brief's chosen mechanism: one `fold` per target with `skipped=`, one shared lock helper (`_fold_lines`), and a single hold path for every not-clean reason. The in-run refactor keeps the old behaviour: the tip is recorded before the re-gate, the re-gate short-circuits on the first red (`next` here, `any` before), and an error or red re-gate still `break`s. Gate evidence agrees. C4 red leg: 10 of 13 new tests fail without the fix, plus the reworded `test_a_late_publish_…` (gate-logs/C4-verify.log:46-213). T3 suite is green (gate-logs/T3-suite.log). The three new tests that stay green pre-fix are the (6)/(7) "unchanged" cases, which is expected.

Findings (all minor):

- `template/src/pdca_harness/flow.py:868` — `integrate.carry_view` runs `_fetch` (with `--prune`) in the primary checkout **outside** the integ lock. The in-run fold only fetches under the lock (`integrate.py` `_prepare_worktree`). Safety still holds, because `fold` re-fetches under the lock and refuses if origin moved off the checked tip `T` (`integrate.py:419-426`). The cost: if another run's fold fetches the same checkout at the same moment, git can fail on a ref lock. The carry then holds every finished id of that target with a confusing "could not fetch" reason, and the hint says to re-open the PR. Rare and loud, not silent. Worth a one-line comment, or taking the lock around the view.
- `template/src/pdca_harness/flow.py:897-899` — on a red carry re-gate the carried line has **already been pushed** to origin. A continued line is pushed without force, so the earlier run's line now also holds the red merge. The target is not seeded, so a later in-run fold replaces it, as the brief says in (8). But if no in-run fold of that target follows (single-wave run, or every dependent held), the red line stays on origin. The next re-issue then finds it "trusted", because P is state-clean, carries again and goes red again. That is consistent with the brief, and the stderr line is loud. It might be clearer if the red-re-gate stderr line said the line was pushed. No code change is required.
- `template/src/pdca_harness/flow.py:801` — `_finished_head` takes `ref` only to test whether it is truthy, then reads `publish._publish_record(d)` (a private helper of another module; `merged._publish_record` at `merged.py:119` is an identical copy). Small simplification: drop the `ref` parameter and test `pr_url` alone. A bundle with no branch on record already fails `if not pr_url`, or will fail the fold's up-front refusal. Cosmetic.
- `template/src/pdca_harness/merged.py:96` — `pr_state` repeats the `gh` run / `OSError` guard / JSON-parse shape of `merged_head` (`merged.py:64`). The brief asked for that guard to be copied, so this is accepted duplication. A shared `_gh_pr_json(url, fields)` helper would cut it. Optional.
- `template/tests/test_flow_resume_stack_prereqs.py` (patch lines 806-822) — test (3) checks that only the second push (the wave-0 fold) has no `--force`. It never checks the first push (the carry onto an absent line, which is expected to be a forced fresh start). That is fine for (3). Nothing tests the carry's whole-target `IntegrationError` path (`flow.py:892-894`, e.g. the push failing after a skip). The brief kept the test list closed and sends that path to review. Reviewed: it holds every clean id with the error text and seeds nothing, which is correct.

No reuse or efficiency problems beyond the notes above. `_fetch` was pulled out of `_prepare_worktree` rather than copied. `_fold_candidates` stays the one definition of "carryable". The `gh` lookup runs once per finished id of a target that has a dependent, and not at all otherwise (tested by the (6)/(7) cases).

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm affected-path merged/closed/rejected prior art and accept the stacked-base ordering risk—this target has one synthetic base commit and no remotes, so the brief's historical search and prerequisite landing cannot be independently settled here (review-provenance.log:1; brief.md:155; brief.md:279).
- [x] Validation — fitness-to-purpose — Decide whether the bounded recovery policy and offline host simulation are sufficient for release—real gh/host PR-state behavior was not exercised, and known non-clean cases still require operator action (target/template/tests/test_flow_resume_stack_prereqs.py:90; target/template/src/pdca_harness/merged.py:103; target/docs/07-crosscutting.md:695).
- [x] **A closed prerequisite's code still reaches a dependent through a stacked finished id.** `template/src/pdca_harness/flow.py:870-879` judges each finished id only on its own PR state. `foreign_commit` (`template/src/pdca_harness/integrate.py:196-207`) then counts every commit reachable from a state-clean head as "accounted for". Case (reproduced on the fixture): the earlier run folded `P` (wave 0), then published `Q` (`Depends on: P`) cut from that line and folded it. The run stopped before `D` (`Depends on: Q`). `P`'s PR was then closed. Re-issue `[P, Q, D]`: the carry prints `issue_P … its PR is CLOSED — holding no bundle`, carries `Q`, and builds `D` on a line whose history holds `P`'s head. The same happens after following the hint and deleting the old line: `Q`'s own head brings `P`'s commits in. This contradicts the brief's own rule at `brief.md:65-68` ("When origin DOES have an earlier line holding a not-clean id's commits … rule (5) wins … Building `P`'s dependent on a line that still holds a closed PR's code would ship that code"). The brief's (5) wording ("reachable … from the head of a STATE-clean finished named id") allows it, so this is a spec gap, not a builder slip. A human has to decide whether "not clean" cascades across finished ids: a finished id whose plain `Depends on` names a not-clean finished id is itself not clean, the way `_runnable`'s skip cascades.
- [x] **The commit the carry approves is not the commit it folds.** `_finished_head` (`template/src/pdca_harness/flow.py:805-816`) checks the PR's `headRefOid`. The fold then merges the branch's *current* tip (`template/src/pdca_harness/integrate.py:468`, `head = _rev(wt, ref)`). Case (reproduced): `P`'s PR is MERGED at `H` (on `main`), then someone pushes `X` onto `fix/P`. GitHub allows this, and `X` is in no PR. The carry reports `P` clean, merges `X` onto the line, and `D` is built on unreviewed `X`. The same split exists for an OPEN PR whose branch moves between the `gh` read and the fold. No test covers the MERGED path: the `gh` stub (`template/tests/test_flow_resume_stack_prereqs.py:690-701`) always reports head == branch tip. Possible fixes: fold the approved head, or call branch tip ≠ PR head "not clean". The in-run fold merges branch tips on purpose (#593), so a human should pick which.
- [x] **A continued line keeps the earlier run's base, so dependents build on an old `main`.** Continuing starts from origin's old tip (`template/src/pdca_harness/integrate.py:430` with `folded_this_run={tgt: tip}` from `flow.py:889-891`). Nothing brings in commits that landed on `main` since the earlier run. Case (reproduced): earlier line = `main@B0 + P`, then a commit `M` lands on `main`. On re-issue, `D` is built and C4-verified on a base without `M`. Pre-fix, `D` had `M` but not `P`. Now it has `P` but not `M`. Criterion (2) requires this trade-off, but a run that resumes days later makes it much larger than within one run. It is not among the known limits in `docs/07-crosscutting.md:695-702`. Sign-off should accept it explicitly, or the docs should name it.
- [x] **The stated invariant claims more than its sources say, and more than criteria (6) and (7) keep.** The brief says: "Within a batch, the integration line only grows … Sources: … the append-only rule in `integrate.py:30-34` and `docs/07-crosscutting.md:658-665`". Both sources limit the rule to **one run**, and both say cross-run replacement is intended:
- [x] **The in-run fold after wave 0 is unspecified for the "hold" outcomes.** Criterion (5) says only that "the carry itself pushes nothing to that line". The same gap applies to a red carry re-gate (Scope: "no bundle of that target is pointed at the line"). In both cases `folded_tips` presumably stays unseeded for that target. With two or more waves, `flow.py:2067-2070` then folds wave 0 in `fresh` mode and force-pushes over the "untrusted" line. That is the line the advice tells the operator to inspect and delete. If the planner instead seeds `folded_tips` from the red re-gate, wave 1 builds on a red line.
- [x] **Two required behaviours are hard to get by reusing the in-run fold path, and the brief requires that reuse.**
- [x] **A non-clean id whose commits are already on the earlier line turns criterion (4) into criterion (5) whenever origin has an earlier line holding the id's commits.** Criterion (5) calls the line untrusted when it holds a non-merge commit reachable "neither from the target base nor from the head of a **clean** finished named id". Take the usual re-issue case: the earlier run folded `P` and `H`, and `H`'s PR was later CLOSED, so `H` is not clean. `H`'s commits are then unaccounted for, the whole line is untrusted, and the carry puts nothing on that target. That also holds `P`'s dependents and moves `U` to the plain base. Criterion (4) promises "hold only its dependents, run goes on" with `U` on the line, and the 4(c) wording ("the first is carried, and its dependent builds on the line") assumes the carry still happens.
- [x] **A case from the issue body was dropped without being listed as out of scope.** The issue body (`notes.json`) motivates the fix with stranding: the force-replace "strands any accepted-but-unpublished bundle whose recorded line tip was on it (`publish._line_tip_refusal`, `publish.py:691-726`)". Its criterion (2) asserted that `_line_tip_refusal` for such an `H` returns `""`. This brief removes `H` from (2). It does not list the stranding case under "out of scope" or "Known limits". It still tells Do to rewrite the `publish.py:696` and `:726` wording ("resuming across runs is #616", "Re-drive it in a new run (#616)") "so they describe the carried line". When the carry doesn't trigger (criteria 6 and 7), `_line_tip_refusal` still fires for the same reason as today, and the old advice is still the right advice. Either keep an `H` assertion or list the case as a known limit, so the wording change doesn't promise something the code doesn't do.
- [x] **The test-size constraint can't be checked, and criterion (4)'s "for ANY reason" claim covers more than the tests do.** The Test file section asks for "One test per criterion item (1)-(7), with (4)(a)/(b)/(c) as separate tests". (6) and (7) each contain several independent claims: an empty or missing `patch.diff` with an unrelated `Q`; wave-0 `U` pointed at the line; `Stacks on`; `Depends on (merged)`; dry-run asks no host; `--no-publish`; merge mode untouched. One test each cannot check all of them, so "keep the file focused" (v4: 66 KB / 39 tests was "part of what was rejected") has no measurable bar. Criterion (4) also claims "for ANY reason", but only three reasons are tested. Head-unresolvable, MERGED-not-reachable and red re-gate are covered by no test, so the adversary can still find the next untested case. Give a size or test-count ceiling, or list exactly which sub-claims are asserted and which are covered by review only.
- [x] **"Repo + branch target" and the build base point at different branches. Minor, but declare it.** "Repo + branch target: eduralph/pdca-harness @ main". The Ordering note puts Do and C4 on `pdca-integration/main`, because the fix needs #591's batch-scoped name, and PR #639 is "still OPEN". The resulting PR against `main` will carry #531/#590/#591 until they merge (the fold-line PR behaviour, `integrate.py:21-23`). If #639 is reworked before it merges, the bundle is built on a base that was never merged. No `Depends on` field records this (the brief explicitly dropped `Depends on (merged): 591`), so nothing gates it. A human should accept that risk explicitly at sign-off.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 7 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- Follow-up (from #646 sign-off, adversary): cascade "not clean" across finished ids — a finished id whose plain `Depends on` names a not-clean finished id is itself not clean (closed P leaks via carried Q).
- Follow-up (from #646 sign-off, adversary): carry approves PR `headRefOid` but folds the branch's current tip — fold the approved head, or treat tip ≠ PR head as not clean.
- Follow-up (from #646 sign-off, adversary): a continued line keeps the earlier run's base (stale `main` on a late re-issue) — document as a known limit in docs/07-crosscutting.md or refresh the base.
