# Build notes — issue 477 / size-signal-discount-human-class-rounds

Target: eduralph/pdca-harness @ main, built on the folded wave base in `$PDCA_WORKTREE`
(`00dc958 pdca-integrate: issue_409` on top of `9405658`). Line numbers below are on that
tree with the patch applied.

## What changed

All production changes are in `template/src/pdca_harness/size_signal.py`.

- `iteration_rounds` docstring, `size_signal.py:131-140`: names the new #477 discount next
  to the #436 one.
- `_environment_attributed`, `size_signal.py:154-216`: now one rule, "every recorded driver
  of the round is non-slice", exactly the Design section's (a)-(d):
  - (a) no plain gating `fail` (unchanged, `:202-203`);
  - deferred-element set built from ALL rows, gating or not (`:204-206`);
  - (c) primary review readable, not a placeholder, no FAIL cell (`:207-209`), and every
    non-STANDING finding sits on a deferred element (`:210-212`);
  - (b) at least one of: an `unverifiable`/`flaky` gating row, or a finding on a deferred
    element (`:213-215`);
  - (d) no archived advisory with an IMPL item or a placeholder (`:216`).
  I kept the function name because `iteration_rounds` and the #446 tests refer to it; the
  docstring says the name is historical.
- `_archived_gating_rows` → `_archived_gate_rows`, `size_signal.py:219-235`: returns all
  rows; the caller filters to gating rows. Needed because clause 1 requires a non-gating
  `deferred` row to still count. No other callers (grepped the tree).
- `_element_of`, `size_signal.py:238-246`: reads the leading id with
  `assemble._ELEMENT_RE` (`assemble.py:64`), as the brief asks. It does not re-derive the
  pattern.
- `_review_findings`, `size_signal.py:249-280`: the old `_review_drove_the_iterate` body,
  but it returns the non-STANDING items (or `None` for missing / placeholder / FAIL cell)
  so the caller can check each item's element. It still reads only through
  `assemble._items_from_artifact(text, allow_standing=True)`, so there is one parser.
- `_review_drove_the_iterate`, `size_signal.py:283-288`: kept as a thin wrapper with the
  same meaning as before, because `template/tests/test_attempt_harvest.py:593,684` calls it
  directly. Those tests pass unchanged.
- `_advisory_drove_the_iterate`, `size_signal.py:291-313`: reads `check-advisory-*.md` in
  the archive (archived by `state.DOWNSTREAM_GLOBS`, `state.py:155`) the way
  `collect_needs_human` does (`assemble.py:326-330`, no `allow_standing`). It charges on an
  IMPL-kind item, a `leaf_status` placeholder, or an unreadable file. A plain
  `- NEEDS-HUMAN —` bullet is HUMAN and does not charge.

`template/pdca.toml.jinja` (`:285-307`) was left alone: its `[driver.size_signal]` comment
does not describe what is discounted, so the brief's condition for editing it ("if it
describes what is discounted") is not met. Leaving it out also avoids touching the file 371
shares.

## Tests

`template/tests/test_size_signal.py`, appended to `RoundsAreAttributedToTheSliceNotTheEnvironment`:

- Fixtures: `_archive` gains an optional `advisory=` (`:576-587`), `_two_round_bundle` gains
  `v1_advisory=` (`:589-597`). Both default to the old behaviour. New helpers
  `T4_FINDING`, `_t4_deferred`, `_deferred_round` (`:719-736`).
- Clause 1: `:738` (deferred T4 + T4/V review → `(1, 0)`), `:745` (same, through
  `measure`/`oversize_reasons`), `:752` (non-gating deferred row still discounts), `:758`
  (Item cell without a leading id → `(2, 0)`).
- Clause 2: `:767` subtests — plain gating fail, T3 / C5 / T5 findings, FAIL cell, advisory
  `[impl]`, advisory placeholder, placeholder review, missing review, missing and malformed
  `check-gates.json`; `:809` V-only with a deferred row present → `(2, 0)` (the decided
  Open question); `:816` plain advisory bullet on the new path → still `(1, 0)`.
