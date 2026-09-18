# Build notes — issue 534, iteration 3 / handoff-contract-checked-at-reap-not-turn-end

Target: `eduralph/pdca-harness @ main` (`6ba00ba`, the same base as iterations 1 and 2).
Cites are on that commit unless marked "post-patch" (the worktree with the patch applied).

NEEDS-HUMAN external dependency: write permission for `template/.claude/**` in the Do worktree — the Edit tool was refused again this iteration (tried on `template/.claude/settings.json`; the session is non-interactive, so the prompt could not be approved), so the three `.claude/` hunks were never applied at their real paths in Do. The 4 tests that read those files (5 failures: `test_handoff_reap.NoTurnEndIsIntercepted` x3, one with two subtests, plus `test_handoff::test_hook_ships_and_is_not_registered_on_stop`) and the root render slice were green in Do only against copies. C4 and T3 at Check, where the driver applies `patch.diff` itself, are the real-path run. Iterations 1 and 2 both passed C4 and T3 with byte-identical `.claude/` hunks.

No `[[doctor.checks]]` row is proposed, for the same reason as iteration 2. This instance
has `dependency_halt = true`, so a row whose cmd exits non-zero would CONFIRM the claim
and send the bundle down the close fast path with N/A gates. That skips C4, the one run
that applies the `.claude/` hunks at their real paths. A shell probe also cannot see a
Claude Code permission prompt. In iteration 2 the claim was adjudicated "unconfirmed" and
the normal gates ran (`iteration-v2/dependency-adjudication.json`). The fix belongs on the
harness side: let the builder write `.claude/` paths when the brief's Scope names them, or
have Plan flag such bundles.

I did not write any `.claude/` path through the shell to get around the refusal. The
three `.claude/` hunks are copied unchanged from iteration 2's `patch.diff` (the sign-off
said to keep the approach as is). The new patch reproduces them byte for byte (checked
below).

## What changed in this iteration

Only the sign-off's §6.2 finding: one bundle whose check raises hid the whole batch report.

**The defect.** `stop_problems` checked every registered bundle in one loop with no
per-bundle guard (main `handoff.py:388-391`; iteration 2 `:445-447`), and `report_at_reap`
wrapped the whole call in one `try`. Any exception from one bundle therefore replaced
every other bundle's result with one "could not check … — nothing reported" line that did
not name the broken bundle. Realistic triggers: the checks read the bundle's artifacts as
UTF-8 text (`leaves.py:3507`, `:3521`; `handoff.py:140`, `:159`; `cli.py:1172`, `:1188`;
`brief.py:62`), so a file saved in another encoding raises `UnicodeDecodeError`, and a
directory in a file's place raises `IsADirectoryError`.

**The fix** (all in `template/src/pdca_harness/handoff.py`):

1. Per-bundle catch inside the loop (post-patch `:466-472`). A bundle whose
   `check_bundle` raises adds `"<bundle>: could not check (<Type>: <message>)"` to the
   list, and the loop carries on. That is the format the sign-off named.
