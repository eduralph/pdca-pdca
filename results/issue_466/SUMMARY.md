# Result — issue 466 / stub-split-never-reaches-the-tracker

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: With `[leaves.splitter] mode = "stub"`, `pdca split <id> --accept` files the
  **offline placeholder** proposal as real tracker sub-issues and materialises child bundles
  from fixture text. Observed live: `getwyrd/wyrd#708` and `#709` are open as sub-issues of
  `#682`, titled literally `stub-child-one` / `stub-child-two`, with `results/issue_708/brief.md`
  and `issue_709/brief.md` carrying the fixture body — nothing to do with #682's work. Verified
  on the target base, nothing in the chain can tell a stub proposal from a real one:
  * `leaves.do_split` (`template/src/pdca_harness/leaves.py:1594-1602`) branches on
    `cfg.splitter.mode == "command"` and falls through to `_stub_split` for **any** other mode —
    silently: same rc 0, same printed proposal path, nothing on stderr. The operator's only
    signal that no model ran is recognising the fixture by eye.
  * `leaves._stub_split` (`:1605-1631`) writes `<!-- pdca:split-proposal v1 -->` — byte-identical
    in shape to a real splitter's header — so **nothing on disk records the provenance**, and
    `--accept` runs in a different process from `do_split`, where an in-memory flag could not
    reach it.
  * `split.preflight` (`split.py:276-305`) and `split.validate` check structure only (proposal
    present, parent not already split, ordering labels resolve, no cycles). The stub passes
    every one, because it was written to.
  * `split.can_file` (`split.py:912-928`) asks only whether the tracker is GitHub, the repo
    resolves and `gh` is on PATH. Its "never a silent skip" docstring is about the opposite
    failure; nothing asks whether the proposal is **fit to file**.
  * `split.child_title` (`split.py:939-…`) falls back to the child's slug, so the fixture slug
    becomes the tracker issue title verbatim.
  This is the same path #358 specifies as the **offline** end-to-end test ("stub splitter →
  accept → flow over the children"), which is harmless only because `can_file` fails or `--ids`
  is supplied. In a live checkout with a working `gh` and no `--ids`, the fixture reaches the
  tracker — and tracker issues cannot be withdrawn, which is precisely the irreversibility the
  whole accept path is built around (`cli.py:756-766`, `split.py:279-283`).
