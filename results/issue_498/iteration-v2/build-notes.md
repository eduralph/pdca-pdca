# Build notes — issue 498 / one live driver per bundle, and a truthful split hint (iteration 2)

Target: `eduralph/pdca-harness @ main`, base `70ea12b`, worktree `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`). Every `path:line` below is on the patched
tree unless marked "base".

This is a rebuild on top of iteration 1's claim mechanism, which sign-off called sound (an
OS lock per bundle, released on return, raise and SIGKILL, taken after the keep-awake
re-exec). I read `iteration-v1/` (patch, notes, the three check files and the
carry-forward) because the carry-forward points at line numbers inside that patch.

## The six carry-forward items, one by one

1. **Fail closed when a claim cannot be recorded.** `Run.take` now returns a `Refusal`
   (`drive_claim.py:166-172`) instead of `""` when the claim file cannot be opened
   (`drive_claim.py:190-195`) or the lock fails for a reason that is not another holder
   (`drive_claim.py:196-202`). What happens with it depends on how the bundle was reached,
   as asked:
   - named ids: `cli._flow` refuses the whole run, rc 1, before any write, with a line
     naming the bundle and the error (`cli.py:589-611`);
   - CSV sweep: the bundle is skipped with a line (`flow.py:1765-1770`, `_claim_swept`
     at `flow.py:1791-1804`);
   - adoption: the child is skipped with a "NOT adopted: …" line (`flow.py:1271-1274`,
     `_refused_child` at `flow.py:1143-1149`).
   Both implicit paths print through one helper, `_excluded` (`flow.py:800-812`), which
   uses the "NOT adopted: …" shape of the existing reports. Held-by-another and
   could-not-record get different remedies in the same line shape.
2. **Release swept claims the batch does not drive.** Right after
   `waves.partition_schedulable`, every held name is released (`flow.py:1777-1782`). This
   runs before the "nothing schedulable" early return, so that path is covered too.
   Adoption's `dropped → release` logic from iteration 1 is kept (`flow.py:1285`, `:1291`,
   `:1313-1314`, `:1322-1324`). Both release paths now have tests (see the table).
3. **The CSV-sweep hint needs a live run.** I did not add a liveness probe to the
   inherited `SWEEP_ENV` token. I removed the environment variables entirely (both
   `PDCA_FLOW_RUN` and `PDCA_FLOW_SWEEPS`). A CSV batch now holds a live lock "mark",
   `<process_dir>/.drive-claims/<bundle-root digest>-<run token>.sweep`, from before its
   Plan session until the sweep has enumerated what is in flight (`flow.py:1747-1760`;
   `drive_claim.sweeping` at `drive_claim.py:282-305`). `drives_children` counts a mark
   only while it is locked (`drive_claim.py:330`). A run that returned, raised or died
   holds no lock, so its mark cannot speak for it. The mark also ends once the sweep is
   behind the run, so a straggler accept after that point is not told the sweep will pick
   it up.
4. **Docs softened.** `docs/07-crosscutting.md:469-482` now says runs never *drive* the
   same bundle at once, rather than "never share a bundle". A new paragraph at
   `docs/07-crosscutting.md:484-488` names the gap: Plan sessions are not fenced. A CSV
   batch's Plan session runs before that batch claims anything, and any planner (or a
   `pdca split --accept` it runs) can still rewrite the brief of, or split, a bundle another
   live run holds. Single-step verbs take no claim either.
