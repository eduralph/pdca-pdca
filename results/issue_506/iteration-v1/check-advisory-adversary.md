# Adversarial review — issue 506 (advisory; never gates)

Grounded on `$PDCA_TARGET` (`fb28c6f` + the patch). I reproduced the red→green myself
(reverted `leaves.py`/`progress.py`, kept the test hunks: **4 failures** on the base —
`test_a_terminal_transient_error_after_real_work_is_retried`,
`test_the_error_log_carries_the_leafs_own_terminal_error`,
`test_a_transient_builder_death_is_retried_bounded_with_backoff`,
`test_the_exhausted_message_names_the_class_and_the_resume` — for the same reasons
`gate-logs/C4-verify.log` records; green with the patch), ran the whole suite (1765 tests,
28.6 s, OK — identical runtime to the base, so the new builder retries add no wall clock),
and mutation-tested the four load-bearing production hunks. What survived that:

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/progress.py:420` (`_ERROR_LEAD_RE`, with
  its `^\W*` prefix) misclassifies a *substantive* builder failure as transient whenever the
  leaf's final message merely opens with an error-shaped clause that names an infra cause.**
  Driven through the real path (`_invoke_leaf_resilient` → `_invoke` → `progress` →
  subprocess) with the suite's own stub leaf, each of these substantive deaths came back
  `transient=True` and **re-ran the builder 3×**:
  `"Error: assertion failed - expected 500, got 404 in test_api.py"`,
  `"Error: the repro still fails - curl returns 503 from the stub server; needs a human."`,
  `"Connection refused while starting the fixture server; I could not finish the repro."`.
  `^\W*` also eats markdown, so a builder that *quotes* the incident line at the head of a
  message or bullet — `"- \`API Error: Connection lost mid-response.\` is the incident's
  verbatim line"`, `"> API Error: Connection lost mid-response.\n\nThat is what the stream
  carries."` — is read as the leaf dying of it. The blast radius is exactly the one the
  brief calls most expensive: three opus/max builder runs plus an operator told "nothing
  substantive failed. Safe to re-run." The precision guard the patch ships
  (`template/tests/test_leaf_resilience.py:75`, `:185`) only covers the **mid-sentence**
  mention (`"I reproduced the … defect and fixed it"`), so it passes without testing the
  case its own docstring claims — "a builder fixing this very defect says the string out
  loud" — which is precisely the *leading*-quote case. Tighten the lead (e.g. require the
  cause adjacent to the lead, or anchor on the CLI's literal `API Error:` prefix) and add a
  leading-quote case to that guard.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:1812-1817`: the new
  exhausted-retry message's "how to resume" is false in the incident's own scenario.** It
  says "re-driving Do on `issue_506` (`run` / `flow`) resumes the cycle". Measured: a stub
  builder that writes `patch.diff` and *then* emits the terminal API error leaves the bundle
  at `state.state(d) == BUILT` (`state.py:211` — "Do is done when there's a patch"), and
  `driver.py:76` runs **Check**, not Do, on the dead attempt's partial patch. The repo
  already states this ("a partial build lands there and never re-enters PLANNED",
  `driver.py:49-50`; `tests/test_build_error_log.py:96-101`). Criterion (iv) asks the
  operator message to name the resume, and this one points at a command that will not re-run
  Do. Minimum fix is message-local (name that a partial `patch.diff` must be cleared first);
  do **not** silently delete the builder's artifacts to make the sentence true — see the next
  item.

- **NEEDS-HUMAN — retrying the builder in place re-invokes it on the dead attempt's residue,
  and nothing in the patch or the prompt tells attempt 2 that.** `worktree.ensure` runs once,
  before the wrapper (`leaves.py:1833`), so attempts 2 and 3 start in a worktree already
  carrying attempt 1's edits and a bundle already holding its `patch.diff` / `build-notes.md`
  (`leaves.py:1875-1883`); `_build_prompt` (`leaves.py:1888`) says only "Produce, in the
  bundle directory …". For the reviewer/advisory leaves a retry is idempotent — they rewrite
  one file — but the builder mutates a tree, and the incident's leaf is exactly the one that
  had run 18 minutes before dying. The failure mode to weigh: attempt 2 reads a
  complete-looking `patch.diff` + `build-notes.md`, concludes the work is done, exits 0, and a
  half-finished patch is reported as a **successful** Do. The brief pre-accepted "a fresh
  re-invoke" only for *session* resume; whether a fresh re-invoke on a dirty lane is
  acceptable — or needs a reset / a carry-forward note in the prompt — is a scope call.

- **NEEDS-HUMAN — the classifier's contract with the *real* vendor stream is asserted, never
  observed (verdict provisional; no CLI, no network in this sandbox).** Every new test
  synthesises the event shape it then parses (`tests/test_leaf_resilience.py:63-73`), so it
  cannot distinguish "reads claude's terminal error" from "reads the stub's". If the CLI in
  fact emits that death as a `system` event, as a `result` with only `subtype:
  "error_during_execution"` and no string `result`/`error` key, or on **stderr**,
  `_terminal_error_text` (`progress.py:442`) and `_claude_event_texts` (`progress.py:466`)
  return `""`, the leaf stays substantive, and the whole suite is still green while the
  incident is unfixed. One real transcript from `~/.claude/projects/` (the brief cites it)
  pinned as a fixture would close this; a human should confirm the wire shape before this is
  taken as the incident's fix.

- `template/src/pdca_harness/progress.py:279-285` bends the documented `capture` contract:
  the docstring at `:113-114` says the stream parse is "mutually exclusive with `capture`
  (capture wins if both set)", but the terminal-error line is now appended to `output` on the
  `capture=True` branch too. No caller sets both today (`gates.py:559`, `publish.py:833`,
  `leaves.py:774` are all `capture=True, stream_json=False`), so this is latent — but the
  first caller that captures raw stream JSONL gets a trailing non-JSON line in its evidence.

- `template/src/pdca_harness/leaves.py:108-110` and `:2583` still describe the old rule
  ("A no-output non-zero exit", "ran, exited non-zero with no output; retries exhausted")
  after the patch widened it and rewrote the neighbouring prose at `:94-100` and `:2647`. In
  a codebase where the comment is the contract, that is a conformance nit worth one line each.

## Attempted and could not refute

- **Tautology / wrong-reason pass:** no. Four targeted mutations were each caught — dropping
  the exhausted-retry print (`leaves.py:1806`) → `test_the_exhausted_message…` fails;
  dropping the `_has_content` guard (`leaves.py:1800`) → the 3-record assertion fails;
  dropping `and not terminal["error"]` (`progress.py:287`) → 3 failures; dropping the
  recovery-clearing branch (`progress.py:178-179`) → the recovered-session test fails.
- **Vacuous markers:** no. `_API_ERROR` / `_LEAF_STDERR` reach the child through the env
  (`tests/test_leaf_resilience.py:50`), so `_format_leaf_attempt`'s argv echo cannot satisfy
  the assertions — the base-leg failure output confirms the echo carries the *script*, not
  the marker.
- **Parallel re-implementation:** no. `DoRetriesATransientBuilderDeath`
  (`tests/test_leaf_resilience.py:209`) drives the real `do_build` → `_do_build_command` →
  `_invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat` → `subprocess` chain.
  Note the C5 row's "pass" is *vacuous* here — its evidence line is "patch adds no new test
  file — nothing to assert" (`gate-logs/C5-prod-path.log`), so it supports nothing; the
  production-path claim rests on the manual check above, not on that green.
- **Collateral regressions:** none found. Full suite green, same runtime as base; the
  `_has_content` guard cannot resurrect a stale log (`do_build` still unlinks at
  `leaves.py:1774` before setup); a setup failure before the leaf still lands its own record
  (`tests/test_build_error_log.py:133`); stream-less families keep `produced=True`
  (`leaves.py:674`); codex/gemini degrade to today's classification (`progress.py:449`).
