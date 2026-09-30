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

Task under review: prevent artifacts left by dead reviewer/advisory attempts from being harvested as a later successful attempt's output, while preserving evidence and retry semantics at all three harvest sites.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance decision is explicit across artifact attribution, evidence retention, live-output compatibility, truthful status, unchanged retries, and one shared owner; the affected production boundary is the resilient retry/harvest path at `template/src/pdca_harness/leaves.py:674`. |
| C2 Reproduction (red pre-fix) | PASS | The real three site entry points reproduce the defect: with production hunks stashed, the focused module produced 9 failures and 2 errors, including dead text filed at every site (`template/tests/test_attempt_harvest.py:172`). |
| C3 Change | PASS | One owner now withdraws each dead attempt's artifact before retry and is used by review, advisory, and plan-advisory harvests, so the required attribution boundary is complete (`template/src/pdca_harness/leaves.py:781`, `template/src/pdca_harness/leaves.py:2744`, `template/src/pdca_harness/leaves.py:3099`, `template/src/pdca_harness/leaves.py:3402`). |
| C4 Verification (red→green) | PASS | Independent stash/restore rerun was red pre-fix and 9/9 green post-fix; frozen verification reports the same transition (`gate-logs/C4-verify.log:10`, `gate-logs/C4-verify.log:16`). |
| C5 Causal adequacy | PASS | Ownership changes at the attempt-death boundary, and an unwithdrawable path is disowned then refused without shortening retries; this removes cross-attempt attribution rather than probing or guarding an optional capability (`template/src/pdca_harness/leaves.py:843`, `template/src/pdca_harness/leaves.py:868`). |
| T1 Structure | PASS | The structural decision is centralized in `_LeafHarvest`, with the three sites retaining only their path and placeholder policy; no fourth copy of the harvest mechanism remains (`template/src/pdca_harness/leaves.py:781`). |
| T2 Shape | PASS | `git diff --check` and the independently rerun docs linter are clean; the frozen site-render/link audit also passed (`gate-logs/T2-docs.log:10`, `gate-logs/T2-docs.log:15`). |
| T3 Runtime | PASS | The focused module passes 9/9 and the independently rerun driver suite passes 1,812 tests with 2 skips; the frozen environment additionally ran the seven copier-backed render/update tests and reports both suites green (`template/tests/test_attempt_harvest.py:172`, `gate-logs/T3-suite.log:10`, `gate-logs/T3-suite.log:1668`). |
| T4 Contribution | N/A | Contribution artifacts do not exist during Check by design; the publish gate owes and cannot skip their substantive audit (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Human must enforce dependency ordering before publication — the target is correctly based on #540, but GitHub comparison shows base `480fa6b` is two commits ahead of target branch `main`, so publishing this child first would omit its semantic prerequisite (`template/src/pdca_harness/leaves.py:692`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must decide whether the resulting operator contract—preserve the dead text, refuse ambiguous output, and request a rerun—is fit for real reviewer operations; automated stubs establish mechanics but cannot make that product judgment (`template/src/pdca_harness/leaves.py:873`, `template/src/pdca_harness/assemble.py:99`). |

### Advisory — adversary

# Adversary — refutation attempts (#541)

Evidence re-run independently in a throwaway copy of `$PDCA_TARGET` (never the target
itself): `PYTHONPATH=src python3 -m unittest tests.test_attempt_harvest` is **green** with
the patch (9/9) and **red** with `assemble.py` + `leaves.py` stashed back to the pre-fix
base (9 failures + 2 errors, the same tracebacks as `gate-logs/C4-verify.log`). Every leg
drives the real `leaves._run_review_sandboxed` / `_run_advisory_sandboxed` /
`_run_plan_advisory_sandboxed`, so the red→green is not a parallel re-implementation. What
follows is what survived that.

- NEEDS-HUMAN — the un-owned refusal at `template/src/pdca_harness/leaves.py:836-841`
  destroys a LIVE verdict it could prove is live, and the patch's tests never cover that
  combination. `unlink()` needs write permission on the *directory*, while `open(path,"w")`
  needs it only on the *file* — so the exact scenario the patch's own leg builds (the dying
  attempt does `os.chmod(".", 0o500)`) still lets the NEXT attempt overwrite the residue
  with its own complete review. Driven against the real reviewer site with the stub writing
  `| C4 | PASS | LIVEMARK real verdict |` on attempt 2, `_degrade` fires with
  `self.produced.read_text()` equal to the LIVE attempt's full verdict: the bundle gets
  `# Advisory review — NOT COMPLETED`, the error log holds only the dead attempt's text, and
  the live verdict dies with the `tempfile.TemporaryDirectory` at
  `template/src/pdca_harness/leaves.py:2697`. So criterion 2 ("a real verdict must not be
  destroyed while the operator is told none was produced") is violated for the LIVE
  attempt's verdict by the code that enforces it for the dead one's, and criterion 3 ("the
  live attempt's own artifact is harvested exactly as today") fails in this corner. The
  harness already read the dead bytes in `withdraw`
  (`template/src/pdca_harness/leaves.py:851-857`), so a content/inode comparison would
  settle ownership without weakening the refusal. Left for the human rather than routed to
  Do because the brief's criterion 5 *ordered* "refuse to HARVEST on the success branch" —
  the collision between criteria 3 and 5 is the human's to rule on. Note the test gap either
  way: `template/tests/test_attempt_harvest.py:236,251,284` all pass `lock=True` with the
  default `live=""` (`:150`), so no leg ever has a live attempt writing under a locked
  sandbox.

- NEEDS-HUMAN [impl] — the withdrawn residue is quoted with NO bound into a tracked bundle
  file: `template/src/pdca_harness/leaves.py:852` reads the whole artifact and `:905-907`
  embeds it whole, once per attempt (`:746-751`). Measured against the real reviewer site: a
  stub that writes a 3.2 MB `check-review.md` and dies transiently on all three attempts
  yields a **9,600,536-byte `check-review.error.log`** in the bundle — held entirely in
  memory first, plus a `.check-review.error.log.partial` sibling copy. The channel this
  deliberately mirrors is bounded (`template/src/pdca_harness/progress.py:176`,
  `err_tail: deque[str] = deque(maxlen=200)`), and `results/` is tracked (only
  `results/issue_selftest/` is ignored, `template/.gitignore.jinja:16`), so this commits
  multi-MB logs into project history where today's code commits nothing at all. A head/tail
  cap with an elision line, exactly like `err_tail`'s, closes it.

- NEEDS-HUMAN [impl] — the new unknown-status fallback at
  `template/src/pdca_harness/assemble.py:191` demotes REAL findings. It maps *any*
  unrecognised marker token to `_UNKNOWN_LEAF_STATUS_LABEL`, and `leaf_status` matches the
  marker ANYWHERE in the artifact. Run against the patched `assemble`, an artifact carrying
  a full verdict table and two `- NEEDS-HUMAN [impl] —` findings, one of which merely
  *quotes* a marker with an unknown token (an advisory leaf discussing, say,
  `pdca:leaf-status some-future-status`), comes back as
  `NeedsHumanItem(text='leaf produced no verdict (unrecognised leaf status …) — off-by-one
  at foo.py:12', kind='human')` for BOTH items: §6 now says the leaf produced no verdict
  when it produced one, and the #264 `[impl]` routing is lost. Pre-fix the same artifact was
  untouched (unknown token → label `""`). It is self-triggering in this repo — an adversary
  artifact reviewing this patch has to avoid writing the marker verbatim, as this one does —
  and it is not asked for by the brief (criterion 4 is about the leaf-status *label*, not
  about unrecognised markers), so it is extra surface on a "one logical fix". Requiring the
  marker in the placeholder's own header region, or keeping `""` for an artifact that
  carries a verdict table, restores the old behaviour without giving up the #541 label.

Attempted and could **not** refute: (a) that a site was left behind — all three are
converted, `_invoke_leaf_resilient` has exactly one caller left
(`template/src/pdca_harness/leaves.py:828`), and there is no fourth `copy2` harvest; (b)
that the new `unowned-empty` status breaks an enumerating reader — the only two
`leaf_status` consumers (`leaves.py:3238`, `size_signal.py:240`) test truthiness, and
`_LEAF_STATUS_LABEL` has an entry, so `_items_from_artifact` still forces HUMAN and the
auto-iterate path stays closed; (c) that the retry contract narrowed — an un-withdrawable
residue still costs no attempt (3 observed); (d) that #540's four `*.error.log` readers are
made false — every degrade path writes its placeholder artifact, and `review_never_ran` /
`run_advisory_leaves(only_missing=True)` / `_missing_review_text` /
`driver._resume_interrupted_check` all key on artifact-exists *or* a SETTLED log, while
`_preserve` writes an unsettled record (`leaves.py:893`); (e) that a leg could pass for the
wrong reason — all 9 fail on the pre-fix base. One behaviour change I judged harmless and do
not file: a leaf that recovers from a transient blip and then writes nothing now leaves an
unsettled `check-review.error.log` behind where today it leaves none (`leaves.py:873-897`);
no reader misreads it, and the placeholder gains only a "See `check-review.error.log`"
pointer.

### Advisory — code-review

# Advisory code review — issue #541 (dead-attempt harvest)

Reviewed `patch.diff` against the target source (`leaves.py`, `assemble.py`, `state.py`),
traced every branch of `_LeafHarvest` (`leaves.py:781-907`) and its three call sites
(`leaves.py:2744-2754`, `:3099-3110`, `:3402-3412`), and cross-checked against
`gate-logs/C4-verify.log` (confirms a genuine red pre-fix / green post-fix leg — 9
failures + 2 errors without the fix, 9/9 with it — driven through the real entry points).

**No correctness bugs introduced by this patch, and no reuse/duplication left on the
table.** Specifics I checked and found sound:

- `_LeafHarvest.withdraw` (`leaves.py:843-866`) is called for every dying attempt
  unconditionally, before the transient/stop-rule check
  (`leaves.py:750-754`), so the *last* attempt's residue is preserved exactly like every
  earlier one's — matches brief criterion 5 and is exercised by
  `test_an_unwithdrawable_residue_does_not_narrow_the_retry_contract`.
- `_disown`'s un-owned message (`leaves.py:899-903`, worded "the leaf exited 0, but…") is
  only ever read back in `run()` after `err is None` is confirmed
  (`leaves.py:830-837`) — i.e. only once the leaf really has exited 0 — so the message is
  never stale/misleading despite being written at disown-time, before that outcome is known.
- On a leaf that exhausts all attempts without ever exiting 0, `self._unowned`/`_account` are
  set but never read (`run()`'s `err is not None` branch bypasses them); the same residue
  text still reaches the bundle because `_invoke_leaf_resilient`'s own settled-record write
  (`leaves.py:769`) already includes every `withdraw()` return value. No double-write, no
  lost residue.
- `_preserve()` (`leaves.py:878-897`) deliberately does not use
  `state.settled_record`/`unfinished_record` but its own `_WITHDRAWN_TRAILER`
  (`leaves.py:773-778`), which is a distinct string from `state.ATTEMPTS_SPENT_MARKER`, so
  `state.leaf_ran_and_failed` correctly reads `False` on a preserved-but-unsettled log —
  verified against `state.py:182-196` and matches
  `test_the_preserved_account_never_reads_as_a_leaf_that_spent_its_attempts`.
- All three call sites pass `empty_reason`/`failed_reason` strings identical to what the
  three hand-written branches used to say (`"reviewer produced no check-review.md"`,
  `"produced no artifact"` ×2, `"leaf failed"` default vs `"reviewer leaf failed"`
  override), so the refactor is behavior-preserving on the non-#541 paths, not just on the
  new one.
- `assemble._items_from_artifact`'s fallback to `_UNKNOWN_LEAF_STATUS_LABEL`
  (`assemble.py:190-191`) closes the same hole the brief's C4 red leg exercised
  (`test_an_unrecognised_status_is_still_a_placeholder_never_a_verdict`) without weakening
  the existing recognised-status paths — `if not label: return items` is unchanged for the
  real "no marker at all" case.
- The de-duplication itself (brief criterion 6) is real, not cosmetic: all three call sites
  now route through the one `_LeafHarvest` class, and `test_all_three_sites_go_through_the_one_owner`
  drives that by substituting a recording subclass at the module attribute the call sites
  resolve dynamically (`leaves._LeafHarvest`), which is a valid patch point since Python
  resolves a bare name against module globals at call time.

If the diff is clean on both lenses, say so explicitly: **it is clean.** No findings to
route to a human or back to Do.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Human must enforce dependency ordering before publication — the target is correctly based on #540, but GitHub comparison shows base `480fa6b` is two commits ahead of target branch `main`, so publishing this child first would omit its semantic prerequisite (`template/src/pdca_harness/leaves.py:692`).
- [ ] Validation — fitness-to-purpose — Human must decide whether the resulting operator contract—preserve the dead text, refuse ambiguous output, and request a rerun—is fit for real reviewer operations; automated stubs establish mechanics but cannot make that product judgment (`template/src/pdca_harness/leaves.py:873`, `template/src/pdca_harness/assemble.py:99`).
- [ ] the un-owned refusal at `template/src/pdca_harness/leaves.py:836-841`
- [ ] the withdrawn residue is quoted with NO bound into a tracked bundle
- [ ] the new unknown-status fallback at

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
- Iteration delta (if iterating): Rebuild for issue_541. The slice itself is right and the core landed: all three harvest sites genuinely share one owner (criterion 6 — the whole point of this child), and the red→green is honest (independently re-verified through the real entry points). Do NOT re-open the structure or re-slice; fix the three findings the adversary raised and keep everything else as built. 1. The un-owned refusal can destroy a LIVE verdict (leaves.py:836-841). `unlink()` needs write permission on the DIRECTORY; `open(path,"w")` needs it only on the FILE — so in the very scenario the patch's own test builds (dying attempt does `chmod(".", 0o500)`), the next attempt can still overwrite the residue with its complete real review, and the harvest then refuses it. The live verdict dies with the temp dir while the bundle says "NOT COMPLETED". Settle ownership by content/inode comparison against the bytes already read in `withdraw` (leaves.py:851-857): if the file at the path is no longer the dead attempt's, it is the live attempt's work and must be harvested. That satisfies criterion 3 without weakening criterion 5's refusal, so the two stop colliding. Test gap to close with it: every `lock=True` leg passes the default `live=""` (test_attempt_harvest.py:150,236,251,284) — no leg has a live attempt writing under a locked sandbox. Add that leg. 2. The withdrawn residue is quoted with NO bound into a tracked bundle file. leaves.py:852 reads the whole artifact and :905-907 embeds it whole, once per attempt. Measured: a 3.2 MB artifact dying transiently three times yields a 9.6 MB `check-review.error.log`, held in memory first, plus a `.partial` sibling — committed into project history, since `results/` is tracked and only `results/issue_selftest/` is ignored. Cap it head/tail with an elision line, exactly like the channel it mirrors (`progress.py:176`, `deque(maxlen=200)`). 3. The unknown-status fallback demotes REAL findings (assemble.py:191). `leaf_status` matches the marker ANYWHERE in the artifact, so an artifact carrying a full verdict table and real `NEEDS-HUMAN [impl]` items — one merely QUOTING a marker with an unknown token — comes back labelled "leaf produced no verdict" for every item, losing the #264 `[impl]` routing. Pre-fix an unknown token gave "" and left the artifact alone. This is self-triggering in this repo and the brief never asked for it (criterion 4 is about the leaf-status LABEL, not about unrecognised markers). Either require the marker in the placeholder's own header region, or keep "" for an artifact that carries a verdict table — restoring the old behaviour while keeping the #541 label. Not in scope for the rebuild: the T5 dependency-ordering item is a publish-time concern, not a patch defect — the stack base (`pdca-integration/main`, on #540's `480fa6b`) is already correct.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
