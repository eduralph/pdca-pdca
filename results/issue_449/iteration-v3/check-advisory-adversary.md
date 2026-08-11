# Adversarial review — issue 449 (flow adopts split children mid-run)

Attempted refutation of the C4 red→green, of the fix's edge behaviour, and of the
reviewer's verdict. Everything below is grounded on the target source at
`$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, HEAD `aaa797a` + the
uncommitted patch) and on runs I performed in throwaway copies.

## What I could not refute

- **The evidence is real, and it is the production path.** Patched tree:
  `tests.test_flow_adopt_split` 12/12 green. Red leg rebuilt by restoring **only** the
  three production files to HEAD (`template/src/pdca_harness/{flow,config,leaves}.py`)
  and keeping the new test: 9 of 12 fail with substantive assertion errors
  (`'PLANNED' != 'COMPLETE'`, `None != 'COMPLETE'`), not `ImportError` — so the red is a
  real red, not a PDCA-UNVERIFIABLE. Adoption is driven only through `flow.flow_ids` /
  `flow.flow`, and the split itself is produced by the production `split.accept`
  (`template/tests/test_flow_adopt_split.py:191`), not simulated. The 3 tests green on
  both legs are declared no-regression guards, which is what they should be.
- **Mutation-tested the four load-bearing claims; all are caught.** Narrowing
  `flow.py:770` `except Exception` → `except OSError` ⇒ 1 error; `flow.py:1163`
  `min(allowance, budget - spent)` → `allowance` ⇒ 1 failure; hardcoding the announced
  index to `k + 1` at `flow.py:945` ⇒ 3 failures; disabling the run-budget break at
  `flow.py:1129` ⇒ 1 failure. The iteration-1 ruling's two defects are genuinely fixed,
  not merely asserted.
- **The T3 red is not this patch's.** With `PDCA_VERIFY_BASE` set, `tests/test_verify_base.py`
  fails 11/19 **both** on the patched tree and on the reverted-production tree — identical
  counts. Otherwise the whole offline driver suite is `Ran 1634 tests … OK (skipped=2)` on
  the patched tree. The carry-forward's "pre-existing isolation fault, out of scope" is
  correct; I could not turn it into a refutation.
- **Attacked and failed to break:** a named dependent of the splitting parent
  (`flow 500 700`, `700 Depends on 500` → waves `[500][601,700][602]`, all COMPLETE);
  a *live* recursive split (an adopted child that splits while this run drives it →
  `[500][601][602,701][702]`, all COMPLETE); the CSV entry point (`flow_batch` adopts);
  naming parent + child together (`flow 500 601` → 601 skipped as already in the drive
  set, 602 adopted); a lineage cycle (parent listed as its own grandchild — terminates on
  `examined`); a `../../etc` child id (rejected by `flow.py:811`); `children` not a list
  (degrades to "no readable children record"). Entry-point parity on the Entry-B path
  holds: on byte-identical disk at `max_passes` 2/3/4/5, `flow.flow` and `flow.flow_ids`
  reach identical end states for 500/601/602.

## Findings

- **NEEDS-HUMAN [impl] — the run-budget exhaustion message is wrong on the single-id path.**
  `template/src/pdca_harness/flow.py:1133-1136` prints `budget` and `k`, but on the
  `flow.flow` path `budget` is the *remainder* handed to the adoption tail
  (`run_budget=max(0, max_iters - spent)`, `flow.py:450`) and `k` indexes the adoption
  sub-run's own `wave_list`. Reproduced: Entry-B split, 500 pre-briefed,
  `flow.flow(cfg, "500", max_iters=2)` emits
  `flow: the run's pass budget is spent (0 pass(es) over 0 wave(s)); raise
  [driver].max_passes …` — the run in fact spent 2 passes over 1 wave, and "raise
  max_passes" attached to "0 pass(es)" is unactionable. At `max_iters=3` it reads
  "(1 pass(es) over 1 wave(s))" for a run that spent 3 over 2. `flow_ids` on the same disk
  prints the correct "(2 pass(es) over 1 wave(s))" / "(3 pass(es) over 2 wave(s))". No test
  asserts this message on the single-id path, so the divergence is invisible to the suite.
- **NEEDS-HUMAN [impl] — the adoption announcement numbers waves differently at the two
  entry points, on identical disk.** `flow.py:936` builds `wave_of` from the *local*
  `wave_list`, which on the `flow.flow` path does not contain the parent's own drive.
  Same disk, same budget: `flow.flow` logs `issue_500 split → adopted children issue_601
  into wave 0` / `issue_602 into wave 1`; `flow.flow_ids` logs `wave 1` / `wave 2`. The
  docs this patch adds assert the opposite — `docs/07-crosscutting.md:259-260`: "`pdca flow
  500` and `pdca flow 500 501` do the same thing to the same disk". The new test
  *enshrines* both numbering schemes (`template/tests/test_flow_adopt_split.py:244-245`
  vs `:260-261`), so it can never catch the inconsistency. Either offset the single-id
  announcement by the passes its own loop drove, or say plainly that the index is within
  the adopted schedule.
- **NEEDS-HUMAN — a recovery run's pass pool is sized as if it had one wave, so recovering
  by parent id buys strictly less budget than naming the children.**
  `template/src/pdca_harness/flow.py:1109`: `budget = allowance * max(1, len(wave_list))`.
  A run that names only an already-terminal split parent set out to drive **zero** waves,
  so `max(1, …)` hands the entire adopted subtree one wave's allowance. Reproduced: 500
  stranded on a split into 601 and 602 (`602 Depends on 601`); at `max_passes=1`,
  `flow_ids(["500"])` leaves 602 PLANNED, while `flow_ids(["601","602"])` on the same disk
  completes both. Scaled to the default 20, a stranded split whose children chain past 20
  total passes truncates where naming them does not. The iteration-1 ruling settled *that*
  the cap is run-wide; it did not settle how to size the pool for a run whose original
  schedule is empty — and neither `docs/07-crosscutting.md:319-325` nor
  `template/agents/planner.md.jinja:177-179` ("Re-running the **parent's** id works too")
  warns the operator that the parent-id route is the cheaper-budget route. This is a
  scope/fitness call, not a code slip.
- **NEEDS-HUMAN [impl] — a duplicate child id in the lineage record is adopted twice.**
  `flow.py:809-837` filters each id against `known` but never against the ids already
  taken from the *same* record, and `out.append(d)` at `:837` has no dedup. With
  `children: ["601","602","601"]` the run logs `issue_500 split → adopted children
  issue_601, issue_601 into wave 0` and `bundles += scheduled` (`:938`) pushes `issue_601`
  in twice, so `_sweep_quietly` (`:1255`) and any `_warn_abandoned` (`:1133`) process and
  name it twice. Reproduced by hand-editing the record — which is precisely the threat the
  function's own docstring claims to cover ("the record is a file an operator can
  hand-edit", `flow.py:787-790`). A `seen` set in the `for cid in ids` loop closes it.
- **NEEDS-HUMAN [impl] — the brief's motivating case is not covered for the single-id entry
  point.** `template/tests/test_flow_adopt_split.py:251` drives `flow.flow` with
  `replan_first=False`, i.e. a split at the *first* Plan beat — not Entry-B (`iterate-plan`
  at sign-off → re-plan → split), which the brief names as the whole motivation. The reason
  is mechanical: `_arm` stubs `leaves.run_signoff_batch`, which the single-id path never
  calls (it goes through `flow._signoff_and_apply` → `leaves.run_signoff`, `flow.py:260`),
  so an Entry-B stub silently does nothing there. I built that case by additionally stubbing
  `leaves.run_signoff` and the behaviour holds at budgets 2–5, so this is a coverage gap
  rather than a bug — but it is the gap over the exact path the two message defects above
  live on.

## On the verdict

- `check-gates.json` row **C4** ("red without the fix, green with it") is warranted — I
  reproduced both legs. Row **T3** is correctly non-gating and correctly attributed to
  pre-existing `PDCA_VERIFY_BASE` leakage; I verified the failure is identical without the
  patch.
- **NEEDS-HUMAN — T4 is asserted green but unverifiable from my inputs** (advisory,
  provisional per issue #236): `commit-msg.txt` and `pr-description.md` are not in the
  `{patch.diff, brief.md, check-gates.json}` set I was given, and the same provisionality
  was already raised in the iteration-2 carry-forward. I am not disputing the gate, only
  recording that I could not independently re-run it.
- One reviewer claim I would not have signed as written: the docs' "the two entry points
  agree … do the same thing to the same disk, on the same budget"
  (`docs/07-crosscutting.md:259-260`). End states do agree, and I verified that at four
  budgets — but the *run log* does not (wave numbering, budget-exhaustion message), and the
  budget agreement is between `flow` and `flow_ids` only, not between adopting a parent and
  naming its children.
