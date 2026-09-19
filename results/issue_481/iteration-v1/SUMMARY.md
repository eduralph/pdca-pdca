# Result — issue 481 / split-parent-keeps-a-plan-artifact

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: A split parent that was sent back by `iterate-plan` *before* it was split ends up
  terminal and `UNPLANNED` at the same time. `iterate-plan` archives the brief
  (`template/src/pdca_harness/driver.py:140`, `_archive_iteration(d, n, include_brief=True)`, which
  moves it to `iteration-v<N>/brief.md`, `driver.py:411-450`). The Plan session then splits the
  slice. `split.accept` (`template/src/pdca_harness/split.py:752`) has no brief to keep: it archives
  with `include_brief=False` (`split.py:836-838`, inside the `try` at `:828`), writes `build-notes.md` (`split.py:854-861`) and
  the `close-disposition: split` marker (`split.py:862`), and never writes a parent brief.
  `state.state()` checks for `brief.md` first (`template/src/pdca_harness/state.py:301-307`) and only
  looks at the close marker inside the has-brief branch (`state.py:310`), so the parent derives
  `UNPLANNED`. Every `pdca flow <parent>` then opens an interactive Plan session with nothing to
  decide, gets no brief back, and stops; the parent never reaches sign-off, never gets a
  `SUMMARY.md`, never freezes. `split.py:824-826` itself calls the iterated parent "the realistic
  case". The drafting door already refuses a briefless parent (`leaves.do_split`,
  `template/src/pdca_harness/leaves.py:1800-1804`, pinned by
  `test_a_bundle_with_no_brief_is_refused`, `template/tests/test_split.py:236`); the accept door
  does not (`split.accept` checks only the proposal and the marker, `split.py:763-773`). Observed on
  `getwyrd/wyrd-pdca` v0.56.0: `issue_711` and `issue_654` (both iterated, then split) are stuck;
  `issue_682` / `issue_692` (split on the first attempt) are fine.
- Success criterion: With a parent bundle shaped like the realistic case (an authored brief
  and a first attempt archived by the driver's own iterate-plan path, so `iteration-v1/` holds the
  brief and no `brief.md` is left at the top level) and a valid two-child `split-proposal.md`,
  `split.accept(parent, [ids], cfg)` leaves the parent such that ALL of these hold:
  (a) `state.state(parent)` is not `UNPLANNED` (and not `RESOLVED`);
  (b) `parent/brief.md` exists, `brief.is_placeholder` is False for it, and
  `handoff.check_planner(parent, cfg)` returns `[]`, i.e. slug, success criterion and repo + branch
  target are filled;
  (c) that brief names every child bundle the accept created;
  (d) `build-notes.md` still names the child bundles.
  Separately, (e) any bundle that carries the close marker and no `brief.md`, however it got that
  way, never derives `UNPLANNED` from `state.state()`. And (f) nothing changes for a parent that
  still has its own brief at accept time: its `brief.md` is byte-identical before and after, and
  every existing test in `template/tests/test_split.py` stays green.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Remove the briefless-terminal shape: a split accepted on a parent with no top-level
  `brief.md` must leave the parent with a Plan artifact that describes the split (why, which
  children), and `state()` must not derive `UNPLANNED` for a bundle carrying the close marker.
  The parent's original brief is on disk at `iteration-v<N>/brief.md` and the proposal is at
  `split-proposal.md`; which of these the Plan artifact is built from is Do's call. Keep
  `accept`'s transaction discipline (`split.py:828-878`: every write before the marker, rollback
  on failure). A failed accept must not leave a new parent brief behind either. / out of scope:
  hand-repairing the stuck `wyrd-pdca` bundles; the #498 hint wording; child adoption (#469/#473/#449);
  the #357 state-machine rewrite; `leaves.do_split` (its refusal stays as is); the `_do_close`
  build-notes overwrite the issue mentions (on main a bundle with brief + marker derives `BUILT`,
  so `driver.py:69-72` `_do_close` does not run for it; if Do finds otherwise, record it in
  build-notes rather than widening this slice). Refusing the accept on a briefless parent does
  NOT meet the criterion: the in-session split after iterate-plan is the realistic case and has
  to complete.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
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

