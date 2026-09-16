# Brief — issue 536 / per-attempt-record-and-one-error-log-meaning

> **THIS BRIEF IS SPLIT — see `split-proposal.md`.** Re-planned after `iterate-plan` at v5,
> which rejected the previous attempt on **slicing, not direction** ("the fix's direction is
> right and its proof is sound") and named the error class to design out. The parent scope
> below is carved into **two children** at the seam the five rounds themselves revealed:
> the **record half** (child-1) and the **artifact/harvest half** (child-2, which
> `Depends on` it).
>
> **Why this seam and no other.** v5's post-mortem shows the axis *moved* rather than
> exhausted: rounds 1-4 converted the readers of "an `*.error.log` exists ⇒ ran and failed",
> and v5's new finding was on a *different* shared value — the leaf-status enum → label map.
> Those two meanings are separately enumerable on the base, so they are the two children.
>
> **Neither child splits further, checked mechanically rather than asserted.** Within
> child-1, flush-without-one-owner actively *breaks* recovery (it ships a state no reader
> understands — strictly worse than the base), and one-owner-without-flush is a pure
> refactor with no behavioural delta, which `run-verify.sh` records `PDCA-UNVERIFIABLE`
> rather than red. So the halves of child-1 are not independently shippable, and a size
> advisory firing on child-1 is answered by cutting prose or accepting it — not by a
> third split.

- **Slug:** per-attempt-record-and-one-error-log-meaning
- **Defect:** A retried leaf's `*.error.log` is written only **after** the retry loop ends
  (`leaves.py:720`), so two things are broken at once and neither can be fixed without the
  other. (a) While attempt 2 runs there is nothing on disk explaining attempt 1, and a run
  killed mid-retry loses every attempt's account — the file never existed. (b) The reason
  (a) cannot simply be flushed earlier: the **presence** of that file is hard-coded at four
  sites to mean *"the leaf ran and FAILED"*, so flushing it early makes that sentence false
  at every one of them. Two of the four are executable recovery discriminators
  (`leaves.review_never_ran` `:2103-2104`; `run_advisory_leaves(only_missing=True)`
  `:2800-2801`), so a reviewer that the death window merely **interrupted** would be
  retired instead of re-run, and the bundle would reach sign-off **with no review of the
  diff at all**. Separately, `_format_leaf_attempt` (`:724-730`) embeds `exc.output` raw at
  `:727`, so a leaf's own captured text can impersonate whatever the harness uses to
  describe its own run — which matters only once that description exists.
  **(c) — the second child.** The same root has an artifact face: the three harvest sites
  copy their artifact on a bare existence test (`:2519-2523`, `:2851-2854`, `:3152-3155`)
  with no notion of *which* attempt wrote it, so a truncated verdict a **dead** attempt left
  in the sandbox is adopted as the leaf's own output — exactly what `engine/README.md:44-68`
  forbids ("no evidence must never be filed as a verdict"). Its own reader, the leaf-status
  label at `assemble.py:84-85` (`"leaf did not run (transient infra — safe to re-run)"`),
  becomes false once a run whose last attempt exited 0 can be routed there.
- **Success criterion:** With the patch applied to the target base, all of:
  1. **Each failed attempt's record is on disk before the next attempt starts.** A leaf
     observing the bundle during attempt 2 finds attempt 1's account already there; today
     it finds no file. A run killed mid-retry therefore leaves a post-mortem.
  2. **An unsettled account does not read as "ran and FAILED" to any reader.** All four
     readers enumerated under `Citations expected` agree, because they consult **one**
     point of truth rather than each testing the file's existence: an error log left by a
     leaf whose attempts are not yet spent recovers the leaf exactly as an absent one does
     (`review_never_ran` → True; `only_missing` does not skip it), and the operator-facing
     wording in `assemble._missing_review_text` / `driver._resume_interrupted_check` names
     both shapes instead of asserting only one.
  3. **A leaf's own text cannot impersonate that distinction.** Whatever distinguishes an
     unsettled account from a spent one is neutralised in the captured stderr tail
     `_format_leaf_attempt` embeds, and is recognised only as the log's **last non-blank
     line, alone** — never as a substring, and never mid-line. (Round 3 shipped this leg
     with the token embedded mid-line, which is not the failure mode.)
  4. **The shipped resilience contract is unchanged.** Attempt count, the transient rule,
     the backoff schedule, the staleness clear (`:698-702`) and the `_memory_log_for`
     derivation are exactly as shipped; a **successful** leaf still leaves no error log
     behind; the #420 memory-telemetry post-mortem still rides `output` into the same log
     and survives the neutralisation intact; and `template/tests/test_leaf_resilience.py`
     stays green **untouched** — verified at Plan, not assumed: its error-log *content*
     assertions are `assertIn` (`:64`, `:74`) and its *existence* assertions read the FINAL
     state only (`:63` after a spent retry, `:83`/`:91` after success), so a per-attempt
     flush and a trailer do not disturb any of them.
  5. **DECIDED HERE, not left to Do — the retry contract is NOT narrowed.** A record flush
     that fails (a read-only bundle dir, ENOSPC) **must not end the run**: the shipped stop
     rule is the only stop rule, and the un-flushed records stay in hand so the loop's final
     write still persists them. This is strictly no worse than the base, which persists
     nothing until the end. v5 measured the opposite choice at 3 attempts → 1 and it was
     the finding that could not be closed, because criterion (4) and a fail-closed
     withdrawal cannot both hold. Do not re-introduce it. **This has a mechanical check:**
     `test_leaf_resilience.py:62` asserts `self._runs() == 3` for a transient leaf, and a
     Plan-time run of the base measured exactly 3 attempts — any narrowing turns that
     shipped test red, which criterion (4) forbids.
- **Falsifiability:** RED is reachable offline on the base toolchain (pure-stdlib Python
  ≥ 3.11 + git — no vendor CLI, no network, no API key) in the target checkout Do is given.
  **This was executed against the base at Plan, not reasoned about:** driving
  `_invoke_leaf_resilient` with the stub leaf below on `acb214a` produced `attempts run: 3`,
  `error log at end: True`, **`SNAPSHOT mid-retry: False`** — legs (1) and (2) below cannot
  even be *seeded* on the base, which is the red. The C5 gate was likewise dry-run on a
  synthetic patch of the expected file set and returned `PDCA-EVIDENCE: 1 added driver-suite
  test(s) import the production package 'pdca_harness'`, confirming the new-file choice
  classifies correctly. C4's own split also holds: the patch touches `leaves.py` /
  `assemble.py` / `driver.py` (PROD) and one `template/tests/*.py` (TESTS), so neither
  `PDCA-UNVERIFIABLE` guard at `run-verify.sh:138-143` fires.
  `template/tests/test_leaf_resilience.py:26-35` already ships the harness this needs:
  `_TRANSIENT` (stderr only, no stream event → transient under today's rule), `_SUBSTANTIVE`,
  a leaf whose argv is `[sys.executable, "-c", script]`, and a `$CNT` file counting
  invocations. **Copy that harness into the new test file** — do not import it across
  modules. The whole criterion is driven from *inside* the stub leaf, which is what keeps it
  red-leg safe:
  - **(1)** the stub, on its second invocation, copies the error-log path aside to a
    snapshot. On the base that file does not exist yet, so no snapshot appears and the
    assertion fails — a genuine red, not an error.
  - **(2)** the test seeds a bundle dir with **that snapshot** as `check-review.error.log`
    (it is byte-for-byte the state a mid-retry kill leaves — no hand-built fixture, so the
    test cannot drift from the production shape) and asserts `leaves.review_never_ran(d)`
    is True and that `run_advisory_leaves(only_missing=True)` does not skip the leaf. Red on
    base for the same reason: no snapshot exists to seed from.
  - **(3)** the marker string is **read off the snapshot's last non-blank line** rather than
    named, then a second run's stub emits exactly that line last on stderr; the resulting
    **settled** log must not read as unsettled. Deriving the token from behaviour is what
    keeps this leg free of any symbol the patch adds.
  - **C4 red-leg import trap — why all three legs derive everything from behaviour:** the
    red leg reverts the production hunks but keeps the test (`run-verify.sh:214`), and a
    module that fails to **import** there is recorded `PDCA-UNVERIFIABLE`, not red
    (`:229-232`). So import only pre-existing API at module level
    (`from pdca_harness import leaves`) and drive everything through pre-existing entry
    points (`_invoke_leaf_resilient`, `review_never_ran`, `run_advisory_leaves`). Naming any
    symbol this patch adds — the marker constant above all — forfeits the red.
- **Invariant to restore:** **An attempt is the unit of accountability** — an attempt's
  account exists from the moment it fails rather than only once the loop ends, and no
  reader may report an *unsettled* account as a *spent* one. Stated over the category: it
  holds for every leaf the harness retries, not only the reviewer's, and for every reader of
  that state, not only the one in view. The second clause is load-bearing and is the v5
  sign-off's finding: five rounds each converted the readers *in view* and the next round
  found one more still speaking the old meaning (v1 `assemble.py:417`, v2 `driver.py:178`,
  v3 `leaves.py:2910`, v4 `leaves.py:3176`, v5 `assemble.py:85`) — "the patch widened the
  sentence it could see, then stops one reader short." Enumeration cannot end that class;
  a single point of truth ends it by construction. Source: internal project invariant
  (Tier C) — `leaves.py:641-647` (why a captured tail exists at all: `(no output captured)`
  is "a post-mortem artifact that explains nothing", #286 review), `leaves.py:683-697` (the
  #138 resilience contract), `engine/README.md:44-68` (no evidence must never be filed as a
  verdict). `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6
  category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main   (base `acb214a`; every
  `path:line` in this brief was re-verified against it while the brief was written)
- **Conflicts with:** 539
- **Ordering note:** `#537` (`Depends on: 536`) is unaffected by the narrowing — it moves
  `_do_build_command` onto the resilient path and needs the wrapper, not the harvest half.
  `#539` rewrites the strings and comments in `_invoke_leaf_resilient` (the print at `:717`,
  three lines from the `write_text` at `:720`) and already declares `Conflicts with: 536`;
  declared symmetrically here so neither is ever built blind on the other's base. `#538`
  touches `progress.py` only — no edge. Do **not** adopt #539's `"on transient infra"`
  wording: it is only accurate after #539's redefinition of transient.
  **CARRIED OUT OF THIS SLICE — needs its own tracker issue (flagged to the human at
  Plan):** the artifact/harvest half — no artifact written by a *dead* attempt may be
  harvested as a *live* attempt's output, its text preserved rather than deleted; the three
  near-verbatim harvest sites (`:2519-2523`, `:2851-2854`, `:3152-3155`) reduced to one
  owner; and the leaf-status label `assemble.py:84-85` widened, since `"leaf did not run"`
  becomes false once a run whose last attempt exited 0 can be routed there. That half is
  the v5 sign-off's seam **B**, plus its two surviving `[impl]` items — `_residue_record`
  asserting "withdrawn" as fact, and a stranded `.tmp.<pid>` sibling claimed by no
  `state.DOWNSTREAM_GLOBS` pattern (`state.py:121`), so `_archive_iteration` never moves it
  either. **Those two are cited in v5-PATCH coordinates in the sign-off note
  (`leaves.py:1033-1034` and `:825-828`); neither symbol exists on the base** — that brief
  must re-derive them from `iteration-v5/patch.diff`, not from those line numbers.
  Its own decision is pre-settled by
  the v5 sign-off and must be quoted into that brief: on a residue that cannot be withdrawn,
  **carry the un-owned state forward and refuse to HARVEST on the success branch** (the
  residue is already quoted by then) — do not end the run.
- **Surfaces:** data
- **Difficulty:** high — three production files and ~six regions, but the reach that matters
  is semantic: it changes what the *presence* of an error log means, and that meaning is
  read at two executable recovery discriminators and stated in two modules' operator-facing
  prose. A diff-reviewer must hold the wrapper, the record format and all four readers in
  view at once. (Rated up rather than `medium`: the file count shrank with the narrowing,
  the shared-meaning reach did not.)
- **Scope:** Make each failed attempt's account exist on disk from the moment that attempt
  fails rather than only once the retry loop ends; and make the distinction this creates —
  an account whose leaf has not yet settled versus one whose leaf has spent its attempts —
  carry **a single point of truth that every reader consults**, so that no reader can be
  left speaking the old meaning. A leaf's own captured text must not be able to impersonate
  that distinction. (The single-point-of-truth constraint is a *design constraint carried
  from five rounds of measured evidence*, not a mechanism chosen here: which form it takes —
  predicate, enum, dataclass — stays Do's call.) The unsettled state's whole lifetime is
  **inside `_invoke_leaf_resilient`**: the loop ends either by failing, which settles the
  records, or by succeeding, which discards them as today. No caller changes.
  / **out of scope:** the artifact/harvest half in every part — do **not** pass an artifact
  path into the wrapper, do **not** touch the three harvest sites (`:2519-2523`,
  `:2851-2854`, `:3152-3155`), do **not** add a residue quote/withdrawal, a settle-at-harvest
  hook, or an empty-run classification, and do **not** extend the unsettled state past the
  wrapper's return. Do **not** touch `assemble.py:80-89` (the leaf-status labels) — that
  reader belongs to the carried-out half and is false only under it. The builder path is
  `#537`: do not move `_do_build_command` (`:1824`) onto the resilient path, do not touch
  `do_build`'s capture (`:1765-1778`), `_build_prompt` (`:1834`) or `_stub_build` (`:1889`).
  What counts *as* a transient death is `#539`: do not touch `progress.py`, do not redefine
  `LeafError.transient` (`:103-108`), do not add a signal-death predicate; the retry set is
  reused exactly as shipped. Also out: a lane/worktree reset between attempts; any new
  `pdca.toml` knob; the gate-side transient (#371); #510's remedy; the nine other leaves
  still on plain `_invoke`. Do **not** create `template/tests/fixtures/` and do **not** add
  `template/tests/test_terminal_error_classification.py` — those are #538/#539's.
- **Repro instruction:** On a clean checkout of the target base, offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience -v` — green today; read
     `:26-35` for the stub-leaf harness and `$CNT` counter to copy.
  2. Read the gap: `leaves.py:720` (records written only once the loop ends); `:727`
     (`exc.output` embedded raw); and the four readers listed under `Citations expected`,
     each independently testing the file's existence.
  3. The live incident is named in parent issue #506: getwyrd/wyrd-pdca `results/issue_717/`
     (`build.error.log`, `loop-telemetry.json`).
- **External dependencies:** none — the base toolchain suffices. Every leg is driven by a
  stub "leaf" that is a Python interpreter, so this builds and goes red→green with no vendor
  CLI, no API key, no network and no container.
- **Test file:** `template/tests/test_attempt_ownership.py` (**new**). A new file, not an
  append: `engine/scripts/run-prod-path.py` keys C5 on *newly added* test files, and round
  3's appends made C5 print "patch adds no new test file — nothing to assert" three rounds
  running, which is how two unfaithful-stub findings survived to the adversary. The C4 gate
  runs **every** test file the patch touches, so if `test_leaf_resilience.py` is touched at
  all it must be red-worthy too — criterion (4) says leave it alone. (A stale
  `test_attempt_ownership.py` from the v5 attempt is sitting in the bundle root; it is not
  an input — Do reads `brief.md` only and builds in a worktree of the target.)
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  **The four readers of "an `*.error.log` exists" — this is the enumeration that must not
  stop one short, and it is the whole point of the slice that they end up consulting one
  owner rather than four copies:**
  1. `leaves.review_never_ran` — `leaves.py:2094-2104` (executable; the test at `:2103-2104`)
  2. `leaves.run_advisory_leaves(only_missing=True)` — `leaves.py:2800-2801` (executable),
     with its docstring at `:2789-2793`
  3. `assemble._missing_review_text` — `assemble.py:406-432`; the branch at `:417`, both
     wordings at `:418-432`, the rationale in its docstring at `:410-414`
  4. `driver` — the CHECKED-dispatch comment at `driver.py:121-127`,
     `_resume_interrupted_check`'s docstring at `:148-156`, and the operator line at
     `:170-172` (`"reviewer never ran"`, which becomes only half true)
  **Already truthful — leave alone (named so it is not converted by reflex):**
  `leaves._failure_note`'s log reference at `:2607-2609` runs only on the failure branch,
  where the log is settled by definition.
  **Composition cues.** `_invoke_leaf_resilient` (`leaves.py:673-721`) is the wrapper to
  extend **without weakening it**: keep its staleness clear (`:698-702`), its
  `_memory_log_for` derivation, its `records` list and the `_format_leaf_attempt` record
  format (`:724-730`). **Prior art you may read, selectively:** the v5 patch is archived at
  `results/issue_536/iteration-v5/patch.diff` (+ `build-notes.md`); its gates were all green
  and its mechanism was confirmed by both the reviewer and the adversary — it was returned
  for slice size, not approach. Take from it the per-attempt flush and the atomic write.
  Re-verify anything you take against the current base, and do **not** re-apply its two
  known defects: the retry-contract narrowing (criterion 5 above forbids it) and the
  artifact/residue machinery (out of scope above).
- **Prior-art check (triage cycles):** By file path on `origin/main` @ `acb214a`.
  `template/src/pdca_harness/leaves.py` — `_invoke_leaf_resilient` arrived with #138 for the
  reviewer/advisory leaves; its post-loop record write has never been revisited.
  `template/src/pdca_harness/assemble.py` — `_missing_review_text` is #369's; the leaf-status
  block is #278/#285's, and is excluded here. `template/src/pdca_harness/driver.py` —
  `_resume_interrupted_check` is #369's, untouched since. **Open PRs re-checked at Plan
  (`gh pr list`, live): #519-#525 open; only #524 and #520 touch `leaves.py`.** #520
  (`do_split`, hunks at `:1594`/`:1611`) — no overlap. **#524 needs one caution: its first
  hunk is `@@ -730,6 +730,143 @@` — it inserts 143 lines *immediately after*
  `_format_leaf_attempt` ends (`:730`).** No textual overlap with any region this slice
  edits, but if #524 merges first every citation past `:730` in this brief shifts by ~+137:
  **re-derive the reader line numbers from the checkout rather than trusting them if
  `git log` shows #524 already in.** #521 (export the base ladder to the per-fix verifier) is
  adjacent to the C4 base resolution but changes no region here. #371 (gate-row transient
  red) and #510 (signal death) are adjacent and deliberately excluded; #509 (crash-resume) is
  a different beat. Closed/rejected work: this bundle's own v1-v5, all returned on slicing or
  on an unconverted reader — never on mechanism.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
