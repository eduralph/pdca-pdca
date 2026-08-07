# Brief — issue 411 / merge-mode-wrong-base-fail-closed

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** merge-mode-wrong-base-fail-closed
- **Defect:** In plain terms: with auto-merge turned on, a fix can be merged into another
  fix's branch instead of the real target branch — and nothing says so. The wave reports
  success, the next wave builds on a target branch that never received the work, and the
  change is quietly missing from where it was supposed to land.

  How it happens. When `[driver].wave_mode = "merge"`, the driver merges each accepted
  bundle's recorded PR wherever that PR happens to point
  (`template/src/pdca_harness/merge.py:59, 82-89`). It checks that the bundle is COMPLETE,
  has a patch, and has a recorded PR URL (`:46-57`) — it never looks at what branch the PR
  targets. That branch was decided earlier, at publish time
  (`pr_base = stack_branch if (stack_branch and own_repo) else base`,
  `template/src/pdca_harness/publish.py:257`, used at `gh pr create --base`, `:290`). Two
  separate routes point it at another bundle's branch:

  - **Route 1 — the old `Stacks on:` wiring.** `publish._stack_base_branch`
    (`publish.py:615-630`) uses the wave integration branch if one was recorded, and
    otherwise falls back to **the parent bundle's own fix branch**, read from that parent's
    `publish.json` (`:626-630`). In merge mode no integration branch is ever recorded:
    `flow` only fills `integ` on the stack path via `integrate.fold` (`flow.py:806-820`),
    while the merge path (`:807-811`) fills nothing, so `_point_at_integration`
    (`flow.py:568-580`) clears the marker for every bundle. The fallback is therefore live,
    and a dependent's PR opens against — then gets merged into — its predecessor's branch.
  - **Route 2 — a brief whose `Repo + branch target` names a predecessor's branch.** That is
    the documented practice for stack-mode chains. `publish._resolve_target`
    (`publish.py:531-544`) hands that branch back as the bundle's base, so the PR opens
    against it and the merge lands there.

  **Worth knowing: the issue's own suggested fix only covers route 1.** It proposes
  comparing the PR's base against the bundle's resolved target base and stopping on a
  mismatch. On route 2 those two are the *same string* — the brief's target base genuinely
  *is* the predecessor's branch — so the comparison sees nothing wrong and stays silent.
  That is exactly the situation the issue describes in its own real-world section
  (wyrd-pdca's re-slicing plan told every chained brief to name the previous slice's
  branch). A guard built to the issue's literal wording would ship, pass review, and still
  let route 2 through. The criterion below covers both.

- **Success criterion:** On `eduralph/pdca-harness` @ `main`, new tests appended to
  `template/tests/test_publish_slice.py` fail before the change and pass after it, checking
  that when `[driver].wave_mode = "merge"`, `publish.publish` **refuses** — returns non-zero,
  opens no PR, pushes nothing, and prints a message naming both the branch the PR would have
  targeted and the target base it should have used — in both routes:
  1. the PR base would come from the old `Stacks on:` fallback (route 1);
  2. the PR base equals the bundle's own resolved target base, but that base is a branch
     another bundle in this batch produced (route 2).

  Plus the two things that must not change: under the default `wave_mode = "stack"` a
  stacked PR still chains onto its parent branch exactly as today, and an ordinary bundle
  targeting a real base still publishes normally in either mode.

  All of it is provable by the C4 gate from the patch alone, offline, with git and `gh`
  stubbed.