Review issue #481: restore a Plan artifact for iterated split parents and prevent Do-era bundles from deriving UNPLANNED.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six success criteria distinguish restoring the parent artifact from correcting state derivation, and explicitly require rollback after failed acceptance; brief.md:24, brief.md:75; target/template/src/pdca_harness/state.py:41. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production changes while retaining the regression tests produced 4 assertion failures and 1 missing-brief error across 103 tests; review-red.log:57; target/template/tests/test_split.py:1816. |
| C3 Change | FAIL | A partial parent-brief write escapes rollback, and retry accepts the surviving truncated brief, violating the required recoverable transaction; target/template/src/pdca_harness/split.py:931, target/template/src/pdca_harness/split.py:967; review-rollback.log:2. |
| C4 Verification (red→green) | PASS | Restoring the production patch made all 103 split tests pass, independently confirming the asserted normal-path red→green; this suite does not cover the partial-write defect; review-green.log:5; target/template/tests/test_split.py:1833. |
| C5 Causal adequacy | PASS | The ordinary failure's two causes are addressed: lost parent Plan evidence and state ordering; the tests exercise real archive, accept, state and handoff APIs, and no optional-capability probe masks a load-time cause; target/template/tests/test_split.py:1821, target/template/src/pdca_harness/state.py:314. |
| T1 Structure | PASS | The change stays in the specified split/state modules and regression file, reusing the existing brief parser and transaction boundary; target/template/src/pdca_harness/split.py:734, target/template/src/pdca_harness/split.py:906. |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit and git diff whitespace check pass; the frozen host-parity log confirms the same docs checks; review-docs.log:2, gate-logs/host-ci-docs.log:10. |
| T3 Runtime | PASS | Independent offline execution passes 1,901 tests with 2 skips; frozen evidence additionally shows all 24 root render/update tests passed, including actual Copier execution; review-suite.log:1656, gate-logs/T3-suite.log:54. |
| T4 Contribution | N/A | The contribution artifacts are intentionally absent at Check; the deferred gate's substantive audit must rerun at publish; gate-logs/T4-contribution.log:10. |
| T5 Judgment | PASS | The scope follows the stated invariant; independent path-filtered merged-history checks and the sole closed-unmerged PR's file list reveal no competing fix in the checked evidence; review-history-split.log:1, review-history-state.log:1, review-history-tests.log:1, review-rejected-files.log:1. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the generated parent summary and its requirement that every child reach COMPLETE provide the intended sign-off contract for a recovered split parent — passing artifact/state tests cannot establish that operational policy; target/template/src/pdca_harness/split.py:783. |

**Finding: P2 — include failed partial writes in parent-brief rollback.** At `target/template/src/pdca_harness/split.py:931`, `Path.write_text` can create/truncate the destination and then raise, for example on disk exhaustion. `wrote_parent_brief` becomes true only after that call returns (`:933`), so the exception handler skips removal (`:967`). The children and marker are rolled back, but the new broken brief remains. On retry, `parent_had_brief` is true (`:839`), so acceptance preserves the truncated file and completes with an invalid Plan artifact.

I reproduced this against the patched source using the regression fixture's real archive/accept path. A fault injected only into the parent brief write persisted 40 characters and raised ENOSPC. The failed accept left that file behind; retry reached BUILT while `handoff.check_planner` rejected the brief. See `review-rollback.log:1` and the runnable `review-rollback.py`. This violates the explicit requirement at `brief.md:75`. Track cleanup responsibility before attempting the write, or publish the brief atomically with equivalent rollback, and cover partial-write failure plus retry.

Reproduce from this review directory:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=target/template/src:target/template/tests \
  python3 review-rollback.py