2. Planner pre-read (post-patch `:458-464`), so that a config-wide failure stays one
   line, as the sign-off asked ("keep config-wide failures as the one line
   `test_handoff_reap.py:358` expects"). The trap: that test's failure is **not**
   outside the loop. It breaks `pdca.toml` (`doctor = 1`), and the read that fails
   happens inside `check_planner` for each bundle (`handoff.py:123` →
   `doctor.py:355` → `config.py:551`, where `1.get` raises `AttributeError`; only
   `OSError` / `TOMLDecodeError` fall back, `config.py:549`). So a plain per-bundle
   catch turns the one-line note into a header plus `issue_7: could not check
   (AttributeError …)`, which is 2 lines, and 3 for a two-bundle batch. The mutation run
   below shows exactly that. The fix reads the one input every planner bundle check
   shares, the `[[doctor.checks]]` rows (`doctor.registered_ids(cfg)`,
   `doctor.py:315-331`, the same call `check_planner` reaches), once, before any bundle.
   A broken table then raises out of `stop_problems`, and `report_at_reap` prints its
   one line as before. Signoff and publisher checks read nothing config-wide
   (`cli.contribution_problems` reads only bundle files, `cli.py:1162-1193`), so they get
   no pre-read, and a broken `doctor` key cannot hide their reports.
3. `_error_text(exc)` (post-patch `:281-285`) is the one "Type: message on one line"
   formatter. The per-bundle entry and the whole-check note both use it (post-patch `:471`
   and `:364`; iteration 2 built the string inline in `report_at_reap`), so the two
   cannot drift apart.
4. Docstrings: `stop_problems` (post-patch `:434-440`) and `report_at_reap` (post-patch
   `:350-352`) now describe the per-bundle / config-wide split. The test module's item
   (c) is updated to match (post-patch `test_handoff_reap.py:21-24`).

**Tests** (`template/tests/test_handoff_reap.py`, class `ReportOnly`):

- `test_a_bundle_that_cannot_be_checked_does_not_hide_the_others` (post-patch `:364-403`).
  This is the two-bundle test the sign-off asked for, as three subtests:
  - signoff, where issue_7's decision is `iterate-do` plus a rationale saved as cp1252
    (the adversary's exact case), and issue_8 is `iterate-do` with no rationale;
  - signoff, where issue_17's `signoff-decision` is a directory;
  - planner, where issue_27's `brief.md` is cp1252 and issue_28's brief has an empty
    Success criterion.

  The planner and signoff cases are the two malformed-but-present cases that only the
  reap report catches (brief, criterion b). Each subtest first asserts that the broken
  bundle's check really raises and captures the exception type. It then reaps in both
  registration orders and asserts that the other bundle's problem is printed, that the
  broken bundle is named as `could not check (<that type>: …`, and that the whole-check
  "nothing reported" note is absent.
- `test_a_broken_config_is_one_line_for_the_whole_batch` (post-patch `:405-420`): a
  two-bundle planner batch with `doctor = 1` gives exactly one line and names neither
  bundle. The existing one-bundle test pins this too; this one pins "not once per bundle".
- `test_a_check_that_fails_is_a_one_line_note` is unchanged. Its one-line assertion is
  now at `:360`; it was `:358` in iteration 2, and the module docstring grew by two lines.

## Carried over unchanged from iteration 2

Six of the eight files are byte-identical to iteration 2's patch. `diff` of the two
patches shows changes only in the `handoff.py` and `test_handoff_reap.py` sections.

- `template/.claude/settings.json:60-71`: the Stop registration is removed. Post-image
  blob `66057af`, the same as iteration 2.
- `template/.claude/hooks/handoff_guard.py`: `_stop_verdict` (`:48-73`) is gone. The
  no-argument call exits 0 silently, and an unknown argument exits 2. Post-image `f6f6fb6`,
  mode `100755`.
- `template/.claude/commands/handoff.md.jinja:17-19` (post-image `f3947ee`),
  `docs/01-render-and-integrate.md:177-182`.
- `template/src/pdca_harness/leaves.py`: prompt text and comments only. It is still
  outside `do_plan` (`:904-927`), `do_plan_batch` (`:1055-1133`) and
  `run_plan_advisory_batch`. The stale comments at `:916-917` / `:1104-1108` stay for
  issue 480.
- `template/tests/test_handoff.py`: docstring (b) and the inverted
  `test_hook_ships_and_is_not_registered_on_stop` (`:133-141`).
- `handoff.py` hunks from iterations 1 and 2 are kept as they were: the `registered`
  override at reap, the shared `_abandon_reason` test, and the `check_planner`
  docstring.

## Evidence

The runs used the instance venv's Python (3.14.4). Targeted runs use the same per-module
command `engine/scripts/run-verify.sh:183` uses (`cd template && PYTHONPATH=src python3 -m
unittest tests.<module>`), bounded by `timeout 600`. Logs are in the worktree's gitignored
`.cache/534/`.

- **Patch integrity.** 8 files, 56,989 bytes. It applies cleanly to `6ba00ba` in a
  throwaway index with `--whitespace=error`. The post-image blobs of `handoff.py`
  (`e1e7c7d`) and the test (`69c96ad`) equal the tested worktree files. The three
  `.claude/` post-images equal the staged copies the sanity pass ran (`66057af`,
  `f6f6fb6`, `f3947ee`). All changed Python parses, and `settings.json` is valid JSON.
- **C4-shaped red leg** (production hunks reverted in place, tests kept, `.claude/` at
  main): 55 tests ran, 25 failures (subtests counted), no `_FailedTest`. That includes
  all 3 subtests of the new per-bundle test and the new batch-config test: main's reap
  prints nothing. The tree was restored and checked against the post-image hashes
  (`red-leg.log`).
- **Red for this iteration's finding** (the new tests against iteration 2's `handoff.py`,
  blob `6749a43`, in a scratch copy of the package): all 3 per-bundle subtests FAIL with
  the adversary's symptom. For example: `"issue_8: decision 'iterate-do' has no
  rationale" not found in "handoff: could not check the signoff session's exit contract
  (UnicodeDecodeError: …) — nothing reported"`. The directory case shows the same with
  `IsADirectoryError`, and the planner case with `issue_28`'s empty criterion. The two
  one-line tests pass there, as expected, because iteration 2 already gave one line
  (`red-vs-v2.log`).
- **Mutation: the fix without the planner pre-read.** `test_a_check_that_fails_is_a_one_line_note`
  fails (2 lines) and `test_a_broken_config_is_one_line_for_the_whole_batch` fails
  (3 lines). So the pre-read is what keeps config-wide failures at one line
  (`mut-nopre.log`).
- **Green at real paths** (worktree = full patch except the three `.claude/` files): 55
  ran, 5 failures. They are exactly the `.claude/`-reading tests named in the NEEDS-HUMAN
  line. Every other test passes, including all of `ReportedAtReap` and `ReportOnly`.
- **Sanity pass against the copies** (not a substitute for C4): both modules, unmodified,
  with `HOOK` / `SETTINGS` / `COMMAND` pointed at `.cache/534/stage/`
  (`.cache/534/sanity_run.py`): 55/55 OK.
- **T3 runner** (`engine/scripts/run-suite.sh`, `PDCA_WORKTREE` = this worktree,
  `suite.log`):
  - Driver suite: 1808 tests (iteration 2's 1806 plus the 2 new ones), 5 failures (the
    same five), 2 skipped.
  - Root suite: 24 tests, 1 failure, `test_render_then_slice`. That is the same five
    seen through the rendered instance (its slice: 1808 tests, 5 failures, 10 skipped).
  - All 5 `test_update_compat` cases pass, but with `settings.json` at main they do not
    exercise the settings change. Iterations 1 and 2 passed T3 at Check, where they did.
- **T2 runner** (`engine/scripts/run-docs-check.sh`): docs lint clean, site render and
  link audit clean. The docs hunk is unchanged from iteration 2.
- **Commit-readiness.** The target has no formatter, linter or pre-commit config: no
  `pyproject.toml` / ruff / flake8 / `.pre-commit-config.yaml`, no installed git hooks,
  and CI is docs lint + render + render check + linked issue. Every line this iteration
  adds is 88 characters or fewer. Lines carried over from iteration 2 run to 92, within
  the target's existing width (`leaves.py` runs to 110). The one commit requirement is
  the DCO sign-off (`git commit -s`, `CONTRIBUTING.md:7-17`), which publish applies.

## Refuting my own test

- **(a) Genuine red? Yes.** With the production hunks reverted, 25 failures across the
  55 tests, including every subtest of the new per-bundle test and the batch-config test.
  The sharper red for this iteration: against iteration 2's `handoff.py`, the three
  per-bundle subtests fail with exactly the reported defect (the one-line note replaces
  `issue_8`'s problem). A mutation that drops the pre-read turns both one-line tests red.
- **(b) Production path? Yes.** The tests drive the real `handoff.session` context
  manager that `leaves.py` wraps around every contract leaf (`leaves.py:918`, `:1110`,
  `:3416`, `:3466`, `:3562`, `:3630`), the real `report_at_reap`, `stop_problems` and
  `check_bundle`, and the real `doctor` / `config` reads. There are no mocks in the new
  tests. The only stand-in is the hook-file location for the `.claude/`-reading tests in
  Do's sanity pass; C4 closes that.
- **(c) Fixture includes the fault? Yes.** The broken bundle really raises: each subtest
  asserts `check_bundle` raises on it before reaping, through the real UTF-8 read or a real
  directory. The other bundle really carries the malformed-but-present artifact that must
  still be reported. Both registration orders are reaped, so the broken bundle is first in
  one of them, which is the order that hid `issue_8` before. The config test uses a
  really broken `pdca.toml` that the real `current_doctor_checks` reads.

## Alternatives ruled out

- **Plain per-bundle catch, no pre-read** (the 4-line loop change alone, against the
  shipped 4-line loop change plus the 7-line pre-read). Rejected: it breaks the one-line
  rule the sign-off kept. The mutation run shows the `:360` test at 2 lines and a
  two-bundle batch at 3.
- **Collapse "every bundle failed the same way" into the one line**, in `report_at_reap`
  (about 8 lines). Rejected: it guesses the cause instead of knowing it. With one
  bundle it is always true, so a single bundle's unreadable decision would lose its
  bundle name, the second half of the adversary's finding. Messages that include a
  path (`IsADirectoryError: … '/…/issue_7/signoff-decision'`) differ per bundle, so it
  would not fire for them anyway.
- **Catch only file errors (`OSError`, `UnicodeDecodeError`) per bundle** (the same 4
  lines with a narrower `except`). Rejected: the exception type does not tell you the
  cause. A non-UTF-8 `pdca.toml` raises `UnicodeDecodeError` from `config.py:548` (not
  caught at `:549`) and would be blamed on each bundle. A parser bug that raises
  `IndexError` on one odd brief would still hide every other bundle, which is the finding
  itself.
- **Hand the pre-read rows to `check_planner`**, so the check does not read them a second
  time. That means changing the signatures of `check_planner`, `doctor.unregistered_dependencies`
  and `doctor.failing_dependencies` (3 functions, about 10 lines), and the brief puts the
  per-role checks out of scope. The double read costs one small TOML parse per planner
  reap.
- **Loop over the bundles in `report_at_reap` instead of in `stop_problems`** (about 10
  duplicated lines of dispatch). Rejected: the sign-off said inside the loop, and a
  second copy of the dispatch could drift from the first, the same problem
  `_abandon_reason` fixed in iteration 2.

## Known edges (not changed)

- A planner batch whose briefs are all legitimately absent (`require_artifact=False`)
  still runs the pre-read. If the session broke `pdca.toml`'s `doctor` table, the reap
  prints the one-line note even though no bundle needed the table. The note names the
  error, and the next `pdca` run would fail on the same key anyway (`Config.load`,
  `config.py:744`).
- A bundle that cannot be checked is listed under the existing header "ended with its
  exit contract not discharged". An artifact the driver cannot even read is not a
  discharged contract, so I kept the header.
- Two existing `test_handoff.py` session tests (`:299-308`, `:315-321`) print their reap
  report to the console because they do not capture stderr. They pass. This was already
  the case in iteration 2; I left them alone to keep the diff to the finding.

## Housekeeping

- Working files are in the worktree's gitignored `.cache/534/`: `patch.diff`,
  `claude-hunks.diff`, `stage/` (the post-patch `.claude/` copies), `v2src/` and
  `nopre/` (scratch package copies for the targeted red and the mutation),
  `sanity_run.py`, logs (`red-leg.log`, `red-vs-v2.log`, `mut-nopre.log`,
  `green-realpaths.log`, `sanity.log`, `suite.log`, `docs-check.log`) and throwaway index
  files. I left them for the harness to reclaim, and ran no `rm`.
- The patch was assembled in a throwaway index (`GIT_INDEX_FILE`). The worktree's real
  index is untouched (still at HEAD; the new test file is untracked). The only other git
  side effect is loose blobs in the object store.
- No commit, no push, no PR.
