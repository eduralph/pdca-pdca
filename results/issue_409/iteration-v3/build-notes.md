# Build notes — issue 409 / autoiterate-budgets-defer-ledger (iteration 3)

Target: `eduralph/pdca-harness @ main`, worktree base `9405658`. Every `path:line` below is on
the patched worktree (base + `patch.diff`) unless marked "iteration 2" or "base".

## What this iteration does

The sign-off said the design is right and asked for three implementation defects to be fixed.
`patch.diff` is iteration 2's patch (applied unchanged as the starting point; it applied cleanly
to `9405658`) plus the changes below and nothing else. The infra-row deferral question the
human left open is untouched: which rows get deferred has not changed.

Inputs: `brief.md` with both carry-forward blocks. Because the carry-forward points at it, I
also read `iteration-v2/` (patch.diff, build-notes.md, the adversary, code-review and review
files). I did not read `iteration-v1/`.

Size of this iteration on top of iteration 2 (lines in `diff` between the two versions of each
file): `autoiterate.py` 73, `assemble.py` 35, `flow.py` 31, `cli.py` 4; `test_autoiterate.py`
116 added, 1 removed. Nothing else changed.

### 1. `_same_finding` compares two rows past a label they share (sign-off item 1)

- `template/src/pdca_harness/autoiterate.py:155-181` — `_same_finding` now calls
  `_past_shared_labels` (`:170`) after the exact-match check. Every test after that (the
  floor `:172`, containment, the shared opening, the ratio `:181`) reads only what follows a
  label both rows open with.
- `autoiterate.py:132` `_split_label`: a normalised row that opens with a known label,
  followed by a separator or by nothing, splits into `(label, rest)`.
  `autoiterate.py:144` `_past_shared_labels`: strips labels while BOTH rows open with the
  same one. It loops because labels nest (a placeholder row puts its leaf-status label in
  front of whatever the artifact said, which can start with a 5/5/1 label).
- `autoiterate.py:128` `_LABELS` (normalised, longest first), `:129` `_SEPARATORS`
  (`" —–:-"`: the ` — ` assemble renders, or a typed `:`, `-` or `–`).
- `template/src/pdca_harness/assemble.py:161-168` — new public `FINDING_LABELS`: every label
  assemble renders in front of a finding as `<label> — <text>`. That is the canonical 5/5/1
  Item labels (from `gates.canonical_elements()`, the same source `_CANONICAL_LABELS` uses)
  and the leaf-status labels (`_LEAF_STATUS_LABEL`). Kept in assemble, next to the code that
  renders them (`assemble.py:270` for placeholder rows, `:649` for table rows), so a new
  label source added there is visible where the list lives.
- Comment `autoiterate.py:88-105` rewritten. The old one claimed the label was "a small
  fraction of a full §6 row", which is exactly the assumption the adversary broke.
- `_MATCH_RATIO` and `_MATCH_FLOOR` keep their values (0.6, 20).

