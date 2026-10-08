# Advisory code review — issue 616 (stack-resume-carries-unmerged-prereqs)

Lenses: correctness bugs the patch introduces, and reuse / simplification / efficiency.
Advisory only. Gates: C4 red→green (gate-logs/C4-verify.log: 14 of 21 new tests fail without
the fix), full suite green (gate-logs/T3-suite.log: 2346 tests OK).

No blocking correctness bug found. I traced the pre-wave fold
(`template/src/pdca_harness/flow.py:2187-2208`), the shared `_fold_onto_line`, the hold/carry
logic in `_prereqs_to_carry`, and the `held_pairs` check in `_runnable`
(`template/src/pdca_harness/flow.py:718`). They match the brief and both carry-forward lists:
holds are worked out before any line starts; PR state is asked before the timestamp check;
`Stacks on` starts no line; holds are per (dependent, prerequisite) pair. The in-run fold
keeps `carried` at the head of every later fold. Already-merged branches are a no-op `git merge`
there, and doing it keeps the carried target in `integ`. The `E` continuation goes through the
`folded_this_run` "continue" path (`template/src/pdca_harness/integrate.py:344-401`), so it
does not force-push. The `merged.py` refactor keeps `is_merged`'s old answers and adds the
`OSError` guard through the shared `_pr_view`.

Minor points, none needing a human decision:

- `template/src/pdca_harness/flow.py:925-940` — `_record_predates_signoff` compares file
  mtimes (modification times). It fails closed, but any copy that does not keep mtimes makes a
  good `publish.json` look older than `SUMMARY.md`. Examples: a manual move to `completed/`
  done with `cp -r` instead of `mv` (`config.py:514-530` calls this archive a manual
  convention), restoring `results/` from git or a backup, or moving to another machine. The
  dependents are then held and the user is told to re-publish a prerequisite that is fine.
  This is safe, not a wrong build. The heuristic was asked for in iteration 1. It is worth one
  line in the docs paragraph (`docs/07-crosscutting.md:676-700`) so a user who hits a false
  `stale` hold knows why.
- `template/src/pdca_harness/flow.py:889-894` — `_recorded_pr` repeats the `pr_url` read that
  `merged._pr_view` already does (`template/src/pdca_harness/merged.py:86-88`), through a
  different `_publish_record` helper (`publish._publish_record` instead of
  `merged._publish_record`). The two disagree on a truthy non-string `pr_url`. `_pr_view` passes
  `str(pr_url)` to `gh`, while `_recorded_pr` returns "", so a failed `gh` call there gets the
  `_NO_PR` message ("records no PR URL") instead of `_UNREAD` (`flow.py:843`). This is an edge
  case. A small public `merged.recorded_pr_url(d)` used by both would remove the duplicate.
- `template/src/pdca_harness/merged.py:96-97` — `_pr_view` now serves `pr_state` too, but its
  stderr line still says "treating as not merged". On the #616 path, the next line on stderr is
  a hold ("held this run …"), not a not-merged wait. "could not read PR state for X (url)" alone
  would be accurate for all three callers. Wording only.

Tests (`template/tests/test_flow_resume_stack_prereqs.py`) use real git against a bare origin.
They patch only `_drive_wave`, `_publish_bundle`, `draft_texts`, and `merged.subprocess` (the
`gh` boundary). They cover the success criterion, cases (a) to (d), the `U` and `E` bundles,
and every carry-forward item. I found no test that misses the code path it claims to test.
