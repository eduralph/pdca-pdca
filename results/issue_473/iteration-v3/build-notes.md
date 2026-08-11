# Build notes — issue 473, iteration 3 (flow-adopt-recovery-reporting)

## Wave base and where the citations point

Built in `$PDCA_WORKTREE` (`/home/eddie/pdca/pdca-harness.pdca-wt`), `HEAD` =
`063203a "pdca-integrate: issue_472"` — child-1's accepted adoption core folded onto
`3e3b829` (PR #470, the #468 unified drive path). Every `path:line` below is that tree with
this patch applied. `git apply --check --reverse patch.diff` is clean against it, and the C4
gate's own revert/re-apply cycle round-trips, so the diff reconstructs on the base the
driver rebuilds from.

## The iteration-2 carry-forward — what it asked, and what is honestly possible

Round 2 was rejected on **T4 Contribution** alone: *"affected-path history plus the sole
closed-unmerged PR found no duplicate, but `pr-description.md` and `commit-msg.txt` are
outside reviewer inputs, so the substantive checker defined at
`template/src/pdca_harness/cli.py:1081` could not be reproduced."* Every other row (C1–C5,
T1–T3) was PASS; T5 and Validation were deferred human calls.

That finding is **by design and not addressable from Do**, and the target's own code says
so at the exact line the reviewer cited — `template/src/pdca_harness/cli.py:1075-1083`:

> *"**Artifacts not drafted yet ⇒ a declared deferral, not a bare pass** (issue #401). This
> row is registered for Check *and* re-run by `publish` … at Check time the two artifacts it
> lints do not exist — publish drafts them later … the artifacts the row names are not among
> its inputs, which is why every cycle escalated this by-design condition to SUMMARY §6
> NEEDS-HUMAN. The substantive verdict is unchanged and still hard-gates the push
> (`publish._t4_passes`)."*

So `pr-description.md` / `commit-msg.txt` do not exist during Do or Check for *any* bundle;
they are drafted by the publish leaf after sign-off, and re-gated there. Manufacturing them
in the bundle to make the reviewer's row reproducible would be Do writing publish's
artifacts — the opposite of the STOP discipline — so I did not. What I *can* do, I did:

