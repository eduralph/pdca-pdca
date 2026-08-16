# Build notes — issue 495 / truthful-copier-skip-and-no-silent-green

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All edits made in the cycle
worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`; every `path:line` below is that tree
(post-patch), except where marked "on base".

## 1. What shipped

One answer, four files of mechanism plus two consumers:

| File | Role |
|---|---|
| `tests/copier_support.py` (new, 70 lines) | imports copier **at the point of use** and raises `unittest.SkipTest` with the condition that actually stopped the run (`:37-57` reason, `:59-70` import) |
| `tests/run_root_suite.py` (new, 129 lines) | the root-suite entry point that can answer "could not tell": exit `77` + `PDCA-UNVERIFIABLE:` (`:52-95` classify, `:98-125` main) |
| `tests/test_copier_availability.py` (new, 374 lines, 16 cases) | the brief's regression module — supplies the import outcome and the `PATH` lookup itself |
| `tests/test_render_and_run.py` `:23-26`, `:33`, `:45` | probe deleted; `copier = import_copier()` first statement of the body; `copier.run_copy(…)` |
| `tests/test_render_cli_name.py` `:44-47`, `:53`, `:65` | same |
| `tests/test_update_compat.py` `:35-39`, `:210`, `:213`, `:223`, `:236` | same, reached from `setUpClass` via `render_prior_edit_and_update` (`:205`); class decorator gone |
| `.github/workflows/render-check.yml` `:36-46` | both steps run through the entry point, same module selection, `fetch-depth: 0` untouched (`:27`) |
| `CONTRIBUTING.md` `:27-34` | names the root-suite command, what it needs, and what a `77` means |

Deleted from all three suites: the `try: from copier import … / HAVE_COPIER = True/False`
block and the `@unittest.skipUnless(HAVE_COPIER, "copier not installed")` decorator (on base:
`test_render_and_run.py:23-31`, `test_render_cli_name.py:44-52`, `test_update_compat.py:32-37`
+ `:232`). No `HAVE_COPIER` survives, and no module keeps a second copier import —
`tests/test_copier_availability.py:185-196` asserts exactly that, per name, per module.

## 2. Design decisions, and what each one rules out

**The skip is raised where copier is used, and nothing is computed at import.** Mirrors the
peer the brief cites — `UpdateCompat.setUpClass` raising `SkipTest("no vX.Y.Z tags in this
checkout (shallow clone? needs fetch-depth: 0)")` (base `test_update_compat.py:237-241`,
now `:240-245`). Placement matters as much as wording: a decorator evaluated at collection
can only report a proposition settled before any test body ran, which is how "importable in
this interpreter" got reported as "installed".

