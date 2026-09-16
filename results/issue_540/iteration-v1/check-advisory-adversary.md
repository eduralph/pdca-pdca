# Advisory review — adversary (issue #540)

Lens: refute the red→green evidence and the reviewer's verdict; find the input that breaks
the fix. Re-ran everything below against `$PDCA_TARGET` (a copy of the target tree in this
leaf's own sandbox — the target itself was only read).

## Findings

- NEEDS-HUMAN [impl] — **The record the patch writes to survive a death is itself not
  death-safe, and it fails towards the unsafe verdict.** `template/src/pdca_harness/leaves.py:756`
  writes the unsettled record with `Path.write_text`, which is `open(…, "w")` (O_TRUNC) →
  write → close: the file passes through a **0-byte** state and, for a record larger than the
  text buffer, through **prefix** states — and the settlement marker is the LAST thing
  written. Any such partial state reads as *settled*, i.e. "the leaf ran and FAILED"
  (`state.py:185` → `leaves.py:2151` → `assemble.py:420`). Two concrete cases, both measured
  on the target tree:
  1. **Partial write, no race at all.** Under `RLIMIT_FSIZE` (the faithful ENOSPC/quota
     analogue — the exact failure `_flush_attempt_records`' docstring, `leaves.py:748-752`,
     says it is best-effort for) the shipped `leaves._flush_attempt_records` left 2048 bytes
     of attempt 1 on disk with no marker; `state.leaf_ran_and_failed` → `True`,
     `leaves.review_never_ran` → `False`, `assemble._missing_review_text` → "# Advisory
     review MISSING — the reviewer RAN AND FAILED".
  2. **0-byte file** (a SIGKILL/OOM landing between the truncate and the data) — same three
     answers.
  In both, the reviewer that still had 2 attempts left is **retired instead of re-run**, and
  the bundle reaches sign-off with no review of the diff — the precise catastrophe the brief
  names. On the base the same scenario leaves *no* file and `review_never_ran` → `True`
  (recovered), so `leaves.py:753`'s claim "strictly no worse than before" is false for the
  torn-write case, and `state.py:178`'s stated fail-direction ("Unreadable errs the same way,
  towards re-running") does not hold for *truncated* — truncated errs towards retiring.
  Fixable inside the function the patch added: write a sibling temp file and `os.replace()`
  it into place (still best-effort, still `except OSError`), so the record is all-or-nothing.

- NEEDS-HUMAN — **The post-mortem criterion 1 creates is deleted by the recovery criterion 2
  mandates, before any reader sees it.** `leaves.py:705` (`error_log.unlink(missing_ok=True)`,
  frozen by criterion 4) is the first statement of `_invoke_leaf_resilient`, and
  `driver.py:129-131` runs `_resume_interrupted_check` **before** `assemble.assemble_summary`.
  So on the engine's own path the sequence is: unsettled log → recovery re-runs the reviewer →
  the unsettled account is unlinked. The new §6 sentence at `assemble.py:433-434` ("the
  `check-review.error.log` in this bundle is the unfinished account of the attempts it had
  made by then — read it for the post-mortem") therefore names a file the same `advance` has
  just deleted; and since a leaf that runs and spends its attempts always writes a
  `check-review.md` placeholder (`leaves.py:2610`), that branch is in practice reachable
  only when a human calls assemble by hand on a bundle nobody advanced. The mid-retry
  post-mortem is real on disk, but only for a human who inspects the killed bundle *before*
  the next advance — narrower than "a run killed mid-retry therefore leaves a post-mortem"
  reads. Whether that is enough (or whether the staleness clear should preserve/rename the
  unsettled record) is a scope call the brief pre-decided under criterion 4, so it needs a
  human, not a rebuild.

- `template/src/pdca_harness/leaves.py:762-772` — noted, not blocking: `_format_leaf_attempt`
  is shared with the **builder** path (`leaves.py:1817`, inside the `do_build` capture the
  brief fenced off), so `build.error.log` now also gets marker-shaped lines rewritten with the
  quoted suffix. Harmless (nothing reads `build.error.log`'s settlement) and arguably more
  consistent, but it is a behaviour change inside a fenced region, reached indirectly.

## Refutations attempted and failed

- **The red→green evidence is genuine and reproduced independently.** Green: 8/8 in the target
  tree. Red: reverse-applied only the four production hunks (`git diff -- template/src`),
  kept the test — 5 failures, matching `gate-logs/C4-verify.log`. The test drives the shipped
  `leaves._invoke_leaf_resilient` / `review_never_ran` / `run_advisory_leaves` /
  `assemble._missing_review_text`; nothing is re-implemented (C5's claim holds).
- **The tests are not green for the wrong reason.** Four mutants, each caught: marker dropped
  from `unsettled_record` (3 failures); `neutralize_leaf_text` made identity (1 failure —
  `test_a_leaf_emitting_that_line_last_does_not_read_as_unsettled`); `_unsettled` made a
  substring test (2 failures); success-path `unlink` removed (1 failure). The suite pins each
  leg it claims.
- **Could not break the writer/reader pair.** `state.neutralize_leaf_text:209` and
  `state._unsettled:188` split with the same `str.splitlines()` and compare with the same
  `.strip()`, and the neutralizer rejoins on `"\n"`, so no line the reader would call a marker
  escapes the writer: probed trailing `\r`/`\x0b`/`\x1c` separators, NBSP-for-space variants,
  NUL suffixes, marker + trailing blank lines, marker mid-line, and the record's own framing
  — all symmetric. The one body that skips neutralization, the `(no output captured)
  {type}: {exc}` fallback (`leaves.py:772-773`), is single-line and prefixed, and its text
  derives from argv/OS, not from the leaf.
- **Could not narrow the retry contract.** With the flush failing on every attempt the loop
  still ran 3 attempts (measured), attempt count/transient rule/backoff untouched; the flush
  catches only `OSError`, but the captured text cannot carry surrogates (`progress.py:170`
  spawns with `text=True`, strict decoding), so no `UnicodeEncodeError` escapes it.
- **No fifth reader left speaking the old meaning.** Repo-wide grep finds no other consumer of
  `check-review.error.log` / `check-advisory-*.error.log` (the remaining `.exists()` at
  `leaves.py:2655` only decorates a placeholder written after the wrapper returned, i.e.
  always settled). Neighbouring suites re-run green here: `test_leaf_resilience`,
  `test_check_resume`, `test_terminal_error_retention`, `test_build_error_log`,
  `test_leaf_memory_log`, `test_cycle_evidence` — 90 tests, OK, with `test_leaf_resilience.py`
  untouched as criterion 4 requires.
