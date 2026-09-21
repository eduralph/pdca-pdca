# Build notes — #566, iteration 2

Target branch: `eduralph/pdca-harness` @ `pdca-integration/main`, tip `fe8208f`
("pdca-integrate: issue_565" — the sibling drive-claim child, stacked on `70ea12b`).
Every `path:line` below is on the worktree at that base **with this patch applied**.

## What this iteration changes, and nothing else

The carry-forward scoped this iterate to **finding 2 only**: the end-of-run stranded-child
report named finished children as unfinished work. The conditional-line half was accepted,
findings 1 and 3 were reviewed and accepted as-is.

So I started from the v1 patch applied verbatim to the worktree (`git apply` of
`iteration-v1/patch.diff`, clean) and made four edits on top. The file set is identical to
v1's — same seven files, no new ones:

| file | v1 | now |
|---|---|---|
| `docs/07-crosscutting.md` | ✓ | ✓ (wording) |
| `template/agents/planner.md.jinja` | ✓ | ✓ (wording) |
| `template/src/pdca_harness/cli.py` | ✓ | unchanged from v1 |
| `template/src/pdca_harness/drive_claim.py` | ✓ | unchanged from v1 |
| `template/src/pdca_harness/flow.py` | ✓ | ✓ (the fix) |
| `template/src/pdca_harness/leaves.py` | ✓ | ✓ (wording) |
| `template/tests/test_split_hint_live_run.py` | 8 tests | 11 tests |

### 1. The fix — `flow.py:1556-1560`

```python
if _split_marked(cd):
    ...
    to_examine.append(cd)
    continue
if state.state(cd) in _TERMINAL:      # ← new
    continue
stranded.append(cid)
```

Exactly what the carry-forward asked for, in exactly the order it asked for:

- **A terminal child is skipped.** `state.state(cd) in _TERMINAL` is the same predicate
  `_adoptable` uses to drop a child ("already terminal", `flow.py:1064-1076`) and the same
  one `_warn_abandoned` uses to decide what is in flight (`flow.py:770`). Not a new notion
  of "finished" — the existing one.
- **A split child is still walked THROUGH.** The `_split_marked` test stays **first**. A
  confirmed split parent *is* terminal by design, so a terminal-first order would cut the
  walk off above its own children — the "don't gate the whole walk on non-terminal" trap the
  human named. I verified that trap is now caught (see refutation (a) below); it was not
  caught by the tests as first written, which is why the third new test exists.

Docstring updated at `flow.py:1503-1512` and an inline note at `flow.py:1551-1553` /
`:1557-1559` so the ordering is not an accident a future edit can quietly undo.

### 2. The report line's preamble — `flow.py:1563-1568`

`"its children were not driven this run"` → `"this run did not drive all of its children"`.

Direct consequence of the fix, not scope creep: once the list holds only the in-flight
children, the old preamble asserted something untrue about the finished siblings it no
longer names ("its children were not driven" reads as *all* of them). The tail is
byte-unchanged (`— <ids> left in-flight; drive them with \`pdca flow <ids>\``), so the report
still has `_warn_abandoned`'s shape. Three test assertions follow it.

I considered leaving the string alone to keep the diff minimal. Concretely that saves 4
lines of test-string edit and 3 lines of comment — and buys back a sentence that says the
opposite of the finding I was sent here to fix. Not worth it.

### 3. The text agrees — brief (v)

Brief (v) requires the model-facing text and docs to describe what the report actually does.
v1's text said "every **un-driven** child", which after this fix is wrong: a child an earlier
run carried to COMPLETE was not driven by *this* run and is deliberately not named. Three
one-paragraph edits, all saying "still IN FLIGHT", and all naming the walk-through:

- `docs/07-crosscutting.md:353-361`
- `template/agents/planner.md.jinja:190-197`
- `template/src/pdca_harness/leaves.py:1127-1129` (the planner seed prompt)

### 4. Three new tests — `template/tests/test_split_hint_live_run.py`

All three are built from a shared fixture, `_drive_500_split_to_completion`
(`test_split_hint_live_run.py:458-480`): a real `cli._flow(["500"])` whose stand-in Plan leaf
accepts a split of 500 into 601/602, so the run adopts both and drives the whole brood to
COMPLETE. Afterwards 500 is a parent terminal-on-a-split whose children are **finished**.
No earlier test in this file builds that shape — which is precisely why the bug got through.

- `:482-498` **`…_is_silent_when_every_split_child_is_finished`** — the reviewer's probe,
  verbatim: `pdca flow 500 8` with COMPLETE children. 500 enters as an adoption seed
  (`flow.py:2030-2056`), its children are dropped as already terminal, and the run must end
  saying nothing about it. Brief (iii)'s "no such children → no line".
- `:531-546` **`…_walks_through_a_split_child_to_its_own_children`** — 601 is split mid-run
  (after the adoption pre-pass has already read 500), so at the end 500's brood is 601
  (split, close not driven yet) and 602 (COMPLETE). The report must name 801/802 —
  reachable only through 601 — and not 602.
- `:548-570` **`…_walks_through_a_child_terminal_on_a_split_of_its_own`** — the same, but
  601's own close is driven through (`flow._drive_wave`, the close fast path) so it is
  COMPLETE **and** split-marked at once. This is the one that pins the branch **order**.