- Clause 3: `:822` #446 round + advisory `[impl]` → `(2, 0)`; `:830` #446 round + plain
  advisory bullet → still `(1, 0)`.
- Clause 4: every existing test in the file passes unchanged (65 total, OK), including
  `test_the_calibrator_uses_THIS_definition`. The full template suite also passes:
  `python3 -m unittest discover -s tests` → 2144 tests, OK (2 skipped).

## Red → green (through the project runner)

`PDCA_BUNDLE=… ./engine/scripts/run-verify.sh` (the C4 gate, with `$PDCA_WORKTREE` set):

```
== C4 green leg: … Ran 65 tests … OK
== C4 red leg: … Ran 65 tests … FAILED (failures=5)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The 5 red tests are the ones asserting new behaviour: `:738`, `:745`, `:752`, `:816`
(deferred discount) and `:822` (advisory tightening of a #446 round). The others in the
new block are guards that hold both before and after (they assert "still counted"), which
the brief's clause 2 asks for.

## Refuting my own test

- **(a) Genuine red?** Yes. I reverted only `size_signal.py` (`git checkout` of that file)
  and re-ran: 5 failures, e.g. the clause-1 bundle read `(2, 0)` and the clause-3 bundle
  read `(1, 0)` — exactly the brief's Falsifiability. `run-verify.sh` repeated this on its
  own red leg and reported the same 5 failures.
- **(b) Production path?** Yes. Every new test calls `size_signal.iteration_rounds` (or
  `measure`, which calls it), the function the backstop and `scripts/size-calibrate` use.
  No mocks; the review and advisory text goes through the real
  `assemble._items_from_artifact` / `leaf_status`.
- **(c) Fixture includes the fault?** Yes. The fixtures write real archive files
  (`iteration-v<N>/check-gates.json`, `check-review.md`, `check-advisory-adversary.md`) in the
  shapes the writers produce: gate rows in `gates._finalize` shape with `result: deferred`
  and `element: T4`; the review as a verdict table with a `T4 …` Item cell; the placeholders
  built from `assemble.LEAF_STATUS_INFRA`, `REVIEW_UNAVAILABLE_FINDING` and
  `ADVISORY_UNAVAILABLE_FINDING`, as `leaves._review_unavailable` /
  `_advisory_unavailable` write them.

## Alternatives ruled out

- Leaving `_review_drove_the_iterate` as the only review reader and adding a separate
  "deferred findings" scan: that would parse `check-review.md` twice, through two code
  paths, which the existing docstring (PR #294 review) warns against. Instead
  `_review_findings` returns the items once and both the deferred check and the old
  boolean wrapper use them.
- Classifying by `NeedsHumanItem.kind` alone: a T4 row on a deferred gate is IMPL by
  `assemble._classify_finding` (`assemble.py:274-276`), the same as a T4 row on a live
  gate, so kind cannot tell them apart. The element id plus the gate row's `deferred`
  result can.
- Applying the advisory check only to the new path: the brief's clause 3 asks for one
  rule, and the Open question lists the narrower choice as the alternative. One rule is
  4 fewer lines than a branch on "which path discounted this", and it is the safe direction.

## Housekeeping (for the human)

Two stray files from my red-leg check, neither in `patch.diff`:
`$PDCA_WORKTREE/.prod.patch` (untracked, in the harness-owned worktree) and an empty
`/tmp/.unused` (a redirect I should not have written). I did not delete them, per the
no-cleanup rule; the harness reclaims the worktree.

No formatter or pre-commit hook is configured in the target (no `.pre-commit-config.yaml`,
no `core.hooksPath`, no ruff/black config; `.github/workflows` only has docs and
linked-issue checks). `git diff --check` is clean, and new lines stay within the file's
existing width (longest is 96 chars; the file already has lines near 100).
