<!-- pdca:split-proposal v1 -->
# Split proposal — issue 533

## Why this slice is oversized

Round 3 shipped a patch the reviewer PASSed on all ten cells and the adversary independently
re-verified (30/34 red → 34/34 green on the real spawn path, vendor claims re-derived from the
shipped `claude-code 2.1.233` binary). It was still returned at sign-off, and the measurement
says why: **99 KB against the 80 KB backstop**, of which `progress.py` alone is **+462 lines on
a 505-line module** — the change nearly doubles the module it lands in, adding eleven top-level
functions in one diff. Three rounds produced implementation-shaped findings every time, and
round 3 still closed with six open items. That is the signature of a slice carrying more than
one outcome, not of a builder having a bad run.

The brief's own invariant already names the seam: *"a failure is classified by what actually
happened, **and** the evidence of it is kept."* Those are two outcomes, and they separate
cleanly:

* **Keeping the evidence** needs only the vendor's *marker* — "this message is my API-error
  report" — plus enough scoping to say whose death it describes (main session vs a forwarded
  sub-agent report) and which of several records is nearest it. It needs **no** notion of
  transient vs permanent, touches **one file**, and changes **no** classification: the same leaf
  is retried exactly as many times after it as before. It is independently valuable — it is the
  whole first half of the issue title, and it retires `(no output captured)` for the reported
  incident on its own.
