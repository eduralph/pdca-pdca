# Brief — issue 550 / plan-revision-pass-admits-the-bundles-checkouts

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** plan-revision-pass-admits-the-bundles-checkouts
- **Defect:** The plan-advisory revision pass spawns the planner with no workspace grant.
  `run_plan_advisory_batch` re-enters the planner at
  `template/src/pdca_harness/leaves.py:3710` —
  `_invoke(cfg.planner, cfg.root, _plan_revision_prompt(cfg, with_findings), cfg=cfg)` — with
  no `extra_argv`. Every other interactive spawn carries the #494 grant: `do_plan`
  (`leaves.py:1008-1010`, `_plan_grant`), `do_plan_batch` (`:1203-1205`, `_plan_grant`), and
  the sign-off / batch sign-off / Act / publish spawns (`:3751`, `:3803`, `:3901`, `:3971`,
  all `_bundle_grant`). So the one session whose whole job is to weigh findings written against
  the target source (`plan-advisory-*.md`, path:line citations) and re-check the brief's
  root-cause citation opens with the target checkout outside its workspace: the human gets the
  per-file approval prompts #494 removed everywhere else, and a hand-granted approval cannot
  stick (it lands in the untracked `settings.local.json`, which `--setting-sources project`
  drops). Opt-in path only: it runs when `[[leaves.plan_advisory]]` is configured, the
  reviews raised findings, and `cfg.planner.mode == "command"` (`leaves.py:3704`).
