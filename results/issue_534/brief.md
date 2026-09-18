# Brief — issue 534 / handoff-contract-reported-at-reap-not-turn-end

> Re-plan after four Do rounds (2026-09-16). The approach is unchanged and was confirmed
> at every sign-off; what changed is that the rules the REPORT must obey are now stated
> here up front instead of being discovered one per round. See "Why this is a re-plan".

- **Slug:** handoff-contract-reported-at-reap-not-turn-end
- **Defect:** `template/.claude/settings.json:60-70` registers `handoff_guard.py` as a Claude
  Code **Stop** hook. Stop fires every time the main agent finishes a turn, not when the
  session ends. `_stop_verdict()` (`template/.claude/hooks/handoff_guard.py:48-73`) exits 2
  while the leaf's contract is undischarged, and on exit 2 Claude Code sends the hook's
  stderr back to the model instead of handing the turn to the human (the hook's own
  docstring says so at `handoff_guard.py:13-15`). An interactive leaf that asks the human a
  question therefore never reaches them: the model gets the guard's text, answers it, ends
  another turn, and is blocked again. Nothing bounds the repeat — the Stop envelope, which
  carries `stop_hook_active` for exactly this purpose, is parsed and thrown away
  (`handoff_guard.py:53`). Observed: a sign-off session blocked twelve turns in a row, and
  this re-plan session was blocked on every turn it asked the human a question. The pressure
  on the model is to write the artifact the guard demands, and for sign-off that artifact is
  `signoff-decision` — the human's own decision. Live for every interactive leaf with a
  contract: planner, signoff, publisher, act (`handoff.py:70-78`).
- **Decision (maintainer, Plan 2026-09-15, re-confirmed 2026-09-16):** of the issue's three
  fix shapes, take shape 3. Drop turn-end enforcement entirely and judge the contract when
  the driver reaps the leaf's process. The reap **only reports**: it prints what is unmet and
  changes no bundle state, blocks nothing, and does not reopen the session. Safe because the
  Stop hook never covered the absent-artifact case anyway (Ctrl-D / `/quit` ends the process
  whatever the hook says), and the driver already handles each absent artifact after the
  session: `flow.py:369-372` (no brief), `flow.py:152-155` / `:1378-1392` (no decision),
  `publish.py:55-60` (no publish artifacts). The report earns its keep on the two
  malformed-but-present cases nothing downstream catches: a brief whose Success criterion or
  Repo + branch target is empty (`handoff.py:116-119`), and an `iterate-*` / `discontinue`
  decision with no rationale (`handoff.py:143-146`; with no rationale there is no delta to
  record, so `signoff.py:208-209` leaves SUMMARY §9's Iteration delta empty and the carry-
  forward the next attempt's brief receives (`driver.py:359`) says nothing about why the
  attempt was rejected).
