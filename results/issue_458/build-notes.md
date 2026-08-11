# Build notes — issue 458 / split-child-remedy-and-hatch (iteration 3)

Target branch: `eduralph/pdca-harness @ pdca-integration/main`, worktree
`/home/eddie/pdca/pdca-harness.pdca-wt-l1` at **ef00e6e** (merge of PR #483, which carries
#457's `SizeEstimate.sibling_conflicts`). Every `path:line` below is against that tree
(base = `git show HEAD:<path>`; post = the patched worktree).

---

## 1. What the brief asked for, and what I did

The brief is an explicit **re-house, do not redesign** directive: iteration v2's patch was
judged sound on this base and was rejected only because its own brief named `main` (which
lacks `sibling_conflicts`). So the job was: confirm the reference change still applies and
still holds on `pdca-integration/main`, and adjust only what the base shift demands.

**Result: nothing needed adjusting.** The patch I ship is **byte-identical** to
`iteration-v2/patch.diff`:

```
$ diff results/issue_458/patch.diff results/issue_458/iteration-v2/patch.diff
$ echo $?   # 0 — zero lines of difference
```

`git apply --check` on the clean ef00e6e worktree returned rc=0, and after applying, the
regenerated `git diff` was identical to the reference. No context drift, as the brief
predicted.

I did **not** take this on faith — I re-derived the citations, re-ran every gate on this
base, and refuted the test (§4). What follows is what I verified, not a restatement of v2.

## 2. The change, cited

Three production files + one new test.

### `template/src/pdca_harness/plan_policy.py`

| Base | Post | What |
|---|---|---|
| `:54` `from . import doctor, sizing` | `:54` `from . import doctor, sizing, split` | the lineage reader for the message only |
| — | `:88-111` `_split_child_provenance(d)` | formats `child N of a split of #X, depth D`; **decides nothing** |
| `:88-102` docstring | `:129-145` | records why the *count* is the predicate and why the hatch is not the sizer's verdict |
| `:134-136` `splittable = …` | `:178-180` (unchanged) | still computed, still the fork for everything else |
| `:137` `if not splittable:` | `:189` `if before_do and est.sibling_conflicts:` … `:197` `elif not splittable:` | the provenance question is asked **before** the readout fork |
| `:141` `remedy = "consider \`pdca split\` first"` | `:201` (unchanged) | reachable exactly when `sibling_conflicts == 0` |
| `:142-149` `else:` iterate-plan | `:204-215` (wording unchanged) | criterion (iv) |
| `:150` `detail = …({'; '.join(est.reasons)})` | `:212` `…{extra})` | `extra` is `""` unless the branch at `:189` fired → criterion (vi) |

The predicate is `est.sibling_conflicts` — the count `sizing` already publishes
(`sizing.py:215`, computed `sizing.py:324-325` from `sizing.sibling_conflict_count`,
`sizing.py:238-279`). `plan_policy` re-derives nothing.

### `template/src/pdca_harness/leaves.py`

`split` was already imported at base `:52`, so no import change. New helper
`_split_provenance_note(d)` at post `:524-553`, injected at post `:610` (inside
`_plan_prompt`, base `:524`, immediately before the "SPLIT IT IN THIS BEAT" instruction at
base `:576`) and post `:1294` (inside `_split_prompt`, base `:1226`, immediately before
"Fill {tpl}" at base `:1257`). Nothing else in either prompt string is touched — the test
proves that by full-string equality (§4c).

Note the deliberate asymmetry, which is the crux of the first reproduced failure: the
prompt note gates on **presence of the child edge**, the advisory gates on the **count**.
The note says "your `Conflicts with` may be inherited — check", which is true of every
child and asserts nothing about this brief's score; the advisory says "your score is driven
by inherited fields", which is a claim about the score and needs the count to be true.

### `docs/07-crosscutting.md`

Three hunks, all inside `### The process` (base `:36-99`), exactly the range the brief
scopes: base `:50` (Entry A `splittable?` → new `A4b` fork + `A8` remedy node), base `:59`
(Entry B node label, saying it does *not* fork), base `:87-90` (prose). Untouched: `### The
estimate` (base `:100-189`, #457's) and `### The split` (base `:190+`, #459's) — checked by
hunk offsets, `@@ -47,7 +47,9 @@`, `@@ -56,7 +58,7 @@`, `@@ -87,7 +89,20 @@`, the last
context line of which is base `:93`.

## 3. Alternatives ruled out — with the cost

Two of these are the failures the brief names as must-not-recur. For those the deciding
axis is **the invariant**, not diff size (`docs/principles.md` §1.2/§2): both are cheaper
than what I shipped and both are wrong.

1. **Predicate = `split.read_lineage(d) is not None`** (lineage presence).
   Cost: *smaller* — it drops `sizing.py`'s count from the path entirely (~1 line at the
   `if`, and `_split_child_provenance` becomes the whole implementation).
   Rejected because it asserts a falsehood: child 601 re-planned with four *organic*
   conflicts and zero sibling conflicts would print "driven by inherited/sibling fields"
   in the same string as its own `4 conflict(s) declared`. That is precisely the invariant
   the brief names — advice must be entailed by the evidence it cites. `test_ii` is the
   binding assertion (`assertNotIn("driven by inherited/sibling fields", detail)` beside
   `assertIn("4 conflict(s) declared", detail)`).

2. **Escape hatch = re-enable the split remedy when `est.model_band == sizing.OVERSIZED`.**
   Cost: one extra `or` clause in the `if` — the cheapest possible fix.
   Rejected because it is *dead config* on the shipped default: `leaves.run_sizer`
   (`leaves.py:1085-1086`) routes every non-`command` sizer to `_stub_sizer`
   (`leaves.py:1217-1223`), which returns `{"band": "ok"}` unconditionally, so `model_band`
   is never `oversized` offline and a bundle that ever carried a sibling conflict could
   never again be advised to split. `test_iii` is written so it cannot pass under that
   design: it asserts `cfg.sizer.mode == "stub"`, then that the *recovered* line carries
   the ordinary remedy, then re-reads `sizing.json` to confirm `stub: True` and
   `band: "ok"` were what actually ran.

3. **Nest the provenance check inside the `splittable` fork** (i.e. `elif before_do and
   est.sibling_conflicts:` after `if not splittable:`).
   Cost: identical diff size — literally a reordering of the same branches, 0 extra lines.
   Rejected on reachability, and this is measurable, not rhetorical: with #457 excluding
   sibling conflicts from the score, the canonical child in
   `test_i_a_patch_only_child_reaches_the_same_branch` scores 6 → `churn_band = watch`,
   `patch_band = oversized`, so `splittable is False` and the nested branch never runs. On
   the unpatched tree that bundle prints `oversized — expect a large patch — … (difficulty=high;
   brief 15.7 KB (cutoff 12 KB); structurally predicts a large patch (~100 KB+); sizer says
   ok (confidence low))` — nothing at all about where its size came from. That exact string
   is in the red-leg log.

4. **Suppress the advisory entirely for a sibling-carrying child** (`return []`).
   Cost: **≈ −35 lines** against what I shipped, and every one of them is checkable —
   −8 inside `size_reasons` (post `:190-191` the `remedy` string, `:192-195` its comment,
   `:181` `extra = ""`, `:196` the `extra` assignment), −26 for the whole
   `_split_child_provenance` helper and its blank separators (post `:88-113`), −1 for the
   `split` import at `:54`. So it is strictly cheaper.
   Rejected: it guards the symptom instead of fixing the advice. The bundle *is* oversized
   — the human still wants to see the readout — and a silently dropped advisory is
   indistinguishable from a bundle that scored `ok`. Naming the provenance keeps the signal
   and corrects only the remedy, which is what the brief's success criterion (i) actually
   asks for ("emits an honest line naming the provenance", not "emits nothing").

5. **Fix the cause further upstream — make `sizing` not band such a child `oversized`.**
   Out of scope by the brief ("`sizing.py`: #457 owns the signal; this slice only consumes
   it"), and wrong anyway: the child *is* large (difficulty=high + 15.7 KB brief + external
   dependency tokens). The defect is the *remedy*, not the band.

## 4. Refuting my own test (forced)

Runner: the project's own C4 gate, `./engine/scripts/run-verify.sh` (docs/INTEGRATION.md
§3/§4; `pdca.toml [gates] checks` id `C4-verify`), invoked with `PDCA_BUNDLE` +
`PDCA_WORKTREE`. It runs both legs itself — it reverts only the production hunks
(`--exclude=tests/*  --exclude=template/tests/*`) and keeps the test. No hand-rolled
invocation. Headless, stdlib-only; the test imports nothing heavier than `pdca_harness`.

