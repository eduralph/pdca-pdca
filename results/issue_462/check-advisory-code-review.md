# Advisory code review — issue #462 (merge-wave-waits-for-its-evidence)

Second lens: bugs the patch itself introduces, and reuse/simplification/efficiency.
Grounded on `target/template/src/pdca_harness/{merge.py,config.py}`,
`target/template/tests/test_merge.py`, `target/template/pdca.toml.jinja` (post-patch).

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:143-160` (`_wait_for_green`):
  the bound is tracked as a count of *sleep* seconds (`waited += step`), not elapsed
  wall-clock time. Each `_check_rollup` call is a real `gh pr checks` subprocess (network
  round-trip); its latency is never added to `waited`, so the loop's actual wall-clock
  duration is `merge_wait_secs` plus the cumulative latency of up to
  `merge_wait_secs / 15` `gh` calls. For a slow `gh`/host this can meaningfully overshoot
  the configured bound the success criterion calls "bounded, configurable" (brief §Success
  criterion (i)/(ii)). A `time.monotonic()`-based deadline (`deadline = _now() + wait_secs;
  while verdict in (...) and _now() < deadline: ...`) would be both tighter and no harder
  to keep patchable for tests (the mocked `_sleep` already costs zero real time, and the
  mocked `_check_rollup`/`subprocess.run` calls are instant in the suite, so a real clock
  read would not slow `test_merge.py` down). Low severity — bounded overshoot, never
  unbounded — but worth tightening since "bounded" is the literal invariant being restored.

- NEEDS-HUMAN [impl] — `template/tests/test_merge.py`: every new/updated case that
  exercises the `_undo_ready` path uses a `failing`, `pending`-timeout, or `gh pr merge`
  failure verdict (`test_merge_failure_stops:157-159`,
  `test_failing_check_refuses_and_never_merges:268-269`,
  `test_pending_check_refuses:285-287`,
  `test_wait_bound_zero_performs_no_wait:414-420` in the patched file). None drives an
  `unreadable` rollup (`merge.py:239`, `_check_rollup`'s fifth verdict, unchanged by this
  patch) through `_merge_one` and asserts the `gh pr ready --undo` call. The code path is
  the same `if verdict != "green": ... _undo_ready(pr_url)` branch used for the other three
  verdicts (`merge.py:232-248`), so this is very likely a correct-by-construction case, not
  a live bug — but the brief's own success criterion (ii) names `unreadable` explicitly
  alongside `failing`/timeout as a path that must both STOP *and* restore draft (iii), and
  right now nothing in the suite would catch a future edit that special-cased `unreadable`
  differently (e.g. someone "optimizing" the dict-branch dispatch). A `_drive(...,
  checks=SimpleNamespace(returncode=1, stdout="", stderr="boom"))` case mirroring
  `test_failing_check_refuses_and_never_merges` would close the gap cheaply.

## Not flagged (checked, found clean)

- `_wait_for_green`'s loop always makes forward progress (`step >= 1` whenever the loop
  guard is true, since `wait_secs - waited >= 1` there) — no infinite-loop or zero-sleep
  risk; `merge_wait_secs = 0` is a genuine single-read no-op (`merge.py:148-152`,
  confirmed against `test_wait_bound_zero_performs_no_wait`).
- `config.py:719-729` mirrors the existing `merge_requires` fail-closed pattern exactly
  (bad type → default, out-of-range → default, both warn on stderr) — no new validation
  gap, no crash on a malformed `pdca.toml`.
- `merge_wait_secs` is inserted in `pdca.toml.jinja` before the next `[install]` header
  (`:153`), so it lands in `[driver]` as intended — the file's own "silently joins the
  next table" trap (cited in the brief) is avoided.
- Every decline path that follows the ready-mark (`rollup != green`, and a failing
  `gh pr merge`) now calls `_undo_ready` (`merge.py:248`, `:261`); the `gh pr ready`
  failure path (`:211-216`) correctly does *not* call it, since that call never marked
  the PR ready in the first place.
- No duplicated rollup-classification logic — `_wait_for_green` calls `_check_rollup`
  rather than re-deriving the bucket rules, as the brief's citation directs.
- Scope matches the brief: only `merge.py`, `config.py`, `pdca.toml.jinja`, and
  `test_merge.py` are touched; `docs/07-crosscutting.md` and `docs/05-check.md` are
  untouched, as declared out of scope.
- C4-verify's logged red leg (`gate-logs/C4-verify.log`) genuinely fails on production
  reverted (`AttributeError: 'Config' object has no attribute 'merge_wait_secs'` plus the
  old-behaviour assertion failures) and genuinely passes with the fix — the regression
  test exercises the real defect, not a copy.
