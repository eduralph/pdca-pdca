# Build notes — issue 477 / size-signal-discount-human-class-rounds (iteration 2)

Target: eduralph/pdca-harness @ main, built on the folded wave base in `$PDCA_WORKTREE`
(`00dc958 pdca-integrate: issue_409`, on top of `9405658`). Line numbers below are on that
tree with `patch.diff` applied. All production changes are in
`template/src/pdca_harness/size_signal.py`; the test is
`template/tests/test_size_signal.py` (copy in this bundle at the same path).

## What the carry-forward asked, and what changed

Sign-off said: keep the design, fix the implementation so it keeps its own fail-safe.

1. **Malformed gate-row results (reviewer C3 FAIL).** Iteration 1 only rejected the literal
   `fail`, so a gating row with a missing / `null` / unknown `result` was ignored and a
   deferred-T4 finding discounted the round.
   Fix: `size_signal.py:216-219`. Every gating row must carry a result from
   `_NOT_A_VERDICT = ("pass", "deferred", "unverifiable")` (`:158`), or be a `fail` with a
   truthy `flaky`. Anything else counts the round. This also covers `none` on a gating row
   (only a non-gating judgment cell ever carries `none`: `gates.py:879-887`) and non-string
   values.
   I also made `_archived_gate_rows` (`:232-251`) reject a record whose rows don't all
   carry a bool `gating` flag (`:248-249`). `gates._row` always writes one
   (`gates.py:827-831`, `bool(...)` at `gates.py:506`), and rows have carried `gating`
   since the first commit. Without this, a `fail` row missing its `gating` key would be
   read as non-gating and skipped by the check above: the same hole one field over.
   The obvious alternative, "treat a non-bool flag as gating", is unsafe the other way:
   a malformed `unverifiable` row would then count as an environment driver and
   *discount* the round. Rejecting the record counts the round in both directions.

2. **Element keyed too loosely (code-review §6 item).** Iteration 1 put an element in the
   deferred set if ANY of its rows was `deferred`, so a deferred row could shelter a
   failing sibling of the same element.
   Fix: new `_deferred_elements` (`size_signal.py:254-279`). An element counts as deferred
   only if it has a `deferred` row and every one of its rows, gating or not, is settled:
   `_SETTLED = ("pass", "deferred", "none")` (`:162`) with no `flaky` mark (`:271`). A
   `fail` (flaky or not), `unverifiable`, malformed result, or a `flaky`-marked `pass`
   keeps the element live. I added the flaky `pass` myself: that row failed before it
   passed, so the finding may be about it. A row whose `element` is unreadable (not a
   string) could be any element's sibling, so if it isn't settled, nothing is deferred
   (`:272-274`).

3. **Optional: primary-review `- NEEDS-HUMAN [impl] — T4 …` bullet.** Done. `_review_findings`
   returns `None` (counts the round) if any primary-review item carries the `[impl]` tag
   (`size_signal.py:330-331`). See "The `[impl]` read" below for why it's done this way.

4. **Optional: `_review_drove_the_iterate` is test-only.** Kept and documented
   (`size_signal.py:336-347`). Reason under "Alternatives".

Everything else is iteration 1's design, unchanged in intent:

- `iteration_rounds` docstring names the #477 discount next to #436 (`:131-140`).
- `_environment_attributed` (`:167-229`) is one rule, "every recorded driver is
  non-slice", with the brief's Design (a)-(d) as inline-commented returns (`:219`, `:222`,
  `:225`, `:228`, `:229`). I kept the name, because `iteration_rounds` (`:152`) and the
  #446 tests refer to it, and the docstring says the name is historical.
- `_element_of` (`:282-290`) uses `assemble._ELEMENT_RE` (`assemble.py:64`), as the brief
  asks.
- `_review_findings` (`:293-333`) reads the primary review through
  `assemble._items_from_artifact(text, allow_standing=True)` (`assemble.py:280-304`), as
  the old `_review_drove_the_iterate` did.
- `_advisory_drove_the_iterate` (`:350-372`) reads `check-advisory-*.md` the way
  `collect_needs_human` does (`assemble.py:326-330`, no `allow_standing`). It charges on
  an IMPL item, a `leaf_status` placeholder, or an unreadable file. These files are
  archived per round by `state.DOWNSTREAM_GLOBS` (`state.py:155`).

`template/pdca.toml.jinja` is untouched. Its `[driver.size_signal]` comment (`:285-307`)
doesn't describe which rounds are discounted, so the brief's condition for editing it is
not met. `docs/07-crosscutting.md:483-490` only says "how many rounds this brief has
already spent", so no doc goes stale.

## The `[impl]` read

`_items_from_artifact` strips the tag (`assemble._classify_finding`, `assemble.py:269-271`),
and a table row on a gate element is IMPL without a tag (`assemble.py:274-276`). So no
item's `kind` can tell `- NEEDS-HUMAN [impl] — T4 …` apart from the T4 verdict row. The
tag only survives in the raw item text, before classification. The line reads it from
`assemble._needs_human`, which `_items_from_artifact` maps over one-to-one
(`assemble.py:299-300`), using assemble's own `_IMPL_MARKER_RE` (`assemble.py:68`). It
doesn't re-derive a pattern or a classification.