**(a) Genuine red? — YES.** Verified by actually reverting (the gate does it):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_plan_policy_split_child.py
.........
Ran 9 tests in 0.018s
OK
== C4 red leg: bundle test(s) with the production change reverted
FFF.F.EE.
Ran 9 tests in 0.015s
FAILED (failures=4, errors=2)
C4 PASS: red without the fix, green with it        # rc=0
```

Per-test red-leg outcome (alphabetical, matching `FFF.F.EE.`):

| # | test | red leg |
|---|---|---|
| 1 | `test_i_a_mixed_child_discloses_both_counts` | **F** |
| 2 | `test_i_a_patch_only_child_reaches_the_same_branch` | **F** |
| 3 | `test_i_sibling_carried_score_names_the_provenance_not_pdca_split` | **F** |
| 4 | `test_ii_organic_conflicts_keep_the_ordinary_split_remedy` | pass (by construction) |
| 5 | `test_iii_the_ordinary_remedy_returns_under_the_shipped_stub_sizer` | **F** |
| 6 | `test_iv_a_built_bundle_still_gets_the_iterate_plan_wording` | pass (unchanged branch) |
| 7 | `test_v_a_bundle_that_is_not_a_split_child_gets_no_note` | **E** |
| 8 | `test_v_both_prompts_gain_the_same_provenance_note_and_nothing_else` | **E** |
| 9 | `test_vi_a_bundle_with_no_lineage_is_byte_identical` | pass (regression guard) |

The load-bearing red is #3: pre-fix, `size_reasons` returns

> ``oversized — consider `pdca split` first (difficulty=high; brief 15.8 KB (cutoff 12 KB); 2 external dependency token(s); structurally predicts a large patch (~100 KB+); sizer says ok (confidence low))``

for a child whose only declared conflicts are its own siblings — the defect verbatim.

Three green-by-construction tests (4, 6, 9) are the deliberately non-binding half: they are
the *invariance* criteria (ii)/(iv)/(vi), which by definition pass on the unpatched tree.
They earn their place because `run-verify.sh` runs the **whole module** in one invocation,
so they can only go green *together with* the four that are red — (iii) in particular
cannot degrade into a vacuous green while (i) is red. That is why the brief insisted the
pair live in one module, and I kept it that way.

Also confirmed: the red leg reports `Ran 9 tests` and the log contains **no**
`unittest.loader._FailedTest`, i.e. the module genuinely imported on the red leg and 9 real
tests executed. That is the trap the brief warned about, and the reason the test does
`from pdca_harness import leaves, plan_policy, sizing, split` at module level and reaches
the new symbols only by attribute access inside test bodies (`leaves._split_provenance_note`
at test lines 256/283) — a module-level `from … import _split_provenance_note` would have
produced 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:140-147`).

