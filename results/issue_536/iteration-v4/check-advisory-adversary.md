# Adversarial review — attempt-owned leaf records and harvests (#536, iteration 4)

Evidence re-run independently in a scratch copy of `$PDCA_TARGET` (python 3.14, offline):
green leg `26/26 OK`; red leg (production hunks reverted, test hunk kept) `19 failures + 4
errors` — the red→green in `check-gates.json` C4 is real, the five tests green on both legs
are the declared "nothing else changes" regressions (criterion iii/vi), not padding. The
tests drive real subprocesses through `leaves._invoke_leaf_resilient`,
`leaves._run_review_sandboxed`, `_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`,
`leaves.review_never_ran` and `assemble._missing_review_text` — production, not a copy. I
then ran 20 targeted mutations of the new logic against the full 1784-test driver suite and
9 impersonation payloads through the real wrapper. Three findings.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:912`: `leaf_run_incomplete`
  reads the log with `read_text(encoding="utf-8")` and guards only `except OSError`
  (`:913`), but its own docstring promises "Absent or **unreadable** ⇒ False" (`:909-910`).
  A log whose bytes are not valid UTF-8 raises `UnicodeDecodeError` (a `ValueError`) straight
  out of the discriminator. Reproduced: `log.write_bytes(b"----- attempt 1 - exit 1 -----\n\xff\xfe tail\n")`
  then `leaves.review_never_ran(d)` → `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff`.
  This is a **new** crash surface: `review_never_ran` (`:2430`) and
  `assemble._missing_review_text` (`assemble.py:425`) previously only `.exists()`-tested this
  file, and both now sit on `driver.advance`'s critical path — an undecodable log aborts the
  whole cycle instead of degrading. The reachable route is the patch's own premise: a log the
  **pre-patch** non-atomic `write_text` (base `leaves.py:720`) left truncated mid-multibyte by
  a kill, read after a harness upgrade. Note the inconsistency inside the same patch —
  `_residue_record` reads defensively (`:1004`, `errors="replace"`), this reader does not.
  One-line fix: `errors="replace"`, or `except (OSError, ValueError)`.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:1004`: `_residue_record` reads the
  **entire** dead attempt's artifact into the driver process and only then applies the
  `_RESIDUE_KEEP` bound (`:1007`), whose constant docstring (`:978`) justifies itself by "a
  runaway leaf could write an arbitrarily large file". Measured: a 200 MB `check-review.md`
  costs 420 MB peak allocation in the driver to produce a 20 161-char record. Worse, the read
  is called from *inside* the `except Exception` handler (`:758`, under the
  `# a failed leaf must never crash the cycle` guard at `:750`), and only `OSError` is caught
  (`:1005`) — so a `MemoryError` escapes the guard entirely. Demonstrated end-to-end with a
  stub reviewer that writes an artifact then dies transiently, with the artifact read raising
  `MemoryError`: `_run_review_sandboxed` propagates it and leaves **no `check-review.md`
  placeholder and no `check-review.error.log`** — precisely the "no artifact and no account"
  state this slice exists to eliminate, and it would abort `driver.advance`. The same escape
  applies at the two advisory sites, under the `# advisory must never crash the cycle`
  comment (`:3222`). The base never read this file at all (bare `.exists()` + streamed
  `shutil.copy2`), so both the allocation and the escape are patch-introduced. Fix: bounded
  read (`open(...).read(_RESIDUE_KEEP + 1)`) and widen the guard to `Exception`.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:3176`: the second of the two #369
  recovery discriminators the brief's criterion (v) names explicitly —
  `run_advisory_leaves(only_missing=True)` — is **not exercised by any test**. Reverting that
  line to the base's bare `advisory_error_log(d, leaf_id).exists()` leaves the whole driver
  suite green: `Ran 1784 tests ... OK (skipped=2)`. `test_attempt_ownership.py` calls
  `review_never_ran` nine times and `only_missing` never (no occurrence in the file). The
  regression that would ship green: an advisory leaf that ran, died transiently and was killed
  mid-retry leaves an in-flight log and no artifact, `_resume_interrupted_check` skips it, and
  the bundle reaches sign-off with that advisory leaf silently absent — the exact criterion-(v)
  failure, on the twin the round-1 carry-forward already asked to be covered (item 4). One test:
  seed a bundle with an in-flight advisory error log and no artifact, assert the leaf is re-run.

## Attempted and could not refute

- **The red leg is not a symbol-existence trap.** Every assertion is behavioural and the file
  imports only pre-existing API; the C4 red leg fails on `AssertionError` / the base's own
  `error_log.write_text` at `:720`, not on `ImportError` — no `PDCA-UNVERIFIABLE`.
- **20 mutations of the new production logic, 19 caught** by the 1784-test suite: whole-line →
  substring match in `leaf_run_incomplete`; dropping `_defang_in_flight` in `_format_leaf_attempt`
  and in `_residue_record`; `_atomic_write_text` → plain `write_text`; withdrawing before
  persisting; dropping the `recorded` gate on the retry; dropping the `records` conjunct on the
  keep-the-log condition; dropping the re-flush on a refused withdrawal; `_empty_run_class` →
  always substantive; reverting `assemble.py:425` and `review_never_ran` to `.exists()`; deleting
  `_settle_leaf_record` at each of the five call sites; settling *before* the outcome is filed.
  Only the `only_missing` revert above survived (plus the untested `_RESIDUE_KEEP` bound, folded
  into finding 2).
- **Impersonation.** Nine payloads through the real wrapper — bare marker, whitespace/NBSP
  padded, doubled, CRLF, marker + trailing blanks, marker mid-line, defanged-then-real, and a
  payload long enough to exercise `progress`' 200-line stderr tail cap — none flipped
  `leaf_run_incomplete` on a spent run. The defang cannot synthesise the marker (`pdca:` →
  `pdca-quoted:` is one-way), and truncation at `_RESIDUE_KEEP` can only break it.
- **Kill-ordering.** I walked every ordering of the loop (`:750-775`) and the three harvests: I
  could not construct a kill point that leaves an interrupted leaf looking spent. The
  `recorded`/`owned` fail-closed stops hold; a failed non-first flush leaves a stale marker only
  until the harvest's `_settle_leaf_record`, which is covered.
- **Scope.** No touch to `progress.py`, `LeafError.transient`, the retry set, the builder path,
  the staleness clear (`:718`), or `test_leaf_resilience.py`; no `tests/fixtures/`; all three
  `_invoke_leaf_resilient` call sites pass `artifact=`. `has_cycle_evidence` (`state.py:203`) is
  the only other consumer of the log's existence and the change only makes it *less* likely to
  mis-settle a live bundle.
- **Examined and accepted, not filed:** a success that *did* produce its artifact discards the
  log and with it the dead predecessor's quoted verdict (`:748`) — the round-2 sign-off
  adjudicated exactly this reading of criterion (vi), so it is settled scope, not a defect.
