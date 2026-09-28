# Check advisory — code review (second lens: bugs the patch introduces / reuse / efficiency)

Scope: only `template/src/pdca_harness/leaves.py`, `template/src/pdca_harness/assemble.py`
and the new `template/tests/test_attempt_harvest.py`, as touched by this diff. Verified
against target source at `$PDCA_TARGET`. The three prior sign-off findings (live-verdict
destruction by an un-owned refusal, unbounded residue quoting into a tracked file, and the
unknown-status fallback demoting real findings) all read as genuinely fixed in this build —
`_live_attempt_overwrote_it` settles ownership by digest, `_read_residue` bounds head/tail,
and `_written_as_a_placeholder` restricts the unknown-token fallback to the header region.
C4's log confirms an honest red→green through the real entry points.

## Findings

- NEEDS-HUMAN [impl] — `withdraw()` (`leaves.py:861-884`, called from the retry loop at
  `leaves.py:751-752`) re-reads and re-quotes the **same** un-removed residue for **every**
  subsequent dead attempt, mislabelling it as that attempt's own output. Once one attempt's
  file cannot be `unlink()`ed (the exact scenario the patch's own `lock=True` legs build),
  the file is still sitting at `self.produced` when the *next* attempt dies too — `withdraw()`
  has no "have I already accounted for this exact residue?" check, so it reads it again,
  fails to unlink it again, and returns another `_record(attempt, …)` block claiming
  *that* attempt "left" the file at `self.produced.name`, even though the script never wrote
  to it on that invocation (n != 0 in the stub's own script, `test_attempt_harvest.py:594`).
  Concretely: `_drive(..., deaths=3, lock=True)` (exercised by
  `test_attempt_harvest.py:837-847`, `test_an_unwithdrawable_residue_does_not_narrow_the_retry_contract`)
  produces a settled `check-review.error.log` with the *same* residue quoted three times,
  attributed to attempts 1, 2 **and** 3 — reintroducing, one level down, the very defect this
  issue exists to remove ("no notion of *which attempt* wrote it"), plus tripling the
  read+sha256 work on a large residue for no benefit. The existing test only asserts
  `assertIn(_DEAD_MARK, …)` and the attempt count, so it doesn't catch the duplication/
  misattribution. Fix direction: track the digest(s) already disowned (`self._residues` is
  already populated for exactly this) and have `withdraw()` return `""` (or a
  "same as a prior attempt's" note, not a fresh "attempt N left…" block) when the file at
  the path is unchanged from what a previous `withdraw()` call already recorded and failed
  to remove.

- No other correctness bugs found in the new `_LeafHarvest` / `_read_residue` /
  `_artifact_digest` machinery (`leaves.py:794-1001`) or in the `assemble.py` label/marker
  changes (`assemble.py:85-131, 199-217`): the success/failure branching in
  `_LeafHarvest.run` (`leaves.py:838-859`), the sticky-conservative handling of an unreadable
  residue (`_unreadable`, `leaves.py:891-909`), the settlement-marker neutrality of the
  preserved account (`_WITHDRAWN_TRAILER` carries no `ATTEMPTS_SPENT_MARKER`, so
  `state.leaf_ran_and_failed` correctly reads `False`), and the three call sites
  (`leaves.py:2838-2851`, `3194-3205`, `3497-3508`, not all quoted here) are all
  internally consistent and free of dangling references to the old `err`/`produced`
  pattern they replaced.

- Minor, not flagged as an action item: `_read_residue` (`leaves.py:954-985`) uses
  `fh.readline(_RESIDUE_READ)` to bound line length, which can split a multi-byte UTF-8
  character across two 1000-byte reads and introduce a stray `�` at that boundary when
  decoding with `errors="replace"`. This only affects the *quoted, truncated* display text
  in a tracked error log (never the digest, which hashes raw bytes), so it's cosmetic at
  worst — noting it rather than raising it, since it doesn't affect any success criterion.

## Reuse / simplification / efficiency

- Criterion 6 (one owner, not three copies) reads as genuinely satisfied: all three sites
  now differ only in their paths and their own §6 prose, exactly as the brief asked
  (`leaves.py:2838-2844`, `3194-3199`, `3497-3502` — the `_LeafHarvest` construction+`.run()`
  call is identical in shape at each). No further de-duplication opportunity stands out.
- `_read_residue` and `_artifact_digest` both hash a file with `hashlib.sha256`, but they are
  not simple duplicates worth merging: `_read_residue` must also bound and return quoted text
  for a residue at withdrawal time, while `_artifact_digest` is a plain whole-file digest used
  once, after success, against a (potentially large, non-residue) live artifact — collapsing
  them would force the live-file path to also build a head/tail text it never uses. Leaving
  them separate is the right call here; flagged only because the finding above already touches
  the same code, not as an independent complaint.
