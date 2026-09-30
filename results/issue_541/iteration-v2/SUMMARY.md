# Result — issue 541 / no-dead-attempts-artifact-harvested-as-a-live-ones

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch applied on top of child-1's accepted result:
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: Fixed
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing the attempt-aware harvest fix that must prevent dead retry artifacts from being filed as live reviewer, advisory, or plan-advisory output while preserving recoverable evidence.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief gives an executable three-site reproduction and separately specifies dead-residue refusal, evidence preservation, live-output behavior, unchanged retries, truthful status, and one shared owner; the corresponding production-path cases begin at `template/tests/test_attempt_harvest.py:188`. |
| C2 Reproduction (red pre-fix) | PASS | With the tracked production changes stashed, the focused test module reproduced the defect at all three sites (9 failures and 3 errors); the three-site assertion is grounded at `template/tests/test_attempt_harvest.py:188`. |
| C3 Change | FAIL | A real artifact that quotes an unknown status as a standalone line inside an early fenced block is classified as a placeholder, converting its `[impl]` finding to HUMAN/“no verdict”; the first-eight-lines heuristic does not exclude fenced quotes at `template/src/pdca_harness/assemble.py:130`. |
| C4 Verification (red→green) | PASS | Independent replay produced the pre-fix red above and then 13/13 green after restoring the patch; the live-overwrite, refusal, preservation, label, and shared-owner legs are exercised from `template/tests/test_attempt_harvest.py:188`. |
| C5 Causal adequacy | FAIL | The carried-forward requirement to retain real findings that merely quote an unknown marker remains incomplete for an early fenced quote, so valid implementation findings can still lose routing at `template/src/pdca_harness/assemble.py:130`. |
| T1 Structure | PASS | One `_LeafHarvest` owns the mechanism at `template/src/pdca_harness/leaves.py:794`, and all three production sites delegate to it at `template/src/pdca_harness/leaves.py:2838`, `template/src/pdca_harness/leaves.py:3194`, and `template/src/pdca_harness/leaves.py:3497`. |
| T2 Shape | PASS | Direct rerun reported `lint_docs: OK` and a clean 22-page render/link audit; `git diff --check` also reported no patch-format errors. |
| T3 Runtime | PASS | Direct patched-target execution passed all 1,816 driver tests (2 skips); the local root replay lacked `copier`, while the frozen `T3-suite` log shows all 7 copier-backed root tests passed on the gate host. |
| T4 Contribution | N/A | The row ran before `pr-description.md` exists and explicitly defers its substantive contribution-artifact audit to the mandatory publish re-gate. |
| T5 Judgment | NEEDS-HUMAN | Maintainer must confirm prerequisite #540 publish order and absence of overlapping merged/closed/rejected work by affected path — this target exposes only one synthetic base commit and no remotes, so rejected-work prior art cannot be mechanically settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether the attempt-attribution behavior is fit for real reviewer retries — mechanical stub coverage is strong, but the early-fenced-quote loss above still risks suppressing a genuine implementation finding. |

### Advisory — adversary

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

### Advisory — code-review

# Check advisory — code review (second lens: bugs the patch introduces / reuse / efficiency)

Scope: only `template/src/pdca_harness/leaves.py`, `template/src/pdca_harness/assemble.py`
and the new `template/tests/test_attempt_harvest.py`, as touched by this diff. Verified
against target source at `$PDCA_TARGET`. The three prior sign-off findings (live-verdict
destruction by an un-owned refusal, unbounded residue quoting into a tracked file, and the
unknown-status fallback demoting real findings) all read as genuinely fixed in this build —
`_live_attempt_overwrote_it` settles ownership by digest, `_read_residue` bounds head/tail,
and `_written_as_a_placeholder` restricts the unknown-token fallback to the header region.
C4's log confirms an honest red→green through the real entry points.

## Findings

