# Build notes — issue 473 (flow-adopt-recovery-reporting)

## Wave base

Built inside `$PDCA_WORKTREE` (`/home/eddie/pdca/pdca-harness.pdca-wt`), whose `HEAD` is
`063203a "pdca-integrate: issue_472"` — child-1's accepted adoption core already folded in
(`git log --oneline -3` shows it sitting directly on `3e3b829` "Merge pull request #470",
the #468 unified drive path). All citations below are against that tree, matching the
brief's "wave fold must give this bundle child-1's diff" ordering note.

## What changed, and why (path:line on the wave base)

**(1) Recovery** — `flow.py:1662` `flow_ids`. The pre-run short-circuit at
`flow.py:1731-1737` (`if s in _TERMINAL: … skipped[iid] = s; continue`) still reports the
parent's own disposition exactly as before — that part is untouched, because the parent
IS terminal and there is nothing to build for it. What's new is `flow.py:1741-1754`: when
the terminal bundle is `_is_split_parent(d)` (the SAME predicate the core already uses,
`flow.py:870` region pre-existing), it is appended to a new `seeds` list instead of being
dropped. `flow_ids` then threads `seeds` through as `_drive_and_act`'s new `adopt_seeds`
keyword (`flow.py:1364-1373`, `flow.py:1760`).

Inside `_drive_and_act` (`flow.py:1441-1449`), `_adopt_split_children` — the CORE's own
splice/report function, `flow.py:1084`, reused unmodified in its signature and body — is
called once with `k=-1` BEFORE the wave loop starts, `candidates=adopt_seeds`. `k=-1`
means `wave_list[k+1:]` is `wave_list[0:]`, i.e. the WHOLE schedule: the seed's children
are spliced in front of everything else, exactly mirroring how a mid-run split's children
are spliced in AFTER the wave that caused it (`k` = that wave's own index, the existing
call at `flow.py:1499-1500`). No new adoption mechanism was written — recovery is one
extra CALL to the mechanism child-1 already landed, with `k=-1` as the only new argument
value `_adopt_split_children` sees. This is the literal reading of the brief's Scope (1)
("route it through the same lineage-scoped adoption the core uses… not a second
mechanism") and the cited peer callsite ("child-1's adoption entry point").

**(2) Budget re-sizing** — `flow.py:1322-1351` (`_run_pool`), called at
`flow.py:1441`/`:1454`/`:1512` (`_drive_and_act`). Sizing the pool once
(`allowance * len(wave_list)`, the OLD/child-1 formula, still visible in
`test_flow_adopt_split.py`'s own budget tests) is provably safe for a run that never
adopts, but the v3 adversary's reproduction shows it fails once a splice pushes a NAMED
bundle (one the operator actually typed) into a wave LATER than the pool was sized for.

I rejected the two textually-plausible readings of "allowance × live wave count,
recomputed at splice" before landing on the one below, and both would have broken
something a red→green run caught:

- **`budget = allowance * len(wave_list)`, recomputed after every splice.** Simple, and
  it fixes the starvation case — but it also grows the pool for `500` alone splitting
  into `601`+`602` (no other named bundle at all): `test_the_pass_budget_is_one_cap_for_
  the_whole_run` (child-1's own pinned test, `test_flow_adopt_split.py:397-427`) asserts
  `max_passes=3` still stops the run at exactly 3 passes with `602` left `PLANNED`; this
  formula instead grows the pool to `3 × 3 = 9` the moment `601`/`602` are spliced in,
  finishing `602` on a 4th pass — directly contradicting the ALREADY-ACCEPTED behaviour
  the sibling child's own suite pins, and the split-proposal's own text ("a split can
  never multiply what the operator allowed"). I ran this variant first; it broke that
  exact test (`AssertionError: 3 != 4` on `self.passes`). Rejected — not a hypothetical,
  a real red I reverted.
- **`budget = allowance * (index of the last wave holding a NAMED bundle, + 1)`, taken
  as a bare re-assignment at every splice.** This is what actually reconciles the two
  requirements — it leaves the single-parent recursive-split case unchanged (the only
  named bundle, `500`, never leaves wave 0, so the pool never grows past `allowance × 1`
  no matter how many generations it recurses through) while growing exactly enough to
  cover a named bundle a splice pushes later (`810`, pushed from wave 1 to wave 2 by
  `601`'s splice: `allowance × 3` now covers it). But a BARE re-assignment can also
  SHRINK the pool: a named bundle the SAME splice's reschedule HOLDS (an unresolved
  `Depends on`) leaves `wave_list` entirely — held bundles are never scheduled — so
  re-scanning `wave_list` for named bundles "forgets" it and can shrink the pool below
  what an earlier, wider schedule already promised. This broke
  `test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost`
  (`test_flow_adopt_split.py:570-596`) — `811`, walked-away-held, stops being counted the
  moment `601`/`602` splice in, so the pool shrinks from 6 to 3 and the run abandons
  before `601`'s wave even opens. I ran this too; same discipline, reverted on the red.

The shipped formula is `budget = max(budget, _run_pool(allowance, wave_list, named))` —
`_run_pool` computes the "last named wave" value above, and the CALLER never lets it
shrink. This is not a bigger diff than either rejected alternative (`_run_pool` is ~10
lines of logic plus its own docstring; the call sites are one line each, `flow.py:1441`,
`:1454`, `:1512`) — it is the version that actually reconciles "never multiplies what a
run that adopts nothing would have had" with "never starves a bundle the operator typed",
which is what Scope (2) actually asks for, and it is what makes the FULL existing
`test_flow_adopt_split.py` suite (27 tests) pass unchanged alongside the five new tests
(see Verification below).

**(3) Stdout honesty** — `cli.py:644` `_report_single`. The single line for `iid` is
still printed first, unconditionally. `_results_rc` is now computed once, into `rc`
(previously returned directly); when `rc != 0`, every OTHER entry in `results` that is
NOT in the `ok` set is printed as its own `state<TAB>path` line (`cli.py:668-675`) —
mirroring the batch shape's per-line format, but keyed on the single-id contract's own
`state<TAB>path` (not `state<TAB>id`, which is the batch shape's, `cli.py:695` region).
Only failing entries are named, not every adopted child, so a run with an
`AWAITING_SIGNOFF` (ok) or `COMPLETE` (ok) child stays exactly as terse as before —
pinned by `test_single_id_stdout_prints_only_the_one_line_when_the_run_succeeds`.

## Alternative considered and rejected: "one summary line" instead of extra `state<TAB>path` lines

The brief offers this as an explicit alternative ("or a one-line summary of what made the
rc non-zero"). I chose the per-entry `state<TAB>path` lines because the SAME contract
(`state<TAB>path`, one bundle per line) already exists for exactly this purpose in the
batch shape (`cli.py:695` region, `_report_batch`) — reusing it costs one `for` loop
(7 lines) and no new format to document or parse; a prose summary line would be a SECOND,
undocumented shape a machine reader would have to learn on top of the one contract the
brief itself calls out as authoritative ("the documented `state<TAB>path` machine
contract"). Given the brief names both as acceptable and the per-line shape is strictly
cheaper to specify/parse, I did not also build the summary-line variant to compare cost
concretely — there is no rejected diff to show, only the format decision above.

## Scope discipline

Not touched: `_adoptable`, `_reschedule`, `_report_held`, `_report_refused` (the core's
detect/validate/report internals — reused as-is, per Scope's explicit "out of scope").
`waves.compute_waves` / `partition_schedulable` — untouched, called only through the
existing `_reschedule` wrapper. `flow_batch` — untouched; it never called
`_drive_and_act` with `adopt_seeds`, and the new keyword defaults to `None` so its
behaviour is unchanged (confirmed by the passing `test_flow_slice.py` / `test_overflow.py`
suites, see below). `docs/07-crosscutting.md` / `planner.md.jinja` — the brief's Scope
lists only `cli._flow`'s pre-run path, the pool arithmetic and `_report_single` as the
touched surface; I left the prose docs alone rather than expand blast radius into files
the brief does not name (a Plan-level call, not mine to second-guess without a citation).

## Verification — the three refutation questions

**(a) Genuine red?** Yes. I reverted `template/src/pdca_harness/{cli,flow}.py` to
`063203a` (`git stash push` of just those two files) and re-ran
`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery -v`
with the new test file present: 4 of 5 tests fail (`test_recovery_adopts_…`,
`test_mid_run_and_recovery_shapes_agree_…`, `test_the_run_wide_pool_is_resized_…`,
`test_single_id_stdout_names_the_adopted_bundle_…`), each on the SAME assertion the
post-fix run passes (`601`/`810`/`602` left `PLANNED` instead of `COMPLETE`; the extra
stdout line absent). The 5th (`test_single_id_stdout_prints_only_the_one_line_…`) is a
no-regression pin for the ALREADY-passing clean-run case, not one of the four red→green
criteria — it stays green in both legs by design. I then `git stash pop`ped the
production files back and re-ran: all 5 green. `patch.diff` applies cleanly to the base
commit with the production files stashed out (`git apply --check`, confirmed clean).

**(b) Production path?** Yes — every test drives `cli._flow` (`cli.py:558`), the real
CLI entry point, which calls the real `flow.flow_ids` → `flow._drive_and_act` →
`flow._adopt_split_children` chain. Only the six LEAVES are stubbed (the project's own
offline-suite convention, `_stub_config`, mirroring `test_flow_slice.py:33`); the split
itself is materialised by the PRODUCTION `split.accept` (`split.py:525`) via `_split_now`,
never hand-built JSON. The one test-only substitution — patching
`flow._adopt_split_children` to a no-op for ONE leg of two tests — exists to construct a
fixture (an "old run that never adopted"), not to bypass the code under test: the SECOND
`_cli` call in each of those tests runs against the real, unpatched function, which is
what every assertion in this bundle is actually about.

**(c) Fixture includes the fault?** Yes. The starvation test reproduces the EXACT
adversary scenario the brief cites — `500` splits into `601`, `810` briefed
`Depends on: 500` + `Conflicts with: 601`, `--max-passes 2`, `601` costing two passes —
and asserts `810` reaches `COMPLETE` (pre-fix: `PLANNED`, rc 1, exactly as v3's adversary
reproduced it). The recovery tests build the "already terminal, children stranded"
disk state via the production split path, not a hand-crafted fixture that excludes the
failure mode (the no-op `_adopt_split_children` patch simulates "an earlier run", not
"a run that can't fail" — the SAME real function is what the recovery leg then exercises).

## Full-suite check (beyond the four falsifiability legs)

`cd template && PYTHONPATH=src python3 -m unittest discover -s tests -p "test_*.py"` —
1665 tests, `OK (skipped=2)`, post-fix. Includes the full `test_flow_adopt_split.py` (27
tests, all pass unchanged — see the budget-formula rejection notes above for the two
variants that broke two of these), `test_flow_entrypoint_parity.py`,
`test_flow_inhibit.py`, `test_flow_slice.py`, `test_overflow.py` (137 tests together,
all green) and every other suite in the tree.

## Formatter / commit hooks

No `.pre-commit-config.yaml`, `pyproject.toml`, `ruff.toml` or `.flake8` exists anywhere
in the target tree (checked: `find . -iname "pyproject.toml" -o -iname
".pre-commit-config.yaml" -o -iname "ruff.toml" -o -iname ".flake8"` — no results).
`CONTRIBUTING.md`'s only stated engineering discipline is "keep the offline suite green:
`cd template && PYTHONPATH=src python3 -m unittest discover -s tests`" — satisfied above.
Line lengths in both edited files were checked against the file's OWN existing wrap
convention (`awk` length check over the diff's added lines only): every added line is
≤99 chars, matching the pre-existing body of both files (which already run up to 99
chars elsewhere, e.g. `flow.py:1732`, `cli.py:180`) — no reformatting needed.
