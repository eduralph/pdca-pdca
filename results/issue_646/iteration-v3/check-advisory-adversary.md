# Adversarial review — issue_646, attempt 3

I couldn't refute the main fix. The red→green proof holds, and the carry, the vouch check, the lock and the re-gate all did what they claim in every case I tried. I found two concrete inputs where the re-issued run now does worse than before, or gives advice that doesn't work. Scratch tests for each are in `scratch/` next to this file.

## Attempts that did not land

- **The red→green proof holds.** In `gate-logs/C4-verify.log`, the red leg has 26 FAILs in the new file and 2 in the updated wording tests, with no import errors. Each one fails on a real assertion: there is no line on origin before D's wave (`template/tests/test_flow_resume_stack_prereqs.py:368`), the earlier line gets force-pushed (`:438`), and bundles get built on a line that should be refused (`:461`). I re-ran both files at `$PDCA_TARGET`: 77 tests OK.
- **The tests use the production code, not a copy.** They call the real `flow._drive_and_act`, the real `integrate.fold` against a bare origin, and the real `publish.publish` with `open_pr=False`. Only three things are stubbed: `_drive_wave`, `draft_texts`, and the `gh` calls that `merged.py` makes (`test_flow_resume_stack_prereqs.py:271`, `:287-308`).
- **A wave-1 bundle on the earlier line is handled.** No test covers this case: the earlier run stopped after wave 1, so its line holds D, whose branch was cut from the line. I ran it in scratch (`scratch/attack_wave1.py`). `_own`'s cut logic (`template/src/pdca_harness/integrate.py:589-596`) vouched for D's commit, the line was continued without force, and E built on it. It works, but it is the most common real re-issue shape and only an in-run fold exercises that path. Consider adding a test for it.
- **Failure modes on the new paths are soft.** `publish._resolve_target`, `publish._fork_owner` and `integrate._rev` all return empty or None instead of raising, so the refusal and lookup paths can't throw a traceback. The owner match in `merged.pr_state` is the same exact compare that `publish._existing_pr` already uses (`template/src/pdca_harness/publish.py:580-583`), so it adds nothing new.
- **`check-gates.json` makes no claim it can't back.** C2 has no gate configured; the red evidence comes from C4 instead. T4 is deferred to publish.

## Findings

- NEEDS-HUMAN — **A squash-merged prerequisite now stops the whole run, where before it built fine.** `template/src/pdca_harness/flow.py:891` carries a MERGED P. If P's branch is gone and its PR was squash- or rebase-merged, the fold raises at `template/src/pdca_harness/integrate.py:548`, and `flow.py:932` stops the run before wave 0.
  - **Concrete case:** `flow P D U`, where P is COMPLETE and was squash-merged into `main` with its branch deleted, D has `Depends on: P`, and U is unrelated (`scratch/attack_squash.py`).
  - **Before the patch:** D and U both reach COMPLETE. D builds on `main`, which already has P's change.
  - **After the patch:** nothing is driven, and the advice says "get that work into origin/main", which by content is already true. Re-issuing the same command stops again every time. The only ways out are to restore P's branch, which puts the pre-squash commits on the line, or to drop P from the ids, which changes the batch and so the line.
  - **Why this is for a human, not the builder:** brief criteria (5) and (6) asked for exactly this ("otherwise raise", and a raise stops the run), and the docs already say never squash (`docs/07-crosscutting.md:647`). A human should decide whether such a P should stop everything, including the unrelated U, or count as "nothing to carry".
- NEEDS-HUMAN [impl] — **A closed PR that was replaced by a new one blocks the whole target, and the advice doesn't work.** `template/src/pdca_harness/merged.py:118-125` only asks about the `pr_url` recorded in `publish.json`. The lookup by branch only runs when that field is empty.
  - **Concrete case:** P's recorded PR is CLOSED, a newer OPEN PR exists for the same branch `fix/P`, and the earlier line holds P (`scratch/attack_superseded.py`).
  - **Result:** `gh pr list` is never called. P is treated as closed (`flow.py:894-898`), the target is blocked so D and the unrelated U are not built, and the advice is "re-open issue_P's PR". GitHub generally won't reopen a PR while another open PR has the same head and base, so the only advice that works is "delete the line", which strands any bundle recorded on that line. Iteration 2's sign-off said exactly this: advice must not be a dead end.
  - **Fix:** when the recorded PR is CLOSED, fall back to the same `gh pr list --head` lookup used for an empty `pr_url`, and add a test for it.
- **Two wording slips in the docs (minor).**
  - `docs/07-crosscutting.md:670-671` says the run "builds all of wave 0 on it". In fact only wave-0 bundles with the same (repo, base) target are pointed at the line (`flow.py:745-751`).
  - `docs/07-crosscutting.md:674` says a finished id that can't be carried "holds only the bundles that depend on it". Only plain `Depends on` dependents are held (`flow.py:719`); a `Stacks on` dependent is still built, as the brief intends.
