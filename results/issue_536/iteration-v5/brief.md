- **Slug:** attempt-owned-leaf-records-and-harvests
- **Defect / goal:** Nothing ties a leaf's artifact or error record to the *attempt that
  produced it*, on the three leaves that already retry. Three live consequences on the base:
  (a) `_invoke_leaf_resilient` writes its attempt records only **after** the loop
  (`leaves.py:720`), so while attempt 2 runs there is nothing on disk explaining attempt 1,
  and a run killed mid-retry loses them all; (b) the three harvest sites copy their artifact
  on a bare existence test — `:2519-2523` (`check-review.md`), `:2851-2854`, `:3152-3155` —
  with no notion of *which* attempt wrote it, so a truncated verdict a dead attempt left in
  the sandbox is adopted as the leaf's own output, which `engine/README.md:44-68` names
  directly: no evidence must never be filed as a verdict; (c) `_format_leaf_attempt`
  (`:724-730`) embeds `exc.output` raw, so a leaf's own text can impersonate whatever trailer
  the harness uses to describe its own run. None of this needs a builder retry to bite —
  those three leaves retry today.
- **Success criterion:** With the patch: (i) each failed attempt's record is on disk
  **before** the next attempt starts, so a retried leaf — and a post-mortem of a run killed
  mid-retry — can read the predecessor's account instead of a file that does not exist yet;
  (ii) at all three harvest sites, no artifact written by a **dead** attempt is copied out as
  a **successful** attempt's output, and a dead attempt's text is *preserved* in the bundle's
  `*.error.log` rather than merely deleted — a real verdict must not be destroyed while the
  operator is told none was produced; (iii) the **live** attempt's own artifact is still
  harvested exactly as today, and a leaf that exits 0 having written nothing still degrades
  to today's placeholder; (iv) no dead attempt's captured stderr and no quoted artifact text
  can impersonate the harness's own in-flight trailer: whatever marker distinguishes an
  interrupted log from a spent one is neutralised in **both** the quoted-artifact text and
  the `_format_leaf_attempt` stderr tail, and is matched as the log's **last non-blank line,
  alone** — never as a substring; (v) an in-flight log does not read as "the leaf ran and
  FAILED" to the #369 recovery discriminators (`review_never_ran` at `:2094`, its test at
  `:2103-2104`; `run_advisory_leaves(only_missing=True)` at `:2800-2801`), so a reviewer the
  death window merely interrupted is still re-run and a bundle cannot reach sign-off with no
  review of the diff; (vi) nothing else changes: the shipped resilience contract holds
  unchanged (attempt count, backoff, the staleness clear at `:698-702`, the `_memory_log_for`
  derivation), a success still leaves no error log behind, the #420 memory-telemetry
  post-mortem still rides `output` into the same log **and survives the neutralisation
  intact**, and `template/tests/test_leaf_resilience.py` stays green **untouched** (its five
  tests assert with `assertIn`, so a per-attempt flush and a trailer do not disturb them —
  verify that rather than editing the file).
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:26-35` already ships the harness this needs:
  `_TRANSIENT` (stderr only, no stream event → transient under today's rule), `_SUBSTANTIVE`
  (emits `{"type":"assistant"}` first), a leaf whose argv is `[sys.executable, "-c", script]`,
  and a `$CNT` file counting invocations. **Copy that harness into the new test file** — do
  not import it across modules. (i): instrument from *inside* the stub leaf — attempt 2
  asserts the error log already exists and holds attempt 1's stderr, recording the
  observation where the test can read it; today the file does not exist until the loop ends.
  (ii)/(iii): drive `leaves._run_review_sandboxed` with a stub reviewer whose first attempt
  writes a truncated `check-review.md` into the sandbox then dies transiently, followed by an
  attempt that exits 0 without writing — today the harvest copies the dead attempt's file out
  as the review. (iv): a dead attempt's artifact whose text **ends in** the marker, and a
  leaf whose stderr quotes it; **the marker must be alone on its own final line** — round 3
  shipped this leg with the marker embedded mid-line ("echo of the source: " + marker), which
  is not the failure mode, because the discriminator reads the last non-blank line. (v): an
  error log left mid-retry must still let `review_never_ran` recover the leaf. All genuine
  reds on the current base.
- **Invariant to restore:** **An attempt is the unit of accountability** — the bookkeeping
  half: nothing a **dead** attempt left behind may be reported as a **live** attempt's work,
  and an attempt's account exists from the moment it fails rather than only once the loop
  ends. Stated over the category, not this incident: it holds for every artifact the harness
  harvests from a retried leaf, not only the reviewer's. Source: internal project invariant
  (Tier C), the target's own written rules — `leaves.py:641-647` (why a captured tail exists
  at all: `(no output captured)` is "a post-mortem artifact that explains nothing", #286
  review), `leaves.py:683-697` (the #138 resilience contract), `engine/README.md:44-68` (no
  evidence must never be filed as a verdict). `docs/principles.md` §5/§6 are unfilled
  scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `acb214a`; every `path:line`
  above was re-verified against it while this proposal was written)
- **Reproduction:** On a clean checkout of the target base, offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today; read
     `:26-35` for the stub-leaf harness and `$CNT` counter to copy.
  2. Read the gap: `leaves.py:720` (records written only once the loop ends);
     `:2519-2523` / `:2851-2854` / `:3152-3155` (harvest on a bare `.exists()`,
     attempt-blind); `:727` (`exc.output` embedded raw); `:2103-2104` and `:2800-2801` (an
     error log means "ran and failed" — a meaning this slice changes and must keep honest).
  3. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`).
- **Surfaces:** data
- **Difficulty:** high — one production module, but seven regions in it, and the widest reach
  is semantic: it changes what the *presence* of an error log means, which is read at two
  recovery discriminators and documented in `driver.py`'s `advance` / `_resume_interrupted_check`
  prose. A diff-reviewer must hold the wrapper, the record format, three near-identical
  harvests and both discriminators in view at once.
