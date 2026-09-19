# Build notes — issue 498 / one live driver per bundle, and a truthful split hint

Target: `eduralph/pdca-harness @ main`, base `70ea12b` (worktree `$PDCA_WORKTREE`).
All `path:line` below are on the patched tree unless marked "base".

## What the patch does

**One live driver per bundle.** A new module, `template/src/pdca_harness/drive_claim.py`,
holds the one cross-process rule. It mirrors Act's session lock (`act.py:125-159` base):
non-blocking, reports rather than crashes when it cannot open its file, released by the OS
when the process ends, and uses the same cross-platform `act._lock_exclusive` / `act._unlock`
helpers (`act.py:29-62` base), so there is no hard `import fcntl` at load time.

- A claim is an exclusive `flock` on `<process_dir>/.drive-claims/<name>-<digest>.lock`,
  held on an open handle for the whole run (`drive_claim.py:116-148`, `Run.take`). The key
  is the bundle's *resolved* path (`drive_claim.py:69-78`), so a `--rehearse` bundle root
  never collides with `results/`, and a symlinked alias of a bundle is the same claim.
- The files live **outside every bundle**, so `state.state()` never sees one and no results
  commit can carry one (`record.py:111` only adds `issue_*` paths). They are gitignored in
  the render (`template/.gitignore.jinja:40-43`), next to Act's `.act-session.lock`.
- The **run** owns its claims, not the process. `Run` keeps a dict of the handles it holds;
  a second `take` of a bundle it already holds is a no-op (`drive_claim.py:121-122`), so a
  run never refuses itself. Two runs in one process hold separate handles, and `flock`
  refuses the second exactly as it refuses another process.
- The lifetime is the run: `drive_claim.run(cfg)` (`drive_claim.py:172-190`) releases every
  claim in `finally` (normal return or raise), and the OS drops the `flock` if the process
  dies. Python opens files non-inheritable (PEP 446), so no leaf or command the run spawns
  holds a claim after the run ends. Lock files are never deleted: unlinking a lock file
  someone may already have open is how two holders of "the same" lock happen.
- The claim is taken **in the process that drives**: `cli._flow` enters the scope
  (`cli.py:573-574`), and `main()` has already done the keep-awake re-exec before
  `_flow` runs (`cli.py:433` base). A claim taken before that exec would be lost.

**Where claims are taken (every CLI drive path):**

- **Named ids** — `cli._flow_claimed` claims every named id, sorted, *before anything writes*:
  before `--from-briefs` seeding, before `flow_ids`' RESOLVED revalidation and before its
  Plan pre-pass (`cli.py:589-603`). One held by another live run refuses the whole run with
  rc 1 and the line `flow: issue_7 is held by another live `flow` run (pid N) — refusing to
  start a second driver over it; no bundle was touched. …`. Criterion (i).
- **CSV batch sweep** — `flow_batch` claims each in-flight bundle after the Plan session and
  *skips* the ones another run holds, naming each (`flow.py:1728-1733`,
  `_claim_swept` at `flow.py:1748-1761`). The rest of the batch goes on. Criterion (ii).
- **Split adoption** — `_adoptable` claims a child as its last step and reports one held
  elsewhere in the existing "NOT adopted: …" shape (`flow.py:1063-1068`, cf. base
  `flow.py:1041-1056`). `_adopt_split_children` then **releases** the claim on any child it
  did not schedule (held, retracted, or a failed reschedule) (`flow.py:1257`,
  `:1263`, `:1284-1286`, `:1294-1296`), because those are left in flight with a "resume it
  with `pdca flow <id>`" line, and that command must not be refused by the run that just
  stopped driving it. Criterion (ii) + (iv) "bundles A adopts become A's".
- `claims` is threaded as an optional keyword through `flow_ids` (`flow.py:1778`,
  `:1872`), `flow_batch` (`flow.py:1693`, `:1745`), `_drive_and_act` (`flow.py:1441`,
  `:1516`, `:1587`), `_adopt_split_children` (`flow.py:1134`, `:1245`) and `_adoptable`
  (`flow.py:915`). Default `None` = claims nothing, so the library path (`flow.flow()`,
  out of scope) and every existing test that calls these directly behave exactly as today.

