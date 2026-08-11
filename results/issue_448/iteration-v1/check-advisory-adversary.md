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
