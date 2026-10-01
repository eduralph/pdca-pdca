# Advisory code review — issue 477 (size-signal: discount deferred-gate rounds)

Lens: bugs the patch introduces, plus reuse and simplification. Line numbers are from
the patched target tree (`target/template/...`).

The gate evidence holds up. `gate-logs/C4-verify.log` shows the suite at 65 tests, OK
with the fix and 5 failures without it. All the #446 tests and
`test_the_calibrator_uses_THIS_definition` still pass. The patch reuses the shared
parser as the brief asks: review and advisory findings both go through
`assemble._items_from_artifact`, and the element match uses `assemble._ELEMENT_RE`. Every
fail-safe path still returns False, so the round still counts. I found no resource,
ordering or exception-handling bugs.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/size_signal.py:204-210`: the deferred set is
  keyed by **element** only, and one element can have more than one gate row. T2 already
  has two on this project (`T2-docs` and `host-ci-docs`). Suppose one row of an element is
  `deferred` and a sibling row of the same element is a **non-gating** `fail`. The
  reviewer flags that failing sibling. The finding's leading id matches the deferred
  element, so the round is discounted, even though the finding is about a live, failing
  check. Check (a) only catches gating fails. This follows the brief as written ("equals
  the `element` of an archived gate row whose `result` is `deferred`"), so it is a scope
  choice, not a builder slip. A tighter rule would treat an element as deferred only if
  none of its rows is `fail` or `unverifiable`. No test covers an element whose rows
  disagree. On T4 today (one row) this cannot happen.
- `template/src/pdca_harness/size_signal.py:210` together with `:279`: on the primary
  review the patch ignores `kind` and matches by element only. A primary-review bullet
  `- NEEDS-HUMAN [impl] — T4 …` has its `[impl]` marker removed by
  `assemble._classify_finding` (`assemble.py:269-271`). After that, the text starts with
  `T4`, so the round is discounted, even though the reviewer explicitly tagged the item as
  something a rebuild can fix. The advisory path does the opposite (`:311` charges on
  IMPL). This is low stakes: reviewer table rows on gate elements already classify as
  IMPL without a marker, so `kind` cannot separate the two cases here, and the brief puts
  classification out of scope. I am noting it, not asking for a change.
- `template/src/pdca_harness/size_signal.py:283-288`: `_review_drove_the_iterate` no longer
  has a production caller. Only `tests/test_attempt_harvest.py:593` and `:684` use it. As
  a thin wrapper over `_review_findings` it is harmless, but it is now test-only API.
  Either say so in its docstring, or point those two tests at `_review_findings` and
  delete the wrapper. This is a cleanup, not a defect.
- `template/src/pdca_harness/size_signal.py:238-246`: `_element_of` re-imports `assemble`
  on every call (once per finding). That is cheap, since it hits the module cache after the
  first time. Moving the `_ELEMENT_RE` match inline, inside `_review_findings` or next to
  line 210, would also be fine. A minor style point.

Apart from the element-keying scope question above, the diff is clean on both lenses.
