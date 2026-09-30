# Adversarial review — issue #541 (advisory; never gates)

Grounded on `$PDCA_TARGET` (`template/…`), patch applied in the worktree over base `7eb7e24`.
Red→green re-run independently: 12 of 13 legs fail with the two production files stashed,
13/13 pass with them — the core evidence is honest and drives the real site entry points
(`leaves._run_review_sandboxed` / `_run_advisory_sandboxed` / `_run_plan_advisory_sandboxed`).
The refutations below are all against the **two carry-forward remedies**, whose guard tests
(`tests/test_attempt_harvest.py:263` and `:376`) pass in *both* legs — so C4's red leg is no
evidence for either of them, and both turn out to be incomplete.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/assemble.py:112` (`_LEAF_STATUS_HEADER_LINES = 8`),
  used at `:122-131` and `:211`: the "header region" discriminator is defeated by a quote in the
  first 8 lines, so carry-forward item 3 (a real verdict must keep its findings) is still broken —
  and still a **regression against the base**. Concrete case, run both ways: an advisory artifact
  whose body is `# Advisory review — adversary` / blank / `- NEEDS-HUMAN [impl] — off-by-one at
  foo.py:12` / `- NEEDS-HUMAN [impl] — the placeholder emits this marker:` / a fenced block whose
  single line is the leaf-status comment with an unknown token (fence opens at line 5, marker at
  line 6). Pre-fix `assemble.collect_needs_human` returns both items as `impl`; post-fix both come
  back `human`, prefixed "leaf produced no verdict (unrecognised leaf status …)" — the `[impl]`
  routing of two genuine findings is stripped, which is exactly what the rebuild was told to stop.
  The added guard at `tests/test_attempt_harvest.py:376` only avoids the hole by construction (its
  fence sits at line 10+), and it passes with the production change reverted, so nothing in C4
  covers this. The carry-forward's *other* offered remedy — "keep '' for an artifact that carries a
  verdict table / findings" — is not subject to a line-position accident and would hold here.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:891-909`
  (`_live_attempt_overwrote_it`, digest-only), with the sticky flag set at `:941-947` and consumed
  at `:856`: carry-forward item 1 is only half-closed — a **live verdict is still destroyed**, and
  again this is a regression against the base. Concrete case, driven through `_run_review_sandboxed`:
  attempt 1 writes a residue and `chmod(artifact, 0o000)` before dying transiently (the file, not the
  directory — the ordinary shape of an unreadable leftover); `withdraw` cannot read it, so `_disown`
  sets `_unreadable = True` permanently; attempt 2 — writing **atomically via a temp file +
  `os.replace`**, the standard safe-write idiom — lands its complete review at the path and exits 0.
  `_live_attempt_overwrote_it()` short-circuits on `_unreadable` and the harvest refuses: measured
  pre-fix "live verdict filed? True", post-fix "False" plus an un-owned placeholder, with the real
  review dying with the sandbox. The carry-forward asked for "content/**inode** comparison"; only
  content was implemented. Recording `st_ino` / `st_mtime_ns` at `withdraw` time and treating any
  stat change as "the live attempt's file" closes this *and* the unreadable case, since the residue's
  identity is knowable even when its bytes are not.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:909`
  (`digest is not None and digest not in self._residues`): the same root, second case — content
  equality cannot tell "nobody rewrote it" from "rewritten byte-identically". Concrete case, driven
  through `_run_review_sandboxed` with the patch's own `lock=True` stub shape: a **deterministic
  command-mode leaf** (the harness supports arbitrary `argv`; its own stubs are exactly this) writes
  the same artifact on attempt 1, dies transiently under a sandbox whose directory is no longer
  writable, then writes the identical bytes on attempt 2 and exits 0. Result: `check-review.md` is
  the un-owned placeholder and the live attempt's complete verdict is discarded. The new guard at
  `tests/test_attempt_harvest.py:263` cannot see this — its live text differs from the residue.

- `template/src/pdca_harness/leaves.py:790-791` (`_RESIDUE_LINES` / `_RESIDUE_READ`) — observation,
  not a refutation: the cap is real (a 3.7 MB residue dying 3 times now yields a 12 KB
  `check-review.error.log`, vs the ~9 MB the carry-forward measured), but the bound is per-read, not
  total. Worst case measured through the production path: a newline-free 3 MB residue that cannot be
  withdrawn over 3 attempts writes **601,487 bytes** into the tracked `check-review.error.log`
  (~200 KB quoted per attempt). Whether ~600 KB per incident in project history is acceptable is a
  judgement call, not a defect against the instruction, which asked only for a head/tail cap.

- `template/src/pdca_harness/leaves.py:3333` and `template/src/pdca_harness/size_signal.py:240` —
  scope note, pre-existing (identical before and after this diff, so not filed against the builder):
  both still call `assemble.leaf_status()`, which matches the marker *anywhere* and for *recognised*
  tokens too. An advisory artifact that quotes the marker — as any leaf reviewing this harness does,
  including with the new `unowned-empty` token this patch introduces — is therefore still read as a
  placeholder by the plan-revision counter and by the size signal, and (via `_LEAF_STATUS_LABEL`,
  which the patch deliberately left matching anywhere) still has every finding relabelled and forced
  HUMAN in §6. The patch's own comment at `assemble.py:100-109` argues this hazard is real; the
  remedy was applied to one of the three readers and only to unknown tokens.

Attempted and could not refute: (a) the red→green itself — reproduced independently, and the legs
drive production, not a copy (C5's claim holds); (b) criterion 6 — `shutil.copy2(self.produced,
self.dest)` at `leaves.py:859` is now the only harvest, no fourth site and no second caller of
`_invoke_leaf_resilient` exists (`leaves.py:846`); (c) criterion 5 — the attempt budget is untouched
(3 attempts under a locked sandbox, `test_leaf_resilience` and `test_attempt_ownership` still green);
(d) the new unsettled preserved log does not fool `state.leaf_ran_and_failed`,
`driver._resume_interrupted_check` or `assemble._missing_review_text`, and the placeholder's
`See <log>` pointer stays guarded by `error_log.exists()` (`leaves.py:2955-2957`); (e) the
placeholder's own marker still lands on line 5 even when a multi-line `argv` is interpolated into
the reason (`repr` escapes it), so the 8-line window does not misfire on today's placeholders.
