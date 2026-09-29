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
  (`:666-670`), the retry print (`:717`, "with no output (transient)"), `_FAIL_TRANSIENT`
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
  stream-less family still reports substantive (`leaves.py:666-670`), `capture` still returns the
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
  spelling — is invoked **3** times and must be invoked 1 (`_TRANSIENT`,
  `test_leaf_resilience.py:28-31`, is the no-stream-event stub to start from — it writes only
  stderr); (iv) `test_leaf_status.py:135` asserts the full stale label and `:188` its
  `"leaf did not run ("` prefix, so both go red the moment the string is corrected — update them
  **with** the change, not around it.
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
- **Depends on:** 538
- **Conflicts with:** 537, 540, 541
- **Ordering note:** `Depends on: 538` is substance, not merge hygiene — this bundle classifies
  off the record 538 retains, and the wave fold is what puts that record on its base. The
  `Conflicts with` edge is the boundary with issue #532's children, live in this same run: this
  bundle rewrites the retry print at `leaves.py:717`, three lines from the `write_text` at `:720`
  that **#536** moves into the loop, and `_failure_class` (`:2534`) sits ten lines below #536's
  harvest (`:2519-2523`); **#537** varies the `_invoke` call at `:707` in the same loop.
  `Conflicts with` rather than `Depends on` deliberately: an out-of-batch conflict is dropped as
  moot (`waves.py:104-109`), whereas a `Depends on` naming a bundle neither in-batch nor COMPLETE
  aborts the whole run (`waves.py:70-80`) — and nothing here needs to *build on* #536/#537, only
  to avoid being built blind on the same base. With pairs oriented name-lower-first
  (`waves.py:165-175`) the schedule is: **538 ‖ #536** → **#537** → **this**, which is the publish
  order #537's own brief recommends. Being wave ≥ 2 in this instance, **expect one false advisory
  T3 red and do not chase it** — that is target issue #474 (the leaked `PDCA_VERIFY_BASE` export
  under `wave_mode = "stack"`, `pdca.toml:122`), not evidence about this patch. T3 is
  `gating = false`; the gating C4 row is unaffected, since `engine/scripts/run-verify.sh` honours
  `$PDCA_BASE > $PDCA_VERIFY_BASE > override > $PDCA_BRIEF_BASE` and so applies this patch to the
  folded base carrying 538's accepted diff.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues: `progress._is_session_event` (`:365-377`) is the existing per-family stream
  classifier (dispatch on `stream_format`, best-effort JSON, default `False`) and child-1's report
  reader sits beside it in that shape — the classifier belongs in the same neighbourhood and must
  degrade the same way for codex/gemini. `leaves.py:666-670` documents why a stream-less family
  reports `produced=True`; keep that fallback intact. `assemble.py:76-79` states in the codebase's
  own words why the infra shapes must not be conflated and why a false "safe to re-run" is the
  specific harm — the label correction is that rule applied. Note that **no site on the base
  states the definition in the two-shape form**: every one of the six is single-shape ("no
  output"), so criterion (iv) is a rewrite everywhere, not an alignment onto an existing good
  example. Round 3's patch did produce two correct two-shape phrasings (in
  `_review_unavailable`'s and `_unavailable_classification`'s prose) while getting two others
  wrong — see the archived diff, and defect (b) below. **Vendor grounding is the
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

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on implementation issues; the approach and slice are sound. Fix in the rebuild: 1. progress.py (_reports_transient_cause, kind in _CLAUDE_TRANSIENT_KINDS branch): a `rate_limit` report carrying a typed api_error (e.g. long_context_credits_required, model_requires_usage_credits) is a permanent entitlement stop and must NOT be transient — criterion (ii). Check the typed cause before the kind-set shortcut; add a test. 2. progress.py (`kind != _CLAUDE_UNKNOWN_KIND or ev.get("api_error")`): also honour the transcript spelling `apiError` (the classifier already accepts `isApiErrorMessage`). A typed `apiError="gateway_session_expired"` currently falls through to prose and is retried 3x. Add a test in that spelling. 3. _TRANSIENT_CAUSE_RE is too broad for `unknown` reports: bare `\b5\d\d\b` matches message indices (`messages.536…`) and bare `\btimeout\b` matches field names in 400 invalid_request_error bodies. Anchor the status arm to the leading `API Error: NNN`, drop/narrow bare `timeout`, and add negative cases with an incidental number and a `timeout` field name (a mutant replacing the whole regex currently passes every test). 4. assemble.py:95 comment still says both INFRA shapes mean "nothing reviewed the diff" — reword to agree with leaves.py ("no review came back"), per criterion (iv). 5. Keep `rate_limit` in _CLAUDE_TRANSIENT_KINDS — that is a deliberate project choice (human, at sign-off). But fix the fixtures README ("Hence `_CLAUDE_TRANSIENT_KINDS`") and the progress.py comment so they state it as the project's policy, borrowed from the vendor's sub-agent retry set — not as the vendor's main-session rule (which covers only overloaded/server_error). 6. Scope, decided by the human at sign-off: KEEP both out-of-bounds edits — the flipped/renamed guards in child-1's test_terminal_error_retention.py (unavoidable under criterion (i)) and the transient message rewrite in _do_build_command. That print was introduced by #537's PR 587 (open), which this bundle stacks on; the edit is a string correction on top of 587, not a collision — merge 587 first, then 539. ALSO ALLOWED (exception to the brief's do-not-touch list): update the module docstring of template/tests/test_builder_retry.py (added by PR 587), which defines a transient death as "the child exits non-zero before emitting any work" — restate it in the two-shape form per criterion (iv). Docstring only; no test changes in that file.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on implementation issues; the approach and slice are sound. Fix in the rebuild:
  1. progress.py (_reports_transient_cause, kind in _CLAUDE_TRANSIENT_KINDS branch): a `rate_limit` report carrying a typed api_error (e.g. long_context_credits_required, model_requires_usage_credits) is a permanent entitlement stop and must NOT be transient — criterion (ii). Check the typed cause before the kind-set shortcut; add a test.
  2. progress.py (`kind != _CLAUDE_UNKNOWN_KIND or ev.get("api_error")`): also honour the transcript spelling `apiError` (the classifier already accepts `isApiErrorMessage`). A typed `apiError="gateway_session_expired"` currently falls through to prose and is retried 3x. Add a test in that spelling.
  3. _TRANSIENT_CAUSE_RE is too broad for `unknown` reports: bare `\b5\d\d\b` matches message indices (`messages.536…`) and bare `\btimeout\b` matches field names in 400 invalid_request_error bodies. Anchor the status arm to the leading `API Error: NNN`, drop/narrow bare `timeout`, and add negative cases with an incidental number and a `timeout` field name (a mutant replacing the whole regex currently passes every test).
  4. assemble.py:95 comment still says both INFRA shapes mean "nothing reviewed the diff" — reword to agree with leaves.py ("no review came back"), per criterion (iv).
  5. Keep `rate_limit` in _CLAUDE_TRANSIENT_KINDS — that is a deliberate project choice (human, at sign-off). But fix the fixtures README ("Hence `_CLAUDE_TRANSIENT_KINDS`") and the progress.py comment so they state it as the project's policy, borrowed from the vendor's sub-agent retry set — not as the vendor's main-session rule (which covers only overloaded/server_error).
  6. Scope, decided by the human at sign-off: KEEP both out-of-bounds edits — the flipped/renamed guards in child-1's test_terminal_error_retention.py (unavoidable under criterion (i)) and the transient message rewrite in _do_build_command. That print was introduced by #537's PR 587 (open), which this bundle stacks on; the edit is a string correction on top of 587, not a collision — merge 587 first, then 539. ALSO ALLOWED (exception to the brief's do-not-touch list): update the module docstring of template/tests/test_builder_retry.py (added by PR 587), which defines a transient death as "the child exits non-zero before emitting any work" — restate it in the two-shape form per criterion (iv). Docstring only; no test changes in that file.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on one policy gap; the approach, slice and the rest of the patch are sound — keep them. Fix in the rebuild: a subscription usage-window stop (5-hour / weekly limit) must NOT be classified transient. Today it arrives as an untyped `error:"rate_limit"` report, is retried 3x, and §6 tells the operator "safe to re-run" — false for hours (the assemble.py:95-99 "false instruction" harm). Distinguish it from a passing 429 using the stream's non-prose signal, the `{"type":"rate_limit_event","rate_limit_info":{status, resetsAt, rateLimitType, ...}}` event (claude-code 2.1.284, functions Qio / Zio) — not by reading prose. A passing mid-session 429 stays transient (rate_limit stays in _CLAUDE_TRANSIENT_KINDS, per iteration-1 decision). Add inline tests: work + window-exhausted rate_limit_event + rate_limit report + exit 1 → 1 run, not transient; work + plain rate_limit report (no window event) + exit 1 → still retried. Out of scope for this bundle (tracked separately in §10): skipping the leaf loudly so the flow continues, and blocking its dependents — that is flow-scheduling work, not classification.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on one policy gap; the approach, slice and the rest of the patch are sound — keep them.
  Fix in the rebuild: a subscription usage-window stop (5-hour / weekly limit) must NOT be classified transient. Today it arrives as an untyped `error:"rate_limit"` report, is retried 3x, and §6 tells the operator "safe to re-run" — false for hours (the assemble.py:95-99 "false instruction" harm). Distinguish it from a passing 429 using the stream's non-prose signal, the `{"type":"rate_limit_event","rate_limit_info":{status, resetsAt, rateLimitType, ...}}` event (claude-code 2.1.284, functions Qio / Zio) — not by reading prose. A passing mid-session 429 stays transient (rate_limit stays in _CLAUDE_TRANSIENT_KINDS, per iteration-1 decision). Add inline tests: work + window-exhausted rate_limit_event + rate_limit report + exit 1 → 1 run, not transient; work + plain rate_limit report (no window event) + exit 1 → still retried.
  Out of scope for this bundle (tracked separately in §10): skipping the leaf loudly so the flow continues, and blocking its dependents — that is flow-scheduling work, not classification.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