- **Success criterion:** all of the following, shown by the named tests at C4. Items (a)–(c)
  are the fix; (d)–(g) are the rules the report itself must obey — they are part of the
  criterion, not polish.
  (a) **No turn end is intercepted.** The rendered template registers no hook on the Stop
      event, and `handoff_guard.py` run the way the old registration ran it (no arguments, a
      Stop-event JSON envelope on stdin, `PDCA_HANDOFF_ROLE` and `PDCA_HANDOFF_STATE` set,
      and the registered bundle's contract **undischarged**) exits 0 and writes nothing to
      stderr. An instance whose `settings.json` still carries the old registration (a
      `copier update` merge that kept it) therefore cannot deadlock either.
  (b) **The contract is reported at reap.** When the `handoff.session(...)` context the
      driver wraps around an interactive leaf exits with the contract undischarged, the
      problems `stop_problems()` finds are printed to **stderr**, naming the role and each
      bundle (a sign-off bundle with no `signoff-decision`; a signoff `iterate-do` with no
      rationale; a planner brief with an empty Success criterion). A discharged contract
      prints nothing.
  (c) **Report only.** The reap writes nothing into any bundle, deletes or moves no artifact,
      raises nothing, and does not reopen the session. A failure inside the check degrades to
      a printed line, never an exception out of the context manager (the existing rule at
      `handoff.py:273`: a checked exit contract must never break the leaf it checks).
  (d) **The report hides nothing.** Four cases, each with its own test:
      1. **An abandon never hides the list.** A recorded `--abandon` reason is printed
         first, and then every problem `stop_problems()` finds. `stop_problems()` does not
         read `abandoned` at all. (This deliberately reverses the pre-2026-09-15 rule
         "reason instead of the list": under report-only nothing is blocked, so hiding the
         list only keeps information from the human.)
      2. **One "was it abandoned?" test.** A blank or whitespace-only `abandoned` value —
         which a session can write straight into its own scratch file — is no reason: no
         abandon line is printed and the problem list still is. The reap and
         `stop_problems()` must not disagree about what counts as abandoned.
      3. **One bundle's failure never hides another's.** A bundle whose check raises (a
         `signoff-decision` that is not UTF-8, a directory where a file belongs) is listed
         as `<bundle>: could not check (<error>)` and every other registered bundle is still
         checked and reported.
      4. **A broken `[[doctor.checks]]` table is reported, and hides nothing.** Planner
         bundle checks read that table from `pdca.toml` as it is at reap time (the session
         may have edited it). If it cannot be read, the reap says so at **every planner
         session's reap** — whether the bundles were registered or not, and whether any of
         them carries a `brief.md` or not. A broken table is a real problem, and a batch
         that rightly left every issue UNPLANNED must still hear about it. The message names the
         cause and its actual effect: the file and table that failed, the error, and that
         the dependency clause was not checked. It must not claim the exit contract was not
         checked when the rest of it was. The checks that do not need the table — `Slug`,
         `Success criterion`, `Repo + branch target` for every authored brief — still run
         and are still reported next to it. One line for the table, however many bundles are
         registered.
  (e) **Nothing the session wrote is printed raw.** Every line the reap prints — the abandon
      reason and each problem item — has its non-printable characters escaped, so text a
      session controls (a `--abandon` reason, a dependency token quoted out of a brief)
      cannot use a terminal escape such as `ESC[8m` to conceal the lines that follow it.
  (f) **The suite stays quiet.** No test in the driver suite prints the reap report to the
      real stderr. Every test that drives `handoff.session` (or a function that does) over
      an undischarged contract captures it, as `test_handoff.py:323-328` already does with
      `redirect_stderr`. Confirmed today on the round-4 tree: the only remaining leaks are
      `template/tests/test_state_resolved.py:191` and `:217`. Check this by rule, not by the
      two names: run the whole driver suite and grep its stderr for `handoff:` — that is how
      those two were found, and how rounds 3 and 4 each missed the next pair.
  (g) **The prose is true.** No text promises Stop-hook enforcement to the model or the
      operator. Where the driver could not register a bundle set (the CSV/default batch
      planner, Act), `docs/01-render-and-integrate.md` and the `report_at_reap` /
      `stop_problems` docstrings say what the code does — the session must have named its
      work through a passing `/handoff`, and the re-read covers **every bundle the driver
      registered** — with no wider promise. Re-reading the briefs a CSV session authored is
      issue #549 and is not done here. **One exclusion, deliberate and not a finding:** the
      stale comment at `leaves.py:916-917` stays untouched for the ordering reason above. It
      is a developer comment, not text the model or the operator reads, and its twin at
      `leaves.py:1104-1108` IS corrected here. At least one test pins the part a reader cannot be
      trusted to re-check: the shipped text the MODEL reads — the rendered `/handoff` command
      body and the planner / sign-off leaf prompts — no longer tells it that a hook enforces
      the contract when a turn or session ends. (Round 4 satisfied this item but left it to
      review; with no test it can silently come back.)
  (h) `/handoff <id>` (`handoff_guard.py --check`) and `--abandon` keep working exactly as
      today: the model's self-check and the typed-abandon channel, verdict by exit status,
      nothing written into any bundle.
- **Falsifiability:** RED is reachable offline on the template driver suite, which the C4
  gate runs from `template/` with `PYTHONPATH=src` (`engine/scripts/run-verify.sh:183`). The
  gate reverts every non-test, non-docs path and keeps the tests, so the settings, hook and
  `handoff.py` hunks are all reverted on the red leg. Pre-fix: (a) fails because
  `settings.json` registers the Stop hook and `_stop_verdict` returns 2 for an undischarged
  contract; (b), (d) and (e) fail because `session()`'s `finally` (`handoff.py:306-311`)
  prints only an abandon reason and `stop_problems` returns `[]` whenever `abandoned` is set
  (`handoff.py:374-375`); (f) fails because the pre-fix reap prints nothing at all, so its
  red must be asserted on the post-fix behaviour (a test that drives a session and asserts
  the captured stream, not the real one). **Trap, verified in round 1:** if the hook fixture
  cannot load an instance config, the pre-fix hook takes its "contract check unavailable —
  allowing the stop" branch (`handoff_guard.py:59-62`) and exits 0, making the red leg a
  false green (C4 FAIL). The (a) test must first prove the contract check is live in that
  same environment (round 4 did this with `--check` → 1 at
  `test_handoff_reap.py:189`) and only then assert the no-argument exit. Two more properties
  of that gate, read from the script and true of the round-4 patch: the red leg needs **one**
  changed test module to fail, not all of them, so the quiet-wrapper edits required by (f)
  (which pass in both legs) are safe to ship; and every changed test module must still
  **import** with the production hunks reverted — a module that imports API this patch adds
  makes the whole gate UNVERIFIABLE (77) rather than red (`run-verify.sh:230-233`). Exercise
  new behaviour through existing API, as round 4 did.
- **Invariant to restore:** an interactive leaf's turn end always hands control to the human.
  No harness mechanism may turn a turn end into feedback to the model. The exit contract is
  judged at the session boundary — the leaf's process exit, where the driver reaps it — and
  its verdict goes to the human, not the model. Source: the Claude Code hooks reference (Stop
  runs "when the main agent has finished responding"; exit 2 feeds stderr back to the model)
  and #331's own framing that the question is "did the leaf discharge its contract when the
  session ended" (`handoff.py:3-7`). This holds for all four contract roles, not one module.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** none
- **Ordering note:** run 3 of `plan-0.60-bug-order.md`, one wave with 467, 480, 527 and 529.
  **#480 is still live** (tracker OPEN, milestone 0.60.0, confirmed 2026-09-16), so its
  `template/src/pdca_harness/leaves.py` change is still coming and this bundle stays out of its
  way. Its hunks, by the ranges in `results/issue_480/patch.diff`, are `do_plan` (old
  `:912-917`, `:924-930`), `do_plan_batch` (old `:1070-1078`, `:1126-1136`) and
  `run_plan_advisory_batch` (old `:3351-3356`, `:3358-3368`). So: **do not edit `do_plan` or
  `run_plan_advisory_batch` at all**, and in `do_plan_batch` change nothing inside those two
  hunk ranges. Concretely, the stale "Stop hook" comment at `leaves.py:916-917` **stays as it
  is** — it sits in 480's first hunk's context, and rewording it would stop that patch applying
  — while the same stale claim at `leaves.py:1104-1108` sits between 480's hunks and **is fixed
  here** (see criterion (g)). #508 and #528 (same hook/handoff family) and #549 (the CSV
  re-read) all come after this lands.
