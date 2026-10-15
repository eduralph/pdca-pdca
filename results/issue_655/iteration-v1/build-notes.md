# Build notes — issue 655 / merged-prereq-gate-checks-the-line

Worktree: `/home/eddie/pdca/pdca-harness.pdca-wt-l0`, base `420f8b4` (the run's integration
line `pdca-integration/main-r8bf6d15b2de3`, which already holds 629). Line numbers below are
on that base plus this patch. They have moved from the brief's `b5f5c29` numbers because
629 landed in `_runnable` first.

## What changed

1. **`merged.merge_commit`** (`template/src/pdca_harness/merged.py:148-177`, module
   docstring `:24-25`). Asks `gh pr view <url> --json state,mergeCommit` and returns
   `mergeCommit.oid` only when the PR is MERGED. Fail-closed and silent, like `pr_state`
   (`merged.py:180`): no PR on record, not merged, `gh` failure, `gh` missing (OSError) or
   bad JSON all return `None`. Same shape as `merged_head` (`merged.py:116-145`), but it
   reads `mergeCommit`, not `headRefOid`. The brief's criterion (4) explains why: a squash
   or rebase merge never puts the head on the base.

2. **`flow._runnable`** gets a `lines=` parameter (`flow.py:687`): target `(repo, base)`
   maps to `(line branch, recorded tip)`. Docstring paragraph at `flow.py:728-736`.
   - The cache of fetched checkouts for one call is at `flow.py:738`, and the new
     `off_line` list is at `flow.py:753`.
   - The gate change is at `flow.py:771-779`. When `merged.merged_into` says yes, d is
     targeted, the run has a line with a recorded tip for d's target, and P has a non-empty
     patch, it asks `_line_lacks_merge`. Any reason holds d. A close/no-fix prerequisite
     merged nothing, so it is not checked. A `None` tip (dry-run) is skipped too: a dry-run
     holds nothing.
   - The held message is at `flow.py:798-807`. It is ONE line naming d, each prerequisite
     with its reason, "merged into <base> (<repo>)", the line branch and its 12-char tip,
     and "does not have that merge" (or "is not known to have that merge" when the check
     itself failed). It says "this run does not take <base> into its line" and tells the
     user to re-run once this run ends. It does not say this run cut the line: on a resumed
     run the #646 carry continued it.
   - `runnable.append` now also requires `not off_line` (`flow.py:819`).

3. **`flow._line_lacks_merge`** (`flow.py:824-856`) is the new helper. It reads the checkout
   with `integrate.carry_view(cfg, repo_spec, branch)`, which fetches first and only reads,
   so it needs no lock (as `_carry_finished` uses it, `flow.py:1044`). The checkout is
   cached per target per call. It then gets `merged.merge_commit` and asks
   `integrate._carries(view, oid, …, of=<recorded tip>)` (`integrate.py:648-655`). A commit
   the clone lacks counts as "not in it". A git exit 128 (for example, the tip itself is
   missing) raises `IntegrationError`, which becomes a reason. Return value: `None` (on the
   line), `(reason, True)` (known to be missing), or `(reason, False)` (could not check).

4. **Caller** (`flow.py:2321-2324`): `_drive_and_act` passes
   `lines={tgt: (branch, folded_tips.get(tgt)) for tgt, branch in integ.items()}`. Those
   are the same maps `_point_at_integration` uses to set d's stack base and tip
   (`flow.py:2368`, via `:859-880`), so the gate checks exactly the commit d will be cut
   from. Merge mode never fills `integ` (`flow.py:2432` takes the `merge_wave` branch, and
   only the stack branch updates `integ`, `flow.py:2468`), so merge mode is not affected, as the brief
   requires.

5. **Docs** (`docs/07-crosscutting.md:744-754`): a new paragraph right after the #647
   paragraph. It says the dependent also waits until the run's line has the merge commit,
   that it fails closed, and what to do.

## Alternatives ruled out

- **Check `headRefOid` instead of `mergeCommit`.** This is wrong for squash and rebase
  merges, which is exactly what criterion (4) pins.
  `test_a_squash_merge_already_on_the_line_builds_the_dependent_on_it` asserts that P's head
  is NOT on the tip D was built on while D still builds.
- **Ask `merged_into` to do the line check itself.** That would change its contract for
  its other callers (`merged_into` docstring: "Only `flow._runnable` calls it", but the
  brief puts `merged.is_merged` and the rest out of scope). It would also make the
  `merged.py` module depend on `integrate`. Keeping it in `flow` costs one extra helper
  (35 lines) and leaves `merged_into` unchanged.
