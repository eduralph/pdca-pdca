# Build notes — issue 629 / hold-conflicts-with-partner-of-unpushed-bundle

Target: `eduralph/pdca-harness` `main` @ `b5f5c29`. Worktree: `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l1`). Line numbers below are post-patch unless
marked "base".

## What changed

1. `template/src/pdca_harness/flow.py:681-686` — `_runnable` takes two new keyword args:
   `unpushed` (the run's `held_unpushed`) and `conflicts` (a symmetric name → names map).
   The defaults (`frozenset()`, `None`) keep every other caller unchanged (the #646 carry at
   base `flow.py:2149` passes `held=` only, and existing tests call `_runnable(cfg, [d], {...})`).
2. `flow.py:723-728` — per wave bundle, `partners = conflicts[d.name] ∩ unpushed`.
3. `flow.py:776-783` — if any partners, print ONE new line (who is held, by what, why, what
   to do — the shape of the #647 line at `flow.py:766-772`, own wording, never the word
   "prerequisite") and leave the bundle out of `runnable`. Its own dependents then cascade
   through the existing not-COMPLETE check (base `flow.py:731-733`), which is criterion (d).
4. `flow.py:2181-2187` — the wave loop passes `unpushed=held_unpushed` and
   `conflicts=waves.conflict_map(cfg, bundles)`, built from the LIVE `bundles` list on each
   wave (adoption appends to it in place, `flow.py:2570` / filters it at `flow.py:1704`), and
   only when `held_unpushed` is non-empty, so the common case reads no extra briefs.
   Reuses `waves.conflict_map` (`waves.py:136-153`) as the brief asks: symmetric, restricted
   to the bundles passed in, so `held_finished` ids (not in the drive set) never match.
5. `flow.py:2310-2314` — the announcement now says "bundles that depend on it or are its
   `Conflicts with` partners are held this run" (criterion (e)).
6. `docs/07-crosscutting.md:672-675` — "holds only the bundles that depend on it" now
   includes `Conflicts with` partners and says why.
7. `template/PCDA/quality-cycle/09-parallel-lanes.md:69` — the same sentence, word for word,
   is in the shipped reference model. Not named in the brief's Scope, but leaving it would
   ship a statement the code now contradicts. One-clause edit. If the human wants the patch
   strictly to the brief's file list, drop this hunk; nothing else depends on it.

## Test — `template/tests/test_flow_conflict_partner_hold.py`

Copied the stub set of `test_flow_out_of_batch_prereq_hold.py` (config, `_brief`, `gh` stub,
`_run` via `flow.flow_ids`). Differences, each for a reason:

- `_drive_wave` (`:94`) accepts each bundle (non-empty `patch.diff`, `check-gates.json`,
  SUMMARY with `accept` in §9) as the brief requires.
- Each bundle's patch adds its own file (`_patch(name)`). With one shared `p.txt` the run
  prints an "undeclared conflict" warning containing "`Conflicts with`", which polluted the
  stderr checks.
- `_publish` (`:104`) writes a `publish.json` with a branch and returns True, or returns
  False for `issue_701`. `integrate.unpublished` needs the branch on record, not only the
  True return (`integrate.py:172-182`).
- `flow._fold_lines` is stubbed to return `({}, {}, [])` (`:122`). The temp dir has no git
  checkout; pre-fix, a pushed CJ makes the real fold stop the run ("checkout not found"),
  which would hide criterion (d)'s pre-fix behaviour. The fold is not the code under test:
  the hold is decided in `_runnable` before any fold, and post-fix CA is left out of the
  fold's input by production code (`flow.py:2319`). In the main case post-fix, no bundle
  with a target pushed, so the real fold would have nothing to merge anyway.

Cases: (1) CA unpushed → criteria (a)–(e); (2) control: CA pushed → all five built and
COMPLETE, no `Conflicts with` text on stderr ("Unchanged" clause).

## Runs

- Pre-fix (`cd template && PYTHONPATH=src timeout 300 python3 -m unittest
  tests.test_flow_conflict_partner_hold`): case 1 FAIL — `'issue_702' unexpectedly found in
  ['issue_701', 'issue_704', 'issue_702', 'issue_703', 'issue_705']`; case 2 OK.
- Post-fix: both OK.
- C4 gate, the project's own `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` set:
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0.
- Full offline driver suite (`cd template && PYTHONPATH=src python3 -m unittest discover -s
  tests`): `Ran 2371 tests … OK (skipped=2)`.
- `docs/publishing/tools/lint_docs.py`: OK. `render_site.py --check`: link audit OK.
  (That render wrote an untracked `.render-check/` dir into the worktree; it is not in the
  patch. Left for the harness to reclaim.)
- No pre-commit config or Python formatter is set up in the target (no
  `.pre-commit-config.yaml`; CI runs only docs lint, site render and the root suites). New
  lines are ≤ 100 chars, matching the file; the three >100 lines in `flow.py` (211, 2366,
  2555) are pre-existing.

## Refute-your-own-test

- **(a) Genuine red?** Yes. With only the production hunks reverted (C4's red leg, and my
  own pre-fix run), case 1 fails at `assertNotIn("issue_702", self.built)` — CJ is built in
  wave 1, the exact defect. Case 2 stays green, as it should (it pins unchanged behaviour).
- **(b) Production path?** Yes. The test goes through `flow.flow_ids` → `_drive_and_act` →
  the real `waves.compute_waves`, the real `held_unpushed` logic, the real
  `integrate.unpublished`, the real `waves.conflict_map` and the real `_runnable`. Stubbed:
  the build leaf, `_publish_bundle`'s result, `draft_texts`, `_fold_lines` and `gh` — all
  either named by the brief or outside the changed code.
- **(c) Fixture includes the fault?** Yes. CA is a targeted, accepted bundle whose publish
  returns False and records no branch — exactly the #593 "pushed no branch" case — and CJ
  declares `Conflicts with: 701`, so `compute_waves` puts it in wave 1. The pre-fix stderr
  shows the real `issue_701 pushed no branch this run` announcement.

## Ruled out

- Folding the conflict edge into `held` / `declared_deps`: it would make the hold print
  the "prerequisite(s) not ready" line, which the brief forbids (criterion (b)), and would
  also apply to `held_finished`, which the brief puts out of scope.
- Building the conflict map once before the loop: misses split children adopted mid-run
  (brief Scope). Cost of the live build: one `conflict_map` call per wave, and only on runs
  where something is already in `held_unpushed`.
- Re-reading `Conflicts with` from briefs inside `_runnable`: the brief asks to reuse
  `waves.conflict_map`.

## Known gap (from the brief, for sign-off)

A partner of a partner (CK `Conflicts with: CJ`, CJ held by this fix) still builds, on a
line without CJ — same as today for a partner of any bundle that is not COMPLETE for another
reason. Left out of scope by the brief.