The brief says to read the review through `_items_from_artifact` because a second parser
let a real objection pass as the standing row (#294). That failure was a second read
*granting an exemption*. This read can only count a round, never discount one, so it
can't repeat that failure. Classification still goes only through `_items_from_artifact`,
so when #408 changes it, this rule follows.

Rejected alternatives, with cost:
- Key on `kind`: can't work, for the reason above.
- Unroll `_items_from_artifact` here (call `_needs_human` + `_classify_finding` per item
  and keep the raw text): about the same line count, but this module would stop following
  #408's changes to `_items_from_artifact`, and the brief's ordering note depends on that.
- Add a "tagged" field to `assemble.NeedsHumanItem`: changes `assemble.py`, which the
  brief puts out of scope.

## Tests

All appended to `RoundsAreAttributedToTheSliceNotTheEnvironment` in
`template/tests/test_size_signal.py`.

- Fixtures: `_archive` gains `advisory=` (`:576-587`); `_two_round_bundle` gains
  `v1_advisory=` (`:589-598`). Both default to the old behaviour. New helpers:
  `T4_FINDING` (`:719`, the canonical `| T4 Contribution | NEEDS-HUMAN | … |` Item cell the
  reviewer prompt mandates, `leaves.py:2741-2745`), `IMPL_ADVISORY` / `PLAIN_ADVISORY`
  (`:721-722`), `_t4` (`:724`), `_without` (`:731`), `_deferred_round` (`:734`).
- Clause 1: `:744` (deferred T4 + T4/V review → `(1, 0)`), `:751` (same, through `measure` /
  `oversize_reasons`), `:758` (non-gating deferred row still discounts), `:764` (Item cell
  with no leading id → `(2, 0)`).
- Clause 2: `:773` subtests (plain gating fail, T3 / C5 / T5 findings, FAIL cell, advisory
  `[impl]`, advisory placeholder, placeholder review, missing review, missing and malformed
  `check-gates.json`); `:815` V-only beside a deferred row → `(2, 0)` (the decided Open
  question); `:822` plain advisory bullet on the new path → still `(1, 0)`.
- Clause 3: `:828` #446 round + advisory `[impl]` → `(2, 0)`; `:836` #446 round + plain
  advisory bullet → still `(1, 0)`.
- **New this iteration:**
  - `:843` malformed gating result: missing, `null`, unknown string (`skipped`), `none` on a
    gating row, non-string (`["pass"]`), each beside a deferred-T4 finding AND on the #446
    environment path → `(2, 0)`. The list value also pins the tuple-not-set choice
    (`:163-164`); a set would raise `TypeError` out of Check.
  - `:866` `gating` flag missing / `null` / a string → `(2, 0)`.
  - `:880` a deferred T4 row beside a live T4 sibling: non-gating `fail`, non-gating
    `unverifiable`, gating `fail` flagged flaky, gating `pass` flagged flaky, non-gating
    `null` result, non-gating missing result, and a failing row with no `element` →
    `(2, 0)`.
  - `:904` the complement: a passing T4 sibling leaves T4 deferred → `(1, 0)`.
  - `:909` primary-review `[impl]`-tagged T4 bullet → `(2, 0)`; the same bullet untagged →
    `(1, 0)`.
- Clause 4: every pre-existing test in the file passes unchanged (70 tests in the module,
  OK), including the #446 class and `test_the_calibrator_uses_THIS_definition` (`:529`).

## Red → green, through the project's runners

C4 gate, `PDCA_BUNDLE=results/issue_477 PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`
(run from the pdca-pdca root):

```
== C4 green leg: … template/tests/test_size_signal.py
Ran 70 tests … OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 70 tests … FAILED (failures=12)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

Red against base (12): clause 1 (`:744`, `:751`, `:758`), `:822`, clause 3 `:828`, `:904`,
`:909` (untagged half), and the 5 environment-path subtests of `:843`. That last group
shows **the #446 code on main has the same malformed-row hole**: a `null`-result gating
row beside an `unverifiable` row is discounted on main today. The rest of the new tests
are guards ("still counted") and pass on base by construction, since base never
discounts a deferred round.

**Red against iteration 1** (this shows the new tests target the carry-forward, not just
base). I put iteration 1's production hunks (`iteration-v1/patch.diff`) under the final
tests and ran the same gate script; its green leg reported:

```
Ran 70 tests … FAILED (failures=20)
PDCA-EVIDENCE: C4 FAIL — bundle test red WITH the fix applied
```

The 20: all 7 live-sibling cases (`:880`), all 10 malformed-result cases (`:843`, both
paths), `gating` missing and `null` (`:866`), and the `[impl]` bullet (`:909`). The
`gating: "false"` case passes under iteration 1 because that string is truthy, so the row
was already read as a gating fail. It's kept as a guard. Afterwards the worktree was
restored and checked byte-for-byte against `patch.diff` (`git diff | cmp`).

T3 gate, `./engine/scripts/run-suite.sh`: root suite 24 tests OK; driver suite 2149 tests
OK (2 skipped). That includes `tests/test_attempt_harvest.py:593,684`, which still call
`_review_drove_the_iterate`.

**Real archives.** In a read-only check, I ran base and patched `_environment_attributed`
over all 89 archived rounds in pdca-pdca `results/`. 0 rows fall outside the writer's
shape (non-bool `gating`, unknown `result`, non-string `element`), 0 rounds were
discounted by either version, and no bundle's `(rounds, replans)` changes. The stricter
checks don't affect real records, and the deferred path is defensive, as the brief's
measurement (0 of 39) says.

## Refuting my own test

- **(a) Genuine red?** Yes, at two levels. With all production hunks reverted to base,
  `run-verify.sh`'s red leg failed 12 times (e.g. the clause-1 bundle read `(2, 0)` and the
  clause-3 bundle `(1, 0)`, the brief's Falsifiability). With iteration 1's production
  code, the same suite failed 20 times, exactly on the carry-forward items, each
  `(1, 0) != (2, 0)`. The guard tests that pass on base are named above and pass on base
  by construction.
- **(b) Production path?** Yes. Every new test calls `size_signal.iteration_rounds` (or
  `measure`, which calls it). That is the function the Check backstop
  (`size_signal.measure`, `:411`) and `scripts/size-calibrate` use. No mocks: review and
  advisory text go through the real `assemble._items_from_artifact` / `_needs_human` /
  `leaf_status`.
- **(c) Fixture includes the fault?** Yes. The fixtures write real archive files
  (`iteration-v<N>/check-gates.json`, `check-review.md`, `check-advisory-adversary.md`) in
  the shapes the writers produce: rows in `gates._row` shape with `result: deferred` and
  `element: T4`; the review as the mandated verdict table with the canonical
  `T4 Contribution` Item cell; placeholders built from `assemble.LEAF_STATUS_INFRA`,
  `REVIEW_UNAVAILABLE_FINDING` and `ADVISORY_UNAVAILABLE_FINDING`. The faulty element is
  in each fixture: the malformed row, the failing sibling, the element-less failing row,
  the tagged bullet.

## Alternatives ruled out

- **Remove `_review_drove_the_iterate` and point `test_attempt_harvest.py` at
  `_review_findings`.** Cost: -13 lines in `size_signal.py`, ~4 lines changed in
  `tests/test_attempt_harvest.py` (`:589-594`, `:684`). But it adds a second test file to
  the patch, outside the brief's named test file, and `run-verify.sh` runs every changed
  test file in both legs. On the red leg those two calls would hit `AttributeError`, a red
  unrelated to the defect. Documenting the wrapper (`:341-345`, why it's kept and that it
  is off the rounds path) was the carry-forward's other permitted option.
- **Validate `element` on every row (reject the record if any row lacks one).** Rows have
  carried `element` only since `67ab4ea`, and it matters only for the deferred lookup.
  Rejecting the whole record would also cancel #446 discounts for any older archive. The
  narrower rule (`:272-274`: an unreadable element on an unsettled row defers nothing)
  closes the hole at 2 lines without touching #446.
- **Charge on any primary-review IMPL item, mirroring the advisory path.** This would charge
  every T4 verdict row (T4 is a gate element, so it's IMPL), which cancels the feature.
- **Rename `_environment_attributed`** to match its wider meaning: rejected in a fix
  iteration to keep the diff readable against the reviewed iteration 1. The docstring
  says the name is historical.

## Behaviour changes the human should know about

- Malformed gating rows now count the round **on the #446 path too** (5 subtests red on
  base). This is the safe direction and is what the carry-forward asked for ("validate
  every gating row"). No real archive is affected (scan above).
- Advisory `[impl]` findings now charge #446 rounds (clause 3; the brief's Open question).
- A `flaky`-marked `pass` on the deferred element keeps it live. This goes slightly beyond
  the carry-forward's list (fail / unverifiable / malformed) and is the safe direction.

## Commit-readiness

The target has no formatter or commit-hook setup: no `.pre-commit-config.yaml`, no
`core.hooksPath`, no installed `.git/hooks`, no ruff/black/flake8 config. CI
(`.github/workflows/render-check.yml`, `docs-check.yml`) renders the template and lints
docs, and this patch touches no docs. `git diff --check` is clean. All new lines are
≤ 96 characters; the only longer line in `size_signal.py` is the existing `:36`.

## Housekeeping (for the human)

I wrote one stray file outside the allowed roots: `/tmp/.unused-477-verify.log`, a copy
of one `run-verify.sh` run's output, saved before I switched to piping output. It is not
part of the patch. I did not delete it, per the no-cleanup rule. The worktree has no
untracked files.

No external dependency beyond the brief's (none) was needed.
