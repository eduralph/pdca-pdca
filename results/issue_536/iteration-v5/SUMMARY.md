# Result — issue 536 / attempt-owned-leaf-records-and-harvests

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch: (i) each failed attempt's record is on disk
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
- Repo + branch target: eduralph/pdca-harness @ main (base `acb214a`; every `path:line`
  above was re-verified against it while this proposal was written)
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
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

Task under review: make retried reviewer and advisory leaves account for artifacts and failures by attempt, so interrupted or dead-attempt output cannot be filed as a live verdict.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is falsifiable and covers persistence, ownership, recovery, impersonation resistance, and the unchanged retry contract; the implementation-facing contract is explicit at `template/src/pdca_harness/leaves.py:684`. |
| C2 Reproduction (red pre-fix) | PASS | With only the production hunks stashed, the retained behavioral suite produced 23 failures and 4 errors, including missing predecessor records and dead-artifact adoption at `template/tests/test_attempt_ownership.py:233` and `template/tests/test_attempt_ownership.py:363`. |
| C3 Change | PASS | The patch stays on the specified accounting path: records are persisted before retry and residue is withdrawn before another attempt can claim it at `template/src/pdca_harness/leaves.py:727`; the excluded builder, transient-classification, and `progress.py` surfaces are untouched. |
| C4 Verification (red→green) | PASS | Independent stash/unstash execution was red with the fix absent, then all 31 ownership tests and all 5 untouched resilience tests passed with it restored; the crash-atomic leg is exercised at `template/tests/test_attempt_ownership.py:276`. |
| C5 Causal adequacy | PASS | The cause is transformed at the attempt boundary—a retry requires a recorded predecessor and cleared ownership at `template/src/pdca_harness/leaves.py:759`—while recovery consumes an explicit unsettled-state discriminator at `template/src/pdca_harness/leaves.py:898`; no capability probe or symptom guard was added. |
| T1 Structure | PASS | The invariant is centralized in the resilient wrapper and shared discriminator, while each harvest site only composes that mechanism; the reviewer integration is at `template/src/pdca_harness/leaves.py:2863` and both advisory twins are covered by `template/tests/test_attempt_ownership.py:680`. |
| T2 Shape | PASS | `git diff --check`, documentation lint, rendered-site generation, and internal-link audit all passed; the frozen host-CI log independently records the same clean patched-tree result. |
| T3 Runtime | PASS | The full offline driver suite passed, the frozen T3 run records both root and 1,789-test driver suites green, and the recovery behavior is driven end to end at `template/tests/test_attempt_ownership.py:1015`. |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check; the frozen deferred row says the substantive contribution audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm merged-history and closed/rejected-work overlap for the four affected non-`leaves.py` paths—including `template/src/pdca_harness/assemble.py:417`, `template/src/pdca_harness/driver.py:121`, `template/src/pdca_harness/state.py:68`, and `template/tests/test_attempt_ownership.py:216`—because the supplied prior-art record settles only `leaves.py`, so collision risk remains. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether re-running an interrupted reviewer/advisory after a genuinely killed Check produces the right operator-visible outcome—the syscall/process windows are simulated at `template/tests/test_attempt_ownership.py:276`, `template/tests/test_attempt_ownership.py:778`, and `template/tests/test_attempt_ownership.py:1015`, but live workflow fitness remains a human judgment. |

### Advisory — adversary

# Adversarial review — refutation pass (#506 / issue_536)

Evidence re-run locally at `$PDCA_TARGET`: green leg `PYTHONPATH=src python3 -m unittest
tests.test_attempt_ownership` → 31 tests OK; red leg (production hunks reverted with
`git checkout -- template/src/pdca_harness/`, the new test file kept) → 23 failures + 4
errors, every one behavioural — no module-level import fault, so the red leg cannot have
been the `PDCA-UNVERIFIABLE` route in disguise. Full `template` suite: 1789 tests OK,
`test_leaf_resilience.py` untouched. The C4 row is sound; the findings below attack the
fix, not the proof.

