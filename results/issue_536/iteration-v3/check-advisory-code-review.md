# Advisory code review — correctness + reuse/simplification (issue #64 lens)

Scope: `template/src/pdca_harness/{leaves,driver,assemble,state}.py` and
`template/tests/test_attempt_ownership.py`, as changed by patch.diff (issue #506:
attempt-as-unit-of-accountability for the reviewer/advisory/plan-advisory retry
wrapper). Grounded on `$PDCA_TARGET/template/src/pdca_harness/leaves.py`.

## Findings

- NEEDS-HUMAN [impl] — `leaves.py:2804-2807` (mirrored at `leaves.py:3167-3170` and
  `leaves.py:3470-3473`): the `err is not None` branch of all three harvest sites
  (`_run_review_sandboxed`, `_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`)
  files the "leaf failed" placeholder via `_review_unavailable`/`_advisory_unavailable`/
  `_plan_advisory_unavailable` but never calls `_settle_leaf_record`. This relies on the
  invariant that the retry loop's own last `_write_attempt_records(..., in_flight=False)`
  call (`leaves.py:760`) already settled the log before breaking. That invariant holds
  only when that final write *succeeds*. If it fails (`_atomic_write_text` raises
  `OSError`, e.g. a transient disk error) while a *prior* attempt's write already landed
  with `in_flight=True` (`leaves.py:744`/`760` when `may_retry` was still `True` on an
  earlier iteration), `_write_attempt_records` reports the failure and returns `False`
  (`leaves.py:845-853`) but leaves the on-disk file exactly as the prior successful write
  left it — still carrying `_LEAF_IN_FLIGHT`. The loop then breaks (`leaves.py:761-762`,
  `not (may_retry and recorded)`), `err is not None` at the call site, and the "leaf
  failed" placeholder is written to the bundle — while the error log itself is still
  read by `leaf_run_incomplete`/`_leaf_ran_and_failed` as *in flight*. The next `advance`
  will then treat this leaf as never-run (`review_never_ran` / `only_missing`) and
  re-run and re-pay it, even though a "reviewer leaf failed: …" verdict was already filed
  for it — the same "leaf recorded as two contradictory things" conflation issue #506
  otherwise sets out to remove. This is a narrow window (requires a disk write failure on
  a *non-first* attempt specifically), and it is a strict improvement over the pre-patch
  code's unguarded final `write_text` — but nothing in `test_attempt_ownership.py` drives
  a write failure on a middle/last attempt after an earlier one already landed (the one
  write-failure case that's tested, `test_a_retry_never_starts_without_its_predecessors_
  account_on_disk`, refuses *every* write from attempt 1, so no stale in-flight marker is
  ever created). Consider settling (or re-checking) the log in the `err is not None`
  branches too, or making `_write_attempt_records`'s failure path itself strip a stale
  in-flight trailer it can no longer trust.

- Reuse/simplification (non-blocking) — `leaves.py:2789-2823`, `3158-3176`,
  `3462-3480`: the three harvest sites are near-identical, and the patch (by its own
  in-code admission at `leaves.py` comments "the reviewer's two near-identical twins")
  threads the same five-line attempt-aware harvest sequence (`artifact=…`, the
  `err is not None` branch, `out.exists()`/`produced.exists()`, the `_empty_run_class`
  call, the `_settle_leaf_record` call) through all three copies by hand. That's exactly
  the shape that let the gap above land identically in all three places rather than
  once. A small shared helper (e.g. `_harvest_leaf(d, out, dest, error_log, err, ...)`)
  encapsulating "copy on success / `_*_unavailable` + settle on empty / `_*_unavailable`
  on `err`" would remove the duplication and make the settle-call omission structurally
  impossible to repeat at a fourth site later.

Everything else in the diff — the `_LEAF_IN_FLIGHT` marker/defang scheme, the atomic
write, `_withdraw_residue`'s fail-closed ownership handshake, the `#369` discriminator
updates in `driver.py`/`assemble.py`/`review_never_ran`, and the new
`test_attempt_ownership.py` coverage — reads correctly against the target source and is
exercised by a real production-path test suite (confirmed against
`gate-logs/T3-suite.log`: 1780 driver-suite tests green, `gate-logs/C4-verify.log`
red→green). No other correctness bugs or reuse gaps found.
