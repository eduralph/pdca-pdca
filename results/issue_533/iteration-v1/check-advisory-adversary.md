# Adversarial pass — issue_533 (a leaf's own terminal error is kept and read)

Re-ran the asserted red→green at `$PDCA_TARGET` (23 tests green with the patch; the frozen
`gate-logs/C4-verify.log` red leg fails 20 of them, including the two headline assertions —
`err.transient` and `"Connection lost mid-response" in error_log` — so the red is real, not a
missing-file artifact: the fixture-replaying cases *failed on their assertions* rather than
skipping). The suite drives the production symbols (`progress.run_with_heartbeat`,
`leaves._invoke_leaf_resilient`), not a copy — I re-drove the same two entry points from my own
scratch probes and reproduced every asserted behaviour. Vendor grounding re-derived
independently from `~/.local/share/claude/versions/2.1.233`. One refutation landed.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:560-562`: the `_REPORT` branch
  matches a marked api-error message **without checking `parent_tool_use_id`**, while
  `_is_main_session_work` (`progress.py:660-681`) is deliberately main-session-scoped. So a
  **sub-agent's** report is credited as the leaf's own account of its death, and because
  `_note_terminal` (`:615`) only protects a `_REPORT` from a *wrap-up*, a later sub-agent report
  overwrites the main session's. Concrete failing case, run against the patched target:
  `assistant(work)` → main-session report `{"is_api_error_message":true,"error":"invalid_request"}`
  → trailing sub-agent report `{"parent_tool_use_id":"toolu_…","subagent_type":"general-purpose",
  "is_api_error_message":true,"error":"overloaded"}` → `result/error_during_execution`, exit 1 ⇒
  `produced=False` (leaf retried to the attempt budget) and the retained diagnostic is
  `"API Error: 529 the API is at capacity"`. That is brief criterion (ii) inverted — a cause the
  vendor marked **permanent** is promoted, and the `*.error.log` names the wrong death — and it is
  the same family as the defect the brief said must not be rebuilt (a second marked report
  swallowing the first). The input is vendor-emittable, not hypothetical: 2.1.233's
  `agent_progress` branch yields `{type:"assistant", …, parent_tool_use_id: e.parentToolUseID,
  error: i.error, ...(i.isApiErrorMessage===!0 && {is_api_error_message:!0}), …}` — and
  `template/tests/fixtures/README.md:115-117` quotes exactly that branch with `error:` and the
  flag **elided behind "…"**, which is why the shape reads like harmless chatter. The gap was
  contemplated and left unasserted: the test helper's `parent=` parameter
  (`template/tests/test_terminal_error_classification.py:71-77`) is passed by **no** test, while
  `test_a_trailing_subagent_line_does_not_clear_the_report` (`:294`) establishes that trailing
  sub-agent lines are exactly the interleaving to expect. Fix is one predicate (scope the
  `_REPORT` branch, or make `_note_terminal` prefer a main-session report) plus the missing case.

- **NEEDS-HUMAN** — `template/src/pdca_harness/leaves.py:693` and `:724-726` are a **fifth**
  restatement of the definition this patch widens, and the patch leaves both false: the operator
  now sees `leaves: <bundle> — leaf exited 1 with no output (transient); retry 1/2 in 0s` for a
  leaf that produced 18 minutes of work and a report — printed verbatim in this round's own green
  leg (`gate-logs/C4-verify.log`, lines 12-13). The brief lists only four prose sites and scopes
  `_invoke_leaf_resilient`'s body to sibling child-1, so this needs a human scope call: either
  child-1 owns these two lines (confirm it does) or the codebase ships the contradiction the
  invariant exists to prevent. Not marked `[impl]` because touching them crosses the split.

- `template/src/pdca_harness/progress.py:303` bends the documented contract of the third return
  value on the **success** path: a leaf whose stream carried a transient marked report and then
  exited **0** now returns `produced=False`, and `:295-301` appends the report to `output` (was
  `""`). I checked every call site — `leaves.py:663-678` (guarded by `rc != 0`), `leaves.py:760`,
  `gates.py:559`, `publish.py:833` (all `capture=True` and/or discard the flag) — so nothing today
  misreads it; but the docstring at `:60-62` still defines `produced` as "did the child emit a
  substantive stream event", which is now false for a *successful* run, and #510's signal-death
  work is the next reader of that flag.

- Attempted and **could not** refute: (a) that the red is vacuous — it is not, the inline cases
  carry it; (b) that the regex could promote a permanent cause — `_kind_is_transient`
  (`progress.py:576-585`) answers from the vendor kind first in both directions, and I confirmed
  `_CLAUDE_PERMANENT_ERROR_KINDS` is exactly 2.1.233's enum minus its own transient set minus
  `unknown`, so only `unknown` reaches `_TRANSIENT_CAUSE_RE` (the false positives I could build —
  `"cannot read /var/log/429/config.json"` — are not shapes the CLI's `"API Error: "+e.message`
  mapper emits); (c) that the clearing rule wipes the death via a trailing main-session
  `user` tool_result — plausible on paper (`_WORK_EVENT_TYPES` at `:408` includes `user`, and
  `_is_main_session_work` does not exclude the CLI's `isSynthetic` echoes, so such a line would
  drop **both** the classification and the retained text), but I found no evidence for it: every
  `isApiErrorMessage` record in the local `~/.claude/projects` corpus (2 of them) was its
  session's last event, so this stays a residual risk, not a refutation; (d) that `capture`
  changed — the raw stdout is byte-identical (`:295`); (e) that the vendor citations were
  asserted rather than observed — the assistant emitter (no `api_error_status` on `assistant`),
  the three `result` variants with `api_error_status` only on `success`, and the transient
  predicate `apiErrorIsTransient===!0 || error==="overloaded" || error==="server_error"` all
  re-derived from the binary and all as the fixture README describes them.
