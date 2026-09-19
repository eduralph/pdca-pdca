# Build notes — issue 550

## The change

`template/src/pdca_harness/leaves.py:3710-3711` — the plan-advisory revision spawn now
carries `extra_argv=_bundle_grant(with_findings, cfg, cfg.profile(cfg.planner))`, exactly
mirroring the sibling bundle-scoped spawn the brief cited at `leaves.py:3751`
(`extra_argv=_bundle_grant([d], cfg, cfg.profile(cfg.signoff))`). The only differences
from that pattern, both required by this call site's own shape:

- the bundle list is `with_findings` (the revision's own bundles — already resolved,
  non-placeholder briefs by construction, `leaves.py:3685-3687`), not `[d]`, because the
  revision covers every bundle a finding was raised against in one pass;
- the profile is `cfg.profile(cfg.planner)`, because this spawn's `leaf` argument is
  `cfg.planner`, not `cfg.signoff`.

Used `_bundle_grant`, not `_plan_grant` — the brief is explicit about this (Citations
expected) and the doctrine comment at `leaves.py:833-837` backs it: this session already
has bundles (`with_findings` is non-empty by the `if with_findings and ...` guard at
`leaves.py:3704`), so it is a "session that already knows what it is about" and must
never widen to `_known_targets`. `_plan_grant`'s fallback (`leaves.py:944`) is reserved
for Plan's own two spawns, which the brief's out-of-scope list also protects
(`_bundle_grant`/`_plan_grant`/`_known_targets`/`_primary_checkout` are explicitly
untouched).

Also updated the module docstring at `template/tests/test_leaf_workspace_admission.py:1-17`
per the brief's Scope note ("name the seventh") — it now says a seventh interactive spawn
exists (the revision pass) and explains which rule covers it (bundle-scoped, not Plan's
fallback).

## What I read

Brief only (`results/issue_550/brief.md`), plus the one cited peer callsite
(`leaves.py:3742-3753`, `run_signoff`, to copy `_bundle_grant`'s call shape) and the
surrounding doctrine block the brief itself quotes (`leaves.py:810-945`, already partly
reproduced in the brief text) to confirm `_bundle_grant` vs `_plan_grant` and to find
`_plan_revision_prompt` / `_bundle_targets` signatures. I also opened
`template/tests/test_leaf_workspace_admission.py` (the brief's named test file — this
is the test file I'm appending to, not a "peer callsite", so reading the whole module was
necessary to match its fixture conventions) and the `_REVIEWER` stub shape at
`template/tests/test_plan_advisory.py:26-30` (the brief cites this shape by name and
line range as what triggers a finding).

## What I ruled out

- **Changing `_bundle_grant`/`_plan_grant`/`_known_targets`/`_primary_checkout`** — out of
  scope by the brief. Not needed either: `_bundle_grant` already does exactly what this
  call site needs (strict, no fallback) once given the right bundle list and profile.
- **Adding `extra_argv` via `_plan_grant`** — would let the revision pass fall back to
  `_known_targets` when none of `with_findings`'s checkouts resolve, which is exactly the
  over-admission the brief's criterion (ii) forbids for a session that already has
  bundles. This is the wrong-but-locally-plausible shape the brief's citation cue warns
  against (Plan's other two spawns use `_plan_grant`, and a careless read of "this
  happens inside `do_plan`/`do_plan_batch`" could suggest reusing it).
- **A brand-new grant helper for the revision pass** — unnecessary: `_bundle_grant`'s
  contract ("a session that is ABOUT bundles", `leaves.py:925`) already matches a
  revision pass that runs over `with_findings`, a list of already-resolved, non-placeholder
  bundles.

## Refutation checklist

**(a) Genuine red?** Yes. With the production hunk reverted (`git apply -R` on just the
`leaves.py` hunk, test hunk kept — the same thing C4 (`run-verify.sh`) does), running
`PYTHONPATH=src python3 -m unittest tests.test_leaf_workspace_admission` from `template/`
fails exactly one test:
`test_plan_revision_admits_the_bundles_checkouts` — `AssertionError: unexpectedly None :
the spawn passed no extra_argv at all`. Re-applying the hunk turns all 17 tests in the
module green. (The two other new tests — the criterion-(ii) negative and the
generic-family negative — pass on both legs, which is expected: they assert an ABSENCE
that already holds pre-fix; only the positive assertion is what the fix changes. The
brief's own falsifiability section makes the same point about criterion (i) being the
one that reaches red.)

**(b) Production path?** Yes. The test drives `leaves.run_plan_advisory_batch` directly
(no copy/mock of it), which is the exact function `_invoke`'s new `extra_argv=` argument
lives inside. `leaves._invoke` itself is replaced by a recorder (the module's existing
`setUp` fixture, unchanged in shape — I only added a `"prompt"` key to what it records),
which is the documented, pre-existing pattern this whole test module uses to keep the
suite offline (no vendor CLI spawned) while still exercising the harness's own argv
construction — the thing under test.

**(c) Fixture includes the fault?** Yes. The positive test
(`test_plan_revision_admits_the_bundles_checkouts`) builds a REAL git-init'd sibling
checkout (`self._checkout("repo")`, `setUp`) and a real, non-placeholder brief naming it
(`self._bundle`), so `_bundle_targets`/`_primary_checkout` actually resolve something —
an empty-fixture version of this test would pass on the base for the wrong reason (nothing
to admit either way). The negative test
(`test_plan_revision_admits_nothing_when_its_bundles_checkout_is_absent`) mirrors
`test_a_bundle_scoped_session_never_widens_to_the_known_targets` exactly as the brief's
falsifiability section instructs: it first proves the instance's known-target set is
non-empty (`checkouts={"org/repo": str(self.target)}`, proven through a real `do_plan`
spawn before the assertion), so the fixture cannot make the negative pass by having
nothing to fall back to.

## Test run

- `cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_workspace_admission`
  — 17/17 green with the fix.
- Same command with only the `leaves.py` hunk reverted — 1 failure (the new positive
  test), the rest still pass.
- `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` — 1924 tests,
  OK (skipped=2, pre-existing/unrelated — a worktree/network-shaped skip, not touched by
  this change).
- `pdca-pdca gates 550` from the instance root — overall gating: **pass**. C4-verify
  (the red→green correctness gate) reports "C4 PASS — red without the fix, green with
  it", matching the manual run above. T2/T3/host-ci-docs also pass; T4 defers to publish
  (pr-description.md not drafted yet, expected at this stage).

## Formatter / commit hooks

No formatter, linter, or pre-commit config exists in the target repo for Python sources
(`CONTRIBUTING.md:24-33` only names the offline unittest suites as the verification
step; no `.pre-commit-config.yaml`, `ruff.toml`, `.flake8`, or `pyproject.toml`
lint/format section under `template/`). Matched the surrounding code's style (line
length, `f"..."` string joins, trailing-comma-free call wrapping) by eye against the
sibling spawns.

## Not done / deferred

Nothing. The change is one call site plus the appended tests, matching the brief's
stated difficulty ("low — one call site … mirrors a grant the six sibling spawns already
use").
