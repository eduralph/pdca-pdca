# Build notes — issue_457 (iteration 3)

Target branch: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l1`) whose base is `aaa797a "pdca-integrate:
issue_456"` — the run's folded integration branch, so child-1's accepted `split.py`
lineage reader (`split.read_lineage`, `split.py:373-402`) is on the base, as the brief
says for a wave-1 bundle. `git apply --check` of the shipped `patch.diff` against a
pristine `aaa797a` worktree: clean.

## What the change is

The splitter writes a `Conflicts with` entry into every child naming its siblings
(`split.py:493-499`), and `rewrite_ordering` turns the proposal-local labels into the same
real ids the lineage record stores under `siblings` (`split.py:333-358`) — the splitter
leaf is told outright that those fields "BETWEEN children are the point"
(`leaves.py:1261`). `sizing.estimate` counted them like organic conflicts, so with
`difficulty_high` inherited from the parent and `ext_deps` copied down, 3+3+3 = 9 ≥ the
`oversized` cutoff of 7 for **every** materialised child, before anyone read its scope.

One new function, called from both places that need it:

* `sizing.sibling_conflict_count(brief_path, conflict_ids)` — `sizing.py:238-279` (new).
  Reads the record via `brief_path.parent` (the brief's constraint), through
  `split.read_lineage`, and counts how many declared conflict ids are this bundle's own
  siblings.
* `sizing.estimate` — `sizing.py:317-325` (new block): `conflicts = len(conflict_ids) -
  sibling_conflicts`. The weighted feature therefore counts **organic** conflicts only, and
  the excluded ones stop appearing in `reasons` (which is what a human reads).
* `SizeEstimate.sibling_conflicts` — `sizing.py:205-215`, default 0, carried through
  `combine` (`sizing.py:557-565`) so a model escalation cannot drop it.
* `scripts/size-calibrate` — imports that same function (`size-calibrate:79-84`), splits
  the declared set once (`:304-307`), and emits `conflicts_with` (organic) plus
  `sibling_conflicts` (excluded, deliberately **not** in `FEATURES`) — `:233-245`,
  `:333-334`.
* `docs/07-crosscutting.md` — the two `### The estimate` rows the brief scoped: the weights
  table's meaning of `conflicts_with` (`:129-140`) and the retune procedure (`:176-179`).
  `### The process` and `### The split` untouched (child-3 / child-4).

Nothing else moved: no weight, no cutoff, no new config key, and `plan_policy.py`,
`split.py`, `cli.py`, `leaves.py` are not in the diff.

## Iteration carry-forward — what this attempt does about it

**Iteration 1, C3 (`set(siblings)` on raw lineage JSON raised `TypeError` on
`{"siblings": [[]]}`).** Kept fixed, and kept the way the reviewer passed it at C3: both
sides are narrowed to `str` before anything is hashed (`sizing.py:277-279`). The rule is
stated once rather than as a list of malformed shapes, because the record is a
hand-editable hint and enumerating failure modes is what failed the first time. Whatever
the filter drops is simply *not a sibling*, so it keeps scoring at full weight — the
direction that under-corrects rather than silently discarding a conflict someone declared.
`MalformedLineageAbstains` now sweeps **eight** values (added a nested-dict member and a
bool to iteration-2's six), each asserted through the real `sizing.estimate` — a helper
that abstains is only half the contract, since the beat can still die one frame up — and
again one frame down through the helper itself.

**Iteration 2 (auto-iterate on the reviewer's T3 / T4 NEEDS-HUMAN rows).** Both were
"could not reproduce here", not defects in the patch, and both are now answered with
evidence:

* *T3, "Copier is absent here so all seven root tests skipped — a green that tested
  nothing."* Copier **is** present in this instance's venv (`copier 9.17.0`,
  `.venv/bin/python3`, which is the interpreter `engine/scripts/run-suite.sh:14` picks).
  With the patch in the working tree the seven really ran — `/tmp/patched-suite.log:1-20`
  shows each rendering the template ("No git tags found in template; using HEAD as ref")
  and `Ran 7 tests … OK` with **no** skip count. The render/update suites copy the working
  tree, so the `template/` half of this patch was exercised by them.
* *T3, the 11 `test_verify_base` failures.* Reproduced on the **clean base with no patch at
  all**, purely by exporting `PDCA_VERIFY_BASE` the way the driver does for a wave-1
  bundle: `/tmp/baseline-suite-verifybase.log` → the same 11 `FAIL:
  test_verify_base.VerifyBaseExport.*` and the same verdict line `== T3: root suite OK,
  driver suite FAILED (rc 1)`. Without that variable the same clean base is
  `/tmp/baseline-suite.log` → `root suite OK, driver suite OK`. So it is a harness
  test-isolation fault (the variable leaks into subprocesses the test expects it unset in),
  not this patch, and — per iteration 1's carry-forward — out of scope, not chased.
* *T4, "`./scripts/pdca` and the PR/commit artifacts were not supplied."* Those artifacts
  are drafted by the publish step after sign-off; nothing in Do produces them. Not
  actionable here.

The approach itself (sibling exclusion, one shared helper, an exposed count) was accepted
in principle at sign-off and is unchanged. What is **new** in this attempt, beyond the
extra malformed cases:

* Criterion (b)'s "assert against an existing fixture, not only a synthetic one" is now
  literally that. `ThePreExistingFixturesAreUnchanged` loads `template/tests/test_sizing.py`
  **by path** and re-runs its `Structural`, `Combine`, `SecondReviewFixes` and
  `ThirdReviewFixes` cases in-process, failing if any moves — #320's own calibration pins,
  not a copy of one of them that can drift. Iteration 2 hand-copied a single fixture body
  into the new module instead.
* The same direction for the calibrator:
  `test_the_column_is_unchanged_for_a_bundle_with_no_lineage` asserts
  `row.conflicts_with == len(set(brief.conflicts_with(ap)))` for a lineage-free bundle —
  i.e. the whole published corpus's column does not move.
* The `estimate` assertion for a lineage-free brief now pins the full `reasons` list, not
  only the score, because "byte-identically to today" includes what a human reads.

## Alternatives considered, with their cost

1. **A new `split_child` weight defaulting to 0** (iteration 1's rejected shape, and the
   brief's out-of-scope list). Cost is not the objection: it is a no-op. With the default
   the child still scores 3+3+3 = 9 ≥ 7, so success criterion (a) fails outright while
   `pdca.toml.jinja` gains a documented knob and the docs gain a claim. Sibling exclusion
   is the deterministic mechanism that actually changes the number.
2. **"Any lineage ⇒ don't count conflicts"** — literally one line
   (`if split.read_lineage(brief_path.parent): conflicts = 0`) against the ~3-line helper
   body I shipped (`sizing.py:277-279`). Rejected on the criteria, not on size: it discards
   *organic* conflicts inside a split child (criterion (b)) and cannot distinguish "child
   with 2 sibling conflicts" from "child with none", which is exactly the signal criterion
   (c) exists for — children that conflict pairwise are the splitter saying the split
   separated nothing. Two extra lines to keep a signal the brief names as load-bearing.
3. **Reaching the record through `AprioriBrief`** (adding `parent` to `_DELEGATED`).
   Forbidden by the brief and rightly: `parent` hands back a real `Path`, whose
   `read_text()` returns the whole brief including the post-Do carry-forward the allowlist
   exists to withhold (`sizing.py:476-492`). Inside `estimate` the real `Path` is already in
   hand (`sizing.py:303`), so nothing is bought.
4. **Calibrator: keep `conflicts_with` raw and add `organic_conflicts` beside it.** The
   brief allows "mine both under distinct names", and this is a 2-line change instead of my
   4. Rejected because it leaves the **shared** name denoting two quantities — the exact
   thing criterion (d) is about — so the next Act-cadence retune of the `conflicts_with`
   *weight* would still be fitted to the raw column. Mining the same excluded count, with
   the excluded amount reported beside it, keeps one name = one quantity and keeps the
   exclusion auditable (the discipline `carry_forward_bytes` already sets).
5. **Deduplicating `conflict_ids` in the engine** (`set(...)`, one word) so it matches the
   calibrator's `len(set(...))` on repeated ids too. Rejected on criterion (b), not cost: it
   would change a lineage-free brief's `reasons` today (`- **Conflicts with:** 12, 12`
   currently reads "2 conflict(s) declared"), and (b) asks for byte-identical. **Disclosed:**
   engine-counts-declarations vs calibrator-counts-unique is a *pre-existing* divergence
   (pre-patch `sizing.py:241` vs `size-calibrate:300`) that this change neither
   introduces nor removes — it only guarantees both sides subtract the *same* sibling
   exclusion. Worth an Act-cadence look with the weight retune (#324/#359); out of scope
   here.

Two edges I decided deliberately rather than by accident: a child declaring a conflict with
its **parent** still scores at full weight (the parent is not in `siblings`, and a conflict
with a terminal parent is not sibling scheduling metadata), and a depth-2 bundle that is
both a child and a parent has only its own `siblings` excluded — conflicts naming its
`children` score normally.

## Red → green, through the project's runner

`./engine/scripts/run-verify.sh` (the C4 gate; `PDCA_BUNDLE` + `PDCA_WORKTREE` set, from the
instance root) — log kept at `/tmp/c4-verify.log`:

```
== C4 green leg: … template/tests/test_sizing_split_child.py
Ran 17 tests in 0.057s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 17 tests in 0.063s
FAILED (failures=10, errors=20)
C4 PASS: red without the fix, green with it
```

The red leg's headline failure is the brief's reproduction, verbatim:
`AssertionError: 9 not less than 7 : a child whose only conflicts are its own siblings
still scored oversized: ['difficulty=high', '2 conflict(s) declared', '1 external
dependency token(s)']`.

Suites, via `./engine/scripts/run-suite.sh` (T2/T3 gate scripts):

| run | root suite | driver suite |
|---|---|---|
| clean base, no patch (`/tmp/baseline-suite.log`) | `Ran 7 … OK` | `Ran 1622 … OK (skipped=2)` |
| with this patch (`/tmp/patched-suite.log`) | `Ran 7 … OK` | `Ran 1639 … OK (skipped=2)` |
| clean base + `PDCA_VERIFY_BASE` (`/tmp/baseline-suite-verifybase.log`) | `Ran 7 … OK` | 11 `test_verify_base` FAILs (rc 1) |

+17 driver tests = exactly this module; nothing else moved. `./engine/scripts/run-docs-check.sh`
(T2): `lint_docs: OK`, `render_site: link audit OK`.

Beyond the gates, the calibrator was smoke-run against this live instance (read-only, no
`--csv` into the bundle root): 35 settled bundles, correlation table renders,
`sibling_conflicts` correctly absent from it, and `--csv /tmp/calib457.csv` emits columns
14 `conflicts_with` / 15 `sibling_conflicts`.

## The three refutation questions

**(a) Genuine red?** Yes — and not by inspection: `run-verify.sh` reverted the production
hunks (keeping the test) and the module went `FAILED (failures=10, errors=20)`, then green
with the patch. Every criterion's binding case is in the red list: (a)
`test_a_child_whose_only_conflicts_are_siblings_scores_below_the_cutoff`, (b)
`test_an_organic_conflict_inside_a_split_child_scores_full_weight` +
`test_a_bundle_with_no_lineage_scores_exactly_what_it_scored_before`, (c) the four
exposure cases, (d) the four calibrator cases, plus 16 malformed-lineage subtests. The
red leg **ran** (`Ran 17 tests`, no `unittest.loader._FailedTest`), which is why the module
imports `pdca_harness.sizing` and reaches the new names by attribute inside test bodies —
a module-level `from pdca_harness.sizing import sibling_conflict_count` would have made the
red leg exit 77 `PDCA-UNVERIFIABLE` instead of proving anything (`run-verify.sh:140-143`).
Two cases pass on **both** legs by design and are labelled as such:
`test_the_same_fixture_reaches_the_cutoff_under_the_unfixed_formula` (anti-vacuity: proves
the fixture really reaches 7 under the old formula) and
`test_the_calibration_suite_still_passes_unchanged` (the "nothing else moved" guard).

**(b) Production path?** Yes. The test drives `sizing.estimate` / `sizing.combine` /
`sizing.sibling_conflict_count` from `template/src/pdca_harness/sizing.py` — the functions
the patch changes — and the *real* `template/scripts/size-calibrate` file, loaded from its
shipped path, with `assertIs(calibrate.sibling_conflict_count, sizing.sibling_conflict_count)`
so a second copy of the rule cannot satisfy it. No mock of the behaviour under test exists
in the module (the only `mock` anywhere is inside the pre-existing peer suite it re-runs).

**(c) Fixture includes the fault?** Yes. The fixtures are produced by **`split.accept`**
itself — production `materialise` writes the lineage record and `rewrite_ordering` turns
the sibling labels into real ids — not hand-built JSON, and the first assertions in the
headline test check exactly that (`siblings == ["602","603"]`, and the brief's `Conflicts
with` really contains those ids rather than `child-2, child-3`). The child carries the full
fault the brief describes: two sibling conflicts **plus** inherited `Difficulty: high`
**plus** one external-dependency token = 9 pre-fix. The malformed-lineage sweep includes
the exact record that crashed iteration 1 (`"siblings": [[]]`, an unhashable member) rather
than curating it out.

## Environment / dependencies

No unnamed external dependency: everything ran on python 3.13 stdlib + git, offline, no
tracker, no `gh`, no container. The brief's one declared dependency — `copier importable
(.venv)` — is satisfied here (9.17.0) and the seven render/update-compat tests genuinely
ran rather than skipping, so no `NEEDS-HUMAN external dependency` marker is warranted.

Target commit hooks: the repo configures no formatter or linter (no pre-commit config, no
ruff/flake8 config); its enforcement is CI — `docs-check.yml` (the two checkers
`run-docs-check.sh` runs: both green) and `render-check.yml` (`tests.test_render_and_run` +
`tests.test_update_compat`: the seven that ran green above). Line lengths in the touched
files stay inside each file's own convention (max added line 94 in `sizing.py` / the test
against a 96 baseline in `split.py`/`test_sizing.py`; 98 in `size-calibrate`'s docstring,
which already runs to 101).

STOP discipline observed: nothing pushed, no branch created, no PR opened.
