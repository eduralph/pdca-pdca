<!-- pdca:split-proposal v1 -->
# Split proposal — issue 332

## Why this slice is oversized

The previous attempt (iteration-v1) shipped all five numbered items of #332 plus the
#335 fold as one patch: 114.7 KB across 16 files against the 100 KB size backstop.
Work quality was strong (C4 green, 9/12 advisory PASS) — the slice, not the work, was
rejected. The issue contains two separable shippable outcomes along a clean seam:

1. **The classification signal** — what a reviewer finding *is* (IMPL / HUMAN /
   STANDING): the reviewer-stated `[impl]` tag, the classifier honouring it bounded by
   the taxonomy, and the Validation-row exact-match fix. Lives in `assemble.py` +
   the prompts (`leaves.py`, `agents/*.jinja`). Ships alone with observable value:
   tagged judgment findings classify IMPL and the 37 broken V-rows classify STANDING,
   so today's `eligible()` fires strictly more often.
2. **The loop policy** — when the rebuild loop *fires, stops, and hands over*:
   soft/hard round budgets with the convergence test, HUMAN findings deferring to a
   loss-proof ledger instead of vetoing, the #335 retirement fold, and the #324
   size-backstop composition. Lives in `autoiterate.py`, `config.py`, `state.py`,
   `driver.py`, `flow.py` + the ledger merge in `assemble.py`. Ships alone with
   observable value under today's classifier: IMPL findings already exist in
   production (31/230 attempts were eligible), so deferral + budgets change firing
   behaviour without the tag.

Measured against the prior patch's per-file sizes, the seam lands ~45 KB / ~70 KB —
both under the backstop, including each child's share of the 43.7 KB test file.

## Wave sketch

