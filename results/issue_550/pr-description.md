# Fix: the plan revision pass runs without access to your target checkout

## Summary
**User impact:** If you turn on the optional plan-advisory reviews, the planner
session that runs right after them — the one that revises the brief in light of what
the reviews found — starts without permission to read the repository it is supposed
to be reading. You get an approval prompt for every single file it opens, on the one
step that cannot run unattended, and approving by hand does not help: the next
session asks all over again. Every other interactive step stopped doing this a while
ago; this one kept doing it.

This PR gives that session the same access the others already get: the checkouts of
the bundles it is revising, and nothing beyond them.

Reported in [#550](https://github.com/eduralph/pdca-harness/issues/550).

## What to look at
One call in `run_plan_advisory_batch` (`template/src/pdca_harness/leaves.py`) — the
one that re-enters the planner after findings — now passes the workspace grant its
six sibling spawns already pass. Everything else about that call is untouched.

To see the old behaviour: configure a plan-advisory leaf and an interactive
command-mode planner, give a bundle a brief that names a repo you have checked out
locally, and run the Plan beat so the reviews raise a finding. Before this change the
revision session opens with the checkout outside its workspace and asks you to
approve it; after, it opens with the checkout already admitted.

Three tests in `template/tests/test_leaf_workspace_admission.py` record the arguments
the driver builds for that spawn, so you can read the expected behaviour directly.

## Root cause
When the workspace grants were introduced, six interactive spawns were enumerated and
fixed — Plan single and batch, sign-off single and batch, Act, publish — but the
planner is re-entered from a seventh place, the revision pass inside
`run_plan_advisory_batch`, and that call was left with no `extra_argv`. Its working
directory is the instance root, so the target checkout it is told to read sits
outside the workspace, and a manually granted permission lands in the operator's
untracked `.claude/settings.local.json`, which `--setting-sources project` drops by
design.

## Fix
`leaves.py:3710` now passes
`extra_argv=_bundle_grant(with_findings, cfg, cfg.profile(cfg.planner))`, mirroring
the sign-off spawn at `leaves.py:3750-3751`. `_bundle_grant` — not `_plan_grant` — is
the right helper here: the doctrine at `leaves.py:833-841` reserves the
known-targets fallback for a Plan session that has no brief yet, while this session
already has bundles (`with_findings` is non-empty by the guard at `leaves.py:3704`,
and each brief is non-placeholder by construction at `leaves.py:3685-3687`), so it
must never widen past them. The test module's docstring, which enumerated "six"
interactive spawns, now names the seventh.

## Verification
- **Claim:** the revision spawn admits, through the family's grounding flag, exactly
  the deduplicated primary checkouts the bundles in `with_findings` resolve to.
  - **Checked:** `template/src/pdca_harness/leaves.py:3710` on `main` (base `70ea12b`)
    passed no `extra_argv` at all, against the identical bundle-scoped grant at
    `:3750-3751` (sign-off) and `:3971` (publish).
  - **Test:** `template/tests/test_leaf_workspace_admission.py` —
    `test_plan_revision_admits_the_bundles_checkouts` fails pre-fix
    (`AssertionError: unexpectedly None : the spawn passed no extra_argv at all`) and
    passes post-fix.
- **Claim:** when none of those bundles' checkouts resolve on this host, the spawn
  admits nothing — it never falls back to the instance's other known targets.
  - **Checked:** the two-grant doctrine at `leaves.py:830-841` on `main`, which
    reserves the fallback for Plan's own spawns.
  - **Test:** `test_plan_revision_admits_nothing_when_its_bundles_checkout_is_absent`,
    which first proves through a real Plan spawn that the fixture's known-target set
    is non-empty, so the negative cannot pass for the wrong reason.
- **Claim:** nothing else about the spawn moves — same cwd, byte-identical prompt,
  and a planner family with no grounding flag still gets no admission arguments.
  - **Checked:** `leaves.py:3704-3715` on `main` — the containing `try`/`except` and
    the prompt construction are unchanged by the diff.
  - **Test:** the positive test asserts the recorded `workdir` and prompt equal the
    pre-change values; `test_plan_revision_generic_family_planner_spawns_with_no_admission`
    covers the flagless family.
- **Suites:** `PYTHONPATH=src python3 -m unittest tests.test_leaf_workspace_admission`
  from `template/` — 17/17 green with the fix, 1 failure with only the production hunk
  reverted. Full offline suite `python3 -m unittest discover -s tests` — 1924 tests, OK
  (2 pre-existing skips, unrelated).

Fixes #550
