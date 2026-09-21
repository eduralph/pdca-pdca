# Result — issue 566 / split-hint-honest-about-a-live-run

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Through `cli._split` and `cli._flow`, with the patch:
  (i) **In reach of a live run, the line is conditional.** When `split --accept` completes
  while (a) a live `pdca flow` run holds the parent (the sibling child's claim) — whether
  the accept runs from that run's own Plan or sign-off session or from another shell — or
  (b) a live CSV batch run (`pdca flow --from-csv`) has not yet swept its in-flight bundles
  (`flow.py:1678`), then today's line is **not** printed. In its place one line that: starts
  `<parent> marked split;`, names every child id, says that run drives them only if it
  reaches them and lists any it did not drive when it ends, and gives `pdca flow
  <child-ids>` (via `_prog()`, as today) for use after that run has ended. It never
  promises ("will drive") and never says "do not start another flow". Suggested wording:
  `issue_500 marked split; a running \`pdca flow\` holds issue_500 and drives its children
  (601 602) if it reaches them — it lists any it did not drive when it ends. After that
  run ends, drive any left with \`pdca flow 601 602\``.
  (ii) **Otherwise, today's line byte-identical.** A standalone accept, an accept after the
  run has ended (returned, raised or was killed), and an accept on a parent the live run
  has let go (e.g. a named id it skipped) print exactly
  `<parent> marked split; run \`<prog> flow <ids>\` to drive the children`.
  (iii) **End-of-run report.** Just before `_drive_and_act` returns (`flow.py:1641-1646`,
  so both CLI shapes and the CSV batch get it), for every split parent in the run's drive
  set or its adoption seeds, the run names on stderr every lineage child that is not
  terminal and not in the run's final drive set — one line per parent, with a
  `pdca flow <ids>` command. It walks through a child that is itself terminal on a split,
  as adoption does (`flow.py:1216-1231`). No such children → no line. The exit code is
  unchanged. Probe: `pdca flow 7 8` with 8 `Conflicts with: 7`, nobody answers 7's
  sign-off; while A drives 8, a split of 7 is accepted from another shell (the line is
  (i)'s conditional one, since A still holds 7); when A ends it names 7's children with
  `pdca flow 701 702`.
  (iv) **Checking never causes a false refusal.** Whatever the accept does to learn whether
  a live run holds the parent must never make a concurrent `pdca flow` over that bundle
  refuse it as "held by another run" when no run holds it. If the check can collide with a
  claim attempt, the claim side retries past it, pinned by a test that forces the
  collision deterministically.
  (v) **The text agrees.** `template/agents/planner.md.jinja:155` and `:182-183`, the
  planner seed prompt at `leaves.py:1119-1120`, and `docs/07-crosscutting.md:340-343` say
  what `--accept` now prints and when, and mention the end-of-run report.
  (vi) **Nothing else changes.** Every other line of `cli._split` and the existing
  adoption reports (`flow.py:980-985`, `:1041-1056`, `:1115`, `:1245`) are byte-identical;
  the whole `template/tests` suite stays green. Every branch that changes which line
  `--accept` prints, or whether the end-of-run report fires, has a test that fails if that
  branch is deleted.
  Shown by the named test going red on this child's base (the in-flow accept prints
  today's instruction; no end-of-run line) and green with the fix.
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b` plus the sibling
  child's accepted change; line numbers here are on `70ea12b`, verified 2026-09-19 —
  re-locate them on the stacked base)
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

Review #566: make split guidance conditional on a live run and report unfinished descendants; this iteration must omit finished children while still traversing children that were themselves split.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The carry-forward gives a falsifiable boundary: finished children must stay silent, but unfinished descendants below a terminal split must remain visible; the two earlier accepted findings are outside this iteration (`brief.md:159`, `brief.md:169`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing production changes independently reproduces six behavioral assertion failures; removing only the terminal-state skip in memory reproduces this iteration's false unfinished-work reports in three tests (`reviewer-red.log:45`, `reviewer-terminal-counterfactual.log:9`). |
| C3 Change | PASS | Finished work no longer enters the recovery list, and checking split lineage before terminal state preserves unfinished grandchildren; the terminal set covers COMPLETE, DISCONTINUED and RESOLVED (`target/template/src/pdca_harness/flow.py:1548`, `target/template/src/pdca_harness/flow.py:1556`, `target/template/src/pdca_harness/flow.py:687`). |
| C4 Verification (red→green) | PASS | The independently restored patch passes all 11 focused tests; the three iteration-specific tests also fail when only the missing state filter is removed, establishing sensitivity to this fix (`reviewer-green.log:25`, `reviewer-terminal-counterfactual.log:47`, `target/template/tests/test_split_hint_live_run.py:482`). |
| C5 Causal adequacy | PASS | The defect is incorrect membership in an unfinished-work report; checking the child's actual state corrects that classification without a capability probe or load-time workaround, and the tests exercise production CLI flow (`target/template/src/pdca_harness/flow.py:1556`, `target/template/tests/test_split_hint_live_run.py:194`). |
| T1 Structure | PASS | Reporting retains existing lineage, containment and cycle checks, and this iteration's filter changes neither adoption nor the returned results (`target/template/src/pdca_harness/flow.py:1535`, `target/template/src/pdca_harness/flow.py:1824`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit and whitespace checks pass; frozen host-parity evidence agrees (`reviewer-validation.log:2`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | Independent driver-suite execution reports 1,966 tests with two skips; frozen evidence records all 24 root tests passing, including Copier render/update cases unavailable to the review interpreter (`reviewer-suite.log:1656`, `gate-logs/T3-suite.log:54`, `reviewer-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally not drafted at Check; their substantive audit is deferred to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the recorded affected-path prior-art search adequately covers merged and closed/rejected work — the supplied single-commit target has no remotes or review history with which to independently settle overlap (`brief.md:126`, `reviewer-prior-art.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept whether silence for finished children and recovery commands for unfinished descendants provide sufficient operator guidance — the automated scenarios establish behavior, but operational fitness remains the sign-off decision (`target/template/tests/test_split_hint_live_run.py:482`, `target/template/tests/test_split_hint_live_run.py:548`). |

No new patch defect found within the authorized iteration. The accepted CSV-marker lifetime and bounded retry behavior are not reopened (`brief.md:174`). The target is readable and contains the sibling drive-claim prerequisite; there is no stale-target caveat. After stash/pop, reverse-application validation of the entire supplied patch succeeded, and no target source was edited by the reviewer.

Independent evidence:

- Ran `git stash push` in the disposable target, leaving the new test available, then `PYTHONPATH=src python3 -m unittest discover -s tests -p test_split_hint_live_run.py -v` from `target/template`; restored with `git stash pop` and reran. Red: six assertion failures plus one missing `_retry_wait` attribute error. Green: 11 tests passed. The attribute error is not counted as behavioral reproduction (`reviewer-red.log:28`, `reviewer-green.log:25`).
- To isolate the previously rejected defect from the whole patch's older red cases, compiled the report function in memory with only its terminal-state skip removed. All three new cases failed with zero errors: completed children were reported again, including alongside unfinished grandchildren. Target files remained untouched (`reviewer-terminal-counterfactual.log:50`). With the actual patch these cases pass, including traversal through a COMPLETE split child (`target/template/tests/test_split_hint_live_run.py:548`).
- Reran the production-import scanner, docs validator, renderer/link audit, and full offline driver suite. The instance-scoped gate wrappers were adjudicated against their frozen logs and the corresponding available target tools; wrapper absence is not a finding (`reviewer-validation.log:2`, `reviewer-suite.log:1656`).
- The root-suite rerun exited 77 because this interpreter cannot import Copier. This is a local host limitation, not a patch failure or an unmet feature dependency: the frozen T3 log explicitly shows actual render and update tests executing successfully, followed by 24 tests OK (`reviewer-root-suite.log:6`, `gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`). The feature's declared Python/git dependency was exercised directly; stub leaves do not suppress the terminal-state failure demonstrated by the counterfactual.
- Repeated the affected-file history query across every changed path: only synthetic base commit `cf9baae` is available and `git remote -v` is empty (`reviewer-prior-art.log:1`). The brief records the earlier affected-path search and rejected #498 attempts; closed/rejected review coverage cannot be independently verified from this artifact bundle. The template integration document lists no concrete additional human-only items (`target/template/docs/INTEGRATION.md.jinja:80`).

### Advisory — code-review

# Advisory code review — issue #566

## Findings

- NEEDS-HUMAN [impl] — `drive_claim.held()`'s success path doesn't suppress `OSError` on
  close the way every other claim-handling path in this module does.
  `template/src/pdca_harness/drive_claim.py:281-284`:
  ```
  with contextlib.suppress(OSError):
      act._unlock(fh)
  fh.close()
  return False
  ```
  Every other close in this module — the failure branch three lines above
  (`drive_claim.py:278-279`), `Run.take`'s two close sites (`:198-199`, `:207-208`), and
  `_release` (`:144-150`, used by `Run.release`/`Run.close`) — wraps `fh.close()` in
  `contextlib.suppress(OSError)`. This one doesn't, so a rare close-time `OSError` (a full
  disk flushing a buffered `"a+"` handle, an NFS I/O error) escapes `held()` uncaught.
  `held()`'s only caller is `cli.py:892`
  (`if drive_claim.held(cfg, d) or drive_claim.held(cfg, drive_claim.sweep_marker(cfg)):`),
  sitting directly inside the block `cli.py:875-878` calls out by name as the exact thing
  that must never happen again: "no write here can change the outcome — but an unguarded
  one could still change the EXIT CODE… before #459, [this] turned a completed acceptance
  into a traceback." An uncaught `OSError` out of `held()` would do exactly that — crash
  `cli._split` after the tracker issues are already filed and the child bundles are already
  on disk, on the very call this patch adds to that guarded tail. Fix: wrap the `fh.close()`
  at `drive_claim.py:283` in `contextlib.suppress(OSError)` like its neighbors.

- `flow._warn_stranded_split_children`'s lineage walk (`flow.py:1539-1547`) dedupes a child
  only by `cd.name`, not by resolved path — unlike `_adoptable`'s own walk (`flow.py:1041-
  1047`, `seen_real`), which the same function's docstring says it mirrors. A lineage record
  naming one bundle under two spellings that resolve to the same directory (a symlinked
  alias, same hazard `_adoptable` guards against) would be examined twice and, if in flight,
  could appear twice in one `stranded` line's `pdca flow <ids>` command. Read-only report,
  so the worst case is a redundant id in the printed hint, not a scheduling error — low
  severity, and outside brief scope (the adoption algorithm itself is explicitly out of
  scope), so I'm not asking for a fix, just flagging it since the docstring claims a mirror
  that isn't quite complete.

## Everything else

Traced the rest of the diff against the target source (`drive_claim.Run.take`'s retry loop,
`flow._warn_stranded_split_children`'s terminal/split-marked ordering against `_adoptable`,
the `sweep_marker`/`flow_batch` claim-and-release, `cli._split`'s conditional line) and it
holds up. The iteration-1 carry-forward bug (finished split children reported as "left
in-flight") is fixed correctly: the terminal check now runs after the split-marked check, in
that order, walking through a terminal-and-split child while skipping a terminal-and-not-
split one — matches `_adoptable`'s own ordering and reasoning, and is pinned by three new
tests I traced by hand (`test_end_of_run_report_is_silent_when_every_split_child_is_finished`,
and the two "walks through" tests) against the actual `driven`/`_TERMINAL`/`_split_marked`
checks at `flow.py:1546-1561`. C4's gate log confirms the new test file (11 tests) is
genuinely red on the reverted production hunks (6 failures + 1 error) and green with them
applied — it exercises the fix, not a copy of it.

Minor, non-blocking reuse note: `_split_marked` (`flow.py:1461-1483`) duplicates the
close-marker read `_is_split_parent` already does (`flow.py:924-930`), deliberately dropping
the terminal gate — the docstring explains why at length, and the duplication is small and
justified, not worth a refactor for this patch.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the recorded affected-path prior-art search adequately covers merged and closed/rejected work — the supplied single-commit target has no remotes or review history with which to independently settle overlap (`brief.md:126`, `reviewer-prior-art.log:1`).
- [x] Validation — fitness-to-purpose — Accept whether silence for finished children and recovery commands for unfinished descendants provide sufficient operator guidance — the automated scenarios establish behavior, but operational fitness remains the sign-off decision (`target/template/tests/test_split_hint_live_run.py:482`, `target/template/tests/test_split_hint_live_run.py:548`).
- [x] `drive_claim.held()`'s success path doesn't suppress `OSError` on

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
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
