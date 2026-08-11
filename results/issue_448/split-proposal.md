<!-- pdca:split-proposal v1 -->
# Split proposal — issue 448

Authored in Plan, by the human + planner, after issue 448's first attempt was rejected at
sign-off with `iterate-plan`. The sign-off's own words: *"Rejected as one slice: T5 breadth
is the root problem, not the implementation. The work is wanted; the SLICING was wrong."*
The four seams below are the ones it named, with the findings that motivated each folded
into the child that owns them. The full rejected attempt is preserved in
`results/issue_448/iteration-v1/`.

All line references verified against `eduralph/pdca-harness` `main` @ `b95aa58` — the
rejected patch never landed, so every citation below is current code.

## Why this slice is oversized

Issue 448 asks for four changes and says so itself: *"Four changes, smallest first — each
closes one side of the ratchet, and they are independently shippable if a split is
(fittingly) wanted."* The first attempt built all four as one coherent change. It **worked**
— C4 was not refuted, the red and green legs were genuine and ran through the real
production path (`cli._split` → `split.accept` → `sizing.estimate` →
`plan_policy.size_reasons`), and the 1610-test offline suite stayed green. It was still sent
back, because breadth was the problem and breadth is not fixable by rebuilding:

* **Four modules, four separately-arguable design decisions.** Adversarial review returned
  seven NEEDS-HUMAN items against one patch, spanning schema (`split.py`), scoring
  (`sizing.py`), policy wording (`plan_policy.py`) and CLI plumbing (`cli.py`). Each is a
  judgement a reviewer must make on its own evidence; bundled, they arrive as one
  accept/reject and none of them gets decided properly.
* **Two of them are genuine open design questions, not implementation slips.** *What is the
  lineage schema when a bundle is both a child and a parent?* and *what does a sibling
  conflict mean — noise to exclude, or the splitter's statement that two children share a
  resource?* Both need answering before the code that depends on them is written, and the
  second is upstream of two other children.
* **The rollback surface is the whole feature.** The record is the declared contract with
  issue #449, so reverting the bundle to fix a scoring bug would also withdraw an interface
  another in-flight bundle consumes.
* **A rebuild cannot converge.** A single attempt cannot turn four outcomes into one, and
  the findings will read implementation-shaped every round while the budget drains — which
  is precisely why the route back was `iterate-plan` and not `iterate-do`.

The seams are the *dependency* seams, not arbitrary cuts: one child ships the artifact,
one ships the scoring semantics that read it, and two independently consume that signal.

## Wave sketch

```
wave 0:  child-1   lineage record + schema          (nothing to build on)
wave 1:  child-2   estimator stops scoring siblings (needs child-1's record)
wave 2:  child-3   honest remedy + reachable hatch  (needs child-2's sibling count)
wave 3:  child-4   pre-filing convergence report    (needs child-2; conflicts with child-3)
```

* **child-2 depends on child-1** — the estimator cannot exclude *sibling* conflicts until
  something on disk says who the siblings are. There is no partial version of this.
* **child-3 and child-4 both depend on child-2** — each keys on the sibling-conflict count
  child-2 exposes. Neither can be written honestly against a signal that does not exist:
  child-3's whole defect is that the previous attempt keyed on *presence of lineage*
  instead, and asserted something demonstrably false; child-4 must see pairwise sibling
  conflicts in order to report a split that separated nothing.
* **child-3 conflicts with child-4** — no dependency between them, but both edit
  `docs/07-crosscutting.md`. The three doc-touching children own one disjoint section each —
  child-2 `### The estimate` (`:100-173`), child-3 `### The process` (`:36-99`), child-4
  `### The split` (`:174-218`) — but section discipline does not help a *patch*: same file
  ⇒ the second hunk set will not apply on a base missing the first. So child-3 and child-4
  go into different waves and neither is built blind. Their code files are disjoint
  (`plan_policy.py` + `leaves.py` vs `split.py` + `cli.py`).

