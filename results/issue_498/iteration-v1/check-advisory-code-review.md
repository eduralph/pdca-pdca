# Advisory code review — issue #498

Lens: correctness bugs this patch introduces, plus reuse/simplification/efficiency. Grounded
on the patched tree at `$PDCA_TARGET` (`template/src/pdca_harness/{cli,flow,leaves,drive_claim}.py`,
`template/tests/test_flow_single_driver.py`).

## Correctness

- The claim/lock half of `drive_claim.py` is solid: `Run.take()` opens the claim file `"a+"`
  (never `"w"`, so a contended open cannot truncate another run's stamp — `drive_claim.py:127`),
  takes a non-blocking `flock`/`LK_NBLCK` reusing `act._lock_exclusive`/`_unlock`
  (`drive_claim.py:49,132`), and is released only by the OS when the holding handle closes —
  correct for return, raise, and `SIGKILL`. Traced every call site (`cli.py:572-583` named-id
  claim before any write, `flow.py:1063-1068` child adoption, `flow.py:1750-1763`
  `_claim_swept`, `flow.py:1294-1296` release of dropped/retracted children) and the
  claim/release bookkeeping is consistent: a child dropped by a failed or partial reschedule
  is released exactly once (`flow.py:1257-1296`), and a bundle already in `known`/`batch_names`
  is refused via the owner check before ever reaching `claims.take()`, so no redundant
  claim-then-release churn.

- NEEDS-HUMAN [impl] — `drive_claim.py:57-61,179-208,246-252`: the "truthful hint" state
  (`RUN_ENV`, `SWEEP_ENV`) is process-global `os.environ`, not thread-scoped, while the
  module's own docstring (`drive_claim.py:18-22`) explicitly describes "two runs in one
  process — a test driving two flows on two threads" as a scenario the mechanism must not
  tell apart from two processes. That claim is true for the *lock* (per-open-handle
  `flock`, thread- and process-safe) but not for `drives_children()`'s inputs: if two
  distinct `drive_claim.run()` scopes were ever active concurrently on two threads of one
  process, each entry/exit does `prev = os.environ.get(RUN_ENV); os.environ[RUN_ENV] = token`
  and restores `prev` on exit (`:180-190`) — a second scope's exit can stomp the first
  scope's still-live token, or a leaf spawned from one run can read the other run's token.
  Worst case this only corrupts the *hint* (wrongly suppresses or wrongly prints the
  `pdca flow <child-ids>` instruction), never the actual exclusion, and it isn't reachable
  through the shipped CLI (one `cli._flow` call per process; lane fan-out inside one run is
  threads sharing one token, not two runs) or exercised by any test in this patch — every
  test uses at most one thread-based run at a time. Narrow and not exercised, but it is a
  real gap between what the docstring asserts and what the env-var-based hint actually
  guarantees; worth a follow-up (e.g. a `contextvars.ContextVar` as the primary token, with
  the environment variable kept only for subprocess inheritance) or a narrowed docstring
  claim.

- Test coverage for the SIGKILL half of (iii) (`test_flow_single_driver.py`, the
  `test_a_killed_run_holds_nothing_and_blocks_nothing` case) is real and runs on this gate
  host (`hasattr(signal, "SIGKILL")` is true on Linux), and `C4-verify.log` confirms 11/11
  green with the fix and 8/11 red without it, driven through `cli._flow`/`cli._split` as the
  brief requires (not a copy — `C5-prod-path.log` confirms the new test imports
  `pdca_harness`). No issue found in the test's mechanics: the "ready" handshake file is
  written only after the holder process has already taken its claim (claiming happens before
  Do runs), so there's no window where the competing run could win a race the test doesn't
  intend to test.

## Reuse / simplification / efficiency

- No duplicated locking logic: `drive_claim.py` reuses `act._lock_exclusive`/`_unlock`
  directly (`drive_claim.py:49`) rather than re-implementing the Windows/Unix branch, exactly
  as the brief's composition cue asks. The per-bundle keying (`_key`, resolved path + digest)
  and run-lifetime bookkeeping are new because nothing in the codebase already does per-bundle
  ownership — not a case of skipped reuse.
- The claiming loops in `cli._flow_claimed` (whole-run refusal) and `flow._claim_swept`
  (per-bundle exclusion) share the same `claims.take(d)` / `why` shape but differ in exit
  behavior (return-whole vs. continue-and-exclude) and in message wording tied to their own
  context; collapsing them into one helper would save a few lines at the cost of the
  context-specific messages the brief's success criteria (i) vs (ii) both call for
  separately. Not worth flagging as duplication.
- No hot-path concern: every claim/lock check is a non-blocking `flock` attempt on a tiny
  file, at most once per bundle per run; no busy-waiting in production code (the busy-wait
  loops — `_pausing_build`'s `time.sleep(0.02)` polling — are test-only, bounded by `_WAIT`).

## Summary

Clean on the whole. One narrow, unexercised gap in the new module's thread-safety story for
the advisory hint (not the exclusion itself) — flagged above as an implementation follow-up,
not a blocker.