The children are functionally independent — neither builds on the other's result
(child-2's `eligible()` rework operates on the `NeedsHumanItem.kind` interface that
already exists on main; child-1's tag promotion is useful under today's veto rule) —
but they EDIT SHARED FILES: `template/src/pdca_harness/assemble.py` and
`template/tests/test_autoiterate.py`, so they must be in different waves either way.
Both also conflict with in-flight #369 (edits the §6 assembly in `assemble.py` and
the driver's Check sequencing); 369 is not a child of this proposal, so that conflict
is added to the materialised briefs' `Conflicts with` value lines post-accept
(sibling-label fields here cannot carry tracker ids). #331, named by the parent
brief, has since MERGED (pdca-harness PR #398) and is no longer a conflict.

**Post-accept amendment (human decision, same Plan beat):** both children land on ONE
parent integration branch instead of per-child PRs — `Onto branch:
origin/enhancement/332-autoiterate-soft-hard-defer` (created off origin/main with an
empty DCO-signed scaffold commit; draft PR pdca-harness#410, closing #332/#408/#409
and #335-by-fold, merged to main once by the human). That turns the inter-child
relation into a genuine build-on — #408 publishes its commit onto the branch, #409
builds and publishes on top — so the materialised briefs carry `Depends on: 408` on
409 (not the mutual `Conflicts with` drafted below), plus `Conflicts with: 369` on
both. Waves verified: wave 0 = 408, wave 1 = 409.

<!-- pdca:child child-1 -->
- **Slug:** review-impl-tag-v-row
- **Defect / goal:** builder-fixability of a §6 finding is inferred from a taxonomy
  proxy — which 5/5/1 cell it landed on — rather than stated by the reviewer that found
  it, so a judgment cell (C5/T5) whose substance is an ordinary build defect classifies
  HUMAN (T5 present in 146/230 measured attempts, C5 in 66/230); `_advisory_prompt`
  tells the advisory leaves "when in doubt, OMIT `[impl]`" (`leaves.py:2024`), which is
  why 139 advisory findings arrive untagged and classify HUMAN; and the STANDING match
  for the Validation row demands an exact Item-cell match against `_V_LABEL`
  (`assemble.py:445-447`) while production writes the cell three ways, so 37/223
  observed V-rows classify as a real HUMAN objection. Deliver items 2, 3 and 5 of
  issue #332: the reviewer states builder-fixability with a `NEEDS-HUMAN [impl]`
  verdict, the classifier honours the tag bounded by the taxonomy, and the V-row match
  accepts all three observed forms.
- **Success criterion:** (1) a judgment-cell (C5/T5) verdict `NEEDS-HUMAN [impl]` is
  promoted to IMPL only for promotable elements — judgment-kind minus V, derived from
  `gates.canonical_elements()` the way `_GATE_ELEMENTS` is at `assemble.py:50` — with
  STANDING checked before the tag so a tagged V row stays STANDING; an `[impl]` tag on
  an input cell (C1/C3) and on V is ignored; an untagged bullet still classifies HUMAN
  (fail-safe unchanged); gates-that-could-not-run / declared / unregistered
  dependencies are never promotable. (2) The STANDING match accepts all three
  production forms (`Validation — fitness-to-purpose`,
  `V — Validation — fitness-to-purpose`, `Validation -- fitness-to-purpose`) by
  normalizing an optional leading `<element-id> —` prefix and folding ASCII `--` before
  comparing, comparison exact *after* normalization (no prefix-matching of free text —
  the #294 rule); the `i in verdict_table` guard and the fail-closed dual-STANDING
  guard (`assemble.py:452-457`) stay. (3) `_REVIEW_PROMPT` (`leaves.py:1418`) instructs
  the tag on judgment rows and renders the element list consistently with
  `agents/reviewer.md.jinja` (the current `{elem} — {label}` listing vs the role
  prompt's bare label is the root cause of the prefix form); `_advisory_prompt`'s
  "when in doubt, OMIT `[impl]`" (`leaves.py:2024`) is replaced by a required
  `[impl]`/`[human]` tag on every NEEDS-HUMAN bullet, untagged→HUMAN fail-safe
  unchanged; `agents/reviewer.md.jinja` and `agents/adversary.md.jinja` carry the same
  contract (they are prepended inline for the codex family via `_role_injection`).
- **Falsifiability:** the offline driver suite on this host
  (`cd template && PYTHONPATH=src python3 -m unittest tests.test_autoiterate`), run by
  the C4 gate (`engine/scripts/run-verify.sh`, which reverts production hunks in place
  and keeps the briefed tests — an appended test earns its red). RED now, per clause:
  (1) `[impl]` on a C5/T5 verdict cell is ignored — `assemble.py` has no
  `_PROMOTABLE_ELEMENTS` and `_classify_finding` (`assemble.py:128`) never promotes;
  (2) the prefix form `V — Validation — fitness-to-purpose` fails the exact casefolded
  match at `assemble.py:445-447` (parameterizing the suite's `_STANDING_ROW` over the
  three forms goes red on two of them); (3) grep-level: `leaves.py:2024` still says
  OMIT.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** child-2
- **Ordering note:** child-2 also edits `assemble.py` and `test_autoiterate.py` —
  shared files, no functional dependency, so different waves with the wave fold
  composing the edits. Also conflicts with in-flight #369 (same `assemble.py` §6
  assembly) — added to the materialised brief post-accept.
- **Difficulty:** medium
- **Scope (one logical fix) / out of scope:** issue #332 items 2, 3, 5 — reviewer /
  advisory / role-prompt tag contract, `_PROMOTABLE_ELEMENTS` + tag honouring in
  `assemble.py` (`_needs_human` carries the tag out beside `standing`;
  `_classify_finding` promotes for promotable elements only, STANDING check ordered
  ahead of the tag check), V-row normalization, prompt alignment; tests parameterized
  over the three V forms, tag-on-C1/C3/V ignored, promotion bounded by taxonomy.
  / out of scope: `eligible()` / budgets / deferral / ledger (child-2); routing
  input-cell defects to `iterate-plan` (#332's declared follow-up); any change to
  `autoiterate.py`, `config.py`, `state.py`, `driver.py`, `flow.py`.
- **Reproduction:** feed `_needs_human` a verdict table containing
  `| V — Validation — fitness-to-purpose | … | NEEDS-HUMAN | … |` → the row classifies
  HUMAN (vetoing), not STANDING; feed a C5 row `NEEDS-HUMAN [impl]` →
  `_classify_finding` returns HUMAN. Both as unittests in the named test file.
- **External dependencies:** none
- **Test file:** template/tests/test_autoiterate.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites verified on main: `_GATE_ELEMENTS` `assemble.py:50` (mirror its
  derivation for `_PROMOTABLE_ELEMENTS`: `kind == "judgment"` minus `V`), `_V_LABEL`
  `assemble.py:64`, `_classify_finding` `assemble.py:128`, `_needs_human`
  `assemble.py:404` with the exact casefolded match at `:445-447` and the fail-closed
  dual-STANDING guard at `:452-457`; `_REVIEW_PROMPT` `leaves.py:1418`; the OMIT
  instruction `leaves.py:2024`; the existing suite hard-codes the exact V form in its
  `_STANDING_ROW` (`test_autoiterate.py:41` area) — parameterize it.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline
  origin/main -- template/src/pdca_harness/assemble.py
  template/src/pdca_harness/leaves.py` — #293/#294 history present; no
  `_PROMOTABLE_ELEMENTS`, no V-form normalization on main (exact match still at
  `assemble.py:445-447`, OMIT still at `leaves.py:2024`, both re-verified 2026-08-02).
  Instance prototype getwyrd/wyrd-pdca#167 exists downstream only. The parent's
  iteration-v1 patch implements this shape and passed C4/advisory — carry the
  implementation shape, re-cut to this child's scope.
- **Disposition hint:** likely-fix
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** autoiterate-budgets-defer-ledger
- **Defect / goal:** one HUMAN finding vetoes the rebuild outright —
  `eligible()` (`autoiterate.py:56`, return at `:74-75`) requires every non-IMPL item
  to be STANDING, so auto-iterate fired on 13.5% of eligible-checked attempts (31/230;
  two maintainer-reported broken bundles spent ZERO rounds, vetoed at eligibility),
  and the round budget — the thing meant to bound iteration — is never the binding
  constraint. Deliver items 1 and 4 of issue #332: soft/hard round budgets with a
  convergence test, and HUMAN findings deferring to a loss-proof ledger instead of
  blocking — folding in the #335 retirement defect fix (per the maintainer's triage:
  it must be fixed *inside* this change; the instance implementation shipped with it)
  and the #324 size-backstop composition from the issue's landing checklist.
- **Success criterion:** (1) with `soft_auto_iters`=3, `max_auto_iters`=5, the worked
  example holds: rounds n≤3 always fire (no convergence test); 3<n≤5 fire only if the
  per-round IMPL finding count did not increase; n>5 never; `soft_auto_iters` unset
  defaults to `max_auto_iters` so a rendered instance reproduces today's behaviour
  exactly; both clamped strictly below `max_passes`; `auto-iterate.json` carries the
  per-round IMPL counts with `count()` tolerant of the old `{"count": n}` shape.
  (2) `eligible()` becomes "≥1 IMPL item": HUMAN findings beside IMPL items defer to a
  `deferred-findings.json` ledger kept out of `driver.DOWNSTREAM_OF_BRIEF`, listed in
  `state.CYCLE_EVIDENCE_ONLY` (`state.py:108` — membership pinned against the module
  constant so a rename breaks loudly), and merged deduped into §6 at
  `assemble_summary` so every deferred finding reaches the human at handover under the
  C6 guard; empty §6 still halts (never auto-accept); HUMAN-only sets still halt
  immediately; `rationale()` (`autoiterate.py:93`) states what was addressed AND what
  was deferred, and still carries IMPL items only into the builder's carry-forward
  (the #294 property: a human-only judgment call is never handed to Do as a defect).
  (3) **The #335 fold:** ledger retirement (`retire_cleared`, new) recognises a
  still-open §6 row with the SAME `_same_finding` relation the tick match uses,
  assigned exact-first, two-tier: a still-open row *verbatim equal* to a ledger entry
  protects that entry ALONE (a near-twin cannot shield its exactly-ticked neighbour,
  so near-twin pairs still drain); an *edited* open row (verbatim owner of nothing)
  protects EVERY entry it `_same_finding`-matches — fail closed. NOT the flat
  symmetric-fuzzy exclusion (`any(_same_finding(entry, o) for o in still_open)`): that
  re-creates the permanently-unclearable pair. Shape proven in the instance
  (getwyrd/wyrd-pdca@e4fdf3b): a `protected: set[int]` computed once before the tick
  loop; the tick loop's guard becomes `hits[0] not in protected`. The ticked-rows
  reader gets the explicit `whole_on_missing=True` contract (the lenient §6 side — it
  is read together with `open_needs_human` by `retire_cleared`). Three fold tests:
  (a) the #335 repro — an annotated-unticked row plus a similar ticked new finding →
  the unadjudicated entry survives; (b) a matcher-drift guard — every edit shape
  `_same_finding` tolerates in a tick must also protect when left open, even against
  an exact tick; (c) an edited open row matching two near-twin entries protects both.
  (4) **The #324 composition:** the size backstop stops the loop by *kind*, not by
  disqualifying all HUMAN items — `if any(item.kind == HUMAN and
  size_signal.is_size_item(item.text) for item in items): return False`, then
  `return any(item.kind == IMPL …)`; ordinary HUMAN items defer, the size item stops
  the loop, the same text tagged IMPL still rebuilds; both directions of #324's
  `test_the_tag_is_the_mechanism` pass, and the two `test_size_signal` flow tests get
  this branch's fixture adaptations (an IMPL + ordinary-HUMAN set now *fires*, so the
  "declines silently" case becomes HUMAN-only; the decline path records the
  convergence observation, so fixtures need a real bundle dir plus the soft-budget
  config field).
- **Falsifiability:** the offline driver suite on this host
  (`cd template && PYTHONPATH=src python3 -m unittest tests.test_autoiterate` and
  `tests.test_size_signal`), run by the C4 gate (`engine/scripts/run-verify.sh`,
  revert-production-hunks contract — appended tests earn their red). RED now, per
  clause: (1) `soft_auto_iters` is unparsed (`config.py:276` dataclass field and
  `:598-601` parse only `max_auto_iters`); (2) a HUMAN item beside IMPL items vetoes
  at `autoiterate.py:74-75` (`all(item.kind in (IMPL, STANDING) …)`), and
  `deferred-findings.json` is absent from `state.CYCLE_EVIDENCE_ONLY`
  (`state.py:108` holds exactly two names); (3) `retire_cleared`/`_same_finding` do
  not exist upstream — the ledger ships with the exact-first protected-set shape from
  day one, and tests (a)+(b) go red against both the pre-fix instance shape
  (fuzzy select / exact-text exclude) and the symmetric-fuzzy variant; (4) #324's
  `test_the_tag_is_the_mechanism` direction "ordinary HUMAN beside IMPL fires" is red
  under today's veto.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** child-1
- **Ordering note:** child-1 also edits `assemble.py` and `test_autoiterate.py` —
  shared files, no functional dependency (this child's `eligible()` rework operates on
  the `NeedsHumanItem.kind` interface that exists on main; IMPL items already occur in
  production, 31/230). Different waves; the wave fold composes the shared-file edits.
  Also conflicts with in-flight #369 (same `assemble.py` §6 assembly + driver Check
  sequencing) — added to the materialised brief post-accept. #335 is NOT a separate
  bundle: its defective code exists only downstream; the fix shape is folded here.
- **Difficulty:** high
- **Scope (one logical fix) / out of scope:** issue #332 items 1, 4 plus the #335 fold
  and the #324 composition, exactly as in the success criterion — `config.py`
  (`soft_auto_iters` beside `max_auto_iters`, default-to-hard when unset, clamps),
  `autoiterate.py` (round gating, per-round IMPL counts in `auto-iterate.json`,
  `eligible()`, `rationale()`, the ledger + `retire_cleared`), `state.py`
  (`CYCLE_EVIDENCE_ONLY`), `driver.py` (ledger out of `DOWNSTREAM_OF_BRIEF`),
  `assemble.py` (merge deferred findings, deduped, into §6 at assemble),
  `flow.py`/`size_signal.py` touchpoints for the #324 composition,
  `template/pdca.toml.jinja` + docs for the new config key; tests: table-driven round
  gating over the worked example, C5/T5-beside-IMPL defers vs C5/T5-alone halts,
  round-1 HUMAN finding still in §6 at handover,
  `test_empty_section6_halts_and_never_auto_accepts` passing unchanged, the three #335
  fold tests, the #324 adaptations. / out of scope: the `[impl]` tag, prompt changes,
  `_PROMOTABLE_ELEMENTS`, V-row normalization (child-1); routing input-cell defects to
  `iterate-plan` (`autoiterate.DECISION` stays the single `iterate-do` token, guard
  unchanged); #334 itself (landed — this change only adds the new ledger file to the
  existing `CYCLE_EVIDENCE_ONLY`).
- **Reproduction:** construct `[NeedsHumanItem(kind=IMPL), NeedsHumanItem(kind=HUMAN)]`
  → `eligible()` returns False today (the veto); `Config` has no `soft_auto_iters`
  attribute. Both as unittests in the named test file.
- **External dependencies:** none
- **Test file:** template/tests/test_autoiterate.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites verified on main: `eligible` `autoiterate.py:56` (veto at `:74-75`),
  `count`/`bump` + `BUDGET_FILE` `autoiterate.py:50,79-91` (extend the JSON shape,
  keep `count()` tolerant), `rationale` `:93`, `DECISION` guard `:53`;
  `max_auto_iters` `config.py:276` (parse `:598-601` — mirror for `soft_auto_iters`,
  clamp ≤ hard, both < `max_passes`); `CYCLE_EVIDENCE_ONLY` `state.py:108` and its
  archive guard `state.py:167`; `driver.DOWNSTREAM_OF_BRIEF` `driver.py:34` area;
  `size_signal.is_size_item` `size_signal.py:269`; the flow's auto-iterate callsite
  `flow.py:660` area (isolated: an auto-iterate that raises must not break the flow).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline
  origin/main -- template/src/pdca_harness/autoiterate.py
  template/src/pdca_harness/config.py template/src/pdca_harness/state.py` —
  #293/#294/#324/#334 history present; `soft_auto_iters` absent from `config.py`, no
  `retire_cleared`/`_same_finding`/`deferred-findings.json` anywhere upstream
  (re-verified 2026-08-02, confirming #335 has no upstream code to fix separately).
  Instance prototype getwyrd/wyrd-pdca#167 (reconciled with v0.56.0 in
  getwyrd/wyrd-pdca#195) exists downstream only and carries the #335 bug — the fold is
  binding. The parent's iteration-v1 patch implements this shape and passed
  C4/advisory — carry the implementation shape, re-cut to this child's scope.
- **Disposition hint:** likely-fix
<!-- pdca:end child-2 -->
