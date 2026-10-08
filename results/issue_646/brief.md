# Brief — issue 646 / stack-reissue-carries-clean-finished-prereqs

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.
> Child 1 of the split of #616. **Re-plan (iteration 5)** after four rejected builds: see
> "Re-plan note" at the end, which REPLACES every earlier carry-forward.
> Verified against `eduralph/pdca-harness` `origin/pdca-integration/main` @ `12405dc`
> (`origin/main` @ `c67a14d` plus #531, #590, #591 folded; same tree as the `f594d8e` the
> earlier rounds cited). All `path:line` below are on that commit. The bundle's
> `stack-base` is `pdca-integration/main`, so Do and C4 build on it. #591's batch-scoped
> line name (`integrate.integration_branch(cfg, base, batch)`, `integrate.py:67`) exists
> only there until PR #639 merges.

- **Slug:** stack-reissue-carries-clean-finished-prereqs
- **Defect:** In stack mode the recovery for a run that stopped part-way (an integrity stop,
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
- **Success criterion:** With the patch, in stack mode with publishing on (non-stub
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
- **Falsifiability:** RED is reachable offline on the C4 gate's own runner (`cd template &&
  PYTHONPATH=src python3 -m unittest tests.test_flow_resume_stack_prereqs`).
  `template/tests/test_integrate_stack_bases.py` already provides the fixture:
  `StackFoldGit` (`:115`) gives a bare `origin`, a primary checkout and a `gh` stub, and
  `_publish` (`:142`) pushes a branch and writes `publish.json` through production publish
  code. Driving `flow._drive_and_act` with stubbed build/sign-off leaves over `[D]` with
  `batch=["P","D"]` shows `D`'s stack base cleared and no line holding `P` today, so (1)
  fails pre-fix. (4)(a)/(b) also fail pre-fix, because `D` is built. (5) and (8) fail pre-fix,
  because `D` is built. No network. The publisher must NOT be in stub mode for (1)-(6): a
  stub turns every fold into a dry-run (`flow.py:2038`), which records no line. Patch
  `flow._publish_bundle`, or reuse the fixture's `_publish`, rather than running the publisher
  leaf. The iteration-v4 C4 log confirms this gate keeps the NEW `template/tests/*.py` file in
  the red leg and reverts only production hunks.
- **Invariant to restore:** Every bundle a stack-mode run builds is built on a base that
  carries all of its declared prerequisites, whether the prerequisite was accepted in this run
  or in an earlier run of the same batch. A prerequisite the run cannot put on that base
  cleanly holds only its own dependents, loudly. No run builds on a line holding commits it
  cannot account for. A line that a run CONTINUES (the carry put it to use) is append-only for
  the rest of that run, from the carried tip onward. Where the carry does not put a target's
  line to use, the run's first fold of it still starts fresh with a force-push, as the
  one-run rule says. This brief extends append-only across runs ONLY for a carried line; it
  does not make every line append-only across runs. Sources: the wave contract in
  `_drive_and_act` ("a dependent builds on its prerequisite's accepted result within one
  run"); `_runnable`'s docstring, which states the hazard ("a dependent built on a
  COMPLETE-but-unmerged base would miss the prerequisite", `flow.py:692-698`); the one-run
  append-only rule in `integrate.py:30-34` and `docs/07-crosscutting.md:658-665`. Both of
  those limit append-only to one run and allow the run's first fold to force-replace an
  earlier run's line. This brief keeps that, except for a carried line.
  The property spans the readiness check, the fold's start mode and the stack-base pointing,
  so guarding a single module cannot satisfy it.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** First child of #616. No scheduling field: #591 (PR #639, still OPEN) is
  not a sibling. It reaches this child through the run's integration line, which the bundle's
  `stack-base` (`pdca-integration/main`) points at; Do and C4 build there. The earlier
  `Depends on (merged): 591` was dropped (the field is deprecated, and it never gated the
  four builds). Sibling #647 declares `Depends on: 646`. **Base risk, for sign-off to accept
  explicitly:** the PR targets `main` but is built on `pdca-integration/main`. Until #531,
  #590 and #591 merge, it carries their commits (the fold-line PR behaviour,
  `integrate.py:21-23`). If PR #639 (#591) is reworked before it merges, this bundle was
  built on a base that never landed and must be rebuilt. No scheduling field gates this; the
  human accepts it at sign-off.
- **Surfaces:** data
- **Difficulty:** high. `_drive_and_act` gains a pre-wave carry step that feeds the same
  `integ` / `folded_tips` / held-set bookkeeping as the in-run fold. `_runnable` must hold a
  finished named id's dependents. `integrate.fold` gains one `skipped=` keyword (per-bundle
  skip, unchanged when absent). There is a PR-state read with a missing-`gh` guard, one
  line-trust check, wording in `publish.py` / `drift.py` / docs, and two existing test
  assertions. The reviewer must keep #593's in-run fold contract and #591's batch scoping in
  view.
- **Scope:** Make a re-issued stack-mode `pdca flow <ids>` put its CLEAN finished named ids
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
- **Repro instruction:** On `origin/pdca-integration/main`, in `template/` with
  `PYTHONPATH=src`, using the `StackFoldGit` shape: plan and publish `P` (`org/repo @ main`, a
  patch adding a file), mark it COMPLETE (sign-off accept, then `publish.json` written after
  it), and stub `gh pr view` to report `OPEN`. Plan `D` with `- **Depends on:** P` and a patch
  that needs `P`'s file. Call `flow._drive_and_act(cfg, [D], do_publish=True, batch=["P", "D"], …)`
  with build/sign-off leaves stubbed and `flow._publish_bundle` patched. Wrap
  `flow._drive_wave` to record `D`'s stack base when its wave runs. Observed: `D`'s
  `stack-base` is absent and no line on `origin` holds `P`.
- **External dependencies:** none
- **Test file:** template/tests/test_flow_resume_stack_prereqs.py (NEW file. The C4 gate
  reverts only production hunks and keeps `template/tests/*.py`, so a new file earns its red.)
  Import modules only, never a symbol the fix adds, so the red leg fails on assertions and not
  at import. Reuse the `StackFoldGit` fixture shape from
  `template/tests/test_integrate_stack_bases.py` (subclass or import it; don't copy it). The
  test list is closed: (1), (2), (3), (4a), (4b), (4c), (5), (6) as two tests (empty
  `patch.diff`; unrelated carryable `Q` not carried), (7) as two tests (no trigger; dry-run),
  (8). That is 12 tests at most, plus at most one unit test for the new `fold(skipped=…)`
  parameter. Ceiling: about 700 lines / 30 KB. Claims not in this list are covered by the
  existing suites or by review (see (4) and (7)), not by more tests here. The iteration-v4
  test file was 66 KB with 39 tests, and that size is part of what was rejected.
- **Citations expected:** Do must cite path:line on the target branch for every change. Peer
  callsites to mirror:
  - the in-run fold block in `_drive_and_act` (`flow.py:2045-2095`): the
    `integrate.unpublished(…, pushed=…)` hold with its stderr line (`:2053-2058`), the
    `integrate.fold(…, locks=locks, folded_this_run=…, batch=run_batch)` call (`:2067-2070`),
    the `folded_tips` / `integ` bookkeeping (`:2074-2081`), and the re-gate under the same
    lock (`:2087-2095`);
  - the fold's start modes (`integrate.fold` docstring `integrate.py:265-272`, code
    `:344-345`): `folded_this_run=None` means "continue if origin has it, else fresh", and a
    continued line is pushed without force (`:390`, `:401`);
  - `integrate._fold_candidates` (`integrate.py:158`) as the ONE definition of "carryable";
  - the missing-`gh` guard to copy: `merged.merged_head` (`merged.py:62-80`, guard at `:73-80`);
  - what `integrate._gone_branch` (`integrate.py:442`) already decides for a MERGED PR whose
    branch is gone: a head already on the line is skipped, a head on the base takes the base
    in, anything else raises. Under this brief that raise is just "not clean ⇒ hold";
  - `_runnable`'s existing `held` set (`flow.py:681-720`) as the way dependents are held.
  Carried ids must not later be reported by `integrate.unpublished(accepted, pushed=pushed)`
  as unpushed: keep them out of `accepted`, or count them as pushed.
- **Prior-art check (triage cycles):** merged history by path,
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/flow.py
  template/src/pdca_harness/integrate.py template/src/pdca_harness/merged.py`, turns up
  `69abaa1` (#597), `b21f248` (#593: append-only fold, `held_unpushed`, `stack-base-tip`), and
  `96c9704` / `389bf1a` (#469/#473 split adoption). None of them carries finished named ids or
  continues an earlier run's line. Open PRs on these paths: #639 (#591, batch-scoped line,
  needed here) and #638 (#590). Closed-unmerged PRs touching them: #598, #599, #600
  (auto-iterate / gate re-run / size signal, all unrelated). Earlier attempts at this issue:
  `results/issue_616/iteration-v1..v3` (rejected: fresh line plus a carry of any out-of-batch
  prerequisite) and `results/issue_646/iteration-v1..v4` (rejected: right approach, but a
  special case per host scenario, ending at 149 KB).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Re-plan note (replaces the iteration 1–4 carry-forwards)

Four builds were rejected. Each one added recovery code for one more combination of PR state
(open / closed / merged / replaced / no `pr_url`), branch state (deleted / force-pushed /
squash-merged) and what the earlier run's line holds, and the adversary found the next
combination every round. The cause was that the brief never fixed a policy for the non-clean
case. This brief fixes it: **carry only the clean case; everything else holds only that id's
dependents, with a reason, and the run goes on.** Do NOT rebuild the v2–v4 machinery: no PR
lookup by branch, no per-commit "vouch" of the line beyond the single check in criterion
(5), and no recovery path for any known limit. Still required from round 1: the lock is held
across the carry fold and tip read, and the re-gate runs under it. Both come from reusing the
in-run fold path. Expect the patch to be a fraction of v4's 149 KB. If the rule cannot be met
without a new special case, stop and say so in `build-notes.md` rather than invent one.

Plan-review response: the review (plan-advisory-plan-reviewer.md) raised 7 findings, and all 7
are addressed in place. (1) The invariant is narrowed: append-only across runs applies only to a
carried line, and a "when does a fold force-push?" rule is added under criterion (8). (2) The
hold outcomes are pinned down: an untrusted line or a red re-gate leaves the target out of
`folded_tips`, so the first in-run fold is today's fresh, forced fold. The (5) and new (8)
tests assert this with a wave-1 bundle. (3) The mechanism is chosen: one `fold` per target
with a new `skipped=` keyword, NOT one `fold` per id, because `integ_lock` would self-deadlock
(`integrate.py:213`). A carry red re-gate or a whole-target error holds the ids and does not
`break`. The carry seeds `folded_this_run` with origin's tip so `fold` continues without
force. (4) (5) wins over (4) when an earlier line holds a closed id's commits, and trust is
judged against state-clean heads. (5) Stranding `H` is now a known limit, and the
`publish.py` wording must keep the "re-drive" advice. (6) The test list is closed at 12 tests,
about 700 lines, with each remaining claim mapped to the existing suites or to review. (7) The
base risk (#639 still open) is written into the Ordering note for sign-off to accept. One
point for Do: when the carry seeds `folded_this_run`, a refusal from `fold` uses the message
"the tip this run's last fold pushed" (`integrate.py:383-388`). That is slightly wrong for a
carry; Do may reword it, and it changes no behaviour.
