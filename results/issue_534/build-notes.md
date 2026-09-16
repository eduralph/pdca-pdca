# Build notes — issue 534 (Do round 5, after the 2026-09-16 re-plan)

Target: `eduralph/pdca-harness @ main`, base `6ba00ba`. Worktree:
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`. Unless a line says otherwise, "base `x:N`" is
the file on `main` and "`x:N`" is the patched file.

## What the patch does

Turn ends are no longer intercepted: the Stop registration is gone from
`template/.claude/settings.json` (base `:60-71`), and the hook's no-argument path is now
an inert `return 0` (`template/.claude/hooks/handoff_guard.py:77-79`; base `_stop_verdict`
`:48-73` and its call at `:101` removed). The exit contract is judged when the driver reaps
the session: `handoff.session()`'s `finally` (`template/src/pdca_harness/handoff.py:396-412`)
calls `report_at_reap()` (`:415-458`), which prints the abandon reason first and then
everything `stop_problems()` (`:512-566`) finds. It never blocks, writes, or raises. The
model-facing and operator-facing text no longer promises Stop-hook enforcement.

## Starting point

The brief allows starting from `results/issue_534/iteration-v4/patch.diff`. I applied it
(it still applies cleanly at `6ba00ba`), kept what it did for (a), (b), (c), (d)(1)-(d)(3)
and (h), and built (d)(4), (e), (f) and (g) on top. I read only that patch and the brief,
plus the target files, the gate scripts the brief cites (`engine/scripts/run-verify.sh`,
and the docs/C5 gate scripts to run them), and the two peer callsites in
`template/tests/test_handoff.py` it names. I did not read the round-4 review or notes.

## Criterion by criterion

**(a) No turn end is intercepted.** `settings.json` has no `hooks` key. The hook with no
arguments exits 0 and prints nothing without reading stdin
(`handoff_guard.py:77-79`), so an instance whose `settings.json` kept the old
registration through a `copier update` merge cannot deadlock either. I also added a usage
error for an unknown mode (`:73-76`, exit 2). Before, any unknown argument fell through to
the Stop verdict (base `:101`). The old registration passed no arguments (base
`settings.json:66`), so this cannot touch a turn end, and a typo like `--abandn "why"` no
longer silently records nothing. Tests: `test_handoff_reap.py:209`, `:228`, `:263`. The
liveness guard the brief calls a trap (base `handoff_guard.py:59-62`) is checked first in
the same environment: `--check` must return 1 (`:239-244`, and `:281-285` for the real
subprocess) before the no-argument exit is asserted.

**(b) Reported at reap.** `report_at_reap` prints `handoff: the <role> session ended;
checking its exit contract found (a report only, the driver carries on as usual):` and
then one `  - <bundle>: <problem>` line per item (`handoff.py:450-454`). A discharged
contract with no abandon prints nothing. Tests: `ReportedAtReap`,
`test_handoff_reap.py:297-378`.

I changed round 4's header ("ended with its exit contract not discharged"). With (d)(4), a
planner session whose only item is the unreadable doctor table (for example a batch that
rightly left every issue UNPLANNED) would have been told its contract was "not
discharged", which is the over-claim (d)(4) forbids. "Checking its exit contract found" is
true for every kind of item: unmet, could-not-check, and not-checked.

**(c) Report only, never raises.** The reap writes nothing and moves nothing. Nothing
raises out of the context manager:
- the whole report sits in one `try`, and failures become one line (`handoff.py:444-458`);
- printing goes through `_emit` (`:317-324`), which swallows a stderr that cannot be
  written;
- two holes found while writing the tests and closed here: a scratch file the session
  rewrote as deeply nested JSON makes `_read_json` raise `RecursionError`, which is not a
  `ValueError` and so is not caught by base `:227`. It escaped the base `finally` at
  `:307`, and round 4's at the same place. It is now guarded at `:403-406`. A scratch
  path the session replaced with a directory made `path.unlink` raise (base `:311`). That
  is now a printed line (`:408-412`).

Tests: `ReportOnly`, `test_handoff_reap.py:384-456`. The whole-check failure line cannot be
reached with real input any more (each bundle and the doctor table are contained), so
`:403` injects it by patching `handoff.stop_problems` to raise. Everything else uses real
failures.

**(d)(1) An abandon never hides the list.** Base `stop_problems` returned `[]` whenever
`abandoned` was set (base `:374-375`). That is removed, and `stop_problems` does not read
`abandoned` at all. The reason line is appended before the check runs (`:446-449`), so a
failing check cannot take it down. Tests: `:464`, `:488`, plus `test_handoff.py:352`
(inverted from `test_abandon_is_the_escape_hatch`, as Scope asks).

**(d)(2) One abandoned test.** `_abandon_reason` (`handoff.py:282-292`) is the only reader,
and a blank or whitespace value is no reason. Test: `:500`.

**(d)(3) One bundle's failure never hides another's.** Each bundle's check runs in its own
`try` (`:556-561`) and becomes `<bundle>: could not check (<Type>: <msg>)`. Test: `:518`,
using real failures (a cp1252 file, a directory in the file's place) in both
registration orders.

**(d)(4) A broken `[[doctor.checks]]` table.**
- `_doctor_table_problem` (`handoff.py:327-350`) reads the table the way the dependency
  clause does, via `doctor.registered_ids` (`template/src/pdca_harness/doctor.py:315-331`).
  It does this once, at every planner reap, before the bundle check, whether or not
  bundles were registered and whether or not briefs exist (`stop_problems`, `:547-549`).
- If the read fails, the result is ONE item:
  `<root>/pdca.toml: the [[doctor.checks]] table could not be read (<Type>: <msg>), so the
  dependency clause was not checked — no brief's External dependencies were matched to a
  registered row or probed`. It names the file, the table, the error and the actual
  effect, and nothing wider.
- Every registered brief is then still checked with `check_planner(...,
  dependencies=False)` (`:552-555`). That new keyword (`:102-141`) skips only the
  dependency clause (`:138-140`), so Slug, Success criterion and Repo + branch target
  (plus missing/placeholder) still run and are reported next to the table line.
- `/handoff` is unchanged: `run_check` still calls `check_bundle(role, d, cfg)` with no
  keyword (`:496`), so on a broken table it raises exactly as before. The test pins that
  (`:597-602`).
- One case I added beyond the literal wording: a `pdca.toml` that exists but does not
  PARSE. `Config.current_doctor_checks` (`template/src/pdca_harness/config.py:547-551`)
  silently falls back to the rows loaded at startup on `TOMLDecodeError`, so the reap
  would have checked briefs against a table the session no longer has and said nothing.
  That is the "broken check stays quiet" pattern the re-plan names. So
  `_doctor_table_problem` parses the file itself when it exists (`:342-343`). A missing
  `pdca.toml` is left to the fallback: every synthetic test `Config` has none, and
  reporting it would put a line on every planner reap in the suite.
- Tests: `:588` (four ways the read raises: `doctor` not a table, `checks` not an array,
  a row not a table, not UTF-8), `:605` (does not parse; `/handoff` still FAILs against
  the startup rows, as before), `:623` (id-seeded batch with no briefs, single Plan with a
  discharged brief, CSV session with a `/handoff` pass, CSV session with none: always
  exactly one table item).

**(e) Nothing printed raw.** `_printable` (`handoff.py:303-314`) escapes every character
`str.isprintable()` rejects, using `unicode_escape` (`\x1b`, `\n`, `\u202e`). `_emit`
applies it to every reap line, including the header, the reason, each item and the
failure lines. Escaping happens at print time, not when items are built, so `/handoff`
output is unchanged. The `reap()` helper checks the rule on every reap in the file
(`test_handoff_reap.py:187-190`). Targeted tests: `:664` (reason `out of time\x1b[8m\n  -
issue_7: all clear` + U+202E: printed escaped on one line, no forged item, real items
still follow) and `:685` (a backticked dependency token containing ESC, quoted from a
brief).

**(f) The suite stays quiet.** The capture wrappers are
`template/tests/test_state_resolved.py:208`, `:217`, `:244` (the two leaks the brief
names; the first test reaps twice), plus round 4's `test_publish_slice.py:1048` and
`test_handoff.py:308`, `:327`. Checked by rule, as asked: the whole driver suite with the
patched `.claude` copies ran 1817 tests, OK (2 skipped), and `grep -c handoff` over its
captured stderr and stdout gave **0** and **0**. Run through the standard `unittest
discover` at the real (unpatched) `.claude` paths, the stderr also had 0 `handoff:` lines.

**(g) The prose is true.**
- Model-facing: `leaves.py` prompts `_plan_prompt` `:1035-1036`, `_plan_batch_prompt`
  `:1294-1295` and `:1311-1312`, `_signoff_prompt` `:3440-3442`, `_signoff_batch_prompt`
  `:3496-3499`, `_publish_prompt` `:3699-3701`; the `/handoff` command body
  (`template/.claude/commands/handoff.md.jinja:17-23`); the hook's `--abandon` reply
  (`handoff_guard.py:70-71`; base `:98-99` said "the session may now end").
- Comments: `run_signoff` `:3416-3418`, `run_signoff_batch` `:3468-3469`, `run_publish`
  `:3633-3635`, and the `do_plan_batch` twin at base `:1106-1107` (now `:1107-1108`).
- As the brief orders, base `leaves.py:916-917` is untouched.
- The command body, `docs/01-render-and-integrate.md:175-191`, and the `report_at_reap` /
  `stop_problems` docstrings now say what the code covers: a re-read of every bundle the
  driver registered; where it registered none (CSV/default batch Plan, Act), a check that
  a `/handoff` passed and no re-read. I removed round 4's "so a session can't close
  silently with a bad artifact" (not true for a CSV session, whose re-read is #549), and
  an "only checks that a `/handoff` passed" I had written myself: a planner reap also
  reads the doctor table.
- The pin: `ModelFacingTextPromisesNoEnforcement` (`test_handoff_reap.py:727-766`) runs
  one rule, `_ENFORCEMENT_CLAIM` (`:699-705`), over the command body, all six contract
  prompts plus `_act_prompt`, and the hook's `--check` FAIL and `--abandon` replies. So
  that the rule cannot quietly stop matching, `:752` requires it to catch every retired
  #331 sentence verbatim, plus four rewordings (`:709-724`).

**(h) `/handoff` and `--abandon` unchanged.** `run_check` is not touched. `--abandon` keeps
its checks and exit codes (`handoff_guard.py:57-72`); only its reply text changed, per (g).
Tests: `:773`, `:785` (the second also checks the bundle is untouched).

## The `.claude/` write limit recurred, and how I handled it

The first Edit on `template/.claude/settings.json` was refused ("Claude requested
permissions to write … but you haven't granted it yet"). A plain `cp` out of `.claude/`
also asked for approval. As the brief instructs, I did not route around it with a shell
write into `.claude/`:
- I exported the three base files with `git show HEAD:<path> > .cache/issue534-claude/…`
  and edited the copies with the Edit/Write tools.
- I built `patch.diff` from a temporary index (`.cache/issue534-build-patch.sh`): `git
  add` for ordinary files, and `git hash-object -w` + `git update-index --cacheinfo` for
  the three copies (keeping mode 100755 on the hook). Only git objects and the temporary
  index were written. No path under `.claude/` was written.
- Checks on the result: `git apply --cached --check` on a fresh index at `HEAD` passes.
  After applying, the three `.claude` blobs are byte-identical to the copies (`cmp`), and
  the worktree equals base + patch for every other path.
- Green runs used `.cache/issue534-run-with-claude-copies.py`, which imports the test
  modules and points only the `HOOK`, `SETTINGS` and `COMMAND` constants that name those
  three files at the copies (my first version also redirected `test_guard_shim`'s
  unrelated `HOOK`; I fixed that).

Consequences for Check:
- **C4 at Check is the first run of the `.claude`-dependent tests at the real paths.** At
  the unpatched real paths exactly 7 cases fail locally, and all of them need the patched
  files: `test_handoff.py:136`, `test_handoff_reap.py:209`, `:228` (2 subtests), `:263`,
  and `:757` for the command body and the `--abandon` reply.
- **The T3 root suites** (`tests/test_render_and_run.py`, `tests/test_update_compat.py`)
  were not run. They `shutil.copytree` the working tree (`tests/test_render_and_run.py:43`),
  whose `.claude/` files are unpatched here, so a local run would test a different tree.
  `settings.json` is still valid JSON, and the command body has no Jinja syntax (checked).

## Verification evidence (all against the final `patch.diff`)

- **C4 green** (runner with copies; the 4 changed modules): Ran 158, OK.
- **C4 red**, reproduced the way `run-verify.sh:212-221` does it: `git apply -R
  --exclude='tests/*' --exclude='template/tests/*'` (plus `template/.claude/*`, which is
  already base on disk), then `cd template && PYTHONPATH=src python3 -m unittest
  tests.<mod>`, then restore:
  - `test_handoff`: rc=1, ran 35, load failures 0 (2 failures);
  - `test_handoff_reap`: rc=1, ran 29, load failures 0 (46 failures, 2 errors);
  - `test_publish_slice` and `test_state_resolved`: rc=0 in both legs (the quiet
    wrappers, as the brief expects);
  - no changed module imports API this patch adds, so no module fails to load.
- **Whole driver suite** with copies: 1817 OK (2 skipped); 0 lines mentioning `handoff`.
- **T2**: `docs/publishing/tools/lint_docs.py` OK; `render_site.py --check` link audit OK.
- **C5** (`run-prod-path.py`): "1 added driver-suite test(s) import the production package".
- `git diff --check`: clean. A tokenizer scan for 3.12-only f-string syntax: none.
- Only Python 3.14.4 is installed here, so 3.11 and 3.12 were not run. CI uses 3.12.
- **Ordering with #480**: `results/issue_480/patch.diff` still applies on top of this
  patch (`git apply --cached --check`, rc 0, line offsets only).

## Refuting my own test

- **(a) Genuine red? Yes.** With the production hunks reverted (above), `test_handoff_reap`
  fails 46 cases plus 2 errors, and `test_handoff` fails 2, with no load failures. The
  red covers every criterion: (a) the four NoTurnEnd cases, (b) all eight ReportedAtReap
  problem cases, (c) `:385`, `:403`, `:424`, (d)(1) `:464`, (d)(2) `:500`, (d)(3) `:518`,
  (d)(4) `:588`, `:605`, `:623`, (e) both, (g) the command body, six prompts and the
  `--abandon` reply. Green in both legs, by design, because they pin behaviour the old
  code already had: `:368` (discharged prints nothing), `:449` (the leaf's own exception
  passes through), `:488` (an abandon with nothing unmet prints only the reason), `:752`
  (the rule's self-check) and both (h) tests.
- **(b) Production path? Yes.** Every reap goes through the real `handoff.session()` and
  real `stop_problems` / `check_*` / `doctor.registered_ids`. The hook runs in-process
  from its file, and once as a real subprocess exactly as the old registration spelled it
  (`:263`). The prompts come from the real `leaves._*_prompt` builders and the command
  body from the shipped file. The only injected fault is `:403` (patched `stop_problems`
  raises), and it exists because no real input reaches that line any more.
- **(c) Fixture includes the fault? Yes.**
  - The Stop test first proves the contract check is live (`--check` → 1 in the same
    environment) before asserting exit 0.
  - Each broken-table fixture is proven broken by making `check_planner` raise and
    `run_check` raise the same type; the unparseable one by `tomllib.loads` raising.
  - Each could-not-check fixture is proven by `check_bundle` raising.
  - The escape fixtures carry real ESC and U+202E characters.
  - Every "report only" subtest asserts its contract is undischarged first.

## Alternatives I ruled out

- **Read the doctor table in `report_at_reap` and pass the result into `stop_problems`.**
  That means two readers of one fact: the same "reap and `stop_problems` disagree" shape
  (d)(2) rules out for `abandoned`. It also moves the table item out of `stop_problems()`'s
  list, which (b) defines as what gets printed. The cost is a new `stop_problems(...,
  table_problem=None)` keyword plus a read and pass in `report_at_reap` (about 6 lines),
  with no gain.
- **Hand the pre-read rows to `doctor.unregistered_dependencies` /
  `failing_dependencies`**, so the clause reuses the reap's single read. Both are shared
  with the pre-dispatch guard and assemble (`doctor.py:334-409`, #333/#340/#341), and
  Scope keeps check contents out of reach. The only gain would be closing a sub-second
  window in which the table breaks between the two reads. If that happens, it shows up as
  that bundle's "could not check" item; nothing is hidden.
- **Make `Config.current_doctor_checks` stop falling back on a parse error.** That fallback
  is documented behaviour for assemble ("so this never crashes an assemble",
  `config.py:544-545`), and changing it would change `/handoff` and assemble. The parse
  check lives in the reap only (`handoff.py:342-343`, 2 lines).
- **`repr()`-style escaping.** It also doubles backslashes and adds quotes, which garbles
  detect commands and paths quoted in items. Only non-printable characters can drive a
  terminal, so `isprintable()` is the exact boundary.
- **Escaping inside the `check_*` functions.** That would change `/handoff`'s own output,
  which (d)(4)/(h) forbid.
- **Catching `RecursionError` inside `_read_json`** (base `:227`). `_read_json` also
  serves `/handoff` (`load_state`, `record_pass`, `_update_state`), so that would change
  `/handoff` in that edge case. The guard went into the reap instead (4 lines, `:403-406`).
- **Discharging the contract in the two `test_state_resolved.py` fakes** by recording a
  `/handoff` pass, so they print nothing. Their fake briefs have no Success criterion, so
  a real `/handoff` would FAIL; recording a pass would fake session behaviour. Capturing
  stderr is what (f) asks for.
- **A test that runs the whole suite to enforce (f).** A nested 30 s run of 1817 tests
  inside one test is not worth it. The rule check is the grep above, which Check can rerun.

## Observations outside this slice (not changed)

- Two unrelated tests fail when `TMPDIR` is inside a harness worktree, because they assert
  a temp path does not contain `.pdca-wt` / `.pdca-`: `test_leaf_workspace_admission.py:327`
  and `test_sweep.py:107`. I hit this when I pointed `TMPDIR` into the worktree's `.cache/`.
  With the default `TMPDIR` both pass. It could surprise anyone running the suite from a
  lane worktree with `TMPDIR` set there.
- Early on, one ad-hoc probe script created `/tmp/tmpd3y28g0g` (a tiny `results/issue_7/
  brief.md`) before I switched to `TMPDIR` under the worktree. I did not remove it. The
  whole-suite runs used the default `TMPDIR`, where the tests clean up after themselves.
- Local helpers left in the worktree's gitignored `.cache/` (not in the patch):
  `issue534-claude/` (the edited `.claude` copies), `issue534-run-with-claude-copies.py`,
  `issue534-build-patch.sh`, `issue534-index*` (temporary indexes), `issue534-logs/`,
  `issue534-site/`, `issue534-tmp/`.
