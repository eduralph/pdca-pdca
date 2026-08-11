# Build notes — issue #457 (iteration 2)

Target: `eduralph/pdca-harness` @ the run's folded integration branch, base `aaa797a`
(`pdca-integrate: issue_456` — child-1's `split.py` lineage reader is on the base, as the
brief states). All citations are `path:line` in that tree with this patch applied
(`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt-l1`).

## Carry-forward first — what iteration 1 got wrong, and what changed

The sign-off kept the approach ("sibling-conflict exclusion, shared helper, exposed count
— accepted in principle") and rejected on one reviewer finding:

**1) C3: the helper could still crash the Plan beat.** v1 did
`if not isinstance(siblings, list): siblings = []` then `set(siblings)`. A record like
`{"siblings": [[]]}` passes the isinstance-list guard and `set()` raises
`TypeError: unhashable type: 'list'` — from inside `estimate`, whose whole contract is
that a malformed input abstains rather than throwing (`sizing.py:267-270`).

Fixed at `sizing.py:259-261` — three lines, and the rule is stated once instead of
enumerating malformed shapes: **both sides of the membership test are narrowed to `str`
before anything hashes them.**

```python
raw = (split.read_lineage(brief_path.parent) or {}).get("siblings")
siblings = {s for s in raw if isinstance(s, str)} if isinstance(raw, list) else set()
return sum(1 for c in conflict_ids if isinstance(c, str) and c in siblings)
```

Shape borrowed deliberately from `split._recorded_depth` (`split.py:405-421`), which is
the same division of labour one module over: the *reader* abstains on a file it cannot
parse, the *value normaliser* abstains on a value it cannot compute with, and it lives
next to its consumer. `split.py` is out of scope for this child, so the normalising
belongs here anyway.

Anything the filter drops is simply "not a sibling", so it keeps scoring at full weight —
pre-#457 behaviour. That is the direction that under-corrects: a corrupt record can only
fail to remove inflation, never silently delete a conflict someone really declared
(`sizing.py:229-258` closing paragraph).

Proof it binds, not just that it is green: I re-installed v1's helper body verbatim and
ran the new `MalformedLineageAbstains` class — **4 failures + 1 error**, including
`sibling_conflict_count raised TypeError("cannot use 'list' as a set element (unhashable
type: 'list')")`. Restored, all 15 tests green. The `[[]]` case the reviewer named is the
first entry in `CASES` (`template/tests/test_sizing_split_child.py:262-276`).

