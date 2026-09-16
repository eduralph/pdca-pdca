# Build notes — issue 506 (a transient leaf death is explained and retried)

Target: `eduralph/pdca-harness @ main`. All edits in the cycle worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l0` (base `acb214a`); every `path:line` below is on
that tree **with the patch applied** unless it says "base".

## What the change is, in three places (the invariant is not guardable in one)

The brief's invariant — *a leaf's failure must be attributable and classified by what
actually happened* — decomposes exactly as the brief says it does: classification lives in
the stream reader, retention in the error-log writer, retry at the builder call site.

1. **Classification — read the terminal event the stream already delivers.**
   `progress._terminal_error_text` (`template/src/pdca_harness/progress.py:442-463`), with
   `_claude_event_texts` (`:466-482`) and `_work_continued` (`:485-498`), sits beside the
   existing per-family classifier `_is_session_event` (`:398-410`) and has its shape:
   dispatch on `stream_format`, best-effort `json.loads`, degrade-to-today default (codex
   and every stream-less family answer `""`/`False`, so nothing is guessed about a vendor
   error text we have not verified). The drain thread consults it
   (`progress.py:169-181`) and `run_with_heartbeat` returns
   `produced["session"] and not terminal["error"]` (`:288`).
   The old rule ("produced anything" ⇒ substantive) is a **proxy for "died at
   invocation"**; the fix does not guard the proxy, it replaces it with the fact.

2. **Retention — the same bounded-tail route the stderr tail already takes.** The terminal
   error text is appended to `output` at `progress.py:280-286`, i.e. exactly where
   `err_tail` becomes `output` on the base (`progress.py:255`). So
   `leaves._format_leaf_attempt` (`leaves.py:737-743`) needs **no** special case, and the
   `(no output captured)` fallback stops firing for this death. The memory-telemetry
   post-mortem (#420) still rides the same `output` (`leaves.py:665-668`), untouched.

3. **Retry — the builder joins the resilient path.** `_do_build_command` now calls
   `_invoke_leaf_resilient` (`leaves.py:1865-1886`) instead of plain `_invoke`
   (base `leaves.py:1824`), reusing the wrapper **as it is** — its attempts/backoff
   defaults, its error-log staleness rule, its `_memory_log_for` pairing (which derives
   `build.error.log` → `build.memory.jsonl`, byte-identical to the `BUILD_MEMORY_LOG` the
   call site already passed). The exception is re-raised (`:1885-1886`) so `do_build`'s
   capture-and-re-raise contract and `flow._isolate` see what they see today.

Supporting edits, each forced by the three above:

- `do_build`'s capture no longer clobbers the wrapper's per-attempt log
  (`leaves.py:1793-1799` + `_has_content`, `leaves.py:746-752`). Without this, the multi-
  attempt post-mortem the wrapper had just written was overwritten by a single record —
  criterion (iii) undone by the very handler that exists to preserve evidence. A setup
  failure (`worktree.ensure`, the lane lock) still writes, because nothing is on disk then;
  `test_a_setup_failure_before_the_leaf_launches_is_captured` still pins that.
- The exhausted-retry operator line (`leaves.py:1805-1815`): names the class (TRANSIENT
  infra), where the cause is (`build.error.log`), and the resume (re-drive Do on this
  bundle). It is printed **before** the raise, so `flow._isolate`'s
  `build/check failed (LeafError: Command '[…]' returned non-zero exit status 1)` is no
  longer all the operator gets.
- `_invoke_leaf_resilient`'s final `write_text` is now OSError-tolerant
  (`leaves.py:731-735`). Required: `test_capture_never_masks_the_real_failure` patches
  `Path.write_text` to raise, and with the builder on the wrapper an unguarded write there
  would replace the leaf's `LeafError` with an `OSError` — capture masking the real
  failure, the exact rule `do_build` already applies at `leaves.py:1801-1802`.
- Two prose fixes that would otherwise become lies: the retry notice no longer says "with
  no output" (`leaves.py:721-726`), and the transient placeholder no longer asserts the
  leaf "exited non-zero with no output" (`leaves.py:2646-2651`). The `transient infra —
  safe to re-run` wording, the `LEAF_STATUS_INFRA` marker and the §6 row are unchanged.
- The retry notice now prefers the leaf's `label` over `workdir.name`: for a cwd-discovery
  builder `workdir` is the harness root, which names no bundle at all.

## Alternatives considered, with their cost

- **Return a 4th value from `run_with_heartbeat`** (`(rc, output, produced, transient)`)
  instead of folding the signal into `produced`. Rejected on a measured cost: 18 call sites
  unpack the 3-tuple today — `gates.py:559`, `leaves.py` ×2, `publish.py:833`,
  `template/tests/test_progress.py` ×12, `template/tests/test_leaf_memory_log.py` ×2. The
  14 in `template/tests/*` are the deciding ones: C4's red leg **keeps** every test hunk and
  reverts production, so all 14 would raise `ValueError: too many values to unpack` against
  the reverted 3-tuple — 14 tests red for a reason that has nothing to do with the defect,
  and a red leg whose evidence is unreadable. The chosen route changes 1 line of return
  (`progress.py:288`) and 0 call sites. Cost of the choice: `produced` now means "did
  substantive work **and** was not killed by an error it reported itself" — paid for in the
  docstrings that define it (`progress.py:59-79`, `leaves.py:91-100`), which are the only
  two places that word is contracted.
- **Match the error text anywhere in the stream** (no "terminal" requirement). Rejected: a
  builder working on *this* issue emits assistant text quoting `API Error: Connection lost
  mid-response.`, so an "error seen anywhere" rule would retry a genuinely substantive Do
  three times, at ~18 minutes an attempt. `_work_continued` (`progress.py:485-498`) keeps
  the signal terminal — work after the error clears it — and `_ERROR_LEAD_RE`
  (`progress.py:420-422`) additionally requires the text to *read as* an error report, not
  merely mention one. Both directions are pinned:
  `test_prose_that_mentions_an_api_error_is_still_substantive` and
  `test_an_error_the_session_recovered_from_is_not_terminal`.
- **Override `LeafError.__str__`** so `flow._isolate`'s line explains itself. Rejected: that
  string is embedded verbatim in reviewer/advisory placeholders
  (`leaves.py:2561-2568`, `:2894-2900`, `:3196-3202` → `_review_unavailable`), so it would
  silently rewrite artifacts the brief's criterion (v) freezes. A dedicated stderr line at
  the one call site costs 6 lines and changes no artifact.
- **A `pdca.toml` knob for the builder's attempts/backoff.** Explicitly out of scope in the
  brief; the wrapper's existing defaults (3 attempts, 4 s doubling) are reused unchanged.
- **A `system`/`api_retry` reader.** Not added: those events are the CLI's *recoverable*
  retry notice (documented at `progress.py:70-72`), not a terminal death, and their payload
  shape is unverified. Degrading to today's behaviour there is deliberate.

**Session-resume, as the brief asks me to state:** the retry is a **fresh re-invoke** of the
builder with the same prompt, not the CLI's own session resume. For this incident nothing
would have been lost either way (the identical argv re-run minutes later succeeded); the
cost of the cheap version is that a leaf which died 18 minutes in redoes those 18 minutes,
and a partially-written `patch.diff` from the dead attempt is left in the bundle for the
retry to overwrite. Resume is the brief's out-of-scope item and remains open.

## Test cost note (sibling suite)

`do_build` on the resilient path means the mocked transient `LeafError`s in
`template/tests/test_build_error_log.py` now retry with the real 4 s + 8 s backoff:
measured, that module went **0.069 s → 36.1 s**. Three `mock.patch.object(leaves.time,
"sleep")` lines bring it back to **0.092 s** (whole offline suite: 29.0 s, same as base).
Those cases pin capture, not backoff; the backoff itself is pinned in
`test_leaf_resilience.py`.

## Refuting my own test (forced, recorded)

**(a) Genuine red?** Yes — proven by the project's own C4 gate, not by hand:
`./engine/scripts/run-verify.sh` reverts the production hunks and keeps the test hunks →
`FAILED (failures=4)` → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The
four, one per success criterion:
- (i) `test_a_terminal_transient_error_after_real_work_is_retried` → `AssertionError: False
  is not true` (`err.transient` is False on the base rule);
- (iii) `test_the_error_log_carries_the_leafs_own_terminal_error` → the log on the red leg
  is *the incident's artifact verbatim*: `----- attempt 1 — exit 1 ----- (no output
  captured) LeafError: Command '[…]' returned non-zero exit status 1.`;
- (ii) `test_a_transient_builder_death_is_retried_bounded_with_backoff` →
  `AssertionError: 1 != 3` (the builder was never retried);
- (iv) `test_the_exhausted_message_names_the_class_and_the_resume` → `'transient' not found
  in 'leaves: issue_506 — do failed; captured the error tail in build.error.log'`.
The other three appended cases (the two precision guards + the negative Do case) pass on
both legs by design — they bound the fix, they are not the red.

**(b) Production path?** Yes. The tests call `leaves._invoke_leaf_resilient` and
`leaves.do_build` directly, which run the real `_invoke` → `progress.run_with_heartbeat` →
`subprocess.Popen` path against a real child process. Nothing in the classification, the
retention or the retry is stubbed: the only patches are `time.sleep` (wall clock) and
`os.environ` (handing the child its markers). `do_build` is entered at the top, so
`select_builder`, the lane lock, `worktree.ensure`, `_record_loop_attempt` and
`_build_prompt` all really run.

**(c) Fixture includes the fault?** Yes — and the first cut of it did **not**, which is why
this section exists. The stub leaf emits real work *and then* the incident's verbatim
`API Error: Connection lost mid-response.` before exiting 1; nothing curates the failing
event out. But in the first cut the marker was an argv **literal**, and
`_format_leaf_attempt` echoes the failed command line into the log — so
`assertIn(_API_ERROR, log)` passed on the RED leg with no capture whatsoever (observed in
the gate output: the string was found inside the echoed `python3 -c "…"` argv). The markers
are now delivered through the **environment** (`_LEAF_ENV`,
`template/tests/test_leaf_resilience.py:48-56`), the same trap and the same fix recorded in
`test_build_error_log.py:183-192` on the base — so the only way a marker can reach the log
is by actually being captured off the stream. Re-verified: the red leg now fails with
`'API Error: Connection lost mid-response.' not found in '… (no output captured) …'`.

## Gates run here

- `./engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it`.
- `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` (the runner
  CONTRIBUTING.md names) → `Ran 1765 tests … OK (skipped=2)` in 28.6 s.
- `./engine/scripts/run-suite.sh` → `PDCA-EVIDENCE: root suite OK, driver suite OK`
  (copier render + `copier update` compatibility included).
- Commit-readiness: the target configures no formatter/linter hook — CONTRIBUTING.md and
  AGENTS.md require DCO sign-off, a conventional-prefix subject and a green offline suite;
  CI is `docs-check`, `render-check`, `require-linked-issue`. No docs changed, so
  `docs-check` is unaffected. Added lines stay ≤ 97 chars, inside the file's existing range.

No external dependency was needed: every leg runs on stdlib Python with a stub leaf, offline
— as the brief's `External dependencies: none` predicted.

## STOP discipline

No branch pushed, no PR opened, no PR marked ready. Artifacts only.
