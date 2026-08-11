# Adversarial review — issue_449 (flow adopts split children mid-run)

Re-ran the asserted red→green at `$PDCA_TARGET` before attacking. It holds: with only the
production hunks reverted (`flow.py`, `config.py`, `leaves.py` restored from `HEAD`,
`template/tests/test_flow_adopt_split.py` kept) the suite is **red on 9 assertions**
(`'PLANNED' != 'COMPLETE'`, `None != 'COMPLETE'`), and green 8/8 with the patch. The test
drives the real `flow.flow_ids` / `flow.flow` and builds the fixture with the production
`split.accept`, so it is not a parallel re-implementation. The findings below are what
survived that.

## Refutations

- **NEEDS-HUMAN [impl] —** `template/src/pdca_harness/flow.py:1304` calls `_is_split_parent(d)`
  **outside any `_isolate`**, and `_is_split_parent` (`flow.py:744-748`) catches only
  `OSError`. A `close-disposition` file whose bytes are not UTF-8 raises `UnicodeDecodeError`
  (a `ValueError`), which escapes `flow_ids` and kills the **whole** explicit-id run.
  Reproduced: with `results/issue_500/close-disposition` = `b"split\xff\n"`,
  `flow.flow_ids(cfg, ["500", "601"])` dies with
  `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 5` at `flow.py:745`
  — and `601`, a perfectly drivable named id, is never driven. `flow.flow` survives the
  same disk only because it wraps adoption in `_isolate` (`flow.py:433`). This is exactly
  the trap the sibling reader this patch builds on documents at
  `template/src/pdca_harness/split.py:382-390` ("bytes that are not UTF-8 raise
  `UnicodeDecodeError` out of the *read*, where only `OSError` was expected") — the patch
  cites `split.read_lineage` as its model and then repeats the failure it was written to
  avoid. Pre-fix `flow_ids` read no file on that branch, so the crash is new.

- **NEEDS-HUMAN [impl] —** The patch's own headline claim — "`pdca flow 500` and
  `pdca flow 500 501` behave the same on the same disk state" (`flow.py:1015-1016`,
  `docs/07-crosscutting.md` new §"Naming a parent that is already terminal…", and
  iteration-1 sign-off RULING (b), which asked for exactly this) — is **false whenever the
  budget binds**. `flow.py:388-390` charges `spent += 1` *before* the loop body, and on a
  recovery run (`pdca flow 500`, 500 already terminal on a split) the body immediately
  `break`s at `flow.py:393` having done no work; `flow.py:435` then hands adoption only
  `max_iters - spent`. `flow_ids` charges the seed parent nothing (`flow.py:1303-1315`).
  Concrete failing case, identical disk state (500 split into 601 → 602, chained,
  `max_passes=2`): `flow.flow_ids` → `('COMPLETE', 'COMPLETE')`; `flow.flow` →
  `('COMPLETE', 'PLANNED')` with "the run's pass budget is spent (1 pass(es) over 1
  wave(s))". The CLI routes one id to `flow.flow` and several to `flow_ids`
  (`cli.py:639` / `cli.py:652`), so this is user-visible exactly as the claim words it.
  Compounding it: the regression test for this axis,
  `template/tests/test_flow_adopt_split.py:252-275`, runs both entry points on the
  **default** budget (20) against children needing 2 passes — the budget can never bind, so
  it passes for the wrong reason on precisely the property RULING (b) asked to fix. A
  binding-budget case belongs in that test.

- **NEEDS-HUMAN —** Making `[driver].max_passes` a run-wide cap (`flow.py:1027-1028`,
  `:1059-1067`, `:1089`; `config.py:293-299`) changes behaviour for **every** multi-wave
  batch, including ones with no split anywhere — not only adopting runs, which is all
  RULING (1) needed. Concrete: six bundles in a linear `Depends on` chain (six waves, one
  pass each) with `max_passes=5` — pre-fix all six reach COMPLETE; post-fix the run stops
  with "the run's pass budget is spent (5 pass(es) over 5 wave(s))" and `705` is abandoned
  PLANNED. At the shipped default of 20 this truncates any CSV sweep or id list whose waves
  × passes exceed 20 (a deep chain, or ~10 waves at 2 passes each) — runs that completed
  before. `brief.md:225` still asserts "no config key is added and none changes meaning";
  that claim is now false and was not corrected, and no default was raised. Human call:
  raise the default, or scope the run-wide cap to runs that actually adopted. (Related, if
  the cap stays: `flow.py:985-986` now reports the *remaining* allowance — "pass budget
  exhausted after 1 pass(es); raise `[driver].max_passes`" while `max_passes` is 20 —
  which reads as a contradiction to the operator it is addressed to.)

- **NEEDS-HUMAN —** `flow.py:1043-1047` swaps the **strict** levelling for the tolerant one
  whenever a seed adopts, so an explicit id list gets two different failure contracts
  depending on unrelated disk state. `waves.partition_schedulable`'s own docstring
  (`waves.py:243-246`) says raising is "right for an explicit `flow <ids>` / `pdca waves`
  request". Demonstrated: with `800`/`801` in a mutual `Depends on` cycle,
  `pdca flow 800 801` raises `ValueError: dependency cycle: issue_800 → issue_801 →
  issue_800`; adding one *unrelated* stranded split parent — `pdca flow 500 800 801` —
  returns normally, holds both (loudly, to be fair) and drives 500's children. Whether an
  explicit request should silently degrade to resume-sweep tolerance because some other
  named id happens to carry a readable lineage record is a contract decision, not a detail;
  the comment at `flow.py:1035-1042` rationalises it without acknowledging that the same
  id list now behaves two ways.

- **NEEDS-HUMAN [impl] —** `flow.py:763` documents the third `_adoptable` filter as "one
  already in this run's drive set (`known`) is named and dropped", but `flow.py:785-786`
  drops it with a bare `continue` and no message — so `pdca flow 500 601` (parent + one of
  its own children) silently says nothing about 601 while naming every other skip. Minor,
  but this repo treats a docstring claim as load-bearing.

## Attempted and could not refute

- **The evidence.** Red→green reproduces on the production path (above); the test exercises
  the real entry points, never a helper, and the split is produced by production
  `split.accept`, so the fixture is not a mirror of the fix.
- **Transitive adoption.** Built a two-level split (500 → 601,602; 601 → 701,702) driven
  through `flow_ids`: waves `[500] [601,602] [701,702]`, all five COMPLETE, both adoptions
  announced with their real wave index. The brief's "transitively, bounded" claim holds.
- **The splice vs. existing later waves.** `flow 500 501 502` with `502 → 501 → 500` and a
  mid-run split of 500 yields `[500] [501,601,602] [502]` — nothing dropped, nothing driven
  twice, `501`'s ordering preserved. I could not construct an input where the reschedule
  loses a listed bundle without also reporting it via `_report_held`.
- **Scope.** Could not get an explicit-id flow to widen into a `results/` sweep; the
  `known` / `examined` sets do bound re-adoption.
- **T3's red is not this patch.** The full offline driver suite runs **1630 tests, OK** at
  `$PDCA_TARGET` with the patch applied. The gate red reproduces only with the env var set:
  `PDCA_VERIFY_BASE=HEAD python3 -m unittest tests.test_verify_base` → 11 failures. That
  matches the carry-forward's "pre-existing harness test-isolation fault" and is not
  attributable to this diff.