```

**Evidence and limits.** The target is the supplied self-contained patched checkout; no stale-target caveat applies. Production files were stashed for the red run and restored before the green run. The final tracked diff still contains only the three supplied changed files. Regression and suite commands were `PYTHONPATH=src python3 -m unittest discover -s tests -p test_split.py` and `PYTHONPATH=src python3 -m unittest discover -s tests`, respectively, from `target/template`, with temporary files confined under this review directory.

All six frozen gate logs were read. The C5 scanner's pass means only “no new test file,” not positive production-path verification (`gate-logs/C5-prod-path.log:10`); the independent regression supplies that evidence. Instance-scoped wrappers were not available here, so I reran their accessible underlying checks. Copier is unavailable in this review interpreter, preventing a fresh root render/update suite; the frozen log explicitly records those cases executing and passing (`gate-logs/T3-suite.log:38`, `:54`). This is a local rerun limitation, not an undischarged external dependency: the brief declares none and the captured original run exercised Copier. T4 remains deferred, not a missing-evidence finding.

The local target intentionally has one synthetic base commit. I therefore checked GitHub's main-branch commit history by each of the three affected paths and enumerated all closed-unmerged PRs via the API. The recent path histories corroborate the brief's cited work; the only closed-unmerged PR is #4, touching README.md alone (`review-unmerged.log:1`, `review-rejected-files.log:1`). No other checkout was consulted. The supplied target's integration template has no enumerated project-specific human-only items beyond its TODO (`target/template/docs/INTEGRATION.md.jinja:80`).

This review is advisory; it does not alter deterministic gate results or gate acceptance.

### Advisory — code-review

# Advisory code review — issue #481

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/split.py:735-754` (`_archived_brief_source`)
  and `:757-787` (`_parent_split_brief`) only check the archived original's **Slug** field
  (`brief_mod.is_placeholder(bp)`, which reads Slug alone — see `brief.py:161-178`) before
  treating it as a valid source and copying its `Repo + branch target` field verbatim into
  the rebuilt parent brief. Nothing checks that field for emptiness or an unfilled `<…>`
  placeholder before the write. Reproduced directly against the target: an archived brief
  with an authored Slug but a still-placeholder `Repo + branch target` line makes
  `split.accept` succeed (children created, parent marked terminal with the close marker),
  and the new `parent/brief.md` it writes fails `handoff.check_planner` — exactly the
  criterion (b) the brief requires (`brief.md:29-31`: "`handoff.check_planner(parent, cfg)`
  returns `[]`"). `check_planner` (`handoff.py:131-134`) requires all three of Slug, Success
  criterion and Repo + branch target non-placeholder; `_parent_split_brief` only guarantees
  Success criterion (it rewrites that field unconditionally) and, via the Slug-only guard,
  Slug — not Repo + branch target. The realistic case the brief describes (a COMPLETE
  authored brief archived whole by `_archive_iteration`) is unaffected and is what the new
  test class exercises, so this gap is real but untested: an archived brief that is
  authored-but-incomplete (a shape `_archive_iteration` will happily archive, since it
  doesn't validate completeness either) produces a terminal split parent whose Plan
  artifact silently fails the Plan-exit contract. Worth tightening `_archived_brief_source`
  to check the same completeness `check_planner` will later demand (or reuse
  `handoff.check_planner`-style field checks) rather than only `is_placeholder`, and to
  raise `SplitError` in the pre-write validation phase the way the "no archive found" branch
  already does at `split.py:843-848`.

- `template/src/pdca_harness/split.py:732` (`_ITERATION_RE = re.compile(r"^iteration-v(\d+)$")`)
  duplicates `size_signal.py:70` (`_ITERATION_DIR`, the identical pattern) and the
  glob-then-match-then-sort-by-int shape at `size_signal.py:147-151`. Neither module exposes
  a public helper the other could import, so this isn't a straightforward reuse miss the
  patch introduced carelessly — just noting the third private copy of "parse the numbered
  `iteration-v<N>` archives" now living in the codebase (a fourth, non-regex version already
  exists in `driver.py:315-317`, `_next_iteration_no`, which only counts). Not blocking;
  a shared `iteration_archives(d) -> list[tuple[int, Path]]` helper in one module would
  remove all three/four copies if anyone touches this area again.

## Not flagged

The transaction discipline (`split.py:904-972`) is sound: `parent_had_brief` and
`brief_source` are captured in the pre-write validation phase before any write, the new
brief is written before the breadcrumb/marker so a later failure still rolls it back
(`wrote_parent_brief` gates the `unlink` in the except branch), and criterion (f) — a
parent that already has `brief.md` is never touched — is enforced structurally (the write
is inside `if not parent_had_brief:`) and is covered by
`test_a_parent_with_its_own_brief_is_untouched`. `state.py`'s restructured ladder preserves
the placeholder-brief behaviour for every pre-existing branch (verified by inspection: the
`else`/`if not has_do_artifact` split only changes what happens when a Do-artifact is
present with no brief.md — the new fall-through case — and leaves the brief-exists /
placeholder / patch-exists combinations exactly as before). No resource leaks, no
concurrency concerns (single-process, synchronous file I/O throughout), and the test class
exercises all six criteria (a)-(f) named in the brief.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Decide whether the generated parent summary and its requirement that every child reach COMPLETE provide the intended sign-off contract for a recovered split parent — passing artifact/state tests cannot establish that operational policy; target/template/src/pdca_harness/split.py:783.
- [ ] `template/src/pdca_harness/split.py:735-754` (`_archived_brief_source`)

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
- Iteration delta (if iterating): Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — `template/src/pdca_harness/split.py:735-754` (`_archived_brief_source`)
- By / date: auto-iterate / 2026-09-18

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
