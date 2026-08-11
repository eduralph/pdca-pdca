# Build notes — issue_449 (flow adopts split children mid-run), iteration 2

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, HEAD `aaa797a` = `pdca-integrate: issue_456`,
i.e. the stacked base carrying 456's `split-lineage.json` and 453's sign-off fix). All
`path:line` citations below are **post-patch** in that worktree unless marked "on HEAD".

---

## 1. What the previous attempt got right, and what I changed

The Iteration-1 sign-off kept the mechanism (detect → validate → splice → report, transitive
+ bounded) and rejected three implementation defects. Each is now fixed **and bound by a
test that fails if the defect is reintroduced** (mutation evidence in §4 — that is the T5 gap
the ruling called out: it is not enough that the new tests are red on a full revert, they
have to be red on the *specific* defect).

### (1) `max_passes` is now a RUN-WIDE cap

Ruling: *"`max_passes` must be a RUN-WIDE cap, but `_drive_and_act` hands the full budget to
every wave — `max_passes=2` completed the parent plus two child waves. Enforce the cap across
all waves including adopted ones."*

- `_drive_wave` now **returns the number of passes it consumed** (`flow.py:899` signature,
  `:920` counter, `:952` / `:982` / `:987` the three returns). It is the only place a pass is
  spent, so it is the only honest place to count them.
- `_drive_and_act` holds one `budget` / `spent` pair (`flow.py:1027-1028`), hands each wave
  **what is left** (`flow.py:1089`), and refuses to open another wave once the budget is gone
  — never silently: `_warn_abandoned` names every remaining bundle with its resume hint
  (`flow.py:1059-1066`), the same #260 discipline the wave-level exhaustion already used.
- This is a real semantic change for *every* multi-wave run, not only adopted ones — which is
  what the ruling asked for ("across all waves"). It is documented where the budget is
  defined: `docs/07-crosscutting.md:309-318` and `config.py:293-300`.
  With the default `max_passes = 20` and a wave costing 1–3 passes, ordinary batches are
  unaffected; a run that does hit the cap now stops and says so instead of spending
  20 passes *per wave*.
- Two tests bind it: `test_the_pass_budget_is_one_cap_for_the_whole_run`
  (`test_flow_adopt_split.py:273`) — budget 3 finishes the parent (2 passes) and 601 (1), and
  602 is left PLANNED and named; budget 4 finishes all three — and
  `test_an_adopted_wave_only_gets_what_is_LEFT_of_the_run_budget` (`:306`), where 601 wants
  two passes and gets the one that remains. The second test counts **actual passes**
  (`_build_all` calls) and asserts `passes == 3` on a budget of 3, which is what catches a
  wave being handed the full allowance again.

### (2) The announcement names the child's REAL wave

Ruling: *"report each child's REAL wave index from the recomputed schedule, not the hardcoded
parent-index+1 … fix both report sites and the assertions."*

- There is now **one** report site (`flow.py:888-895`), reading the index back out of the
  schedule `_reschedule` just produced: `wave_of = {name: k + 1 + j …}` (`flow.py:884`). One
  line per (parent, wave) group, so the criterion's shape survives when two children of one
  parent land in different waves:
  `flow: issue_500 split → adopted children issue_601 into wave 1` /
  `… issue_602 into wave 2`.
- The v1 second report site is gone: the single-id `flow` no longer prints its own literal
  `into wave 1`; it routes through `_drive_and_act` (`flow.py:433-435`) and gets the same
  announcement from the same code.
- A child the reschedule **held** is no longer announced as adopted at all (`flow.py:891-892` —
  it is not in `wave_of`); `_report_held` has already named it. The held test asserts the
  absence (`test_flow_adopt_split.py:363`).
