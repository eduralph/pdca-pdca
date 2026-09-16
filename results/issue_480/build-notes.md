# Build notes — issue 480

## What changed

`template/src/pdca_harness/leaves.py`, target branch `eduralph/pdca-harness@main`,
base commit `6ba00bad8e9c7257dacfd4b87c54450ab7259bc9`:

- `do_plan` (`leaves.py:904-939`, was `:904-927`): before invoking the planner, snapshot
  the WHOLE bundle root by content hash (`_brief_snapshot(cfg)`, new helper at
  `leaves.py:3360-3368`) instead of only knowing about `d`. After the session, call
  `run_plan_advisory_batch(cfg, _fresh_plan_briefs(cfg, briefed_before))` instead of
  `run_plan_advisory(d, cfg)` — the same selection `do_plan_batch` already used
  (`leaves.py:1073-1075` pre-fix, `:1129-1133` pre-fix), so a `pdca split <id> --accept`
  run *inside* a single-bundle session is picked up: its new child bundles get reviewed,
  and the parent (now carrying `close-disposition`) does not, whether or not its own
  brief is still present.
- `do_plan_batch` (`leaves.py:1067-` region): replaced its inline `briefed_before = {...}`
  snapshot (old `:1073-1075`) with `_brief_snapshot(cfg)`, and its inline `fresh = sorted(...)`
  computation + call (old `:1129-1133`) with `run_plan_advisory_batch(cfg, _fresh_plan_briefs(cfg, briefed_before))`.
  Behaviourally identical to what was there — this is the factoring the brief calls
  for ("one selection rule shared by `do_plan` and `do_plan_batch`"), not a logic change
  on the batch path's happy path.
- Two new helpers next to `run_plan_advisory_batch`, per the brief's "confined to
  `do_plan`, `do_plan_batch` and `run_plan_advisory_batch` (plus any new helper it adds
  next to them)" ordering constraint:
  - `_brief_snapshot(cfg)` — the pre-session content-hash snapshot, factored out of what
    was inline in `do_plan_batch`.
  - `_fresh_plan_briefs(cfg, briefed_before)` — the post-session "authored or rewrote"
    diff, factored out of what was inline in `do_plan_batch`.
- `run_plan_advisory_batch` (`leaves.py:` the `reviewed = [...]` filter): added
  `and not (d / state.CLOSE_MARKER).exists()` to the existing
  `(d / "brief.md").exists() and not brief.is_placeholder(...)` filter. This is the
  single choke point both `do_plan` and `do_plan_batch` funnel bundle lists through, so
  putting the close-disposition guard here (rather than duplicating it in both callers)
  covers success criterion (b) on both Plan paths at once, and covers the case where a
  bundle's brief WAS rewritten this session but the same session also closed it (a
  content-hash diff alone would not exclude that bundle — see
  `test_terminal_bundle_is_never_reviewed_even_if_its_brief_changed`).

Nothing else in `leaves.py` was touched: no prompt string, no `handoff.session(...)`
block, no other function. `split.py`, `flow.py`, `_plan_revision_prompt` and
`split-lineage.json` handling are all untouched, per the brief's explicit out-of-scope
list.

## Why this shape, and what I ruled out

**Ruled out: following `split-lineage.json` to find children explicitly.** The brief
rules this out directly ("the content-hash selection makes it unnecessary") — and it
would also fork the single-bundle and batch paths onto two different selection
mechanisms instead of the one shared rule the brief asks for.

**Ruled out: keeping `run_plan_advisory(d, cfg)` in `do_plan` and just widening it
internally.** `run_plan_advisory` is a single-bundle convenience wrapper used directly
by ~15 existing tests in `test_plan_advisory.py` and 2 in `test_leaf_memory_cap.py`
(`run_plan_advisory(d, cfg)` == `run_plan_advisory_batch(cfg, [d])`, unchanged at
`leaves.py:3404-3406`/pre-fix `:3404-3406`). Widening it to scan the bundle root would
change its contract for every one of those callers, none of which expect a single-bundle
call to reach into siblings. `do_plan` instead calls `run_plan_advisory_batch` directly
with the freshly-computed list — `run_plan_advisory` itself is untouched, matching the
brief's three-function scope (it's not one of the three).