- Success criterion: With the patch:
  (a) a stub-produced `split-proposal.md` is **self-identifying on disk** — the provenance is
  written into the proposal by the stub itself and survives the process boundary, so a reader
  that never saw `do_split` run can tell it apart (not a slug-name sniff, not an in-memory
  flag);
  (b) `pdca split <id> --accept` **refuses** on a stub-marked proposal **before** `can_file`
  and before any `gh issue create`, naming the cause and the remedy
  (`[leaves.splitter] mode = "command"`); the refusal is on the **filing**, not on acceptance
  as such — it exits non-zero, creates no child bundle and does not mark the parent split;
  (c) `--ids` still accepts a stub-marked proposal unchanged, so #358's offline round-trip
  keeps working: that path files nothing, the ids already exist, and the operator supplied them
  deliberately — this is the seam between "exercising the machinery" and "reaching the tracker";
  (d) `pdca split <id>` in stub mode **says so on stderr at the moment it runs**, rather than
  leaving the operator to infer it from the proposal's contents;
  (e) with `mode = "stub"` and `can_file` returning `(True, repo)`, `pdca split <id> --accept`
  invokes **no** `gh issue create` and creates **no** bundles — asserted on the *absence of the
  call*, not on the exit code alone, because a refusal that filed the first child before
  erroring is the failure mode worth locking.
  Demonstrable by C4-verify offline: the whole path is driven in-process with `subprocess.run`
  stubbed, so (b)-(e) are assertions over recorded argv.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make a stub-authored split proposal self-identifying, and make the **filing**
  branch of `pdca split --accept` refuse one; announce stub mode on stderr when `do_split` takes
  the stub branch. **Out of scope:** whether a split child should route through Plan at all (the
  issue parks it deliberately: today `split.py`'s docstring calls each child body "a full draft
  brief" and the run continues straight to Do; changing that needs a new state distinguishing
  "split seed" from "planned brief" — a separate decision); retroactive cleanup of
  `getwyrd/wyrd#708`/`#709` (instance data, by hand); the `--ids` path's behaviour, which must
  stay byte-identical; `split.validate` / `split.preflight`'s structural checks and the
  convergence report (#459), which answer a different question — whether a *real* split
  converged; `state.state`'s PLANNED derivation (`state.py:167-187`) and `brief.is_placeholder`
  (`brief.py:161-…`), which the issue cites only to explain the blast radius;
  `template/pdca.toml.jinja`; every other stub leaf (this slice is the one whose output reaches
  a tracker).

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

Task under review: Prevent an offline stub split proposal from filing real tracker children while preserving deliberate `--ids` acceptance and clearly identifying stub output.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract has a testable safety boundary: stub provenance blocks only automatic tracker filing, while operator-supplied `--ids` remains allowed because it performs no filing (`template/src/pdca_harness/cli.py:778`). |
| C2 Reproduction (red pre-fix) | PASS | With production stashed and the new test retained, the base produced 3 failures and 1 error; critically, reachable-tracker acceptance returned rc 0 instead of refusing, demonstrating exposure to irreversible filing (`template/tests/test_split_stub_guard.py:124`). |
| C3 Change | PASS | The scope is confined to persistent proposal provenance, the stub-run warning, the pre-filing decision, and focused coverage; the refusal precedes `file_children` and leaves the explicit-id path untouched (`template/src/pdca_harness/cli.py:778`). |
| C4 Verification (red→green) | PASS | Independent stash/pop verification reproduced red as 3 failures + 1 error and green as 6/6 focused tests; the complete offline test discovery also exited 0, including no-call/no-bundle assertions (`template/tests/test_split_stub_guard.py:124`). |
| C5 Causal adequacy | PASS | The cross-process root cause is discharged by producer-written provenance read before the irreversible consumer branch; this is durable artifact provenance, not an optional-capability probe or fallback guard (`template/src/pdca_harness/leaves.py:1618`, `template/src/pdca_harness/split.py:131`, `template/src/pdca_harness/cli.py:784`). |
| T1 Structure | PASS | Responsibility stays at the correct seams: the stub leaf identifies its artifact, the split module interprets provenance, and the CLI owns the filing policy (`template/src/pdca_harness/leaves.py:1611`, `template/src/pdca_harness/split.py:131`, `template/src/pdca_harness/cli.py:778`). |
| T2 Shape | PASS | `git diff --check`, docs lint, site rendering, and internal-link audit are clean; the marker matcher and refusal retain the surrounding module conventions (`template/src/pdca_harness/split.py:51`, `template/src/pdca_harness/cli.py:784`). |
| T3 Runtime | PASS | The patched focused tests pass 6/6 and the full offline driver suite exits 0; coverage exercises production `pdca_harness` and records that no tracker subprocess or child materialisation occurs (`template/tests/test_split_stub_guard.py:124`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted during Check; the frozen deferred evidence says the substantive PR-description and tracker-reference audit reruns at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Affected-path history found 0 open and no closed-unmerged overlapping PRs; nearby merged work hardens structural preflight but does not identify stub provenance, and source review found no actionable defect (`template/src/pdca_harness/split.py:294`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the live operator policy and refusal/remedy wording are fit for actual tracker workflows—the mocked red→green proves no filing call occurs, but final acceptance of the safety/UX boundary remains a human sign-off decision (`template/src/pdca_harness/cli.py:784`). |

### Advisory — code-review

# Check — advisory code review (issue #466)

Scope: `template/src/pdca_harness/{cli.py,leaves.py,split.py}` and the new
`template/tests/test_split_stub_guard.py`, as touched by patch.diff.

## Correctness

No bugs introduced by this diff.

- `template/src/pdca_harness/split.py:56` — `_STUB_RE` (`<!--\s*pdca:split-proposal-stub\s*-->`)
  cannot collide with `_VERSION_RE` (`<!--\s*pdca:split-proposal\s+v(\d+)\s*-->`): "stub" is not
  "v<digits>" and both markers are written on separate lines by `_stub_split`
  (`leaves.py:1619,1624`). Verified `_VERSION_RE` does not match the stub line and vice versa.
  `parse()`/`_scan()` are unaffected — the stub marker sits before the first
  `<!-- pdca:child -->` and is never mistaken for one.
- `template/src/pdca_harness/cli.py:784` — the `is_stub_proposal` check is correctly scoped
  inside `if not ids:` (cli.py:778), so `--ids` (criterion c) is untouched, matching the brief's
  citation of `cli.py:777-796` as the filing-only branch. The refusal happens before
  `split.file_children` (and therefore before `can_file` and any `gh issue create`), matching
  criterion (b)/(e).
- `template/src/pdca_harness/leaves.py:1594-1603` — the stderr announcement sits in the `else`
  branch guarding `_stub_split`, so `mode == "command"` prints nothing extra (test
  `test_command_mode_prints_no_stub_notice` locks this) and every non-`"command"` mode (not
  just literal `"stub"`) gets the notice — consistent with the pre-existing fallthrough the brief
  itself documents, not a new edge case introduced by the patch.
- Refactor at `cli.py:768-769` (splitting the single `read_text()` call into a `proposal_text`
  local reused by both `split.parse` and the new `is_stub_proposal` check) preserves the original
  single-read behaviour — no extra I/O, no change in exception shape (`OSError` still propagates
  from the same call site).
- C4 gate log confirms the new suite's red leg fails for the expected reasons (missing
  `is_stub_proposal` attribute, rc 0 where non-zero was expected, empty stderr) rather than an
  unrelated import error — the red is real, not `PDCA-UNVERIFIABLE` masquerading as red.

## Reuse / simplification

- `cli.py:785-790` reuses the existing `split.advisory(...)` + `return 1` shape used by the
  neighbouring `TrackerUnavailable` handler (`cli.py:795-802`), exactly as the brief's citations
  call for — no new error-reporting path was invented.
- `template/tests/test_split_stub_guard.py` duplicates (rather than imports) the `Config`/fake-`gh`
  setup pattern already present in `test_split.py`'s `Accepting` class. This is a style choice
  each test module in this suite already makes independently (no shared base class exists to
  reuse), and the brief only asked to "reuse that harness" in the sense of shape/approach, not
  necessarily via inheritance — not flagging this as a defect.

No findings need human or builder follow-up; the diff is clean on both lenses.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Decide whether the live operator policy and refusal/remedy wording are fit for actual tracker workflows—the mocked red→green proves no filing call occurs, but final acceptance of the safety/UX boundary remains a human sign-off decision (`template/src/pdca_harness/cli.py:784`).
- [x] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
- plan-reviewer produced no artifact in all 5 bundles of this sign-off batch (466/474/497/475/506) — systemic, not per-bundle: those briefs reached Do with no advisory pass, and each cost a human §6 adjudication. Act: find the leaf's failure mode, and decide whether a no-artifact plan advisory should hold Plan rather than pass through.
