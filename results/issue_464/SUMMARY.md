# Result — issue 464 / wave-mode-none

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: decomposed instead of built as one cycle: the slice was judged to be more
  than one shippable outcome. The seams are set out in `split-proposal.md`; the
  original defect and scope are in `iteration-v4/brief.md`.
- Success criterion: the slice is decomposed, not built here — the child bundles
  issue_842, issue_843, issue_844 each carry their own brief, and together they cover
  the goal of `iteration-v4/brief.md`. No patch lands in this bundle; each child is verified
  by its own cycle.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: decomposition only: no patch, test or gate run belongs to this bundle. / out
  of scope: building any part of the original slice here — the child bundles
  carry that work.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: split
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — N/A — close disposition (no patch to verify)
- C3 Change: none — patch.diff
- C4 Verification (red→green): none — N/A — close disposition (no patch to verify)
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — N/A — close disposition (no patch to verify)
- T2 Shape: none — N/A — close disposition (no patch to verify)
- T3 Runtime: none — N/A — close disposition (no patch to verify)
- T4 Contribution: none — N/A — close disposition (no patch to verify)
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

# Advisory review — SKIPPED (close disposition)

The reviewer leaf was skipped: this bundle's Plan concluded a close / no-fix disposition (split), so there is no patch to review.

