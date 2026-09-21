# Advisory code review — issue #566

## Findings

- NEEDS-HUMAN [impl] — `drive_claim.held()`'s success path doesn't suppress `OSError` on
  close the way every other claim-handling path in this module does.
  `template/src/pdca_harness/drive_claim.py:281-284`:
  ```
  with contextlib.suppress(OSError):
      act._unlock(fh)
  fh.close()
  return False
  ```
  Every other close in this module — the failure branch three lines above
  (`drive_claim.py:278-279`), `Run.take`'s two close sites (`:198-199`, `:207-208`), and
  `_release` (`:144-150`, used by `Run.release`/`Run.close`) — wraps `fh.close()` in
  `contextlib.suppress(OSError)`. This one doesn't, so a rare close-time `OSError` (a full
  disk flushing a buffered `"a+"` handle, an NFS I/O error) escapes `held()` uncaught.
  `held()`'s only caller is `cli.py:892`
  (`if drive_claim.held(cfg, d) or drive_claim.held(cfg, drive_claim.sweep_marker(cfg)):`),
  sitting directly inside the block `cli.py:875-878` calls out by name as the exact thing
  that must never happen again: "no write here can change the outcome — but an unguarded
  one could still change the EXIT CODE… before #459, [this] turned a completed acceptance
  into a traceback." An uncaught `OSError` out of `held()` would do exactly that — crash
  `cli._split` after the tracker issues are already filed and the child bundles are already
  on disk, on the very call this patch adds to that guarded tail. Fix: wrap the `fh.close()`
  at `drive_claim.py:283` in `contextlib.suppress(OSError)` like its neighbors.

- `flow._warn_stranded_split_children`'s lineage walk (`flow.py:1539-1547`) dedupes a child
  only by `cd.name`, not by resolved path — unlike `_adoptable`'s own walk (`flow.py:1041-
  1047`, `seen_real`), which the same function's docstring says it mirrors. A lineage record
  naming one bundle under two spellings that resolve to the same directory (a symlinked
  alias, same hazard `_adoptable` guards against) would be examined twice and, if in flight,
  could appear twice in one `stranded` line's `pdca flow <ids>` command. Read-only report,
  so the worst case is a redundant id in the printed hint, not a scheduling error — low
  severity, and outside brief scope (the adoption algorithm itself is explicitly out of
  scope), so I'm not asking for a fix, just flagging it since the docstring claims a mirror
  that isn't quite complete.

## Everything else

Traced the rest of the diff against the target source (`drive_claim.Run.take`'s retry loop,
`flow._warn_stranded_split_children`'s terminal/split-marked ordering against `_adoptable`,
the `sweep_marker`/`flow_batch` claim-and-release, `cli._split`'s conditional line) and it
holds up. The iteration-1 carry-forward bug (finished split children reported as "left
in-flight") is fixed correctly: the terminal check now runs after the split-marked check, in
that order, walking through a terminal-and-split child while skipping a terminal-and-not-
split one — matches `_adoptable`'s own ordering and reasoning, and is pinned by three new
tests I traced by hand (`test_end_of_run_report_is_silent_when_every_split_child_is_finished`,
and the two "walks through" tests) against the actual `driven`/`_TERMINAL`/`_split_marked`
checks at `flow.py:1546-1561`. C4's gate log confirms the new test file (11 tests) is
genuinely red on the reverted production hunks (6 failures + 1 error) and green with them
applied — it exercises the fix, not a copy of it.

Minor, non-blocking reuse note: `_split_marked` (`flow.py:1461-1483`) duplicates the
close-marker read `_is_split_parent` already does (`flow.py:924-930`), deliberately dropping
the terminal gate — the docstring explains why at length, and the duplication is small and
justified, not worth a refactor for this patch.