One thing I learned building these and it is worth recording: `split.accept` archives the
parent's `patch.diff` / `check-gates.json` / `SUMMARY.md` (`split.py:942-952`), so a freshly
split bundle reads **BUILT**, not terminal. That is why the second test above does *not*
catch a terminal-first ordering and the third one does — I only found that out by running
the swap (below). `_split_marked` vs `_is_split_parent` exists for this same reason.

## Rejected alternatives

- **Gate the whole walk on non-terminal** (`if state.state(cd) in _TERMINAL: continue`
  before the `_split_marked` test). Two lines shorter than what I shipped. Rejected: it
  strands the grandchildren of every confirmed split, which the third new test now proves —
  with that order the run prints nothing at all where it should print
  `pdca flow 801 802`. The carry-forward warned about exactly this.
- **Filter at print time** (`stranded = [c for c in stranded if not terminal(c)]` after the
  loop). Same output, one line shorter. Rejected because it separates the decision from the
  walk: the next reader of the loop sees `stranded.append(cid)` with no terminal test beside
  the `driven` and `_split_marked` tests it belongs with, and `_adoptable` — the function
  this mirrors — makes both decisions in one place at `flow.py:1059-1076`.
- **Reword the whole report line** to drop "left in-flight". Rejected: brief (vi) keeps the
  existing report shapes byte-identical and the brief asks this one to keep
  `_warn_abandoned`'s shape (`flow.py:773-777`). Only the untrue clause changed.
- **Also fix findings 1 and 3.** Explicitly refused by the sign-off. Untouched: `flow_batch`
  still holds the sweep marker for the whole drive, and `Run.take` still retries 5 times.

## Refuting my own test

**(a) Genuine red?** Yes — and in three separate ways, each run through the project's own
runner or the runner's own invocation:

1. *Full C4 revert* (`./engine/scripts/run-verify.sh`, the registered gate): green leg
   `Ran 11 tests … OK`; red leg `Ran 11 tests … FAILED (failures=6, errors=1)` →
   `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
2. *Only my hunk reverted, back to the exact v1 code the reviewer rejected* — two of the
   three new tests fail, and the failure text is the reviewer's probe verbatim:
   ```
   AssertionError: 'did not drive all of its children' unexpectedly found in
   '… flow: issue_500 split; … 601, 602 left in-flight; drive them with `pdca flow 601 602`'
   ```
   and, for the walk test, `… — 602, 801, 802 left in-flight` (the finished 602 wrongly in
   the list). That is the binding proof: it is red against v1, not merely against the base.
3. *Branch-by-branch* (brief (vi)). Delete the terminal skip → 2 failures. Delete the
   `_split_marked` walk-through → 2 failures. Swap the two tests so terminal comes first →
   1 failure (`…_terminal_on_a_split_of_its_own`). Every branch that decides whether the
   report fires is pinned by deletion, and the order is pinned too.

**(b) Production path?** Yes. Every test drives `cli._flow` / `cli._split` — the real CLI
entry points — over a real stub-leaf `Config`; the only stand-ins are leaf callbacks
(`leaves.do_plan_batch`, `flow._build_all`) used as *timing hooks* to act mid-run, with the
real implementation still called through. `_warn_stranded_split_children` is never called
directly by any test; it is reached only from the tail of `_drive_and_act`
(`flow.py:1832`). The registered C5 row agrees: `PDCA-EVIDENCE: 1 added driver-suite
test(s) import the production package 'pdca_harness'`.

**(c) Fixture includes the fault?** Yes, and this is the specific thing v1 got wrong. The
fault is a **finished** child appearing in the report, so the fixture has to contain real
finished children — not children curated out. `_drive_500_split_to_completion` asserts
`state.COMPLETE` for 500, 601 **and** 602 before the run under test starts, and the
walk tests assert 801/802 are `PLANNED` and (third test) that 601 is `COMPLETE` with
`close-disposition == "split"` on disk. The COMPLETE siblings stay in the lineage record
the walk reads; nothing removes them. Under v1's code they are named, which is the red.

## Gates run here (all through the project's own runners)

| runner | result |
|---|---|
| `./engine/scripts/run-verify.sh` (C4) | `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it` |
| `./engine/scripts/run-suite.sh` (T3) | root suite `Ran 24 … OK`; driver suite `Ran 1966 … OK (skipped=2)` |
| `./engine/scripts/run-docs-check.sh` (T2) | `docs lint clean, site render + link audit clean` |
| `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` (C5) | added test imports the production package |

Brief (vi)'s "the whole `template/tests` suite stays green" holds: 1966 tests, 0 failures.

## Commit-readiness

The target repo has no `.pre-commit-config.yaml`, no `ruff`/`flake8`/`black` config and no
line-length rule (`flow.py` already carries a 102-char line, `cli.py` a 236-char one). Its
CI is `docs-check.yml` / `docs.yml` / `render-check.yml` / `require-linked-issue.yml`; the
two docs checkers are what T2 and the `host_ci` parity row run, and both are clean above.
`git diff --check` reports no whitespace errors and all five touched Python files compile.

No external dependency beyond the base toolchain was needed — stdlib Python and git only,
as the brief's `External dependencies: none` said. Nothing to declare.

## STOP discipline

Nothing pushed, no branch created, no PR. The patch lives in `patch.diff` and in the cycle
worktree only.