* **The novelty half of T4, with evidence a human can re-run.** On the wave base:
  `git log --all -S "adopt_seeds" -- template/src/pdca_harness/flow.py` → no commit in any
  ref; `git log --all -S "_report_single" -- template/src/pdca_harness/cli.py` → one commit,
  `4814b3d` (#468), which *introduced* it and never touched it again;
  `git log --all -- template/tests/test_flow_adopt_recovery.py` → empty (the file exists in
  no ref). The only prior adoption commit on `flow.py` is `96c9704` (child-1 / #472), folded
  here as `063203a`. There is no duplicate or prior art for this slice.
* **Flagged it for the human below** (§ Not done), because §6 will carry it again and the
  human should know it is the #401 condition, not an unanswered defect.

I did **not** re-submit round 2 unchanged: I re-derived the implementation on a clean base,
and the differences from it are listed in the next section (a corrected rationale for the
retained pool guard plus a test that makes it non-vacuous, a recovery-shape stdout test that
round 2 had no coverage for, a stronger parity assertion, one fewer test helper).

## The three changes

### (1) Recovery — `flow.py:1750-1782` (`flow_ids`) + `flow.py:1467-1476` (`_drive_and_act`)

The pre-run terminal filter still skips the parent and still prints #468's non-destructive
hint (`flow.py:1765-1768`, untouched) — a terminal bundle has nothing to build. What is new
is `flow.py:1769-1777`: when `_is_split_parent(d)` (the core's own predicate, `flow.py:876`)
holds, the bundle is appended to `seeds` and the run says so on stderr; `flow_ids` threads
`seeds` into `_drive_and_act`'s new `adopt_seeds` keyword (`flow.py:1782`). Inside,
`flow.py:1468` calls **the core's own** `_adopt_split_children` once with `k=-1`, so
`wave_list[k+1:]` is the whole schedule and the seed's children are levelled in front of
everything else exactly as a mid-run split's children are levelled after their parent's
wave. No second adoption mechanism exists; `k=-1` is the only new argument value the
function sees. Mirrors the brief's cited reference implementation
(`results/issue_469/iteration-v3/patch.diff`, `_drive_and_act`'s seed pre-pass).

Transitivity needed one addition to the core, because a recovery seed's child can itself be
terminal on a split (500 → 601 → 701, an earlier run stopped mid-chain) and `_adoptable`
dropped it as "already terminal": the candidate list became a **work queue**
(`flow.py:1194-1210`) and `_adoptable` hands such a child back through a new `onward`
out-param (`flow.py:1029-1039`), mirroring the existing `refused` out-param idiom. The chain
is therefore walked by re-entering the same reader with the same guards — `_PLAIN_ID`,
`_inside_bundle_root`, the dedup, the `known` refusal — never by a second reader of
`split-lineage.json`. `examined` (`flow.py:1198`) lets each bundle leave the queue once, so
a hand-edited lineage cycle drains it (pinned:
`test_a_lineage_cycle_is_examined_once_and_the_run_returns`, recovery test module `:370`).

A seed-only run that finds nothing adoptable returns `{}` early (`flow.py:1471-1476`) rather
than sweeping and Act-ing an empty schedule; the seed's own disposition is `flow_ids`'
`skipped` map, which is what the caller reports.

### (2) Budget — `flow.py:1263` `_pass_pool`, called at `:1461`, `:1470`, `:1540`

`_pass_pool(allowance, wave_list) = allowance * len(wave_list)` — the brief's Scope (2)
literally ("per-wave allowance × live wave count, recomputed at splice", `brief.md:24`), and
the iteration-1 ruling's literally ("Rebuild the budget rule around every live wave (while
retaining the non-reset bound)"). Taken as `budget = max(budget, _pass_pool(...))` at the
initial sizing, after the recovery splice, and after every mid-run splice. `spent` is never
reset (`flow.py:1431`) and no wave is ever handed more than `allowance`
(`flow.py:1529-1530`, unchanged) — the non-reset bound the ruling told me to retain.

**The consequence I am not hiding: the pool no longer truncates a run.** With one allowance
per live wave and every wave capped at `allowance`, before wave *k* we have
`spent ≤ allowance × k` while `budget ≥ allowance × (k+1)`, so `spent >= budget`
(`flow.py:1486`) cannot fire for any `allowance ≥ 1`. That is the trade Plan decided:

* What the operator loses: `--max-passes 3` on a run that splits can cost more than 3 passes
  in total, because each wave — including ones the split created — gets the 3 set for a wave.
* What the operator gains: no bundle the run **scheduled** is abandoned by arithmetic done
  before that wave existed, including ids they typed themselves.
* What still bounds the run: adoption is finite — a bundle is adopted once (`known`), a
  candidate examined once (`examined`), every adopted child is a bundle already on disk. Total
  passes ≤ allowance × (bundles reachable through the lineage).

I checked whether the two goals can be reconciled before accepting the trade. They cannot:
satisfying the adversary's scenario (budget ≥ 5 where the pre-adoption schedule sizes 4) and
pure recovery (budget ≥ allowance × child waves where the drive set sizes 0) both force *one
allowance per live wave*; any rule that funds every live wave makes `spent >= budget`
unreachable, and any rule that keeps it reachable starves one of the two. The only formula
that keeps all 27 child-1 tests green is iteration 1's named-only rule — measured, not
assumed: it is the rule the reviewer rejected.

**Correcting round 2's rationale for keeping the guard.** Round 2 justified retaining
`spent >= budget` by saying it is "what a degenerate `[driver].max_passes = 0` hits". That is
**false**: `config.py:675` clamps the loaded value (and `PDCA_MAX_PASSES`) to `max(1, …)`,
and `cli.py:572` clamps `--max-passes` the same way, so no operator input reaches allowance
0. The honest reason to keep it is that it is the pool's **admission rule** — "no wave opens
on budget the pool does not hold" — which a future splice site that forgets to re-size, or a
wave that came to spend more than it was handed, would violate silently without it. The
comment at `flow.py:1487-1501` now says that, and names the clamps, instead of claiming a
reachable degenerate config. To stop it being an unfalsifiable claim I pinned it through
`cli._flow` at the one input that still reaches it, an in-process `Config` with
`max_passes = 0` (`test_no_wave_opens_on_budget_the_pool_does_not_hold`, recovery module
`:537`).

Rejected alternative — *delete* the pool (drop `budget`/`spent`, revert `_drive_wave` to
`-> None`) so nothing vestigial remains. Measured cost: 7 production lines removed in
`_drive_and_act` (`flow.py:1431`, `:1461`, `:1467-1470` re-size, `:1486-1505` guard,
`:1529-1530` cap, `:1540`), but `_drive_wave`'s `used` accounting and `int` return go with
them — `flow.py:1288` (signature), `:1312`, `:1314`, `:1344`, `:1374`, `:1383` — and 4
child-1 tests read that return through `self.passes`
(`test_a_wave_that_runs_its_allowance_out_…`, `…stalls_is_charged…`,
`…_capped_at_one_allowance…`, `…keeps_a_full_budget_per_wave`): ≈40 changed lines across
`flow.py` and `test_flow_adopt_split.py`. It also deletes #260 machinery that landed with
child-1 and is explicitly out of scope (`brief.md:65` — "the adoption core's
detect/validate/splice/report mechanics (child-1, reused as-is)"). Not the smallest change
that restores the invariant.

### (3) Stdout — `cli.py:644-679` (`_report_single`)

The named id's line prints first, unconditionally, as before. `_results_rc` is computed into
`rc`; when `rc` is non-zero, every OTHER entry whose state is not a successful terminal is
printed in the SAME `state<TAB>path` shape (`cli.py:673-678`). A successful run prints
exactly one line, as it always has (pinned by
`test_a_single_id_run_that_succeeds_still_prints_exactly_one_line`, `:609`).

I chose the per-entry lines over the brief's alternative ("one summary line") because the
shape already exists and is already parsed: the loop is 4 lines (`cli.py:674-677`) and adds
no format to document, where a prose summary would be a second, undocumented shape on top of
the one contract the brief itself calls authoritative. No rc rule changed: the single-id
AWAITING_SIGNOFF leniency (#468) is untouched (asserted explicitly at recovery module `:522`)
and so is the affirmed policy that held children stay out of the results map.

Round 2 tested this only in the **mid-run** shape. The sharpest case is the recovery one,
where the named id's `COMPLETE` was written by an *earlier* run — stdout then reported a
success this run neither delivered nor performed. That case now has its own test
(`test_a_recovery_run_never_reports_an_earlier_runs_success_as_its_own`, `:590`), asserting
the full stdout of a failed recovery, not just a substring.

## Re-pinning child-1's five budget tests

The contract those tests state ("one cap for the whole run") is the one the brief replaces,
so they go red on the new rule. I re-pinned them rather than deleting or weakening them, and
rewrote each docstring to say what it now pins and what it used to:

| `test_flow_adopt_split.py` | now pins |
|---|---|
| `:397` `test_every_wave_the_run_grows_into_is_funded_at_the_allowance` | 602 completes instead of starving; 4 passes over 3 waves; second leg at `--max-passes 2` |
| `:438` `test_an_adopted_wave_is_capped_at_one_allowance_like_any_other` | the adopted wave takes 2 and stops, named; its sibling still lands |
| `:463` `test_a_wave_that_runs_its_allowance_out_does_not_stop_the_waves_it_created` | the exhausted wave is still charged and named, and the wave it created still runs; rc still 1 |
| `:498` `test_a_wave_that_stalls_is_charged_and_the_adopted_wave_still_runs` | the stall still happens and 820 is still named; the adopted wave gets its own allowance |
| `:545` leg 2 of `test_an_adopted_child_that_splits_again_is_re_adopted_and_bounded` | the recursion is bounded by ADOPTION: same 6 passes at an allowance of 2, each bundle adopted exactly once |

Every non-budget assertion is kept verbatim. The two operator-facing documents that stated
the superseded contract are updated with it (`docs/07-crosscutting.md:332`,
`template/agents/planner.md.jinja:170`), as is the sentence saying a parent an earlier run
closed is *not* picked up (`docs/07-crosscutting.md:275` is the new recovery paragraph, and
`:251`/`:258` the adjusted pool/bound wording). Shipping code whose docs contradict it is not
"minimal", it is a second defect.

## Verification — the three refutation questions

**(a) Genuine red?** Yes. The project's own gate reverts the production hunks itself and
reports `C4 PASS: red without the fix, green with it`
(`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`, exit 0):

* green leg — `test_flow_adopt_recovery` 12/12 OK, `test_flow_adopt_split` 27/27 OK;
* red leg — 10 of 12 fail in the new module, 5 of 27 in the re-pinned one.

The 2 that stay green on the red leg are deliberate no-regression pins, and are labelled as
such in their docstrings: `…succeeds_still_prints_exactly_one_line` (the terse successful
shape must not change) and `test_no_wave_opens_on_budget_the_pool_does_not_hold` (the guard
predates this change; it is pinned so re-sizing cannot quietly turn it into dead code). The
10 red ones cover all three criteria — recovery (4), the chain walk and its cycle bound (2),
the budget (2 + the starvation scenario), stdout (2). No test loads a symbol this patch
adds, so the red leg runs rather than ImportError-ing (the module imports modules only,
`test_flow_adopt_recovery.py:48`).

**(b) Production path?** Yes. Every test drives `cli._flow` (`cli.py:558`) — the real CLI
entry — into the real `flow.flow_ids` → `_drive_and_act` → `_adopt_split_children` chain.
Splits are materialised by the production `split.accept` (`split.py:525`), never hand-written
JSON, and the "an earlier run stranded these" fixture is carried to COMPLETE by the
production `flow._drive_wave` (`_drive_to_complete`, `:203`), so the disk the recovery run
starts from is what a real interrupted run leaves — asserted inside the fixture (parent
COMPLETE, close marker `split`, children PLANNED) before the run under test starts. Only the
six leaves are stubbed (the suite's own convention); `_build_all` / `_drive_wave` are
pass-through spies that call the production function and return its value. There is no mock
of adoption, of the pool, or of the reporting anywhere in the module.

**(c) Fixture includes the fault?** Yes. The starvation test is the adversary's own
scenario, unedited: `500` splitting into `601`, `810` briefed `Depends on: 500` +
`Conflicts with: 601`, `pdca flow 500 810 --max-passes 2`, `601` costing two passes — and on
the red leg it reproduces exactly what v3 reported (`810` PLANNED, rc 1, "the run's pass
budget is spent"). The recovery fixtures contain the stranded children rather than curating
them out (the chain test leaves 601 terminal-on-split with 701/702 PLANNED and asserts that
before the run). Both stdout tests get their non-zero rc from a real injected builder-leaf
exception on an adopted child that IS in the results map — never from a starved schedule,
which would contradict criterion (2) — and the failing child is in the fixture, not excluded
from it.

## Full-suite, docs and formatter

* `engine/scripts/run-verify.sh` → `C4 PASS` (above).
* `engine/scripts/run-suite.sh` → `== T3: root suite OK, driver suite OK`. Root: **7 tests
  OK** — the copier render + `copier update` compatibility legs really ran here (copier 9.17.0
  in the instance venv), not skipped. Driver: **1672 tests, OK (skipped=2)**.
* `engine/scripts/run-docs-check.sh` → `lint_docs: OK`, `render_site: link audit OK`
  (22 pages) — the render also exercises the edited `planner.md.jinja`.
* `./scripts/pdca contribcheck` (T4) → exit 0 (default-open pre-publish; see § carry-forward).
* Formatter / commit hooks: the target has **no** `pyproject.toml`, `.pre-commit-config.yaml`,
  `ruff.toml`, `.flake8`, `setup.cfg`, `tox.ini` or `.editorconfig` (checked at depth 3), and
  no CI lint job — `.github/workflows/` holds only `docs-check`, `render-check`, `docs`,
  `require-linked-issue`, all of which this patch passes locally through the two gate scripts
  above. `CONTRIBUTING.md`'s single stated discipline ("keep the offline suite green") holds.
  Added lines were measured against each file's own wrap convention: max added length is 96
  (`flow.py`, file max 102), 91 (`cli.py`, 236), 93 (`test_flow_adopt_recovery.py`, 93), 92
  (`test_flow_adopt_split.py`, 95), 93 (`planner.md.jinja`, 101), 83
  (`docs/07-crosscutting.md`, 141).

## Not done / for the human

* **T4 will be NEEDS-HUMAN again, by design.** `contribcheck` lints `pr-description.md` +
  `commit-msg.txt`, which publish drafts *after* sign-off (`template/src/pdca_harness/cli.py:1075-1083`,
  issue #401); no Do-side change can give the reviewer that subject. The novelty half is
  evidenced above and reproducible with three `git log --all -S` commands. The substantive
  audit still hard-gates the push at publish (`publish._t4_passes`). Nothing here is an open
  implementation defect.
* **Landing order.** This patch is verified on the folded content of #472 (child-1), which is
  not yet in `origin/main`. Publishing this before #472 merges would omit the adoption core it
  extends — the same T5 note round 2 raised, unchanged and still the human's call.
* **The run-wide pool is, by construction, unreachable** for a run whose waves each spend at
  most their allowance (§(2)). If the project wants a genuine whole-run ceiling *as well as*
  funded adopted waves, that is a second knob (e.g. `[driver].max_run_passes`) and a Plan
  decision, not something to smuggle in here.
* **`flow_batch` (the CSV resume sweep) still does not recover stranded splits**: its resume
  set excludes terminal bundles by design, and a disk sweep is explicitly out of scope
  (`brief.md:68`). Recovery there is `pdca flow <parent-id>`.
