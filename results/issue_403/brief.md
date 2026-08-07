# Brief — issue 403 / gate-evidence-in-reviewer-sandbox

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** gate-evidence-in-reviewer-sandbox
- **Defect:** The reviewer is asked to independently reproduce every recorded gate result, but
  its sandbox is seeded with `REVIEWER_INPUTS = ["patch.diff", "brief.md", "check-gates.json"]`
  only (`template/src/pdca_harness/leaves.py:64,1887` and the advisory twin at `:2201`). Since
  #415 each gate row also carries `row["log"] = "gate-logs/<rule_id>.log"`
  (`template/src/pdca_harness/gates.py:529-545`) — the full captured output plus a header
  naming `cmd`, `cwd` and `PDCA_WORKTREE` (`gates.py:557-593`) — and that directory is **not**
  copied into the sandbox. So the one artifact that would let the reviewer adjudicate a row it
  cannot re-run is referenced by a path that does not resolve where it works, and #370's stated
  promise ("the verdict's whole basis must be reconstructable from bundle files alone",
  `gates.py:535-537`) does not hold for the leaf that most needs it. The reviewer's contract
  text compounds it: it is told to mark an unrepeatable gate NEEDS-HUMAN
  (`template/agents/reviewer.md.jinja`, "Can't re-run a gate? Say so") and is never told that
  the frozen evidence exists or that the wrappers are instance-root/`$PDCA_WORKTREE`-scoped and
  are not runnable from `$PDCA_TARGET` at all. Result, from the pdca-pdca instance's frozen
  bundles: T2/T3 rows escalate as *"the exact `./engine/scripts/run-docs-check.sh` oracle named
  in `check-gates.json` is absent in this target checkout"* (issue_331, 341, 368, 375, 380, 386,
  387) while the same gates cleared on issue_356 — same instance, same wrappers, different
  reviewer behaviour.
- **Success criterion:** With the patch applied, the reviewer's sandbox (and the advisory
  leaves' sandbox, which uses the same seeding) contains the round's `gate-logs/` directory, so
  every path a frozen `check-gates.json` row references resolves inside the leaf's cwd — while
  `build-notes.md` remains absent (the independence contract, asserted by
  `template/tests/test_driver_slice.py:62`). Demonstrable by C4-verify alone: the named test is
  red with the production hunks reverted and green with them applied.
- **Falsifiability:** RED is producible offline on the environment Do gets — the existing
  sandbox tests (`template/tests/test_driver_slice.py:319-411`) already drive
  `leaves._run_review_sandboxed` with a fake leaf command and inspect the temp cwd, needing no
  model, network or service. A test asserting `gate-logs/<id>.log` is readable from the sandbox
  fails on `origin/main` today (the copy loop iterates file names only,
  `leaves.py:1887-1890`). The prompt/contract half is falsifiable the same way the existing
  grounding test does it (`test_driver_slice.py:257 test_review_prompt_grounds_on_pdca_target`
  asserts on the prompt text). The pdca-pdca C4 wrapper treats
  `template/src/pdca_harness/leaves.py` as production and `template/tests/*.py` as tests
  (`engine/scripts/run-verify.sh:39-53`), so reverting the production hunk gives a real red leg.
- **Invariant to restore:** Every artifact a frozen gate row references is present in the
  sandbox of the leaf asked to adjudicate that row — the verdict's whole basis is
  reconstructable from the bundle files the leaf actually has. Cited to the target's own
  written contract for the evidence logs: "the verdict's whole basis — including the partial
  capture of a timed-out gate — must be reconstructable from bundle files alone"
  (`template/src/pdca_harness/gates.py:535-537`, #370). Independence is unaffected: a gate log
  is the *gate's* output, never the builder's rationale.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** wave 0, alongside 428. This bundle's files
  (`template/src/pdca_harness/leaves.py`, the reviewer role prompt, `test_driver_slice.py`) are
  disjoint from the `gates.py` trio (428 → 402 → 401), so no dependency or conflict is
  declared. Sibling reviewer-sandbox issue **#419** (read-only git index blocks the stash-based
  C4 reproduction) is NOT in this batch and touches the same sandbox seeding — if it is briefed
  later, declare a conflict with this bundle then.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** make the round's frozen gate evidence available to the reviewer and advisory
  leaves, and align the reviewer's contract text so a row it cannot re-run is adjudicated from
  that evidence — with the missing-oracle escalation reserved for a row that has none. Both
  seeding call sites must stay in step (`leaves.py:1887-1890` and `:2201-2204`), and the prompt
  sentence that enumerates the sandbox contents ("You have ONLY patch.diff, brief.md and
  check-gates.json in this directory", `leaves.py:1472-1476`) must stop being false. Keep the
  vendored role body (`template/agents/reviewer.md.jinja`) and the driver-side prompt saying
  the same thing.
  / **out of scope:** the sandbox-interior doctor preflight and any per-gate
  `reviewer_reproducible` declaration (the issue's second proposal — a separate slice; do not
  start it here); making `engine/scripts/run-*.sh` runnable from `$PDCA_TARGET` (they are
  instance-root scripts by design and the instance is not the reviewer's checkout); #419's
  read-only-index defect; any change to what a gate records or to §6/C6 routing.
- **Repro instruction:** from a clean worktree of `origin/main`, run the existing sandbox test
  path with a bundle that has a `gate-logs/` directory: drive `leaves._run_review_sandboxed`
  exactly as `template/tests/test_driver_slice.py:319-345` does, with a fake reviewer command
  that lists its cwd, and observe that `check-gates.json` (copied in) names
  `gate-logs/<rule_id>.log` while no such path exists in the sandbox. The shipped consequence
  is frozen in `results/issue_386/SUMMARY.md` §10 and the §6 rows of issue_331/341/368/375/380/
  386/387.
- **External dependencies:** none
- **Test file:** `template/tests/test_driver_slice.py` — append to the existing sandbox/
  independence group (this project's C4 gate reverts the *production* hunks and keeps the
  patch's test files, `engine/scripts/run-verify.sh:70-81`, so an appended test earns its red;
  it does **not** classify on added test files). The gate runs the module as
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_driver_slice`.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cue — this is a composition slice: seed the evidence the way the sandbox already
  seeds its other invisible-from-a-temp-cwd inputs, `leaves._seed_sandbox_agents` /
  `_seed_sandbox_settings` as called at `template/src/pdca_harness/leaves.py:1894-1898`
  (best-effort, an OSError must never abort Check — `test_driver_slice.py:396` asserts exactly
  that). Do MAY open that callsite to mirror the failure posture. The directory name is
  `state.GATE_LOGS_DIR` (`template/src/pdca_harness/state.py:69-73`), already listed in
  `state.DOWNSTREAM_OF_BRIEF`; the row key is written at `gates.py:544`.
- **Prior-art check (triage cycles):** by affected file path against `origin/main` @ `9fb4860`
  (fetched 2026-08-02). `git log --oneline origin/main -8 -- template/src/pdca_harness/leaves.py`
  and `-- template/agents/reviewer.md.jinja`: `f262fb0`/#415 created `gate-logs/` (the artifact
  this bundle delivers to the sandbox, merged 2026-08-02 — after the Act review that filed this
  issue, which is why the diagnosis in the thread predates it), `a1a0f61` (#236, "mark gate
  verdicts provisional when the toolchain is absent") is the closest reviewer-contract work, and
  `#161`/`#261` established the seeding pattern for agents and settings. Nothing seeds the gate
  evidence. `gh search issues "reviewer sandbox"` → #419 (open, different defect), #161/#276/#379
  (closed). `gh pr list --state open` → empty.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
