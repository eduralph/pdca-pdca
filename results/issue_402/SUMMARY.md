# Result — issue 402 / gate-evidence-not-leaked-stdout

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two halves of one symptom — a **green** gate whose frozen record reads like a
  failure path.
  **(1) The leak.** `template/tests/test_split.py` drives production CLI code that prints to
  stdout — `leaves.do_split` at `template/src/pdca_harness/leaves.py:1155`
  (`print(f"{d / split.PROPOSAL}")`) and `cli._split` at
  `template/src/pdca_harness/cli.py:786-787` (`print(child)`) — without capturing it on every
  path (:181, :216, :586-587; the file's own convention is `redirect_stdout(io.StringIO())`,
  applied at :856, :888, :939, :1133, :1212, …). `unittest` writes its report to **stderr**, so
  under a pipe the block-buffered stdout flushes last and the leaked scratch paths become the
  final lines of the merged capture. Reproduced verbatim on `origin/main` @ `9fb4860`:
  `Ran 96 tests … OK` followed by three `/tmp/tmp…/results/issue_500/split-proposal.md` lines
  and two `/tmp/tmp…/results/issue_60{1,2}` lines.
  **(2) The rule.** `_classify` takes `output.strip().splitlines()[-1:]` as the evidence for
  pass **and** fail (`template/src/pdca_harness/gates.py:619-621`), so whatever flushed last is
  filed as the gate's verdict. A T3 wrapper exiting **0** was therefore recorded as
  `path_line = "/tmp/…/results/issue_500/split-proposal.md"` — a scratch path nobody can
  inspect, escalated to §6 NEEDS-HUMAN in 12 of 19 frozen pdca-pdca cycles (frozen example:
  `results/issue_387/check-gates.json`, T3 row). The premise originally filed here — that the
  synthetic `issue_500` fixture *flakes* — was **corrected in the thread**: the fixture has
  never failed, and the historical T3 reds were genuine and are already fixed by #417/#418.
  What survives is the misleading evidence string on a green row.
  **Measured at Plan (2026-08-02, clean `origin/main` worktree), and it changes the weighting
  of the two halves:** the gate reads ONE merged stream (`stdout=PIPE, stderr=STDOUT`,
  `template/src/pdca_harness/progress.py:112`), and the whole offline suite leaks **506** stdout
  lines — the `issue_500` paths are only the most visible; `git -C /tmp/example-repo add --all`,
  publish dry-run plans and rendered gate matrices leak from other modules too. Under a merged
  pipe the last line of `python3 -m unittest discover -s tests` is today
  `/tmp/…/results/issue_500/split-proposal.md`; with half (1) alone it would simply become a
  *different* leaked line. So half (2) is the load-bearing half — half (1) removes the specific
  noise this issue names and the fixture the reviewers kept misreading, but it cannot restore
  the invariant on its own.
- Success criterion: Both hold with the patch applied, and both fail without it:
  1. `cd template && PYTHONPATH=src python3 -m unittest tests.test_split` writes **nothing** to
     stdout — that module's complete output is the unittest report on stderr. (Scoped to this
     module by design: the wider suite-hygiene sweep is out of scope, see Scope.)
  2. A gate that declares its verdict summary and whose command output then continues with
     further, unrelated child-process stdout has **that declared summary** recorded as the
     row's `path_line` — not the trailing line. A gate that declares nothing keeps a defined,
     documented evidence rule, with the full basis still reachable through `row["log"]`
     (`gates.py:529-545`).
  Demonstrable by C4-verify alone: the named test modules are red with the production hunk
  reverted and green with it applied.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: one logical change with two halves — stop the suite from leaking the driven code's
  stdout on the `test_split.py` paths that do not capture it, and make the recorded gate
  evidence be the gate's own verdict rather than whatever line happened to flush last. If the
  fix introduces a convention gate authors must write to, state it where the gate contract is
  written (`template/PCDA/quality-cycle/04-validation-tooling.md` §Gate result vocabulary) so a
  wrapper can be written against it. The exact discrimination rule is Do's to choose, aligned
  with the declaration rule 428 settles — do not invent a second, different notion of "the gate
  said this".
  / **out of scope:** the `PDCA-UNVERIFIABLE` marker rule (issue 428, this bundle's base — do
  not re-litigate it); the T4 default-open row status (issue 401); the transient-`/tmp`
  inspectability idea from the original filing (`gate-logs/` already persists the full output,
  #415 — nothing further is needed); quarantining or "de-flaking" the `issue_500` fixture (the
  corrected diagnosis: it does not flake, and must not be quarantined); the pdca-pdca-side
  follow-up to its `run-suite.sh` stopgap; and the **suite-wide** stdout-hygiene sweep — the
  other ~500 leaked lines measured across the offline suite are the same class but a separate,
  much larger slice, and half (2) is what makes them harmless. Do NOT start it here.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Issue 402 fixes misleading gate evidence by making gates declare their recorded summary and by stopping `tests.test_split` from leaking driven stdout.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines two linked obligations: `tests.test_split` must write no stdout, and declared gate evidence must beat trailing child output; the patch covers both surfaces at `template/src/pdca_harness/gates.py:29` and `template/tests/test_suite_output_hygiene.py:37`. |