## Findings

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/assemble.py:85`, newly reached via
  `leaves.py:2940` (`_empty_run_class`) from `leaves.py:2892-2893`: the §6 line the human
  actually reads now files a false account of the run.** The patch is careful to widen the
  *placeholder* sentence (`leaves.py:2984-2996`: "the retries were spent, or one came back
  alive and yielded nothing") on the express grounds that "a slice whose invariant is that
  the harness never files a false account of a run cannot make an exception for the sentence
  the operator actually reads" — then stops one reader short. `_empty_run_class` newly routes
  `LEAF_STATUS_INFRA` for a run whose **last attempt ran to completion and exited 0**, and
  `assemble._LEAF_STATUS_LABEL[LEAF_STATUS_INFRA]` renders that as **"leaf did not run
  (transient infra — safe to re-run)"**. Reproduced against the patched tree: reviewer
  attempt 1 dies with `overloaded_error 529`, attempt 2 exits 0 writing nothing →
  `check-review.md` carries `<!-- pdca:leaf-status infra-empty -->` and
  `assemble.collect_needs_human` emits
  `leaf did not run (transient infra — safe to re-run) — re-run the Check reviewer…`.
  Before this patch `infra-empty` was reachable only through `_failure_class(err)`, where
  "leaf did not run" was true; the diff created the new reachability and neither the label
  (`assemble.py:85`) nor its comment (`assemble.py:80`, "ran, died with no output") followed
  it. Builder-fixable by iterating — widen the label exactly as the placeholder sentence was
  widened.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:1033-1034`: the residue record
  asserts "withdrawn" as fact, and on the fail-closed path this patch itself adds, the
  bundle's only durable copy of that claim is false.** `_residue_record` is composed *before*
  `_withdraw_residue` runs (`leaves.py:762-767` — and that ordering is right), so when the
  unlink is refused the archived `check-review.error.log` reads
  `----- attempt 1 — the check-review.md it left behind (withdrawn: a dead attempt's
  artifact is never harvested) -----` over a file still sitting in the sandbox — the very
  condition that ended the run. Reproduced against the patched tree with `Path.unlink`
  refusing `check-review.md`: the correction ("could not withdraw … stopping the retries")
  exists only on **stderr**, i.e. terminal scrollback, which `leaves.py:647` is on record
  saying the error log exists to replace. The branch already re-flushes the records
  (`leaves.py:768-769`), so the hook to correct the wording is in hand; on the
  `may_retry is False` variant (last attempt, or a non-transient death) there is no re-flush
  at all and the same false line is filed unamended. Same defect class the patch condemns two
  hundred lines away.

