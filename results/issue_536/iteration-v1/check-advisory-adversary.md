# Adversarial review — attempt-owned leaf records and harvests (#536 / parent #506)

Evidence re-run here, offline, on the target at `$PDCA_TARGET` (python3 3.14, stdlib only):
red leg = production hunks reverted, `template/tests/*` kept → **6 failures + 1 error**
(3 of the 10 are guards that legitimately pass on the base); green leg = patched tree →
**10 OK**; `tests/test_leaf_resilience.py` untouched → **5 OK**. C4's `red without the fix,
green with it` reproduces. The two impersonation legs are load-bearing (remove
`_defang_in_flight` and both go red), so the added tests are not tautologies. Findings
below are what survived an attempt to break the fix.

- **NEEDS-HUMAN [impl] — the per-attempt flush is not crash-atomic, which re-opens the very
  window criterion (v) exists to close.** `template/src/pdca_harness/leaves.py:800`
  (`error_log.write_text(body, …)`) truncates first and appends the `_LEAF_IN_FLIGHT`
  trailer **last**. A kill between the truncate and the trailer bytes — SIGKILL, the OOM
  kill the #420 telemetry exists to explain — leaves a log with **no trailer** (0 bytes in
  the common case). Concrete failing case, verified against the target: with
  `check-review.error.log` containing `""` **or** `"----- attempt 1 — exit 1 -----\nboom\n"`,
  `leaves.leaf_run_incomplete()` → `False` and `leaves._leaf_ran_and_failed()`
  (`leaves.py:835`) → `True`, so `review_never_ran` (`leaves.py:2277`) → `False` and
  `driver.py:176` never recovers the reviewer — the bundle reaches sign-off with **no review
  of the diff**. On the base the same kill left *no* log at all and the leaf **was**
  recovered, so this is a new (narrow) failure mode introduced by the flush, not pre-existing
  debt. The repo already ships the crash-atomic idiom this needs — temp sibling +
  `os.replace` (`src/pdca_harness/act.py:326`) — and `_write_attempt_records` does not use it.

- **NEEDS-HUMAN — the patch's own recovery path destroys the dead-attempt text criterion (ii)
  went to the trouble of preserving.** An in-flight log is precisely the log that makes
  `review_never_ran` say "recover me" (`leaves.py:2277` → `driver.py:176` →
  `leaves.run_review`), and the first statement of the re-run is the staleness clear
  `error_log.unlink(missing_ok=True)` at `leaves.py:714`. Verified end to end on the target:
  attempt 1 writes a complete verdict and dies transiently → the mid-retry log is in-flight
  and holds that verdict → `review_never_ran` is `True` → after the recovery run the verdict
  is **gone** (`"the real verdict" in log` → `False`). The sandbox that held the original
  died with the run, so if the recovery run then fails the operator is told "the reviewer
  produced no verdict" while the only surviving copy of a real one has been deleted — the
  exact harm the brief's criterion (ii) rationale names. Not marked `[impl]` because closing
  it means either archiving the log before the clear or changing the staleness clear, and
  criterion (vi) freezes that clear: a scope call, not an iteration.

- **NEEDS-HUMAN [impl] — the new "successful attempt wrote nothing after a withdrawal" branch
  files an infra death as a substantive one.** `leaves.py:2704` (and its twins `:3039`,
  `:3340`) passes `error_log=` but leaves `failure=` at the default `_FAIL_SUBSTANTIVE`, so
  `_unavailable_classification` (`leaves.py:2769-2792`) stamps
  `<!-- pdca:leaf-status human-empty -->` and prints *"**substantive — needs a human.** The
  leaf ran but did not yield a usable verdict; do not assume an infra blip"* — one sentence
  before pointing at a log that reads `overloaded_error 529` plus a withdrawn partial verdict
  (reproduced verbatim on the target). `assemble` keys the §6 row off that marker, so a
  transient blip now presents to the operator as a reviewer that reviewed and failed — the
  inversion #278's marker exists to prevent. The wrapper only ever retries *transient*
  failures, so a log that survives a **successful** return is by construction an infra death:
  the branch can classify it without new information.

- **NEEDS-HUMAN [impl] — the third reader of "an error log means the leaf ran and FAILED" was
  left un-#506-aware.** `src/pdca_harness/assemble.py:417` still splits on a bare
  `(d / state.REVIEW_ERROR_LOG).exists()`, so an in-flight log renders *"the reviewer RAN AND
  FAILED … Fix the cause, then re-run"* for a leaf the death window merely interrupted, while
  `leaves.py:2277` and `leaves.py:2986` now say the opposite about the same file. Honest
  caveat: I could **not** construct a live failure — `driver.py:130` recovers before
  `driver.py:132` assembles, and every `run_review` path leaves a `check-review.md` behind,
  so the branch is currently shadowed. Filed as the one reader the semantic change missed,
  cheap to align (`leaves._leaf_ran_and_failed`), not as a reachable bug.

- **NEEDS-HUMAN [impl] — two of the three harvest sites the brief names are asserted by
  inspection only.** `template/tests/test_attempt_ownership.py:255,301` drive only
  `_run_review_sandboxed`; nothing exercises `leaves.py:3028` (advisory) or `leaves.py:3329`
  (plan-advisory). I drove both myself through the production functions and they behave
  correctly (dead text withdrawn, preserved in the log, placeholder written) — so this is
  test blindness, not a live defect. Its cost is concrete: had either site been wired to the
  **bundle** path (`advisory_artifact(d, leaf_id)`) instead of the sandbox `out`, a dead
  attempt would `unlink()` the previous round's shipped artifact and the suite would stay
  green. One parametrized case over `_run_advisory_sandboxed` closes it.

**Attempted to refute and could not:** (a) the criterion-(iv) impersonation leg — I ran 30
payloads through the production path (dead-attempt artifact **and** captured stderr): bare
marker, space/tab-padded, `\r`-, form-feed-, vertical-tab-, U+2028- and U+0085-separated,
marker + ZWSP / BOM / NUL, BOM + marker, no trailing newline, trailing blank lines, and a
21 000-char artifact past the `_RESIDUE_KEEP` truncation. `review_never_ran` stayed `False`
in every one — `_defang_in_flight` (`leaves.py:781`) plus the whole-line last-non-blank match
(`leaves.py:829`) hold, and the #420 post-mortem survives verbatim. (b) The fail-closed
`owned` stop: a leaf that `mkdir`s its artifact path costs itself two of three attempts
(`leaves.py:752`), but the wrapper stays fail-closed, prints why, and leaves a non-in-flight
log — and the brief explicitly blesses this mechanism. (c) The success path: I could not
construct a case reaching `leaves.py:734` with a dead attempt's file still standing (an
un-withdrawable artifact breaks the loop first). (d) `_format_leaf_attempt`'s
`(no output captured) …` fallback is not leaf-controllable, so it is no second door.
