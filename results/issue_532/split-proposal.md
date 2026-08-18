<!-- pdca:split-proposal v1 -->
# Split proposal — issue 532

## Why this slice is oversized

The brief states its invariant as **two halves** and then names four sites that carry them:
"the retry lives at the builder call site, the record flush inside the wrapper, the ownership
at three harvest sites, the honesty in the operator's message." Those four group **2 + 2**,
and the two groups share two lines of code:

* **The harness's own bookkeeping** — an attempt's account is on disk while the next attempt
  runs, and no dead attempt's artifact is harvested as a live attempt's output. This is live
  **today** on the base with no builder retry at all, because the reviewer, advisory and
  plan-advisory leaves already retry (`leaves.py:2507`, `:2840`, `:3142`) and all three
  harvest on a bare `.exists()` (`:2520`, `:2851`, `:3152`). It is fixable, testable and
  shippable without touching Do.
* **The builder and the operator** — Do is the one leaf never retried (`:1824` calls plain
  `_invoke`), and when it dies the operator is handed an argv and an exit status while a
  half-written `patch.diff` silently makes the bundle read BUILT. Also live today, and also
  fixable without making the harvests attempt-aware.

This is not a seam I am inventing: **the brief already authored it.** Its `Test file` field
names two *new* files, one per group, and says so out loud — "it keeps the two halves
separable". Its Ordering note is written in terms of "**this bundle's two children**", pins a
merge order ("child-1 → child-2 → #533's children"), and does the #533 collision analysis
against "**child-1's regions**". What is missing is only the briefs, which is Plan's to file.

Measured, not asserted: round 3's rejected patch — the one whose *mechanism* the reviewer and
the adversary both confirmed, returned for slice size — is **83.9 KB over 4 files**
(`iteration-v3/patch.diff`). Its hunks partition by region along exactly this seam. Group one
owns the wrapper (`leaves.py:671`, `:727`, `:754`), the record format (`:928`), the two
recovery discriminators and the three harvests (`:2871`–`:3529`); group two owns `do_build`
(`:1978`), `_do_build_command` (`:2163`) and `test_build_error_log.py`. The only contact is
two lines inside one `for` loop (see the Wave sketch). Each child is then a ~30–40 KB patch
in one production module plus one new test file — a Do, not four.

**Why two and not three.** Criterion (iv) cannot leave (i): its "transient — absorbed after N
attempts" sentence needs an attempt count that only exists once the builder is on the wrapper,
so splitting the report from the retry ships a report that says "1" and is then rewritten.
Criterion (v)'s marker cannot leave (ii): the marker exists *because* records are now flushed
mid-loop, and (v) is the rule that the marker cannot be forged. And (ii) and (v) are both the
wrapper's loop body. Cutting any finer cuts a mechanism in half, and each cut costs a full
cycle.

## Wave sketch

**Wave 1: child-1 alone. Wave 2: child-2 alone** (`child-2` declares `Depends on: child-1`).
Two waves, as the parent brief expected; `compute_waves` folds child-1's accepted work onto
the base child-2 builds from, so no human merge sits between them.

**They cannot share a wave.** Both edit the body of `_invoke_leaf_resilient`'s
`for attempt in range(...)` loop (`leaves.py:705-720`): child-1 must move the
`error_log.write_text(...)` at `:720` *into* the loop and withdraw a dead attempt's artifact
after each failure; child-2 must vary the prompt on the `_invoke(...)` call at `:707` so that
only a *retried* builder is told a predecessor died. Thirteen lines apart and inside each
other's diff context — co-scheduled on one base, they conflict at the fold.

**Why `Depends on` and not `Conflicts with`** — i.e. why the direction is load-bearing, not
just merge hygiene:

1. `do_build`'s outer capture (`:1773`) *unconditionally* overwrites `build.error.log` with a
   single record. The moment child-1's per-attempt flush exists, that overwrite destroys the
   post-mortem the retries just built. The guard against it belongs in the change that puts
   the builder on the retry path — i.e. in child-2, written on a base where the flush is
   already there. Built in the other order, child-1 would have to reach into `do_build` to
   protect its own flush, which is child-2's region: the seam would leak.
2. Both of child-2's honesty criteria describe **what is on disk**. Only on child-1's base is
   the predecessor's account actually present when the retried builder reads its prompt
   (criterion iii), and only there can the exhausted-Do report count attempts off the log
   instead of inventing a second mechanism to carry the number (criterion iv).

**No ordering field names #533 or its children, deliberately.** Neither child needs #533 to
compile or to go red→green. A `Depends on` naming an id that is neither in the batch nor an
existing COMPLETE bundle aborts the whole run (`waves.py:77-80`), and a `Conflicts with`
naming an out-of-batch bundle is silently dropped (`waves.py:104-109`) — so any edge
authorable from here either breaks the run or does nothing. #533's Plan session owns that
edge, since it will know these ids. Note `Conflicts with` is *undirected* and oriented by
deterministic id order, so if a child must land before a #533 child, that has to be a
directed `Depends on` on the #533 side.

**The one hazard to carry across the fold** (from the parent's measurement, unchanged): #533
rewrites the retry-backoff **print string** at `:717`, three lines from the `write_text` at
`:720` that child-1 must move. child-1 owns the loop **body**; #533 owns the **strings and
comments** in that function. Expect `:717` to move under you and do not take it — and do not
adopt #533's `"on transient infra"` wording, which is only accurate after #533's
redefinition. `leaves.py:2526-2532` (#533's `_FAIL_TRANSIENT` comment) against child-1's
harvest at `:2520` is clean, 9 lines apart. Recommended publish order:
**child-1 → child-2 → #533's children.**

<!-- pdca:child child-1 -->
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
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
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
- **Ordering note:** Wave 2 of the two-wave split of #532. `Depends on: child-1` and the
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
- **Depends on:** child-1

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
<!-- pdca:end child-2 -->