**Ruled out: putting the close-disposition guard only in `_fresh_plan_briefs`.** That
would leave `run_plan_advisory_batch` called directly (as several existing tests and, per
the brief's out-of-scope note, potentially other future callers do) still able to review
a terminal bundle if handed one. Putting the guard in `run_plan_advisory_batch`'s own
`reviewed` filter closes it at the one place both Plan paths — and any other caller —
funnel through, which is what "never reviewed on either Plan path" in the success
criterion asks for. Cost: one added clause (`and not (d / state.CLOSE_MARKER).exists()`)
on an existing list comprehension, vs. duplicating the same check in both `do_plan` and
`do_plan_batch` (two lines each) if it lived in `_fresh_plan_briefs` alone — smaller and
it can't drift between the two callers.

**Ruled out: fixing the split-after-sign-off / split-from-a-shell gap.** The brief
explicitly puts "children of a split accepted OUTSIDE any Plan session" out of scope
("a separate gap; note it in build-notes if seen, don't fix it here"). I did see it: a
`pdca split <id> --accept` run from a sign-off session or a bare shell never re-enters
`do_plan`/`do_plan_batch` at all (`flow.py:367-368`'s early return applies to a bundle
already materialised `PLANNED` regardless of how it got there), so neither this fix nor
the pre-existing code gives those children a plan-advisory pass. Not fixed here, per
scope.

## Refutation (the three required questions)

**(a) Genuine red?** Yes. I reverted `leaves.py` to the pre-fix `HEAD~1` version (base
commit `6ba00bad8e9...` at `origin/main`) with the new test file left in place, and ran:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_plan_advisory_split_children -v
```

Result: 3 of 4 sub-tests fail with real `AssertionError`s —
`test_shape1_parent_keeps_brief_children_reviewed_parent_is_not` (children got no
artifact — `False is not true : C1`), `test_shape2_parent_has_no_brief_children_still_reviewed`
(same, `C3`), and `test_terminal_bundle_is_never_reviewed_even_if_its_brief_changed` (the
terminal bundle got reviewed anyway — the list-equality assertion shows the two
unexpected artifact files). The fourth, `test_single_bundle_path_selects_like_the_batch_path`,
already passed pre-fix — it only exercises within-`d` freshness/placeholder selection,
which `do_plan` already got right before this fix; it stays in the suite as a regression
guard for success criterion (c), not as a defect-reproducing case. Then I restored the
fix and re-ran: all 4 pass, plus the full pre-existing `tests.test_plan_advisory` suite
(29 tests total across both files) — unchanged and still green.

**(b) Production path?** Yes. The test calls `leaves.do_plan` and
`leaves.run_plan_advisory_batch` directly — the exact functions the fix changes — with a
real `Config` and the real `_stub_plan`/`brief.is_placeholder`/`state.CLOSE_MARKER`
machinery; only the planner's own act of writing files is stood in for (via
`mock.patch.object(leaves, "_stub_plan", side_effect=...)`), which is unavoidable without
a live model session and is exactly the substitution the brief's own repro instruction
prescribes ("simulates the session by patching `leaves._stub_plan`").

**(c) Fixture includes the fault?** Yes. The fixture is built to reproduce the exact
defect shape from the brief's repro: a parent bundle whose (stubbed) planner session
writes new child bundles and marks the parent `close-disposition` mid-session — the real
`pdca split <id> --accept` outcome the brief describes, not a curated case that excludes
it. `test_terminal_bundle_is_never_reviewed_even_if_its_brief_changed` additionally
exercises the close-disposition guard on a bundle whose brief WAS rewritten (not just
unchanged), so the guard's own correctness doesn't hide behind the content-hash filter's.

## Test runner used

`bash engine/scripts/run-suite.sh` (via `PDCA_WORKTREE=<worktree> bash
engine/scripts/run-suite.sh` from the `pdca-pdca` root) — the T3 gate script named in
`pdca.toml`'s doctor row (`cmd = "test -d ../pdca-harness/tests && test -d
../pdca-harness/template/tests"`, hint pointing at this script). Both suites reported
`PDCA-EVIDENCE: root suite OK, driver suite OK` post-fix. I additionally ran the
narrower `python3 -m unittest tests.test_plan_advisory_split_children` /
`tests.test_plan_advisory` directly (same interpreter, same `PYTHONPATH=src`, no
container, no hand-rolled invocation beyond what the runner itself does) to get the
per-test pass/fail detail quoted above — that direct invocation mirrors exactly the
"offline driver suite (template/tests, PYTHONPATH=src)" step the runner script itself
performs (`engine/scripts/run-suite.sh:33-34`), not a separate ad-hoc runner.

## Formatter / commit hooks

No `.pre-commit-config.yaml`, no formatter config (`pyproject.toml` black/ruff section,
`.flake8`, etc.) and no local git hooks exist in the target worktree
(`git rev-parse --git-common-dir` → the primary checkout's `.git`, its `hooks/` holds
only the `*.sample` files Git ships by default). `CONTRIBUTING.md` names no formatter to
run. Nothing to run beyond the test suite above.

## Scope check against the ordering note

Brief's ordering note requires staying inside `do_plan`, `do_plan_batch`,
`run_plan_advisory_batch`, plus any new helper added next to them, and leaving every
prompt string and the two named `handoff.session(...)` blocks + their comments
untouched (pre-fix `:916-925` inside `do_plan`, `:1104-1117` inside `do_plan_batch`).
Confirmed: `git diff origin/main -- template/src/pdca_harness/leaves.py` touches only
those three functions plus the two new helpers `_brief_snapshot` / `_fresh_plan_briefs`,
placed immediately above `run_plan_advisory_batch`; the `handoff.session(...)` blocks in
both functions are byte-identical to `origin/main` (diffed separately to confirm — no
hunk overlaps either block).
