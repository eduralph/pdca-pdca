# Build notes — issue #565 (one-live-driver-per-bundle)

Target: `eduralph/pdca-harness` @ `main`. Worktree: `/home/eddie/pdca/pdca-harness.pdca-wt`
(base `b191da4`, the `pdca-integration/main` stack base; `cli.py` and `flow.py` are
byte-identical between the brief's `70ea12b` and that base — `git diff --stat 70ea12b HEAD`
touches only `docs/01-*`, `handoff.py`, `leaves.py` and two test modules — so every
`path:line` the brief gives still resolves).

All `path:line` below are **post-patch** lines in that worktree.

## What the change is

A `pdca flow` run now takes an exclusive, non-blocking advisory lock on a per-bundle file
before it drives that bundle, and holds it for the life of the run.

| | file:line |
|---|---|
| new module | `template/src/pdca_harness/drive_claim.py:1-207` |
| claim scope entered in the driving process | `template/src/pdca_harness/cli.py:573-574` (`_flow` → `_flow_claimed`) |
| named ids claimed before the first write | `cli.py:589-612` |
| claims threaded to the two drive entry points | `cli.py:634-636`, `cli.py:651-653` |
| the "excluded, not refused" line | `flow.py:805-817` |
| adoption claims each child | `flow.py:1139-1145` (`_refused_child`), wired at `flow.py:1267-1270` |
| the sweep claims each in-flight bundle | `flow.py:1796-1808` (`_claim_swept`), wired at `flow.py:1768-1773` |
| resume line says when it applies | `flow.py:777-782` |
| ignore rule | `template/.gitignore.jinja:40-43` |
| the rule + its known gap, documented | `docs/07-crosscutting.md:464-486` |

Release points (a bundle the run decides **not** to drive is let go at that decision):

| # | what | file:line |
|---|---|---|
| R1 | named id with no brief | `flow.py:1895-1896` |
| R2 | named id already terminal (non-seed) | `flow.py:1904-1910` |
| R2b | split-parent **seed**, after its adoption pre-pass | `flow.py:1549-1556` |
| R3 | swept bundle the scheduler held (incl. the "nothing schedulable" return) | `flow.py:1780-1787` |
| R4 | children whose reschedule failed outright | `flow.py:1286-1289`, released at `:1323-1325` |
| R5 | a child this splice held / one an earlier call adopted and this one retracts | `flow.py:1310-1316`, released at `:1323-1325` |

One existing expectation changed with the resume line:
`template/tests/test_flow_adopt_recovery.py:490-491` asserts that line by **equality**, so
the suffix had to be added there too. The brief predicted "today's text stays a prefix, so
existing assertions hold" — true for the three `assertIn` sites
(`test_flow_adopt_recovery.py:566`, `:594`; `test_flow_adopt_split.py:461`, `:495`, `:521`),
false for that one equality. A separate extra line would have avoided the edit, but (vii)
asks for *the line* to say when the command applies, and a second line is the thing an
operator scrolling past the per-bundle list does not read. One expected literal is the
cheaper honest price.

## Carved from #498 iteration-v2, as the brief directs

Taken: the claim mechanism and the CLI/flow wiring. **Left out**, because they exist only to
answer the split hint (the sibling child's): `_PASSED` / `Run.passed` (and its `flow.py`
caller `_past_adoption`, 3 call sites), `_held_now`, `sweeping` + `_SWEEP_SUFFIX` +
`_sweep_marks` + `_hold_new` + `Run.token`, `drives_children`, the `cli._split` hunk, and
the `planner.md.jinja` / `leaves.py` hunks. That is 332 → 207 lines in `drive_claim.py`
(`wc -l`: 125 lines dropped) and 6 of the prior 15 `flow.py` hunks gone.
`cli.py:843-844`'s closing line is untouched — `git diff` shows no hunk in `_split`.

