# Brief — issue 532 / an-attempt-is-the-unit-of-accountability

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.
> Re-planned after iterate-plan at round 3 (`iteration-v3/session-carry-forward`).
> All `path:line` below re-verified against `eduralph/pdca-harness @ main, acb214a`
> during this Plan session — the base has not moved since round 3.

- **Slug:** an-attempt-is-the-unit-of-accountability
- **Defect:** The harness spawns leaves in bounded-retry loops, but nothing ties an
  artifact, an error record, or an operator sentence to the *attempt that produced it*.
  Three consequences, all live on the base:
  * **Do is never retried.** `_do_build_command` calls plain `_invoke`
    (`leaves.py:1824`), while the reviewer (`:2507`), the advisory (`:2840`) and the plan
    advisory (`:3142`) all run under `_invoke_leaf_resilient` (`:673-721`). So no builder
    failure is ever retried — on the leaf where an attempt is most expensive. The reported
    incident burned ~18 minutes and a cycle round to a dropped connection.
  * **A retried leaf inherits a dead attempt's work.** `_invoke_leaf_resilient` writes its
    attempt records only *after* the loop (`:720`), so while attempt 2 runs there is nothing
    on disk explaining attempt 1, and a killed run loses them all. The three harvest sites
    copy their artifact on a bare existence test — `:2520` (`check-review.md`), `:2851`,
    `:3152` — with no notion of *which* attempt wrote it, so a truncated verdict from a dead
    attempt is adopted as the leaf's own. This is live **today**, without any builder
    retry: those three leaves already retry.
  * **The exhausted death explains nothing.** `do_build` captures one record and re-raises
    (`:1765-1778`); the operator reads an argv and an exit status. What the honest next
    action *is* depends on residue: a bundle holding `patch.diff` reads BUILT
    (`state.py:224`), so `driver.advance` (`driver.py:76`) runs **Check** on that partial
    patch, not Do.
- **Success criterion:** With the patch:
  (i) a **transient** builder death is retried, bounded, with backoff, under the same
  `_invoke_leaf_resilient` contract the other three leaves use, while a **substantive**
  builder failure is still not retried; either way the final failure is still captured to
  `build.error.log` and still re-raised, so `flow._isolate` drops just this bundle as today;
  (ii) each attempt's error record is on disk **before** the next attempt starts, so a
  retried leaf — and a post-mortem of a run killed mid-retry — can read the predecessor's
  account instead of a file that does not exist yet;
  (iii) a retried **builder** is told in its prompt that a previous attempt died mid-flight
  and that any `patch.diff` / `build-notes.md` / test file present is that attempt's
  incomplete residue to verify or replace — never evidence the work is done;
  (iv) **every** failed Do — transient or substantive — prints the residue actually on disk
  and the next action true for it (naming, when a `patch.diff` was left, that the bundle now
  reads BUILT and a plain re-run runs Check on it); only the *"transient — absorbed after N
  attempts"* sentence is conditioned on the failure having been classified transient.
  Nothing deletes the builder's artifacts to make that sentence true. **(Settled at this
  re-plan — see Ordering note §2; round 3's gating of the whole report on retryability made
  the residue branch unreachable in production.)**
  (v) no artifact written by a **dead** attempt is harvested as a **successful** attempt's
  output at the reviewer / advisory / plan-advisory sites, and no dead attempt's captured
  stderr can impersonate the harness's own in-flight trailer: whatever marker distinguishes
  an interrupted log from a spent one must be neutralised in **both** the withdrawn-artifact
  text and the `_format_leaf_attempt` stderr tail (`:724-730`), which today embeds
  `exc.output` raw;
  (vi) nothing else changes: the shipped resilience contract holds unchanged (attempt count,
  backoff, the staleness clear at `:698-702`, the `_memory_log_for` derivation — derive it,
  do not pass `memory_log=` where the other three call sites do not; the builder's current
  explicit `memory_log=d / BUILD_MEMORY_LOG` at `:1830` derives to the identical file), the
  #420 memory-telemetry post-mortem still rides `output` into the same log, a successful
  build is spawned and reported exactly as today, `_stub_build` (`:1889`) behaves exactly as
  today, and both offline suites stay green **and fast** (see Falsifiability).
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  * `template/tests/test_leaf_resilience.py:26-35` already ships the harness this needs:
    `_TRANSIENT` (stderr only, no stream event → transient under today's rule), `_SUBSTANTIVE`
    (emits `{"type":"assistant"}` first), a leaf whose argv is `[sys.executable, "-c", script]`,
    and a `$CNT` file counting invocations. **Copy that harness into the new test files** —
    do not import it across modules.
  * (i): driving `leaves.do_build` with such a builder counts **1** invocation today and must
    count the attempt budget after the fix. (iii)/(iv) are assertions over the child's stdin
    and over captured stderr. (ii): instrument from inside the stub leaf — attempt 2 asserts
    `build.error.log` exists and holds attempt 1's text; today it does not exist until the
    loop ends. (v): a first stub attempt that writes a truncated `check-review.md` into the
    sandbox then dies transiently, followed by an attempt that exits 0 without writing → the
    harvest copies the dead attempt's file today. All genuine reds on the current base.
  * **The marker leg must put the marker ALONE on its own final line.** Round 3 shipped this
    test with the marker embedded mid-line (`"echo of the source: " + marker`), which is not
    the failure mode; the equality test is against the log's last non-blank line.
  * **Wall-clock trap, read before you build:** `template/tests/test_build_error_log.py:63-70`
    raises `LeafError(1, ["claude"], output="panic…")` and `produced` defaults to `False`
    (`leaves.py:99`), so `.transient` is `True`. The moment `do_build` retries, that existing
    test spends the real backoff (4 s + 8 s) and calls its mock three times. Keep the suite
    fast **and** honest: make the attempt budget / backoff reachable from the test (or patch
    the sleep). Do **not** weaken `_invoke_leaf_resilient`'s shipped defaults to do it.
  * **C4 red-leg import trap — this is why the test file is new.** The red leg reverts the
    production hunks and keeps every `tests/*` and `template/tests/*` hunk
    (`engine/scripts/run-verify.sh:214`), so a new file earns a genuine red — **provided it
    imports no symbol this patch adds at module level**: a red-leg import failure is recorded
    `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:189,232`). Import only pre-existing API at
    module level (`from pdca_harness import leaves`) and exercise the behaviour through
    pre-existing entry points (`leaves.do_build`, `leaves._run_review_sandboxed`), so the
    assertions are behavioural rather than symbol-existence. The C4 gate runs **every** test
    file the patch touches, so each must be red-worthy and green.