- **Surfaces:** data
- **Difficulty:** high
- **Scope:** remove turn-end enforcement of the interactive leaves' exit contract, judge it at
  the session boundary, and make that report obey the rules in the criterion. Files in reach:
  `template/.claude/settings.json` (the Stop registration),
  `template/.claude/hooks/handoff_guard.py` (the no-argument path; docstring),
  `template/src/pdca_harness/handoff.py` (the `session()` reap and the reporting it drives;
  module and function docstrings that describe a Stop hook), and the text that promises
  Stop-hook enforcement to the model or the operator: the `leaves.py` prompt strings in
  `_plan_prompt` (`:1035`), `_plan_batch_prompt` (`:1293`, `:1310`) and `_signoff_prompt`
  (`:3438`), the comments in `run_signoff` (`:3414`), `run_publish` (`:3628`) and
  `do_plan_batch` (`:1104-1108` only — see Ordering note),
  `template/.claude/commands/handoff.md.jinja:17-19`, and
  `docs/01-render-and-integrate.md:174-181`. Those prompts should say `/handoff` is the
  session's self-check and the driver reports an unmet contract to the human when the session
  ends. Criterion (d)(4) may change how `check_planner`'s dependency clause is invoked or
  reported from the reap — that is **in scope**, provided `/handoff`'s own behaviour and
  output are unchanged. Updating the driver suite to match is in scope and expected:
  `test_handoff.py::test_stop_hook_ships_and_is_registered` (`:133-141`) asserts the
  registration this fix removes and must be inverted; the module docstring's item (b)
  (`:10-11`) needs rewriting; `test_abandon_is_the_escape_hatch` (`:341-344`) asserts
  `stop_problems(...) == []` for an abandoned session, which criterion (d)(1) reverses, so it
  changes too; the other `StopVerdict` tests (`:331-362`) exercise `stop_problems()`, which
  stays, and must keep passing.
  / out of scope: `do_plan` and `run_plan_advisory_batch` in `leaves.py`, and everything inside
  480's two `do_plan_batch` hunk ranges — the single exception is the stale comment at
  `leaves.py:1104-1108`, which is in scope (see Ordering note and criterion (g)); **#549** — re-reading the briefs a CSV/default batch session authored
  (that needs a session-start snapshot, and is a separate slice); reopening a session,
  blocking, or changing any flow/state transition on an unmet contract; renaming
  `stop_problems`; the contents of the per-role checks `check_signoff` / `check_publisher` /
  `check_act`, and of `check_planner` beyond what (d)(4) requires; #508 (`/handoff` cannot run
  in a rendered instance) and #528 (Act vs `/handoff`); #492 `/interview`; #404 (a rendered
  `/abandon` command); this instance's own copy of the hook, which changes at its next
  `copier update`.