5. **Criterion (v): the first sentence wins.** `drives_children` (`drive_claim.py:308-332`)
   no longer looks at the environment. It returns True when a live run holds the parent's
   claim, whichever shell the accept was typed in, or when a live CSV mark exists for this
   bundle root. Otherwise the instruction prints byte-identical to the base (`cli.py:881-890`;
   the `else` branch is the base's two lines, unchanged, at `cli.py:889-890`).
6. **Docstring narrowed.** `drive_claim.py:26-34` now says the two-runs-in-one-process
   guarantee is a property of the lock, and that nothing else in the module is kept in the
   environment or a module global. That is true now: no environment variables are left.
   It also names the NFS case, where `flock` falls back to per-process POSIX locks.

## Two additions beyond the carry-forward, and why

Item 5's rule makes "a live run holds the parent's claim" mean "a live run will drive the
children". Two places in iteration 1 would have made that false, so I closed them:

- **A named id the run skips is let go** (`flow.py:1890-1891`, `:1899-1901`). `flow_ids`
  skips an id that still has no brief after the Plan pre-pass, or that is already terminal
  (a split parent is handed on as a seed; its children are claimed one by one by
  adoption). Iteration 1 kept the claim on such ids for the whole run. Under item 5, a split
  of such a bundle typed elsewhere would have printed "the running flow will drive the
  children", and no run would have. A `pdca flow` naming it would also have been refused
  although nobody was driving it, which is the same shape as item 2.
- **"Past adoption" stamp.** A run adopts a split only at one point per bundle: the splice
  right after that bundle's wave. After that point the run still holds the bundle (it
  publishes, folds and reports it), but it will not adopt a later split of it. `Run.passed`
  (`drive_claim.py:211-221`) writes `passed` under the pid in the claim file, and
  `drives_children` ignores a held-but-passed claim (`drive_claim.py:328`). The flow marks
  each wave after its splice (`flow.py:1619`), marks a wave with nothing runnable
  (`flow.py:1562`), and marks everything left once the wave loop ends, before a possibly
  long Act session (`flow.py:1705`). Helper: `_past_adoption` at `flow.py:1134-1140`.
  - Alternative rejected: release the claim after the wave instead of stamping it. That is
    the same number of call sites, but the run still reads those bundles, and its results
    map reads their state from disk at the end (`flow.py:1707`). A second run driving a
    released bundle would then show up as this run's result. The stamp costs about 20
    lines and keeps the claim's lifetime equal to the run's for every bundle the run
    drives.

## The mechanism (unchanged in kind from iteration 1)

- A claim is an exclusive, non-blocking `flock` (Act's cross-platform
  `act._lock_exclusive`, called through the module at call time) on
  `<process_dir>/.drive-claims/<bundle name>-<digest of resolved path>.lock`
  (`drive_claim.py:97-104`), held on an open handle in `Run._held` (`drive_claim.py:175-242`).
  The OS drops it on return, raise or death. Python opens files non-inheritable
  (PEP 446), so no spawned leaf holds it.
- Claim files are never deleted: unlinking a lock file another process may have open is
  how two holders of "the same" lock happen. The sweep mark is the one file that is
  unlinked, and only by its owner, after release (`drive_claim.py:301-305`): nobody else
  ever holds it, and probes only test it.
- Probes (`_held_now`, `drive_claim.py:145-162`) open read-only, so asking never creates a
  file.
- The claim scope is entered in `cli._flow` (`cli.py:573-574`), which `main()` reaches only
  after the keep-awake re-exec (`cli.py:433`, base). Named ids are claimed in sorted order
  before `--from-briefs` seeding, `flow_ids`' RESOLVED revalidation and its Plan pre-pass
  (`cli.py:589-611`).
- The files live outside every bundle and are gitignored in the render
  (`template/.gitignore.jinja:40-44`). `state.state` never sees them, and the results commit
  adds only bundle paths (`record.py:111`, base).
- `claims` is an optional keyword on `flow_batch` (`flow.py:1726`), `flow_ids`
  (`flow.py:1820`), `_drive_and_act` (`flow.py:1469`) and `_adopt_split_children`
  (`flow.py:1155`). `None` (the library path, and every existing test that calls these
  directly) claims nothing and behaves exactly as the base does.
- Swept bundles are claimed *before* the partition on purpose. The partition treats a
  dependency outside the swept set that is not COMPLETE as unresolved
  (`waves.py:264-274`, base), so a dependent of a bundle another run holds is held there.
  Claiming after the partition would leave it scheduled against a missing prerequisite.
- Claiming adopted children moved from inside `_adoptable` (iteration 1) to right after
  it returns (`flow.py:1271-1274`). If `_adoptable` raises part-way, `_isolate` swallows it,
  and in iteration 1 the children it had already claimed stayed claimed for the whole run.

