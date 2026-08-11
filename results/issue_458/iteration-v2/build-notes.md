# Build notes — #458 (iteration 2): split-child-remedy-and-hatch

**Target branch / base actually built on:** `eduralph/pdca-harness` — the #457-carrying
tree, i.e. `origin/fix/457-sizing-ignores-sibling-conflicts` = `b4c924d`, whose parent is
`origin/pdca-integration/main` = `824139d`. That branch is *exactly* the integration tip
plus prerequisite #457 (PR #483, still open). `origin/main` (`36300ee`) and
`origin/pdca-integration/main` have byte-identical trees (`git diff --stat` between them is
empty), so the only difference that matters is #457 itself.

> **Read this first — the gate base.** See §7. The bundle carries no `stack-base` marker,
> so the C4 gate will reset the lane worktree to `origin/main`, which does **not** carry
> #457. The patch *applies* there (`git apply --check` rc=0) but cannot *pass* there —
> `plan_policy` reads `est.sibling_conflicts`, a field #457 adds. It is declared as a
> NEEDS-HUMAN external dependency in §7 with a one-line remedy.

## 1. What the carry-forward said, and what I changed because of it

Iteration 1 was rejected for two things:

1. *"the patch re-derives the sibling-conflict count from lineage + brief instead of
   consuming the single sibling-conflict signal #457 exposes"* — it called
   `split.read_lineage` + `brief.conflicts_with` and intersected them itself.
2. *"the remedy decision at `plan_policy.py:134` bypasses the new branch at `:151`"* — the
   provenance branch was nested inside `elif before_do:` of the `splittable` fork, and on
   the #457-folded tree the sibling fixture stops being churn-oversized (the sibling
   conflicts are no longer scored), so it lands `churn=watch` / `patch=oversized`,
   `splittable is False`, and never reaches the branch at all.

Both are addressed at their cause, not guarded around:

* the predicate is now `est.sibling_conflicts` — #457's field, read off the same estimate
  the band came from (`plan_policy.py:189`). There is no second derivation anywhere in the
  patch; `split.read_lineage` is called only to *format* the ids for the sentence
  (`plan_policy.py:88-111`), and only after the count is already non-zero. The docstring at
  `plan_policy.py:88-104` states that division explicitly so it cannot quietly regress.
* the question is asked **before** the readout fork, as its own first branch of the
  if-chain (`plan_policy.py:181-197`), so `splittable` cannot route around it. The
  patch-only shape #457 leaves behind has its own test
  (`test_i_a_patch_only_child_reaches_the_same_branch`), which asserts
  `(churn_band, patch_band) == (watch, oversized)` before asserting the message — that is
  the exact stacked failure the reviewer reproduced, now pinned.

## 2. The change, file by file (citations against the worktree at the base above)

