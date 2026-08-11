# Build notes — issue #457

## What changed and why

`sizing.estimate` (`template/src/pdca_harness/sizing.py:255-338` on the target
branch, pre-patch) counted every `Conflicts with` id identically, including the
ones `split.materialise` writes into a child naming its own siblings
(`split.py:491-499`) and `split.rewrite_ordering` turns from proposal-local
labels into real ids (`split.py:333-358`). Those sibling entries are the
split's own scheduling metadata — the splitter is told they're "the point"
(brief, citing `leaves.py:1261`) — not organic churn, so counting them against
the ρ 0.32 `conflicts_with` weight (calibrated over organic bundles) inflated
every materialised child regardless of scope.

The fix adds one function, `sizing.sibling_conflict_count(brief_path,
conflict_ids)` (`sizing.py:224-252`), that reads `split.read_lineage(brief_path
.parent)` and returns how many of the declared conflict ids are in that
record's `siblings`. `estimate()` (`sizing.py:290-294`) subtracts that count
from the raw declared count before weighting, so only *organic* conflicts
score. The excluded count is exposed as a new `SizeEstimate.sibling_conflicts`
field (`sizing.py:195-201`), threaded through `combine()`
(`sizing.py:526-530`) so an escalation from the sizer leaf doesn't drop it.

