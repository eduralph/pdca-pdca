# Result — issue 448 / split-lineage-and-deratchet-sizing

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: a split child stops being indistinguishable from a fresh oversized brief.
  `pdca split --accept` records machine-readable **lineage** in every bundle it writes (and
  the inverse children record in the parent); the estimator stops scoring the split's own
  artifacts; the size remedy stops recommending a further split on structural score alone;
  and `--accept` reports, before filing irreversible issues, whether the split lowers the
  estimate.
- Success criterion: for a bundle carrying split lineage, (a) `sizing.estimate` no
  longer counts `Conflicts with` entries naming its own siblings, so a child whose only
  churn features are sibling conflicts + inherited `Difficulty`/`External dependencies`
  scores **below** the `oversized` cutoff where it scores ≥ 7 today; (b)
  `plan_policy.size_reasons` emits the split-recommending remedy (`consider \`pdca split\`
  first`) for such a child ONLY when `model_band == oversized`, and otherwise an honest
  "scores large for a split child — driven by inherited/sibling fields" line; (c)
  `split.materialise` writes a `split-lineage.json` into each child and the parent, and
  `split.preflight` reports each staged child's structural band against the parent's
  before `file_children` runs. Demonstrable by C4-verify on the patch alone.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: the four items in *Design*, as one coherent change: (1) lineage + children
  record at materialisation; (2) the estimator stops counting sibling conflicts, plus a
  registered-but-zero `split_child` weight; (3) a depth- and evidence-aware remedy in
  `size_reasons`, and the same context injected into the planner and splitter prompts;
  (4) an advisory convergence report in `split.preflight`.
  / out of scope: a `max_split_depth` cap (held in reserve — items 2–3 remove the *reason*
  depth grows, a cap truncates the symptom); re-calibrating any existing weight or cutoff
  (that is the #324/#359 Act-cadence loop); making the size guard blocking (it stays
  advisory, `plan_policy.py:88-102`); `waves.compute_waves` scheduling semantics; anything
  in `flow.py` — mid-run adoption of children is issue 449 and this bundle must not touch
  that file.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue 448: record split lineage and use it to prevent structural sizing metadata from repeatedly recommending another split.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance contract is explicit and falsifiable across lineage, scoring, remedy selection, and pre-filing convergence reporting, so each promised outcome has an observable oracle. |
| C2 Reproduction (red pre-fix) | PASS | On base `b95aa58` with the production hunks absent and the retained test present, all 19 tests executed and the suite failed (7 failures, 13 errors), including the pre-fix score of 9 at `template/tests/test_split_lineage.py:166`. |
| C3 Change | PASS | The target delta exactly matches `patch.diff`; accepted children and their parent gain transactional lineage at `template/src/pdca_harness/split.py:639` and `template/src/pdca_harness/split.py:695`, while only declared sibling conflicts are removed from churn at `template/src/pdca_harness/sizing.py:277`. |
| C4 Verification (red→green) | PASS | The same 19-test module passed with the patch after a real red on the base, `compileall` passed, and the 1,610-test offline driver suite passed with two skips; the end-to-end pre-filing assertion is at `template/tests/test_split_lineage.py:312`. |
| C5 Causal adequacy | PASS | The change records the missing provenance and removes split-generated sibling metadata from the causal input at `template/src/pdca_harness/sizing.py:277`; it adds no capability probe or guard around a capability-present path. |
| T1 Structure | PASS | One tolerant reader centralizes schema handling at `template/src/pdca_harness/split.py:258`, child writes remain staged at `template/src/pdca_harness/split.py:551`, and the provenance file is correctly absent from attempt artifacts at `template/src/pdca_harness/state.py:82`. |
| T2 Shape | PASS | Documentation lint and the 22-page rendered-site link audit passed independently, and the published zero-weight contract agrees with the template setting at `docs/07-crosscutting.md:128` and `template/pdca.toml.jinja:259`. |
| T3 Runtime | NEEDS-HUMAN | Decide whether to accept unrerun render/update compatibility — `copier` is absent, so all seven root tests skipped even though the 1,610-test driver suite passed; this matters because the patch changes the rendered configuration at `template/pdca.toml.jinja:237`. |
| T4 Contribution | NEEDS-HUMAN | Confirm the contribution artifacts have the required user-impact opener and issue-448 linkage — `commit-msg.txt` and `pr-description.md` are absent from the reviewer inputs, so the recorded `contribcheck` pass cannot be independently reproduced and publishability remains provisional. |
| T5 Judgment | NEEDS-HUMAN | Decide whether four independently shippable design items should remain one slice — affected-path merged history and the sole closed-unmerged PR (README-only #4) show no competing prior art, but the breadth across lineage, sizing, policy, and prompts affects review and rollback. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide in an actual operator workflow whether the lineage-aware score and advisory wording stop repeat splitting without suppressing legitimate re-splits — automated coverage proves the mechanics at `template/tests/test_split_lineage.py:162` and `template/tests/test_split_lineage.py:218`, not operational fitness. |

### Advisory — adversary

# Adversarial review — issue 448 / split lineage + de-ratcheted sizing

Evidence re-run at `$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt-l1`, HEAD `b95aa58`):
red leg reproduced by reverting the six production hunks and keeping the new test —
`7 failures + 13 errors`, all errors `AttributeError` on `split.lineage` / `split.LINEAGE`
(module-level imports, so a genuine red, not the ImportError/PDCA-UNVERIFIABLE trap the
brief warned about); green leg `Ran 19 tests … OK`; whole offline driver suite
`Ran 1610 tests … OK (skipped=2)`. The chain runs through the real production path
(`cli._split` → `split.accept` → `sizing.estimate` → `plan_policy.size_reasons`), not a
parallel re-implementation. **C4 as such is not refuted.** What follows attacks the fix.