- **Repro instruction:** on `main`, from `template/`, with `PYTHONPATH=src`: set
  `PDCA_HANDOFF_ROLE=signoff` and a `PDCA_HANDOFF_STATE` file registering an empty bundle
  dir, load `.claude/hooks/handoff_guard.py` as a module, point its `_bootstrap` at a test
  `Config` whose signoff leaf is interactive, feed `{}` on stdin and call `main()` with no
  arguments: it returns 2 and prints "This signoff leaf session may not end yet". Separately,
  enter and exit `handoff.session(cfg, "signoff", [bundle])` with no `signoff-decision`
  written: nothing is printed. For (d)(1), `record_abandon(state, "out of time")` before the
  exit prints the reason and no problem list.
- **External dependencies:** none — base toolchain only (python3 ≥ 3.11, git); the hook
  protocol is exercised by running the script the way Claude Code runs it, so no Claude Code
  binary is needed. Known Do-environment limit, no detect command possible (no-check: it is a
  Claude Code tool-permission prompt, which a shell probe cannot observe): in rounds 1–3 the
  builder's Edit tool refused every write under `template/.claude/` as a "sensitive file",
  and a headless session cannot approve the prompt. The builder correctly did not route
  around it with a shell write; it built those three hunks from copies under the worktree's
  gitignored `.cache/`, so C4 at Check was the first run at the real paths. Do the same if it
  recurs, and say so in `build-notes.md` — do not silently work around it.
