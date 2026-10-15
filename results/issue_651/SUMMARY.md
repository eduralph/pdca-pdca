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

Review issue #651: correct the stale strict-levelling comment so it accurately distinguishes recovery-seed dependency acceptance from ordering at the seed splice.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded comment-only correction has a precise acceptance criterion, including the ordering distinction and continued stack refusal; no behavior change is authorized (`brief.md:12`; `brief.md:20`; `target/template/src/pdca_harness/waves.py:95`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing the patch independently reproduced both the false “adoption never relaxes it” claim and stale line citation; this is textual reproduction, not a failing runtime test (`review-source.log:5`; `review-source.log:6`; `target/template/src/pdca_harness/waves.py:95`). |
| C3 Change | PASS | The entire diff stays within the authorized comment block, removes the contradiction, and preserves acceptance-versus-ordering and stack-refusal distinctions (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`; `review-source.log:19`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether source comparison suffices for this comment-only correction — the verifier explicitly reports no test and exits 77; independent restoration confirms corrected text but cannot establish runtime red→green (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `review-source.log:21`). |
| C5 Causal adequacy | PASS | The misleading explanation itself is corrected; dependency acceptance, absent initial ordering, and cycle holding agree with the actual code, with no added capability probe or runtime guard (`target/template/src/pdca_harness/waves.py:95`; `target/template/src/pdca_harness/waves.py:197`; `target/template/src/pdca_harness/waves.py:321`; `target/template/src/pdca_harness/flow.py:2177`). |
| T1 Structure | PASS | No executable structure changes: pre/post AST and non-comment tokens are identical, and the restored target diff exactly matches the supplied patch (`review-source.log:17`; `review-source.log:18`; `review-source.log:20`). |
| T2 Shape | PASS | Independent docs lint and rendering/link audit pass for 22 pages; the symbolic docstring citation resolves correctly and the frozen host-parity log agrees (`review-docs-lint.log:1`; `review-docs-render.log:2`; `target/template/src/pdca_harness/waves.py:278`; `gate-logs/host-ci-docs.log:14`). |
| T3 Runtime | PASS | Independent offline run passes 2,423 tests with two skips; frozen evidence also shows 24 root tests passing, although this reviewer interpreter lacks importable Copier (`review-driver-suite.log:1814`; `review-driver-suite.log:1816`; `gate-logs/T3-suite.log:54`; `gate-logs/T3-suite.log:56`; `review-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the frozen row is deferred and the substantive audit must rerun at publish (`gate-logs/T4-contribution.log:8`; `gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the recorded prior-art search by affected file path adequately covers merged and closed/rejected work — the brief enumerates both, but this synthetic one-commit target has no remotes or underlying history to independently settle that provenance (`brief.md:25`; `review-source.log:3`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the revised explanation is sufficiently clear for maintainers — it must communicate that an offered dependency is initially resolvable without ordering, then ordered or held at the seed splice (`target/template/src/pdca_harness/flow.py:2158`; `target/template/src/pdca_harness/flow.py:2163`; `target/template/src/pdca_harness/waves.py:95`). |

Independent evidence and limits:

- The disposable target identifies its base as `41210bcd18e0b6d1b77fd5fe6e29c2bbebb6fa57`, matching the brief. I stashed and restored the supplied patch, confirmed the textual symptom before and its removal after, checked Python AST/token equivalence, and ran `git diff --check`. The target remains patched exactly as supplied. No stale-target caveat applies.
- From `target/template`, `TMPDIR=/tmp/pdca-review-7vboqc5w PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests` exited 0. Existing coverage includes dependency ordering, merged dependencies, stack refusal, and cycles through offered children (`target/template/tests/test_flow_adopt_recovery.py:769`, `:900`, `:918`, `:948`). These tests exercise existing behavior; they do not make a comment edit runtime-falsifiable.
- The root-suite rerun exited 77 because Copier is not importable by `/usr/bin/python3` (`review-root-suite.log:6`). This is a reviewer-host limitation, not a patch defect or an undisclosed dependency of this fix: frozen T3 output explicitly records the render/update cases executing successfully (`gate-logs/T3-suite.log:37`; `gate-logs/T3-suite.log:54`). T3's root-suite conclusion rests on that captured output, not on the local skipped cases.
- Instance-specific C4/C5 wrappers are outside this target; their frozen logs were read. C4 is unverifiable because no test ships, and C5's scanner reports nothing to assert because no test file was added (`gate-logs/C4-verify.log:10`; `gate-logs/C5-prod-path.log:10`). C5's judgment above instead rests on inspected production code. The comment-only C4 decision is human-owned, not an implementation defect to route back to Do; adding a token test would contradict `brief.md:13`.
- For the human source comparison, from `target` run `sed -n '2141,2179p' template/src/pdca_harness/flow.py`, then `sed -n '74,109p;172,198p;275,325p' template/src/pdca_harness/waves.py`. Confirm acceptance without an initial graph edge, ordering at the recovery splice, continued stack refusal, and holding cycles once children join. No GUI verification is required. The only supplied integration document is an uninstantiated template, so it supplies no additional concrete human-only requirements.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 651 (reword-stale-strict-levelling-comment)

The diff is clean on both lenses: no correctness bug and no reuse/simplification finding. No NEEDS-HUMAN items from this lens.

- Comment-only change. Every added and removed line in `patch.diff` is a `#` line in `template/src/pdca_harness/flow.py` (`flow.py:2141-2145`, `flow.py:2158-2167`), and no other file changes. T3 passes (`gate-logs/T3-suite.log`: root suite OK, driver suite OK), so the file still parses.
- The claims in the new text match the code:
  - An offered `Depends on` / `Depends on (merged)` edge is skipped without adding a graph edge, and a `Stacks on` edge to an offered child still falls through to the refusal. See `template/src/pdca_harness/waves.py:95-96` (`if dn in offered and dep not in stacks: continue`) and `waves.py:102-109`.
  - `offered` comes from `_offered_by_seeds` and is passed into `compute_waves`; the child is spliced in later at `k=-1`. See `flow.py:2168-2170` and `flow.py:2176-2178`.
  - "A loop through the child is not seen here … it holds such a loop instead of raising" matches `template/tests/test_flow_adopt_recovery.py:948-972`.
  - The cited test `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it` exists at `test_flow_adopt_recovery.py:769`.
- The stale `waves.py:243-246` line reference was dropped rather than renumbered (`flow.py:2143-2144`). The brief allows a symbol reference with no line number, and the quoted text is still at `waves.py:278-279`. Dropping the number avoids the same drift happening again.
- Minor wording point, no action needed: the first paragraph (`flow.py:2141-2145`) says the strict check "raises on a cycle", then names only the edge as the one relaxation. A cycle through an offered child also goes unraised as a result. That is stated 15 lines later (`flow.py:2160-2163`), and the first paragraph points the reader there, so the block does not contradict itself.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C4 Verification (red→green) — Decide whether source comparison suffices for this comment-only correction — the verifier explicitly reports no test and exits 77; independent restoration confirms corrected text but cannot establish runtime red→green (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `review-source.log:21`).
- [x] T5 Judgment — Confirm the recorded prior-art search by affected file path adequately covers merged and closed/rejected work — the brief enumerates both, but this synthetic one-commit target has no remotes or underlying history to independently settle that provenance (`brief.md:25`; `review-source.log:3`).
- [x] Validation — fitness-to-purpose — Decide whether the revised explanation is sufficiently clear for maintainers — it must communicate that an offered dependency is initially resolvable without ordering, then ordered or held at the seed splice (`target/template/src/pdca_harness/flow.py:2158`; `target/template/src/pdca_harness/flow.py:2163`; `target/template/src/pdca_harness/waves.py:95`).
- [x] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — patch ships no test (changed: template/src/pdca_harness/flow.py)
- [x] **The success criterion could lose a fact the current comment gets right.** The brief's criterion asks the new text to say an offered `Depends on` edge "is accepted". The code is more specific: an offered edge "is resolvable and adds NO edge here — the child joins the schedule only at the seed splice, which re-levels with it in place, so that is where the edge orders anything" (`waves.py:76-79`; already reflected at `flow.py:2158-2159`). Scope lets Do rewrite the 2157-2159 paragraph too. A rewrite that keeps only "accepted" would suggest `compute_waves` orders the edge, which is a new inaccuracy. Suggested fix: add a clause to the criterion that the reworded block must still say the offered edge adds no edge in `compute_waves` and is ordered by the `k=-1` seed splice.
- [x] **The Falsifiability citation for the gate cannot be checked in the target repo.** The brief cites `engine/scripts/run-verify.sh` and "the `TESTS`/`PROD` classification and the 'patch ships no test' exit". No `engine/scripts/` exists in the target tree. The only `run-verify.sh` in `eduralph/pdca-harness` is `template/engine/scripts/run-verify.sh`, an unimplemented stub that `exit 1`s (`:91-94`). Its header only describes the "nothing ran → 77" rule (`:61-78`); it contains no TESTS/PROD classifier. If the gating C4 script is the operator's (pdca-pdca) copy, the brief should say so. Otherwise a reviewer cannot confirm the claim that exit 77 routes to §6 instead of failing. If C4 actually exits 1 on this bundle, the run hits a hard gate fail rather than the expected §6 route.
- [x] **Minor line-number drift in the brief.** The brief says the docstring text is at `waves.py:277-279`. Line 277 is the docstring's opening sentence ("Split ``bundles`` into …"); the quoted phrase is at `:278-279`. Either range is fine for Do to cite, and the brief already allows a symbol reference with no line number. Raised only because the brief requires every cited `path:line` to be exact.
- [x] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [x] T5 Judgment — Accept or independently confirm the recorded prior-art conclusion for the affected flow.py path — the brief names merged history and closed-unmerged PRs, but this artifact-only sandbox contains one synthetic base commit and no remote, preventing independent historical confirmation (`brief.md:25`; `target/template/src/pdca_harness/flow.py:2141`).
- [x] T5 Judgment — Decide whether to accept the recorded path-based prior-art clearance — the brief lists merged and closed-unmerged work for flow.py, but the supplied target has only one snapshot commit and no remotes, so that history cannot be independently corroborated here (`brief.md:25`; `review-source.log:8`).
- [x] T5 Judgment — Confirm the recorded prior-art disposition for `template/src/pdca_harness/flow.py` against merged history and closed/rejected PRs — the brief lists both searches, but this single-commit snapshot has no remote or captured PR evidence to independently settle them (`brief.md:25`; `review-source.log:13`; `review-source.log:14`).

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
- By / date: Eduard Ralph / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 3 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
