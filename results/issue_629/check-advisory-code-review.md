# Advisory code review — issue 629 (hold `Conflicts with` partner of an unpushed bundle)

No correctness bug or reuse problem in this diff needs a human decision. The round-1 finding (advice that led straight back to the bug) is fixed. The held line now says to wait for the merge (`template/src/pdca_harness/flow.py:781-786`), and the test pins the exact advice text (`template/tests/test_flow_conflict_partner_hold.py:43`, `:187-188`). The C4 log shows 3 of 4 cases red without the fix; the 4th is the unchanged-behaviour control, which should pass both ways.

What I checked and found sound:

- The patch reuses `waves.conflict_map` (`template/src/pdca_harness/waves.py:136-153`) instead of re-reading `Conflicts with` from briefs, as the brief asked. It is rebuilt from the live `bundles` each wave (`template/src/pdca_harness/flow.py:2233-2237`). That costs nothing extra when no bundle is unpushed (`None` is passed then), and the split-child test (`template/tests/test_flow_conflict_partner_hold.py:225-245`) covers the live-list requirement.
- The symmetric map makes "either direction" work. A partner sitting in an earlier wave than the unpushed bundle has already been built, so the hold can only hit a bundle the scheduler placed after it. There are no false holds within a run.
- The cascade to `705` falls out of the existing not-COMPLETE check. No new code path was needed.
- `publish._resolve_target` now also runs for a bundle that has partners but no deps (`flow.py:737`). It only does that when there is a partner, so the hot path is unchanged.
- Every bundle in `held_unpushed` has a usable target (`integrate.unpublished` keeps only fold candidates, `template/src/pdca_harness/integrate.py:187-197`). So the advice to "`pdca publish <id>`" is always something the operator can actually do.

Minor notes (no action needed):

- `template/src/pdca_harness/flow.py:782` — the "wait until their PR merges into {base} ({repo})" text uses the HELD bundle's own target. If a `Conflicts with` pair spans two different targets, the unpushed partner's PR goes into a different repo/base than the line names. This is rare (a cross-target conflict edge does not share a line anyway), and the brief does not cover it.
- `template/src/pdca_harness/flow.py:774-786` — a bundle that both `Depends on` and `Conflicts with` the same unpushed bundle gets two stderr lines: the existing "prerequisite(s) not ready" line and the new conflict line. Both are accurate. Folding them into one line would be cosmetic only.

<!-- pdca:leaf-complete -->
