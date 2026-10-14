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

Review issue #651: correct the stale strict-levelling comment so it accurately explains recovery-seed dependency resolution and ordering after #590.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The bounded documentation correction has a clear acceptance criterion: distinguish initial resolvability from ordering at adoption, preserve stack refusal, and change comments only (`brief.md:11`; `target/template/src/pdca_harness/waves.py:74`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing the patch reproduced the false “adoption never relaxes it” claim while offered dependencies already bypassed refusal; this reproduces a textual defect, not a failing runtime test (`review-source.log:3`; `target/template/src/pdca_harness/waves.py:95`). |
| C3 Change | PASS | The supplied patch matches the target diff and changes only the permitted comment block; both dependency forms, deferred ordering, and stack refusal are covered (`review-source.log:1`; `target/template/src/pdca_harness/flow.py:2158`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether source comparison suffices for this comment-only correction — the verifier exits 77 because no test ships, and the independent stash/restore check establishes textual correction, not runtime red→green (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `review-source.log:12`). |
| C5 Causal adequacy | PASS | Correcting the contradictory explanation addresses the defect directly; deferred edges and cycle holding agree with the scheduler, with no added capability probe or runtime guard (`target/template/src/pdca_harness/waves.py:95`; `target/template/src/pdca_harness/waves.py:197`; `target/template/src/pdca_harness/flow.py:1521`; `target/template/src/pdca_harness/flow.py:2177`). |
| T1 Structure | PASS | No executable structure or dependency changes: pre/post Python ASTs are identical and the diff is confined to comments (`review-source.log:1`; `review-source.log:12`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, and diff whitespace check pass; the symbol reference resolves to the quoted docstring without retaining the stale line number (`review-checks.log:2`; `review-checks.log:3`; `review-checks.log:4`; `target/template/src/pdca_harness/waves.py:278`). |
| T3 Runtime | PASS | Independent patched-tree offline suite passes all 2,423 tests with two skips; frozen root-suite evidence additionally records 24 tests passing, without claiming a new runtime red leg (`review-driver.log:1814`; `review-driver.log:1816`; `gate-logs/T3-suite.log:54`; `gate-logs/T3-suite.log:56`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the deferred gate explicitly owes its substantive PR-body/tracker audit to publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the recorded prior-art disposition for `template/src/pdca_harness/flow.py` against merged history and closed/rejected PRs — the brief lists both searches, but this single-commit snapshot has no remote or captured PR evidence to independently settle them (`brief.md:25`; `review-source.log:13`; `review-source.log:14`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the revised explanation is clear enough for future scheduler maintenance — it now separates acceptance, splice ordering, and cycle holding, but that explanatory fitness requires human sign-off (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`). |

No implementation defect found. C4 is the brief's expected comment-only verification limitation, not a request to manufacture a test or alter runtime behavior. The prior iteration notes do not change that limitation into a builder-fixable defect. No external dependency is declared or needed for this correction (`brief.md:22`).

The disposable target matches the supplied patch and base; no target-state caveat was found. I stashed and restored the patch, confirmed the original contradiction and corrected wording, compared ASTs, reran the offline driver suite and docs checks, and verified the final diff still matches `patch.diff`. Instance-scoped gate wrappers were adjudicated from all six frozen logs; the production-path gate only establishes that no new test file exists (`gate-logs/C5-prod-path.log:10`), and the host-CI log records successful lint/render/link checks (`gate-logs/host-ci-docs.log:11`). The root suite was assessed from its frozen log rather than independently rerun.

For human source review, run `sed -n '2141,2179p' "$PDCA_TARGET/template/src/pdca_harness/flow.py"` and compare with `sed -n '74,109p;183,198p;275,289p;315,326p' "$PDCA_TARGET/template/src/pdca_harness/waves.py"`. Confirm the wording conveys that offered dependency edges do not order the initial batch and become ordered or held at the seed splice. The existing cycle regression grounds the added cycle explanation (`target/template/tests/test_flow_adopt_recovery.py:948`). The available integration document is the template, whose project-specific human-only list is unfilled (`target/template/docs/INTEGRATION.md.jinja:80`); no instance-specific list was supplied.

<!-- pdca:leaf-complete -->

### Advisory — code-review

# Advisory code review — issue 651 (reword-stale-strict-levelling-comment)

The patch changes `#` comment lines only, in one file (`template/src/pdca_harness/flow.py`). It makes no code change, so it cannot add a correctness bug. T3 (the offline driver suite) passed, so the file still parses. I checked each claim in the new wording against the target source. All of them hold:

- `template/src/pdca_harness/flow.py:2141-2145`: the "exactly as before" and "adoption never relaxes it" claims are gone. The stale `waves.py:243-246` line number is replaced by a symbol reference (`waves.partition_schedulable`'s docstring). The quoted text is there at `template/src/pdca_harness/waves.py:278-279`. Correct.
- `template/src/pdca_harness/flow.py:2158-2164`: "resolvable here instead of raising, but adds NO edge in `compute_waves`" matches `template/src/pdca_harness/waves.py:95-96` (`if dn in offered and dep not in stacks: continue`). It also matches the docstring at `waves.py:74-80`. "A `Stacks on` edge to such a child still refuses" matches the same `dep not in stacks` guard. The block keeps both facts the brief asks for: the edge is resolvable here, and the seed splice orders it.
- `template/src/pdca_harness/flow.py:2160-2163`: "a loop through the child is not seen here either … it holds such a loop instead of raising" is true. It is pinned by `test_a_loop_through_an_offered_child_is_held_never_a_raise` (`template/tests/test_flow_adopt_recovery.py:948`). That test asserts the "held this run — dependency cycle" message (`:972`).
- `template/src/pdca_harness/flow.py:2166`: the cited test `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it` exists at `template/tests/test_flow_adopt_recovery.py:769`. The "other #590 cases beside it" are at `:788-948`.
- Minor wording nit, not blocking (`template/src/pdca_harness/flow.py:2144`): the first paragraph says the strict check has "one relaxation". The later paragraph (`:2160-2163`) adds that a loop through an offered child is also not caught up front. That follows from the same "adds no edge" rule, so it is not a second relaxation. A reader skimming only the first paragraph could still miss it. If the builder iterates for another reason, they could add "(and so a loop through such a child)" at `:2145`. Optional.
- Reuse and simplification: nothing to flag. The new #590 paragraph mostly restates the `check_dep_graph` docstring (`waves.py:74-80`). Pointing to that docstring instead would be shorter and less likely to drift. But the brief explicitly asks for the block to keep both facts, so the restatement is justified.

No NEEDS-HUMAN findings from this lens. The C4 row is `unverifiable` (exit 77, no test shipped). The brief says that is the expected outcome for a comment-only slice. The human handles it at sign-off, and it is not a code defect in this diff.

<!-- pdca:leaf-complete -->

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C4 Verification (red→green) — Decide whether source comparison suffices for this comment-only correction — the verifier exits 77 because no test ships, and the independent stash/restore check establishes textual correction, not runtime red→green (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `review-source.log:12`).
- [ ] T5 Judgment — Confirm the recorded prior-art disposition for `template/src/pdca_harness/flow.py` against merged history and closed/rejected PRs — the brief lists both searches, but this single-commit snapshot has no remote or captured PR evidence to independently settle them (`brief.md:25`; `review-source.log:13`; `review-source.log:14`).
- [ ] Validation — fitness-to-purpose — Decide whether the revised explanation is clear enough for future scheduler maintenance — it now separates acceptance, splice ordering, and cycle holding, but that explanatory fitness requires human sign-off (`target/template/src/pdca_harness/flow.py:2141`; `target/template/src/pdca_harness/flow.py:2158`).
- [ ] C4 fix verified: bundle test red pre-fix, green post-fix unverifiable — patch ships no test (changed: template/src/pdca_harness/flow.py)
- [ ] **The success criterion could lose a fact the current comment gets right.** The brief's criterion asks the new text to say an offered `Depends on` edge "is accepted". The code is more specific: an offered edge "is resolvable and adds NO edge here — the child joins the schedule only at the seed splice, which re-levels with it in place, so that is where the edge orders anything" (`waves.py:76-79`; already reflected at `flow.py:2158-2159`). Scope lets Do rewrite the 2157-2159 paragraph too. A rewrite that keeps only "accepted" would suggest `compute_waves` orders the edge, which is a new inaccuracy. Suggested fix: add a clause to the criterion that the reworded block must still say the offered edge adds no edge in `compute_waves` and is ordered by the `k=-1` seed splice.
- [ ] **The Falsifiability citation for the gate cannot be checked in the target repo.** The brief cites `engine/scripts/run-verify.sh` and "the `TESTS`/`PROD` classification and the 'patch ships no test' exit". No `engine/scripts/` exists in the target tree. The only `run-verify.sh` in `eduralph/pdca-harness` is `template/engine/scripts/run-verify.sh`, an unimplemented stub that `exit 1`s (`:91-94`). Its header only describes the "nothing ran → 77" rule (`:61-78`); it contains no TESTS/PROD classifier. If the gating C4 script is the operator's (pdca-pdca) copy, the brief should say so. Otherwise a reviewer cannot confirm the claim that exit 77 routes to §6 instead of failing. If C4 actually exits 1 on this bundle, the run hits a hard gate fail rather than the expected §6 route.
- [ ] **Minor line-number drift in the brief.** The brief says the docstring text is at `waves.py:277-279`. Line 277 is the docstring's opening sentence ("Split ``bundles`` into …"); the quoted phrase is at `:278-279`. Either range is fine for Do to cite, and the brief already allows a symbol reference with no line number. Raised only because the brief requires every cited `path:line` to be exact.
- [ ] T5 Judgment — Accept or independently confirm the recorded prior-art conclusion for the affected flow.py path — the brief names merged history and closed-unmerged PRs, but this artifact-only sandbox contains one synthetic base commit and no remote, preventing independent historical confirmation (`brief.md:25`; `target/template/src/pdca_harness/flow.py:2141`).
- [ ] T5 Judgment — Decide whether to accept the recorded path-based prior-art clearance — the brief lists merged and closed-unmerged work for flow.py, but the supplied target has only one snapshot commit and no remotes, so that history cannot be independently corroborated here (`brief.md:25`; `review-source.log:8`).

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
- Iteration delta (if iterating): Auto-iterate (round 3): rebuilding for the implementation-level findings — C4 Verification (red→green) — Decide whether source comparison suffices for this comment-only correction — the verifier exits 77 because no test ships, and the independent stash/restore check establishes textual correction, not runtime red→green (`gate-logs/C4-verify.log:7`; `gate-logs/C4-verify.log:10`; `review-source.log:12`).. Deferred, not addressed here: 4 finding(s) that need human judgment, held in deferred-findings.json for the human at handover — not build work
- By / date: auto-iterate / 2026-10-14

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 3 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