- **NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:773` narrows the shipped resilience
  contract, and the comment defending it is worded so as not to say so.**
  `if not (may_retry and recorded and owned): break` adds two stop conditions to
  `_invoke_leaf_resilient`; `leaves.py:770-772` claims "Neither widens the retry set" — true,
  and beside the point: they **narrow** it, while brief criterion (vi) asks that "the shipped
  resilience contract holds unchanged (attempt count, backoff, …)". Measured on both legs:
  with `Path.write_text` refusing the bundle log the base spends its full 3 attempts and the
  patch stops after 1 (`template/tests/test_attempt_ownership.py:264`); with `Path.unlink`
  refusing the sandbox artifact the base runs 2 and the patch runs 1
  (`test_attempt_ownership.py:497`; the red-leg log records `2 != 1`). So a recoverable
  rate-limit blip that coincides with a bundle write/unlink refusal now ends as "reviewer
  leaf failed" with **no review of the diff** — the outcome direction this slice exists to
  prevent. There is a fail-closed design that costs no attempts: carry `owned=False` forward
  and refuse to *harvest* that path on the success branch (the residue is already quoted by
  then) rather than ending the run. Whether to trade retries for ownership is an
  architectural / fitness call, not a builder nit — hence no `[impl]`.

- `template/src/pdca_harness/leaves.py:825-828` — minor, recorded rather than raised: the
  `.tmp.<pid>` sibling a kill can strand is correctly *not* claimed by
  `state.DOWNSTREAM_GLOBS` (`state.py:127`), exactly as the docstring says — but the same
  fact means `driver._archive_iteration` (`driver.py:436`) will never move it either, so a
  stranded temp lingers in the bundle root across every later round. Inert, and only
  reachable after a kill mid-write; noted so a later reader does not mistake it for evidence.

## Attempted and could not refute

- **Forging the in-flight trailer.** Tried both quoted channels (`_format_leaf_attempt`'s
  stderr tail, `_residue_record`'s artifact text) and the classic single-pass-`str.replace`
  re-formation attack (`"<!-- pd" + MARKER + "ca:leaf-attempt …"`, plus the nested variant):
  `_defang_in_flight` (`leaves.py:793-801`) cannot re-create the marker — the quoted
  replacement contains it nowhere and shares no suffix/prefix overlap with it. Combined with
  the whole-line, last-non-blank match at `leaves.py:922-923` (which survives `strip()`-
  equivalent payloads: trailing `\r`, NBSP), I could not make a leaf speak for the harness's
  own run.
- **Weakening the accept guard through the new `infra-empty` route.** `_items_from_artifact`
  forces both `infra-empty` and `human-empty` to `HUMAN` (`assemble.py:168-173`), so the
  reclassification changes §6 *wording* (finding 1) but cannot let a bundle auto-iterate or
  reach accept where it previously could not.
- **A fourth reader of the discriminator.** Grepped the package: the only readers of
  `*.error.log`-as-state are the three the patch updated (`leaves.py:2456`, `leaves.py:3202`,
  `assemble.py:425`). The plan-advisory path has no `only_missing` resume, and `docs/` states
  the discriminator nowhere, so no prose was left stale by the semantic change.
- **Sandbox-input collision for `artifact=`.** All three sites checked: `REVIEWER_INPUTS`
  (`leaves.py:68`) and `PLAN_ADVISORY_INPUTS` (`leaves.py:3293`) never seed a file at the path
  passed as `artifact=`, so `_withdraw_residue` cannot unlink a seeded input a later attempt
  needed, and the withdrawn path is always sandbox-local — never the bundle's shipped
  artifact from a prior round.
- **A raise-after-success in `_invoke`.** `_invoke` (`leaves.py:566-668`) raises only on
  `rc != 0`, so no live attempt's artifact can be reclassified as a dead attempt's residue;
  the interactive and stream-less branches reach the wrapper's success path with `records`
  empty and behave byte-identically to the base.
- **Runaway re-run of a recovered leaf.** An in-flight log makes `review_never_ran` true, but
  the recovered run's entry-time clear (`leaves.py:720`) removes it and every terminating
  branch files a placeholder first, so I could not construct a bundle that re-pays for the
  same leaf on successive `advance`s.

### Advisory — code-review

# Advisory code review — correctness + reuse/simplification (issue #64 lens)

Scope: this patch only (attempt-owned leaf records/harvests, #506), grounded on
`$PDCA_TARGET/template/src/pdca_harness/{leaves,driver,assemble,state}.py` and the new
`template/tests/test_attempt_ownership.py`. This is round 5; four prior sign-off rounds
already found and closed real defects (non-atomic flush, withdraw-before-persist kill
window, unsettled error logs left beside filed placeholders, unbounded-residue reads,
undecodable-log crashes, false "retries did not recover" prose, an untested second
recovery discriminator). I re-walked the mechanism fresh rather than trusting that
history, and traced every kill window, the defang/whole-last-line match, and all three
harvest sites end to end against the current target source.

## Findings

- `leaves.py:745-746` — minor redundant write, not a bug. On a successful attempt that
  produced no artifact over a run with a dead predecessor (`records and artifact is not
  None and not artifact.exists()`), the wrapper calls `_write_attempt_records(error_log,
  records, in_flight=True)` again. To reach this branch the loop must have already
  continued past a failed attempt whose own flush used the *same* `records` list and the
  *same* `in_flight=True` and whose `recorded` return value was `True` (required for the
  retry to have been allowed at all, `leaves.py:773`) — so this second write reproduces
  byte-identical content already durably on disk. It's correctness-safe (the call's
  return value is intentionally unchecked, and if this redundant write fails the
  already-landed state from the prior flush stands unchanged), just a needless
  temp-file + `os.replace` round trip on the "retried, came back alive, wrote nothing"
  path. Worth a comment noting it's deliberate belt-and-suspenders (or dropping it), but
  not worth gating on.

- No new correctness bugs found in the crash-atomic flush (`_atomic_write_text`,
  `leaves.py:804`), the persist-before-unlink ordering in the failed-attempt branch
  (`leaves.py:759-773`, closing round 3's withdraw-before-persist window), the
  `_defang_in_flight` neutralisation applied to both quoted channels (the residue text at
  `leaves.py:1035` and the stderr tail *and* its no-output fallback at `leaves.py:1074`,
  closing round 4's optional finding), the bounded/degrading residue read
  (`_residue_record`, `leaves.py:1024-1035`), or the three harvest sites' settle/no-settle
  symmetry (`leaves.py:2871-2897`, `:3248-3258`, `:3552-3563`) — all three now settle on
  both the `err is not None` branch and the empty-success branch, never on the
  artifact-harvested branch, matching the documented contract.

- Reuse note, not new to this round: the three harvest sites remain near-verbatim
  duplicates of each other (settle ordering, `_empty_run_class`/`error_log=` wiring, the
  `# see the reviewer` cross-references acknowledging the copy). This was already named
  by the iteration-3 carry-forward as a legitimate `_harvest_leaf`-helper Act candidate
  and deliberately deferred ("closing item 2 at three sites by hand is smaller than the
  refactor, and this patch is already oversized") — re-flagging only for completeness,
  not as a fresh finding.

- Test coverage: the new file drives all three harvest sites (`BothAdvisoryHarvestsAre
  AttemptAwareToo` parametrizes over `_run_advisory_sandboxed` and
  `_run_plan_advisory_sandboxed`, closing round 1/4's twin-blindness gap) and both #369
  recovery discriminators (`AnInterruptedLeafIsRecoveredNotRetired` for
  `review_never_ran`, `AnInterruptedAdvisoryLeafIsRecoveredToo` for
  `run_advisory_leaves(only_missing=True)`, closing round 4's untested-twin finding). I
  did not find a case that exercises production without also asserting something
  meaningful — no "test that doesn't actually exercise the fix" gap.

- C4 evidence (`gate-logs/C4-verify.log`) independently confirms the red leg is a real
  regression on the base (23 failures + 4 errors reverting only the production hunks) and
  the green leg is 31/31; `gate-logs/T3-suite.log` shows the full 1789-test driver suite
  green. No gate-adjudication concerns.

## Verdict

Clean on both lenses at this round. The one item above is a harmless, non-blocking
efficiency nit — not a correctness defect and not something requiring human
adjudication.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm merged-history and closed/rejected-work overlap for the four affected non-`leaves.py` paths—including `template/src/pdca_harness/assemble.py:417`, `template/src/pdca_harness/driver.py:121`, `template/src/pdca_harness/state.py:68`, and `template/tests/test_attempt_ownership.py:216`—because the supplied prior-art record settles only `leaves.py`, so collision risk remains.
- [ ] Validation — fitness-to-purpose — Decide whether re-running an interrupted reviewer/advisory after a genuinely killed Check produces the right operator-visible outcome—the syscall/process windows are simulated at `template/tests/test_attempt_ownership.py:276`, `template/tests/test_attempt_ownership.py:778`, and `template/tests/test_attempt_ownership.py:1015`, but live workflow fitness remains a human judgment.
- [ ] size backstop — this slice is behaving oversized: patch is 104 KB (threshold 80 KB); 4 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): WHY REJECTED — slicing, not direction. The fix's direction is right and its proof is sound: all gates green, C4 independently re-run (23 failures + 4 errors on the red leg, 31/31 green, full 1789-test suite green, test_leaf_resilience.py untouched as criterion (vi) required). Nothing here says the work is unwanted. It is rejected because the slice is too big to converge: 5 builder attempts, 4 sign-off rounds, patch 44 -> 68 -> 79 -> 93 -> 104 KB (threshold 80), with implementation-shaped adversary findings every single round (4, 4, 2, 3, 2). The size backstop fired at v4 and again at v5. THE ERROR CLASS TO DESIGN OUT (this is the actionable insight). The slice redefines the meaning of a shared signal — the presence/content of *.error.log ("the leaf ran and FAILED") is split into failed vs. merely-interrupted, plus a derived empty-run / leaf-status classification. That meaning has many independent readers, each hard-coding it at its own site. Every round converts the readers in view; the next round finds one more still speaking the old meaning: v1 assemble.py:417 — "the reviewer RAN AND FAILED" v2 driver.py:178-179 — "reviewer never ran" v3 leaves.py:2910 — "retries did not recover" v4 leaves.py:3176 — second #369 discriminator, unconverted v5 assemble.py:85 — "leaf did not run (transient infra — safe to re-run)" The adversary's phrase is exact: the patch widened the sentence it could see, "then stops one reader short." Note the axis MOVED rather than exhausted — v5 confirmed by grep that the *.error.log-as-state readers are now all converted, and the new finding is on a different shared value (the leaf-status enum -> label mapping). Two related faces of the same root (no single point of truth): - the patch's own new paths file false accounts — the very invariant the slice enforces (v1 human-empty misfiling, v2 "inert" docstring, v3 "retries did not recover", v5 the "withdrawn" line written over a file still present); - twin blindness — the mechanism is hand-copied at 3 harvest sites and 2 discriminators, so tests or _settle_leaf_record calls miss a twin (v1, v2 x2). Per-instance fixes cannot end this class. iterate-do would close the two named [impl] items and leave the generator intact. SPLIT SEAMS FOR THE RE-PLAN (candidates — Plan authors the briefs). A. Give the redefined meaning ONE owner: a single predicate/type that every reader consults (production branches, both #369 discriminators, assemble.py status labels and prose, driver.py operator messages). Ends the "stops one reader short" class by construction rather than by enumeration. B. The _harvest_leaf helper: de-duplicate the three near-verbatim harvest sites (settle ordering, _empty_run_class / error_log= wiring). Kills the twin-blindness face. The code-review advisory flags this as a legitimate deferred Act candidate, refused in round 3 on the express grounds that "this patch is already oversized" — that refusal is the loop: the refactor that ends the class is declined because the slice is too big, so the class keeps producing findings, so the slice keeps growing. C. The bookkeeping half proper — per-attempt record persistence, crash-atomic flush, trailer defanging (criteria (i) and (iv)). This part has converged and is stable across rounds; keep it intact rather than rebuilding it. MUST BE SETTLED IN THE BRIEF, NOT LEFT TO THE BUILDER. leaves.py:773 — the patch narrows the shipped retry contract (measured: base spends 3 attempts, patch stops after 1 on a bundle write refusal; base 2 -> patch 1 on an unlink refusal), while criterion (vi) demands the contract "holds unchanged". As written the builder is asked to satisfy both and cannot, which is why this surfaced as a fitness question with no [impl] tag. The next brief must pick one explicitly: either sanction the narrowing, or adopt the adversary's no-cost alternative — carry owned=False forward and refuse to HARVEST on the success branch (the residue is already quoted by then) instead of ending the run. Leaving this ambiguous will reproduce the same finding next round. DO NOT LOSE (open [impl] items, to land in whichever child slice owns the surface): - assemble.py:85 — widen _LEAF_STATUS_LABEL[LEAF_STATUS_INFRA] exactly as the placeholder sentence was widened; _empty_run_class now routes runs whose last attempt exited 0. - leaves.py:1033-1034 — _residue_record asserts "withdrawn" as fact; false on the fail-closed path this patch adds. The re-flush hook at :768-769 is already in hand; the may_retry is False variant files the false line unamended. - leaves.py:825-828 — recorded, not raised: a stranded .tmp.<pid> sibling is claimed by no DOWNSTREAM_GLOBS pattern, so _archive_iteration never moves it either. §6 left open (3 items: T5 prior-art on the four non-leaves.py paths, fitness-to-purpose, size backstop). Not cleared — this is an iterate, not an accept.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