## Alternatives ruled out (with the cost)

1. **Keep `SWEEP_ENV` and add a liveness probe on its token** (the carry-forward's literal
   wording for item 3). It fixes the dead-run case, but it cannot answer an accept typed
   in a second shell during a live CSV Plan session (no token there), which is item 5's
   case for CSV batches. It also keeps the environment-variable state item 6 flagged. The
   lock-mark design costs about 45 lines (`drive_claim.py:107-110`, `:258-305`, `:330`) and
   removes that state entirely.
2. **One lock per run plus a claim registry under a mutex** (to avoid one open file
   descriptor per claimed bundle): about 120 lines against the per-bundle lock's 60, plus
   stale-record handling. Rejected; the descriptor cost is listed under gaps.
3. Iteration 1's rejections still hold: fixing only the hint (the Invariant rules it out);
   a lock file inside each bundle (`record.py:111` would commit it, and a refused run
   would create `results/issue_3/…` before failing on 7); locking the bundle directory
   (an UNPLANNED id has no directory until the Plan pre-pass creates it); a per-process
   registry (an in-process thread reads as "self"); pid files (pid reuse, stale-file
   cleanup).

## Tests — `template/tests/test_flow_single_driver.py` (new, 22 tests; bundle copy is identical)

Every test goes through `cli._flow` / `cli._split` with all six leaves stubbed and gates
empty. The fixture is copied from `test_flow_adopt_split.py:43-63`, not imported. The file
imports only existing modules (`act, cli, leaves, split, state`, `config`). The competing
driver is a real second process (`_spawn`, `test_flow_single_driver.py:292-314`): it runs
`python -c <bootstrap>`, which loads this same file by path, with
`PYTHONPATH=<checkout>/template/src` and no `PDCA_*`. `setUp` also strips `PDCA_*` from the
test process. Every wait is bounded (60 s), and children are killed and reaped at
teardown.

| Test (line) | Criterion | On the base |
|---|---|---|
| `…_a_live_run_holds_is_refused` (:367) | (i), (iii) return | red: B returns 0 and drives 7 |
| `…_refused_whole_before_its_plan_pre_pass` (:410) | (i) before Plan pre-pass | red: 3 planned, 7 driven |
| `…_cannot_open_its_claim_refuses…` (:431) | carry-forward 1 | red: drives 7 unclaimed |
| `…_filesystem_cannot_lock_refuses…` (:448) | carry-forward 1 | red: drives 7 unclaimed |
| `…_run_that_raises_leaves_nothing_behind` (:470) | (iii) raise | green (guard) |
| `…_killed_run_holds_nothing_and_blocks_nothing` (:489) | (i), (iii) SIGKILL | red: runs under the holder |
| `…_csv_sweep_skips_a_bundle_another_live_run_holds` (:515) | (ii) sweep | red: drives 7 |
| `…_csv_sweep_skips_every_bundle_it_cannot_claim` (:537) | (ii) + carry-forward 1 | red: drives both |
| `…_adoption_skips_a_child_another_live_run_holds` (:555) | (ii) adoption | red: adopts 601 |
| `…_adoption_skips_a_child_it_cannot_claim` (:580) | (ii) + carry-forward 1 | red: adopts 601 |
| `…_swept_bundle_the_scheduler_holds_is_let_go…` (:609) | carry-forward 2 | red: `flow 7` not refused |
| `…_adopted_child_the_reschedule_holds_is_let_go…` (:634) | carry-forward 2, (iv) | red: `flow 601` not refused |
| `…_named_id_the_run_skips_is_not_its_to_speak_for` (:663) | (v) second sentence | green (guard) |
| `…_parent_whose_wave_is_behind_the_run…` (:684) | (v), passed stamp | red: `flow 7` not refused |
| `…_inside_the_run_driving_the_parent…` (:716) | (v) id run | red: instruction printed |
| `…_split_command_spawned_by_the_run…` (:736) | (iv), (v) | red: instruction printed |
| `…_accept_from_another_shell_while_a_live_run_holds…` (:763) | carry-forward 5 | red: instruction printed |
| `…_inside_a_csv_batch_plan_session…` (:782) | (v) CSV | red: instruction printed |
| `…_after_the_csv_batch_has_ended…` (:800) | carry-forward 3 | green (guard) |
| `…_standalone_accept_…_byte_identical` (:825) | (v) byte-identical | green (guard) |
| `…_run_not_driving_that_parent_keeps_the_instruction` (:834) | (v) byte-identical | green (guard) |
| `…_claims_live_outside_every_bundle_and_are_gitignored…` (:855) | Citations: out of bundles, out of git | red: no record at all |

