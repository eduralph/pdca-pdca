# plan_policy: an honest split-child advisory, with an escape hatch that actually works

- **Slug:** split-child-remedy-and-hatch
- **Defect / goal:** `plan_policy.size_reasons` answers an oversized bundle with
  `consider `pdca split` first` (`plan_policy.py:134-141`), and its `splittable` predicate
  is true whenever *structural churn alone* fired — exactly the readout a split inflates
  (child-2). So every level of a recursion sees the same inputs and gives the same advice,
  and the planner prompt points at `pdca split` again. Make the advisory evidence-aware —
  and, the part the previous attempt got wrong, keep the split recommendation **reachable**.
  Two specific failures, both reproduced against the rejected patch, must not recur:
  1. **Keying on mere presence of lineage asserts something demonstrably false.** Child 601
     of a split of 500, re-planned with four *organic* conflicts (811-814) and **zero**
     sibling conflicts, scored 12 / `oversized` and still printed *"scores large for a split
     child … driven by inherited/sibling fields; prefer building over re-splitting"* — in
     the same string as its own contradicting evidence `4 conflict(s) declared`, and with no
     "sibling conflict(s) not counted" clause anywhere. The honest predicate is child-2's
     exposed sibling-conflict count.
  2. **The escape hatch was unreachable in the shipped configuration.** Re-enabling the
     split remedy only when `est.model_band == sizing.OVERSIZED` is dead config on any
     offline instance: `[leaves.sizer]` ships `mode = "stub"` and `leaves._stub_sizer`
     (`leaves.py:1213-1219`) returns `{"band": "ok"}` unconditionally. Combined with lineage
     deliberately surviving `iterate-plan`, a bundle that *ever* carried child lineage could
     never again be advised to split, whatever its brief later said, unless the operator
     bought a `mode = "command"` sizer. The hatch has to work with the sizer this project
     actually ships.