- NEEDS-HUMAN [impl] — `withdraw()` (`leaves.py:861-884`, called from the retry loop at
  `leaves.py:751-752`) re-reads and re-quotes the **same** un-removed residue for **every**
  subsequent dead attempt, mislabelling it as that attempt's own output. Once one attempt's
  file cannot be `unlink()`ed (the exact scenario the patch's own `lock=True` legs build),
  the file is still sitting at `self.produced` when the *next* attempt dies too — `withdraw()`
  has no "have I already accounted for this exact residue?" check, so it reads it again,
  fails to unlink it again, and returns another `_record(attempt, …)` block claiming
  *that* attempt "left" the file at `self.produced.name`, even though the script never wrote
  to it on that invocation (n != 0 in the stub's own script, `test_attempt_harvest.py:594`).
  Concretely: `_drive(..., deaths=3, lock=True)` (exercised by
  `test_attempt_harvest.py:837-847`, `test_an_unwithdrawable_residue_does_not_narrow_the_retry_contract`)
  produces a settled `check-review.error.log` with the *same* residue quoted three times,
  attributed to attempts 1, 2 **and** 3 — reintroducing, one level down, the very defect this
  issue exists to remove ("no notion of *which attempt* wrote it"), plus tripling the
  read+sha256 work on a large residue for no benefit. The existing test only asserts
  `assertIn(_DEAD_MARK, …)` and the attempt count, so it doesn't catch the duplication/
  misattribution. Fix direction: track the digest(s) already disowned (`self._residues` is
  already populated for exactly this) and have `withdraw()` return `""` (or a
  "same as a prior attempt's" note, not a fresh "attempt N left…" block) when the file at
  the path is unchanged from what a previous `withdraw()` call already recorded and failed
  to remove.

- No other correctness bugs found in the new `_LeafHarvest` / `_read_residue` /
  `_artifact_digest` machinery (`leaves.py:794-1001`) or in the `assemble.py` label/marker
  changes (`assemble.py:85-131, 199-217`): the success/failure branching in
  `_LeafHarvest.run` (`leaves.py:838-859`), the sticky-conservative handling of an unreadable
  residue (`_unreadable`, `leaves.py:891-909`), the settlement-marker neutrality of the
  preserved account (`_WITHDRAWN_TRAILER` carries no `ATTEMPTS_SPENT_MARKER`, so
  `state.leaf_ran_and_failed` correctly reads `False`), and the three call sites
  (`leaves.py:2838-2851`, `3194-3205`, `3497-3508`, not all quoted here) are all
  internally consistent and free of dangling references to the old `err`/`produced`
  pattern they replaced.

- Minor, not flagged as an action item: `_read_residue` (`leaves.py:954-985`) uses
  `fh.readline(_RESIDUE_READ)` to bound line length, which can split a multi-byte UTF-8
  character across two 1000-byte reads and introduce a stray `�` at that boundary when
  decoding with `errors="replace"`. This only affects the *quoted, truncated* display text
  in a tracked error log (never the digest, which hashes raw bytes), so it's cosmetic at
  worst — noting it rather than raising it, since it doesn't affect any success criterion.

## Reuse / simplification / efficiency

- Criterion 6 (one owner, not three copies) reads as genuinely satisfied: all three sites
  now differ only in their paths and their own §6 prose, exactly as the brief asked
  (`leaves.py:2838-2844`, `3194-3199`, `3497-3502` — the `_LeafHarvest` construction+`.run()`
  call is identical in shape at each). No further de-duplication opportunity stands out.
- `_read_residue` and `_artifact_digest` both hash a file with `hashlib.sha256`, but they are
  not simple duplicates worth merging: `_read_residue` must also bound and return quoted text
  for a residue at withdrawal time, while `_artifact_digest` is a plain whole-file digest used
  once, after success, against a (potentially large, non-residue) live artifact — collapsing
  them would force the live-file path to also build a head/tail text it never uses. Leaving
  them separate is the right call here; flagged only because the finding above already touches
  the same code, not as an independent complaint.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Maintainer must confirm prerequisite #540 publish order and absence of overlapping merged/closed/rejected work by affected path — this target exposes only one synthetic base commit and no remotes, so rejected-work prior art cannot be mechanically settled here.
- [ ] Validation — fitness-to-purpose — The human must decide whether the attempt-attribution behavior is fit for real reviewer retries — mechanical stub coverage is strong, but the early-fenced-quote loss above still risks suppressing a genuine implementation finding.
- [ ] `template/src/pdca_harness/assemble.py:112` (`_LEAF_STATUS_HEADER_LINES = 8`),
- [ ] `template/src/pdca_harness/leaves.py:891-909`
- [ ] `template/src/pdca_harness/leaves.py:909`
- [ ] `withdraw()` (`leaves.py:861-884`, called from the retry loop at

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rebuild for issue_541, round 3. The slice is right and the core landed again: all three harvest sites genuinely share one owner (criterion 6 — the point of this child), the retry budget is untouched (criterion 5), and the red→green is honest through the real entry points. Do NOT re-open the structure, do NOT re-slice, and keep everything else as built. Two of the three round-2 carry-forward remedies were only PARTIALLY closed, and the code review found a third defect inside the fix itself. Close these three, nothing more. 1. assemble.py:112 — the header-region remedy is defeated by an early fenced quote. `_LEAF_STATUS_HEADER_LINES = 8` (used at :122-131 and :211) classifies a REAL artifact as a placeholder when it quotes an unknown status token as a standalone line inside a fenced block that opens in the first 8 lines (fence at line 5, marker at line 6). Measured: two genuine `NEEDS-HUMAN [impl]` findings come back `human` prefixed "leaf produced no verdict (unrecognised leaf status …)" — the #264 `[impl]` routing is stripped, still a regression against the base, and self-triggering in this repo. The guard at tests/test_attempt_harvest.py:376 only misses the hole by construction (its fence sits at line 10+) and passes with the production change reverted, so C4 covers none of it. Prefer the OTHER remedy the round-2 carry-forward offered — keep "" for an artifact that carries a verdict table / findings — which is not subject to a line-position accident and holds in this case. Add a leg with the fence at line 5. 2. leaves.py:891-909 — `_live_attempt_overwrote_it` is digest-only; the carry-forward asked for content/INODE. Two measured cases still destroy a LIVE verdict (both regressions against the base), driven through `_run_review_sandboxed`: (a) a residue that could not be READ sets `_unreadable = True` permanently (:941-947, consumed at :856), so an attempt that writes its complete review atomically via temp file + `os.replace` and exits 0 is refused — "live verdict filed?" pre-fix True, post-fix False, with an un-owned placeholder in its place; (b) content equality cannot distinguish "nobody rewrote it" from "rewritten byte-identically" (:909) — a deterministic command-mode leaf writing identical bytes on attempt 2 has its verdict discarded. Record `st_ino` / `st_mtime_ns` at withdraw time and treat any stat change as the live attempt's file: that closes both, including the unreadable case, since the residue's identity is knowable even when its bytes are not. Existing guard at tests/test_attempt_harvest.py:263 cannot see (b) — its live text differs from the residue. 3. leaves.py:861-884 — `withdraw()` re-quotes the SAME un-removable residue for every subsequent dead attempt. Once one attempt's file cannot be unlinked (the patch's own `lock=True` shape), it is still at `self.produced` when the next attempt dies, and `withdraw()` has no "have I already accounted for this residue?" check: it reads it again, fails to unlink it again, and emits another `_record(attempt, …)` claiming THAT attempt left it — even though that invocation never wrote. `_drive(..., deaths=3, lock=True)` yields the same residue quoted three times, attributed to attempts 1, 2 and 3 — reintroducing "no notion of which attempt wrote it" one level down, inside the fix for it, plus tripling the read+sha256 on a large residue. `self._residues` is already populated for exactly this: return "" (or a "same as a prior attempt's" note, not a fresh "attempt N left…" block) when the file is unchanged from what a previous withdraw already recorded and failed to remove. The current test only asserts `assertIn(_DEAD_MARK, …)` plus the attempt count, so add a leg that asserts the residue is accounted for ONCE. Not defects against the brief, do not spend the round on them: the ~600 KB worst-case residue quoting (the head/tail cap asked for was delivered; the bound is per-read, not total), the UTF-8 split at the `readline` boundary in `_read_residue` (cosmetic, display text only), and the pre-existing `assemble.leaf_status()` readers at leaves.py:3333 / size_signal.py:240 (identical before and after this diff — Act candidate, not this child's). The T5 ordering item is a publish-time concern, not a patch defect: the stack base (`pdca-integration/main`, on #540) is already correct.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
