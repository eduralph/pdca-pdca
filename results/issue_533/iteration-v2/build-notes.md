# Build notes — issue #533, iteration 2 (a leaf's own terminal error is kept and read)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a` (worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`, `HEAD == origin/main == acb214a`).
All `path:line` below are **post-patch** lines on that base unless marked "(base)".

Iteration 1 was rejected on **one landed refutation**, not on the design ("the approach is
sound and the evidence is strong … Rejected on one landed refutation"). So this round keeps
the design and closes the three carry-forward items. §2 is the new material; §1 is the whole
change for a reader who has not seen v1.

---

## 1. What the change is

Two rules inside the stream reader the driver already runs, plus the prose that restates
them downstream.

| Site | What it does |
|---|---|
| `progress.py:188` | one more piece of drain state: `terminal = {"text", "transient", "shape"}` |
| `progress.py:197-206` | in the existing drain loop, beside `_is_session_event`: read a marked terminal record; a **main-session** work event after one clears it |
| `progress.py:307-313` | the report rides `output` into the caller's `*.error.log` by the same route the stderr tail takes (skipped under `capture`, where `output` is raw stdout) |
| `progress.py:315-322` | `produced` becomes `produced and not died_of_reported_infra` — the classification change, scoped to a **non-zero exit the child itself made** |
| `progress.py:425-427` | `_WORK_EVENT_TYPES` = the `assistant`/`user` subset (a `result` is the wrap-up, not "it recovered") |
| `progress.py:448-484` | section comment: what the incident was, why the *mark* and not the prose is the discriminator, which field lives on which event, and **whose** death a mark denotes |
| `progress.py:485-562` | the constants — the three record shapes, their precedence, the sub-agent label, the vendor's transient and permanent kinds, the retryable statuses, the category regex, the 500-char bound |
| `progress.py:565-631` | `_terminal_error` — the per-family classifier, in `_is_session_event`'s shape (dispatch on `stream_format`, best-effort JSON, degrade-to-today default); `:621-622` is the main-session scoping |
| `progress.py:634-646` | `_kind_is_transient` — **the vendor's kind answers first, both ways**; prose only for kind `unknown` |
| `progress.py:649-681` | `_note_terminal` — newest wins *within a shape*, never across a shape nearer to the leaf's own death |
| `progress.py:684-721` | `_claude_message_texts` / `_claude_result_texts` / `_transient_status` / `_report_line` |
| `progress.py:724-747` | `_is_main_session_work` — only the MAIN session carrying on clears a report |
| `progress.py:52-101` | `run_with_heartbeat`'s docstring: the two halves of the signal, what `produced` still means, and why retention is wider than classification |

**Prose sites that restated the old definition** (prose only, nothing else touched):
`leaves.py:91-106` (`LeafError`) and `:110-112` (`.transient`), `leaves.py:672-677` (the
`_invoke` comment; the `produced or not use_stream` fallback at `:678` is untouched),
`leaves.py:693-704` (`_invoke_leaf_resilient`'s docstring) and `leaves.py:728-729` (the
retry notice) — the two the sign-off found (see §2.3), `leaves.py:2541` (`_FAIL_TRANSIENT`),
`leaves.py:2549-2555` (`_failure_class`), `leaves.py:2598` + `:2608-2613`
(`_unavailable_classification`), `assemble.py:80` (`LEAF_STATUS_INFRA`).

**Tests + fixtures.** `template/tests/test_terminal_error_classification.py` (28 cases) and
`template/tests/fixtures/` (README + two observed vendor records + their derived stream
forms). Both ship **inside `patch.diff`** at the paths the brief names — the C4 gate runs the
test out of `$PDCA_WORKTREE`, and a second copy in the bundle dir is not in
`state.DOWNSTREAM_OF_BRIEF` (`template/src/pdca_harness/state.py:82-105`), so it would not be
archived on an iterate and would leak into the next round.
`template/tests/test_leaf_resilience.py` and `test_build_error_log.py` are untouched
(child-1 owns both). Nothing in `_invoke_leaf_resilient`'s **logic**, `do_build`, the
harvests, or `_format_leaf_attempt`.

---

## 2. The three carry-forward items

### 2.1 (BLOCKER) The terminal-report reader is now scoped to the main session

**What was wrong.** v1's `_REPORT` branch matched any marked api-error message, and
`_note_terminal` was newest-wins except against a *wrap-up*. So a trailing **sub-agent**
report overwrote the main session's, and a main-session `invalid_request` followed by a
sub-agent `overloaded` was retried to the attempt budget with the log naming the wrong death.

**What ships.** Three shapes instead of two, ordered by how near each is to the leaf's own
death (`progress.py:485-500`):

| shape | rank | classifies? | retained? |
|---|---|---|---|
| `_REPORT` — marked message, `parent_tool_use_id is None` | 3 | yes, by the vendor's kind | yes |
| `_WRAPUP` — `result` with `is_error` | 2 | only via `api_error_status` on the `success` variant | yes |
| `_SUBAGENT_REPORT` — marked message with a Task's `parent_tool_use_id` | 1 | **never** | yes, prefixed `[sub-agent report, not the leaf's own death] ` |

`_note_terminal` (`progress.py:679-681`) keeps the highest rank seen, newest-wins within a
rank. That is one predicate and it closes both variants the sign-off named:

* the conjunction — main `invalid_request` then sub-agent `overloaded`: the sub-agent record
  cannot displace rank 3, so the classification stays permanent **and** the log names the
  400 (`test_a_trailing_subagent_report_does_not_overwrite_the_main_sessions`);
* the commoner one — a sub-agent blip in a leaf that then fails on its own merits: a
  `_SUBAGENT_REPORT` is never transient, so the leaf stays substantive
  (`test_a_subagent_report_alone_is_not_the_leafs_death`).

Scoping cuts one way only, which is its own case
(`test_the_main_sessions_own_report_still_decides_after_a_subagent_one`): a sub-agent report
must not *stop* the main session's from being read either.

**Why "retain, labelled" and not "ignore".** Ignoring sub-agent reports is one line cheaper —
the branch would be `and ev.get("parent_tool_use_id") is None` folded into the existing
condition instead of `progress.py:621-622` plus the `_SUBAGENT_REPORT` / `_SUBAGENT_NOTE` /
rank-table constants: **5 added code lines** (3 constants, 2 branch lines) and ~14 lines of
comment. What those 5 lines buy: when a session's only marked record is a sub-agent's, the
`*.error.log` still carries the one account that exists instead of reverting to
`(no output captured)` — the half of the invariant that says "no evidence must never be filed
as a verdict". The label is what keeps that honest: the sign-off's own standard is that a log
which confidently names the wrong death is worse than none, so the retained text says whose
report it is.

**Why a sub-agent report may never classify** — the vendor's own behaviour, re-derived from
the shipped binary this round (§3): an agent that dies of an API error raises
`AgentApiErrorTerminationError`, and for its own transient kinds
(`new Set(["rate_limit","overloaded","server_error"])`) the CLI **recovers the agent's partial
output back into the main loop** ("Everything below is PARTIAL output recovered from the agent
before it was cut off"). The session carries on. "A Task hit a 529" is therefore not evidence
about how the *leaf* died — while the main session's own report is exactly that.

### 2.2 `produced`'s documented contract is restored, not bent

v1 returned `produced["session"] and not terminal["transient"]` on every path, so a leaf that
reported a blip, recovered and **exited 0** returned `produced=False` — false against the
docstring, and #510's signal-death work is the next reader of that flag.

Ships (`progress.py:315-322`): `died_of_reported_infra = terminal["transient"] and rc not in
(0, TIMEOUT_RC)`. The override now applies only to the outcome it describes — a non-zero exit
**the child itself made**:

* `rc == 0` → `produced` means what it says (`test_a_recovered_run_that_exits_zero_still_reports_produced`);
* `rc == TIMEOUT_RC` → the harness killed the child on its wall-clock bound; `progress.py:27-32`
  is explicit that this is "the oracle did not answer", never a verdict the child expressed.
  Re-labelling it off the stream's last line would buy three more runs of a leaf that *hung*,
  each paying the whole bound (`test_a_timed_out_run_is_not_reclassified_by_its_stream`).

The docstring is restated to match (`progress.py:59-66`, `:84-91`) rather than left to be
read charitably.

### 2.3 The fifth and sixth restatements — I fixed them; the scope call is flagged

The sign-off left this **unadjudicated** ("settle which child owns these two lines before
either lands"). I fixed them, because shipping a known-false operator string is exactly the
contradiction the invariant exists to prevent, and both are **prose**:

* `leaves.py:693-705` — the `_invoke_leaf_resilient` docstring's "produced **no output**"
  definition;
* `leaves.py:728-729` — the retry notice, base `:716-718`. Was
  `leaf exited 1 with no output (transient)`; now `leaf exited 1 on transient infra`. It is
  printed verbatim in this round's own green leg (see the C4 log), which is where the previous
  round's contradiction was visible.

**For the human at sign-off:** these two lines sit inside `_invoke_leaf_resilient`, whose
*body* the brief assigns to sibling child-1 (issue 532). The change is a docstring and one
f-string — no logic, no control flow — so a merge with 532 conflicts only if 532 rewrites
those same lines; with the recommended order (child-1 first, then this one) a conflict is a
one-line prose choice. If you would rather 532 own them, dropping these two hunks costs
nothing else in this patch. I did **not** touch `_format_leaf_attempt` (`leaves.py:736-742`):
the brief scopes it to child-1 and it needs no change — the report reaches it through
`output`, which is why no special case is required there.

---

## 3. Vendor grounding (the standard this slice is held to)

v1's grounding table was re-derived from the installed CLI and two real transcripts; the
adversary independently re-derived it. This round I re-verified the claims **this** change
rests on, from `~/.local/share/claude/versions/2.1.233` (byte offsets into that file):

| Claim | Status | Evidence |
|---|---|---|
| the main loop's `assistant` emitter hard-codes `parent_tool_use_id: null` and appends the mark | DERIVED (binary) | offset 300270618: `yield{type:"assistant",message:o.message,parent_tool_use_id:null,session_id:qt(),…,error:o.error,…,...e.isApiErrorMessage===!0&&{is_api_error_message:!0},…}` |
| **the mark is forwarded for a SUBAGENT too**, with the Task id | DERIVED (binary) | offset 300271354, the `case "progress"` / `agent_progress` branch: `yield{type:"assistant",message:…,parent_tool_use_id:e.parentToolUseID,…,error:i.error,…,...n!==void 0&&{subagent_type:n},…,...i.isApiErrorMessage===!0&&{is_api_error_message:!0},…}` — so `is_api_error_message` alone does **not** say whose death it was; `parent_tool_use_id` does |
| a subagent's API-error death is **recovered by the CLI**, not the session's end | DERIVED (binary) | 300404401 `class …{…this.name="AgentApiErrorTerminationError"}`; 300404438 `new Set(["rate_limit","overloaded","server_error"])`; 300394642 `vJv(e,t)`: for those kinds it returns `{history, cutoffNote: … "Everything below is PARTIAL output recovered from the agent before it was cut off. The agent did NOT finish its task…"}` back to the main loop |
| no **observed** sub-agent api-error record exists to pin | OBSERVED (absence) | every `"isApiErrorMessage":true` record across `~/.claude/projects/**.jsonl` on this machine is `isSidechain: false` — the two already pinned. So the sub-agent framing stays DERIVED and the suite builds those events inline; `fixtures/README.md` says so rather than shipping an invented fixture with a fixture's authority |
| the `result` wrap-up shapes (unchanged from v1) | DERIVED (binary) | 306383539 region: `subtype:"error_max_turns"|"error_during_execution"` carry `errors:[…]`; the `success` variant carries `is_error: Ze, api_error_status: gt, result: Ze?Dt:qe` |

`template/tests/fixtures/README.md:113-152` now quotes all three emitters plus the recovery
function, labels every claim OBSERVED or DERIVED, and records why no sub-agent fixture is
pinned. The CLI was used as a **reading** input only, exactly as the brief scopes it: every
test leg runs a Python interpreter as the stub leaf — no vendor CLI, no API key, no network,
no container. `External dependencies: none` held; **no NEEDS-HUMAN dependency**.

---

## 4. Design decisions, and what was ruled out (this round)

**Rejected: scope the report branch to `parent_tool_use_id is None` and drop sub-agent
reports entirely.** Cost measured above (§2.1): saves 5 code lines; loses the only diagnostic
that exists when a session's last marked record is a sub-agent's, i.e. re-opens
`(no output captured)` for that posture. Criterion (iii) is about evidence, so the 5 lines are
the cheaper side of the trade.

**Rejected: let a sub-agent report classify when no main-session report exists.** It reads
"one of my Tasks hit a 529" as "I died of a 529". The vendor's own recovery path (§3) says
otherwise, and the failure mode is the sign-off's commoner variant: every leaf that fails on
its own merits after a sub-agent blip becomes retryable — three of the most expensive runs in
the cycle bought by an event that was handled.

**Rejected: `_note_terminal` "prefers a main-session report" as a special case** (the
sign-off's alternative b). Two-way special cases are what v1's wrap-up rule already was, and
adding a second one leaves the third pair (`_WRAPUP` vs `_SUBAGENT_REPORT`) undefined. A rank
table states the whole order in one line and is the same code size (`progress.py:498`,
`:679-681`).

**Rejected: restore `produced` on `rc == 0` only, leaving the timeout path folded in.** One
character cheaper (`rc != 0` vs `rc not in (0, TIMEOUT_RC)`) and wrong for the same reason
`TIMEOUT_RC` exists at all (`progress.py:27-32`).

**Kept from v1** (unchanged, and re-listed so a reviewer need not diff two bundles): the
vendor's kind decides first in both directions (`progress.py:636-646`); the category regex
only ever decides kind `unknown`, because a mid-body abort arrives as `API Error: terminated`
with no kind; retention is wider than classification; the report rides `output` rather than a
fourth tuple element — that would change `run_with_heartbeat`'s signature and its 5 call sites
(`leaves.py:663`, `:764`, `gates.py:559`, `publish.py:833`, plus every test that unpacks 3)
and force a special case in `_format_leaf_attempt`, which is child-1's file region.

**Session-resume was NOT attempted (accepted first cut, as the brief asks me to say).** When a
long session dies of a dropped connection, a fresh re-invoke throws away the work it had done;
the CLI can resume a session (`--resume <session_id>`, and the id is in the events we now
parse). The brief scopes resume out, so this ships the fresh re-invoke. For an 18-minute
builder that is correct but expensive — resume is the obvious follow-up issue.

---

## 5. Red → green (the project's own runners; no hand-rolled invocation)

* **C4 gate** — `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` (the configured
  gating check): `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  Green leg `Ran 28 tests … OK`; red leg (production hunks reverted, tests kept)
  `Ran 28 tests … FAILED (failures=23)` — 28 executed, **no** `unittest.loader._FailedTest`, so
  a real red, not `PDCA-UNVERIFIABLE`. 18 distinct cases fail there, including all three new
  sub-agent cases; the 10 that stay green are the "nothing else changes" parity cases, which is
  what they are for.
* **T3 suite** — `./engine/scripts/run-suite.sh`: `PDCA-EVIDENCE: root suite OK, driver suite
  OK` (`Ran 1786 tests … OK (skipped=2)`), so the copier render check ran with the new fixtures
  present and `test_leaf_resilience`, `test_build_error_log`, `test_leaf_memory_log`,
  `test_progress`, `test_leaf_status` are all still green.
* **T2 docs** — `./engine/scripts/run-docs-check.sh`: `docs lint clean, site render + link audit
  clean`. **C5** — `run-prod-path.py`: the added suite imports the production package.
* Criterion (iv)'s **#420 clause** is evidenced by the *existing* suite, deliberately: the
  memory post-mortem is composed in `_invoke` (`leaves.py:671`) on top of whatever
  `run_with_heartbeat` returned, and `test_leaf_memory_log.py:229-240` already asserts "stderr
  tail + memory telemetry, both in `LeafError.output`" — green unchanged. Duplicating it here
  would have to mock `run_with_heartbeat` and so would test nothing this patch changes;
  `test_report_and_stderr_tail_both_survive` proves the report joins `output` by the same route,
  before that append happens.
* Gate-trap compliance: every criterion has at least one case built **inline** in the test
  module; the two fixture-replaying cases `skipTest` when `fixtures/` is absent; the module
  imports only `leaves`, `progress`, `LeafConfig` and `progress.TIMEOUT_RC` — nothing this
  patch adds — so the red leg imports cleanly.

**Commit-readiness.** No formatter/linter/pre-commit is configured in the target
(`core.hooksPath` unset, no `.pre-commit-config.yaml`, no ruff/black/flake8 config; CI is
`docs-check` / `docs` / `render-check` / `require-linked-issue`). Checked by hand instead: no
trailing whitespace and no tabs in any touched file, every file ends in a newline, longest
added line 95 chars against a file max of 97 (`progress.py`) / 110 (`leaves.py`), all four
Python files byte-compile, and no Jinja delimiters (`{{`, `{%`, `{#`) anywhere in the new
`template/…` files — the render check copies them verbatim into a rendered instance. DCO
sign-off is the publisher's `git commit -s`.

---

## 6. Forced self-refutation

**(a) Genuine red?** Yes — measured twice, and the second is stricter than the gate.

1. *Against the base.* The C4 red leg reverts the production hunks in place and re-runs: 23
   failures over 28 executed cases, module imports fine. Every criterion has failing cases
   there: (i) `test_work_then_connection_lost_is_transient_and_retried`, (ii)
   `test_a_trailing_subagent_report_does_not_overwrite_the_main_sessions`, (iii)
   `test_error_log_explains_the_death_without_the_transcript` (the log reads
   `(no output captured)` pre-fix — verbatim the incident's artifact).
2. *Against the rejected v1 implementation* (the refutation this round exists to close).
   Monkeypatch-only counterfactual, nothing written: re-introducing v1's `_terminal_error`
   (no `parent_tool_use_id` check) and v1's `_note_terminal` (wrap-up-only stickiness) makes
   `test_a_trailing_subagent_report_does_not_overwrite_the_main_sessions` and
   `test_a_subagent_report_alone_is_not_the_leafs_death` **fail** (2 failures, 0 errors), with
   `AssertionError: True is not false` on `err.transient` — i.e. exactly the promotion the
   sign-off described. With the shipped code both pass.
3. The other guards were re-checked the same way, because `_note_terminal` was rewritten:
   `_note_terminal` reduced to pure newest-wins fails `test_report_survives_the_wrapups_that_
   name_no_cause` (both sub-tests); clearing widened to any work event (v0's scope-blind rule)
   fails `test_a_trailing_subagent_line_does_not_clear_the_report`; shipped, all five pass.
4. The two `produced`-contract cases were checked by temporarily restoring v1's line in
   `progress.py` (edit → run → revert; the worktree was then diffed byte-for-byte against
   `patch.diff` to prove the revert): both fail with `AssertionError: False is not true`.

**(b) Production path?** Yes. No mocks, no stand-ins, no re-implementation. Each case spawns a
**real child process** (`sys.executable -c …`, the shape `test_leaf_resilience.py:38-40` uses)
through the **production** entry points: `progress.run_with_heartbeat` (`progress.py:35`) and
`leaves._invoke_leaf_resilient` (`leaves.py:681`), which runs the real `_invoke` → real spawn →
real drain thread → real `LeafError` → real `error_log.write_text`. The assertions are over an
invocation counter the child itself writes and the bytes of the error log the production code
wrote. The counterfactuals in (a) monkeypatch a production symbol *in place* — they still run
production `run_with_heartbeat`.

**(c) Fixture includes the fault?** Yes; nothing is curated out. The marked report is *in* the
replayed stream; the stub really exits non-zero; the incident's own vendor record is replayed
**verbatim** from `fixtures/claude_api_error_death.stream.jsonl`, and its permanent counterpart
likewise. The new cases really include the failing element they are about: the trailing
sub-agent report is present in the stream (not asserted around), the sub-agent-only case
contains no main-session report at all, and the timeout case really lets the harness kill a
child that is still alive (`STUB_SLEEP=30`, `timeout=1`, `rc == TIMEOUT_RC` asserted).

---

## 7. For the human at sign-off

* **The one scope call I made for you to confirm:** §2.3 — I reworded
  `_invoke_leaf_resilient`'s docstring and its retry notice, which live inside the function
  body the brief assigns to child-1 (532). Prose only; drop the two hunks if you would rather
  532 own them.
* **§6 fitness-to-purpose** turns, per the sign-off, on the main-session scoping: it is now
  `progress.py:621-622` (read) plus `:679-681` (precedence), asserted by three cases, and the
  boundary is stated by the vendor's own recovery path rather than by our preference (§2.1, §3).
* **The expensive case** the sign-off noted — replaying a long-running builder — is still not
  reachable from this patch alone (the builder is not on the resilient path here); it becomes
  live when 532 lands. Merge order from the brief stands: **child-1 first**, then this one.
* **Manual validation, if wanted:** with `claude` on PATH, run any headless leaf against a
  deliberately broken endpoint (`ANTHROPIC_BASE_URL=http://127.0.0.1:9 pdca run <id>`) and read
  the resulting `*.error.log` — it should carry the CLI's `API Error: …` line instead of
  `(no output captured)`. Not needed for the criteria (all four are proven offline above); an
  end-to-end smell test only.
