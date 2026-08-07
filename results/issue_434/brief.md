# Brief — issue 434 / red-leg-zero-tests-unverifiable

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** red-leg-zero-tests-unverifiable
- **Defect:** In plain terms: the check that is supposed to prove a fix works can pass
  when the test never ran at all.

  Here is how. Every project's C4 gate proves a fix twice. Once with the fix in — the test
  must pass. Once with the fix taken back out — the test must now fail, which is what proves
  the test is really catching this bug and not something else. That second run is the one at
  issue.

  To decide whether that second run "failed", the gate looks at the exit code of the test
  runner. But a test runner exits non-zero for two very different reasons: the test ran and
  failed (good — that is the proof we want), or the test never built and so never ran at
  all (no proof of anything). The gate cannot tell those apart, so it treats both as "the
  test failed without the fix" and reports **PASS**. A bundle whose test never even compiled
  gets recorded as proof that its test catches the bug.

  Four possible outcomes; only the last one is wrong:

  | test runner exited | tests that actually ran | verdict today | verdict it should give |
  |---|---|---|---|
  | 0 | none | UNVERIFIABLE | UNVERIFIABLE (already right) |
  | 0 | some | FAIL — passes without the fix | FAIL (already right) |
  | non-zero | some | PASS | PASS (already right) |
  | **non-zero** | **none** | **PASS** | **UNVERIFIABLE** |

  This is not a hypothetical corner. Taking the fix back out also removes any new function
  the fix added — so if the test calls one of those new functions, it cannot build, and we
  land in the bad row. That is an everyday shape for a fix. It already happened for real:
  getwyrd/wyrd-pdca recorded "PASS — red without the fix" for a bundle whose test never
  compiled, and had to patch its own copy of the gate on 2026-08-02.

  **One thing the issue gets wrong, worth knowing before you read the rest.** The issue says
  the buggy script is shipped by the harness and so every project has the same bug. Half
  right. The file *is* copied into every project untouched (`copier.yml:14` sets
  `_templates_suffix: .jinja`, so a file without that suffix is copied as-is). But what the
  harness copies is an **empty outline** — it prints "not yet implemented for this project"
  and stops (`template/engine/scripts/run-verify.sh:53-60`). Each project writes the real
  gate itself, following the written instructions in that outline's header comment
  (`:35-52`). Those instructions never mention "did any test actually run?", so every
  project that follows them writes the same bug. So the thing to fix here is the
  **instructions**, not a script. That is a different fix from the one the issue imagines —
  see Scope, and §Settled at Plan at the bottom.

- **Success criterion:** On `eduralph/pdca-harness` @ `main`, a new test file
  `template/tests/test_verify_red_leg.py` fails before the change and passes after it. What
  it checks: the instructions in `template/engine/scripts/run-verify.sh` now tell a project
  to decide the second run's verdict from **two** things — the runner's exit code *and*
  whether any test actually ran — and say plainly that if no test ran, the answer is
  `PDCA-UNVERIFIABLE` / exit 77 (which sends it to SUMMARY §6 for a human to look at),
  never PASS. That holds whether the runner exited 0 or non-zero.

  Everything the criterion needs is inside `template/`, so the C4 gate can prove it from the
  patch alone. No fork CI, no whole-suite run.

