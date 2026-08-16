# Brief — issue 507 / shipped-suites-assert-only-sanctioned-postures

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** shipped-suites-assert-only-sanctioned-postures
- **Defect:** Three assertions the template ships **into** every rendered instance pin the
  template's own *default* posture, so an instance that follows the template's published
  instructions inherits permanently red tests in its T3 gate.
  **(a) The sandbox pair — an outright contradiction.**
  `template/tests/test_families.py:353` (`ShippedPdcaTomlExamples.test_leaves_sandbox_is_declared_exactly_once`)
  counts `[leaves.sandbox]` headers *including commented ones* (`^#?\s*\[leaves\.sandbox\]\s*$`)
  and requires exactly one; `:359` (`test_the_commented_example_parses_when_uncommented`)
  requires a **commented** header to exist. Enabling the seam is the sanctioned #277/#287
  opt-in that the block's own comment invites (`template/pdca.toml.jinja:821-827`, "uncomment
  only the lines you need"), and an instance that takes the invitation has no green option:
  drop the example and `:359` fails; keep it beside the now-active table and `:353` fails
  (two headers). Verified by evaluating both regexes over the three postures — default
  PASS/PASS, active-without-example PASS/**FAIL**, active-with-example **FAIL**/PASS — and
  observed live in this instance (enabled at its 2026-08-01 Act review so the codex reviewer's
  prior-art check could reach `api.github.com`; see Repro (a)). It is the instance's only
  remaining `make check` failure across 1730 tests.
  **(b) The C4-skeleton wording assertions — satisfiable, but they contradict the template's
  own instructions.** `template/tests/test_verify_red_leg.py:65-141` (`C4RedLegVerdictRule`,
  7 cases) string-matches sentences of the **skeleton** `engine/scripts/run-verify.sh`
  ("JUDGE EVERY LEG BY TWO FACTS", its ASCII verdict table, the exit-77 vocabulary), and
  `template/tests/test_verify_base.py:293-301` (`VerifyBaseExport.test_the_c4_skeleton_names_the_export_as_the_last_rung`)
  asserts that file contains "Resolve as: $PDCA_BASE > $PDCA_VERIFY_BASE > your own override
  > $PDCA_BRIEF_BASE". But `run-verify.sh` is the one file every instance is *told* to replace
  — `template/engine/scripts/run-verify.sh:2` ("SKELETON. Fill this in for your project."),
  `template/engine/README.md.jinja:31` ("a skeleton for this — fill it in") and `:84`
  ("Replace the skeleton(s) here with your real runners"). An instance with a filled-in gate
  gets exactly **8 failures** the moment it updates to v0.57.0 (the 7 above + the base-ladder
  case), while `EngineReadmeExplainsTheRule` (`test_verify_red_leg.py:144-173`) stays green —
  reproduced, see Repro (b). This instance papered over it by restoring the skeleton's contract
  verbatim above its own implementation (`engine/scripts/run-verify.sh:15-27`, marked TEMPORARY
  pending this issue) — defensive, not necessary.
  This is #386 in two more suites; that issue's resolution (PR #426, commit `75294d1`) is the
  model.
