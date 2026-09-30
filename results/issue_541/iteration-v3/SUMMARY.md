# Result — issue 541 / no-dead-attempts-artifact-harvested-as-a-live-ones

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: With the patch applied on top of child-1's accepted result:
  1. **No artifact written by a dead attempt is copied out as a successful attempt's
     output**, at **all three** harvest sites — not two of three.
  2. **A dead attempt's text is preserved** in the bundle's `*.error.log` rather than merely
     deleted: a real verdict must not be destroyed while the operator is told none was
     produced.
  3. **The live attempt's own artifact is harvested exactly as today**, and a leaf that exits
     0 having written nothing still degrades to today's placeholder.
  4. **The leaf-status label tells the truth** for every run it can now classify: a run whose
     last attempt exited 0 must not be labelled "leaf did not run".
  5. **DECIDED HERE, not left to Do — the retry contract is NOT narrowed**, the same ruling
     child-1 makes for the record flush. On a residue that cannot be withdrawn, **carry the
     un-owned state forward and refuse to HARVEST on the success branch** (the residue is
     already quoted by then) rather than ending the run. This is the v5 sign-off's own
     no-cost alternative, quoted verbatim as an instruction: v5 measured the fail-closed
     variant at base-3-attempts → patch-1 on a bundle write refusal and 2 → 1 on an unlink
     refusal, while its criterion demanded the contract "hold unchanged" — the builder was
     asked to satisfy both and could not. `test_leaf_resilience.py:62` (`_runs() == 3`) is
     the mechanical check.
  6. **The three harvest sites end up sharing one implementation, not three copies.** This is
     the point of the child: the v5 code-review advisory flagged the de-duplication as a
     legitimate Act candidate and round 3 refused it on the express grounds that "this patch
     is already oversized" — that refusal *is* the loop, and this child exists to break it.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: Fixed
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