- **Invariant to restore:** **An attempt is the unit of accountability.** Two halves, stated
  over the category rather than this incident: (1) an infrastructure failure the leaf did not
  cause is the harness's to absorb — bounded — on **every** leaf it spawns, not on the three
  that happened to be given the wrapper; and (2) nothing a **dead** attempt left behind may be
  reported as a **live** attempt's work, and nothing the harness tells the operator or the
  retried leaf about that residue may be false. Self-test: it cannot be satisfied by guarding
  one module — the retry lives at the builder call site, the record flush inside the wrapper,
  the ownership at three harvest sites, the honesty in the operator's message. Source:
  internal project invariant (Tier C), the target's own written rules — `leaves.py:641-647`
  (why a captured tail exists at all: `(no output captured)` is "a post-mortem artifact that
  explains nothing", #286 review), `leaves.py:683-697` (the #138 resilience contract),
  `engine/README.md:44-68` (no evidence must never be filed as a verdict). `docs/principles.md`
  §5/§6 are unfilled scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** Three decisions this re-plan settles, each recorded here so a child
  brief inherits them rather than re-litigating:
  1. **C5 was vacuously green three rounds running.** `engine/scripts/run-prod-path.py` keys
     on *newly added* test files; round 3's brief directed appending to two existing files, so
     the gate printed "patch adds no new test file — nothing to assert" and carried no weight
     — which is how two unfaithful-stub findings survived to the adversary. This brief
     therefore ships the regression in **new** files under `template/tests/`.
  2. **Criterion (iv) is settled as "report for every failed Do".** `LeafError.transient` is
     `not produced` (`leaves.py:104-108`) and `produced` means a substantive stream event
     arrived (`progress.py:144-155`) — so a transient death did no tool work and *cannot* have
     written `patch.diff`. Gating the whole report on retryability made its residue branch
     unreachable in production while the half-written-patch shape the Defect names got nothing.
     Only the transient-classification sentence stays conditioned.
  3. **The transient rule is reused exactly as shipped — this slice changes nothing about
     it.** Putting the builder on the retry path means it now spends the attempt budget on
     whatever `LeafError.transient` (`leaves.py:103-108`) currently classifies; that is the
     one genuine coupling this slice has to the classification question, and it is a *cost*,
     not a defect to fix here. Measured on the base: a builder that OOMs after doing work has
     `produced=True` → substantive → is **not** retried (the expensive case is already safe),
     and the transient-classified shape that dominates — systemd-oomd killing the leaf's own
     scope under session-wide pressure from a concurrent leaf (`leaves.py:232-234`) — is
     genuine transient infra a retry *should* absorb. So no signal-death exclusion is
     authored here. If sign-off judges the resulting retry set wrong **for the builder
     specifically**, that is sibling #533's slice (it owns `progress.py` and the definition)
     or #510's, not a reason to widen this one. Neither child may redefine `.transient`,
     touch `progress.py`, or add a signal-death predicate.
  **Scheduling — this bundle's two children run as two waves in this run; #533 schedules
  itself.** Neither child needs #533 to compile or to go red→green, and no ordering field
  names it. That is a *mechanical* constraint, not a judgement that they are disjoint:
  #533's children do not exist yet, a `Depends on` naming a non-existent id aborts the whole
  run (`waves.py:77-81`), and a `Conflicts with` naming an out-of-batch id is silently
  dropped (`waves.py:104-109`) — so no edge authorable from here would do anything but
  break or nothing. **#533's Plan session authors the edge**, since it will know these
  children's ids; note that `Conflicts with` is *undirected* and oriented by deterministic
  id order (`waves.py:19-22`), so if child-1 must land first that has to be a directed
  `Depends on` on the #533 side.
  **What #533's planner needs from this bundle — measured, not assumed.** #533's round-3
  `leaves.py` footprint is +52/−33 and is almost entirely prose (its real code is
  `progress.py`, +422/−2). Against child-1's regions exactly **one** collides:
  * `leaves.py:714-720` — #533 rewrites the retry-backoff **print string** at line 717;
    child-1 must **move** `error_log.write_text(…)` at line 720 into the loop (criterion
    (ii)). Three lines apart, inside each other's diff context ⇒ whichever lands second
    rebases. Round 3's T1 constraint ("leave the print wording to #533") was honoured and
    would **not** have prevented this, because child-1 must change 720 regardless. State the
    constraint at the real hazard: child-1 owns the loop **body**, #533 owns the **strings
    and comments** in that function; expect 717 to move under you and do not take it.
    Child-1 must **not** adopt #533's new wording — `"on transient infra"` is only accurate
    given #533's redefinition of transient, so shipping it early puts a false string in tree.
  * `leaves.py:2526-2532` (#533's `_FAIL_TRANSIENT` comment) vs child-1's harvest at `:2520`
    — **clean**, 9 lines apart, outside the 3-line context. `assemble.py` — **clean**, #533
    touches one line, child-1 none.
  Recommended merge order at publish: child-1 → child-2 → #533's children.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** Who gets retried, what a retry may inherit, and what the operator is told when
  the retries run out — the leaf-invocation layer of #506. Put the builder on the existing
  resilient path; flush each attempt's record as it happens; tell a retried builder that a
  predecessor died mid-flight and that any artifacts present are its residue; make the failed
  Do report name the residue actually on disk and a next action true for it; and give the
  three artifact harvests a notion of which attempt produced what, including the stderr tail
  that today can impersonate the harness's own trailer.
  **Out of scope:** the stream-side question of *what counts as* a transient death and the
  retention of the leaf's own error text — that is sibling #533, and this work must not touch
  `progress.py`, redefine `LeafError.transient`, or add a signal-death predicate (Ordering
  note §3 — the retry set is reused exactly as shipped); a lane/worktree reset between attempts, and any new `pdca.toml` knob (reuse
  the shipped attempts/backoff defaults — a prompt-level statement of the residue is the
  bounded fix; if the rebuild concludes that is insufficient, say so in `build-notes.md`
  rather than expanding the slice); the gate-side transient (issue #371); issue #510's own
  remedy; `flow._isolate`'s containment contract and the `flow_one` library route's
  propagation (`flow.py:302-306` documents why the single-issue path differs); the #420
  memory-telemetry post-mortem, which must keep working unchanged; and the nine other leaves
  still on plain `_invoke` (planner, sizer, splitter, plan-revision, sign-off, act, publisher)
  — the invariant is stated over every leaf, but this slice's four sites are the ones the
  reported incident runs through.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness, `acb214a`), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today; read
     `:26-35` for the stub-leaf harness and `$CNT` counter to copy.
  2. Read the gap: `leaves.py:1824` (`_invoke`, not `_invoke_leaf_resilient`) against the
     three peer call sites `:2507`, `:2840`, `:3142`; `:720` (records written only after the
     loop); `:2520` / `:2851` / `:3152` (bare existence test, attempt-blind); `:724-730`
     (`exc.output` embedded raw); `:1765-1778` (what a failed Do prints); `state.py:224` +
     `driver.py:76` (why a bundle left holding `patch.diff` goes to Check, not Do).
  3. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`), failing tier = the
     `[[leaves.builder_escalation]]` opus/max entry; an identical re-run minutes later
     succeeded.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a stub "leaf" that is a Python interpreter, so the slice builds and goes red→green with no vendor CLI, no API key, no network and no container.
- **Test file:** `template/tests/test_attempt_ownership.py` (**new**) for criteria (ii) and
  (v), and `template/tests/test_builder_retry.py` (**new**) for criteria (i), (iii) and (iv).
  New files, not appends: that is what makes C5 adjudicable (Ordering note §1) and it keeps
  the two halves separable. `template/tests/test_build_error_log.py` may be **updated** where
  the retry changes its wall-clock or call counts (the trap above), but the new assertions
  belong in the new files. Do **not** create `template/tests/fixtures/` and do **not** add
  `template/tests/test_terminal_error_classification.py` — both belong to sibling #533.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this slice wires into patterns the codebase already applies:
  * `_invoke_leaf_resilient` (`leaves.py:673-721`) is the wrapper to reuse **as it is**: its
    staleness clear (`:698-702`), its `_memory_log_for` derivation, its `records` list and the
    `_format_leaf_attempt` record format (`:724-730`);
  * the three peer call sites that already compose it — `:2507` (reviewer), `:2840`
    (advisory), `:3142` (plan advisory) — show the shape to mirror (`err = _invoke_leaf_resilient(…)`,
    then act on `err`). `do_build`'s outer contract differs and must survive: its failure is
    captured to `build.error.log` **and re-raised** (`:1765-1778`), and its stale-log clear
    (`:1747-1753`) plus the archive rule pinned by `test_build_error_log.py:91-105` still hold
    — a wrapper that writes per-attempt records must not then be overwritten by the outer
    capture;
  * `_stub_build` (`:1889`) and `select_builder` (`:1634`) bound the change: a stub backend
    must behave exactly as today; `_build_prompt` (`:1834`) is where criterion (iii)'s note
    reaches the retried builder;
  * honesty inputs for the failed-Do message: `state.py:224` (a bundle holding `patch.diff`
    reads BUILT) and `driver.py:76` (BUILT → Check). Ask the state machine, do not infer from
    the residue's shape.
  * **Prior art you may read, selectively:** round 3's rejected patch is archived at
    `results/issue_532/iteration-v3/patch.diff` (+ `build-notes.md`). Its mechanism was
    confirmed by the reviewer and the adversary; it was returned for slice size, the vacuous
    C5, and criterion (iv)'s unreachable branch — not for its approach. You may read it for
    decisions already settled (the fail-closed withdrawal, the `may_retry`/`recorded` gating,
    the `_died_of_a_signal` two-spelling read, asking `state.state(d)` rather than sniffing
    `patch.diff`). Re-verify anything you take against the current base, and do **not**
    re-apply its two known defects: `_format_leaf_attempt` was never defanged, and its
    residue report was gated on retryability.

  **Path convention in this brief:** every `template/…` and `tests/…` path is on the **target
  branch** (eduralph/pdca-harness @ main) — the files Do reads and edits. Every `engine/…`,
  `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification engine
  and the bundles that run the cycle); they are cited to explain how the gates will judge the
  patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main` (re-run this session):
  `template/src/pdca_harness/leaves.py` — `_invoke_leaf_resilient` arrived with #138 for the
  reviewer/advisory leaves and was never extended to the builder; `do_build`'s error capture
  is #279/#286; the most recent touch of `_invoke` is `0881af9` (#420 memory sampling), and
  the base is unchanged at `acb214a` since round 3. Open PRs on the target: #519-#525, of
  which #524 (issue 494) and #520 (issue 466) touch `leaves.py` at distant regions (`:782`,
  `:3261`, `:3400`, `:3465`; `do_split`) — no overlap. Open issues searched for `retry` /
  `transient`: #371 (gate-row transient red) and #510 (signal death) are adjacent and
  deliberately excluded above; #509 (crash-resume) is a different beat. Not previously
  attempted as its own slice and not rejected on mechanism; parent #506's four-round attempt
  and this bundle's three rounds were both returned on slicing.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
