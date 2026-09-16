# Adversarial review — issue 506 (iteration 4)

Ground: `$PDCA_TARGET` (patched working tree, base `bc16d55`). Evidence re-run independently:
red leg (production files restored from `HEAD`, all test hunks kept) → **30 failures / 39 tests**;
green leg → **39 OK**; full template suite → 1780 tests, only `test_settings_permissions` red and
only because my scratch copy re-roots `REPO_SETTINGS` (`tests/test_settings_permissions.py:40`) —
unrelated to the patch. So C4's red→green is real, and it is real *through the production path*
(each case spawns a python "leaf" whose bytes go through `progress.run_with_heartbeat`).

## Findings

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:188-191` (with `:405`, `:625-636`):
  the "the CLI recovered, so that report was not the end" rule is **scope-blind**, and one trailing
  **sub-agent** line restores the pre-fix outcome exactly. Measured through
  `_invoke_leaf_resilient` → `_invoke` → `progress` → a real subprocess, replaying the pinned
  incident fixture and then a single
  `{"type":"assistant","parent_tool_use_id":"toolu_01SUB", …"subagent: still summarising"}`:
  `transient=False`, **1** invocation, error log back to
  `(no output captured) LeafError: Command '[…]'` — the incident's verbatim artifact, i.e. criteria
  (i) *and* (iii) both fail with the suite green. A trailing sub-agent `user` tool_result gives the
  same result. This is not an invented event shape: claude-code 2.1.233 emits sub-agent messages on
  *this* stream through the same emitter, as `type:"assistant"`/`"user"` with `parent_tool_use_id`
  set (`case "progress"` → `UXe`, binary offsets ~300270907/300271692, `yield {type:"assistant", …,
  parent_tool_use_id: e.parentToolUseID, …i.isApiErrorMessage===!0&&{is_api_error_message:!0}}`),
  while `_is_work_event` dispatches on `ev["type"]` alone. An orphaned sub-agent still streaming is
  not the main session carrying on. Cheap containment: require the clearing event to be main-session
  (`parent_tool_use_id` null/absent) and pin it with the existing stub harness. **What I could not
  establish:** an ordering where a sub-agent line lands *after* the main session's terminal report
  and the process then exits non-zero — the natural candidate is two parallel `Task` sub-agents, one
  of which dies of the API error. The gap is concrete and cheap to close; its field frequency is not.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:580`: stickiness is stated over the
  `result` wrap-up (docstring `:563-577`) but implemented over *any* later report, so a **second
  marked api-error report** is swallowed. Measured: work → `api_error(server_error, "…Connection
  lost mid-response…")` → `api_error(invalid_request, "API Error: 400 duplicate tool_use ID in
  conversation history.")` → exit 1 yields `transient=True`, **3** builder invocations, and a
  `build.error.log` that keeps only the first line — the permanent 400 that will fail identically on
  every retry is neither retained nor read. Two marked reports with no work event between them is
  what two parallel sub-agents (or a sub-agent plus the main session) produce; the CLI's own loop
  does not stop after emitting one (`case "assistant": if(_t.isApiErrorMessage) yield*tt("stream_error")`
  continues the message loop, 2.1.233). Keeping the sign-off's endorsed rule while closing this is a
  one-line narrowing: stick only against a `result` event, let a later *marked report* overwrite.

- `template/src/pdca_harness/leaves.py:1861` + `:1870`: `residue` is computed over
  `("patch.diff", "build-notes.md")` but only printed on the `patch.diff` branch. Measured with
  `_transient_do_death` on a bundle holding a half-written `build-notes.md` and no patch: the
  operator is told "no patch.diff was left behind … its inputs are intact — `pdca run 506` …
  re-drives Do from the top", and the residue is never named. Accurate about *state* (the bundle does
  read PLANNED, and `worktree.ensure` resets the tree on the next run), so this is an honesty nit in
  a message whose whole point is honesty, not a functional break.

- `template/src/pdca_harness/progress.py:603`: `_claude_result_texts` reads a top-level `error` key
  "as a fallback for a shape neither of those covers" — but the CLI's `result` schema attaches
  `errors: string[]` to the `error_*` variants and `result` to the `success` one (verified in the
  binary at ~306393322, the same quote the fixture README uses), so that key is unreachable, and
  mutation-testing confirms it is unpinned (deleting it leaves 39 tests green). That is the identical
  "a branch that looks like coverage and is not" the previous sign-off had removed for
  `UND_ERR_[A-Z_]+`. Two smaller mutants also survive: dropping `ev.get("subtype") == "success"`
  at `:555` (defensible — the excluded shape cannot exist) and dropping the `stream disconnected`
  alternative at `:495`.

- Verdict caveat (not a refutation): `check-gates.json` C5 records `pass` with
  `"patch adds no new test file — nothing to assert"`. That row supports **no** production-path
  claim — as prior sign-offs already noted. I checked the substance separately and it holds: every
  new case drives a real subprocess and asserts on an invocation counter and the error log's bytes,
  and each marker reaches the child through the env or a fixture file, so the argv echo in
  `_format_leaf_attempt` cannot satisfy an assertion (`tests/test_leaf_resilience.py:64-66`).

## Attempted and could not refute

- **The vendor contract**, which is where rounds 2-3 found the rot. I re-derived the fixture README's
  claims from the shipped binary myself: the stream's assistant emitter writes `error` and
  `is_api_error_message` and **no** `api_error_status` (~300266437); `Yd` always normalises the
  api-error content to one text block, `isApiErrorMessage:!0` (~302956461), so `_claude_message_texts`
  cannot miss it; the `result` emitter is byte-for-byte what the README quotes (~306393322); `sie`/`gde`
  hold no `UND_ERR_*` code (~296572269), so the mapper's `error:"unknown"` + `API Error: terminated`
  fallback is real — and this round's cause set now matches it.
- **The "too broad" arm** iterations 1-2 were rejected for. The regex only ever runs on text the CLI
  itself marked, and I walked the mapper's permanent branches (`invalid_request` 400 duplicate
  tool_use / tool-use concurrency, `authentication_failed`, `model_not_found`, `billing_error`,
  request_too_large): none of their texts match `_TRANSIENT_CAUSE_RE`. The two precision legs
  (leading "Error: … 500 …", a leaf quoting the incident line verbatim) hold.
- **Tautology / mutation cover**: 13 mutants of the load-bearing hunks; 9 caught, including
  `\bterminated\b`, `other side closed`, the 5xx range in `_transient_status`, the
  `isApiErrorMessage` spelling, the per-attempt flush (`leaves.py:741`), `do_build`'s `_has_content`
  guard, `_transient_do_death`, the retention of a `result` ending's text, and the
  attempt-1-prompt-unchanged rule. The 4th survivor is cosmetic (`leaves.py:749` names the leaf by
  `label`, unpinned).
- **The builder's newly inherited legacy arm**: a builder that dies before any stream event (a bad
  `effort_argv`, a memory-scope kill at startup) is now retried 3× and told "nothing substantive
  failed" (`leaves.py:1859`). That is #138's pre-existing rule reaching a new caller, `#510` is
  explicitly out of scope in the brief, and the cost is bounded (3 spawns, 12s) — noted, not filed.
