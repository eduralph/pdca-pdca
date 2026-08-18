# Build notes — issue #533 (a leaf's own terminal error is kept and read)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a` (worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`, `HEAD == origin/main == acb214a`).
All `path:line` below are **post-patch** lines on that base unless marked "(base)".

---

## 1. What the change is

Two rules, both inside the stream reader the driver already runs, plus the prose that
restates them downstream.

**Classification + retention (`progress.py`).**

| Site | What it does |
|---|---|
| `progress.py:176` | one more piece of drain state: `terminal = {"text", "transient", "shape"}` |
| `progress.py:188-193` | in the existing drain loop, beside `_is_session_event`: read a marked terminal record; a **main-session** work event after one clears it |
| `progress.py:295-301` | the report rides `output` into the caller's `*.error.log` by the same route the stderr tail takes (skipped under `capture`, where `output` is raw stdout) |
| `progress.py:303` | `produced` becomes `produced and not terminal["transient"]` — the whole classification change |
| `progress.py:408` | `_WORK_EVENT_TYPES` = the `assistant`/`user` subset (a `result` is the wrap-up, not "it recovered") |
| `progress.py:429-455` | section comment: what the incident was, why the mark and not the prose is the discriminator, which field lives on which event |
| `progress.py:457-520` | the constants — report/wrap-up shapes, the vendor's transient and permanent kinds, the retryable statuses, the category regex, the 500-char bound |
| `progress.py:523-573` | `_terminal_error` — the per-family classifier, in `_is_session_event`'s shape (dispatch on `stream_format`, best-effort JSON, degrade-to-today default) |
| `progress.py:576-588` | `_kind_is_transient` — **the vendor's kind answers first, both ways**; prose only for kind `unknown` |
| `progress.py:591-618` | `_note_terminal` — newest wins, except the wrap-up never overwrites the report that named the cause |
| `progress.py:620-657` | `_claude_message_texts` / `_claude_result_texts` / `_transient_status` / `_report_line` |
| `progress.py:660-681` | `_is_main_session_work` — only the MAIN session carrying on clears a report |
| `progress.py:58-90` | `run_with_heartbeat`'s docstring: the two halves of the signal, and why retention is wider than classification |

**Prose sites that restated the old definition** (prose only, nothing else touched):
`leaves.py:90-112` (`LeafError` + `.transient`), `leaves.py:672-677` (the `_invoke`
comment; the `produced or not use_stream` fallback at `:678` is untouched),
`leaves.py:2537` (`_FAIL_TRANSIENT`), `leaves.py:2542-2549` (`_failure_class`),
`leaves.py:2583-2608` (`_unavailable_classification`, incl. the operator-facing
"transient infra" paragraph), `assemble.py:80` (`LEAF_STATUS_INFRA`).

**Tests + fixtures.** `template/tests/test_terminal_error_classification.py` (415 lines,
23 cases) and `template/tests/fixtures/` (README + two observed vendor records + their
derived stream forms). Both ship **inside `patch.diff`** at the paths the brief names —
this instance's bundles carry no separate copy of the test (cf. `results/issue_507/`,
`issue_494/`, `issue_506/iteration-v4/`), and a stray copy in the bundle dir would not be
in `state.DOWNSTREAM_OF_BRIEF`, so it would leak across an iterate.
`template/tests/test_leaf_resilience.py` and `test_build_error_log.py` are untouched
(child-1 owns both).

Nothing in `_invoke_leaf_resilient`'s body, `do_build`, the harvests, or
`_format_leaf_attempt` — sibling child-1's regions; see §6.

---

## 2. Vendor grounding (the standard this slice is held to)

Everything below was re-derived **in this cycle** from the installed CLI
(`~/.local/share/claude/versions/2.1.233`, an ELF with the JS bundle embedded; byte
offsets are into that file) and from two real session transcripts. Nothing was taken on
the prior attempt's word.