`template/scripts/size-calibrate` is updated in lockstep (criterion d): it now
imports the same `sibling_conflict_count` (`size-calibrate:70-71`) rather than
mining `len(set(brief.conflicts_with(ap)))` raw, and its `Row.conflicts_with`
column is now the organic-only count — the same quantity `sizing.estimate`
scores — with the excluded count reported separately as `Row.sibling_conflicts`
(`size-calibrate:220-229`, `size-calibrate:290-293`, `:313-317`), mirroring how
`carry_forward_bytes` already keeps a leak auditable rather than silent. A
future Act-cadence retune (#324/#359) now fits the value the engine actually
scores.

`docs/07-crosscutting.md`'s `### The estimate` weights table
(`docs/07-crosscutting.md:121-127` pre-patch) gets one paragraph documenting
the exclusion and the new field, restricted to the section the brief scoped in.

## Alternatives considered and ruled out

**A second, ad-hoc read of `split-lineage.json` inside `estimate()`, duplicating
the JSON-parsing / tolerance logic `split.read_lineage` already has.** Rejected
on the module's own stated discipline: the docstring explicitly says the
a-priori split is "defined once… because a second definition would drift the
first time either side changed" (`sizing.py:72-75`), and the calibrator already
follows that pattern for `apriori_text`/`AprioriBrief`
(`size-calibrate:67-70`). A hand-rolled second reader would be ~15 lines
duplicating `read_lineage`'s total-exception contract (`split.py:373-402`) for
no benefit, and any future tightening of that contract (e.g. a new corrupt-file
shape) would need fixing in two places instead of one. Concretely: importing
`split` and calling the one function already-tested in `test_split_lineage.py`
is a 1-line dependency vs. reimplementing ~30 lines of `read_lineage` +
`_recorded_depth`-style tolerance.

**A new `split_child` weight, defaulting to 0** — the shape the brief explicitly
says the *previous* attempt at this issue took, and explicitly rules out
("out of scope… the previous attempt registered one defaulting to 0, a
documented no-op"). I did not re-attempt it; it doesn't fix anything at the
shipped default and would only be exercised by an instance's own retune,
leaving today's oversized-on-every-child behaviour as the shipped default it
is fixing.

**Deduplicating `conflicts_with` in `sizing.estimate` while I was in the
function.** Noticed the calibrator already dedupes (`len(set(...))`,
pre-patch) while `sizing.estimate` counts raw declarations. Left this
pre-existing discrepancy alone — it predates #457, is not the "shared feature
name denotes two different quantities" gap the brief calls out (that gap is
specifically about the sibling exclusion, which this patch closes), and
touching it would be an uncited, out-of-scope weight-adjacent behaviour change
("out of scope: changing any existing weight or cutoff").

## Constraints honoured

- `AprioriBrief`'s `_DELEGATED` allowlist (`sizing.py:363-365` pre-patch) is
  untouched. `sibling_conflict_count` takes the real `brief_path: Path` — the
  one already in scope inside `estimate()` before `AprioriBrief` is
  constructed (`sizing.py:276` pre-patch, brief's own citation) — and calls
  `.parent` on it directly, never through `ap`.
- `estimate()`'s "never raises" promise: `split.read_lineage` is documented and
  tested (`test_split_lineage.py:174-204`) as a TOTAL catch — absent, unreadable,
  non-UTF8, malformed JSON, non-dict, wrong version, pathologically nested, all
  return `None`. `sibling_conflict_count` additionally guards against a
  `siblings` value that parses but isn't a list. Nothing new can crash the
  Plan beat; a bad lineage record degrades to "0 excluded", matching pre-#457
  behaviour exactly.
- No existing weight, cutoff, or `pdca.toml.jinja` surface changed.
- `split.py`, `cli.py`, `leaves.py`, `plan_policy.py` untouched, per scope.

## Peer callsite consulted

The brief's own citations (`split.py:320-345` region, actually `:333-358` for
`rewrite_ordering` and `:472-501` for `materialise`) were read to confirm the
exact shape of `siblings` and how `Conflicts with` gets its real ids — this is
the "cited peer callsite" exception, read to avoid inventing an id-matching
scheme (e.g. re-stripping `issue_`/`#` prefixes) that duplicates what
`brief._id_list` (`brief.py:347-371`) and `split.materialise`
(`split.py:493-499`) already guarantee agree byte-for-byte.

## The three refutation questions

**(a) Genuine red?** Yes. Reverted the three production files (`git stash push
-- docs/07-crosscutting.md template/scripts/size-calibrate
template/src/pdca_harness/sizing.py`, keeping the new test), then ran
`PYTHONPATH=src python3 -m unittest tests.test_sizing_split_child -v` from
`template/`: 1 genuine `AssertionError` (`9 not less than 7`, the exact
symptom the brief's Reproduction describes) plus 8 `AttributeError`/
`TypeError` on the not-yet-existing `sibling_conflicts` field / function — no
`ImportError`, so it's a real red, not PDCA-UNVERIFIABLE. Restored the stash
and re-ran: 9/9 green. Log excerpt in this bundle's session; reproducible with
the same two commands.

**(b) Production path?** Yes. The primary tests drive `split.accept` →
`split.materialise` → `split.rewrite_ordering` (the actual splitter code, not a
hand-built lineage fixture) to produce a real materialised child, then run the
real `sizing.estimate` over its real `brief.md`. The calibrator agreement test
loads the actual `template/scripts/size-calibrate` file via
`SourceFileLoader` (the same technique `test_sizing.py`'s pre-existing
`test_the_calibrator_IMPORTS_the_split_rather_than_copying_it` already uses)
and calls its real `extract()`, not a copy.

**(c) Fixture includes the fault?** Yes. `SiblingConflictsExcluded` materialises
a child via `split.accept` with `Conflicts with: child-2, child-3` — both
resolve to real siblings — so the fixture is exactly the failure case (a child
whose only conflicts are its own siblings), not a fleet that excludes it.
`test_the_same_child_scores_oversized_before_exclusion` independently confirms
the fixture reaches the `oversized` cutoff under the pre-fix formula, so the
first test isn't passing on a fixture too small to matter.

## External dependency (already declared by the brief, not new)

`copier` is not importable in this sandbox (no `.venv`, no `pip`). The brief
already names this ("External dependencies: `copier importable (.venv)`") and
states the exact consequence: the seven root-level `tests/test_render_and_run
.py` / `test_update_compat.py` / `test_render_cli_name.py` tests skip
themselves via `@unittest.skipUnless(HAVE_COPIER, …)`. Verified:
`python3 -m unittest discover -s tests` (repo root) → `Ran 7 tests … OK
(skipped=2)` for the driver's own root suite and `OK (skipped=7)` for the
render/copier-compat suite specifically — no failures, all skips, exactly as
predicted. This is not a NEEDS-HUMAN discovery on my part (Plan already
registered it); flagging it here only so the human sign-off knows T3's green
on those seven tests carries no evidence either way for this patch, per the
brief's own words ("T3 reports a green that tested nothing").

## Verification commands (repo: the target worktree, base `aaa797a`)

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_sizing_split_child -v
cd template && PYTHONPATH=src python3 -m unittest discover -s tests   # 1631 tests, OK (skipped=2)
python3 -m unittest discover -s tests                                  # repo root, OK (skipped=7, no copier)
```

Also confirmed `patch.diff` applies cleanly (`git apply --check`) to a fresh
clone checked out at `aaa797a` and the full offline suite is green after
applying it there.