**2) T3 red (11 failures in `test_verify_base.py`) — confirmed pre-existing, not chased.**
The carry-forward calls it a harness test-isolation fault (`PDCA_VERIFY_BASE` leaking into
the tests' subprocesses). Verified rather than assumed: I extracted the **unpatched base**
(`git archive HEAD | tar -x -C $TMP`, no patch at all) and ran
`PDCA_VERIFY_BASE=aaa797a python3 -m unittest tests.test_verify_base` there → `Ran 19
tests … FAILED (failures=11)`. Identical count, zero patch involvement. Out of scope,
untouched. With `PDCA_VERIFY_BASE` unset — the environment the gate script itself
prepares — `./engine/scripts/run-suite.sh` is **green** here: `T3: root suite OK, driver
suite OK`.

## What changed and why

`sizing.estimate` counted every `Conflicts with` id identically, including the ones the
splitter itself installs: `split.materialise` writes each child's siblings into its
`Conflicts with` (`split.py:493-499`) and `rewrite_ordering` turns the proposal-local
labels into the real ids the lineage record stores (`split.py:333-358`). So three of the
five weighted features were process artifacts on a materialised child — `conflicts_with`
+3, inherited `difficulty_high` +3, copied-down `ext_deps` +3 = 9 against the `oversized`
cutoff of 7 — with `is_plan_pointer`, the only de-escalating term, being one a split child
never has.

| Where | What |
|---|---|
| `sizing.py:84` | `from . import brief, split` — one new module edge; no cycle (`split` imports only `state` at module level, `split.py:35`). |
| `sizing.py:228-261` | `sibling_conflict_count(brief_path, conflict_ids)` — the one definition, total by construction. |
| `sizing.py:288`, `:305-306` | `estimate` keeps the ids, subtracts the sibling count, weights only the organic remainder. Placed *outside* the `try/except OSError` on purpose: the helper cannot raise, so there is no failure there for a handler to catch. |
| `sizing.py:205`, `:350` | `SizeEstimate.sibling_conflicts` — criterion (c). Defaults to 0, so every existing positional construction is untouched. |
| `sizing.py:546` | `combine` carries it through: an escalation says nothing about the split's own metadata, and dropping it there would hide a non-converged split behind exactly the verdict most likely to be attached to one. |
| `size-calibrate:70-76`, `:222-235`, `:295-298`, `:320-324` | criterion (d) — the calibrator **imports the same function** rather than mining `len(set(brief.conflicts_with(ap)))` raw; `conflicts_with` becomes the organic count and the excluded count is reported beside it as `sibling_conflicts`, deliberately absent from `FEATURES`. |
| `docs/07-crosscutting.md:129-137`, `:173-176` | the weights table's paragraph and the retune procedure — the only two docs rows the brief scopes in. |

`brief_path` is the real `Path` already in scope at `sizing.py:305`, before `AprioriBrief`
is constructed; `_DELEGATED` (`sizing.py:420`) and its `__getattr__` are untouched, and
nothing reaches the record through `ap`.

**No new reason string.** The estimate exposes the count as data and says nothing new in
`reasons` — the remedy wording is child-3's, per the brief's out-of-scope list.

## Alternatives considered, with their cost

**A second lineage read inside `sizing`, not importing `split`.** Rejected: `read_lineage`
is 30 lines of deliberately *total* tolerance (`split.py:373-402`, plus the
`_recorded_depth` half at `:405-421`) with its own 11-case test module
(`test_split_lineage.py:133-204`). Re-deriving it here is ~30 duplicated lines against
**1** import line, and every future tightening of the contract would have to be found in
two places. The module's own docstring already forbids this shape ("a second definition
would drift the first time either side changed and the drift would be invisible",
`sizing.py:72-75`).

**A new `split_child` weight defaulting to 0** — v0 of this issue, and explicitly ruled
out by the brief. Not re-attempted: at the shipped default it changes nothing, so the
9-against-7 score stays the shipped behaviour; it only adds a `pdca.toml.jinja` row and a
docs claim.

**Leaving the calibrator alone and deferring (d) to the Act loop.** Rejected because the
cost is invisible and lands later: `size-calibrate:300` (pre-patch) mined
`len(set(brief.conflicts_with(ap)))`, so the moment `estimate` excludes siblings the two
sides publish **one feature name over two quantities**, and #324/#359's retune would fit
the `conflicts_with` weight on a number the engine no longer uses for split children.
Cost of fixing it now: **9 added lines + 1 changed line** in one file (numstat: 26/2 total
for `size-calibrate`, most of it comment). Cost of deferring: a mis-fitted weight nobody
can see, in the loop this change explicitly leaves the weights to.

**Deduplicating `conflicts_with` inside `estimate` while I was in the function.** The
calibrator dedupes (`len(set(...))`), `estimate` counts raw declarations. Left alone: it
predates #457, `estimate` uses the count as a boolean (`if conflicts:`, `sizing.py:323`)
so it changes no score, and touching it is weight-adjacent behaviour the brief puts out of
scope. Both sides still agree on the *organic* count, which is what (d) asks for.

## Real-corpus check of criterion (b), beyond the fixture

Ran the calibrator over this instance's own 37-bundle corpus with the patch and with the
pristine base, and diffed:

```
bundles: 37 | conflicts_with differences vs BASE: []
new column values: ['0']
```

