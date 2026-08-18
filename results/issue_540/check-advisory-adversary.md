# Adversarial review — #540 (per-attempt record + one error-log meaning)

Method: re-ran the C4 green leg on the target (`tests.test_attempt_ownership` 11/11 OK),
re-read the frozen red leg in `gate-logs/C4-verify.log`, ran seven mutants against the new
suite (all killed), re-ran the six neighbouring suites (90 tests, OK), then went hunting for
the input that breaks the fix. One landed.

- NEEDS-HUMAN [impl] — **The impersonation defence is defeated by a truncation at the one
  offset it names.** `state.neutralize_leaf_text` defuses a leaf-emitted marker line by
  APPENDING the quote note *after* the marker on the same line
  (`template/src/pdca_harness/state.py:242`, suffix at `:100`), so the bytes
  `…ran and FAILED -----` are still a complete prefix of that line. Its own docstring
  (`state.py:231-234`) says the exposure it exists to close is "a record cut short right
  after such a line … would read as spent and retire a leaf that was only interrupted" —
  and that is exactly what still happens. Measured end-to-end on the target through the
  **production** writer and all four production readers: drive `leaves._invoke_leaf_resilient`
  with a stub whose stderr's last line is the settlement line, take the mid-retry record the
  production flush wrote, cut it at the end of the marker text (offset 88 or 89 of the
  neutralised line — a bare `-----` or `----- ` both strip to the marker):
  `state.leaf_ran_and_failed` → **True**, `leaves.review_never_ran` (`leaves.py:2176-2177`)
  → **False**, `assemble._missing_review_text` (`assemble.py:420`) → "RAN AND FAILED",
  `run_advisory_leaves(only_missing=True)` (`leaves.py:2874-2877`) → **skips the leaf**. A
  reviewer the death window merely interrupted is retired and the bundle reaches sign-off
  with no review of the diff — the precise catastrophe this slice exists to prevent, and a
  direct counterexample to the unconditional fail-direction claim at `state.py:186-189`
  ("torn off part-way by a dead write … fail towards RE-RUNNING") and to brief criterion 3.
  Fix is one expression: put the note BEFORE the line (`f"{_QUOTED_SUFFIX} {line}"`) or
  rewrite the marker text itself — measured, both leave **zero** dangerous cut offsets
  (shipped form: 2). Reachability, stated honestly: `_replace_record` (`leaves.py:778-781`)
  makes the harness's own writes rename-atomic, so a SIGKILL can no longer tear the file;
  what remains is a crash/power-loss with unflushed data (`_replace_record` does **not**
  fsync the temp before `os.replace`, so its "all-or-nothing" docstring at `leaves.py:765-776`
  is a rename claim, not a durability one), an externally truncated log, or any future writer
  of these records. Narrow — but the code, the brief and the test all assert the property
  unconditionally.
- NEEDS-HUMAN [impl] — **The test that claims to pin that property only pins the adjacent
  cut.** `template/tests/test_attempt_ownership.py:381-391` builds its torn record with
  `_before_last_line` (`:222-225`), which cuts at the *start* of the last line — i.e. it
  removes the harness's own closing line and leaves the neutralised leaf line **whole**, the
  one shape the append does defuse. The sibling leg at `:330-339` walks several cuts
  (`settled[:head]`, `settled[:head + len//2]`) but drives the *non*-impostor stub, so no cut
  can land inside a neutralised marker line. The missing leg is the intersection of the two:
  impostor stub + a cut at `mid.index(line) + len(line)`. It fails today.
- NEEDS-HUMAN [impl] — **The new sibling temp is orphanable inside the bundle and matches no
  ignore rule.** `leaves.py:778` writes `.{error_log.name}.partial`; the OSError path unlinks
  it, a killed run does not. `template/.gitignore.jinja:17` ignores `*.log` (so the error logs
  themselves are never committed) but nothing matches `.check-review.error.log.partial`, so
  `record.py:111` (`git add -A -- <bundle>`) would sweep an orphan into a records commit/PR.
  The file's own convention is explicit about this class — `.pdca-prompt-*.md` (`:25`),
  `.pdca-handoff-*.json` (`:32`), `.act-reviewed.tmp.*` (`:37`) each exist because "a killed
  session can orphan one", two of them with a test asserting the pattern tracks the code
  constant. `state.DOWNSTREAM_GLOBS` (`state.py:154`) and `driver._archive_iteration`
  (`driver.py:430`) also won't archive or clear it.
- Evidence-quality note (not a defect, no adjudication needed): three of the C4 red-leg
  failures are `AttributeError: module 'pdca_harness.state' has no attribute 'settled_record'`
  from the *modified* `test_check_resume.py` (`gate-logs/C4-verify.log:398`, `:407`, `:416`) — symbol
  absence, the same class of non-evidence `run-verify.sh:229-232` rejects at import time,
  just surfacing at attribute access instead. The verdict stands on
  `test_attempt_ownership.py` alone, which went genuinely red (15 behavioural failures,
  `C4-verify.log:378-380`) and which I re-ran green on the target; those three should not be
  counted as independent red evidence for the check-resume readers.

## Attempted and could not refute

- **Seven mutants, all killed** by the new suite: neutralisation → identity; last-line test →
  substring; drop the success-path unlink (`leaves.py:722-723`); `_replace_record` → plain
  `write_text`; `_flush_attempt_records` no longer best-effort (`leaves.py:758-762`);
  `unfinished_record` emitting the settled marker; empty log reading as settled.
- **Criterion 5 (the retry contract) holds under a non-OSError.** I looked for an exception
  the flush's `except OSError` would not catch and that would cut the loop from 3 attempts to
  1 — the obvious candidate is `UnicodeEncodeError` on a surrogate-bearing tail, but
  `progress.py:169-171` spawns with `text=True` and strict decoding, so a leaf's output can
  never carry a lone surrogate. Attempts stay 3 on the unwritable-dir path (re-ran).
- **No fifth reader speaking the old meaning.** Repo-wide grep for `*.error.log` /
  `REVIEW_ERROR_LOG` finds only the four converted readers plus non-discriminating uses
  (`leaves.py:2681` log_ref, `driver.py:430` archiving, `state.py:296` cycle evidence — which
  now flips True slightly earlier, in the safe direction). Plan-advisory logs
  (`leaves.py:3216`) have no existence reader; `build.error.log` is off this path.
- **Criterion 4 intact.** `test_leaf_resilience.py` is untouched by the diff and green
  (re-ran); the success path still leaves no error log; the #420 memory post-mortem still
  rides `output` through the neutralisation (`leaves.py:664-666`).
- **The staleness clear (`leaves.py:706`) deleting the mid-retry post-mortem when the
  recovery re-runs the leaf** is real, but the brief pre-decided it under criterion 4 and the
  previous round already routed it to Act — not re-filed here.