Task under review: prevent artifacts left by dead retry attempts from being harvested as successful reviewer, advisory, or plan-advisory output while preserving retry behavior and truthful status reporting.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is concrete and testable across the three identified consumers, whose shared-path requirement maps to the reviewer, advisory, and plan-advisory call sites at `template/src/pdca_harness/leaves.py:2927`, `template/src/pdca_harness/leaves.py:3283`, and `template/src/pdca_harness/leaves.py:3586`. |
| C2 Reproduction (red pre-fix) | PASS | The retained test drives all three real entry points and asserts both refusal and preservation at `template/tests/test_attempt_harvest.py:212`; my tracked-only stash run reproduced nine failures and four errors pre-fix. |
| C3 Change | FAIL | A successful retry that only repairs permissions can still harvest the dead attempt's bytes: `st_ctime_ns` participates in identity at `template/src/pdca_harness/leaves.py:1074`, so the lookup misses and treats the path as newly written at `template/src/pdca_harness/leaves.py:962`; a direct `_LeafHarvest.run` probe produced `identity_changed_by_chmod=True` and `harvested_dead=True`. |
| C4 Verification (red→green) | PASS | Independently reproduced 17/17 green, nine failures plus four errors with tracked production changes stashed, then 17/17 green after restore; the frozen gate records the same transition at `gate-logs/C4-verify.log:10` and `gate-logs/C4-verify.log:195`. |
| C5 Causal adequacy | FAIL | The ownership decision must distinguish an artifact write from metadata-only repair; treating any unknown stat tuple as authorship at `template/src/pdca_harness/leaves.py:962` leaves the stated root failure possible even though the covered overwrite cases at `template/tests/test_attempt_harvest.py:303` pass. |
| T1 Structure | PASS | All three harvest sites delegate to the single `_LeafHarvest` implementation defined at `template/src/pdca_harness/leaves.py:809`, with the structural guard at `template/tests/test_attempt_harvest.py:407`. |
| T2 Shape | PASS | `git diff --check` is clean, and the frozen docs/render plus pushed-tree parity audits both report clean results at `gate-logs/T2-docs.log:16` and `gate-logs/host-ci-docs.log:15`. |
| T3 Runtime | PASS | The complete offline driver suite independently passed 1,820 tests with two skips; the frozen runtime evidence reports the same result at `gate-logs/T3-suite.log:1668`, including the real-site tests rooted at `template/tests/test_attempt_harvest.py:184`. |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check, so the substantive contribution audit is owed to the mandatory publish-time rerun, as recorded at `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | The human must sequence dependency #540 before publishing this patch: GitHub shows `main` at `acb214a` while `pdca-integration/main` is two commits ahead at `480fa6b` and contains issue_540, whose contract this code explicitly assumes at `template/src/pdca_harness/leaves.py:713`; affected-path merged history and closed-unmerged PRs were checked, with no competing rejected implementation found. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | The human must decide whether real reviewer leaves may perform metadata-only permission repair and therefore require that action to remain non-owning — otherwise the confirmed path from identity lookup to copy at `template/src/pdca_harness/leaves.py:962` and `template/src/pdca_harness/leaves.py:881` can still file a dead verdict. |

### Advisory — adversary

# Advisory review — adversary (issue #541, round 4)

Re-ran the asserted red→green on the target: green leg reproduces (17/17 OK, no skips,
`PYTHONPATH=src python -m unittest tests.test_attempt_harvest`), and the red-leg log
(`gate-logs/C4-verify.log`) shows 8 distinct tests genuinely red on the base — the C4 claim
itself is honest, and the tests drive the real site entry points (`_run_review_sandboxed`,
`_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`), not a re-implementation. Two
refutations landed anyway.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:962-964`: a dead attempt's
  residue is still filed as the live attempt's verdict when the live attempt only touched
  the file's METADATA. `_live_attempt_took_the_path` returns `True` the moment
  `_residue_identity` moves (`known is None → return True`), and that tuple includes
  `st_mtime_ns`/`st_ctime_ns` — both of which move with no byte changed. Measured, twice,
  through the production entry point (dying attempt writes a truncated verdict then
  `chmod(".", 0o500)` so the withdrawal is refused; the live attempt exits 0 having only run
  `os.utime(art, None)` — and, separately, only `os.chmod(art, 0o600)`): `check-review.md`
  in the bundle is byte-for-byte the dead attempt's text, with no `NOT COMPLETED`
  placeholder and no un-owned refusal. That is criterion 1 failing in exactly the lane the
  refusal exists for, and it contradicts the invariant the code claims for itself at
  `leaves.py:950` ("Only 'the same file, unchanged' is refused") — here the file IS
  unchanged and it is filed. Any leaf or wrapper that normalises timestamps/permissions on
  its outputs (a formatter, `chmod -R`, a `touch`, a copy tool) triggers it. Cheap fix
  inside the existing design: `_residues` already carries the digest, so when the identity
  has moved, cross-check the current `_artifact_digest` against the recorded digests and
  treat a byte-identical match as still-un-owned. (`st_ctime_ns` in the identity tuple is
  net-harmful: it is the only member a pure `chmod` moves.)