- NEEDS-HUMAN — Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Confirm the close disposition 'split' (no patch was built). Override to a fix path (iterate-to-Do) if the close is wrong.
- [x] T5 Judgment — Confirm that config-value validation belongs in this feature and complete the affected-path merged/closed/rejected-work prior-art decision—this target exposes only one synthetic base commit, and the brief's prior-art narrative covers only part of the changed paths (brief.md:8; brief.md:20; template/src/pdca_harness/config.py:744).
- [x] **A dependency chain exits 1 on every run except the last.** flow.py:804-806 and flow.py:928 (`… and not unmet`): with A→B→C in one `"none"` batch, B is held as `"unmerged"`, but C is "skipped — prerequisite(s) not ready (11)" with no hold of its own. So cli.py:755-757 returns **1** (probe: `holds={'11':'unmerged'}`, rc=1). This goes against the brief's Goal line: "A bundle whose prerequisite … has not merged into the bundle's own target base is **held** with a one-line reason and the way out". C's prerequisite has not merged, yet C is skipped. The builder documented this choice (docs/07-crosscutting.md, "a bundle that depends on a held one is skipped as not ready, so that run exits 1"), and it follows the #738 `"base"` precedent. But in `"none"`, chains are the normal case, not an error. A CI job reading the exit code would see "failed" on every run of a depth-3+ batch until the last two. Someone needs to decide whether C should be held too, so the run exits 3.
- [x] **A dependent on a different base can never be built in `"none"`.** flow.py:810 checks `merged_into(cfg, dep, repo, base)` against the dependent's base, and merged.py:109-116 rejects a merge into any other base. Concrete case: A targets `org/repo @ main`; B targets `org/repo @ release` and `Depends on: A`. After A's PR merges into main, the re-run still holds B, logging "merged, but into org/repo @ main; treating as not merged into org/repo @ release" and telling the user to "merge their PR into release". That is impossible, because A's PR targets main. The same input in `"stack"` builds B (rc 0). The brief does say "the bundle's own target base", so the code follows the brief. But this outcome (held forever, with advice that cannot be followed) is probably not what the brief meant. A cross-repo prerequisite gets the same dead end. A human should decide: accept a merge into the prerequisite's own base, refuse such a batch up front, or at least change the message.
- [x] docs/07-crosscutting.md:931-932 and flow.py:928 — in a three-bundle chain A→B→C under `"none"`, the first run builds A, holds B (`"unmerged"`) and skips C as "not ready" because B is not COMPLETE. C gets no hold, so `_results_rc` returns **1**, a failure, on a run where nothing went wrong and every step is waiting on a human merge. The docs state this on purpose, but it means any `"none"` batch with a chain deeper than one edge always reads as failed to CI. One option is to also add C to `waiting` when every unmet prerequisite is itself in `waiting`. This is a scope and exit-code decision.
- [x] **Load-time validation is a separate change.** Criterion (c) (fall back with a note on an unknown `wave_mode`, like `merge_requires` at config.py:738-742) is not in the issue. It also changes what an instance with a typo sees, which the "out of scope: any change to `stack`/`merge` behaviour" line half-contradicts. The change is small and goes naturally with adding a value, so this is not a blocker. The human should still confirm it belongs in this bundle and was not slipped in.
- [x] T5 Judgment — Approve the additional invalid-value fallback scope and complete affected-path merged/closed-work prior-art clearance — the brief explicitly reserves scope approval, while its prior-art record covers only some affected files and this supplied target exposes one synthetic commit with no remotes (brief.md:8; brief.md:20; template/src/pdca_harness/config.py:744).
- [x] **A prerequisite that targets a different base or repo, or one published with `Onto branch`, can never satisfy the hold, and the run reports a normal hold (rc 3) forever.** See `flow.py:824-826` together with `merged.py:109-114`. Case: 10 targets `org/repo @ dev`, 11 targets `@ main`, and 11 has `Depends on: 10`. Run 1 gives `holds={'11': 'unmerged'}`, rc=3, and "merge their PR into main", but 10's PR targets `dev`. After it merges into `dev`, the re-run logs "merged, but into org/repo @ dev; treating as not merged into org/repo @ main" and is held again with rc=3, with no end. `"stack"` builds both, rc=0. A mode `"stacked"` (`Onto branch`) prerequisite is refused the same way at `merged.py:109`. The brief asks for exactly this rule ("merged into the bundle's own target base"), so this is a scope decision. Either such edges are refused up front in `"none"`, or the hold line says they can never be met, not "merge their PR into main".
- [x] **A chain of three exits 1 on an ordinary `"none"` run, which defeats the point of rc 3.** Case: 10 ← 11 ← 12 (`Depends on`). Run 1 gives `holds={'11': 'unmerged'}` and "issue_12 skipped — prerequisite(s) not ready (11)", rc=**1**. The cause is `flow.py:810-812`: 11 is PLANNED, so for 12 it is `unmet`, and `flow.py:950` adds only bundles with no `unmet` to `waiting`. Then `cli.py:757-758` fails the run. In `"none"` a chain is the expected shape, and every run except the last two exits 1. A CI script cannot tell "waiting for a merge" from a real failure, which is what rc 3 is for. The docs admit it (`docs/07-crosscutting.md:931-932`). But `template/pdca.toml.jinja:132` says "(`flow` exits 3)" with no exception. Decide whether a bundle blocked only by an `"unmerged"` hold should itself count as `"unmerged"`. If not, at least fix the jinja comment.
- [x] C1 Spec — Confirm that unknown-value validation belongs in this enhancement — the brief explicitly reserves approval of this extra scope for sign-off; `brief.md:8`, `template/src/pdca_harness/config.py:744`.
- [x] **A prerequisite whose PR can't reach the dependent's base holds the dependent for good, and the message gives a way out that can't work.** `flow.py:876` holds whenever `merged.merged_into` is false, and `merged.py:109-110` returns false for a different repo, a different base or an `Onto branch` record (`mode == "stacked"`). So these in-batch cases, which all build in stack mode, can never be released: B targeting `org/b` and depending on a PR in `org/a`; B on `main` and its prerequisite on `dev`; a prerequisite published with `Onto branch`. Each run still exits 3 and prints "merge their PR into main" (`flow.py:950`), even when the PR already reads MERGED. `test_a_merge_into_another_base_does_not_release_the_dependent` asserts that hold with the same advice. The brief asks for "merged into the bundle's own target base", so the hold itself follows the spec. The human needs to decide whether these edges should stay held, be refused up front, or count as ready like a prerequisite with no target. Whatever the decision, the message needs fixing: when the PR has already merged elsewhere, it should say that no merge into this base can release the bundle.

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
- By / date: Eduard Ralph / 2026-10-30

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
