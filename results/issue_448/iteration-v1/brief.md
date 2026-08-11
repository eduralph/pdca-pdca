# Design proposal — issue 448 / stop-the-split-ratchet

> The Plan artifact. Do reads ONLY this file; Check runs the regular gated check. The
> `- **Label:** value` lines are parsed by the driver.

- **Slug:** split-lineage-and-deratchet-sizing
- **Kind:** enhancement (design proposal)
- **Goal:** a split child stops being indistinguishable from a fresh oversized brief.
  `pdca split --accept` records machine-readable **lineage** in every bundle it writes (and
  the inverse children record in the parent); the estimator stops scoring the split's own
  artifacts; the size remedy stops recommending a further split on structural score alone;
  and `--accept` reports, before filing irreversible issues, whether the split lowers the
  estimate.
- **Success criterion:** for a bundle carrying split lineage, (a) `sizing.estimate` no
  longer counts `Conflicts with` entries naming its own siblings, so a child whose only
  churn features are sibling conflicts + inherited `Difficulty`/`External dependencies`
  scores **below** the `oversized` cutoff where it scores ≥ 7 today; (b)
  `plan_policy.size_reasons` emits the split-recommending remedy (`consider \`pdca split\`
  first`) for such a child ONLY when `model_band == oversized`, and otherwise an honest
  "scores large for a split child — driven by inherited/sibling fields" line; (c)
  `split.materialise` writes a `split-lineage.json` into each child and the parent, and
  `split.preflight` reports each staged child's structural band against the parent's
  before `file_children` runs. Demonstrable by C4-verify on the patch alone.
- **Falsifiability:** RED is producible on the ordinary offline driver suite — `cd
  template && PYTHONPATH=src python3 -m unittest tests.test_split_lineage`, which is what
  `engine/scripts/run-verify.sh` runs for a `template/tests/*.py` test. Pre-fix a
  materialised child with two sibling conflicts, `Difficulty: high` and one external
  dependency token scores 3+3+3 = 9 ≥ the `oversized` cutoff of 7
  (`template/src/pdca_harness/sizing.py:89-95`, `:126-127`) and `size_reasons` returns
  "consider `pdca split` first" (`plan_policy.py:134-141`); post-fix it scores below the
  cutoff and the remedy changes. No lineage file exists pre-fix at all, so every assertion
  on it fails. Pure functions of files + config — no network, tracker, `gh` or container.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** no prereq — wave 0, alongside 453 (disjoint file sets: this slice
  touches `split.py` / `sizing.py` / `plan_policy.py` / `leaves.py`, 453 touches only
  `flow.py`). Issue 449 declares `Depends on: 448` and consumes this slice's children
  record, so it builds on the accepted result in wave 1.
- **Surfaces:** data
- **Difficulty:** high — four production modules (`split.py`, `sizing.py`,
  `plan_policy.py`, `leaves.py`) plus `pdca.toml`'s `[driver.sizing]` documentation, and it
  introduces a new bundle artifact a second issue (449) then consumes.
- **Scope:** the four items in *Design*, as one coherent change: (1) lineage + children
  record at materialisation; (2) the estimator stops counting sibling conflicts, plus a
  registered-but-zero `split_child` weight; (3) a depth- and evidence-aware remedy in
  `size_reasons`, and the same context injected into the planner and splitter prompts;
  (4) an advisory convergence report in `split.preflight`.
  / out of scope: a `max_split_depth` cap (held in reserve — items 2–3 remove the *reason*
  depth grows, a cap truncates the symptom); re-calibrating any existing weight or cutoff
  (that is the #324/#359 Act-cadence loop); making the size guard blocking (it stays
  advisory, `plan_policy.py:88-102`); `waves.compute_waves` scheduling semantics; anything
  in `flow.py` — mid-run adoption of children is issue 449 and this bundle must not touch
  that file.
- **External dependencies:** none — python3 ≥ 3.11 stdlib + git only; every touched
  function is a pure function of files plus config, and the test runs in the offline
  driver suite with no tracker, network or container.
- **Test file:** `template/tests/test_split_lineage.py` (new module in the offline driver
  suite). The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`engine/scripts/run-verify.sh`, `--exclude=template/tests/*`), so a new file earns its
  red. **Import modules, never new symbols:** `from pdca_harness import split, sizing,
  plan_policy`, then `split.<new_name>`. A `from pdca_harness.split import <new helper>`
  raises ImportError on the red leg, which run-verify.sh classifies PDCA-UNVERIFIABLE
  (exit 77) rather than red — the test would prove nothing.
