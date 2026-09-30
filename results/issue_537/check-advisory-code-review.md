# Advisory code review — issue_537 (the builder retries like every other leaf)

I found no correctness bug that blocks this patch. The builder now goes through
`_invoke_leaf_resilient` with the shipped defaults. Attempt 1's prompt is built exactly as
before. The memory log is derived by the wrapper, not passed in. `do_build` still
re-raises, and its outer capture no longer overwrites the per-attempt record. Both new
test files drive the real `do_build` through a stub leaf. The findings below are minor.

- `template/src/pdca_harness/leaves.py:2042` — low, edge case. If the wrapper's
  mid-retry flush worked but the final settle write then failed (for example ENOSPC),
  `build.error.log` is left holding the UNFINISHED record. `do_build` sees that the file
  exists, skips its own write, and prints "the builder's per-attempt record is in
  build.error.log". The record is there, but readers treat it as if no log existed. Before
  this patch, the outer capture's raw `write_text` did not carry the settled marker
  either, so what a reader concludes does not change. The console line is only a little
  more confident than the disk supports. Not worth another round.
- `template/src/pdca_harness/leaves.py:766` / `:2180` — `raise exc from last` changes what
  the other three resilient call sites see when the settle write fails: the OSError now
  has `__cause__` set to the leaf's failure. They still get the same OSError type, so
  their behaviour does not change. Only `_do_build_command` reads `__cause__`, and it
  re-raises the original when the cause is `None` (for example an OSError from the
  opening `unlink`). The existing read-only test covers this path:
  `template/tests/test_build_error_log.py:165-170` patches `Path.write_text`, which
  `_replace_record` goes through.
- `template/src/pdca_harness/leaves.py:2160` — simplification, optional. The attempt count
  is tracked with a `nonlocal spent` side effect inside the prompt callback. It is correct:
  the callback runs right before each spawn, so `spent` is the number of attempts actually
  made. But the count comes from how prompts are generated, not from the wrapper. Having
  the wrapper expose the attempt count (or count the `----- attempt N` records) would
  avoid the hidden coupling. Leave it as is unless someone touches this again.
- `template/tests/test_build_error_log.py:36` vs `template/tests/test_builder_retry.py:99`
  — the two test modules each carry their own "time without sleep" shim
  (a `SimpleNamespace` copy vs a `__getattr__` proxy). The brief asks for copying over
  cross-module imports, so this is expected. Mentioned only in case a shared test helper
  is wanted later.
- `template/src/pdca_harness/leaves.py:2056` — checked, no issue. `_do_residue` resolves
  the brief's test file against the bundle. That matches `brief.test_files` ("relative to
  the bundle", `brief.py:181-186`) and the Do prompt, which tells the builder to put the
  test file in the bundle directory. The residue report and the retry notice are therefore
  talking about the same files.

No NEEDS-HUMAN items from this lens.