**Why the floor and containment are measured past the label too, not only the shared
opening.** The carry-forward named the shared opening. Containment had the same hole:
`C5 Causal adequacy — symptom only` sits inside `C5 Causal adequacy — symptom only in the
parser; the renderer is fine`, and with the label counted the shorter row is 33 characters,
over the floor, so a tick on either retired the other. The mutation run below ("floor+ratio
measured on full rows") shows what measuring only the opening past the label would leave: 5
failing tests, including that pair.

**One step past the carry-forward's wording: leaf-status labels.** The carry-forward said "a
common canonical `Item —` prefix". Placeholder rows open with a leaf-status label that does
the same thing, only longer (47 to 119 characters today). Checked on iteration 2's code:
`_same_finding` returned True for the transient-infra placeholders of two DIFFERENT leaves
(`adversary` vs `code-review`). They share a 137-character opening, and the ratio needed 130
of the 217-character shorter row. Same fail-open class as the adversary's V1/V2 case. It is
included because it is the same defect in the same function. It changes only how these rows
MATCH at retirement; nothing about which rows are deferred. To drop it: remove
`+ tuple(_LEAF_STATUS_LABEL.values())` from `assemble.py:167-168` and delete
`test_two_placeholder_rows_are_two_findings`.

Tests, all in `template/tests/test_autoiterate.py`, class `RetiresOnlyWhatTheHumanTicked`:

- `:1068` `test_two_findings_on_one_element_are_two_findings` — the adversary's two pairs (C5,
  one short; V), plus a typed-colon C5 pair (`C5 causal adequacy: ` is exactly 20 characters,
  the floor) and a short finding inside a longer one. For each pair: `_same_finding` is
  False; with one entry's own row deleted, a tick on the other retires nothing, in both
  directions; ticked exactly beside the other left open, the entry retires (the "other
  direction" the adversary described). A precondition asserts that, counting the label, the
  pair's common opening clears the floor, so each fixture really is a shape the old relation
  misread. Control: the same finding annotated still retires.
- `:1101` `test_a_shared_opening_must_be_most_of_the_shorter_finding` — pins the ratio. Two
  findings share a 26-character opening (over the floor, under 0.6 × 56). Preconditions
  assert both facts and that neither contains the other, so only the ratio can refuse the
  pair. Run with no label and with `C5 Causal adequacy — ` in front. Control: an edit in the
  middle (`last attempt` → `final attempt`, 60 of 72 shared) retires.
- `:1123` `test_two_placeholder_rows_are_two_findings` — the two leaves' rows, produced by the
  production path (`leaves._advisory_unavailable` then `assemble._items_from_artifact`), and
  a nested pair (a report that quotes a status marker without the completion trailer, with
  two C5 rows, so each row is `<leaf-status label> — C5 Causal adequacy — …`). Control: the
  same placeholder row annotated still retires.

### 2. One C6 read for both accept paths (sign-off item 2)

- `template/src/pdca_harness/flow.py:214-233` — `accept_blockers(d)` replaces
  `_hold_unreadable_ledger`. Same hold (an unreadable ledger → an open §6 row via
  `signoff.ensure_needs_human_item`), then it returns `signoff.open_needs_human(...)`.
- `flow.py:176` — `_apply_decision` takes its C6 check from it.
- `template/src/pdca_harness/cli.py:1448-1450` — `cli._signoff --accept` takes its C6 check
  from `flow.accept_blockers(d)` instead of its own `signoff.open_needs_human(summary)`.
- `flow.py:368` — the one comment that named the old helper.
- The stderr line lost its `flow:` prefix, since the CLI prints it too. No test reads it.

Only two code paths record an accept: `flow.py:184` and `cli.py:1465` (every
`signoff.record(` call; the third, `cleanup.py:154`, records `discontinue`). The other
`open_needs_human` callers (`cli.py:554`, `:697`, `:983`, `queue.py:43`) only display counts.

Why a function that returns the open rows, rather than calling the old hold helper from the
CLI (a 2-line change): with the hold inside the C6 read, a path cannot do one without the
other, which is how the CLI came to skip it. The cost over that 2-line change is small:
`flow.py` +53/-16 against iteration 2's +49/-15, `cli.py` +4/-2 against +1/-1. Why in `flow`
and not `signoff.py`: the helper was already in `flow`, `cli` already imports `flow` and calls
its public functions (`flow.flow_batch` `cli.py:638`, `flow.flow_ids` `:655`), so the helper
is public too (no underscore). `signoff.py` would need a function-local
`from . import autoiterate` (autoiterate imports signoff at module top) plus bundle-level
logic that module does not have today.

Test: `test_autoiterate.py:815` `test_an_unreadable_ledger_blocks_accept_on_the_cli_path_too`
— the adversary's repro. A clean bundle, auto-iterate off, a ledger with a non-string entry
written after assembly, then the real `cli._signoff(cfg, Namespace(accept=True, …))`: exit 1,
state stays `AWAITING_SIGNOFF`, the row is in §6, stderr says "cannot accept". Then the human
ticks it: exit 0, `COMPLETE`, the row appears once. `no_publish=True` keeps the accept leg
from publishing.

### 3. Stale comments (sign-off item 3)

- The three named in `assemble.py`: iteration 2's `:246-248` → `:257-262` (a placeholder never
  causes a round; beside implementation work it is deferred), `:278-279` → `:292-295` (a gate
  that could not run: a rebuild cannot supply the mechanic; beside implementation work it is
  deferred), `:302-303` → `:317-320` (plan-advisory findings).