- **Falsifiability:** Do is pointed at this instance's C4 gate
  (`engine/scripts/run-verify.sh` in pdca-pdca), which takes the patch's production changes
  back out and leaves the new tests in place (`:72-81`), then runs
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_publish_slice` (`:55-65`).
  With `publish.py` reverted, the wrong-base cases publish happily and `publish.publish`
  returns 0, so the new assertions fail — a real red. Green with the patch.

  The red is earned by a **failing assertion** on a return code from an existing public
  function (`publish.publish`), not by an import or attribute error. That matters here: the
  gate judging this bundle scores an import error as a legitimate red (see #434), so a test
  that only fails because a new symbol is missing would prove nothing.

  Checked against the gates this project actually runs (`pdca.toml` `[[gates.checks]]`):
  `C4-verify` is the only gating bundle check. `template/tests/test_publish_slice.py` is
  standard-library only, stubs git/`gh`/leaves and drives `publish.publish(dry_run=True)`
  (see its module docstring: "No Claude, no git, no network"), and sits behind no feature
  flag, so it cannot quietly run zero tests and report success. **Base:** the scheduler puts
  this bundle in **wave 0** (verified — see Ordering note), so neither `$PDCA_BASE` nor
  `$PDCA_VERIFY_BASE` is exported and the gate's base is simply the brief's target,
  `origin/main`, which the patch applies to cleanly. (The precedence
  `$PDCA_BASE > $PDCA_VERIFY_BASE > $PDCA_BRIEF_BASE` is published at
  `template/engine/scripts/run-verify.sh:12-34`; this instance's gate needs no base handling
  of its own, because the driver rebuilds base + patch in `$PDCA_WORKTREE` before any gate
  runs — `engine/scripts/run-verify.sh:4-10`.)

- **Invariant to restore:** *Work lands on the shared target base, or the run stops and says
  so.* A bundle's contribution only ever goes to a base that exists independently of this
  run — never to a branch the run itself produced — and a destination that cannot be shown
  to be that base is a loud, fail-closed refusal naming both branches, never a silent
  success. Stated for any bundle and any of the ways a PR's base can get set, not for the
  `Stacks on:` fallback, which is only one of the two routes into it.

  Sources (all internal to this repo — `docs/principles.md` §5 Tier C; its §6 category table
  is empty for this instance, so this is reference material, not a gated category):
  - `template/src/pdca_harness/merge.py:32-33` — `merge_wave`'s own stated contract: "Merge
    each accepted bundle's PR **into its base**, then fetch the base";
  - `template/src/pdca_harness/publish.py:229-233` — publish already refuses, loudly and
    fail-closed, when a stacked bundle's parent has not published a branch yet; this is the
    same class of refusal;
  - `template/src/pdca_harness/publish.py:531-544` (#235/#262/#387) — the "one parse" rule:
    a bundle's base comes from `publish._resolve_target`, never a second re-derivation.

- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** (none)
- **Conflicts with:** 420
- **Ordering note:** No dependency in either direction — #411 and #420 are independent fixes
  and neither needs the other's result. They are declared conflicting (**confirmed by the
  human**) because both add user-facing driver documentation to the **same file**,
  `docs/07-crosscutting.md`: this bundle in §Waves in execution (`:333-358`, where
  `[driver].wave_mode` is documented), #420 in §Parallel lanes & housekeeping (`:300-332`,
  `:359-380`). Two patches editing adjacent sections of one file is the case the wave
  scheduler exists to separate, so they must not be built on the same base. Which one goes
  first is the scheduler's call, not the brief's; ran the real scheduler over all three
  bundles (`waves.compute_waves`): **wave 0 = {411, 434}, wave 1 = {420}** — this bundle is
  in wave 0, and #420 builds on the folded result. Code files do not overlap: this bundle
  owns `template/src/pdca_harness/publish.py` and `template/tests/test_publish_slice.py`;
  #420 owns `template/src/pdca_harness/{leaves,config}.py` + `template/pdca.toml.jinja`;
  #434 owns `template/engine/**`.
- **Surfaces:** data
- **Difficulty:** medium — one function on one opt-in path (`publish.publish`, and only when
  `wave_mode = "merge"`), but it has to read data belonging to *other* bundles (their
  `publish.json` branch records) and it sits next to two existing publish routes — the
  `Onto branch` path and the stacked-PR path — that must keep working untouched. Two to
  three files.
- **Scope:** Make merge mode refuse to publish a PR that would land anywhere other than a
  base existing independently of this run, covering **both** routes in Defect above (a base
  that differs from the bundle's own resolved target, *and* a resolved target that is itself
  another batch bundle's produced branch). The refusal returns non-zero, pushes nothing,
  opens no PR, and names both branches.

  **The refusal belongs at publish time, not at merge time** (the human's call, recorded
  here so Do does not re-litigate it): the publisher is an interactive leaf with a person
  present who can correct the brief's branch target on the spot, whereas the wave merge runs
  unattended in the middle of a flow — a stop there is a stop nobody is at. Refusing to
  create the wrong-based PR also removes the cause rather than guarding the symptom: if the
  PR is never opened against another bundle's branch, the merge has nothing wrong to merge.

  Under `wave_mode = "merge"` the old `Stacks on:` branch wiring has no business choosing a
  PR base at all — wave order carries dependencies there — so a bundle reaching publish in
  merge mode with a stacked-PR base is one of the cases that gets refused.

  The refusal must behave like the ones already there: non-zero return, a clear message on
  stderr, nothing pushed.

  Out of scope: `merge.py` is not changed (see the known limitation below); `wave_mode =
  "stack"` — the default — is untouched in every respect, including the stacked-PR base
  chaining that is correct there; removing the legacy `Stacks on:` field or its stack-mode
  fallback (deprecating it is a separate decision); teaching the planner or `brief.md`
  anything new (this is a driver-side guard, and the instance-side documentation was already
  fixed in wyrd-pdca); repairing or retargeting a wrongly-based PR automatically — the
  contract is refuse, not self-heal.

  **Known limitation, accepted at Plan.** Because the refusal sits at publish time, it
  covers PRs this run publishes — which is the normal case, since `flow` publishes a wave
  and then merges it inside the same loop (`flow.py:764-797` then `:807`), and it is the
  reported scenario. It does **not** cover a PR published by an *earlier* run (for example
  under stack mode, before the project switched to merge mode) that a later merge-mode run
  then merges: that PR already exists with the wrong base and never passes through publish
  again. Narrower than the main case, but real. Left out deliberately rather than
  overlooked; raise it at sign-off if you want a merge-time backstop as well, and it becomes
  a follow-up issue.

- **Repro instruction:** On a clean worktree of `origin/main` in `../pdca-harness`. The
  failure is a silent success, so the repro is a code path; the executable form is the test
  named below.
  1. `git -C ../pdca-harness show origin/main:template/src/pdca_harness/publish.py | sed -n '224,258p'`
     → `stack_branch` is resolved and becomes `pr_base` with no check on what it is, and no
     awareness of `wave_mode`.
  2. `git -C ../pdca-harness show origin/main:template/src/pdca_harness/publish.py | sed -n '615,631p'`
     → `_stack_base_branch` falls back to the parent bundle's fix branch.
  3. `git -C ../pdca-harness show origin/main:template/src/pdca_harness/flow.py | sed -n '800,815p'`
     and `| sed -n '568,581p'` → in merge mode `integ` is never filled, so every bundle gets
     `clear_stack_base` and that fallback is the only thing left deciding the base.
  4. `git -C ../pdca-harness show origin/main:template/src/pdca_harness/merge.py | sed -n '42,96p'`
     → and merge then merges whatever that produced, without ever looking at the base.
  5. Offline demonstration (what the new tests encode): with `wave_mode = "merge"`, a bundle
     whose brief says `- **Stacks on:** PARENT` and whose parent published branch
     `fix/PARENT-my-fix` publishes today with `--base fix/PARENT-my-fix` and returns 0 —
     see the existing `test_own_repo_stacked_pr_chains_onto_the_parent_branch`
     (`template/tests/test_publish_slice.py:402-408`), which asserts exactly that and must
     keep passing in **stack** mode.
- **External dependencies:** none
  (git, the GitHub CLI and the model leaves are all stubbed in
  `template/tests/test_publish_slice.py` — module docstring: "No Claude, no git, no
  network" — so nothing beyond the base toolchain, python3 + git, is needed to build or to
  move the criterion from red to green. Do MUST NOT write a test that needs a real GitHub
  repo, a real PR, or merge rights.)
- **Test file:** `template/tests/test_publish_slice.py` — **appended** to the existing
  suite. It already owns publish's refusal behaviour and carries the fixtures this needs:
  `_cfg`, `_bundle`, `_FIX_BRIEF` and the stubbed git/`gh`. Note `_stacked_dry_run`
  (`:377-390`) asserts `rc == 0` inside itself, so it is a model to copy for the setup, not
  a helper the refusal tests can call unchanged. Also note the suite never sets `wave_mode`,
  so every existing test runs in the default `"stack"` mode and is unaffected by a
  merge-mode-only refusal. Appending earns a real red under
  this instance's C4 gate, which takes production changes back out but keeps every test
  (`engine/scripts/run-verify.sh:72-81`) — checked, not assumed. The gate runs the file as
  `tests.test_publish_slice` from `template/`, so **every** existing test in it must still
  pass with the patch applied (`:67-68` fails the bundle if the green run is red) — in
  particular the stack-mode ones listed below.
- **Citations expected:** Do must cite path:line on the target base for every change.
  Places to look at (Do MAY open these):
  - **`template/src/pdca_harness/publish.py:229-233`** — **copy this refusal's shape.** It is
    publish's existing fail-closed stop (`Stacks on` a prereq that has not published):
    message on stderr naming the bundle and the problem, `return 1`, nothing pushed. Put the
    new refusal in the same place in the flow — after the target is resolved, before any
    branch/push/PR work — and in the same voice.
  - **`template/tests/test_publish_slice.py:410-420`
    (`test_stacked_pr_without_published_parent_errors`)** — **copy this test's shape**: set
    up the bundle, call `publish.publish(..., dry_run=True)`, assert `rc == 1` and assert the
    message. The new tests are the same thing with `cfg.wave_mode = "merge"`.
  - **`template/tests/test_publish_slice.py:392-408`** — the two stack-mode behaviours that
    must keep working unchanged (`test_fork_stacked_pr_targets_upstream_base_with_cumulative_diff`,
    `test_own_repo_stacked_pr_chains_onto_the_parent_branch`), and `_stacked_dry_run` at
    `:377-390` — copy its setup (a parent bundle with a `publish.json` branch, a `Stacks on:`
    dependent), but not the helper itself: it asserts `rc == 0`.
  - `template/src/pdca_harness/publish.py:531-544` (`_resolve_target`) — use this accessor
    for the bundle's own target base; never write a second parse of `brief.md`. Its docstring
    says why (#235, #262, #387).
  - `template/src/pdca_harness/publish.py:364-377` — the `publish.json` record other bundles
    leave behind: `mode` (`"stacked-pr"` / `"new-pr"`), `branch`, `base`, `repo`,
    `stacks_on`. Everything route 2 needs to recognise "that base is a branch we produced" is
    here, offline.
  - `template/src/pdca_harness/publish.py:615-630` (`_stack_base_branch`) — where route 1
    comes from.
  - `template/src/pdca_harness/flow.py:568-580` and `:806-811` — the proof that merge mode
    never records an integration branch, i.e. that the fallback is live there.
- **Prior-art check (triage cycles):** Searched by affected file path and by keyword.
  `git -C ../pdca-harness log --oneline origin/main -n 15 -- template/src/pdca_harness/merge.py
  template/src/pdca_harness/publish.py` → 15 commits; the nearest are `126db1f` (#279, ready
  a non-final wave's PR before merging) and `9ecbb01` (`pdca record`), neither of which
  validates a PR base. Tracker
  (`gh search issues --repo eduralph/pdca-harness "Stacks on" / "merge mode base"`): the
  neighbours are all **closed** and complementary — #147 (waves), #123 (auto-stacked chains,
  where the fallback came from), #186 (`Depends on (merged)` merge gate), #171 (archived
  prereqs), #235/#262/#387 (one-parse base resolution). Nothing open duplicates this, and
  there are no open PRs on the repo (`gh pr list` → empty). Not previously proposed and
  rejected: getwyrd/wyrd-pdca#198 switched a live batch to merge mode and the hazard was
  caught in review before any run; the instance docs were fixed there, and this is the same
  fix routed upstream.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
