# Adversarial review — issue_469 (flow: adopt split children mid-run)

Advisory only; nothing here gates. Evidence was re-run at `$PDCA_TARGET`
(`/home/eddie/pdca/pdca-harness.pdca-wt`), whose working tree is byte-identical to
`patch.diff`.

## Evidence re-run (the red→green does hold)

- Green leg: `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split`
  → **22 tests OK**. Red leg (production hunks reverted, `template/tests/*` kept, as
  `run-verify.sh --exclude=template/tests/*` does) → **19 of 22 FAIL**. The 3 that stay
  green pre-fix are the no-regression guards
  (`test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`,
  `test_a_named_id_list_keeps_its_strict_scheduling_contract`,
  `test_an_unreadable_close_marker_never_kills_the_run`) — correct for their purpose.
- The suite drives the real production path: `cli._flow` → `flow.flow_ids` →
  `_drive_and_act`, with the real `split.accept` building the fixture; every monkeypatch
  (`flow._drive_wave`, `flow._build_all`, `flow._point_at_integration`, `flow.flow_ids`)
  is a pass-through spy that calls the original and returns its value. No parallel
  re-implementation, no mocked-away defect.
- T3 independently reproduced: all 79 driver modules, **1655 tests OK (2 skipped)**.

## Refutations

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/flow.py:1112` (and
  `flow.py:1073`): the run-pool accounting is pinned only for waves that reach
  all-terminal. Mutate the budget-exhausted exit `return used` → `return 0` (or the
  no-progress exit at `:1073`) and **all 22 tests still pass**, yet the mutant overspends
  the operator's budget. Concrete case, run against both: `pdca flow 500 810
  --max-passes 4` where 810 is never answered (halts AWAITING_SIGNOFF) and 500 splits into
  two *independent* children — production spends 4 `_build_all` passes and leaves 601/602
  PLANNED; the mutant spends **5** and drives both to COMPLETE. The wave that runs its
  allowance out without finishing is exactly the case where "one pool, never multiplied"
  matters, and no test charges it. Add an assertion on `self.passes` for a run whose first
  wave exhausts its allowance while a later (adopted) wave is still runnable.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/flow.py:1173-1175` asserts "Only what
  adoption ADDS goes through the tolerant path." That is not what the code does:
  `_adopt_split_children` passes `remaining + children` to `_reschedule`
  (`flow.py:1003`, `flow.py:916`), and `remaining` is the *un-driven tail of the operator's
  own id list*, which therefore goes through `waves.partition_schedulable`. Reproduced:
  `pdca flow 500 810 811` (811 `Depends on 810`; 810 walked away from → AWAITING_SIGNOFF;
  500 splits) prints `flow: issue_811 held this run — unresolved dependency (810); left
  in-flight (resolve it, then re-run).` — the resume-sweep report shape, for an id the
  operator explicitly named. Pre-fix the same disk produced `_runnable`'s
  `skipped — prerequisite(s) not ready (810); not built on a base missing them`. The end
  state (811 PLANNED, rc 1) is unchanged, so this is a claim/report-shape defect rather
  than a data defect — but the docstring is the thing a later maintainer will trust, and
  no test covers a named id in the re-scheduled remainder.

- **NEEDS-HUMAN** — an unfinished adopted child gets two opposite verdicts depending on
  *how* it was left unfinished. `cli.py:669-670` deliberately makes an adopted child at
  AWAITING_SIGNOFF fail the run (rc 1, pinned at
  `template/tests/test_flow_adopt_split.py:598`), and a child the pool ran out on is in
  `bundles` so it also yields rc 1 (verified). But a child adoption could not *schedule* is
  excluded from the results map at `flow.py:1009`, so `pdca flow 500` exits **0** with 602
  left PLANNED — asserted as intended at `test_flow_adopt_split.py:876`. Same run, same
  cause (the split this run itself performed), and the operator's automation sees total
  success. The brief does say "excluded from the results map", so the builder followed it;
  whether rc 0 is the wanted contract for "this run created work it then could not
  schedule" is a fitness call the human should make, not a reviewer rationalisation.

