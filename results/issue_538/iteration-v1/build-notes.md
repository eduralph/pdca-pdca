# Build notes — #538 "a leaf's own account of its death is kept"

Target: `eduralph/pdca-harness` @ `main`, base `acb214a` (worktree
`$PDCA_WORKTREE = /home/eddie/pdca/pdca-harness.pdca-wt-l1`). Every `path:line` below is
against that worktree with the patch applied.

## What the patch does

One production file, `template/src/pdca_harness/progress.py`, additive, no control-flow or
classification change:

| where | what |
| --- | --- |
| `progress.py:182` | `terminal = {"text": "", "shape": ""}` — the drain's retained record, beside `produced` (`:177`) and `latest_tool` (`:183`) |
| `progress.py:194-196` | in the existing stdout drain, next to the `_is_session_event` / `_stream_tool_label` calls it already makes: read the CLI's own marked report and keep it |
| `progress.py:297-305` | append the kept text to `output` **after** the stderr tail, skipped under `capture` |
| `progress.py:309` | `produced` returned exactly as before — the change retains, it does not classify |
| `progress.py:431-620` | the reader itself: `_terminal_error` (`:496`), `_note_terminal` (`:550`), `_is_subagent_event` (`:576`), `_claude_message_texts` (`:591`), `_claude_result_texts` (`:600`), `_report_line` (`:615`), plus the record constants (`:478-493`) |

Placement is the brief's composition cue: the reader sits beside `_is_session_event`
(`progress.py:417`) in the same shape — dispatch on `stream_format`, best-effort JSON
parse, default `("", "")` — so codex and every stream-less family degrade to today's
behaviour instead of guessing at a vendor's error text.

The retained text reaches the artifact by the route the brief names and nothing else
changes: `run_with_heartbeat` returns it inside `output`, `leaves._invoke`
(`leaves.py:657-670`, untouched) puts that `output` on the `LeafError`,
`_invoke_leaf_resilient` (`leaves.py:720`) writes it, and `_format_leaf_attempt`
(`leaves.py:724-730`) needs no special case — its `tail` is simply no longer empty, so it
stops emitting `(no output captured)`. `leaves.py` and `assemble.py` are untouched, as
Scope requires (they are #536's / #537's).

New non-production files: `template/tests/test_terminal_error_retention.py` (the brief's
test path, **new** file so C5 keys on it) and `template/tests/fixtures/` (4 pinned vendor
records + `README.md`, the provenance note).

## Vendor grounding — observed vs derived

Re-derived from the **installed** binary, claude-code **2.1.234**
(`readlink -f "$(command -v claude)"` → `~/.local/share/claude/versions/2.1.234`), not
from the round-3 archive; and from real transcripts under `~/.claude/projects/`. The full
statement, with the greps to re-run, ships next to the fixtures in
`template/tests/fixtures/README.md`.

**Observed** (bytes a real CLI wrote, pinned verbatim, one line each):

* `claude_api_error_death.transcript.jsonl` — `"error":"server_error"`,
  `"isApiErrorMessage":true`, text `API Error: Connection lost mid-response. …`
  (2.1.228, `-home-eddie-wyrd-wyrd-pdca`, 2026-08-12). This is the incident's own record.
* `claude_api_error_permanent.transcript.jsonl` — `"error":"model_not_found"`,
  `"apiErrorStatus":404` (2.1.222, `-home-eddie-pdca-pdca-pdca`, 2026-08-06).
* A corpus sweep of every `*.jsonl` under `~/.claude/projects/` found exactly **two**
  records with `isApiErrorMessage is True` — both above — and **2080** records with
  `"isSidechain": true` (sub-agent transcripts, e.g. `…/<session>/subagents/agent-*.jsonl`),
  which is how I know the transcript's sub-agent spelling and that such records carry no
  `parent_tool_use_id` key at all. No marked API-error record with `isSidechain:true`
  exists in that corpus, so that *combination* is derived, not observed — stated as such
  in the fixture README rather than dressed up as observation.

**Derived** (quoted emitters from the 2.1.234 binary; the `.stream.jsonl` fixtures are the
observed records mapped through the first of these):

* main-loop stream emitter — `…session_id:qt(),parent_tool_use_id:null,uuid:r.uuid,
  timestamp:r.timestamp,error:r.error,…r.isApiErrorMessage===!0&&{is_api_error_message:!0}…`
* transcript direction — `…t.is_api_error_message===!0&&{isApiErrorMessage:!0}…`, plus the
  schema's own `"@internal True when this assistant message wraps an API error (from
  internal AssistantMessage.isApiErrorMessage)."`
