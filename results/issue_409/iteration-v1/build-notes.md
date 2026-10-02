# Build notes — issue 409 / autoiterate-budgets-defer-ledger

Target: `eduralph/pdca-harness @ main` (worktree base `9405658`). All `path:line` below are
on the patched worktree unless marked "base".

## What changed, per success-criterion clause

### (2) Defer, don't veto — the core change

- `template/src/pdca_harness/autoiterate.py:136` `eligible()` is now
  `any(IMPL) and not any(HUMAN and size_signal.is_size_item(text))`. The base veto
  (`all(kind in (IMPL, STANDING))`, base `autoiterate.py:73-74`) is gone.
- Ledger: `DEFERRED_FILE = "deferred-findings.json"` (`autoiterate.py:76`), shape
  `{"items": [text, …]}`.
  - `deferred()` (`:195`) — absent file → `[]`; exists but not JSON / no `items` list /
    a non-string entry → raises `DeferredLedgerUnreadable` (`:180`). Fails closed on
    purpose (the tolerant reading loses findings in the accepting direction).
  - `defer()` (`:238`) — appends HUMAN texts only (not IMPL, not STANDING), deduplicated on
    whitespace-collapsed + casefolded text; writes only when something new was added;
    atomic write via temp sibling + `os.replace` (`_write_ledger`, `:228`).
  - `write_decision()` (`:346`) — keeps the refuse-if-ineligible guard; ledger is written
    FIRST, then `bump`, then the decision. An unreadable ledger raises before any budget is
    spent or decision written.
- `state.CYCLE_EVIDENCE_ONLY` gains the ledger (`state.py:174`), comment updated
  (`state.py:161-173`). Not in `DOWNSTREAM_OF_BRIEF`, so `_archive_iteration` leaves it.
  The existing `test_cycle_evidence.py` subtests (they iterate `CYCLE_EVIDENCE_ONLY`) now
  cover it automatically — evidence, never archived, survives a real archive.
- `assemble.assemble_summary` merges ledger entries into §6 after the fresh items
  (`assemble.py:361`, helper `_deferred_needs_human` `:429`): exact (normalised) dedup
  against the fresh texts, never fuzzy (a near-twin must not hide behind its neighbour).
  Unreadable ledger → one fixed row `autoiterate.UNREADABLE_LEDGER_ITEM` (`autoiterate.py:83`).
- `flow._apply_decision` — before the C6 check, on `accept`, `_hold_unreadable_ledger`
  (`flow.py:177`, def `:216`) adds the fixed row unticked via the new
  `signoff.ensure_needs_human_item` (`signoff.py:144`) if the ledger is unreadable, so C6
  blocks. Runs regardless of `cfg.auto_iterate` (the shared decision path). If the human
  has already ticked that row it is left alone — a tick is their clearance, same as every
  other §6 row. The `- (none — …)` placeholder is dropped when the row is added.
- `flow._maybe_auto_iterate` — docstring + the `:319-324` comment rewritten (now
  `flow.py:341-347`) to state the two-stop rule; `write_decision` wrapped
  (`flow.py:359-367`) so an unreadable ledger declines the round with a stderr line; the
  fire message now says how many findings are addressed and how many deferred.
- `rationale()` (`autoiterate.py:325`) names the IMPL findings (quoted) and the deferred
  ones by COUNT plus the file they are held in. It does not quote them: the rationale IS
  the §9 "Iteration delta", which `driver._carry_forward_into_brief` copies into the
  builder's brief, so quoting a HUMAN finding there would break the #294 property. That is
  how I read "names what was addressed AND what was deferred … and still carries only IMPL
  items into the carry-forward" — the two halves only fit together if "names what was
  deferred" means the fact and count, not the text.

### (3) #335 fold — retirement

- `autoiterate.retire_cleared(d, summary)` (`autoiterate.py:263`), `_same_finding`
  (`:115`, proportional-prefix relation ported from getwyrd/wyrd-pdca@e4fdf3b), and the
  exact-first two-tier `protected: set[int]` computed once before the tick loop; the tick
  guard is `hits[0] not in protected` as the brief specifies.
- Readers take opposite directions, as decided at Plan:
  - open rows: `signoff.open_needs_human` (`whole_on_missing=True`, unchanged);
  - ticks: new `signoff.cleared_needs_human` (`signoff.py:123`, `whole_on_missing=False`).
