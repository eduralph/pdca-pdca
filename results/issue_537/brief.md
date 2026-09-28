- **Slug:** the-builder-retries-like-every-other-leaf
- **Defect / goal:** Do is the one leaf whose failure is never absorbed, and its death
  explains nothing. `_do_build_command` calls plain `_invoke` (`leaves.py:1824`) while the
  reviewer (`:2507`), the advisory (`:2840`) and the plan advisory (`:3142`) all run under
  `_invoke_leaf_resilient` (`:673-721`) — so no builder failure is ever retried, on the leaf
  where an attempt is most expensive; the reported incident burned ~18 minutes and a cycle
  round to a dropped connection, and an identical re-run minutes later succeeded. And when
  the attempts do run out, `do_build` captures one record and re-raises (`:1765-1778`): the
  operator reads an argv and an exit status, while what the honest next action *is* depends
  on residue — a bundle holding `patch.diff` reads BUILT (`state.py:224`), so
  `driver.advance` (`driver.py:76`) runs **Check** on that partial patch, not Do.
- **Success criterion:** With the patch: (i) a **transient** builder death is retried,
  bounded, with backoff, under the same `_invoke_leaf_resilient` contract the other three
  leaves use, while a **substantive** builder failure is still not retried; either way the
  final failure is still captured to `build.error.log` and still re-raised, so
  `flow._isolate` drops just this bundle as today; (ii) a retried **builder** is told in its
  prompt that a previous attempt died mid-flight and that any `patch.diff` /
  `build-notes.md` / test file present is that attempt's incomplete residue to verify or
  replace — never evidence the work is done, and attempt 1's prompt is byte-identical to
  today's; (iii) **every** failed Do — transient or substantive — prints the residue actually
  on disk and the next action true for it, naming, when a `patch.diff` was left, that the
  bundle now reads BUILT and that a plain re-run runs Check on it; only the *"transient —
  absorbed after N attempts"* sentence is conditioned on the failure having been classified
  transient, and N is the attempts actually spent, not the budget. Nothing deletes the
  builder's artifacts to make that sentence true, and the state machine is **asked**
  (`state.state(d)`), never inferred from the residue's shape; (iv) the per-attempt records
  the wrapper flushed (child-1) survive — `do_build`'s outer capture must not overwrite the
  post-mortem the retries built; what is left for that capture is a Do that died *around* the
  leaf (`worktree.ensure`, the lane lock), which otherwise has nothing bundle-local at all;
  (v) nothing else changes: the shipped resilience contract holds unchanged (attempt count,
  backoff, the staleness clear at `:698-702`, and the `_memory_log_for` derivation — **derive
  it, do not pass `memory_log=`** where the other three call sites do not; the builder's
  current explicit `memory_log=d / BUILD_MEMORY_LOG` at `:1830` derives to the identical
  file), the #420 memory-telemetry post-mortem still rides `output` into the same log, a
  successful build is spawned and reported exactly as today, `_stub_build` (`:1889`) and
  `select_builder` (`:1634`) behave exactly as today, `do_build`'s stale-log clear
  (`:1747-1753`) and the archive rule pinned by `test_build_error_log.py:91-105` still hold,
  and both offline suites stay green **and fast** (see Falsifiability).
