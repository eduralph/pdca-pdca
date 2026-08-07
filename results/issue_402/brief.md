# Brief — issue 402 / gate-evidence-not-leaked-stdout

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** gate-evidence-not-leaked-stdout
- **Defect:** Two halves of one symptom — a **green** gate whose frozen record reads like a
  failure path.
  **(1) The leak.** `template/tests/test_split.py` drives production CLI code that prints to
  stdout — `leaves.do_split` at `template/src/pdca_harness/leaves.py:1155`
  (`print(f"{d / split.PROPOSAL}")`) and `cli._split` at
  `template/src/pdca_harness/cli.py:786-787` (`print(child)`) — without capturing it on every
  path (:181, :216, :586-587; the file's own convention is `redirect_stdout(io.StringIO())`,
  applied at :856, :888, :939, :1133, :1212, …). `unittest` writes its report to **stderr**, so
  under a pipe the block-buffered stdout flushes last and the leaked scratch paths become the
  final lines of the merged capture. Reproduced verbatim on `origin/main` @ `9fb4860`:
  `Ran 96 tests … OK` followed by three `/tmp/tmp…/results/issue_500/split-proposal.md` lines
  and two `/tmp/tmp…/results/issue_60{1,2}` lines.
  **(2) The rule.** `_classify` takes `output.strip().splitlines()[-1:]` as the evidence for
  pass **and** fail (`template/src/pdca_harness/gates.py:619-621`), so whatever flushed last is
  filed as the gate's verdict. A T3 wrapper exiting **0** was therefore recorded as
  `path_line = "/tmp/…/results/issue_500/split-proposal.md"` — a scratch path nobody can
  inspect, escalated to §6 NEEDS-HUMAN in 12 of 19 frozen pdca-pdca cycles (frozen example:
  `results/issue_387/check-gates.json`, T3 row). The premise originally filed here — that the
  synthetic `issue_500` fixture *flakes* — was **corrected in the thread**: the fixture has
  never failed, and the historical T3 reds were genuine and are already fixed by #417/#418.
  What survives is the misleading evidence string on a green row.
  **Measured at Plan (2026-08-02, clean `origin/main` worktree), and it changes the weighting
  of the two halves:** the gate reads ONE merged stream (`stdout=PIPE, stderr=STDOUT`,
  `template/src/pdca_harness/progress.py:112`), and the whole offline suite leaks **506** stdout
  lines — the `issue_500` paths are only the most visible; `git -C /tmp/example-repo add --all`,
  publish dry-run plans and rendered gate matrices leak from other modules too. Under a merged
  pipe the last line of `python3 -m unittest discover -s tests` is today
  `/tmp/…/results/issue_500/split-proposal.md`; with half (1) alone it would simply become a
  *different* leaked line. So half (2) is the load-bearing half — half (1) removes the specific
  noise this issue names and the fixture the reviewers kept misreading, but it cannot restore
  the invariant on its own.
- **Success criterion:** Both hold with the patch applied, and both fail without it:
  1. `cd template && PYTHONPATH=src python3 -m unittest tests.test_split` writes **nothing** to
     stdout — that module's complete output is the unittest report on stderr. (Scoped to this
     module by design: the wider suite-hygiene sweep is out of scope, see Scope.)
  2. A gate that declares its verdict summary and whose command output then continues with
     further, unrelated child-process stdout has **that declared summary** recorded as the
     row's `path_line` — not the trailing line. A gate that declares nothing keeps a defined,
     documented evidence rule, with the full basis still reachable through `row["log"]`
     (`gates.py:529-545`).
  Demonstrable by C4-verify alone: the named test modules are red with the production hunk
  reverted and green with it applied.
- **Falsifiability:** RED is producible offline on the environment Do gets, for both halves.
  (1) is reproducible today by the command above — the leaked paths print after `OK` (verified
  on a clean `origin/main` worktree, 2026-08-02). (2) is exercised by real, deterministic gate
  commands with no model/Docker/network: `template/tests/test_gate_logs.py:97,143` already
  asserts `path_line == "last-line"` for a shell gate, so a case where a *declared* summary is
  followed by trailing stdout fails on `origin/main`. The pdca-pdca C4 wrapper counts
  `template/src/pdca_harness/gates.py` as production and `template/tests/*.py` as tests
  (`engine/scripts/run-verify.sh:39-53`); reverting the production hunk leaves the changed test
  modules in place, and half (2)'s module goes red — a real red leg. Note that half (1) alone
  would be a **test-only** patch, which that wrapper classifies `PDCA-UNVERIFIABLE` and exits 77
  (`run-verify.sh:51-53`) — no red→green is possible for it in isolation, which is why this
  bundle carries both halves.