This is a serial chain of four waves, and that is the honest shape: each child's input is
the previous child's output.

## Convergence check (run by hand at Plan — this is what child-4 automates)

`sizing.estimate` over the parent's rejected brief and over each staged child body, with
sibling labels rewritten to ids:

```
PARENT (iteration-v1/brief.md)  score  6  oversized  difficulty=high; brief 13.6 KB (cutoff 12 KB);
                                                     structurally predicts a large patch (~100 KB+)
child-1                         score  3  ok         1 external dependency token(s)
child-2                         score  3  ok         1 external dependency token(s)
child-3                         score  6  watch      1 conflict(s) declared; 1 external dependency token(s)
child-4                         score  6  watch      1 conflict(s) declared; 1 external dependency token(s)
```

The split **converges**: no child is `oversized`, and every child's brief is ~7 KB against
the parent's 13.6 KB. Two things in that table are worth keeping:

* **child-3 and child-4 carry +3 each purely for their sibling `Conflicts with` entry** —
  correct scheduling metadata, scored as organic churn. That is issue 448's whole thesis,
  reproducing itself inside 448's own split. Child-2 is the change that stops it, and after
  child-2 lands these two would score 3 / `ok`.
* **The parent's `oversized` came from `patch_band`, not churn** (`difficulty=high` AND
  brief ≥ cutoff), so `splittable` was *false* and the guard would have said "a large
  COHERENT change is not a split candidate" (`plan_policy.py:134-139`). This split was
  driven by the human's T5 judgement at sign-off, not by the size guard — a useful reminder
  that the guard is advisory and that child-3 must not make it any more suppressive than it
  already is.

Also verified at Plan: the `copier importable (.venv)` token every child declares resolves
to a registered `[[doctor.checks]]` row whose detect cmd passes, so
`plan_policy.dependency_reasons` is clean for all four and none of them opens a §6 item.

**Ordering consequence outside this proposal:** issue **#449** currently declares
`Depends on: 448, 453` and consumes 448's parent→children record. Once 448 is marked
`split` that dependency must be re-pointed at **child-1**, which is the bundle that actually
ships the record. Re-point it before driving #449.

<!-- pdca:child child-1 -->
# split: record lineage in the child and parent bundles (the schema children 2-4 and #449 read)

- **Slug:** split-lineage-record
- **Defect / goal:** `pdca split --accept` records nothing locally about the split it just
  performed. `materialise` writes only the child's `brief.md` (`split.py:348-362`), and the
  "Child slice of #N" breadcrumb goes solely into the filed tracker issue body
  (`split.py:609-687`, `body_head` at `:636` is the only place it is recorded today). On
  disk a split child is therefore indistinguishable from a fresh oversized brief — to
  `sizing.estimate`, to `plan_policy.size_reasons`, to the sizer leaf, to
  `leaves._plan_prompt`, and to `pdca flow`. Ship the missing provenance: a machine-readable
  lineage record in each child bundle *and* in the parent, plus one tolerant reader for it.
  Nothing else consumes it in this slice — it is the declared contract that children 2-4 and
  issue #449 build on, which is why it lands first and alone.
