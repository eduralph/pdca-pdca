<!-- pdca:split-proposal v1 -->
# Split proposal — issue 536

## Why this slice is oversized

Five rounds of measured evidence, not a heuristic: 5 builder attempts, 4 sign-off rounds,
patch 44 → 68 → 79 → 93 → 104 KB (threshold 80), with implementation-shaped adversary
findings *every single round* (4, 4, 2, 3, 2). The v5 sign-off rejected it on **slicing, not
direction** — all gates green, C4 independently re-run, mechanism confirmed by both the
reviewer and the adversary.

The generator is a **shared meaning with many independent readers, each hard-coding it at
its own site**. Every round converted the readers in view; the next round found one more
still speaking the old meaning (v1 `assemble.py:417`, v2 `driver.py:178`, v3
`leaves.py:2910`, v4 `leaves.py:3176`, v5 `assemble.py:85`). The adversary's phrase is
exact: the patch widened the sentence it could see, *"then stops one reader short."*

**The seam is where that axis MOVED.** v5 confirmed by grep that the
`*.error.log`-as-state readers were all converted, and its new finding was on a *different*
shared value — the leaf-status enum → label map. Those are two distinct meanings with two
disjoint, separately enumerable reader sets on the base:

| Meaning | Readers on base `acb214a` | Child |
|---|---|---|
| "an `*.error.log` exists" ⇒ ran and FAILED | `leaves.py:2103-2104`, `:2800-2801`, `assemble.py:417`, `driver.py:121-127`/`:148-156`/`:170-172` | **child-1** |
| leaf-status enum → label | `assemble.py:84-89`, written `leaves.py:2588`, read `:168` | **child-2** |

A third seam the v5 sign-off named (seam A, "give the meaning ONE owner") is deliberately
**not** its own child: a pure refactor has no behavioural delta, so `run-verify.sh` records
it `PDCA-UNVERIFIABLE` rather than red. It therefore rides *inside* each child, applied to
that child's own meaning — which is what ends the "stops one reader short" class by
construction instead of by enumeration.

## Wave sketch

**Two waves, stacked — not parallel.** child-2 `Depends on` child-1 for two independent
reasons, either of which alone would force the order:

1. **Semantic:** child-2 must know *which attempt is live* to refuse a dead attempt's
   artifact. That notion is exactly what child-1 creates.
2. **Textual:** both edit the body of `_invoke_leaf_resilient`'s `for attempt` loop
   (`leaves.py:705-719`). Co-scheduling them would collide on the same base.

**Two external edges must be re-pointed by hand immediately after `--accept`** — the
proposal's ordering fields may only name sibling *labels*, never tracker ids (`preflight`
enforces this), so neither can be expressed here:

- **`Conflicts with: <both child ids>` must be added to each child's `brief.md`.** `#539`
  rewrites the strings and comments in the same function (the print at `leaves.py:717`,
  three lines from the `write_text` at `:720`). It currently declares `Conflicts with: 536,
  537` from its side — but `536` will be a *split parent* after acceptance, so that edge
  dangles and is either aborted or silently dropped by the scheduler. **`#539`'s brief must
  be re-pointed at the two child ids too.**
- **`#537` declares `Depends on: 536`** and needs the wrapper, not the harvest half, so it
  stacks after **child-1**; re-point it at child-1's filed id.

<!-- pdca:child child-1 -->
- **Slug:** per-attempt-record-and-one-error-log-meaning
- **Defect / goal:** A retried leaf's `*.error.log` is written only **after** the retry loop
  ends (`leaves.py:720`), so two things are broken at once and neither can be fixed without
  the other. (a) While attempt 2 runs there is nothing on disk explaining attempt 1, and a
  run killed mid-retry loses every attempt's account — the file never existed. (b) The reason
  (a) cannot simply be flushed earlier: the **presence** of that file is hard-coded at four
  sites to mean *"the leaf ran and FAILED"*, so flushing it early makes that sentence false
  at every one of them. Two of the four are executable recovery discriminators
  (`leaves.review_never_ran` `:2103-2104`; `run_advisory_leaves(only_missing=True)`
  `:2800-2801`), so a reviewer the death window merely **interrupted** would be retired
  instead of re-run, and the bundle would reach sign-off **with no review of the diff at
  all**. Separately `_format_leaf_attempt` (`:724-730`) embeds `exc.output` raw at `:727`, so
  a leaf's own captured text can impersonate whatever the harness uses to describe its own
  run — which matters only once that description exists.
