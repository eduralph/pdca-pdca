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

Review issue #590: allow a named flow bundle to depend on an in-flight child offered by a named terminal split parent, while preserving refusal and safe-hold boundaries.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The recovery contract is falsifiable: children precede their named dependent, unrelated or unavailable prerequisites still refuse, and claimed children hold dependents safely (`brief.md:23`; `target/template/tests/test_flow_adopt_recovery.py:769`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only production changes reproduced the child, grandchild, and live-claim refusals before work; the retained 19-test suite failed exactly those three cases (`reviewer-red.log:2`; `target/template/tests/test_flow_adopt_recovery.py:782`). |
| C3 Change | PASS | The expanded request admits only eligible seed lineage dependencies; ordinary callers retain strict defaults and stack edges remain refused, including mixed dependency/stack declarations (`target/template/src/pdca_harness/waves.py:95`; `target/template/src/pdca_harness/flow.py:1886`; `reviewer-boundaries.log:2`). |
| C4 Verification (red→green) | PASS | Restoring the production patch changed the same recovery suite from three failures to all 19 passing, including exact child-before-dependent ordering and the real second-process claim boundary (`reviewer-red.log:35`; `reviewer-green.log:3`; `target/template/tests/test_flow_adopt_recovery.py:784`). |
| C5 Causal adequacy | PASS | The failure was an incomplete request view at strict validation; eligibility is now established before that check, and production split/CLI execution demonstrates the correction without a capability-probe workaround (`target/template/src/pdca_harness/flow.py:1886`; `target/template/tests/test_flow_adopt_recovery.py:242`; `target/template/tests/test_flow_adopt_recovery.py:188`). |
| T1 Structure | PASS | The change stays within lineage eligibility and wave validation; adoption reporting, drive claims, and tolerant rescheduling keep their existing ownership, limiting cross-entry-point regression risk (`target/template/src/pdca_harness/flow.py:1777`; `target/template/src/pdca_harness/flow.py:1894`; `target/template/src/pdca_harness/waves.py:172`). |
| T2 Shape | PASS | Independent whitespace validation, docs lint, and the 22-page render/link audit passed using the target's CI commands (`reviewer-grounding.log:13`; `reviewer-docs-lint.log:1`; `reviewer-docs-render.log:2`; `target/.github/workflows/docs-check.yml:36`). |
| T3 Runtime | PASS | Independent offline execution passed 2,303 tests with two skips; frozen evidence additionally records 24 successful root render/update tests, while the local root rerun lacked importable Copier (`reviewer-suite.log:1796`; `gate-logs/T3-suite.log:38`; `gate-logs/T3-suite.log:54`; `reviewer-root-suite.log:6`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; the substantive contribution audit is deferred to its mandatory publish rerun (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm that merged and closed/rejected work by all three affected paths does not supersede this fix — the brief records production-path searches but omits the changed test path, and the supplied target has one synthetic commit, no remote, and no PR evidence to independently settle that judgment (`brief.md:127`; `reviewer-grounding.log:1`; `target/template/tests/test_flow_adopt_recovery.py:769`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept whether the demonstrated recovery ordering and safe holds meet the operator's intended workflow — the requested offline CLI scenario is exercised, but production operational fitness remains the sign-off decision (`brief.md:23`; `target/template/tests/test_flow_adopt_recovery.py:784`; `reviewer-boundaries.log:18`). |

No patch defect was found. Source citations above resolve within the supplied `$PDCA_TARGET` (`target/`); other citations name supplied evidence or this review's rerun logs. The disposable base identifies itself as `c67a14d`, matching the brief. After verification, `git diff` matched `patch.diff` byte for byte.

Independent verification used `PYTHONDONTWRITEBYTECODE=1` and a `TMPDIR` inside this review directory. For red→green, I stashed only `flow.py` and `waves.py`, retained the added tests, ran `PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery` from `target/template`, restored the stash, and repeated the identical command. The full driver command was `PYTHONPATH=src python3 -m unittest discover -s tests`.

Supplemental CLI exercises using the existing production-backed fixture confirmed `Depends on (merged)` drives `601 → 602 → 810`; `Stacks on`, including a mixed declaration, returns rc 2 with no work; and two real claim-holder processes preventing all adoption leave `810` PLANNED with rc 1 and an explicit prerequisite skip (`reviewer-boundaries.log:1`, `:10`, `:18`). This also exercises the no-reschedule hold path beyond the patch's regression cases.

All six frozen gate logs were inspected. The C5 scanner explicitly did no substantive check because no new test file was added (`gate-logs/C5-prod-path.log:10`); C5 above rests on inspecting and exercising the actual production calls. Instance-scoped wrappers were not available here; their absence is expected. Docs/host-parity checks were reproduced with the commands in the target workflow. The local root runner exited 77 because `/usr/bin/python3` cannot import Copier; it did not independently verify render/update coverage. The frozen T3 log explicitly shows those cases executing successfully, so this is a local host limitation, not a patch defect or an undischarged dependency of the demonstrated fix. The brief declares no external dependencies (`brief.md:119`).

The supplied integration template's human-only list remains a TODO (`target/template/docs/INTEGRATION.md.jinja:80`); it enumerates no additional project-specific decisions. Prior-art confirmation and fitness-to-purpose are the two decisions carried by the NEEDS-HUMAN rows above.

### Advisory — code-review

# Advisory code review — issue 590 (flow-dep-on-seed-child-refused)

Lenses: correctness bugs the patch introduces; reuse / simplification / efficiency.
Grounded on `$PDCA_TARGET` (patched tree). Advisory only.

**Overall: no correctness bug found.** The fix does what the brief asks. The quiet walk
gives the same answers as `_adoptable` for every case the brief defines (plain-id guard,
containment guard, walk through split children, terminal / no-brief children not offered).
`check_dep_graph` behaves exactly as before when `offered` is empty. Only the strict call
passes it. C4 goes red for the right reason: all three new positive tests fail pre-fix on
the exact refusal message (`gate-logs/C4-verify.log`). T3 runs green. The holder-process
test cleans up in the right order (release runs before rmtree, because cleanups run last
in, first out) and uses `drive_claim.Run.take`'s real "None means held" contract.

Findings, all minor:

- `template/src/pdca_harness/waves.py:95` — **cycle through an offered child is no longer
  refused up front.** An offered name adds no edge to the strict levelling, so a loop like
  `810 Depends on: 602` + `602 Depends on: 810` (602 a seed child) now passes the strict
  check. The `k=-1` splice re-levels through the tolerant path (`_reschedule`), which holds
  both and reports them rather than raising. Before the patch the same request was refused
  with rc 2 (as an unresolved dependency). The end state is safe (nothing built, both
  PLANNED, reported), and the brief explicitly asked for "adds no edge". But it is a small
  change to "unschedulable ⇒ refused before any work" that no test pins. Noting it so the
  human knows. No action needed unless they want the cycle refused up front too.
- `template/src/pdca_harness/flow.py:1774-1792` — **one `try` per parent, not per child.**
  If one child's `state.state` / `_inside_bundle_root` raises, the `except` drops that
  child *and every later sibling* in the same record. That fails safe (fewer offered names
  means today's strict refusal), but it can refuse an edge to a healthy sibling that
  adoption will in fact adopt a moment later. Moving the `try` inside the `for cid` loop
  would limit the damage to the bad entry. Low likelihood (those helpers are documented as
  never raising), so this is a cleanup, not a defect.
- `template/src/pdca_harness/flow.py:1743-1793` — **the filter is a second copy of
  `_adoptable`'s rules** (`flow.py:1103-1244`): plain-id, containment, terminal/split walk,
  no-brief. The brief required this (no refactor of `_adoptable`, no second noisy pass), and
  the two match today. Small differences: the copy skips `_adoptable`'s dedupe-by-resolved-
  path and its `known` check. Neither changes the result, because `check_dep_graph` checks
  `names` first and an aliased name that adoption then skips is just held at the re-level.
  The risk is drift: a future change to what `_adoptable` accepts must also be made here, or
  the strict check and adoption will disagree. A one-line cross-reference comment inside
  `_adoptable` pointing at `_offered_by_seeds` would make that harder to miss. Not a blocker.
- `template/src/pdca_harness/flow.py:1770` — `to_examine.pop(0)` on a list is O(n) per
  pop. The lists are tiny (one lineage tree), so this does not matter in practice. A
  `collections.deque` or a plain `pop()` (order does not affect a set result) would be
  cleaner. Nit.

No NEEDS-HUMAN items. Nothing above needs an architecture or scope call, and none of it
is a defect the builder must fix before sign-off.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm that merged and closed/rejected work by all three affected paths does not supersede this fix — the brief records production-path searches but omits the changed test path, and the supplied target has one synthetic commit, no remote, and no PR evidence to independently settle that judgment (`brief.md:127`; `reviewer-grounding.log:1`; `target/template/tests/test_flow_adopt_recovery.py:769`).
- [ ] Validation — fitness-to-purpose — Accept whether the demonstrated recovery ordering and safe holds meet the operator's intended workflow — the requested offline CLI scenario is exercised, but production operational fitness remains the sign-off decision (`brief.md:23`; `target/template/tests/test_flow_adopt_recovery.py:784`; `reviewer-boundaries.log:18`).
- [ ] **The prescribed reader prints to stderr, so calling it twice duplicates operator output.** The brief's Citations say to "collect the offered names with that same reader" (`_adoptable`, `flow.py:1103`). Its Scope cites the same walk (`_adopt_split_children` / `_adoptable`, `flow.py:1103-1180`). But `_adoptable` has side effects. It prints the malformed-record warning (`flow.py:1167-1171`), the "no readable children record" line (`:1173-1175`), the "NOT adopted: no brief.md" line (`:1231`), "is itself terminal on a split; examining it" (`:1240-1241`) and "already terminal" (`:1244`). It also appends to the caller's `refused` list. A pre-strict pass through it, followed by the real pass at `k=-1`, prints each of those lines twice. That would break existing exact-count assertions, for example `err.count("issue_500 — child of issue_601 is itself terminal on a split…")` in `tests/test_flow_adopt_recovery.py:393`. The Scope then says something different: "Read the children … the same way adoption does (`_lineage_children`, `flow.py:770-788`)". That function is the silent, unfiltered reader. The brief needs to pick one: either a quiet transitive walk over `split.read_lineage` + `_lineage_children` (walking through children terminal on a split per `_is_split_parent`), or a refactor of `_adoptable` that separates its reporting from its selection. That refactor would be a second change and should be scoped as one.
- [ ] **"Offered" is not defined, and the choice changes which edges stop being refused up front.** Should every id in the seeds' lineage records count as resolvable, or only those `_adoptable` would actually take? Take the raw-lineage reading. Then a named `D` that depends on a seed child that is already DISCONTINUED or RESOLVED, unbriefed, outside the bundle root, or `_PLAIN_ID`-invalid stops being refused before any work. It becomes a later skip or hold instead. That relaxes the very contract the brief says it keeps ("an edge to anything else unresolvable still refuses before any work"). The success criterion only pins a dep on an id that is *not* among the lineage children. Add a criterion case: `D` depends on a lineage child that is already terminal-not-COMPLETE, with the expected outcome stated (refused rc 2 up front, or held). Otherwise the boundary is unfalsifiable.
- [ ] **The "not taken" invariant names a mechanism the code doesn't use on one path, and no test pins it.** The Invariant and Scope say that a dependency adoption does not take "is held by the tolerant re-level … (`flow._reschedule`, `flow.py:1251-1270`)". But `_reschedule` runs only `if adopted:` (`flow.py:1454-1457`). Suppose `C` is the seed's only adoptable child and it is refused, because it is claimed by another run (`_refused_child`, `:1440`) or fails `_admit` (`:1442`). Then nothing is re-levelled. `D` stays in the strict wave list without the edge, and `_runnable` skips it at its wave (`flow.py:705-716`, "skipped — prerequisite(s) not ready"). That is a different report shape from `_report_held`. It doesn't raise, so the safety claim holds, but the brief describes the wrong mechanism. More importantly, the success criterion has no case for "the edge is accepted up front, then adoption does not take `C`". That is the riskiest new path the fix opens. Add at least one criterion case, e.g. `C` claimed by a fake concurrent run, or the record lists `C` but `C` has no brief. State the expected rc and stderr shape, and require "no traceback".
- [ ] **`Stacks on` is in the strict check but the brief doesn't mention it.** `check_dep_graph` checks `Stacks on` against the active bundle (`waves.py:80, 86-91`), because a stacked dependent bases its PR on the parent's live published branch. The brief only discusses `Depends on`. If `D` declares `Stacks on: C`, where `C` is a seed child, does the fix accept it too? The `--no-publish` criterion can't exercise a stack base. Either scope `Stacks on` out explicitly, or state the expected behaviour.
- [ ] **Two files means changing a shared signature that other callers use; say how it stays narrow.** Difficulty says the change touches `waves.check_dep_graph` / `compute_waves`, "whose strictness is shared with `partition_schedulable`'s callers" and with `pdca waves`. Adding an `offered`/`also_resolvable` parameter is fine if it defaults to empty. The brief should say so, and should require the existing callers (`_reschedule`'s `compute_waves`, `flow.py:1267`; `pdca waves`) to stay unchanged. Otherwise Do may widen the relaxation to every entry point, which goes beyond the one-fix scope. A smaller option would keep `waves.py` untouched and pass the offered names in as a pseudo-batch. The brief should say which design it wants, so review isn't left to settle it.
- [ ] (minor) — **The criterion pins wave shape via "an earlier wave", but the brief doesn't name the expected `waves_driven`.** The fixture records `self.waves_driven`, and existing tests assert exact lists (e.g. `test_flow_adopt_recovery.py:444`). For `pdca flow 500 810` with `810 Depends on: 602` and `602 Depends on: 601`, the expected list is `[["issue_601"], ["issue_602"], ["issue_810"]]`. Stating that makes the green check exact rather than a judgement call.

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
- Iteration delta (if iterating): The fix is sound (no defect found, all gates green), but three behaviours it touches have no test in the patch. Keep the production change as is and add these cases to template/tests/test_flow_adopt_recovery.py (AdoptRecovery, through cli._flow, --no-publish): 1. Dependency loop through an offered seed child (e.g. 810 Depends on: 602, 602 Depends on: 810, with 500 split into 601/602). Pre-patch this was refused up front with rc 2; post-patch it passes the strict check and the tolerant re-level holds both. Pin the current behaviour: no traceback, neither 602 nor 810 driven, both still PLANNED, stderr names the held ids. This is a deliberate behaviour change and needs a test. 2. `Stacks on: <seed child>` stays refused up front: rc 2, nothing driven (include a mixed Depends on + Stacks on declaration). 3. `Depends on (merged): <seed child>` resolves like `Depends on`: waves_driven == [["issue_601"], ["issue_602"], ["issue_810"]]. The reviewer already confirmed 2 and 3 by hand (reviewer-boundaries.log); they only need to be committed as tests.
- By / date: Eduard Ralph / 2026-10-04

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 6 finding(s); brief revised: yes (plan-advisory-*.md)
- (empty is the common case)
