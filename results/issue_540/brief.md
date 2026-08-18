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
- **Conflicts with:** 539
- **Ordering note:** Child-1 of the split of #536 (siblings: #541, which `Depends on` this).
  `Conflicts with: 539` because #539 rewrites the strings and comments in
  `_invoke_leaf_resilient` — the print at `leaves.py:717`, three lines from the `write_text`
  at `:720` this slice moves into the loop. Own the loop **body**; #539 owns the **strings**.
  Do not adopt #539's `"on transient infra"` wording: it is only accurate after #539's
  redefinition of transient, so shipping it early puts a false string in tree. `#537`
  (`Depends on: 540, 541`) stacks after this and #541.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the advisory findings, not on the design: the slice is right-sized, the single-point-of-truth predicate is the right shape, and the red->green evidence held up under independent reproduction and four mutants. One local defect blocks it. 1. BLOCKING — make the unsettled-record write crash-safe. `_flush_attempt_records` (leaves.py) uses `Path.write_text`, i.e. open(O_TRUNC) -> write -> close, and the UNSETTLED marker is the LAST thing written. So the file passes through a 0-byte state and, for records larger than the buffer, prefix states — and any such partial state has no trailing marker, so `state.leaf_ran_and_failed` returns True and a reviewer that still had attempts left is RETIRED instead of re-run. Measured on the target tree under RLIMIT_FSIZE (2048 bytes, no marker) and as a 0-byte file. On the base the same scenario leaves no file and the leaf is recovered, so the docstring's "strictly no worse than before" is false for the torn-write case, and state.py's "unreadable errs towards re-running" does not hold for TRUNCATED — truncated errs towards retiring. That is the exact catastrophe the slice exists to prevent, reintroduced by the write it added. Fix inside the function the patch already added: write a sibling temp file and `os.replace()` it into place, so the record is all-or-nothing. Keep it best-effort — still `except OSError`, still no narrowing of the retry contract (criterion 5). Add a leg pinning it: a torn/0-byte error log must recover its leaf, not retire it. 2. SECONDARY — the settled/unsettled asymmetry that made (1) dangerous is worth removing at the source: an EMPTY or contentless log currently reads as settled by default. Consider making `_unsettled`/`leaf_ran_and_failed` fail towards re-running for a log with no recognisable attempt record at all, consistent with the stated fail-direction. Not in scope for this rebuild: the observation that the mid-retry post-mortem is unlinked by `_invoke_leaf_resilient`'s staleness clear before `assemble` runs. The brief pre-decided that under criterion 4, and the adversary flagged it as a human scope call, not a rebuild item. Leave criterion 4 honoured and `test_leaf_resilience.py` untouched; carried to Act.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the advisory findings, not on the design: the slice is right-sized, the
  single-point-of-truth predicate is the right shape, and the red->green evidence held up
  under independent reproduction and four mutants. One local defect blocks it.

  1. BLOCKING — make the unsettled-record write crash-safe. `_flush_attempt_records`
     (leaves.py) uses `Path.write_text`, i.e. open(O_TRUNC) -> write -> close, and the
     UNSETTLED marker is the LAST thing written. So the file passes through a 0-byte state
     and, for records larger than the buffer, prefix states — and any such partial state has
     no trailing marker, so `state.leaf_ran_and_failed` returns True and a reviewer that
     still had attempts left is RETIRED instead of re-run. Measured on the target tree under
     RLIMIT_FSIZE (2048 bytes, no marker) and as a 0-byte file. On the base the same scenario
     leaves no file and the leaf is recovered, so the docstring's "strictly no worse than
     before" is false for the torn-write case, and state.py's "unreadable errs towards
     re-running" does not hold for TRUNCATED — truncated errs towards retiring. That is the
     exact catastrophe the slice exists to prevent, reintroduced by the write it added.
     Fix inside the function the patch already added: write a sibling temp file and
     `os.replace()` it into place, so the record is all-or-nothing. Keep it best-effort —
     still `except OSError`, still no narrowing of the retry contract (criterion 5).
     Add a leg pinning it: a torn/0-byte error log must recover its leaf, not retire it.

  2. SECONDARY — the settled/unsettled asymmetry that made (1) dangerous is worth removing
     at the source: an EMPTY or contentless log currently reads as settled by default.
     Consider making `_unsettled`/`leaf_ran_and_failed` fail towards re-running for a log
     with no recognisable attempt record at all, consistent with the stated fail-direction.

  Not in scope for this rebuild: the observation that the mid-retry post-mortem is unlinked
  by `_invoke_leaf_resilient`'s staleness clear before `assemble` runs. The brief pre-decided
  that under criterion 4, and the adversary flagged it as a human scope call, not a rebuild
  item. Leave criterion 4 honoured and `test_leaf_resilience.py` untouched; carried to Act.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