- **NEEDS-HUMAN — the escape hatch is unreachable in the shipped configuration, so the
  suppression is unconditional and permanent.** `template/src/pdca_harness/plan_policy.py:152`
  re-enables `consider \`pdca split\` first` for a split child only when
  `est.model_band == sizing.OVERSIZED`, but `[leaves.sizer]` ships `mode = "stub"`
  (`template/pdca.toml.jinja:507-511`) and `leaves._stub_sizer`
  (`template/src/pdca_harness/leaves.py:1221-1227`) returns `{"band": "ok"}` unconditionally
  → `model_band` is `"ok"` for every offline instance. Combined with lineage deliberately
  surviving `iterate-plan` (`split.py:60-63`), a bundle that once carried child lineage can
  **never again** be advised to split, whatever its brief later says, unless the operator
  buys a `mode = "command"` sizer. The docs row added by this patch
  (`docs/07-crosscutting.md:128-134`) states the new rule without stating that the shipped
  sizer cannot satisfy it. This is the brief's own design (§Design item 3), so it is a
  fitness call for sign-off — but note that the *only* test covering the hatch mocks the
  stub away (`template/tests/test_split_lineage.py:249-251`) and passes on the red leg too,
  so nothing in the evidence would have surfaced it.

- **NEEDS-HUMAN [impl] — the new remedy asserts something demonstrably false on a concrete
  input.** `template/src/pdca_harness/plan_policy.py:152-156` keys only on *presence* of
  lineage, never on whether split-installed fields actually carry the score. Reproduced:
  child `601` of a split of `500`, re-planned to a 15.8 KB brief with **four organic
  conflicts (811, 812, 813, 814) and zero sibling conflicts**, scores 12/`oversized`, and
  `size_reasons` still prints *"scores large for a split child (child 1 of a split of #500,
  depth 1) — driven by inherited/sibling fields; prefer building over re-splitting"* — in
  the same string as its own evidence `4 conflict(s) declared` and **no** "sibling
  conflict(s) not counted" clause. `estimate` already computes `sibling_conflicts`
  (`sizing.py:280`); the honest predicate is available and unused.

