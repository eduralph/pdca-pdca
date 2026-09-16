# Build notes — issue 506 (iteration 2)

*Builder rationale; withheld from the reviewer.*
Target: `eduralph/pdca-harness @ main`, worktree `/home/eddie/pdca/pdca-harness.pdca-wt`.
All `path:line` below are on that target branch **after** the patch unless marked "base".

---

## 1. What the change is

Three rules, in the three places the invariant says they live.

| Rule | Where | Lines (patched) |
|---|---|---|
| Classification — read the leaf's own terminal error out of the stream | `progress.py` | `_terminal_error` `:491-538`, wired in the drain `:184-190`, returned `:291-299` |
| Retention — that text rides `output` into `*.error.log` | `progress.py` `:291-298` → `leaves._format_leaf_attempt` `:748-757` | — |
| Retry — the builder joins the resilient path, bounded, with a residue-aware retry prompt | `leaves.py` `:1931-1941` (call), `:1862-1874` (`_BUILD_RETRY_NOTE`), `:719-723` (note applied) | — |

Plus (iv): `leaves._transient_do_death` (`:1823-1852`), called from `do_build` (`:1818-1819`).

### The discriminator is the vendor's own mark, not the prose

This is the single biggest change from iteration 1 and it is what kills defect 1 in **both**
directions at once. I opened the incident's real transcript (the brief cites it) before
writing any matcher:

```
~/.claude/projects/-home-eddie-wyrd-wyrd-pdca/31fa2f21-4d73-4810-9c23-ba33bd860167.jsonl:345
{"type":"assistant", …, "message":{"model":"<synthetic>", …,
   "content":[{"type":"text","text":"API Error: Connection lost mid-response. The response
   above may be incomplete."}]},
 "error":"server_error", "isApiErrorMessage":true, "entrypoint":"sdk-cli", "version":"2.1.228"}
```

It is line 345 of 346 — the session's last event (346 is the CLI's `last-prompt`
bookkeeping record), and the prompt in it is `You are the Do builder. Read
/home/eddie/wyrd/wyrd-pdca/results/issue_717/brief.md…`. So this *is* the incident.

Two fields settle the whole design:

* **`isApiErrorMessage: true`** — the CLI *marks* the message it synthesises for an API
  failure. A leaf that merely writes *about* an API error never carries it. So the
  classifier keys on the mark and never on the wording, and the "too broad" half of defect 1
  disappears structurally rather than by tightening a regex.
