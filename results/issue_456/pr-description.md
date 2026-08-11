## Summary

**User impact:** When you split an oversized item into smaller ones, nothing on disk
remembers that the split happened. The "Child slice of #N" note goes into the filed
tracker issue and nowhere else, so a child's own directory looks exactly like any
other oversized brief. Anyone — or anything — that picks that directory up later
cannot tell that the work has already been sliced, which items it was sliced
alongside, or how many rounds of slicing it took. The consequence people actually
hit: a slice that is already small is treated as if it were the original oversized
item all over again, and the advice to split it comes back around a second time.

This change makes the split write its own record into every directory it touches, so
the relationship survives outside the tracker.

Reported in [#456](https://github.com/eduralph/pdca-harness/issues/456).

## What to look at

One module plus one docs paragraph: `template/src/pdca_harness/split.py` and the
`### The split` section of `docs/07-crosscutting.md`. Accepting a split now writes a
small `split-lineage.json` into each child (its parent, its siblings, its depth) and
into the parent (the children it produced), and reads it back through a single
deliberately unshakeable reader. Nothing consumes the record yet — this PR ships the
file and its schema on their own, so the pieces that will read it are all built
against one settled shape rather than each inventing its own.

To try it: take a bundle with a split proposal and accept it (`pdca split <id>
--accept --ids …`). Previously each new child directory contained a `brief.md` and
nothing else; now it also carries a lineage record, and the parent's directory gains
one naming the children. Split one of those children in turn and its record keeps its
own parent and siblings while gaining its children — the case worth staring at, since
that is the one where a record that replaced rather than merged would silently lose
half the relationship.

Two behaviours are intentional and easy to mistake for oversights. A corrupted or
hand-edited record is never allowed to break a run: the reader simply reports nothing,
and a `depth` that is not a number is ignored for the arithmetic instead of raising.
And the record is deliberately *not* in the list of files that re-planning archives,
because it describes the split, not any one build attempt.

## Root cause

The provenance was only ever written to the tracker: `materialise` wrote each child's
`brief.md` and stopped there (`template/src/pdca_harness/split.py:348-362` on `main`),
and the sole record of the parent→child edge was the issue body composed at
`split.py:636`. Nothing was written into the parent either, so even the local half of
the relationship was unrecoverable without querying the tracker — and a machine-
readable inverse of that breadcrumb had no home at all.

## Fix

`accept` now writes one file, `split-lineage.json`, carrying independent optional
edges and no role field: `parent`/`siblings`/`depth` if the bundle is a child,
`children` if it has been split, both if it is both. A parent's record is *merged*
into whatever it already carried, which is what keeps a child-of-a-child whole; a
single reader returns the record or nothing at all, catching every failure to read
rather than an enumerated list of the ones anyone thought of, and depth arithmetic
abstains on a value it cannot compute with. The write is folded into the accept's
existing all-or-nothing discipline: children's records are staged and moved with their
briefs, the parent's is written before the close marker, a failed accept restores the
parent's previous bytes exactly, and a record that cannot be read refuses the accept
before anything is staged — since one that cannot be read cannot be restored.

## Verification

- **Claim:** after an accepted split, each child records its parent, its siblings and
  its depth (the parent's plus one), and the parent records its children.
  **Checked:** `template/src/pdca_harness/split.py:348-362` on `main` — `materialise`
  wrote `brief.md` and nothing more; `split.py:636` — the only place the edge existed.
  In this PR: `split.py:472-501` (child records, staged) and `split.py:619` (parent
  record). **Test:** `template/tests/test_split_lineage.py:80`, `:95`.
- **Claim:** a bundle that is both a child and a parent keeps both edges — the
  regression that would otherwise return at every level below the first.
  **Checked:** `split.py:433-449` in this PR — the parent record merges into the
  existing one instead of replacing it, carrying `parent`, `siblings` and `depth`
  through. **Test:** `template/tests/test_split_lineage.py:104` seeds a real child
  record on the parent before accepting and asserts both edges survive; `:123` asserts
  depth keeps accumulating through such a parent.
- **Claim:** the reader never raises — absent, unreadable, non-UTF-8, malformed,
  non-object, deeply nested or wrong-version all yield nothing, and a corrupt record
  cannot crash the accept that reads it.
  **Checked:** `split.py:373-403` (the read/decode/parse in one guarded step) and
  `split.py:405-421` (a `depth` that is not a non-negative integer contributes 0).
  **Test:** `template/tests/test_split_lineage.py:133-212` for the reader, and `:214`
  / `:236` push a non-UTF-8 record and a non-numeric `depth` through `accept` itself
  and assert the split still completes — a reader-only probe can be green while the
  caller one frame up still dies.
- **Claim:** the record survives re-planning, which archives a rejected attempt's
  output.
  **Checked:** `template/src/pdca_harness/state.py:82-114` on `main` — unchanged by
  this PR; the record's absence from that list is the point. **Test:**
  `template/tests/test_split_lineage.py:257` asserts the filename by name, and `:262`
  first proves the archive really ran before asserting the record was left alone.
- **Claim:** the existing all-or-nothing guarantee is preserved.
  **Checked:** `split.py:556-570` (the parent's prior bytes are read in the pre-write
  phase, so an unreadable record refuses while refusing is still free), `split.py:619`
  written before the close marker at `:635`, and the restore at `:642`. **Test:**
  `template/tests/test_split_lineage.py:304-421` — staging, ordering, byte-for-byte
  restore, no-prior-record cleanup, and a refusal that never reaches `shutil.move`.
- **Test:** `template/tests/test_split_lineage.py` (new, 23 cases) — fails pre-fix,
  passes post-fix. Run with `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_split_lineage`. With the production changes reverted and the test kept,
  all 23 error out on the missing behaviour; with them restored, 23/23 pass.
- **Suites:** the offline driver suite is green at 1622 tests; the template render and
  `copier update` compatibility suites are green at 7 tests with copier 9.17 actually
  installed, so they exercised a real render rather than skipping themselves. Docs lint
  and the site render/link audit are green over the new `docs/07-crosscutting.md:217-241`
  paragraph.

Fixes #456
