# Advisory code review — issue 500 (merge-mode retarget of a wrong-based PR)

Lenses: bugs the patch introduces, and reuse / simplification / efficiency. Advisory only.

No correctness bug found in the main path. The new check sits where the brief asks: after the
`"stacked"` refusal, the `is_merged` skip and the `expected_checks_error` refusal, and before
`gh pr ready` (`template/src/pdca_harness/merge.py:567`). Its refusal is a plain STOP plus
`return 1`, not `_refuse`, so no spurious `gh pr ready --undo` is sent. It runs under both
`merge_requires` values. Route 2 (`publish._batch_branch_producer`) is checked before any host
call (`merge.py:489`). The target comes from `publish._resolve_target(d)[:2]` (`merge.py:480`),
as the brief requires. The C4 log shows the new tests failing on assertions before the fix and
passing after it, and T3 (2635 tests) passes. The findings below are small.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:483-486` copies, word for word, the
  `fix` hint string from `publish._merge_base_refusal` (`template/src/pdca_harness/publish.py:792-795`),
  leaving off only the final period. Two copies of the same user-facing text will drift apart.
  Move it to one module-level constant in `publish` and use it from both places.
- NEEDS-HUMAN [impl] — `template/src/pdca_harness/merge.py:500-503` and `:504-509`: when
  `gh pr edit --base` fails (for example, no permission to edit the PR, or a network error) or
  the host ignores it, the refusal still adds the `fix` hint "Point the brief's `Repo + branch
  target` at the shared base, or use … stack". That hint fits the route-2 case. In these two
  cases the brief is usually correct and the PR is what needs fixing, so the hint sends the
  operator the wrong way. Say instead to retarget the PR on the host (or check `gh` rights),
  then re-run.
- `template/src/pdca_harness/merge.py:475-482`: a COMPLETE bundle with no `brief.md`, or no
  usable target, now refuses at merge time where it used to merge. This is the correct
  fail-closed choice, and it is why five test fixtures needed a `brief.md` added. But it is a
  new hard requirement on every merge-mode bundle, and the merge-mode docs bullet
  (`docs/07-crosscutting.md:887`) doesn't mention it. Low risk, because real bundles always
  carry a brief. Noted only, no action needed.
- `template/src/pdca_harness/merge.py:491`: under `merge_requires = "all"` the PR is now read
  with `gh pr view` once here and again inside `_base_read` (`merge.py:378`), with no step in
  between that could change it (unless a retarget happened). The brief allows reusing that
  read ("Do may reuse it"). The cost is one extra API call per PR, which is fine at wave
  scale. Optional cleanup, not a defect.
- `template/src/pdca_harness/merge.py:480`/`:489`: route 2 is looked up using the brief's
  `repo_spec`, while the PR's repo comes from the publish record (`merge.py:525`). The patch
  doesn't check that the two match. Publish writes the record from the same brief, so they
  should agree, and this would only matter if someone edited one by hand. Noted, no action
  needed.
- Tests: `template/tests/test_merge_retarget.py` covers legs (a) through (f). It covers both
  `merge_requires` values for (a), (b), (d) and (e). It asserts that no `gh pr ready` or
  `gh pr merge` call is made on refusal, and that the base is read again between the edit and
  the ready-mark. Leg (f) is tested only under the default `"all"` setting. That is enough,
  since the `expected_checks_error` refusal comes before the `merge_requires` branch. One gap:
  no test covers a bundle whose PR is retargeted and then refused later (for example, a red
  rollup). The PR then keeps its new base while its ready-mark is undone. That is the correct
  outcome, but a test would pin it down. Optional.

<!-- pdca:leaf-complete -->
