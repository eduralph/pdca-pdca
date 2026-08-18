# Adversarial pass — issue_533 (a leaf's own terminal error is kept and read)

Evidence re-run independently, not taken on trust: red leg (production reverted to
`acb214a`, new test file kept) → **23 of 28 fail**; green leg → **28/28 OK**, matching
`gate-logs/C4-verify.log:29,254-256`. The suite drives the real spawn path (a real
subprocess through `leaves._invoke_leaf_resilient` / `progress.run_with_heartbeat`), not a
re-implementation. I also re-derived the vendor grounding from the shipped binary
(`~/.local/share/claude/versions/2.1.233`) rather than from `fixtures/README.md`: the
main-session emitters really do hard-code `parent_tool_use_id:null` (both the `assistant`
and the `user` case), the `agent_progress` branch really does forward
`is_api_error_message` with `parent_tool_use_id:e.parentToolUseID`, and the kind enum is
exactly the ten the patch splits. Both pinned fixtures are byte-verifiable against the
only two `isApiErrorMessage` records in the local transcripts, and both are main-session
and terminal. That part of the round holds. Five findings landed anyway — the first two are
substantive misclassifications reachable from the vendor's own emitters; the rest are a
scope call for the human and two conformance gaps.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:619` + `:646`: a marked
  message with **no `error` key** is not "the vendor's unknown API error", and routing it
  to `_TRANSIENT_CAUSE_RE` promotes leaf-side failures to transient. `kind = str(ev.get("error")
  or "unknown")` collapses *absent* into *"unknown"*, and `_kind_is_transient` then falls
  through to prose for **any** kind outside the two frozensets. 2.1.233's queryLoop
  catch-all emits exactly that shape for *any* exception that escapes the loop —
  `let wn = tr instanceof Error ? tr.message : String(tr); … let ii = Yd({content:wn,now:m.now,uuid:m.uuid})`
  — and `Yd` sets `isApiErrorMessage:!0` unconditionally while leaving `error` undefined
  (so the stream line carries the mark and no kind). Verified through the production path
  on the patched tree: a main-session marked message whose text is `connect ECONNREFUSED
  127.0.0.1:8931` (a dead MCP server), `fetch failed`, `Command timed out after 120000ms`,
  `socket hang up` or `terminated` all return `produced=False` → `.transient` → **retried
  to the attempt budget**, and the §6 row then tells the operator "transient infra — safe
  to re-run" (`leaves.py:2608-2613`) for a config failure that fails identically every
  time — the very conflation PR #285's review is cited for at `leaves.py:2541-2543`. The
  same line is the drift hole: any kind the vendor adds after 2.1.233 (the CLI
  auto-updates; the harness pins nothing) is unlisted, so its prose decides. The patch's
  own docstring already states the correct rule — "The text is read **only** for the kind
  the CLI leaves ``unknown``" (`:638-639`) — and the code does not implement it. Nothing
  asserts the looser behaviour: replacing the fallthrough with `if kind != "unknown":
  return False` leaves all 28 tests green, so the over-broad branch is both unnecessary
  and untested.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:321`: the exclusion list
  stops one death short. `died_of_reported_infra = terminal["transient"] and rc not in (0,
  TIMEOUT_RC)` deliberately spares the run *the harness killed* on its wall-clock bound,
  but not the run the harness killed on its **memory** bound (#420) or one a signal took.
  Measured on the patched tree: a stub leaf that emits a work event, then the incident's
  own `server_error` report, then dies of `SIGKILL` returns `(-9, …, produced=False)` →
  `.transient` → three attempts, each of which will hit the same cap. `_memory_cap_prefix`
  (`leaves.py:309-322`) puts every capped leaf one OOM away from this, and the brief
  explicitly fences signal-death out as #510's ("neither #506's transient nor #421's
  preflight"), so this patch is silently reclassifying an excluded case from substantive
  to transient. One predicate (`rc > 0`, or the same `TIMEOUT_RC`-style exclusion for a
  negative/128+n status) closes it; the missing case is worth a test either way.

- **NEEDS-HUMAN** — `template/src/pdca_harness/leaves.py:693-704` and `:728-730` are inside
  `_invoke_leaf_resilient`'s **body**, which the brief reserves for sibling child-1
  ("`_invoke_leaf_resilient`'s body, `do_build`, and the artifact harvests are sibling
  child-1's … this child changes only `progress.py`, the four prose sites in `leaves.py`,
  one comment in `assemble.py`") and which the last sign-off flagged as an *unresolved*
  ownership question to settle "before either lands" (carry-forward item 3). The builder
  resolved it unilaterally: the docstring is rewritten and the retry line now prints "on
  transient infra". The prose is now true — but this is the one region the split exists to
  keep disjoint, and 532 is still movable, so the merge-order collision is a human call,
  not a builder's.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:617-621`: the mark is read
  in two spellings, the scope in one. `_terminal_error` deliberately accepts the persisted
  **transcript** spelling `isApiErrorMessage` alongside the stream's `is_api_error_message`
  ("keying on one of them would leave the incident unfixed"), but decides whose death it
  was from `parent_tool_use_id` only — a field the transcript shape does not have (it
  carries `isSidechain`; see the pinned `claude_api_error_death.transcript.jsonl`). Since
  `.get()` returns `None` for an absent key, a transcript-shaped **sidechain** record —
  `{"type":"assistant","isSidechain":true,"isApiErrorMessage":true,"error":"overloaded",…}`
  — is classified `_REPORT`, returns `produced=False`, is retried, and the retained
  diagnostic names a sub-agent's blip as the leaf's own death. Verified on the patched
  tree: `(1, 'API Error: 529 the API is at capacity\n', False)`. No 2.1.233 emitter puts
  that shape on stdout, so this is not reachable today — but that is an argument for
  deleting the transcript-spelling branch, not for keeping half of it: either the shape can
  appear (then honour `isSidechain` / treat a missing `parent_tool_use_id` as unknown
  scope) or it cannot (then the branch and its test assert a record no vendor emits). It is
  the same scope family this round was rebuilt to close.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/progress.py:425-427` (and
  `_note_terminal`'s docstring at `:663-666`): the claim that excluding `result` from
  `_WORK_EVENT_TYPES` is load-bearing ("Let it win and the death this fix exists for is
  retried zero times again, with the suite green") is unasserted. Mutation-tested: adding
  `"result"` to `_WORK_EVENT_TYPES` leaves all 28 tests **green**, because every wrap-up the
  suite emits carries `is_error` and therefore takes the `_note_terminal` branch, never the
  clearing `elif`. The exclusion only bites for a text-less `is_error` result
  (`{"type":"result","subtype":"success","is_error":true,"result":""}` → `_terminal_error`
  returns `("",False,"")` at `:626-627` → falls to the clearing branch), and no case covers
  it. One event appended to `test_report_survives_the_wrapups_that_name_no_cause` fixes the
  gap. (For contrast, eight other mutations I planted — dropping the sub-agent scope check,
  making `_note_terminal` newest-wins, unscoping `_is_main_session_work`, letting prose
  promote a permanent kind, classifying on `TIMEOUT_RC`, dropping the `[sub-agent report…]`
  label, appending under `capture`, reading the wrap-up's prose — were each caught by a
  named test. The suite is strong; this is its one blind spot.)

Attempted and could **not** refute: the red leg is not vacuous (23 real assertion failures,
no import/collection error, fixtures present on both legs); the two fixture-replaying cases
skip rather than error when `fixtures/` is absent; `capture=True` returns the child's stdout
byte-identical with the append suppressed (`:307`); the codex format degrades silently
(`:608-609`); a stream-less family still reports `produced=True` (`leaves.py:678`); the
`TIMEOUT_RC` path is not reclassified; `rc == 0` keeps `produced`'s documented meaning
(carry-forward item 2 closed); the retained report rides `LeafError.output` into
`build.error.log` via `_format_leaf_attempt` (`leaves.py:1785`), so criterion (iii) reaches
the builder's log without touching child-1's harvest; #420's post-mortem still appends after
it; and `tests.test_progress test_leaf_resilience test_build_error_log test_leaf_status
test_leaf_memory_log` (80 tests) are green on the patched tree.
