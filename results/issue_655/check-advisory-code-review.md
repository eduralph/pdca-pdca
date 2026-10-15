# Advisory code review — issue 655 (merged-prereq-gate-checks-the-line)

Lens: bugs the patch introduces, plus reuse/simplification/efficiency. Advisory only.

**Verdict: no correctness bugs found.** The gate fails closed in every path I traced, the cache keys are right, and the tests use real git and cover all five brief criteria plus the carried-head case from round 1. The C4 log shows 5 of 9 new tests red with the production hunks reverted (`gate-logs/C4-verify.log`, "FAILED (failures=5)"), and they are green with the fix. Only small cleanups below, none blocking.

## Correctness (checked, nothing found)

- `template/src/pdca_harness/flow.py:776-784` — the new check runs only when `merged_into` is already True, the target has a line, and the tip is recorded (not a dry run). `lacks` is keyed by `(prereq, repo, base)`, and `lines` has one entry per `(repo, base)`, so a cached answer can't be reused for a different line. A close/no-fix prereq is skipped through `integrate._has_patch`, which matches `merged_into`'s own short-circuit (`merged.py:93-95`).
- `template/src/pdca_harness/flow.py:831-868` (`_line_lacks_merge`) — fail-closed is correct: a fetch error, a `gh` failure (`merge_and_head` → None → both oids empty → "could not be read", False) and a git exit 128 from `_in_line` (`integrate.py:812-818`, caught as `IntegrationError`) all hold D. Accepting either `mergeCommit` or `headRefOid` on the tip fixes round 1's false hold without weakening criterion (4). A squash is still judged on `mergeCommit`, and a stale head simply isn't an ancestor.
- `template/src/pdca_harness/flow.py:2335-2336` — `lines` is built from `integ`, which is only filled on the stack-fold path (`flow.py:2480`, `:1094`). Merge mode is not affected, which matches the brief's scope.
- `template/src/pdca_harness/merged.py:172-200` — the `_pr_view` extraction keeps `pr_state`'s old behaviour: same None cases, and the same `state`-is-a-string check, now done after the `_pr_view` call at `merged.py:178`.

## Cleanups (optional)

- `template/src/pdca_harness/merged.py:117-146` — `merged_head` still runs its own `subprocess.run(["gh","pr","view",…,"state,headRefOid"])` + JSON parse, which is the body the patch just pulled into `_pr_view` (`merged.py:185`). It could call `_pr_view(str(pr_url), "state,headRefOid")` and keep its own stderr line on None. This is minor, and the brief doesn't require it.
- `template/src/pdca_harness/flow.py:773` + `:857` — for each held-or-checked prereq the PR is read from `gh` twice: once in `merged_into` (via `pr_state`, `merged.py:100`) and again in `merge_and_head` (`merged.py:164`). One `state,headRefOid,mergeCommit` read could serve both. It's cheap (one extra `gh` call per out-of-batch merged prereq per wave, and only when the target has a line), so leaving it is fine.
- `template/src/pdca_harness/flow.py:851-852` — on a fetch failure the held line embeds `_fetch`'s message, which ends "the fold cannot see the branches it merges" (`integrate.py:874-875`). That wording fits a fold, not this gate, so the stderr line reads a little oddly. Wording only.

## Recovery advice (for the human, not a code bug)

- NEEDS-HUMAN [human] — `template/src/pdca_harness/flow.py:809-814` and `docs/07-crosscutting.md:752-757` tell the operator to "delete {branch} on origin, then re-run". I checked whether this could close open PRs: in wave stack mode a bundle's PR targets the base, not the line (`publish.py:282`, `pr_base = … and not wave_stacked`), so it shouldn't close them. It does throw away the line's fold history, and the re-run rebuilds it through the #646 carry. The test proves this works for one W + D batch (`template/tests/test_flow_merged_prereq_on_line.py`, `test_the_way_out_is_to_delete_the_line_then_re_run`). Whether telling users to delete a remote branch is acceptable advice, instead of a harness-side option to re-cut the line, was declined at Plan as out of scope. It is still a product decision worth a look at sign-off.

<!-- pdca:leaf-complete -->
