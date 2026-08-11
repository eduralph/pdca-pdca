# Build notes — issue 473, iteration 2 (flow-adopt-recovery-reporting)

## Wave base and where the citations point

Built in `$PDCA_WORKTREE` (`/home/eddie/pdca/pdca-harness.pdca-wt`), `HEAD` =
`063203a "pdca-integrate: issue_472"` — child-1's accepted adoption core folded onto
`3e3b829` (PR #470, the #468 unified drive path). Every `path:line` below is that tree.
`git apply --check --reverse patch.diff` is clean against it, so the diff reconstructs on
the base the driver rebuilds from.

## Iteration 1 carry-forward — what I did differently

The previous attempt was rejected on **C5 / C3 / T3** (the budget rule) and **T5** (the
test that encoded the rejected rule). Its `_run_pool` sized the pool at *allowance × (index
of the last wave holding a NAMED id + 1)*, which fixed the named-id starvation the adversary
reproduced and left every other starvation in place: a purely adopted tail wave, and a
**pure recovery** run (whose own drive set is empty, so the pool funded one wave however
many children the seed handed over). The reviewer's ruling was explicit — *"Rebuild the
budget rule around every live wave (while retaining the non-reset bound)"* — and that is the
brief's own words (`brief.md:24`, Scope (2)): **per-wave allowance × live wave count,
recomputed at splice**.

So iteration 2 ships that rule literally: `flow.py:1259` `_pass_pool(allowance, wave_list)
= allowance * len(wave_list)`, taken as `budget = max(budget, _pass_pool(...))` at the
initial sizing (`flow.py:1458`), after the recovery splice (`flow.py:1467`) and after every
mid-run splice (`flow.py:1527`). `spent` is never reset and no wave is ever handed more than
`allowance` (`flow.py:1516`, unchanged) — the "non-reset bound" the ruling told me to retain.

I did **not** re-submit the named-only rule in any disguise; `named` is not read by the pool
arithmetic at all any more.

### The consequence I am not hiding: the pool no longer truncates a run

With one allowance per live wave and every wave capped at `allowance`, `spent ≤ allowance ×
k` before wave `k`, while `budget ≥ allowance × (k+1)` — so `spent >= budget`
(`flow.py:1479`) cannot fire for a run whose waves each spend at most their allowance. Five
of child-1's 27 tests pinned the *superseded* property ("one cap for the whole run") and go
red under the new rule. That is not a regression I tolerated, it is the trade Plan decided:

- What the operator loses: `--max-passes 3` on a run that splits can now cost more than 3
  passes in total (4 in the pinned case), because each wave — including the ones the split
  created — gets the 3 the operator set for a wave.
- What the operator gains: no bundle the run **scheduled** is abandoned by arithmetic done
  before that wave existed, including ids they typed themselves.
- What still bounds the run: adoption is finite — a bundle is adopted once (`known`), a
  parent examined once (`examined`, `flow.py:1194`), every adopted child is a bundle already
  on disk. Total passes ≤ allowance × (bundles reachable through the lineage), the same
  shape of bound a non-adopting run has always had.

I checked whether the two goals can be reconciled before accepting the trade. They cannot:
satisfying the adversary scenario (budget ≥ 5 where the pre-adoption schedule sizes 4) and
pure recovery (budget ≥ allowance × child waves where the drive set sizes 0) both force
*one allowance per live wave*; any rule that funds every live wave makes `spent >= budget`
unreachable, and any rule that keeps it reachable starves one of the two. The only formula
that keeps all 27 child-1 tests green is exactly iteration 1's named-only rule — measured,
not assumed: it is the version I ran first, and the version the reviewer rejected.

Because the *contract* changed, I re-pinned the five tests rather than deleting or weakening
them, and rewrote each docstring to say what it now pins and what it used to
(`test_flow_adopt_split.py:397` → `test_every_wave_the_run_grows_into_is_funded_at_the_allowance`,
`:438` → `test_an_adopted_wave_is_capped_at_one_allowance_like_any_other`, `:462` →
`test_a_wave_that_runs_its_allowance_out_does_not_stop_the_waves_it_created`, `:498` →
`test_a_wave_that_stalls_is_charged_and_the_adopted_wave_still_runs`, `:544` leg 2 of
`test_an_adopted_child_that_splits_again_is_re_adopted_and_bounded`). Every non-budget
assertion in those tests is kept verbatim; the renamed ones would otherwise carry names that
assert a property the code no longer has. The two operator-facing documents that stated the
superseded rule are updated with it (`docs/07-crosscutting.md:328`,
`template/agents/planner.md.jinja:170`) — shipping code whose docs contradict it is not
"minimal", it is a second defect.

**T5 (the rejected test evidence) is addressed at the root**: iteration 1 got its non-zero
rc for the stdout test by making an adopted child *starve on the budget* — i.e. its stdout
test required the very outcome criterion (2) forbids. The new stdout test
(`test_flow_adopt_recovery.py:518`) gets its failure from an injected **builder-leaf
failure** on an adopted child (`_build_fails`), which is budget-independent: the run has
budget to spare, 601 simply cannot be built. No test in this bundle asserts a starved
schedule anywhere.

## The three changes

**(1) Recovery — `flow.py:1743` (`flow_ids`) + `flow.py:1465` (`_drive_and_act`).**
The pre-run terminal filter still skips the parent and still prints #468's non-destructive
hint (`flow.py:1751-1754`, untouched) — a terminal bundle has nothing to build. What is new
is `flow.py:1756-1767`: when it `_is_split_parent(d)` (the core's own predicate,
`flow.py:874`), it is appended to `seeds` and the run says so on stderr, and `flow_ids`
threads `seeds` into `_drive_and_act`'s new `adopt_seeds` keyword (`flow.py:1773`). Inside,
`flow.py:1465-1466` calls **the core's own** `_adopt_split_children` once, with `k=-1` — so
`wave_list[k+1:]` is `wave_list[0:]`, the whole schedule, and the seed's children are
levelled in front of everything else exactly as a mid-run split's children are levelled
after their parent's wave. No second adoption mechanism exists; `k=-1` is the only new
argument value the function sees.

Transitivity needed one addition to the core, because a recovery seed's child can itself be
terminal on a split (500 → 601 → 701, an earlier run stopped mid-chain) and `_adoptable`
dropped it as "already terminal": the candidate list became a **work queue**
(`flow.py:1192-1205`) and `_adoptable` hands such a child back through a new `onward`
out-param (`flow.py:1028-1033`), mirroring the existing `refused` out-param idiom. The chain
is therefore walked by re-entering the same reader with the same guards — `_PLAIN_ID`,
`_inside_bundle_root`, the dedup, the `known` refusal — rather than by a second reader of
`split-lineage.json`. `examined` makes each bundle leave the queue once, so a hand-edited
lineage cycle drains it (pinned: `test_a_lineage_cycle_is_examined_once_and_the_run_returns`).
This is the shape the brief's cited reference implementation uses
(`results/issue_469/iteration-v3/patch.diff`, `_adopt_split_children`'s queue).

**(2) Budget — `flow.py:1259` `_pass_pool`, called at `:1458`, `:1467`, `:1527`.** Above.
The `spent >= budget` guard is kept and its comment rewritten to say plainly that a
per-wave-capped run can no longer reach it (`flow.py:1479-1487`): it remains the invariant
"no wave opens on budget the pool does not hold", it is what a degenerate
`[driver].max_passes = 0` hits, and removing it would mean deleting child-1's `spent`
accounting and `_drive_wave`'s return contract — a much larger diff (≈40 lines across
`_drive_wave`, `_drive_and_act` and four tests) that also discards the "non-reset bound" the
ruling told me to retain.

**(3) Stdout — `cli.py:670-676` (`_report_single`, docstring from `:655`).** The named id's line is printed first,
unconditionally, as before. `_results_rc` is computed into `rc`; when `rc` is non-zero, every
OTHER entry whose state is not a successful terminal is printed in the SAME
`state<TAB>path` shape. A successful run prints exactly one line, as it always has (pinned
by `test_a_single_id_run_that_succeeds_still_prints_exactly_one_line`). I chose the
per-entry lines over the brief's alternative ("one summary line") because the shape already
exists and is already parsed — reusing it costs the 4-line loop at `cli.py:672-675` and adds
no format to document; a prose summary would be a second, undocumented shape on top of the
one contract the brief itself calls authoritative. No rc rule changed: the single-id
AWAITING_SIGNOFF leniency (#468) is untouched, and so is the affirmed policy that held
children stay out of the results map.

## Scope discipline

Untouched: `_reschedule`, `_report_held`, `_report_refused`, the splice/announce body of
`_adopt_split_children` below the queue, `waves.*`, `split.*`, `flow_batch` (the new keyword
defaults to `None`, so a CSV run is byte-identical), `_terminal_hint`'s text, the results-map
and rc rules. Docs/prompt edits are confined to what this patch makes false or newly true:
the two paragraphs that asserted the superseded budget contract
(`docs/07-crosscutting.md:328`, `planner.md.jinja:170`), the sentence that said a parent an
earlier run already closed is *not* picked up (`docs/07-crosscutting.md:277`), and one added
paragraph documenting recovery for the operator (`docs/07-crosscutting.md:257`). No other
doc page, prompt or config is touched.

## Verification — the three refutation questions

**(a) Genuine red?** Yes, twice over. By hand: `git stash push` of only
`template/src/pdca_harness/{flow,cli}.py`, then the new module — **9 of 10 fail**, all 10
run (no ImportError; the module imports modules only). The 10th
(`…succeeds_still_prints_exactly_one_line`) is a no-regression pin for the already-correct
terse case, green in both legs by design. Independently, the project's own gate
`engine/scripts/run-verify.sh` reverts the production hunks itself and reports
`C4 PASS: red without the fix, green with it` — green leg 10/10 + 27/27, red leg 9 failures
+ 5 failures. The 5 are the re-pinned child-1 budget tests: they are red without the
production change *because they now pin the new rule*, which is the intended outcome, not
collateral.

**(b) Production path?** Yes. Every test drives `cli._flow` (`cli.py:558`) — the real CLI
entry — into the real `flow.flow_ids` → `_drive_and_act` → `_adopt_split_children` chain.
The splits are materialised by the production `split.accept` (`split.py:525`), never
hand-written JSON, and the "an earlier run stranded these" fixture is carried to COMPLETE by
the production `flow._drive_wave` (`_drive_to_complete`), so the disk the recovery run starts
from is what a real interrupted run leaves — asserted inside the fixture (`COMPLETE`, close
marker `split`, children `PLANNED`) before the run under test starts. Only the six leaves are
stubbed (the suite's own convention, `test_flow_adopt_split.py:43`), and `_build_all` /
`_drive_wave` are pass-through spies that call the production function and return its value.
There is no mock of adoption, of the pool, or of the reporting anywhere in the module.

**(c) Fixture includes the fault?** Yes. The starvation test is the adversary's own
scenario, unedited: `500` splitting into `601`, `810` briefed `Depends on: 500` +
`Conflicts with: 601`, `pdca flow 500 810 --max-passes 2`, `601` costing two passes — and
pre-fix it reproduces exactly what v3 reported (`810` PLANNED, rc 1, "the run's pass budget
is spent"). The recovery fixtures contain the stranded children rather than curating them
out (the chain test leaves 601 terminal-on-split with 701/702 PLANNED, and asserts that
before the run). The stdout test's failure is a real injected builder-leaf exception on an
adopted child that IS in the results map, not a fixture arranged to exclude it.

## Full-suite, docs and formatter

- `engine/scripts/run-suite.sh` → `== T3: root suite OK, driver suite OK` (root: 7 tests
  including the copier render + update-compat legs, which really ran here — not skipped;
  driver: **1670 tests, OK (skipped=2)**).
- `engine/scripts/run-docs-check.sh` → `lint_docs: OK`, `render_site: link audit OK`
  (22 pages) — the T2 gate exists in this instance at `engine/scripts/run-docs-check.sh`
  and passed; the render also exercises the edited `planner.md.jinja`.
- Formatter/commit hooks: the target has **no** `pyproject.toml`, `.pre-commit-config.yaml`,
  `ruff.toml`, `.flake8`, `setup.cfg` or `.editorconfig` (checked at depth 3), and no CI
  lint job — `.github/workflows/` holds only `docs-check`, `render-check`,
  `docs`, `require-linked-issue`, all of which this patch passes locally through the two
  gate scripts above. `CONTRIBUTING.md:26`'s single stated discipline ("keep the offline
  suite green") is satisfied. Added lines were measured against each file's own wrap
  convention: max added length is 98 (`flow.py`, base max 106), 94 (`cli.py`, base 236),
  95/94 (the two test files, base 98), 93 (`planner.md.jinja`, base 101), 81
  (`docs/07-crosscutting.md`, base 144).

## Not done / for the human

- The run-wide pool is now, by construction, unreachable for a run whose waves each spend at
  most their allowance (see above). If the project wants a genuine whole-run ceiling *as
  well as* funded adopted waves, that is a second knob (e.g. `[driver].max_run_passes`) and
  a Plan decision, not something to smuggle in here.
- `flow_batch` (the CSV resume sweep) still does not recover stranded splits: its resume set
  excludes terminal bundles by design, and a disk sweep is explicitly out of scope
  (`brief.md:68`). Recovery there is `pdca flow <parent-id>`.