* **Deciding the verdict** needs the vendor's *kinds* and statuses, the "the CLI recovered"
  clearing rule, the signal-death boundary (#510), and — because widening the definition makes
  six downstream restatements false, one of them the operator-facing §6 string — the truthful
  re-statement of that definition across two modules and a pinned test suite.

The second genuinely builds on the first: it classifies **off the record the first one retains**.
Cutting here also *dissolves* one of round 3's six open items outright — the complaint that the
clearing rule discarded the retained text along with the verdict cannot arise once retention is
unconditional and lives in a slice that has no verdict to clear. Every other carry-forward item
lands in exactly one child.

Two children, not three: the signal-death rule (#510's narrow half) is folded into child-2
rather than split out, because it is the *same predicate* — `LeafError.transient` — and the
*same* six restatement sites. Splitting it out would buy a third full cycle to change one
boolean and re-word the same prose twice.

**On the convergence report.** It scores `difficulty=high` + `brief ≥ 12 KB` only
(`sizing.py:332-361`), a rule its own docstring rates at 55% precision. Both children are now
under the brief cutoff, and child-1 is `medium` because blast-radius — the field's actual
definition — is one file, additively, with no control-flow change; its *reasoning* depth is
vendor grounding, which is what the `Do model:` pin is for. The measure that actually returned
this bundle is patch KB, and the round-3 material each child inherits is ~40 KB and ~35 KB
against the 80 KB backstop.

## Wave sketch

`child-1` is **independent** and touches exactly one production file,
`template/src/pdca_harness/progress.py` — which sibling bundles **#536** and **#537** (issue
#532's children, live in this same run) both explicitly declare out of scope. So child-1 shares
a wave with them and runs in parallel.

`child-2` **`Depends on: child-1`** — not merge hygiene, but substance: it classifies off the
record child-1 retains, and the fold is what puts that record on its base.

`child-2` additionally conflicts with **#536** and **#537** on `leaves.py`: it rewrites the retry
print at `leaves.py:717`, three lines from the `write_text` at `:720` that #536 moves into the
loop, and `_failure_class` at `:2534` sits ten lines below #536's harvest at `:2519-2523`. That
edge is `Conflicts with: 536, 537`, **added to the materialised brief, not declared here** —
a proposal's ordering fields may only name sibling labels (`split.py:305-320`), and
`Conflicts with` is the safe cross-bundle form: an out-of-batch conflict is dropped as moot
(`waves.py:104-109`), whereas a `Depends on` naming a bundle that is neither in-batch nor
COMPLETE aborts the entire run (`waves.py:70-80`).

Resulting schedule, conflict pairs oriented name-lower-first (`waves.py:165-175`): **wave k** =
`child-1` ‖ #536 · **wave k+1** = #537 · **wave k+2** = `child-2`. That matches the publish order
#537's brief already recommends: 536 → 537 → #533's children. Being wave ≥ 2, `child-2` should
expect one **false advisory T3 red** from this instance's own #474 (`PDCA_VERIFY_BASE` leak,
`wave_mode = "stack"`, `pdca.toml:122`); T3 is `gating = false` and the gating C4 row is
unaffected.

<!-- pdca:child child-1 -->
- **Slug:** a-leafs-own-account-of-its-death-is-kept
- **Defect / goal:** `progress.run_with_heartbeat` reads every event a leaf's stream emits and
  keeps none of it. The drain parses stdout for a session flag and a tool label, then discards
  the line (`progress.py:150-159`); what it retains is a bounded **stderr** tail (`:143`,
  `:162-168`), and with `capture` off `output` is that stderr tail alone (`:255`, `:257`). The
  CLI's own API-error report arrives as a stream *text* event on **stdout**, so it is displayed
  and dropped, and `_format_leaf_attempt` falls back to `(no output captured)` (`leaves.py:729`)
  — verbatim what the reported incident's `build.error.log` contained. The cause of an 18-minute
  death was legible only in the CLI's session transcript under `~/.claude/projects/`, which no
  post-mortem reads. `leaves.py:641-647` already states the rule this breaks: `(no output
  captured)` is "a post-mortem artifact that explains nothing".
- **Success criterion:** With the patch: (i) when a leaf's stream carried the CLI's **own marked
  terminal error report** — the message the vendor itself flags as its API-error report — that
  text is in the leaf's `*.error.log`, reaching it by the same route the stderr tail takes
  (appended to what `run_with_heartbeat` returns as `output`), so a post-mortem explains the
  failure without opening `~/.claude/projects/`; (ii) retention is **unconditional** — every
  marked report is kept whatever its cause, *including* one the session then recovered from,
  because a harness holding the text must never file `(no output captured)`; (iii) a report the
  CLI forwarded for a **sub-agent** (the Task's `parent_tool_use_id`, or `isSidechain` in the
  persisted-transcript spelling) is kept **labelled as such**, never presented as the leaf's own
  death — a log that confidently names the wrong death is worse than the silence it replaces;
  (iv) where a stream carries several candidate records, the one nearest the leaf's own death
  wins and a farther one (a `result` wrap-up naming only the effect, a sub-agent's report) cannot
  bury it, in either arrival order; (v) **nothing is classified** — `produced`,
  `LeafError.transient` and the retry counts are byte-identical to today for every input: a leaf
  retried 3 times today is retried 3 times after this, and one retried 0 times still is;
  (vi) nothing else changes — `capture` still returns the child's raw stdout unmodified (confirm
  the appended text cannot leak into a gate's evidence line: every other `run_with_heartbeat`
  caller passes `capture=True` — `gates.py:559`, `publish.py:833`, `leaves.py:767`), the
  codex/gemini stream formats degrade to today's behaviour, a stream-less family is untouched, a
  leaf that exits 0 is spawned and reported exactly as today, and the #420 memory-telemetry
  post-mortem (`leaves.py:663-666`) still rides `output` into the same log.
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python ≥ 3.11
  + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:26-40` ships the harness shape to **copy** (do not
  import across modules): a stub "leaf" whose argv is `[sys.executable, "-c", script]`, emitting
  chosen stream events on stdout and exiting non-zero, plus a `$CNT` file counting invocations;
  `:58` shows the `attempts=3, backoff=0.0` spelling that keeps the suite fast. Drive it through
  `leaves._invoke_leaf_resilient` (resilient on **any** base, so no dependency on #537) and
  through `progress.run_with_heartbeat` directly. Today a leaf that emits a work event, then the
  CLI's marked report, then exits 1 with empty stderr writes an error log reading
  `----- attempt 1 — exit 1 -----` / `(no output captured) LeafError: …`, so every retention
  assertion fails pre-fix. That is the red. (v) is a guard, green on both legs by design: assert
  the invocation counts explicitly so a later change cannot silently move them.
  **Two gate traps, measured against this instance's C4 gate.** `run-verify.sh:131-137` counts
  only `tests/*.py` / `template/tests/*.py` as tests and `*.md` as non-behavioural, so a
  `…/fixtures/*.jsonl` is **production** and is reverted on the red leg (`:214-217`): a case that
  only replays a fixture goes red because the file is *gone* — a vacuous red. Construct at least
  one case per criterion **inline in the test module**, and make any fixture-replaying case
  `skipTest` (not error) when its fixture is absent. Second: the red leg keeps every
  `template/tests/*.py` hunk, so a **new** test file earns a genuine red *provided it imports no
  symbol this patch adds at module level* — a red-leg import failure is recorded
  `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:231-233`). Import only pre-existing API
  (`from pdca_harness import progress, leaves`) and assert behaviourally.
- **Invariant to restore:** **The evidence of a failure is kept** — the retention half of "a
  failure is classified by what actually happened, and the evidence of it is kept". Stated over
  the category, not this incident: when the harness is already reading a child's own account of
  its death, it must retain that account in the artifact the cycle preserves, and must never
  attribute it to a death it does not describe. "No evidence" must never be filed as a verdict.
  Self-test: it cannot be met by guarding a single module — the reading happens in the stream
  drain, the keeping in what `output` carries, and the consumer is every `*.error.log` the harness
  writes. Source: internal project invariant (Tier C), the target's own written rules —
  `leaves.py:641-647` (`(no output captured)` is "a post-mortem artifact that explains nothing",
  #286 review), `progress.py:55-64`, `engine/README.md:44-68`. `docs/principles.md` §5/§6 are
  unfilled scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `acb214a`; every `path:line` here
  was re-verified against it while this proposal was written)
- **Reproduction:** On a clean checkout of the target base, offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today; read
     `:26-40` and `:58` for the stub-leaf harness, the `$CNT` counter and the fast-backoff
     spelling to copy.
  2. Read the drop at the lines cited in Defect above, plus `leaves.py:724-730` (the record
     format), and what the module already knows but does not use: `progress.py:55-64` and
     `_is_session_event` at `:359`/`:365-377`.
  3. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`); an identical argv re-run minutes later succeeded.
- **Scope (one logical fix) / out of scope:** Read the CLI's own marked terminal error report out
  of the stream the drain already parses, decide **whose** death it describes and **which** record
  is nearest it, and keep that text so it reaches the leaf's `*.error.log` by the route the stderr
  tail already takes. **This child touches exactly one production file,
  `template/src/pdca_harness/progress.py`**, plus its own new test file and
  `template/tests/fixtures/`. **Out of scope — load-bearing, because three sibling bundles are
  live in the same run:** do **not** change `produced`, do **not** touch `LeafError.transient`
  (`leaves.py:104-107`), do **not** add a signal-death predicate, and do **not** add any notion of
  transient-vs-permanent cause, vendor error *kinds*, HTTP statuses, or a "the CLI recovered"
  clearing rule — that is child-2, which builds on this. Do **not** edit `leaves.py` or
  `assemble.py` **at all**: `_invoke_leaf_resilient`'s loop body, `_format_leaf_attempt`
  (`:724-730`) and the artifact harvests are #536's, `do_build` / `_build_prompt` /
  `_do_build_command` are #537's, and the prose restatements are child-2's. Also out: resuming a
  long session via the CLI's own session-resume; the gate-side transient (#371); issue #510; any
  new `pdca.toml` knob.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a stub
  "leaf" that is a Python interpreter, so this builds and goes red→green with no vendor CLI, no
  API key, no network and no container. Grounding the event shape against the vendor is a
  *reading* step, not a build or verification input.
- **Test file:** `template/tests/test_terminal_error_retention.py` (**new**), plus
  `template/tests/fixtures/` for the pinned vendor records and a provenance note scoped to the
  claims THIS child depends on (the marker, the sub-agent spelling); child-2 appends its
  kind/status provenance to the same note on its own base. A **new** file, not an append:
  `engine/scripts/run-prod-path.py:88-90` keys C5 on *newly added* test files and prints "patch
  adds no new test file — nothing to assert" for an append. Do **not** touch
  `test_leaf_resilience.py`, `test_build_error_log.py`, `test_attempt_ownership.py` or
  `test_builder_retry.py` — the last three are #536/#537's, building in this same run, and a
  shared test file is the one place the patches would collide.
- **Difficulty:** medium — blast-radius is one production file, additive, no control-flow or
  classification change; beyond it a diff-reviewer holds the four `run_with_heartbeat` call sites
  and the #420 telemetry append. The *reasoning* depth here is vendor grounding, not reach — hence
  the `Do model` pin rather than a `high` tag.
- **Do model:** opus
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues: `progress._is_session_event` (`:365-377`) is the existing per-family stream
  classifier — it dispatches on `stream_format`, parses JSON best-effort and defaults to `False`.
  The terminal-report reader belongs **beside it, in the same shape**, so codex/gemini degrade to
  today's behaviour instead of guessing. `:143` + `:162-168` show how a bounded tail is kept
  (`deque(maxlen=…)`) and `:255` how it becomes `output` — the retained report must reach
  `LeafError.output` by that same route, so `_format_leaf_attempt` (#536's file) needs no special
  case and this child need not touch it. `leaves.py:663-666` is the one existing precedent for
  appending to `output` on a failure (the #420 post-mortem) — mirror it rather than inventing a
  second shape. **Vendor grounding is the standard here:** two of parent #506's four rejected
  rounds were rejected for asserting an event shape the CLI cannot emit, and the round that held
  re-derived it from the shipped binary. Establish the marker and the sub-agent spelling from the
  installed `claude` CLI and/or a real transcript under `~/.claude/projects/`, and record beside
  the fixture which claims are **observed** and which **derived**. **Prior art, read selectively:**
  round 3's patch is archived at `results/issue_533/iteration-v3/patch.diff` (+ `build-notes.md`,
  `SUMMARY.md`); its mechanism was confirmed by reviewer and adversary and it was returned for
  slice size and the #532 boundary, **not** for approach. Read only its retention-side hunks — the
  matcher anchored on the vendor's own flag, `_is_subagent_event` used as the single predicate so
  the stream and persisted-transcript spellings cannot drift apart, the record-precedence table,
  the bounded report line. Re-verify what you take against the current base. Do **not** carry its
  classification hunks (kind sets, clearing rule, signal-death predicate) — that would recreate
  the oversized slice this split exists to undo.
- **Prior-art check (triage cycles):** By file path on `origin/main`: `progress.py` — `0881af9`
  (#420), `4091b94` (straggler sweep), `228e80b` (#368), `49f6611` (#286, "capture a stream-less
  leaf's stderr too"): the closest relative, and it extended **stderr** capture — the stream's own
  events have never been read for anything but a tool label. Open PRs #519-#525: none touches
  `progress.py`. Open issues searched for `transient`: #371 and #510 are adjacent and deliberately
  excluded, #509 is a different beat. Not previously attempted as its own slice; #533's round 3
  and parent #506's four rounds were returned on slicing, never on mechanism.
- **Disposition hint:** likely-fix
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** what-a-transient-leaf-death-is-decided-once
- **Defect / goal:** What the harness calls a "transient" death is decided by a proxy —
  `LeafError.transient` is literally `return not self.produced` (`leaves.py:104-107`), where
  `produced` means "a substantive stream event arrived" (`progress.py:154-155`, `:257`). "Did it
  say anything?" stands in for "did it die at invocation?", and the proxy is wrong in both
  directions, on the path every leaf shares. **It refuses to retry pure infrastructure:** the
  reported incident's 18-minute builder did plenty of work and *then* lost its API connection, so
  it was classified substantive and a full cycle round was burned; an identical re-run minutes
  later succeeded (`progress.py:61` already records that the CLI emits `system`/`api_retry` on a
  **retryable** API error — the **terminal** report has no reader). **And it retries a death that
  will repeat identically:** a leaf a signal killed *before* its first substantive event is
  `produced=False`, hence transient, hence re-run for the whole attempt budget — so a leaf the
  `leaf_memory_max` cap (#420) OOM-kills buys three more OOMs. Measured on the base through
  `_invoke_leaf_resilient`: `LeafError(returncode=-9).transient is True`, run 3 times; the wrapper
  spelling (`rc=137`, no stream events) likewise. That is the concrete instance of the #510
  boundary, and it worsens the moment sibling #537 puts the builder on the resilient path.
  **Meanwhile the definition is restated in six places that do not agree**, and widening it makes
  them false: `LeafError`'s docstring (`leaves.py:90-107`), the `_invoke` fallback comment
  (`:661-670`), the retry print (`:717`, "with no output (transient)"), `_FAIL_TRANSIENT`
  (`:2529`), `_failure_class` (`:2534-2549`), `_unavailable_classification` (`:2573-2600`), the
  reviewer call-site comment (`:2505`), `assemble.py:80` — and, the one the operator actually
  reads, `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` at `assemble.py:85`: **"leaf did not run
  (transient infra — safe to re-run)"**, which `assemble.py:168` prefixes onto every §6 row for an
  infra-empty placeholder. For the headline case that asserts "did not run" of a leaf that ran for
  eighteen minutes, directly above the retained report proving it did.
  `template/tests/test_leaf_status.py:135,188` pin the stale string and `:84` restates it in a
  comment, so the suite cannot catch the drift.
- **Success criterion:** With the patch: (i) a leaf whose stream carried a marked terminal error
  report and then exited non-zero is classified **transient** when the vendor marked the cause
  transient — a lost or interrupted connection, an overload or 5xx, a mid-session rate-limit
  rejection — **however much work came first**; (ii) it is **not** so classified when the vendor
  marked the cause **permanent** (invalid request, authentication, billing), nor for a kind this
  harness does not recognise, nor for a report the vendor left **unstamped** — no prose inside a
  marked report may promote a permanent cause, and a leaf that merely mentions or quotes an error
  is untouched; a report the CLI **recovered** from, with real **main-session** work following, is
  not the leaf's death; and a **sub-agent's** report never classifies (the CLI has its own
  recovery for those); (iii) a leaf a **signal** killed is never classified transient on the
  strength of having emitted nothing — in **both** returncode spellings, `-signum` from a direct
  child and the shell's `128+signum` from a wrapper argv — so a memory-capped leaf is not re-run
  into the same cap, while the harness's own wall-clock kill (`progress.TIMEOUT_RC`) keeps today's
  meaning; (iv) **every** site that restates the definition states the same true thing, covering
  **both** shapes — a leaf that produced nothing at all, **or** one that ended on its own marked
  transient report — and the operator-facing `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` no longer
  asserts "did not run" of a leaf that ran; `template/tests/test_leaf_status.py` is updated with
  it rather than left pinning the stale string; (v) child-1's retention is **unchanged** — in
  particular the report text is still retained for a report the session recovered from, even
  though this child's clearing rule removes the *verdict*; (vi) nothing else changes: a
  stream-less family still reports substantive (`leaves.py:661-670`), `capture` still returns the
  child's raw stdout unmodified, codex/gemini degrade to today's behaviour, a leaf that succeeds
  is spawned and reported exactly as today, and the #420 post-mortem still rides `output` into the
  same log.
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python ≥ 3.11
  + git, no vendor CLI, no network, no API key — on the folded base carrying child-1's accepted
  result. Copy the stub-leaf harness from `template/tests/test_leaf_resilience.py:26-40` (do not
  import across modules) and the `attempts=3, backoff=0.0` spelling from `:58`; drive through
  `leaves._invoke_leaf_resilient`, resilient on **any** base. Reds available: (i) a stub emitting
  a work event, then a marked transient report, then exit 1 is invoked **1** time and must be
  invoked 3; (iii) a stub emitting **nothing** that dies of `SIGKILL` — and its `rc=137` wrapper
  spelling — is invoked **3** times and must be invoked 1 (`test_leaf_resilience.py:35` is the
  no-stream-event stub to start from); (iv) the assertions at `test_leaf_status.py:135,188` go
  red the moment the string is corrected, so update them **with** the change, not around it.
  **Round 3's three surviving mutations are requirements here**, each a load-bearing guard that
  was unasserted; each must be pinned by a case that fails when the guard is removed: the
  **main-session `user` tool-result** membership of the work-event set (delete it and a leaf that
  recovered through a tool cycle then failed on its own merits flips to retryable — the
  criterion-(ii) inversion — with the whole suite still green; every round-3 clearing case cleared
  with an `assistant` event, which is why it survived); the **transient HTTP-status set** (round
  3's only status-carrying case used 503, decided by the 5xx range, so emptying the set changed
  nothing); and the **`subtype == "success"` guard** on the wrap-up's status field (round 3's
  execution-error case never set the status, so the guard was unreachable — add the status to it,
  keeping it substantive, plus one 429 wrap-up).
  **Two gate traps, measured against this instance's C4 gate.** `run-verify.sh:131-137` counts
  only `tests/*.py` / `template/tests/*.py` as tests and `*.md` as non-behavioural, so a
  `…/fixtures/*.jsonl` is **production**, reverted on the red leg (`:214-217`): a fixture-replaying
  case goes red because the file is *gone* — a vacuous red. Construct at least one case per
  criterion **inline**, and `skipTest` any fixture-replaying case whose fixture is absent. Second:
  a **new** test file earns a genuine red only if it imports no symbol this patch adds at module
  level — a red-leg import failure is recorded `PDCA-UNVERIFIABLE`, not red (`:231-233`) — so
  import only pre-existing API and assert behaviourally. A new file is also what C5 keys on
  (`run-prod-path.py:88-90`).
- **Invariant to restore:** **A failure is classified by what actually happened** — the
  classification half of the parent invariant, with its corollary that a definition restated in
  many places must be restated *truthfully* or not at all. Over the category, not one API string:
  the harness must decide whether to spend another attempt from the leaf's own account of *how it
  died* — the cause the vendor marked, and the manner of the kill — never from whether the child
  happened to speak first, never by promoting a cause the vendor marked permanent, never by
  inferring one from prose it was not given; and no message the harness shows a human about that
  decision may assert something the harness knows to be false. Self-test: it cannot be met by
  guarding a single module — the verdict is computed in the stream reader, exposed as a property
  in `leaves`, consumed by `_failure_class`, and told to the operator by a label in `assemble`.
  Source: internal project invariant (Tier C), the target's own written rules —
  `progress.py:55-64` (what the transient signal is for, and that a *retryable* API error is
  already named there and excluded from "produced"), `leaves.py:683-697` (the #138 resilience
  contract), `assemble.py:76-79` (why the two infra shapes must not be conflated: telling the
  operator "safe to re-run" where it is false "would be a false instruction", PR #285 review),
  `engine/README.md:44-68`. `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so
  no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `acb214a`; every `path:line` here
  was re-verified against it while this proposal was written)
- **Reproduction:** On a clean checkout of the target base — **plus child-1's accepted result,
  which the wave fold gives you** — offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience tests.test_leaf_status -v` —
     green today; read `test_leaf_resilience.py:26-40` for the stub-leaf harness.
  2. Read the proxy and the six restatements at the lines cited in Defect above.
  3. Measure the signal hole first: a stub emitting no stream event and dying of `SIGKILL`,
     driven through `leaves._invoke_leaf_resilient`, is invoked three times.
  4. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`.
- **Scope (one logical fix) / out of scope:** Decide what a transient leaf death **is** — from the
  cause the vendor marked on the record child-1 retains, and from how the child actually died —
  and make every place that restates that definition say the same true thing, the operator-facing
  §6 label included. Files: `progress.py` (classification only), `leaves.py` **strings, comments
  and the `transient` property only**, `assemble.py` (`:80`, `:85`),
  `template/tests/test_leaf_status.py`, the new test file, and the provenance note beside the
  fixtures. **Out of scope — load-bearing, because siblings #536 and #537 are live in the same run
  and both name this issue explicitly:** do **not** make a structural edit to
  `_invoke_leaf_resilient`'s `for attempt` loop — #536 moves the `write_text` at `leaves.py:720`
  into it and #537 varies the `_invoke` call at `:707`; the fold gives you their version, so
  **read the folded loop before touching the print at `:717`**, and change the *string* only. Do
  **not** touch `_format_leaf_attempt` (`:724-730`), the three artifact harvests (`:2519-2523`,
  `:2851-2854`, `:3152-3155`) or the #369 recovery discriminators (#536's), nor `do_build`
  (`:1747-1778`), `_do_build_command` (`:1824`) or `_build_prompt` (`:1834`) (#537's) — putting
  the builder on the retry path is **not** this child's to do, and the fact that #537 makes the
  builder spend this child's retry set is a *consequence* to state in `build-notes.md`, not a
  reason to widen either slice. Do **not** re-author child-1's retention mechanism — read it on
  the folded base and classify off it. Also out: issue #510's remedy beyond criterion (iii)'s
  narrow exclusion; the gate-side transient (#371); resuming a long session via the CLI's own
  session-resume (a fresh re-invoke is the accepted first cut — say so in `build-notes.md`); any
  new `pdca.toml` knob.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a stub
  "leaf" that is a Python interpreter, so this builds and goes red→green with no vendor CLI, no
  API key, no network and no container. Grounding the vendor's error kinds and statuses is a
  *reading* step, not a build or verification input.
- **Test file:** `template/tests/test_terminal_error_classification.py` (**new**) for criteria
  (i)-(iii) and (v); `template/tests/test_leaf_status.py` is **updated** for (iv) — its
  `:135,188` assertions pin the string this child corrects and `:84`'s comment restates it — but
  new assertions belong in the new file. A **new** file, not an append:
  `engine/scripts/run-prod-path.py:88-90` keys C5 on *newly added* test files. Do **not** touch
  `test_leaf_resilience.py`, `test_build_error_log.py`, `test_attempt_ownership.py`,
  `test_builder_retry.py`, or child-1's `test_terminal_error_retention.py`. The C4 gate runs
  **every** test file the patch touches, so `test_leaf_status.py` must be red-worthy and green too.
- **Difficulty:** high — three production modules, two test files and six prose sites, changing a
  definition consumed at four removes: computed in the stream reader, exposed as
  `LeafError.transient`, consumed by `_failure_class`, told to the human by a label in `assemble`.
  A diff-reviewer must hold all of that, the #510 boundary, and the folded loop it edits a string
  inside, in view at once.
- **Depends on:** child-1
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues: `progress._is_session_event` (`:365-377`) is the existing per-family stream
  classifier (dispatch on `stream_format`, best-effort JSON, default `False`) and child-1's report
  reader sits beside it in that shape — the classifier belongs in the same neighbourhood and must
  degrade the same way for codex/gemini. `leaves.py:661-670` documents why a stream-less family
  reports `produced=True`; keep that fallback intact. `assemble.py:76-79` states in the codebase's
  own words why the infra shapes must not be conflated and why a false "safe to re-run" is the
  specific harm — the label correction is that rule applied. `leaves.py:2552-2554` and
  `:2611-2616` already phrase the definition in the two-shape form ("produced no substantive
  output, **or** …") and are the model the other sites should match. **Vendor grounding is the
  standard here:** two of parent #506's four rejected rounds were rejected for asserting an event
  shape the CLI cannot emit. Establish the error kinds, the transient set and the status field
  from the installed `claude` CLI and/or a real transcript, recording which claims are **observed**
  and which **derived**. **Prior art, read selectively:** round 3's patch is archived at
  `results/issue_533/iteration-v3/patch.diff` (+ `build-notes.md`, `SUMMARY.md`), whose §5 records
  what the adversary re-derived from `claude-code 2.1.233` and which twelve mutations it killed;
  it was returned for slice size and the #532 boundary, **not** for approach. You may take its
  classification hunks (the vendor transient kind set; the rule that only the vendor's own "I
  could not classify this" kind has its text read, and then only against the *category* the
  harness promises to retry; the main-session clearing rule; the dual-spelling signal predicate).
  Re-verify against the current base, and do **not** re-apply its four known-open defects, all
  measured: (a) `leaves.py:102` and `:700-702` claimed a signal-killed leaf is not transient while
  `transient` remained `not produced` — criterion (iii) requires the *code*, not a narrowed
  sentence; (b) `assemble.py:80` and `leaves.py:2544` were re-worded to "ran, died of infra it
  reported", dropping #138's emitted-nothing shape that still routes to the same
  `_FAIL_TRANSIENT` / `LEAF_STATUS_INFRA` pair — criterion (iv) requires **both**; (c)
  `_LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` was missed entirely — the fifth restatement site and the
  only operator-facing one; (d) the three unasserted guards named in Falsifiability.
- **Prior-art check (triage cycles):** By file path on `origin/main`: `leaves.py` —
  `LeafError.transient` and `_invoke_leaf_resilient` arrived with #138 and the `not produced`
  definition has never been revisited; `_failure_class` / `_unavailable_classification` are
  #278/#285; `assemble.py`'s leaf-status labels are #278. Open PRs on the target: #519-#525, of
  which #524 (issue 494) and #520 (issue 466) touch `leaves.py` at distant regions (`:782`,
  `:3261`, `:3400`, `:3465`; `do_split`) — no overlap; none touches `progress.py` or `assemble.py`.
  Open issues searched for `transient` / `retry`: #371 (gate-row transient red) is deliberately
  excluded; #510 (signal death) is what criterion (iii) settles narrowly and is cited as such;
  #509 (crash-resume) is a different beat. Not previously attempted as its own slice; #533's round
  3 and parent #506's four rounds were returned on slicing, never on mechanism.
- **Disposition hint:** likely-fix
<!-- pdca:end child-2 -->