- **Success criterion:** With the patch applied to the target base, all of:
  1. **Each failed attempt's record is on disk before the next attempt starts.** A leaf
     observing the bundle during attempt 2 finds attempt 1's account already there; today it
     finds no file. A run killed mid-retry therefore leaves a post-mortem.
  2. **An unsettled account does not read as "ran and FAILED" to any reader.** All four
     readers under `Citations expected` agree because they consult **one** point of truth
     rather than each testing the file's existence: an error log left by a leaf whose
     attempts are not yet spent recovers the leaf exactly as an absent one does
     (`review_never_ran` → True; `only_missing` does not skip it), and the operator-facing
     wording in `assemble._missing_review_text` / `driver._resume_interrupted_check` names
     both shapes instead of asserting only one.
  3. **A leaf's own text cannot impersonate that distinction.** Whatever distinguishes an
     unsettled account from a spent one is neutralised in the captured stderr tail
     `_format_leaf_attempt` embeds, and is recognised only as the log's **last non-blank
     line, alone** — never as a substring, never mid-line. (Round 3 shipped this leg with the
     token embedded mid-line, which is not the failure mode.)
  4. **The shipped resilience contract is unchanged.** Attempt count, the transient rule, the
     backoff schedule, the staleness clear (`:698-702`) and the `_memory_log_for` derivation
     exactly as shipped; a **successful** leaf still leaves no error log behind; the #420
     memory-telemetry post-mortem still rides `output` into the same log and survives the
     neutralisation intact; and `template/tests/test_leaf_resilience.py` stays green
     **untouched** — verified at Plan, not assumed: its error-log *content* assertions are
     `assertIn` (`:64`, `:74`) and its *existence* assertions read the FINAL state only
     (`:63` after a spent retry, `:83`/`:91` after success).
  5. **DECIDED HERE, not left to Do — the retry contract is NOT narrowed.** A record flush
     that fails (read-only bundle dir, ENOSPC) **must not end the run**: the shipped stop rule
     is the only stop rule, and the un-flushed records stay in hand so the loop's final write
     still persists them — strictly no worse than the base, which persists nothing until the
     end. v5 measured the opposite choice at 3 attempts → 1 and it was the finding that could
     not be closed, because criterion (4) and a fail-closed withdrawal cannot both hold.
     Mechanical check: `test_leaf_resilience.py:62` asserts `_runs() == 3`, and a Plan-time
     run of the base measured exactly 3.
- **Repo + branch target:** eduralph/pdca-harness @ main   (base `acb214a`; every
  `path:line` re-verified against it at Plan)
- **Reproduction:** From `template/` on a clean checkout of the base, offline:
  `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` is green today; read
  `:26-35` for the stub-leaf harness and `$CNT` counter to copy. Then read the gap:
  `leaves.py:720` (records written only once the loop ends), `:727` (`exc.output` raw), and
  the four readers below, each independently testing the file's existence. **RED proven by
  execution at Plan, not reasoned about:** driving `_invoke_leaf_resilient` with the stub
  leaf on `acb214a` produced `attempts run: 3`, `error log at end: True`, **`SNAPSHOT
  mid-retry: False`** — criteria (1) and (2) cannot even be *seeded* on the base.
  Test design, all three legs derived from behaviour so no symbol this patch adds is named:
  (1) the stub, on its second invocation, copies the error-log path aside to a snapshot —
  absent on base; (2) the test seeds a bundle dir with **that snapshot** as
  `check-review.error.log` (byte-for-byte the state a mid-retry kill leaves, so it cannot
  drift from the production shape) and asserts `review_never_ran` is True and `only_missing`
  does not skip the leaf; (3) the marker is **read off the snapshot's last non-blank line**,
  then a second run's stub emits exactly that line last on stderr and the resulting settled
  log must not read as unsettled. **C4 red-leg import trap:** the red leg reverts production
  hunks but keeps the test (`run-verify.sh:214`), and a module that fails to **import** there
  is `PDCA-UNVERIFIABLE`, not red (`:229-232`) — import only pre-existing API at module level
  (`from pdca_harness import leaves`).
