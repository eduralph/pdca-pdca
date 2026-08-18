# Brief — issue 533 / a-leafs-own-terminal-error-is-kept-and-read

> Re-planned after round 3 was returned `iterate-plan` at sign-off (see
> `iteration-v3/SUMMARY.md` §9). The round-3 **mechanism was not rejected** — the reviewer
> returned PASS on all ten cells and the adversary independently reproduced 30/34 red →
> 34/34 green on the real spawn path, re-deriving the vendor claims from the shipped
> `claude-code 2.1.233` binary. It came back for two reasons: the boundary with sibling
> #532 was being re-cut in the same session, and the slice measured **99 KB against the
> 80 KB backstop** (`progress.py` +462 lines on a 505-line module) with implementation-shaped
> findings three rounds running. This brief is therefore authored to be **split** — see
> `split-proposal.md` in this bundle.

- **Slug:** a-leafs-own-terminal-error-is-kept-and-read
- **Defect:** `progress.run_with_heartbeat` already reads every event a leaf's stream emits
  and throws away the one line that explains a death; and what the harness calls a
  "transient" death is decided by a proxy that is wrong for exactly the sessions where an
  attempt is most expensive. Four facts, each re-verified against the target base
  (`eduralph/pdca-harness` @ `main`, `acb214a`) while this brief was written:
  * **The stream's own error text is discarded.** The drain parses stdout for a session flag
    and a tool label and keeps nothing else (`progress.py:150-159`); what it retains is a
    bounded **stderr** tail (`:143`, `:162-168`), and with `capture` off `output` is that
    stderr tail alone (`:255`, `:257`). The CLI's API-error line arrives as a stream *text*
    event on **stdout**, so it is displayed and dropped, and `_format_leaf_attempt`
    (`leaves.py:724-730`) falls back to `(no output captured)` at `:729` — verbatim what the
    reported incident's `build.error.log` contained. The cause was legible only in the CLI's
    own session transcript under `~/.claude/projects/`.
  * **The transient signal cannot see it.** A failure is classified transient only when the
    child produced **no** substantive stream event (`progress.py:154-155`, `_is_session_event`
    at `:359`/`:365`; `LeafError.transient` is literally `return not self.produced`,
    `leaves.py:104-107`). "Produced anything?" is a *proxy* for "died at invocation", and the
    proxy fails for the long sessions: the incident's 18-minute builder did plenty of work and
    then died of an API connection drop, so it was classified substantive — correctly by that
    rule, wrongly for that cause. The module's own docstring (`progress.py:61`) already records
    that the CLI emits `system`/`api_retry` on a **retryable** API error; the **terminal**
    report is the case with no reader.
  * **The same proxy files a signal kill as transient infra.** `transient` is `not produced`
    with no notion of *how* the child died, so a leaf SIGKILLed **before** its first
    substantive event — the `leaf_memory_max` cap (#420), an OOM killer, a Ctrl-C — is
    classified transient and re-run for the full attempt budget. A capped leaf buys three more
    OOMs. Measured on the base by round 3's adversary through `_invoke_leaf_resilient`:
    `LeafError(returncode=-9).transient is True`, run 3 times; the wrapper spelling
    (`rc=137`, no stream events) likewise. This is the concrete instance of the #510 boundary,
    and it gets **worse** the moment sibling #537 puts the builder on the resilient path.
  * **The definition is restated in six places, and they do not agree.** `LeafError`'s
    docstring (`leaves.py:90-107`), the `_invoke` fallback comment (`:661-670`), the retry
    print (`:717`), `_FAIL_TRANSIENT` (`:2529`), `_failure_class` (`:2534-2549`),
    `_unavailable_classification` (`:2573-2600`), the reviewer call-site comment (`:2505`),
    plus `assemble.py:80` (`LEAF_STATUS_INFRA`, "ran, died with no output — a transient blip")
    and — the one the operator actually reads — `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` at
    `assemble.py:85`: **"leaf did not run (transient infra — safe to re-run)"**, the string
    `assemble.py:168` prefixes onto every §6 row for an infra-empty placeholder. Widening what
    "transient" means makes that string false for the headline case — an 18-minute leaf that
    ran, at length. `template/tests/test_leaf_status.py:135,188` pin the stale string, so the
    suite cannot catch the drift.
- **Success criterion:** With the patch:
  (i) **Retention, unconditionally.** A leaf whose stream carried the CLI's **own marked
  terminal error report** has that report's text in its `*.error.log`, by the same route the
  stderr tail takes — for **every** marked report, whatever its cause and whether or not the
  session recovered from it — and a report the CLI forwarded for a **sub-agent** is retained
  *labelled as such*, never passed off as the leaf's own death. A post-mortem explains the
  failure without opening `~/.claude/projects/`.
  (ii) **Classification by cause, not by silence.** Such a leaf is classified **transient**
  when the vendor marked its cause transient (a lost or interrupted connection, an overload
  or 5xx, a mid-session rate-limit rejection), however much work came first; and is **not**
  when the vendor marked it permanent (invalid request, authentication, billing) — no prose
  inside a marked report may promote it — nor when a leaf merely mentions or quotes an error,
  nor when the CLI **recovered** and real **main-session** work followed, nor when it failed
  substantively.
  (iii) **A signal kill is not transient infra.** A leaf a signal killed is not retried on the
  strength of having emitted nothing — in **both** returncode spellings (`-signum` from a
  direct child, the shell's `128+signum` from a wrapper argv).
  (iv) **One definition, stated truthfully everywhere.** Every site that restates what a
  transient leaf death is — including the operator-facing `_LEAF_STATUS_LABEL` string — says
  the same true thing, covering both shapes (produced nothing at all, **or** ended on its own
  marked transient report) and asserting neither "did not run" of a leaf that ran nor
  "no output" of a leaf that explained itself.
  (v) **Nothing else changes:** a stream-less family still reports substantive
  (`leaves.py:661-670`), `capture` still returns the child's raw stdout unmodified, the
  codex/gemini stream formats degrade to today's behaviour, a leaf that succeeds is spawned
  and reported exactly as today, and the memory-telemetry post-mortem (#420, `leaves.py:665`)
  still rides `output` into the same log.
  Demonstrable by C4-verify offline: a stub "leaf" that is a Python interpreter emitting
  chosen stream events and exiting non-zero, driven both through `progress.run_with_heartbeat`
  directly and through `leaves._invoke_leaf_resilient` (the reviewer/advisory path, resilient
  on **any** base), so every clause is an assertion over an invocation counter and the error
  log's bytes.
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:26-40` ships the harness shape to copy:
  `_SUBSTANTIVE` emits one `{"type": "assistant"}` event and then fails, and the suite asserts
  it is **not** retried — precisely the rule the incident falls foul of. A stub leaf that emits
  a work event, **then** the CLI's marked terminal error report, then exits non-zero is the new
  posture: today it is retried 0 times and its error log reads `(no output captured)`, so both
  assertions fail pre-fix. For (iii), a stub that emits **nothing** and dies of `SIGKILL` is
  run **3** times today. Patch the retry backoff from the test so red→green costs no wall-clock
  (`test_leaf_resilience.py:58` passes `attempts=3, backoff=0.0` — mirror that).
  **Two gate-shaped traps, both re-measured against this instance's C4 gate:**
  * `engine/scripts/run-verify.sh:131-137` classifies a changed path as a *test* only when it
    matches `tests/*.py` / `template/tests/*.py`, and as non-behavioural for `*.md`. A
    **fixture** (`…/fixtures/*.jsonl`) therefore classifies **production** and is **reverted on
    the red leg** (`:214-217`), so a case that only replays a fixture goes red because the file
    is gone — a vacuous red. At least one case per criterion must construct its events
    **inline in the test module**, and a fixture-replaying case must `skipTest` (not error)
    when its fixture is absent.
  * The red leg keeps every `template/tests/*.py` hunk, so a **new** test file earns a real red
    — provided it imports no symbol this patch adds at module level: a red-leg import failure
    is recorded `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:231-233`). Exercise everything
    through pre-existing API (`progress.run_with_heartbeat`, `leaves._invoke_leaf_resilient`).
    A **new** file is also what C5 keys on — `engine/scripts/run-prod-path.py:88-90` prints
    "patch adds no new test file — nothing to assert" for an append.
- **Invariant to restore:** **A failure is classified by what actually happened, and the
  evidence of it is kept.** Two halves, stated over the category rather than one API string:
  the harness must read the leaf's **own account** of its death out of the stream it is already
  parsing — never infer a cause from prose it was not given, never *promote* a cause the vendor
  marked permanent, and never file silence as a diagnosis — and it must **retain** that account
  in the artifact the cycle preserves. "Produced no output" is a proxy for "died at invocation"
  that fails for every long session and for every signal kill; and "no evidence" must never be
  filed as a verdict. Self-test: it cannot be satisfied by guarding a single module — the
  classification lives in the stream reader, the retention in what `output` carries, and the
  definition is restated in six places downstream that go stale the moment it widens. Source:
  internal project invariant (Tier C), the target's own written rules — `progress.py:55-64`
  (what the transient signal is for, and that a *retryable* API error is already named there
  and excluded from "produced"), `leaves.py:641-647` (`(no output captured)` is "a post-mortem
  artifact that explains nothing", #286 review), `engine/README.md:44-68` (no evidence must
  never be filed as a verdict). `docs/principles.md` §5/§6 are unfilled scaffolds in this
  instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `acb214a`)
- **Ordering note:** **No machine ordering field is set on this parent deliberately.** It is
  being closed `split`; its two children carry the real edges, and an edge added to a bundle
  the run is mid-drive on is needless risk. The boundary that matters is with sibling #532's
  children, which are live in this same run: **#536** owns `_invoke_leaf_resilient`'s loop
  **body** (it moves the `write_text` at `leaves.py:720` into the loop), `_format_leaf_attempt`
  (`:724-730`), the three artifact harvests (`:2519-2523`, `:2851-2854`, `:3152-3155`) and the
  #369 recovery discriminators; **#537** (`Depends on: 536`) owns `_do_build_command` (`:1824`),
  `do_build` (`:1747-1778`), `_build_prompt` (`:1834`) and the `_invoke` call at `:707`. Both
  briefs explicitly reserve `progress.py`, `LeafError.transient` and *any signal-death
  predicate* to this issue, and #536 records that "#533 owns the **strings and comments** in
  that function". So this slice's `leaves.py` reach is **strings, comments and the `transient`
  property only** — never a structural edit to that loop — and the child that touches
  `leaves.py` declares `Conflicts with: 536, 537` (not `Depends on`: `waves.check_dep_graph`
  aborts the whole run on a prereq that is neither in-batch nor COMPLETE, while an out-of-batch
  conflict is dropped as moot, `waves.py:104-109`). Recommended publish order: 536 → 537 →
  this issue's children.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** What a leaf's death *is*, and what survives it, on the spawn path every leaf
  shares: read the CLI's own marked terminal error report out of the stream the driver already
  parses; keep that text so it reaches the leaf's `*.error.log` by the route the stderr tail
  already takes; decide "transient" from the cause the **vendor** marked (and from how the
  child actually died) rather than from whether it happened to say anything; and make every
  site that restates that definition — the operator-facing label included — say the same true
  thing. **Out of scope:** who is retried and what a retry may inherit — the builder is **not**
  put on the resilient path here, and `_invoke_leaf_resilient`'s **body**, `do_build`,
  `_build_prompt` and the artifact harvests are #536/#537's; resuming a long session via the
  CLI's own session-resume (a fresh re-invoke is the accepted first cut — say so in
  `build-notes.md` so the human can weigh it); the gate-side transient (issue #371); issue
  #510's own remedy beyond the narrow "a signal kill is not transient infra" rule above; any
  new `pdca.toml` knob.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness, `acb214a`), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today. Read
     `:26-40` and `:58`: `_SUBSTANTIVE` emits one stream event, then fails, and the suite
     asserts it is **not** retried. That is the rule the incident falls foul of.
  2. Read the drop: `progress.py:150-159` (stdout parsed for a session flag and a tool label,
     then discarded), `:143` + `:162-168` (the bounded **stderr** tail), `:255`/`:257`
     (`output` is that stderr tail when `capture` is off), `leaves.py:104-107`
     (`transient` is `not produced`), `leaves.py:729` (the `(no output captured)` fallback the
     incident's log shows verbatim).
  3. Read what the module already knows and does not use: `progress.py:55-64` (claude emits
     `system`/`api_retry` on a **retryable** API error — deliberately excluded from "produced")
     and `_SESSION_EVENT_TYPES` (`:359`).
  4. Read the stale restatements: `assemble.py:80` and `:85`, `leaves.py:2529`, `:2534-2549`,
     `:2573-2600`, `:2505`; and `test_leaf_status.py:84,135,188`, which pin them.
  5. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`); the identical argv re-run minutes later
     succeeded.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a stub
  "leaf" that is a Python interpreter, so the slice builds and goes red→green with no vendor
  CLI, no API key, no network and no container. (Grounding the event shape against the vendor
  is a *reading* step, not a build or verification input — see Citations expected.)
- **Test file:** `template/tests/test_terminal_error_classification.py` (**new**), plus
  `template/tests/fixtures/` for the pinned vendor records and their provenance note. Do **not**
  append to `template/tests/test_leaf_resilience.py` and do **not** edit
  `template/tests/test_build_error_log.py` or `template/tests/test_attempt_ownership.py` /
  `test_builder_retry.py`: #536/#537 own those and build in the same run.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `progress._is_session_event` (`:365-377`) is the existing per-family stream classifier: it
    dispatches on `stream_format`, parses JSON best-effort and defaults to `False`. A
    terminal-error reader belongs **beside it, in the same shape**, so the codex/gemini formats
    degrade to today's behaviour instead of guessing;
  * `:143` + `:162-168` show how a bounded tail is kept (`deque(maxlen=…)`) and `:255` how it
    becomes `output` — the retained report should reach `LeafError.output` by that same route,
    so `_format_leaf_attempt` (`leaves.py:724-730`, **#536's**) needs no special case and this
    slice need not touch it;
  * `leaves.py:661-670` documents why a stream-less family reports `produced=True`; keep that
    fallback intact.
  * **Vendor grounding is the standard this slice is held to.** Two of parent #506's four
    rejected rounds were rejected for asserting an event shape the CLI cannot emit. Establish
    the shape from the installed `claude` CLI and/or a real session transcript under
    `~/.claude/projects/`, and record next to the fixture which claims are **observed** and
    which are **derived**.
  * **Prior art you may read, selectively:** round 3's patch is archived at
    `results/issue_533/iteration-v3/patch.diff` (+ `build-notes.md`, `SUMMARY.md`). Its
    mechanism was confirmed by both the reviewer and the adversary and it was returned for
    **slice size and the #532 boundary, not for approach** — re-verify what you take, and do
    not rebuild its six known-open items, which are enumerated per child in
    `split-proposal.md`.

  **Path convention in this brief:** every `template/…` and `tests/…` path is on the **target
  branch** (eduralph/pdca-harness @ main) — the files Do reads and edits. Every `engine/…`,
  `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification engine
  and the bundles that run the cycle); they are cited to explain how the gates will judge the
  patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/progress.py` — `0881af9` (#420 memory sampling), `4091b94`
  (straggler sweep), `228e80b` (#368 timeouts), `49f6611` (#286, "capture a stream-less leaf's
  stderr too"): the closest relative, and it extended **stderr** capture — the stream's own
  events were never read. Open PRs on the target (`gh pr list -R eduralph/pdca-harness --state
  open`): #519-#525; none touches `progress.py`, and the two that touch `leaves.py` (#524 issue
  494, #520 issue 466) are at distant regions. Open issues searched for `transient`: #371
  (gate-row transient red) is deliberately excluded; #510 (signal death) is the boundary
  criterion (iii) settles narrowly; #509 (crash-resume) is a different beat. Attempted once as
  this slice (round 3, `iteration-v3/`) and returned on slicing, never on mechanism; parent
  #506's four-round attempt was likewise returned on slicing.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