- **Success criterion:** With the patch, one offline run of
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_families tests.test_verify_red_leg tests.test_verify_base`
  is green, and the cases it contains prove all of the following (each non-current posture
  constructed by the cases themselves as synthetic file text in a temp dir, since the modules
  today read only their own checkout):
  (i) the **unrendered template checkout** — today's green, unchanged;
  (ii) a **rendered instance with an ACTIVE `[leaves.sandbox]` table and no commented example**
  (this instance's posture) is green — red today;
  (iii) a **rendered instance with an active table that kept the commented example beside it**
  is green — red today;
  (iv) a **rendered instance whose `engine/scripts/run-verify.sh` is a filled-in project gate
  that does not quote the skeleton's wording** is green — 8 failures today;
  (v) **still RED:** a rendered instance whose `pdca.toml` declares **two ACTIVE**
  `[leaves.sandbox]` headers — the PR #292 defect (`tomllib` refuses the file, so the driver
  will not start at all) must stay caught in every posture;
  (vi) the template-checkout-only properties keep being asserted **where they hold**: the
  commented sandbox example is present and round-trips to valid TOML when uncommented, and the
  skeleton still publishes the two-facts rule, its four-outcome table and the base ladder;
  (vii) `EngineReadmeExplainsTheRule` and every other case in the three modules are untouched
  and still bind every instance.
- **Falsifiability:** RED is reachable on the base toolchain — pure-stdlib Python ≥ 3.11, no
  services, no network — on the target checkout Do is given. Postures (ii) and (iv) were both
  observed red before this brief was written (Repro (a) and (b)); (iii) and (v) are
  synthesizable the same way. Because each module today reads only its own checkout's
  `pdca.toml` / `engine/scripts/run-verify.sh`, the regression cases MUST drive the assertions
  over synthetic file text in a temp dir — the #386 precedent's shape — so every posture above
  is falsifiable in one offline run.
  **Gate posture — declared, not a gap.** This bundle's patch is confined to
  `template/tests/*.py`, so `engine/scripts/run-verify.sh:130-144` classifies it **test-only**
  and C4-verify exits 77 `PDCA-UNVERIFIABLE` ("no behavioral production change to revert") →
  SUMMARY §6 NEEDS-HUMAN, non-gating, rather than a false red. That is the sanctioned path for
  this class (issue #165 discipline; `docs/INTEGRATION.md` §4 names an UNVERIFIABLE C4 as a
  project-defined human-only item), and it is exactly the route the #386 bundle took
  (`results/issue_386/check-gates.json`: C4 `unverifiable`, overall `pass`). Do **not** invent a
  production edit to manufacture a red leg. Green-with-fix evidence comes from the bundle-scoped
  advisory `T3-suite` gate, which runs both suites inside the patched worktree; the red comes
  from the commands above on the unpatched base.
- **Invariant to restore:** A suite the template ships **into** rendered instances may assert
  only properties that hold in **every posture the template sanctions**. A property that holds
  solely in the unrendered template — "the sandbox example is still commented", "the C4 gate
  still carries the skeleton's wording" — must be asserted against the template checkout, and
  where a real protection hides behind such a default it is the *protection*, not the default,
  that gets asserted in every posture. Quantified over the category, not the repro file: this
  binds every posture-sensitive assertion in the shipped suites, so a patch that fixed only
  `test_families.py` and left the two `run-verify` modules pinning skeleton prose visibly fails
  it. Source: internal project rule, Tier C per `docs/principles.md` §5 — established by the
  #386 resolution (`75294d1`, "may assert only what holds in every posture the template
  sanctions") and its in-file precedent `template/tests/test_remote_control_docs.py:31-36` and
  `:117-127`, and corroborated by the template's own three published statements that
  `run-verify.sh` is to be replaced. `docs/principles.md` §5/§6 are an unfilled scaffold in this
  instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** Make the three shipped modules assert each property in the posture where it holds.
  (i) The sandbox pair — the property that binds every instance is that `pdca.toml` stays
  loadable: no more than **one active** `[leaves.sandbox]` table, and any commented example
  that is present round-trips to valid TOML under one table with an unquoted boolean. "A
  commented example is still present" is the template's default and binds the template
  checkout. (ii) The `run-verify.sh` wording — what the harness *publishes* in its skeleton
  binds the template checkout, because every instance is instructed to replace that file; the
  instance-binding half of the two-facts rule is already carried in parallel by
  `EngineReadmeExplainsTheRule` against `engine/README.md`, which ships to every render and is
  not a fill-in file, and stays exactly as it is. Every case's docstring must state which
  posture it binds. **Out of scope:** `template/pdca.toml.jinja` — its sandbox guidance, its
  defaults, and the fact that it ships the example commented all stay unchanged, and the seam
  is neither enabled nor disabled anywhere; `template/engine/scripts/run-verify.sh` and
  `template/engine/README.md.jinja` — no wording changes at all, and in particular do **not**
  add the base ladder to the README to "restore" a parallel home (see Citations: it was never
  there; a follow-up if wanted); `EngineReadmeExplainsTheRule` and every other case in the three
  modules; any `src/`, driver, engine or `copier.yml` change; this instance's own
  `engine/scripts/run-verify.sh:15-27` temporary block, which is pdca-pdca's repo and comes out
  separately once this lands (`docs/INTEGRATION.md` §2 keeps instance changes outside the cycle).
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), from the sibling instance and the target:
  **(a) sandbox pair, no synthesis needed** — this instance already sits in the enabled posture
  (`pdca.toml:977-978`): `PYTHONPATH=src .venv/bin/python3 -m unittest tests.test_families`
  → `FAIL: test_the_commented_example_parses_when_uncommented … AssertionError: unexpectedly
  None : the [leaves.sandbox] example must still be there` (Ran 30 tests, 1 failure). Restore the
  commented example beside the active table and the *other* case fails instead ("a second
  [leaves.sandbox] header makes the uncommented file unparseable") — the two regexes over the
  three postures give PASS/PASS, PASS/FAIL, FAIL/PASS.
  **(b) skeleton wording** — assemble a temp tree with `tests/test_verify_red_leg.py` and
  `tests/test_verify_base.py` from the render, `engine/README.md` beside them, and an
  `engine/scripts/run-verify.sh` that is a real project gate not quoting the skeleton header;
  run `PYTHONPATH=<instance>/src python3 -m unittest tests.test_verify_red_leg tests.test_verify_base`
  → `FAILED (failures=8)`: the 7 `C4RedLegVerdictRule` cases plus
  `VerifyBaseExport.test_the_c4_skeleton_names_the_export_as_the_last_rung`, with
  `EngineReadmeExplainsTheRule`'s 4 cases green.
  Cross-check the shipped text with
  `git -C ../pdca-harness show origin/main:template/tests/test_families.py` (and the two verify
  modules).
- **External dependencies:** none
- **Test file:** `template/tests/test_families.py`, `template/tests/test_verify_red_leg.py`, `template/tests/test_verify_base.py`
  — the defect *is* these three modules, so each regression ships in the module it binds.
  Appending to an existing test file is correct for this project's C4 red leg: the gate
  reverts production hunks only and keeps every `tests/` and `template/tests/` path in place
  (see the excludes at line 212-217 of the instance's C4 script), and it does **not** classify
  on an *added* test file — so an appended case earns its red normally. As declared under
  Falsifiability, this particular bundle has no production hunks and will classify
  UNVERIFIABLE regardless.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  **Composition cue — mirror the #386 resolution, do not invent a new mechanism.** The idiom
  lives in `template/tests/test_remote_control_docs.py` (commit `75294d1`):
  `:31-36` (module docstring stating the posture rule and why the default is not an invariant);
  `:33-35` (the `TOML` / `RENDERED` resolution that exposes *which* posture the checkout is in);
  `:117-127` (`@unittest.skipIf(RENDERED, …)` scoping the default-only assertion, with a
  docstring naming the posture it binds); and the `# --- posture regressions (issue #386)`
  block from `:131` onward, which builds the OTHER postures as synthetic config text in a temp
  dir and runs this very module against them, so both legs are falsifiable in one run.
  **Fork-storm constraint (added 2026-08-15, after two OOM-killed Do attempts on this brief).**
  Prefer asserting over the synthetic file text directly — no subprocess at all; the Success
  criterion already mandates that shape. If a case nevertheless runs this module as a
  subprocess, it MUST copy `test_remote_control_docs.py:285-288` exactly, all three
  load-bearing parts: (1) restrict discovery to this one module —
  `["-m", "unittest", "discover", "-s", "tests", "-p", <this file's name>]`, never a bare
  `discover -s tests`; (2) pass the recursion guard through an **inherited** environment —
  `env={**os.environ, GUARD: "1"}` — and `@unittest.skipIf(os.environ.get(GUARD), …)` the
  spawning case; (3) never build a fresh env dict — the `env={"PYTHONPATH": …}` idiom at
  `tests/test_render_and_run.py:75` erases the guard, so every child believes it is the
  top-level run. Both killed attempts spawned bare `discover -s tests` chains: ~960 blocked
  interpreters filled the 16G leaf cap within ~40 seconds of the first spawn (evidence:
  `build.error.log` and `build.memory.jsonl` in this bundle).
  In the target file, `ShippedPdcaTomlExamples._source()` at `template/tests/test_families.py:340-351`
  already picks `pdca.toml.jinja` in-tree vs `pdca.toml` in a render — but note it returns only
  the **text**, not which file it came from, so the posture is not yet exposed at the point of
  assertion the way `RENDERED` exposes it at `test_remote_control_docs.py:35`.
  **Correction to the issue text, verified — do not repeat its claim.** The issue says
  `engine/README.md` "carries the same statement" for both halves. That is true for the
  two-facts rule (`template/engine/README.md.jinja:44-68` → `engine/README.md:44-68` in a
  render: the "exit code AND how many tests actually ran" sentence, the four-row truth table,
  and 'A gate never turns "no evidence" into a verdict.'), which is why dropping the
  *skeleton* half of `test_verify_red_leg.py` outside the template costs an instance nothing.
  It is **false** for the base ladder: `$PDCA_BASE` / `$PDCA_VERIFY_BASE` / `$PDCA_BRIEF_BASE`
  and the "Resolve as:" sentence appear **nowhere** in `template/engine/README.md.jinja` (zero
  matches). `test_verify_base.py:293-301` is still correctly scoped to the template checkout —
  the rule is about what the *harness publishes*, which exists only there — but it must be
  scoped, not deleted, and not on the grounds that the README covers it.
- **Prior-art check (triage cycles):** By affected file path, against `origin/main` after
  `git -C ../pdca-harness fetch origin`:
  `-- template/tests/test_families.py` → `a75ef49` (rubric fence closers, unrelated), then
  `5f656d4` "fix(config): one [leaves.sandbox] table, not two — the shipped example was
  unparseable (#292 review)" — the commit that *introduced* the pair; nothing has revisited it.
  `-- template/tests/test_verify_red_leg.py` → a single commit, `edd9352` "fix: don't let a C4
  gate pass a fix whose test never ran" (#434), which introduced the file.
  `-- template/tests/test_verify_base.py` → `96c9704`, `e79d109` "fix(gates): supply the base
  ladder's last rung as $PDCA_BRIEF_BASE" (#387, which introduced the skeleton assertion),
  `2ef3e28`, `8e9b5fb`. None revisits the posture question.
  `gh search issues --repo eduralph/pdca-harness "test_families"` → only #507 (this one);
  `… "posture"` → #386 **closed/fixed** (PR #426 — the precedent this brief mirrors, not a
  rejection) and unrelated enhancements; `… "run-verify"` → #434 closed (introduced the
  wording), #474/#441/#371 open but on gate export/runner wiring, different files.
  `gh pr list -R eduralph/pdca-harness --state open` → empty. No closed/rejected attempt at this
  class exists. Not fixed, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
