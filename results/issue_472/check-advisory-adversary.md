# Adversarial review — issue_472 (flow-adopt-core)

Re-ran the asserted red→green at `$PDCA_TARGET` rather than trusting it. Green leg:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split` → **27/27 OK**.
Red leg (production hunks reverted to `3e3b829`, test kept — the C4 shape): **26 of 27 FAIL**;
the single survivor is `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`
(`template/tests/test_flow_adopt_split.py:503`), which is a no-regression guard and is
*supposed* to be green pre-fix. Full driver suite on the target: 1660 tests, OK (skipped=2);
stable across five `PYTHONHASHSEED` values. The tests drive the real `cli._flow` and build
fixtures with the production `split.accept` — the spies at `template/tests/test_flow_adopt_split.py:258`
and `:284` are pass-throughs that return the production value, not re-implementations. I could
not find a tautology or a mocked-away defect in the evidence.

## Findings

- **NEEDS-HUMAN [impl] —** `template/src/pdca_harness/flow.py:1177` (with `:1041`): the feature's
  central promise — "a split must never be able to abort the flow that caused it"
  (`flow.py:1030`) — has **no test at all**, and I proved it by mutation. Three mutants survive
  the entire new 27-test suite: (a) delete the `if tail is None:` guard at `flow.py:1177`;
  (b) narrow `_reschedule`'s deliberately-broad `except Exception` at `flow.py:1041` to
  `except ZeroDivisionError`; (c) make `_real` (`flow.py:831`) re-raise instead of returning
  `None`. Each ran `Ran 27 tests … OK`. Mutant (a) is not cosmetic: with `waves.partition_schedulable`
  made to raise mid-splice, `pdca flow 500` dies with an uncaught
  `TypeError: must assign iterable to extended slice` out of `_drive_and_act` — the run aborts,
  wave 0's completed work is never reported, and rc is a traceback. The unmutated code is
  correct here (I verified it: rc 0, `flow: could not re-wave the run after a split (RuntimeError: …)`
  + `flow: the children of issue_500 could not be scheduled; they are left in-flight …`, no
  traceback, children left PLANNED) — the defect is that nothing pins it, so the one contract
  the brief calls out as "never aborts" is the one contract a rebuild could silently break.
  Cheap fix: one test that forces `_reschedule` to return `None` (patch `flow.waves.partition_schedulable`
  to raise) and asserts rc, both stderr lines, and `assertNotIn("Traceback", err)`.

- **NEEDS-HUMAN [human] —** `template/src/pdca_harness/cli.py:657` and `:661`: the **single-id
  exit code silently flipped 0 → 1** while its stdout is byte-identical. Concrete case — exactly
  the scenario of `template/tests/test_flow_adopt_split.py:407`: `pdca flow 500 --max-passes 3`
  where 500 splits into 601/602 and the pool stops before 602's wave. I ran it on both legs:
  post-fix stdout is `COMPLETE\t<root>/results/issue_500` with **rc 1**; pre-fix (HEAD) the same
  command prints the same line with **rc 0**. `_report_single` prints only `results[iid]`
  (`cli.py:657`) but derives rc from the *whole* map (`cli.py:661`), which now carries adopted
  children — so an operator (or `pdca flow 500 && …` automation) reads "COMPLETE" and gets a
  failure code with nothing on stdout naming 602. No test in the bundle asserts rc for a
  single-id run with an unfinished adopted child (`:407` and `:422` both discard `self._cli`'s
  return). The brief parks "single-id stdout reporting of adopted dispositions" with the sibling
  child but says nothing about the exit code; the human has to decide whether the rc may move
  ahead of the reporting, or must stay scoped to named ids until the sibling lands. Note the
  asymmetry this creates with the *held*-child contract, which the code deliberately keeps at
  rc 0 (`test_a_children_entry_that_is_not_an_id_is_reported_not_dropped_silently:815` exits 0
  with two briefed children left PLANNED): "this run created work it could not finish" is rc 1
  in one shape and rc 0 in the other.

## Attacks that failed (stated so the negative result counts)

- **Mutation-tested the guards the brief names.** All caught, most by ≥2 tests:
  `known=batch_names | taken` → `known=batch_names` (the #469-v3 adversary's mutation, 2 failures);
  resolution-aware containment → lexical `d.parent == cfg.bundle_root` (1);
  drop the `len(entries) > len(ids)` malformed-entry report (1); drop the `seen_real`
  resolved-path dedup (1); drop the retraction block (1); drop the `named` exclusion from the
  retraction predicate (1); drop the terminal half of `_is_split_parent` (1);
  `min(allowance, budget - spent)` → `allowance` (2); `wave_of` → hardcoded `k + 1` (4);
  `scheduled = children` i.e. put held children in the map (4); `bundles += []` (4);
  delete the `spent >= budget` break (3); `_PLAIN_ID` → `.+` (1); drop the alias `owner` lookup (1).
- **The pool-sizing claim** at `flow.py:1385` / `config.py:312-324` ("a run that adopts nothing
  can never reach the pool") — I could not construct a counterexample: every wave spends
  ≤ `min(allowance, budget - spent)` ≤ `allowance`, `_drive_wave` returns `used` on *all three*
  exits (`flow.py:1274`, `:1304`, `:1313`), `wave_list` only grows via the splice, and
  `cli.py:572` / `config.py:675` floor `max_passes` at 1 so `budget - spent ≥ 1` at the call site.
- **The "same end state" claim** at `flow.py:1370-1379` (a named id held by the tolerant re-levelling
  vs. skipped by `_runnable`). I tried to break it with a `Depends on (merged)` prereq that
  `merged.is_merged` accepts but that is not COMPLETE on disk — unreachable, because
  `waves.check_dep_graph` (`waves.py:77`) already raises on that brief before any wave runs, on
  both legs. Every reachable divergence I could build ends PLANNED-in-the-map-and-rc-1 either way.
- **Doc claim "the CSV batch alike"** (`docs/07-crosscutting.md`, `planner.md.jinja`): untested in
  the bundle, so I probed it directly — `flow.flow_batch` returns `{'500': COMPLETE, '601': COMPLETE,
  '602': COMPLETE}` with both adoption announcements. The claim is structurally true via
  `_drive_and_act`; not a refutation.
- **Every `path:line` citation added by the diff** (24 of them, across `flow.py`, `cli.py`,
  `config.py`, `split.py`) resolves to the line it claims on the target — including the three the
  previous iterations got wrong (`config.py:686` for the clamp, `flow.py:1429` for the `min`,
  `flow.py:1310` for the per-wave allowance message). The docstring test citations
  (`test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once`,
  `test_a_shared_child_the_reschedule_holds_is_not_reported_as_driven`,
  `test_a_symlinked_alias_of_a_bundle_this_run_drives_is_driven_once`) all name tests that exist.
- **In-root symlink aliasing an *un-driven* bundle** — noted, not filed. `results/issue_601` →
  `results/issue_999` (briefed, in-flight, not in the drive set) is adopted and driven, and the
  map reports `'601': COMPLETE` while the directory that actually completed is `issue_999`
  (`flow.py:861-864` accepts it by design; `flow.py:1000`'s `driven` map only covers the drive
  set). I am **not** scoring this as a refutation: `pdca flow 601` does exactly the same thing on
  HEAD, so it is pre-existing parity, and the iteration-4 sign-off explicitly narrowed this to the
  "one directory, two lanes" case that the patch does close.