- NEEDS-HUMAN — `template/src/pdca_harness/assemble.py:88,95-97`: adding `unowned-empty` to
  `_LEAF_STATUS_LABEL` re-opens, for a RECOGNISED token, the exact demotion the round-2/3
  carry-forwards rejected for unrecognised ones — and it is self-triggering on this very
  bundle. `leaf_status` matches the marker anywhere in the text, so a REAL advisory/review
  artifact that quotes the new placeholder verbatim (any leaf reviewing #541 — this report
  had to mangle the marker to avoid it) has every finding relabelled and forced HUMAN at
  `assemble.py:188-193`. Measured against base with `collect_needs_human` on an artifact
  holding a fenced quote of the marker plus one genuine `[impl]`-marked finding
  ("off-by-one at foo.py:12"): base → `impl`, `autoiterate.eligible` True; patched → `human`, prefixed "leaf
  ran and exited 0, but no artifact could be attributed to it", `eligible` False. So the
  #264 `[impl]` routing is stripped from findings that exist, and the §6 row states
  something false about a leaf that ran fine — a regression against the base caused by this
  diff. The patch's guard (`tests/test_attempt_harvest.py:449`, token `some-future-status`)
  misses it by construction and is green pre-fix, so C4 covers none of it. Flagged for a
  human rather than `[impl]` because the remedy the round-3 carry-forward prescribed ("keep
  '' for an artifact that carries a verdict table / findings") collides with the shipped
  #278 guard `tests/test_leaf_status.py:194`
  (`test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl`), so the choice —
  scope the match to the artifact's own header, drop the new token's label, or accept the
  demotion — is a design call, not an iteration.

- Evidence caveat (no adjudication needed, context for the two above):
  `tests/test_attempt_harvest.py:304,324,340` — the three "a live verdict written over an
  un-withdrawable residue is still filed" legs, i.e. the round-2/3 carry-forward's core
  remedy — are green **pre-fix** as well as post-fix (the base files everything, so no
  over-refusal exists there to go red). That is unavoidable for a guard against a rejected
  patch, but it means the whole identity mechanism (`_residue_identity`, the digest
  fallback) carries no red→green proof, which is how the metadata-touch hole above survived
  into round 4. The `check-gates.json` C4 row ("red without the fix, green with it") is
  true, and is weaker than it reads for the parts of the patch added in this round.

Attempted and could not refute: the retry contract (criterion 5) really is untouched —
`withdraw` never breaks the loop and `_runs() == 3` holds under a locked sandbox; the
residue-de-dup (`_unchanged`, `leaves.py:905-907`) does account for an un-removable residue
exactly once across three deaths; criterion 6 is stronger than claimed — `_LeafHarvest.run`
is now the ONLY caller of `_invoke_leaf_resilient` in the package, so a fourth site cannot
grow its own copy; the preserved account cannot settle a leaf that exited 0
(`_WITHDRAWN_TRAILER` carries no marker, and the residue goes through
`state.neutralize_leaf_text`); no sandbox seeds a file at any site's artifact name
(`REVIEWER_INPUTS`, `PLAN_ADVISORY_INPUTS`, `<sandbox>/target`), so nothing but the leaf can
leave a residue; the forward reference `harvest: _LeafHarvest | None` at `leaves.py:684`
is safe on CI's Python 3.12 (`from __future__ import annotations` at `leaves.py:35`), not
merely on the 3.14 the gates ran; and the residue quote really is bounded head/tail with an
elision line, leaving no `.partial` sibling.

### Advisory — code-review

# Check advisory — code review (correctness + reuse/simplification), issue #541

Scope: this diff only (`template/src/pdca_harness/leaves.py`, `assemble.py`,
`template/tests/test_attempt_harvest.py`), grounded on `$PDCA_TARGET`. Round-3
carry-forward's three named defects (assemble.py header-line hole, digest-only
identity, per-attempt residue re-quoting) were checked against the current
target source, not just the diff text — all three are genuinely closed, not
partially patched around:

- `assemble.py:99-108,188` — the `_LEAF_STATUS_HEADER_LINES` mechanism from the
  prior round is gone outright; `_items_from_artifact` now leaves an artifact
  alone whenever it carries no *recognised* status token, independent of where
  in the file an unknown token appears. Verified no residual
  `_LEAF_STATUS_HEADER_LINES` reference remains anywhere in `assemble.py` or
  the tests.
- `leaves.py:1058-1074` (`_residue_identity`) + `933-966`
  (`_live_attempt_took_the_path`) — ownership is settled by `(st_dev, st_ino,
  st_size, st_mtime_ns, st_ctime_ns)` recorded at withdraw time, with a digest
  fallback only when identity is unchanged; both the unreadable-residue and
  identical-content-rewrite cases are now correctly recognised as live work.
- `leaves.py:883-926` (`withdraw`) — identity is checked *before* any read, so
  a residue already on file in `self._residues` short-circuits to
  `_unchanged` (leaves.py:1015-1020) instead of re-reading/re-hashing and
  re-quoting under a new attempt's name.

Traced every branch of `_LeafHarvest` (`run`, `withdraw`,
`_live_attempt_took_the_path`, `_disown`, `_preserve`) by hand against the
brief's six success criteria and cross-checked against `gate-logs/C4-verify.log`
(13 failures pre-fix on the exact assertions the brief names, 17/17 green
post-fix) and `gate-logs/T3-suite.log` (1820 tests, OK). Independently re-ran
`template/tests/test_attempt_harvest.py` as a non-root user (all 17 tests,
including the 8 `@unittest.skipUnless(_rootless())` permission-dependent legs,
genuinely executed rather than skipped) — all pass.

No correctness bug was found in the patch itself. Two minor, non-blocking
observations, neither rising to a defect against the brief:

