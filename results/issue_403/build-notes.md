# Build notes — issue 403 / gate-evidence-in-reviewer-sandbox

Target: `eduralph/pdca-harness` @ `main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`,
base `9fb4860`). All `path:line` below are **post-patch** lines in that worktree unless the
text says "on `origin/main`".

## What the defect actually is

Since #370/#415 every gate row carries `row["log"] = "gate-logs/<rule_id>.log"`
(`template/src/pdca_harness/gates.py:544`), written with a header naming `cmd`, `cwd`,
`PDCA_WORKTREE` and then the combined output verbatim (`gates.py:557-593`), under the stated
promise "the verdict's whole basis … must be reconstructable from bundle files alone"
(`gates.py:535-537`).

The reviewer/advisory leaves run in a temp sandbox cwd seeded from
`REVIEWER_INPUTS = ["patch.diff", "brief.md", "check-gates.json"]` — a list of **file names**,
copied by a `shutil.copy2` loop (`leaves.py:1887-1890` and the advisory twin `:2201-2204` on
`origin/main`). A *directory* therefore never landed. So the leaf holds a `check-gates.json`
whose rows point at `gate-logs/<id>.log`, and that path does not resolve one `cd` away from
where it was written — the one artifact that lets it adjudicate a row it cannot re-run.

The contract text compounded it: the driver prompt asserted "You have ONLY patch.diff,
brief.md and check-gates.json in this directory" (`leaves.py:1472-1476` on `origin/main`) and
the role body told the leaf to escalate an unrepeatable gate to NEEDS-HUMAN
(`template/agents/reviewer.md.jinja:50-57` on `origin/main`) without ever naming the frozen
evidence, or the fact that the `oracle` wrappers are instance-root/`$PDCA_WORKTREE`-scoped
and are *not* runnable from `$PDCA_TARGET`. Hence the observed split: identical wrappers,
T2/T3 escalated as "the oracle is absent in this target checkout" on issues 331/341/368/375/
380/386/387 but cleared on 356.

## The change (5 hunks + docs)

1. `leaves.py:1601-1632` — new `_seed_sandbox_gate_logs(d, sandbox)`. Mirrors
   `_seed_sandbox_agents` (`leaves.py:1562-1588` — the composition cue the brief named):
   `shutil.copytree(..., dirs_exist_ok=True, ignore_dangling_symlinks=True)` inside a
   `try/except (shutil.Error, OSError)` that degrades to a stderr note. No `gate-logs/`
   ⇒ silent no-op.
2. `leaves.py:1939` — call it in `_run_review_sandboxed`, right after the `REVIEWER_INPUTS`
   copy loop and before the agents/settings seeds.
3. `leaves.py:2256` — the same call in `_run_advisory_sandboxed` (the brief requires both
   sites to stay in step).
4. `leaves.py:1474-1486` — `_REVIEW_PROMPT`: the sandbox-contents sentence is now true, and
   the leaf is told to *read* `gate-logs/<rule_id>.log` for a gate it cannot re-run, that the
   wrappers are instance-root/`$PDCA_WORKTREE`-scoped (their absence from `$PDCA_TARGET` is
   expected, not a finding), and that the escalation is **reserved** for a row with no log
   (no `log` key / a `log_error` / a missing file).
5. `template/agents/reviewer.md.jinja:17-22` (Inputs) and `:52-67` ("Can't re-run a gate?") —
   the vendored role body says the same thing, including that a gate log is the *gate's*
   output so it costs no independence.

Also: `leaves.py:2136-2140` — the advisory prompt's identical "You have ONLY …" sentence
became false the moment the seed landed, so it is corrected too (one clause);
`leaves.py:64-66` — a comment at `REVIEWER_INPUTS` so the next reader knows the file-name
list is not the whole sandbox; `docs/05-check.md:420-423` — the doc sentence enumerating
sandbox contents, likewise false otherwise.

`build-notes.md` is untouched by all of this — it is not in `REVIEWER_INPUTS` and
`gate-logs/` is the gate's own output, so `test_driver_slice.py:62` (independence) still
holds, and the new tests assert `build-notes.md` absent from both sandboxes.

## What I ruled out, with the cost

- **Adding `"gate-logs"` to `REVIEWER_INPUTS`.** Rejected: the constant is also the
  independence contract's public surface — `reviewer_input_paths` (`leaves.py:1467-1469`)
  returns `d / name` per entry and `run_review` asserts on it (`leaves.py:1539-1541`); the
  copy loops call `shutil.copy2`, which raises `IsADirectoryError` on a directory. Making it
  work means a branch inside both loops plus a `reviewer_input_paths` that returns a
  directory to callers that expect files — ~6 changed lines in shared code and a widened
  public meaning, versus one best-effort helper called twice. Worse, it would put the
  evidence *inside* the hard independence assert's list, where a future `+= [...]` edit is
  one keystroke from a real leak.
