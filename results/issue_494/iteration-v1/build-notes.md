# Build notes — issue 494 / interactive-leaves-are-admitted-to-what-they-must-read

## What I built

A single new helper, `leaves._target_grant(bundles, cfg, profile)`
(`template/src/pdca_harness/leaves.py:2006-2036`), and one call at each of the five
interactive-leaf spawn sites the brief names:

- `do_plan` — `leaves.py:782-784`
- `run_signoff` — `leaves.py:3296` (was `:3261` pre-patch)
- `run_signoff_batch` — `leaves.py:3344-3345` (was `:3308`)
- `run_act` — `leaves.py:3437-3438` (was `:3400`)
- `run_publish` — `leaves.py:3504` (was `:3465-3466`)

`_target_grant` does exactly what the reviewer's own grant already does
(`leaves.py:2495-2500`, cited in the brief) — generalized from one bundle to a list:
for each bundle it calls `_reviewer_target(d, cfg)` (`leaves.py:1972-2002`, **reused,
not re-derived**, per the brief's citation), which resolves the per-cycle worktree
when one exists, else the sibling checkout via `publish._resolve_target` /
`_checkout_path`. Distinct resolved checkouts are deduped in encounter order and each
is admitted as `[profile.grounding_flag, str(path)]` — skipped entirely when the
profile has no grounding flag (`generic`), so that spawn is byte-for-byte unchanged
(criterion iii). `run_publish` reuses the `profile` it already computes at
`leaves.py:3459` rather than resolving it twice.

## Why this shape, not another

**Composition, not invention.** The brief is explicit that this is a composition
slice — the headless leaves already solve exactly this problem
(`leaves.py:1802/1816` for Do, `:2499-2500` for the reviewer). I did not invent a
second mechanism (e.g. writing `.claude/settings.local.json` entries, or a bespoke
per-leaf directory list) — I reused the reviewer's own `_reviewer_target` resolution
and its conditional-grant shape verbatim, applied to five more call sites. The diff
is small (48 lines in `leaves.py`) because the resolution and the grounding-flag
convention already existed; the only new code is the loop that applies it to a list
of bundles instead of one.

**Rejected: re-deriving target resolution per call site.** I considered inlining
`publish._resolve_target(d)` + `_checkout_path(cfg, repo_spec)` directly at each of
the five sites (skipping `_reviewer_target`). Cost: that duplicates the
worktree-vs-sibling-checkout preference logic (`leaves.py:1985-2002`, ~15 lines) five
times, and drops the "ground on the same base the gates ran against" property the
reviewer's version already has — worse than reuse for the same effort, so I kept the
shared function.

**Rejected: a single per-bundle helper that only ever takes one `Path`.** Batch
sign-off (`SIGNOFF_BATCH_SIZE`, `flow.py:73-75`) and Act (`covered`, a snapshot of
every frozen bundle) both cover *several* bundles in one session, and the Success
criterion says "checkout(**s**)" / "bundle(**s**)" explicitly. A single-bundle
signature would have needed a second wrapper for the two batch call sites — more
code, and a second place the same "dedupe, admit each once" logic could drift from
the first. `_target_grant(bundles: list[Path], …)` takes the list directly; the
four single-bundle call sites just pass `[d]`.

**do_plan's real-world grant is usually empty, and that's correct, not a bug.**
`flow._plan_if_unplanned` (`flow.py:354-362`) only calls `do_plan` when
`state.state(d) == state.UNPLANNED` — i.e. `brief.md` does not exist yet (or is an
unfilled placeholder, `state.py:202-222`). `_reviewer_target` → `publish._resolve_target`
reads `d/brief.md`'s "Repo + branch target" field; with no brief, `FileNotFoundError`
is caught (both in `worktree._target` and in `_reviewer_target`'s own `try/except`,
`leaves.py:1988-2002`) and `None` is returned, so `_target_grant` returns `[]` and the
planner's spawn stays byte-identical to today. This is exactly what criterion (iii)
"never faked" and the invariant's "nothing wider" demand — there being nothing the
*config* resolves yet is not a case to special-case around; it degrades to the
existing behaviour for free. `test_planner_with_no_resolvable_target_admits_nothing`
asserts this directly (the config-can't-name-a-target case), and
`test_planner_admits_the_resolved_target_checkout` exercises the mechanism `do_plan`
itself carries once a target *is* resolvable (`do_plan` has no internal guard against
being called with an existing `brief.md` — only the flow-level trigger does — so this
is a legitimate direct call, not a fabricated one; see (b) below).

**Out of scope, left untouched, per the brief's own scope line:**
`do_plan_batch` (`leaves.py:956-971`) and the plan-advisory revision invoke
(`leaves.py:3232`, unchanged numbering) are both planner call sites but are **not**
among the five cited (`:782-783`, `:3261`, `:3308`, `:3400`, `:3465-3466`), and the
Falsifiability section's repro instruction (step 1) lists exactly those five. I did
not touch them.

## The three questions

**(a) Genuine red?** Yes — verified directly: `git stash push -- template/src/pdca_harness/leaves.py`
(reverting only the production hunk, keeping the new test), then
`cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_workspace_admission -v`
→ all 8 cases **FAIL** (not error/import-fail — the module loads fine since the test
never imports `_target_grant` by name, it only calls `leaves.do_plan` /
`run_signoff` / `run_signoff_batch` / `run_publish` / `run_act` and inspects the
captured `extra_argv`, which is `None` pre-fix vs. the expected list). `git stash pop`
restored the fix; the same run is green (8/8 `ok`).

**(b) Production path?** Yes. Every test calls the real driver functions
(`leaves.do_plan`, `leaves.run_signoff`, `leaves.run_signoff_batch`, `leaves.run_publish`,
`leaves.run_act`) exactly as `flow.py` calls them — no reimplementation of the admission
logic in the test. The only substitution is `leaves._invoke` (the subprocess-spawning
boundary — this project's own established pattern, mirrored from
`template/tests/test_do_confine.py:90-106`), which is necessary because a real spawn
would try to exec `claude`/`gh`/etc; the code under test (`_target_grant` and its five
callers) runs unmodified and is what the test's assertions are against. For
`test_act_admits_the_resolved_target_checkouts` I also substitute
`leaves.act_mod.frozen_bundles` (a collaborator that decides *which* bundles Act
reviews — reaching real `COMPLETE` state needs a fully signed-off `SUMMARY.md` §9,
unrelated to workspace admission); `run_act`'s own admission call
(`_target_grant(covered, cfg, cfg.profile(cfg.act))`, the code this brief changes)
still runs for real against the substituted `covered` list.

**(c) Fixture includes the fault?** Yes. Every positive test builds a bundle whose
`brief.md` names a real "Repo + branch target" resolving (via `cfg.repo_checkouts`) to
an actual on-disk git checkout outside `cfg.root` — the exact shape the defect
describes (a target the config names but the leaf's cwd cannot reach). The negative
tests (`test_planner_with_no_resolvable_target_admits_nothing`,
`test_generic_family_spawn_is_byte_identical`) and the "config names two checkouts,
only one is this bundle's target" shape in every positive test (an `org/other`
checkout configured but never admitted) assert criterion (ii)/(iii) rather than
assuming them — a fixture that only ever configured *one* checkout could not have
caught an over-admitting fix (e.g. one that granted every configured checkout, not
just the resolved one).

## Manual verification (not gate-observable, per the brief's Falsifiability note)

The brief itself notes Claude Code's prompting behaviour (whether the human is asked
to re-approve a read) is not mechanically observable and is deliberately supplementary:
this cycle's own sign-off/publish sessions read `../pdca-harness` and will show it
directly, and `pdca-pdca try 494` gives a patched worktree to check by hand.