- **NEEDS-HUMAN** — `template/src/pdca_harness/flow.py:916` (`_reschedule`) levels adopted
  children by their *own* `Depends on` / `Conflicts with` and never re-points a dependent
  of the split parent at the children, so adoption newly **co-schedules a dependent with
  the work it depends on**. Concrete: `pdca flow 500 700` with 700 declaring
  `- **Depends on:** 500`, and 500 splitting into 601 + 602(`Depends on` 601), gives waves
  `[[issue_500], [issue_601, issue_700], [issue_602]]` — 700 is built blind of 601, folded
  in the *same* integration step as 601, and published a whole wave before 602, even
  though a split parent closes with **no patch** and the work 700 declared a dependency on
  is precisely what moved into 601/602. Pre-fix the same input gives
  `[[issue_500], [issue_700]]` with the children never in the run, so the shared-wave /
  fold-before hazard is created by this diff. Arguably outside the brief's scope ("changing
  why recursive splits happen" is excluded) — hence a human scope decision rather than an
  iterate.

- **NEEDS-HUMAN** — the patch carries an unrelated test-only change the brief explicitly
  put **out of scope** ("the pre-existing T3 red … verified pre-existing isolation fault …
  do not chase it"): `template/tests/test_verify_base.py:76-84`. It does fix the recorded
  iteration-1 gate (verified: with `PDCA_VERIFY_BASE=deadbeef`, 11 of 19 fail without the
  hunk, 19/19 pass with it), but it fixes the *test*, not the leak its own comment names —
  `gates._merged_env` (`template/src/pdca_harness/gates.py:778-782`) still hands
  `{**os.environ, **exports}` to every gate subprocess, so a nested / self-hosting run's
  stale `PDCA_VERIFY_BASE` still reaches a real gate command with nothing to stop it. Also
  worth knowing at sign-off: because C4 reverts production hunks only and keeps
  `template/tests/*`, this hunk is present on **both** legs — the recorded C4 PASS says
  nothing about it.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/flow.py:1010`
  (`batch_names |= {c.name for c in scheduled}`) can be replaced by a no-op with **all 22
  tests still green**, while the docstring at `flow.py:956-959` claims the adopted children
  join "`_runnable`'s in-batch prereq rule". Unpinned behaviour: a second parent that
  splits in a later wave and names an already-adopted child would re-adopt it (the
  in-call `taken` set does not survive the call), and a child declaring
  `Depends on (merged)` on a sibling would take the #186 merge gate instead of the wave
  fold. Low blast radius, but the claim is currently unverified either way.

## Attempted and could not refute

- **Boundedness.** Removing the `examined` guard (`flow.py:986-988`) makes the suite hang
  and the SIGALRM deadline convert it to an error — the lineage-cycle test is real, not
  decorative. A self-naming record, a child listed twice, and an ancestor back-edge all
  terminate.
- **The guards.** Mutating away the path-escape check, the record dedup, the terminal
  half of `_is_split_parent`, the drive-set dedup, the chain walk, the splice
  (`wave_list[k+1:] = tail` → `+=`), the seed's `k=-1`, the announced wave index
  (`k+1+j` → `k+1`), the per-wave hand-down (`min(allowance, budget-spent)` → `allowance`),
  the pool sizing, the `spent` accumulation, the tolerant reschedule, and the
  `cli._report_single` hunk alone — **every one is caught**, 1 to 9 failures each.
- **Pool non-bindingness for a non-adopting run.** Proved by induction over the loop
  (each wave spends ≤ `allowance`, `budget = allowance × len(wave_list)`) and confirmed by
  the 4-wave `--max-passes 1` test; I could not construct a run that adopts nothing and is
  newly truncated.
- **Traversal.** `"../../etc"`, `"601/602"`, an absolute-looking id, a trailing slash, an
  embedded newline and `"."` all either fail `d.parent != cfg.bundle_root` or degrade to
  the "no brief.md" report; I found no id that reaches a bundle outside `cfg.bundle_root`.
- **Marker spelling.** `SPLIT_DISPOSITION = "split"` matches the only writer
  (`split.py:635` writes `"split\n"`), and `config.py:32` confirms "split" is deliberately
  not a configurable close class, so no other disposition can collide with it.
- **Entry-point parity.** `flow.flow()` has no production caller (`cli._flow` routes every
  shape through `flow_ids`), so the "adoption lives once" claim holds structurally.
