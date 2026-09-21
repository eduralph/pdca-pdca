# Advisory code review — issue #565 (one live driver per bundle)

Traced the claim/release bookkeeping end to end against the target source
(`drive_claim.py`, `cli.py:558-660`, `flow.py`'s claim/release call sites) and
cross-checked every release point the brief calls out. No correctness bug and
no reuse/simplification opportunity found in this diff.

Specific things checked and found sound:

- `drive_claim.Run.take()` / `.release()` key claims by `_claim_file`, which
  hashes the bundle's *resolved* path (`drive_claim.py:218-224`). The named-id
  claim loop (`cli.py:598-611`), `_claim_swept` (`flow.py:1796-1808`), and the
  `held` release loop (`flow.py:1786-1787`) all build their `Path` from the
  same `cfg.bundle_root / name` / `cfg.bundle(iid)` shape, so a claim taken one
  place is found and released at the other — verified `waves.partition_schedulable`
  keys `held` by the same `b.name` bundle-directory string (`waves.py:255-274`),
  matching the `cfg.bundle_root / name` reconstruction at `flow.py:1787`.
- The `dropped` computation in `_adopt_split_children` (`flow.py:1281-1326`)
  covers all three ways a claimed child stops being driven — never spliced at
  all (`dropped = children`), spliced but held by this reschedule, and adopted
  earlier but retracted by a later one — without releasing a claim more than
  once: once a bundle is dropped it's removed from `bundles`/`batch_names`/the
  rescheduled `wave_list`, so it can't reappear in a later call's `remaining`.
- The keep-awake re-exec ordering the brief calls out is real:
  `main()` calls `_inhibit_suspend_and_reexec()` (`cli.py:433`, which
  `os.execvpe`s and never returns on success) *before* dispatching to `_flow`
  (`cli.py:454`), and `drive_claim.run(cfg)` is entered inside `_flow` itself
  (`cli.py:573`) — so a claim is always taken in the process that actually
  drives, never one that's about to be replaced.
- `_contended()`'s `isinstance(exc, BlockingIOError)` check is redundant with
  its own `exc.errno in _CONTENDED` check (CPython maps EAGAIN/EWOULDBLOCK
  OSErrors to `BlockingIOError` automatically), but it's harmless — not
  flagging as a finding, just noting it in case a reviewer wonders why both are
  there.

Gate evidence corroborates the fix: `C4-verify.log` shows 14/23 tests failing
on the reverted (red) leg for real reasons (the sweep and adoption drive
bundles a held claim should have excluded), green after the fix; `T3-suite.log`
shows the full 1955-test suite passing.

No findings requiring a human or a builder iteration.