- **Invariant to restore:** A gate row's recorded evidence is output the gate emitted **as its
  verdict** — never a line the gate merely relayed from a child process; and a test suite's
  output is its own report — a test does not leak the output of the code it drives into the
  suite's stream. Cited to the target's own written contracts: the evidence-sufficiency
  invariant "the verdict's whole basis … must be reconstructable from bundle files alone"
  (`template/src/pdca_harness/gates.py:535-537`, #370) — evidence that names a transient
  `/tmp` path from a since-deleted sandbox satisfies neither *reconstructable* nor *basis* —
  and `test_split.py`'s own established capture convention (`:856`, `:888`, `:939`), which this
  fix simply applies to the paths it was not applied to.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 428
- **Ordering note:** wave 1. 428 fixes the *marker* half of `_classify` and settles what counts
  as a line the **gate itself declared**; this bundle's evidence rule builds on that notion in
  the same function, so it takes 428's accepted result as its base rather than colliding with
  it. 401 declares `Depends on: 402` and lands in wave 2 for the same file. Once this lands,
  the pdca-pdca instance's local stopgap in `engine/scripts/run-suite.sh` (Act 2026-08-02,
  commit `a100098`, marked REVERT-once-#402-lands) is superseded: its wrapper should adopt
  whatever declaration convention this patch establishes rather than hand-rolling a last line —
  a follow-up in THIS instance, not part of this patch. Note that a plain revert would restore
  the misleading evidence, since the other leaked lines remain.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** one logical change with two halves — stop the suite from leaking the driven code's
  stdout on the `test_split.py` paths that do not capture it, and make the recorded gate
  evidence be the gate's own verdict rather than whatever line happened to flush last. If the
  fix introduces a convention gate authors must write to, state it where the gate contract is
  written (`template/PCDA/quality-cycle/04-validation-tooling.md` §Gate result vocabulary) so a
  wrapper can be written against it. The exact discrimination rule is Do's to choose, aligned
  with the declaration rule 428 settles — do not invent a second, different notion of "the gate
  said this".
  / **out of scope:** the `PDCA-UNVERIFIABLE` marker rule (issue 428, this bundle's base — do
  not re-litigate it); the T4 default-open row status (issue 401); the transient-`/tmp`
  inspectability idea from the original filing (`gate-logs/` already persists the full output,
  #415 — nothing further is needed); quarantining or "de-flaking" the `issue_500` fixture (the
  corrected diagnosis: it does not flake, and must not be quarantined); the pdca-pdca-side
  follow-up to its `run-suite.sh` stopgap; and the **suite-wide** stdout-hygiene sweep — the
  other ~500 leaked lines measured across the offline suite are the same class but a separate,
  much larger slice, and half (2) is what makes them harmless. Do NOT start it here.
- **Repro instruction:** from a clean worktree of `origin/main`:
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_split` → `Ran 96 tests … OK`,
  then three `/tmp/…/results/issue_500/split-proposal.md` lines and two
  `/tmp/…/results/issue_60{1,2}` lines on stdout. Pipe it (`… 2>&1 | tail -3`) to see the leak
  become the last lines a gate would record. Executed at Plan against the target's own code:
  `_classify(0, "C4 PASS: red without the fix, green with it\n/tmp/x/results/issue_500/split-proposal.md\n")`
  returns `('pass', ['/tmp/x/results/issue_500/split-proposal.md'])` — the declared verdict is
  discarded in favour of the trailing leak. The shipped consequence is frozen at
  `results/issue_387/check-gates.json` (T3 row) and in the §6 rows of the 12 cycles named in
  the Act log for 2026-08-02.
- **External dependencies:** none
- **Test file:** `template/tests/test_gate_logs.py` — the **binding** one: append the
  declared-summary-with-trailing-output case there (it is where `path_line` is already
  asserted, at `:97` and `:143`; those two assertions encode the current last-line rule and Do
  must bring them into step with the new one). Ship the leak regression as a new module
  `template/tests/test_suite_output_hygiene.py` that runs `tests.test_split` in a **subprocess**
  (`cwd=template`, `PYTHONPATH=src`) and asserts its stdout is empty — it must be a separate
  module, since a suite that shells out to itself would recurse. This project's C4 gate reverts
  the *production* hunks and keeps the patch's test files
  (`engine/scripts/run-verify.sh:70-81`), so an appended test earns its red; it does **not**
  classify on added test files. The gate runs every changed test module as
  `cd template && PYTHONPATH=src python3 -m unittest tests.<module>`, and requires all of them
  green with the fix.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cue — for the leak half, mirror the peer callsite **inside the same file**:
  `template/tests/test_split.py:856` (`with … redirect_stderr(io.StringIO()),
  redirect_stdout(io.StringIO()):`) is the convention the uncaptured paths (:181, :216, :311,
  :586-587) fail to apply; copy it rather than inventing a fixture-level capture. Do MAY open
  that callsite. For the evidence half, the rule lives in `_classify`
  (`template/src/pdca_harness/gates.py:596-621`) and its consumers are `_row`/`path_line`
  (`gates.py:529-533`, truncated to 120 chars) and the log reference at `gates.py:544`.
- **Prior-art check (triage cycles):** by affected file path against `origin/main` @ `9fb4860`
  (fetched 2026-08-02). `git log --oneline origin/main -15 -- template/src/pdca_harness/gates.py`:
  `f262fb0` (#415, persists the full output as `gate-logs/` — complementary, already merged, and
  the reason the "make /tmp inspectable" proposal is moot), `228e80b` (#368, timeout evidence),
  `c6784ec` (#329, the marker's exit-code half). Nothing changes the evidence-line rule.
  `git log --oneline origin/main -8 -- template/tests/test_split.py`: `f918fd8`, `3a3d8ce`,
  `5f3ee1d`, … — all split-behaviour fixes, none about output capture. The historical T3 reds
  this issue originally blamed on the fixture were fixed by **#417** and **#418** (merged
  2026-08-02) — verified: the suite is green on `origin/main` today. `gh pr list -R
  eduralph/pdca-harness --state open` → empty.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