- **Falsifiability:** RED is reachable offline on the base toolchain — pure-stdlib Python
  ≥ 3.11 + git, no vendor CLI, no network, no API key — in the target checkout Do is given.
  `template/tests/test_leaf_resilience.py:26-35` already ships the harness this needs:
  `_TRANSIENT` (stderr only, no stream event → transient under today's rule), `_SUBSTANTIVE`
  (emits `{"type":"assistant"}` first), a leaf whose argv is `[sys.executable, "-c", script]`,
  and a `$CNT` file counting invocations. **Copy that harness into the new test file** — do
  not import it across modules. (i): driving `leaves.do_build` with such a builder counts
  **1** invocation today and must count the attempt budget after the fix; the substantive
  stub must still count 1. (ii)/(iii) are assertions over the child's stdin and over captured
  stderr. (iv): a first attempt whose record is on disk, then a final failure — the log must
  still hold both.
  **Wall-clock trap, read before you build:** `template/tests/test_build_error_log.py:63-71`
  raises `LeafError(1, ["claude"], output="panic…")` and `produced` defaults to `False`
  (`leaves.py:99`), so `.transient` is `True`. The moment `do_build` retries, that existing
  test spends the real backoff (4 s + 8 s) and calls its mock three times. Keep the suite
  fast **and** honest: make the attempt budget / backoff reachable from the test (or patch
  the sleep). Do **not** weaken `_invoke_leaf_resilient`'s shipped defaults to do it — note
  `test_leaf_resilience.py:58` already passes `attempts=3, backoff=0.0` explicitly, which is
  the shape to mirror.
- **Invariant to restore:** **An attempt is the unit of accountability** — the absorption and
  honesty half: an infrastructure failure the leaf did not cause is the harness's to absorb,
  bounded, on **every** leaf it spawns and not merely on the three that happened to be given
  the wrapper; and nothing the harness tells the retried leaf or the operator about a dead
  attempt's residue may be false. Stated over the category rather than this incident. Source:
  internal project invariant (Tier C), the target's own written rules — `leaves.py:641-647`
  (why a captured tail exists at all: `(no output captured)` is "a post-mortem artifact that
  explains nothing", #286 review), `leaves.py:683-697` (the #138 resilience contract).
  `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6 category gate
  applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `acb214a`; every `path:line`
  above was re-verified against it while this proposal was written)
- **Reproduction:** On a clean checkout of the target base — **plus child-1's accepted
  result, which the wave fold gives you** — offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_build_error_log -v` — green today; read
     `:63-71` for the wall-clock trap and `:91-105` for the archive rule that must survive.
  2. Read the gap: `leaves.py:1824` (`_invoke`, not `_invoke_leaf_resilient`) against the
     three peer call sites `:2507`, `:2840`, `:3142`; `:1765-1778` (what a failed Do prints);
     `:1834` (`_build_prompt`, where the retried builder's note must reach it);
     `state.py:224` + `driver.py:76` (why a bundle left holding `patch.diff` goes to Check,
     not Do).
  3. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`), failing tier = the
     `[[leaves.builder_escalation]]` opus/max entry; an identical re-run minutes later
     succeeded.
- **Surfaces:** data
- **Difficulty:** high — five regions across one production module and two test files, and it
  changes how **every** Do in the instance is spawned: a diff-reviewer must hold the builder
  call site, the prompt, the exhausted-Do report, the interaction with child-1's per-attempt
  flush, and the wall-clock of an existing suite in view at once.
- **Scope (one logical fix) / out of scope:** Put the builder on the existing resilient path;
  tell a retried builder that a predecessor died mid-flight and that any artifacts present
  are its residue; and make the failed-Do report name the residue actually on disk and a next
  action true for it. **Out of scope:** the harvest sites and the record flush — that is
  child-1, which this builds on: do **not** re-author its flush, its withdrawal, its trailer
  or its recovery discriminators, and do not re-introduce a raw `exc.output` embed in
  `_format_leaf_attempt`. The stream-side question of *what counts as* a transient death —
  sibling #533: do **not** touch `progress.py`, redefine `LeafError.transient`
  (`leaves.py:103-108`), or **add a signal-death predicate**. Putting the builder on the
  retry path means it spends the attempt budget on whatever `.transient` currently
  classifies; that is this slice's one genuine coupling to the classification question, and
  it is a *cost*, not a defect to fix here. Measured on the base: a builder that OOMs after
  doing work has `produced=True` → substantive → not retried (the expensive case is already
  safe), and the shape that dominates — systemd-oomd killing the leaf's own scope under
  session-wide pressure from a concurrent leaf (`leaves.py:232-234`) — is genuine transient
  infra a retry *should* absorb. If sign-off judges the resulting retry set wrong **for the
  builder specifically**, that is #533's or #510's slice, not a reason to widen this one.
  Also out: a lane/worktree reset between attempts, and any new `pdca.toml` knob — reuse the
  shipped attempts/backoff defaults; a prompt-level statement of the residue is the bounded
  fix, and if the build concludes that is insufficient, say so in `build-notes.md` rather
  than expanding the slice. Also out: the gate-side transient (#371); issue #510's own
  remedy; `flow._isolate`'s containment contract and the `flow_one` library route's
  propagation (`flow.py:302-306` documents why the single-issue path differs); the #420
  memory-telemetry post-mortem, which must keep working unchanged; and the nine other leaves
  still on plain `_invoke`. Do **not** create `template/tests/fixtures/` and do **not** add
  `template/tests/test_terminal_error_classification.py` — both belong to #533.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter, so this builds and goes red→green with no vendor
  CLI, no API key, no network and no container.
- **Test file:** `template/tests/test_builder_retry.py` (**new**) for criteria (i)-(iii).
  `template/tests/test_build_error_log.py` may be **updated** where the retry changes its
  wall-clock or call counts (the trap above) and for criterion (iv), but the new assertions
  belong in the new file. A new file, not an append: `engine/scripts/run-prod-path.py` keys
  C5 on *newly added* test files, and round 3's appends made C5 print "patch adds no new test
  file — nothing to assert" three rounds running. **C4 red-leg import trap — this is why the
  file is new:** the red leg reverts the production hunks and keeps every `tests/*` and
  `template/tests/*` hunk (`engine/scripts/run-verify.sh:214`), so a new file earns a genuine
  red **provided it imports no symbol this patch adds at module level** — a red-leg import
  failure is recorded `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:189,232`). Import only
  pre-existing API at module level (`from pdca_harness import leaves`) and exercise the
  behaviour through pre-existing entry points (`leaves.do_build`), so the assertions are
  behavioural rather than symbol-existence. The C4 gate runs **every** test file the patch
  touches, so `test_build_error_log.py` must stay red-worthy and green too.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cues — this is a composition slice: the three peer call sites `:2507`
  (reviewer), `:2840` (advisory) and `:3142` (plan advisory) show the shape to mirror
  (`err = _invoke_leaf_resilient(…)`, then act on `err`), and you may open them. `do_build`'s
  outer contract differs and must survive: its failure is captured to `build.error.log`
  **and re-raised** (`:1765-1778`), and its stale-log clear (`:1747-1753`) plus the archive
  rule pinned by `test_build_error_log.py:91-105` still hold. `_stub_build` (`:1889`) and
  `select_builder` (`:1634`) bound the change — a stub backend must behave exactly as today;
  `_build_prompt` (`:1834`) is where criterion (ii)'s note reaches the retried builder.
  Honesty inputs for the failed-Do message: `state.py:224` (a bundle holding `patch.diff`
  reads BUILT) and `driver.py:76` (BUILT → Check) — ask the state machine, do not infer from
  the residue's shape. **Prior art you may read, selectively:** round 3's rejected patch is
  archived at `results/issue_532/iteration-v3/patch.diff` (+ `build-notes.md`); its mechanism
  was confirmed by the reviewer and the adversary and it was returned for slice size, not
  approach. You may take from it the `may_retry` gating and the `state.state(d)` question
  rather than sniffing `patch.diff`. Re-verify anything you take against the current base,
  and do **not** re-apply its two known defects: its residue report was gated on
  retryability, which made the branch the Defect names unreachable in production (criterion
  (iii) settles this as "report for every failed Do" — `LeafError.transient` is `not
  produced` (`:104-108`) and `produced` means a substantive stream event arrived
  (`progress.py:144-155`), so a transient death did no tool work and *cannot* have written
  `patch.diff`); and it authored a signal-death predicate, which is out of scope here.
- **Ordering note:** **RE-POINTED — read this first.** This brief was written when the
  prerequisite was a single "child-1" (#536) carrying *both* the record half and the
  artifact/harvest half. #536 has since been split into **#540** (record half: per-attempt
  flush, the unsettled marker, the four `*.error.log` readers) and **#541** (artifact half:
  the three harvest sites, residue quote/withdrawal, the leaf-status label). So **every
  "child-1" below means "#540 + #541 together"** — this slice `Depends on` BOTH, because the
  text below references the flush *and* the withdrawal/residue, and the latter only exists
  after #541. It therefore lands in a wave after both, and the fold gives you both.
  Everything else in this note stands. Original text follows. Wave 2 of the two-wave split
  of #532. `Depends on: child-1` and the
  direction is load-bearing, not merge hygiene: (a) `do_build`'s outer capture at `:1773`
  unconditionally overwrites `build.error.log`, which on child-1's base would destroy the
  per-attempt post-mortem — the guard belongs here, on a base where the flush already exists,
  rather than making child-1 reach into `do_build`; (b) both honesty criteria describe what
  is **on disk**, and only on child-1's base is the predecessor's account actually there when
  the retried builder reads its prompt, and the attempts-spent count readable from the log.
  **Both children edit the body of `_invoke_leaf_resilient`'s `for attempt` loop** — child-1
  moves the `write_text` at `:720` into it, this one varies the prompt on the `_invoke` call
  at `:707` — so they are never co-scheduled; the fold gives you child-1's version of that
  loop, so read it before editing. Sibling #533 owns the **strings and comments** in that
  function; do not adopt its `"on transient infra"` wording. No ordering field names #533's
  children — they do not exist yet, and an edge naming them would either abort the run
  (`waves.py:77-80`) or be silently dropped (`waves.py:104-109`); #533's Plan session authors
  that edge. Recommended publish order: child-1 → this → #533's children.
  **Expect one false advisory red at Check, and do not chase it.** This is a wave-2 bundle in
  this instance, and this instance's own driver (rendered 0.57.0) carries target issue **#474**:
  the leaked `PDCA_VERIFY_BASE` export gives every wave-≥2 bundle a false **T3** red
  (`wave_mode = "stack"`, `pdca.toml:122`). T3-suite is `gating = false`, and the gating C4 row
  is unaffected — `engine/scripts/run-verify.sh` honours `$PDCA_BASE > $PDCA_VERIFY_BASE >
  override > $PDCA_BRIEF_BASE` (its header, lines 31-50), so C4 correctly applies this patch to
  the folded base carrying child-1's accepted diff. A T3 red here is an artefact of the harness
  running the cycle, not evidence about this patch; `run-suite.sh` reads none of those exports.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/leaves.py` — `_invoke_leaf_resilient` arrived with #138 for the
  reviewer/advisory leaves and was **never extended to the builder**; `do_build`'s error
  capture is #279/#286; the most recent touch of `_invoke` is `0881af9` (#420 memory
  sampling). Open PRs on the target: #519-#525, of which #524 (issue 494) and #520 (issue
  466) touch `leaves.py` at distant regions (`:782`, `:3261`, `:3400`, `:3465`; `do_split`) —
  no overlap. Open issues searched for `retry` / `transient`: #371 (gate-row transient red)
  and #510 (signal death) are adjacent and deliberately excluded above; #509 (crash-resume)
  is a different beat. Not previously attempted as its own slice and not rejected on
  mechanism; parent #506's four-round attempt and #532's three rounds were both returned on
  slicing.
- **Disposition hint:** likely-fix
- **Depends on:** 540, 541

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