- **Scope (one logical fix) / out of scope:** Make each failed attempt's account exist on
  disk from the moment that attempt fails rather than only once the retry loop ends; and make
  the distinction this creates — an account whose leaf has not yet settled versus one whose
  leaf has spent its attempts — carry **a single point of truth that every reader consults**,
  so no reader can be left speaking the old meaning. A leaf's own captured text must not be
  able to impersonate that distinction. (The single-point-of-truth constraint is a design
  constraint carried from five rounds of measured evidence, not a mechanism chosen here:
  which form it takes — predicate, enum, dataclass — stays Do's call.) The unsettled state's
  whole lifetime is **inside `_invoke_leaf_resilient`**: the loop ends either by failing,
  which settles the records, or by succeeding, which discards them as today. **No caller
  changes.** **Out of scope:** the artifact/harvest half in every part — do **not** pass an
  artifact path into the wrapper, do **not** touch the three harvest sites (`:2519-2523`,
  `:2851-2854`, `:3152-3155`), do **not** add a residue quote/withdrawal, a settle-at-harvest
  hook, or an empty-run classification, and do **not** extend the unsettled state past the
  wrapper's return; that is child-2. Do **not** touch `assemble.py:80-89` (leaf-status
  labels) — child-2's reader, false only under child-2. The builder path is `#537`: do not
  move `_do_build_command` (`:1824`) onto the resilient path, nor touch `do_build`'s capture
  (`:1765-1778`), `_build_prompt` (`:1834`), `_stub_build` (`:1889`). What counts *as* a
  transient death is `#539`: do not touch `progress.py`, redefine `LeafError.transient`
  (`:103-108`), or add a signal-death predicate. Also out: a lane/worktree reset between
  attempts; any new `pdca.toml` knob; #371; #510's remedy; the nine other leaves still on
  plain `_invoke`. Do **not** create `template/tests/fixtures/`.
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter: no vendor CLI, no API key, no network, no
  container.
- **Test file:** `template/tests/test_attempt_ownership.py` (**new**). A new file, not an
  append: `engine/scripts/run-prod-path.py` keys C5 on *newly added* test files, and round
  3's appends made C5 print "patch adds no new test file — nothing to assert" three rounds
  running. Dry-run at Plan on a synthetic patch of the expected file set returned
  `PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package
  'pdca_harness'`. The C4 gate runs **every** test file the patch touches, so if
  `test_leaf_resilience.py` is touched at all it must be red-worthy too — criterion (4) says
  leave it alone.
