# Result — issue 379 / headless-leaf-scratch-ownership

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: no headless leaf's role body says who owns its filesystem, so the model invents
  an answer and the answer is wrong. Verified: `template/agents/reviewer.md.jinja` (130 lines),
  `adversary.md.jinja`, `code-review.md.jinja`, `plan-reviewer.md.jinja` and `builder.md.jinja`
  contain **zero** occurrences of "scratch" / "cwd" / "working directory" / "temp dir". The
  harness meanwhile owns that lifecycle mechanically: the reviewer's cwd is a
  `tempfile.TemporaryDirectory(prefix="pdca-review-")` deleted when the leaf exits
  (`template/src/pdca_harness/leaves.py:1831`), the advisory reviewers get the identical shape
  (`:2145` `pdca-advisory-`, `:2437` `pdca-plan-advisory-`), and the builder edits the
  per-cycle worktree the harness creates and reclaims (`:1290` `worktree.ensure`, plus
  `[driver].sweep_worktrees`). Left unstated, a conscientious model creates scratch **outside**
  its cwd and then feels obliged to delete it. Observed on a live `pdca flow` Check with a
  codex `exec` reviewer: it composed one compound self-validation script ending in an
  `rm -rf` of a scratch dir it had made for itself under `/var/tmp/pdca/pdca-reviewer-<id>-*`
  (case-guarded to its own path), and codex's command policy refused the **whole** script
  before executing any of it — `rejected: rm -f style commands are not permitted. Use a safer
  approach`. Per run it is benign (nothing half-executed, the leaf continued), but it is
  systematic: codex `exec` bans rm-style commands unconditionally in this mode, so **every**
  codex reviewer cycle that self-cleans pays a wasted model round-trip — and may loop hunting a
  "safer approach" — while the invented scratch leaks into `/var/tmp` when the model gives up.
- Success criterion: every headless leaf role body whose working files the harness creates
  and disposes states that ownership, in the vendor-neutral canonical source under
  `template/agents/` (inlined for codex, wrapped for claude, so every vendor inherits it).
  Concretely, for each of the five bodies named in Scope the rendered text must say (a) which
  roots the leaf may write in — for a sandboxed reviewer/advisory leaf, its cwd; for the
  builder, `$PDCA_WORKTREE` **and** the bundle dir it is granted (it must keep writing
  `patch.diff` / the test / `build-notes.md` there, so a blanket "never write outside your cwd"
  would be wrong for it); (b) that it must not create files outside those roots; and (c) that
  cleanup is **not the leaf's to perform** — the harness disposes of them — so no rm-style
  command is ever warranted. The statement is phrased over **"the roots the harness gives
  you"**, not "your cwd", so a future harness-provided root (#422) is covered without
  rewording. `test_role_prompts.py`'s wrapper/canonical sync assertion still passes.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: state the harness's filesystem ownership in the canonical vendor-neutral role
  bodies of the headless leaves whose working files the harness creates and disposes — the
  sandboxed reviewer (`template/agents/reviewer.md.jinja`), the advisory reviewers
  (`adversary.md.jinja`, `code-review.md.jinja`) and the plan advisory
  (`plan-reviewer.md.jinja`), which share one sandbox shape, plus the builder
  (`builder.md.jinja`), whose worktree-and-granted-bundle shape differs and must be stated
  accurately rather than copied. / out of scope: **any persistent or cached scratch location**
  — do not name one, promise one, or imply one exists (#422 owns that, and pre-empting it here
  is exactly the contradiction the Ordering note avoids); any change to `leaves.py`, `sweep.py`
  or `config.py` — this bundle is prompt text plus its test, no driver code; the `sizer` and
  `splitter` bodies, whose cwd is the **bundle dir** (persistent harness state, `leaves.py:1066`
  / `:1149`), a different lifetime that would need its own statement; the interactive leaves;
  the `.claude/agents/*.md.jinja` wrappers, which are generated from the canonical bodies by
  `{% include %}` and must not be hand-edited (`test_role_prompts.py` enforces the sync); and
  re-litigating the reviewer's independent-re-verification mandate at
  `template/agents/reviewer.md.jinja:24-25`, which stays exactly as it is.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — no behavioral production change to revert (test-only or docs-only patch)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpn6dz0t0a/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Issue 379 fixes missing filesystem-ownership instructions in headless leaf role prompts so leaves do not invent external scratch directories or self-cleanup.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is concrete: all five canonical `template/agents/` bodies must state harness-given writable roots, forbid outside files, and say cleanup is harness-owned; scope excludes persistent scratch/cache claims that would pre-empt #422 (`brief.md:25`, `brief.md:78`). |