- Wiring: `driver._retire_cleared_deferrals` (`driver.py:317`) called between
  `_carry_forward_into_brief` and `_archive_iteration` in BOTH iterate branches
  (`driver.py:135`, `:141`). Best-effort (logs and continues) — a failure keeps the entry,
  which is the visible direction, never the lossy one.

### (4) #324 composition

- `eligible()` stops on the size item by kind (above). `assemble.py:307-312` and the
  `size_signal.py:41-44` module docstring updated — both stated the old "requires every
  item be IMPL or STANDING" rule.
- `test_size_signal.py:215` fixture: an ordinary HUMAN item now rides beside the size item,
  so the flow-level test shows the size item (by kind) is what declines and is named.
  `test_size_signal.py:240`: HUMAN-only now (an IMPL + ordinary-HUMAN set fires).
  `test_the_tag_is_the_mechanism` unchanged and passing.

### (1) Two stops, no new budget

- No config change at all (`config.py` untouched). `max_auto_iters` field/default/clamp and
  `auto-iterate.json` `{"count": n}` shape unchanged (`bump` untouched).
- Docs consolidated: `docs/07-crosscutting.md:429-490` (the auto-iterate section) now
  describes the defer rule, the ledger, retirement, and "Exactly two things stop the loop"
  (`:464`) — size backstop (default 2 rounds, below the cap, and why) + hard cap.
  `docs/05-check.md:405-410` and `:773-779` point to step 07 instead of restating.
  `template/pdca.toml.jinja:53-73` rewritten for the defer rule; it points to the size
  thresholds block instead of restating the number; `:289` "(which disqualifies
  auto-iterate)" → "(which stops auto-iterate)". The `[driver.size_signal]` `rounds`
  comment stays the one place in the toml that states the threshold.
- `cli.py:180` `--auto-iterate` help text.

## Tests (template/tests/test_autoiterate.py, plus test_size_signal.py fixtures)