- **NEEDS-HUMAN — a bundle that is both a child and a parent loses its child edge, and the
  ratchet returns at depth ≥ 1.** `split.py:695-697` overwrites the bundle's own `role:
  "child"` record with a `role: "parent"` one, preserving only `depth`. Reproduced: bundle
  `601` (child of `500`) scores `6 / watch` with `size_reasons == []`; after
  `split.accept(601, [701,702])` its record is
  `{"role":"parent","id":"601","children":["701","702"],"depth":1}`, its estimate returns to
  `9 / oversized` (`'1 conflict(s) declared'` is back), `leaves._plan_prompt` no longer
  carries the provenance note, and once the close marker is archived on the reopen path the
  module itself documents (`split.py:686-688`), the remedy is `consider \`pdca split\` first`
  again. `test_depth_counts_recursion_without_anyone_counting`
  (`template/tests/test_split_lineage.py:97-108`) asserts only that `depth` survives, so it
  blesses the loss rather than catching it. One filename in both directions cannot express a
  mixed-role bundle; since the schema is the declared contract with issue 449, the fix (keep
  `parent`/`siblings` on a parent record, or let a record carry both edges) is a human
  schema decision, not a silent builder tweak.

- **NEEDS-HUMAN [impl] — the convergence report never fires on the `--ids` path.**
  `cli.py:764` calls `split.accept(d, ids, cfg)` directly, and `accept` (`split.py:607`)
  does not call `preflight`; only the auto-filing branch does (`cli.py:733`). Reproduced:
  `pdca split 500 --accept --ids 601,602` materialised both children and marked the parent
  split with stderr containing nothing but
  `issue_500 marked split; run \`pdca flow 601 602\`` — no convergence line. That is the
  path the docs call *required* for a tracker `pdca` cannot reach
  (`docs/07-crosscutting.md:200-204`), i.e. exactly the operator who has already paid for
  the irreversible issues and most needs the verdict. The one test for ordering
  (`test_split_lineage.py:212-224`) passes `ids=""`, so the gap is untested.

- **NEEDS-HUMAN [impl] — the advisory's own prints can abort the acceptance.**
  `split.py:442-447` emits `len(children)+1` lines to stderr inside `preflight`, and the
  fallback handler prints again; both writes are inside `cli.py:733-739`'s
  `try: … except OSError:`. Reproduced with a stderr that fails after the first line (what
  `pdca split 500 --accept 2>&1 | head` produces): `BrokenPipeError` from the second report
  line → `except Exception` → the fallback `print` raises again → the exception escapes
  `preflight`, and the operator gets either an unhandled traceback or the flatly wrong
  `split: issue_500 has no split-proposal.md — run \`pdca split 500\` first` with rc 1, on a
  bundle whose proposal is fine. Pre-patch `preflight` wrote nothing to stderr, so this is
  new. `cli.py:756-759` already guards its own stderr print with `except OSError: pass` for
  precisely this reason; the same guard belongs around these prints.

- **NEEDS-HUMAN — the exclusion also blinds the one check that could see a bad split.**
  `split.py:397-398` writes staged sibling records so `convergence_report` excludes
  sibling conflicts exactly as the live estimator will. But a `Conflicts with` edge *between
  siblings* is the splitter's statement that those two children edit a shared resource —
  the splitter prompt calls those fields "the point" (`leaves.py:1274`). A proposal whose
  children all conflict pairwise (i.e. the split separated nothing) is therefore scored
  *lower* by the very report that exists to detect non-convergence, and its lines will read
  as a clean split. The brief's *Alternatives considered* weighs dropping/lowering
  `conflicts_with` globally, but not the claim that sibling conflicts carry no information —
  worth answering at sign-off.

- **NEEDS-HUMAN — estimator and calibrator now disagree on `conflicts_with`.**
  `template/scripts/size-calibrate:300` still mines `len(set(brief.conflicts_with(ap)))`,
  including sibling entries that `sizing.py:277-281` no longer scores. Any Act-cadence
  retune of `conflicts_with` (#324/#359 — the loop the brief explicitly defers to, and
  which `template/pdca.toml.jinja:237-243` points at for `split_child`) will fit the weight
  on a feature value the engine does not use for split children. The added `pdca.toml`
  comment concedes only that "size-calibrate mines no lineage feature yet"; the sharper
  problem is that a *shared* feature now means two different things.