| C2 Reproduction (red pre-fix) | PASS | The pre-fix symptom is grounded: `git show HEAD` for the five affected prompt bodies has 0 matches for scratch/cwd/working-directory terms, and running the new test against those base bodies failed all 10 subtests exercising the property checks in `template/tests/test_leaf_scratch_discipline.py:87` and `template/tests/test_leaf_scratch_discipline.py:115`. |
| C3 Change | PASS | The diff is limited to the five in-scope canonical prompt bodies plus the non-vacuous property test; reviewer/advisory cwd ownership is present at `template/agents/reviewer.md.jinja:22`, and the builder's distinct worktree-plus-bundle roots are present at `template/agents/builder.md.jinja:43`. |
| C4 Verification (red→green) | NEEDS-HUMAN | Decision owed: whether the reproduced unit red-green is sufficient despite the configured C4 gate being unverifiable for prompt/test-only changes; I observed red in a `/tmp` copy seeded with base prompt bodies and green in `$PDCA_TARGET`, but `check-gates.json:33` records C4 as `unverifiable` and the local skeleton runner exits "not yet implemented" when given `PDCA_BUNDLE`. |
| C5 Causal adequacy | PASS | The patch removes the stated silence across the whole affected category rather than adding a capability probe/runtime guard: all five leaves are covered in `AGENT_ROOTS` at `template/tests/test_leaf_scratch_discipline.py:43`, and the added role text maps to the harness-owned lifecycle at `template/src/pdca_harness/leaves.py:1290`, `template/src/pdca_harness/leaves.py:1831`, `template/src/pdca_harness/leaves.py:2145`, and `template/src/pdca_harness/leaves.py:2437`. |
| T1 Structure | PASS | The ownership text sits in canonical vendor-neutral bodies outside conditionals, and the test uses posture-aware `agents/<name>.md.jinja` vs `agents/<name>.md` resolution mirroring the local pattern at `template/tests/test_remote_control_docs.py:19` and implemented at `template/tests/test_leaf_scratch_discipline.py:63`. |
| T2 Shape | NEEDS-HUMAN | Decision owed: whether to trust the driver-recorded docs/link audit pass, because `check-gates.json:60` reports `T2-docs` pass but `$PDCA_TARGET` contains no runnable `./engine/scripts/run-docs-check.sh` to independently reproduce it. |
| T3 Runtime | NEEDS-HUMAN | Decision owed: whether the recorded offline-suite failure is patch-relevant or an unrelated/environmental suite failure; `check-gates.json:69` reports `T3-suite` fail at `/tmp/tmpn6dz0t0a/results/issue_500/split-proposal.md`, but `$PDCA_TARGET` contains no runnable `./engine/scripts/run-suite.sh` for an independent rerun. |
| T4 Contribution | NEEDS-HUMAN | Decision owed: whether the contribution artifacts satisfy the opener/tracker convention, because `check-gates.json:78` records a pass but this reviewer received only `patch.diff`, `brief.md`, and `check-gates.json`, so the commit/PR artifacts needed for `contribcheck` are absent. |
| T5 Judgment | NEEDS-HUMAN | Decision owed: human prompt/process judgment for agent role prompt changes, including whether naming `/tmp` and `/var/tmp` only as forbidden self-made locations avoids implying a persistent scratch root; the brief explicitly classifies `template/agents/` prompt changes as human-only at sign-off (`brief.md:46`, `brief.md:84`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decision owed: final fitness-to-purpose for the prompt wording across vendors and future #422; I verified `cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_scratch_discipline` passes green, and the human should read the five added sections, especially `template/agents/reviewer.md.jinja:24` and `template/agents/builder.md.jinja:45`, for operational clarity. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Decision owed: whether the reproduced unit red-green is sufficient despite the configured C4 gate being unverifiable for prompt/test-only changes; I observed red in a `/tmp` copy seeded with base prompt bodies and green in `$PDCA_TARGET`, but `check-gates.json:33` records C4 as `unverifiable` and the local skeleton runner exits "not yet implemented" when given `PDCA_BUNDLE`.
- [x] T2 Shape — Decision owed: whether to trust the driver-recorded docs/link audit pass, because `check-gates.json:60` reports `T2-docs` pass but `$PDCA_TARGET` contains no runnable `./engine/scripts/run-docs-check.sh` to independently reproduce it.
- [x] T3 Runtime — Decision owed: whether the recorded offline-suite failure is patch-relevant or an unrelated/environmental suite failure; `check-gates.json:69` reports `T3-suite` fail at `/tmp/tmpn6dz0t0a/results/issue_500/split-proposal.md`, but `$PDCA_TARGET` contains no runnable `./engine/scripts/run-suite.sh` for an independent rerun.
- [x] T4 Contribution — Decision owed: whether the contribution artifacts satisfy the opener/tracker convention, because `check-gates.json:78` records a pass but this reviewer received only `patch.diff`, `brief.md`, and `check-gates.json`, so the commit/PR artifacts needed for `contribcheck` are absent.
- [x] T5 Judgment — Decision owed: human prompt/process judgment for agent role prompt changes, including whether naming `/tmp` and `/var/tmp` only as forbidden self-made locations avoids implying a persistent scratch root; the brief explicitly classifies `template/agents/` prompt changes as human-only at sign-off (`brief.md:46`, `brief.md:84`).
- [x] Validation — fitness-to-purpose — Decision owed: final fitness-to-purpose for the prompt wording across vendors and future #422; I verified `cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_scratch_discipline` passes green, and the human should read the five added sections, especially `template/agents/reviewer.md.jinja:24` and `template/agents/builder.md.jinja:45`, for operational clarity.
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — no behavioral production change to revert (test-only or docs-only patch)

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
