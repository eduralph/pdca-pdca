# Result — issue 472 / flow-adopt-core

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: exercised **through `cli._flow`** on byte-identical disk state:
  a run whose Plan/re-plan beat splits a drive-set bundle drives that bundle's children
  to a terminal state within the same call — in a wave AFTER the parent's, honouring
  their `Depends on` / `Conflicts with`, counted against ONE run-wide `max_passes`
  budget across original AND adopted waves (pool sized off the pre-adoption schedule —
  the converged v3 mechanics; live re-sizing is the sibling child's), each adoption
  announced on stderr with the child's REAL wave index from the recomputed schedule. A
  child with an unresolvable dependency is held loudly in the existing held-report
  shape, excluded from the results map, and the run continues — never aborts. Adoption
  is lineage-scoped and transitive (only descendants of the ids given), never a disk
  sweep; an adopted child that itself splits is re-adopted within the same shared budget
  — bounded, no recursion reset. Guards proven by test, not just present: a split-marked
  but NON-terminal parent (e.g. sign-off recorded `iterate-do`) does NOT have its
  children adopted; a parent whose lineage record is unreadable is reported and skipped,
  never a crash; a lineage child id that escapes the bundle root (e.g. `"../../etc"`) is
  skipped with a report; an id already in the run's drive set is not adopted twice —
  dedup against the batch, against a duplicate id within one record, AND against a child
  already taken by another parent adopted in the SAME wave (two parents splitting in one
  wave, the second's record also naming the first's child — the #469-v3 adversary's
  unpinned-`taken` mutation; the docstring's test citation must name this test).
  Demonstrable by C4-verify on the patch alone.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: adopt the children of a bundle that goes `close-disposition = split` while
  in the drive set — detect (read `split.read_lineage`; a parent with the marker but no
  readable record is reported and skipped, never a crash), validate
  (`waves.partition_schedulable` tolerance; held children reported in the existing
  "held this run — <reason>; left in-flight" shape and EXCLUDED from the results map),
  splice (children join after the current wave; pointed at the same per-target
  integration branch via the existing `_point_at_integration`; one run-wide `max_passes`
  pool across original AND adopted waves, sized as converged in v3; adopted children
  join the set `_warn_abandoned` / final sweep cover), report (stderr announcements
  with real wave indices) — on the unified drive path, so every CLI shape inherits it
  from one implementation. Includes the same-wave two-parents dedup test (v3 carry-
  forward 3) and the corrected docstring citation, and the ancillary
  `template/tests/test_verify_base.py` environment cleanup the v3 review accepted as
  discharging an iteration carry-forward, not scope expansion.
  / out of scope: **terminal-parent recovery** (a run handed an id ALREADY terminal on a
  split — the pre-run short-circuit stays for now; sibling child) and **shape-parity
  assertions against that recovery path**; **single-id stdout reporting of adopted
  dispositions** and **budget re-sizing on adoption** (sibling child); changing why
  recursive splits happen (#448's line — merely never enable an infinite one); a disk
  sweep in `flow_ids` (the distinction from the CSV sweep is deliberate and stays); the
  `--accept` hint printing `pdca flow <child-ids>` (still right for a split accepted
  outside a running flow); `waves.compute_waves` / `partition_schedulable` semantics
  (reused as-is); the split command, `split.accept`, or the lineage schema (#456 shipped
  it); publish/fold semantics beyond the existing reconciliation.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing the mid-run flow enhancement that adopts a terminal split parent's lineage children into later waves under one run-wide pass budget.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is bounded and falsifiable: adoption is mid-run, lineage-scoped, scheduled after the parent, and charged to one pool (`docs/07-crosscutting.md:243`, `docs/07-crosscutting.md:257`, `docs/07-crosscutting.md:319`). |
| C2 Reproduction (red pre-fix) | PASS | In an isolated clean `HEAD` with only the new test retained, all 27 tests executed and 26 failed on stranded children, including the CLI criterion at `template/tests/test_flow_adopt_split.py:322`. |
| C3 Change | PASS | The change stays on the unified drive path and performs adoption before the existing publish/fold boundary, while the ancillary environment cleanup is confined to its test fixture (`template/src/pdca_harness/flow.py:1430`, `template/tests/test_verify_base.py:74`). |
| C4 Verification (red→green) | PASS | The clean-base leg ran 27 tests with 26 failures and the patched target ran all 27 green; the focused same-wave mutation also failed its named adversary test (`template/tests/test_flow_adopt_split.py:1052`). |
| C5 Causal adequacy | PASS | The frozen-tail cause is removed by recomputing and replacing the un-driven schedule, then invoking that splice from the shared loop; no capability-probe or symptom guard was introduced (`template/src/pdca_harness/flow.py:1173`, `template/src/pdca_harness/flow.py:1434`). |
| T1 Structure | PASS | Adoption is factored once and reached from the common `_drive_and_act` wave loop, preserving entry-point parity (`template/src/pdca_harness/flow.py:1082`, `template/src/pdca_harness/flow.py:1434`). |
| T2 Shape | PASS | Independent docs lint and a 22-page rendered-link audit both passed, grounding the new operator contract at `docs/07-crosscutting.md:243`. |
| T3 Runtime | NEEDS-HUMAN | Accept the runtime baseline only after rerunning the 7 Copier-dependent render/update tests — Copier was absent here, so they all skipped even though 1,660 driver tests passed (`tests/test_render_and_run.py:23`, `tests/test_render_and_run.py:31`). |
| T4 Contribution | NEEDS-HUMAN | Approve release text only after inspecting `commit-msg.txt` and `pr-description.md` — neither artifact was supplied, so the asserted user-impact opener and tracker linkage cannot be independently rerun (`template/pdca.toml.jinja:985`). |
| T5 Judgment | NEEDS-HUMAN | Confirm no applicable closed/rejected prior work beyond the locally found #468 path history — artifact-only `git log --all` cannot settle tracker history, which matters to avoid reviving rejected flow semantics (`template/src/pdca_harness/flow.py:1434`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the adoption, held-child reporting, and fixed-pool behavior fit real operator workflows — the offline CLI suite verifies mechanics but cannot establish product fitness (`template/tests/test_flow_adopt_split.py:322`). |

### Advisory — adversary

# Adversarial review — issue_472 (flow-adopt-core)

Re-ran the asserted red→green at `$PDCA_TARGET` rather than trusting it. Green leg:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split` → **27/27 OK**.
Red leg (production hunks reverted to `3e3b829`, test kept — the C4 shape): **26 of 27 FAIL**;
the single survivor is `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`
(`template/tests/test_flow_adopt_split.py:503`), which is a no-regression guard and is
*supposed* to be green pre-fix. Full driver suite on the target: 1660 tests, OK (skipped=2);
stable across five `PYTHONHASHSEED` values. The tests drive the real `cli._flow` and build
fixtures with the production `split.accept` — the spies at `template/tests/test_flow_adopt_split.py:258`
and `:284` are pass-throughs that return the production value, not re-implementations. I could
not find a tautology or a mocked-away defect in the evidence.

## Findings

- **NEEDS-HUMAN [impl] —** `template/src/pdca_harness/flow.py:1177` (with `:1041`): the feature's
  central promise — "a split must never be able to abort the flow that caused it"
  (`flow.py:1030`) — has **no test at all**, and I proved it by mutation. Three mutants survive
  the entire new 27-test suite: (a) delete the `if tail is None:` guard at `flow.py:1177`;
  (b) narrow `_reschedule`'s deliberately-broad `except Exception` at `flow.py:1041` to
  `except ZeroDivisionError`; (c) make `_real` (`flow.py:831`) re-raise instead of returning
  `None`. Each ran `Ran 27 tests … OK`. Mutant (a) is not cosmetic: with `waves.partition_schedulable`
  made to raise mid-splice, `pdca flow 500` dies with an uncaught
  `TypeError: must assign iterable to extended slice` out of `_drive_and_act` — the run aborts,
  wave 0's completed work is never reported, and rc is a traceback. The unmutated code is
  correct here (I verified it: rc 0, `flow: could not re-wave the run after a split (RuntimeError: …)`
  + `flow: the children of issue_500 could not be scheduled; they are left in-flight …`, no
  traceback, children left PLANNED) — the defect is that nothing pins it, so the one contract
  the brief calls out as "never aborts" is the one contract a rebuild could silently break.
  Cheap fix: one test that forces `_reschedule` to return `None` (patch `flow.waves.partition_schedulable`
  to raise) and asserts rc, both stderr lines, and `assertNotIn("Traceback", err)`.

- **NEEDS-HUMAN [human] —** `template/src/pdca_harness/cli.py:657` and `:661`: the **single-id
  exit code silently flipped 0 → 1** while its stdout is byte-identical. Concrete case — exactly
  the scenario of `template/tests/test_flow_adopt_split.py:407`: `pdca flow 500 --max-passes 3`
  where 500 splits into 601/602 and the pool stops before 602's wave. I ran it on both legs:
  post-fix stdout is `COMPLETE\t<root>/results/issue_500` with **rc 1**; pre-fix (HEAD) the same
  command prints the same line with **rc 0**. `_report_single` prints only `results[iid]`
  (`cli.py:657`) but derives rc from the *whole* map (`cli.py:661`), which now carries adopted
  children — so an operator (or `pdca flow 500 && …` automation) reads "COMPLETE" and gets a
  failure code with nothing on stdout naming 602. No test in the bundle asserts rc for a
  single-id run with an unfinished adopted child (`:407` and `:422` both discard `self._cli`'s
  return). The brief parks "single-id stdout reporting of adopted dispositions" with the sibling
  child but says nothing about the exit code; the human has to decide whether the rc may move
  ahead of the reporting, or must stay scoped to named ids until the sibling lands. Note the
  asymmetry this creates with the *held*-child contract, which the code deliberately keeps at
  rc 0 (`test_a_children_entry_that_is_not_an_id_is_reported_not_dropped_silently:815` exits 0
  with two briefed children left PLANNED): "this run created work it could not finish" is rc 1
  in one shape and rc 0 in the other.

## Attacks that failed (stated so the negative result counts)

- **Mutation-tested the guards the brief names.** All caught, most by ≥2 tests:
  `known=batch_names | taken` → `known=batch_names` (the #469-v3 adversary's mutation, 2 failures);
  resolution-aware containment → lexical `d.parent == cfg.bundle_root` (1);
  drop the `len(entries) > len(ids)` malformed-entry report (1); drop the `seen_real`
  resolved-path dedup (1); drop the retraction block (1); drop the `named` exclusion from the
  retraction predicate (1); drop the terminal half of `_is_split_parent` (1);
  `min(allowance, budget - spent)` → `allowance` (2); `wave_of` → hardcoded `k + 1` (4);
  `scheduled = children` i.e. put held children in the map (4); `bundles += []` (4);
  delete the `spent >= budget` break (3); `_PLAIN_ID` → `.+` (1); drop the alias `owner` lookup (1).
- **The pool-sizing claim** at `flow.py:1385` / `config.py:312-324` ("a run that adopts nothing
  can never reach the pool") — I could not construct a counterexample: every wave spends
  ≤ `min(allowance, budget - spent)` ≤ `allowance`, `_drive_wave` returns `used` on *all three*
  exits (`flow.py:1274`, `:1304`, `:1313`), `wave_list` only grows via the splice, and
  `cli.py:572` / `config.py:675` floor `max_passes` at 1 so `budget - spent ≥ 1` at the call site.
- **The "same end state" claim** at `flow.py:1370-1379` (a named id held by the tolerant re-levelling
  vs. skipped by `_runnable`). I tried to break it with a `Depends on (merged)` prereq that
  `merged.is_merged` accepts but that is not COMPLETE on disk — unreachable, because
  `waves.check_dep_graph` (`waves.py:77`) already raises on that brief before any wave runs, on
  both legs. Every reachable divergence I could build ends PLANNED-in-the-map-and-rc-1 either way.
- **Doc claim "the CSV batch alike"** (`docs/07-crosscutting.md`, `planner.md.jinja`): untested in
  the bundle, so I probed it directly — `flow.flow_batch` returns `{'500': COMPLETE, '601': COMPLETE,
  '602': COMPLETE}` with both adoption announcements. The claim is structurally true via
  `_drive_and_act`; not a refutation.
- **Every `path:line` citation added by the diff** (24 of them, across `flow.py`, `cli.py`,
  `config.py`, `split.py`) resolves to the line it claims on the target — including the three the
  previous iterations got wrong (`config.py:686` for the clamp, `flow.py:1429` for the `min`,
  `flow.py:1310` for the per-wave allowance message). The docstring test citations
  (`test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once`,
  `test_a_shared_child_the_reschedule_holds_is_not_reported_as_driven`,
  `test_a_symlinked_alias_of_a_bundle_this_run_drives_is_driven_once`) all name tests that exist.
- **In-root symlink aliasing an *un-driven* bundle** — noted, not filed. `results/issue_601` →
  `results/issue_999` (briefed, in-flight, not in the drive set) is adopted and driven, and the
  map reports `'601': COMPLETE` while the directory that actually completed is `issue_999`
  (`flow.py:861-864` accepts it by design; `flow.py:1000`'s `driven` map only covers the drive
  set). I am **not** scoring this as a refutation: `pdca flow 601` does exactly the same thing on
  HEAD, so it is pre-existing parity, and the iteration-4 sign-off explicitly narrowed this to the
  "one directory, two lanes" case that the patch does close.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T3 Runtime — Accept the runtime baseline only after rerunning the 7 Copier-dependent render/update tests — Copier was absent here, so they all skipped even though 1,660 driver tests passed (`tests/test_render_and_run.py:23`, `tests/test_render_and_run.py:31`).
- [x] T4 Contribution — Approve release text only after inspecting `commit-msg.txt` and `pr-description.md` — neither artifact was supplied, so the asserted user-impact opener and tracker linkage cannot be independently rerun (`template/pdca.toml.jinja:985`).
- [x] T5 Judgment — Confirm no applicable closed/rejected prior work beyond the locally found #468 path history — artifact-only `git log --all` cannot settle tracker history, which matters to avoid reviving rejected flow semantics (`template/src/pdca_harness/flow.py:1434`).
- [x] Validation — fitness-to-purpose — Decide whether the adoption, held-child reporting, and fixed-pool behavior fit real operator workflows — the offline CLI suite verifies mechanics but cannot establish product fitness (`template/tests/test_flow_adopt_split.py:322`).
- [x] size backstop — this slice is behaving oversized: 4 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [x] `flow.py:1001` (`wave_list[k + 1:] = tail`, splice) with the
- [x] `cli.py:794`: `pdca split <id> --accept` — the command the Plan /
- [x] Fitness-to-purpose, for sign-off: a first-reschedule-held child is
- [x] T4 in `check-gates.json` is the one gating row that carries an

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- issue_472: T3 ran without copier again (7 render/update tests skipped, green-by-skip) — recurring across bundles; make the gate environment install copier (extra_bootstrap exists) or fail loudly when the render suites skip.
- issue_472: the "a split never aborts the flow" contract (`flow.py:1177`/`:1041`/`:831`) is correct but unpinned — three mutants survive all 27 tests; add one test forcing `_reschedule` to fail and asserting rc + stderr + no traceback.
- issue_472: single-id `pdca flow` rc silently flips 0→1 when an adopted child is unfinished while stdout stays byte-identical (`cli.py:657`/`:661`) — decide rc scoping vs. the held-child rc-0 contract when the stdout-reporting sibling lands.
- issue_472: a bundle that declares `Depends on <split parent>` shares a wave with the parent's adopted children (levelled by its own edges, not re-pointed) — documented as out of scope; consider a `waves` semantics issue for re-pointing dependents at split children.
- issue_472: `pdca split --accept` still prints the `pdca flow <child-ids>` hint even when accepted inside a running flow that will adopt the children itself — following it races the run (no per-bundle lock); consider making the hint conditional or adding a drive-path lock.