- Two more in `assemble.py` that described the same old rule: `:34-37` (the STANDING comment
  said "The ONLY thing it no longer does is veto a rebuild"; now it says what still sets the
  row apart, which is that it is never deferred) and `:233-238` (`_classify_finding`: "it
  merely declines to veto one").
- One in the test file: `test_autoiterate.py:1322-1325` ("still halt the bundle").
- Checked and left alone: `size_signal.py:91-105` and `:369-371` (they describe the size item,
  which still stops the loop); `template/tests/test_leaf_status.py:11`, `:164` and
  `template/tests/test_attempt_harvest.py:559` (outside the brief's file list, and still
  accurate: each describes a placeholder on its own, which never causes a round and halts).

## Refute-your-own-test (forced)

**(a) Genuine red? YES.**

- The C4 gate, through the project's own runner:
  `PDCA_BUNDLE=results/issue_409 PDCA_WORKTREE=<worktree> timeout 900 ./engine/scripts/run-verify.sh`
  → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`, rc 0. Run twice, the second
  time on the final `patch.diff`; same counts both times.
  - green leg: `test_autoiterate` Ran 91, OK; `test_size_signal` Ran 56, OK.
  - red leg (production hunks reverted, tests kept): `test_autoiterate` Ran 91, FAILED
    (failures=22, errors=29); no `unittest.loader._FailedTest`, so the module loaded and the
    tests ran. `test_size_signal` OK on both legs, as the brief expects.
  - Iteration 2's red leg was failures=21, errors=20. The difference is my 4 tests: the CLI
    test fails on base (`0 != 1`, the accept goes through), and the 3 matcher tests error
    on base with `AttributeError` for `_MATCH_FLOOR` / `_MATCH_RATIO` / `retire_cleared`,
    which base does not have. They reach new symbols as module attributes, per the brief.
  - After each gate run, `git diff | cmp - patch.diff` → identical.
- Against base the new tests only prove "the feature is missing". The sharper red: I put
  iteration 2's `_same_finding` and `_signoff` (parsed from saved copies of iteration 2's
  files) back into the loaded modules in memory and ran the 4 new tests. All 4 fail, 8
  failing subtests, 0 errors, each on its real assertion: `True is not false` for every pair
  in the two matcher tests, the labelled leg of the ratio test retiring the entry, and
  `0 != 1 : the CLI accepted over an unreadable ledger`. The unlabelled leg of the ratio test
  passes there, correctly: iteration 2 had the ratio, just no test for it.
- Mutations, each put into the loaded module in memory, whole `test_autoiterate` module
  (91 tests) run each time. Every one is caught, all by failed assertions, 0 errors:

  | mutation | failing tests |
  |---|---|
  | none (baseline) | 0 |
  | ratio removed (`return shared >= _MATCH_FLOOR`, the adversary's survivor) | ratio test, both legs |
  | ratio raised to 0.9 | 8 (ratio test control, near-twin preconditions, placeholder preconditions) |
  | ratio lowered to 0.4 | ratio test (its "the ratio does" precondition) |
  | no label stripping (iteration 2's relation) | 7 (every new matcher subtest) |
  | floor and ratio measured on the full rows, compared past the labels | 5 (#335 repro, near-twin tests, "short finding inside a longer one") |
  | one shared label stripped, no loop | placeholder test, "nested labels" |
  | separator must be ` — ` | "a typed colon" |
  | 5/5/1 labels only, no leaf-status labels | placeholder test, both pairs |
  | retire the first fuzzy hit | `test_a_tick_matching_two_entries_retires_neither` |
  | floor removed from containment | 5 (the short-row test's 4 subtests, "short finding inside a longer one") |
  | CLI back to its own `open_needs_human` check | the new CLI test |
  | `_apply_decision` back to its own `open_needs_human` check | `test_an_unreadable_ledger_blocks_accept_on_the_shared_decision_path` |

**(b) Production path? YES.** The matcher tests call the production
`autoiterate.retire_cleared` on real files (the ledger in the production `{"items": [...]}`
shape, a SUMMARY with a real §6 heading, read through the production `signoff` readers).
Direct `_same_finding` calls are assertions beside those, not replacements. The placeholder
rows are produced by the production `leaves._advisory_unavailable` and
`assemble._items_from_artifact`. The CLI test calls the production `cli._signoff`, which
records into a SUMMARY assembled by the production `assemble_summary` from real gate output.
The mutations and the iteration-2 functions were put into the imported modules themselves, so
the tests ran against them, not against a copy.

**(c) Fixture includes the fault? YES.** Each matcher fixture is a shape the old relation
misread, and preconditions prove it: counting the label, every pair's common opening clears
the floor (for the placeholder pairs, the ratio too), and the ratio pair's opening clears the
floor but not the ratio, with no containment either way. The pairs include the adversary's
two exact examples. The CLI fixture is the adversary's repro: the ledger breaks AFTER
assembly, so the SUMMARY on disk does not carry the row and only the accept path can add it.

## Other verification

- T3, the project's suite runner: `PDCA_WORKTREE=<worktree> timeout 2400
  ./engine/scripts/run-suite.sh` → `PDCA-EVIDENCE: root suite OK, driver suite OK`, rc 0. Root
  suite (copier render + update-compat) Ran 24, OK; offline driver suite Ran 2125, OK
  (skipped=2), which is iteration 2's 2121 plus my 4. Run on the final tree.
- T2, the project's docs runner: `./engine/scripts/run-docs-check.sh` → `PDCA-EVIDENCE: docs
  lint clean, site render + link audit clean`, rc 0 (22 pages). No docs changed in this
  iteration. I pointed `TMPDIR` at the worktree's `.cache/tmp` so its scratch render stayed in
  the worktree. For T3 I left `TMPDIR` alone: the root suite copies the whole worktree into a
  temp dir, so a temp dir inside the worktree would make it copy into itself.
- The docs still match: `docs/07-crosscutting.md` says an accept is refused over an unreadable
  ledger, which is now true on both paths. They do not describe the matching rule.
- `git diff --check` clean; touched Python byte-compiles. One added line is over 100
  characters: the `--auto-iterate` help string at `cli.py:180`, carried from iteration 1,
  which matches the other long `add_argument` lines in that block.

## Commit-readiness

Re-checked: the target has no pre-commit config, no active git hooks, and no formatter or
linter config. CI runs `docs-check.yml`, `docs.yml`, `render-check.yml` and
`require-linked-issue.yml`. `CONTRIBUTING.md:7-19` requires a DCO sign-off (`git commit -s`);
`:26` asks for the offline suite to be green (it is, above). Recent commit subjects mix
`fix(…)`/`test(…)` prefixes and plain sentences.

## Decisions for the human

1. **Leaf-status labels are included** in the label rule (one step past the carry-forward's
   wording; reasons and the 2-line way to drop it are in section 1).
2. **A short finding now matches only exactly.** When what follows the shared label is under
   20 characters, even an annotated tick no longer retires it. Checked on both versions:
   ledger `[C5 Causal adequacy — symptom only]`, tick `… symptom only (fixed)` → iteration 2
   retired it; now it stays, comes back verbatim at the next assembly, and one tick of that
   row retires it. This fails closed, and it follows from measuring the floor on the finding,
   which the "short finding inside a longer one" case needs.
3. **Protection now also ignores a shared label.** An unrelated finding under the same label,
   left open, no longer shields an entry the human ticked exactly. This is the adversary's
   "other direction", and the brief requires both sides to use the same relation.
4. **Separators:** a row counts as opening with a label when the label is followed by ` — `, a
   typed `:`, `-` or `–`, or the end of the row. Tested for ` — ` and `:`.
5. Carried open from iteration 2, unchanged: no guard against a deleted ledger; the behaviour
   change that HUMAN findings beside implementation work defer; a ticked unreadable-ledger row
   is honoured; `README.md` and the `size_signal.py` docstring edited outside the brief's file
   list; and the question the human left open (whether re-derived infra rows should be
   deferred at all).

## Rejected alternatives

- **Strip the label for the shared-opening rule only** (the literal wording): leaves the same
  hole in containment. See section 1 and the "floor and ratio measured on the full rows"
  mutation.
- **No label list; strip up to the last ` — ` inside the common opening**: finding texts
  contain ` — ` themselves. It would cut into the finding and break a real middle edit.
  Example: `C5 Causal adequacy — the retry loop swallows the error — see flow.py:12` vs the same
  row ending `flow.py:14 (fixed)` leaves `see flow.py:12` (14 characters), under the floor, so
  no match.
- **Only the first ` — `**: fails for the V label, which contains ` — ` itself.
- **Defect 2 by calling the old hold helper from the CLI** and **the helper in `signoff.py`**:
  see section 2.

## Tracker notes for publish

The PR should close #409 and #335 (`Closes #409`, `Closes #335` in the body). Note on #332
that item 1 (`soft_auto_iters`) was dropped at Plan, not done, so #332 can close without it.

## Housekeeping

Local logs are in the worktree's git-ignored `.cache/` (`c4-v3.log`, `c4-v3-final.log`,
`t3-v3.log`, `t3-v3-final.log`, `t2-v3.log`), with copies of iteration 2's `autoiterate.py`,
`flow.py`, `cli.py` and `assemble.py` in `.cache/iter2/` for the comparison runs. None of it is
in `patch.diff`. The mutation and comparison runs happened in memory, each under `timeout`;
no source file was edited for them. The bundle carries a copy of the named test at
`template/tests/test_autoiterate.py`, identical to the one in the patch. No missing external
dependency to declare.