**The reason carries three facts** (`copier_support.py:37-57`): which interpreter could not
import it (`sys.executable`), the real exception (`ModuleNotFoundError: No module named
'copier'`, not a paraphrase), and where `PATH` found the executable — plus the sentence that
turns those into a diagnosis ("a CLI-only install (pipx-style, in its own venv) is not
importable from here") and the command that fixes it. On this host it reads:

> `copier is not importable by this interpreter (/usr/bin/python3): ModuleNotFoundError: No
> module named 'copier'; a `copier` executable IS on PATH at /home/eddie/.local/bin/copier —
> the tool is installed, but a CLI-only install (pipx-style, in its own venv) is not
> importable from here. These suites use copier as a LIBRARY (run_copy/run_update): install
> it for THIS interpreter with `/usr/bin/python3 -m pip install copier`.`

**The third answer lives at the process boundary, not in a test body** — the invariant's own
argument. `classify` (`run_root_suite.py:52-95`) judges by two facts, the run-verify doctrine
applied to the suite that supplies the gates their evidence (`template/engine/scripts/
run-verify.sh:47-75`): *did anything fail* and *how many cases actually executed*. Order is
deliberate — a real failure outranks absent evidence (and `template/src/pdca_harness/gates.py:762`
honours a marker only at rc 0 or 77 — #329 — so a failing run that printed one would be
claiming a channel it does not have), so the marker is printed on the 77 path and nowhere
else (`test_copier_availability.py:335-342` asserts the failure path carries none).

**Why the copier-skip is recognised by a string prefix.** `unittest` keeps only
`str(exception)` for a skip — `unittest/case.py:63` calls `_addSkip(result, test_case,
str(e))`, and `unittest/suite.py:243` does the same for a class-level one — so a
custom `SkipTest` subclass could not be recognised downstream: the exception object never
reaches `TestResult.skipped`. The prefix is therefore the only available channel, and it is
single-sourced: `copier_support.UNIMPORTABLE_PREFIX` (`:34`, the constant) is *imported* by the runner
(`run_root_suite.py:34-37`), and `test_copier_availability.py:344-354` binds the two halves
end-to-end (real modules → real reason → production `classify` → 77).

**Why "any copier skip ⇒ no copier evidence"** (`run_root_suite.py:77-84`) rather than
"nothing ran at all": one interpreter has one import outcome, so if any case skipped for it,
every copier-dependent case in that run did. This is what makes the *documented* command
(`python3 -m tests.run_root_suite`, full discovery) still exit 77 on a pipx host even though
this bundle's own 16 regression cases pass in the same run — the case
`test_other_cases_passing_does_not_make_it_evidence` (`:296-303`) exists precisely for that
trap, and the live run below confirms it. A plain `executed == 0` rule would have reported
that run `OK` and re-created the defect one level up.

### Alternatives rejected, with their cost

- **Three copies of the truthful reason, one per module** (no shared helper): the reason
  builder is 21 lines (`copier_support.py:37-57`); ×3 = 63 duplicated lines, and the runner
  would then have to match three independently-worded strings instead of importing one
  constant. The brief's own reading — the three sites are byte-identical in shape — is why
  this is one answer, not three edits.
- **A bash entry point** (`scripts/run-root-suite.sh`) parsing `python -m unittest -v`
  output: it would have to scrape `Ran N tests` and count `... skipped` lines out of a
  human-readable format that is not a contract (≈35 lines of grep/awk, plus a new top-level
  `scripts/` dir the repo does not have — the target root holds no `scripts/`). The Python
  module reads `TestResult.testsRun` / `.skipped` directly (45 lines including comments) and
  is callable in-process, which is what lets the regression module drive it with a
  `StringIO` instead of a subprocess (`test_copier_availability.py:275-278`).
- **Putting the helper inside the named test module** to avoid a fourth file: the test module
  is collected by discovery *and* imports the three suites (`:86-100`); having the suites
  import it back is an import cycle whose module-level code would run at collection — the
  exact class of thing this bundle is removing.
- **`tests/__init__.py`** to make one import form work everywhere: the base has none, the
  brief says this slice has no reason to add one, and it would change how `discover -s tests`
  resolves every existing module. Cost of the alternative actually taken: a 3-line
  `try/except ImportError` at each of the 4 import sites = 12 lines, both shapes verified
  below.
- **`self.fail(...)` when `$PDCA_BUNDLE` is set** — the archived v1 approach the brief
  forbids. Not re-attempted; there is no environment read anywhere in this patch, and
  `test_no_environment_variable_turns_a_skip_into_a_failure` (`:216-228`) pins that with
  `PDCA_BUNDLE`/`PDCA_WORKTREE`/`PDCA_TARGET`/`CI` all set.
- **Driving the copier CLI as a subprocess** so a pipx host regains coverage: out of scope
  per the brief (option 1 of the issue); worth its own slice.

## 3. Red → green, in three slices

The C4 gate cannot produce this (every file here is test/non-behavioural, so the verifier's
`PROD` set is empty and it exits 77 — declared in the brief's Falsifiability). So the
refutation was run by hand, three ways, each reverting a different part of the fix. Runner:
`/usr/bin/python3 -m unittest tests.test_copier_availability` from the worktree root.

| Slice reverted | Result |
|---|---|
| **A.** the three suite modules restored to base (`git stash push -- tests/test_render_and_run.py tests/test_render_cli_name.py tests/test_update_compat.py`) | **FAILED (failures=14)**, 4 distinct cases: `test_every_case_skips_with_the_truthful_reason_and_nothing_fails`, `test_modules_import_and_collect_with_copier_unimportable`, `test_no_module_level_copier_probe_survives`, `test_the_real_suites_under_the_pipx_posture_classify_as_no_evidence` — quoting the defect verbatim: `AssertionError: False is not true : test_render_then_slice (…): copier not installed` and `test_update_compat still binds \`HAVE_COPIER\` at module level` |
| **B.** `classify` short-circuited to unittest's two answers (`return (0 if result.wasSuccessful() else 1, "ok")`) | **FAILED (failures=5)**: the four `NoEvidenceIsNotSuccess` classification cases + the end-to-end one |
| **C.** `unimportable_reason` returning the shipped proposition `"copier not installed"` | **FAILED (failures=8)**: both `TruthfulSkipReason` reason cases, the bare-run case, the two runner cases that match on the prefix, and the end-to-end one |
| **restored** | `Ran 16 tests … OK` |

Post-restore, with the whole patch in place: `Ran 16 tests in 0.015s / OK`. (The three
slices were re-run against the final module after a 16th case — the usage-error guard at
`test_copier_availability.py:327-333` — and a diff tightening that keeps `_git` where the
base has it; same red sets, quoted above.)

## 4. The three forced questions

**(a) Genuine red?** Yes — three independent reverts, three different red sets, table above.
Full-revert is not a usable slice (the regression module imports `copier_support` /
`run_root_suite`, so removing them makes it un-importable rather than failing); the three
partial reverts are what actually isolate the defect, and slice A is the base code verbatim.

**(b) Production path?** Yes. `TruthfulSkipReason` calls `copier_support.import_copier()`
itself (`:141`, `:153`, `:166`). `NoVerdictBeforeATestBodyRuns` and
`BareDeveloperRunIsUnchanged` import the **real** `tests/test_render_and_run.py`,
`tests/test_render_cli_name.py`, `tests/test_update_compat.py` (`:86-100`, reloaded so the
posture under test is the one in force) and run their real cases through a real
`unittest.TestResult` (`:108-113`). `NoEvidenceIsNotSuccess` calls the production
`run_root_suite.main()` / `classify()` (`:277`, `:344-354`). Nothing is re-implemented or mocked
except the two *environmental* facts the criterion says the test must supply.

**(c) Fixture includes the fault?** Yes — the fault is injected, not curated out. The failing
element is "this interpreter cannot import copier while the executable is on `PATH`", and
`copier_unimportable()` (the finder at `:55-62`, the context manager at `:64-84`) creates
exactly that: a meta-path finder that raises
`ModuleNotFoundError("No module named 'copier'")` for `copier` and `copier.*` (with any
already-imported `copier` removed for the duration), plus `shutil.which` answering
`/home/dev/.local/bin/copier`. The three real suites are then run **under that posture** and
must skip truthfully; nothing excludes them. Proof it is not host luck: the module passes
identically on `/usr/bin/python3` (cannot import copier) and on
`.venv/bin/python3` (copier 9.17.0 importable) — both runs below.

## 5. Criterion-by-criterion evidence (commands a human can re-run)

From the worktree root. `SYS=/usr/bin/python3` (pipx posture: `copier 9.17.1` at
`/home/eddie/.local/bin/copier`, shebang `#!/home/eddie/.local/share/copier-venv/bin/python3`,
`import copier` fails); `VENV=/home/eddie/pdca/pdca-pdca/.venv/bin/python3` (copier importable).

| # | Command | Result |
|---|---|---|
| i, ii, iv | `$SYS -m unittest discover -s tests` | `Ran 18 tests … OK (skipped=3)`, **rc 0**; each skip reads *"copier is not importable by this interpreter (/usr/bin/python3): ModuleNotFoundError … a `copier` executable IS on PATH at /home/eddie/.local/bin/copier …"*. On base the same command gave `Ran 7 tests … OK (skipped=7)`, every case `skipped 'copier not installed'` |
| iii | `$SYS -m tests.run_root_suite` | **rc 77**, line 1 of the verdict: `PDCA-UNVERIFIABLE: no copier-dependent case executed [discover -s …/tests]: copier is not importable …` — and this is the run in which the 16 new cases *passed*, so the "something else ran" trap is closed live |
| iii | `$SYS -m tests.run_root_suite tests.test_update_compat` | **rc 77**, `PDCA-UNVERIFIABLE: no copier-dependent case executed [tests.test_update_compat]: …` (the CI step shape) |
| iii, v | `$VENV -m tests.run_root_suite` | **rc 0**, `root suite OK: 23 executed, 0 skipped` (measured at 22 before the 16th case was added) |
| iii, v | `$VENV -m tests.run_root_suite tests.test_render_and_run` | **rc 0**, `root suite OK: 1 executed, 0 skipped` (CI step 1, verbatim) |
| iii, v | `$VENV -m tests.run_root_suite tests.test_update_compat -v` | **rc 0**, `root suite OK: 5 executed, 0 skipped` (CI step 2, verbatim) |
| v | `./engine/scripts/run-suite.sh` (T3, from the pdca-pdca instance, `PDCA_WORKTREE` set) | **rc 0** — root suite `Ran 23 tests in 24.106s / OK`: the original 7 all executed for real (`test_render_then_slice … ok`, `test_namespaced_cli_name… ok`, 5× `UpdateCompat … ok`) + the 16 new; offline driver suite `Ran 1758 tests / OK (skipped=2)`; `PDCA-EVIDENCE: root suite OK, driver suite OK` |
| vi | `$SYS -m unittest tests.test_copier_availability` / `$SYS -m unittest discover -s tests -p 'test_copier_availability.py'` / same two with `$VENV` | `Ran 16 tests … OK` in all four — both mandatory invocation shapes, both host postures |
| — | T2 docs gate `./engine/scripts/run-docs-check.sh` | `docs lint clean, site render + link audit clean` |
| — | `git apply --check patch.diff` against a pristine `acb214a` tree | `APPLIES CLEANLY` (all 8 files) |

## 6. Behaviour changes a reviewer will notice

1. **In the unimportable posture the counts move**: the three suites now report `Ran 2 tests
   … OK (skipped=3)` instead of `Ran 7 … (skipped=7)`. Cause: a `SkipTest` from `setUpClass`
   is recorded **once, for the class**, against a `unittest.suite._ErrorHolder`, and the five
   `UpdateCompat` methods are never started — exactly how `UpdateCompat`'s existing
   shallow-clone skip already reports on base. Criterion (iv) asks for `OK (skipped=N)` and
   exit 0, which holds. It is also why `classify` subtracts only the skips that are real
   `TestCase` instances (`run_root_suite.py:60-67`): with the naive `testsRun - len(skipped)`
   the count goes **negative** (2 − 3) and a wholly-skipped class reads as evidence — found
   by running it, fixed before the test was written around it.
2. **The green posture is untouched**: same 7 tests, same assertions, no new dependency
   (`copier_support` and `run_root_suite` are stdlib-only). Verified by the T3 row above.
3. **`render-check` can now go red for a reason it never could**: a step whose cases all
   skipped exits 77 → non-zero → the job stops instead of reporting success. That is the
   intent (GitHub has no third state), and it is what makes the two consumers real rather
   than a mechanism nobody invokes.

## 7. Not touched, deliberately

- `engine/scripts/run-suite.sh` in **this pdca-pdca instance** — the brief's residual; the T3
  row keeps running `discover -s tests`, which is why its row stays green rather than 77.
- `AGENTS.md:33-35` repeats CONTRIBUTING's "keep the offline suite green" line. The brief
  scoped the consumers to `render-check.yml` and `CONTRIBUTING.md`; adding a third would be
  scope creep. Flagging it as a possible follow-up, not a defect of this patch.
- `template/tests/`, `template/src/pdca_harness/gates.py` (read for its constants only — the
  regression module re-reads them with `ast` at `:356-372` so this patch cannot drift from
  them silently), the `copier importable (.venv)` doctor row.

## 8. External dependencies

None missing. Everything the brief listed was present: copier importable in `.venv`
(9.17.0 — the green posture) and the red posture was already the host's shape (system
interpreter + pipx CLI). No `NEEDS-HUMAN external dependency` to declare.

## 9. Housekeeping note for the human

`results/issue_495/test_copier_probe.py` is the **v1** iteration's test file, left in the
bundle root from the rejected attempt; this iteration's test is
`results/issue_495/test_copier_availability.py` (identical to
`tests/test_copier_availability.py` in the patch). Removing stale bundle files is the
harness's to do, not mine — noting it so the stale name is not mistaken for a second shipped
module.
