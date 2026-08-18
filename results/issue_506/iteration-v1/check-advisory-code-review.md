# Advisory code review — issue #506

Correctness lens: traced the new stream classifier (`progress.py`) and the retry
wiring (`leaves.py`) against the tests and the target source. The core mechanism —
`_terminal_error_text` / `_work_continued` setting `terminal["error"]`, folding it
into `produced`, and `_do_build_command` moving to `_invoke_leaf_resilient` with
`do_build`'s `_has_content` guard against clobbering the per-attempt log — is
internally consistent and the traced scenarios (fatal-then-exit, fatal-then-recover,
prose-mentioning-an-error, setup-vs-invocation failure) all resolve the way the
docstrings claim. No functional bug found that breaks the fix itself. Findings below
are all minor: a heuristic edge case worth a human's attention, and two cosmetic nits.

- NEEDS-HUMAN [impl] — `progress.py:420-422` (`_ERROR_LEAD_RE`) combined with
  `_TRANSIENT_CAUSE_RE` (`progress.py:423-...`) can misclassify a genuinely
  substantive assistant text block as a terminal transient death: the lead pattern
  matches the bare word `error` (not just `api error`), so any content block that
  *starts* with `"Error ..."` or `"Error: ..."` (a builder narrating a traceback it's
  fixing, or opening a paragraph with "Error handling: ...") and separately mentions
  any of the very common words in `_TRANSIENT_CAUSE_RE` elsewhere in the same block
  (`timeout`, `unavailable`, `network error`, or a bare `500`/`502`/`503`/`504` that
  could just as easily be an HTTP status code the builder is implementing) would be
  read as the CLI's own terminal report and forced `transient` — triggering a retry
  of what is actually a substantive failure. The docstring at `progress.py:411-419`
  frames the two-pattern design as "reads as an error report… not prose that mentions
  one," but the only test guarding that boundary
  (`test_prose_that_mentions_an_api_error_is_still_substantive`,
  `test_leaf_resilience.py:519-529`) deliberately opens with `"I reproduced the ..."`,
  i.e. it never exercises a block that *itself* opens with the bare lead word. Worth
  either tightening the lead regex (e.g. requiring the `api`/`fatal`/`connection`
  qualifiers rather than bare `error`) or adding a red case for a substantive block
  that opens with "Error" before this ships, since the failure mode this would
  produce — a builder failure silently retried and re-billed as transient — is exactly
  the class of misclassification the brief is trying to eliminate, just in the
  opposite direction.

- `leaves.py:108-109` (`LeafError.transient` property docstring), `leaves.py:2583`
  (the `_FAIL_TRANSIENT` inline comment) and `leaves.py:2588` (`_failure_class`
  docstring) still describe "transient" as "no output" / "ran, exited non-zero with
  no output" only. The class-level docstring just above (`leaves.py:97-105`) and the
  `_invoke_leaf_resilient` docstring (`leaves.py:686-689`) were updated for the new
  "worked, then reported its own terminal death" trigger, but these three secondary
  descriptions were not — cosmetic drift, not a behavior bug, but worth a follow-up
  touch so a future reader of `_failure_class` doesn't reason from the stale half of
  the definition.

- `leaves.py:1882` — `_do_build_command` passes `memory_log=d / BUILD_MEMORY_LOG`
  explicitly into `_invoke_leaf_resilient`, but `_invoke_leaf_resilient` already
  derives the identical path itself via `_memory_log_for(error_log)`
  (`leaves.py:704`, confirmed: `_memory_log_for(d / "build.error.log")` ==
  `d / "build.memory.jsonl"` == `BUILD_MEMORY_LOG`). The three other call sites
  (`leaves.py:2561`, `2894`, `3196`) all rely on the derivation and pass no
  `memory_log` kwarg. Harmless today (the explicit value and the derived one are
  byte-identical), but it's a needless carry-over from the pre-#506 `_invoke` call
  this replaced, and leaves the builder site as the one inconsistent caller of the
  four — dropping the kwarg would match the pattern this slice says it reuses "as it
  is" (`leaves.py:1866`).

No reuse/duplication or resource-leak/concurrency issues found beyond the above; the
new `_has_content` helper (`leaves.py:747-750`) has no existing equivalent to reuse,
and the shared-dict / single-drain-thread mutation pattern for `terminal["error"]`
follows the same (already-safe) shape as the pre-existing `produced` dict.