- `leaves.py:965` — the digest-comparison fallback inside
  `_live_attempt_took_the_path` (used only when a *new* stat exactly matches a
  previously-recorded residue's `(dev, ino, size, mtime_ns, ctime_ns)` tuple —
  i.e., an in-place rewrite a coarse clock failed to separate) is not exercised
  by any test leg; every legged scenario changes at least one of those five
  fields on a real write. This is a defensive branch for a filesystem/timing
  edge case the test harness cannot reliably construct, not a sign of a wrong
  implementation — the reasoning in the docstring (leaves.py:943-950) is sound
  and the branch is cheap. Not asking for a rebuild over it.
- `leaves.py:1077-1090` (`_artifact_digest`) and `leaves.py:1023-1055`
  (`_read_residue`) both stream-hash a file in chunks but for different
  purposes (unbounded full-file digest for comparison vs. bounded head/tail
  quote-plus-digest for the withdrawn record); there's no pre-existing
  streaming-file-hash helper elsewhere in the module they could have shared
  (checked `act.py`/`handoff.py`'s `sha256` usages — both hash an
  already-in-memory string, not a file). The mild duplication between the two
  functions is justified by their differing bound requirements, not a
  reuse gap worth flagging.

The three harvest sites (`leaves.py:2927-2940`, `3283-3294`, `3586-3596`) are
wired identically through the one `_LeafHarvest` owner, satisfying criterion 6
without any hand-copied logic left behind at any site — confirmed by reading
all three call sites directly, not just the diff hunks.