- **Test file:** `template/tests/test_handoff_reap.py` (new; the round-4 version is a good
  starting point and is preserved at `results/issue_534/iteration-v4/`), plus the sanctioned
  updates to `template/tests/test_handoff.py` described in Scope, and the capture wrappers in
  `template/tests/test_publish_slice.py` and `template/tests/test_state_resolved.py` required
  by criterion (f). Checked against the gate that will actually judge this: the instance's C4
  script derives its test set from the patch itself
  (`pdca-pdca engine/scripts/run-verify.sh:129-141` — every changed `template/tests/*.py`),
  reverts all other changed paths for the red leg (`:212-214`), and runs each module from
  `template/` with `PYTHONPATH=src` (`:183`) with no cfg/feature flag gating it. So a new file
  and edits to existing suites both earn their red here, and the tests named above do execute
  under the gate's own invocation. No base export applies: this is an ordinary single bundle
  on the brief's own branch target. Supplementary, advisory T3:
  the root render/update suites (`tests/test_render_and_run.py`, `tests/test_update_compat.py`),
  since `settings.json` is a rendered template file and `copier update` must still apply.
- **Citations expected:** Do cites `path:line` on `main` for every change.
  **Starting point:** `results/issue_534/iteration-v4/patch.diff` — the round-4 attempt, which
  satisfies (a), (b), (c), (d)(1), (d)(2), (d)(3) and (h), applies cleanly to `main` at
  `6ba00ba`, and passes the driver suite (1810 tests, verified 2026-09-16). Do MAY read that
  patch and start from it; what remains is (d)(4), (e), (f) and (g). Peer callsites: load the
  hook module in-process as `template/tests/test_handoff.py:143-147` does; build the contract
  `Config` with `_cfg()` at `test_handoff.py:83-104`; capture the reap report as
  `test_abandon_reason_is_reported_when_the_driver_reaps` does (`test_handoff.py:323-328`,
  `redirect_stderr` around `handoff.session`); take a session-start baseline the way the `act`
  role does at `handoff.py:281-285` if one is needed.
- **Prior-art check (triage cycles):** re-run by path on `origin/main` (fetched 2026-09-16,
  tip `6ba00ba`, unchanged since the round-4 attempt). `handoff_guard.py` and `handoff.py`
  have exactly one commit, `900d638` (#331/PR #398, which introduced them); `settings.json`'s
  last change is `a7df381` (permission rules, unrelated); `test_state_resolved.py`'s last
  changes are `9b224bd` / `27e9a73` (#302, unrelated). No open PR touches any of these files
  (open: #542, #543 — `progress.py` / `leaves.py` / `assemble.py` error-log work). No closed
  or merged PR references #534. `gh search issues stop_hook_active` finds only #534. Related
  open issues: #508, #528, #549 (filed from this session), #492, #404.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Why this is a re-plan (and what would end it)

Four Do rounds all passed every gate — C4 red→green, C5, T2, T3 — and each was sent back by
an advisory finding about the report's own behaviour, never by a broken fix. Three patterns
produced that:

1. The earlier brief specified the swap from *blocking* to *reporting* but not the rules a
   report must follow. The code underneath kept gate rules: an abandon lets you out (so hide
   the list), a broken check fails open (so say nothing), odd input is harmless (nobody reads
   it). Rounds 1–3 each rediscovered one of those. Round 3's was written into the brief
   itself, which required the abandon to replace the list. Criterion (d)–(g) now states them
   up front.
2. Fixes created the next round's findings: the round-4 doctor-table alarm came from the
   round-2 error-isolation fix, and the escape-code exposure only mattered because the
   round-3 fix moved the list after the reason.
3. Carry-forwards named line numbers rather than rules ("silence these two tests"), so the
   next review found the next instances of the same class.

For the reviewer and for sign-off: a finding that does not break one of the criterion items
above is a follow-up issue, not another round. The size backstop's "oversized → split" advice
does not fit this bundle — the sizer reports one outcome and the patch is inside the size
limit; the rounds came from review depth against a moving target.
