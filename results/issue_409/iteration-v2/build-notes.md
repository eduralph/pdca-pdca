# Build notes — issue 409 / autoiterate-budgets-defer-ledger (iteration 2)

Target: `eduralph/pdca-harness @ main`, worktree base `9405658`. Every `path:line` below is
on the patched worktree (base + `patch.diff`) unless marked "base".

## What this iteration does

The sign-off asked for two gaps in the retirement code to be closed and everything else
kept as it was. So `patch.diff` is iteration 1's patch plus exactly these changes (a diff of
the two patches shows nothing else, apart from `index` lines and hunk offsets):

1. **§6 item 7 (code review) — the length floor now bounds containment.** One production
   change, in `_same_finding`.
2. **§6 item 5 (adversary) — the "more than one fuzzy hit fails closed" rule now has a
   test.** No production change: the rule was already right, it just wasn't pinned.
3. A one-paragraph accuracy fix to the `RetiresOnlyWhatTheHumanTicked` class docstring.

Items 3, 4 and 6 of the sign-off were marked out of scope and are untouched.

Inputs: `brief.md` with its iteration-1 carry-forward. Because the carry-forward says to keep
everything else as it was, I also read `iteration-v1/patch.diff` (applied unchanged as the
starting point; it applied cleanly to `9405658`) and `iteration-v1/build-notes.md`. I did not
read the iteration-1 SUMMARY, reviews or gate logs; the carry-forward quotes items 5 and 7.

### 1. The floor bounds containment (`autoiterate.py`)

- `template/src/pdca_harness/autoiterate.py:132-138` — `_same_finding` now returns True for
  an exact (normalised) match first, then returns False when the shorter string is under
  `_MATCH_FLOOR` (20) characters, and only then tries containment (`a in b or b in a`) and
  the shared-opening rule. In iteration 1 that was one line (iteration 1's `:126`, the one
  the carry-forward cites), `if a == b or a in b or b in a: return True`, so a ticked row
  like `retry loop` retired any ledger entry that contained it.