- **Success criterion:** With the patch, when `run_plan_advisory_batch` runs the revision pass
  on a planner leaf whose family has a grounding flag (claude → `--add-dir`), the planner spawn
  (i) admits, through that flag, exactly the deduplicated primary checkouts that the bundles
  in `with_findings` resolve to (one flag/value pair per distinct directory); (ii) admits
  **nothing** when none of those bundles' checkouts resolve on this host, even if the
  instance has other known targets (`[publisher.checkouts]` or other briefs' targets). A
  session that already has bundles never widens to the instance's other targets; that is
  the `_bundle_grant` rule at `leaves.py:830-841`. (iii) Nothing else about the spawn changes:
  cwd stays `cfg.root`, the prompt is byte-identical, a `generic`-family planner (no
  grounding flag) is spawned with no admission argv, and a revision that raises is still
  contained (the `try/except` at `:3709-3715`). Shown by the named test going red on the
  base (the spawn's `extra_argv` is `None`) and green with the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11 +
  git), in the target checkout Do gets. `template/tests/test_leaf_workspace_admission.py`
  already replaces `leaves._invoke` with a recorder of `extra_argv` (`:74-83`) and builds real
  sibling checkouts with `git init` (`:86-90`). A stub plan-advisory leaf
  (`{"id": "plan-reviewer", "mode": "stub", ...}`, the `_REVIEWER` shape at
  `template/tests/test_plan_advisory.py:26-30`) writes a `- NEEDS-HUMAN` line, which counts
  as a finding and triggers the revision pass on a command-mode planner. That is already
  proven by `test_plan_advisory.py:213-233` (`test_revision_pass_records_revised_true`). On
  the base the recorded revision spawn's `extra_argv` is `None`, so an assertion that it
  admits the bundle's checkout fails. Criterion (ii)'s negative only means something if the
  fixture has a non-empty known-target set (copy the pattern in
  `test_a_bundle_scoped_session_never_widens_to_the_known_targets`, `:279-312`, which proves
  the known set is non-empty through a Plan spawn before asserting the negative). Without
  that, "admits nothing" passes for the wrong reason.
- **Invariant to restore:** Every interactive leaf the driver spawns is admitted to the target
  checkouts its session is about, derived from the session's bundles and never widened
  beyond them. That covers all spawn sites, not only the six #494 enumerated. Source:
  internal project invariant (Tier C), the target's own written doctrine at
  `template/src/pdca_harness/leaves.py:813-841` (under- vs over-admission, and which grant
  each role may use). `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so
  no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here re-verified against it)
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** No ordering fields, on purpose. This instance's driver is still rendered
  v0.57.0 (`.copier-answers.yml`), so a batch run must stay one wave (a second wave stacks and
  hits target #474's false T3 red). #498 in the same batch also edits `leaves.py`, but only
  the planner-prompt text near `:1119`; this slice edits `:3710`, about 2,600 lines away, so
  the hunks merge cleanly in either order.
- **Surfaces:** data
- **Difficulty:** low — one call site in one production module (plus appended tests). It
  mirrors a grant the six sibling spawns already use.
- **Scope:** The revision-pass planner spawn in `run_plan_advisory_batch` is admitted to the
  checkouts of the bundles it revises, by the same rule as the other bundle-scoped sessions.
  Update the `test_leaf_workspace_admission.py` module docstring, which says "six" interactive
  spawns, so it names the seventh. / out of scope: the revision pass's lack of a
  `handoff.session` exit contract (a separate question); any change to `_bundle_grant`,
  `_plan_grant`, `_known_targets` or `_primary_checkout`; the plan-advisory reviewer's own
  sandbox and grounding (`_run_plan_advisory_sandboxed`); OS-level sandboxing of interactive
  leaves (#551); the revision prompt text.
- **Repro instruction:** On a clean checkout of `eduralph/pdca-harness@70ea12b`, from
  `template/`: read `src/pdca_harness/leaves.py:3700-3715` (no `extra_argv`) against
  `:1203-1205` and `:3751`. Then configure a `Config` with an interactive command-mode claude
  planner, `plan_advisory_leaves=[<stub reviewer>]`, and a bundle whose brief names
  `org/repo @ main` with `repo_checkouts={"org/repo": <a git-init'd dir>}`. Patch
  `leaves._invoke` to record kwargs and call `leaves.run_plan_advisory_batch(cfg, [d])`: the
  recorded revision spawn's `extra_argv` is `None`.
  `PYTHONPATH=src python3 -m unittest tests.test_leaf_workspace_admission` is green today.
- **External dependencies:** none — the base toolchain (Python ≥ 3.11, git) suffices; no
  vendor CLI is spawned (`_invoke` is replaced by a recorder).
- **Test file:** `template/tests/test_leaf_workspace_admission.py` (append; the issue asks for
  the test "alongside the #494 ones", and its fixture is exactly what this needs). The C4 gate
  (`engine/scripts/run-verify.sh`) runs every touched test module whole, reverts only the
  production hunks, and keeps the test hunks, so an appended test earns a real red. Import no
  new symbol at module level; the module already imports `leaves`, so drive the behavior
  through `leaves.run_plan_advisory_batch`. C5 (advisory) will say "patch adds no new test
  file — nothing to assert". That is expected for an append and is not a defect.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cue: mirror the bundle-scoped spawn at `leaves.py:3751`
  (`extra_argv=_bundle_grant([d], cfg, cfg.profile(cfg.signoff))`), with the revision's own
  bundle list (`with_findings`) and the planner's profile. Use `_bundle_grant`, not
  `_plan_grant`. Every bundle in `with_findings` has a non-placeholder brief by construction
  (`:3685-3687`), so this session is about known bundles, and the doctrine at `:830-841`
  reserves the known-targets fallback for a Plan session with nothing to resolve. That
  difference is what criterion (ii) tests.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 5
  -S"_bundle_grant" -- template/src/pdca_harness/leaves.py` → `304ff71 fix(leaves): stop
  prompting for the target checkout every session` (#494/PR #524, which introduced the grants
  and missed this site). Closed-unmerged PRs touching `leaves.py` /
  `test_leaf_workspace_admission.py` (the INTEGRATION §5 `gh pr list --state closed` filter):
  none. Open PRs on the target: none. Related open issue #551 (OS sandbox for interactive
  leaves) is a different mechanism and does not cover this.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