From v2's suite I kept the lock tests and dropped the eight "(v) the hint is truthful" ones.
Added: one test per release point (the v2 adversary deleted five release lines with all 63
tests still green — see the mutation table below), the (vii) resume-line test, and a
self-refusal test.

## Alternatives considered

- **Claim inside `flow_ids` / `flow_batch` instead of `cli._flow`.** Rejected: the brief's
  (i) requires run B to exit *before* `flow_ids`' RESOLVED revalidation (`flow.py:1860-1874`)
  and its Plan pre-pass (`:1876-1884`), both of which write. `cli._flow` is the only point
  above all of them, and it is also below `main`'s keep-awake re-exec (`cli.py:433` →
  `cli.py:131-148`), which a claim taken earlier would not survive.
- **A pid file + liveness probe instead of a lock.** Rejected: it needs stale-record cleanup,
  which is exactly what (iii)'s SIGKILL half punishes. An open flock has no stale state — the
  kernel drops it when the handle closes, however that happens.
- **Deleting the claim file on release.** Rejected: unlinking a lock file another process may
  already hold open is how two holders of "the same" lock arise. Files accumulate (one per
  bundle, empty but for a pid) under `process/.drive-claims/`.
- **Keying claims by issue id.** Rejected: a `--rehearse` bundle root (`PDCA_BUNDLE_ROOT`)
  would collide with the real one, and a symlinked alias of a bundle would be two claims on
  one directory. Keyed on the resolved path instead (`drive_claim.py:73-94`), which is also
  what makes the self-refusal test (`issue_9` → `issue_7`) pass.
- **Refusing implicitly-reached bundles instead of skipping them.** Rejected by the brief's
  (ii), and it is the right call: a CSV batch that aborts because one unrelated leftover is
  busy is worse than one that drives the rest.

## Out of scope, noted per the brief

`pdca run` / `signoff` / `publish` and the other single-step verbs take **no** claim, so two
of them (or one of them and a live `flow`) can still write the same bundle. So does a CSV
batch's Plan session, which runs before that batch claims anything — the planner in it, or a
`pdca split --accept` it launches, can rewrite or split a bundle another live run holds.
Both are stated in `docs/07-crosscutting.md:482-486` and in `drive_claim.py:42-46`.

## Refuting my own test

- **(a) Genuine red?** Yes. `./engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS —
  red without the fix, green with it`. Red leg (production hunks reverted, test hunks kept):
  **14 of 23** cases in `test_flow_single_driver.py` fail, plus the recovery-suite line —
  including every core criterion: `test_a_second_flow_over_a_bundle_a_live_run_holds_is_refused`
  (i), `test_the_csv_sweep_skips_a_bundle_another_live_run_holds` /
  `test_split_adoption_skips_a_child_another_live_run_holds` (ii),
  `test_a_killed_run_holds_nothing_and_blocks_nothing` (iii),
  `test_a_run_that_cannot_open_its_claim_refuses_rather_than_drive_unclaimed` /
  `…_whose_filesystem_cannot_lock_…` / the two sweep+adoption fail-closed cases (v),
  `test_a_resume_line_for_a_bundle_the_run_still_holds_says_when_it_applies` (vii),
  `test_claims_live_outside_every_bundle_and_are_gitignored_in_the_render`.
  Green leg: 23/23.

  The nine cases that are green on the base are green **by design** — they pin a release
  that does not exist there to be wrong. So each was killed by deleting exactly its release
  line and re-running (`/tmp/mutate.py`, one mutant at a time, `flow.py` restored after):

  | mutation | test that went red |
  |---|---|
  | drop R1 (`claims.release(d)`, no-brief) | `test_a_named_id_with_no_brief_is_let_go_at_the_skip` |
  | `if claims is not None and not seed:` → `if False:` | `test_a_named_id_already_terminal_is_let_go_at_the_skip` |
  | drop R2b (seed release) | `test_a_split_parent_seed_is_let_go_once_its_adoption_pre_pass_is_done` |
  | drop R3 (held sweep) | `…_the_scheduler_holds_is_let_go_while_the_batch_runs` **and** `…_before_the_nothing_schedulable_return` |
  | move R3 *below* the "nothing schedulable" return | `test_a_swept_bundle_is_let_go_before_the_nothing_schedulable_return` (only) |
  | `dropped = children` → `dropped = []` | `test_children_a_failed_reschedule_leaves_in_flight_are_let_go` |
  | drop the `children` half of R5 | `test_an_adopted_child_the_reschedule_holds_is_let_go_while_the_run_goes_on` |
  | drop the `remaining` half of R5 | `test_a_child_a_later_reschedule_retracts_is_let_go` |

  Seven release points, seven distinct killers, plus an ordering mutant. The remaining
  base-green cases are (iv) `…_the_split_it_spawns_is_not_blocked` /
  `…_does_not_refuse_itself` and (viii) `…_says_nothing_about_claims`, which exist to pin
  what must *not* change and are meant to be green both sides.

