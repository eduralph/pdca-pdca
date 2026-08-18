# Adversarial pass — issue_533 (a leaf's own terminal error is kept and read)

Re-ran the asserted red→green independently on a copy of `$PDCA_TARGET`: **green 34/34**
with the patch, **red 30/34** with the three production files reverted (`git checkout --`
on `progress.py` / `leaves.py` / `assemble.py`, test + fixtures kept). The four that pass on
red are the (iv) "nothing else changes" invariants, by design. The suite drives the real
spawn path — a real `subprocess`, `progress.run_with_heartbeat` and
`leaves._invoke_leaf_resilient` — with no mock, no stub classifier and no re-implementation
of the production logic, so C4/C5 are honest. I also re-derived the load-bearing vendor
claims from the shipped `claude-code 2.1.233` binary rather than from `fixtures/README.md`:
the stream emitter's `is_api_error_message:!0` + top-level `error:r.error`, the main loop's
hard-coded `parent_tool_use_id:null` vs the `agent_progress` branch's `e.parentToolUseID`,
`new Set(["rate_limit","overloaded","server_error"])`, the `Yd({content:…,error:"unknown"})`
last resorts, and `api_error_status` only on the `variant:{subtype:"success"}` result — all
confirmed. Findings below are what survived that.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/leaves.py:102` and `:700-702` state a rule
  the code does not implement: a signal-killed leaf *is* still classified transient and
  retried when it died before its first substantive stream event.** `LeafError`'s new
  docstring says "A child a SIGNAL killed (the memory cap, an OOM, a Ctrl-C) is neither
  shape", and `_invoke_leaf_resilient`'s says "Any other failure of a leaf that ran —
  including one a **signal** killed, whatever its stream last said (#510) — … is
  substantive: do not retry." Measured through the production path
  (`_invoke_leaf_resilient`, claude family, stream on): a stub leaf that emits **no** stream
  event and dies of `SIGKILL` returns `LeafError(returncode=-9).transient is True` and is run
  **3 times**; the wrapper spelling (`rc=137`, no stream events) likewise. `is_signal_death`
  is consulted only in the new branch (`progress.py:358-359`), while `LeafError.transient`
  (`leaves.py:110-115`) is still `not produced`. That is exactly the `_memory_cap_prefix`
  (#420) shape the sentence names — a capped leaf OOM-killed before its first `assistant`
  event buys three more OOMs — and it is the half of last round's item 2 that was left open
  while the prose claims both halves. Minimal in-scope fix is to narrow the two sentences to
  the reported-infra branch; extending `is_signal_death` into `transient` itself changes
  #138's base behaviour and is the #510 boundary decision, so that variant is a human call.
  Suite gap: both signal cases (`tests/test_terminal_error_classification.py:599`, `:612`)
  emit a work event first, so neither reaches this shape.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/progress.py:465`: the `"user"` member of
  `_WORK_EVENT_TYPES` is load-bearing and unasserted — deleting it flips a real
  classification with all 34 tests still green.** Mutation-measured: with
  `_WORK_EVENT_TYPES = {"assistant"}` the suite is `OK`, yet the stream
  `[assistant work, marked server_error report, main-session user tool_result, exit 1]`
  goes from `produced=True` / 1 attempt to `produced=False` / 3 attempts — i.e. a leaf that
  recovered through a tool cycle and then failed on its own merits becomes retryable, the
  criterion-(ii) inversion. Every clearing case in the suite (`:369`, `:245`) clears with an
  `assistant` event; the vendor emits main-session tool results as `type:"user"`,
  `parent_tool_use_id:null` (confirmed in 2.1.233), which is the only reason the member is
  there. This is the exact twin of last round's item 4 (the `result` *exclusion*, now
  properly pinned by `:245`'s `success-with-no-text` case) — one case with a `user`
  tool_result after the report closes it.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/progress.py:687-688` and `:567`: the
  `result` branch's two discriminators are both unasserted.** Emptying
  `_TRANSIENT_STATUSES = frozenset({408, 409, 425, 429})`, or dropping the
  `ev.get("subtype") == "success"` guard, each leaves all 34 tests green. The only
  status-carrying case (`tests/test_terminal_error_classification.py:271`) uses 503, which is
  decided by the `500 <= status <= 599` range, and `wrapup_execution_error` (`:123`) never
  sets `api_error_status`, so the `error_during_execution` case at `:497` cannot exercise the
  subtype guard. The guard is vendor-*correct* (2.1.233 attaches `api_error_status` only to
  the `success` variant), so this is coverage, not behaviour: add `api_error_status: 503` to
  the execution-error event (must stay substantive) and one 429 wrap-up.

- NEEDS-HUMAN [impl] — **`template/src/pdca_harness/assemble.py:80` and
  `template/src/pdca_harness/leaves.py:2544` replace one half-true restatement with the other
  half, so the codebase still carries two statements of the definition.** Both were narrowed
  to "ran, died of infra it reported", dropping #138's original shape — a leaf that emitted
  nothing at all and exited non-zero — which still routes to the same `_FAIL_TRANSIENT` /
  `LEAF_STATUS_INFRA` pair (the suite's own case at
  `tests/test_terminal_error_classification.py:628` produces exactly that leaf). Their
  siblings at `leaves.py:2552-2554` and `:2611-2616` get it right ("produced no substantive
  output, **or** …"). Since "the definition is restated in N places and goes stale the moment
  it widens" is the invariant this slice exists to serve, a newly-wrong restatement is the
  same defect in the other direction. (`template/tests/test_leaf_status.py:84`'s "ran, no
  output → retryable blip" comment is stale for the same reason and is not fenced off by the
  brief.)

- NEEDS-HUMAN — **`template/src/pdca_harness/progress.py:237-240`: the clearing rule discards
  the retained *text* along with the verdict, so `(no output captured)` can still be the
  post-mortem for a leaf whose CLI did explain itself.** Measured on the resilient path:
  `[work, marked server_error report, main-session work]` + exit 1 with empty stderr writes
  `----- attempt 1 — exit 1 -----\n(no output captured) LeafError: …` — the artifact the
  brief calls "a post-mortem artifact that explains nothing" — even though the harness had
  the report text in hand. Criterion (iii) says the text is retained "for every marked
  terminal report, transient or not"; the patch's reading is that a recovered report is not
  *terminal*, which is defensible, so this is a fitness call rather than a bug. Cheap
  alternative if the human wants (iii) read literally: clear `transient`/`shape` but keep the
  text under a "recovered" label, which changes no classification.

## Attempted and could not refute

- **The evidence.** Red→green reproduced independently; no tautology, no over-broad
  assertion, no mocked-away defect; the C4 red leg fails on the *assertions* (30 of them),
  not on an import or a missing fixture: no symbol this patch adds is imported at module
  level, and the two fixture-replaying cases carry the `skipTest` guard the brief demanded
  (`tests/test_terminal_error_classification.py:281`, `:509`) — in this round's gate log the
  untracked fixtures survived the revert, so both went red on their retention assertions
  rather than skipping. Both gate traps avoided.
- **Prose-promotion.** Tried to promote a permanent cause through the text path: the
  permanent kinds, an unrecognised (post-2.1.233) kind, an *unstamped* marked report and the
  cloud-runner tail all stay substantive — last round's item 1 is genuinely closed, not
  re-worded. Likewise the transcript spelling (item 3: `isSidechain` honoured on both sides
  of the scope rule) and the main-session scoping.
- **Mutation battery (12).** Killed: `isSidechain` in `_is_subagent_event`, the shell
  `128+signum` spelling of `is_signal_death`, the `_note_terminal` precedence guard,
  `result`-as-work, the 5xx range, a subagent report classifying, and the retention append
  leaking under `capture`. Survivors are the three coverage items above plus two nits I do
  **not** file as findings: `_report_line`'s 500-char bound and `_MAX_SIGNUM`'s exact value
  are unasserted.
- **One precedence hole I could not ground.** A retained `_SUBAGENT_REPORT` is overwritten by
  a later `_WRAPUP` (`_TERMINAL_PRECEDENCE`, `progress.py:543`), which drops the
  `[sub-agent report, not the leaf's own death]` label and can classify transient off the
  wrap-up's status. I could not derive a 2.1.233 emission sequence that produces it (the
  vendor builds the `success` wrap-up out of the *main* transcript's last message), so I am
  not filing it — noted only so the next reader does not have to re-derive it.
- **Neighbour behaviour.** Checked every `run_with_heartbeat` caller: all but the leaf spawn
  pass `capture=True`, so the appended report cannot corrupt a gate's evidence line
  (`gates.py:559`, `publish.py:833`, `leaves.py:767`), and `_invoke` discards `output` on
  `rc == 0`.