No NEEDS-HUMAN findings from this lens.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — The human must sequence dependency #540 before publishing this patch: GitHub shows `main` at `acb214a` while `pdca-integration/main` is two commits ahead at `480fa6b` and contains issue_540, whose contract this code explicitly assumes at `template/src/pdca_harness/leaves.py:713`; affected-path merged history and closed-unmerged PRs were checked, with no competing rejected implementation found.
- [x] Validation — fitness-to-purpose — The human must decide whether real reviewer leaves may perform metadata-only permission repair and therefore require that action to remain non-owning — otherwise the confirmed path from identity lookup to copy at `template/src/pdca_harness/leaves.py:962` and `template/src/pdca_harness/leaves.py:881` can still file a dead verdict.
- [x] `template/src/pdca_harness/leaves.py:962-964`: a dead attempt's
- [ ] `template/src/pdca_harness/assemble.py:88,95-97`: adding `unowned-empty` to

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): REPLAN — re-author this ONE brief. Do NOT split: the human ruled at sign-off that this stays a single slice (it is already depth 3 of the #536 split, siblings #540/#537, and does not need deepening again). Return to Plan because the remaining work needs SPECIFYING, not because the slice is too big. WHY PLAN AND NOT A REBUILD: the remaining defect is no longer "tighten a matching rule" but a redesign of the leaf-status mechanism, and three consecutive rounds have shown Do cannot author it from a carry-forward paragraph. Round 2 shipped "match the marker anywhere", holed by a quoted marker. Round 3 shipped an 8-line header window, holed by a fenced block opening at line 5. Round 4 made `unowned-empty` a recognised token, which self-triggers on any artifact that quotes it — including any advisory reviewing this very issue. Each round closed the previous hole and opened a new one in the same mechanism, because each round was given the destination and left to guess the route. The replanned brief must specify the route. WHAT THE REPLANNED BRIEF KEEPS — criteria 1, 2, 3, 5, 6 are MET by the patch in this bundle and must be carried forward as "keep as built", not re-derived. All three lenses confirm it; the code-review lens found no correctness bug at all. Specifically: all three harvest sites share one owner and `_LeafHarvest.run` is the only caller of `_invoke_leaf_resilient`, so a fourth site cannot grow its own copy (criterion 6, stronger than the brief asked); the retry contract is untouched, `_runs() == 3` under a locked sandbox (criterion 5); the residue de-dup accounts for an un-removable residue exactly once across three deaths; the residue quote is head/tail bounded; the red->green is honest through the real entry points and was independently re-reproduced by both advisory lenses. Do not re-open the structure and do not re-slice. WHAT THE REPLANNED BRIEF RE-SPECIFIES — criterion 4 only (the leaf-status label / marker). DESIGN CHOSEN BY THE HUMAN AT SIGN-OFF — this is the intent to specify, not an open question: invert the marker to a POSITIVE COMPLETION signal, written as the LAST LINE of the artifact, and written BY THE LEAF ITSELF. Its presence means the artifact closed successfully; its ABSENCE means something did not close, and those cases get surfaced and worked through one by one. WHY THIS BEATS THE ALTERNATIVES (record the reasoning, do not re-litigate it): - It removes the use/mention collision that has now defeated three implementations. Only the final line is consulted, so a real report may quote the marker anywhere in its body — which is exactly what any advisory reviewing this harness must do — with no effect. - A leaf-written trailer detects TRUNCATION, which is the actual defect class here (a dying attempt leaves a half-written report). A harness-written stamp applied on exit 0 would only re-assert "the process exited cleanly", which the harness already knows, and would still stamp a report whose generation stopped mid-way. QUESTIONS THE REPLAN MUST ANSWER IN THE BRIEF — leaving any of these to Do repeats the loop: 1. Non-cooperating leaves. Leaves are arbitrary external commands, including third-party ones; nothing can compel them to emit a trailer. Model-backed leaves can be INSTRUCTED via their prompt; non-model command leaves cannot. Specify per-leaf-kind behaviour, or a declared capability, so a leaf that cannot stamp is not permanently read as failing. 2. False "incomplete". A model leaf that finishes correctly but omits the trailer reads as a failure. Specify the tolerance — corroborate against the exit code and the ownership signal this bundle's `_LeafHarvest` already computes, rather than trusting the trailer alone. 3. Legacy migration. NO existing artifact in ANY bundle carries the trailer, so on the day this lands the entire back catalogue reads as "did not close successfully" — including every artifact the corpus / size-signal scripts read. Specify the legacy rule ("no trailer AND no recorded failure ⇒ legacy, stay quiet"), or state deliberately that history should flag. The human's "catch them one by one" was said of GOING FORWARD; confirm the scope at Plan. 4. The #278 contract. The existing guard (tests/test_leaf_status.py:194, `test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl`) exists to stop findings being smuggled out of placeholders. An inverted marker must keep that property. 5. All THREE readers, not one. `leaf_status` is read at assemble.py:168, size_signal.py:240 and leaves.py:3057; this bundle's patch only goes near the first. The marker is WRITTEN at exactly one site today (leaves.py:2664, `_unavailable_classification` — the harness's own placeholder generator; no leaf writes it now), so the redesign adds a write site in the leaf path and must convert every reader together. Say so in the brief's scope. DECISIONS ALREADY TAKEN AT SIGN-OFF — carry into the replanned brief, do not re-open: - The metadata-only-touch hole is ACCEPTED and lived with (the reviewer's C3/C5 FAIL; identity at leaves.py:1074 includes st_mtime_ns/st_ctime_ns, so a live attempt that only chmods or utimes an artifact moves the tuple, the ownership lookup misses, and a dead attempt's artifact can still be harvested). The human accepted this knowingly, to see whether it occurs in practice; it is filed as an issue and recorded in SUMMARY §10. Do NOT change `_residue_identity`, do NOT remove `st_ctime_ns`, do NOT add a digest cross-check on a moved identity. If it is ever observed in the wild it returns as its own issue. - The related Validation / fitness-to-purpose question (may real leaves perform metadata-only permission repair) is answered by that same acceptance. - T5 dependency ordering on #540 is CONFIRMED as a publish-time concern, not a patch defect; `stack-base` already reads `pdca-integration/main`, which carries #540. EVIDENCE NOTE FOR THE REPLAN: the round-4 adversary measured the current defect against base on an artifact holding a fenced quote of the `unowned-empty` marker plus one genuine `[impl]` finding — base gave `impl` with autoiterate eligible, patched gave `human`, not eligible, with the finding's #264 routing stripped. The replanned brief must name that shape as a required test leg, and require it to be genuinely RED on the base: the existing guard (tests/test_attempt_harvest.py:449, token `some-future-status`) is green pre-fix and therefore proves nothing. More generally the adversary observed that the whole identity mechanism carries no red->green proof (tests/test_attempt_harvest.py:304,324,340 are green pre-fix as well as post), which is structurally how the round-4 hole survived into a fourth round.
- By / date: Eduard Ralph / 2026-08-16

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Accepted risk (#541 sign-off, items 2+3): a live attempt that touches only an artifact's METADATA (chmod/utime — no byte changed) moves the identity tuple, so the ownership lookup misses and a dead attempt's artifact can still be harvested as the live one's. File an issue and live with it; revisit if it is ever observed in the wild.
