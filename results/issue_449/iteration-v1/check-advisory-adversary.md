# Adversarial review — issue_449 (flow adopts split children mid-run)

Advisory only; nothing here gates. Every citation is `$PDCA_TARGET` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`.

## Findings

- NEEDS-HUMAN — `template/src/pdca_harness/flow.py:414-421` — **the single-id path adopts a
  split that did *not* happen in this run, spending unrequested cycles.** `flow()` tests only
  `_is_split_parent(d)` (terminal + `close-disposition == split`, `flow.py:723-736`); nothing
  records whether the split occurred during *this* call. Concrete case, reproduced against the
  target: bundle 500 was split and closed in an *earlier* run, its children 601/602 left
  stranded PLANNED. A fresh `pdca flow 500` — which the CLI routes to `flow.flow`
  (`cli.py:639`) — breaks out of the loop on beat 1 (500 is COMPLETE, nothing to plan) and then
  drives **601 and 602 to COMPLETE**, emitting `flow: issue_500 split → adopted children
  issue_601, issue_602 into wave 1`. Pre-patch the identical call drove *zero* waves and just
  printed `COMPLETE`. Because `do_publish` is forwarded (`flow.py:421`), on a live instance
  those two cycles also publish draft PRs. This directly contradicts `brief.md` §Impact &
  compatibility — *"Behaviour changes only when a split happens during a run"* — and the docs
  hunk the patch adds (`docs/07-crosscutting.md:9-12`: *"When a bundle **in the drive set**
  reaches `close-disposition = split`"* — here it never was). It also splits the two entry
  points apart: the same stale parent through `flow.flow_ids(cfg, ["500"])` adopts **nothing**
  (the terminal-id filter at `flow.py:1258-1260` removes 500 before `_drive_and_act` ever
  runs), so `pdca flow 500` and `pdca flow 500 501` now disagree on identical on-disk state —
  while the patch's own planner prompt asserts the opposite (`template/agents/planner.md.jinja:58-60`:
  *"That holds for every shape"*). The scope call is the human's: either restrict adoption in
  `flow()` to a parent that was non-terminal at loop entry, or accept re-driving stranded
  children as intended and correct the brief/docs claim. Note brief §Design step 5 ("on exit,
  if the bundle is terminal with `close-disposition = split`") *does* read literally as
  implemented — the brief is internally inconsistent, which is why this needs adjudication
  rather than a rebuild.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:864-865` and `flow.py:894` — **the
  adoption announcement names a wave the child is not in.** Both report sites hardcode the
  parent's index + 1 (`into wave {k + 1}` / the literal `into wave 1`), but the children are
  placed by `_reschedule`'s recomputed `tail` (`flow.py:860`), which levels them by their own
  `Depends on`. The patch's own test proves the mismatch: it asserts the waves actually driven
  are `[["issue_500"], ["issue_601"], ["issue_602"]]` (`template/tests/test_flow_adopt_split.py:176-177`)
  while asserting the message says `into wave 1` for **both** children
  (`test_flow_adopt_split.py:178-179`) — 602 is driven in wave 2. I reproduced the same skew on
  a mixed drive set (`{500, 700}`, 700 depending on 500): waves driven
  `[[500], [601, 700], [602]]`, message still `into wave 1`. The brief's success criterion does
  spell the format as `into wave <k+1>`, so flag it to the builder rather than treat it as a
  spec change: report each child's real index from `tail`, and update the two assertions.

- NEEDS-HUMAN — `check-gates.json` row **T3** (`"result": "fail"`, evidence `== T3: root suite
  OK, driver suite FAILED (rc 1)`) — **the red is an environment fault, not this patch, and the
  frozen record does not say so.** The 11 failures are all in `template/tests/test_verify_base.py`
  (e.g. `:184`, `:111`, `:269`), asserting `PDCA_VERIFY_BASE == "UNSET"` and getting
  `origin/pdca-integration/main`. Cause: issue_449 is a wave>0 bundle carrying a `stack-base`
  marker, so `gates.py:533` exports `PDCA_VERIFY_BASE` into the T3 gate process itself, and
  that var leaks into the subprocesses `test_verify_base` spawns. I reproduced it exactly —
  `PDCA_VERIFY_BASE=origin/pdca-integration/main python3 -m unittest tests.test_verify_base`
  → `FAILED (failures=11)`, same count — and the whole suite is **green** without it (`Ran 1627
  tests … OK (skipped=2)`) with the patch applied. Nothing in `patch.diff` touches
  `test_verify_base.py`, `gates.py` or `publish.read_stack_base`. Human call only on whether a
  non-gating red left unexplained in the frozen record is acceptable at sign-off; **this is not
  a refutation of the fix** (issue #236) and is pre-existing test-isolation debt.

## Refutations attempted that failed

The red→green evidence held up under direct re-execution, and the fix survived every input I
could aim at it:

- **Is the red leg real?** Reverted only the production hunks (`flow.py`, `leaves.py`) to
  `HEAD` in a scratch copy, kept the test: `FAILED (failures=5)`, all on substantive assertions
  (`'PLANNED' != 'COMPLETE'`), **not** an ImportError — so it is not a PDCA-UNVERIFIABLE
  masquerading as red. Post-fix: `Ran 5 tests … OK`. The test drives the real `flow.flow_ids` /
  `flow.flow` entry points and the real `split.accept`, not a re-implementation.
- **Does adoption evict already-scheduled work?** `_reschedule` replaces `wave_list[k+1:]`
  wholesale (`flow.py:860`) from `partition_schedulable`, which is stricter than the
  `compute_waves` validation the run started with. Built the case — drive set `{500, 700}`,
  700 `Depends on: 500`, 500 splits — expecting 700 to be held out as "unresolved". It is not:
  the split parent is COMPLETE by the time `_adopt_split_children` runs, so the disk resolution
  at `waves.py:269-271` satisfies it. All four bundles reached COMPLETE.
- **Is the "transitive, bounded" claim (`flow.py:741-745`) real?** Chained a second split
  (500 → 601, 602; then 601 → 701, 702). Grandchildren were adopted and completed
  (`[[500], [601], [602, 701, 702]]`), and the `known`/`examined` guards stopped re-adoption.
- **Can the patch-less split parent crash the newly-reachable fold?** Changing `k < last` to
  `k < len(wave_list) - 1` (`flow.py:1097`) makes the parent's wave fold where it previously
  would not. `integrate.fold` filters on `_has_patch` (`integrate.py:160`), so a close-
  disposition parent with no `patch.diff` drops out — no raise.
- **Can a hand-edited lineage record break it?** `split.read_lineage` is total by construction
  (`split.py:373-391`), the traversal guard at `flow.py:762-766` rejects a child id resolving
  outside `cfg.bundle_root`, and both adoption sites sit inside `_isolate`.
- Also probed and could not break: adoption vs. the `flow_ids` Plan pre-pass (a just-accepted
  split leaves the parent BUILT, not terminal, so it survives the drive-set filter); duplicate
  adoption of a child already in the batch; held children still reaching the results map.