- **Difficulty:** high
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** no-dead-attempts-artifact-harvested-as-a-live-ones
- **Defect / goal:** The three harvest sites copy their artifact on a bare existence test —
  `leaves.py:2519-2523` (`check-review.md`), `:2851-2854` (advisory), `:3152-3155` (plan
  advisory) — with no notion of *which attempt* wrote it. So a truncated verdict a **dead**
  attempt left in the sandbox is adopted as the leaf's own output, which
  `engine/README.md:44-68` names directly: no evidence must never be filed as a verdict. The
  mechanism is hand-copied at all three sites, which is the "twin blindness" face the v5
  sign-off identified — a fix or a test that lands at two of three leaves the third wrong.
  A second reader carries the same root: the leaf-status label at `assemble.py:84-85` reads
  `"leaf did not run (transient infra — safe to re-run)"`, which becomes **false** once a run
  whose last attempt exited 0 can be routed there (v5's final unconverted reader).
- **Success criterion:** With the patch applied on top of child-1's accepted result:
  1. **No artifact written by a dead attempt is copied out as a successful attempt's
     output**, at **all three** harvest sites — not two of three.
  2. **A dead attempt's text is preserved** in the bundle's `*.error.log` rather than merely
     deleted: a real verdict must not be destroyed while the operator is told none was
     produced.
  3. **The live attempt's own artifact is harvested exactly as today**, and a leaf that exits
     0 having written nothing still degrades to today's placeholder.
  4. **The leaf-status label tells the truth** for every run it can now classify: a run whose
     last attempt exited 0 must not be labelled "leaf did not run".
  5. **DECIDED HERE, not left to Do — the retry contract is NOT narrowed**, the same ruling
     child-1 makes for the record flush. On a residue that cannot be withdrawn, **carry the
     un-owned state forward and refuse to HARVEST on the success branch** (the residue is
     already quoted by then) rather than ending the run. This is the v5 sign-off's own
     no-cost alternative, quoted verbatim as an instruction: v5 measured the fail-closed
     variant at base-3-attempts → patch-1 on a bundle write refusal and 2 → 1 on an unlink
     refusal, while its criterion demanded the contract "hold unchanged" — the builder was
     asked to satisfy both and could not. `test_leaf_resilience.py:62` (`_runs() == 3`) is
     the mechanical check.
  6. **The three harvest sites end up sharing one implementation, not three copies.** This is
     the point of the child: the v5 code-review advisory flagged the de-duplication as a
     legitimate Act candidate and round 3 refused it on the express grounds that "this patch
     is already oversized" — that refusal *is* the loop, and this child exists to break it.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** From `template/` on a clean checkout, offline. Drive
  `leaves._run_review_sandboxed` with a stub reviewer whose **first** attempt writes a
  truncated `check-review.md` into the sandbox then dies transiently, followed by an attempt
  that exits 0 without writing: today the harvest copies the dead attempt's file out as the
  review. Copy the stub-leaf harness from `template/tests/test_leaf_resilience.py:26-35`
  (`_TRANSIENT`, `_SUBSTANTIVE`, the `[sys.executable, "-c", script]` argv, the `$CNT`
  counter) — do not import it across modules. Assert the same shape at **all three** sites,
  not just the reviewer's, or the twin-blindness face survives. **C4 red-leg import trap:**
  import only pre-existing API at module level (`from pdca_harness import leaves`) and drive
  through pre-existing entry points, since a red-leg import failure is recorded
  `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:229-232`).
- **Scope (one logical fix) / out of scope:** Give the three harvest sites one owner, and
  through it make a harvest attempt-aware: what a dead attempt left at the artifact path is
  preserved as that attempt's account and cannot be reported as a later attempt's work, and
  every reader of the resulting classification — including the leaf-status label — is told
  the truth by consulting that one owner rather than restating it. **Out of scope:** the
  record half (child-1's — do not revisit the per-attempt flush, the unsettled marker, or the
  four `*.error.log` readers except where this child's own change makes one false); the
  builder path (`#537` — `_do_build_command` `:1824`, `do_build`'s capture `:1765-1778`,
  `_build_prompt` `:1834`, `_stub_build` `:1889`); what counts *as* a transient death (`#539`
  — `progress.py`, `LeafError.transient` `:103-108`, any signal-death predicate); a
  lane/worktree reset between attempts; any new `pdca.toml` knob; #371; #510's remedy; the
  nine other leaves still on plain `_invoke`. Do **not** create `template/tests/fixtures/`.
- **External dependencies:** none — the base toolchain suffices; every leg is driven by a
  stub "leaf" that is a Python interpreter.
- **Test file:** `template/tests/test_attempt_harvest.py` (**new**, and confirmed at Plan to
  collide with nothing tracked in the target). It must be a **new** file rather than an
  append to child-1's `test_attempt_ownership.py`, and the binding reason is C5: the gate
  keys on *newly added* test files, so an append prints "patch adds no new test file —
  nothing to assert" — the degradation that let two unfaithful-stub findings survive to the
  adversary for three rounds. (A secondary, non-blocking effect: C4 runs every test file the
  patch touches, so an append would also re-run child-1's tests on this bundle's legs. Those
  would pass — child-1's production code is in this bundle's base, not in its patch — so it
  costs noise, not a false verdict.) Do **not** touch `test_leaf_resilience.py` or
  `test_attempt_ownership.py`.
- **Difficulty:** high
- **Depends on:** child-1
<!-- pdca:end child-2 -->