- Consequence to read carefully at sign-off: the index is the wave of **the schedule the
  child is driven in**, i.e. the same numbering every other `flow: wave k …` message in that
  run uses. For a mid-run `flow_ids` split that is `k+1, k+2, …` (matching the brief's
  `<k+1>` shape). For the single-id path — where the parent was never *in* a numbered wave —
  the children's waves are that adoption drive's 0, 1, …, and the test asserts exactly that
  (`test_flow_adopt_split.py:245-246`). Naming them 1, 2 there would have required a
  reporting offset that lies about which wave the fold/publish messages refer to.

### (3) The two entry points now agree on identical disk state

Ruling (b): *"adopting stranded children of a parent split in an EARLIER run is accepted as
intended recovery behavior — do NOT restrict adoption to this-run splits. Instead make both
entry points consistent … today `flow_ids` filters the terminal parent out before adoption
runs."*

- `flow_ids` keeps a terminal split parent as an **adoption seed** instead of dropping it
  (`flow.py:1296`, `:1304-1310`, `:1320`), and no longer returns early when the drive set is
  empty but a seed exists (`flow.py:1317-1318`).
- `_drive_and_act` takes `adopt_seeds` (`flow.py:999`) and runs one **pre-pass** over them
  before the batch is levelled (`flow.py:1043-1047`). The single-id `flow` uses the same
  parameter (`flow.py:433-435`), so both entry points reach adoption through one code path.
- `test_both_entry_points_adopt_a_stranded_split_on_identical_disk_state`
  (`test_flow_adopt_split.py:248`) drives the *same* on-disk shape through `flow.flow_ids`
  and `flow.flow` (two subTests, fresh instance each) and requires both to complete 601/602.
