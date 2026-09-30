# Build notes — issue 539 (what a transient leaf death is, decided once)

Base: the worktree at `41c19e9` ("pdca-integrate: issue_537"), which carries #538 (merged,
`b920752`), #540 (merged, `4050da2`) and #537 (folded). Line numbers below are **pre-patch**
on that base unless marked "post".

## What changed and why

**The verdict, computed in the stream reader** (`template/src/pdca_harness/progress.py`).

- The drain now asks one more question of the marked record child-1 keeps: is its cause
  one the vendor marks transient? `_reports_transient_cause` (post `:803`) answers from the
  vendor's stamped kind (`server_error` / `overloaded` / `rate_limit`), from the `unknown`
  kind's text only when no typed `api_error` is on it, and from the `success` wrap-up's HTTP
  status (408/409/429/5xx). A sub-agent's report never answers yes.
- The verdict follows the record `_note_terminal` keeps (it now returns whether it kept the
  record, pre `:595-618`). So a farther record that cannot bury the cause's text cannot
  overrule its verdict either.
- Main-session `assistant` or `user` work after the report clears the verdict only
  (`_is_main_session_work`, post `:854`; drain, post `:258-267`). The kept text stays, so
  criterion (v) holds: a recovered report is still in the error log.
- At return (pre `:327-330`, post `:381-389`) the verdict is folded into `produced` only when
  the run ended non-zero and was not the harness's own timeout (`rc not in (0, TIMEOUT_RC)`).
  Exit 0 and a timeout keep `produced` as it was.
- `is_signal_death(rc)` (post `:34-58`) answers both spellings: `-signum` and the shell's
  `128+signum`, for signals 1..64. `TIMEOUT_RC` (-1001) falls outside both ranges.

**The property** (`leaves.py:105-109` → post `:108-116`):
`transient = not produced and not progress.is_signal_death(returncode)`. This is the fix for
round 3's defect (a): the code changes, not just the sentence. The manner of the kill lives
in exactly one place. `progress` decides "did the stream show work that stands as its own";
the property adds "and no signal ended it".

**Every restatement, rewritten to the two-shape definition.** These are prose-only; the one
code change in `leaves.py` is the property.

- `LeafError` docstring (`:93-99`).
- `_invoke` fallback comment (`:674-677`; the `produced or not use_stream` code is untouched).
- `_invoke_leaf_resilient` docstring (`:703-707`). It also states that a retry is a fresh
  re-invoke, not a session resume, as the brief asked.
- The retry print (`:755-757`, string only; the folded `for attempt` loop is otherwise
  untouched).
- The reviewer call-site comment (`:2918-2919`).
- The `_FAIL_*` comments and the INFRA/SUBSTANTIVE split comment above them (`:2939-2944`).
- `_failure_class` (`:2956-2957`).
- `_unavailable_classification` (`:3002-3003`, `:3014-3018`).
- `assemble.py:103` (comment) and `:109`, the operator-facing label. It now reads *"leaf
  died of transient infra (before emitting any work, or on its own transient API-error
  report — safe to re-run)"*. That fixes round 3's defects (b) (both shapes) and (c) (the
  label). "Safe to re-run" stays: re-running is still the right action.
- `progress.py` prose that said "nothing is classified" / "produced is byte-identical"
  (`:61-66`, `:78-79`, `:210-212` area, `:328-329`, `:466-468`, `:488-489`, `:572-573`).

