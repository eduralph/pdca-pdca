# driver: a leaf's terminal API error is discarded, and a long session that dies of one is misclassified substantive

- **Slug:** a-leafs-own-terminal-error-is-kept-and-read
- **Defect:** `progress.run_with_heartbeat` already reads every event a leaf's stream emits,
  and throws away the one line that explains a death. Two rules, both verified on the target
  base (`eduralph/pdca-harness` @ `main`, `acb214a`):
  * **The stream's own error text is discarded.** The drain parses stdout for a session flag
    and a tool label and keeps nothing else (`template/src/pdca_harness/progress.py:147-158`);
    what it retains is a bounded **stderr** tail (`:143`, `:162-171`), and with `capture` off
    `output` is that stderr tail alone (`:255`). The CLI's API-error line arrives as a stream
    *text* event on **stdout**, so it is displayed and dropped, and `_format_leaf_attempt`
    (`leaves.py:724-730`) falls back to `(no output captured)` — verbatim what the reported
    incident's `build.error.log` contained. The cause was legible only in the CLI's own
    session transcript under `~/.claude/projects/`.
  * **The transient signal cannot see it.** A failure is classified transient only when the
    child produced **no** substantive stream event (`progress.py:144`, `:154-155`,
    `_is_session_event` at `:365-377`; `LeafError.transient` at `leaves.py:103-107`).
    "Produced anything?" is a *proxy* for "died at invocation", and the proxy fails for
    exactly the long sessions where an attempt is most expensive: the incident's 18-minute
    builder did plenty of work and then died of an API connection drop, so it was classified
    substantive — correctly by that rule, wrongly for that cause. The module's own docstring
    (`:55-64`) already records that the CLI emits `system`/`api_retry` on a **retryable** API
    error; the **terminal** report is the case with no reader.
