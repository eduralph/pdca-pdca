# split: record lineage in the child and parent bundles (the schema children 2-4 and #449 read)

- **Slug:** split-lineage-record
- **Defect / goal:** `pdca split --accept` records nothing locally about the split it just
  performed. `materialise` writes only the child's `brief.md` (`split.py:348-362`), and the
  "Child slice of #N" breadcrumb goes solely into the filed tracker issue body
  (`split.py:609-687`, `body_head` at `:636` is the only place it is recorded today). On
  disk a split child is therefore indistinguishable from a fresh oversized brief — to
  `sizing.estimate`, to `plan_policy.size_reasons`, to the sizer leaf, to
  `leaves._plan_prompt`, and to `pdca flow`. Ship the missing provenance: a machine-readable
  lineage record in each child bundle *and* in the parent, plus one tolerant reader for it.
  Nothing else consumes it in this slice — it is the declared contract that children 2-4 and
  issue #449 build on, which is why it lands first and alone.
- **Success criterion:** after `split.accept(parent, ids, cfg)` —
  1. each created child bundle contains `split-lineage.json` naming its `parent`, its
     `siblings` (the *other* children of the same split, by tracker id) and its `depth`
     (parent's depth + 1, so recursion depth is recorded without anyone counting);
  2. the parent bundle contains `split-lineage.json` naming its `children`;
  3. **the mixed-role case is preserved**: for a parent that *itself* already carried a
     child record, the post-accept record still carries its own `parent` and `siblings`
     **and** gains `children`. This is the specific defect the previous attempt shipped —
     it overwrote the child record with a parent one, keeping only `depth`, so a depth-1
     bundle silently lost its sibling set and the whole ratchet returned at depth ≥ 1
     (reproduced: bundle 601 scored `6 / watch` with no advisories; after
     `split.accept(601, [701,702])` it was back to `9 / oversized`). A test must accept a
     split whose parent is itself a child and assert both edges survive — asserting only
     that `depth` survives blesses the loss rather than catching it;
  4. one tolerant module-level reader returns the parsed record, or `None` for an absent,
     unreadable, malformed or wrong-`version` file. It never raises: a provenance reader
     that can throw into a beat is worse than one that abstains, and every consumer must
     behave exactly as today when it returns `None`;
  5. the record is **not** added to `state.DOWNSTREAM_OF_BRIEF` (`state.py:82-110`), so it
     survives `iterate-plan` and the archiving of a rejected attempt — it is provenance,
     not attempt output. Assert this by name in a test, not in a comment;
  6. the existing transactional discipline is preserved: child records are written into
     `staging` and moved with the rest (`split.py:348-362`, moved by `accept` at
     `:406-427`), and the parent's record is written **before** `CLOSE_MARKER`
     (`split.py:453-461` region) so a failed write leaves the parent un-marked and
     `_rollback` still correct. A failed accept restores the parent's prior record bytes.
- **Schema (the contract — this is the interface decision, and it is settled here):** one
  file, `split-lineage.json`, carrying *independent optional edges* and **no** `role`
  discriminator:
  ```json
  {"version": 1, "id": "601",
   "parent": "500", "siblings": ["602", "603"],
   "children": ["701", "702"],
   "depth": 1}
  ```
  `parent`/`siblings` are present iff the bundle is a split child; `children` is present iff
  the bundle has been split. Writing a parent record **merges into** any existing record
  rather than replacing it. A `role` field was tried and rejected in the previous attempt
  for exactly the reason item 3 describes: one filename carrying one role cannot express a
  bundle that is both, and one filename is required because #449 needs the parent→children
  edge while children 2-4 need the child→parent/siblings edge, and two files would drift.
  The prose breadcrumb in the parent's `build-notes.md` stays — this is its parseable
  inverse, not a replacement.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** n/a — new functionality. The gap is directly observable:
  `git -C ../pdca-harness grep -rn "lineage" template/src/pdca_harness/` returns nothing,
  and after `pdca split 500 --accept --ids 601,602` each child bundle contains `brief.md`
  and nothing else.
- **Falsifiability:** RED is producible on the ordinary offline driver suite — `cd template
  && PYTHONPATH=src python3 -m unittest tests.test_split_lineage`, which is what
  `engine/scripts/run-verify.sh` runs for a `template/tests/*.py` test. Pre-fix **no lineage
  file exists at all**, so every assertion on it fails and every `split.<new_name>` attribute
  access raises `AttributeError` — a genuine red, empirically confirmed on the previous
  attempt's red leg (`7 failures + 13 errors`). This is a wave-0 bundle, so the gate verifies
  against the brief's own branch target with no `PDCA_BASE`/`PDCA_VERIFY_BASE` export
  (`gates.py:389-397`). Pure functions of files — no network, tracker, `gh` or container.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/split.py` (the
  filename constant, the writer, the tolerant reader), one docs row describing the artifact
  and its schema in `docs/07-crosscutting.md` `### The split` (`:174-218`, the section that
  already documents `--accept`'s transactional guarantees), and the new test module.
  **Out of scope:** every *consumer* of the record
  — `sizing.estimate` (child-2), `plan_policy.size_reasons` and the leaf prompts (child-3),
  the convergence report (child-4), `flow.py` (issue #449). No weight, no cutoff, no remedy
  wording, no `pdca.toml.jinja` change. Do not edit `state.py`'s `DOWNSTREAM_OF_BRIEF` list
  — the record's *absence* from it is the point.
- **External dependencies:** `copier importable (.venv)` — this patch changes files under
  `template/`, so the target's render and `copier update` compatibility suites at the target
  root exercise it. Without copier those seven tests skip themselves and T3 reports a green
  that tested nothing. Otherwise python3 ≥ 3.11 stdlib + git only: the test runs in the
  offline driver suite with no tracker, network or container.
- **Test file:** `template/tests/test_split_lineage.py` — a new module in the offline driver
  suite, run by `engine/scripts/run-verify.sh` as `cd template && PYTHONPATH=src python3 -m
  unittest tests.test_split_lineage`. The C4 gate reverts only the PRODUCTION hunks and
  keeps the test (`run-verify.sh:121-130`, `--exclude=tests/* --exclude=template/tests/*`),
  so a new file in `template/tests/` earns a genuine red.
  **Import the module, never the new symbols.** Use `from pdca_harness import split`, then
  `split.<new_name>` inside test bodies. A module-level `from pdca_harness.split import
  <helper>` raises ImportError on the red leg, so 0 tests run and `run-verify.sh` exits 77
  `PDCA-UNVERIFIABLE` instead of red (`run-verify.sh:145`) — the test would prove nothing.
  Attribute access inside a body yields `AttributeError`, which is a real red; this was
  confirmed on the previous attempt's red leg (`7 failures + 13 errors`).
- **Difficulty:** medium

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: C3 FAIL (verified): the parent-lineage snapshot read at template/src/pdca_harness/split.py:511 (`prior_lineage_bytes = lineage_path.read_bytes() if lineage_path.exists() else None`) sits in the gap between accept()'s two protected regions — after the children are moved into place, before the try block whose except performs _rollback(created) + prior-bytes restore + marker-unlink. If the path exists but read_bytes() raises (e.g. a directory at split-lineage.json — a case the patch's own tolerant-reader tests construct — or a permissions error), the exception escapes with children materialised and the parent left open, violating the brief's item 6 transactional guarantee. Fix: move the snapshot inside the protected try (the restore logic already handles None vs bytes) or otherwise ensure a snapshot-read failure triggers _rollback(created); add one test — a parent with a directory at the lineage path must fail accept() cleanly (no children left, no CLOSE_MARKER, no lineage record). Everything else stands: mixed-role merge, tolerant reader, staging discipline, DOWNSTREAM_OF_BRIEF exclusion, and the real copier T3 run (7/7 root tests passed) are good — keep the approach, harden only this one boundary.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T4 Contribution — Re-run the contribution lint against the actual commit and PR artifacts before publish — those artifacts are absent from the reviewer inputs, so the checker correctly returned deferred at `template/src/pdca_harness/cli.py:1089` and the recorded PASS cannot be independently confirmed.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