- Why an early return and not the literal "`min(len) >= _MATCH_FLOOR and (a in b or b in
  a)`": they behave the same. The shared-opening rule already needed `shared >= max(20, …)`,
  and `shared` can never exceed the shorter length, so for a shorter string under 20 that
  rule was already always False. The early return changes containment only, and states the
  floor once for both rules. `:144` reuses `shorter` instead of recomputing it.
- The exact-match check stays before the floor, so a short entry still matches itself.
  (`retire_cleared` settles exact matches before calling `_same_finding` anyway: `:319` for
  protection, `:325` for ticks.)
- Comment `:94-98` and docstring `:123-127` updated. The old floor comment at `:100` ("so
  short rows can't match") was false for containment; it is true now.
- Test: `template/tests/test_autoiterate.py:1014`
  `test_a_short_row_matches_only_exactly`. A ledger entry E whose own row was deleted, and a
  single ticked row that is a short substring of E, at three positions: prefix `T5 Judgment`
  (11 chars), middle `retry loop swallows` (19 chars, one under the floor), suffix `the last
  one` (12 chars). Each must leave E in the ledger. A fourth subtest covers the other
  direction: a short ENTRY (`C1 Spec — vague`, 15 chars) inside a long ticked row. Two
  controls: a short entry still retires on its exact tick, and a full-length annotated tick
  (`E (fixed in round 2)`) still retires E. The controls show the test is not green just
  because fuzzy retirement stopped working.

### 2. Two fuzzy hits retire neither (test only)

- The rule lives at `autoiterate.py:327` (`if len(hits) == 1 and hits[0] not in
  protected`), unchanged from iteration 1.
- Test: `test_autoiterate.py:999` `test_a_tick_matching_two_entries_retires_neither` — the
  exact shape the sign-off named. Ledger `[P, R]` (near-twins that `_same_finding` can't tell
  apart). P's row is deleted; R's row is edited to `R (fixed by the rebuild)` and ticked.
  Preconditions assert the edit `_same_finding`-matches both entries and is an exact match
  for neither, so the fuzzy tier is what runs. Expected: both entries stay. Control: with
  only R in the ledger, the same tick retires R.

### 3. Class docstring (`test_autoiterate.py:910-913`)

It said every test in the class fails against both #335 wrong shapes (exact-only protection
and symmetric-fuzzy protection). I ran the class under both shapes (swapped into
`retire_cleared` in memory): exact-only fails the #335 repro, the matcher-drift test and the
near-twins test; symmetric-fuzzy fails only the first two; the other five (including my two)
pass under both. So the claim was already untrue for four tests in iteration 1. The
docstring now names the two tests that target both shapes and says each other test pins one
further rule, named in the test.

## The floor also changes protection — please weigh this at sign-off

`_same_finding` is the one relation used both to match a tick and to decide which entries a
still-open row protects (`autoiterate.py:321`, `:326`). That was the brief's requirement
(clause 3) and the sign-off put the floor inside `_same_finding`, so the floor applies to
both sides. I ran both shapes below through the real `retire_cleared`, with the new relation
and with iteration 1's (floor removed from containment, in memory):

| shape | iteration 1 | iteration 2 |
|---|---|---|
| 1. A short fresh open row `- [ ] C1 Spec`, plus an exact tick of ledger entry `C1 Spec — the brief never says which config file wins` | entry kept (the short row, owning no entry verbatim, shielded every entry containing `c1 spec`, so the human's exact tick was ignored and the entry came back unticked at the next assembly) | entry retired (the exact tick counts) |
| 2. E's own row trimmed to `retry loop swallows` (19 chars) and left open, plus a ticked near-twin of E (`…the last ones`) | E kept (the trimmed row protected it) | E retired (the trimmed row is under the floor, so it protects nothing; the near-twin tick is the only fuzzy hit) |

Shape 1 is a fix: before, a short unrelated open row could stop a ticked entry from
clearing. Shape 2 is a narrow loosening: it needs the human to cut an entry's own row down
to a fragment under 20 characters, leave it open, AND tick a different row that
fuzzy-matches only that entry.

The alternative is to floor containment on the tick side only. Sketch (3 changed lines,
plus a docstring note):

```diff
-def _same_finding(a: str, b: str) -> bool:
+def _same_finding(a: str, b: str, *, protecting: bool = False) -> bool:
 …
-    if shorter < _MATCH_FLOOR:
+    if shorter < _MATCH_FLOOR and not (protecting and (a in b or b in a)):
 …
-                         [i for i, t in enumerate(ledger) if _same_finding(t, o)])
+                         [i for i, t in enumerate(ledger) if _same_finding(t, o, protecting=True)])
```

I did not do it. It keeps shape 1's ignored tick, and it splits the relation in two, which
the brief rules out ("protects ledger entries using the same `_same_finding` relation the
tick match uses") and which is the root of #335. If you would rather keep shape 2 protected,
that sketch is the change.

## Refute-your-own-test (forced)

**(a) Genuine red? YES.**

- The C4 gate, run through the project's own runner: `PDCA_BUNDLE=results/issue_409
  PDCA_WORKTREE=<worktree> timeout 900 ./engine/scripts/run-verify.sh` →
  `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0. Run twice with the
  same counts: once mid-way, and once on the final `patch.diff` (after the last,
  docstring-only, test edit).
  - green leg: `test_autoiterate` Ran 87, OK; `test_size_signal` Ran 56, OK.
  - red leg (production hunks reverted, tests kept): `test_autoiterate` Ran 87, FAILED
    (failures=21, errors=20); no `unittest.loader._FailedTest`, so the module loaded and
    the tests ran. `test_size_signal` OK on both legs, as the brief expects (fixture
    adaptations only; `test_the_tag_is_the_mechanism` is not a red leg).
  - Iteration 1's red leg was failures=21, errors=14. The 6 extra errors are my two tests:
    on base `main` they hit `AttributeError: module 'pdca_harness.autoiterate' has no
    attribute '_same_finding'` / `'_MATCH_FLOOR'` (1 error + 5 in the short-row test's
    subtests and tail). They reach new symbols as module attributes, per the brief.
  - After the gate, `git diff HEAD | cmp - patch.diff` → identical (the gate restored the
    tree).