The five guards pass on the base by design: they pin output that must stay exactly as it
is today, or a claim that must *not* be held. The three release tests and the "wave behind
the run" test each go red on the base on their first half (a second run over a bundle a
live run holds is not refused there).

## Evidence (all through the project's own scripts, from the instance root)

- **C4** — `engine/scripts/run-verify.sh` with `PDCA_BUNDLE=results/issue_498`,
  `PDCA_WORKTREE=$PDCA_WORKTREE`, under `timeout 900`. Green leg `Ran 22 tests … OK`. Red
  leg (production hunks reverted, test kept) `Ran 22 tests … FAILED (failures=17)`: all 17
  are `AssertionError`, with no `_FailedTest` and no import error. Final line
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. The worktree was restored
  afterwards (`git status` unchanged).
- **Mutation checks** (each applied to the patched source, the new test file run, the
  source restored). Every one is caught by exactly the test(s) meant to pin it:
  no past-adoption stamp → the wave-behind test; no skip release → the skipped-id test;
  no sweep-held release → the sweep release test; no dropped release → the adoption release
  test; fail-open on open → the two unopenable tests; fail-open on lock → the two ENOLCK
  tests; no sweep mark → the CSV Plan-session test; hint ignoring the parent's claim → the
  three id-run hint tests.
- **T3** — `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`, and
  `test_render_then_slice` ran (not skipped). That test renders the template and runs the
  generated project's own suite, including this new file, inside a rendered instance.
  Driver suite `Ran 1943 tests … OK (skipped=2)`, the same two skips as the base.
- **T2** — `engine/scripts/run-docs-check.sh`: docs lint clean, site render + link audit
  clean (the `#lanes` anchor resolves).
- `git apply --cached --check patch.diff` against a scratch index read from `70ea12b`:
  applies clean.

## Refuting my own test

- **(a) Genuine red?** Yes. With the production hunks reverted by the C4 script, 17 of 22
  fail, each on an assertion, for the reasons in the table: a second run over a held bundle
  returns 0 and drives it; a run with no way to record a claim drives anyway; the sweep and
  adoption drive held or unclaimable bundles; the id-run, second-shell, spawned and CSV
  accepts print `run pdca flow 601 602`. The five that pass there are guards on behavior
  that must not change, or on a claim that must not exist. The mutation checks above also
  show each new release/stamp/fail-closed path is bound by its own test, not only the
  suite as a whole.
- **(b) Production path?** Yes. Every run is production `cli._flow` / `cli._split`, the
  production stub leaves and production `split.accept`. The stand-ins are:
  - Plan sessions that write a brief/proposal and then call production `cli._split` or
    `split.accept` (or pause first);
  - a builder wrapper that pauses, then calls the production stub builder;
  - a sign-off wrapper that withholds one bundle and passes the rest to the production stub;
  - a ^C raised inside the builder;
  - `act._lock_exclusive` patched to fail with ENOLCK. This one simulates a filesystem
    without lock support, which cannot be produced offline. Only the OS primitive is
    replaced; the code under test is production. The "cannot open" case uses a real
    filesystem fault instead (a regular file where the claims directory goes).
  The second driver is a separate OS process running production code, never a thread or
  a mock.
- **(c) Fixture includes the fault?** Yes. Each refusal/exclusion test has a real second
  process paused mid-drive and holding its claim. The SIGKILL test really kills it. The
  fail-closed tests really cannot record a claim. The dead-batch test really ends the
  batch by raising before its sweep, and only then lets the late accept run. The
  second-shell test runs the accept in a different process from the run that holds the
  parent.

