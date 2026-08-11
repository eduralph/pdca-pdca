# Build notes — issue_469 (iteration 2), flow: adopt split children mid-run

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) off the wave base `e955b79`
(`pdca-integrate: issue_468` — child-1's accepted unified drive path, i.e. `stack-base =
pdca-integration/main`). Every `path:line` below is that tree **with the patch applied**,
unless it says "at `e955b79`".

## What changed since iteration 1 (this is a re-run — read this first)

Iteration 1's adoption mechanics are kept as they were (C4 PASS, C1/C2/C3/C5/T1/T2/T5 all
PASS in the advisory review). This iteration addresses the four things Check left open. The
adversary's own words are quoted so the human can match each item to its finding.

| Check finding | Disposition | Where |
|---|---|---|
| **NEEDS-HUMAN** — "adoption breaks the CLI-shape exit-code parity the brief makes success criterion (3)" | **FIXED** (production) | `cli.py:664-670` + `test_flow_adopt_split.py:598` |
| **NEEDS-HUMAN [impl]** — `flow.py:1287` "is a load-bearing production hunk with zero test coverage" | **COVERED** (test) | `test_flow_adopt_split.py:454` |
| **NEEDS-HUMAN [impl]** — `flow.py:984` "the termination bound … is the one mutation the suite does not catch" | **COVERED** (test) | `test_flow_adopt_split.py:907` |
| **T3 Runtime** — "the frozen gate run was not hermetic" (11 `test_verify_base` failures under an inherited `PDCA_VERIFY_BASE`) | **FIXED** (test isolation) | `test_verify_base.py:31-42,76-84` |
| **NEEDS-HUMAN** — the run-wide pass pool is "a fitness call, not a bug" | **left for the human**, argued below | — |
| **T4 Contribution** — artifacts not supplied | **not the builder's to supply**, explained below | — |

The suite went 19 → 22 tests; the C4 red leg went 16 → **19 failures of 22**.

### 1. Exit-code parity for an adopted child (production fix)

The adversary's reproduction is exact, and I re-ran it as a test before changing anything:
`pdca flow 500` returned **0** with adopted child 602 sitting `AWAITING_SIGNOFF`, while
`pdca flow 500 <sibling>` on byte-identical disk returned **1**
(`test_an_adopted_child_left_unfinished_exits_1_at_either_arity` → `AssertionError: 0 != 1`
against iteration 1's patch). That is the brief's success criterion (3) — "both shapes
produce the same child states, announcements and **exit code**" — broken by iteration 1.

Cause, precisely: `cli._report_single` applied its `AWAITING_SIGNOFF`-is-OK leniency to the
**whole** results map (`_results_rc(results, ok=(*_FLOW_OK, AWAITING_SIGNOFF))` at
`cli.py:661` in iteration 1), and #469 is the first change to put bundles the operator never
typed into that map (`flow.py:1009`, `bundles += scheduled`).

Fix (`cli.py:664-670`, 2 lines of code + 7 of docstring): the leniency is scoped to the id
the operator TYPED; everything else in the map keeps the batch rule.

```python
    return (_results_rc({iid: final}, ok=(*_FLOW_OK, state.AWAITING_SIGNOFF))
            or _results_rc({k: v for k, v in results.items() if k != iid}))
```

Why this direction and not the other (make both shapes lenient for adopted children):
`_results_rc`'s documented contract is "0 iff every bundle in it reached a successful
terminal" (`cli.py:630-641`), and the single-id exception exists for one stated reason —
"stopping for the human who just typed the command is the intended end of that run". An
adopted child is by construction *not* what they typed; it is unfinished work that needs a
follow-up `pdca flow 602`, so rc 1 is the honest answer and it is the answer the batch shape
already gives. Widening the leniency instead would have made `pdca flow 500 999` return 0
with un-terminal work outstanding — changing #468's batch rule for a case #469 invented.

Both directions of the hunk are pinned by test, not just the one:

* map-wide leniency (iteration 1's behaviour) ⇒ `test_an_adopted_child_left_unfinished_…`
  fails (1 failure across the two modules);
* no leniency at all (over-correction) ⇒ that test **and**
  `test_flow_entrypoint_parity.py:388` (`test_single_id_awaiting_signoff_presentation_preserved`)
  fail. The new test carries its own third leg asserting the typed id still exits 0, so the
  module is self-sufficient about it.

### 2. The wave-boundary hunk `flow.py:1287` now has coverage

The adversary verified that restoring the pre-patch cached `last = len(wave_list) - 1`
survives all 1652 driver tests while taking `integrate.fold` from
`[['issue_500'], ['issue_500','issue_601']]` to `[]`. Every test in the module ran
`--no-publish`, so the publish/fold branch was dead under the whole new suite.

`test_the_wave_a_split_happened_in_still_folds_for_its_adopted_wave`
(`test_flow_adopt_split.py:454`) is the one test in the module that runs with publishing ON
(stub publisher ⇒ `integrate.fold`'s dry-run, no git remotes — the same offline shape the
peer wave test uses at `tests/test_flow_slice.py:1115-1136`), spying the production fold
pass-through. Re-ran the adversary's mutation with it in place:

```
mutation 1 applied: cached `last`
FAIL: test_the_wave_a_split_happened_in_still_folds_for_its_adopted_wave
Ran 22 tests … FAILED (failures=1)
```

### 3. The recursion bound `flow.py:984` now has coverage — and the first attempt at it was wrong

Scenario: 500 split → 601, 602; 601 split → 701; 601's `split-lineage.json` hand-edited so
`children = ["500", "701"]` — an ancestor back-edge. Without `if parent.name in examined:
continue`, `cli._flow` never returns.

The first version of this test used a SIGALRM watchdog raising `AssertionError`. **It did
not catch the mutation** — the module ran 60 s and reported `OK`. Why: `flow._isolate`
contains `Exception` around every per-bundle step including adoption (`flow.py:60-69`), so
the watchdog's exception was swallowed, logged as "split adoption failed", and the queue
happened to drain on that iteration — a hang laundered into a green test. I only found this
because I ran the mutation instead of assuming the test worked.

The shipped watchdog raises `_RunDidNotReturn(BaseException)`
(`test_flow_adopt_split.py:47-88`), which is exactly the contract `_isolate`'s own docstring
publishes ("only ``Exception`` is contained"). Plus a direct assertion of the bound: a
pass-through spy on the production `_children_of_split` records every parent examined, and
the test asserts each appears once (`test_flow_adopt_split.py:335-356`, `:937-939`). Re-ran
the mutation:

```
mutation 2 re-applied: dropped the examined-once bound
ERROR: test_a_lineage_cycle_is_examined_once_and_the_run_returns
  _RunDidNotReturn: the run did not return within 30s — the lineage walk is unbounded
Ran 22 tests in 30.191s … FAILED (errors=1)
```

The spy is reached with `getattr(flow, "_children_of_split", None)` and degrades to an empty
list when absent, so on the C4 red leg the test fails on the **states** it asserts (the
defect) rather than on a missing attribute — and the module still imports, which is what
keeps the red leg a red rather than a PDCA-UNVERIFIABLE (exit 77).

### 4. T3 hermeticity (the failing gate named in the carry-forward)

Reproduced first, on the patched tree:

```
$ PDCA_VERIFY_BASE=origin/pdca-integration/main PYTHONPATH=src python3 -m unittest discover -s tests
FAILED (failures=11, skipped=2)        # all 11 in tests/test_verify_base.py
```

— byte-for-byte the 11 rows in the frozen `gate-logs/T3-suite.log:1115-1227`, and not one of
them touches this patch. The mechanism: `gates._merged_env` builds a gate subprocess's
environment as `{**os.environ, **exports}` (`gates.py:778-782`), and `test_verify_base`
reads the three base variables back **out of a real gate subprocess** to assert which one
the driver set. So when the OUTER harness exports `PDCA_VERIFY_BASE` to the gate that runs
this suite — which it does for every wave-dependent bundle, this one included — the inner
assertions see a variable nobody in the test set.

Fix (test-only, `test_verify_base.py:31-42` + `:76-84`): the module snapshots `os.environ`
with `mock.patch.dict`, drops the three variables it is about for the duration of each test,
and restores afterwards. Only those three — the gate subprocess still needs `PATH`/`HOME` to
run at all. A module that asserts *what the driver exports* has to own the baseline it
measures against.

Result: `== T3: root suite OK, driver suite OK`, run through the project's own
`engine/scripts/run-suite.sh` **with `PDCA_VERIFY_BASE=origin/pdca-integration/main` in the
environment**, i.e. under the very condition that made iteration 1's gate run non-hermetic.

**What I deliberately did NOT do, and why the human may want to file it.** The same evidence
shows a *production* hole: `gates.py:495-524` documents "these three exports are MUTUALLY
EXCLUSIVE … Exactly one is set for every bundle-scoped gate invocation", and
`_merged_env`'s pass-through makes that false whenever one of them is already in the ambient
environment — a wave-0 bundle's gate can be told a stale integration base while publish
commits elsewhere, which is the divergence `PDCA_BASE` exists to prevent (#54). Reproduce:

```
$ PDCA_VERIFY_BASE=x PDCA_BASE=y PDCA_BRIEF_BASE=z PYTHONPATH=src python3 -m unittest tests.test_publish_slice
FAIL: test_stack_exposes_pdca_base_to_bundle_gate      # a second module, same class of fault
```

I left it out for two reasons, one of scope and one of substance. Scope: the brief's
out-of-scope list names this exact fault ("verified pre-existing isolation fault,
non-gating, expect it, do not chase it"), and a builder overriding an explicit Plan scope
decision on its own judgment is worse than surfacing it. Substance: the fix is **not** the
4-line scrub it looks like — `_run_one` passes `env=None` for a repo-scoped gate
(`gates.py:491`), so `_merged_env(None)` returns `None` and the subprocess inherits
`os.environ` wholesale; restoring the invariant everywhere means deciding what a
repo-scoped gate should see, which is a design call with its own test surface (~25 lines),
not a hunk to smuggle into an adoption patch. **Recommend filing it** — the one-line
symptom for the tracker: "a bundle-scoped gate inherits an ambient PDCA_BASE /
PDCA_VERIFY_BASE / PDCA_BRIEF_BASE, breaking the 'exactly one base' invariant
(`gates.py:778-782`)".

### 5. T4 — why no `commit-msg.txt` / `pr-description.md`

The reviewer asked whether the asserted T4 PASS is sufficient given the artifacts were not
supplied. They are not the builder's to supply, by design of this harness, not by omission:
`contribcheck` returns 0 when `pr-description.md` is absent, with the comment "artifacts not
drafted yet (Check-time gate, pre-publish) — nothing to lint"
(`pdca-pdca/src/pdca_harness/cli.py:1034-1036`), and the artifacts are drafted **by the
publish step on accept** and hard-gated there (`publish.draft_texts` → `_ensure_texts` →
`_t4_passes`, `publish.py:58-104`). `_ensure_texts` only drafts what is **absent**, so a
builder-written pair would silently pre-empt the publisher leaf — the Check-closing step
that belongs to the human's accept path. So: T4 is honestly vacuous at Check time here, it
becomes a real gate at publish, and nothing I can do at Do would make the Check-time row
mean more.

### 6. The pass-pool fitness question — left for the human, as the adversary asked

"Adoption is strictly weaker than the manual restart it replaces, which is a fitness call,
not a bug": `pdca flow 500` gives the whole run (parent + every adopted generation)
`max_passes` passes total, where the operator's current remedy `pdca flow 601 602 …` gets
`max_passes` per wave. I did not re-decide it. It is loud (`flow.py:1201-1209` names
everything still in flight with a resume hint), documented in the patch
(`docs/07-crosscutting.md`, "One consequence worth knowing before you type it") and pinned
by `test_the_pass_budget_is_one_cap_for_the_whole_run`. The alternative — a fresh
`max_passes` per adopted wave — is what makes a split multiply the operator's allowance
without bound, which is the property the brief asks for ("counted against ONE run-wide
`max_passes` budget").

## The rest of the patch (unchanged from iteration 1 — summary for continuity)

| Piece | Where (post-patch) |
|---|---|
| shared held-report (was inline in `flow_batch`) | `flow.py:768`, reused at `flow.py:928`, `flow.py:1379` |
| `SPLIT_DISPOSITION` marker value | `flow.py:801` |
| `_is_split_parent` — TERMINAL **and** marker == `split`, total catch | `flow.py:804` |
| `_adoptable` — `split.read_lineage`, filter (dup / path-escape / known / no brief / terminal), walk-on list | `flow.py:831` |
| `_children_of_split` — the one detect+validate step | `flow.py:908` |
| `_reschedule` — `partition_schedulable` tolerance + `compute_waves` | `flow.py:916` |
| `_adopt_split_children` — queue, splice into `wave_list[k+1:]`, announce REAL wave | `flow.py:939` |
| `_drive_wave` returns the passes it consumed | `flow.py:1021`, `:1073`, `:1103`, `:1112` |
| run-wide pool, sized off the ORIGINAL schedule | `flow.py:1181` |
| seed pre-pass (`k=-1`) | `flow.py:1188` |
| per-wave allowance = `min(allowance, budget - spent)` | `flow.py:1234` |
| mid-wave splice after the wave that split | `flow.py:1240` |
| live `len(wave_list) - 1` (the list grows) | `flow.py:1287` |
| `flow_ids`: terminal-on-split id becomes an adoption **seed** | `flow.py:1470-1487` |
| **rc scoped to the ids named (NEW)** | `cli.py:644-670` |
| **hermetic base-var baseline (NEW, test-only)** | `test_verify_base.py:31-42`, `:76-84` |
| docs / prompts that stated the opposite | `docs/07-crosscutting.md`, `template/agents/planner.md.jinja`, `leaves.py` `_plan_prompt`, `config.py` `max_passes` comment |

Reused rather than re-derived, per the brief's peer-callsite list: `_lineage_children`
(`flow.py:678`), `_point_at_integration` (`flow.py:637`, adopted waves go through the
ordinary call at `flow.py:1230`), `_warn_abandoned`'s not-terminal predicate
(`flow.py:738`), the held-report shape, and `tests/test_flow_slice.py:32-55` for the offline
fixture (plus `:1122-1128` for the fold spy).

Three v5 pieces stay deleted, for the reasons iteration 1 recorded and Check did not
contest: `_RunSoFar` + `wave_offset` threading (41 lines in v5 — unnecessary with one loop),
`flow.flow`'s adoption tail + its own `spent` accounting (~35 lines — `cli._flow` never
calls `flow.flow` since #468, `cli.py:613-622`), and the `_isolate` `PreflightError`
carve-out (8 lines — proven unnecessary by
`test_a_refused_adopted_wave_exits_1_at_either_arity`).

## Evidence — every gate re-run through the project's own runners

* **C4** (`./engine/scripts/run-verify.sh`, with `PDCA_BUNDLE` / `PDCA_WORKTREE`):
  `C4 PASS: red without the fix, green with it`. Green leg **22/22 OK** (+ `test_verify_base`
  19/19); red leg (production hunks reverted, tests kept) **19 failures of 22**, including
  all three new tests.
* **T3** (`./engine/scripts/run-suite.sh`, run WITH `PDCA_VERIFY_BASE=origin/pdca-integration/main`):
  `== T3: root suite OK, driver suite OK` — 1655 driver tests (1633 pre-existing + 22),
  0 failures. Iteration 1's recorded red is gone, and gone under the condition that caused it.
* **T2** (`./engine/scripts/run-docs-check.sh`): `lint_docs: OK`, `render_site: link audit OK`
  (22 pages).
* **Applies to the pristine base**: extracted `e955b79` with `git archive` into a scratch
  tree, `git apply --check` clean, applied, and `tests.test_flow_adopt_split` runs 22/22 OK
  there — so the patch is not carrying any dependence on the worktree's state.
* `git diff --check` clean. No formatter / linter / commit hook is configured in the target
  (`.pre-commit-config.yaml` absent, `core.hooksPath` unset, CONTRIBUTING.md names only the
  offline suite; CI is docs-check / render-check / require-linked-issue, all covered by T2
  and T3's root suite). No line I added exceeds the file's existing width convention
  (the two >95-char lines in the touched test files are both pre-existing).

### The three tests that are green pre-fix — deliberately

`test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`,
`test_a_named_id_list_keeps_its_strict_scheduling_contract`,
`test_an_unreadable_close_marker_never_kills_the_run`. Each asserts that something did **not**
change, so "green before and after" is their contract. The other 19 are red pre-fix.

## Forced self-refutation

**(a) Genuine red?** Yes — reverted for real, not reasoned about. `run-verify.sh` reverts the
production hunks (`git apply -R --exclude=tests/* --exclude=template/tests/*`) and re-runs:
`FAILED (failures=19)` of 22. The three tests added this round are each in that set:
`test_an_adopted_child_left_unfinished_exits_1_at_either_arity`,
`test_the_wave_a_split_happened_in_still_folds_for_its_adopted_wave`,
`test_a_lineage_cycle_is_examined_once_and_the_run_returns`. Beyond the C4 revert I ran a
4-mutation battery on the specific hunks this round is about — cached `last`, dropped
`examined` bound, map-wide leniency, no leniency — and **all four are caught**, each by the
test written for it (transcripts above). The first shipped version of the cycle test did
*not* catch its mutation; that is why it was rebuilt around a BaseException watchdog.

**(b) Production path?** Yes. Every test drives `cli._flow(cfg, argv-namespace)` — the real
CLI entry — which calls the real `flow.flow_ids` → `_drive_and_act` → `_drive_wave` →
`driver.advance`, and the exit code asserted is the one the real `cli._report_single`
computed. Nothing is re-implemented: splits are made by the **production** `split.accept`
(`split.py:525`), so the close marker, `split-lineage.json` and the child bundles are
byte-for-byte what `pdca split --accept` writes; the stranded-split fixture is built with the
production `flow._drive_wave`; the fold assertion wraps the **production** `integrate.fold`
as a pass-through spy and hands back its real return value; the examined-parents spy wraps
the production `_children_of_split` the same way. `test_verify_base` reads its values out of
a real gate subprocess run by the production `gates.run_gates`. The only substitutions are
the six leaf stubs the offline suite already uses and a scripted sign-off decision written
into the real `leaves.SIGNOFF_DECISION` file the real `_apply_decision` consumes.

**(c) Fixture includes the fault?** Yes, and this round's three additions each carry a real
fault rather than a curated one: the un-finished child is genuinely left `AWAITING_SIGNOFF`
by a sign-off session that never answers it (not a state written by hand), and the run's
other child really completes, so the map contains both; the fold test really runs the
publish/fold branch (`no_publish=False`) rather than asserting about it; the cyclic record is
a real `split-lineage.json` on disk whose `children` names an ancestor, next to a legitimate
sibling that must still be adopted, and the run under test really walks it. The earlier
hostile inputs are unchanged and still present: `"../../etc"`, the duplicated `["601", "601",
"602"]`, `Depends on: GHOST`, non-UTF-8 marker bytes, a genuinely failing `lane_preflight`.

## Not done / for the human

* **The `gates._merged_env` production hole** (§4 above) — out of the brief's scope, real,
  reproduced, and worth its own issue. Not fixed here.
* **The pass-pool fitness call** (§6 above) — the adversary's own framing is "for the human
  to ratify at sign-off, not for the builder to re-decide". Unchanged.
* **`flow.flow`** (the single-bundle *library* driver, `flow.py:367`) does not adopt — by
  design, argued in iteration 1's notes and recorded in its docstring (`flow.py:389-394`);
  `cli._flow` never calls it since #468 (`cli.py:613-622`), so a tail there would be an
  unreachable second implementation. Check did not contest this reading.
* **Publish/fold of adopted waves beyond the boundary call**: the new fold test pins that the
  boundary RUNS and with which cumulative set, under the stub publisher's dry-run. A
  non-stub publisher (real git remotes) is out of reach of the offline suite; the
  `_point_at_integration` assertion remains the structural stand-in for "adopted children are
  pointed at this run's integration branch".
* No external dependency was missing: python3 + git, fully offline, no tracker / network /
  `gh` / container.