- Against the base revert alone the new tests only prove "the feature is missing". The
  sharper red for each of this iteration's two items:
  - **Item 7:** `test_a_short_row_matches_only_exactly` run against iteration 1's
    production code (before my `_same_finding` edit) → all 4 subtests FAIL on the real
    assertion, e.g. `[] != ['T5 Judgment — the retry loop swallows …']` and
    `[] != ['C1 Spec — vague']`. With the fix: OK.
  - **Item 5:** its rule was already in the code, so the test passes against iteration 1 by
    design; the gap was the missing test. I mutated `autoiterate.py:327` in memory (the
    mutated function exec'd into the real module, no file touched) and ran the class:
    - "retire the first hit" → the new test FAILS: `['…in the renderer'] != ['…in the
      parser', '…in the renderer']` — P, which nobody ticked, is dropped;
    - "retire every hit" → FAILS: `[] != [P, R]`;
    - under both mutations the 6 retirement tests from iteration 1 stay green, which
      reproduces the adversary's finding that nothing pinned this rule before.
  - Floor mutations (same in-memory method), each turning the short-row test red through a
    different leg: floor removed from containment (iteration 1's shape) → 4 subtests red;
    floor on the ticked row only → the short-entry subtest red; floor on the ledger entry
    only → the 3 short-tick subtests red; floor lowered to 10 → all 4 red (3 through the
    `assertLess(len(short), _MATCH_FLOOR)` precondition, which is there so that lowering
    the floor fails loudly, and the short-entry subtest on the real assertion).

**(b) Production path? YES.** Both tests call the production `autoiterate.retire_cleared` on
real files: a ledger JSON in the production `{"items": [...]}` shape and a SUMMARY.md with a
real §6 heading, read through the production `signoff.open_needs_human` and
`signoff.cleared_needs_human`. Direct `_same_finding` calls appear only as preconditions.
The mutations replaced the real functions inside the imported module, so the tests ran
against them, not against a copy.

**(c) Fixture includes the fault? YES.** Item 5's fixture is the exact failing shape the
sign-off named (ledger `[P, R]` near-twins, P's row gone, R's row edited and ticked), with
preconditions proving the tick really hits both entries and is not exact. Item 7's fixture is
the code review's shape (a short ticked row that is a substring of a deleted entry) at
three positions, including a 19-character one right under the floor, plus the reverse
direction; preconditions prove each fragment really is a substring and really is under
`_MATCH_FLOOR`.

## Other verification

- Both changed test modules, directly: `test_autoiterate` + `test_size_signal` → Ran 143, OK.
- T3, the project's suite runner: `PDCA_WORKTREE=<worktree> timeout 2400
  ./engine/scripts/run-suite.sh` → `PDCA-EVIDENCE: root suite OK, driver suite OK`, rc 0.
  Root suite (copier render + update-compat) Ran 24, OK; offline driver suite Ran 2121, OK
  (skipped=2) — iteration 1's 2119 plus the two new tests. This ran before the final
  docstring-only edit to the test class; the final C4 run re-ran `test_autoiterate` after
  it (87, OK).
- T2, the project's docs runner: `./engine/scripts/run-docs-check.sh` →
  `PDCA-EVIDENCE: docs lint clean, site render + link audit clean`, rc 0. No docs changed
  in this iteration; run anyway. I pointed `TMPDIR` at the worktree's `.cache/` so the
  gate's scratch render stayed inside the worktree.
- All touched Python byte-compiles; no added line is over 100 characters.
- `_same_finding` and `_MATCH_FLOOR` are used only inside `autoiterate.py` (grep of the
  worktree), so the floor change cannot reach any other caller.

## Commit-readiness

Unchanged from iteration 1, re-checked: the target has no pre-commit config, no active git
hooks, and no formatter or linter config (no ruff / flake8 / black / isort settings). CI runs
the docs lint, the render check, and the linked-issue check (`.github/workflows/`).
CONTRIBUTING asks for `git commit -s` (DCO sign-off), one logical change per commit, and
both suites green. Use a `feat:` prefix.

## Carried unchanged from iteration 1 (summary; full rationale in `iteration-v1/build-notes.md`)

- **Defer, don't veto:** `eligible()` `autoiterate.py:147` is "≥ 1 IMPL and no size-backstop
  HUMAN item" (base veto at base `autoiterate.py:73-74` removed). Ledger
  `deferred-findings.json` (`:76`): `deferred()` `:206` (absent → `[]`, unreadable →
  `DeferredLedgerUnreadable` `:191`), `defer()` `:249`, atomic `_write_ledger` `:239`,
  `write_decision()` `:357` (guard kept; ledger written before the budget is spent),
  `rationale()` `:336` (names the IMPL findings, counts the deferred ones without quoting
  them — the #294 property).
- `state.CYCLE_EVIDENCE_ONLY` gains the ledger (`state.py:174`); not in `DOWNSTREAM_OF_BRIEF`.
- `assemble.assemble_summary` merges the ledger into §6 (`assemble.py:361`, helper `:429`,
  exact dedup only); the #324 comment at `assemble.py:307-312` restated.
- `flow._apply_decision` puts an unreadable ledger into §6 before the C6 check
  (`flow.py:177`, `:216`); `_maybe_auto_iterate` messages and stop-rule comment
  (`flow.py:340-367`).
- Retirement: `retire_cleared` `autoiterate.py:274` with the exact-first two-tier
  `protected` set (`:317-321`) and the tick guard `hits[0] not in protected` (`:327`); tick
  reader `signoff.cleared_needs_human` (`signoff.py:123`, `whole_on_missing=False`); open-row
  reader `signoff.open_needs_human` unchanged (lenient). Wired in both iterate branches,
  between the carry-forward and the archive (`driver.py:135`, `:141`, helper `:317`).
- `--auto-iterate` help `cli.py:180`; docs consolidated in `docs/07-crosscutting.md`
  (auto-iterate section), `docs/05-check.md` points to it; `template/pdca.toml.jinja:53-73`
  and `:289`; `README.md` feature bullet; `size_signal.py` module docstring.

## Decisions carried from iteration 1 that are still open for the human

1. **No guard against a deleted ledger.** If a leaf deletes `deferred-findings.json`, the
   deferred findings are gone silently — the same exposure `auto-iterate.json` already has.
   A marker file would close it (~15 lines). Left out as unasked scope.
2. **Behaviour change:** beside a real IMPL defect, an external dependency, an unverifiable
   gate, a missing review, an unmarked advisory, or an unregistered dependency no longer
   halts the round; each is deferred to the handover §6. The size backstop (2 rounds by
   default) and the hard cap still bound the loop.
3. **A ticked unreadable-ledger row is honoured** (the human's tick clears it, as for any
   other §6 row).
4. **Two docs-only edits outside the brief's file list:** `README.md:161-167` and the
   `size_signal.py:41-44` docstring, both of which stated the old veto rule.

## Tracker notes for publish

The PR should close #409 and #335 (`Closes #409`, `Closes #335` in the body). Note on #332
that item 1 (`soft_auto_iters`) was dropped at Plan, not done, so #332 can close without it.

## Housekeeping

Gate logs from this iteration's local runs are in the worktree's git-ignored `.cache/`
(`c4-v2.log`, `c4-v2-final.log`, `t3-v2.log`, `t2-v2.log`); they are not part of
`patch.diff`. The mutation and shape checks ran in memory (mutated functions exec'd into the
imported module, temp bundles from the test class's own `tempfile` setup, removed in its
`tearDown`), each under `timeout`; no source file was edited for them. The bundle carries a copy of
the named test at `template/tests/test_autoiterate.py`, identical to the one in the patch.
No missing external dependency to declare.
