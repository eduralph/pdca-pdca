# Result — issue 590 / flow-dep-on-seed-child-refused

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `pdca flow 809 810 776 777` is refused before any work when `809` is terminal on
  a split (its children `839`–`843` still PLANNED — the recovery-seed case #473 handles) and
  `810` (also named) declares `Depends on: 842`, a child of `809`:
  `issue_810: declared dependency '842' is neither in this batch nor an existing COMPLETE bundle`.
  `flow 809` alone works (the children are adopted), and `flow 839 840 841 842 843 810 776 777`
  works; only naming the seed AND an id that depends on one of its children fails.
  Cause: `flow_ids` moves the terminal split parent out of the drive set into `seeds`
  (`template/src/pdca_harness/flow.py:2232-2268`). `_drive_and_act` then levels the NAMED
  batch strictly first — `waves.compute_waves(cfg, bundles)` (`flow.py:1830`), which calls
  `check_dep_graph` (`template/src/pdca_harness/waves.py:171`) — and only afterwards splices
  the seeds' children in at `k=-1` (`flow.py:1836-1839`). At the strict check `842` is neither
  in the batch nor COMPLETE, so `check_dep_graph` raises (`waves.py:81-99`), although the very
  next statement would have scheduled `842` ahead of `810`. The comment above the strict call
  (`flow.py:1815-1818`) says the strictness "belongs to the request… and adoption never relaxes
  it"; here the prerequisite IS part of the request — the operator named its parent as a
  recovery seed.
- Success criterion: With the patch, through `cli._flow` (the operator surface) on the
  offline driver suite: given a parent `P` already terminal on a split (via the production
  `split.accept`) whose child `C` is PLANNED, and a named bundle `D` with `Depends on: C`,
  `pdca flow P D` is NOT refused: `C` is adopted and driven in an earlier wave than `D`, and
  `D` is driven after it (both reach COMPLETE with stubbed leaves). Exact shape for the repro
  below (`500` split into `601`, `602` with `602 Depends on: 601`, the fixture's `_CHILD_TWO`;
  `810 Depends on: 602`): `waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]]`. Pre-fix the same call
  returns rc 2 with "declared dependency 'C' is neither in this batch nor an existing COMPLETE
  bundle" and drives nothing. The strict contract still holds for everything else: in the
  same suite, `pdca flow D` alone (no seed named) and `pdca flow P D` where `D` depends on an
  id that is NOT among `P`'s lineage children are still refused up front with rc 2, exactly
  as today. A grandchild reached by walking through a child that is itself terminal on a
  split (#473's 500 → 601 → 701 walk) counts as offered too.
  Boundary cases, both in the same file:
  (a) **Not offered ⇒ still refused up front.** `D` depends on a lineage child of `P` whose
  bundle is already terminal and not COMPLETE (DISCONTINUED or RESOLVED), or has no brief.md:
  `pdca flow P D` returns rc 2 with today's "neither in this batch nor an existing COMPLETE
  bundle" message and drives nothing. "Offered" means: a lineage child (reached transitively)
  whose bundle has a brief and is in flight (not terminal). A child that is COMPLETE already
  resolves today; a child terminal on a split is walked through, not offered.
  (b) **Offered, then not taken ⇒ held, never a raise.** `C` is offered but adoption does not
  take it because another run holds its drive claim (hold it the way
  `test_split_adoption_skips_a_child_another_live_run_holds` does,
  `template/tests/test_flow_single_driver.py:610-632` — a real second process holding the
  claim via that file's `_hold` helper; copy the technique, do not import from that file):
  `pdca flow P D` returns without a traceback and without rc 2, `C` and `D` are not driven,
  and stderr names `D` as not built for want of `C` (today's `_runnable` line "skipped —
  prerequisite(s) not ready (C)", `flow.py:714-715`, or the `_reschedule` hold line if a
  re-level ran — either shape, but `D` is named). The rc is not 2 (no up-front refusal);
  assert `D`'s state is still PLANNED rather than pinning an exact rc.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Before the strict levelling, the names the seeds will offer must count as
  resolvable for the strict check. Collect them with a QUIET walk: read each seed's lineage
  record with `split.read_lineage` + `_lineage_children` (`flow.py:770-788`, the reader adoption
  itself uses — never a second parse), walk THROUGH children that are themselves terminal on a
  split (`_is_split_parent`), and keep a child only if its bundle has a brief and is not
  terminal (the "offered" definition in the criterion). Do NOT call `_adoptable` /
  `_adopt_split_children` for this: they print operator-facing lines (malformed record, "no
  readable children record", "NOT adopted: no brief.md", "is itself terminal on a split",
  "already terminal", `flow.py:1167-1175`, `:1231-1244`) and append to `refused`, so a second
  pass would print every line twice and break exact-count assertions such as
  `test_flow_adopt_recovery.py:393`. Do not refactor `_adoptable` either; the k=-1 adoption pass
  stays exactly as it is.
  How the names reach the check: add an optional keyword parameter (e.g. `offered:
  frozenset[str] = frozenset()`) to `waves.check_dep_graph` and pass it through
  `waves.compute_waves`; with the default, behaviour is byte-for-byte today's. A dependency on
  an offered name is resolvable and adds no edge in the strict levelling (the child is not in
  the named batch yet); the `k=-1` splice already re-levels the whole schedule with the
  children in it, and that is where the edge becomes a real ordering constraint. ONLY the
  strict call in `_drive_and_act` (`flow.py:1830`) passes `offered`. The other callers —
  `_reschedule`'s `compute_waves` (`flow.py:1267`), `partition_schedulable`, and `pdca waves` —
  stay unchanged. Do not pass the offered names in as a pseudo-batch (that would add real
  edges and bundles to the strict levelling).
  `Depends on` / `Depends on (merged)` only: a `Stacks on:` edge to a seed child stays refused
  up front as today (`waves.py:80-91` — a stack parent must be an active COMPLETE bundle with a
  live published branch, which a PLANNED child is not).
  A dependency that adoption then does not take is held (see Invariant) — never a mid-run raise.
  / out of scope: edges that point at the split PARENT itself (#499 — different case);
  changing what adoption adopts or how children are claimed (#565); the refusal's message
  shape (#589, done); `Stacks on` to a seed child (stays refused); `flow_batch` (CSV) — it has
  no seeds; refactoring `_adoptable`'s reporting.

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

Review issue #590: allow `pdca flow P D` to schedule a named split parent’s eligible descendants before their dependent, while preserving unrelated dependency refusals.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The requested ordering, refusal boundaries, live-claim hold and carry-forward cases are falsifiable and within the declared scope; `brief.md:24`, `brief.md:145`; executable criteria at `target/template/tests/test_flow_adopt_recovery.py:769`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes reproduces six assertion failures, including the original dependency refusal, with the patched tests retained; `review-red.log:13`, `review-red.log:68`; `target/template/tests/test_flow_adopt_recovery.py:769`. |
| C3 Change | PASS | Requested children precede the dependent; absent seeds, unrelated or ineligible children, and stack edges still refuse; grandchild and live-claim boundaries pass; `target/template/tests/test_flow_adopt_recovery.py:788`, `target/template/tests/test_flow_adopt_recovery.py:809`, `target/template/tests/test_flow_adopt_recovery.py:844`, `target/template/tests/test_flow_adopt_recovery.py:874`, `target/template/tests/test_flow_adopt_recovery.py:918`. |
| C4 Verification (red→green) | PASS | Restoring the production changes turns the same 22-test run from six failures to green, independently confirming the frozen gate; `review-red.log:68`, `review-green.log:3`, `gate-logs/C4-verify.log:10`; `target/template/tests/test_flow_adopt_recovery.py:769`. |
| C5 Causal adequacy | PASS | The premature rejection now considers descendants offered by the request before adoption establishes ordering; this addresses the incomplete request view, with no optional-capability probe masking a load-time cause; `target/template/src/pdca_harness/flow.py:1887`, `target/template/src/pdca_harness/waves.py:95`. |
| T1 Structure | PASS | Existing lineage parsing, containment checks and adoption remain authoritative; the offered-name exception is confined to initial recovery levelling and defaults empty for other callers; `target/template/src/pdca_harness/flow.py:1777`, `target/template/src/pdca_harness/flow.py:1889`, `target/template/src/pdca_harness/waves.py:65`. |
| T2 Shape | PASS | Independent whitespace, docs lint and 22-page site/link checks pass; frozen host-CI evidence agrees; `review-grounding.log:8`, `review-scanners.log:1`, `gate-logs/host-ci-docs.log:10`; CI commands at `target/.github/workflows/docs-check.yml:1`. |
| T3 Runtime | PASS | Independent offline run passes 2,306 tests with two skips; frozen root-suite evidence additionally shows 24 tests passing, including actual update compatibility cases; `review-suite.log:1796`, `gate-logs/T3-suite.log:42`, `gate-logs/T3-suite.log:54`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the deferred substantive audit must run at publish; `gate-logs/T4-contribution.log:8`, `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged-history and closed/rejected-work search excludes an already accepted or rejected equivalent — the brief reports a search, but the supplied snapshot has one synthetic base commit, no remotes and no closed-PR evidence; `brief.md:127`, `review-grounding.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept recovery seeds as offering their eligible descendants, including partial progress when a newly visible cycle holds the dependent — tests establish ordering and rc 1 with held nodes, but operational suitability remains the sign-off decision; `target/template/tests/test_flow_adopt_recovery.py:769`, `target/template/tests/test_flow_adopt_recovery.py:948`. |

No patch defect found. Source citations above are grounded in the supplied `$PDCA_TARGET`; its base identifies `c67a14d77537fcf7208bfc0785e4c60a5f11eda0`, and its restored diff exactly matches `patch.diff` (`review-grounding.log:10`). No stale-target caveat applies.

Independent reproduction used `git stash push` for only `flow.py` and `waves.py`, ran `PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery` from `target/template`, restored the stash, and ran the identical command again. All temporary test work was directed into this review sandbox. The full offline suite and scanner outputs are retained in `review-suite.log` and `review-scanners.log`.

The frozen C5 scanner explicitly audited no new test file (`gate-logs/C5-prod-path.log:10`); its green result alone does not establish causal coverage. Source inspection and the independent red→green run do: the fixture calls production `cli._flow`, creates lineage through `split.accept`, and holds a production drive claim in a real second process (`target/template/tests/test_flow_adopt_recovery.py:185`, `target/template/tests/test_flow_adopt_recovery.py:234`, `target/template/tests/test_flow_adopt_recovery.py:122`). Stubbed leaves do not hide the reported scheduling failure, which reproduced before the fix. The brief declares no external dependency (`brief.md:119`).

The instance-scoped gate wrappers are not supplied. Their logs were read; equivalent available checks were rerun directly. Root render/update verification is adjudicated from its full frozen log because this synthetic checkout has no release tags for a genuine prior-release comparison (`review-grounding.log:6`; `target/tests/test_update_compat.py:55`). The supplied integration template lists no concrete additional human-only items (`target/template/docs/INTEGRATION.md.jinja:80`).

### Advisory — code-review

# Advisory code review — issue 590 (flow-dep-on-seed-child-refused)

I found no correctness bug in the patch. All gates are green: C4 is red without the fix (6 of the 22 cases fail) and green with it, and T3 ran 2306 tests OK. The notes below are small cleanups and edge cases. None blocks.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:1868-1871`: the old comment above the strict levelling still says the named batch "is levelled first and strictly, exactly as before" and "adoption never relaxes it". The new paragraph at `flow.py:1884-1886` now says the opposite: seed-offered children do relax it. Reword the first paragraph (for example, "adoption relaxes it only for what a named seed offers, #590") so the two paragraphs agree.
- `template/src/pdca_harness/flow.py:1743-1796` (`_offered_by_seeds`) copies `_adoptable`'s child filters (`_PLAIN_ID`, `_inside_bundle_root`, terminal / split walk-through, UNPLANNED / no brief) instead of sharing one predicate with `flow.py:1199-1247`. The brief chose this on purpose, to keep the walk quiet and leave `_adoptable` alone, so this is not a defect. It is a drift risk, though: if adoption's filter changes later, the up-front check and adoption can disagree. Any such disagreement goes to the safe side, because an offered child adoption does not take is held by `_reschedule` / `_runnable` rather than raised. That safety path is covered by `test_an_offered_child_another_run_holds_is_held_never_a_raise`.
- `template/src/pdca_harness/flow.py:1769-1795`: two small differences from adoption, both harmless.
  - Aliases: `_adoptable` drops a second record entry that resolves to an already-seen directory (`flow.py:1211-1216`), but the offered walk keeps it under its alias name. So `Depends on: <alias>` passes the strict check and is then held by the tolerant re-level, never raised.
  - Failed reads: the `try` covers a seed's whole child loop. One child whose read raises drops the rest of that seed's children from `offered`, which is stricter, not looser. Today the only call in that loop that could plausibly raise is `state.state`.
  Neither needs action. If you want the second one tighter, move the `try` inside the `for cid` loop.
- Tests (`template/tests/test_flow_adopt_recovery.py:725-973`): they go through `cli._flow` and cover every case the brief and the iteration-1 carry-forward ask for: the main repro with the exact `waves_driven`, the grandchild walk, both strict-contract regressions, boundary (a) for all three not-offered states, boundary (b) with a real second process holding the claim, `Depends on (merged)`, three `Stacks on` shapes, and the cycle through an offered child. I found nothing weak in them. The holder helper (`_hold_main` / `_BOOT`) copies the `_hold` technique from `test_flow_single_driver.py:383` without importing it, as the brief requires. Its waits are bounded by `_WAIT`, and cleanup kills the process if it hangs.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the affected-path merged-history and closed/rejected-work search excludes an already accepted or rejected equivalent — the brief reports a search, but the supplied snapshot has one synthetic base commit, no remotes and no closed-PR evidence; `brief.md:127`, `review-grounding.log:1`.
- [x] Validation — fitness-to-purpose — Accept recovery seeds as offering their eligible descendants, including partial progress when a newly visible cycle holds the dependent — tests establish ordering and rc 1 with held nodes, but operational suitability remains the sign-off decision; `target/template/tests/test_flow_adopt_recovery.py:769`, `target/template/tests/test_flow_adopt_recovery.py:948`.
- [x] `template/src/pdca_harness/flow.py:1868-1871`: the old comment above the strict levelling still says the named batch "is levelled first and strictly, exactly as before" and "adoption never relaxes it". The new paragraph at `flow.py:1884-1886` now says the opposite: seed-offered children do relax it. Reword the first paragraph (for example, "adoption relaxes it only for what a named seed offers, #590") so the two paragraphs agree.
- [x] **The prescribed reader prints to stderr, so calling it twice duplicates operator output.** The brief's Citations say to "collect the offered names with that same reader" (`_adoptable`, `flow.py:1103`). Its Scope cites the same walk (`_adopt_split_children` / `_adoptable`, `flow.py:1103-1180`). But `_adoptable` has side effects. It prints the malformed-record warning (`flow.py:1167-1171`), the "no readable children record" line (`:1173-1175`), the "NOT adopted: no brief.md" line (`:1231`), "is itself terminal on a split; examining it" (`:1240-1241`) and "already terminal" (`:1244`). It also appends to the caller's `refused` list. A pre-strict pass through it, followed by the real pass at `k=-1`, prints each of those lines twice. That would break existing exact-count assertions, for example `err.count("issue_500 — child of issue_601 is itself terminal on a split…")` in `tests/test_flow_adopt_recovery.py:393`. The Scope then says something different: "Read the children … the same way adoption does (`_lineage_children`, `flow.py:770-788`)". That function is the silent, unfiltered reader. The brief needs to pick one: either a quiet transitive walk over `split.read_lineage` + `_lineage_children` (walking through children terminal on a split per `_is_split_parent`), or a refactor of `_adoptable` that separates its reporting from its selection. That refactor would be a second change and should be scoped as one.
- [x] **"Offered" is not defined, and the choice changes which edges stop being refused up front.** Should every id in the seeds' lineage records count as resolvable, or only those `_adoptable` would actually take? Take the raw-lineage reading. Then a named `D` that depends on a seed child that is already DISCONTINUED or RESOLVED, unbriefed, outside the bundle root, or `_PLAIN_ID`-invalid stops being refused before any work. It becomes a later skip or hold instead. That relaxes the very contract the brief says it keeps ("an edge to anything else unresolvable still refuses before any work"). The success criterion only pins a dep on an id that is *not* among the lineage children. Add a criterion case: `D` depends on a lineage child that is already terminal-not-COMPLETE, with the expected outcome stated (refused rc 2 up front, or held). Otherwise the boundary is unfalsifiable.
- [x] **The "not taken" invariant names a mechanism the code doesn't use on one path, and no test pins it.** The Invariant and Scope say that a dependency adoption does not take "is held by the tolerant re-level … (`flow._reschedule`, `flow.py:1251-1270`)". But `_reschedule` runs only `if adopted:` (`flow.py:1454-1457`). Suppose `C` is the seed's only adoptable child and it is refused, because it is claimed by another run (`_refused_child`, `:1440`) or fails `_admit` (`:1442`). Then nothing is re-levelled. `D` stays in the strict wave list without the edge, and `_runnable` skips it at its wave (`flow.py:705-716`, "skipped — prerequisite(s) not ready"). That is a different report shape from `_report_held`. It doesn't raise, so the safety claim holds, but the brief describes the wrong mechanism. More importantly, the success criterion has no case for "the edge is accepted up front, then adoption does not take `C`". That is the riskiest new path the fix opens. Add at least one criterion case, e.g. `C` claimed by a fake concurrent run, or the record lists `C` but `C` has no brief. State the expected rc and stderr shape, and require "no traceback".
- [x] **`Stacks on` is in the strict check but the brief doesn't mention it.** `check_dep_graph` checks `Stacks on` against the active bundle (`waves.py:80, 86-91`), because a stacked dependent bases its PR on the parent's live published branch. The brief only discusses `Depends on`. If `D` declares `Stacks on: C`, where `C` is a seed child, does the fix accept it too? The `--no-publish` criterion can't exercise a stack base. Either scope `Stacks on` out explicitly, or state the expected behaviour.
- [x] **Two files means changing a shared signature that other callers use; say how it stays narrow.** Difficulty says the change touches `waves.check_dep_graph` / `compute_waves`, "whose strictness is shared with `partition_schedulable`'s callers" and with `pdca waves`. Adding an `offered`/`also_resolvable` parameter is fine if it defaults to empty. The brief should say so, and should require the existing callers (`_reschedule`'s `compute_waves`, `flow.py:1267`; `pdca waves`) to stay unchanged. Otherwise Do may widen the relaxation to every entry point, which goes beyond the one-fix scope. A smaller option would keep `waves.py` untouched and pass the offered names in as a pseudo-batch. The brief should say which design it wants, so review isn't left to settle it.
- [x] (minor) — **The criterion pins wave shape via "an earlier wave", but the brief doesn't name the expected `waves_driven`.** The fixture records `self.waves_driven`, and existing tests assert exact lists (e.g. `test_flow_adopt_recovery.py:444`). For `pdca flow 500 810` with `810 Depends on: 602` and `602 Depends on: 601`, the expected list is `[["issue_601"], ["issue_602"], ["issue_810"]]`. Stating that makes the green check exact rather than a judgement call.

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
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
- issue 590: stale comment at `flow.py:1868-1871` still says the strict levelling is "exactly as before" and "adoption never relaxes it" — reword to match #590 (seed-offered children relax it).
