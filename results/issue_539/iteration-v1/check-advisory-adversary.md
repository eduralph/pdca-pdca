# Adversarial review — issue #539 (what a transient leaf death is)

Lens: refute the red→green proof and find inputs that break the fix. Grounded on the patched
target at `$PDCA_TARGET`. Probes and mutants were run from this sandbox against a copy of the
source. The installed `claude` CLI (2.1.284) was greppable, so the vendor claims below were
checked against the binary, not taken on trust.

## The evidence holds

- C4's red is real, not vacuous. `gate-logs/C4-verify.log` shows the red leg failing on
  assertions: 21 of 40 in the new file, 2 in `test_leaf_status.py`, 3 in the retention file.
  None of them are import errors. The two replayed fixtures (`claude_api_error_death.stream.jsonl`,
  `…permanent…`) are child-1's and already on the base, so they are present on the red leg:
  `test_the_observed_incident_record_after_work_is_retried` goes red with "expected transient;
  rc=1", not with a skip. Every case drives `leaves._invoke_leaf_resilient` → `_invoke` →
  `progress.run_with_heartbeat` with a real subprocess stub, and the `sh -c` wrapper case
  really produces rc 137. I re-ran the four affected test files on the patched tree: 94 OK.
- The three guards the brief named as round-3 survivors are now pinned. With a mutant for
  each: dropping `"user"` from `_WORK_EVENT_TYPES` fails 2 tests, emptying
  `_TRANSIENT_STATUSES` fails 1, and dropping the `subtype == "success"` guard fails 1. So do
  mutants for the `_note_terminal` gate, both sub-agent checks, the `api_error` check on
  `unknown`, the `rc not in (0, TIMEOUT_RC)` guard, and each signal spelling.
- The drain logic survives the CLI's own recovery. In `-p` mode the binary's `Nd(...)` resumes
  a main session after a `truncatedAfterOutput` report ("Connection lost mid-response").
  Main-session work that follows clears the verdict (`progress.py:266-267`), and a later
  report sets it again. I found no event order that clears or keeps the verdict wrongly.

## Refutations

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/progress.py:836`: every `rate_limit` report
  is treated as transient without looking at the typed `api_error` the vendor puts on it. The
  code reads `api_error` only for `unknown` (`:838`). But claude-code 2.1.284 stamps two
  entitlement stops as `error:"rate_limit"` with a typed cause:
  `apiError:"long_context_credits_required"` ("Usage credits required for 1M context") and
  `apiError:"model_requires_usage_credits"`. The wire converter `_o` puts `api_error` on the
  stream event, so the harness can see it. Probe through `_invoke_leaf_resilient`, with work
  followed by `{"error":"rate_limit","api_error":"long_context_credits_required",…}` and
  exit 1: the leaf runs **3 times** and is classed `transient`. The long-context case is the
  expensive one. Each fresh attempt runs until its context passes the limit again, so a long
  builder spends the whole budget re-doing the same work. That goes against criterion (ii): a
  billing/entitlement cause the vendor typed as permanent must not be retried. Fix: treat a
  `rate_limit` that carries any typed `api_error` as not transient (the plain 429 and the quota
  limit carry none), and add a test for it.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/progress.py:799` and `:789`: the prose check
  for `unknown` reports matches a 5xx-looking number or the word `timeout` anywhere in the
  text. In this CLI a 5xx `APIError` is already stamped `server_error` and a 429 `rate_limit`.
  What falls through to `unknown` (`if(e instanceof Pt)return Qo({…error:"unknown"})`) is
  mostly a generic 4xx, with the JSON body in the text. Concrete cases the probe retries 3×:
  `API Error: 400 {…"invalid_request_error","message":"messages.536.content.0.text: cache_control
  cannot be set for empty text blocks"}` (matched by `\b5\d\d\b` on a message index, which
  long sessions like the headline one pass 500), and `API Error: 400 {…"messages.40.content.1.
  tool_use.input.timeout: Input should be a valid integer"}` (the Bash tool's `timeout` field,
  matched by `\btimeout\b`). A body that literally says `invalid_request_error` gets promoted by
  a stray token. The test side is weak too: `tests/test_terminal_error_classification.py:285`
  is the only negative case, and a mutant that replaces the whole regex with "any text not
  containing 'Unexpected'" passes every test. Fix: tie the status arm to the leading
  `API Error: NNN`, drop or narrow bare `timeout`, and add negative cases with an incidental
  number and field name.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/assemble.py:95` still says both INFRA shapes
  mean "nothing reviewed the diff". The patch rewrote the same phrase in
  `leaves.py:3023` to "no review came back", because it is false for a reviewer that worked
  for minutes and then lost the API. This is the `assemble.py:76-79` "why" block the brief
  cites, and it now disagrees with the code next to it. It's a comment, not operator-facing,
  so low impact, but criterion (iv) asks for every restatement to agree.

## Scope calls for a human

- NEEDS-HUMAN — The patch edits two things the brief put out of bounds. First,
  `template/tests/test_terminal_error_retention.py:368-401`: child-1's `NothingIsClassified`
  guards are renamed and flipped (a transient report after work is now asserted retried 3×,
  and `produced` is now asserted `False`). Second, the print string inside `_do_build_command`
  at `template/src/pdca_harness/leaves.py:2201-2205`, which is #537's function. Both edits
  follow from the brief's own criteria: child-1's guard pinned exactly the behaviour this
  child changes, and the old builder string ("without emitting any work") would be false for
  the headline case. Only strings and assertions changed, and the `for attempt` loop is
  untouched. Still, the brief said "do not touch" both, so a human should accept the
  deviation and check it against #537's and #538's branches at fold time.
- NEEDS-HUMAN — `template/src/pdca_harness/progress.py:765`: `rate_limit` is in the transient
  set because the brief asks for it, but the vendor's own main-session rule (`Akr`: only
  `overloaded`/`server_error`, or the `apiErrorIsTransient` flag) leaves it out. The vendor
  sets that flag on a plain 429 only in some conditions (`apiErrorIsTransient:M`). A
  mid-session quota stop ("resets 5pm") now buys a full fresh re-invoke of a long leaf. The
  retries fail fast at startup, so the cost is small, but the fixtures README
  (`tests/fixtures/README.md`, "Hence `_CLAUDE_TRANSIENT_KINDS`") presents the set as the
  vendor's rule when `rate_limit` actually comes from the vendor's *sub-agent* retry set. This
  is a policy choice, not a bug.

## Tried and could not break

The signal predicate (both spellings; 128 and 255 are correctly outside it; `TIMEOUT_RC`
answers False). A sub-agent report arriving before or after the main one. A wrap-up status
overruling a permanent report. Exit 0 and the harness timeout keeping `produced`. The codex
and stream-less fallbacks. `capture` staying raw. The only other readers of
`run_with_heartbeat` (`gates.py:588`, `publish.py:833`, `leaves.py:993`) ignore `produced`, so
the new meaning cannot leak there.