* sub-agent forwarding — `if(e.data.type==="agent_progress"…){…yield{type:"assistant",…,
  parent_tool_use_id:e.parentToolUseID,…,…i.isApiErrorMessage===!0&&{is_api_error_message:!0}…}`
* `result` wrap-up — `variant:{subtype:"success",api_error_status:mt,result:rt?Ut:We,…}`
  with `common:{…,is_error:rt,…}`, or `variant:{subtype:"error_during_execution",errors:Ur}`

Nothing in the patch reads an error **kind**, an HTTP **status**, or the prose for a cause
— those are #539's, and this slice deliberately carries none of round 3's classification
hunks (`_CLAUDE_TRANSIENT_ERROR_KINDS`, `_TRANSIENT_CAUSE_RE`, `_TRANSIENT_STATUSES`,
`is_signal_death`, `_kind_is_transient`, the `produced` demotion): that is ~120 lines of
round 3's `progress.py` hunks left out on purpose, which is what makes this the retention
half rather than the oversized slice the split exists to undo.

## Success criterion, item by item

| criterion | where it is met | where it is proven |
| --- | --- | --- |
| (i) marked report in `*.error.log` via `output` | `progress.py:194-196`, `:297-305` | `test_…retention.py:187`, `:194`, `:199` |
| (ii) retention unconditional (recovered, permanent) | no clearing rule; no cause is read (`progress.py:496-548`) | `:219`, `:228`, `:235` |
| (iii) sub-agent report kept **labelled**, both spellings | `_SUBAGENT_NOTE` (`:486`), `_is_subagent_event` (`:576`) | `:248`, `:254`, `:261` |
| (iv) nearest record wins, either arrival order | `_TERMINAL_PRECEDENCE` (`:482`), `_note_terminal` (`:550`) | `:277`, `:282`, `:285`, `:290`, `:293`, `:300` |
| (v) nothing classified — `produced`, `transient`, retry counts identical | `progress.py:307-309`; `_is_session_event` untouched | `:309`, `:315`, `:320`, `:327` (counts asserted explicitly: 3, 1, 1) |
| (vi) nothing else changes | append skipped under `capture` (`:297`); `fmt != "claude-stream-json"` → `("", "")` (`:525-526`) | `:339`, `:346`, `:352`, `:359`, `:369`, `:376` |