- **Falsifiability:** Do is pointed at this instance's own C4 gate
  (`engine/scripts/run-verify.sh` in pdca-pdca), and the criterion goes red there for a real
  reason: that gate takes the patch's production changes back out but leaves the new test in
  place (`:72-81`). With the instructions back to their current wording, the new test's
  assertions do not hold, so it fails — a genuine red. With the patch applied it passes.

  Two things Do must get right, or that red is fake:
  1. **The patch has to change `template/engine/scripts/run-verify.sh` itself.** This
     instance's gate treats `*.md` and `*.md.jinja` as non-behavioural
     (`engine/scripts/run-verify.sh:43`). If the only change were to
     `template/engine/README.md.jinja`, the gate would find nothing to take back out and
     exit 77 as unverifiable (`:51-53`) — no proof either way. README prose can accompany
     the change; it cannot be the whole change.
  2. **The new test must assert against that `.sh` file**, not the README. A test that only
     reads the README stays green when the `.sh` is reverted, and the gate then reports
     `C4 FAIL: bundle test still green WITHOUT the fix` (`:78-81`).

  Checked against the gates this project actually runs (`pdca.toml` `[[gates.checks]]`):
  `C4-verify` is the only gating bundle check. It runs the named test as
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_verify_red_leg`
  (`engine/scripts/run-verify.sh:55-65`), so the file has to sit at exactly
  `template/tests/test_verify_red_leg.py` and use only the standard library. Nothing hides
  the test behind a feature flag, so it cannot silently run zero tests and report success.
  This bundle is in wave 0 with no `Onto branch`, so the gate's base is simply the brief's
  target, `origin/main`, which the patch applies to cleanly.

- **Invariant to restore:** *A gate never turns "no evidence" into a pass.* Whether a
  verification step counts is decided by whether the test actually ran — not by which exit
  code the runner happened to return. A step in which no test ran is `UNVERIFIABLE`
  (exit 77 → §6, for a human to judge): not a pass, and not a fail either. This is stated
  for **every** verification step the harness publishes instructions for, not just the
  second run of one project's script.

  Sources (all internal to this repo — `docs/principles.md` §5 Tier C. Its §6 category table
  is empty for this instance, so this is reference material, not a gated category):
  - `template/src/pdca_harness/gates.py:19-38, 82-85, 761-773` — exit 77 and the
    `PDCA-UNVERIFIABLE:` marker are the harness's existing "no verdict was earned" channel,
    and (#329, `gates.py:38`) that marker "declares EVIDENCE, never a verdict";
  - `template/engine/README.md.jinja:33-43` (#165) — the existing rule that a step which
    *cannot* go red must report unverifiable rather than invent a verdict;
  - `docs/05-check.md:45` — C4's whole job is "red pre-fix, green post-fix".

- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** (none)
- **Conflicts with:** (none — this bundle touches only `template/engine/**` and one new
  `template/tests/` file; #420 and #411 touch neither)
- **Ordering note:** Independent of both siblings in this batch. #420 and #411 conflict with
  each other (shared docs file), so the scheduler separates those two; this one can ride
  either wave. Ran the real scheduler over all three bundles (`waves.compute_waves`):
  **wave 0 = {411, 434}, wave 1 = {420}**.
  Files each bundle touches, checked for overlap: #434 =
  `template/engine/scripts/run-verify.sh`, `template/engine/README.md.jinja`,
  `template/tests/test_verify_red_leg.py`; #420 =
  `template/src/pdca_harness/{leaves,config}.py`, `template/pdca.toml.jinja`,
  `docs/07-crosscutting.md`, one new `template/tests/` file; #411 =
  `template/src/pdca_harness/merge.py`, `template/tests/test_merge.py`,
  `docs/07-crosscutting.md`. Nothing overlaps with this bundle.
- **Surfaces:** data
- **Difficulty:** low — three files, no change to any driver code path, no new configuration
  surface. The change is the wording one shipped file publishes, plus the test that holds
  that wording in place. A reviewer has one script and one test to hold in view.
- **Scope:** Fix the instructions the harness publishes so a project following them cannot
  report PASS for a run in which no test executed. The instructions must:
  - decide the verdict from both the runner's exit code and whether any test ran;
  - say explicitly that "runner exited non-zero **and** no test ran" is
    `PDCA-UNVERIFIABLE` (exit 77), not PASS;
  - keep that case distinguishable from "runner exited 0 and no test ran" — the two have
    different causes and need different things from the human reading §6;
  - live where someone writing their gate will actually read them, and be held in place by
    a test so the wording cannot quietly rot.

  `template/engine/README.md.jinja` §"The two gate shapes that matter" can carry the longer
  explanation.

  **How** a project ends up enforcing this — wording alone, or wording plus a small reusable
  snippet under the `engine/scripts/lib/` convention the README already documents
  (`template/engine/README.md.jinja:16-21`) — is Do's call; the criterion works either way.
  Either way the `.sh` file has to be a real part of the diff (see Falsifiability).

  Out of scope: writing an actual working gate inside the outline (it stays an outline —
  that is the point of it); touching `gates.py`'s exit-77 handling (already correct,
  #329/#428); auditing or fixing **this** project's own copy of `engine/scripts/run-verify.sh`
  — different repository, and per `docs/INTEGRATION.md` §2 that is an ordinary pdca-pdca PR
  outside the cycle; fixing getwyrd/wyrd-pdca (already done there — this is the fix being
  routed upstream).

- **Repro instruction:** On a clean worktree of `origin/main` in `../pdca-harness`:
  1. `git -C ../pdca-harness show origin/main:template/engine/scripts/run-verify.sh` — read
     lines 35-52. The instructions describe the second run as "run the test → expect FAIL
     (red)" and allow exactly one non-verdict outcome (#165: there was nothing to take out).
     Nothing anywhere says that a run in which the test never executed is not a red.
  2. `grep -rn "TESTS_RAN\|tests ran\|executed" template/engine/` — no matches. The "did any
     test run?" question does not appear in the published instructions at all.
  3. From `template/`, with `PYTHONPATH=src`: `python3 -m unittest tests.test_verify_base` —
     `test_the_c4_skeleton_names_the_export_as_the_last_rung` passes. That shows the suite
     already holds this outline's wording in place for a different claim; there is simply no
     equivalent for the verdict rule.
- **External dependencies:** none
  (python3 + git + bash — the base toolchain. The new test must be standard-library only and
  self-contained: it reads files from the checkout, and touches no network, no cargo and no
  Docker.)
- **Test file:** `template/tests/test_verify_red_leg.py` (new file). New rather than
  appended because no existing suite covers this rule. This instance's C4 gate is fine with
  either — it takes production changes back out and keeps every test, checked at
  `engine/scripts/run-verify.sh:72-81` — so this is about keeping things tidy, not about the
  gate. The gate runs it as `tests.test_verify_red_leg` from `template/`, so the filename
  must match exactly.
- **Citations expected:** Do must cite path:line on `origin/main` for every change.
  Places to look at (Do MAY open these):
  - `template/tests/test_verify_base.py:271-279`
    (`test_the_c4_skeleton_names_the_export_as_the_last_rung`) — **copy this test's shape**.
    It is how this repo holds a claim in that outline in place: read the file's text, assert
    the wording that must be there is there, assert the old wording is gone. Reuse its
    locator too — `_SKELETON = Path(__file__).resolve().parents[1] / "engine" / "scripts" /
    "run-verify.sh"` at `:42`.
  - `template/engine/scripts/run-verify.sh:46-52` — the `PDCA-UNVERIFIABLE` / exit-77
    wording that already exists for the #165 case. Say the new case in that same vocabulary
    rather than inventing a second one.
  - `template/src/pdca_harness/gates.py:82-85, 761-773` — what exit 77 and the marker
    actually do to a gate row (`unverifiable` → §6), so the new wording describes the real
    consequence.
- **Prior-art check (triage cycles):** Searched by affected file path and by keyword.
  `git -C ../pdca-harness log --oneline origin/main -- template/engine/scripts/run-verify.sh
  template/engine/README.md.jinja` → 7 commits, none about the verdict rule (`e79d109` base
  ladder, `f918fd8` cli_name, `2ef3e28`/`8e9b5fb` verify base, `71e12fa` #165 non-production
  classification, `dce8394` gating policy, `f7931d3` initial). Tracker
  (`gh search issues --repo eduralph/pdca-harness "UNVERIFIABLE" / "compile"`): the nearby
  work is all **closed** and complementary rather than duplicate — #428 (marker matched
  anywhere in output), #329 (marker hiding a hard failure), #165 (non-production
  classification), #368 (gate timeout). #435 is open but different (doctor rows check that a
  tool exists, not that it is new enough). No open PRs on the repo (`gh pr list` → empty).
  Not previously proposed and rejected: getwyrd/wyrd-pdca#178 queued it on 2026-07-26,
  applied it on 2026-08-02, then routed it here.
- **Disposition hint:** likely-fix

## Settled at Plan (was an open question; the human decided)

The issue was filed believing the harness ships the broken script. It ships an empty
outline (verified above), so "fix it upstream" could have meant two things. **Decided: the
first.**

1. **Chosen.** Fix the published instructions — the wording, plus a test that keeps it
   there, optionally plus a small reusable snippet projects can drop in. Cheap, provable,
   and it reaches projects at render or `copier update`.
2. Not chosen. The harness *enforcing* the rule itself rather than instructing. There is
   nowhere generic to do it: `gates.py` only ever sees an exit code and some captured
   output, and "how many tests ran" depends entirely on the project's language and test
   runner. The instructions are the lever.

**Also settled: downstream instances stay out of scope.** A rendered instance runs an older
copy of the harness and writes its own gate, so it is expected to lag — reconciling it is
the instance's own business, not this bundle's. That explicitly includes the pdca-pdca
instance whose gate is judging this very bundle (its `engine/scripts/run-verify.sh:55-83`
has the same defect: no count of executed tests, so a test that errors on import counts as
a legitimate red). The target here is `eduralph/pdca-harness` and nothing else.

One consequence Do must respect, already stated above under Falsifiability: because the
gate judging this bundle has that defect, the new test's red must be earned by a **failing
assertion**, not by an import or attribute error. Otherwise the red proves nothing.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
