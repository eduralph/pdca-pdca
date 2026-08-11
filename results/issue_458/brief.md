# Brief — issue 458 / split-child-remedy-and-hatch

> Re-plan (iteration 3) after sign-off `iterated-to-Plan` on 2026-08-10. The v2 PATCH was
> judged sound (reviewer C1–C5, T1–T3 all PASS on the #457-carrying base); the v2 BRIEF was
> wrong — it targeted `main`, which lacks #457's `SizeEstimate.sibling_conflicts`, so C4
> gated against a base that cannot carry the fix and publish would have opened the PR
> against the wrong branch. This brief re-houses the SAME change under the corrected
> target. **Do must not redesign** — see Citations expected.

- **Slug:** split-child-remedy-and-hatch
- **Defect:** `plan_policy.size_reasons` answers an oversized bundle with ``consider
  `pdca split` first`` (`plan_policy.py:140-141` on the target branch), and its
  `splittable` predicate (`plan_policy.py:134-136`) is true whenever *structural churn
  alone* fired — exactly the readout a split inflates. So every level of a recursion sees
  the same inputs and gives the same advice, and the planner prompt points at `pdca split`
  again. Make the advisory evidence-aware — keyed on the honest signal #457 now exposes
  (`sizing.py:215` `SizeEstimate.sibling_conflicts`, computed at `sizing.py:324-325`) —
  and keep the split recommendation **reachable**. Two failures reproduced against the
  first rejected attempt must not recur:
  1. **Keying on mere presence of lineage asserts something demonstrably false.** Child
     601 of a split of 500, re-planned with four *organic* conflicts and **zero** sibling
     conflicts, scored `oversized` and still printed "driven by inherited/sibling fields;
     prefer building over re-splitting" — contradicting its own evidence. The honest
     predicate is the sibling-conflict *count*, not lineage presence.
  2. **The escape hatch must work with the sizer this project ships.** Re-enabling the
     split remedy only when `est.model_band == sizing.OVERSIZED` is dead config on any
     offline instance: `[leaves.sizer]` ships `mode = "stub"` and `leaves._stub_sizer`
     (`leaves.py:1217-1224`) returns `{"band": "ok"}` unconditionally, so a bundle that
     ever carried lineage could never again be advised to split.
- **Success criterion:**
  (i) for a split child whose oversized score **is carried by** sibling conflicts,
      `size_reasons` emits an honest line naming the provenance ("scores large for a split
      child (child N of a split of #X, depth D) — driven by inherited/sibling fields;
      prefer building over re-splitting") and **not** ``consider `pdca split` first``;
  (ii) for a split child with **zero** sibling conflicts — its score carried by organic
      evidence — `size_reasons` emits the ordinary split remedy unchanged, and never the
      inherited-fields line;
  (iii) **(ii) still holds on an instance running the shipped stub sizer**: the test
      exercises the real `_stub_sizer` (`band: "ok"`), not a mock, proving the suppression
      is neither permanent nor conditional on buying a `mode = "command"` sizer;
  (iv) the `before_do=False` branch keeps its existing `iterate-plan` wording
      (`plan_policy.py:142-148`) — a bundle that already has a patch is still told to
      re-plan, not to `pdca split`;
  (v) the same one-sentence provenance context is injected into `leaves._plan_prompt`
      (`leaves.py:524`) and `leaves._split_prompt` (`leaves.py:1226`) when the bundle
      carries lineage, without otherwise rewording the existing split instructions;
  (vi) a bundle with **no** lineage produces byte-identical output to today.
- **Falsifiability:** RED verified 2026-08-11 directly on `origin/pdca-integration/main`
  (ef00e6e): the 9-test module on the unpatched tree runs all 9 tests and FAILS (4
  failures, 2 errors; the load-bearing red is criterion (i) — pre-fix `size_reasons`
  returns ``consider `pdca split` first`` for a sibling-conflict-carried child). GREEN
  verified on the same base with the reference patch applied (9 tests OK). Criteria (ii)
  and (iii) pass on the red leg by construction — with `plan_policy.py` reverted the
  ordinary remedy is emitted unconditionally — which is exactly why they must live in the
  same module as (i): `run-verify.sh` runs the whole module, so the pair can only go green
  together and (iii) cannot degrade into a vacuous green. The gate base is resolved from
  THIS brief's branch-target field (`worktree._target` → `publish._resolve_target`), so
  the worktree is cut off `origin/pdca-integration/main`, which carries #457 (PR #483
  merged 2026-08-10) — no `stack-base` marker, no `$PDCA_BASE`/`$PDCA_VERIFY_BASE`
  needed. No network or container.
- **Invariant to restore:** advice emitted by the driver must be entailed by the evidence
  it cites — a remediation string may not assert a provenance ("driven by
  inherited/sibling fields") the readouts contradict, and a documented escape hatch must
  be reachable in the shipped default configuration (docs/principles.md §3: prefer
  removing the cause — the dishonest predicate — over guarding the symptom).
- **Repo + branch target:** eduralph/pdca-harness @ pdca-integration/main
- **Depends on:** 457
- **Conflicts with:** 459
- **Ordering note:** #457 (child-2 of the #448 split) is COMPLETE and its PR #483 is
  merged into `pdca-integration/main` (commit b4c924d, merge ef00e6e) — the dependency is
  satisfied by the target branch itself, which is why the branch target above is
  `pdca-integration/main` and not `main` (the v2 rejection cause). #459 (child-4) also
  edits `docs/07-crosscutting.md` (its `### The split` section), so it must not build
  blind on the same base in the same wave.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** the remedy selection in `template/src/pdca_harness/plan_policy.py`
  (`size_reasons`), the two prompt builders **only** in
  `template/src/pdca_harness/leaves.py` (`_plan_prompt` :524, `_split_prompt` :1226), and
  `docs/07-crosscutting.md` **restricted to `### The process`** (`:36-99` on the target
  branch: the `splittable?` decision nodes in the flowchart at `:50` and `:59`, the remedy
  node at `:52`, and the prose at `:83-98`). / out of scope: `sizing.py` (#457 owns the
  signal; this slice only consumes it), `split.py` and `cli.py` (#459), `docs/07-crosscutting.md`
  `### The estimate` (`:100-189`, #457's) and `### The split` (`:190+`, #459's), and
  making the size guard blocking — it stays advisory for the calibrated reason in its own
  docstring (`plan_policy.py:88-102`: 62% precision, `hold` unimplemented).
- **Repro instruction:** on a checkout of `origin/pdca-integration/main`, run
  `size_reasons` over a split child whose only churn features are sibling conflicts and
  inherited fields: it returns ``oversized — consider `pdca split` first (…)`` — the same
  advice its parent got, on a slice that is one function wide.
- **External dependencies:** `copier importable (.venv)` — the patch changes files under
  `template/`, so the target's render and `copier update` compatibility root suites
  exercise it; without copier those seven tests skip themselves and T3 reports a green
  that tested nothing. Otherwise python3 ≥ 3.11 stdlib + git only; the test runs in the
  offline driver suite with no tracker, network or container.
- **Test file:** `template/tests/test_plan_policy_split_child.py` — a new module in the
  offline driver suite. The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`run-verify.sh:121-126`), so a new file earns its red. **Import the module, never the
  new symbols** — `from pdca_harness import plan_policy, sizing, leaves`, then attribute
  access inside test bodies; a module-level `from … import <helper>` raises ImportError on
  the red leg, giving 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:140-146`).
  Pair criterion (iii) with (i) in the same module so the pair can only pass together.
- **Citations expected:** Do must cite path:line on `pdca-integration/main` for every
  change. **Reference implementation (sign-off directive — re-house, do not redesign):**
  this bundle's `iteration-v2/patch.diff` and `iteration-v2/test_plan_policy_split_child.py`
  are the accepted-content attempt, rejected ONLY for its brief's wrong branch target. Do
  MAY read both and SHOULD re-apply the same change: the patch applies cleanly on
  `origin/pdca-integration/main` (ef00e6e, `git apply --check` rc=0, verified 2026-08-11)
  and its 9-test module is red unpatched / green patched on that base. Adjust only what
  the base shift demands (context drift, none observed).
- **Prior-art check (triage cycles):** by affected path against `origin/main` and
  `origin/pdca-integration/main` merged history — #483 (`sizing.py`, the signal this slice
  consumes; merged) is the only adjacent change; closed-PR path search (v2 review): 2 hits
  `plan_policy.py`, 15 `leaves.py`, 8 `docs/07-crosscutting.md`, 0 for the test path —
  none implements this remedy. GitHub has no open PR for #458.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts. The PR base is `pdca-integration/main` — publish
resolves it from this brief's branch-target field; do not open against `main`.