* `template/src/pdca_harness/plan_policy.py:54` — `split` added to the module imports (for
  the message's ids only; `sizing` already imports `split`, so no new edge in the graph).
* `template/src/pdca_harness/plan_policy.py:88-111` — `_split_child_provenance(d)`: formats
  `child N of a split of #X, depth D`. Total: a hand-edited record missing an edge yields
  `#?` / `depth ?`, never a raise. Deliberately **not** routed through
  `split._recorded_depth` (`split.py:405-421`): that helper's floor of `0` is the correct
  answer for arithmetic and the wrong *statement* to a human, since `depth 0` is what a
  bundle that was never split reads.
* `template/src/pdca_harness/plan_policy.py:129-145` — the docstring paragraphs stating the
  predicate (the count, never the presence of a lineage record) and why the hatch is not
  gated on the sizer.
* `template/src/pdca_harness/plan_policy.py:181-196` — `extra = ""` plus the new first
  branch; `:212` folds `extra` into the detail line, so the message that claims
  "driven by inherited/sibling fields" carries the count it rests on
  (`; N sibling conflict(s) not counted`). #457 excludes those from the score, so
  `est.reasons` would otherwise be silent about them, or report a *smaller* organic count —
  the exact contradiction the brief's failure 1 describes.
* `template/src/pdca_harness/plan_policy.py:203-208` — comment only: the `before_do=False`
  branch's wording is untouched, and now says why provenance does not fork it (criterion iv).
* `template/src/pdca_harness/leaves.py:524-553` — `_split_provenance_note(d)`, one sentence,
  `""` when the bundle has no `parent` edge. Injected verbatim into both prompts at
  `leaves.py:610` (`_plan_prompt`) and `leaves.py:1294` (`_split_prompt`); no existing
  instruction text is reworded.
* `docs/07-crosscutting.md:50-52` — the Entry-A flowchart gains the sibling question ahead
  of `splittable?` (a new node `A4b` + remedy `A8`; the existing `A5`/`A6`/`A7` lines are
  untouched). `:61` — Entry B's node is labelled to say it deliberately has no such fork.
  `:92-105` — the prose in the cited `splittable` paragraph, quoting the message verbatim.
  Nothing outside `### The process` is touched (`### The estimate` is child-2's, `### The
  split` is child-4's).

## 3. Why the predicate is the count and not "is the model band oversized"

The brief calls the previous hatch dead config, and it is: `[leaves.sizer]` ships
`mode = "stub"`, and `leaves._stub_sizer` (`leaves.py:1252-1258` after this patch) returns
`{"band": "ok"}` unconditionally, so `est.model_band == OVERSIZED` is unreachable offline.
I did not add it back even as a *secondary* escape, for that reason plus one more: an
escape only a paid leaf can open is not an escape an operator can use, and every extra
branch here is another way for the two attempts' failure modes to reappear.

The hatch that exists instead is the brief's own evidence, and it is reachable with the
shipped stub sizer in one edit: remove the stale sibling entries from `Conflicts with:`
(what happens naturally once the siblings land) and the ordinary `consider `pdca split`
first` returns. `test_iii_the_ordinary_remedy_returns_under_the_shipped_stub_sizer` drives
exactly that transition through `plan_policy.evaluate` — the entry `driver.advance` calls —
asserting on the way that the real `_stub_sizer` wrote `sizing.json` (`band: "ok"`,
`stub: true`) and that `model_band` is not `oversized`, i.e. nothing in the green leg is
being held up by a model verdict. No mock anywhere in the module.

## 4. Alternatives considered and rejected

* **Keep the branch inside the `splittable` fork and only fix the predicate.** Rejected on
  evidence, not taste: on this base the sibling fixture scores 6 (difficulty 3 + brief
  bytes 3; the two sibling conflicts no longer score), so `churn=watch`,
  `patch=oversized`, `splittable is False` — the branch is unreachable for the very shape
  #457 produces. Measured, not argued: `test_i_a_patch_only_child_reaches_the_same_branch`
  asserts those two bands, and pre-fix that bundle prints `oversized — expect a large patch
  …` with nothing about provenance (captured in the red leg of the C4 log).
* **Suppress on lineage presence and re-enable on `model_band`** (iteration 1's shape).
  Rejected: both of the brief's named failures. Cost of the alternative I chose instead:
  the diff is the same size (one branch either way, ±0 lines) — this is not a cost
  trade-off, it is a correctness one.
* **Append the provenance to the existing remedy rather than replacing it.** Rejected:
  criterion (i) requires that `consider `pdca split` first` **not** be emitted for that
  child, and a line carrying both sentences tells the human to do the thing the rest of the
  line argues against.
* **Gate the prompt note on the sibling-conflict count too.** Rejected: the note is
  *context for a model about to read the brief*, not a verdict about this brief's score —
  "your `Conflicts with` may be inherited; check" is true for every child, and gating it on
  the count would hide it from precisely the child whose organic conflicts the planner is
  about to weigh. Criterion (v) says "when the bundle carries lineage", which is what it
  does (`leaves.py:541-544`). The asymmetry is documented in the helper's docstring so the
  next reader does not "fix" one to match the other.
* **A narrower predicate for the MIXED case** (some sibling conflicts *and* enough organic
  ones to be oversized on their own). Considered and rejected: after #457 the score already
  excludes the sibling ids, so "would it still be oversized without them" is not a question
  the estimate can answer differently — there is no second number to compare against, and
  inventing one would be the re-derivation this iteration exists to remove. A non-zero count
  is also the splitter's own statement that the previous split separated nothing, which is
  an argument against re-splitting whatever else fired. The honesty requirement is met in
  the message rather than the predicate: `test_i_a_mixed_child_discloses_both_counts` pins
  that such a bundle prints *both* `4 conflict(s) declared` and `1 sibling conflict(s) not
  counted`, so the line never claims more than it shows.
* **`getattr(est, "sibling_conflicts", 0)` so the patch degrades on a base without #457.**
  Rejected: it would convert the honest hard failure in §7 into a silent no-op — the
  advisory would go back to recommending `pdca split` with every gate green. The dependency
  on #457 is real and belongs on the surface.

## 5. Forced refutation of my own test

* **(a) Genuine red?** Yes — established by the project's own runner, not by hand:
  `PDCA_BUNDLE=results/issue_458 PDCA_WORKTREE=…pdca-wt-l1 ./engine/scripts/run-verify.sh`
  → green leg `Ran 9 tests … OK`; red leg (production hunks reverted, tests kept)
  `Ran 9 tests … FAILED (failures=4, errors=2)`; verdict
  `C4 PASS: red without the fix, green with it`. The red-leg detail is the defect verbatim:
  `AssertionError: 'scores large for a split child (child 601 of a split of #500, depth 1)
  … ' not found in 'oversized — consider `pdca split` first (difficulty=high; brief 15.8 KB
  (cutoff 12 KB); 2 external dependency token(s); …)'` — criterion (i)'s load-bearing red.
  The module **imported** on the red leg (`Ran 9 tests`, no `unittest.loader._FailedTest`),
  so this is a real red, not the exit-77 shape: every module-level import is a pre-existing
  symbol, and the two new symbols are touched only inside test bodies.
  Criteria (ii), (iv), (v-no-note) and (vi) pass on the red leg by construction — they are
  invariance criteria — which is exactly why they share a module with (i): `run-verify.sh`
  runs the module, so they can only ever be recorded green together with it.
* **(b) Production path?** Yes. The test calls `plan_policy.size_reasons`,
  `plan_policy.evaluate`, `leaves._plan_prompt`, `leaves._split_prompt`,
  `leaves.run_sizer`, `sizing.estimate`/`combine` and `split.read_lineage` — the same
  functions `driver.advance`, `leaves.do_plan` and `leaves.do_split` call. There is no
  `unittest.mock` import in the module at all, and no re-implementation of the logic: the
  expected sentence is a literal (`_PROVENANCE`), never rebuilt by calling the code under
  test.
* **(c) Fixture includes the fault?** Yes. The lineage record is written in the exact shape
  `split.materialise` emits (`split.py:493-499`: `version`/`id`/`parent`/`siblings`/`depth`),
  the failing ids (`602`, `603`) are *in* the brief's `Conflicts with` rather than curated
  out, and the sizer is the shipped `_stub_sizer` running for real (asserted via the
  `sizing.json` it writes). The one fixture that removes a sibling id
  (`test_iii`, second leg) does so as the behaviour under test — the escape hatch —
  after asserting the suppressed leg on the same bundle.

Gates re-run locally, all green on this base: C4 `PASS`; T3 `root suite OK, driver suite
OK` (both suites, `./engine/scripts/run-suite.sh`); T2 `lint_docs: OK` + `render_site: link
audit OK` (`./engine/scripts/run-docs-check.sh`). Formatting: the target ships no
formatter/linter config (no `.pre-commit-config.yaml`, no ruff/black; CI is
docs-check/render-check/require-linked-issue only), so "commit-ready" here means the house
style — Python lines ≤ 95 (`plan_policy.py`'s pre-existing max is 95), docs prose wrapped
at ≤ 80, and the mermaid block's longest line back to the file's pre-existing 144.

## 6. What I deliberately did not touch

`sizing.py` (child-2 owns the signal — this child only consumes it), `split.py`, `cli.py`
(child-4), `### The estimate` and `### The split` in the docs, and the advisory's
non-blocking nature (`plan_policy.py:117-127`: 50% recall at 62% precision, `hold` stays
unimplemented). No `stack-base` file, no brief edit, no driver state written by me — see §7.

## 7. External dependency the run did not provide

NEEDS-HUMAN external dependency: prerequisite #457 folded into the C4 base — this bundle has no `stack-base` marker, so `worktree._target` / `gates.py:379-397` reset the lane worktree to `origin/main`, where `SizeEstimate.sibling_conflicts` does not exist and the green leg dies with `AttributeError: 'SizeEstimate' object has no attribute 'sibling_conflicts'` (verified on an `origin/main` tree with this patch applied: `Ran 8 tests … FAILED (errors=5)`). The patch itself applies cleanly there (`git apply --check` rc=0). Red→green was earned on `origin/fix/457-sizing-ignores-sibling-conflicts` (= `origin/pdca-integration/main` + #457, PR #483 still open). Fix before re-gating: merge PR #483 into `pdca-integration/main` and re-fetch, **or** stamp the marker the wave driver would have written — `printf 'fix/457-sizing-ignores-sibling-conflicts\n' > results/issue_458/stack-base` — then re-run `pdca-pdca gates 458`.

I did **not** write that marker myself: it also decides publish's PR base
(`publish._stack_base_branch`), which contradicts the brief's `Repo + branch target:
… @ main`, and that is a sign-off call rather than a builder's. The marker above is HUMAN-
tagged in §6 (`assemble.py:201-202`), so it also blocks `autoiterate.eligible` from
spending another Do beat on what is a scheduling gap, not a patch defect.

The `[[doctor.checks]]` row that would have caught it before the cycle burned — a wave>0
bundle whose declared prerequisite is not in the base it will be verified against:

```toml
[[doctor.checks]]
id    = "prereq-457-in-base"   # the token Plan should have put in `External dependencies`
cmd   = "git -C ../pdca-harness show origin/main:template/src/pdca_harness/sizing.py | grep -q sibling_conflicts"
hint  = "#458 consumes #457's `SizeEstimate.sibling_conflicts`; merge PR #483 into pdca-integration/main, or stamp results/issue_458/stack-base with fix/457-sizing-ignores-sibling-conflicts so Do and the C4 gate both build on it"
level = "MISSING"
```

(The general form, worth an Act item rather than a per-issue row: a doctor check that, for
every bundle declaring `Depends on:` an *unmerged* prerequisite, asserts the resolved
verify base contains that prerequisite's branch — today nothing reconciles
`Depends on:` with `stack-base`, which is precisely how iteration 1's green was earned on a
base missing #457.)

## 8. Reproducing the evidence

```bash
git -C /home/eddie/pdca/pdca-harness.pdca-wt-l1 checkout --detach \
    origin/fix/457-sizing-ignores-sibling-conflicts        # the #457-carrying base
cd /home/eddie/pdca/pdca-pdca
PDCA_BUNDLE="$PWD/results/issue_458" \
PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l1 \
  ./engine/scripts/run-verify.sh          # → C4 PASS: red without the fix, green with it
PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l1 ./engine/scripts/run-suite.sh
PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l1 ./engine/scripts/run-docs-check.sh
```
