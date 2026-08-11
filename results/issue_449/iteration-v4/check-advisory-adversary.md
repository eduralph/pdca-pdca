# Adversarial review — issue 449 / flow-adopts-split-children-mid-run

Advisory only; never gates. Everything below is grounded on the target source at
`$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, working tree = patch applied).

## Findings

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:451`: the single-id adoption
  tail is wrapped in `_isolate`, which swallows `PreflightError`, so `pdca flow 500` exits
  **0** where `pdca flow 500 601` exits **1** on byte-identical disk state.** `_isolate`
  contains every `Exception` (`flow.py:~640`, "only `Exception` is contained"), and the
  adopted children's drive raises `PreflightError` at `flow.py:1209` when a pooling wave
  fails lane preflight. Concrete reproduction (run against the target, `lanes=2`, parent
  500 stranded terminal-on-split with two *independent* children 601/602 so the adopted
  wave pools, `preflight.lane_preflight` returning `(False, [...])`):
  - `flow.flow_ids(cfg, ["500"])` → raises `PreflightError: lane preflight failed for a
    lanes=2 batch — not fanning out`; `cli.py:652-656` catches it and returns **1**.
  - `flow.flow(cfg, "500")` → returns `COMPLETE`, printing only `flow: issue_500 — split
    adoption failed (PreflightError: …); skipping this bundle (left COMPLETE)`; `cli.py:639`
    then returns **0** because the *parent* is COMPLETE. The children are still `PLANNED`.
  This contradicts three claims the patch itself adds: `docs/07-crosscutting.md:259-260`
  ("`pdca flow 500` and `pdca flow 500 501` do the same thing to the same disk"),
  `flow.py:1113-1115` ("behave the same on the same disk state"), and the Iteration-1
  sign-off RULING (b) that required the two entry points to be consistent. The abort is
  deliberately loud by design ("aborts the run … rather than produce false-red bundles",
  `flow.py:1197-1200`) — downgrading it to a contained per-bundle skip means automation
  reading the exit code sees a successful flow. Fix is narrow (re-raise `PreflightError`
  — and anything else meant to stop a run — out of the tail, or scope the `_isolate` to the
  detect/validate step rather than the whole `_drive_and_act`), plus a test asserting both
  entry points behave identically here; the suite currently has no case where the tail
  raises at all.

- **NEEDS-HUMAN — `check-gates.json:78-85`: the gating T4 pass is not verifiable from the
  supplied inputs (verdict provisional).** T4's oracle is `./scripts/pdca contribcheck`,
  which is not present in the target worktree, and `patch.diff` contains no
  `commit-msg.txt` / `pr-description.md` — the artifacts T4 judges. Iteration 2's
  carry-forward raised exactly this and it is still unresolved from where Check sits. Not a
  refutation of the fix; a human must confirm the contribution artifacts independently.

## Attempted and could not refute

- **The red→green is real and exercises production.** Reverse-applied the production hunks
  only (`git apply -R --include='template/src/*'`, test file kept) into a scratch copy:
  **18 failures**; with the hunks restored, **15 tests OK**. The tests drive
  `flow.flow_ids` / `flow.flow` / `flow.flow_batch` — the real entry points — and build the
  split with the production `split.accept`, not a simulation.
- **The assertions bind — no tautology, nothing mocked away.** Seven targeted mutations of
  the exact behaviours prior iterations demanded, each caught: dropping the duplicate-child
  `seen` dedup (`flow.py:838`) → 1 fail; ignoring `wave_offset` in the announcement
  (`flow.py:990`) → 3 fails; un-capping the run pool (`flow.py:1160`) → 4 fails; handing the
  single-id tail a fresh budget instead of `max_iters - spent` (`flow.py:453`) → 1 fail;
  narrowing `_is_split_parent`'s catch to `OSError` (`flow.py:794`) → 1 error; dropping the
  terminal parent instead of seeding it (`flow.py:1445`) → 5 fails; splicing into the
  current wave `k` instead of `k+1` (`flow.py:969,978`) → 6 fails.
- **The T3 red is genuinely pre-existing, not this patch.** With a clean environment the
  entire driver suite is green: **1637 tests, OK (skipped=2)**. Re-running
  `tests.test_verify_base` with `PDCA_VERIFY_BASE` inherited reproduces exactly 11 failures
  **both** on the patched tree and on a pristine `git archive HEAD` export — identical
  counts. The carry-forward's "test-isolation fault, out of scope" is verified, not assumed.
- **Hostile lineage records do not break it** (`flow.py:824-873`). Probed on the target: a
  record naming the parent as its own child terminates (`examined` guard); `["601", None,
  42, "../evil", "  ", "602"]` drives 601/602 and rejects `../evil` with *"it resolves
  outside …/results"*; two children in a dependency cycle are both held (`dependency cycle`)
  and the run continues; conflicting siblings land in separate waves.
- **Recursion is bounded and does not multiply the budget.** An adopted child that splits
  again mid-run drove 4 waves (500 → 601 → {701,702}) on a pool sized for 1 wave, spending
  exactly 6 of 6 allowed passes, with each announcement naming the child's real wave
  (601→1, 602→2, 701→2, 702→3). Two split parents in one wave both had their broods adopted.
- **The pool is provably non-binding without adoption**, so no ordinary batch is newly
  truncated: each wave spends `min(allowance, budget - spent)` and `budget = allowance ×
  len(wave_list)` (`flow.py:1160,1220`), so `spent` cannot reach `budget` before the last
  wave. `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` covers it.
- **`_drive_wave`'s new `int` return is total** — all three exit paths return `used`
  (`flow.py:1046,1076,1085`); no caller in `template/tests` depends on the old `None`.
- **Entry-point agreement holds at a *binding* budget for a mid-run split too** (a case the
  suite only covers at a non-binding budget): both entry points ended
  `601=COMPLETE, 602=PLANNED` and printed the identical *"the run's pass budget is spent
  (3 pass(es) over 2 wave(s))"* line at `max_passes/max_iters=3`.
- **Adoption really does reach `flow_batch`'s drive phase**, as `docs/07-crosscutting.md`
  and `template/agents/planner.md.jinja` now claim: a mid-run split under `flow.flow_batch`
  adopted 601/602 into waves 1 and 2.
- **The operator-facing caveat the previous round asked for is documented** — the
  recovery-run pool ("names only a parent already terminal on a split … its pool is one
  wave's worth") is in `docs/07-crosscutting.md`, not only in a module docstring.
- Tried and could not reach: an announced wave index going stale after a *later* adoption
  re-levels the remainder (constructed a name-lower conflicting grandchild; the schedule did
  not move an already-announced child). No concrete failing case, so not filed.
