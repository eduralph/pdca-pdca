# Result — issue 474 / base-export-reaches-only-the-per-fix-verifier

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The per-fix base export is broadcast to **every** gate row of a Check run, not
  only to the row that consumes it. `gates._run_one` sets exactly one of `PDCA_BASE` /
  `PDCA_VERIFY_BASE` / `PDCA_BRIEF_BASE` whenever `bundle is not None`
  (`template/src/pdca_harness/gates.py:525-536`), and `gates.run_gates` passes `bundle=d` for
  **both** scopes (`:197` — `scopes=("repo", "bundle")`). So a repo-scoped whole-suite row, a
  docs-lint row, the T4 contribution row and a C5 lens all run with a bundle-scoped base in
  their environment; `_merged_env` then merges it into the subprocess, and any env-sensitive
  suite in the target reads it as though the driver had set it for *them*.
  Observed on this instance: T3 went red **exactly and only** on the two stacked bundles of a
  37-cycle corpus (issue_419, issue_457) — `results/issue_457/gate-logs/T3-suite.log`, 11
  failures, all `test_verify_base.VerifyBaseExport`, all
  `AssertionError: 'origin/pdca-integration/main' != 'UNSET'`, with the root suite green in the
  same run; the reviewer reproduced it only with `PDCA_VERIFY_BASE` in the ambient environment
  (`results/issue_457/SUMMARY.md` §5). It is very likely also (part of) the recurring
  "unclassifiable T3 driver-suite red" that instance chased across the 2026-08-05/06 Act
  reviews — unreproducible by hand, because a hand rerun exports nothing.
  **Correction to the issue text, verified on the target base:** the issue names two layers.
  Layer 2 (`VerifyBaseExport` was not hermetic against an ambient base) **has since landed** —
  `setUp` now snapshots the environment and pops all three vars
  (`template/tests/test_verify_base.py:91-103`, `_BASE_VARS` at `:42`), in commit `96c9704`.
  So the *observed* red no longer reproduces through that particular suite. Layer 1 — the
  driver broadcasting a bundle-scoped base to rows that never asked for it — is untouched, is
  the half the issue says must be fixed regardless ("fixing only (2) still leaves repo-scoped
  gates of any instance running with a bundle-scoped base in their environment"), and is this
  slice. Note also that the leak is **not** specific to stacked bundles: rung 3
  (`PDCA_BRIEF_BASE`, `:534-536`) is exported on *every* ordinary cycle, so a fix that only
  suppressed the stacked export would guard the symptom that happened to be observed.
- Success criterion: With the patch, in a bundle-scoped gate run (`gates.run_gates`) for a
  bundle in **any** of the three base postures — an `Onto branch` brief, a stacked bundle with a
  stack-base marker, and an ordinary wave-0 bundle:
  (i) the gate command of a row that is **not** the per-fix verifier observes **none** of
  `PDCA_BASE` / `PDCA_VERIFY_BASE` / `PDCA_BRIEF_BASE` — repo-scoped rows and bundle-scoped
  non-verifier rows alike;
  (ii) the per-fix verifier row still receives **exactly one**, resolved by today's unchanged
  ladder (`Onto branch` > wave integration base > brief base), with the same fully-qualified
  `<remote>/<branch>` value it gets today;
  (iii) an instance whose C4 row predates this change does **not** silently lose its base — the
  compatibility rule is explicit, documented, and asserted by a case of its own;
  (iv) nothing else about the gate environment changes: `PDCA_BUNDLE`, `PDCA_WORKTREE` and
  `PDCA_LANE` are still exported to every row, and `host_ci` rows keep the environment they have
  today.
  Demonstrable by C4-verify: `template/tests/test_verify_base.py` already runs `gates.run_gates`
  against a stub config whose gate row echoes all three variables into a file
  (`_ECHO_BASES`, `:45-51`; `_recorded_bases`, `:115-121`), so (i)-(iv) are assertions over
  what the subprocess actually saw.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: `gates._run_one`'s base export: deliver the ladder's one resolved value to the
  per-fix verifier row and to nothing else, and make how a row is recognised as that verifier
  **explicit and declared** rather than inferred from scope (this instance's own T3 row is
  bundle-scoped, so scope alone does not separate them). Ship the compatibility rule with it:
  a rendered instance that has not re-declared its C4 row must not silently lose the base — a
  silent loss would reverse the guarantee of #54/#273/#387 (the test base and the deploy base
  must not diverge) and would be far worse than the leak. Document the row-level contract where
  `[[gates.checks]]` keys are documented (`template/pdca.toml.jinja`'s `[gates]` block) and in
  the C4 skeleton's ladder comment if that file's asserted wording permits (see Falsifiability).
  Do decides the declaration's shape and states the compatibility rule in `build-notes.md`; it
  is the human's call at sign-off. **Out of scope:** `template/tests/test_verify_base.py`'s
  hermeticity (already fixed, `:91-103`) and any other suite's env handling; `PDCA_BUNDLE` /
  `PDCA_WORKTREE` / `PDCA_LANE`, which every row legitimately needs; the worktree
  reconstruction (`worktree.for_gate`, `gates.py:369`) — it already resolves the base itself and
  must keep doing so; `host_ci` rows; the publish-time gate re-run; this instance's own
  `pdca.toml` and `engine/scripts/*` (a different repo — `docs/INTEGRATION.md` §2 keeps instance
  changes outside the cycle).

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

Reviewing issue #474: restrict the per-fix base export to verifier rows without changing host-CI or other gate context.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The verifier-only ladder, explicit override, and legacy `tier == "C4"` fallback are concrete enough to judge, while the existing call structure makes the separate host-CI constraint identifiable (`template/src/pdca_harness/gates.py:473`, `template/pdca.toml.jinja:912`). |
| C2 Reproduction (red pre-fix) | PASS | With only the production hunk stashed and the new tests retained, 3 of 27 tests failed on the expected leaked `origin/main` values, grounding the defect in the subprocess-observation assertions (`template/tests/test_verify_base.py:348`, `template/tests/test_verify_base.py:363`, `template/tests/test_verify_base.py:401`). |
| C3 Change | FAIL | The shared `_run_one` is also used for `cfg.host_ci_checks`, so the new predicate changes an explicitly out-of-scope host-CI environment; a direct base-versus-patch probe changed a T2 host-CI row from `UNSET/UNSET/origin/main` to `UNSET/UNSET/UNSET` (`template/src/pdca_harness/gates.py:425`, `template/src/pdca_harness/gates.py:554`). |
| C4 Verification (red→green) | FAIL | The 27-test red→green is genuine, but every new case exercises `gates_checks`, not `host_ci_checks`; the omitted criterion is observably regressed despite the configured C4 green (`template/tests/test_verify_base.py:342`, `template/src/pdca_harness/gates.py:425`). |
| C5 Causal adequacy | FAIL | The causal boundary must distinguish ordinary configured gates from host-CI rows—placing the filter in their shared execution sink over-corrects excluded callers and changes compatibility outside the defect (`template/src/pdca_harness/gates.py:396`, `template/src/pdca_harness/gates.py:425`). |
| T1 Structure | FAIL | `_verifies_base(chk)` has no row-origin context, so its placement cannot preserve the separately routed host-CI contract; the selection needs a boundary that knows which collection supplied the row (`template/src/pdca_harness/gates.py:473`, `template/src/pdca_harness/gates.py:425`). |
| T2 Shape | PASS | Independent documentation lint and 22-page render/link audit both passed, and `git diff --check` reported no whitespace errors; the published configuration contract is located with the C4 row (`template/pdca.toml.jinja:908`). |
| T3 Runtime | PASS | The restored focused module passed all 27 tests and the full offline driver suite exited 0; the executable assertions cover non-verifier suppression plus explicit opt-in/opt-out (`template/tests/test_verify_base.py:330`, `template/tests/test_verify_base.py:377`). |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check, and `gate-logs/T4-contribution.log` says the mandatory substantive contribution audit re-runs at publish. |
| T5 Judgment | FAIL | Merged and closed PR history was checked by all four affected paths (with no closed-unmerged or open competing attempt), but the confirmed host-CI scope regression must be corrected before this change is fit for sign-off (`template/src/pdca_harness/gates.py:425`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Maintainers must confirm the corrected host-CI compatibility behavior and the implicit `tier == "C4"` fallback against real instance configurations—custom gate scripts may depend on the legacy environment, so automated stub coverage alone cannot approve that compatibility decision (`template/src/pdca_harness/gates.py:487`). |

### Advisory — code-review

# Check — advisory code review (issue #474)

Second lens: correctness bugs the patch introduces, and reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET`'s `template/src/pdca_harness/gates.py`,
`template/tests/test_verify_base.py`, `template/pdca.toml.jinja`,
`template/engine/scripts/run-verify.sh` as patched.

## Correctness

No bugs found. Specifically checked and clean:

- `_verifies_base` (`template/src/pdca_harness/gates.py:473-495`) is a straightforward
  `chk.get("verifies_base", chk.get("tier") == "C4")` — the same "explicit key overrides a
  field-derived default, both directions" shape already used by `publish.publish_gates`'s
  `at_publish` resolution (`template/src/pdca_harness/publish.py:778`), which the docstring
  cites accurately. No off-by-one, no mutation of `chk`, no exception path.
- The gate site (`gates.py:554`, `if bundle is not None and _verifies_base(chk):`) is the
  only call site that matters — `_run_one` is reused unchanged for repo-scoped rows,
  bundle-scoped non-verifier rows, and the `host_ci_checks` loop (`gates.py:412-428`), so the
  fix closes the leak for all three without new branches per caller. Verified the `host_ci`
  loop *also* stops leaking the base to a typically non-`"C4"`-tiered row as a side effect,
  consistent with the brief's "a docs-lint row" example — not a scope violation since the
  brief only lists `host_ci` rows as "must keep doing so [resolving worktree]", not "must
  keep receiving the base".
- Backward compatibility (brief iii) is real: `chk.get("tier")` on a row with no `tier` key
  returns `None`, `None == "C4"` is `False`, so an untagged/mistagged row correctly loses the
  export, while an unmigrated `tier = "C4"` row (no `verifies_base` key at all) still gets
  `chk.get("verifies_base", True)` → `True`. Matches `test_a_predating_c4_row_keeps_its_base_with_no_config_edit`.
- Confirmed against `gate-logs/C4-verify.log`: the red leg (production reverted) fails
  exactly the three new falsifiability/invariant cases
  (`test_only_the_verifier_row_receives_the_ladder`,
  `test_the_unconditional_brief_base_rung_also_stays_off_non_verifier_rows`,
  `test_a_c4_row_can_opt_out_explicitly`) and none of the others — the two "still receives"
  cases (`test_an_explicitly_declared_non_c4_verifier_still_receives_the_base`,
  `test_a_predating_c4_row_keeps_its_base_with_no_config_edit`) correctly stay green on both
  legs, since unpatched `gates.py` already exported the base to every bundle-scoped row. The
  red leg is a genuine, targeted regression test of the introduced logic, not an
  import/collection failure dressed up as red.
- `run-verify.sh` and `pdca.toml.jinja` hunks are comments/docs only (no behavioural change),
  correctly kept in the same patch per the brief's "gate-evaluability trap" note about
  `test_verify_base.py`'s skeleton-wording string-match — `test_the_c4_skeleton_names_the_export_as_the_last_rung`
  (`template/tests/test_verify_base.py:403-…`) still passes because the ladder-resolution
  sentence at `run-verify.sh:36` (`Resolve as: $PDCA_BASE > $PDCA_VERIFY_BASE > your own
  override > $PDCA_BRIEF_BASE`) was left untouched; only surrounding prose changed.

One non-blocking observation, not a bug: `_verifies_base` has no scope guard — a row
explicitly declared `verifies_base = true` (or tagged `tier = "C4"`) while also
`scope = "repo"` would still receive the per-bundle base (`gates.py:554` only tests
`bundle is not None`, which is true for repo-scoped rows too inside `run_gates`'s
`scopes=("repo","bundle")`). This is consistent with the brief's explicit instruction to
make verifier-recognition "explicit and declared **rather than inferred from scope**", so
scope-independence looks intentional rather than an oversight, and every shipped example
places the verifier at `scope = "bundle"` by convention. Flagging only for completeness —
not escalating.

## Reuse / simplification / efficiency

- `_verifies_base` mirrors (but does not literally duplicate) the "declared key overrides a
  field-derived default" idiom `publish.publish_gates` already uses for `at_publish`. The two
  are one-liners in different modules serving different call sites (gate-env export vs.
  publish-time re-run selection); extracting a shared `_declared_or(chk, key, default)` helper
  would save one line and buy an extra layer of indirection for a two-occurrence idiom — not
  worth it here.
- No needless work added to the gate hot path: `_verifies_base` is a single dict lookup,
  called once per row per `_run_one` invocation, same order of work as the `gating`/`label`
  lookups already there.

## Verdict

Diff is clean on both lenses. No NEEDS-HUMAN items.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Maintainers must confirm the corrected host-CI compatibility behavior and the implicit `tier == "C4"` fallback against real instance configurations—custom gate scripts may depend on the legacy environment, so automated stub coverage alone cannot approve that compatibility decision (`template/src/pdca_harness/gates.py:487`).
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