| C2 Reproduction (red pre-fix) | PASS | Because `git stash` could not write the read-only worktree index, I reverse-applied `patch.diff`: the named test run went red and printed the leaked `issue_500/601/602` stdout paths, matching the failure guarded by `template/tests/test_suite_output_hygiene.py:47`. |
| C3 Change | PASS | The human decision is whether the marker convention is an acceptable contract change; it is documented and implemented consistently at `template/PCDA/quality-cycle/04-validation-tooling.md:83` and `template/src/pdca_harness/gates.py:74`. |
| C4 Verification (red→green) | PASS | Reverse-patch red and restored-patch green were reproduced with `PYTHONPATH=src python3 -m unittest tests.test_gate_logs tests.test_suite_output_hygiene tests.test_split`; the binding assertions are at `template/tests/test_gate_logs.py:256` and `template/tests/test_suite_output_hygiene.py:37`. |
| C5 Causal adequacy | PASS | The fix changes the evidence-selection cause rather than adding a capability probe or guard; declared evidence wins, fallback remains defined, and exit-code verdicts are preserved at `template/src/pdca_harness/gates.py:698`. |
| T1 Structure | PASS | The change stays in the named gate contract, classifier, and split-test hygiene slice; the subprocess regression is separated to avoid recursive self-invocation at `template/tests/test_suite_output_hygiene.py:14`. |
| T2 Shape | NEEDS-HUMAN | The shape decision remains provisional because the frozen T2 runner `./engine/scripts/run-docs-check.sh` is not present in the target checkout; I could only run `git diff --check`, which passed, while the docs contract itself is at `template/PCDA/quality-cycle/04-validation-tooling.md:83`. |
| T3 Runtime | NEEDS-HUMAN | The frozen T3 row reports a driver-suite failure, but `./engine/scripts/run-suite.sh` is not present to rerun; local `PYTHONPATH=src python3 -m unittest discover -s tests` passed, so the human must decide whether the unavailable driver-suite red is environmental or real. |
| T4 Contribution | NEEDS-HUMAN | The contribution gate is frozen green, but no contribcheck runner or contribution artifacts are present in this review sandbox to rerun; the human must decide whether the unpublished contribution metadata satisfies the tracker/review convention. |
| T5 Judgment | PASS | Prior art by affected paths found merged related work (#415/#400/#427) and no competing `PDCA-EVIDENCE` implementation; the current classifier contract is the one being extended at `template/src/pdca_harness/gates.py:615`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Always human: decide whether `PDCA-EVIDENCE:` is the right operator-facing convention and whether the observed red→green plus local suite pass is enough fitness evidence for issue 402. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — The shape decision remains provisional because the frozen T2 runner `./engine/scripts/run-docs-check.sh` is not present in the target checkout; I could only run `git diff --check`, which passed, while the docs contract itself is at `template/PCDA/quality-cycle/04-validation-tooling.md:83`.
- [x] T3 Runtime — The frozen T3 row reports a driver-suite failure, but `./engine/scripts/run-suite.sh` is not present to rerun; local `PYTHONPATH=src python3 -m unittest discover -s tests` passed, so the human must decide whether the unavailable driver-suite red is environmental or real.
- [x] T4 Contribution — The contribution gate is frozen green, but no contribcheck runner or contribution artifacts are present in this review sandbox to rerun; the human must decide whether the unpublished contribution metadata satisfies the tracker/review convention.
- [x] Validation — fitness-to-purpose — Always human: decide whether `PDCA-EVIDENCE:` is the right operator-facing convention and whether the observed red→green plus local suite pass is enough fitness evidence for issue 402.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-02

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- In principle every 5/5/1 gate should have a script in every instance, but this is not checked: first a setup helper when creating a new downstream repo, then something that validates the form like the scripts in the doctor (surfaced here by T4 `contribcheck` — a driver subcommand with no runner script, which the reviewer read as an absent gate).