On (vi)'s call-site claim, re-verified on this base: `run_with_heartbeat` has exactly four
callers — `gates.py:559`, `publish.py:833`, `leaves.py:752` all pass `capture=True` (so the
append is skipped and a gate's evidence line is byte-identical), and `leaves.py:657` is the
only one that does not. `test_…retention.py:339` asserts `output == the child's raw stdout`
exactly under `capture`, which is a non-vacuous equality: the report text *is* in those
bytes, so the assertion fails the moment anything is appended.

On (vi)'s #420 clause: `leaves.py:661-670` is untouched, so `telemetry.post_mortem(rc)`
still appends to the same `output`; the only change is that the string it appends to may
now end with the leaf's report. `test_…retention.py:199` pins the ordering the telemetry
append depends on (existing content first, report after). I did **not** drive a live
memory-capped leaf: that needs a `systemd-run` scope, which this offline stdlib suite has
no business requiring. A human can validate it directly with
`[driver].leaf_memory_max` set and a leaf that both OOMs and reports — the two appends land
in the same `*.error.log`, in call order.

## What I ruled out, with the cost

* **Keep the raw stream instead of the marked report** (a `deque(maxlen=200)` of JSONL
  lines, twinning `err_tail` at `progress.py:176`). *Cheaper in diff*: ~6 executable lines
  against my ~12. Rejected on the artifact, not the size: a stream line can be a whole
  `assistant` event (tool inputs, file contents), so a 200-line window is hundreds of KB in
  a `build.error.log` a human opens to find one sentence — and the window is not even
  guaranteed to contain the report, because the `result` wrap-up and any still-draining
  sub-agent chatter arrive *after* it. That is evidence dumping; the invariant asks for the
  account to be kept, legibly, in the artifact the cycle preserves.
* **Newest-wins, no precedence** (drop `_note_terminal` and the three shape constants: 4
  fewer executable lines, ~30 fewer comment lines). Rejected because the observed death
  *is* the case it breaks: the `result` wrap-up arrives after the report and names only the
  effect, so newest-wins re-drops the cause with the suite green — and a trailing sub-agent
  report would make the log confidently name the wrong death. Criteria (iii) and (iv) exist
  for exactly this, and `test_…retention.py:277-304` fails without it.
* **A "the CLI recovered" clearing rule** (round 3 carried one: `_is_main_session_work` +
  `_WORK_EVENT_TYPES` + a drain branch, ~20 lines). Out of scope for this child *and*
  contrary to criterion (ii): it makes retention conditional, which is the one thing a
  harness holding the text must never be. `test_…retention.py:219` asserts the opposite
  behaviour, so this is a deliberate divergence from the archived round-3 patch.
* **Classification** (promote `transient` from a reported cause). Explicitly #539's; every
  guard in `NothingIsClassified` (`:306-334`) exists so that this build cannot have done it
  by accident, and so #539's own red is honest.
* **Doing any of this in `leaves.py`** (e.g. teaching `_format_leaf_attempt` about the
  report). Not a cost trade at all: the stream is read and dropped inside the drain thread
  in `progress.py`, so `leaves.py` never sees the text — and Scope forbids touching the
  file, which #536/#537 are building in this same run.

## Refuting my own test (forced)

* **(a) Genuine red?** Yes. Reverting only the production hunks — exactly as the C4 gate
  does, `git apply -R --exclude='tests/*' --exclude='template/tests/*' patch.diff` — takes
  the module from `Ran 29 … OK` to `Ran 29 … FAILED (failures=19)`. The failure text is
  verbatim the incident's:
  `----- attempt 1 — exit 1 -----` / `(no output captured) LeafError: …`. The remaining 10
  cases are the (v)/(vi) guards, green on both legs **by design** (they assert that retry
  counts, `produced`, `capture` output, codex/stream-less behaviour and the exit-0 path did
  **not** move).
* **(b) Production path?** Yes. Every case drives the shipped functions —
  `leaves._invoke_leaf_resilient` → `leaves._invoke` → `progress.run_with_heartbeat` — and
  asserts on the real `*.error.log` those functions write, or on the tuple
  `run_with_heartbeat` itself returns. Nothing is mocked, re-implemented or monkeypatched;
  the only test-owned code is the *stub leaf* (a `python3 -c` child standing in for the
  vendor CLI, the shape `tests/test_leaf_resilience.py:26-40` already ships) and the
  fd-redirect helper that keeps the stream-less case's inherited stdout out of the suite's
  own stdout (#402).
* **(c) Fixture includes the fault?** Yes. The stub actually emits the marked record on
  stdout and exits non-zero — the failing element is in the stream, not curated out. The
  sub-agent cases *contain* the sub-agent record (that is the point), the precedence cases
  contain both competing records in both orders, and three cases replay the **observed
  vendor bytes**, including the very record from the 18-minute death this fix exists for.
  Those three `skipTest` (never error) if `tests/fixtures/` is absent, per the brief's gate
  trap — measured on this git: `git apply -R --exclude='template/tests/*'` in fact keeps the
  fixtures, so they ran red on the red leg too; the guard covers the other case.

## Verification run

Project runner only (`docs/INTEGRATION.md` §3, `CONTRIBUTING.md`):

* `cd template && PYTHONPATH=src python3 -m unittest tests.test_terminal_error_retention` —
  `Ran 29 tests … OK` with the fix; `FAILED (failures=19)` with the production hunks
  reverted.
* Full offline driver suite: `PYTHONPATH=src python3 -m unittest discover -s tests` —
  `Ran 1787 tests … OK (skipped=2)`.
* Root template suites (render + `copier update` compat, instance venv):
  `python3 -m unittest discover -s tests` — `Ran 7 tests … OK`. This renders the template
  and runs the shipped suite inside the render, so the new `tests/fixtures/` directory is
  exercised through copier too (nothing in `copier.yml:18-54` `_exclude` matches it).
* The gate itself, end to end: `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`
  → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
* Advisory C5: `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` →
  `1 added driver-suite test(s) import the production package 'pdca_harness'`.

Commit-readiness: the target repo configures no pre-commit hooks and no formatter
(`core.hooksPath` unset, no `.pre-commit-config.yaml`, no ruff/flake8 config); its CI is
docs-check + render-check, both covered above. I kept every new line ≤ 92 columns (the
file's existing envelope; one pre-existing 97-column line at `progress.py:667` is
untouched) and left no trailing whitespace.

No external dependency was missing: the brief's `External dependencies: none` held — the
whole build and both legs ran offline on stdlib Python + git, with the vendor binary used
only as a *reading* source for grounding, exactly as the brief scoped it.

Bundle convention note: the test is shipped **inside `patch.diff`** at the path the brief
names, not duplicated as a loose file in the bundle — matching the accepted bundles in
`results/issue_507/` and `results/issue_533/iteration-v3/`.