**(b) Production path? — YES.** `grep -nE "mock|patch\(|monkeypatch|MagicMock|Fake"` over
the test file returns only prose in docstrings/comments; there is no `unittest.mock` import
and nothing is patched. The test calls, all production:
`plan_policy.size_reasons`, `plan_policy.evaluate` (the entry `driver.py:56` calls),
`leaves._plan_prompt`, `leaves._split_prompt`, `leaves._split_provenance_note`,
`leaves.run_sizer`, `leaves.current_sizing`, `sizing.estimate`, `sizing.combine`,
`split.read_lineage`. `Config` is the real `pdca_harness.config.Config` with
`sizer` left at its shipped `LeafConfig(mode="stub")` default — so `run_sizer`
(`leaves.py:1085-1086`) really dispatches to `_stub_sizer` (`leaves.py:1217-1223`) and
really writes `sizing.json`, which the test then reads back off disk.

**(c) Fixture includes the fault? — YES.** The fault here is *sibling conflicts on a
materialised split child*, and the fixture builds exactly that, not a curated stand-in:

- `_lineage()` writes the real `split-lineage.json` record in the exact shape
  `split.materialise` writes (`split.py:493-499`): `version`/`id`/`parent`/`siblings`/`depth`,
  with `split.LINEAGE_VERSION` and `split.LINEAGE` taken from production constants
  (`split.py:47-48`) so a version bump breaks the test rather than silently voiding it.
  `split.read_lineage` (`split.py:373-402`) is the reader that consumes it, unmocked.