## Gaps and judgment calls for the human

- **Out of scope, not fixed (per the brief):** `pdca run`, `signoff`, `publish`, `try` and
  the other single-step verbs take no claim, so `pdca run 7` beside a live `pdca flow 7`
  can still interleave. The library `flow.flow()` takes none either.
- **Plan sessions are not fenced** (now named in the docs, item 4). A planner in any
  session can rewrite a brief of, or split, a bundle another live run holds.
- **A nested `pdca flow` spawned inside A over A's bundles is refused.** I read (iv)'s "every
  leaf or command spawned inside A" as the non-driver commands (leaves, gates,
  `split --accept`, `contribcheck`). A nested `flow` is a second driver, which the
  Invariant forbids. None of the non-driver commands takes a claim, and `split --accept`
  only probes without blocking.
- **Fail closed has a cost.** On a process dir that cannot hold the claim files (read-only,
  or a filesystem without locks), every `pdca flow` naming ids now refuses with rc 1, and a
  CSV batch drives nothing. The batch still exits 0 in that case: its results map is empty,
  the same as the existing "nothing schedulable" path. Each skipped bundle is named on
  stderr. Say if you want a non-zero exit there.
- **The resume command for a bundle the run walked away from is refused until the run
  ends.** The run still holds that bundle (it is in its results map). The refusal says
  which pid holds it. I kept the claim rather than release it; see the "past adoption"
  section.
- **One open file descriptor per claimed bundle, for the run's life.** The default soft
  limits are 1024 (Linux) and 256 (macOS), so a single run holds a few hundred bundles
  before `take` fails, and failing is now fail-closed. A realistic batch is far below
  that, since each bundle costs a full cycle and a human sign-off.
- **A SIGKILLed driver's leaves can outlive it.** Headless leaves run in their own session,
  so a killed driver's builder or reviewer may keep writing the bundle after a new run
  has claimed it. This is not a regression, and the brief asks that nothing left by a dead
  run stop a later one.
- **Leftover files.** A killed CSV batch leaves one empty, unlocked `.sweep` file. It is
  harmless (probes read it as "not live") and is never cleaned up. Claim files accumulate,
  one small file per bundle ever driven, under the gitignored `process/.drive-claims/`,
  and are never deleted on purpose.
- **Misleading reason in one message.** When the sweep excludes a bundle another run
  holds, a swept dependent of it is held by the partition with the existing reason
  "unresolved dependency (7)", although 7 is being driven elsewhere. That line comes from
  `waves.partition_schedulable` and is not changed here.
- **A tiny race at the very start of a CSV batch.** Between creating its mark and locking
  it (microseconds), the mark reads as not live. Only a shell accept at that exact moment
  would print the instruction.
- **NFS:** `flock` becomes a per-process POSIX lock. Two processes are still kept apart;
  two runs inside one process are not (documented in the module docstring).
- **Windows** (out of scope beyond import): claims and marks work through Act's
  `msvcrt` helper, and import is unaffected. But another process cannot read a claim
  file's stamp while it is locked, so refusal lines show no pid, and a held-but-passed
  claim reads as "will drive". That falls back to item 5's literal rule.

## Commit-readiness

The target configures no formatter, linter or pre-commit hook: no
`.pre-commit-config.yaml`, no ruff/flake8 settings. CI runs render-check, docs-check,
docs and require-linked-issue, and the render and docs checks were run above, green.
Checked by hand: `git diff --check` is clean, no added line exceeds 100 columns (matching
the surrounding code), and there are no unused imports in the two new files. The DCO
`Signed-off-by` trailer belongs to publish, not the patch.

## Housekeeping (for the harness)

`.scratch498/` at the worktree root is untracked and not in `patch.diff`. It holds my
scratch scripts (a message printer, the mutation runner), the C4 and T3 logs, one throwaway
instance directory, and the two scratch git index files I used to build and check
`patch.diff` without touching the worktree's real index. Per the builder rules I did not
delete it; the harness reclaims the worktree.
