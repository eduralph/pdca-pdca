# Advisory code review — issue 625 (stack-mode live GitHub check tool)

Lens: bugs the patch introduces, plus reuse/simplification. Lines are cited on `$PDCA_TARGET`.
The offline part (`judge` and its test) looks correct. The C4 red leg fails on assertions, not
on an import (`gate-logs/C4-verify.log`: "can't open file …/stack_mode_live.py", 6 failures).
Every driver API the tool calls exists with the signature it uses: `Config` fields
`base_remote` / `repo_checkouts` / `gates_checks` (`template/src/pdca_harness/config.py:155-162`),
`_drive_and_act(..., batch=, holds=)` (`flow.py:2709-2721`), `cli._results_rc(..., holds=)`
(`cli.py:707`), `publish.read_stack_base_tip` / `_publish_record` / `COMMIT_MSG` / `PR_BODY`
(`publish.py:40-41,644,698`), and `signoff.record` (`signoff.py:255`). The findings below are
all in the live `setup`/`run` path, which no gate runs.

- NEEDS-HUMAN [impl] — `tools/live/stack_mode_live.py:186-191`: `_on_base` treats every non-zero
  exit of `git merge-base --is-ancestor` as "not on base". Exit 1 means "not an ancestor", but
  exit 128 means "unknown commit" (for example, an object this clone never fetched). For `E4`,
  the expected value is `False` (`headRefOid` NOT on base, judged at `:422-423`), so a missing
  object would make `E4` PASS by accident: the one check #626 depends on. Return `True` on
  rc 0, `False` on rc 1, and `None` otherwise, so `judge` reports "not observed" instead of
  passing.
- NEEDS-HUMAN [impl] — `tools/live/stack_mode_live.py:240-242`: the branch delete after a merge
  runs with `check=False` and its result is never recorded. If the delete fails (wrong ref
  name, missing permission), `E2` is read "after delete" while the branch still exists, and
  run 2 never reaches `integrate._gone_branch` (`integrate.py:1406`). `E3` then FAILs with a
  misleading cause, and that FAIL would be filed as a driver bug. Either check the delete
  (allow 422 "Reference does not exist" in case GitHub auto-deleted the branch), or record
  whether the ref was gone in the observations.
- NEEDS-HUMAN [impl] — `tools/live/stack_mode_live.py:404-416` (E3): `gone` matches
  `"{branch} is gone and its PR merged"`. The same phrase begins the `IntegrationError`
  messages at `integrate.py:1443,1491,1503`, and on the carry path those errors are caught and
  turned into holds (`flow.py:1507-1520,1538`), not a `STOPPING` line. So `gone` and
  `not stopped` can both read true when the carry was refused. Today the `D_built_on_holds`
  term catches this, because a held D is never built. Still, the judge ignores `run2.rc`,
  `run2.holds` and `run2.results["D"]`, which `_drive` already records (`:278-279`) and the
  test fixture already fills in. Checking `rc == 0`, an empty `holds`, and D `COMPLETE` would
  make "no stop" mean what the brief says. Matching the success wording ("— taking" /
  "reaches … through", `integrate.py:1509`) would also be tighter than matching the shared
  prefix.
- `tools/live/stack_mode_live.py:115-117,139`: with `--reuse` and an existing workdir, only
  `checkout/` is wiped. `project/results/` keeps the previous run's bundles (accepted
  SUMMARYs, `publish.json` pointing at PRs that may be deleted), and `_drive` copies a brief
  only when one is missing (`:258-260`). A second run in the same workdir would then start
  run 1 with A, B and C already finished. Without `--reuse`, a fresh repo plus a leftover
  `checkout/` makes `checkout.mkdir()` raise *after* `gh repo create`, which leaves the repo
  behind. Suggest wiping `project/` along with `checkout/` on `--reuse`, and checking the
  workdir before creating the repo.
- `tools/live/stack_mode_live.py:224`: `_files` sleeps a fixed `--settle` time, then reads once.
  If GitHub is slow to recompute the PR diff, `E1` or `E1b` FAILs, and per the brief each FAIL
  is filed as its own bug. A short poll (re-read until two reads agree, or until a timeout)
  would cut false FAILs at little cost.
- Simplification, `tools/live/stack_mode_live.py:438` and `:462`: the overall pass/fail rule is
  computed twice, in `_report_md` and in `cmd_judge`. Pass `passed` into `_report_md` so the
  `.md` and `.json` reports cannot disagree. Also, `tests/test_stack_mode_live_tool.py:129`:
  `copy.deepcopy(_good())` does nothing, since `_good()` already returns a fresh dict. That
  makes the `copy` import unused.

No other correctness issues found in `judge` or the test. The six offline cases each check that
exactly one check fails and the rest pass, which is a meaningful test.

<!-- pdca:leaf-complete -->
