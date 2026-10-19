Review whether a bundle whose own base cannot be built is held without stopping unrelated work, with correct dependency holds, remedies, rewrite reporting, and exit codes.

Source paths below are relative to `$PDCA_TARGET` (`target/`); evidence paths are relative to this review directory. The target matches the supplied patch on the advertised prerequisite base; no stale-target caveat applies.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The seven real-git scenarios define affected bundles, cause-specific remedies, exit codes, and explicit fold/carried-prerequisite exclusions; `brief.md:3`, `brief.md:16`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing only the three production files made all eight new tests fail on the original STOPPING behavior, without import errors; `reviewer-red.log:1`, `template/tests/test_flow_bundle_base_holds.py:219`. |
| C3 Change | PASS | Changes remain within base-failure isolation, hold propagation, exit classification, rewrite diagnostics, and their regression tests; `template/src/pdca_harness/flow.py:1042`, `template/src/pdca_harness/cli.py:736`. |
| C4 Verification (red→green) | PASS | After stash pop, all 169 selected tests passed, including the eight independently red cases and every suite named in the brief; frozen C4 also records red/green for the two updated suites; `reviewer-green.log:197`, `gate-logs/C4-verify.log:10`. |
| C5 Causal adequacy | NEEDS-HUMAN [impl] | Correct premature rewritten-PR classification for an accepted no-fix bundle — the independent probe finds no PR containing the lost head, yet the run fails with exit 1 instead of hold exit 3; `template/src/pdca_harness/flow.py:2868`, `reviewer-no-patch-probe.log:1`. |
| T1 Structure | PASS | The change extends the existing base builder, runnable filter, holds collector, and shared exit-code rule without adding another drive path; `template/src/pdca_harness/flow.py:2853`, `template/src/pdca_harness/flow.py:3024`, `template/src/pdca_harness/cli.py:705`. |
| T2 Shape | PASS | Independently reran docs lint and site rendering: lint clean, 22 pages rendered, internal-link audit clean; diff whitespace check also passed; `docs/publishing/tools/lint_docs.py:80`, `docs/publishing/tools/render_site.py:454`; frozen parity agrees at `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | Independently executed 169 affected tests successfully; full-suite evidence is from the frozen log, which shows 24 root tests passing and 2602 driver tests passing with two skips; `reviewer-green.log:197`, `gate-logs/T3-suite.log:54`, `gate-logs/T3-suite.log:1874`. |
| T4 Contribution | N/A | Contribution artifacts are absent by design at Check; the substantive contribution audit must rerun at publish, as the deferred gate states; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm affected-path prior art in merged history and closed/rejected work for flow.py, integrate.py, and cli.py — the isolated target has one base commit and no remotes, and the brief's related commits/previous attempt do not establish both searches; `brief.md:22`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the demonstrated isolation, operator remedies, and exit-code policy meet operational needs after the no-fix classification defect is resolved; automated scenarios establish behavior but cannot make that acceptance decision; `brief.md:20`, `template/tests/test_flow_bundle_base_holds.py:239`. |

One builder-fixable finding: **[P2] Count stale-head PR exposure only after a branch is actually published.** At `template/src/pdca_harness/flow.py:2868`, `_built_on_lost_heads` runs before the build and publishing phases and immediately adds a member to `in_prs` (`template/src/pdca_harness/flow.py:1106`). The collector later records that member as `rewritten` (`template/src/pdca_harness/flow.py:3028`), which forces exit 1. Pointing a bundle at a base does not establish that it produces a PR: an accepted close/no-fix outcome legitimately publishes nothing (`template/src/pdca_harness/publish.py:175`).

I exercised case (6)'s real-git topology with S accepted COMPLETE and an empty patch, using the production publisher for S. A, Z, W, and S completed; B was base-held. S had neither a publish record nor a remote branch, and none of A/Z/W's published branches contained A's lost head. Nevertheless, the run recorded `{'B': 'base', 'A': 'rewritten'}`, exited 1, and told the operator to rebuild S's nonexistent PR. With no published PR containing the lost head, this should retain case (2)'s base-only hold and exit 3. Keep any advance warning separate from failure classification, and derive actual PR exposure after publishing using the pushed-bundle filter already embodied by `template/src/pdca_harness/flow.py:1115`. Add this no-fix outcome to the regression coverage.

The independent probe is retained as `reviewer-no-patch-probe.py`; reproduce from this directory with:

```sh
cd target/template
TMPDIR=/tmp/pdca-review-h7iae23k PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:. python3 ../../reviewer-no-patch-probe.py
```

Its observed output is in `reviewer-no-patch-probe.log`. Fetch/push injections match the brief's permitted fault boundaries, and real git exercises the forbidden failures; they do not leave an undischarged external dependency. The production-path scanner's frozen log confirms the new suite imports production (`gate-logs/C5-prod-path.log:10`), independently corroborated by its imports and real driver call at `template/tests/test_flow_bundle_base_holds.py:46` and `template/tests/test_flow_bundle_base_holds.py:203`. Instance-scoped gate wrappers were adjudicated from their captured logs; no missing-wrapper finding is asserted. The original target patch was restored and passes `git apply --reverse --check ../patch.diff`.

<!-- pdca:leaf-complete -->
