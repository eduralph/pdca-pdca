# Advisory code review — issue 652 (carry-not-clean-cascades-across-finished-ids)

Lenses: correctness bugs the patch adds, and reuse / simplification / efficiency. All
`path:line` refs are on the target at `$PDCA_TARGET`. Gate evidence: C4 is red without the
fix and green with it (`gate-logs/C4-verify.log`, 5 failures pre-fix), and T3 passes in full
(`gate-logs/T3-suite.log`, 2374 tests OK).

I found no correctness bug. The cascade does what the brief asks, and the loop always ends.
Two small notes and one point for the human:

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:892` spreads "not clean" from
  every entry in `why`, including the `edge` case from `_finished_head`
  (`flow.py:854-856`: PR MERGED, but its head is on neither the base nor the line). A
  squash-merge or rebase-merge into the base produces exactly that state, because the
  original head commit never lands on `origin/<base>`. In that case `P`'s work *was*
  reviewed and merged, yet a finished `Q` built on it is now held with the `built_on`
  advice ("get issue_P carried, or re-drive issue_Q on a base without it",
  `flow.py:866-867`). That advice is confusing for a squash-merged prerequisite. Before the
  patch, `Q` was carried. The brief's invariant ("judged not clean before the fold, from
  its PR state and head") does cover this case literally, so the code matches the brief.
  The human should decide whether an `edge` hold should cascade, or whether the cascade
  should cover only the `open`-hint reasons (closed PR, missing branch, state unreadable).
  No test covers a MERGED-not-on-base `P` with a finished dependent.

- `template/src/pdca_harness/flow.py:963-964`: `foreign_commit` now leaves out the heads of
  cascaded ids. So when an old line on origin holds a cascaded `Q`, every finished id of
  that target is held, clean ones included (the `line` hint). This follows from the
  invariant and is documented (`docs/07-crosscutting.md:692-696`: "none of
  them ... accounts for a commit on the line"). The new test
  `test_a_held_ids_head_does_not_vouch_for_an_old_line` covers it. No action needed. I
  list it only because it widens the hold beyond `Q`'s own dependents.

- Reuse nit (not blocking): `template/src/pdca_harness/flow.py:882-886` parses each
  finished id's plain `Depends on` with the same `brief.depends_on(bp) if bp.exists()` /
  `cfg.bundle(dep).name` pattern as the dependents loop at `flow.py:931-935`. It also calls
  `cfg.bundle(dep)` twice per edge (in the filter and in the value). A small helper, such
  as `_plain_dep_names(cfg, d) -> list[str]`, would remove the duplicate and the second
  call. The cost is trivial (a handful of briefs), so this is tidiness only.

- Tests (`template/tests/test_flow_resume_stack_prereqs.py`, new section (9)): these cover
  the brief's criteria (1)-(3), the "rest is still carried" mixed case
  (`test_a_clean_finished_id_beside_them_is_still_carried`, which now makes the
  "P's commit is not on the line" check meaningful because a line exists), and the
  old-line case. They check the `built_on` hint text and that the `open` hint is absent.
  The chain test asks for the ids in reverse order (`["R", "Q", "P", "D"]`), so the
  fixed-point loop is tested on input that is not in dependency order. I found no weak
  assertion.

<!-- pdca:leaf-complete -->