- Honesty fixes that ride along: `docs/07-crosscutting.md:256-268` states the recovery
  semantics outright ("Naming a parent that is **already** terminal on a split does the same
  thing … deliberate … it is how a run that stopped before its children were driven is
  recovered"); the planner role prompt (`template/agents/planner.md.jinja:162-179`) and the
  runtime Plan prompt (`leaves.py:581-590`) say the same. I also corrected the brief's now-
  superseded Impact bullet in place (`results/issue_449/brief.md`, "Behaviour changes when a
  split is adoptable"), marked as the Iteration-1 ruling rather than rewritten as if Plan had
  said it.

### (4) The T3 red from iteration 1

Not touched, per the ruling: it is `PDCA_VERIFY_BASE` leaking from a wave>0 bundle's gate
process into the subprocesses `template/tests/test_verify_base.py` spawns. In this
environment `./engine/scripts/run-suite.sh` is **fully green** (root 7/7 OK, driver
1630/1630 OK) because the var is unset; expect the same 11 non-gating failures if the gate
runs with it set. Nothing in this patch touches `gates.py`, `publish.read_stack_base` or
that test.

---

## 2. One thing I fixed that was NOT in the carry-forward

While probing the new seed path I hit a genuine trap: `pdca flow 500 700` where 500 is a
stranded split parent and 700 declares `Depends on: 601` (a child about to be adopted) raised
`ValueError: issue_700: declared dependency '601' is neither in this batch nor an existing
COMPLETE bundle` — because the strict `waves.compute_waves` ran *before* the seed pre-pass
could put 601 in the batch. (Pre-fix the same call raises identically, so it is not a
regression — but it aborts precisely the recovery run the seed path exists for.)

Fix: the pre-pass runs first, on a provisional single wave, and the strict levelling only
runs when nothing was adopted (`flow.py:1043-1047`); `_adopt_split_children` returns whether
it spliced (`flow.py:828`, `:872`, `:882`, `:896`). Cost: 6 changed lines + a `bool` return.
When a seed *does* contribute children, the initial levelling is the tolerant
`partition_schedulable` + `compute_waves` pair instead of the strict raise — a broken
`Depends on` in that run is then held-and-named rather than fatal, which is the resume path's
documented tolerance and the right behaviour in a recovery run.

Verified by a scratch check (not shipped — it would add a third fixture shape for one edge):
`WAVES: [['issue_601'], ['issue_602', 'issue_700']]`, all three COMPLETE.

---

## 3. Alternatives considered (with costs, not adjectives)

- **Restrict adoption to splits that happened during this run** (v1's other option for the
  adversary's finding): ~8 lines (snapshot the drive set's states at entry, compare at
  adoption). Rejected because the human ruled the opposite in (b) — stale-split adoption is
  the intended recovery — and because it would have made `pdca flow 500` a no-op for exactly
  the operator who is trying to rescue stranded children.
- **A `wave_offset` parameter so the single-id path reports "wave 1, wave 2"**: ~5 lines (one
  parameter, four `wave {k}` f-strings inside `_drive_and_act` at `:1063`, `:1145`, `:1159`,
  `:1174` would have to add it too, or they would contradict the adoption line). Rejected: it
  buys cosmetic agreement between two entry points at the price of a second wave numbering in
  the same log. The ruling asked for the *real* index; this would print a synthetic one.
- **Re-enumerate the bundle root between waves** (the brief's own rejected alternative): 1
  line, and it silently turns every explicit-id flow into a disk sweep. The lineage edge is
  what keeps adoption scoped — asserted by
  `test_adoption_follows_the_lineage_edge_not_a_disk_sweep` (`test_flow_adopt_split.py:323`).
- **Parse child ids out of the parent's `build-notes.md`**: rejected — that breadcrumb is
  prose for a human (`split.py:627-634` on HEAD); 456 shipped the machine-readable record and
  `split.read_lineage` is tolerant by contract (`split.py:373-402` on HEAD), so an unreadable
  record degrades to a report + skip instead of a crash
  (`test_a_split_parent_without_a_children_record_is_reported_not_guessed`).
- **Adopt into the CURRENT wave**: cheaper (no reschedule), but a wave's fold happens once at
  its end (`flow.py:1141-1179`), so a child arriving mid-wave would build on a base about to
  move. Children go into `wave_list[k+1:]` only.

---

## 4. Refuting my own test (forced, recorded)

**(a) Genuine red?** Yes — proved by the project's own C4 runner, not by hand:
`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → green leg `Ran 8 tests …
OK`; red leg (production hunks reverted, test kept) `Ran 8 tests … FAILED (failures=9)`;
`C4 PASS: red without the fix, green with it`. Every red-leg failure is a substantive
assertion — `4× 'PLANNED' != 'COMPLETE'`, `3× None != 'COMPLETE'`, `1× 2 != 3` (the pass
count), `1× 'no readable children record' not found` — and **no** ImportError /
ModuleNotFoundError, so it is a real red and not the exit-77 PDCA-UNVERIFIABLE shape the
brief warned about (the test imports modules only: `from pdca_harness import flow, leaves,
split, state`).

Beyond the whole-patch revert, I mutated each rejected defect back in and re-ran the module
(the tests that fired are exactly the ones that should):

| Mutation (v1's defect) | Result |
|---|---|
| every wave gets `max_passes=budget` (allowance not drawn down) | `FAIL: test_an_adopted_wave_only_gets_what_is_LEFT_of_the_run_budget` |
| no run-wide accounting at all (`_drive_wave(…, max_passes=budget)`, no `spent`) | `FAIL: …_only_gets_what_is_LEFT_…` + `FAIL: test_the_pass_budget_is_one_cap_for_the_whole_run` |
| announcement hardcoded to `into wave {k + 1}` | `FAIL: test_flow_ids_drives_the_children_of_a_mid_run_split` + `FAIL: test_single_id_flow_drives_the_children_of_its_own_split` |
| `flow_ids` drops the terminal split parent (no seeds) | `FAIL: test_both_entry_points_… (entry='flow_ids')` |

**(b) Production path?** Yes. The tests call the real entry points `flow.flow_ids` /
`flow.flow` — never an internal helper — and the split itself is performed by the production
`split.accept` (`test_flow_adopt_split.py:116-123`), so the parent's `close-disposition`
marker, its `split-lineage.json` `children` record and the child bundles are byte-for-byte
what `pdca split --accept` writes. The stranded-split fixture is built the same way plus the
production `flow._drive_wave` (`:184-199`). What is stubbed is only what the offline suite
always stubs: the six model leaves (`_stub_config`, mirroring
`template/tests/test_flow_slice.py:32-55` on HEAD) and, per test, `leaves.do_plan` /
`leaves.run_signoff_batch` standing in for the two interactive sessions — the same technique
`test_flow_slice.py` uses. No adoption logic is re-implemented in the test.

**(c) Fixture includes the fault?** Yes — the failing element is present in every case, not
curated out:
- the parent really reaches `close-disposition = split` **while the run holds it** (Entry-B:
  first sign-off records `iterate-plan`, the re-plan splits — `_arm(replan_first=True)`);
- the stranded-split test really leaves 601/602 PLANNED on disk before the run starts
  (asserted inside `_strand_a_split` — state AND the `split` marker itself, `test_flow_adopt_split.py:198-203`);
- the held test really writes an unresolvable `Depends on: GHOST` into 602's brief after the
  split (`:346-350`), and the run is required to continue;
- the no-record test really `unlink()`s `split-lineage.json` (`:370-371`);
- the budget tests really exhaust the budget (and count the passes) rather than asserting a
  message about it.

Additional refutations I attempted that **failed to break it** (scratch, not shipped):
depth-2 adoption — 500 splits into 601/602, then 601 splits into 701/702 mid-run: all five
COMPLETE, waves `[[500], [601], [602, 701, 702]]`, and the grandchildren announced `into wave
2`, which is where they are actually driven; and the seed-plus-ordinary-bundle case in §2.

---

## 5. Scope, risk and what a reviewer should look at hardest

- **The run-wide budget is the one change that touches runs with no split in them.** It is
  deliberate (ruling 1) and documented in three places, but it is the hunk to review first:
  `flow.py:1059-1066` (stop) and `:1089` (draw-down). A batch whose waves collectively want
  more than `max_passes` passes now stops early **with every un-terminal bundle named** —
  where before it would keep going with a fresh allowance per wave.
- **`flow()` now calls `_drive_and_act` on every single-id run** (`flow.py:433`). With no
  split it costs one `state.state` + one marker read and returns `{}` before any sweep,
  publish or Act (`flow.py:1048-1049`); Act stays `flow()`'s single tail call (`do_act=False`
  on the inner call).
- **Nothing is adopted while a split is still AWAITING_SIGNOFF** (`_is_split_parent` requires
  terminal, `flow.py:734-748`) — the human confirms the decomposition first.
- No external dependency was needed: python3 stdlib + git, the offline suite, no tracker /
  network / `gh` / container. Nothing to declare as NEEDS-HUMAN on that axis.

## 6. Commands run (project runners only)

```
# red→green, the configured C4 gate
PDCA_BUNDLE=…/results/issue_449 PDCA_WORKTREE=…/pdca-harness.pdca-wt-l0 \
  ./engine/scripts/run-verify.sh          → C4 PASS: red without the fix, green with it
./engine/scripts/run-suite.sh             → T3: root suite OK, driver suite OK (1630 tests)
./engine/scripts/run-docs-check.sh        → lint_docs: OK; render_site: link audit OK
```

The target repo configures no formatter/linter hook (no `.pre-commit-config.yaml`, no
ruff/black config); CONTRIBUTING.md's commit-time requirements are the DCO sign-off (publish's
`git commit -s`) and "keep the offline suite green", which is verified above. Added lines stay
within the files' existing width conventions (max added line 95 chars; `flow.py` on HEAD is
106).

STOP discipline observed: nothing pushed, no branch created, no PR opened or marked ready.
