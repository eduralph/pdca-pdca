# Adversarial review: issue_727 (dependency-scoped bases)

Verdict: the red→green evidence holds up, and I could not refute it. For the inputs the brief lists, the fix does what criteria (1)–(7) ask. I found two concrete inputs where a run now ends worse than on `fcae4aa`. One is a gap the builder can fix. The other is a scope call for the human.

## The evidence (attempted, could not refute)

- I re-ran C4 myself on sandbox copies of the target. For the pre-fix copy I took `flow.py` and `integrate.py` from HEAD `fcae4aa`. `tests.test_flow_dependency_scoped_bases` fails 15 of 19 before the fix and passes 19 of 19 after. The 4 that pass before the fix are the four seam tests for (6) (`template/tests/test_flow_dependency_scoped_bases.py:364-423`), which by design assert that behavior is unchanged from `fcae4aa`. The others fail for the right reason. For example, (1) fails at `:266` because `fix/B` holds Z's commits.
- The test runs the production code. `flow._drive_and_act`, `integrate.fold` and `integrate.build_bundle_base` are all real and run against a real git origin. Only `_drive_wave`, `_publish_bundle`, `draft_texts` and `gh` are stubbed. The `_publish_bundle` stub (`:130-159`) cuts the PR branch from the same commit real publish uses (the recorded stack-base tip, `template/src/pdca_harness/publish.py:261-263`). It also records the same `mode` (`publish.py:429`). So it does not hide a difference that `_member_cut_point` would see (`integrate.py:928`).
- Mutation check: I deleted each of the following, one at a time, and each deletion made at least one test fail:
  - the wave guard that drops a member's partner built after it (`flow.py:960`). Last round said nothing tested it. `test_a_members_partner_built_after_it_is_not_on_the_base` now covers it.
  - the finished-bundle seam (`flow.py:955`)
  - the legacy `Stacks on` / `Onto branch` seam (`flow.py:948`)
  - the list of PRs cut from the line (`flow.py:1041`)
  - `bases` in each of the three rewrite checks: `rewritten_carried`, `build_bundle_base` (`integrate.py:827`), and the fold's `_carried_tips` (`integrate.py:519`)
- I tried more closure inputs, and all came out right:
  - Diamond: `D` (`Depends on: B, C`), where B and C both depend on A, and Z is unrelated. D's base holds A, B and C, and no Z.
  - A member's earlier-wave partner: `Y` (`Conflicts with: A`), `D` (`Depends on: Y`). D's base holds A and Y, and no Z.
  - `main` gaining an unrelated commit mid-run is taken into the base without a refusal.

## Findings

- NEEDS-HUMAN [impl] — When a base build stops the run for any reason other than a rewrite, the end-of-run check (#695) is turned off. A rewrite of a branch that is not one of that base's members then goes unreported.
  - **Code path:** the `_bundle_bases` error sets `line_stopped = True` (`template/src/pdca_harness/flow.py:2708`), and that skips `_report_late_rewrites` (`flow.py:2855`). But `build_bundle_base` only checks its own members' heads (`integrate.py:828-833`). A fold is different: its check covers every carried branch before any merge can fail (`integrate.py:519`).
  - **Concrete case (run on both trees):** wave 0 has `A` and `Z` (Z has two commits). Wave 1 has `S` (`Stacks on: Z`, a seam, so built on the line) and `B` (`Depends on: A`). Wave 2 has `C` (`Depends on: B`). After the fold that follows wave 1, `fix/Z` is forced back one commit, and `main` gets a commit that clashes with A's file.
    - On `fcae4aa`: C is built. The run reports `issue_Z's branch origin/fix/Z was rewritten…` and names S's PR, with `holds={'Z': 'rewritten'}`.
    - With the patch: the run stops at C's base because A clashes with main, and Z's rewrite is never mentioned. S's open PR holds a commit that `fix/Z` no longer has, and nothing tells the human.
  - **The test pins this as intended:** `template/tests/test_integrate_carried_rewrite_late.py:215` (`_stopped_at_b`) asserts there is "nothing left for the end of the run to check by hand". That is true in its two-bundle run, where no other PR holds A's head. It is not true in general.
  - **Fix:** either still run the #695 check after a `_bundle_bases` stop (skipping the branch the stop already named), or have the base build check every head in `taken` before it builds anything.

- NEEDS-HUMAN [human] — If the base moves during a run, the whole run can now stop where `fcae4aa` finished it. A bundle's own base starts from `<base_remote>/<base>` as fetched at that moment (`integrate.py:841`), but the line never follows the base (#655).
  - **Concrete case:** wave 0 has `A` and `Z`, and wave 1 has `B` (`Depends on: A`). After the fold that follows wave 0, someone pushes a commit to `main` that touches A's file.
    - On `fcae4aa`: B is built on the line and the run completes.
    - With the patch: the run prints `flow: wave 1 — could not build issue_B's own base from issue_A: issue_A's branch origin/fix/A does not merge cleanly onto origin/main itself … STOPPING — wave 1 and later waves not run.` (`integrate.py:962`, `flow.py:2706`).
  - Every other bundle in wave 1 and later is dropped too, even ones with no tie to A.
  - The brief moves "holds for base-build failures" to #725, but it does not name this trigger, and on a busy repo it is the likely one.
  - You can argue the stop is an early warning, since A's own PR conflicts with main as well. Still, the human should decide what is acceptable until #725 lands: stopping the whole run, holding just B, or building B on the line.

- (Known and already out of scope, so no tag.) An overlap between waves that no edge declares now stops the run at the next fold. Example: `B` (`Depends on: A`) and an unrelated wave-0 `Z` both write `shared.txt`, and a wave 2 follows B. `fcae4aa` completes this run. The patch stops it with `… does not merge cleanly onto pdca-integration/… — an undeclared cross-wave overlap` (`integrate.py:1313`). This is #463's design working as intended: B's base no longer hides the overlap. The brief puts holds for this case in #725. I mention it only so sign-off knows it stops the run rather than holding one bundle.

- Reviewer's verdict: C5 in `check-gates.json` ("1 added driver-suite test(s) import the production package") only proves an import, not that the test runs production code. I checked that separately (see above), and it does. I found no other claim in `check-gates.json` that the evidence does not support. T4 is `deferred` to publish, so nobody has yet checked the PR text, which must tell the human to merge #726 first (brief line 13).

What I tried and could not refute: the red→green proof; that the test runs the production code; the closure walk on transitive, diamond, no-patch, discontinued-partner and partner-built-after-member inputs; the seam fallbacks; and the split in wording between a bundle's own base and the line in the #633, #695 and unchecked messages.

<!-- pdca:leaf-complete -->
