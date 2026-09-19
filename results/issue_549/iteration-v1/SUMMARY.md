# Result — issue 549 / csv-batch-plan-reap-rereads-the-briefs-it-wrote

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: On the CSV/default batch-Plan path the session-end contract check never re-reads
  a brief. `do_plan_batch` registers no bundle set there, because the planner picks its ids
  mid-session (`template/src/pdca_harness/leaves.py:1195-1205`: `seeded = []` when
  `ids is None`). So `handoff.stop_problems` falls to its no-registered-bundles tail
  (`template/src/pdca_harness/handoff.py:622-625`): if any `/handoff` passed, it returns with
  nothing about the briefs. A session that runs `/handoff issue_7` and then writes
  `issue_8/brief.md` with an empty **Success criterion** (or empty `Slug` /
  `Repo + branch target`) ends with nothing reported. Nothing later catches those three empty
  fields. `state.py` only treats an unfilled template copy as UNPLANNED, and `plan_policy`
  checks size and dependencies only. So the empty criterion reaches Do (no stated end result)
  and Check (SUMMARY §1 is assembled from the empty field). The id-seeded path is not
  affected: its bundles are registered and each brief is re-read (`handoff.py:609-621`).
- Success criterion: With the patch, a `planner` session opened through `handoff.session`
  with **no registered bundles** reports at reap, bundle-prefixed and report-only, every
  `check_planner` problem in every `issue_*/brief.md` under `cfg.bundle_root` that the session
  **created or changed** (its content differs from session start, or it did not exist then).
  This holds whether or not a `/handoff` passed during the session. Concretely:
  (i) the issue's case: `/handoff` recorded for `issue_7` (discharged brief), then
  `issue_8/brief.md` written with an empty Success criterion → the reap prints
  `issue_8: brief.md field 'success criterion' is empty …`;
  (ii) a brief that existed before the session and is **byte-unchanged** is not re-read (even
  if malformed). It is not this session's work, which matches the
  `_brief_snapshot`/`_fresh_plan_briefs` "new or rewritten" rule the plan-advisory pass
  already uses (`leaves.py:3640-3669`);
  (iii) a session that changed no brief keeps today's behavior exactly: a passed `/handoff`
  ⇒ nothing about the session; no pass ⇒ the existing "registered no bundle set at spawn and
  verified none" item;
  (iv) when it changed briefs and all of them pass `check_planner`, nothing is reported for
  them and no "verified none" item is added, even without a `/handoff`. This is the rule the
  registered path already follows (`stop_problems` docstring, `handoff.py:579-584`: "a
  session that discharged them without ever typing `/handoff` is discharged too");
  (v) the unreadable-`[[doctor.checks]]`-table rule still holds. It is one item for the
  session, and the re-read briefs are then checked with `dependencies=False`, as for
  registered bundles (`handoff.py:606-614`). A brief whose check raises is its own
  `could not check (…)` item and never hides the others (`:615-620`).
  (vi) the registered paths (single Plan, id-seeded batch, sign-off, publish) and the `act`
  role are unchanged, and nothing in the reap writes, moves or deletes a file under the
  project root. Shown by the named test going red on the base (criterion (i) prints nothing
  about `issue_8`) and green with the fix, with every existing test in that module still
  green (including `test_a_broken_doctor_table_is_reported_at_every_planner_reap`,
  `:623-656`, whose "CSV batch" subtests pre-write their brief **before** the session, so
  criterion (ii) keeps them at their current item count).
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here re-verified against it)
- Scope (one logical fix) / out of scope: Remove the gap where an unregistered planner session's written briefs are never
  re-read at reap. The work set is derived by `handoff.py` itself from the bundle root at
  session start versus reap, so no caller changes (`do_plan_batch` and the `/handoff`
  command are untouched). Update the text that promises the old behavior: the `handoff.py`
  module docstring (`:13-18`), `report_at_reap` (`:483-487`), `stop_problems` (`:586-588`),
  and `docs/01-render-and-integrate.md:181-184` ("…and does not re-read what that session
  wrote"). / out of scope: the `act` role's no-bundles rule (it has no brief to re-read);
  the id-seeded path's `allow_absent` wrinkle; a brief deleted during the session; the
  `[[doctor.checks]]` read itself (#558) and the dependency-clause exception handling
  (#559); `leaves.py` (including `_brief_snapshot` / `_fresh_plan_briefs`: do not import
  `leaves` into `handoff.py`, which is kept import-light for the hook, `handoff.py:120`, `:392`); the
  `/handoff` command and `run_check`; making the reap blocking.

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

Review issue #549: make CSV/default batch Plan reap re-check briefs created or changed during the session, while preserving registered-session behavior and report-only semantics.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable outcomes for changed, unchanged, valid and malformed briefs, including per-bundle error isolation and unchanged registered paths; brief.md:18 and brief.md:37. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the production fix leaves two of 33 tests failing, including the missing issue_8 report after another handoff; target/template/tests/test_handoff_reap.py:380; review-verification.log:5. |
| C3 Change | FAIL | One unreadable brief aborts discovery before per-bundle exception isolation, hiding every other malformed brief in that session; target/template/src/pdca_harness/handoff.py:315 and :680; review-edge-cases.log:1. |
| C4 Verification (red→green) | PASS | Independently restored the production patch and reproduced all 33 reap tests passing after the two expected pre-fix failures; this verifies the supplied regression cases, not the additional failures below; target/template/tests/test_handoff_reap.py:395; review-verification.log. |
| C5 Causal adequacy | PASS | Discovering the session's changed briefs addresses the missing work-set cause directly; the patch introduces no capability probe masking a load-time cause, and tests call the real session/reap path; target/template/src/pdca_harness/handoff.py:680; target/template/tests/test_handoff_reap.py:173. |
| T1 Structure | PASS | The change stays in the existing contract module, tests and documentation and introduces no dependency on leaves; driver-owned baseline state remains authoritative; target/template/src/pdca_harness/handoff.py:506. |
| T2 Shape | PASS | Independently ran documentation lint, the 22-page site render/link audit and git diff --check successfully; these match the host workflow commands at target/.github/workflows/docs-check.yml:33; frozen evidence also passes at gate-logs/T2-docs.log:10 and gate-logs/host-ci-docs.log:10. |
| T3 Runtime | FAIL | A registered planner now loses its exit contract when an unrelated old brief is unreadable: independently reproduced registration/reporting on base and registration failure after the patch; target/template/src/pdca_harness/handoff.py:473; review-registered-regression.log:1. |
| T4 Contribution | N/A | Contribution artifacts are absent by design; the substantive contribution audit must run at publish, as the deferred gate explicitly records; gate-logs/T4-contribution.log:10. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path merged-history and closed/rejected-work prior-art check — the brief records it, but this target contains only a synthetic base commit, no remotes and no independently inspectable closed-work evidence; brief.md:117. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the session-start content-difference boundary and report-only outcome meet the intended batch-Plan workflow, with the two demonstrated error-handling gaps considered explicitly; brief.md:18; target/docs/01-render-and-integrate.md:179. |

Findings (advisory; no accept gate is imposed):

1. **P2 — Isolate discovery errors per brief.** At `target/template/src/pdca_harness/handoff.py:315`, `_brief_sha` reads bytes without per-bundle error handling. `_changed_plan_briefs` completes before the protected checks at line 684, so a read failure escapes to the whole-session handler. I opened an unregistered planner session, created `issue_7/brief.md` and made it unreadable with mode `000`, then created `issue_8/brief.md` with an empty success criterion. Reap printed only `could not check the planner session's exit contract … no contract item was reported`; the required issue_8 diagnostic disappeared (`review-edge-cases.log:1`). Preserve the failing bundle's diagnostic and continue discovering/checking the other bundles. This violates criterion (v), not merely an untested hypothetical.

2. **P2 — Restrict the new snapshot to unregistered planner sessions.** At `target/template/src/pdca_harness/handoff.py:473`, the new snapshot runs for every planner, even when the driver registered a bundle set. A pre-existing unreadable `issue_7/brief.md` therefore disables a session registered only for issue_8. I reran this exact fixture with the production patch stashed and restored: base registered successfully and reported issue_8's empty criterion; patched code yielded an empty environment and said the exit contract was unchecked (`review-registered-regression.log:1`). Snapshot only when needed and prevent unrelated snapshot failures from disabling existing registered contracts. This violates criterion (vi).

Independent evidence and limits:

- The production-only stash/pop left the added regression tests in place. Base: 33 tests, two expected failures. Patched: 33 tests, all pass. The original three-file patch was restored; no target source edits were made.
- Full offline driver suite: 1,925 tests pass, two skips (`review-driver-suite.log`). Additional probes confirmed rewritten briefs are checked, a broken doctor table yields one session item plus brief errors, invalid UTF-8 in one brief does not hide another, and scratch-state baseline tampering does not bypass checking (`review-edge-cases.log:7`). The permission-error probes use real filesystem permissions, not mocked read failures.
- The local root-suite rerun exited 77 because this interpreter cannot import copier (`review-root-suite.log:6`). This is a local toolchain caveat, not a patch defect or an unmet fix dependency: the frozen gate log records 24 root tests passing, including real render/update cases (`gate-logs/T3-suite.log:38`, `gate-logs/T3-suite.log:54`), plus the full driver suite. Instance-scoped wrapper scripts were adjudicated from their supplied logs; their absence from the target is expected.
- The C5 scanner's frozen output only says no new test file was added (`gate-logs/C5-prod-path.log:10`); production-path coverage was independently established by the session-based tests and production-only red→green rerun.
- Prior-art investigation was run by all three affected paths using `git -C target log --oneline --all -- template/src/pdca_harness/handoff.py template/tests/test_handoff_reap.py docs/01-render-and-integrate.md`. Its only result was `17fb57d pre-fix base 70ea12b0e60f6cea4c604a0c2777240760ba11f3`; `git -C target remote -v` returned nothing. This cannot independently establish the brief's claimed merged/closed-work search. The supplied integration template has no enumerated project-specific human-only items (`target/template/docs/INTEGRATION.md.jinja:80`); no rendered instance integration file was supplied.

### Advisory — code-review

# Advisory code review — issue #549

Scope: correctness bugs the patch introduces, plus reuse/simplification/efficiency. Both lenses cover the diff only (`handoff.py`, `docs/01-render-and-integrate.md`, `test_handoff_reap.py`).

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/handoff.py:473-479`: `session()` now hashes every `issue_*/brief.md` under `cfg.bundle_root` for *every* planner session, not just the CSV/default batch (unregistered) path this issue is about. The snapshot is only ever read by `_changed_plan_briefs`, which `stop_problems` calls solely in the `bundles` (`= state.get("bundles")`) empty branch (`handoff.py:675`, reached only after the `if bundles: ... return out` branch at `handoff.py:668-674` has already returned). So for a single Plan (`do_plan`) or an id-seeded batch Plan — both of which register a non-empty `bundles` list — this baseline is computed and then discarded every time. It's a full directory walk + SHA-256 of every brief in the bundle root, paid on the common single-issue Plan path even though the fix's own scope is the CSV/default (no-bundle-set) path. A cheap fix: gate the `elif role == "planner":` branch on `bundles` being empty/`None` (the same condition `stop_problems` already uses to decide whether to call `_changed_plan_briefs`).

- `template/src/pdca_harness/handoff.py:444-449` (docstring): says the snapshot "mirrors `leaves._brief_snapshot`," but it doesn't — `_brief_snapshot` (`leaves.py:3640-3649`) excludes placeholder briefs from the "before" picture, while the new baseline hashes every `issue_*/brief.md` regardless of placeholder status. That's actually the *right* call here (a literal mirror would make an untouched, pre-existing placeholder brief look "changed" at reap and wrongly flag it via `check_planner`'s placeholder message, contradicting success criterion (ii)'s "byte-unchanged … not re-read, even if malformed"), and `_changed_plan_briefs`'s own docstring (`handoff.py:301-310`) states the real rule correctly ("mirrors … the 'new or rewritten' rule … matched, not imported … even if malformed"). Just the `session()` docstring's "mirrors `leaves._brief_snapshot`" phrasing overclaims equivalence with a function it deliberately doesn't replicate. Low severity, wording only.

## Not flagged (checked, found sound)

- `_changed_plan_briefs` (`handoff.py:301-317`) is a correct content-hash diff against the driver-captured `state["baseline"]` (never the leaf-writable scratch file — `session()`'s `finally` block at `handoff.py:505-506` re-merges `registered` over whatever the leaf wrote, so a session can't blank its own baseline). Verified against the four required success criteria and the C4 log (`gate-logs/C4-verify.log`): 2 of the 4 new tests go genuinely red with the production hunks reverted and green with them applied; the other two (criteria (ii)/(iii), unchanged-brief cases) correctly don't need to flip since they pin pre-existing behavior.
- No resource leaks, no exception-safety gaps: the new `try/except Exception` around `check_bundle` in the new branch matches the existing pattern for registered bundles (`handoff.py:668-674`) — one bundle's check failure doesn't hide the rest.
- Test additions actually exercise the new code path through the public `handoff.session`/`stop_problems` surface (no internal monkeypatching), matching C5's expectation for an append to an existing test file.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm the affected-path merged-history and closed/rejected-work prior-art check — the brief records it, but this target contains only a synthetic base commit, no remotes and no independently inspectable closed-work evidence; brief.md:117.
- [ ] Validation — fitness-to-purpose — Decide whether the session-start content-difference boundary and report-only outcome meet the intended batch-Plan workflow, with the two demonstrated error-handling gaps considered explicitly; brief.md:18; target/docs/01-render-and-integrate.md:179.
- [ ] `template/src/pdca_harness/handoff.py:473-479`: `session()` now hashes every `issue_*/brief.md` under `cfg.bundle_root` for *every* planner session, not just the CSV/default batch (unregistered) path this issue is about. The snapshot is only ever read by `_changed_plan_briefs`, which `stop_problems` calls solely in the `bundles` (`= state.get("bundles")`) empty branch (`handoff.py:675`, reached only after the `if bundles: ... return out` branch at `handoff.py:668-674` has already returned). So for a single Plan (`do_plan`) or an id-seeded batch Plan — both of which register a non-empty `bundles` list — this baseline is computed and then discarded every time. It's a full directory walk + SHA-256 of every brief in the bundle root, paid on the common single-issue Plan path even though the fix's own scope is the CSV/default (no-bundle-set) path. A cheap fix: gate the `elif role == "planner":` branch on `bundles` being empty/`None` (the same condition `stop_problems` already uses to decide whether to call `_changed_plan_briefs`).

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
- Iteration delta (if iterating): Approach and tests are right; fix the two error-handling gaps the reviewer showed, both inside this brief's scope: 1. Take the session-start brief snapshot in handoff.session() ONLY when no bundle set is registered (planner with bundles empty/None). Today it runs for every planner session, so one unreadable old brief anywhere under the bundle root makes setup raise OSError and a registered single/id-seeded Plan loses its exit contract entirely — breaks criterion (vi). It is also wasted work on those paths. 2. Make brief discovery tolerate per-brief read errors (_brief_sha / _changed_plan_briefs, handoff.py:315). One unreadable brief must become its own "<bundle>: could not check (…)" item, and every other changed brief must still be checked and reported — criterion (v). Today the read raises before the per-bundle try/except and hides the others. Add tests for both: (a) a registered planner session with an unrelated unreadable brief still reports its own bundle's empty criterion; (b) an unregistered session with one unreadable brief plus one empty-criterion brief reports both. Also fix the session() docstring: it claims to "mirror leaves._brief_snapshot" but deliberately does not exclude placeholders — say what it actually does.
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