- The brief fixture declares `Conflicts with: 602, 603` — the very ids the record lists as
  siblings — so `sizing.sibling_conflict_count` actually finds them. The test asserts
  `est.sibling_conflicts == 2` **before** asserting the message, so a fixture that silently
  stopped exhibiting the fault fails loudly instead of passing vacuously.
- `test_i_a_mixed_child_discloses_both_counts` keeps 4 organic conflicts *in* the fixture
  alongside the sibling one, rather than excluding them to make the message easy.
- `test_iii` runs the real stub sizer and re-reads `sizing.json` for `stub: True` after the
  recovery leg, so "the stub sizer was replaced mid-test" is an assertion, not an
  assumption.

## 5. Other gates run on this base (all from the project's own runners)

| Gate | Command | Result |
|---|---|---|
| C4 (gating) | `./engine/scripts/run-verify.sh` | **PASS** — rc=0, red→green as above |
| T2 docs | `./engine/scripts/run-docs-check.sh` | **PASS** — `lint_docs: OK`; `render_site: wrote 22 page(s)`, `link audit OK` |
| T3 suites | `./engine/scripts/run-suite.sh` | **PASS** — root render/update-compat `Ran 7 tests … OK`; offline driver suite `Ran 1700 tests … OK (skipped=2)` |
| T4 contrib | `./scripts/pdca contribcheck` | rc=0 |

The brief's external dependency `copier importable (.venv)` is **satisfied** —
`.venv/bin/python3 -c "import copier"` → `copier OK 9.17.0`, and the root suite ran **7
tests with 0 skips**, so the render + `copier update` compatibility tests really exercised
the `template/` changes rather than skipping themselves. No NEEDS-HUMAN external
dependency to declare.

## 6. Commit-readiness for the target repo

`eduralph/pdca-harness` ships **no** formatter or linter config — no
`.pre-commit-config.yaml`, no `.git/hooks/pre-commit`, no `pyproject.toml` /
`setup.cfg` / `.editorconfig` / ruff / black / flake8 at the root, and no
`line-length` key in `template/pyproject.toml.jinja`. Its CI is
`docs-check.yml` (`lint_docs.py` + `render_site.py --check` — both run above, green),
`render-check.yml` (`tests.test_render_and_run` + `tests.test_update_compat` — both run
above, green) and `require-linked-issue.yml` (a PR-body concern, publish's job).
CONTRIBUTING.md's only mechanical requirements are the DCO `-s` trailer (publish's job) and
"keep the offline suite green" (1700 tests, OK).

So the applicable "hooks" are the two CI checkers plus the suites, and I ran all of them.
Style-wise I matched the files' existing conventions rather than a tool: longest added
Python line is 94 chars vs. an existing 95 in `plan_policy.py` and 110 in `leaves.py`;
longest added Markdown line is 142 vs. an existing 144 in `docs/07-crosscutting.md`.

## 7. STOP discipline

No branch pushed, no PR opened, no PR marked ready or merged. Worktree is left in the
patched state (base + `patch.diff`), which is what the driver reconstructs for gates
anyway (`run-verify.sh` header, #296).
