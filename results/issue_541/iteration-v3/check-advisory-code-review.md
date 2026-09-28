# Check advisory — code review (correctness + reuse/simplification), issue #541

Scope: this diff only (`template/src/pdca_harness/leaves.py`, `assemble.py`,
`template/tests/test_attempt_harvest.py`), grounded on `$PDCA_TARGET`. Round-3
carry-forward's three named defects (assemble.py header-line hole, digest-only
identity, per-attempt residue re-quoting) were checked against the current
target source, not just the diff text — all three are genuinely closed, not
partially patched around:

- `assemble.py:99-108,188` — the `_LEAF_STATUS_HEADER_LINES` mechanism from the
  prior round is gone outright; `_items_from_artifact` now leaves an artifact
  alone whenever it carries no *recognised* status token, independent of where
  in the file an unknown token appears. Verified no residual
  `_LEAF_STATUS_HEADER_LINES` reference remains anywhere in `assemble.py` or
  the tests.
- `leaves.py:1058-1074` (`_residue_identity`) + `933-966`
  (`_live_attempt_took_the_path`) — ownership is settled by `(st_dev, st_ino,
  st_size, st_mtime_ns, st_ctime_ns)` recorded at withdraw time, with a digest
  fallback only when identity is unchanged; both the unreadable-residue and
  identical-content-rewrite cases are now correctly recognised as live work.
- `leaves.py:883-926` (`withdraw`) — identity is checked *before* any read, so
  a residue already on file in `self._residues` short-circuits to
  `_unchanged` (leaves.py:1015-1020) instead of re-reading/re-hashing and
  re-quoting under a new attempt's name.

Traced every branch of `_LeafHarvest` (`run`, `withdraw`,
`_live_attempt_took_the_path`, `_disown`, `_preserve`) by hand against the
brief's six success criteria and cross-checked against `gate-logs/C4-verify.log`
(13 failures pre-fix on the exact assertions the brief names, 17/17 green
post-fix) and `gate-logs/T3-suite.log` (1820 tests, OK). Independently re-ran
`template/tests/test_attempt_harvest.py` as a non-root user (all 17 tests,
including the 8 `@unittest.skipUnless(_rootless())` permission-dependent legs,
genuinely executed rather than skipped) — all pass.

No correctness bug was found in the patch itself. Two minor, non-blocking
observations, neither rising to a defect against the brief:

- `leaves.py:965` — the digest-comparison fallback inside
  `_live_attempt_took_the_path` (used only when a *new* stat exactly matches a
  previously-recorded residue's `(dev, ino, size, mtime_ns, ctime_ns)` tuple —
  i.e., an in-place rewrite a coarse clock failed to separate) is not exercised
  by any test leg; every legged scenario changes at least one of those five
  fields on a real write. This is a defensive branch for a filesystem/timing
  edge case the test harness cannot reliably construct, not a sign of a wrong
  implementation — the reasoning in the docstring (leaves.py:943-950) is sound
  and the branch is cheap. Not asking for a rebuild over it.
- `leaves.py:1077-1090` (`_artifact_digest`) and `leaves.py:1023-1055`
  (`_read_residue`) both stream-hash a file in chunks but for different
  purposes (unbounded full-file digest for comparison vs. bounded head/tail
  quote-plus-digest for the withdrawn record); there's no pre-existing
  streaming-file-hash helper elsewhere in the module they could have shared
  (checked `act.py`/`handoff.py`'s `sha256` usages — both hash an
  already-in-memory string, not a file). The mild duplication between the two
  functions is justified by their differing bound requirements, not a
  reuse gap worth flagging.

The three harvest sites (`leaves.py:2927-2940`, `3283-3294`, `3586-3596`) are
wired identically through the one `_LeafHarvest` owner, satisfying criterion 6
without any hand-copied logic left behind at any site — confirmed by reading
all three call sites directly, not just the diff hunks.

No NEEDS-HUMAN findings from this lens.