- **Success criterion:**
  (i) for a split child whose oversized score **is carried by** sibling conflicts,
      `size_reasons` emits an honest line naming the provenance ("scores large for a split
      child (child N of a split of #X, depth D) — driven by inherited/sibling fields; prefer
      building over re-splitting") and **not** `consider `pdca split` first`;
  (ii) for a split child with **zero** sibling conflicts — its score carried by organic
      evidence — `size_reasons` emits the ordinary split remedy unchanged, and never the
      inherited-fields line;
  (iii) **(ii) still holds on an instance running the shipped stub sizer**: the test
      exercises the real `_stub_sizer` (`band: "ok"`), not a mock, proving the suppression
      is neither permanent nor conditional on buying a `mode = "command"` sizer. The
      previous attempt's only hatch test mocked the stub away and passed on the red leg too,
      so nothing in the evidence would have surfaced the defect;
  (iv) the `before_do=False` branch keeps its existing `iterate-plan` wording
      (`plan_policy.py:142-149`) — a bundle that already has a patch is still told to
      re-plan, not to `pdca split`;
  (v) the same one-sentence provenance context is injected into `leaves._plan_prompt`
      (`leaves.py:524-591`) and `leaves._split_prompt` (`leaves.py:1222-1268`) when the
      bundle carries lineage, without otherwise rewording the existing split instructions;
  (vi) a bundle with **no** lineage produces byte-identical output to today.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Falsifiability:** RED on `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_plan_policy_split_child`. Criterion (i) is the load-bearing red: pre-fix
  `size_reasons` returns `consider `pdca split` first` for a split child whose score is
  carried by sibling conflicts, so the assertion that it does NOT fails. **Criteria (ii) and
  (iii) pass on the red leg by construction** — with `plan_policy.py` reverted the ordinary
  remedy is emitted unconditionally — which is exactly why they must live in the same module
  as (i): `run-verify.sh` runs the module, so the pair can only go green together and (iii)
  cannot degrade into a vacuous green. **Wave-2 bundle**: gate runs on the folded integration
  branch carrying children 1-2 (`PDCA_VERIFY_BASE`, `gates.py:379-397`), so the
  sibling-conflict count this child keys on exists on the base. No network or container.
- **Reproduction:** run `size_reasons` over a split child whose only churn features are
  sibling conflicts and inherited fields: it returns `oversized — consider `pdca split`
  first (…)`, the same advice its parent got, on a slice that is one function wide.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/plan_policy.py`
  (the remedy selection), `template/src/pdca_harness/leaves.py` (the two prompt builders
  **only**), and `docs/07-crosscutting.md` — **restricted to `### The process`** (`:36-99`;
  the `splittable?` decision nodes in the flowchart at `:50` and `:59`, the remedy node at
  `:52`, and the prose at `:86-87`). Leave `### The estimate` (`:100-173`) to child-2 and
  `### The split` (`:174-218`) to child-4; child-3 and child-4 are scheduled into different
  waves precisely because they share this file. **Out of scope:** `sizing.py` (child-2 owns the
  signal and this child only consumes it), `split.py` and `cli.py` (child-4), making the
  size guard blocking — it stays advisory for the calibrated reason in its own docstring
  (`plan_policy.py:88-102`: 50% recall at 62% precision, and `hold` stays unimplemented).
- **External dependencies:** `copier importable (.venv)` — the patch changes files under
  `template/`, so the target's render and `copier update` compatibility root suites exercise
  it; without copier those seven tests skip themselves and T3 reports a green that tested
  nothing. Otherwise python3 ≥ 3.11 stdlib + git only; the test runs in the offline driver
  suite with no tracker, network or container.
- **Test file:** `template/tests/test_plan_policy_split_child.py` — a new module in the
  offline driver suite. The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`run-verify.sh:121-130`), so a new file earns its red. **Import the module, never the new
  symbols** — `from pdca_harness import plan_policy, sizing, split, leaves`, then attribute
  access inside test bodies; a module-level `from … import <helper>` raises ImportError on
  the red leg, giving 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:145`).
  Note that criterion (iii) must go red for the *right* reason: on the red leg the ordinary
  remedy is emitted anyway, so pair it with (i) in the same module so the pair can only pass
  together.
- **Difficulty:** medium
- **Depends on:** 457
- **Conflicts with:** 459

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rebuild and verify against the real base: pdca-integration/main, which now carries prerequisite #457. The recorded gate green was earned against origin/main without #457; the reviewer's #457-folded tree showed criteria (i) and (iv) fail when stacked — the sibling fixture becomes patch-only and the remedy decision at plan_policy.py:134 bypasses the new branch at :151. Cause: the patch re-derives the sibling-conflict count from lineage + brief instead of consuming the single sibling-conflict signal #457 exposes. Consume #457's exposed signal as the one source before remedy selection; earn the red→green on the #457-carrying base.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Patch content verified sound (reviewer C1-C5/T1-T3 PASS on b4c924d = pdca-integration/main + #457); rejected because the brief is wrong, not the code. The brief declares `Repo + branch target: ... @ main`, but the change hard-depends on #457 (`SizeEstimate.sibling_conflicts`), which is on pdca-integration/main (PR #483 merged 2026-08-10) and NOT on main — so the C4 gate verified against a base that cannot carry the fix, and publish would open the PR against the wrong branch. Re-plan must: (1) declare the branch target / PR base as pdca-integration/main; (2) record the #457 dependency so the wave driver writes `stack-base` and both C4 and publish resolve the right base; (3) carry the iteration-2 patch and its 9-test module (real `_stub_sizer`, no mocks) forward as the reference implementation — do not redesign; re-house the same change under the corrected brief.
- Failing gate: C4 fix verified: bundle test red pre-fix, green post-fix — C4 FAIL: bundle test red WITH the fix applied
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite FAILED (rc 1), driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
