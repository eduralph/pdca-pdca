# Advisory code review — issue 593 (stack mode: append-only fold, real-base PRs)

Lens: bugs this patch introduces, plus reuse / simplification / efficiency. Advisory only.
All `path:line` refs are on the patched target at `$PDCA_TARGET`.

Overall: the fold rewrite (`integrate.py:211-509`), the publish base choice and the flow hold
read as correct for the in-run cases the brief covers. Iteration 4's carry-forward items are all
handled: the tip-pinned cut, the hold keyed on "pushed this run", the gone-and-merged skip when
the line already carries it, the `Onto branch` refusal, and the stale text. The optional cleanups
are also done: one `_fold_candidates` helper, prune only on branch remotes, a single
`_stack_marker` read, and the stronger gone-branch test. I found no blocking correctness bug. Notes:

- NEEDS-HUMAN — `template/src/pdca_harness/publish.py:254-255`: the recorded line tip is used
  to cut the PR branch with no check that it is still on origin's line. Within one run that is
  right, because the line is append-only. But a held bundle can be published late, which the
  flow tells the human to do. If a **later run's first fold** has meanwhile force-pushed a fresh
  `pdca-integration/<base>` (`integrate.py:359`), that tip is no longer on any remote branch.
  The late publish then cuts from the old run's line. That line carries that run's fold merges
  and its other bundles' branches, some possibly rejected since, and they would ride into a PR
  against `main`. If the old commit has been garbage-collected, the publish fails with a
  generic "step failed" (`publish.py:374-378`). A cheap guard would refuse (or warn) when
  `git merge-base --is-ancestor <tip> origin/<stack-base>` fails. This sits on the cross-run
  boundary the brief scopes out (#616), so I have not marked it `[impl]`: a human should decide
  whether to guard now or leave it to #616.
- `template/src/pdca_harness/flow.py:663-664`: when `publish.publish` raises (so `_isolate`
  returns `None`) **after** the push but before `publish.json` is written, the bundle is held
  even though its branch is on origin. One way this happens: `gh` is missing, so
  `subprocess.run(pr_cmd)` raises `FileNotFoundError` (`publish.py:386`). This errs safe, since
  the bundle is held and its dependents are skipped loudly. It does differ from the stated rule
  "a branch pushed this run is folded" (`flow.py:1887-1888`). No change needed. Noting it so
  the docstring at `flow.py:649-654` is not read as exact.
- `template/tests/test_flow_slice.py:1503-1505`: the flow tests' fake publisher cuts from
  `origin/<stack-base>`, not the recorded tip. So none of the in-run flow cases covers the
  production `checkout_base = wave_tip` path (`publish.py:254-255`) for a normal wave>0 publish.
  Only the late-publish test (`test_flow_slice.py:1703-1732`) runs the real `publish.publish`
  on a tip-bearing marker. The two cut points give the same commit within a run, so this is a
  coverage gap, not a wrong assertion. Optional fix: have `_push_branch` read
  `publish._stack_marker(d)[1]` when it is set.
- Reuse / efficiency: nothing to flag. `_fold_candidates` (`integrate.py:127-135`) is now the
  one definition behind both `fold` and `unpublished`. The per-wave repeat of
  `_resolve_target` (once in `flow.unpublished`, once in `fold`) reads small brief files and
  is negligible. `_record_stamp` (`flow.py:667-674`) reads the whole `publish.json`, which is
  a few hundred bytes.

Gate evidence: C4 (red before the fix, green after), host-CI docs and T3 (root + driver suites)
pass per `check-gates.json`. T4 is deferred to publish, as expected at this stage.
