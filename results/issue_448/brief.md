# Brief (pointer) — issue 448 / sizing-split-ratchet-decomposed

> A **pointer** Plan artifact for a bundle that was DECOMPOSED rather than built. The plan
> for issue 448 is `split-proposal.md` in this bundle plus the four child briefs it
> produced; this file does not restate them. It exists so the parent has a Plan artifact
> of record: `iterate-plan` archived the first attempt's brief into `iteration-v1/`, and
> `split.accept` writes the close marker and the children but never a replacement brief —
> leaving the parent UNPLANNED with a terminal disposition already decided.
>
> **No patch lands here.** The close marker (`close-disposition` = `split`) is what the
> driver honours outright (`driver._close_class`, `driver.py:160-166`); the builder and
> reviewer leaves are skipped and the gate matrix is recorded N/A
> (`gates.run_close_gates`). The human confirms or overrides the split at sign-off.

- **Slug:** sizing-split-ratchet-decomposed
- **Planning artifact:** `split-proposal.md` (this bundle) — the accepted decomposition,
  authored in Plan after the first attempt was rejected. Authoritative for the seams, the
  wave sketch, and which of the issue's four asks each child owns. Its line references
  were re-verified against `eduralph/pdca-harness` `main` @ `b95aa58` for this brief.
- **Defect / goal:** issue 448 reports a structural ratchet: three of the five weighted
  features in `sizing.estimate` (`conflicts_with` +3, `difficulty_high` +3, `ext_deps` +3)
  are fields the split process itself installs into every child, so a split child scores
  9 ≥ the `oversized` cutoff of 7 regardless of its real scope; nothing on disk records
  that a split already happened, and `plan_policy.size_reasons` answers the inflated score
  by recommending another split. The issue itself asks for **four** changes and says they
  are independently shippable. The first attempt built all four as one slice: it worked
  (C4 not refuted, offline suite green) and was still rejected — *"T5 breadth is the root
  problem, not the implementation. The work is wanted; the SLICING was wrong."* The goal
  of THIS bundle is therefore no longer a fix: it is the record that the slice was split
  along the seams sign-off named, and that each seam is now carried by a live child.