| Claim | Status | Evidence |
|---|---|---|
| the CLI marks its synthesised API-error message | OBSERVED | transcript line 345 of `~/.claude/projects/-home-eddie-wyrd-wyrd-pdca/31fa2f21-…jsonl` (the #506 incident, 2.1.228): `"isApiErrorMessage":true`, `"error":"server_error"`, text `API Error: Connection lost mid-response.…`; line 346 is a `last-prompt` bookkeeping record, so the report **was** the stream's last word |
| a permanent marked report exists and looks identical apart from its kind | OBSERVED | `-home-eddie-pdca-pdca-pdca/152ac920-…jsonl` line 7 (2.1.222): `"error":"model_not_found"`, `"apiErrorStatus":404` |
| the stream renames the flag to `is_api_error_message` and attaches **no** status on an `assistant` event | DERIVED (binary) | emitter at offset 300266437 (and the two sibling emitters at 300270907 / 300271692): `{type:"assistant", message:n, session_id:qt(), parent_tool_use_id:null, …, error:r.error, …(r.isApiErrorMessage===!0&&{is_api_error_message:!0})}` |
| **sub-agent** messages carry `parent_tool_use_id: <Task id>`, main-session ones `null` | DERIVED (binary) | 300271692, the `case "progress"` / `agent_progress` branch: `parent_tool_use_id: e.parentToolUseID`, plus `subagent_type` / `task_description` |
| the `result` wrap-up shapes | DERIVED (binary) | 306393331: `subtype:"error_max_turns"|"error_during_execution"` carry `errors:[…]`; the `success` variant carries `is_error: Ze, api_error_status: gt, result: Ze?Dt:qe` where (same function, ~306392xxx) `Ze = zt.isApiErrorMessage===!0`, `gt = zt.apiErrorStatus ?? null`, `Dt` = that message's text. Schema at 312730953 declares `api_error_status` on the `success` variant only |
| the vendor's own transient predicate | DERIVED (binary) | 302953009: `isTransient: t.apiErrorIsTransient===!0 \|\| t.error==="overloaded" \|\| t.error==="server_error"`; and 300404460, subagent API-error termination: `new Set(["rate_limit","overloaded","server_error"])` — an independent confirmation of the same three |
| `apiErrorIsTransient` never reaches the stream | DERIVED (binary) | it is a field of the internal message (`CYf`/`Yd`, 302955407-302956539); no stream emitter forwards it — which is why the KINDS carry the decision |
| the full kind enum | DERIVED (binary) | 312710292 (SDK schema `ekc`) and 307342591 (the `StopFailure` hook matcher): `["authentication_failed","oauth_org_not_allowed","billing_error","rate_limit","overloaded","invalid_request","model_not_found","server_error","unknown","max_output_tokens"]` |
| a connection abort with no recognised code lands as kind `unknown` | DERIVED (binary) | 298315595: the mapper's tail — connection-code sets `gde`/`sie` (296572269/296572435, quoted in the fixtures README) → `server_error`; residual `Error` → `Yd({content:`${Uw}: ${e.message}`, error:"unknown"})` with `Uw="API Error"` (298324120). Neither set holds any `UND_ERR_*`, so undici's mid-body abort arrives as `API Error: terminated` |

Both fixtures are pinned verbatim; the derived `.stream.jsonl` twins carry the exact
regeneration recipe. `template/tests/fixtures/README.md` labels every claim OBSERVED or
DERIVED and quotes the emitters, so a reviewer can re-check without the binary.

The brief called the CLI a **reading** input, not a build/verification input — that is how
it was used. Every test leg runs a Python interpreter as the stub leaf: no vendor CLI, no
API key, no network. `External dependencies: none` held; **no NEEDS-HUMAN dependency**.

---

## 3. The two defects the prior attempt (issue_506/iteration-v4) still had

Both were rebuilt-proof-tested, not just "avoided".

**(A) The clearing rule was scope-blind.** Prior art cleared a stored report on *any*
`assistant`/`user` event. One trailing sub-agent line — chatter from a Task still draining
when the session died — therefore restored the pre-fix outcome exactly. Fixed at
`progress.py:660-681`: the clearing event must carry `parent_tool_use_id is None`, i.e. be
the **main** session carrying on. Grounded on the emitter split above.

**(B) Stickiness swallowed a second marked report.** Prior art's rule was "a transient
report is not overwritten by anything non-transient", so a permanent 400 arriving *after* a
dropped connection was dropped on the floor — wrong text in the log, and three retries of a
death that would repeat. Fixed at `progress.py:591-618`: stickiness is scoped **by shape**.
A second `_REPORT` wins outright (it is the leaf's newer account of its own death); only the
`_WRAPUP` — which structurally cannot name a cause — is refused.

Counterfactual proof (monkeypatch only, nothing written; run from `template/` with
`PYTHONPATH=src:tests`): re-introducing prior art's `_is_work_event` makes
`test_a_trailing_subagent_line_does_not_clear_the_report` fail (1 failure, 0 errors);
re-introducing its `_note_terminal` makes `test_a_second_marked_report_wins_outright` fail
(1 failure, 0 errors); with the shipped implementations both pass. So each guard case
binds its defect, not just the overall feature.

---

## 4. Design decisions, and what was ruled out

**The vendor's kind decides first, in both directions** (`progress.py:576-588`). Prior art
computed `transient = kind in TRANSIENT or any(regex.search(text))`, so a report the CLI
marked `invalid_request` whose text quoted a 529 would be *promoted* to transient — exactly
what success criterion (ii) forbids. Now: transient kinds → transient; the six permanent
kinds → never; only `unknown` reaches the category regex.

**Why keep the regex at all** (ruled out: kinds-only). Cost of dropping it: a genuine
mid-body connection abort — the class the incident is in — arrives with kind `unknown` and
text `API Error: terminated` (evidence in §2), so a kinds-only classifier reports it
substantive and criterion (i)'s "a lost or interrupted connection" is not met. That is one
whole cause category unfixed, not a nicety. The regex is 25 lines of alternatives, each
either a code from the CLI's own connection-code sets, a status it maps, or a phrase from
its own message templates — and it can now only ever *decide an undecided* case, never
override the vendor.

**Retention wider than classification.** Every marked record's text reaches `output`
(`:295-301`), including permanent ones and the `error_*` wrap-ups; only the transient flag
changes `produced`. Ruled out: retaining only what we retry — that would leave a 400 death
reading `(no output captured)`, which is the half of the invariant about evidence.

**Appended to `output`, not a new return value or a new `LeafError` field.** Ruled out
(concrete cost): a fourth tuple element changes `run_with_heartbeat`'s signature and the 5
call sites (`leaves.py:657`, `:752`, `gates.py:559`, `publish.py:833`, plus every test that
unpacks 3), and `_format_leaf_attempt` (`leaves.py:724-730`, child-1's file region) would
need a special case. Riding `output` costs 6 lines and touches nothing downstream — which
is why the brief's composition cue points there.

**`shape` in the drain dict rather than a class.** Three keys in a dict the drain thread
already owns; a dataclass would add ~12 lines and an import for no reader outside this
module.

**Session-resume was NOT attempted (accepted first cut).** When a long session dies of a
dropped connection, a fresh re-invoke throws away the work it had done; the CLI can resume a
session (`--resume <session_id>`, and the id is right there in the events we now parse). The
brief scopes resume out, so this ships the fresh re-invoke. Flagging it for the human: for
an 18-minute builder, retry-by-re-invoke is correct but expensive, and resume is the obvious
follow-up issue.

**Sub-agent *reports* are still read (only *clearing* is scope-restricted).** A sub-agent's
marked API-error message can be the stream's last word if the whole session dies with it, so
refusing to read it would re-open the hole. In the normal case the main session gets the tool
result — a main-session `user` event — and clears it. Recorded here because it is the one
asymmetry in the scope rule.

---

## 5. Red → green (the project's own runners; no hand-rolled invocation)

* **C4 gate** — `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` (the
  configured gating check):
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  Green leg: `Ran 23 tests … OK`. Red leg (production hunks reverted, tests kept):
  `Ran 23 tests … FAILED (failures=20)` — 23 executed, **no** `unittest.loader._FailedTest`,
  so a real red, not `PDCA-UNVERIFIABLE`. The 3 that stay green on the red leg are the
  "nothing else changes" parity cases, which is what they are for.
* **T3 suite** — `./engine/scripts/run-suite.sh`:
  `PDCA-EVIDENCE: root suite OK, driver suite OK` (`Ran 1781 tests … OK (skipped=2)`),
  i.e. the copier render check ran with the new fixtures present and `test_leaf_resilience`,
  `test_build_error_log`, `test_leaf_memory_log`, `test_progress`, `test_leaf_status` are
  all still green.
* Criterion (iv)'s **#420 clause** is evidenced by the *existing* suite, deliberately: the
  memory post-mortem is composed in `_invoke` (`leaves.py:671`) on top of whatever
  `run_with_heartbeat` returned, and `test_leaf_memory_log.py:229-240` already asserts
  "stderr tail + memory telemetry, both in `LeafError.output`" — it is green unchanged.
  Duplicating it here would have to mock `run_with_heartbeat` and so would test nothing
  this patch changes; instead `test_report_and_stderr_tail_both_survive` proves the report
  joins `output` by the same route, before that append happens.
* Gate-trap compliance: every criterion has at least one case built **inline** in the test
  module; the two fixture-replaying cases `skipTest` when `fixtures/` is absent; the module
  imports only `leaves`, `progress`, `LeafConfig` — no symbol this patch adds — so the red
  leg imports cleanly.

**Commit-readiness.** No formatter/linter/pre-commit is configured in the target
(`core.hooksPath` unset, no `.pre-commit-config.yaml`, no ruff/black config; CI is
`render-check` + docs). Checked by hand instead: no trailing whitespace in any touched
file, longest added line 94 chars against a file max of 97 (`progress.py`) / 110
(`leaves.py`), and no Jinja delimiters (`{{`, `{%`, `{#`) anywhere in the new
`template/…` files — the render check copies them verbatim into a rendered instance.
DCO sign-off is the publisher's `git commit -s`.

---

## 6. Forced self-refutation

**(a) Genuine red?** Yes. Not asserted — measured by the C4 red leg, which reverts the
production hunks in place and re-runs: 20 of 23 cases fail, 23 execute, module imports
fine. Every criterion has at least one failing case there: (i)
`test_work_then_connection_lost_is_transient_and_retried` (`err.transient` False pre-fix,
1 run instead of 3), (ii) `test_a_trailing_subagent_line_does_not_clear_the_report`,
(iii) `test_error_log_explains_the_death_without_the_transcript` (the log reads
`(no output captured)` pre-fix — verbatim the incident's artifact). Additionally, the two
*regression* guards were shown to bind by re-introducing each prior defect individually
(§3) — a stricter red than the gate's, because it fails a nearly-correct implementation.

**(b) Production path?** Yes. No mocks, no stand-ins, no re-implementation. Each case
spawns a **real child process** (`sys.executable -c …`, the same shape
`test_leaf_resilience.py:38-40` uses) through the **production** entry points:
`progress.run_with_heartbeat` (`progress.py:35`) and `leaves._invoke_leaf_resilient`
(`leaves.py:681`), which runs the real `_invoke` → real spawn → real drain thread → real
`LeafError` → real `error_log.write_text`. The assertions are over an invocation counter
the child itself writes and the bytes of the error log the production code wrote.

**(c) Fixture includes the fault?** Yes. The failing element is present, never curated
out: the marked report is *in* the replayed stream (not asserted around); the stub really
exits non-zero; the incident's own vendor record is replayed **verbatim** from
`fixtures/claude_api_error_death.stream.jsonl` in
`test_pinned_incident_stream_record_is_transient`, and its permanent counterpart in
`test_pinned_permanent_stream_record_is_not_retried`. The sub-agent case really includes
the trailing sub-agent line, and the second-report case really includes both reports — the
two shapes that defeated the previous attempt.

---

## 7. For the human at sign-off

* **Left deliberately untouched (sibling boundary):** `_invoke_leaf_resilient`'s retry
  notice still prints "leaf exited N **with no output** (transient)" (`leaves.py:723-726`,
  base `:716-718`). It is inside the wrapper body the brief assigns to child-1, and it is
  the one remaining sentence that restates the old definition. If child-1 does not reword
  it, it is a one-line follow-up — no behaviour depends on it.
* **Merge order** (from the brief): child-1 first, then this one.
* **Manual validation, if wanted:** with `claude` on PATH, run any headless leaf against a
  deliberately broken endpoint (`ANTHROPIC_BASE_URL=http://127.0.0.1:9 pdca run <id>`) and
  read the resulting `*.error.log` — it should now carry the CLI's `API Error: …` line
  instead of `(no output captured)`. This is *not* needed for the criteria (all four are
  proven offline above); it is only an end-to-end smell test with the real vendor.
