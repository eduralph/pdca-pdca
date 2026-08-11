# Build notes — issue 449 (Iteration 4) — flow adopts split children mid-run

**Target branch:** `eduralph/pdca-harness` @ `pdca-integration/main` (stack base), worktree
`$PDCA_WORKTREE = /home/eddie/pdca/pdca-harness.pdca-wt-l0`, base commit **`aaa797a`**
(`pdca-integrate: issue_456` — the split-lineage record this slice reads is already in the
base). All `path:line` citations below are **post-patch line numbers in that worktree**
unless marked *(base)*.

---

## 1. What this iteration is

The Iteration-3 sign-off kept the mechanism ("the adoption mechanism is sound — C4 red→green
reproduced and mutation-tested by the adversary; keep it") and asked for four
implementation fixes plus one documentation call. So this iteration **starts from the
iteration-v3 patch** and changes only what the carry-forward named. Nothing was
re-architected; the detect → validate → splice → report path, the transitive bounded walk
and the run-wide pass pool are byte-identical to v3 except where a finding required
otherwise.

The whole production delta v3 → v4 is **+74 / −21 lines** in `flow.py` and **+22 / −12** in
`docs/07-crosscutting.md` (most of it rationale comments and re-wrapped prose); the test file
grows **+124 / −27**. No new module, no new call path — the four fixes touch six places.

## 2. The four findings, and how each is fixed

### (1) Budget-exhaustion message on the single-id path named the tail's local totals

*Finding:* `flow.flow` printed `"0 pass(es) over 0 wave(s)"` — the adoption tail's own
budget/wave counters — where `flow_ids` printed the run's. A budget of zero is not a number
an operator can act on ("raise `[driver].max_passes`" while it reads 0 is nonsense).

*Fix:* the tail is handed the run's accounting instead of only its remainder. New frozen
dataclass `_RunSoFar(passes, waves, left)` (`flow.py:753-770`) replaces the bare
`run_budget: int` parameter (`flow.py:1098`); `flow.flow` constructs it at
`flow.py:451-453` from what its own loop spent. `_drive_and_act` derives two report-only
values next to the pool it already computed — `pool = budget + carried.passes`,
`wave0 = carried.waves` (`flow.py:1160-1166`) — and the exhaustion warning uses them
(`flow.py:1192-1194`). The run now says `the run's pass budget is spent (2 pass(es) over 1
wave(s))`, which is the truth at both entry points.

Why a dataclass rather than three loose ints: the three numbers are **one** accounting
(`passes + left` is exactly what the operator allowed, `waves` is where this call's wave 0
falls in the run), and passing them separately invites a caller to update one and not the
others — the precise failure mode this finding is. It costs 18 lines including the
docstring and one stdlib import (`import dataclasses`, `flow.py:23`).

### (2) Adoption announcements numbered differently at the two entry points

*Finding:* on identical disk, `flow.flow` logged `into wave 0` / `wave 1` where `flow_ids`
logged `wave 1` / `wave 2`, because `flow.flow` drives its bundle in its own loop and the
tail's `wave_list` restarts at 0 — while the docs promise the two entry points do the same
thing (`docs/07-crosscutting.md:256-262`).

*Fix:* the **announced** index (never the schedule's own index, which still addresses
`wave_list`) is offset by the waves the run already drove: `_adopt_split_children` takes
`wave_offset: int = 0` (`flow.py:909`) and applies it only at the print
(`flow.py:990`); `_drive_and_act` passes `wave0` at both its call sites
(`flow.py:1175`, `flow.py:1228`). The single-id loop counts as the run's wave 0 iff it
actually drove (`waves=1 if spent else 0`, `flow.py:453`) — so a *recovery* run, whose loop
observes an already-terminal parent and spends nothing, reports `wave 0` for the first
adopted wave at **both** entry points, exactly as `flow_ids` does with an empty drive set.

Chose the offset over "document the index as tail-local": the log line is what an operator
reads to decide what to re-run, and the same sentence meaning two things depending on how
many ids they typed is the defect, not the wording.

### (3) A duplicate child id in a hand-edited lineage record was adopted twice

*Fix:* `_adoptable` dedupes on the **resolved bundle name** (`flow.py:835-845`), which is
what every downstream set (`known`, `batch_names`, `wave_of`) is keyed by — so two spellings
that resolve to one bundle also collapse. Silent by design: the docstring's "every skip is
reported" promise is about children *not adopted*; a duplicate **is** adopted, once.

Observable damage before the fix (measured, see §4): the announcement read `adopted children
issue_601, issue_601 into wave 0` and the child took two slots in the drive set the closing
`_sweep_quietly` walks. The wave schedule itself was already immune (`compute_waves` keys by
name, `waves.py:150` *(base)*), which is exactly why only a test that reads the report
catches this.

### (4) Entry-B coverage gap on the single-id path

*Finding:* the fixture stubbed only `leaves.run_signoff_batch`, so the single-id path — which
calls the per-bundle `leaves.run_signoff` (`flow.py:261`, unchanged by this patch) — could
never record an `iterate-plan`, and the previous single-id test had to fall back to
`replan_first=False` (a split at the *first* Plan beat). Findings (1) and (2) live on the
path that was not covered.

*Fix:* the fixture stubs **both** sign-off leaves from one scripted decision table
(`decide()`, `test_flow_adopt_split.py:161-176`; `signoff_batch` / `signoff_one` at
`:178-185`, installed at `:186-187`; saved and restored at `:98-99`, `:102-103` and
`:112-113`), so the two entry points are driven by the same human answers. `test_single_id_flow_drives_the_children_of_its_own_split` (`:265`) now walks
Entry B end-to-end through `flow.flow` and asserts the archive an `iterate-plan` leaves
(`iteration-v1/`) plus the driver's own `iterate-to-Plan` line — proof the re-plan really
happened, and (since the parent is in no driven wave) that it came through the single-bundle
leaf.

### (5) The fitness call: a recovery run's pool is one wave's worth

Documented, not changed — it is the ceiling `pdca flow <parent>` has always had, and
changing it would alter budget semantics no finding asked to alter. Recorded where the
operator looks: `docs/07-crosscutting.md:331-336` ("Raise `--max-passes`, or name the
children instead … their own schedule then sizes the pool") and in the `_drive_and_act`
docstring (`flow.py:1124-1128`).

## 3. New / changed tests

| Test | Binds |
|---|---|
| `test_single_id_flow_drives_the_children_of_its_own_split` (`:265`) | findings 2 + 4 — Entry B through `flow.flow`, children in the run's waves 1 and 2 |
| `test_the_two_entry_points_announce_the_same_waves` (`:295`) | finding 2 — the same disk driven by both entry points must produce **identical** adoption lines |
| `test_the_single_id_path_reports_the_runs_own_budget_totals` (`:327`) | finding 1 — the exhaustion message is the run's arithmetic, and the un-driven children are still named with resume hints |
| `test_a_child_listed_twice_in_the_record_is_adopted_once` (`:572`) | finding 3 — one bundle, one adoption, one announcement |

The other 11 tests are unchanged from v3 and still pass.

## 4. Forced refutation — the three questions

**(a) Genuine red? Yes — twice, at two granularities.**

*Whole-patch (the C4 gate, `./engine/scripts/run-verify.sh` with `PDCA_BUNDLE` /
`PDCA_WORKTREE` set — the project's configured gating runner, which reverts only the
production hunks and keeps the test):*

```
== C4 green leg: … Ran 15 tests … OK
== C4 red leg: …  Ran 15 tests … FAILED (failures=18)
C4 PASS: red without the fix, green with it        (exit 0)
```

*Iteration-targeted mutation (the important one — a whole-patch red would also be produced
by the v3 code):* I restored **iteration-v3's `flow.py`** under **this iteration's test
file** and re-ran the module. Exactly the four tests that bind this iteration's findings go
red, and the other eleven stay green:

```
FAIL: test_a_child_listed_twice_in_the_record_is_adopted_once
        AssertionError: 0 != 1   (v3 announced "… issue_601, issue_601 into wave 0")
FAIL: test_single_id_flow_drives_the_children_of_its_own_split
        AssertionError: "issue_500 split → adopted children issue_601 into wave 1" not found
FAIL: test_the_single_id_path_reports_the_runs_own_budget_totals
        AssertionError: "the run's pass budget is spent (2 pass(es) over 1 wave(s))" not found
FAIL: test_the_two_entry_points_announce_the_same_waves
        AssertionError: said["flow"] != said["flow_ids"]
Ran 15 tests … FAILED (failures=4)
```

**(b) Production path? Yes.** Every test calls the real entry points — `flow.flow_ids` /
`flow.flow` — with stub *leaves* (the shipped `mode="stub"` leaf implementations, the same
fixture shape as `template/tests/test_flow_slice.py:32-55` *(base)*), never a helper and
never a re-implementation. The split itself is produced by the production `split.accept`
(`test_flow_adopt_split.py:122-131`), so the close marker, `split-lineage.json` and the
child bundles are byte-for-byte what `pdca split --accept` leaves. The only test doubles are
(i) leaf stubs standing in for the interactive human sessions and (ii) two pass-through
spies (`_spy_wave`, `_counting_build_all`) that record and then call the production function.

**(c) Fixture includes the fault? Yes.** The fault is *the split*, and the fixture creates a
real one during the run being tested — including the motivating Entry-B shape (sign-off
records `iterate-plan` → re-plan → split), which iteration 3 could not reach on the single-id
path and this one does. Nothing is curated out: the stranded-recovery tests assert on disk,
before the run, that the parent is terminal on `split` and both children are `PLANNED`
(`test_flow_adopt_split.py:227-232`); the duplicate test hand-edits the record to the exact
shape an operator can produce; the budget test drives a budget that genuinely binds
(children left `PLANNED` and named).

## 5. Gates run locally (project runners, no hand-rolled invocation)

| Runner | Result |
|---|---|
| `./engine/scripts/run-verify.sh` (C4, gating) | `C4 PASS: red without the fix, green with it` |
| `./engine/scripts/run-suite.sh` (T3) | `== T3: root suite OK, driver suite OK` — root 7 tests OK, driver suite **1637 tests OK** (skipped=2) |
| `./engine/scripts/run-docs-check.sh` (T2) | `lint_docs: OK`, `render_site: link audit OK` |

Note on the T3 red that failed the last three iterations: it was 11 failures in
`template/tests/test_verify_base.py` caused by `PDCA_VERIFY_BASE` leaking from the driver
into the suite's subprocesses. Run through the same script without that variable in the
environment, the driver suite is fully green here — which confirms the carry-forward's
diagnosis (a harness test-isolation fault, not this patch) *and* shows this patch adds no
new failure: 1637 tests, 0 failures. If the driver's own gate run reproduces the same 11
`test_verify_base` failures, that is the pre-existing fault, out of scope for this bundle.

## 6. Commit-readiness

The target repo (`eduralph/pdca-harness`) configures no formatter/linter hooks — no
`.pre-commit-config.yaml`, no ruff/flake8/black configuration; its CI is `docs-check.yml`,
`docs.yml`, `render-check.yml`, `require-linked-issue.yml`. The first three are exactly what
the T2/T3 gates above run (both green); the fourth is satisfied by the `Fixes #449` trailer
the publish step writes. `CONTRIBUTING.md:26` asks that the offline suite stay green — it is.
Added lines follow the files' existing widths (≤ ~95 chars in `flow.py`, ~80 in the docs).

## 7. What I deliberately did NOT do

* **Did not re-architect the single-id path to run through `_drive_and_act` wholesale.** It
  would delete the numbering/budget divergence by construction — one run, one accounting —
  but the cost is the whole of `flow.flow`: the 32-line iteration loop (`flow.py:390-421`),
  its exhaustion warning (`:420-421`), its publish tail (`:423-432`) and its sweep/Act tail
  (`:455-458`) are all written for one bundle, and `_drive_and_act`'s per-wave publish +
  fold is not the same sequence. That is ~90 rewritten lines on the hottest single-issue
  path (`pdca flow <id>`, every `pdca flow --from-csv` fallback) and a behaviour change for
  every run that never splits — against 61 lines here that leave both paths' sequences
  untouched. A carry-forward that says "fix the adversary's implementation findings, do not
  re-architect" does not license it; if the divergence recurs a third time, that is the
  cheaper answer and should be its own bundle.
* **Did not change the recovery run's pool sizing** (finding 5) — flagged as a fitness call,
  not a required change; documented instead (§2.5).
* **Did not touch `test_verify_base.py` / the `PDCA_VERIFY_BASE` leak** — explicitly out of
  scope per the carry-forward.
* **Did not report a deduplicated child id on stderr.** A duplicate is not a skip; naming it
  would add a line to every run that reads a hand-edited record while telling the operator
  nothing they can act on.

## 8. STOP discipline

No branch pushed, no PR opened, nothing marked ready or merged. `patch.diff`, the test at the
brief's path (`template/tests/test_flow_adopt_split.py`, also copied into the bundle) and
these notes are the whole deliverable.