- **Citations expected:** Do must cite `path:line` on `origin/main` for every change.
  Verified at `b95aa58`: `sizing.py:89-95` (`DEFAULT_WEIGHTS`), `:126-127` (cutoffs),
  `:238-243` (the five measured features), `:267-269` (the conflict term), `:363`
  (`_DELEGATED`); `plan_policy.py:134-149` (`splittable` + the three remedies);
  `split.py:224-245` (`preflight`), `:247-265` (`_validate_ordering`), `:320-345`
  (`rewrite_ordering`), `:348-362` (`materialise`), `:386-472` (`accept`), `:453-460`
  (breadcrumb), `:609-687` (`file_children`; `body_head` at `:636` is the only place
  "Child slice of #N" is recorded today); `leaves.py:524-591` (`_plan_prompt`),
  `:1222-1286` (`_split_prompt`; the "BETWEEN children are the point" line is `:1261`).
  **Peer callsites to mirror, not re-derive:** `sizing.py:94` + `:273-275`
  (`is_plan_pointer` — a new weight is added the same way, a `DEFAULT_WEIGHTS` key read
  through `_weights`, so `[driver.sizing]` retunes it without patching the engine);
  `plan_policy.py:134-139` (the existing evidence-aware carve-out — the split-child remedy
  is the same shape, keyed on lineage); `split.py:406-427` (staged-write discipline —
  anything new written per child goes into `staging`, never in place).
- **Disposition hint:** new-feature

## Motivation

Operating the harness produced issues decomposed into sub- and sub-sub-issues where one
split (or none) was warranted. The loop is structural, not a judgment failure: three of the
five weighted features are fields the split itself installs into every child —
`conflicts_with` (+3; sibling ordering entries are *correct scheduling metadata*, yet
`estimate()` counts them as organic churn), `difficulty_high` (+3; inherited from a `high`
parent) and `ext_deps` (+3; the parent's tokens are copied into each child). 3+3+3 = 9 ≥
the cutoff of 7, whatever the child's actual scope; the one de-escalating term,
`is_plan_pointer` (−2), split children never have.

And nothing downstream knows a split happened: `materialise` writes only the child body
(`split.py:359-360`) and "Child slice of #N" goes solely to the tracker issue body
(`split.py:636`), so a split child is locally indistinguishable from a fresh oversized
brief — to `estimate`, `size_reasons`, the sizer leaf and the planner prompt, which points
at `pdca split` again (`leaves.py:576-586`).

## Design

**1. Lineage, written at materialisation.** `split.materialise` writes one JSON file,
`split-lineage.json`, into **each staged child** and into the **parent**:

```
child:  {"version": 1, "role": "child", "id": "<child id>", "parent": "<parent id>",
         "siblings": ["<other child ids>"], "depth": <parent depth + 1>}
parent: {"version": 1, "role": "parent", "id": "<parent id>",
         "children": ["<child ids>"], "depth": <parent depth>}
```

One filename in both directions, distinguished by `role`: 449 needs the parent→children
edge and this slice the child→parent/siblings edge; two files would drift. `depth` comes
from the parent's own child-record when the parent was itself a split child, else 0 —
recursion depth for free. Child files are staged and moved with the rest
(`split.py:406-427`); the parent's is written next to the `build-notes.md` breadcrumb and
BEFORE `CLOSE_MARKER` (`split.py:453-461`), preserving the guarantee that a failed write
leaves the parent un-marked. The prose breadcrumb stays — this is its parseable inverse.

Lineage is **provenance, not attempt output**: it must NOT join
`state.DOWNSTREAM_OF_BRIEF` (`state.py:82-110`), so it survives an `iterate-plan` re-plan
and the archive of a rejected attempt. One module-level reader in `split.py` returns the
parsed record or `None`; missing, unreadable or wrong-`version` yields `None` and every
consumer behaves exactly as today. Nothing here may raise into a beat.

**2. The estimator stops scoring the split's own artifacts** (`sizing.estimate`,
`sizing.py:238-272`). With child lineage present, `Conflicts with` entries naming
**siblings of the same split** are excluded from the conflict count — scheduling metadata
this process installed, not churn evidence. Organic conflicts (any id not in `siblings`)
still count at full weight.

One constraint decides *where* this reads from: inside `estimate`, `brief_path` is a real
`Path` (the `AprioriBrief` is constructed there, `sizing.py:238`), so
`brief_path.parent / "split-lineage.json"` is the correct access. Do **not** reach for
`.parent` on an `AprioriBrief` — it refuses every attribute outside its allowlist by design
(`sizing.py:363`, `:400-407`), and that guard must not be widened.

A `split_child` key joins `DEFAULT_WEIGHTS` **defaulting to 0**, documented in `pdca.toml`'s
`[driver.sizing]`: registered so an instance can retune it per the #324 loop, shipped at 0
because a non-zero value is an uncalibrated guess and this module's rule is that only
measured features carry weight (`sizing.py:32-35`). Item 2's real work is the sibling
exclusion, which is deterministic. (See *Open questions*.)

**3. The remedy becomes depth- and evidence-aware** (`plan_policy.size_reasons`,
`:134-149`). For a bundle with child lineage, `consider \`pdca split\` first` is emitted
only when `est.model_band == sizing.OVERSIZED` — the sizer leaf actually naming ≥ 2
independently shippable outcomes, the one signal that can see decomposability. Structural
score alone downgrades to "scores large for a split child (child N of a split of #X, depth
D) — driven by inherited/sibling fields; prefer building over re-splitting", mirroring the
"large but coherent" carve-out immediately above it. The `before_do=False` branch
(`:142-149`) keeps its `iterate-plan` wording. The same one-sentence context is injected
into `leaves._plan_prompt` (`:576-586`) and `leaves._split_prompt` (`:1255-1265`) when the
bundle carries lineage; the existing split instructions are not otherwise reworded.

