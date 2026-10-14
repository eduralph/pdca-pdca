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

Review issue #651: correct the stale strict-levelling comment so it accurately distinguishes offered-child dependency resolution from ordering at the recovery-seed splice.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded comment correction has explicit acceptance criteria for dependency resolution, ordering, and stack refusal, with no runtime change required (`brief.md:12`; `brief.md:20`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing the patch reproduced the false “adoption never relaxes it” claim and obsolete numeric reference; this is textual reproduction, not a failing runtime test (`review-source.log:1`; `patch.diff:9`; `target/template/src/pdca_harness/waves.py:95`). |
| C3 Change | PASS | The change meets the permitted scope: one file, only comment lines, with the two scheduling stages and stack exception explicitly distinguished (`review-source.log:2`; `target/template/src/pdca_harness/flow.py:2158`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether source comparison suffices for this comment-only correction — the frozen verifier explicitly exits 77 because no test ships; the independent stash/restore comparison confirms the textual correction but establishes no runtime red→green (`gate-logs/C4-verify.log:7`; `review-source.log:1`). |
| C5 Causal adequacy | PASS | The contradiction itself is removed, and the explanation matches graph filtering and the later splice; no capability probe or runtime guard is introduced (`target/template/src/pdca_harness/waves.py:95`; `target/template/src/pdca_harness/waves.py:197`; `target/template/src/pdca_harness/flow.py:1716`). |
| T1 Structure | PASS | Identical pre/post Python ASTs establish that the documentation correction preserves executable structure (`review-source.log:4`; `target/template/src/pdca_harness/flow.py:2141`). |
| T2 Shape | PASS | Independent whitespace validation, docs lint, and rendering with internal-link audit passed; 22 pages rendered successfully (`review-source.log:7`; `review-docs-lint.log:1`; `review-docs-render.log:3`). |
| T3 Runtime | PASS | The independent offline suite passed 2,423 tests with two skips; frozen evidence also shows 24 root tests passing, although local root coverage could not execute Copier (`review-driver.log:1814`; `gate-logs/T3-suite.log:54`; `review-root.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are absent by design during Check; their substantive audit is deferred to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Decide whether to accept the recorded path-based prior-art clearance — the brief lists merged and closed-unmerged work for flow.py, but the supplied target has only one snapshot commit and no remotes, so that history cannot be independently corroborated here (`brief.md:25`; `review-source.log:8`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm the revised explanation gives maintainers enough clarity about resolvability versus splice-time ordering — code agreement is established, but whether the wording resolves the reported confusion remains the sign-off decision (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`). |

No implementation defect found. The target is usable and the supplied patch was restored exactly after the independent stash/pop comparison. The source check confirms that every changed line is a comment and the Python AST is unchanged. The obsolete numeric citation is replaced by a symbol reference whose quoted text exists at `target/template/src/pdca_harness/waves.py:278`.

The additional statements about cycles and failed adoption are supported by the tolerant re-level at `target/template/src/pdca_harness/flow.py:1521`, the splice at `target/template/src/pdca_harness/flow.py:1716`, and existing coverage at `target/template/tests/test_flow_adopt_recovery.py:874` and `target/template/tests/test_flow_adopt_recovery.py:948`. These tests ran in the independent driver suite; they verify existing behavior, not a runtime change caused by this patch.

Independent commands were `git stash push` / `git stash pop`, `git diff -w --unified=0`, `git diff --check`, AST comparison, `PYTHONPATH=src python3 -m unittest discover -s tests` from `target/template`, and the target's docs lint/render commands. Test temporary storage and rendering output were confined to this review workspace.

Host caveat: `python3 -m tests.run_root_suite` exited 77 because Copier is not importable by this interpreter (`review-root.log:6`). The frozen root-suite output actually shows the render/update cases executing successfully (`gate-logs/T3-suite.log:40`, `gate-logs/T3-suite.log:54`), so the local limitation is not a patch failure or an unmet dependency in the original gate evidence. Instance-scoped wrappers were adjudicated from their supplied logs. The production-path scanner reports no new test file to inspect (`gate-logs/C5-prod-path.log:10`); it supplies no additional causal proof.

For sign-off, read `target/template/src/pdca_harness/flow.py:2141` and `:2158` alongside `target/template/src/pdca_harness/waves.py:95` and `:197`, then the seed call at `target/template/src/pdca_harness/flow.py:2176`. Confirm the wording communicates that an offered dependency is resolvable before it contributes an ordering edge, and that cycles involving the adopted child are held during the splice. The available integration document is an unrendered template whose human-only items are TODO (`target/template/docs/INTEGRATION.md.jinja:80`); it supplies no additional concrete project-specific item.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 651 (reword-stale-strict-levelling-comment)

The diff is clean on both lenses. It changes `#` comment lines only, in one file (`template/src/pdca_harness/flow.py`). There is no code change, so it cannot introduce a runtime bug, and the T3 suite passes (`gate-logs/T3-suite.log`: 2423 tests, OK). I checked each claim in the new wording against the patched tree:

- `template/src/pdca_harness/flow.py:2141-2145` — the "exactly as before" and "adoption never relaxes it" wording is gone. The new text names the single #590 relaxation and points ahead to the `offered` paragraph. The stale `waves.py:243-246` line reference is replaced by a symbol reference (`waves.partition_schedulable`'s docstring). The brief allows that, and the quoted text does exist at `template/src/pdca_harness/waves.py:277-279`. Correct.
- `template/src/pdca_harness/flow.py:2158-2166` — "resolvable here instead of raising, but adds NO edge in `compute_waves`" matches the `continue` at `template/src/pdca_harness/waves.py:95-96`. "The splice orders it" matches the `check_dep_graph` docstring at `waves.py:74-79`. "A `Stacks on` edge still refuses" matches the `dep not in stacks` guard at `waves.py:95`. Both facts the brief requires are present.
- `template/src/pdca_harness/flow.py:2163` — "a loop through the child is found and held — never a raise" is true. The splice re-levels through `_reschedule` → `waves.partition_schedulable` (`flow.py:1521`), which holds cycle members (`waves.py:319-323`) instead of raising.
- `template/src/pdca_harness/flow.py:2164` — "if adoption does not take the child, its dependent is held or skipped" matches the `_offered_by_seeds` docstring (`flow.py:2018-2020`).
- Minor wording point, not worth a change: `flow.py:2144` says "one relaxation", and `flow.py:2158` then calls it "That relaxation". The two paragraphs are split by the unrelated RE-levelling paragraph (`flow.py:2147-2156`), so a reader has to scroll back to find what "That" refers to. The paragraph names the relaxation again right away ("A `Depends on` / `Depends on (merged)` edge to such a child..."), so this does no real harm.

Reuse / simplification: nothing to flag. The new paragraph repeats some of the `check_dep_graph` docstring (`waves.py:74-79`), but the brief asks for both facts to be stated at this call site, so the repetition is intended.

No NEEDS-HUMAN findings from this lens. The C4 `unverifiable` result (exit 77, no test shipped) is the expected outcome for a comment-only change, as the brief explains. I'm not raising it again here.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Decide whether source comparison suffices for this comment-only correction — the frozen verifier explicitly exits 77 because no test ships; the independent stash/restore comparison confirms the textual correction but establishes no runtime red→green (`gate-logs/C4-verify.log:7`; `review-source.log:1`).
- [ ] T5 Judgment — Decide whether to accept the recorded path-based prior-art clearance — the brief lists merged and closed-unmerged work for flow.py, but the supplied target has only one snapshot commit and no remotes, so that history cannot be independently corroborated here (`brief.md:25`; `review-source.log:8`).
- [ ] Validation — fitness-to-purpose — Confirm the revised explanation gives maintainers enough clarity about resolvability versus splice-time ordering — code agreement is established, but whether the wording resolves the reported confusion remains the sign-off decision (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`).
- [ ] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — patch ships no test (changed: template/src/pdca_harness/flow.py)
- [ ] **The success criterion could lose a fact the current comment gets right.** The brief's criterion asks the new text to say an offered `Depends on` edge "is accepted". The code is more specific: an offered edge "is resolvable and adds NO edge here — the child joins the schedule only at the seed splice, which re-levels with it in place, so that is where the edge orders anything" (`waves.py:76-79`; already reflected at `flow.py:2158-2159`). Scope lets Do rewrite the 2157-2159 paragraph too. A rewrite that keeps only "accepted" would suggest `compute_waves` orders the edge, which is a new inaccuracy. Suggested fix: add a clause to the criterion that the reworded block must still say the offered edge adds no edge in `compute_waves` and is ordered by the `k=-1` seed splice.
- [ ] **The Falsifiability citation for the gate cannot be checked in the target repo.** The brief cites `engine/scripts/run-verify.sh` and "the `TESTS`/`PROD` classification and the 'patch ships no test' exit". No `engine/scripts/` exists in the target tree. The only `run-verify.sh` in `eduralph/pdca-harness` is `template/engine/scripts/run-verify.sh`, an unimplemented stub that `exit 1`s (`:91-94`). Its header only describes the "nothing ran → 77" rule (`:61-78`); it contains no TESTS/PROD classifier. If the gating C4 script is the operator's (pdca-pdca) copy, the brief should say so. Otherwise a reviewer cannot confirm the claim that exit 77 routes to §6 instead of failing. If C4 actually exits 1 on this bundle, the run hits a hard gate fail rather than the expected §6 route.
- [ ] **Minor line-number drift in the brief.** The brief says the docstring text is at `waves.py:277-279`. Line 277 is the docstring's opening sentence ("Split ``bundles`` into …"); the quoted phrase is at `:278-279`. Either range is fine for Do to cite, and the brief already allows a symbol reference with no line number. Raised only because the brief requires every cited `path:line` to be exact.
- [ ] T5 Judgment — Accept or independently confirm the recorded prior-art conclusion for the affected flow.py path — the brief names merged history and closed-unmerged PRs, but this artifact-only sandbox contains one synthetic base commit and no remote, preventing independent historical confirmation (`brief.md:25`; `target/template/src/pdca_harness/flow.py:2141`).

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
- Iteration delta (if iterating): Auto-iterate (round 2): rebuilding for the implementation-level findings — C4 Verification (red→green) — Decide whether source comparison suffices for this comment-only correction — the frozen verifier explicitly exits 77 because no test ships; the independent stash/restore comparison confirms the textual correction but establishes no runtime red→green (`gate-logs/C4-verify.log:7`; `review-source.log:1`).. Deferred, not addressed here: 4 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 3 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