- **Success criterion:** after `split.accept(parent, ids, cfg)` —
  1. each created child bundle contains `split-lineage.json` naming its `parent`, its
     `siblings` (the *other* children of the same split, by tracker id) and its `depth`
     (parent's depth + 1, so recursion depth is recorded without anyone counting);
  2. the parent bundle contains `split-lineage.json` naming its `children`;
  3. **the mixed-role case is preserved**: for a parent that *itself* already carried a
     child record, the post-accept record still carries its own `parent` and `siblings`
     **and** gains `children`. This is the specific defect the previous attempt shipped —
     it overwrote the child record with a parent one, keeping only `depth`, so a depth-1
     bundle silently lost its sibling set and the whole ratchet returned at depth ≥ 1
     (reproduced: bundle 601 scored `6 / watch` with no advisories; after
     `split.accept(601, [701,702])` it was back to `9 / oversized`). A test must accept a
     split whose parent is itself a child and assert both edges survive — asserting only
     that `depth` survives blesses the loss rather than catching it;
  4. one tolerant module-level reader returns the parsed record, or `None` for an absent,
     unreadable, malformed or wrong-`version` file. It never raises: a provenance reader
     that can throw into a beat is worse than one that abstains, and every consumer must
     behave exactly as today when it returns `None`;
  5. the record is **not** added to `state.DOWNSTREAM_OF_BRIEF` (`state.py:82-110`), so it
     survives `iterate-plan` and the archiving of a rejected attempt — it is provenance,
     not attempt output. Assert this by name in a test, not in a comment;
  6. the existing transactional discipline is preserved: child records are written into
     `staging` and moved with the rest (`split.py:348-362`, moved by `accept` at
     `:406-427`), and the parent's record is written **before** `CLOSE_MARKER`
     (`split.py:453-461` region) so a failed write leaves the parent un-marked and
     `_rollback` still correct. A failed accept restores the parent's prior record bytes.
- **Schema (the contract — this is the interface decision, and it is settled here):** one
  file, `split-lineage.json`, carrying *independent optional edges* and **no** `role`
  discriminator:
  ```json
  {"version": 1, "id": "601",
   "parent": "500", "siblings": ["602", "603"],
   "children": ["701", "702"],
   "depth": 1}
  ```
  `parent`/`siblings` are present iff the bundle is a split child; `children` is present iff
  the bundle has been split. Writing a parent record **merges into** any existing record
  rather than replacing it. A `role` field was tried and rejected in the previous attempt
  for exactly the reason item 3 describes: one filename carrying one role cannot express a
  bundle that is both, and one filename is required because #449 needs the parent→children
  edge while children 2-4 need the child→parent/siblings edge, and two files would drift.
  The prose breadcrumb in the parent's `build-notes.md` stays — this is its parseable
  inverse, not a replacement.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** n/a — new functionality. The gap is directly observable:
  `git -C ../pdca-harness grep -rn "lineage" template/src/pdca_harness/` returns nothing,
  and after `pdca split 500 --accept --ids 601,602` each child bundle contains `brief.md`
  and nothing else.
- **Falsifiability:** RED is producible on the ordinary offline driver suite — `cd template
  && PYTHONPATH=src python3 -m unittest tests.test_split_lineage`, which is what
  `engine/scripts/run-verify.sh` runs for a `template/tests/*.py` test. Pre-fix **no lineage
  file exists at all**, so every assertion on it fails and every `split.<new_name>` attribute
  access raises `AttributeError` — a genuine red, empirically confirmed on the previous
  attempt's red leg (`7 failures + 13 errors`). This is a wave-0 bundle, so the gate verifies
  against the brief's own branch target with no `PDCA_BASE`/`PDCA_VERIFY_BASE` export
  (`gates.py:389-397`). Pure functions of files — no network, tracker, `gh` or container.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/split.py` (the
  filename constant, the writer, the tolerant reader), one docs row describing the artifact
  and its schema in `docs/07-crosscutting.md` `### The split` (`:174-218`, the section that
  already documents `--accept`'s transactional guarantees), and the new test module.
  **Out of scope:** every *consumer* of the record
  — `sizing.estimate` (child-2), `plan_policy.size_reasons` and the leaf prompts (child-3),
  the convergence report (child-4), `flow.py` (issue #449). No weight, no cutoff, no remedy
  wording, no `pdca.toml.jinja` change. Do not edit `state.py`'s `DOWNSTREAM_OF_BRIEF` list
  — the record's *absence* from it is the point.
- **External dependencies:** `copier importable (.venv)` — this patch changes files under
  `template/`, so the target's render and `copier update` compatibility suites at the target
  root exercise it. Without copier those seven tests skip themselves and T3 reports a green
  that tested nothing. Otherwise python3 ≥ 3.11 stdlib + git only: the test runs in the
  offline driver suite with no tracker, network or container.
- **Test file:** `template/tests/test_split_lineage.py` — a new module in the offline driver
  suite, run by `engine/scripts/run-verify.sh` as `cd template && PYTHONPATH=src python3 -m
  unittest tests.test_split_lineage`. The C4 gate reverts only the PRODUCTION hunks and
  keeps the test (`run-verify.sh:121-130`, `--exclude=tests/* --exclude=template/tests/*`),
  so a new file in `template/tests/` earns a genuine red.
  **Import the module, never the new symbols.** Use `from pdca_harness import split`, then
  `split.<new_name>` inside test bodies. A module-level `from pdca_harness.split import
  <helper>` raises ImportError on the red leg, so 0 tests run and `run-verify.sh` exits 77
  `PDCA-UNVERIFIABLE` instead of red (`run-verify.sh:145`) — the test would prove nothing.
  Attribute access inside a body yields `AttributeError`, which is a real red; this was
  confirmed on the previous attempt's red leg (`7 failures + 13 errors`).
- **Difficulty:** medium
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
# sizing: stop scoring the split's own scheduling metadata as churn

- **Slug:** sizing-ignores-sibling-conflicts
- **Defect / goal:** three of the five weighted features in `sizing.estimate` are fields the
  split process itself installs into every child — `conflicts_with` (+3, the strongest churn
  weight), `difficulty_high` (+3, inherited from a `high` parent) and `ext_deps` (+3, the
  parent's tokens copied into each child that needs them) (`sizing.py:89-95`). 3+3+3 = 9 ≥
  the `oversized` cutoff of 7 (`sizing.py:126-127`) regardless of the child's actual scope,
  and the one de-escalating term, `is_plan_pointer` (−2), a split child never has. Sibling
  `Conflicts with` entries are *correct scheduling metadata*: the splitter is explicitly
  told the ordering fields "BETWEEN children are the point" (`leaves.py:1261`), and
  `split.rewrite_ordering` turns sibling labels into real ids (`split.py:320-345`). Yet
  `estimate` counts them identically to organic conflicts (`sizing.py:241`, `:268`), and the
  ρ 0.32 calibration behind that weight was measured over *organic* bundles. Stop scoring
  the artifact the process itself created.
- **Success criterion:**
  (a) for a bundle carrying child lineage, `Conflicts with` entries naming its own
      `siblings` are excluded from the conflict count — a materialised child whose churn
      features are N sibling conflicts plus an inherited `Difficulty: high` plus inherited
      external-dependency tokens scores **below** the `oversized` cutoff of 7, where it
      scores ≥ 7 today;
  (b) **organic** conflicts — any id not in `siblings` — still score at full weight, and a
      bundle with no lineage scores byte-identically to today (assert against an existing
      fixture, not only a synthetic one);
  (c) the sibling-conflict **count is exposed** on the estimate (e.g. a field on
      `SizeEstimate`). This is not decoration: child-3 must key its wording on whether
      sibling conflicts actually carry the score rather than on mere presence of lineage,
      and child-4's convergence report must still be able to *see* a proposal whose children
      all conflict pairwise — which is the splitter's own statement that the split separated
      nothing, and would otherwise be scored as a clean split by the very report that exists
      to detect non-convergence;
  (d) **`sizing.estimate` and `template/scripts/size-calibrate` agree on what
      `conflicts_with` means.** The calibrator mines `len(set(brief.conflicts_with(ap)))`
      raw (`size-calibrate:300`), so after (a) a *shared* feature name denotes two different
      quantities, and any Act-cadence retune of the weight (#324/#359 — the loop this
      change explicitly leaves the weights to) would fit it on a value the engine no longer
      uses for split children. Resolve it here rather than deferring: either mine the same
      excluded count, or mine both under distinct names. A test asserts the agreement.
- **Constraints (verified against `main`, carry forward):**
  * Read the record via `brief_path.parent / …`. Inside `estimate`, `brief_path` is a real
    `Path` (`sizing.py:217`; the `AprioriBrief` is constructed below it). **Do not** widen
    the `AprioriBrief` allowlist to get there — `_DELEGATED` (`sizing.py:363`) and its
    `__getattr__` (`:400-412`) refuse every attribute outside a short allowlist *by design*,
    and that guard must stay closed.
  * `estimate` must keep its promise never to raise on a malformed or absent brief
    (`sizing.py:220-224`): a lineage read failure abstains, it does not crash the Plan beat.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Falsifiability:** RED on `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_sizing_split_child`. Pre-fix a materialised child with two sibling conflicts,
  `Difficulty: high` and one external-dependency token scores 3+3+3 = 9 ≥ the `oversized`
  cutoff of 7 (`sizing.py:89-95`, `:126-127`, `:277-278`), so the "scores below the cutoff"
  assertion fails outright; criteria (c) and (d) fail on `AttributeError` for the not-yet-
  exposed count. **This is a wave-1 bundle**: its Do worktree and its gate run on the run's
  folded integration branch (`PDCA_VERIFY_BASE`, `gates.py:379-397`), which already carries
  child-1's accepted `split.py` — so the lineage reader this child calls exists on the base,
  and reverting only THIS child's production hunks still leaves a genuine red. No network,
  tracker, `gh` or container.
- **Reproduction:** materialise a split child carrying two sibling `Conflicts with` entries,
  `Difficulty: high` and one external-dependency token, then run `sizing.estimate` over its
  brief: it scores 9 and bands `oversized` on `sizing.py:277-278`, with
  `2 conflict(s) declared` among its reasons — although its actual scope is one function.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/sizing.py`,
  `template/scripts/size-calibrate`, the `[driver.sizing]` documentation rows in
  `docs/07-crosscutting.md` — restricted to `### The estimate` (`:100-173`; the weights table
  and its retune procedure at `:110` and `:149-162`) — and the new test module. Leave
  `### The process` (`:36-99`) to child-3 and `### The split` (`:174-218`) to child-4.
  **Out of scope:**
  changing any existing weight or cutoff (that is the #324/#359 Act-cadence loop); adding a
  new `split_child` weight — the previous attempt registered one defaulting to 0, a
  documented no-op that added `pdca.toml.jinja` surface and a docs claim without changing
  behaviour, and the sibling exclusion is the deterministic mechanism that actually works;
  the remedy wording and the leaf prompts (child-3); the convergence report (child-4);
  `plan_policy.py`, `split.py`, `cli.py`, `leaves.py`.
- **External dependencies:** `copier importable (.venv)` — the patch changes files under
  `template/`, so the target's render and `copier update` compatibility root suites exercise
  it; without copier those seven tests skip themselves and T3 reports a green that tested
  nothing. Otherwise python3 ≥ 3.11 stdlib + git only; the test runs in the offline driver
  suite with no tracker, network or container.
- **Test file:** `template/tests/test_sizing_split_child.py` — a new module in the offline
  driver suite. The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`run-verify.sh:121-130`), so a new file earns its red. **Import the module, never the new
  symbols** — `from pdca_harness import sizing, split`, then attribute access inside test
  bodies; a module-level `from pdca_harness.sizing import <helper>` raises ImportError on
  the red leg, giving 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:145`)
  instead of a red that proves anything.
- **Difficulty:** medium
- **Depends on:** child-1
<!-- pdca:end child-2 -->

<!-- pdca:child child-3 -->
# plan_policy: an honest split-child advisory, with an escape hatch that actually works

- **Slug:** split-child-remedy-and-hatch
- **Defect / goal:** `plan_policy.size_reasons` answers an oversized bundle with
  `consider `pdca split` first` (`plan_policy.py:134-141`), and its `splittable` predicate
  is true whenever *structural churn alone* fired — exactly the readout a split inflates
  (child-2). So every level of a recursion sees the same inputs and gives the same advice,
  and the planner prompt points at `pdca split` again. Make the advisory evidence-aware —
  and, the part the previous attempt got wrong, keep the split recommendation **reachable**.
  Two specific failures, both reproduced against the rejected patch, must not recur:
  1. **Keying on mere presence of lineage asserts something demonstrably false.** Child 601
     of a split of 500, re-planned with four *organic* conflicts (811-814) and **zero**
     sibling conflicts, scored 12 / `oversized` and still printed *"scores large for a split
     child … driven by inherited/sibling fields; prefer building over re-splitting"* — in
     the same string as its own contradicting evidence `4 conflict(s) declared`, and with no
     "sibling conflict(s) not counted" clause anywhere. The honest predicate is child-2's
     exposed sibling-conflict count.
  2. **The escape hatch was unreachable in the shipped configuration.** Re-enabling the
     split remedy only when `est.model_band == sizing.OVERSIZED` is dead config on any
     offline instance: `[leaves.sizer]` ships `mode = "stub"` and `leaves._stub_sizer`
     (`leaves.py:1213-1219`) returns `{"band": "ok"}` unconditionally. Combined with lineage
     deliberately surviving `iterate-plan`, a bundle that *ever* carried child lineage could
     never again be advised to split, whatever its brief later said, unless the operator
     bought a `mode = "command"` sizer. The hatch has to work with the sizer this project
     actually ships.
- **Success criterion:**
  (i) for a split child whose oversized score **is carried by** sibling conflicts,
      `size_reasons` emits an honest line naming the provenance ("scores large for a split
      child (child N of a split of #X, depth D) — driven by inherited/sibling fields; prefer
      building over re-splitting") and **not** `consider `pdca split` first`;
  (ii) for a split child with **zero** sibling conflicts — its score carried by organic
      evidence — `size_reasons` emits the ordinary split remedy unchanged, and never the
      inherited-fields line;
  (iii) **(ii) still holds on an instance running the shipped stub sizer**: the test
      exercises the real `_stub_sizer` (`band: "ok"`), not a mock, proving the suppression
      is neither permanent nor conditional on buying a `mode = "command"` sizer. The
      previous attempt's only hatch test mocked the stub away and passed on the red leg too,
      so nothing in the evidence would have surfaced the defect;
  (iv) the `before_do=False` branch keeps its existing `iterate-plan` wording
      (`plan_policy.py:142-149`) — a bundle that already has a patch is still told to
      re-plan, not to `pdca split`;
  (v) the same one-sentence provenance context is injected into `leaves._plan_prompt`
      (`leaves.py:524-591`) and `leaves._split_prompt` (`leaves.py:1222-1268`) when the
      bundle carries lineage, without otherwise rewording the existing split instructions;
  (vi) a bundle with **no** lineage produces byte-identical output to today.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Falsifiability:** RED on `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_plan_policy_split_child`. Criterion (i) is the load-bearing red: pre-fix
  `size_reasons` returns `consider `pdca split` first` for a split child whose score is
  carried by sibling conflicts, so the assertion that it does NOT fails. **Criteria (ii) and
  (iii) pass on the red leg by construction** — with `plan_policy.py` reverted the ordinary
  remedy is emitted unconditionally — which is exactly why they must live in the same module
  as (i): `run-verify.sh` runs the module, so the pair can only go green together and (iii)
  cannot degrade into a vacuous green. **Wave-2 bundle**: gate runs on the folded integration
  branch carrying children 1-2 (`PDCA_VERIFY_BASE`, `gates.py:379-397`), so the
  sibling-conflict count this child keys on exists on the base. No network or container.
- **Reproduction:** run `size_reasons` over a split child whose only churn features are
  sibling conflicts and inherited fields: it returns `oversized — consider `pdca split`
  first (…)`, the same advice its parent got, on a slice that is one function wide.
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/plan_policy.py`
  (the remedy selection), `template/src/pdca_harness/leaves.py` (the two prompt builders
  **only**), and `docs/07-crosscutting.md` — **restricted to `### The process`** (`:36-99`;
  the `splittable?` decision nodes in the flowchart at `:50` and `:59`, the remedy node at
  `:52`, and the prose at `:86-87`). Leave `### The estimate` (`:100-173`) to child-2 and
  `### The split` (`:174-218`) to child-4; child-3 and child-4 are scheduled into different
  waves precisely because they share this file. **Out of scope:** `sizing.py` (child-2 owns the
  signal and this child only consumes it), `split.py` and `cli.py` (child-4), making the
  size guard blocking — it stays advisory for the calibrated reason in its own docstring
  (`plan_policy.py:88-102`: 50% recall at 62% precision, and `hold` stays unimplemented).
- **External dependencies:** `copier importable (.venv)` — the patch changes files under
  `template/`, so the target's render and `copier update` compatibility root suites exercise
  it; without copier those seven tests skip themselves and T3 reports a green that tested
  nothing. Otherwise python3 ≥ 3.11 stdlib + git only; the test runs in the offline driver
  suite with no tracker, network or container.
- **Test file:** `template/tests/test_plan_policy_split_child.py` — a new module in the
  offline driver suite. The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`run-verify.sh:121-130`), so a new file earns its red. **Import the module, never the new
  symbols** — `from pdca_harness import plan_policy, sizing, split, leaves`, then attribute
  access inside test bodies; a module-level `from … import <helper>` raises ImportError on
  the red leg, giving 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:145`).
  Note that criterion (iii) must go red for the *right* reason: on the red leg the ordinary
  remedy is emitted anyway, so pair it with (i) in the same module so the pair can only pass
  together.
- **Difficulty:** medium
- **Depends on:** child-2
- **Conflicts with:** child-4
<!-- pdca:end child-3 -->

<!-- pdca:child child-4 -->
# split: report convergence before --accept files irreversible tracker issues

- **Slug:** split-convergence-report
- **Defect / goal:** `pdca split --accept` files real, unrevokable tracker sub-issues
  without ever running the estimate over the staged children. `preflight`
  (`split.py:224-245`) checks only the reasons acceptance would fail — a missing proposal, a
  parent already marked, ordering that names a non-sibling or forms a cycle
  (`_validate_ordering`, `:247-265`). Nothing asks the one question that matters: *does this
  split actually make the children smaller?* A split that leaves every child `oversized` is
  discovered one full cycle later, when each child's guard fires and the planner is pointed
  at `pdca split` again. Report it at the only point where it can still change the decision.
- **Success criterion:**
  (a) **both** acceptance paths emit the report before anything irreversible happens:
      `pdca split <id> --accept` (the auto-filing branch, which reaches `preflight` at
      `cli.py:733`) **and** `pdca split <id> --accept --ids a,b` (which calls
      `split.accept` directly at `cli.py:764` and never reaches `preflight` today). The
      `--ids` path is the one the docs call *required* for a tracker `pdca` cannot reach
      (`docs/07-crosscutting.md:192-197`) — i.e. the operator who has already paid for the
      issues by hand and most needs the verdict. Reproduced on the rejected attempt:
      `pdca split 500 --accept --ids 601,602` materialised both children and printed nothing
      but `issue_500 marked split; run `pdca flow 601 602``;
  (b) the report names, per staged child, its structural band against the parent's and which
      feature carries its score — `SizeEstimate.reasons` already carries this — and says
      plainly when the split does not lower the band for most children;
  (c) it is **not blinded by child-2's exclusion.** A `Conflicts with` edge *between*
      siblings is the splitter's statement that those two children edit a shared resource
      (`leaves.py:1274` calls those fields "the point"), so a proposal whose children all
      conflict pairwise is a split that separated nothing, and must be reported as NOT
      converged. The report therefore reads child-2's exposed sibling-conflict count rather
      than seeing an excluded 0 and reading the proposal as clean;
  (d) **its own output can never abort the acceptance.** A stderr that fails part-way — what
      `pdca split 500 --accept 2>&1 | head` produces — must not change the exit code or the
      set of bundles created. On the rejected attempt a `BrokenPipeError` from the second
      report line escaped `preflight` and produced either an unhandled traceback or the
      flatly *wrong* `split: issue_500 has no split-proposal.md — run `pdca split 500`
      first` with rc 1 on a bundle whose proposal was fine, because `cli.py:726-737` wraps
      `preflight` in an `except OSError` that means "no proposal". Guard these writes the way
      `cli.py:755-762` already guards
      its own (`except OSError: pass`), and cover it with a test that fails the stream;
  (e) it is **advisory and deterministic**: it never blocks, never prompts, and never
      changes what is filed or materialised — matching the size guard's warn-only stance and
      the same calibration argument (`plan_policy.py:88-102`).
- **Constraints (verified against `main`):** at `preflight` time the children have no
  tracker ids — every ordering ref is a sibling **label** by construction
  (`_validate_ordering`, `:247-259`), so a staged estimate must present those labels as the
  sibling set for child-2's exclusion to apply the same rule the live estimator will. Child
  labels are pinned to `child-\d+` by `_LABEL_RE` (`split.py:41`), so composing a temporary
  path from a label cannot traverse. Keep the ordering guarantee `preflight` exists for: it
  runs **before** `file_children` (`cli.py:733` then `:742`), and nothing added here may
  file, write into the instance, or leave anything behind on failure.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Falsifiability:** RED on `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_split_convergence`. Pre-fix no convergence report exists on either path, so
  every assertion on its output fails and the report helper raises `AttributeError`;
  criterion (d) is falsifiable by driving `preflight` with a stderr that raises on its second
  write and asserting the exit code and created-bundle set are unchanged — pre-fix that
  raises out. **Wave-3 bundle**: gate runs on the folded integration branch carrying children
  1-3 (`PDCA_VERIFY_BASE`, `gates.py:379-397`); note this child edits `split.py`, which
  child-1 also edited, and the folded base is precisely what makes that apply cleanly. Drive
  `split.preflight` / `split.accept` directly so no `gh`, network or container is needed.
- **Reproduction:** `pdca split <id> --accept` on any proposal — the children are filed and
  materialised with no estimate ever run over them; and `pdca split <id> --accept --ids a,b`
  never even calls `preflight` (`cli.py:764`).
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/split.py` (the
  report and its call site), `template/src/pdca_harness/cli.py` (the `--ids` path and the
  stderr guarding), `docs/07-crosscutting.md` — **restricted to `### The split`**
  (`:174-218`, the `pdca split` / `--accept` section, including the `--ids` prose at
  `:192-197`). Leave `### The process` (`:36-99`) to child-3 and `### The estimate`
  (`:100-173`) to child-2; child-3 and child-4 are scheduled into different waves precisely
  because they share this file. **Out of scope:** `plan_policy.py`, `sizing.py`,
  `leaves.py`; making the report blocking or interactive; changing what `--accept` files,
  validates or materialises; a `max_split_depth` cap (held in reserve deliberately — the
  earlier children remove the *reason* depth grows, a cap only truncates the symptom).
- **External dependencies:** `copier importable (.venv)` — the patch changes files under
  `template/`, so the target's render and `copier update` compatibility root suites exercise
  it; without copier those seven tests skip themselves and T3 reports a green that tested
  nothing. Otherwise python3 ≥ 3.11 stdlib + git only; the test runs in the offline driver
  suite with no tracker, network or container — in particular it must not require `gh`, so
  drive `preflight` / `accept` directly rather than through a filing path.
- **Test file:** `template/tests/test_split_convergence.py` — a new module in the offline
  driver suite. The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`run-verify.sh:121-130`), so a new file earns its red. **Import the module, never the new
  symbols** — `from pdca_harness import split, sizing`, then attribute access inside test
  bodies; a module-level `from pdca_harness.split import <helper>` raises ImportError on the
  red leg, giving 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:145`) instead
  of a red that proves anything.
- **Difficulty:** medium
- **Depends on:** child-2
- **Conflicts with:** child-3
<!-- pdca:end child-4 -->
