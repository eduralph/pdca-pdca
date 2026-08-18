# Adversarial review — refuting the fix and its evidence (issue 532 / #506 child-1)

Re-ran the asserted red→green in a private copy of `$PDCA_TARGET` (never writing to it):
both patched test files green (37 tests), the whole offline suite green (1778 tests, 2
skipped), and the C4 red leg in `gate-logs/C4-verify.log` is a genuine red — 14 of the new
cases fail on the reverted production hunks for the reasons they claim, not on an import
error. The tests drive `leaves.do_build → _do_build_command → _invoke_leaf_resilient →
_invoke → progress → subprocess` with a real child; only `time.sleep` (and, in the capture
cases, the vendor spawn) stands in. **C4's verdict survives attack.** What follows is what
does not.

- **NEEDS-HUMAN [impl] — the exhausted-retry report asserts authorship it cannot know**
  (`template/src/pdca_harness/leaves.py:1993-1997`, fed by `_do_residue`
  `:1966-1972`, which only asks "does the file exist"). A *transient* death is by
  definition one that produced nothing, so bundle artifacts present at that moment are
  usually **not** the dead attempts'. Reproduced against the patched tree: a bundle at
  PLANNED holding a `build-notes.md` + brief-named test file written by an **earlier run**,
  with this Do's builder dying at spawn three times having written nothing, prints
  `issue_506 — the interrupted attempt left build-notes.md, test_x.py in the bundle …
  Read them as an unfinished attempt's residue`. That is false about both files, in the one
  sentence the brief's invariant governs ("nothing the harness tells the operator … about
  that residue may be false"). Carry-forward item 6 asked for these files to be named, not
  for their provenance to be invented; naming them ("the bundle holds …, which may predate
  this attempt") closes it.

- **NEEDS-HUMAN — the #510 signal-death exclusion is keyed on a premise the leaf's `argv`
  can break** (`leaves.py:1962-1963`, premise stated at `:1958-1960`: "`subprocess` reports
  a signal death as a NEGATIVE returncode"). That holds only when `argv[0]` *is* the process
  that dies. A wrapper argv — the documented `argv = ["local-build", …]` shape
  (`docs/04-do.md:47`), an `sh -c` launcher, `docker run` — reports an OOM SIGKILL of its
  child as **137**, a positive code. Reproduced on the patched tree with
  `argv=["/bin/sh","-c", …]` around a self-SIGKILLing leaf: `returncode 137`,
  `_builder_retryable → True`, **3 spawns**, and stderr reading `died of a TRANSIENT
  infrastructure failure (exit 137) — infra the harness absorbs` while `build.error.log`
  says `Killed`. That is verbatim the carry-forward item 3 defect, reached by a supported
  configuration instead of by the classifier. Whether to widen the exclusion (128+n) or
  leave the hole for #510 is a scope call the patch should not make silently.

- **NEEDS-HUMAN [impl] — a leaf that finished is left flagged "in flight"**
  (`leaves.py:753-756`). On the deliberately-retained-log path — a dead attempt's artifact
  was withdrawn and the successful attempt wrote none — the last write was
  `_write_attempt_records(..., in_flight=True)`, so the surviving log keeps
  `_LEAF_IN_FLIGHT` (`:785`). Reproduced: after `_run_review_sandboxed` completes,
  `check-review.error.log` ends with `<!-- pdca:leaf-attempt in-flight — the retry loop had
  not finished -->` and `leaves.leaf_run_incomplete(log)` returns **True** for a reviewer
  whose loop finished — contradicting that function's own contract (`:804-813`). The
  placeholder written a line later points the operator straight at that file. Blast radius
  today is the log's text (`_leaf_ran_and_failed` is only consulted where the placeholder
  already exists), but the fix is one line: re-flush with `in_flight=False` before returning
  success. Related fragility in the same predicate: it is a substring sniff, while the body
  now embeds up to 20 000 characters of the leaf's own artifact (`:825`, `:849-856`) — a
  verdict that *quotes* the marker (e.g. a review of this very patch) makes a completed log
  read as interrupted.

- **NEEDS-HUMAN [impl] — Do's failure path now has an unguarded stderr write, and it can
  replace the exception the criterion pins.** `do_build` keeps its capture inside
  `try/except OSError: pass` "never let error-capture mask the real failure"
  (`leaves.py:1925-1937`), but the newly-added `_report_exhausted_do_retries` prints
  (`:1988-1999`) sit outside it, and the builder is now also exposed to the wrapper's retry
  notice (`:773-775`), which raises out of `_invoke_leaf_resilient` entirely. Reproduced
  with a stderr that raises `BrokenPipeError` (`pdca run … | head`, a detached session, a
  full disk): patched tree → `do_build` raises **`BrokenPipeError`**, and the retries never
  run; pre-fix base, same probe → `LeafError`. Criterion (i) says "either way the final
  failure is still captured … and still re-raised".

- **NEEDS-HUMAN [impl] — the #369 discriminator's prose was updated in `leaves.py` but not
  where the driver states it**: `template/src/pdca_harness/driver.py:152-155` still
  documents the recovery rule as "`leaves.review_never_ran` — no artifact, no error log",
  which is exactly the reading the patch had to abandon. In a repo whose invariant is that
  what the harness says must be true, this is the one remaining sentence stating the old
  contract.

- **NEEDS-HUMAN — the C5 row is a green that asserts nothing, for the second round
  running.** `check-gates.json` records `C5 added test exercises production, not a copy →
  pass`, basis `patch adds no new test file — nothing to assert`
  (`gate-logs/C5-prod-path.log`) — the identical vacuous pass the sign-off carry-forward
  called out ("Make production-path coverage adjudicable next round"). It is unaddressed at
  the gate: the patch appends to existing files, so the oracle skips. The substance is
  mostly fine (I verified the builder and reviewer/advisory cases run production), but one
  of the three sites the fix exists for is proven only by **mocking the production wrapper**
  — `template/tests/test_leaf_resilience.py:573-595` patches `leaves._invoke_leaf_resilient`
  and then asserts `kw["artifact"] == cwd/"plan-advisory-lens.md"`, i.e. it re-states the
  call-site expression rather than exercising `_withdraw_residue` at that site. A human
  should decide whether that closes the carry-forward.

**Attempted and could not refute:** that the exhausted-retry advice is derived from
`state.state` rather than the residue's shape (`leaves.py:2011-2022` — PLANNED/BUILT/CHECKED
all verified true of the real waterfall); that fail-closed ownership stops the loop when the
withdrawal cannot be enforced (`:857-863`, no further spawn, no dead artifact adopted); that
`_memory_log_for` derivation yields the identical `build.memory.jsonl` and `_MemoryTelemetry`
still appends per spawn, so #420 is intact; that `progress.TIMEOUT_RC = -1001` is excluded
from the builder retry; that the shipped `systemd-run --user --scope` cap execs the leaf, so
the *shipped* OOM path really does surface as `-9`; that `_skip_backoff` does not busy-loop
the heartbeat (`progress.py` waits on `proc.wait(timeout=…)`, and its only `time.sleep` is
0.05 s); and that a dead attempt's artifact can be harvested at any of the three sites — the
harvest is unreachable while `err is not None`, and the withdrawal happens before the next
spawn. The residue-inheritance machinery is largely latent until sibling child-2 changes the
transient rule (a leaf that wrote an artifact has emitted a stream event, hence reads
substantive today) — which the brief's ordering note anticipates, so it is not a finding.