- **Scope (one logical fix) / out of scope:** Give the leaf-invocation wrapper and the three
  artifact harvests a notion of which attempt produced what: flush each attempt's record as
  it happens, and stop a dead attempt's artifact from being harvested as a live one's — text
  preserved, not destroyed — including the stderr tail that today can impersonate the
  harness's own trailer. Keep the recovery discriminators honest about the new state
  ("interrupted" is not "gave up"). **Out of scope:** the builder — do **not** move
  `_do_build_command` (`:1824`) onto the resilient path, do not touch `do_build`'s capture
  (`:1765-1778`), `_build_prompt` (`:1834`) or `_stub_build` (`:1889`); that is sibling
  child-2, which builds on this. The stream-side question of *what counts as* a transient
  death — sibling #533: do **not** touch `progress.py`, redefine `LeafError.transient`
  (`leaves.py:103-108`), or add a signal-death predicate; the retry set is reused exactly as
  shipped, and a judgement that it is wrong is #533's or #510's slice, never a reason to
  widen this one. Also out: a lane/worktree reset between attempts; any new `pdca.toml` knob
  (reuse the shipped attempts/backoff defaults); the gate-side transient (#371); issue #510's
  own remedy; the nine other leaves still on plain `_invoke`. Do **not** create
  `template/tests/fixtures/` and do **not** add
  `template/tests/test_terminal_error_classification.py` — both belong to #533.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter, so this builds and goes red→green with no vendor
  CLI, no API key, no network and no container.
- **Test file:** `template/tests/test_attempt_ownership.py` (**new**). A new file, not an
  append: `engine/scripts/run-prod-path.py` keys C5 on *newly added* test files, and round
  3's appends made C5 print "patch adds no new test file — nothing to assert" three rounds
  running — which is how two unfaithful-stub findings survived to the adversary. **C4 red-leg
  import trap — this is why the file is new:** the red leg reverts the production hunks and
  keeps every `tests/*` and `template/tests/*` hunk (`engine/scripts/run-verify.sh:214`), so
  a new file earns a genuine red **provided it imports no symbol this patch adds at module
  level** — a red-leg import failure is recorded `PDCA-UNVERIFIABLE`, not red
  (`run-verify.sh:189,232`). Import only pre-existing API at module level
  (`from pdca_harness import leaves`) and exercise the behaviour through pre-existing entry
  points (`leaves._invoke_leaf_resilient`, `leaves._run_review_sandboxed`,
  `leaves.review_never_ran`), so the assertions are behavioural rather than
  symbol-existence. The C4 gate runs **every** test file the patch touches, so if
  `test_leaf_resilience.py` is touched at all it must be red-worthy too — the criterion above
  says leave it alone.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this wires into patterns the codebase already applies:
  `_invoke_leaf_resilient` (`leaves.py:673-721`) is the wrapper to extend **without weakening
  it**: its staleness clear (`:698-702`), its `_memory_log_for` derivation, its `records` list
  and the `_format_leaf_attempt` record format (`:724-730`). The three harvest sites already
  compose the wrapper (`:2507`, `:2840`, `:3142`) and each pairs it with an
  `*_unavailable(...)` placeholder that already accepts `error_log=` on its failure branch —
  mirror that shape rather than inventing a second one. **Prior art you may read,
  selectively:** round 3's rejected patch is archived at
  `results/issue_532/iteration-v3/patch.diff` (+ `build-notes.md`); its mechanism was
  confirmed by the reviewer and the adversary and it was returned for slice size, not
  approach. You may take from it the fail-closed withdrawal and the `recorded`-gated retry.
  Re-verify anything you take against the current base, and do **not** re-apply its known
  defect here: `_format_leaf_attempt` was never defanged.
- **Ordering note:** Wave 1 of the two-wave split of #532; child-2 (the builder retry and the
  honest failed-Do report) declares `Depends on` this one. **Both children edit the body of
  `_invoke_leaf_resilient`'s `for attempt` loop** — this one moves the `write_text` at `:720`
  into it, child-2 varies the prompt on the `_invoke` call at `:707` — so they are never
  co-scheduled. Own the loop **body**; sibling #533 owns the **strings and comments** in that
  function (it rewrites the print at `:717`, three lines from `:720`). Do not adopt #533's
  `"on transient infra"` wording: it is only accurate after #533's redefinition of transient,
  so shipping it early puts a false string in tree. No ordering field names #533's children —
  they do not exist yet, and an edge naming them would either abort the run
  (`waves.py:77-80`) or be silently dropped (`waves.py:104-109`).
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/leaves.py` — `_invoke_leaf_resilient` arrived with #138 for the
  reviewer/advisory leaves; its post-loop record write has never been revisited. The harvest
  sites' bare existence test dates from the same change. Open PRs on the target: #519-#525,
  of which #524 (issue 494) and #520 (issue 466) touch `leaves.py` at distant regions
  (`:782`, `:3261`, `:3400`, `:3465`; `do_split`) — no overlap. #371 (gate-row transient red)
  and #510 (signal death) are adjacent and deliberately excluded; #509 (crash-resume) is a
  different beat. Not previously attempted as its own slice; parent #506 and #532 were both
  returned on slicing, never on mechanism.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the crash-recovery findings, not on approach or slicing. The mechanism is right — C4 red→green was independently reproduced, the defang + whole-last-line match survived 30 impersonation payloads, and test_leaf_resilience.py stayed untouched and green. Same slice, same design; close the findings below. What to change: 1. Make the per-attempt flush crash-atomic. `_write_attempt_records` (`leaves.py:800`) truncates first and appends the `_LEAF_IN_FLIGHT` trailer last, so a kill between the two writes leaves an unmarked (commonly 0-byte) log. That reads as "ran and failed" to `_leaf_ran_and_failed` (`:835`), `review_never_ran` (`:2277`) returns False, `driver.py:176` never recovers the reviewer, and the bundle can reach sign-off with no review of the diff. The base left no log at all in that window and DID recover, so this is a new failure mode the patch introduces. Use the crash-atomic idiom the repo already ships: temp sibling + `os.replace` (`act.py:326`). 2. Close the same window on the success path. The reviewer's C5/T3 FAILs (`leaves.py:734`, `:832`) are the post-success/pre-placeholder leg of (1): a silent successful retry after a withdrawal re-flushes the log without the marker, and a kill before the placeholder is written yields artifact absent + non-in-flight log + `review_never_ran` False. Sequence the re-flush and the placeholder so no ordering of the kill leaves an interrupted Check looking spent. 3. Classify an infra death as one. The new "succeeded having written nothing after a withdrawal" branch (`leaves.py:2704`, twins `:3039`, `:3340`) passes `error_log=` but leaves `failure=` at the `_FAIL_SUBSTANTIVE` default, so `_unavailable_classification` stamps `human-empty` and tells the operator "substantive — needs a human" over a log reading `overloaded_error 529`. That is the inversion #278's marker exists to prevent. The wrapper only retries transient failures, so a log surviving a successful return is by construction an infra death — the branch can classify it without new information. 4. Close the two test-blindness gaps the adversary and the code review named; both are cheap and both are the kind of gap that would let a real regression stay green: - one parametrized case over `_run_advisory_sandboxed` covering the advisory (`leaves.py:3028`) and plan-advisory (`:3329`) harvest sites — today only `_run_review_sandboxed` is driven, so wiring either site to the bundle path instead of the sandbox `out` would unlink a shipped artifact and the suite would stay green; - a `Path.unlink`-failure test for `_withdraw_residue`'s fail-closed branch (`leaves.py:875-883`), mirroring the existing `refuse_the_log` pattern — the symmetric write-failure leg is covered, this one is asserted in prose only. 5. Align the third reader of "an error log means the leaf ran and FAILED": `assemble.py:417` still splits on a bare `.exists()`. Currently shadowed, not a reachable bug — but it now contradicts `leaves.py:2277` and `:2986` about the same file. Use `leaves._leaf_ran_and_failed`. Do NOT widen the slice: - Leave the staleness clear at `leaves.py:714` alone. The adversary is right that a recovery re-run deletes the dead attempt's preserved verdict, but criterion (vi) freezes that clear and fixing it is a scope change, not this iteration. Note it in build-notes as a known limitation and let Act decide. - Do not touch the retry set, `LeafError.transient`, `progress.py`, or the builder path — the sibling exclusions in the brief still hold. - Keep `test_leaf_resilience.py` untouched.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the crash-recovery findings, not on approach or slicing. The mechanism is
  right — C4 red→green was independently reproduced, the defang + whole-last-line match
  survived 30 impersonation payloads, and test_leaf_resilience.py stayed untouched and
  green. Same slice, same design; close the findings below.

  What to change:

  1. Make the per-attempt flush crash-atomic. `_write_attempt_records`
     (`leaves.py:800`) truncates first and appends the `_LEAF_IN_FLIGHT` trailer last, so
     a kill between the two writes leaves an unmarked (commonly 0-byte) log. That reads as
     "ran and failed" to `_leaf_ran_and_failed` (`:835`), `review_never_ran` (`:2277`)
     returns False, `driver.py:176` never recovers the reviewer, and the bundle can reach
     sign-off with no review of the diff. The base left no log at all in that window and
     DID recover, so this is a new failure mode the patch introduces. Use the crash-atomic
     idiom the repo already ships: temp sibling + `os.replace` (`act.py:326`).

  2. Close the same window on the success path. The reviewer's C5/T3 FAILs
     (`leaves.py:734`, `:832`) are the post-success/pre-placeholder leg of (1): a silent
     successful retry after a withdrawal re-flushes the log without the marker, and a kill
     before the placeholder is written yields artifact absent + non-in-flight log +
     `review_never_ran` False. Sequence the re-flush and the placeholder so no ordering of
     the kill leaves an interrupted Check looking spent.

  3. Classify an infra death as one. The new "succeeded having written nothing after a
     withdrawal" branch (`leaves.py:2704`, twins `:3039`, `:3340`) passes `error_log=` but
     leaves `failure=` at the `_FAIL_SUBSTANTIVE` default, so `_unavailable_classification`
     stamps `human-empty` and tells the operator "substantive — needs a human" over a log
     reading `overloaded_error 529`. That is the inversion #278's marker exists to prevent.
     The wrapper only retries transient failures, so a log surviving a successful return is
     by construction an infra death — the branch can classify it without new information.

  4. Close the two test-blindness gaps the adversary and the code review named; both are
     cheap and both are the kind of gap that would let a real regression stay green:
     - one parametrized case over `_run_advisory_sandboxed` covering the advisory
       (`leaves.py:3028`) and plan-advisory (`:3329`) harvest sites — today only
       `_run_review_sandboxed` is driven, so wiring either site to the bundle path instead
       of the sandbox `out` would unlink a shipped artifact and the suite would stay green;
     - a `Path.unlink`-failure test for `_withdraw_residue`'s fail-closed branch
       (`leaves.py:875-883`), mirroring the existing `refuse_the_log` pattern — the
       symmetric write-failure leg is covered, this one is asserted in prose only.

  5. Align the third reader of "an error log means the leaf ran and FAILED":
     `assemble.py:417` still splits on a bare `.exists()`. Currently shadowed, not a
     reachable bug — but it now contradicts `leaves.py:2277` and `:2986` about the same
     file. Use `leaves._leaf_ran_and_failed`.

  Do NOT widen the slice:

  - Leave the staleness clear at `leaves.py:714` alone. The adversary is right that a
    recovery re-run deletes the dead attempt's preserved verdict, but criterion (vi)
    freezes that clear and fixing it is a scope change, not this iteration. Note it in
    build-notes as a known limitation and let Act decide.
  - Do not touch the retry set, `LeafError.transient`, `progress.py`, or the builder path
    — the sibling exclusions in the brief still hold.
  - Keep `test_leaf_resilience.py` untouched.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on unclosed carry-forward, not on approach or slicing. The slice is the right size and the design is sound — the atomic per-attempt flush, the defang + whole-last-line match, fail-closed withdrawal, and the three converted readers of "an error log means the leaf ran and FAILED" are all correct and independently reproduced (14 failures + 1 error red, 19/19 green, 1777-test suite green). Same slice, same design; close the items below. 1. Close round 1's carry-forward item 3 in the shape that actually occurs. `_empty_run_class` is keyed on `error_log.exists()`, but the log only survives a success when `withdrew` is True — and `withdrew` is set only when a dead attempt left a FILE. For the canonical transient death (attempt 1 exits non-zero with `overloaded_error 529` on stderr, writes nothing; attempt 2 exits 0 writing nothing) the `else` branch at leaves.py:739-741 unlinks the log, so `_empty_run_class` sees nothing and stamps `_FAIL_SUBSTANTIVE` — the operator is told "substantive — needs a human. The leaf ran but did not yield a usable verdict; do not assume an infra blip" one step after the harness deleted the 529 it was holding. That is #278's inversion and the parent invariant ("the evidence of a failure is kept; no evidence is never filed as a verdict") failing in the COMMON case. Adjudication you need, which the brief left ambiguous: keep the log whenever `records` is non-empty and the artifact is absent, not only after a file withdrawal. Criterion (vi)'s "a success still leaves no error log behind" governs a clean success that PRODUCED its artifact — not a success that produced nothing over a dead predecessor. Criterion (iii) still holds: a leaf that exits 0 having written nothing with NO dead predecessor degrades to today's placeholder, error-log-free, class unchanged. 2. Make the successful-retry cleanup not best-effort (the reviewer's C3/T3 FAIL, leaves.py:737-741). A swallowed `OSError` on `error_log.unlink()` leaves the log in flight; the harvest then succeeds and `_settle_leaf_record` STRIPS the trailer, converting the leftover into a settled "ran and failed" record beside a live check-review.md — one leaf archived as both success and failure, against criterion (vi). Confirmed narrow: no reader is driven to a wrong action (review_never_ran and the advisory short-circuit both see the artifact first), so this is archive pollution plus a contract breach, not a corrupted verdict. Fix at the source rather than papering over it downstream. 3. Close the two test-blindness holes the adversary demonstrated by mutation; both are one assertion and both would let a real regression ship green. - Mutating `leaf_run_incomplete`'s whole-line match into a substring sniff leaves all 1777 tests green, because both impersonation cases route their payload through `_defang_in_flight` before the match runs — the braces leaves.py:859-864 argues for are untested. Hand-write a log whose BODY contains the marker on a non-final line and whose last non-blank line is ordinary text; assert `leaf_run_incomplete(log)` is False. - Deleting BOTH advisory `_settle_leaf_record` calls (leaves.py:3135, :3439) leaves the suite green: `BothAdvisoryHarvestsAreAttemptAwareToo` asserts only the harvest half. Parametrise it to assert `leaf_run_incomplete(error_log)` is False after each site. 4. `driver.py:178-179` still prints "Check — reviewer never ran (beat was interrupted after the gate write)" on every `review_never_ran(d)`, which this patch has just made false for a reviewer that ran, died transiently and was killed during the backoff. The paired text in assemble.py:435-437 was reworded for exactly this reason; this fourth reader was missed. Wording only. Do NOT widen the slice: - Leave the staleness clear at leaves.py:716 alone — criterion (vi) freezes it and the prior sign-off adjudicated it as a deliberate Act deferral. - The non-atomic `shutil.copy2` of the VERDICT at the three harvests (leaves.py:2772, :3131, :3434) and the stranded `*.error.log.tmp.<pid>` (leaves.py:807-808) are noted as Act candidates, not this round's work. Do not harden them here. - Do not touch the retry set, `LeafError.transient`, `progress.py` (sibling #538 owns it) or the builder path. Keep `test_leaf_resilience.py` untouched.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on unclosed carry-forward, not on approach or slicing. The slice is the right
  size and the design is sound — the atomic per-attempt flush, the defang + whole-last-line
  match, fail-closed withdrawal, and the three converted readers of "an error log means the
  leaf ran and FAILED" are all correct and independently reproduced (14 failures + 1 error
  red, 19/19 green, 1777-test suite green). Same slice, same design; close the items below.

  1. Close round 1's carry-forward item 3 in the shape that actually occurs. `_empty_run_class`
     is keyed on `error_log.exists()`, but the log only survives a success when `withdrew` is
     True — and `withdrew` is set only when a dead attempt left a FILE. For the canonical
     transient death (attempt 1 exits non-zero with `overloaded_error 529` on stderr, writes
     nothing; attempt 2 exits 0 writing nothing) the `else` branch at leaves.py:739-741 unlinks
     the log, so `_empty_run_class` sees nothing and stamps `_FAIL_SUBSTANTIVE` — the operator
     is told "substantive — needs a human. The leaf ran but did not yield a usable verdict; do
     not assume an infra blip" one step after the harness deleted the 529 it was holding. That
     is #278's inversion and the parent invariant ("the evidence of a failure is kept; no
     evidence is never filed as a verdict") failing in the COMMON case.
     Adjudication you need, which the brief left ambiguous: keep the log whenever `records` is
     non-empty and the artifact is absent, not only after a file withdrawal. Criterion (vi)'s
     "a success still leaves no error log behind" governs a clean success that PRODUCED its
     artifact — not a success that produced nothing over a dead predecessor. Criterion (iii)
     still holds: a leaf that exits 0 having written nothing with NO dead predecessor degrades
     to today's placeholder, error-log-free, class unchanged.

  2. Make the successful-retry cleanup not best-effort (the reviewer's C3/T3 FAIL,
     leaves.py:737-741). A swallowed `OSError` on `error_log.unlink()` leaves the log in
     flight; the harvest then succeeds and `_settle_leaf_record` STRIPS the trailer, converting
     the leftover into a settled "ran and failed" record beside a live check-review.md — one
     leaf archived as both success and failure, against criterion (vi). Confirmed narrow: no
     reader is driven to a wrong action (review_never_ran and the advisory short-circuit both
     see the artifact first), so this is archive pollution plus a contract breach, not a
     corrupted verdict. Fix at the source rather than papering over it downstream.

  3. Close the two test-blindness holes the adversary demonstrated by mutation; both are
     one assertion and both would let a real regression ship green.
     - Mutating `leaf_run_incomplete`'s whole-line match into a substring sniff leaves all
       1777 tests green, because both impersonation cases route their payload through
       `_defang_in_flight` before the match runs — the braces leaves.py:859-864 argues for are
       untested. Hand-write a log whose BODY contains the marker on a non-final line and whose
       last non-blank line is ordinary text; assert `leaf_run_incomplete(log)` is False.
     - Deleting BOTH advisory `_settle_leaf_record` calls (leaves.py:3135, :3439) leaves the
       suite green: `BothAdvisoryHarvestsAreAttemptAwareToo` asserts only the harvest half.
       Parametrise it to assert `leaf_run_incomplete(error_log)` is False after each site.

  4. `driver.py:178-179` still prints "Check — reviewer never ran (beat was interrupted after
     the gate write)" on every `review_never_ran(d)`, which this patch has just made false for
     a reviewer that ran, died transiently and was killed during the backoff. The paired text
     in assemble.py:435-437 was reworded for exactly this reason; this fourth reader was
     missed. Wording only.

  Do NOT widen the slice:
  - Leave the staleness clear at leaves.py:716 alone — criterion (vi) freezes it and the prior
    sign-off adjudicated it as a deliberate Act deferral.
  - The non-atomic `shutil.copy2` of the VERDICT at the three harvests (leaves.py:2772, :3131,
    :3434) and the stranded `*.error.log.tmp.<pid>` (leaves.py:807-808) are noted as Act
    candidates, not this round's work. Do not harden them here.
  - Do not touch the retry set, `LeafError.transient`, `progress.py` (sibling #538 owns it) or
    the builder path. Keep `test_leaf_resilience.py` untouched.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the findings, not on approach or slicing — for the third time, and the mechanism is holding up: C4 red→green reproduced independently, twelve targeted mutations of the new production logic all caught, 1780-test driver suite green, no impersonation payload flipped either discriminator, `test_leaf_resilience.py` untouched and green. Same slice, same design. Close the items below and keep the diff from growing — it is already flagged oversized, so prefer the minimal edit at each site over a refactor. 1. Close the withdraw-before-persist kill window (the reviewer's C3/C5/T3 FAIL, `leaves.py:986` / `:760`). `_withdraw_residue` reads the dead attempt's text into memory and `unlink()`s the artifact, and only afterwards does the caller persist the record — a kill in that gap loses BOTH the dead attempt's text and its account (`runs=1 bundle_artifact=False error_log=False`). It is narrower than the base's window, not a regression, but it is the exact no-artifact/no-account state this slice exists to eliminate, and it is cheaply closable: persist the record (residue text included) BEFORE the unlink, then unlink. The ordering knot is that `in_flight` depends on `owned`, which depends on the unlink having succeeded — resolve it by flushing first with `in_flight = transient and attempt < attempts`, then withdrawing, then re-flushing with `in_flight=False` if the unlink was refused. The fail-closed stop on a refused withdrawal stays exactly as it is. 2. Settle (or distrust) the log in the three `err is not None` harvest branches (`leaves.py:2804-2807`, mirrored `:3167-3170`, `:3470-3473`). All three file the `*_unavailable` placeholder but never call `_settle_leaf_record`, relying on the loop's final `_write_attempt_records(..., in_flight=False)` having landed. When that write fails on a NON-first attempt after an earlier one already landed in flight, the file keeps its in-flight trailer while a "leaf failed" verdict sits in the bundle — `review_never_ran` / `only_missing` then re-run and re-pay for a leaf whose outcome is already filed, which is the same "one leaf recorded as two contradictory things" this change removes. Fix at either end (settle in the `err` branches, or have `_write_attempt_records`'s failure path strip a trailer it can no longer trust). Add the test that is missing: a write failure on a middle/last attempt AFTER an earlier attempt's in-flight write landed — the existing write-failure test refuses every write from attempt 1, so it never creates the stale marker. 3. Fix the two claim-accuracy defects — prose and rationale only, no behaviour change. In a slice whose whole invariant is "never file a false account of a run", what the harness tells the operator has to be true too. - `leaves.py:2910`: for a run whose attempt 1 died transiently (`overloaded_error 529`) and whose attempt 2 exited 0 having written nothing, `_FAIL_TRANSIENT`'s prose says "retries did not recover" — but they did; the recovered attempt produced no verdict. The class (`infra-empty`) and the action ("safe to re-run") are right; only the account is wrong. Widen the wording, or give the empty-run shape its own. Also strengthen `test_attempt_ownership.py:363-365`, which asserts only the class and the substring "safe to re-run" and is therefore true of the wrong sentence too. - `leaves.py:919-921` and the tests at `test_attempt_ownership.py:607-609`, `:523-525`: the settle's stated justification ("otherwise a leaf that gave up looks recoverable forever and is re-run and re-paid for on every advance") is unwarranted — every reader short-circuits on the placeholder first, and deleting the settle leaves `review_never_ran` False regardless. Restate it as what it is: archive hygiene, plus the genuinely load-bearing half — settle AFTER the outcome is filed, never before — which is already correct and separately proven. Fix the rationale, not the code, so a later maintainer does not read the settle as a recovery guard. Do NOT widen the slice: - The shared `_harvest_leaf` helper the code review suggests for the three near-identical harvest sites is a good idea and an Act candidate, NOT this round's work. Closing item 2 at three sites by hand is smaller than the refactor, and this patch is already oversized. - Leave the staleness clear at `leaves.py:718` alone — criterion (vi) freezes it and two prior sign-offs adjudicated the recovery-re-run/preserved-text interaction as a deliberate Act deferral. - The non-atomic `shutil.copy2` of the verdict at the three harvests and the strandable `*.error.log.tmp.<pid>` remain noted, not hardened here. - Do not touch the retry set, `LeafError.transient`, `progress.py` (sibling #538 owns it) or the builder path. Keep `test_leaf_resilience.py` untouched.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the findings, not on approach or slicing — for the third time, and the
  mechanism is holding up: C4 red→green reproduced independently, twelve targeted mutations
  of the new production logic all caught, 1780-test driver suite green, no impersonation
  payload flipped either discriminator, `test_leaf_resilience.py` untouched and green. Same
  slice, same design. Close the items below and keep the diff from growing — it is already
  flagged oversized, so prefer the minimal edit at each site over a refactor.

  1. Close the withdraw-before-persist kill window (the reviewer's C3/C5/T3 FAIL,
     `leaves.py:986` / `:760`). `_withdraw_residue` reads the dead attempt's text into memory
     and `unlink()`s the artifact, and only afterwards does the caller persist the record — a
     kill in that gap loses BOTH the dead attempt's text and its account (`runs=1
     bundle_artifact=False error_log=False`). It is narrower than the base's window, not a
     regression, but it is the exact no-artifact/no-account state this slice exists to
     eliminate, and it is cheaply closable: persist the record (residue text included) BEFORE
     the unlink, then unlink. The ordering knot is that `in_flight` depends on `owned`, which
     depends on the unlink having succeeded — resolve it by flushing first with
     `in_flight = transient and attempt < attempts`, then withdrawing, then re-flushing with
     `in_flight=False` if the unlink was refused. The fail-closed stop on a refused withdrawal
     stays exactly as it is.

  2. Settle (or distrust) the log in the three `err is not None` harvest branches
     (`leaves.py:2804-2807`, mirrored `:3167-3170`, `:3470-3473`). All three file the
     `*_unavailable` placeholder but never call `_settle_leaf_record`, relying on the loop's
     final `_write_attempt_records(..., in_flight=False)` having landed. When that write fails
     on a NON-first attempt after an earlier one already landed in flight, the file keeps its
     in-flight trailer while a "leaf failed" verdict sits in the bundle — `review_never_ran` /
     `only_missing` then re-run and re-pay for a leaf whose outcome is already filed, which is
     the same "one leaf recorded as two contradictory things" this change removes. Fix at
     either end (settle in the `err` branches, or have `_write_attempt_records`'s failure path
     strip a trailer it can no longer trust). Add the test that is missing: a write failure on
     a middle/last attempt AFTER an earlier attempt's in-flight write landed — the existing
     write-failure test refuses every write from attempt 1, so it never creates the stale
     marker.

  3. Fix the two claim-accuracy defects — prose and rationale only, no behaviour change. In a
     slice whose whole invariant is "never file a false account of a run", what the harness
     tells the operator has to be true too.
     - `leaves.py:2910`: for a run whose attempt 1 died transiently (`overloaded_error 529`)
       and whose attempt 2 exited 0 having written nothing, `_FAIL_TRANSIENT`'s prose says
       "retries did not recover" — but they did; the recovered attempt produced no verdict.
       The class (`infra-empty`) and the action ("safe to re-run") are right; only the account
       is wrong. Widen the wording, or give the empty-run shape its own. Also strengthen
       `test_attempt_ownership.py:363-365`, which asserts only the class and the substring
       "safe to re-run" and is therefore true of the wrong sentence too.
     - `leaves.py:919-921` and the tests at `test_attempt_ownership.py:607-609`, `:523-525`:
       the settle's stated justification ("otherwise a leaf that gave up looks recoverable
       forever and is re-run and re-paid for on every advance") is unwarranted — every reader
       short-circuits on the placeholder first, and deleting the settle leaves
       `review_never_ran` False regardless. Restate it as what it is: archive hygiene, plus
       the genuinely load-bearing half — settle AFTER the outcome is filed, never before —
       which is already correct and separately proven. Fix the rationale, not the code, so a
       later maintainer does not read the settle as a recovery guard.

  Do NOT widen the slice:
  - The shared `_harvest_leaf` helper the code review suggests for the three near-identical
    harvest sites is a good idea and an Act candidate, NOT this round's work. Closing item 2
    at three sites by hand is smaller than the refactor, and this patch is already oversized.
  - Leave the staleness clear at `leaves.py:718` alone — criterion (vi) freezes it and two
    prior sign-offs adjudicated the recovery-re-run/preserved-text interaction as a
    deliberate Act deferral.
  - The non-atomic `shutil.copy2` of the verdict at the three harvests and the strandable
    `*.error.log.tmp.<pid>` remain noted, not hardened here.
  - Do not touch the retry set, `LeafError.transient`, `progress.py` (sibling #538 owns it)
    or the builder path. Keep `test_leaf_resilience.py` untouched.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: Not a slicing problem — reading A. The slice and the design are right and have been stable for four rounds: C4 red->green reproduced independently, 19 of 20 mutations of the new logic caught, no impersonation payload flipped either discriminator, and test_leaf_resilience.py untouched and green. Same slice, same mechanism. Do NOT re-scope, do not split, do not refactor. On the size flag: it is largely the test. 857 of the 1312 added lines (49 KB of 91 KB) are template/tests/test_attempt_ownership.py; the production change is ~450 lines across four files. Keep the diff from growing — prefer the minimal edit at each site. Close these three findings, all in code this patch introduced: 1. template/src/pdca_harness/leaves.py:912 — leaf_run_incomplete reads the log with read_text(encoding="utf-8") and guards only OSError (:913), while its own docstring promises "absent or unreadable => False" (:909-910). A non-UTF-8 log raises UnicodeDecodeError straight out of a discriminator that now sits on driver.advance's critical path, so the cycle aborts instead of degrading; the reachable route is the patch's own premise (a log the pre-patch non-atomic write left truncated mid-multibyte, read after upgrade). Fix: errors="replace" — matching _residue_record's own defensive read at :1004 — or except (OSError, ValueError). 2. template/src/pdca_harness/leaves.py:1004 — _residue_record reads the entire dead artifact into the driver before applying the _RESIDUE_KEEP bound (:1007), and is called from inside the "a failed leaf must never crash the cycle" handler (:758, guard at :750) which catches only OSError (:1005). A MemoryError therefore escapes the guard and leaves no placeholder and no error log — precisely the no-artifact/ no-account state this slice exists to eliminate. Same escape at the two advisory sites (:3222). Fix: bounded read, open(...).read(_RESIDUE_KEEP + 1), and widen the guard to Exception. 3. template/src/pdca_harness/leaves.py:3176 — run_advisory_leaves(only_missing=True), the second of the two #369 recovery discriminators criterion (v) names explicitly, is exercised by no test: reverting it to the base's bare advisory_error_log(...).exists() leaves the whole 1784-test driver suite green. This is the twin round 1's carry-forward already asked to be covered (item 4). Add one test: seed a bundle with an in-flight advisory error log and no artifact, assert the leaf is re-run. Do not widen the slice: keep test_leaf_resilience.py untouched; do not touch progress.py, LeafError.transient, the retry set, the builder path, or the staleness clear. The near-verbatim duplication across the three harvest sites stays an Act candidate, not this round's refactor. Optional, non-gating if it is free while in that function: _format_leaf_attempt's "(no output captured)" fallback body (leaves.py:1046 area) does not pass through _defang_in_flight — only tail does. The code-review lens judged it outside the two channels criterion (iv) names and declined to gate on it. The two routine NEEDS-HUMAN items (T5 prior-art overlap across the four non-leaves.py paths; fitness-to-purpose on re-running an interrupted reviewer) were NOT cleared and remain open for the next sign-off.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Not a slicing problem — reading A. The slice and the design are right and have been
  stable for four rounds: C4 red->green reproduced independently, 19 of 20 mutations of
  the new logic caught, no impersonation payload flipped either discriminator, and
  test_leaf_resilience.py untouched and green. Same slice, same mechanism. Do NOT
  re-scope, do not split, do not refactor.

  On the size flag: it is largely the test. 857 of the 1312 added lines (49 KB of 91 KB)
  are template/tests/test_attempt_ownership.py; the production change is ~450 lines across
  four files. Keep the diff from growing — prefer the minimal edit at each site.

  Close these three findings, all in code this patch introduced:

  1. template/src/pdca_harness/leaves.py:912 — leaf_run_incomplete reads the log with
     read_text(encoding="utf-8") and guards only OSError (:913), while its own docstring
     promises "absent or unreadable => False" (:909-910). A non-UTF-8 log raises
     UnicodeDecodeError straight out of a discriminator that now sits on driver.advance's
     critical path, so the cycle aborts instead of degrading; the reachable route is the
     patch's own premise (a log the pre-patch non-atomic write left truncated mid-multibyte,
     read after upgrade). Fix: errors="replace" — matching _residue_record's own defensive
     read at :1004 — or except (OSError, ValueError).

  2. template/src/pdca_harness/leaves.py:1004 — _residue_record reads the entire dead
     artifact into the driver before applying the _RESIDUE_KEEP bound (:1007), and is
     called from inside the "a failed leaf must never crash the cycle" handler (:758,
     guard at :750) which catches only OSError (:1005). A MemoryError therefore escapes
     the guard and leaves no placeholder and no error log — precisely the no-artifact/
     no-account state this slice exists to eliminate. Same escape at the two advisory
     sites (:3222). Fix: bounded read, open(...).read(_RESIDUE_KEEP + 1), and widen the
     guard to Exception.

  3. template/src/pdca_harness/leaves.py:3176 — run_advisory_leaves(only_missing=True),
     the second of the two #369 recovery discriminators criterion (v) names explicitly, is
     exercised by no test: reverting it to the base's bare advisory_error_log(...).exists()
     leaves the whole 1784-test driver suite green. This is the twin round 1's carry-forward
     already asked to be covered (item 4). Add one test: seed a bundle with an in-flight
     advisory error log and no artifact, assert the leaf is re-run.

  Do not widen the slice: keep test_leaf_resilience.py untouched; do not touch progress.py,
  LeafError.transient, the retry set, the builder path, or the staleness clear. The
  near-verbatim duplication across the three harvest sites stays an Act candidate, not this
  round's refactor.

  Optional, non-gating if it is free while in that function: _format_leaf_attempt's
  "(no output captured)" fallback body (leaves.py:1046 area) does not pass through
  _defang_in_flight — only tail does. The code-review lens judged it outside the two
  channels criterion (iv) names and declined to gate on it.

  The two routine NEEDS-HUMAN items (T5 prior-art overlap across the four non-leaves.py
  paths; fitness-to-purpose on re-running an interrupted reviewer) were NOT cleared and
  remain open for the next sign-off.
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 5 — carry-forward (from the previous attempt)
- Sign-off rationale: WHY REJECTED — slicing, not direction. The fix's direction is right and its proof is sound: all gates green, C4 independently re-run (23 failures + 4 errors on the red leg, 31/31 green, full 1789-test suite green, test_leaf_resilience.py untouched as criterion (vi) required). Nothing here says the work is unwanted. It is rejected because the slice is too big to converge: 5 builder attempts, 4 sign-off rounds, patch 44 -> 68 -> 79 -> 93 -> 104 KB (threshold 80), with implementation-shaped adversary findings every single round (4, 4, 2, 3, 2). The size backstop fired at v4 and again at v5. THE ERROR CLASS TO DESIGN OUT (this is the actionable insight). The slice redefines the meaning of a shared signal — the presence/content of *.error.log ("the leaf ran and FAILED") is split into failed vs. merely-interrupted, plus a derived empty-run / leaf-status classification. That meaning has many independent readers, each hard-coding it at its own site. Every round converts the readers in view; the next round finds one more still speaking the old meaning: v1 assemble.py:417 — "the reviewer RAN AND FAILED" v2 driver.py:178-179 — "reviewer never ran" v3 leaves.py:2910 — "retries did not recover" v4 leaves.py:3176 — second #369 discriminator, unconverted v5 assemble.py:85 — "leaf did not run (transient infra — safe to re-run)" The adversary's phrase is exact: the patch widened the sentence it could see, "then stops one reader short." Note the axis MOVED rather than exhausted — v5 confirmed by grep that the *.error.log-as-state readers are now all converted, and the new finding is on a different shared value (the leaf-status enum -> label mapping). Two related faces of the same root (no single point of truth): - the patch's own new paths file false accounts — the very invariant the slice enforces (v1 human-empty misfiling, v2 "inert" docstring, v3 "retries did not recover", v5 the "withdrawn" line written over a file still present); - twin blindness — the mechanism is hand-copied at 3 harvest sites and 2 discriminators, so tests or _settle_leaf_record calls miss a twin (v1, v2 x2). Per-instance fixes cannot end this class. iterate-do would close the two named [impl] items and leave the generator intact. SPLIT SEAMS FOR THE RE-PLAN (candidates — Plan authors the briefs). A. Give the redefined meaning ONE owner: a single predicate/type that every reader consults (production branches, both #369 discriminators, assemble.py status labels and prose, driver.py operator messages). Ends the "stops one reader short" class by construction rather than by enumeration. B. The _harvest_leaf helper: de-duplicate the three near-verbatim harvest sites (settle ordering, _empty_run_class / error_log= wiring). Kills the twin-blindness face. The code-review advisory flags this as a legitimate deferred Act candidate, refused in round 3 on the express grounds that "this patch is already oversized" — that refusal is the loop: the refactor that ends the class is declined because the slice is too big, so the class keeps producing findings, so the slice keeps growing. C. The bookkeeping half proper — per-attempt record persistence, crash-atomic flush, trailer defanging (criteria (i) and (iv)). This part has converged and is stable across rounds; keep it intact rather than rebuilding it. MUST BE SETTLED IN THE BRIEF, NOT LEFT TO THE BUILDER. leaves.py:773 — the patch narrows the shipped retry contract (measured: base spends 3 attempts, patch stops after 1 on a bundle write refusal; base 2 -> patch 1 on an unlink refusal), while criterion (vi) demands the contract "holds unchanged". As written the builder is asked to satisfy both and cannot, which is why this surfaced as a fitness question with no [impl] tag. The next brief must pick one explicitly: either sanction the narrowing, or adopt the adversary's no-cost alternative — carry owned=False forward and refuse to HARVEST on the success branch (the residue is already quoted by then) instead of ending the run. Leaving this ambiguous will reproduce the same finding next round. DO NOT LOSE (open [impl] items, to land in whichever child slice owns the surface): - assemble.py:85 — widen _LEAF_STATUS_LABEL[LEAF_STATUS_INFRA] exactly as the placeholder sentence was widened; _empty_run_class now routes runs whose last attempt exited 0. - leaves.py:1033-1034 — _residue_record asserts "withdrawn" as fact; false on the fail-closed path this patch adds. The re-flush hook at :768-769 is already in hand; the may_retry is False variant files the false line unamended. - leaves.py:825-828 — recorded, not raised: a stranded .tmp.<pid> sibling is claimed by no DOWNSTREAM_GLOBS pattern, so _archive_iteration never moves it either. §6 left open (3 items: T5 prior-art on the four non-leaves.py paths, fitness-to-purpose, size backstop). Not cleared — this is an iterate, not an accept.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  WHY REJECTED — slicing, not direction.
  The fix's direction is right and its proof is sound: all gates green, C4 independently
  re-run (23 failures + 4 errors on the red leg, 31/31 green, full 1789-test suite green,
  test_leaf_resilience.py untouched as criterion (vi) required). Nothing here says the work
  is unwanted. It is rejected because the slice is too big to converge: 5 builder attempts,
  4 sign-off rounds, patch 44 -> 68 -> 79 -> 93 -> 104 KB (threshold 80), with
  implementation-shaped adversary findings every single round (4, 4, 2, 3, 2). The size
  backstop fired at v4 and again at v5.

  THE ERROR CLASS TO DESIGN OUT (this is the actionable insight).
  The slice redefines the meaning of a shared signal — the presence/content of *.error.log
  ("the leaf ran and FAILED") is split into failed vs. merely-interrupted, plus a derived
  empty-run / leaf-status classification. That meaning has many independent readers, each
  hard-coding it at its own site. Every round converts the readers in view; the next round
  finds one more still speaking the old meaning:
    v1 assemble.py:417   — "the reviewer RAN AND FAILED"
    v2 driver.py:178-179 — "reviewer never ran"
    v3 leaves.py:2910    — "retries did not recover"
    v4 leaves.py:3176    — second #369 discriminator, unconverted
    v5 assemble.py:85    — "leaf did not run (transient infra — safe to re-run)"
  The adversary's phrase is exact: the patch widened the sentence it could see, "then stops
  one reader short." Note the axis MOVED rather than exhausted — v5 confirmed by grep that
  the *.error.log-as-state readers are now all converted, and the new finding is on a
  different shared value (the leaf-status enum -> label mapping).
  Two related faces of the same root (no single point of truth):
    - the patch's own new paths file false accounts — the very invariant the slice enforces
      (v1 human-empty misfiling, v2 "inert" docstring, v3 "retries did not recover",
      v5 the "withdrawn" line written over a file still present);
    - twin blindness — the mechanism is hand-copied at 3 harvest sites and 2 discriminators,
      so tests or _settle_leaf_record calls miss a twin (v1, v2 x2).
  Per-instance fixes cannot end this class. iterate-do would close the two named [impl]
  items and leave the generator intact.

  SPLIT SEAMS FOR THE RE-PLAN (candidates — Plan authors the briefs).
    A. Give the redefined meaning ONE owner: a single predicate/type that every reader
       consults (production branches, both #369 discriminators, assemble.py status labels
       and prose, driver.py operator messages). Ends the "stops one reader short" class by
       construction rather than by enumeration.
    B. The _harvest_leaf helper: de-duplicate the three near-verbatim harvest sites (settle
       ordering, _empty_run_class / error_log= wiring). Kills the twin-blindness face. The
       code-review advisory flags this as a legitimate deferred Act candidate, refused in
       round 3 on the express grounds that "this patch is already oversized" — that refusal
       is the loop: the refactor that ends the class is declined because the slice is too
       big, so the class keeps producing findings, so the slice keeps growing.
    C. The bookkeeping half proper — per-attempt record persistence, crash-atomic flush,
       trailer defanging (criteria (i) and (iv)). This part has converged and is stable
       across rounds; keep it intact rather than rebuilding it.

  MUST BE SETTLED IN THE BRIEF, NOT LEFT TO THE BUILDER.
  leaves.py:773 — the patch narrows the shipped retry contract (measured: base spends 3
  attempts, patch stops after 1 on a bundle write refusal; base 2 -> patch 1 on an unlink
  refusal), while criterion (vi) demands the contract "holds unchanged". As written the
  builder is asked to satisfy both and cannot, which is why this surfaced as a fitness
  question with no [impl] tag. The next brief must pick one explicitly: either sanction the
  narrowing, or adopt the adversary's no-cost alternative — carry owned=False forward and
  refuse to HARVEST on the success branch (the residue is already quoted by then) instead of
  ending the run. Leaving this ambiguous will reproduce the same finding next round.

  DO NOT LOSE (open [impl] items, to land in whichever child slice owns the surface):
    - assemble.py:85 — widen _LEAF_STATUS_LABEL[LEAF_STATUS_INFRA] exactly as the placeholder
      sentence was widened; _empty_run_class now routes runs whose last attempt exited 0.
    - leaves.py:1033-1034 — _residue_record asserts "withdrawn" as fact; false on the
      fail-closed path this patch adds. The re-flush hook at :768-769 is already in hand;
      the may_retry is False variant files the false line unamended.
    - leaves.py:825-828 — recorded, not raised: a stranded .tmp.<pid> sibling is claimed by
      no DOWNSTREAM_GLOBS pattern, so _archive_iteration never moves it either.

  §6 left open (3 items: T5 prior-art on the four non-leaves.py paths, fitness-to-purpose,
  size backstop). Not cleared — this is an iterate, not an accept.
- Full previous attempt preserved in `iteration-v5/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
