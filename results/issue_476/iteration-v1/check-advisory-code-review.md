# Check — advisory code review (issue #476, lineage-reader-doc-matches-the-reader)

Docs-only patch (`docs/07-crosscutting.md`, one hunk, ~5 lines). No production code
touched (`split.py` is out of scope and untouched, per brief). Both lenses below,
scoped strictly to this diff.

## Correctness (of the claim the patch makes)

Cross-checked the corrected paragraph against the actual implementation:

- `docs/07-crosscutting.md:282-283` ("returns `None` … for *any* way of failing to
  **parse** it") matches `read_lineage` (`target/template/src/pdca_harness/split.py:583-612`):
  the only `return None` paths are the total `except` around read/parse and the
  `isinstance`/`version` check.
- `docs/07-crosscutting.md:284-286` ("A `depth` it parses fine but can't compute with …
  is absorbed one layer down instead, by the depth arithmetic, which treats it as unknown
  (`0`) so the child lands at depth 1") matches `_recorded_depth`
  (`target/template/src/pdca_harness/split.py:615-631`) and is pinned by
  `target/template/tests/test_split_lineage.py:236-251`.
- The false clause named in the brief ("and for a `depth` that isn't a number") is gone;
  no other sentence in the paragraph or file was touched, matching the brief's scope.

This is a well-grounded, narrowly-scoped correction — no bug introduced, nothing to
reuse/simplify (no code changed, no hot path involved).

## Minor prose-precision nit

- NEEDS-HUMAN [impl] — `docs/07-crosscutting.md:284-286`: the sentence "…absorbed one
  layer down instead, by the depth arithmetic, which treats it as unknown (`0`) so the
  child lands at depth 1 **and the parent's own record is left untouched**" grammatically
  attributes *both* consequences to "the depth arithmetic … treats it as unknown (0)".
  The child-depth-1 outcome is indeed produced by `_recorded_depth` (`split.py:615-631`,
  called from `materialise`, `split.py:~625`). But the parent's record being left
  untouched is a *different* mechanism: `_merge_parent_lineage` (`split.py:642-657`)
  copies `depth` (and `parent`/`siblings`) through **verbatim** from the existing record
  without ever calling `_recorded_depth` on it — it would be left untouched regardless of
  what the depth arithmetic does. As written, a careful reader could infer a causal link
  between "depth arithmetic treats it as unknown" and "parent's record is untouched" that
  doesn't exist in the code; the two facts are correct individually but not connected the
  way the sentence implies. Given this brief exists specifically because doc precision on
  this exact reader/arithmetic split previously produced false review findings (issue
  #456), this is worth a wording pass (e.g., splitting into two independent clauses) even
  though it doesn't misstate any individual fact — a human/builder call on whether the
  ambiguity clears the bar to fix now or is accepted as close enough.

No other findings. Nothing in this diff duplicates existing logic, adds needless work, or
introduces a resource/concurrency/API-misuse risk — it's a text-only doc edit with no code
or test surface.
