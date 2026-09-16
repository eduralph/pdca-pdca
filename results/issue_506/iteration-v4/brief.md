# Brief — issue 506 / a-transient-leaf-death-is-explained-and-retried

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** a-transient-leaf-death-is-explained-and-retried
- **Defect:** A mid-response API failure inside a leaf burns the whole attempt and leaves a
  post-mortem artifact that explains nothing. Observed downstream (getwyrd/wyrd-pdca, bundle
  `results/issue_717/`): the escalated builder (opus, `--effort max`, the #135 ladder tier) ran
  ~18 minutes in auto-iterate, the API connection dropped mid-response, the CLI exited 1, and
  `build.error.log` recorded only
  `----- attempt 1 — exit 1 ----- (no output captured) LeafError: Command '['claude', '-p', …]'
  returned non-zero exit status 1.` The cause was visible only in the CLI's own session
  transcript under `~/.claude/projects/`:
  `2026-08-12T00:29:33 TEXT: API Error: Connection lost mid-response.` An identical re-run
  minutes later succeeded. Three weaknesses compound, all verified on the target base:
  * **The stream's own error text is discarded.** `progress.run_with_heartbeat` drains stdout
    for a session flag and a tool label only (`template/src/pdca_harness/progress.py:146-158`)
    and keeps a bounded **stderr** tail (`:143`, `:163-171`); with `capture` off, `output` is
    that stderr tail alone (`:255`). The API-error line arrives as a stream *text* event on
    stdout, so it is displayed and dropped, and `_format_leaf_attempt`
    (`template/src/pdca_harness/leaves.py:723-730`) falls back to `(no output captured)`.
  * **The transient signal cannot see it.** A failure is classified transient only when the
    child produced **no** substantive stream event (`progress.py:154-155`, `_is_session_event`
    at `:365-377`; `leaves.py:664-670`). An 18-minute session that then dies mid-response
    produced plenty, so it is classified substantive — correctly by that rule, wrongly for this
    cause.
  * **The builder is not on the resilient path at all.** `_invoke_leaf_resilient`
    (`leaves.py:673-720`: bounded retry with backoff + a per-attempt error log) is used by the
    reviewer (`:2507`), the advisory (`:2840`) and the plan advisory (`:3142`). `do_build` calls
    plain `_invoke` (`leaves.py:1825`, via `_do_build_command`), so **no** builder failure is
    ever retried — and the builder is the leaf where an attempt is most expensive, and the
    escalation ladder's deep tiers (opus/max) are exactly where sessions run longest.
  On the current base the run itself no longer dies of a traceback on either CLI path —
  `flow._advance_one` wraps the beat in `_isolate` (`flow.py:459`) and the batch auto-iterate is
  wrapped at `:1333` — so what survives of the report's third symptom is the *message*: the
  operator gets `build/check failed (LeafError: Command '[…]' returned non-zero exit status 1)`,
  which names an argv and an exit status and nothing about why. (`flow_one`, the library-only
  route, still propagates — deliberately out of scope below.)
- **Success criterion:** With the patch:
  (i) a leaf whose stream carries a **terminal transient error event** — a lost/interrupted
  connection, an overload or 5xx, a mid-session rate-limit rejection — and then exits non-zero is
  classified **transient**, whether or not it produced substantive work first, while a leaf that
  fails for a substantive reason is still classified substantive and is **not** retried;
  (ii) that classification actually reaches Do: a transient builder death is retried, bounded,
  with backoff, instead of burning the attempt;
  (iii) `build.error.log` for such a death carries the leaf's **own terminal error text** rather
  than `(no output captured)`, so the post-mortem explains the failure without opening
  `~/.claude/projects/`;
  (iv) when the bounded retries are exhausted, what the operator reads names the transient
  classification and how to resume, rather than an argv and an exit status alone;
  (v) nothing else changes: a leaf that succeeds is spawned and reported exactly as today, the
  existing reviewer/advisory resilience contract (attempt count, backoff, per-attempt records,
  the `transient` attribute) still holds, a stream-less family still reports substantive
  (`leaves.py:664-669`), and the memory-telemetry post-mortem (#420) still rides `output` into
  the same log.
  Demonstrable by C4-verify: the offline suite spawns a stub "leaf" that is a Python interpreter
  emitting chosen stream events and exiting non-zero, so (i)-(iv) are assertions over an
  invocation counter and the error log's bytes.
- **Falsifiability:** RED is reachable on the base toolchain — pure-stdlib Python ≥ 3.11, no
  network, no vendor CLI — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:26-40` already carries exactly the harness this needs:
  `_TRANSIENT` (stderr only, no stream event → retried today) and `_SUBSTANTIVE` (prints one
  `{"type": "assistant"}` stream event, then fails → not retried today), a leaf whose argv is
  `[sys.executable, "-c", script]`, and a `$CNT` file counting invocations. A third script that
  emits a session event **and then** the API-error text before exiting 1 is the new posture: it
  is retried 0 times today and its error log reads `(no output captured)` — both assertions fail
  pre-fix, and that is the red. The retry backoff must be patchable so the red→green costs no
  wall-clock (the existing suite already does this). C4's red leg reverts `progress.py` /
  `leaves.py` and keeps every `template/tests/*.py` hunk
  (`engine/scripts/run-verify.sh:214-217`), so appended cases earn a genuine red — provided the
  test imports no symbol the patch adds at module level (see Citations expected).
- **Invariant to restore:** A leaf's failure must be **attributable** and classified by **what
  actually happened**, not by a proxy that happens to correlate: the artifact the cycle keeps
  must carry the leaf's own account of its death, and an infrastructure failure the leaf did not
  cause must not be charged to the leaf as a substantive failure. Stated over the category, not
  the one API string: "produced no output" is a proxy for "died at invocation" that fails for
  every long session, so the classification must read the terminal event the stream already
  delivers; and the retention rule is the same one the harness already applies to stderr
  (`leaves.py:647` — the `(no output captured)` fallback is called out there as "a post-mortem
  artifact that explains nothing", #286 review) extended to the stream that carries the
  diagnostic. Self-test: it cannot be satisfied by guarding one module — the classification lives
  in the stream reader, the retention in the error-log writer, and the retry at the builder call
  site. Source: internal project invariant (Tier C) — the target's own written rules:
  `progress.py:59-64` (what the transient signal is for), `leaves.py:641-647` (why a captured
  tail exists at all), and the harness-wide rule that "no evidence" must never be filed as a
  verdict (`engine/README.md:44-68`). `docs/principles.md` §5/§6 are unfilled scaffolds in this
  instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves, and a
  wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds. Ordering
  lives in the run boundaries. Known same-file neighbours, accepted by that plan: 466 and 494
  also touch `leaves.py`, in distant regions (`:1594-1631` and `:782`/`:3261`/`:3400`/`:3465`
  versus this slice's `:647-730` and `:1740-1830`); `progress.py` is this bundle's alone. The run
  plan puts this first among the nine — it is the failure class run 1 itself hit.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** Leaf-death classification and retention on the spawn path shared by every leaf, and
  putting the builder on the resilient path: read the terminal transient signal out of the stream
  the driver already parses, keep that text so it reaches the leaf's `*.error.log`, and let Do
  retry on it, bounded — with the exhausted-retry message naming the cause and the resume.
  **Out of scope:** resuming a long session via the CLI's own session-resume (a fresh re-invoke
  is an acceptable first cut, and for this incident nothing would have been lost either way — but
  say so in `build-notes.md` so the human can weigh it); the gate-side transient (issue #371 —
  one transient red on a *gating gate row* is the same argument in a different layer, and is its
  own slice); a leaf **signal-death** under the memory scope (issue #510 states explicitly that a
  SIGKILLed leaf "is neither #506's transient nor #421's preflight" — do not fold it in here);
  `flow._isolate`'s containment contract and the `flow_one` library route's propagation (a
  different, deliberate design point — `flow.py:302-306` documents why the single-issue path has
  no `_isolate` there); the memory-telemetry post-mortem (#420), which must keep working
  unchanged; any new `pdca.toml` knob (reuse the existing attempts/backoff defaults rather than
  adding configuration this slice has no evidence to tune).
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today. Read
     `:26-40`: `_SUBSTANTIVE` emits one stream event, then fails; the suite asserts it is **not**
     retried. That is the rule the incident falls foul of.
  2. Read the drop: `progress.py:146-158` (stdout is parsed for a session flag and a tool label
     and then discarded), `:255` (`output` is the **stderr** tail when `capture` is off),
     `leaves.py:664-670` (`produced` decides `transient`), `leaves.py:723-730` (the
     `(no output captured)` fallback the incident's log shows verbatim).
  3. Read the missing wiring: `leaves.py:1825` (`_invoke`, not `_invoke_leaf_resilient`) against
     `:2507`, `:2840`, `:3142`.
  4. The live artifacts are named in the issue body: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`), failing tier = the `[[leaves.builder_escalation]]`
     opus/max entry; the identical argv re-run minutes later succeeded.
- **External dependencies:** none — every leg is driven with a stub leaf that is a Python
  interpreter, so the slice builds and goes red→green on the base toolchain, with no vendor CLI,
  no API key and no network.
- **Test file:** `template/tests/test_leaf_resilience.py` — append to the existing suite. It owns
  this contract (#138), and its stub-leaf harness, invocation counter and error-log assertions are
  exactly what the new posture needs; C4's red leg keeps all `template/tests/*.py` hunks and
  reverts only production, so appended cases earn their red. If Do also changes `do_build`'s
  error-log shape, `template/tests/test_build_error_log.py` is the sibling that pins it and must
  stay green.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `progress._is_session_event` (`progress.py:365-377`) is the existing per-family stream
    classifier, dispatching on `stream_format` with a best-effort JSON parse and a
    `False` default — a terminal-error classifier belongs beside it, in the same shape, so the
    codex/gemini formats degrade to today's behaviour instead of guessing. Note what the module
    already knows and does not yet use: `_SESSION_EVENT_TYPES` is `{"assistant", "user",
    "result"}` (`:359`) and the docstring at `:61-64` records that claude also emits
    `system`/`api_retry` **on a retryable API error** — deliberately excluded from "produced".
    The incident's error text arrived inside an `assistant` event *after* real work, which is
    exactly the gap: the retry signal the stream carries is already named there, and the
    terminal case is what has no reader;
  * `progress.py:143` + `:163-171` show how a bounded tail is kept (`deque(maxlen=…)`) and
    `:255` how it becomes `output` — the stream tail should reach `LeafError.output` by the same
    route, so `_format_leaf_attempt` (`leaves.py:723-730`) needs no special case;
  * `leaves._invoke_leaf_resilient` (`:673-720`) is the retry wrapper to reuse **as it is**,
    including its error-log staleness rule and its `memory_log` pairing (`_memory_log_for`);
    `do_build`'s existing capture-and-re-raise (`leaves.py:1763-1777`) is the outer contract it
    must compose with — Do's failure must still be captured and still re-raised for
    `flow._isolate`;
  * `leaves.py:664-669` documents why a stream-less family reports `produced=True`; keep that
    fallback intact.
  The appended tests must not import a symbol this patch introduces at module level: C4's red leg
  reverts production first, and a module that then fails to import is recorded
  `PDCA-UNVERIFIABLE`, not red (`engine/scripts/run-verify.sh:231-234`).

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/progress.py` — `0881af9` (#420 memory sampling), `4091b94`
  (straggler sweep), `228e80b` (#368 timeouts), `49f6611` (#286, "capture a stream-less leaf's
  stderr too"): the closest relative, and it extended **stderr** capture, never the stream's own
  events. `template/src/pdca_harness/leaves.py` — `_invoke_leaf_resilient` arrived with #138 for
  the reviewer/advisory leaves and was never extended to the builder.
  `gh pr list -R eduralph/pdca-harness --state open` → **no open PRs**. Open issues searched for
  `transient`: #371 (gate-row transient red) and #510 (signal-death classification) are adjacent
  and deliberately excluded above; #509 (crash-resume) is a different beat. Not previously
  attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the findings (reviewer C3/T3/T5 + the adversary lens). The core mechanism is sound and independently confirmed -- red->green reproduced, full suite green at base runtime, and all four mutations of the load-bearing hunks were caught, so the tests are not tautological. Keep that. Four defects sit on top of it: 1. The matcher is wrong in BOTH directions (progress.py:420-423). - Too narrow: `API Error: Connection interrupted.` and `API Error: Connection timed out.` yield no classification when probed against the patched target -- `_TRANSIENT_CAUSE_RE` accepts "interrupted" only before "mid-response", and only 429/500/502/503/504/529. Criterion (i) promises lost/interrupted connections. - Too broad: `_ERROR_LEAD_RE`'s `^\W*` lead plus a bare `error` word classifies substantive builder deaths as transient and re-runs the builder 3x -- measured through the real path with e.g. "Error: assertion failed - expected 500, got 404 in test_api.py". The `^\W*` also eats markdown, so a builder that QUOTES the incident line at the head of a bullet or blockquote is read as dying of it. Tighten the lead (require the api/fatal/connection qualifier, or anchor on the CLI's literal `API Error:` prefix) and widen the cause to the promised category. Add a red case for a substantive block that OPENS with the lead word, and one for a leading verbatim quote: the existing guard (test_leaf_resilience.py:75, :185, :519-529) only covers a mid-sentence mention, so it never tests the case its own docstring claims. 2. The exhausted-retry "how to resume" is false in this incident's own scenario (leaves.py:1812-1817). A builder that writes patch.diff and then dies leaves the bundle at BUILT (state.py:211), and driver.py:76 then runs Check, not Do, on the partial patch. Fix the message (name that a partial patch.diff must be cleared first). Do NOT silently delete the builder's artifacts to make the sentence true. 3. Retry re-invokes the builder on the dead attempt's residue: worktree.ensure runs once, before the wrapper (leaves.py:1833), so attempts 2-3 start in a worktree carrying attempt 1's edits and a bundle already holding patch.diff/build-notes.md. Risk: attempt 2 reads a complete-looking patch, exits 0, and a half-finished build is reported as successful. HANDLE THIS AT DO LEVEL, bounded -- make the retry prompt state that a previous attempt died mid-flight and that any patch.diff / build-notes.md present are its incomplete residue to be verified or replaced, not evidence the work is done. A lane reset or a new config knob is out of scope for this iteration; if the rebuild concludes a prompt-level note is insufficient, say so in build-notes.md rather than expanding the slice. 4. The classifier's contract with the real vendor stream is asserted, never observed -- every test synthesises the event shape it then parses (test_leaf_resilience.py:63-73). If the CLI emits that death as a `system` event, a `result` with no string result/error key, or on stderr, `_terminal_error_text` (progress.py:442) and `_claude_event_texts` (progress.py:466) return "" and the incident stays unfixed with the suite green. Pin one real transcript from ~/.claude/projects/ (the brief cites it) as a fixture. Also worth closing while in there: - progress.py:279-285 bends the documented `capture` contract (docstring :113-114 says the stream parse is mutually exclusive with capture) -- latent today, since no caller sets both, but the first raw-JSONL capturer gets a trailing non-JSON line. - leaves.py:108-110, :2583, :2588 still describe transient as "no output" only, after the patch widened the rule -- stale half of the definition. - leaves.py:1882 passes `memory_log=` explicitly where the other three call sites rely on `_memory_log_for` deriving the identical path; drop the kwarg to match. - Note the C5 green is vacuous here ("patch adds no new test file -- nothing to assert"), so it supports no production-path claim.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the findings (reviewer C3/T3/T5 + the adversary lens). The core mechanism
  is sound and independently confirmed -- red->green reproduced, full suite green at
  base runtime, and all four mutations of the load-bearing hunks were caught, so the
  tests are not tautological. Keep that. Four defects sit on top of it:

  1. The matcher is wrong in BOTH directions (progress.py:420-423).
     - Too narrow: `API Error: Connection interrupted.` and `API Error: Connection timed
       out.` yield no classification when probed against the patched target --
       `_TRANSIENT_CAUSE_RE` accepts "interrupted" only before "mid-response", and only
       429/500/502/503/504/529. Criterion (i) promises lost/interrupted connections.
     - Too broad: `_ERROR_LEAD_RE`'s `^\W*` lead plus a bare `error` word classifies
       substantive builder deaths as transient and re-runs the builder 3x -- measured
       through the real path with e.g. "Error: assertion failed - expected 500, got 404
       in test_api.py". The `^\W*` also eats markdown, so a builder that QUOTES the
       incident line at the head of a bullet or blockquote is read as dying of it.
     Tighten the lead (require the api/fatal/connection qualifier, or anchor on the
     CLI's literal `API Error:` prefix) and widen the cause to the promised category.
     Add a red case for a substantive block that OPENS with the lead word, and one for
     a leading verbatim quote: the existing guard
     (test_leaf_resilience.py:75, :185, :519-529) only covers a mid-sentence mention, so
     it never tests the case its own docstring claims.

  2. The exhausted-retry "how to resume" is false in this incident's own scenario
     (leaves.py:1812-1817). A builder that writes patch.diff and then dies leaves the
     bundle at BUILT (state.py:211), and driver.py:76 then runs Check, not Do, on the
     partial patch. Fix the message (name that a partial patch.diff must be cleared
     first). Do NOT silently delete the builder's artifacts to make the sentence true.

  3. Retry re-invokes the builder on the dead attempt's residue: worktree.ensure runs
     once, before the wrapper (leaves.py:1833), so attempts 2-3 start in a worktree
     carrying attempt 1's edits and a bundle already holding patch.diff/build-notes.md.
     Risk: attempt 2 reads a complete-looking patch, exits 0, and a half-finished build
     is reported as successful. HANDLE THIS AT DO LEVEL, bounded -- make the retry
     prompt state that a previous attempt died mid-flight and that any patch.diff /
     build-notes.md present are its incomplete residue to be verified or replaced, not
     evidence the work is done. A lane reset or a new config knob is out of scope for
     this iteration; if the rebuild concludes a prompt-level note is insufficient, say
     so in build-notes.md rather than expanding the slice.

  4. The classifier's contract with the real vendor stream is asserted, never observed
     -- every test synthesises the event shape it then parses
     (test_leaf_resilience.py:63-73). If the CLI emits that death as a `system` event, a
     `result` with no string result/error key, or on stderr, `_terminal_error_text`
     (progress.py:442) and `_claude_event_texts` (progress.py:466) return "" and the
     incident stays unfixed with the suite green. Pin one real transcript from
     ~/.claude/projects/ (the brief cites it) as a fixture.

  Also worth closing while in there:
  - progress.py:279-285 bends the documented `capture` contract (docstring :113-114 says
    the stream parse is mutually exclusive with capture) -- latent today, since no caller
    sets both, but the first raw-JSONL capturer gets a trailing non-JSON line.
  - leaves.py:108-110, :2583, :2588 still describe transient as "no output" only, after
    the patch widened the rule -- stale half of the definition.
  - leaves.py:1882 passes `memory_log=` explicitly where the other three call sites rely
    on `_memory_log_for` deriving the identical path; drop the kwarg to match.
  - Note the C5 green is vacuous here ("patch adds no new test file -- nothing to
    assert"), so it supports no production-path claim.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the findings — both advisory lenses converged independently on the same place. The core mechanism is SOUND and independently reproduced (13 red / 20 green through the real subprocess path, 1773 template tests OK, pinned real vendor transcript), and iteration 1's four defects are genuinely fixed: the matcher is re-anchored on the CLI's own `is_api_error_message` marker, the resume message is honest about a partial patch.diff, the retry note warns about residue, and the vendor contract is now observed rather than synthesised. KEEP ALL OF THAT — also the `_has_content` guard (leaves.py:758-765, :1812), the `capture`-exclusivity guard on the stream append (progress.py:409-415), and the derived `memory_log`. What must change is the `result`-event branch, `progress.py:529-535`. Three defects, all measured through the production path: 1. It silently overwrites the incident's own correct verdict. `terminal.update(...)` at progress.py:186 is last-writer-wins, so assistant(work) -> assistant{is_api_error_message, "Connection lost mid-response"} -> result{is_error, subtype:"error_during_execution", result:"Execution error"} yields transient=False and ONE invocation: the fix fails on the exact death it was built for, with the suite green. This contradicts the patch's own reasoning — progress.py:401-403 excludes `result` from `_WORK_EVENT_TYPES` because it is "the session's wrap-up", yet the same wrap-up is allowed to re-classify the death. Make a transient report STICKY unless real work follows it, rather than overwritable by the wrap-up. 2. The "too broad" arm iteration 1 was rejected for survives, relocated into this branch. It is gated only on `is_error` + `subtype != "success"` and then runs the wide `_TRANSIENT_CAUSE_RE` over free prose from `result`/`error`/`errors`. Measured through do_build: "Build failed: the integration test timed out waiting for the fixture server" -> 3 builder invocations; "2 tests failed: expected 500, got 404 in test_api.py" -> 3 invocations. Non-infra endings (error_max_turns, a guardrail refusal, a tool's own execution error, a log the leaf was merely reading) all reach it. Fix by keying on a field the CLI itself marks as an infra cause — e.g. restrict to the documented `error_during_execution` subtype plus `api_error_status` — or drop the branch; do not leave classification resting on prose in the one shape iteration 1's fix didn't reach. 3. The branch is entirely unpinned. `is_error` appears in no file under `template/tests/`, no stub emits a `result` event, and disabling progress.py:529 outright leaves 63 tests green. Whatever survives of this branch needs precision tests for a SUBSTANTIVE `result`-event ending, the mirror of the two assistant-branch precision tests. Two further items to close in the same rebuild: 4. The retry prompt points at a file that does not exist. `_BUILD_RETRY_NOTE` (leaves.py:1866) tells the retried builder its predecessor's account "is in build.error.log in the bundle directory", but `_invoke_leaf_resilient` unlinks it at leaves.py:712 and writes the records only after the loop at :741 — instrumented from inside the child, attempts 1/2/3 all see exists=False. Flush "".join(records) before each backoff sleep (which also survives a SIGKILLed run) or drop the sentence. Note the test at test_leaf_resilience.py:450 asserts only that the strings are present, so it passes over the false instruction. 5. The "read the vendor's verdict, not the prose" claim is not what the tests pin: both `_CLAUDE_TRANSIENT_ERROR_KINDS -> frozenset()` (progress.py:451) and `_transient_status -> return False` (:561-563) survive with 63 tests green — every transient case is rescued by the prose regex instead. Consequence: criterion (i)'s promised mid-session RATE-LIMIT rejection has no test at all. Pin the kind and `api_error_status` paths directly, with text the regex would not rescue. SCOPE — flagged, do NOT expand the slice to it. Widening the classification makes the reviewer/advisory leaves retryable after they have produced work, which they never were before, and their harvest is `if produced.exists()` (leaves.py:2629-2632) — unconditional on which attempt wrote it — so a truncated check-review.md from a dead attempt 1 can be copied into the bundle as the reviewer's verdict. Passing `retry_note` at leaves.py:2618/:2952/:3254 is necessary but not sufficient, since the harvest itself is attempt-blind. If the rebuild concludes this cannot be closed within the slice, say so in build-notes.md and leave it for a separate issue rather than growing this one. Not re-litigated: C4's derived stream fixture, the PR #524 rebase ownership, and the dirty-worktree fitness question remain open §6 items for the next sign-off; the disabled plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the findings — both advisory lenses converged independently on the same
  place. The core mechanism is SOUND and independently reproduced (13 red / 20 green
  through the real subprocess path, 1773 template tests OK, pinned real vendor
  transcript), and iteration 1's four defects are genuinely fixed: the matcher is
  re-anchored on the CLI's own `is_api_error_message` marker, the resume message is
  honest about a partial patch.diff, the retry note warns about residue, and the vendor
  contract is now observed rather than synthesised. KEEP ALL OF THAT — also the
  `_has_content` guard (leaves.py:758-765, :1812), the `capture`-exclusivity guard on the
  stream append (progress.py:409-415), and the derived `memory_log`.

  What must change is the `result`-event branch, `progress.py:529-535`. Three defects,
  all measured through the production path:

  1. It silently overwrites the incident's own correct verdict. `terminal.update(...)` at
     progress.py:186 is last-writer-wins, so assistant(work) -> assistant{is_api_error_message,
     "Connection lost mid-response"} -> result{is_error, subtype:"error_during_execution",
     result:"Execution error"} yields transient=False and ONE invocation: the fix fails on
     the exact death it was built for, with the suite green. This contradicts the patch's own
     reasoning — progress.py:401-403 excludes `result` from `_WORK_EVENT_TYPES` because it is
     "the session's wrap-up", yet the same wrap-up is allowed to re-classify the death. Make a
     transient report STICKY unless real work follows it, rather than overwritable by the wrap-up.

  2. The "too broad" arm iteration 1 was rejected for survives, relocated into this branch.
     It is gated only on `is_error` + `subtype != "success"` and then runs the wide
     `_TRANSIENT_CAUSE_RE` over free prose from `result`/`error`/`errors`. Measured through
     do_build: "Build failed: the integration test timed out waiting for the fixture server"
     -> 3 builder invocations; "2 tests failed: expected 500, got 404 in test_api.py" -> 3
     invocations. Non-infra endings (error_max_turns, a guardrail refusal, a tool's own
     execution error, a log the leaf was merely reading) all reach it. Fix by keying on a
     field the CLI itself marks as an infra cause — e.g. restrict to the documented
     `error_during_execution` subtype plus `api_error_status` — or drop the branch; do not
     leave classification resting on prose in the one shape iteration 1's fix didn't reach.

  3. The branch is entirely unpinned. `is_error` appears in no file under `template/tests/`,
     no stub emits a `result` event, and disabling progress.py:529 outright leaves 63 tests
     green. Whatever survives of this branch needs precision tests for a SUBSTANTIVE
     `result`-event ending, the mirror of the two assistant-branch precision tests.

  Two further items to close in the same rebuild:

  4. The retry prompt points at a file that does not exist. `_BUILD_RETRY_NOTE`
     (leaves.py:1866) tells the retried builder its predecessor's account "is in
     build.error.log in the bundle directory", but `_invoke_leaf_resilient` unlinks it at
     leaves.py:712 and writes the records only after the loop at :741 — instrumented from
     inside the child, attempts 1/2/3 all see exists=False. Flush "".join(records) before each
     backoff sleep (which also survives a SIGKILLed run) or drop the sentence. Note the test at
     test_leaf_resilience.py:450 asserts only that the strings are present, so it passes over
     the false instruction.

  5. The "read the vendor's verdict, not the prose" claim is not what the tests pin: both
     `_CLAUDE_TRANSIENT_ERROR_KINDS -> frozenset()` (progress.py:451) and `_transient_status ->
     return False` (:561-563) survive with 63 tests green — every transient case is rescued by
     the prose regex instead. Consequence: criterion (i)'s promised mid-session RATE-LIMIT
     rejection has no test at all. Pin the kind and `api_error_status` paths directly, with text
     the regex would not rescue.

  SCOPE — flagged, do NOT expand the slice to it. Widening the classification makes the
  reviewer/advisory leaves retryable after they have produced work, which they never were
  before, and their harvest is `if produced.exists()` (leaves.py:2629-2632) — unconditional on
  which attempt wrote it — so a truncated check-review.md from a dead attempt 1 can be copied
  into the bundle as the reviewer's verdict. Passing `retry_note` at leaves.py:2618/:2952/:3254
  is necessary but not sufficient, since the harvest itself is attempt-blind. If the rebuild
  concludes this cannot be closed within the slice, say so in build-notes.md and leave it for a
  separate issue rather than growing this one.

  Not re-litigated: C4's derived stream fixture, the PR #524 rebase ownership, and the
  dirty-worktree fitness question remain open §6 items for the next sign-off; the disabled
  plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the adversary's three implementation findings — the core mechanism is SOUND and independently confirmed (red 26 / green 29, 1782 template tests OK, 16/16 mutations of the load-bearing hunks caught, pinned vendor transcript). KEEP ALL OF IT: the marker-anchored matcher on `is_api_error_message`, the sticky-transient rule (it survived the adversary's attack — the aborted-turn variant genuinely can follow the api-error message, and stickiness is what saves it), the per-attempt `_write_attempt_records` flush before the backoff sleep, the `_has_content` guard, the `capture`-exclusivity guard, and the derived `memory_log`. Three defects sit on top of it, all grounded in the shipped vendor binary (claude-code 2.1.233) and measured through the production path: 1. A real mid-response connection loss is classified SUBSTANTIVE and the builder is NOT retried when the CLI's error kind is `unknown` (progress.py:452, :468). claude-code's API-error mapper ends `return Yd({content: "API Error: " + e.message, error: "unknown"})` whenever no cause code is found in its `sie`/`gde` sets — and neither set contains any `UND_ERR_*` code, so Node/undici's canonical mid-response stream abort (`TypeError: terminated`, cause `SocketError{code:"UND_ERR_SOCKET"}`) surfaces as `{"type":"assistant","is_api_error_message":true,"error":"unknown", … "API Error: terminated"}`. `_TRANSIENT_CAUSE_RE` matches none of `terminated` / `other side closed` / `stream disconnected`. Measured: transient=False, 1 invocation, vs transient=True and 3 invocations for the pinned incident text. That is criterion (i)'s "a lost/interrupted connection" left unretried — the exact category the slice promises. Add those shapes to the cause set. This is SAFE in the direction iteration 1 was rejected for: the regex only ever runs on text the CLI itself marked (progress.py:537), so it cannot re-open the false-positive arm. While in there: the patch's own `UND_ERR_[A-Z_]+` alternative (progress.py:493) is unreachable for this shape — the code lives in the event's `cause`, never in the text — so either read the nested cause code or drop that alternative rather than leave a branch that looks like coverage and is not. 2. The `result`-branch `api_error_status` arm is dead code against the real stream, and both tests that "pin" it construct an event the CLI cannot emit. progress.py:546 guards on `subtype != "success"` while :551 requires `error_during_execution` PLUS an `api_error_status` — but in 2.1.233 the only result carrying that field is the `subtype:"success"` variant with `is_error`; the `error_during_execution` / `error_max_turns` variants carry `errors:[…]` and nothing else. The CLI asserts this in its own telemetry (`api_error_status: ol.subtype === "success" ? … : void 0`). So the guard excludes exactly the shape that carries the field. Either re-key the arm on the CLI's actual API-error ending (`subtype == "success" and is_error` — still machine-marked, still no prose matching) or DELETE the arm and state that the wrap-up is retention-only. Either way, remove the two impossible records at test_leaf_resilience.py:461 and :473 — that is the "synthesised the shape it then parses" defect round 2 rejected, relocated into the one branch the vendor fixture never covered. Do not leave a green test standing for an event that cannot exist. 3. The stickiness rationale cites an incident ending that was never observed (progress.py:558-560) and `_WRAP_UP` (test_leaf_resilience.py:85, used at :208) encodes it. An api-error ending with no thrown/aborted turn produces the SUCCESS variant with the API-error text in `result`; the `error_during_execution` variant is emitted only for a throw or an aborted turn and then carries `errors:["[ede_diagnostic] turn aborted (…) stop_reason=…"]` — "Execution error" appears nowhere, and the pinned transcript (tests/fixtures/README.md, line 345 = last event) contains no result record at all. Keep the sticky RULE; restate the comment and the fixture over the aborted-turn variant that actually can follow, or drop the claim. Asserted-rather-than-observed is the exact standard the fixture was added to enforce. SCOPE — unchanged, do NOT expand. The reviewer/advisory attempt-blind harvest (leaves.py:2653, :2986, :3287) stays a follow-up issue; build-notes.md already records it honestly with a measured ≈28-line cost, which is what was asked for. Do not take it here. SIZE — the patch is 86 KB against the 80 KB backstop already (35 KB of it tests). These three fixes must not grow it: (2) deletes a dead arm and two tests, (1) and (3) are small. If the rebuild finds itself adding substantial new surface, say so in build-notes.md rather than widening the slice. Not re-litigated, still open §6 items for the next sign-off: C4's derived-stream fixture vs a live API death, the prior-art check on a disposable target, and fitness-to-purpose. The C5 gate row is a vacuous pass ("patch adds no new test file — nothing to assert") and supports no production-path claim; the adversary checked the substance separately and it holds. The plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure. Optional if free: the drain hot path now parses the same line up to 4× (progress.py:182-194) — non-gating, a single `json.loads` passed to each classifier would do.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the adversary's three implementation findings — the core mechanism is SOUND and
  independently confirmed (red 26 / green 29, 1782 template tests OK, 16/16 mutations of the
  load-bearing hunks caught, pinned vendor transcript). KEEP ALL OF IT: the marker-anchored
  matcher on `is_api_error_message`, the sticky-transient rule (it survived the adversary's
  attack — the aborted-turn variant genuinely can follow the api-error message, and stickiness
  is what saves it), the per-attempt `_write_attempt_records` flush before the backoff sleep,
  the `_has_content` guard, the `capture`-exclusivity guard, and the derived `memory_log`.
  Three defects sit on top of it, all grounded in the shipped vendor binary (claude-code
  2.1.233) and measured through the production path:

  1. A real mid-response connection loss is classified SUBSTANTIVE and the builder is NOT
     retried when the CLI's error kind is `unknown` (progress.py:452, :468). claude-code's
     API-error mapper ends `return Yd({content: "API Error: " + e.message, error: "unknown"})`
     whenever no cause code is found in its `sie`/`gde` sets — and neither set contains any
     `UND_ERR_*` code, so Node/undici's canonical mid-response stream abort (`TypeError:
     terminated`, cause `SocketError{code:"UND_ERR_SOCKET"}`) surfaces as
     `{"type":"assistant","is_api_error_message":true,"error":"unknown", … "API Error:
     terminated"}`. `_TRANSIENT_CAUSE_RE` matches none of `terminated` / `other side closed` /
     `stream disconnected`. Measured: transient=False, 1 invocation, vs transient=True and 3
     invocations for the pinned incident text. That is criterion (i)'s "a lost/interrupted
     connection" left unretried — the exact category the slice promises. Add those shapes to
     the cause set. This is SAFE in the direction iteration 1 was rejected for: the regex only
     ever runs on text the CLI itself marked (progress.py:537), so it cannot re-open the
     false-positive arm. While in there: the patch's own `UND_ERR_[A-Z_]+` alternative
     (progress.py:493) is unreachable for this shape — the code lives in the event's `cause`,
     never in the text — so either read the nested cause code or drop that alternative rather
     than leave a branch that looks like coverage and is not.

  2. The `result`-branch `api_error_status` arm is dead code against the real stream, and both
     tests that "pin" it construct an event the CLI cannot emit. progress.py:546 guards on
     `subtype != "success"` while :551 requires `error_during_execution` PLUS an
     `api_error_status` — but in 2.1.233 the only result carrying that field is the
     `subtype:"success"` variant with `is_error`; the `error_during_execution` /
     `error_max_turns` variants carry `errors:[…]` and nothing else. The CLI asserts this in
     its own telemetry (`api_error_status: ol.subtype === "success" ? … : void 0`). So the
     guard excludes exactly the shape that carries the field. Either re-key the arm on the
     CLI's actual API-error ending (`subtype == "success" and is_error` — still machine-marked,
     still no prose matching) or DELETE the arm and state that the wrap-up is retention-only.
     Either way, remove the two impossible records at test_leaf_resilience.py:461 and :473 —
     that is the "synthesised the shape it then parses" defect round 2 rejected, relocated into
     the one branch the vendor fixture never covered. Do not leave a green test standing for an
     event that cannot exist.

  3. The stickiness rationale cites an incident ending that was never observed
     (progress.py:558-560) and `_WRAP_UP` (test_leaf_resilience.py:85, used at :208) encodes
     it. An api-error ending with no thrown/aborted turn produces the SUCCESS variant with the
     API-error text in `result`; the `error_during_execution` variant is emitted only for a
     throw or an aborted turn and then carries `errors:["[ede_diagnostic] turn aborted (…)
     stop_reason=…"]` — "Execution error" appears nowhere, and the pinned transcript
     (tests/fixtures/README.md, line 345 = last event) contains no result record at all. Keep
     the sticky RULE; restate the comment and the fixture over the aborted-turn variant that
     actually can follow, or drop the claim. Asserted-rather-than-observed is the exact
     standard the fixture was added to enforce.

  SCOPE — unchanged, do NOT expand. The reviewer/advisory attempt-blind harvest
  (leaves.py:2653, :2986, :3287) stays a follow-up issue; build-notes.md already records it
  honestly with a measured ≈28-line cost, which is what was asked for. Do not take it here.

  SIZE — the patch is 86 KB against the 80 KB backstop already (35 KB of it tests). These three
  fixes must not grow it: (2) deletes a dead arm and two tests, (1) and (3) are small. If the
  rebuild finds itself adding substantial new surface, say so in build-notes.md rather than
  widening the slice.

  Not re-litigated, still open §6 items for the next sign-off: C4's derived-stream fixture vs a
  live API death, the prior-art check on a disposable target, and fitness-to-purpose. The C5
  gate row is a vacuous pass ("patch adds no new test file — nothing to assert") and supports no
  production-path claim; the adversary checked the substance separately and it holds. The
  plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure.
  Optional if free: the drain hot path now parses the same line up to 4× (progress.py:182-194) —
  non-gating, a single `json.loads` passed to each classifier would do.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on SLICING, not on the mechanism. The core is sound and has survived four rounds of independent attack — red->green reproduced every round through the real subprocess path, 1780 template tests green, 9/13 and 16/16 mutations of the load-bearing hunks caught, the vendor contract re-derived from the shipped binary. KEEP ALL OF IT. Each round also genuinely closed the previous round's defects. The problem is that the findings have been implementation-shaped in all four rounds, which is what an oversized slice produces: 92 KB against the 80 KB backstop, round 4 against a 3-round threshold. Do not rebuild this as one slice again — split it in Plan. Proposed seams (author the briefs at the split; the sizing.json currently claims one indivisible outcome, which is the judgement being overridden here): 1. STREAM-SIDE classification + retention, in progress.py: read the CLI's own terminal error event, classify transient by the marker/kind/status the vendor sets, keep the text so it reaches the leaf's *.error.log. This is criteria (i) and (iii). Self-contained and independently testable against the pinned fixture. 2. DO-SIDE resilience, in leaves.py: put do_build on _invoke_leaf_resilient with the retry note, the _has_content guard, the per-attempt _write_attempt_records flush, and the _transient_do_death exhausted-retry message. This is criteria (ii) and (iv). Depends on 1 but is a distinct outcome. 3. Optional third: the reviewer/advisory attempt-blind harvest, already deferred twice and measured at ~34 lines across two files in build-notes.md:197-206. File it as its own issue rather than deferring it a third time. Carry into the child briefs, unresolved this round: - Adversary finding A (progress.py:188-191, :405, :625-636): the "the CLI recovered" clearing rule is scope-blind — one trailing SUB-AGENT line restores the pre-fix outcome exactly (transient=False, 1 invocation, "(no output captured)"), so criteria (i) and (iii) both fail with the suite green. Containment is one line: require the clearing event to be main-session (parent_tool_use_id null/absent). The adversary could not establish the ordering in the wild; the gap is cheap to close regardless. - Adversary finding B (progress.py:580): stickiness is documented over the `result` wrap-up but implemented over any later report, so a SECOND marked api-error report is swallowed — a permanent 400 following a dropped connection is neither retained nor read, and costs 3 spawns. Containment is one line: stick only against a `result` event, let a later marked report overwrite. Already self-disclosed as a known trade-off in build-notes.md; close it rather than re-disclose it. - The reviewer's C3/T3 FAIL needs adjudication, not compliance. It rests on an `invalid_request` event whose text says "request timed out"; the adversary walked every permanent branch the vendor actually emits and found no text that matches _TRANSIENT_CAUSE_RE, i.e. the probe may be a synthesised shape the CLI cannot produce — the exact defect rounds 2 and 3 rejected the build for. Settle this against the binary before treating it as a defect to fix. - Nits, non-gating: residue is computed over both artifacts but printed only on the patch.diff branch (leaves.py:1861, :1870); the top-level `error` key in _claude_result_texts is unreachable against the real result schema and survives mutation (progress.py:603) — same "a branch that looks like coverage and is not" already removed once; the drain hot path now parses each line up to 4x (progress.py:182-194). Open §6 items carry forward UNCLEARED — none was ticked at this sign-off: - T1 / code-review: the attempt-blind harvest boundary (see seam 3). - T5: rebase/ownership order against open PR #524 (same base SHA, same post-_format_leaf_attempt boundary). Still to be decided at publish time. - Validation: the stream fixture is derived from the shipped binary and a pinned incident record, not observed from a live mid-response connection death. Standing since round 2; a limit of the environment, not an untried option. - The plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not by failure. Note the C5 gate row is a vacuous pass ("patch adds no new test file — nothing to assert") and supports no production-path claim; both advisory lenses checked the substance separately and it holds.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on SLICING, not on the mechanism. The core is sound and has survived four
  rounds of independent attack — red->green reproduced every round through the real
  subprocess path, 1780 template tests green, 9/13 and 16/16 mutations of the
  load-bearing hunks caught, the vendor contract re-derived from the shipped binary.
  KEEP ALL OF IT. Each round also genuinely closed the previous round's defects. The
  problem is that the findings have been implementation-shaped in all four rounds, which
  is what an oversized slice produces: 92 KB against the 80 KB backstop, round 4 against
  a 3-round threshold. Do not rebuild this as one slice again — split it in Plan.

  Proposed seams (author the briefs at the split; the sizing.json currently claims one
  indivisible outcome, which is the judgement being overridden here):

    1. STREAM-SIDE classification + retention, in progress.py: read the CLI's own
       terminal error event, classify transient by the marker/kind/status the vendor
       sets, keep the text so it reaches the leaf's *.error.log. This is criteria
       (i) and (iii). Self-contained and independently testable against the pinned
       fixture.
    2. DO-SIDE resilience, in leaves.py: put do_build on _invoke_leaf_resilient with
       the retry note, the _has_content guard, the per-attempt _write_attempt_records
       flush, and the _transient_do_death exhausted-retry message. This is criteria
       (ii) and (iv). Depends on 1 but is a distinct outcome.
    3. Optional third: the reviewer/advisory attempt-blind harvest, already deferred
       twice and measured at ~34 lines across two files in build-notes.md:197-206.
       File it as its own issue rather than deferring it a third time.

  Carry into the child briefs, unresolved this round:

    - Adversary finding A (progress.py:188-191, :405, :625-636): the "the CLI recovered"
      clearing rule is scope-blind — one trailing SUB-AGENT line restores the pre-fix
      outcome exactly (transient=False, 1 invocation, "(no output captured)"), so
      criteria (i) and (iii) both fail with the suite green. Containment is one line:
      require the clearing event to be main-session (parent_tool_use_id null/absent).
      The adversary could not establish the ordering in the wild; the gap is cheap to
      close regardless.
    - Adversary finding B (progress.py:580): stickiness is documented over the `result`
      wrap-up but implemented over any later report, so a SECOND marked api-error report
      is swallowed — a permanent 400 following a dropped connection is neither retained
      nor read, and costs 3 spawns. Containment is one line: stick only against a
      `result` event, let a later marked report overwrite. Already self-disclosed as a
      known trade-off in build-notes.md; close it rather than re-disclose it.
    - The reviewer's C3/T3 FAIL needs adjudication, not compliance. It rests on an
      `invalid_request` event whose text says "request timed out"; the adversary walked
      every permanent branch the vendor actually emits and found no text that matches
      _TRANSIENT_CAUSE_RE, i.e. the probe may be a synthesised shape the CLI cannot
      produce — the exact defect rounds 2 and 3 rejected the build for. Settle this
      against the binary before treating it as a defect to fix.
    - Nits, non-gating: residue is computed over both artifacts but printed only on the
      patch.diff branch (leaves.py:1861, :1870); the top-level `error` key in
      _claude_result_texts is unreachable against the real result schema and survives
      mutation (progress.py:603) — same "a branch that looks like coverage and is not"
      already removed once; the drain hot path now parses each line up to 4x
      (progress.py:182-194).

  Open §6 items carry forward UNCLEARED — none was ticked at this sign-off:
    - T1 / code-review: the attempt-blind harvest boundary (see seam 3).
    - T5: rebase/ownership order against open PR #524 (same base SHA, same
      post-_format_leaf_attempt boundary). Still to be decided at publish time.
    - Validation: the stream fixture is derived from the shipped binary and a pinned
      incident record, not observed from a live mid-response connection death. Standing
      since round 2; a limit of the environment, not an untried option.
    - The plan-advisory leaf produced no verdict by configuration (commit 319eb4d), not
      by failure.

  Note the C5 gate row is a vacuous pass ("patch adds no new test file — nothing to
  assert") and supports no production-path claim; both advisory lenses checked the
  substance separately and it holds.
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