No bundle here carries lineage yet (#456 only just landed), so "no lineage ⇒ byte-identical
to today" is demonstrated on real data, not only on the synthetic fixture. The synthetic
half is `test_a_bundle_with_no_lineage_scores_exactly_what_it_scored_before`, which asserts
the *pre-existing* `test_sizing.Structural.test_bands_follow_the_cutoffs` fixture
(`test_sizing.py:95-98`) and its score of 9.

## Peer callsites consulted

Only those the brief cites: `split.py:333-358` (`rewrite_ordering`) and `:472-501`
(`materialise`) — read to confirm the exact `siblings` shape and that the ids in
`Conflicts with` are byte-identical to the record's, rather than inventing a second
id-normalising scheme alongside `brief._id_list` (`brief.py:347-371`).

## The three refutation questions

**(a) Genuine red?** Yes — established through the project's own C4 gate, not by hand:
`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →

```
== C4 green leg: … Ran 15 tests … OK
== C4 red leg: bundle test(s) with the production change reverted
   Ran 15 tests … FAILED (failures=8, errors=17)
C4 PASS: red without the fix, green with it
```

15 tests ran on **both** legs — no `_FailedTest`, no 0-test leg, so neither leg is a
PDCA-UNVERIFIABLE. The red leg reproduces the brief's exact symptom:
`AssertionError: 9 not less than 7 : … ['difficulty=high', '2 conflict(s) declared', '1
external dependency token(s)']`. Separately, the hardening itself was refuted against the
*rejected v1 helper* (4 failures + 1 error), so the C3 fix has its own red, not just the
feature.

**(b) Production path?** Yes. The fixtures come out of `split.accept` → `materialise` →
`rewrite_ordering` (`split.py:525`, `:472`, `:333`) — the real splitter, writing a real
`split-lineage.json` and a real `brief.md` — and the assertions run the real
`sizing.estimate`. The malformed cases hand-edit that **real** record and drive
`sizing.estimate`, the production consumer, not the helper alone (a helper that abstains
is only half the contract; the beat can still die one frame up — the discipline
`test_split_lineage.py:206-212` already sets). The calibrator tests load the actual
`template/scripts/size-calibrate` by `SourceFileLoader` and call its real `extract`; the
agreement is asserted by **object identity** (`assertIs`), which no copy can satisfy.

**(c) Fixture includes the fault?** Yes. `_CHILD_1` is the failing element itself: a child
of a `high` parent whose `Conflicts with` names nothing but its siblings and whose
dependency token is inherited — 3+3+3 = 9 ≥ 7 pre-fix, asserted independently by
`test_the_same_fixture_reaches_the_cutoff_under_the_unfixed_formula` so the main assertion
cannot pass on a fixture too small to matter. Nothing is curated out: the organic test
*adds* a non-sibling id to the same child and requires it to score full weight; the
pairwise test builds the "the split separated nothing" case rather than avoiding it.

## External dependencies

`copier importable (.venv)` — the brief's one declared dependency — **is present**
(copier 9.17.0), so the target's root render / `copier update`-compat suite really ran
here (`Ran 7 tests … OK`, no skips) rather than skipping itself into a green that tested
nothing. No NEEDS-HUMAN on this. Nothing else was needed: python3 stdlib + git, no
network, tracker, `gh` or container.

## Commands run (all through the project's own runners)

```
PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh      # C4  → PASS
PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-docs-check.sh  # T2  → lint OK, 22-page render + link audit OK
PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-suite.sh       # T3  → root suite OK (7), driver suite OK (1637, skipped=2)
```

The target ships no formatter or pre-commit hook config (no `pyproject.toml`,
`.pre-commit-config.yaml`, `setup.cfg`, `.editorconfig`; CONTRIBUTING.md asks only for DCO
sign-off, one logical change, and a green offline suite). Its CI checks are exactly the
docs-check and render-check workflows the T2/T3 gates run — both green above. Added lines
stay inside each file's own width norm (≤94 in `sizing.py` and the test, ≤96 in
`size-calibrate`; the one 97-char docs line is a joined prose line in a file whose
existing lines run to 144).