**Attempted and could not refute:** unbound `lineage` on the malformed-brief path (the
`except OSError` at `sizing.py:284-290` returns early, so `sizing.py:316` is unreachable
with `lineage` unset); `#601` / `issue_601` id shapes defeating the sibling match
(`cli.py:713-717` normalises before `accept`, and `brief._id_list` strips both, so
`siblings` and `Conflicts with` agree); path traversal via a proposal label into
`convergence_report`'s `Path(tmp) / child.label` (`split.py:394`) — `_LABEL_RE`
(`split.py:43`) pins labels to `child-\d+`; widening of the `AprioriBrief` allowlist (the
read goes through `brief_path.parent`, `sizing.py:239`, and the guard is untouched);
rollback of the parent record on a failed accept (`split.py:711-717` restores the prior
bytes, verified by inspection against `prior_lineage` read at `split.py:635`); and any
regression in the 1610-test offline suite.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T3 Runtime — Decide whether to accept unrerun render/update compatibility — `copier` is absent, so all seven root tests skipped even though the 1,610-test driver suite passed; this matters because the patch changes the rendered configuration at `template/pdca.toml.jinja:237`.
- [ ] T4 Contribution — Confirm the contribution artifacts have the required user-impact opener and issue-448 linkage — `commit-msg.txt` and `pr-description.md` are absent from the reviewer inputs, so the recorded `contribcheck` pass cannot be independently reproduced and publishability remains provisional.
- [ ] T5 Judgment — Decide whether four independently shippable design items should remain one slice — affected-path merged history and the sole closed-unmerged PR (README-only #4) show no competing prior art, but the breadth across lineage, sizing, policy, and prompts affects review and rollback.
- [ ] Validation — fitness-to-purpose — Decide in an actual operator workflow whether the lineage-aware score and advisory wording stop repeat splitting without suppressing legitimate re-splits — automated coverage proves the mechanics at `template/tests/test_split_lineage.py:162` and `template/tests/test_split_lineage.py:218`, not operational fitness.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Rejected as one slice: T5 breadth is the root problem, not the implementation. The work is wanted; the SLICING was wrong. Split into separate outcomes at these seams: 1. Lineage record + schema. Must settle the mixed-role case first: a bundle that is both child and parent currently loses its child edge (split.py:695-697 overwrites the child record with a parent one, preserving only depth), and the ratchet returns at depth >= 1. This schema is the declared contract with issue 449, so it lands first and alone. 2. Estimator de-ratchet. Stop counting sibling conflicts. Resolve the estimator / calibrator disagreement on conflicts_with (scripts/size-calibrate:300 still mines the raw feature that sizing.py:277-281 no longer scores) rather than deferring it to the #324/#359 loop. FOLDED IN (was a separate finding): excluding sibling conflicts also blinds the convergence report to a split that separated nothing — children conflicting pairwise now score LOWER in the very report meant to detect non-convergence. Handle both together, since both turn on what a sibling conflict is taken to mean. 3. Remedy wording + escape hatch. Key the "driven by inherited/sibling fields" line on the already-computed sibling_conflicts, not on mere presence of lineage — today a child with four organic conflicts and zero sibling conflicts scores 12/oversized and still prints the inherited-fields line next to its own contradicting evidence. And make the hatch reachable: the shipped sizer is mode = "stub" and returns band = "ok" unconditionally, so on any offline instance the split recommendation is suppressed permanently once lineage exists. 4. Convergence report. Must fire on the --ids path too (cli.py:764 calls split.accept directly; only the auto-filing branch calls preflight), which is the path the docs call required for unreachable trackers. Its stderr writes must not be able to abort the acceptance — a BrokenPipeError currently escapes preflight and can report the flatly wrong "no split-proposal.md" with rc 1 on a healthy bundle. Not a rebuild: a single attempt cannot turn these four into one outcome, and the findings will read implementation-shaped every round until the split is authored. Note for Plan: C4 was NOT refuted — the red/green legs are genuine and run through the real production path. The mechanics largely work; it is the breadth and two design questions (schema mixed-role, meaning of a sibling conflict) that send this back. §6 NEEDS-HUMAN items left open (unticked) — not cleared, superseded by the iterate.
- By / date: Eduard Ralph / 2026-08-07

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