- **Check origin's current line tip (the `carry_view` return value) instead of the
  recorded tip.** The dependent is cut from the recorded tip (`stack-base-tip`), so the
  recorded tip is the right commit to check. Origin's tip is only the same thing when no
  one else moved it.
- **Refresh or re-cut the line.** Declined at Plan (out of scope).

## Tests — `template/tests/test_flow_merged_prereq_on_line.py` (new, 7 cases)

The tests use real git (the `StackFoldGit` fixture, loaded by path as
`test_flow_resume_stack_prereqs.py:35-38` loads it) and drive `flow._drive_and_act` with a
non-stub publisher. `gh` is stubbed and answers `state`, `headRefOid` and
`mergeCommit{oid}`. The fixture wraps `integrate.fold` so a hook runs once, after the
first real fold.

| Case | Criterion | Pre-fix | Post-fix |
|---|---|---|---|
| merge after line cut, `Depends on (merged)` | (1) | FAIL: D built on the line | OK: held, one line |
| merge after line cut, plain `Depends on` | (2) | FAIL | OK |
| merge-commit merge before run | (3) | OK | OK |
| squash merge before run | (4) | OK | OK |
| `mergeCommit` query fails | (5) | FAIL | OK: held, "could not be read" |
| checkout fetch fails | (5) | FAIL | OK: held, "could not be fetched" |
| no line for D's target | (5) | OK | OK: built from the base |

Gate run: `engine/scripts/run-verify.sh` (the C4 gate, with `PDCA_BUNDLE` and
`PDCA_WORKTREE` set). Result: green leg `Ran 7 tests … OK`; red leg `Ran 7 tests …
FAILED (failures=4)`, all four failures are assertion failures in `_held`
(`'issue_D' unexpectedly found in {… 'issue_D': ('pdca-integration/main-r…', '<tip>')}`).
Final line: `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.

The first version of the fetch-failure case broke `origin` for good. On the red leg that
made D's own publish fail inside the fixture (an error, not a gate assertion). I changed
it so the fixture's `_publish_bundle` points `origin` back at the real bare repo before
publishing, so only the gate's fetch fails. After that change all four red-leg results
are assertion failures.

Neighbouring suite: `engine/scripts/run-suite.sh` (T3). The result is recorded at the end
of this file.

## Refute-your-own-test

- **(a) Genuine red?** Yes. The C4 gate reverted the production hunks (`flow.py`,
  `merged.py`), kept the test, and ran it: 4 of 7 FAIL on the assertion
  `assertNotIn("issue_D", self.seen)`, because D was built on
  `pdca-integration/main-r1bf7d0372cf7` at a tip without P's merge. Cases (3), (4) and
  no-line are green on both legs, as the brief says they should be ("(4) is green before
  and after").
- **(b) Production path?** Yes. The tests call the real `flow._drive_and_act` →
  `_runnable` → `merged.merged_into` / `merged.merge_commit` → `integrate.carry_view` /
  `integrate._carries`, and the real `integrate.fold` (only wrapped to run a hook after
  it). Only the build and sign-off leaves, publish texts, and `gh` are stubbed. `gh` is a
  host the brief says to stub.
- **(c) Fixture includes the fault?** Yes. P's PR is really merged into `main` on the bare
  origin (`fx._merge_pr`, or a real `git merge --squash` + push), after the real wave-0
  fold has pushed the line. The test asserts
  `assertFalse(fx._ancestor(merge_oid, line))` before checking the hold, so the line
  provably lacks the merge. The fetch-failure case points the real checkout's `origin` at
  a path that does not exist, so the real `git fetch` fails.

## Commit-readiness

The target has no formatter config and no commit hooks (no `.pre-commit-config.yaml`, no
`core.hooksPath`, no ruff or flake8 in `.github/workflows`). CONTRIBUTING.md asks for a DCO
sign-off (`git commit -s`), which publish adds. No added line is longer than 96 characters
(existing `flow.py` lines go up to 106). `engine/scripts/run-docs-check.sh`: `lint_docs: OK`,
`render_site: link audit OK`.

## Housekeeping note

I wrote one verify log to `/tmp/claude-verify-655.log`, which is outside the harness roots.
It is a throwaway log. I did not delete it, because cleanup belongs to the harness.

## T3 suite

`engine/scripts/run-suite.sh` with the patch applied: template-repo suite `Ran 24 tests …
OK`; offline driver suite `Ran 2449 tests … OK (skipped=2)`. That includes every case in
`test_flow_out_of_batch_prereq_hold.py`, `test_flow_resume_stack_prereqs.py`,
`test_flow_slice.py` and `test_integrate_stack_bases.py`.