- **Success criterion:** With the patch:
  (i) a leaf whose stream carries the CLI's **own terminal error report** — the report the
  vendor itself marks as an API error — and then exits non-zero is classified **transient**
  when that report's cause is transient (a lost or interrupted connection, an overload or
  5xx, a mid-session rate-limit rejection), however much work came first;
  (ii) it is **not** classified transient when the vendor marks the cause **permanent** (an
  invalid request, an authentication or billing failure) — no prose inside a marked report
  may promote it — nor when a leaf merely mentions or quotes an error, nor when it fails
  substantively; and a report the CLI then **recovers** from, with real **main-session** work
  following it, is not the leaf's death;
  (iii) the report's text is **retained for every marked terminal report, transient or not**,
  so it reaches the leaf's `*.error.log` by the same route the stderr tail takes, and the
  post-mortem explains the failure without opening `~/.claude/projects/`;
  (iv) nothing else changes: a stream-less family still reports substantive
  (`leaves.py:661-670`), `capture` still returns the child's raw stdout unmodified, the
  codex/gemini stream formats degrade to today's behaviour, a leaf that succeeds is spawned
  and reported exactly as today, and the memory-telemetry post-mortem (#420) still rides
  `output` into the same log.
  Demonstrable by C4-verify offline: a stub "leaf" that is a Python interpreter emitting
  chosen stream events and exiting non-zero, driven both through
  `progress.run_with_heartbeat` directly and through `leaves._invoke_leaf_resilient` (the
  reviewer/advisory path, which is resilient on **any** base), so (i)-(iv) are assertions
  over an invocation counter and the error log's bytes.
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:28-40` shows the harness shape to copy into this
  child's own new test file: `_SUBSTANTIVE` emits one `{"type": "assistant"}` event and then
  fails, and the suite asserts it is **not** retried — that is precisely the rule the incident
  falls foul of. A stub leaf that emits a work event, **then** the CLI's marked terminal
  error report, then exits non-zero is the new posture: today it is retried 0 times and its
  error log reads `(no output captured)`, so both assertions fail pre-fix. That is the red.
  Patch the retry backoff from the test so red→green costs no wall-clock.
  **Two gate-shaped traps, both measured against this instance's C4 gate:**
  * `engine/scripts/run-verify.sh:130-137` classifies a changed path as a *test* only when it
    matches `tests/*.py` / `template/tests/*.py`. A **fixture** (`…/fixtures/*.jsonl`) is
    therefore classified **production** and is **reverted on the red leg**, so a case that
    only replays a fixture goes red because the *file is gone*, not because the classifier is
    missing — a vacuous red. So: at least one case per criterion must construct its events
    **inline in the test module**, and a fixture-replaying case must **skip** (not error) when
    its fixture is absent.
  * C4's red leg keeps every `template/tests/*.py` hunk (`:214-217`), so a new test file earns
    a real red — provided it imports no symbol this patch adds at module level: a red-leg
    import failure is recorded `PDCA-UNVERIFIABLE`, not red (`:231-233`). Exercise everything
    through the pre-existing API (`progress.run_with_heartbeat`, `leaves._invoke_leaf_resilient`).
- **Invariant to restore:** **A failure is classified by what actually happened, and the
  evidence of it is kept.** Two halves, stated over the category rather than one API string:
  the harness must read the leaf's **own account** of its death out of the stream it is
  already parsing — never infer a cause from prose it was not given, and never *promote* a
  cause the vendor marked permanent — and it must **retain** that account in the artifact the
  cycle preserves. "Produced no output" is a proxy for "died at invocation" that fails for
  every long session; and "no evidence" must never be filed as a verdict. Self-test: it
  cannot be satisfied by guarding a single module — the classification lives in the stream
  reader, the retention in what `output` carries, and the definition is restated in four
  places downstream that go stale the moment it widens. Source: internal project invariant
  (Tier C), the target's own written rules — `progress.py:55-64` (what the transient signal
  is for, and that a *retryable* API error is already named there and excluded from
  "produced"), `leaves.py:641-647` (`(no output captured)` is "a post-mortem artifact that
  explains nothing", #286 review), `engine/README.md:44-68`. `docs/principles.md` §5/§6 are
  unfilled scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` — the sibling child-1 is independent
  (neither needs the other to compile or to go red→green) and both build on `origin/main` in
  one wave, which is also what this instance's own #474 base-export leak makes preferable
  (`plan-0.60-bug-order.md`). The two children share `leaves.py` but in disjoint regions:
  this one touches **prose only** (the four sites that restate the transient definition),
  child-1 owns the wrapper body, `do_build` and the harvest sites; and they ship tests in
  **different files** by construction. Recommended merge order at publish: **child-1 first**,
  then this one — widening *which* failures are retried is what first makes a leaf retryable
  after it has produced work, and child-1 is what makes that safe.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** What a leaf's death *is*, on the spawn path every leaf shares — read the CLI's
  own terminal error report out of the stream the driver already parses, classify transient
  by what the **vendor** marked (not by prose the harness guesses at), and keep that text so
  it reaches the leaf's `*.error.log` by the route the stderr tail already takes. Update the
  four downstream prose sites that restate the old definition so the codebase does not carry
  two contradictory statements of it.
  **Out of scope:** who is retried and what a retry may inherit — the builder is **not** put
  on the resilient path here, `_invoke_leaf_resilient`'s body, `do_build`, and the artifact
  harvests are sibling child-1's (this child changes only `progress.py`, the four prose sites
  in `leaves.py`, one comment in `assemble.py`, and its own tests/fixtures); resuming a long
  session via the CLI's own session-resume (a fresh re-invoke is the accepted first cut — say
  so in `build-notes.md` so the human can weigh it); the gate-side transient (issue #371); a
  leaf **signal-death** under the memory cap (issue #510: "neither #506's transient nor
  #421's preflight"); the memory-telemetry post-mortem (#420), which must keep working
  unchanged; any new `pdca.toml` knob.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today. Read
     `:32-35` and `:66-74`: `_SUBSTANTIVE` emits one stream event, then fails, and the suite
     asserts it is **not** retried. That is the rule the incident falls foul of.
  2. Read the drop: `progress.py:147-158` (stdout parsed for a session flag and a tool label,
     then discarded), `:143` + `:162-171` (the bounded **stderr** tail), `:255` (`output` is
     that stderr tail when `capture` is off), `:257` (what the third return value means),
     `leaves.py:103-107` (`transient` is `not produced`), `leaves.py:724-730` (the
     `(no output captured)` fallback the incident's log shows verbatim).
  3. Read what the module already knows and does not use: `progress.py:55-64` (claude emits
     `system`/`api_retry` on a **retryable** API error — deliberately excluded from
     "produced") and `_SESSION_EVENT_TYPES` (`:359`).
  4. The live incident is named in the parent issue: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`); the identical argv re-run minutes later
     succeeded.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter, so the slice builds and goes red→green with no
  vendor CLI, no API key, no network and no container. (Grounding the event shape against the
  vendor is a *reading* step, not a build or verification input — see Citations expected.)
- **Test file:** `template/tests/test_terminal_error_classification.py` (**new**), plus
  `template/tests/fixtures/` for the pinned vendor record and its provenance note. Do **not**
  append to `template/tests/test_leaf_resilience.py` and do **not** edit
  `template/tests/test_build_error_log.py`: sibling child-1 owns both and builds on the same
  base in the same wave — a shared test file is the one place the two patches would collide.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `progress._is_session_event` (`:365-377`) is the existing per-family stream classifier:
    it dispatches on `stream_format`, parses JSON best-effort and defaults to `False`. A
    terminal-error reader belongs **beside it, in the same shape**, so the codex/gemini
    formats degrade to today's behaviour instead of guessing;
  * `:143` + `:162-171` show how a bounded tail is kept (`deque(maxlen=…)`) and `:255` how it
    becomes `output` — the retained report should reach `LeafError.output` by that same route,
    so `_format_leaf_attempt` (`leaves.py:724-730`) needs **no** special case and this child
    need not touch it (it is child-1's);
  * `leaves.py:661-670` documents why a stream-less family reports `produced=True`; keep that
    fallback intact;
  * the four sites that restate the definition and go stale when it widens — update the prose,
    touch nothing else in them: `leaves.py:90-107` (`LeafError`), `:661-670` (the `_invoke`
    comment), `:2534-2549` (`_failure_class`), `:2573-2590` (`_unavailable_classification`),
    and `assemble.py:80` (`LEAF_STATUS_INFRA`'s "ran, died with no output" comment);
  * **Vendor grounding is the standard this slice is held to.** Two of the parent's four
    rejected rounds were rejected for asserting an event shape the CLI cannot emit, and the
    round that held re-derived it from the shipped binary. Establish the shape from the
    installed `claude` CLI and/or a real session transcript under `~/.claude/projects/`, and
    record next to the fixture which claims are **observed** and which are **derived**.
  * **Prior art you may read, selectively:** the rejected single-slice attempt is archived at
    `results/issue_506/iteration-v4/patch.diff` (+ `build-notes.md`), including a pinned
    fixture and a provenance README that the adversary independently re-derived from
    claude-code 2.1.233. You may reuse them — re-verifying the load-bearing claims first —
    and read the `progress.py` hunks for decisions already settled (the matcher anchored on
    the vendor's own marker; the "the CLI recovered" clearing rule; stickiness against the
    session wrap-up). Two defects were still open against that attempt and must not be
    rebuilt: the clearing rule was **scope-blind** (one trailing *sub-agent* line restored the
    pre-fix outcome exactly — require the clearing event to be main-session), and stickiness
    was implemented over *any* later report so a **second** marked report (a permanent 400
    following a dropped connection) was swallowed. Read **only** the hunks for the files this
    child owns — re-applying the `leaves.py` body / `do_build` / harvest material would
    recreate the oversized slice this split exists to undo.

  **Path convention in this brief:** every `template/…` and `tests/…` path is on the **target
  branch** (eduralph/pdca-harness @ main) — the files Do reads and edits. Every `engine/…`,
  `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification engine
  and the bundles that run the cycle); they are cited to explain how the gates will judge the
  patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/progress.py` — `0881af9` (#420 memory sampling), `4091b94`
  (straggler sweep), `228e80b` (#368 timeouts), `49f6611` (#286, "capture a stream-less leaf's
  stderr too"): the closest relative, and it extended **stderr** capture — the stream's own
  events were never read. Open PRs on the target (`gh pr list -R eduralph/pdca-harness
  --state open`): #519-#525; none touches `progress.py`, and the two that touch `leaves.py`
  (#524 issue 494, #520 issue 466) are at distant regions. Open issues searched for
  `transient`: #371 (gate-row transient red) and #510 (signal death) are adjacent and
  deliberately excluded above; #509 (crash-resume) is a different beat. Not previously
  attempted as its own slice, not rejected; the parent 506's four-round attempt was rejected
  on slicing (`results/issue_506/iteration-v4/SUMMARY.md` §9).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: The approach is sound and the evidence is strong — gates green, all reviewer rows PASS, the adversary independently re-ran the red→green and re-derived the vendor grounding from the shipped binary. Rejected on one landed refutation, not on the design. Must close before re-submission: 1. Scope the terminal-report reader to the main session (`progress.py:560-562`). The `_REPORT` branch matches a marked api-error message without checking `parent_tool_use_id`, while its sibling `_is_main_session_work` (`:660-681`) is deliberately main-session-scoped. Because `_note_terminal` is newest-wins and only protects a `_REPORT` from a *wrap-up*, a trailing SUB-AGENT report overwrites the main session's. Confirmed by reading the patch at sign-off. Consequence, and why it blocks: a main-session `invalid_request` followed by a sub-agent `overloaded` classifies transient — a cause the vendor marked PERMANENT is promoted and retried to the attempt budget — and the retained diagnostic names the wrong death ("API Error: 529 the API is at capacity"). That is criterion (ii) inverted, and it is the same family as the defect the brief said must not be rebuilt (a second marked report swallowing the first). Retention is the point of criterion (iii); a log that confidently names the wrong cause is worse than the "(no output captured)" it replaces. Fix is one predicate — scope the `_REPORT` branch to `parent_tool_use_id is None`, or make `_note_terminal` prefer a main-session report — plus the missing case. The test helper's `parent=` parameter (`test_terminal_error_classification.py:71-77`) already exists and is passed by no test; the gap was contemplated and left unasserted. Note the commoner variant, which needs no conjunction: a sub-agent blip in a leaf that then fails on its own merits is now labelled transient. Fixing the scope closes both. 2. `produced`'s documented contract is bent on the SUCCESS path. A leaf whose stream carried a transient marked report and then exited 0 returns `produced=False`, while the docstring (`progress.py:60-62`) still defines it as "did the child emit a substantive stream event". No current call site misreads it, but #510's signal-death work is the next reader of that flag. Either restore the flag on rc == 0 or restate the contract. 3. UNRESOLVED SCOPE QUESTION, not adjudicated at this sign-off: `leaves.py:693` and `:724-726` are a fifth and sixth restatement of the definition this patch widens, and both are left false — the operator sees "leaf exited 1 with no output (transient)" for a leaf that produced 18 minutes of work and a report (printed verbatim in this round's own green leg, gate-logs/C4-verify.log lines 12-13). The brief lists only four prose sites and scopes `_invoke_leaf_resilient`'s body to sibling child-1 (issue_532). Since 532 also went back for rebuild this round, its scope is still movable: settle which child owns these two lines before either lands, so the codebase does not ship the contradiction the invariant exists to prevent. §6 fitness-to-purpose was NOT cleared and remains open for the next round. The main-session scoping in item 1 is what the boundary's fitness turns on. Note also that the expensive case in that item — replaying a long-running builder — is not reachable from this patch alone (the builder is not on the resilient path here); it becomes live when 532 lands, which is a further reason to settle the two together.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The approach is sound and the evidence is strong — gates green, all reviewer rows PASS,
  the adversary independently re-ran the red→green and re-derived the vendor grounding from
  the shipped binary. Rejected on one landed refutation, not on the design.

  Must close before re-submission:

  1. Scope the terminal-report reader to the main session (`progress.py:560-562`). The
     `_REPORT` branch matches a marked api-error message without checking
     `parent_tool_use_id`, while its sibling `_is_main_session_work` (`:660-681`) is
     deliberately main-session-scoped. Because `_note_terminal` is newest-wins and only
     protects a `_REPORT` from a *wrap-up*, a trailing SUB-AGENT report overwrites the main
     session's. Confirmed by reading the patch at sign-off.

     Consequence, and why it blocks: a main-session `invalid_request` followed by a
     sub-agent `overloaded` classifies transient — a cause the vendor marked PERMANENT is
     promoted and retried to the attempt budget — and the retained diagnostic names the
     wrong death ("API Error: 529 the API is at capacity"). That is criterion (ii)
     inverted, and it is the same family as the defect the brief said must not be rebuilt
     (a second marked report swallowing the first). Retention is the point of criterion
     (iii); a log that confidently names the wrong cause is worse than the
     "(no output captured)" it replaces.

     Fix is one predicate — scope the `_REPORT` branch to `parent_tool_use_id is None`, or
     make `_note_terminal` prefer a main-session report — plus the missing case. The test
     helper's `parent=` parameter (`test_terminal_error_classification.py:71-77`) already
     exists and is passed by no test; the gap was contemplated and left unasserted.

     Note the commoner variant, which needs no conjunction: a sub-agent blip in a leaf that
     then fails on its own merits is now labelled transient. Fixing the scope closes both.

  2. `produced`'s documented contract is bent on the SUCCESS path. A leaf whose stream
     carried a transient marked report and then exited 0 returns `produced=False`, while
     the docstring (`progress.py:60-62`) still defines it as "did the child emit a
     substantive stream event". No current call site misreads it, but #510's signal-death
     work is the next reader of that flag. Either restore the flag on rc == 0 or restate
     the contract.

  3. UNRESOLVED SCOPE QUESTION, not adjudicated at this sign-off: `leaves.py:693` and
     `:724-726` are a fifth and sixth restatement of the definition this patch widens, and
     both are left false — the operator sees "leaf exited 1 with no output (transient)" for
     a leaf that produced 18 minutes of work and a report (printed verbatim in this round's
     own green leg, gate-logs/C4-verify.log lines 12-13). The brief lists only four prose
     sites and scopes `_invoke_leaf_resilient`'s body to sibling child-1 (issue_532). Since
     532 also went back for rebuild this round, its scope is still movable: settle which
     child owns these two lines before either lands, so the codebase does not ship the
     contradiction the invariant exists to prevent.

  §6 fitness-to-purpose was NOT cleared and remains open for the next round. The
  main-session scoping in item 1 is what the boundary's fitness turns on. Note also that the
  expensive case in that item — replaying a long-running builder — is not reachable from
  this patch alone (the builder is not on the resilient path here); it becomes live when
  532 lands, which is a further reason to settle the two together.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the implementation, not the slice or the evidence. This round is well evidenced — C5 is a genuine pass (unlike the sibling's), the vendor grounding was re-derived from the shipped 2.1.233 binary rather than trusted from fixtures/README.md, and the suite caught eight of nine planted mutations. Both blocking defects from the previous round (main-session scoping, `produced`'s contract on the success path) are genuinely fixed, not re-worded. Do NOT re-cut this slice. What follows are local defects in the classifier, each confirmed by reading patch.diff directly. Must close before re-submission: 1. The classifier reads prose for ANY unrecognised kind, and its own docstring says it must not. Two defects in three lines of `_kind_is_transient` / `_terminal_error`: (a) `kind = str(ev.get("error") or "unknown")` collapses an ABSENT `error` key into the string "unknown" — but 2.1.233's queryLoop catch-all marks a message (`isApiErrorMessage:!0`) while leaving `error` undefined, which is the shape ANY exception escaping the loop takes; (b) the final `return any(_TRANSIENT_CAUSE_RE .search(t) for t in texts)` fires for every kind outside the two frozensets, while the docstring immediately above states "The text is read **only** for the kind the CLI leaves ``unknown``". Consequence, verified through the production path: a dead MCP server (`connect ECONNREFUSED`), `fetch failed`, `socket hang up`, `terminated` are all retried to the attempt budget and the operator is told "transient infra — safe to re-run" for a config failure that fails identically every time — the exact conflation PR #285's review is cited against. It is also the drift hole: the CLI auto-updates and the harness pins nothing, so any kind the vendor adds after 2.1.233 gets classified by regex. Make the code match its docstring (`if kind != "unknown": return False` keeps all 28 tests green, so the loose branch is both unnecessary and untested), and distinguish an absent `error` key from a literal "unknown". 2. Signal deaths are not excluded from the transient class, and the brief fences them out. `died_of_reported_infra = terminal["transient"] and rc not in (0, TIMEOUT_RC)` spares the run the harness killed on its WALL-CLOCK bound but not the one it killed on its MEMORY bound (#420), nor one a signal took. Measured: a stub leaf that emits a work event, then the incident's own `server_error` report, then dies of SIGKILL returns `(-9, ..., produced=False)` -> transient -> three attempts, each of which will hit the same cap. `_memory_cap_prefix` puts every capped leaf one OOM away from this. The brief states a signal death "is neither #506's transient nor #421's preflight" (#510's own question), so this patch must not silently reclassify it. Add the exclusion and a test. COORDINATE WITH SIBLING issue_532 (also iterate-do this round): the two children have OPPOSITE holes at the same boundary. 532's `_builder_retryable` excludes `rc < 0` but misses a positive 137 (a wrapper argv — `sh -c`, `docker run`, the documented `local-build` shape — reports its child's OOM SIGKILL as 137). 533 excludes neither. The signal-death boundary wants deciding ONCE and spelled the same way in both, rather than each child inventing half of it. 3. The transcript spelling is half-supported. `_terminal_error` deliberately accepts the persisted transcript spelling `isApiErrorMessage` alongside the stream's `is_api_error_message`, but decides WHOSE death it was from `parent_tool_use_id` only — a field the transcript shape does not carry (it carries `isSidechain`). Since `.get()` returns None for an absent key, a transcript-shaped SIDECHAIN record is classified as the main session's own death, retried, and the retained diagnostic names a sub-agent's blip as the leaf's death. Not reachable from any 2.1.233 emitter today — which is an argument for resolving the branch, not for keeping half of it: either the shape can appear (then honour `isSidechain`, or treat an absent `parent_tool_use_id` as unknown scope) or it cannot (then delete the transcript-spelling branch and the test asserting a record no vendor emits). 4. The `result` exclusion from `_WORK_EVENT_TYPES` is load-bearing but unasserted. The comment claims that letting `result` count as work means "the death this fix exists for is retried zero times again, with the suite green" — and mutation testing confirms exactly that: adding `"result"` leaves all 28 tests green, because every wrap-up the suite emits carries `is_error` and so takes the `_note_terminal` branch, never the clearing `elif`. The exclusion only bites for a text-less `is_error` result (`{"type":"result","subtype":"success","is_error":true,"result":""}`), which no case covers. One event appended to `test_report_survives_the_wrapups_that_name_no_cause` closes it. OWNERSHIP QUESTION — RESOLVED AT SIGN-OFF, this child KEEPS the prose: The `_invoke_leaf_resilient` docstring and retry-print edits (`leaves.py:693-704`, `:728-730`) stay with THIS child. Sibling issue_532 has been instructed in its own iterate-do carry-forward to leave those two prose sites alone. Rationale: 533 is the child that changes what "transient" MEANS, so it is the child that must restate it; 532's version of that print keeps the old "with no output (transient)" wording, which this child's whole purpose is to retire. Verified mechanically at sign-off that the two patches DO collide — both rewrite the same retry-print line and the same docstring, and 533's hunk carries as trailing context an `error_log.write_text(...)` line that 532 deletes. Keep these edits; do not hand them back. Section 6's fourth bullet is a truncated duplicate of its first ("`leaves.py:693-704` and `:728-730` (the `_invoke_leaf_resilient` docstring" — cut off mid-sentence). An assembly artifact, not a finding; noted so the next round does not chase it as a separate item. Section 6 items are left OPEN (an iterate does not require them cleared). Item 1's substance — the ownership question — is settled above; items T5 and Validation remain genuinely open and should be re-examined once 1-4 are closed.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the implementation, not the slice or the evidence. This round is well
  evidenced — C5 is a genuine pass (unlike the sibling's), the vendor grounding was
  re-derived from the shipped 2.1.233 binary rather than trusted from fixtures/README.md,
  and the suite caught eight of nine planted mutations. Both blocking defects from the
  previous round (main-session scoping, `produced`'s contract on the success path) are
  genuinely fixed, not re-worded. Do NOT re-cut this slice. What follows are local defects
  in the classifier, each confirmed by reading patch.diff directly.

  Must close before re-submission:

  1. The classifier reads prose for ANY unrecognised kind, and its own docstring says it
     must not. Two defects in three lines of `_kind_is_transient` / `_terminal_error`:
     (a) `kind = str(ev.get("error") or "unknown")` collapses an ABSENT `error` key into
     the string "unknown" — but 2.1.233's queryLoop catch-all marks a message
     (`isApiErrorMessage:!0`) while leaving `error` undefined, which is the shape ANY
     exception escaping the loop takes; (b) the final `return any(_TRANSIENT_CAUSE_RE
     .search(t) for t in texts)` fires for every kind outside the two frozensets, while the
     docstring immediately above states "The text is read **only** for the kind the CLI
     leaves ``unknown``". Consequence, verified through the production path: a dead MCP
     server (`connect ECONNREFUSED`), `fetch failed`, `socket hang up`, `terminated` are all
     retried to the attempt budget and the operator is told "transient infra — safe to
     re-run" for a config failure that fails identically every time — the exact conflation
     PR #285's review is cited against. It is also the drift hole: the CLI auto-updates and
     the harness pins nothing, so any kind the vendor adds after 2.1.233 gets classified by
     regex. Make the code match its docstring (`if kind != "unknown": return False` keeps
     all 28 tests green, so the loose branch is both unnecessary and untested), and
     distinguish an absent `error` key from a literal "unknown".

  2. Signal deaths are not excluded from the transient class, and the brief fences them out.
     `died_of_reported_infra = terminal["transient"] and rc not in (0, TIMEOUT_RC)` spares
     the run the harness killed on its WALL-CLOCK bound but not the one it killed on its
     MEMORY bound (#420), nor one a signal took. Measured: a stub leaf that emits a work
     event, then the incident's own `server_error` report, then dies of SIGKILL returns
     `(-9, ..., produced=False)` -> transient -> three attempts, each of which will hit the
     same cap. `_memory_cap_prefix` puts every capped leaf one OOM away from this. The brief
     states a signal death "is neither #506's transient nor #421's preflight" (#510's own
     question), so this patch must not silently reclassify it. Add the exclusion and a test.

     COORDINATE WITH SIBLING issue_532 (also iterate-do this round): the two children have
     OPPOSITE holes at the same boundary. 532's `_builder_retryable` excludes `rc < 0` but
     misses a positive 137 (a wrapper argv — `sh -c`, `docker run`, the documented
     `local-build` shape — reports its child's OOM SIGKILL as 137). 533 excludes neither.
     The signal-death boundary wants deciding ONCE and spelled the same way in both, rather
     than each child inventing half of it.

  3. The transcript spelling is half-supported. `_terminal_error` deliberately accepts the
     persisted transcript spelling `isApiErrorMessage` alongside the stream's
     `is_api_error_message`, but decides WHOSE death it was from `parent_tool_use_id` only —
     a field the transcript shape does not carry (it carries `isSidechain`). Since `.get()`
     returns None for an absent key, a transcript-shaped SIDECHAIN record is classified as
     the main session's own death, retried, and the retained diagnostic names a sub-agent's
     blip as the leaf's death. Not reachable from any 2.1.233 emitter today — which is an
     argument for resolving the branch, not for keeping half of it: either the shape can
     appear (then honour `isSidechain`, or treat an absent `parent_tool_use_id` as unknown
     scope) or it cannot (then delete the transcript-spelling branch and the test asserting
     a record no vendor emits).

  4. The `result` exclusion from `_WORK_EVENT_TYPES` is load-bearing but unasserted. The
     comment claims that letting `result` count as work means "the death this fix exists for
     is retried zero times again, with the suite green" — and mutation testing confirms
     exactly that: adding `"result"` leaves all 28 tests green, because every wrap-up the
     suite emits carries `is_error` and so takes the `_note_terminal` branch, never the
     clearing `elif`. The exclusion only bites for a text-less `is_error` result
     (`{"type":"result","subtype":"success","is_error":true,"result":""}`), which no case
     covers. One event appended to `test_report_survives_the_wrapups_that_name_no_cause`
     closes it.

  OWNERSHIP QUESTION — RESOLVED AT SIGN-OFF, this child KEEPS the prose:
  The `_invoke_leaf_resilient` docstring and retry-print edits (`leaves.py:693-704`,
  `:728-730`) stay with THIS child. Sibling issue_532 has been instructed in its own
  iterate-do carry-forward to leave those two prose sites alone. Rationale: 533 is the child
  that changes what "transient" MEANS, so it is the child that must restate it; 532's
  version of that print keeps the old "with no output (transient)" wording, which this
  child's whole purpose is to retire. Verified mechanically at sign-off that the two patches
  DO collide — both rewrite the same retry-print line and the same docstring, and 533's hunk
  carries as trailing context an `error_log.write_text(...)` line that 532 deletes. Keep
  these edits; do not hand them back.

  Section 6's fourth bullet is a truncated duplicate of its first ("`leaves.py:693-704` and
  `:728-730` (the `_invoke_leaf_resilient` docstring" — cut off mid-sentence). An assembly
  artifact, not a finding; noted so the next round does not chase it as a separate item.

  Section 6 items are left OPEN (an iterate does not require them cleared). Item 1's
  substance — the ownership question — is settled above; items T5 and Validation remain
  genuinely open and should be re-examined once 1-4 are closed.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Human rationale (sign-off, issue_533): iterate-plan concerning the replanning of its sibling. Not rejected on the implementation. This round is strong — the reviewer returned PASS on all ten cells, the adversary reproduced red->green independently (30/34 red, 34/34 green) on the real spawn path with no mocked classifier, re-derived the vendor claims from the shipped `claude-code 2.1.233` binary, and killed 6 of 12 mutations. C5 is a GENUINE pass here (a real new test file importing `pdca_harness`) — the C5 vacuity that decided sibling issue_532 does NOT apply to this bundle and must not be carried across. Why it returns to Plan anyway: - The Validation fitness item is not free-standing: it asks to approve the vendor-event boundary and the fresh-reinvoke policy "together with sibling issue #532". #532 was sent to iterate-plan in this same session, so that boundary is being re-cut. Clearing this item now would approve one half of a boundary whose other half is being redrawn. The re-plan must settle the two children against each other, not separately. - Signal-death is the concrete instance of that shared boundary, and each child owns the opposite half: #532's `_builder_retryable` excludes `rc < 0` but misses a positive 137; this child's `died_of_reported_infra` excludes neither. Decide it ONCE across both, and state where the #510 line falls, rather than letting each child invent half of it. - Slice size: 99 KB against the 80 KB backstop, and it is not fixture bloat — 44 KB is production source (`progress.py` 32.6 KB, `leaves.py` 10.5 KB), 34 KB test, 19 KB fixtures + README. Round 3 of implementation-shaped findings each round. Author the split at Plan (`pdca-pdca split 533`, then `pdca-pdca split 533 --accept`). Carry into whichever child keeps the mechanism (all confirmed by measurement, not reading): - Prose/code mismatch with a live cost: `leaves.py:102` and `:700-702` state that a signal-killed leaf is not transient, but `LeafError.transient` is still `not produced`, so a leaf emitting no stream event and dying of SIGKILL (or the wrapper's rc=137) is classified transient and run 3 times — a memory-capped leaf buys three more OOMs. Both signal tests emit a work event first, so neither reaches the shape. - Operator-facing falsehood: `assemble.py:85` `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` still reads "leaf did not run (transient infra — safe to re-run)", and that string is prefixed onto the §6 items the human reads. The patch widens that class to cover a leaf that DID run substantively — the brief's own 18-minute-builder headline case — so §6 will assert "did not run" directly above the retained report proving it ran. It is the fifth restatement site (four were enumerated), and `test_leaf_status.py:135,188` pin the stale string, so the suite cannot catch it. - Definition still restated two contradictory ways: `assemble.py:80` and `leaves.py:2544` were narrowed to "ran, died of infra it reported", dropping #138's original emitted-nothing shape, which still routes to the same `_FAIL_TRANSIENT` / `LEAF_STATUS_INFRA` pair. Their siblings at `leaves.py:2552-2554` and `:2611-2616` get it right. A newly-wrong restatement is the same defect this slice exists to prevent. (`test_leaf_status.py:84`'s comment is stale for the same reason.) - Two surviving mutations = unpinned guards: the `"user"` member of `_WORK_EVENT_TYPES` (`progress.py:465`) is load-bearing — deleting it flips a recovered-then-substantively- failed leaf to retryable, the criterion-(ii) inversion, with all 34 tests still green; and both `result`-branch discriminators (`_TRANSIENT_STATUSES`, the `subtype == "success"` guard, `progress.py:687-688` and `:567`) are unasserted. - Fitness call to settle in the brief, not in Do: the clearing rule (`progress.py:237-240`) discards the retained text along with the verdict, so `(no output captured)` can still be the post-mortem for a leaf whose CLI did explain itself. Criterion (iii) says the text is retained for every marked terminal report; the patch reads a recovered report as not terminal. Decide which reading is wanted. §6 NEEDS-HUMAN items were left open — none were cleared.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Human rationale (sign-off, issue_533): iterate-plan concerning the replanning of its
  sibling.

  Not rejected on the implementation. This round is strong — the reviewer returned PASS on
  all ten cells, the adversary reproduced red->green independently (30/34 red, 34/34 green)
  on the real spawn path with no mocked classifier, re-derived the vendor claims from the
  shipped `claude-code 2.1.233` binary, and killed 6 of 12 mutations. C5 is a GENUINE pass
  here (a real new test file importing `pdca_harness`) — the C5 vacuity that decided sibling
  issue_532 does NOT apply to this bundle and must not be carried across.

  Why it returns to Plan anyway:

  - The Validation fitness item is not free-standing: it asks to approve the vendor-event
    boundary and the fresh-reinvoke policy "together with sibling issue #532". #532 was sent
    to iterate-plan in this same session, so that boundary is being re-cut. Clearing this
    item now would approve one half of a boundary whose other half is being redrawn. The
    re-plan must settle the two children against each other, not separately.

  - Signal-death is the concrete instance of that shared boundary, and each child owns the
    opposite half: #532's `_builder_retryable` excludes `rc < 0` but misses a positive 137;
    this child's `died_of_reported_infra` excludes neither. Decide it ONCE across both, and
    state where the #510 line falls, rather than letting each child invent half of it.

  - Slice size: 99 KB against the 80 KB backstop, and it is not fixture bloat — 44 KB is
    production source (`progress.py` 32.6 KB, `leaves.py` 10.5 KB), 34 KB test, 19 KB
    fixtures + README. Round 3 of implementation-shaped findings each round. Author the
    split at Plan (`pdca-pdca split 533`, then `pdca-pdca split 533 --accept`).

  Carry into whichever child keeps the mechanism (all confirmed by measurement, not
  reading):

  - Prose/code mismatch with a live cost: `leaves.py:102` and `:700-702` state that a
    signal-killed leaf is not transient, but `LeafError.transient` is still `not produced`,
    so a leaf emitting no stream event and dying of SIGKILL (or the wrapper's rc=137) is
    classified transient and run 3 times — a memory-capped leaf buys three more OOMs. Both
    signal tests emit a work event first, so neither reaches the shape.

  - Operator-facing falsehood: `assemble.py:85`
    `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` still reads "leaf did not run (transient infra —
    safe to re-run)", and that string is prefixed onto the §6 items the human reads. The
    patch widens that class to cover a leaf that DID run substantively — the brief's own
    18-minute-builder headline case — so §6 will assert "did not run" directly above the
    retained report proving it ran. It is the fifth restatement site (four were enumerated),
    and `test_leaf_status.py:135,188` pin the stale string, so the suite cannot catch it.

  - Definition still restated two contradictory ways: `assemble.py:80` and `leaves.py:2544`
    were narrowed to "ran, died of infra it reported", dropping #138's original
    emitted-nothing shape, which still routes to the same `_FAIL_TRANSIENT` /
    `LEAF_STATUS_INFRA` pair. Their siblings at `leaves.py:2552-2554` and `:2611-2616` get it
    right. A newly-wrong restatement is the same defect this slice exists to prevent.
    (`test_leaf_status.py:84`'s comment is stale for the same reason.)

  - Two surviving mutations = unpinned guards: the `"user"` member of `_WORK_EVENT_TYPES`
    (`progress.py:465`) is load-bearing — deleting it flips a recovered-then-substantively-
    failed leaf to retryable, the criterion-(ii) inversion, with all 34 tests still green;
    and both `result`-branch discriminators (`_TRANSIENT_STATUSES`, the
    `subtype == "success"` guard, `progress.py:687-688` and `:567`) are unasserted.

  - Fitness call to settle in the brief, not in Do: the clearing rule
    (`progress.py:237-240`) discards the retained text along with the verdict, so
    `(no output captured)` can still be the post-mortem for a leaf whose CLI did explain
    itself. Criterion (iii) says the text is retained for every marked terminal report; the
    patch reads a recovered report as not terminal. Decide which reading is wanted.

  §6 NEEDS-HUMAN items were left open — none were cleared.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
