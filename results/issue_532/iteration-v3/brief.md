# driver: Do burns a whole attempt on transient infra, and a retried leaf can inherit a dead attempt's work

- **Slug:** an-attempt-is-the-unit-of-accountability
- **Defect:** The builder is the only leaf the harness never retries, and the retry path it
  is missing has two attempt-ownership holes of its own. All verified on the target base
  (`eduralph/pdca-harness` @ `main`, `acb214a`):
  * **Do is never retried.** `_do_build_command` calls plain `_invoke`
    (`template/src/pdca_harness/leaves.py:1824`), while the reviewer (`:2507`), the advisory
    (`:2840`) and the plan advisory (`:3142`) all run under `_invoke_leaf_resilient`
    (`:673-721` — bounded retry with backoff plus a per-attempt error log, #138). So **no**
    builder failure is ever retried — on the leaf where an attempt is most expensive, and
    where the #135 escalation ladder's deep tiers (opus/`--effort max`) run longest. The
    reported incident burned ~18 minutes and a whole cycle round to a dropped connection.
  * **The exhausted death explains nothing and its "next step" would be false.** `do_build`
    captures one record and re-raises (`:1765-1778`); what the operator reads is
    `build/check failed (LeafError: Command '[…]' returned non-zero exit status 1)` — an
    argv and an exit status. And the honest next action depends on what the dead attempt
    left behind: a bundle holding `patch.diff` reads **BUILT** (`state.py:211`), so
    `driver.advance` (`driver.py:76`) runs **Check** on that partial patch, not Do.
  * **A retry would inherit the dead attempt's work.** Two holes, both live the moment any
    leaf is retried after producing output: `_invoke_leaf_resilient` writes its attempt
    records only *after* the loop (`:720`), so while attempt 2 runs there is nothing on disk
    explaining attempt 1 (and a killed run loses them all); and the three harvest sites
    copy their artifact `if produced.exists()` — `:2519-2523` (`check-review.md`),
    `:2851-2854`, `:3152-3155` — with no notion of *which* attempt wrote it, so a truncated
    verdict from a dead attempt can be adopted as the leaf's own. `worktree.ensure` likewise
    runs once, before the wrapper (`:1791`), so a retried builder opens a worktree still
    carrying the dead attempt's edits and a bundle that may already hold `patch.diff` /
    `build-notes.md`.
- **Success criterion:** With the patch:
  (i) a **transient** builder death is retried, bounded, with backoff, under the same
  `_invoke_leaf_resilient` contract the reviewer/advisory leaves use, while a **substantive**
  builder failure is still not retried; either way the final failure is still captured to
  `build.error.log` and still re-raised, so `flow._isolate` drops just this bundle exactly as
  today;
  (ii) each attempt's error record is on disk **before** the next attempt starts, so a
  retried leaf — and a post-mortem of a run that was killed mid-retry — can read the
  predecessor's account instead of a file that does not exist yet;
  (iii) a retried **builder** is told in its prompt that a previous attempt died mid-flight
  and that any `patch.diff` / `build-notes.md` / test file present is that attempt's
  incomplete residue to verify or replace — never evidence the work is done;
  (iv) when the bounded retries are exhausted, what the operator reads names the transient
  classification, points at the on-disk account, and states a next action that is **true for
  the residue actually present** (naming, when a partial `patch.diff` was left, that the
  bundle now reads BUILT and a plain re-run would run Check on it); nothing deletes the
  builder's artifacts to make that sentence true;
  (v) no artifact written by a **dead** attempt is harvested as a **successful** attempt's
  output at the reviewer / advisory / plan-advisory sites;
  (vi) nothing else changes: the existing resilience contract holds unchanged (attempt count,
  backoff, the staleness clear at `:698-702`, the `_memory_log_for` pairing — derive it, do
  not pass `memory_log=` explicitly where the other three call sites do not), the
  memory-telemetry post-mortem (#420) still rides `output` into the same log, a successful
  build is spawned and reported exactly as today, and both offline suites stay green **and
  fast** (see Falsifiability).
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  * (i)/(iii)/(iv): `template/tests/test_leaf_resilience.py:28-40` already ships the harness
    this needs — `_TRANSIENT` (stderr only, no stream event → transient under *today's* rule),
    a leaf whose argv is `[sys.executable, "-c", script]`, and a `$CNT` file counting
    invocations. Driving `leaves.do_build` with such a builder counts **1** invocation today
    and must count the attempt budget after the fix; the prompt note and the exhausted
    message are assertions over the child's stdin and over captured stderr. That red needs no
    new classification, so this child is falsifiable on today's `origin/main` alone.
  * (ii): instrument from inside the stub leaf — attempt 2 asserts `build.error.log` exists
    and holds attempt 1's text. Today it does not exist until the loop ends.
  * (v): a first stub attempt that writes a truncated `check-review.md` into the sandbox and
    then dies transiently, followed by an attempt that exits 0 without writing → the harvest
    copies the dead attempt's file today. Genuine red on the current base.
  * **Wall-clock trap, read this before you build:** `template/tests/test_build_error_log.py:63-71`
    raises `LeafError(1, ["claude"], output="panic…")`, and `produced` defaults to `False`
    (`leaves.py:99`) so `.transient` is `True`. The moment `do_build` retries, that existing
    test spends the real backoff (4 s + 8 s) and calls its mock three times. Keep the suite
    fast **and** honest: make the attempt budget / backoff reachable from the test (or patch
    the sleep), and do **not** weaken `_invoke_leaf_resilient`'s shipped defaults to do it.
  * C4's red leg reverts the production hunks and keeps every `template/tests/*.py` hunk
    (`engine/scripts/run-verify.sh:214-217`), so appended cases earn a genuine red — provided
    the appended tests import no symbol this patch adds at module level: a red-leg import
    failure is recorded `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:231-233`). Note also
    that the C4 gate runs **every** test file the patch touches, so both test files below
    must be red-worthy and green.
- **Invariant to restore:** **An attempt is the unit of accountability.** Two halves, both
  stated over the category rather than this incident: (1) an infrastructure failure the leaf
  did not cause is the harness's to absorb — bounded — on **every** leaf it spawns, not on
  the three that happened to be given the wrapper; and (2) nothing a **dead** attempt left
  behind may be reported as a **live** attempt's work, and nothing the harness tells the
  operator or the retried leaf about that residue may be false. Self-test: it cannot be
  satisfied by guarding one module — the retry lives at the builder call site, the record
  flush inside the wrapper, the ownership at three harvest sites, the honesty in the
  operator's message. Source: internal project invariant (Tier C), the target's own written
  rules — `leaves.py:641-647` (why a captured tail exists at all: `(no output captured)` is
  "a post-mortem artifact that explains nothing", #286 review), `leaves.py:683-697` (the
  resilience contract #138 states), `engine/README.md:44-68` (no evidence must never be filed
  as a verdict). `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6
  category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` — the sibling child-2 is independent
  (neither needs the other to compile or to go red→green) and both build on `origin/main` in
  one wave, which is also what this instance's own #474 base-export leak makes preferable
  (`plan-0.60-bug-order.md`). The two children share `leaves.py` but in disjoint regions —
  this one owns the wrapper **body**, `do_build`, and the harvest sites; child-2 owns only
  the four prose sites that restate the transient definition — and they ship tests in
  **different files** by construction. Recommended merge order at publish: **this child
  first**, then child-2, because child-2 is what first makes a leaf retryable *after* it has
  produced work, and this child is what makes that safe.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** Who gets retried, what a retry may inherit, and what the operator is told when
  the retries run out — the leaf-invocation layer of #506. Put the builder on the existing
  resilient path; flush each attempt's record as it happens; tell a retried builder that a
  predecessor died mid-flight and that any artifacts present are its residue; make the
  exhausted-retry report name the class of failure, where its account is, and a next action
  that matches the residue actually on disk; and give the three artifact harvests a notion of
  which attempt produced what.
  **Out of scope:** the stream-side question of *what counts as* a transient death and the
  retention of the leaf's own error text — that is sibling child-2, and this child must not
  touch `progress.py` or change the transient rule; a lane/worktree reset between attempts,
  and any new `pdca.toml` knob (reuse the shipped attempts/backoff defaults — a prompt-level
  statement of the residue is the bounded fix; if the rebuild concludes that is insufficient,
  say so in `build-notes.md` rather than expanding the slice); the gate-side transient
  (issue #371 — the same argument one layer down, its own slice); a leaf **signal-death**
  under the memory cap (issue #510 states it "is neither #506's transient nor #421's
  preflight" — do not fold it in); `flow._isolate`'s containment contract and the `flow_one`
  library route's propagation (`flow.py:302-306` documents why the single-issue path differs);
  the memory-telemetry post-mortem (#420), which must keep working unchanged.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today; read
     `:28-40` for the stub-leaf harness and `$CNT` counter this child reuses.
  2. Read the gap: `leaves.py:1824` (`_invoke`, not `_invoke_leaf_resilient`) against the
     three peer call sites `:2507`, `:2840`, `:3142`; `:720` (records written only after the
     loop); `:2519-2523` / `:2851-2854` / `:3152-3155` (`if produced.exists()`, attempt-blind);
     `:1765-1778` (what a failed Do prints); `state.py:211` + `driver.py:76` (why a bundle
     left holding `patch.diff` goes to Check, not Do).
  3. The live incident is named in the parent issue: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`), failing tier = the
     `[[leaves.builder_escalation]]` opus/max entry; an identical re-run minutes later
     succeeded.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter, so the slice builds and goes red→green with no
  vendor CLI, no API key, no network and no container.
- **Test file:** `template/tests/test_leaf_resilience.py` (append — it owns the
  `_invoke_leaf_resilient` contract, #138) **and** `template/tests/test_build_error_log.py`
  (the sibling that pins `build.error.log`'s shape and archival; update it here — it is this
  child's file, and see the wall-clock trap above). Do **not** create
  `template/tests/fixtures/` and do **not** add `template/tests/test_terminal_error_classification.py`:
  both belong to sibling child-2, which builds on the same base in the same wave.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `_invoke_leaf_resilient` (`leaves.py:673-721`) is the wrapper to reuse **as it is**:
    its staleness clear (`:698-702`), its `_memory_log_for` derivation, its `records` list and
    the `_format_leaf_attempt` record format (`:724-730`);
  * the three peer call sites that already compose it — `:2507` (reviewer), `:2840`
    (advisory), `:3142` (plan advisory) — show the shape to mirror (`err = _invoke_leaf_resilient(…)`,
    then act on `err`). `do_build`'s outer contract differs and must survive: its failure is
    captured to `build.error.log` **and re-raised** (`:1765-1778`), and its stale-log clear
    (`:1747-1753`) plus the archive rule pinned by `test_build_error_log.py:91-105` still hold
    — a wrapper that writes per-attempt records must not then be overwritten by the outer
    capture;
  * `_stub_build` (`:1755`) and `select_builder` (`:1746`) bound the change: a stub backend
    must behave exactly as today;
  * honesty inputs for the exhausted-retry message: `state.py:211` (a bundle holding
    `patch.diff` reads BUILT) and `driver.py:76` (BUILT → Check).
  * **Prior art you may read, selectively:** the rejected single-slice attempt is archived at
    `results/issue_506/iteration-v4/patch.diff` (+ `build-notes.md`). Its **leaf-side** hunks
    were independently confirmed four rounds running and were rejected for slice size, not
    mechanism, so you may read them for decisions already settled. Read **only** the hunks for
    the files this child owns — re-applying the `progress.py` / `tests/fixtures/` /
    `test_terminal_error_classification` material would recreate the oversized slice this
    split exists to undo — and re-verify anything you take against the current base rather
    than trusting it.

  **Path convention in this brief:** every `template/…` and `tests/…` path is on the **target
  branch** (eduralph/pdca-harness @ main) — the files Do reads and edits. Every `engine/…`,
  `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification engine
  and the bundles that run the cycle); they are cited to explain how the gates will judge the
  patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/leaves.py` — `_invoke_leaf_resilient` arrived with #138 for the
  reviewer/advisory leaves and was never extended to the builder; `do_build`'s error capture
  is #279/#286; the most recent touch of `_invoke` is `0881af9` (#420 memory sampling). Open
  PRs on the target (`gh pr list -R eduralph/pdca-harness --state open`): #519-#525, of which
  #524 (issue 494) and #520 (issue 466) touch `leaves.py` at distant regions (`:782`,
  `:3261`, `:3400`, `:3465`; `do_split`) — no overlap with this child's regions. Open issues
  searched for `retry` / `transient`: #371 (gate-row transient red) and #510 (signal death)
  are adjacent and deliberately excluded above; #509 (crash-resume) is a different beat. Not
  previously attempted as its own slice, not rejected; the parent 506's four-round attempt was
  rejected on slicing (`results/issue_506/iteration-v4/SUMMARY.md` §9).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the open findings in this bundle's own Check record, not on the approach: the slice's shape is right, the implementation is not yet correct. Must close before re-submission: 1. Fail-closed artifact ownership (`leaves.py:783`) — the reviewer's C3/T3 FAIL. When the rename AND the fallback unlink both raise, the error is suppressed and control continues, leaving a dead attempt's artifact harvestable — the opposite of the invariant the code's own diagnostic claims. 2. The #369 trap-door regression (`leaves.py:742`) — the per-attempt flush, which is criterion (ii) itself, disarms recovery for a run killed mid-retry. `review_never_ran` is "no artifact AND no error log"; attempt 1's record now exists, so the reviewer is never re-run and the bundle can reach sign-off with NO review of the diff. This violates criterion (vi). Decide which contract yields (an in-flight suffix, or teach the discriminator that a record short of the attempt budget is not "ran and failed"). 3. Signal-death scope leak (`leaves.py:1883-1886`) — a builder SIGKILLed under the #420 memory cap exits -9 with produced=False, so it is classified transient: 3 spawns instead of 1, each repeating whatever exhausted the bound, while stderr asserts it was absorbed infra and build.error.log says otherwise. #510 is out of scope per the brief; this patch must not extend the classifier to it. 4. Exhausted-retry next action (`leaves.py:1888-1894`) — ask `state.state(d)`, do not infer from `patch.diff` existence. Confirmed at sign-off by reading `state.py`: state() is a waterfall, so a bundle holding patch.diff AND check-gates.json returns CHECKED, not BUILT, and the printed advice is false exactly on the bundle its own previous advice creates. (The code-review lens cleared this by reading only the first rung; the adversary is correct.) 5. `_disown_artifact` (`leaves.py:775-777`) — the rename target is inside the temp sandbox that is destroyed on exit, so "stays readable beside it" is false at all three call sites: a real verdict is discarded while the operator is told none was produced. Copy the disowned file into the bundle. 6. The `residue` list is computed and dropped on the floor in the no-patch branch (`leaves.py:1887,1895-1898`) — the operator is told inputs are intact while a half-written build-notes.md (and any brief-named test file) is on disk, inherited by a re-driven Do without the retry note. Also: the C5-prod-path green is vacuous ("patch adds no new test file"). The appended cases were only hand-checked. Make production-path coverage adjudicable next round. Not iterate-plan: the four concerns (retry the builder, per-attempt accountability, residue awareness, operator reporting) were weighed as one outcome and kept in one slice.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the open findings in this bundle's own Check record, not on the approach:
  the slice's shape is right, the implementation is not yet correct.

  Must close before re-submission:

  1. Fail-closed artifact ownership (`leaves.py:783`) — the reviewer's C3/T3 FAIL. When the
     rename AND the fallback unlink both raise, the error is suppressed and control
     continues, leaving a dead attempt's artifact harvestable — the opposite of the
     invariant the code's own diagnostic claims.

  2. The #369 trap-door regression (`leaves.py:742`) — the per-attempt flush, which is
     criterion (ii) itself, disarms recovery for a run killed mid-retry. `review_never_ran`
     is "no artifact AND no error log"; attempt 1's record now exists, so the reviewer is
     never re-run and the bundle can reach sign-off with NO review of the diff. This
     violates criterion (vi). Decide which contract yields (an in-flight suffix, or teach
     the discriminator that a record short of the attempt budget is not "ran and failed").

  3. Signal-death scope leak (`leaves.py:1883-1886`) — a builder SIGKILLed under the #420
     memory cap exits -9 with produced=False, so it is classified transient: 3 spawns
     instead of 1, each repeating whatever exhausted the bound, while stderr asserts it was
     absorbed infra and build.error.log says otherwise. #510 is out of scope per the brief;
     this patch must not extend the classifier to it.

  4. Exhausted-retry next action (`leaves.py:1888-1894`) — ask `state.state(d)`, do not infer
     from `patch.diff` existence. Confirmed at sign-off by reading `state.py`: state() is a
     waterfall, so a bundle holding patch.diff AND check-gates.json returns CHECKED, not
     BUILT, and the printed advice is false exactly on the bundle its own previous advice
     creates. (The code-review lens cleared this by reading only the first rung; the
     adversary is correct.)

  5. `_disown_artifact` (`leaves.py:775-777`) — the rename target is inside the temp sandbox
     that is destroyed on exit, so "stays readable beside it" is false at all three call
     sites: a real verdict is discarded while the operator is told none was produced. Copy
     the disowned file into the bundle.

  6. The `residue` list is computed and dropped on the floor in the no-patch branch
     (`leaves.py:1887,1895-1898`) — the operator is told inputs are intact while a
     half-written build-notes.md (and any brief-named test file) is on disk, inherited by a
     re-driven Do without the retry note.

  Also: the C5-prod-path green is vacuous ("patch adds no new test file"). The appended
  cases were only hand-checked. Make production-path coverage adjudicable next round.

  Not iterate-plan: the four concerns (retry the builder, per-attempt accountability,
  residue awareness, operator reporting) were weighed as one outcome and kept in one slice.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the implementation, not the slice. The shape is right and all six of the previous round's carry-forwards are genuinely closed with real red->green tests; what remains are local code defects, each confirmed by reading patch.diff directly. Do NOT re-cut this slice and do NOT re-attempt the previous approach unchanged. Must close before re-submission: 1. The retry starts even when the attempt record failed to write — criterion (ii) head-on. `_write_attempt_records` catches OSError, prints, and returns None; the loop computes `retry = retry_when(exc) and attempt < attempts and owned` BEFORE the write and never learns it failed, so attempt N+1 launches with attempt N's account absent from disk. Make starting attempt N+1 contingent on attempt N's record being durably written (return the write's success and fold it into `retry`, the same way `owned` already gates it). This is the patch's central invariant having a fail-open branch — it is the reviewer's C3/T3/T5 FAIL, which are one defect counted three times. Note `do_build`'s `if not _has_content(error_log)` guard does still capture the FINAL failure; what is lost is the per-attempt account during the retry window, and everything if the run is killed in that window. 2. An unguarded stderr write can replace the exception criterion (i) pins. `_report_exhausted_do_retries(d, exc)` sits OUTSIDE `do_build`'s `try: ... except OSError: pass` ("never let error-capture mask the real failure"), immediately before `raise`. BrokenPipeError is an OSError subclass, so a broken stderr turns the LeafError into a BrokenPipeError on the way out; the retry notice inside `_invoke_leaf_resilient` has the same shape. Criterion (i) requires the final failure to be captured and re-raised either way. Bring both prints under the guard. 3. The exhausted-retry message asserts authorship it cannot know. `_do_residue` is a pure existence check with no provenance, but the caller prints "the interrupted attempt left ...". A transient death by definition produced nothing, so those files are usually an EARLIER run's — making that sentence false in the one place the brief's invariant governs ("nothing the harness tells the operator about that residue may be false"). Name the files without claiming authorship, e.g. "the bundle holds ..., which may predate this attempt". Carry-forward item 6 asked for these files to be named, not for their provenance to be invented. 4. The signal-death carve-out is one wrapper deep — the previous round's item 3 reached through a different door. `_builder_retryable` excludes only `rc < 0`, but a wrapper argv (`sh -c`, `docker run`, the documented `local-build` shape) reports its child's OOM SIGKILL as 137 — positive. That is retried three times while stderr asserts "infra the harness absorbs" and build.error.log says `Killed`. The docstring's premise ("subprocess reports a signal death as a NEGATIVE returncode") holds only when argv[0] is the process that dies. Either widen the exclusion (128+n) or state explicitly why the hole is left to #510 — but do not leave it made silently. Worth a test either way. 5. A leaf that finished is left flagged "in flight" (one-line fix). On the deliberately-retained-log path — a dead attempt's artifact was withdrawn and the winning attempt wrote none — the last write was `in_flight=True` and the success path does not re-flush, so `leaf_run_incomplete()` returns True for a loop that finished, contradicting its own docstring. Re-flush with `in_flight=False` before returning success. Related fragility worth a look while you are there: that predicate is a substring sniff over a body that now embeds up to 20 000 characters of the leaf's own artifact, so a verdict that QUOTES the marker makes a completed log read as interrupted. SCOPE CONSTRAINT — LEAVE THE PROSE ALONE (decided at sign-off, binding on this rebuild): Do NOT touch the `_invoke_leaf_resilient` DOCSTRING or the retry-backoff PRINT line (`leaves.py:693-704` and `:728-730` on the base). Those two prose sites belong to sibling issue_533, which is landing its own rewrite of them, and which has been told at sign-off to keep them. This child owns the FUNCTION BODY, `do_build`, and the harvest sites — the mechanism, not the wording. Why this is binding and not a style note: verified mechanically at sign-off that the two patches collide. Both rewrite the same retry-print line, and the collision is SEMANTIC as well as textual — this round's version keeps "with no output (transient)", which is exactly the definition 533 exists to retire, so if this child lands second and wins that hunk the operator-facing prose silently regresses to the wrong contract. This round's patch also rewrites the docstring 533 rewrites, and deletes an `error_log.write_text(...)` line that sits in 533's trailing context. Keep the label-prefix improvement if it is still wanted (`kw.get('label') or workdir.name` — a real fix, since `workdir` names the sandbox or the harness root, not the bundle), but apply it WITHOUT restating the transient definition: take 533's wording for the classification clause and change only the name. Recommended merge order is unchanged (this child first, then 533), so expect 533's prose to land on top. Related, and worth settling with the sibling rather than alone: the signal-death boundary. This child's `_builder_retryable` excludes `rc < 0` but misses a positive 137; 533's `died_of_reported_infra` excludes neither. Same boundary, opposite holes, two children each inventing half of it. 533's carry-forward carries the mirror of this note. Non-blocking, close if cheap: `driver.py:152-155` still documents the old recovery rule ("no artifact, no error log") — the reading this patch had to abandon, and the last sentence in the codebase stating the old contract; `_do_residue`'s docstring overclaims parity with `_stub_build`'s `Path("test_stub.py")` fallback, which it does not share. C5 remains vacuously green ("patch adds no new test file") for the second round running, because the brief directs appending to existing files. Not a reason to reject, and the C4 red/green log does make the appended cases adjudicable — but it means C5 is carrying no weight on this bundle and should not be read as evidence. Section 6 (Validation — fitness-to-purpose) is deliberately left OPEN: no real interrupted provider session was induced. Findings 2, 3 and 4 above are each a case where the operator-facing wording is factually wrong, which is that item's substance and should be re-examined once they are closed.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the implementation, not the slice. The shape is right and all six of the
  previous round's carry-forwards are genuinely closed with real red->green tests; what
  remains are local code defects, each confirmed by reading patch.diff directly. Do NOT
  re-cut this slice and do NOT re-attempt the previous approach unchanged.

  Must close before re-submission:

  1. The retry starts even when the attempt record failed to write — criterion (ii)
     head-on. `_write_attempt_records` catches OSError, prints, and returns None; the loop
     computes `retry = retry_when(exc) and attempt < attempts and owned` BEFORE the write
     and never learns it failed, so attempt N+1 launches with attempt N's account absent
     from disk. Make starting attempt N+1 contingent on attempt N's record being durably
     written (return the write's success and fold it into `retry`, the same way `owned`
     already gates it). This is the patch's central invariant having a fail-open branch —
     it is the reviewer's C3/T3/T5 FAIL, which are one defect counted three times. Note
     `do_build`'s `if not _has_content(error_log)` guard does still capture the FINAL
     failure; what is lost is the per-attempt account during the retry window, and
     everything if the run is killed in that window.

  2. An unguarded stderr write can replace the exception criterion (i) pins.
     `_report_exhausted_do_retries(d, exc)` sits OUTSIDE `do_build`'s
     `try: ... except OSError: pass` ("never let error-capture mask the real failure"),
     immediately before `raise`. BrokenPipeError is an OSError subclass, so a broken stderr
     turns the LeafError into a BrokenPipeError on the way out; the retry notice inside
     `_invoke_leaf_resilient` has the same shape. Criterion (i) requires the final failure
     to be captured and re-raised either way. Bring both prints under the guard.

  3. The exhausted-retry message asserts authorship it cannot know. `_do_residue` is a pure
     existence check with no provenance, but the caller prints "the interrupted attempt
     left ...". A transient death by definition produced nothing, so those files are
     usually an EARLIER run's — making that sentence false in the one place the brief's
     invariant governs ("nothing the harness tells the operator about that residue may be
     false"). Name the files without claiming authorship, e.g. "the bundle holds ..., which
     may predate this attempt". Carry-forward item 6 asked for these files to be named, not
     for their provenance to be invented.

  4. The signal-death carve-out is one wrapper deep — the previous round's item 3 reached
     through a different door. `_builder_retryable` excludes only `rc < 0`, but a wrapper
     argv (`sh -c`, `docker run`, the documented `local-build` shape) reports its child's
     OOM SIGKILL as 137 — positive. That is retried three times while stderr asserts "infra
     the harness absorbs" and build.error.log says `Killed`. The docstring's premise
     ("subprocess reports a signal death as a NEGATIVE returncode") holds only when argv[0]
     is the process that dies. Either widen the exclusion (128+n) or state explicitly why
     the hole is left to #510 — but do not leave it made silently. Worth a test either way.

  5. A leaf that finished is left flagged "in flight" (one-line fix). On the
     deliberately-retained-log path — a dead attempt's artifact was withdrawn and the
     winning attempt wrote none — the last write was `in_flight=True` and the success path
     does not re-flush, so `leaf_run_incomplete()` returns True for a loop that finished,
     contradicting its own docstring. Re-flush with `in_flight=False` before returning
     success. Related fragility worth a look while you are there: that predicate is a
     substring sniff over a body that now embeds up to 20 000 characters of the leaf's own
     artifact, so a verdict that QUOTES the marker makes a completed log read as
     interrupted.

  SCOPE CONSTRAINT — LEAVE THE PROSE ALONE (decided at sign-off, binding on this rebuild):
  Do NOT touch the `_invoke_leaf_resilient` DOCSTRING or the retry-backoff PRINT line
  (`leaves.py:693-704` and `:728-730` on the base). Those two prose sites belong to sibling
  issue_533, which is landing its own rewrite of them, and which has been told at sign-off
  to keep them. This child owns the FUNCTION BODY, `do_build`, and the harvest sites — the
  mechanism, not the wording.

  Why this is binding and not a style note: verified mechanically at sign-off that the two
  patches collide. Both rewrite the same retry-print line, and the collision is SEMANTIC as
  well as textual — this round's version keeps "with no output (transient)", which is
  exactly the definition 533 exists to retire, so if this child lands second and wins that
  hunk the operator-facing prose silently regresses to the wrong contract. This round's
  patch also rewrites the docstring 533 rewrites, and deletes an `error_log.write_text(...)`
  line that sits in 533's trailing context.

  Keep the label-prefix improvement if it is still wanted (`kw.get('label') or
  workdir.name` — a real fix, since `workdir` names the sandbox or the harness root, not the
  bundle), but apply it WITHOUT restating the transient definition: take 533's wording for
  the classification clause and change only the name. Recommended merge order is unchanged
  (this child first, then 533), so expect 533's prose to land on top.

  Related, and worth settling with the sibling rather than alone: the signal-death boundary.
  This child's `_builder_retryable` excludes `rc < 0` but misses a positive 137; 533's
  `died_of_reported_infra` excludes neither. Same boundary, opposite holes, two children
  each inventing half of it. 533's carry-forward carries the mirror of this note.

  Non-blocking, close if cheap: `driver.py:152-155` still documents the old recovery rule
  ("no artifact, no error log") — the reading this patch had to abandon, and the last
  sentence in the codebase stating the old contract; `_do_residue`'s docstring overclaims
  parity with `_stub_build`'s `Path("test_stub.py")` fallback, which it does not share.

  C5 remains vacuously green ("patch adds no new test file") for the second round running,
  because the brief directs appending to existing files. Not a reason to reject, and the C4
  red/green log does make the appended cases adjudicable — but it means C5 is carrying no
  weight on this bundle and should not be read as evidence.

  Section 6 (Validation — fitness-to-purpose) is deliberately left OPEN: no real interrupted
  provider session was induced. Findings 2, 3 and 4 above are each a case where the
  operator-facing wording is factually wrong, which is that item's substance and should be
  re-examined once they are closed.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 3 — carry-forward (from the previous attempt)
- Sign-off rationale: Human rationale (sign-off, issue_532): iterate-plan to settle the C5 item. What the re-plan must author: - C5 ("added test exercises production, not a copy") has been vacuously green three rounds running — "patch adds no new test file — nothing to assert" — because the brief directs appending to existing test files. Round 1's sign-off carry-forward already asked for this and it is still unclosed. The next brief must make production-path coverage adjudicable instead of leaving C5 carrying no weight; hand-reading in its place is how the two unfaithful-stub findings below survived. - Slice size: 82 KB against the 80 KB backstop, and round 3 of implementation-shaped findings every round. Author the split at Plan (`pdca-pdca split 532`, then `pdca-pdca split 532 --accept`) rather than re-cutting it in Do. - Criterion (iv) is not implementable as written. The exhausted-retry report is gated on `_builder_retryable`, but transient means the attempt produced nothing, so the BUILT / "partial patch.diff" branch is unreachable in production — while the half-written-patch shape the brief's own defect bullet names is classified substantive and gets no report at all. The brief must settle whether the residue + next-action lines print for every failed Do, or drop the claim. - Carry into whichever child keeps the mechanism: `_format_leaf_attempt` does not run `_defang_in_flight` over the captured stderr tail, so a leaf that spent its whole budget but whose stderr ends on a line equal to the marker reads as merely interrupted and buys extra spawns (reviewer C3/T3/T5, both advisory lenses, verified end-to-end on the production path). The fix is small; the test must place the marker alone on its own final line, not mid-line. - The T1 scope constraint versus sibling #533 (leave the `_invoke_leaf_resilient` docstring and the retry-backoff print wording to 533) was honored this round — keep it binding through the re-slice. §6 NEEDS-HUMAN items were left open — none were cleared.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Human rationale (sign-off, issue_532): iterate-plan to settle the C5 item.

  What the re-plan must author:

  - C5 ("added test exercises production, not a copy") has been vacuously green three
    rounds running — "patch adds no new test file — nothing to assert" — because the
    brief directs appending to existing test files. Round 1's sign-off carry-forward
    already asked for this and it is still unclosed. The next brief must make
    production-path coverage adjudicable instead of leaving C5 carrying no weight;
    hand-reading in its place is how the two unfaithful-stub findings below survived.

  - Slice size: 82 KB against the 80 KB backstop, and round 3 of implementation-shaped
    findings every round. Author the split at Plan (`pdca-pdca split 532`, then
    `pdca-pdca split 532 --accept`) rather than re-cutting it in Do.

  - Criterion (iv) is not implementable as written. The exhausted-retry report is gated
    on `_builder_retryable`, but transient means the attempt produced nothing, so the
    BUILT / "partial patch.diff" branch is unreachable in production — while the
    half-written-patch shape the brief's own defect bullet names is classified
    substantive and gets no report at all. The brief must settle whether the residue +
    next-action lines print for every failed Do, or drop the claim.

  - Carry into whichever child keeps the mechanism: `_format_leaf_attempt` does not run
    `_defang_in_flight` over the captured stderr tail, so a leaf that spent its whole
    budget but whose stderr ends on a line equal to the marker reads as merely
    interrupted and buys extra spawns (reviewer C3/T3/T5, both advisory lenses, verified
    end-to-end on the production path). The fix is small; the test must place the marker
    alone on its own final line, not mid-line.

  - The T1 scope constraint versus sibling #533 (leave the `_invoke_leaf_resilient`
    docstring and the retry-backoff print wording to 533) was honored this round — keep
    it binding through the re-slice.

  §6 NEEDS-HUMAN items were left open — none were cleared.
- Full previous attempt preserved in `iteration-v3/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
