# Brief — issue 428 / unverifiable-marker-provenance

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** unverifiable-marker-provenance
- **Defect:** `_classify` honours `PDCA-UNVERIFIABLE:` as a bare substring on **any** line of
  a gate's captured output (`template/src/pdca_harness/gates.py:614-618` on `origin/main`).
  On an exit-0 gate, a line printed by anything the gate ran — a test's stdout, an assertion
  diff, a source comment a test read back — that merely *contains* the literal converts the
  gate's real verdict into `unverifiable`. #329 closed only the `rc != 0` half. Frozen
  evidence, `results/issue_387/check-gates.json`: the **gating** C4 row records
  `"result": "unverifiable"` with the reason
  `` `<reason>` and exit 77\n# (-> SUMMARY §6 NEEDS-HUMAN, non-gating) instead of a red->green … ``
  — a fragment of `engine/scripts/run-verify.sh`'s *comment block*, not a declaration by any
  gate. `unverifiable` does not count toward `overall`, so a genuine green C4 stops being
  recorded as verified and a genuine red would equally be laundered into "defer to the human".
  Structural for any project whose tests exercise the gate machinery: the harness's own suite
  is exactly that (`template/tests/test_gates_unverifiable.py:28,32,103`,
  `template/tests/test_prod_path_gate.py:51-89`).
- **Success criterion:** With the patch applied, `_classify` records a gate that exits 0 and
  whose captured output contains the marker only **embedded inside a line the gate relayed**
  (e.g. `# … Emit \`PDCA-UNVERIFIABLE: <reason>\` and exit 77`) as its real verdict —
  `pass` — while a gate that **declares** unverifiable itself still records `unverifiable`:
  both the exit-77 channel and the documented exit-0 self-declaration keep working
  (`template/engine/scripts/run-verify.sh:49`, `template/scripts/checks/test_exercises_production.py:24`,
  `template/tests/test_gates_unverifiable.py:103,113`). Demonstrable by C4-verify alone: the
  named test module is red with the production hunk reverted and green with it applied.
- **Falsifiability:** RED is producible offline on the environment Do gets — the gate under
  test is a shell one-liner run by `gates._run_checks`, no service or topology needed. A gate
  `cmd` that echoes a marker-containing line at a non-declaring position and exits 0 is
  classified `unverifiable` on `origin/main` today (reproduced: the frozen C4 row above), and
  must classify as `pass` after the fix. The pdca-pdca C4 wrapper
  (`engine/scripts/run-verify.sh:39-53`) counts `template/src/pdca_harness/gates.py` as a
  production path and `template/tests/*.py` as tests, so reverting the production hunk with
  the test in place gives a real red leg.
  **Self-poisoning caution:** the driver classifying THIS bundle's gates is the instance's own
  (unfixed) engine, so the C4 row for issue_428 is itself flipped to `unverifiable` if the
  gate's captured output carries the literal on any line. Do MUST NOT `print()` /`echo` the
  literal `PDCA-UNVERIFIABLE:` from the new test at module import or on a passing run (drive
  it through the gate fixture's captured subprocess output, as the existing tests do). A
  failing run may still print it; that is a §6 row for the human, not a criterion change.
- **Invariant to restore:** An `unverifiable` verdict is reached only when **the gate itself
  declares it**; output a gate merely *relayed* from a child process never changes the
  recorded verdict. Cited to the target's own written contract: "A gate with no possible
  verdict has its own channel; it must use it rather than piggy-backing on a failure"
  (`template/src/pdca_harness/gates.py:596-613` docstring) and the normative vocabulary in
  `template/PCDA/quality-cycle/04-validation-tooling.md:67` ("the marker lets a gate that did
  not fail defer to the human"). The declaration is the gate's; the substring is not.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Conflicts with:** 401
- **Ordering note:** wave 0. `402` (evidence-line rule) and `401` (T4 row status) both edit
  `template/src/pdca_harness/gates.py`; 402 declares `Depends on: 428` because its evidence
  rule builds on the notion of a gate-declared line this bundle settles, and 401 declares
  `Depends on: 402`, so all three are ordered into separate waves. `403` shares no file with
  this bundle (`leaves.py` + the reviewer role prompt) and builds alongside it in wave 0.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** make the recorded `unverifiable` verdict follow the gate's own declaration
  rather than any occurrence of the literal in captured output, and align the normative
  statement of the contract wherever the repo states it
  (`template/PCDA/quality-cycle/04-validation-tooling.md:67,71`,
  `06-quality-cycle-guidelines.md:226`, `08-glossary.md:153`, the `gates.py` module docstring
  at `:19-20` and `_classify`'s own docstring). The discrimination rule is Do's to choose —
  the issue names candidates (marker at line start only · the gate's last output line only ·
  the dedicated exit-77 channel only) and any is acceptable if it satisfies the criterion
  above; state the chosen rule in the docs so gate authors can write to it.
  / **out of scope:** the *evidence line* rule (`output.strip().splitlines()[-1:]`, issue 402
  — a different defect in the same function, briefed separately and scheduled after this);
  the T4 default-open row status (issue 401); changing what `unverifiable` means downstream
  (`assemble._unverifiable_items` → §6 → C6 stays exactly as is); the `rc != 0` half (#329,
  already closed and must not regress).
- **Repro instruction:** from a clean worktree of `origin/main`:
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_gates_unverifiable` is green
  today, because no case covers a *relayed* marker. Add a gate whose `cmd` is
  `echo '# see the docs: emit PDCA-UNVERIFIABLE: <reason> and exit 77'; exit 0` and assert the
  row records `pass`: it records `unverifiable` on `origin/main`. Executed at Plan against the
  target's own code: calling `_classify` with rc 0 and a two-line output whose FIRST line is a
  prose sentence quoting the marker and whose second is "suite OK" returns the result
  `unverifiable` with a reason that is a fragment of that prose — the frozen defect, reproduced
  in one call. The two legitimate declarations still return `unverifiable`, as they must: rc 0
  with a marker-led line, and rc 77. The shipped instance of the same defect is frozen at
  `results/issue_387/check-gates.json` (C4 row).
- **External dependencies:** none
- **Test file:** `template/tests/test_gates_unverifiable.py` — append the new cases to the
  existing module (this project's C4 gate reverts the *production* hunks and keeps the whole
  patch's test files, `engine/scripts/run-verify.sh:70-81`, so an appended test earns its red;
  it does **not** classify on added test files). The gate runs the module as
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_gates_unverifiable`.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cue — mirror the **peer tightening of the same contract**, #329's fix at
  `template/src/pdca_harness/gates.py:596-613`: it narrowed the marker's authority by exit
  code, recorded the reason in `_classify`'s own docstring, and aligned the normative doc
  sentence in `template/PCDA/quality-cycle/04-validation-tooling.md:67,71`. Do MAY open that
  callsite and follow the same shape (narrow the rule · explain why in the docstring · align
  the spec sentence) rather than inventing a new one.
- **Prior-art check (triage cycles):** by affected file path against `origin/main` @ `9fb4860`
  (fetched 2026-08-02). `git log --oneline origin/main -15 -- template/src/pdca_harness/gates.py`:
  `c6784ec` (#329, the `rc != 0` half — the complementary hole this bundle closes) and
  `8e0b6a9` ("align the marker contract", #330 review round 1) are the closest work; nothing
  addresses provenance on an exit-0 gate. `gh search issues "unverifiable marker"` → #329
  (closed) and this issue only. `gh pr list --state open` → empty (no in-flight work on any
  file in scope).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
