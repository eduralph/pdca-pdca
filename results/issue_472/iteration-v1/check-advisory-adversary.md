# Adversarial review — issue_472 (flow: adopt split children mid-run)

Ground: `$PDCA_TARGET` = `/home/eddie/pdca/pdca-harness.pdca-wt` (HEAD `3e3b829`, patch applied
in the worktree). Red leg reproduced in a copy with the production hunks reverted
(`git checkout -- flow.py config.py leaves.py docs/ planner.md.jinja test_verify_base.py`,
new test kept).

## Findings

- NEEDS-HUMAN [human] — `flow.py:1001` (`wave_list[k + 1:] = tail`, splice) with the
  self-declared carve-out at `flow.py:969-973`: a bundle that declared `Depends on <the id
  that splits>` is re-levelled by its **own** edges and lands in the **same wave as the
  children that parent decomposed into**. Concrete, run at the target: `pdca flow 500 811
  812` where `811` declares `Depends on: 500` and `812` declares `Depends on: 811`, and
  `500` splits mid-run into `601`/`602`, drives
  `[['issue_500'], ['issue_601','issue_602','issue_811'], ['issue_812']]` and folds wave 1 as
  `['issue_500','issue_601','issue_602','issue_811']`. `811` declared it must build *after*
  `500`'s work; that work now lives in `601`/`602`, which build concurrently with it (in
  parallel under `lanes>1`) and are then folded together — so a patch conflict between `811`
  and a child now hits `integrate.fold` and stops the run ("wave 1 did not integrate;
  STOPPING — later waves not run", `flow.py:1290-1293`) in a configuration that pre-fix could
  not produce one. The docstring calls re-pointing a dependent "a `waves` semantics change,
  deliberately out of this scope"; the brief never mentions the case and no test pins it.
  Human call: accept the degraded edge, or scope a follow-up.

- NEEDS-HUMAN [impl] — `config.py:312-314` now states an invariant the patch breaks:
  "`max_auto_iters` … Clamped below `max_passes` so a wave's pass budget can't run out
  mid-auto-iteration (which #260 would then report as abandoned)". `flow.py:1221` hands a
  wave `min(allowance, budget - spent)`, which for an **adopted** wave can be far below
  `max_passes`. Concrete: `[driver].auto_iterate = true`, `max_passes = 20` (so
  `max_auto_iters` clamps to ≤ 19, default 3), `pdca flow 500` → `budget = 20 × 1`; the
  parent's wave spends 18, the adopted child's wave gets 2, and a child with 3 automatic
  rounds available exhausts its allowance mid-auto-iteration and is reported abandoned —
  exactly what the clamp exists to prevent. The patch rewrote the comment block immediately
  above this one (`config.py:294-301`) and left this neighbour stale; either the clamp text
  must acknowledge the pool or the adopted wave's allowance needs a floor.

- NEEDS-HUMAN [impl] — `template/tests/test_flow_adopt_split.py:821`
  (`test_an_unreadable_close_marker_never_kills_the_run`) is **green on the red leg**.
  Measured: reverting the production hunks leaves 18/20 failing; the two survivors are this
  guard and the deliberate no-adoption regression test at `:503`. Every assertion it makes
  (`601` PLANNED, `_adoptions() == []`, no `Traceback`, no `split adoption failed`, rc 0) is
  satisfied trivially by a build that has no adoption at all, so it cannot distinguish "the
  probe swallows `UnicodeDecodeError`" from "there is no probe". The brief's falsifiability
  says "The guard tests are red pre-fix by the same route" — this one is not. It is not
  worthless (narrowing `flow.py:832` to `except OSError` does fail it), but the cheap fix is a
  second, *readable* split parent in the same run whose children **are** adopted, so the test
  asserts a difference adoption makes.

- NEEDS-HUMAN [human] — `cli.py:794`: `pdca split <id> --accept` — the command the Plan /
  re-plan leaf runs *inside* the flow — still prints "`issue_500` marked split; run `pdca flow
  601 602` to drive the children". Post-fix that instruction, followed while the run is still
  going, starts a **second driver over the same child bundles**; the drive path takes no
  per-bundle lock (the only `flock`s reachable from `_drive_and_act` are `integrate`'s,
  `flow.py:1287`/`flow.py:1300`). The brief rules the hint out of scope because it is "still right for a
  split accepted outside a running flow" — but the case this feature creates is a split
  accepted *inside* one, which is precisely where the hint is now wrong. Human call: leave it
  (and the double-drive window) or make the hint conditional.

- NEEDS-HUMAN [impl] — `flow.py:894` and `flow.py:898`: both `_adoptable` guards are unpinned.
  Mutating away `if not d.exists() or s == state.UNPLANNED` and `if s in _TERMINAL` leaves all
  20 tests green (verified). Minor — neither is on the brief's enumerated "proven by test"
  list — but the fixture already has the hand-edited-record hook, and I confirmed by probe
  that `_record(iid, ["601", "999"])` prints `issue_999 — child of issue_500 NOT adopted: no
  brief.md`; one `assertIn` in an existing test closes both.

## Refutations attempted and failed

- **The red→green claim is honest.** With the patch: `cd template && PYTHONPATH=src python3 -m
  unittest tests.test_flow_adopt_split` → 20/20 OK. With production reverted and the test kept
  → 18 failures. The suite drives through `cli._flow` (`test_flow_adopt_split.py:158`) and
  builds fixtures with the production `split.accept`, not a re-implementation. The full driver
  suite at the target is green (1653 tests, OK, skipped=2), so T3's row holds too.
- **The brief's mandated mutation behaves exactly as specified**: `known=batch_names | taken`
  → `known=batch_names` (`flow.py:985`) fails exactly
  `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once` and nothing else, and the
  docstring at `flow.py:959-961` cites that test by name.
- **13 further mutations, all killed**: hardcoded `k + 1` announcement index (4 fails);
  `budget = allowance * (len(wave_list) + 1)` (5); fold boundary from a cached wave count (1);
  `except OSError` in `_is_split_parent` (1); dropping its terminal predicate (1); the stall
  exit returning 0 passes (1); removing the run-level `spent >= budget` break (3); handing each
  wave the full `allowance` (2); dropping `_report_held` from `_reschedule` (2); `bundles +=
  children` instead of `scheduled` (1); dropping the `seen` dedup (1); dropping the
  bundle-root traversal guard (1); not growing `batch_names` (1); narrowing the budget-break
  abandonment report to `wave_list[k+1:]` (3).
- **Budget/termination could not be broken.** Before wave *i*, `spent ≤ i·allowance` and
  `budget = n·allowance` (`flow.py:1177`), so the pool is provably non-binding for a run that
  adopts nothing, and `min(allowance, budget - spent) = allowance` there; every *driven* wave
  costs ≥ 1 pass, so a chain of splits terminates. `budget = 0` (which would break the run at
  wave 0 before publishing anything) needs `max_passes ≤ 0`, and both entry points clamp to ≥ 1
  (`config.py:660`, `cli.py:572`) — unreachable from the CLI.
- **Traversal guard holds**: `cfg.bundle()` on `"../../etc"`, `"/etc"`, `"a/b"` all fail
  `d.parent != cfg.bundle_root` (`flow.py:881`); `".."` / `"."` pass that check but resolve to
  non-existent `issue_..` / `issue_.` and are dropped by the brief guard.
- **The CSV shape the shipped docs advertise works**, though no test covers it: I drove
  `cli._flow` with `--from-csv` and no ids (→ `flow_batch` → the same `_drive_and_act`,
  `flow.py:1370`); the children were adopted, driven and reported (`flow: 5/5 complete`).
- **A cycle among adopted children does not crash and does not abort**: both children are held
  ("dependency cycle"), the run continues and exits **0** — i.e. a `pdca flow 500` that creates
  two bundles it cannot schedule still reports success. That is the contract the brief asked
  for ("held … excluded from the results map … never aborts") and `flow.py:975-979` states it
  outright, so I record it as a conforming trade-off rather than a refutation — but it is the
  one place the reviewer's "the run answers for what it did" framing is weakest.

Toolchain note (issue #236, not a refutation): the target checkout has no `engine/scripts/` or
`scripts/pdca`, so T2 (`run-docs-check.sh`) and the gating T4 (`contribcheck`) could not be
re-run here; C4 and T3 were reproduced directly and both hold.
