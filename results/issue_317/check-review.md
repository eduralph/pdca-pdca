Review task: add `pdca record [<ids>...]` to commit terminal-finished result bundles, optionally opening one batch PR.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines the selection, commit, PR, off-mode, and post-publish contracts clearly enough to judge implementation impact (`brief.md:7`). |
| C2 Reproduction (red pre-fix) | PASS | A temp copy with `patch.diff` reversed rejects `record` as an argparse invalid choice, so the pre-fix command surface is red (`template/src/pdca_harness/cli.py:396`). |
| C3 Change | PASS | The implementation adds the verb, config, state-owned terminal set, engine, publish hook, and tests within the requested surface (`template/src/pdca_harness/record.py:33`). |
| C4 Verification (red→green) | NEEDS-HUMAN | Decide whether the local red→green substitute is sufficient: exact `./engine/scripts/run-verify.sh` was unavailable at `$PDCA_TARGET` root and Git stash could not write the read-only worktree index, though `python3 template/tests/test_record.py` passed 15 tests (`template/tests/test_record.py:352`). |
| C5 Causal adequacy | PASS | The fix consumes `state.state` plus `state.TERMINAL`, so the safety predicate is centralized rather than re-enumerated in the new command (`template/src/pdca_harness/record.py:52`). |
| T1 Structure | PASS | The change is structured around one new engine module with narrow CLI/config/publish/state integration points, matching the existing command-module shape (`template/src/pdca_harness/cli.py:485`). |
| T2 Shape | NEEDS-HUMAN | Decide whether to accept shape without the configured docs wrapper: `./engine/scripts/run-docs-check.sh` was unavailable at `$PDCA_TARGET` root, so its recorded pass could not be independently re-run (`check-gates.json:29`). |
| T3 Runtime | NEEDS-HUMAN | Decide whether the recorded non-gating T3 failure is stale or material: local `python3 -m unittest discover -s template/tests` passed, but the exact `./engine/scripts/run-suite.sh` row was unavailable and `check-gates.json` reports a generated `split-proposal.md` failure (`check-gates.json:39`). |
| T4 Contribution | NEEDS-HUMAN | Decide prior-art/comtribution completeness beyond local history: affected-file `git log` and `--grep '#317'` found no record work, but the configured `pdca-pdca contribcheck` pass could not be re-run here (`check-gates.json:48`). |
| T5 Judgment | NEEDS-HUMAN | Decide the headless `issue = "ask"` behavior and best-effort post-publish recording scope: the implementation chooses commit-only fallback and never fails publish, which matches the brief's direction but is still policy-significant (`template/src/pdca_harness/record.py:95`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human sign-off must decide whether batch-recording terminal bundles is the right operational answer for preventing local-only provenance, independent of the passing offline tests (`brief.md:7`). |
