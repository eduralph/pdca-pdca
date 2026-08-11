# Build notes — issue 449 (iteration 3): flow adopts split children mid-run

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`) off the stack base
`pdca-integration/main` = **`aaa797a`** ("pdca-integrate: issue_456" — the
`split-lineage.json` record this slice reads, plus 453's `09e4a66`). Every `path:line`
below is on that tree: **base** line numbers are the unpatched file, **post** line numbers
are the patched file the diff produces.

## What this iteration is

The adoption mechanism from iteration 2 (detect → validate → splice → report, transitive
and bounded) is **kept** — the carry-forward says it is sound. Iteration 3 fixes the five
implementation defects Check found and adds the four regression tests that let them
through. I started from `iteration-v2/patch.diff` applied to the base (it applies clean at
`aaa797a`) and edited from there, so the reviewed-sound parts are unchanged and the diff a
human re-reads is the delta below.

### The five defects and what changed

**1. `_is_split_parent` could kill a whole explicit-id run** (adversary NEEDS-HUMAN [impl];
`iteration-v2` `flow.py:744-748` caught only `OSError`, and `flow_ids` calls the predicate
outside any `_isolate`). A `close-disposition` whose bytes are not UTF-8 raises
`UnicodeDecodeError` — a `ValueError` — out of the *read*, so one corrupt marker took down
every drivable id named alongside it. Now a **total** catch (`flow.py:770` post), with the
rationale the sibling reader this builds on already spells out (`split.py:382-390` base:
"the catch is TOTAL on purpose, not a list of the expected failure types"). Bound by
`test_an_unreadable_close_marker_never_kills_the_run` (test:440).

**2. Entry-point budget parity** (adversary NEEDS-HUMAN [impl] + reviewer C3). `flow()`
charged `spent += 1` *before* the loop body, so a recovery run (`pdca flow 500`, 500
already terminal on a split) burned an iteration **observing** a finished bundle and handed
adoption `max_iters - 1` where `flow_ids` handed it the lot. Fixed by breaking out of the
loop before the charge when the bundle is already terminal (`flow.py:390-399` post) — which
is behaviour-preserving: `_plan_if_unplanned` is a no-op for a non-UNPLANNED bundle and
`driver.run_issue` returns immediately for a state already in `state.HALTED`
(`driver.py:188` base), which is what the very next line broke on. The adoption tail now
also hands down the run's *remaining pool* explicitly (`run_budget=max(0, max_iters -
spent)`, `flow.py:450` post) instead of a per-wave allowance. Bound by
`test_both_entry_points_recover_a_stranded_split_on_the_same_budget` (test:263), which runs
**both** entry points at a budget that binds (1 pass, children needing 2) and at one that
doesn't (2) and asserts the state pairs are equal.

**3. The run-wide cap truncated ordinary batches** (adversary NEEDS-HUMAN). Iteration 2
made `max_passes` a flat run-wide cap, which — as the adversary demonstrated — strands the
tail of any multi-wave batch that never adopts anything (six chained bundles at
`max_passes=5`: `705` left PLANNED where it used to complete). The human's iteration-1
RULING (1) still stands ("enforce the cap across all waves including adopted ones"), so the
answer is not to drop it but to **size** it: the run's pool is `max_passes` × the number of
waves the run *set out to* drive (`flow.py:1109` post), spent down by every wave including
adopted ones, each wave still capped at `max_passes` (`flow.py:1163` post).

> Why that is exactly right: a wave can spend at most `allowance` passes, and a
> non-adopting run has exactly `len(wave_list)` waves, so `spent ≤ allowance ×
> len(wave_list) = budget` always — the pool **provably cannot bind** without adoption, and
> `min(allowance, budget - spent) == allowance` for every one of its waves. So "no config
> key is added and none changes meaning" (brief:225) is true again for every run that does
> not adopt; `max_passes` gains a run-pool dimension **only** where the drive set grows.
> RULING (1)'s own example still holds: one seed wave at `max_passes=2` ⇒ pool 2 ⇒ the
> parent plus **one** child wave, not two.

Bound by `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` (test:375 — a
four-deep chain at `max_passes=1` completes all four waves) plus the two pre-existing
budget tests, unchanged and still green.

**4. A stale chain stopped at its first terminal generation** (reviewer C3: "`_adoptable`
drops a terminal split child before examining its descendants"). If an earlier run split
500 → 601, 602 and then split 601 → 701, 702 before stopping, 601 is terminal-on-split:
undrivable, but the only route to the grandchildren that are actually stranded. `_adoptable`
now returns two lists — drivable children, and children that are split parents themselves
(`flow.py:774-838` post) — and `_adopt_split_children` walks its candidates as a **work
queue** (`flow.py:911-921` post), so each generation is examined under its own name and the
announcement attributes 701/702 to **601**, not to the run's seed. Bound by
`test_a_stale_chain_is_walked_through_its_terminal_generation` (test:299).

**5. An explicit id list had two scheduling contracts** (adversary NEEDS-HUMAN). Iteration 2
replaced the strict levelling with the tolerant one whenever a seed adopted, so `pdca flow
800 801` (a cycle) raised while `pdca flow 500 800 801` did not — the same id list behaving
two ways on unrelated disk state. Now the batch the caller **named** is levelled strictly
first, always (`flow.py:1103` post: `waves.compute_waves(cfg, bundles)`, which raises
exactly as it does today), and only what adoption **adds** goes through
`partition_schedulable`'s tolerance. `waves.py:243-246` base is explicit that raising is
"right for an explicit `flow <ids>` / `pdca waves` request". Bound by
`test_a_named_id_list_keeps_its_strict_scheduling_contract` (test:414).

*Known limit of this ordering, stated honestly:* a named bundle that `Depends on` a
still-stranded child now hits `compute_waves`' "neither in this batch nor COMPLETE" before
adoption could put the child in the batch — but that is **today's** behaviour too (adoption
does not exist on the base), so it is not a regression, and iteration 2's ordering bought
that edge at the price of defect 5. No new raise, no removed raise.

**6 (minor, adversary).** A child dropped because it is already in the drive set was
dropped by a bare `continue` while the docstring claimed every skip is named. It is now
reported (`flow.py:820` post).

Also corrected: `_drive_wave`'s exhaustion message said "raise `[driver].max_passes`" while
naming a number that is now a *share* of the pool (reads as a contradiction at
`max_passes=20`); it now says "— this wave's allowance out of the run's pool"
(`flow.py:1038-1040` post), keeping the `pass budget exhausted after N pass(es)` prefix the
three existing `test_flow_slice.py` assertions match (`test_flow_slice.py:1597`, `:1625`,
`:1650` base). Docs (`docs/07-crosscutting.md` §The split, §The iteration budget), the
`[driver].max_passes` comment (`config.py:293-303` post) and the planner's runtime prompt
(`leaves.py:581-591` post) + role prompt (`template/agents/planner.md.jinja:162-179` post)
are updated to the pool wording and to the recovery semantics RULING (b) accepted.

## Refuting my own test (forced, recorded)

**(a) Genuine red?** Yes, twice over.
* Against the **base** (the C4 gate's own revert of the production hunks only, keeping the
  test): `./engine/scripts/run-verify.sh` → green leg `Ran 12 tests … OK`, red leg
  `Ran 12 tests … FAILED (failures=13)` → `C4 PASS: red without the fix, green with it`.
* Against **iteration 2's implementation** (the sharper question — do this round's fixes
  bind?): I swapped `flow.py`/`config.py` for iteration-v2's versions, kept this test file,
  and ran the module: `FAILED (failures=4, errors=1)` — and precisely the five new/
  strengthened cases fail, each with the defect's own signature:
  `test_an_unreadable_close_marker_never_kills_the_run` → **error** (`UnicodeDecodeError`
  escaping `flow_ids`); `test_a_named_id_list_keeps_its_strict_scheduling_contract` →
  "ValueError not raised"; `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave` →
  `[['issue_810']] != [['issue_810'], ['issue_811'], ['issue_812'], ['issue_813']]`;
  `test_a_stale_chain_is_walked_through_its_terminal_generation` → `'PLANNED' !=
  'COMPLETE'`; `test_both_entry_points_recover_a_stranded_split_on_the_same_budget` →
  `('PLANNED','PLANNED') != ('COMPLETE','PLANNED')` on the `flow` vs `flow_ids` comparison
  at the binding budget. The seven inherited cases stayed green across the swap, which is
  the other half of the claim: this round changed only what it meant to change.

**(b) Production path?** Yes. Every test calls the real entry points — `flow.flow_ids` /
`flow.flow` — never an internal helper (the defect *is* that the entry points freeze their
drive set, so a helper call would prove nothing). Imports are modules only (`from
pdca_harness import flow, leaves, split, state`), per the brief, so the red leg fails on
assertions rather than an `ImportError` the verifier classifies PDCA-UNVERIFIABLE. The
only production functions replaced are the **leaf** stubs (`leaves.do_plan`,
`leaves.run_signoff_batch` — that is what a stubbed leaf is for) plus two spies that call
straight through to the real `flow._drive_wave` / `flow._build_all` and return their
values, so the scheduling under test is the shipped code.

**(c) Fixture includes the fault?** Yes. The split is not simulated: the fixture calls the
**production** `split.accept` (`split.py:600-650` base), so the parent's
`close-disposition`, its merged `split-lineage.json` `children` record, the breadcrumb and
the child bundles with their rewritten `Depends on` are byte-for-byte what `pdca split
--accept` leaves. The stranded-recovery fixtures then drive the parent to COMPLETE through
the production `flow._drive_wave` — the per-wave driver, which has never had adoption of its
own — so the "earlier run that stopped" is really on disk, and `_strand_a_split` asserts the
fault (parent COMPLETE + `split` marker, children PLANNED) *before* the run under test
starts. Nothing is curated out: the corrupt-marker case writes real non-UTF-8 bytes, the
held-child case really has an unresolvable `Depends on: GHOST`, and the chain case really
has a terminal middle generation.

## Alternatives rejected, with the cost shown

* **Scope the run-wide cap to runs that actually adopted** (the adversary's other option).
  Rejected: it recreates defect 5's shape on the budget axis — the same id list gets two
  different budget contracts depending on whether some named id happens to carry a lineage
  record — and it retroactively re-charges the *named* waves once an adoption occurs. The
  pool sized off the original schedule costs **one line** (`flow.py:1109`) and needs no
  conditional at all.
* **Raise the shipped default `max_passes`** (the adversary's first option). Rejected: it
  changes every instance's behaviour to compensate for a cap that should not have bound in
  the first place, and `copier update` would push it to rendered instances. Cost of the
  chosen fix instead: the `max(1, len(wave_list))` factor, +1 line.
* **Traverse terminal split children inside `_adoptable` by recursion** rather than
  returning a second list. Rejected on attribution, not size (both are ~6 lines): the
  grandchildren would be announced under the *root* parent's name, so the operator's log
  would say "issue_500 split → adopted children issue_701" for a child 500 never declared.
  The queue keeps each announcement true.
* **Keep iteration 2's "seeds before levelling"** (which let a named bundle depend on a
  not-yet-adopted child). Rejected: it costs the strict contract for the ids the operator
  typed, which is the more load-bearing property (`waves.py:243-246`), and the edge it buys
  raises on the base today anyway — so nobody loses a behaviour they have.
* **Re-enumerate `results/` between waves** (one line). Still rejected, as in the brief:
  it silently turns every explicit-id flow into a disk sweep.

## Verification run (all local, offline)

| Gate | Command | Result |
|---|---|---|
| C4 | `./engine/scripts/run-verify.sh` | `C4 PASS: red without the fix, green with it` (green 12/12; red 13 failures) |
| T3 | `./engine/scripts/run-suite.sh` | `root suite OK (7), driver suite OK (1634, skipped=2)` |
| T2 | `./engine/scripts/run-docs-check.sh` | `lint_docs: OK`, `render_site: 22 pages, link audit OK` |

Note on the T3 red that failed the last two iterations: it does **not** reproduce here. The
driver suite is green at 1634 tests; the 11 `test_verify_base.py` failures the frozen gate
log shows appear only with `PDCA_VERIFY_BASE` leaking into the subprocesses — the
pre-existing harness test-isolation fault iteration 1's sign-off ruled out of scope. I did
not chase it.

Formatter/commit hooks: the target ships no pre-commit config, no `ruff`/`flake8`/`black`
config and no `core.hooksPath`; CI runs the docs lint + render and the two suites, all three
of which are green above. Longest added line is 95 chars, inside the file's existing range.

## STOP discipline

No branch pushed, no PR opened, nothing marked ready. `patch.diff`, the test at
`template/tests/test_flow_adopt_split.py` and these notes are the whole output.