**4. Convergence is checked before irreversible filing** (`split.preflight`, `:224-245`).
After `_validate_ordering`, each parsed child body is written to a temporary file, run
through `sizing.estimate`, and its band compared with the parent's — `preflight` runs
before `file_children`, the only point at which the check can still change a decision.
There every ordering ref is a sibling **label** by construction (`:247-259`), so the staged
estimate treats them as siblings, i.e. excluded, the same rule as item 2. The output is
**advisory and deterministic**, matching the size guard's warn-only stance
(`plan_policy.py:88-102`): when the split does not lower the band for most children, print
which did not converge and which feature carries each score (`SizeEstimate.reasons` already
carries this). It never blocks, never prompts, never changes what is filed.

## Alternatives considered

* **A `max_split_depth` cap.** Blunt: every level still sees the same inputs and gives the
  same advice. Held in reserve; items 2–3 remove the reason depth grows.
* **A `Split of:` brief FIELD instead of JSON.** It would sit inside the very text
  `sizing.apriori_text` measures (moving `brief_bytes`), cannot carry the children list
  449 needs, and a hand-edited brief could silently change provenance.
* **Dropping or globally lowering `conflicts_with`.** The strongest measured churn signal
  on *organic* bundles; weakening it everywhere trades a real signal for a special case.
* **Making the convergence check blocking.** Rejected for the reason `size_guard` has no
  `hold` mode: 62% best precision (`plan_policy.py:91-101`) trains people to override it.

## Impact & compatibility

* **New artifact**, from this change onward; existing bundles carry none and behave exactly
  as today — every consumer treats absent lineage as "not a split child".
* **Scores can only go DOWN, and only for split children.** No cutoff or existing weight
  changes and the new weight ships at 0, so an untouched `pdca.toml` is behaviourally
  identical except for the sibling-conflict exclusion. Nothing becomes blocking: the guard
  stays advisory, the convergence report is a print, `--accept` files what it files today.
* **Consumed by 449**, whose detection step reads the parent's children record; the schema
  above is the contract between the two bundles.
* **Rendered instances** pick this up on their next `copier update`; `[driver.sizing]`
  gains one documented key with a no-op default (additive for `test_update_compat`).

## Open questions

1. **Ship `split_child` at 0 or at −2?** This brief specifies **0**; the issue allows
   either ("and/or"). A −2 default by symmetry with `is_plan_pointer` is a one-line change
   at sign-off if you prefer it.
2. **Is one slice right?** The four items are independently shippable and were filed as
   such; they are briefed together because item 1 is the artifact items 2–4 key off, and
   three of the four are small edits to one function each. Splitting this would be a
   fitting irony and cost four cycles. Say so at sign-off if you disagree.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected as one slice: T5 breadth is the root problem, not the implementation. The work is wanted; the SLICING was wrong. Split into separate outcomes at these seams: 1. Lineage record + schema. Must settle the mixed-role case first: a bundle that is both child and parent currently loses its child edge (split.py:695-697 overwrites the child record with a parent one, preserving only depth), and the ratchet returns at depth >= 1. This schema is the declared contract with issue 449, so it lands first and alone. 2. Estimator de-ratchet. Stop counting sibling conflicts. Resolve the estimator / calibrator disagreement on conflicts_with (scripts/size-calibrate:300 still mines the raw feature that sizing.py:277-281 no longer scores) rather than deferring it to the #324/#359 loop. FOLDED IN (was a separate finding): excluding sibling conflicts also blinds the convergence report to a split that separated nothing — children conflicting pairwise now score LOWER in the very report meant to detect non-convergence. Handle both together, since both turn on what a sibling conflict is taken to mean. 3. Remedy wording + escape hatch. Key the "driven by inherited/sibling fields" line on the already-computed sibling_conflicts, not on mere presence of lineage — today a child with four organic conflicts and zero sibling conflicts scores 12/oversized and still prints the inherited-fields line next to its own contradicting evidence. And make the hatch reachable: the shipped sizer is mode = "stub" and returns band = "ok" unconditionally, so on any offline instance the split recommendation is suppressed permanently once lineage exists. 4. Convergence report. Must fire on the --ids path too (cli.py:764 calls split.accept directly; only the auto-filing branch calls preflight), which is the path the docs call required for unreachable trackers. Its stderr writes must not be able to abort the acceptance — a BrokenPipeError currently escapes preflight and can report the flatly wrong "no split-proposal.md" with rc 1 on a healthy bundle. Not a rebuild: a single attempt cannot turn these four into one outcome, and the findings will read implementation-shaped every round until the split is authored. Note for Plan: C4 was NOT refuted — the red/green legs are genuine and run through the real production path. The mechanics largely work; it is the breadth and two design questions (schema mixed-role, meaning of a sibling conflict) that send this back. §6 NEEDS-HUMAN items left open (unticked) — not cleared, superseded by the iterate.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
