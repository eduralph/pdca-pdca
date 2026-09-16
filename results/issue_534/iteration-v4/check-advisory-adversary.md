# Adversarial review: issue 534, iteration 4

**Result: I could not refute the fix.** The red→green proof holds, the tests run the real
code, and I found no input that makes the reap block a turn, write to a bundle, or raise out
of `handoff.session`. Below are two gaps for a human to judge (both low impact), two
low-priority notes, and the attacks that failed.

## For a human to judge

- NEEDS-HUMAN — **The docs promise more than the reap checks on the CSV-batch planner path.**
  `docs/01-render-and-integrate.md:177-180` (new text in this diff) says the end-of-session
  check means "a session can't close silently with a bad artifact". On the CSV/default
  planner path the driver registers no bundles, so `stop_problems` returns `[]` as soon as
  any `/handoff` has passed (`template/src/pdca_harness/handoff.py:478-479`) and never
  re-checks the briefs. Concrete case, run against the patched tree: the session passes
  `/handoff issue_7`, then writes `issue_8/brief.md` with an empty Success criterion and
  never checks it. `check_planner(issue_8)` reports the empty field, but the reap prints
  **nothing**. An empty Success criterion is exactly the case the brief says nothing
  downstream catches. The gap predates this diff (the old Stop hook used the same
  `stop_problems`), so this is not a regression. But the diff restates the promise, and the
  `report_at_reap` docstring (`handoff.py:360-363`) makes the same claim. There are two ways
  to fix it: make the docs sentence say "every bundle the driver registered", or, as a
  follow-up, re-check the briefs the session added. The driver already works out that list
  in `_warn_unseeded_briefs`, but that code is in `do_plan_batch`, which is out of scope
  here (issue 480).
- NEEDS-HUMAN — **An abandon reason with a terminal escape code can hide the list that
  follows it.** `report_at_reap` prints the reason raw (`handoff.py:368-369`) and then the
  problem list. Concrete case, run against the patched tree:
  `record_abandon(state, "out of time\x1b[8m")` produces
  `'…deliberately abandoned — out of time\x1b[8m\nhandoff: the signoff session ended with…'`.
  `ESC[8m` is the "concealed text" mode, so on most terminals the problem list and any
  driver output after it print invisibly. That breaks the promise this diff adds, "an
  abandon never hides what is missing" (`docs/01-render-and-integrate.md:184-185`,
  `handoff.py:264-268`). The leaf can also write any `abandoned` value straight into its
  scratch file. The odds are low: it takes a leaf doing this on purpose, and the leaf never
  sees the reap output, so nothing pushes it to. Printing the reason raw predates this diff.
  What is new is that the list now comes after the reason. The fix is small: escape
  non-printable characters in the reason before printing it. The human's call is whether a
  leaf that hides the report on purpose is in scope.

## Low-priority notes (not refutations)

- Reading the doctor table early (`handoff.py:462-468`) turns a malformed
  `[[doctor.checks]]` table (for example `[doctor] checks = ["protoc"]`) into the one line
  "could not check the planner session's exit contract … — nothing reported". That happens
  even for an id-seeded batch where every issue was legitimately left UNPLANNED, where each
  bundle's own `check_planner` would pass (I ran this). It also hides "brief.md is missing"
  and "unfilled template copy" findings, but the driver catches both later (`flow.py`,
  `state` treats a placeholder brief as UNPLANNED). Nothing only the reap can catch is lost,
  and a broken table is worth reporting anyway. This matches the human's iteration-3 wish
  to keep config-wide failures to one line.
- Two more driver-suite tests print the reap report to the real stderr:
  `template/tests/test_state_resolved.py:191` and `:217` (visible in
  `gate-logs/T3-suite.log:1043-1050`). This is the same kind of noise as iteration 3's item
  2, which silenced `test_handoff.py` and `test_publish_slice.py`. Each needs one
  `redirect_stderr(io.StringIO())` wrapper. Worth folding in only if there is another
  iteration anyway.

## Attacks that did not land

- **Red→green evidence.** I re-ran both legs in a sandbox copy of `$PDCA_TARGET`. On the
  patched tree, 57/57 pass (`tests.test_handoff_reap`, `tests.test_handoff`). With
  `settings.json`, `handoff_guard.py`, `handoff.py` and `leaves.py` put back to HEAD, 29
  fail, the same 2 + 27 as `gate-logs/C4-verify.log:108-371`. The (a) red leg is not the
  false green the brief warned about: `template/tests/test_handoff_reap.py:189` first proves
  the contract check is live (`--check` → 1 in the same environment), and the pre-fix hook
  then returns 2 with "may not end yet" (`C4-verify.log:113-133`). The subprocess variant
  (`test_handoff_reap.py:210-236`) loads its own `pdca.toml` and does not rely on the
  `_bootstrap` patch.
- **Production path.** The tests load the real hook file from `template/.claude/hooks/` and
  the real `pdca_harness.handoff`. There is no mirror copy.
- **Making the reap raise.** `report_at_reap` catches `Exception` around both the reason
  print and `stop_problems` (`handoff.py:365-374`). Each bundle check is isolated
  (`:472-475`), and the leaf's own exception passes through unchanged (tested). The only
  ways out are `BaseException` (Ctrl-C during a slow detect command) or the final `print`
  failing on a closed stderr. Neither is realistic.
- **Making the reap write.** The sign-off, publisher and act checks are pure reads. Planner
  detect commands (`doctor.py:312`, no timeout) are the only side channel, and
  `plan_policy` already runs them after Plan (`driver.py:56`).
- **Other turn-end hooks.** Nothing is registered on Stop or SubagentStop in
  `settings.json`, and the agent frontmatter only registers PreToolUse (`builder_guard.py`)
  for builder and publisher.
- **The new "unknown mode → exit 2" branch** (`handoff_guard.py:73-76`) would only bring
  back a turn-end block for a Stop registration that passes an argument. The retired
  registration passed none, and no caller passes anything other than `--check` or
  `--abandon`.
- **Leftover promises of Stop-hook enforcement.** None remain in prompts, agent bodies,
  `/handoff`, or the docs, apart from the comments this bundle was told to leave alone
  (`leaves.py:916-917`, `:1106-1108`).
- **Blank abandon values, a non-UTF-8 decision file, a directory in a file's place, a leaf
  that rewrites its scratch file, an abandon plus a problem list:** all are covered by
  tests that go red before the fix.