- **(b) Production path?** Yes. Every run goes through `cli._flow` with the real
  `flow.flow_ids` / `flow.flow_batch` / `_drive_and_act` / `_adopt_split_children`, the real
  `split.accept` (`split.py:857`), the real `state.state`, and `drive_claim`'s real locks via
  `act._lock_exclusive` (`act.py:29-62`). `./engine/scripts/run-prod-path.py` (C5):
  `PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package 'pdca_harness'`.
  Nothing is re-implemented; the only stand-ins are *leaves* (the six model subprocesses,
  stubbed as the whole offline suite stubs them) and two pass-through spies used purely as
  observation points inside a live run: `cli._report_batch`
  (`test_a_swept_bundle_is_let_go_before_the_nothing_schedulable_return`) and
  `waves.partition_schedulable` raising (`--break-reschedule`), which is the only way to
  reach `_reschedule`'s `except Exception` branch (`flow.py:1098-1101`). Both call the
  production function afterwards or leave it to it.

- **(c) Fixture includes the fault?** Yes. The competing driver is a **real second process**
  (`_spawn` → `subprocess.Popen`, its own interpreter, `PYTHONPATH=<checkout>/template/src`,
  no `PDCA_*` inherited) — never an in-process thread, which could pass on a per-process
  claim for the wrong reason. The SIGKILL leg really sends `SIGKILL` to that process and
  waits for it. The "nothing changed" assertions fingerprint every path under `results/`
  (size + mtime_ns + sha256, `_fingerprint`) rather than checking a curated subset. The
  bundles under contention are the ones actually held: run A is paused *inside a build*
  (`_pausing_build`) and asserted still alive (`a.poll() is None`) at the end of each case.

## Runner / gates run

Through the project's own runners only (`docs/INTEGRATION.md` §3-4), never a hand-rolled
invocation:

- `./engine/scripts/run-verify.sh` (C4, gating) → **PASS**
- `./engine/scripts/run-suite.sh` (T3) → `root suite OK, driver suite OK` (1955 tests, 2 skipped)
- `./engine/scripts/run-docs-check.sh` (T2) → `docs lint clean, site render + link audit clean`
- `./engine/scripts/run-prod-path.py` (C5) → PASS

Commit-readiness: the target ships no formatter/linter config (no `pyproject.toml`,
`.pre-commit-config.yaml`, ruff/black/flake8 anywhere in the tree) and no hooks under
`.githooks`; CI is `render-check.yml` / `docs-check.yml` / `docs.yml` /
`require-linked-issue.yml`, the first two of which are exactly T3 and T2 above. House style
is ≤ ~95 columns: no production line this patch adds exceeds 95, and the test file's longest
is 98 (repo max is 236, `cli.py:180`).

No external dependency beyond the base toolchain was needed — stdlib Python 3.14 here (≥ 3.11
per the brief) and `git`, both already registered.