- **Rewriting only the prompt/role text ("if you can't re-run a gate, say so more
  precisely").** Rejected outright: the brief names an **invariant to restore** — every
  artifact a frozen row references is present in the sandbox of the leaf asked to adjudicate
  it. Text alone leaves the row's `log` path dangling; the leaf would be told to read a file
  that is not there, which is strictly worse than today. Text is necessary (a leaf that never
  learns the evidence exists will not look) but not sufficient — hence both halves.
- **Making `engine/scripts/run-*.sh` runnable from `$PDCA_TARGET`.** Explicitly out of scope
  in the brief, and wrong: they are instance-root scripts and the instance is not the
  reviewer's checkout.
- **A sandbox-interior doctor preflight / a per-gate `reviewer_reproducible` flag.** The
  issue's second proposal; the brief puts it out of scope. Not started.
- **Symlinking `gate-logs/` into the sandbox instead of copying.** Rejected: the leaf's
  sandbox may be confined (`--setting-sources project`, `leaves.py:1860-1875`) and a symlink
  escaping the temp cwd is exactly the read the confinement is meant to bound; a copy of a
  handful of small text files is the same shape as the agents seed already in place.

## Test — `template/tests/test_driver_slice.py` (appended to the sandbox/independence group)

Five tests at `:415-531`, in `AdvisoryReviewResilience` beside the existing seeding tests:

- `test_sandbox_seeds_gate_logs_so_every_row_log_resolves` (`:444`) — the binding one. The
  fixture runs a **real** bundle-scoped gating gate through `gates.run_gates`
  (`_real_gate_round`, `:434-442`), so `check-gates.json` **and** `gate-logs/T3-log.log` are
  the production artifacts, not hand-written. A fake leaf command (`_sandbox_probe`, `:421`)
  reads the seeded `check-gates.json` from its own cwd, and for **every** row carrying a
  `log` key resolves that row's own `log` value relative to the cwd — plus asserts the file
  really carries the header and both output lines, and that `build-notes.md` (written into
  the bundle by the fixture) is absent.
- `test_advisory_sandbox_seeds_gate_logs_too` (`:467`) — same, through
  `_run_advisory_sandboxed`; keeps the two call sites in step.
- `test_gate_log_seed_failure_does_not_abort_check` (`:484`) — `copytree` raising `OSError`
  degrades to the §6 placeholder, never an aborted Check (the posture
  `test_driver_slice.py:396` already asserts for the agents seed).
- `test_sandbox_without_gate_logs_is_a_no_op` (`:500`) — an older/stub round has no
  `gate-logs/`; the leaf runs exactly as before.
- `test_reviewer_contract_routes_unrepeatable_gate_to_its_log` (`:515`) — the contract half,
  asserted the way `test_review_prompt_grounds_on_pdca_target` (`:257`) does: the driver
  prompt, the advisory prompt and the vendored role body all name `gate-logs/`, and the old
  false sentence is gone. The role body is located as `.md.jinja` *or* rendered `.md` so the
  test also passes inside a copier-rendered instance (the T3 root suite renders the template
  and runs this module — it failed there on the first attempt with a hard-coded `.jinja`).

## Red → green, through the project's own runner

`./engine/scripts/run-verify.sh` (the C4 gate; reverts **production** hunks only and keeps
the patch's test files, `engine/scripts/run-verify.sh:70-81`):

```
== C4 green leg: … Ran 84 tests … OK
== C4 red leg: … FAILED (failures=3)
    test_sandbox_seeds_gate_logs_so_every_row_log_resolves
      AssertionError: False is not true : {'gate-logs/T3-log.log': False}
    test_advisory_sandbox_seeds_gate_logs_too            (same)
    test_reviewer_contract_routes_unrepeatable_gate_to_its_log
      AssertionError: 'gate-logs/' not found in "…You have ONLY patch.diff, brief.md and
      check-gates.json in this directory…"
C4 PASS: red without the fix, green with it
```

Also run green: `./engine/scripts/run-suite.sh` → "T3: root suite OK, driver suite OK"
(1499 template-repo tests incl. the rendered instance + 84 driver tests);
`./engine/scripts/run-docs-check.sh` → "lint_docs: OK … link audit OK" (I touched
`docs/05-check.md` and a `.md.jinja`). The patch applies clean to `9fb4860`
(`git apply --check` against a stashed tree). The target repo ships no pre-commit
formatter/linter config (no `.pre-commit-config.yaml`, no ruff/flake8 config; CI runs exactly
the docs lint + the two suites above), and no added line exceeds the module's existing width
norm.

## Self-refutation (forced)

- **(a) Genuine red?** **Yes** — verified by actually reverting: `run-verify.sh`'s red leg
  `git apply -R --exclude=tests/* --exclude=template/tests/*` removes the production hunks
  (and the prompt/role text) while keeping the new tests, and 3 of the 5 go red with the
  assertions quoted above. The two that stay green are the degradation/no-op guards, which by
  construction describe behaviour that is unchanged when the seed is absent — they are
  regression guards, not the binding evidence.
- **(b) Production path?** **Yes** — the tests call `leaves._run_review_sandboxed` and
  `leaves._run_advisory_sandboxed` (the production leaf entry points; only `leaves._invoke`,
  the subprocess boundary, is replaced by a probe that runs *inside the real sandbox cwd*),
  and the fixture's `check-gates.json` + `gate-logs/` are produced by the production
  `gates.run_gates`. No copy or re-implementation of the seeding logic exists in the test.
- **(c) Fixture includes the fault?** **Yes** — the fixture is a real gating gate whose row
  actually carries `log: gate-logs/T3-log.log`, and the assertion resolves *that row's own
  value* from the leaf's cwd (not a hard-coded name the fixture chose), then reads it back and
  checks the header + both output lines. `build-notes.md` is genuinely written into the bundle
  before the run, so the independence assertion is a real exclusion rather than a vacuous one.

No external dependency was needed beyond the brief's "none": the whole red→green runs offline
with stdlib unittest and `echo`-shaped gate commands.
