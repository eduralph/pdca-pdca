# Adversarial review — issue 616 (stack-resume-carries-unmerged-prereqs)

Lens: refute the red→green evidence and find inputs that break the fix. I re-ran both legs and
tried five breaking inputs with scratch tests (sandbox only), each on the patched tree and on a
copy with the production hunks reverted.

- **Evidence holds.** Green: 14/14 on the patched tree. Red: 8/14 fail with
  `template/src/pdca_harness/{flow,merged}.py` reverted. The 6 that pass pre-fix are the
  "unchanged behaviour" cases, so that is expected. The tests drive the real
  `flow._drive_and_act` → `integrate.fold` → `_point_at_integration` → `worktree._target`
  against a real bare `origin`, so they are not a copy of production. One weak assertion:
  `template/tests/test_flow_resume_stack_prereqs.py:347-348` ("D's PR branch … carries P")
  checks the test's own `_publish_bundle` stub (`:254-265`), not `publish.publish`. Also,
  C5's "exercises production" only checks imports (gate-logs/C5-prod-path.log). My reading,
  not the gate, is what confirms the production path.

- NEEDS-HUMAN — **Regression: an empty `pr_url` on a merged prerequisite now stops the whole
  run.** `template/src/pdca_harness/flow.py:816` asks `merged.is_merged`, which returns False
  whenever `publish.json` has no `pr_url` (`merged.py:48-50`). So P is "carried". Its head
  branch was deleted on merge, so `integrate.py:462-467` raises, and `flow.py:2132-2133` sets
  `wave_list = []`. Verified case: P published with `pr_url: ""`, PR merged into main, branch
  deleted; D `Depends on: P`, U unrelated. Patched: D and U both PLANNED, nothing built. Pre-fix:
  both built on `origin/main`, which already has P, so pre-fix was correct. Ways to get an empty
  `pr_url`:
  - `gh pr create` failed and the human opened the PR by hand, as `publish.py:404-431` tells
    them to (the record keeps `pr_url: ""`).
  - The re-publish this patch tells the user to run for a stale record (`flow.py:2118`). The
    new-PR path runs `gh pr create` again, which fails when a PR already exists for that
    branch.

  With no `gh`, or a broken one, the same happens to any merged P whose branch was deleted
  (`merged.py:51-58`). The stop also takes down bundles of unrelated targets. Brief case (d)
  asks for this stop, but it assumed the host really does not know P merged; here the harness
  lost the URL itself. Human call: hold only that prerequisite's dependents (as the
  unpublished hold does), or check the base for P's work, instead of stopping everything.

- NEEDS-HUMAN — **A prerequisite whose PR was closed without merging is carried.**
  `flow.py:816` treats every state other than MERGED as "carry". Verified: P's PR CLOSED
  (rejected), `fix/P` still on origin. D and the unrelated U are both built on a line that
  carries P. Their PRs target main and include P's commits (`publish.py:266-277`), so merging
  U's PR would land P's rejected work. Pre-fix, both built on `origin/main`. The only stderr
  line is "carrying earlier runs' unmerged prerequisite(s) issue_P". The brief never covers
  CLOSED. A human should decide whether a closed PR holds its dependents.

- NEEDS-HUMAN — **The `Stacks on` claim is overstated.** `flow.py:767-769` and
  `docs/07-crosscutting.md:688-691` say a target that gets a line carries its `Stacks on`
  parent. That holds only for a line the pre-wave fold starts (`lined`, `flow.py:834-839`).
  Verified case: W has `Depends on: A` (in the batch) and `Stacks on: Q` (an earlier run's,
  published, PR open). In wave 1, W is pointed at the line folded after wave 0, which is
  main + A (`flow.py:742-746`). The stack base wins over `Stacks on` (`publish.py:738`,
  `worktree.py:96-98`), so W is built without Q. This also happens pre-fix, so it is not a
  regression. But it breaks the invariant the brief says to restore (`Stacks on` is a declared
  prerequisite, `waves.py:39-48`), and the new docs sentence is wrong for this case. Scope call:
  either carry such parents for any target that will get a line, or narrow the wording.

- NEEDS-HUMAN [impl] — **A line is started even when every dependent that needs it is held.**
  `lined` and `carried` (`flow.py:834-842`) never check whether the dependent is already held
  by another prerequisite. Verified: D `Depends on: P, P2`, where P can be carried and P2 has
  no published branch. D is held, yet the run force-pushes a fresh line carrying P, and the
  unrelated U is re-pointed at it (`do_base` = the line). So U's PR shows P's changes for no
  benefit. Fix: work out the holds first, then carry a prerequisite only for dependents that
  are not held.

- **Low: the stale check depends on file modification times** (`flow.py:850-865`). No harness
  code writes `SUMMARY.md` after a bundle is COMPLETE, so this is sound on the harness's own
  paths. A hand edit, or a `git pull` of recorded bundles (`[records]`,
  `template/pdca.toml.jinja:448-453`), can make `SUMMARY.md` newer than `publish.json` and hold
  a correct prerequisite. That fails safe, but the printed fix (re-publish) leads into the
  empty-`pr_url` problem above.

- **Tried and could not refute:**
  - Moving the in-run fold into `_fold_onto_line` (`flow.py:868-906`, `:2274-2281`) keeps the
    same stop and re-gate messages and the same break behaviour.
  - `carried + accepted` keeps a target's line through a wave that accepts nothing of it.
  - The fold after wave 0 continues the line without a force-push.
  - Holds are per pair across targets.
  - `Depends on (merged)` is unchanged.
  - A dry run makes no holds.
  - A missing `brief.md` on a COMPLETE prerequisite does not raise.