**Provenance**: `template/tests/fixtures/README.md` gets a new section, "Classifying the
report (issue #539)". It says which claims are observed and which are derived, and gives
greps that re-verify each one. I ran every grep against the installed binary and each
matched.

## Vendor grounding (claude-code 2.1.284, the installed binary)

Re-derived, not copied from round 3 (which read 2.1.233):

- The vendor's own transient rule is `Akr(e)`: `apiErrorIsTransient===!0 ||
  error==="overloaded" || error==="server_error"`. Its sub-agent recovery set is
  `rl = new Set(["rate_limit","overloaded","server_error"])`. The `apiErrorIsTransient`
  flag is absent from the wire converter `_o`, so it never reaches the stream.
- **New since 2.1.233:** a lost connection is now stamped `server_error` directly (the
  `JF`/`J0` code sets), with text `Connection to the API was lost (<code>)`. So the
  `unknown`-text path matters less than it did in round 3.
- **New since 2.1.233:** there is a typed `api_error` field. The `unknown` kind now
  sometimes carries a typed cause (`gateway_signin_required`, `gateway_session_expired`,
  `provider_credentials`), and all of those are sign-in or credential stops. So an
  `unknown` report with any typed `api_error` does not have its prose read. This is a
  refinement over round 3, and it only ever withholds a retry.
- The HTTP status reaches the stream only on the `success` wrap-up. It is taken from the
  last main-loop assistant message (`pt=n.isApiErrorMessage===!0,
  Ut=n.apiErrorStatus??null`). The SDK schema declares `api_error_status` on the assistant
  message, but no 2.1.284 emitter sets it.
- The status set follows the API client's own `shouldRetry`: 408, 409, 429, >=500. Round 3
  had 425; I dropped it because the client does not retry 425.
- A main-session tool result is `{type:"user", parent_tool_use_id:null}` (emitter `PYt`). A
  sub-agent's carries the Task id.

**Not observed:** a real 2.1.284 stream of an API-error death. The only observed death
record is the 2.1.228 incident transcript, which is replayed in the test.

## Deviations from the brief — the human should look at these

1. **I edited child-1's `test_terminal_error_retention.py`, which the brief says not to
   touch.** Three of its guards (the old `NothingIsClassified` class) assert the exact
   opposite of this brief's criterion (i):
   - `_stream(_WORK, _REPORT)` with a `server_error` report and exit 1 → "not transient,
     1 run";
   - `_stream(_REPORT)` → the same;
   - `produced` stays True for both.

   No implementation can satisfy criterion (i) and leave those green. Child-1's own
   docstring says the guards exist "so a later change cannot silently move them", which
   means this change is expected to move them in the open. I flipped exactly those three
   assertions, renamed the class to `RetryCountsArePinned`, and rewrote the one docstring
   bullet. I added one line showing that a permanent report is retained with `produced`
   True, so the guard still shows that retention alone classifies nothing. Nothing about
   retention changed, and all 31 other cases in that file pass unchanged.
2. **I changed one string in `_do_build_command` (#537's code, pre `:2187-2190`), which the
   brief fences off.** That print is operator-facing. It said the builder "exited N without
   emitting any work", which is false for the headline case once this change lands (an
   18-minute builder that died on its own transient report). The change is string only.
   `test_builder_retry.py` asserts only the `— transient:` prefix, which is kept. The fence
   was drawn at plan time, before #537 was folded and before this print existed on the base.
3. **The brief says `test_leaf_status.py:188` goes red. It does not.** `:188` checks the
   *startup* label ("leaf did not run (its command could not be launched…)"). That label is
   true and I kept it. The line that did go red was `:225`: it found the transient
   reviewer's §6 row by searching for "leaf did not run". I updated `:135`, `:225` and the
   `:84` comment. `:215` (a real artifact is not relabelled) still holds as written.
4. `_note_terminal` now returns a bool (it used to return None). Its retention behaviour is
   byte-identical. This is the smallest way to tie the verdict to the kept record without
   copying the precedence rule.

## Consequence to state (not widened)

- #537 put the builder on `_invoke_leaf_resilient`, so the builder now spends this retry
  set. An 18-minute builder that ends on its own `server_error` report is re-invoked up to
  twice more, with #537's retry notice about residue. That can triple the most expensive
  leaf's cost on a real outage. That is the trade the brief accepted. A retry is a fresh
  re-invoke; resuming the CLI session is out of scope.
- A signal death is now 1 attempt, down from 3, whether the leaf emitted anything or not.
  What to do with it beyond "don't re-run into the same cap" is still #510's question.
- `rate_limit` also covers usage-quota exhaustion. The vendor's `ua(e)` is
  `429 && rate_limit && !apiErrorIsTransient`. A 4s/8s backoff won't clear a quota lock,
  but a re-invoked leaf then hits the limit on its first request, so each extra attempt is
  cheap.
- `server_error` with a typed `tls_untrusted_ca` is retried because the vendor's rule keys
  on the kind alone. It dies at the first request, which #138 already retried.

## Alternatives ruled out, with their cost

- **Carry the verdict on a new `LeafError` field or a fourth return value** instead of
  folding it into `produced`. This touches `_invoke`'s `raise` (pre `:678`) and
  `LeafError.__init__`, which is outside "leaves.py strings, comments and the `transient`
  property only". A 4-tuple return breaks every 3-tuple unpack of `run_with_heartbeat`:
  21 call sites across `src/` and `tests/` (`grep -c "run_with_heartbeat("` minus the def).
  Rejected on scope and churn.
- **Put the signal exclusion in `progress` (keep `produced=True` on a signal death).** That
  makes `produced` claim "did work" for a leaf that emitted nothing. It also means the
  manner-of-kill rule lives beside the stream verdict instead of on the returncode the
  property already holds. The property-side check is 1 line and covers both shapes.
- **Read the `LeafError.output` text to classify.** That is prose the leaf's stderr can
  forge. Rejected on the invariant.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** On the unfixed base, the new file had 21 of 39 cases fail on
  assertions, not imports; the exit-0 guard added later is green on both legs by design.
  Through the project's C4 script (`engine/scripts/run-verify.sh`, which reverts only the
  production hunks), the red leg was: new file 21/40 fail, `test_leaf_status` 2/15,
  `test_terminal_error_retention` 3/34. It printed `PDCA-EVIDENCE: C4 PASS — red without
  the fix, green with it`. No module failed to import on the red leg; the new file imports
  only API that existed before this patch.
- **(b) Production path? Yes.** Every case drives `leaves._invoke_leaf_resilient` → `_invoke`
  → `progress.run_with_heartbeat` with a real child process (a Python stub). There is no
  mock and no copy of the classifier. The §6 case goes through `_failure_class`,
  `_review_unavailable` and `assemble._items_from_artifact`. C5 (`run-prod-path.py`)
  confirms the file imports `pdca_harness`. I also broke 21 guards one at a time; each
  broken guard fails at least one test, including the three the brief requires (`user` in
  the work set, the status set, the `subtype == "success"` guard) and the exit-0 fold.
- **(c) Fixture includes the fault? Yes, with one caveat.**
  - The stub really emits the marked report and exits 1.
  - SIGKILL and SIGTERM are really delivered to the child (`os.kill`, rc -9 / -15).
  - The 137 case includes a real `sh -c` wrapper that outlives the killed child.
  - The observed 2.1.228 incident record is replayed after an inline work event.

  Caveat: no real `claude` CLI and no real cgroup OOM kill. `--scope` execs the leaf as a
  direct child (`leaves.py:241-244`), so a real OOM kill surfaces as the same -9 the stub
  produces. The stream shapes are the vendor's derived shapes, not a captured 2.1.284 death.

## Runs

- The three touched test files: green (15 + 40 + 34).
- Full driver suite `template/tests`: 2021 tests OK, 2 skips, both pre-existing and
  unrelated (Jinja-unrendered prompts).
- `engine/scripts/run-suite.sh` (T3): root suite 24 OK, driver suite OK.
- `git diff --check`: clean.
- The target has no formatter or pre-commit hooks configured. Only DCO sign-off applies,
  and that happens at commit.
- `patch.diff` is 73,962 bytes, under the 80 KB backstop.

Housekeeping: I wrote one T3 log to `/tmp/claude-t3-539.log` by mistake. It is outside the
harness roots and nothing reads it. I left it in place rather than delete it.
