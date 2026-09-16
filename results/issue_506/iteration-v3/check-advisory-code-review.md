# Advisory code review — correctness & reuse/efficiency lens (issue #506)

## Findings

- **NEEDS-HUMAN — reviewer/advisory/plan-advisory harvest is attempt-blind, and this
  patch widens the retry surface that can trigger it** (`template/src/pdca_harness/leaves.py:2653-2654`,
  `:2973/:2986`, `:3275/:3287`). All three sandboxed leaves run every attempt of
  `_invoke_leaf_resilient` in the *same* `sandbox` tempdir, then simply check
  `if produced.exists(): copy` / `if out.exists(): copy` after the wrapper returns
  `None` (success) — with no record of *which* attempt wrote the file. Before this
  patch, a reviewer/advisory retry only ever fired on a true no-output invocation
  death, so a stale `check-review.md` from a prior attempt could not exist to be
  mis-harvested. This patch's widened transient classification (`progress._terminal_error`
  / `_note_terminal`) now also retries a leaf that already did real work and wrote a
  *partial* artifact before its terminal transient death — so a retried attempt that
  exits 0 without re-writing the file (e.g. it half-completes, or misreads the leftover
  artifact as "already done") will have its predecessor's partial `check-review.md` /
  `check-advisory-*.md` / `plan-advisory-*.md` silently copied into the bundle as the
  final verdict. This exact risk is called out explicitly in the brief's iteration-2
  sign-off notes ("SCOPE — flagged, do NOT expand the slice to it... if the rebuild
  concludes this cannot be closed within the slice, say so in build-notes.md and leave
  it for a separate issue") — build-notes.md is withheld from this lens, so a human
  should confirm it was actually recorded/tracked rather than silently dropped, since
  the vulnerability is real and now more reachable than before the patch.

- Minor efficiency/reuse nit — **redundant per-line JSON parsing in the stream drain
  hot path** (`template/src/pdca_harness/progress.py:182-194`). The drain loop already
  called `json.loads` twice per stream line before this patch (`_is_session_event`,
  `_stream_tool_label`); this patch adds `_terminal_error` (parses every line
  unconditionally) and, conditionally, `_is_work_event` (parses again) — up to 4
  independent `json.loads` calls on the same line, each with its own try/except and
  `isinstance(ev, dict)` guard. For the long streaming sessions this very issue is
  about (the incident cited an ~18-minute run), this is needless repeated work in the
  one loop that runs on every emitted stream event. A single `json.loads` per line,
  passed as a parsed dict to each classifier, would keep the same dispatch-by-`fmt`
  shape at a fraction of the cost. Not a correctness bug (best-effort try/except means
  behavior is unaffected either way), so not gating — worth a follow-up cleanup.

## Not flagged

- The sticky-`terminal` design (`progress._note_terminal`, `progress.py:592-610` in the
  diff) — where a transient report survives a later non-transient marked report unless
  real work intervenes — looked overbroad at first glance (it defeats *any* subsequent
  report, not just the `result` wrap-up that motivated it), but this is exactly the
  fix iteration 2's sign-off mandated ("Make a transient report STICKY unless real work
  follows it"), so it's treated as intentional, not a defect.
- `_do_build_command` no longer passes `memory_log=` explicitly, relying on
  `_memory_log_for` to derive `build.memory.jsonl` from `build.error.log` — verified
  against `_memory_log_for` (`leaves.py:368-377`): the derivation is correct and matches
  the other three call sites, closing the iteration-1 review note cleanly.
- `_invoke_leaf_resilient`'s per-attempt flush (`_write_attempt_records`, called before
  the backoff `time.sleep`) and the `_BUILD_RETRY_NOTE` pointer at `BUILD_ERROR_LOG` were
  re-verified against the code: the file is genuinely readable by the next attempt (and
  by a run killed mid-backoff), closing the iteration-2 "false instruction" defect.
- Ran `template/tests/test_leaf_resilience.py` locally against the target tree (29
  tests) — all green, exercising the real `_invoke` → `progress.run_with_heartbeat` →
  `subprocess` path with a stub leaf, not a mock of the classifier.