**The truthful hint (criterion v).** `cli._split` now asks
`drive_claim.drives_children(cfg, parent)` (`cli.py:873-882`, `drive_claim.py:230-254`):

- True only when this process is **inside** a live run (`PDCA_FLOW_RUN`, set by
  `drive_claim.run` for the run's lifetime and inherited by every leaf and command it
  spawns) **and** either that run is a CSV batch in its Plan session (`PDCA_FLOW_SWEEPS`,
  set by `drive_claim.sweeping` around `leaves.do_plan_batch`, `flow.py:1712-1713`), or that
  run holds the parent's claim right now (the claim file's first line is the run's token,
  and a non-blocking probe shows it locked, `drive_claim.py:211-227`).
- Then it prints `issue_500 marked split; the running `pdca flow` will drive the children
  (601 602) — do not start another flow for them`.
- Otherwise it prints the old instruction. That line is byte-identical to base
  (`cli.py:843-844` base: the two string pieces concatenate to the same text), and the
  test `test_a_standalone_accept_prints_the_instruction_byte_identical` pins it against the
  exact base string.

**Text updates (scope list):** `template/agents/planner.md.jinja:153-156` (code-block
comment) and `:183-188` (the "`--accept` still prints" bullet); the planner seed prompt
`template/src/pdca_harness/leaves.py:1118-1123`; `docs/07-crosscutting.md:340-348`. I also
added one paragraph to docs 07 §Lanes (`docs/07-crosscutting.md:469-479`) describing the
claim rule, because the refusal line is new user-visible behavior with no other doc. Both
prompts still contain `flow <child-ids>`, `csv` and `flow 500 501`, which
`test_split.py:1291-1307` pins.

## Alternatives ruled out (with the cost)