* **`error: "server_error"`** — the CLI's own error *kind*, and its own transient test is
  (read out of the shipped binary, claude-code 2.1.233):
  `isTransient: t.apiErrorIsTransient===true || t.error==="overloaded" || t.error==="server_error"`.
  `progress._CLAUDE_TRANSIENT_ERROR_KINDS` is that set (+ `rate_limit`, which criterion (i)
  names explicitly and which #138 already retried at invocation).

The stdout stream spells the flag differently — evidence, from the same binary's
transcript→stream emitter:

```js
case "assistant": return [{ type:"assistant", message:n, session_id:qt(), parent_tool_use_id:null,
  uuid:r.uuid, timestamp:r.timestamp, error:r.error, …,
  ...(r.isApiErrorMessage === true && { is_api_error_message: true }), … }]
```

and the SDK schema string in the same binary: *"`is_api_error_message` … True when this
assistant message wraps an API error"*, with `api_error_status` — *"HTTP status code of the
API error"* — beside it. `_terminal_error` accepts **both spellings** (`progress.py:520-521`):
keying on one of them is exactly how the incident stays unfixed with the suite green.

The result-event path (`progress.py:529-536`) covers the other shape the binary emits on a
terminal failure: `{type:"result", subtype:"error_during_execution", is_error:true,
errors:[…]}` — the `errors` **list**, which iteration 1's `result`/`error` string lookup
would have missed.

---

## 2. Iteration 1's four defects — how each is closed

**1. The matcher was wrong in both directions (`progress.py:420-423`, iteration 1).**
Both halves are gone, and neither is fixed by "a better regex":

* *Too broad* → the prose is never consulted for an event the CLI did not mark.
  Measured through the real path: `Error: assertion failed - expected 500, got 404 in
  test_api.py` as an ordinary assistant message → **substantive, 1 invocation**
  (`test_a_substantive_failure_opening_with_the_lead_word_is_not_retried`); a leaf that opens
  its message with the **verbatim** incident line *and* repeats it as a markdown blockquote →
  **substantive, 1 invocation** (`test_a_leaf_quoting_the_incident_line_is_not_retried`, and
  the quoted text is read out of the pinned fixture so it is byte-identical to the real one).
  Both are the cases the reviewer said the old guard's docstring claimed but never tested.
* *Too narrow* → the cause regex is now stated over the **category** criterion (i) promises
  and is only ever applied to text the CLI marked. Probed through `_terminal_error` against
  15 real CLI error strings lifted from the binary; the reviewer's two →
  `API Error: Connection interrupted.` **transient**, `API Error: Connection timed out.`
  **transient** (`test_a_flagged_error_of_no_named_kind_is_read_from_its_text`, run with kind
  `unknown` — the CLI's own fallback — so the *text* rule is what is under test, not the kind).
  Also transient: `The response stopped arriving.`, `Server error mid-response.`,
  `Connection to the API was lost (ECONNRESET)`, `socket hang up`, `fetch failed`,
  `Request rejected (429) · temporary capacity`, `Overloaded … at capacity`, `503`.
  Not transient (and still **retained**): `400 duplicate tool_use ID`, `request_too_large`,
  `credit balance is too low`, `model is not available`.

**2. The "how to resume" was false in this incident's own scenario.**
`_transient_do_death` (`leaves.py:1823-1852`) now branches on what is actually on disk. With
a partial `patch.diff` present it says the bundle reads BUILT and that `pdca run`/`flow`
would run **CHECK on the partial patch**, and names the two real ways out (move/delete it, or
let Check run and record `iterate-do`, which archives to `iteration-v<N>/`). It deletes
nothing — the docstring says so explicitly, because destroying the builder's artifacts to
make a sentence true is not a fix. Pinned both ways:
`test_the_exhausted_message_owns_up_to_a_partial_patch` (asserts the file survives, that
"CHECK" is named, and that the *false* instruction is absent) and
`test_the_exhausted_message_names_the_class_and_how_to_resume` for the no-residue branch.
Facts checked on the target: `state.py:211` (patch.diff ⇒ BUILT), `driver.py:76` (BUILT ⇒
Check), `driver.py:131-135` (iterate-do archives + rebuilds).

**3. Retry runs over the dead attempt's residue.** Handled at Do level, bounded, exactly as
instructed: `_invoke_leaf_resilient` grows one optional `retry_note` kwarg (default `""`, so
the other three call sites are byte-identical and attempt 1 is byte-identical to a plain
`_invoke`), and Do passes `_BUILD_RETRY_NOTE` — "a previous attempt died MID-FLIGHT … treat
any patch.diff / build-notes.md / test file as INCOMPLETE RESIDUE, not evidence the work is
done … re-run the test red→green yourself rather than trusting a result you did not observe."
Pinned by reading the child's **stdin** (`test_a_retried_builder_is_told_the_previous_attempt
_died_mid_flight`): 3 prompts logged, attempt 1 has no notice, attempts 2 and 3 do.

*Is a prompt-level note sufficient?* Honestly: it is a mitigation, not a guarantee — a model
can ignore a prompt. I am reporting that rather than expanding the slice. The complete fix is
a lane/bundle reset between attempts, which the reviewer put out of scope for this iteration
and which needs its own decision (a reset would also destroy a partial patch the human may
want to read — the same evidence-preservation argument as defect 2). Worth its own issue.

**4. The classifier's contract with the real vendor stream was asserted, never observed.**
Now pinned: `template/tests/fixtures/claude_api_error_death.transcript.jsonl` is the incident
line **byte-for-byte**, and the tests **replay it on the leaf's stdout** so it travels the
real `_invoke → run_with_heartbeat → _terminal_error` path rather than being handed to a
parser. `claude_api_error_death.stream.jsonl` is the same record in the stdout-stream shape,
**derived and labelled as derived** (a real mid-response connection loss cannot be induced on
demand) using the CLI's own emitter, with the derivation, the source path, and the
regeneration snippet recorded in `template/tests/fixtures/README.md`.
`test_the_pinned_incident_event_is_classified_in_both_stream_shapes` runs both.

**Also-worth-closing list:**
* `capture` contract — the terminal report is no longer appended under `capture`
  (`progress.py:291`), so a raw-JSONL capturer keeps verbatim bytes; the *classification*
  still applies. Pinned by `test_a_capturing_caller_still_gets_verbatim_stream_bytes` (and it
  is a real assertion, not a formality: mutation M6 below breaks it).
* Stale "no output" halves updated: `LeafError` docstring + `transient` property
  (`leaves.py:90-113`), `_FAIL_TRANSIENT` (`:2640`), `_failure_class` (`:2645-2656`),
  `_unavailable_classification` prose (`:2705-2710`), the reviewer call-site comment
  (`:2615-2617`), and `assemble.py:80` (the one-line marker comment, now the only other
  place stating the rule).
* `memory_log=` kwarg dropped at the builder call site — `_memory_log_for` derives the
  identical `build.memory.jsonl` (`leaves.py:368-378`), matching the other three sites.
* C5 stays vacuous ("no new test file"), by the brief's own instruction to append to
  `test_leaf_resilience.py`. The production-path claim rests instead on the tests
  themselves: nothing is mocked between the child process's bytes and the assertion (see §4b).

---

## 3. Alternatives considered and rejected

**A. Keep iteration 1's text-only matcher, just tighten/widen it.** Rejected because it
cannot be made right in both directions: the CLI's own error text is the *same string* a
builder writing about the incident emits, so any text rule either misses
`API Error: Connection interrupted.` or fires on a builder quoting the line. Concretely,
mutation **M5** (below) is exactly that design — classify on text without the vendor mark —
and it fails 3 tests, two of them the reviewer's own examples. Cost of the structural rule
instead: +2 dict lookups per stream line.

**B. Denylist instead of allowlist for the cause** (retry every marked API error except a
known-permanent set). Rejected: it retries `400 duplicate tool_use ID`, `request_too_large`,
`credit balance too low` and `model_not_found` three times each — 2 extra full builder
invocations per death, on the leaf the brief calls the most expensive in the cycle — for
failures that are byte-identical on the retry. The allowlist is also what criterion (i)
literally specifies. Retention is applied to *both* sets, so a permanent failure still
explains itself (`test_a_permanent_api_error_is_explained_but_not_retried`).

**C. Retry `error: "rate_limit"` — deliberate, with its cost.** The CLI uses `rate_limit`
both for a transient 429-capacity rejection and for a hard usage limit. Retrying the latter
costs 2 extra spawns and 12 s of backoff and will not succeed. I kept it transient because
(i) criterion (i) names "a mid-session rate-limit rejection", (ii) #138's existing contract
already calls a usage/rate limit transient and retries it, and (iii) the bounded cost is 12 s
+ 2 spawns versus a burnt cycle round when it *is* the capacity kind. Flagging it here so the
human can weigh it rather than burying it.

**D. A `pdca.toml` knob for builder attempts/backoff.** Rejected by the brief's own scope
("no new knob this slice has no evidence to tune"); `_invoke_leaf_resilient`'s existing
`attempts=3, backoff=4.0` are reused untouched.

**E. Session-resume instead of a fresh re-invoke** *(the brief asks me to say so
explicitly)*. Out of scope, and I agree with the call: the CLI's `--resume` would need a
session id the harness does not currently capture from the stream, a decision about what a
half-finished session should be told, and a story for a resumed session that dies again. For
**this** incident nothing would have been lost either way — the dead attempt had written no
artifacts, and the identical argv re-run minutes later succeeded. The cost of a fresh
re-invoke is one wasted attempt's tokens/wall-clock; the cost of resume is a new stateful
coupling to a vendor flag. First cut: re-invoke. Worth revisiting only if a retry that
re-does 18 minutes of work becomes the common case.

**F. Reset the worktree/bundle between retries.** Out of scope per the reviewer (defect 3),
and it conflicts with defect 2's rule against silently deleting the builder's artifacts. See
§2.3.

---

## 4. Forced refutation of my own test

**(a) Genuine red?** Yes — twice over.
* Through the project's own gate: `PDCA_WORKTREE=… PDCA_BUNDLE=… ./engine/scripts/run-verify.sh`
  → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg 32 tests OK; red
  leg (production reverted, all `template/tests/*` hunks kept) **13 failures, `Ran 20 tests`,
  no load failure** — i.e. a measured red, not a module that failed to import.
* Per-hunk mutation testing (each mutation applied alone, suite re-run, then restored). All
  **10 CAUGHT**, none survived:

  | # | mutation | caught by |
  |---|---|---|
  | M1 | drop `and not terminal["transient"]` from the returned `produced` | 11 tests |
  | M2 | drop the `output` append (retention) | 8 tests |
  | M3 | never clear the report when work continues | `…recovered_from_is_not_terminal` |
  | M4 | accept only the stream spelling of the flag | 4, incl. the transcript fixture leg |
  | M5 | classify on text alone, no vendor mark (iteration 1's design) | 3, incl. both quote/lead cases |
  | M6 | append under `capture` too | `…capturing_caller_still_gets_verbatim_stream_bytes` |
  | M7 | builder back on plain `_invoke` | 8 tests |
  | M8 | never append the retry note | `…told_the_previous_attempt_died_mid_flight` |
  | M9 | always claim a plain re-run resumes Do | `…owns_up_to_a_partial_patch` |
  | M10 | let `do_build` overwrite the attempt log | `…retried_bounded_with_backoff` |

**(b) Production path?** Yes. Every new case spawns a **real child process** through the real
`do_build` → `_do_build_command` → `_invoke_leaf_resilient` → `_invoke` →
`progress.run_with_heartbeat` → `subprocess.Popen` chain and asserts on what came back out of
it. Nothing between the child's bytes and the assertion is mocked; the only mock anywhere is
`time.sleep` (so the backoff costs no wall clock) — and `test_…_retried_bounded_with_backoff`
asserts that it was *called*, so the backoff itself is still pinned. Retention is asserted by
reading the on-disk `build.error.log` / `check-review.error.log`, not a return value. Every
asserted marker reaches the child via **env or a fixture file, never argv**, because
`_format_leaf_attempt` echoes the failed argv into the log — an argv-borne marker would make
the assertion pass with no capture at all (the trap `test_build_error_log.py:184-188`
records; iteration 1's notes report measuring it).

**(c) Fixture includes the fault?** Yes. The fault *is* the fixture: the pinned bytes are the
incident's own last stream event, replayed verbatim on the leaf's stdout, **after** the stub
has emitted a substantive `assistant` event — i.e. the test deliberately includes the
"18 minutes of real work" that made the old rule call this substantive. Nothing is curated
out: the same run asserts the retry count (3), the on-disk log content, and the operator
message. The precision cases carry the opposite fault (a real leaf failure that merely *reads*
like infrastructure) and assert it is **not** retried.

**Residual limitation, stated plainly:** no test can induce a real mid-response API
disconnection, so the last unobserved link is "the CLI really does write this event to stdout
in a live death". It is closed as far as evidence allows — real transcript bytes from the
incident + the CLI binary's own emitter and its own transient rule, both quoted in
`template/tests/fixtures/README.md` — but it is a derivation, not a live capture, and the
human should read it as such. No missing external dependency: the whole slice builds and goes
red→green offline on stdlib Python (no vendor CLI, no key, no network).

---

## 5. Commit-readiness

* Target hooks: the repo ships **no** formatter/linter config (no ruff/black/pre-commit, no
  `.editorconfig`); `AGENTS.md:24-29` / `CONTRIBUTING.md:22-27` state the discipline as DCO
  sign-off, one logical change, conventional-prefix subject, and "keep the offline suite
  green". Line length kept inside each file's existing maximum (new code ≤ 93 chars where the
  base files already run to 97/110).
* `./engine/scripts/run-suite.sh` (T3, both suites): `PDCA-EVIDENCE: root suite OK, driver
  suite OK` — 1773 driver tests + 7 root tests, green.
* `./engine/scripts/run-verify.sh` (C4, gating): PASS.
* `git apply --check --reverse patch.diff` on the worktree succeeds, so the patch is exactly
  the tree and applies cleanly to base. 3 new files (2 fixtures + their README).
* No PR pushed, opened, or marked ready.
