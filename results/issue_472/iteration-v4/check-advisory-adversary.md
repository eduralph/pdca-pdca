# Adversarial review — issue_472 (flow-adopt-core), advisory

Evidence re-run at `$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt`, base `3e3b829`):
C4 red leg reproduced by reverting only the production hunks (`flow.py`, `config.py`,
`cli.py`, `leaves.py`) and keeping the new test — **24 of 25 fail**; green leg 25/25. The
one pre-fix pass is `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`, which is
a no-regression guard and is *supposed* to be green on both legs. The suite drives through
`cli._flow` → the production `flow_ids`/`_drive_and_act` (`flow.py:1364`) and builds
fixtures with the production `split.accept` (`split.py:525`), so it is not a parallel
re-implementation. Full offline driver suite: 1658 tests, OK.

## Findings

- **NEEDS-HUMAN [impl]** — `flow.py:914` (with `flow.py:696`): a lineage record whose
  `children` array holds a **non-string** entry drops that child **silently**, in the one
  branch of `_adoptable` that prints nothing. Concrete case, run at the target: parent 500
  splits into 601/602, then `split-lineage.json` is hand-edited to `"children": [601,
  "602"]` (ints — the shape any non-`split.accept` writer or a hand edit produces).
  `_lineage_children` filters `601` out at `flow.py:696` *before* `_adoptable`'s loop, so
  none of the four report branches (`flow.py:933`, `:939`, `:953`, `:957`) ever sees it and
  `ids` is non-empty so the "no readable children record" line at `flow.py:916` does not
  fire either. Observed result: **601 never adopted and never named on stderr; 602 adopted
  then immediately held on the `Depends on: 601` `split.accept` itself wrote; parent
  COMPLETE, both children left PLANNED, and the run exits 0.** The only line an operator
  gets is `issue_602 held this run — unresolved dependency (601)`, which reads as "601 does
  not exist" while a briefed PLANNED bundle sits next to it. That is precisely the
  stranded-children end state the feature exists to end, reached quietly. Every neighbouring
  malformed-id class in this diff is loud by design (`_PLAIN_ID`, `_inside_bundle_root`, no
  brief, already terminal), and the brief's guard list demands "skipped **with a report**";
  this one is the exception. `_adoptable`'s own docstring (`flow.py:897-904`) claims "Each
  id is then filtered exactly as `flow_ids` filters an explicitly named one" — it is not,
  for ids discarded upstream of the loop. Fix is small: have `_adoptable` count/report the
  entries `_lineage_children` refused, and pin it with a `_record(iid, [601, "602"])` test.