New classes / tests (line numbers in the patched file):
- `DefersHumanFindings` (`:658`) — mixed set fires + defers (`:668`); HUMAN-only halts
  (`:673`); ext-dep / unmarked advisory / missing review beside a red gate defer
  (`:680`, `:696`); **loss-proof handover** (`:704`: round 1 raises C5, round 2's reviewer
  doesn't, handover §6 still shows C5 open and C6 blocks accept on that row alone);
  ledger is cycle evidence and never archived, pinned to `autoiterate.DEFERRED_FILE` vs
  `state.CYCLE_EVIDENCE_ONLY` / `DOWNSTREAM_OF_BRIEF` (`:737`); rationale (`:751`) and the
  #294 carry-forward property end to end (`:767`); unreadable ledger at assembly (`:779`),
  on the shared decision path with auto-iterate OFF (`:786`), and in auto-iterate (`:814`).
- `TwoStops` (`:829`) — no `soft_auto_iters` in `Config` or the toml template (`:851`, a
  guard, not a red leg); `[IMPL, HUMAN]` Checks fire to `count == max_auto_iters == 3` then
  "auto-iterate budget spent (3/3)" with `rounds = 0` (`:864`); default rounds → stops at
  2 with "not auto-iterating: size backstop" on stderr (`:878`).
- `RetiresOnlyWhatTheHumanTicked` (`:903`) — basic tick/absence (`:937`); (a) #335 repro +
  drain leg (`:944`); (b) matcher drift over five edit shapes (`:960`); (c) edited row
  protects both near-twins (`:988`); (d) no §6 heading retires nothing, with a control
  (`:997`); unreadable ledger never rewritten (`:1005`).
- `RetireAtTheIterate` (`:1014`) — driver wiring for iterate-do (`:1033`) and iterate-plan
  (`:1039`).
- `DecisionModule` — `eligible` table (`:1057`); **clause 4 discriminating test**
  (`:1065`); ledger written before the round, deduped across rounds (`:1083`); size set
  refused (`:1095`); unreadable vs absent (`:1104`).

Existing tests CHANGED because they asserted the veto this issue removes (none weakened —
each still pins the property it was written for, through the new observable):
- `TheStandingValidationRow` SV3/SV5/SV6/SV7/SV9/SV10 (`:235-348`): they asserted a HALT
  because STANDING was then the only non-IMPL kind that did not veto. Now both STANDING
  and HUMAN let the round fire, so what distinguishes them is the ledger: each test now
  asserts the exact ledger contents — the real objection is in it, the standing row is
  not. A misclassification as STANDING would leave the ledger without the objection and
  the test red. Two were renamed (`…_still_halts` → `…_is_deferred_not_dropped` /
  `…_is_still_a_real_objection`).
- `HaltsForTheHuman`: removed `test_one_judgment_item_disqualifies_the_whole_bundle` (its
  exact inversion is `DefersHumanFindings:668`); `test_declared_external_dependency_halts`,
  `test_unregistered_dependency_halts`, `test_missing_review_halts` now run with a passing
  gate (HUMAN-only, still halts, `:401`, `:407`, `:434`) and their mixed shapes moved to
  `DefersHumanFindings` asserting deferral.
- `DecisionModule.test_eligible_only_when_nonempty_and_all_impl` → `…_iff_there_is_
  implementation_work` (the `[IMPL, HUMAN] → False` line is the veto being removed).
- `_assert_halted` now also asserts no ledger was written on a halt.

## Refute-your-own-test (forced)

**(a) Genuine red? YES.** Ran the project's C4 gate, `./engine/scripts/run-verify.sh`
(PDCA_BUNDLE=results/issue_409, PDCA_WORKTREE=the worktree), which reverts only the
production hunks for the red leg and restores them after:
- green leg: `test_autoiterate` Ran 85, OK; `test_size_signal` Ran 56, OK.
- red leg: `test_autoiterate` Ran 85, **FAILED (failures=21, errors=14)**; no
  `unittest.loader._FailedTest` (the module imported fine — all new symbols are reached as
  `autoiterate.X` attributes, so the errors are AttributeErrors inside running tests, not a
  load failure); `test_size_signal` OK on both legs, as the brief expects (its changes are
  fixture adaptations and `test_the_tag_is_the_mechanism` is not a red leg).
- `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0; worktree afterwards
  byte-identical to `patch.diff` (`git diff | cmp`).
- Per-clause red legs confirmed in that output: clause 1 `TwoStops.test_mixed_checks_fire_
  until_the_hard_cap` + `…size_backstop_first_by_default`; clause 2 `eligible` table,
  the ledger/`CYCLE_EVIDENCE_ONLY` pin, handover, unreadable-ledger tests; clause 3 all of
  (a)–(d) and both wiring tests; clause 4 `test_the_size_item_stops_by_kind_…` (its first
  leg, `[IMPL, ordinary HUMAN] → True`).

Mutation checks beyond the plain revert (wrong variants swapped in memory, each named
test run individually):

| wrong variant | test | result |
|---|---|---|
| symmetric-fuzzy protection `any(_same_finding(e,o))` | (a) `:944` | RED |
| symmetric-fuzzy protection | (b) `:960` | RED |
| exact-only protection (the #335 bug) | (a), (b), (c) | RED ×3 |
| no protection (#168 prototype) | (a), (b), (c) | RED ×3 |
| edited row protects only its best match | (c) `:988` | RED |
| tick reader `whole_on_missing=True` | (d) `:997` | RED |
| naive `eligible = any(IMPL)` | clause 4 `:1065` | RED |

(c) and (d) stay green under symmetric-fuzzy, which is expected: (c) wants the over-
protection symmetric gives, and (d) tests the tick reader, not protection. The brief asks
only (a) and (b) to discriminate against symmetric-fuzzy.

**(b) Production path? YES.** The flow tests drive the real `flow._maybe_auto_iterate` →
`autoiterate.write_decision` → `flow._apply_decision` → `driver.run_issue` (real archive,
real stub builder, real gate commands `true`/`false`, real `assemble.assemble_summary`,
real `driver._size_backstop` measuring real `iteration-v*` archives). Only the reviewer
leaf is replaced (`mock.patch.object(leaves, "run_review", …)` writing a fixed review) —
the same pattern the existing `test_repeated_rounds_terminate_at_the_cap` uses, since the
review text IS the fixture input. Retirement tests call the production
`autoiterate.retire_cleared` on real files; wiring tests go through `driver.advance`.

**(c) Fixture includes the fault? YES.** The mixed fixture carries the exact production
shape the veto broke on: a C4 defect, a situational C5 judgment row, AND the reviewer's
standing Validation row (the row whose absence from fixtures hid #293). The loss-proof test
makes the later reviewer drop the C5 finding, so the only route to §6 is the ledger. The
#335 fixtures include the annotated-but-unticked row and the similar ticked new finding
(the exact failing pair), and the near-twin texts are asserted to be `_same_finding`
matches as a precondition so the tests can't pass vacuously. The size-backstop test runs
with the real default threshold (not a stub), and the hard-cap test switches only the
backstop off.

## Other verification run

- Full offline driver suite: `cd template && PYTHONPATH=src python3 -m unittest discover -s
  tests` → Ran 2119, OK (skipped=2).
- T3 `./engine/scripts/run-suite.sh`: root suite (copier render + update-compat + the
  suite run inside the rendered instance) Ran 24 OK; driver suite Ran 2119 OK.
- T2 docs: `docs/publishing/tools/lint_docs.py` OK; `render_site.py --check` link audit OK.
- `test_autoiterate` writes nothing to stdout (checked with `2>/dev/null | wc -l` → 0).
- One slip caught on the way: my first toml comment spelled `[driver.size_signal]`, and
  `test_size_signal.TheShippedExampleMatchesTheDefaults` splits the file on the first
  occurrence of that string — 10 failures. Reworded the comment; suite green.

## Commit-readiness

The target has no pre-commit config, no ruff/flake8/black config, and CI runs only the
docs lint, the render check, and the linked-issue check (`.github/workflows/`). Docs lint
passes; all touched Python compiles; new Python lines are ≤ 100 chars except the
`cli.py:180` argparse line, which follows that file's existing one-line-per-flag style.
Commit needs `git commit -s` (DCO) and a conventional prefix (`feat:`), per CONTRIBUTING.

## Decisions and things ruled out

1. **No absence guard for a deleted ledger.** The downstream #168 marks "a ledger was
   written" with a `ledger` key inside `auto-iterate.json`, so a later absent file reads as
   loss. The brief pins the budget file's `{"count": n}` shape, so I did not port that.
   Consequence: if a leaf deletes `deferred-findings.json`, the deferred findings are gone
   silently — the same exposure `auto-iterate.json` already has (deleting it resets the
   budget). A separate marker file would close it (~15 lines: write `.deferred-mark` after
   the first `_write_ledger`, and in `deferred()` raise when the mark exists and the ledger
   doesn't; plus adding the mark to `CYCLE_EVIDENCE_ONLY`). Left out as unasked scope;
   worth a follow-up issue if the human agrees.
2. **Merge in `assemble_summary`, not `collect_needs_human`.** As the brief says. Putting
   ledger entries into `collect_needs_human` would feed them back into `items`, so every
   later round's `rationale()` would count them as newly deferred and `defer()` would
   re-scan them — harmless (dedup) but it would misreport. Cost of the chosen place: §6 is
   now `collect_needs_human` + ledger, so that function's "single source" docstring is
   true for fresh findings only; the ledger is the second, documented source.
3. **Behaviour change the human should know about:** beside a real IMPL defect, an
   external dependency, an unverifiable gate, a missing review, an unmarked advisory, and
   an unregistered dependency no longer halt the round — they are deferred, per the
   brief's `eligible()` rule ("≥ 1 IMPL and no size item"). The loop is still bounded by
   the size backstop (2 rounds by default) and the cap. An unregistered dependency is also
   still caught before Do by `plan_policy` (#333), so such a round is held at PLANNED.
4. **A ticked unreadable-ledger row is honoured.** `_apply_decision` adds the row
   unticked, which blocks the first accept; a human who then ticks it has cleared it. The
   alternative (re-add unticked forever until the file is repaired) would make the only
   exit "edit the bundle by hand", which C6 does not require for any other row.
5. **Scope additions beyond the brief's file list, both docs-only fixes of statements this
   change makes false:** `README.md:161-167` (the feature bullet described the veto; also
   corrected its stale "doc 06" pointer to doc 07) and the `size_signal.py:41-44` module
   docstring. `size_signal.py` is #477's file; the edit is confined to those docstring
   lines, so a textual conflict with #477 is possible only if #477 rewrites that paragraph.
6. Not touched: `config.py`, `_classify_finding`, `autoiterate.DECISION`, prompts, `[impl]`
   tag, `_PROMOTABLE_ELEMENTS`, round counting — all out of scope per the brief.

## Tracker notes for publish

The PR should close #409 and #335 (`Closes #409`, `Closes #335` in the body). Note on #332
that item 1 (`soft_auto_iters`) was dropped at Plan, not done, so #332 can close without it.

## Housekeeping

Scratch output (verify/suite logs, rendered site) is in the untracked `.site-dDtw/` inside
the worktree; it is not part of `patch.diff`. The bundle also carries a copy of the named
test at `template/tests/test_autoiterate.py`, identical to the one in the patch.

No missing external dependency to declare: everything needed (python3, git, copier in the
instance venv, the docs tooling) was present.