1. **Fix only the hint** (make `_split`'s last line conditional, no claims). About 10 lines
   in `cli.py`. Rejected: the brief's Invariant says guarding the hint alone cannot satisfy
   it — two operator-started `pdca flow 7` runs would still interleave writes to one bundle.
2. **Lock file inside each bundle** (`results/issue_7/.drive.lock`). Rejected on two concrete
   counts: `record.py:111` runs `git add -A -- <bundle paths>`, so the file would be
   committed unless every instance's `.gitignore` covered a per-bundle pattern; and a
   refused run B naming `3 7` would create `results/issue_3/…` before failing on 7, which
   breaks (i) "nothing under `results/` changes because of B".
3. **Lock the bundle directory itself.** Rejected: an UNPLANNED id has no directory until
   `flow_ids` creates it in the Plan pre-pass (`flow.py:1765` base), which is exactly
   the write (i) says must come after the claim. It also cannot be done with `msvcrt`.
4. **A per-process registry** (module-level set of held names). Rejected: an in-process
   thread would read as "self" (the false pass the brief warns about), and it says nothing to
   another process.
5. **PID file + liveness check** (`os.kill(pid, 0)`). Rejected: PID reuse, stale files that
   need cleanup, and different semantics on Windows. `flock` is released by the kernel on
   death, so (iii)'s SIGKILL half needs no code.
6. **Take the claims inside `flow_ids` / `flow_batch`** instead of `cli._flow`. It would
   need the same wrapper there plus a new exception type carried back to `cli._flow` for the
   rc-1 refusal, and it would still miss the `--from-briefs` seeding (`cli.py:605-616`),
   which writes bundle directories before `flow_ids` is called. `cli._flow` is the one
   place both CLI shapes pass through before any write: a 3-line scope + an 8-line claim
   loop (`cli.py:573-574`, `:596-603`).
7. **Decide the hint by a lock probe alone** (no run token). Rejected: an accept typed in a
   shell while some other run holds the parent would then print the "running flow will drive
   them" line, but (v) lists a shell accept as the byte-identical case; and a run that held
   the parent but already drove its wave would not re-examine it, so the line would be false.

## Tests

`template/tests/test_flow_single_driver.py` (new; copy in the bundle dir). 11 tests, all
through `cli._flow` / `cli._split`, all six leaves stubbed, gates empty. The fixture shape is
copied from `test_flow_adopt_split.py:43-63`, not imported. Imports only existing modules
(`cli, leaves, split, state`, `config`), so the C4 red leg loads the module.

- The competing driver is a **real second process** (`_spawn`, `test_flow_single_driver.py`
  `:221-240`): `python -c <bootstrap>` loads this same test file by path and calls
  `_child_main`, which runs production `cli._flow` / `cli._split`. `PYTHONPATH` is set to
  `template/src`; a "separate shell" child gets no `PDCA_*` at all; a "spawned inside A"
  child inherits the run's environment. `setUp` also strips every `PDCA_*` from this
  process for the test's duration, so a gate or an enclosing flow cannot leak in.
- A run is held mid-drive by `_pausing_build` (`:117-134`): the first build call drops a
  `ready` file and waits (bounded) for a `go` file, then calls the **production** stub
  builder. Every wait is bounded by 60 s; child output goes to files so a paused child can
  never block on a full pipe; children are killed and reaped at teardown.

| Test | Criterion | Red on base because |
|---|---|---|
| `test_a_second_flow_over_a_bundle_a_live_run_holds_is_refused` | (i), (iii) normal return | B (subprocess) returns 0 and drives 7 while A is paused |
| `test_a_named_id_list_is_refused_whole_before_its_plan_pre_pass` | (i) before Plan pre-pass | B plans 3 and drives 7; no "held" line |
| `test_a_killed_run_holds_nothing_and_blocks_nothing` | (i) reverse direction, (iii) SIGKILL | the in-process run drives 7 while the other process holds it (rc 0 ≠ 1) |
| `test_the_csv_sweep_skips_a_bundle_another_live_run_holds` | (ii) sweep | the batch drives 7 under its holder |
| `test_split_adoption_skips_a_child_another_live_run_holds` | (ii) adoption | 601 is adopted and driven under its holder |
| `test_an_accept_inside_the_run_driving_the_parent_does_not_say_run_flow` | (v) id run, (iv) | the instruction is printed |
| `test_a_split_command_spawned_by_the_run_is_neither_blocked_nor_told_to_run_flow` | (iv) real child process, (v) | the instruction is printed |
| `test_an_accept_inside_a_csv_batch_plan_session_does_not_say_run_flow` | (v) CSV Plan session | the instruction is printed |
| `test_a_run_that_raises_leaves_nothing_behind` | (iii) raise | green on base by design (base has no claim to leak) |
| `test_a_standalone_accept_prints_the_instruction_byte_identical` | (v) byte-identical | green on base by design (guard) |
| `test_an_accept_inside_a_run_not_driving_that_parent_keeps_the_instruction` | (v) byte-identical | green on base by design (guard) |

**Evidence (project runner).** `engine/scripts/run-verify.sh` (the C4 gate) with
`PDCA_BUNDLE=results/issue_498`, `PDCA_WORKTREE=$PDCA_WORKTREE`, under `timeout 900`:
green leg `Ran 11 tests … OK`; red leg (production hunks reverted, test kept)
`Ran 11 tests … FAILED (failures=8)` — all eight are `AssertionError`s, no import or load
failures; final line `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Run
twice, on the final patch the second time.

**Wider checks, all green with the patch:**
- offline driver suite `cd template && PYTHONPATH=src python3 -m unittest discover -s tests`:
  `Ran 1932 tests … OK (skipped=2)` (run twice, once on the final patch);
- root suites (render + `copier update` compat) with the instance venv's python:
  `Ran 24 tests … OK`;
- docs: `lint_docs.py` → `lint_docs: OK`; `render_site.py --check` → `link audit OK`;
- the new test run five times in a row: OK each time (about 0.8 s per run);
- `git apply --check --cached patch.diff` against the base index (`70ea12b`): applies clean.

## Refuting my own test

- **(a) Genuine red?** Yes. `run-verify.sh` reverts exactly the production hunks and keeps
  the test: 8 of 11 fail, each with an assertion failure, for the reasons in the table
  (B returns 0 and drives 7; the batch and adoption drive a held bundle; the in-run accept
  prints `run `pdca flow 601 602` to drive the children`). The three tests that pass on base
  are guards on "unchanged" behavior (byte-identical instruction; release after a raise) and
  are meant to pass there.
- **(b) Production path?** Yes. Every test drives production `cli._flow` / `cli._split`,
  the production stub leaves, and production `split.accept`. The only stand-ins are the
  Plan leaf (it writes a brief/proposal and then calls production `cli._split` or
  `split.accept`), a builder wrapper that pauses and then calls the production stub
  builder, and one builder that raises `KeyboardInterrupt` to simulate a ^C. The second
  driver is a separate OS process running production code, not a thread or a mock.
- **(c) Fixture includes the fault?** Yes. The fault is "a second live driver over the same
  bundle", and every refusal/exclusion test has one: a real second process paused inside its
  own Do beat, holding its claim. The SIGKILL test really kills that process mid-drive, and
  the spawned-accept test runs `split --accept` as a real child process of the running flow.

## Gaps and judgment calls for the human

- **Out of scope, not fixed (per the brief):** `pdca run`, `pdca signoff`, `pdca publish`,
  `pdca try` and the other single-step verbs take no claim, so `pdca run 7` next to a live
  `pdca flow 7` can still interleave. Library `flow.flow()` takes none either.
- **Plan sessions are not fenced.** A CSV batch's interactive Plan session (a model) could
  still edit the brief of a bundle another run holds; only the sweep *after* it is claimed.
  Same for `flow_ids`' shared Plan pre-pass touching an id it was not given.
- **A nested `pdca flow` spawned inside A over A's bundles is refused.** I read (iv)'s
  "every leaf or command spawned inside A" as the non-driver commands (leaves, gates,
  `split --accept`, `contribcheck`); a nested `flow` is a second driver, which the
  Invariant forbids. None of those non-driver commands takes a claim, and `split --accept`
  only probes without blocking, so none can be blocked.
- **"Will drive the children" in an id run assumes the split is accepted at sign-off.**
  Adoption needs the parent terminal on `split` (`flow.py` `_is_split_parent`). If the human
  rejects the split at sign-off, the run does not drive the children; the parent is then
  reported as in flight by the existing `_warn_abandoned` path.
- **Over-claiming named ids.** Every named id is claimed for the whole run, including ones it
  then skips (already terminal, or still UNPLANNED after Plan). A second run naming such an
  id is refused until the first ends. Conservative; I did not add early release for them.
- **Unopenable claim → drives unclaimed, with a warning** (`drive_claim.py:164-169`). This
  keeps (vi) on a read-only process dir, but the invariant is not enforced there.
- **Windows:** claims work (the lock helper is Act's), but reading another process's claim
  file fails under `msvcrt`'s mandatory lock, so the in-run hint falls back to today's
  instruction there, and the refusal line shows no pid. Import is unaffected.
- **NFS:** Linux emulates `flock` with POSIX locks on NFS, which are per-process. Two
  processes are still kept apart, but two runs in one process would not be.
- **Claim files accumulate**, one small file per bundle ever driven, under the gitignored
  `process/.drive-claims/`. They are never deleted, on purpose (see above).

## Commit-readiness

The target configures no formatter, linter or pre-commit hook (no `.pre-commit-config.yaml`,
no ruff/flake8 settings; CI runs only the render check and the docs check, both run above
and green). No added line exceeds 100 columns, matching the surrounding code. The publish
commit's DCO `Signed-off-by` trailer is publish's job, not the patch's.

## Housekeeping (for the harness)

- The docs render check wrote its output to `.docs-build-check/` at the worktree root; it is
  untracked and not in `patch.diff`.
- I wrote one scratch diff to `/tmp/pdca498-new.diff` while comparing patches, which is
  outside the roots I was given. It is a copy of this patch and holds nothing else.