- **NEEDS-HUMAN [human]** — `flow.py:849` and the carve-out its docstring makes at
  `flow.py:841-846`: `_inside_bundle_root` now resolves symlinks (correctly closing the
  previous round's escape), but deliberately still accepts an `issue_<id>` that is a symlink
  to **another bundle inside the same root**. Probed at the target: with
  `results/issue_601 -> results/issue_910`, where `910` is an id the operator also named and
  which is still *un-driven*, the run adopts `issue_601` and schedules **`issue_601` and
  `issue_910` into the same wave** — the same directory driven as two bundles
  (interleaved `→ issue_601: Do…` / `→ issue_910: Check…` on one bundle dir), which under
  `lanes>1` is two lanes writing one bundle. The docstring's justification only covers the
  *already-finished* alias ("skipped as terminal like any other" — which I confirmed holds);
  the in-flight alias is the case it declines, on the grounds that re-keying the drive set by
  resolved path is a wider change. That is a defensible scope call, but it is a
  data-corruption class reached from the same hand-edited-record threat model the two guards
  beside it were added for, so a human should decide whether it ships as-is or gets a cheap
  resolved-path dedup in `_adoptable`.

- **NEEDS-HUMAN [impl]** — `flow.py:775`: the docstring the patch writes for the newly
  hoisted `_report_held` asserts, unconditionally, "a held bundle is never counted as work
  the run did". The patch's own comment eleven hundred lines later
  (`flow.py:1305`) says the opposite for the case it introduced: a **named** id held by the
  re-levelling is "PLANNED, in the results map, the run fails" — and
  `test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost:595-596` pins exactly that
  (`results["811"] == PLANNED`, `rc == 1`). One helper, three call sites, two different
  downstream consequences; the shared docstring should state the child-only scope rather
  than the universal claim, since this is the file where a reader goes to learn what "held"
  costs a run.

## Refutations attempted and defeated

I could not break the following, and record the attempts so the absence is legible:

- **Mutation testing of the new code** (16 mutants against the bundle suite): `known =
  batch_names | taken` → `batch_names`; drop `_is_split_parent`'s terminal gate; lexical
  `_inside_bundle_root`; permissive `_PLAIN_ID`; hardcode the announced wave to `k+1`;
  per-wave allowance instead of `min(allowance, budget - spent)`; drop the `spent >= budget`
  break; drop the `named` protection; drop the duplicate-id dedup; cache a stale `last` for
  the fold boundary; make `_drive_wave` report 0 on each of its two un-finished exits; drop
  the retraction; report the refusal eagerly; make `_reschedule` strict. **All 15 real
  mutants were killed by named tests** (the 16th "survivor" was a no-op mutation I wrote:
  `wave_list[k:] = [wave_list[k]] + tail` is `wave_list[k+1:] = tail`). Notably the brief's
  required mutation — `known=batch_names` — is killed by
  `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once`, which the docstring at
  `flow.py:1062` cites by name as required.
- **The budget claim.** `budget = allowance * len(wave_list)` (`flow.py:1315`) with the
  break at `flow.py:1325`: for `k < len(wave_list)`, `spent ≤ allowance*k < budget`, so the
  pool is provably non-binding for a non-adopting run — the docstring/`config.py:312-325`
  claim holds. `allowance ≥ 1` is guaranteed (`config.py:675`, `cli.py:572`), so
  `min(allowance, budget - spent) ≥ 1` at the call site and the adoption recursion is
  bounded by `budget` waves; no zero-pass wave, no reset.
- **Termination / unbounded splice.** Adoption only runs after a driven wave, each driven
  wave costs ≥1 pass, a non-runnable wave `continue`s without adopting; `wave_list` cannot
  grow without spending the pool.
- **`flow_ids` totality.** `skipped | _drive_and_act(...)` (`flow.py:1595`) — I checked the
  case where an id the operator named was skipped UNPLANNED and is then materialised and
  adopted by a mid-run split: the right-hand map wins, so it is reported COMPLETE, not
  UNPLANNED.
- **Edge probes run at the target, all correct:** child bundle deleted between split and
  adoption (reported "no brief.md"); `children: []` and `children: [null, 601]` (both hit the
  loud "no readable children record"); record naming the parent itself (refused as already in
  the drive set); alias to an *already-completed* in-root bundle (skipped as terminal);
  adoption under `lanes=2` with the pooled beat sweep (waves and states correct).
- **Citation audit.** Every `path:line` the patch adds resolves on the merged base:
  `flow.py:679/694/759/1240/1354/1359`, `config.py:686`, `split.py:47/281/297/373/382-390/
  405/525/635`, `waves.py:243-246`, `gates.py:782`, the refreshed `cli.py:609-610` pointers
  (`flow.py:1549-1563`, `:1584-1590`), and all nine cited test names exist. The three docs
  anchors added to `docs/07-crosscutting.md` (`#the-split`, `#the-iteration-budget`,
  `#waves-in-execution`) resolve to real headings.
- **The ancillary `test_verify_base.py` hunk genuinely red→greens:** with
  `PDCA_VERIFY_BASE=some/branch` in the ambient environment, pre-hunk 11 of 19 fail,
  post-hunk 19/19 pass — it is a real hermeticity fix, not a cosmetic edit.
