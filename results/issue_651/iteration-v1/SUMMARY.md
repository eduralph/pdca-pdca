# Result — issue 651 / reword-stale-strict-levelling-comment

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The comment at `template/src/pdca_harness/flow.py:2141-2144` (inside `_drive_and_act`) says the named batch is levelled strictly "exactly as before" and that "adoption never relaxes it". Since #590 (`29a7943`) that is false: `_offered_by_seeds` (`flow.py:2160`) collects the in-flight children a recovery seed offers, and `waves.compute_waves(cfg, bundles, offered=offered)` (`flow.py:2162`) passes them to `waves.check_dep_graph`, which then accepts a `Depends on` / `Depends on (merged)` edge to such a child instead of raising (`template/src/pdca_harness/waves.py:74-79`, `:95-96`). So adoption (by a recovery seed) does relax the strict check for those edges. A later paragraph of the same comment block (`flow.py:2157-2159`) already describes the #590 behaviour, so the block now contradicts itself. The same sentence also cites `waves.partition_schedulable`'s docstring as `waves.py:243-246`; that text ("right for an explicit `flow <ids>`") is now at `waves.py:278-279` (inside the docstring that opens at `:277`).
- Success criterion: With the patch, the comment block above `offered = _offered_by_seeds(...)` in `flow._drive_and_act` (`flow.py:2141-2162` today) makes no claim that the named batch is levelled "exactly as before" or that adoption "never relaxes" the strict check. It states that the named batch is still levelled strictly (`compute_waves` raises on a cycle or an unresolvable dependency) except for one relaxation since #590: a `Depends on` / `Depends on (merged)` edge to a child a recovery seed offers is resolvable instead of raising, but adds NO edge in `compute_waves`; the child joins the schedule only at the recovery seed's splice, which re-levels with it in place, so that splice is what orders the edge. A `Stacks on` edge to one still refuses (`waves.py:74-80`). The reworded block must keep both facts (resolvable here, ordered at the seed splice); saying only that the edge is "accepted" is not enough, because it would suggest `compute_waves` orders it. Any line reference it keeps points at the text it names on the patched tree (the `partition_schedulable` docstring text is `waves.py:278-279` on `41210bc`; a symbol reference with no line number is also fine). The patch changes comment lines only: `git diff -w` of the patch shows no change outside `#` comment lines in `flow.py`, and no other file changes. The offline driver suite still passes (`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`, the advisory T3 row).
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Reword the comment block at `flow.py:2141-2144` (and, if needed so the block reads as one consistent statement, the #590 paragraph at `flow.py:2157-2159`) so it describes the behaviour after #590, and correct its stale `waves.py:243-246` reference. / out of scope: any code change in `flow.py` or `waves.py`; other comments or docstrings elsewhere that may also mention strict levelling (if Do finds another stale one, note it in `build-notes.md`, do not fix it here); the docs under `docs/`.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: unverifiable — patch ships no test (changed: template/src/pdca_harness/flow.py)
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

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

Review issue 651: correct the strict-levelling comment to explain recovery-seed dependency resolution and ordering, without changing executable code.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded comment correction has a concrete semantic criterion: distinguish accepting an offered dependency from ordering it at the seed splice; the implementation supports that distinction (`brief.md:12`; `target/template/src/pdca_harness/waves.py:95`; `target/template/src/pdca_harness/flow.py:1716`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing the patch reproduced the contradictory “adoption never relaxes it” claim and obsolete reference in the pre-fix source; this is a textual reproduction, not a failing runtime test (`patch.diff:9`; pre-fix `target/template/src/pdca_harness/flow.py:2141`). |
| C3 Change | PASS | The entire diff is confined to comments in the specified block, preserves executable AST identity, and restores the distinction required for readers to understand scheduling (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Accept source comparison as sufficient verification for this comment-only correction — the gate explicitly exits 77 because no test ships, so no runtime red→green is established (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `target/template/src/pdca_harness/flow.py:2158`). |
| C5 Causal adequacy | PASS | The misleading statement itself is corrected: offered non-stack dependencies bypass refusal without adding an initial ordering edge; the splice re-levels with children present. No capability probe or runtime guard is introduced (`target/template/src/pdca_harness/waves.py:95`; `target/template/src/pdca_harness/waves.py:197`; `target/template/src/pdca_harness/flow.py:1716`). |
| T1 Structure | PASS | The one-file comment-only diff and identical parsed AST leave scheduling structure and interfaces intact (`target/template/src/pdca_harness/flow.py:2164`; `target/template/src/pdca_harness/flow.py:2173`). |
| T2 Shape | PASS | Independent whitespace check, docs lint, and 22-page render/link audit pass; the symbol reference resolves to the intended docstring, avoiding the stale line number (`target/template/src/pdca_harness/waves.py:278`; `gate-logs/T2-docs.log:15`; `gate-logs/host-ci-docs.log:14`). |
| T3 Runtime | PASS | Independent patched-tree run passes all 2,423 offline tests with two skips; frozen evidence also records 24 passing root-suite tests, whose copier dependency is unavailable in this reviewer interpreter (`review-suite.log:1814`; `gate-logs/T3-suite.log:54`; `gate-logs/T3-suite.log:56`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the logged deferred result requires the substantive contribution audit at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Accept or independently confirm the recorded prior-art conclusion for the affected flow.py path — the brief names merged history and closed-unmerged PRs, but this artifact-only sandbox contains one synthetic base commit and no remote, preventing independent historical confirmation (`brief.md:25`; `target/template/src/pdca_harness/flow.py:2141`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the revised explanation is clear enough for maintainers to distinguish dependency resolvability from scheduling order — code agreement and passing suites cannot settle reader comprehension (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`). |

Independent checks reproduced the original wording with `git stash`, then restored the patch with `git stash pop` and verified the restored file byte-for-byte. All 11 added and seven removed lines are comments in the intended file; pre/post ASTs are identical and `git diff --check` passes. The target matches the brief's base, so no target-state caveat applies. No implementation defect was found.

The offline suite was rerun using `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`, with temporary files confined to this review directory. It completed in 56.978 seconds. The existing recovery tests cover plain dependencies, merged dependencies, and refused stack dependencies (`target/template/tests/test_flow_adopt_recovery.py:769`, `:900`, `:918`). These tests confirm existing behavior; they do not test comment quality.

All six frozen gate logs were inspected. Instance-only wrappers were adjudicated from their captured outputs rather than substituted with the target's template stub. The production-path scanner reports no new test to inspect (`gate-logs/C5-prod-path.log:10`). The root suite was not independently rerun because copier is not importable here; its frozen log shows actual render/update cases executed successfully (`gate-logs/T3-suite.log:38`). This is a reviewer-environment limitation, not an undischarged build dependency or patch failure. The template integration document enumerates no additional project-specific human checks (`target/template/docs/INTEGRATION.md.jinja:80`).

For the human wording check, run `sed -n '2141,2175p' "$PDCA_TARGET/template/src/pdca_harness/flow.py"` and compare with `sed -n '74,104p;184,198p;275,281p' "$PDCA_TARGET/template/src/pdca_harness/waves.py"`. Confirm that both dependency forms are resolvable before adoption, no edge to an absent child is added then, the recovery splice orders the dependency, and the offered-child exception does not admit `Stacks on`.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 651 (reword-stale-strict-levelling-comment)

I found no problems with either lens (correctness, and reuse/simplification). The patch only changes `#` comment lines in one file, `template/src/pdca_harness/flow.py`. No code changed, so the patch cannot add a runtime bug. The T3 suite log shows `Ran 2423 tests ... OK (skipped=2)`, so the file still parses.

I checked the new wording against the code in the patched tree:

- `template/src/pdca_harness/flow.py:2141-2145`: the "exactly as before" and "adoption never relaxes it" claims are gone. The block now says there is "exactly one relaxation" since #590. That is accurate: `template/src/pdca_harness/waves.py:95-96` (`if dn in offered and dep not in stacks: continue`) is the only path that lets a dependency through without raising.
- The stale `waves.py:243-246` line number was replaced with a symbol-only reference. The quoted text "right for an explicit `flow <ids>`" does exist in the `partition_schedulable` docstring (`template/src/pdca_harness/waves.py:277-279`), so nothing is left that can go stale again.
- `template/src/pdca_harness/flow.py:2158-2163`: the comment keeps both facts the brief requires. The offered `Depends on` / `Depends on (merged)` edge is resolvable but "adds NO edge in `compute_waves`", and the `k=-1` splice is what orders it. This matches the `check_dep_graph` docstring at `template/src/pdca_harness/waves.py:74-80`. `compute_waves` passes `offered` straight through (`template/src/pdca_harness/waves.py:184`), and the splice call follows at `template/src/pdca_harness/flow.py:2173`.
- The `Stacks on` claim is correct. An offered child that is a `Stacks on` target fails the `dep not in stacks` test (`waves.py:95`), then gets checked with `cfg.bundle(dep)` for COMPLETE (`waves.py:102-103`). An in-flight child is not COMPLETE, so it raises.
- Minor, no action needed: the `k=-1` splice is now explained in two places, the reworded paragraph at `flow.py:2158-2163` and the existing recovery comment at `flow.py:2166-2170`. They agree, and the brief allowed rewording the #590 paragraph, so this is fine.

I saw no other stale strict-levelling text near the edit. The `_offered_by_seeds` docstring at `template/src/pdca_harness/flow.py:2003-2007` already describes the #590 behavior correctly.

C4 reports `unverifiable` (the patch ships no test). The brief expects that for a comment-only change, and the harness already sends that row to §6 for a human to read. I am not filing a separate finding for it.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Accept source comparison as sufficient verification for this comment-only correction — the gate explicitly exits 77 because no test ships, so no runtime red→green is established (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `target/template/src/pdca_harness/flow.py:2158`).
- [ ] T5 Judgment — Accept or independently confirm the recorded prior-art conclusion for the affected flow.py path — the brief names merged history and closed-unmerged PRs, but this artifact-only sandbox contains one synthetic base commit and no remote, preventing independent historical confirmation (`brief.md:25`; `target/template/src/pdca_harness/flow.py:2141`).
- [ ] Validation — fitness-to-purpose — Decide whether the revised explanation is clear enough for maintainers to distinguish dependency resolvability from scheduling order — code agreement and passing suites cannot settle reader comprehension (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`).
- [ ] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — patch ships no test (changed: template/src/pdca_harness/flow.py)
- [ ] **The success criterion could lose a fact the current comment gets right.** The brief's criterion asks the new text to say an offered `Depends on` edge "is accepted". The code is more specific: an offered edge "is resolvable and adds NO edge here — the child joins the schedule only at the seed splice, which re-levels with it in place, so that is where the edge orders anything" (`waves.py:76-79`; already reflected at `flow.py:2158-2159`). Scope lets Do rewrite the 2157-2159 paragraph too. A rewrite that keeps only "accepted" would suggest `compute_waves` orders the edge, which is a new inaccuracy. Suggested fix: add a clause to the criterion that the reworded block must still say the offered edge adds no edge in `compute_waves` and is ordered by the `k=-1` seed splice.
- [ ] **The Falsifiability citation for the gate cannot be checked in the target repo.** The brief cites `engine/scripts/run-verify.sh` and "the `TESTS`/`PROD` classification and the 'patch ships no test' exit". No `engine/scripts/` exists in the target tree. The only `run-verify.sh` in `eduralph/pdca-harness` is `template/engine/scripts/run-verify.sh`, an unimplemented stub that `exit 1`s (`:91-94`). Its header only describes the "nothing ran → 77" rule (`:61-78`); it contains no TESTS/PROD classifier. If the gating C4 script is the operator's (pdca-pdca) copy, the brief should say so. Otherwise a reviewer cannot confirm the claim that exit 77 routes to §6 instead of failing. If C4 actually exits 1 on this bundle, the run hits a hard gate fail rather than the expected §6 route.
- [ ] **Minor line-number drift in the brief.** The brief says the docstring text is at `waves.py:277-279`. Line 277 is the docstring's opening sentence ("Split ``bundles`` into …"); the quoted phrase is at `:278-279`. Either range is fine for Do to cite, and the brief already allows a symbol reference with no line number. Raised only because the brief requires every cited `path:line` to be exact.

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
- Iteration delta (if iterating): Auto-iterate (round 1): rebuilding for the implementation-level findings — C4 Verification (red→green) — Accept source comparison as sufficient verification for this comment-only correction — the gate explicitly exits 77 because no test ships, so no runtime red→green is established (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `target/template/src/pdca_harness/flow.py:2158`).. Deferred, not addressed here: 4 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 3 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