- **Success criterion:** issue 448 lands **no patch**, and its four asks are wholly
  carried by four bundles that exist on disk with an authored `brief.md` and a filed
  GitHub sub-issue of #448 — verified at Plan and re-checkable by inspection at sign-off:
  1. **456** `split-lineage-record` — ask 1 (record lineage at materialisation; owns the
     schema decision the other three read).
  2. **457** `sizing-ignores-sibling-conflicts` — ask 2 (stop the estimator scoring the
     split's own scheduling metadata).
  3. **458** `split-child-remedy-and-hatch` — ask 3 (depth-/evidence-aware remedy in
     `size_reasons` + the prompts).
  4. **459** `split-convergence-report` — ask 4 (convergence check before `--accept` files
     irreversible issues).
  The four child briefs carry the wave order **456 → 457 → {458 ∥ 459}** with
  `458 Conflicts with 459`, so no two of them are built blind on the same base. Nothing
  from ask 1–4 is left unowned by this bundle, and the `max_split_depth` cap the issue
  explicitly holds in reserve is claimed by none of them (correctly — the issue defers it).
- **Falsifiability:** there is deliberately **no RED leg**, and this is not the
  Plan-blocking gap the template warns about — it is the close-disposition path working as
  designed: a bundle with a close marker never builds a patch, so C4 and the T-tiers are
  recorded N/A by construction (`gates.run_close_gates`), and the adjudication is the
  human's at sign-off under the C6 guard. The criterion is nonetheless falsifiable by
  deterministic inspection, and each clause was executed at Plan:
  `ls results/issue_45{6,7,8,9}/brief.md` (all present, all authored — no `<…>` slug);
  `gh api graphql` sub-issues of #448 → exactly `456, 457, 458, 459`;
  `pdca status` → `PLANNED issue_456`, `PLANNED issue_457 [blocked-by: 456]`,
  `PLANNED issue_458 [blocked-by: 457]`, `PLANNED issue_459 [blocked-by: 457]`.
  Delete a child bundle, drop a `Depends on:` edge, or find one of the issue's four asks
  unclaimed, and the criterion fails.
- **Repo + branch target:** eduralph/pdca-harness @ main — of record only. This bundle
  publishes no PR (`close: no PR`, as split parent #332 did); the four children publish
  against this target individually.
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** the parent is terminal and touches no file, so it neither depends on
  nor conflicts with anything — including its own children. The children carry the whole
  ordering: 457 depends on 456 (the estimator cannot exclude *sibling* conflicts until
  something on disk says who the siblings are); 458 and 459 both depend on 457 (each keys
  on the sibling-conflict count 457 exposes); 458 conflicts with 459 (no dependency, but
  both edit the accept/report path), so they are scheduled into different waves.
  **NOTE for the human — cross-bundle, not fixable from this brief:** `issue_449`
  (`flow-adopt-split-children`) declares `Depends on: 448, 453` and its `Ordering note:`
  says 448 is a genuine build-on because it writes the `split-lineage.json` children
  record that 449 reads. After the split, that record is **456's** deliverable, not 448's
  — 448 now lands no code at all. Left as-is, 449 waits on a bundle that gives it nothing
  and builds without the interface it consumes. 449's brief should be re-pointed to
  `Depends on: 456, 453`. See §Open item below.
- **Scope:** record the decomposition of issue 448 and carry it to sign-off for
  confirmation. / **out of scope:** every code change — all four asks belong to 456–459;
  re-opening the rejected single-slice implementation preserved in `iteration-v1/`
  (an `iterate-do` at sign-off archives the close marker and re-enables the full Do+Check
  band, which is the escape hatch if you reject the split); the `max_split_depth` cap
  (issue 448 defers it deliberately, and no child claims it).
- **Difficulty:** low — no file is touched on the target repo; blast-radius is zero.
- **External dependencies:** none
- **Test file:** none — this bundle lands no patch, so there is no regression to ship and
  C4 is N/A by construction on the close path.
- **Citations expected:** none — no change is made, so there is nothing for Do to cite.
  The claims above were cited at Plan against `main` @ `b95aa58` and against the driver
  source in this instance (`driver.py:144-172`, `split.py:435-461`, `gates.py:152-160`,
  `config.py:20-36`); the weights and cutoff quoted above are `DEFAULT_WEIGHTS` /
  `DEFAULT_OVERSIZED = 7` in `template/src/pdca_harness/sizing.py:89-94,127` on target main.
- **Prior-art check (triage cycles):** by affected file path on the target —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/split.py
  template/src/pdca_harness/sizing.py template/src/pdca_harness/plan_policy.py` returns
  the #322/#323/#358/#359 split-and-sizing history, and **none** of issue 448's four asks;
  `git -C ../pdca-harness grep -n "split-lineage\|split_lineage" origin/main -- template/src`
  returns nothing, confirming the lineage record does not exist upstream. Open PRs on the
  target carry none of it. The rejected first attempt never landed, so every citation in
  `split-proposal.md` is still current code.
- **Disposition hint:** likely-close — the parent is terminal. The hint is documentation
  only: the driver honours the existing `split` **marker** outright and never consults the
  hint here, and `split` is deliberately absent from the close-disposition vocabulary
  because `close_class` substring-matches (`config.py:31-35`).

## Open item for sign-off (the one thing this brief cannot settle)

`issue_449` still declares `Depends on: 448`. 448 will reach COMPLETE as a close/split with
no diff, so the wave fold hands 449 nothing, and 449 would be built without the
`split-lineage.json` record its `Ordering note:` says it reads. The correct edge is
`Depends on: 456, 453`. That is an edit to **449's** brief — a different bundle, and this
beat authors one brief — so it is raised here rather than made silently. 449 is still
`PLANNED` (nothing built), so the edit is free until it dispatches.

## If you reject the split

`iterate-do` at sign-off archives the close marker and this brief's attempt and re-enables
the full Do+Check band on the parent — the rejected single-slice patch is preserved intact
in `iteration-v1/patch.diff` (50 KB, C4 not refuted, offline suite green) and can be
carried forward. The four child *tracker issues* are filed and cannot be withdrawn by the
driver; closing them is a manual tracker action.

## STOP discipline

Draft only until Check sign-off. No PR is opened for this bundle. The children's PRs MUST
NOT be marked ready before their own sign-off accepts.
