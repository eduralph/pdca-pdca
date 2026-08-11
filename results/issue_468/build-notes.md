# Build notes — issue #468 / flow-entrypoint-parity (iteration 3)

Target: `eduralph/pdca-harness` @ `main`, base **f7876f2** (verified:
`git rev-parse HEAD` in `$PDCA_WORKTREE` == `git rev-parse origin/main` == `f7876f2`).
All edits made in `$PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt`; the host's
primary checkout was not touched.

---

## 1. What the carry-forward actually asked for

Two `## Iteration N — carry-forward` blocks are on the brief. Their quoted sign-off lines
are the **auto-iterate rationale** (the driver quotes one §6 line), so I went to the
archived reviews for the substance:

* `iteration-v2/check-review.md` — the round-2 verdicts. Three FAILs share one root cause:
  * **C3** — "A skipped DISCONTINUED id is removed at `flow.py:1100`, so DISCONTINUED
    alone returns rc 1 but the same disk state plus a completing filler returns rc 0 and
    reports `1/1 complete`".
  * **C5** — "Arity-dependent authority remains: single-ID reporting reconstructs a
    filtered terminal result from disk at `cli.py:654`, while batch reporting sees only
    the incomplete map".
  * **T1** — "The decision still has two inputs — the returned map and a single-only disk
    fallback at `cli.py:649`".
  * **C4/T5** — the round-2 test left the batch rc (`_rc2`) unasserted, so the divergence
    passed under a green test.
* `iteration-v1` — T3 "provisional green" because **Copier was absent** in that review
  environment and all 7 root render/update tests skipped; and T4 (contribution artifacts
  not supplied). Both handled in §6 below.

So round 2's structure (one CLI route, one map, two presentations) was right, and its
**map was wrong**: `flow_ids` returned only the bundles it *drove*, so the CLI had to
invent a disposition for every id the drive path skipped — and the two shapes invented
different ones. Round 2 patched the symptom at the reporting layer (a single-id-only disk
fallback). This round removes the cause.

## 2. The change

**One drive path, and a map that is TOTAL over the ids it was given.**

* `flow.flow_ids` now answers for **every requested id**, driven or skipped
  (`flow.py:1113`, `:1130`, `:1132` post-patch; the filter it replaces is `flow.py:1033-1046`
  on f7876f2). A skipped id's disposition is `state.state(d)` — the identical value
  `_drive_and_act` records for a bundle it *did* drive (`flow.py:918` on f7876f2), so the
  two kinds of entry are indistinguishable to a consumer, which is the point. Contract
  written into the docstring (`flow.py:1069-1079`).
* `cli._flow` routes **every** non-empty id list through that one call inside one
  `except flow.PreflightError` (`cli.py:604-620`), then picks a *presentation*:
  `_report_single` or `_report_batch` (`cli.py:622`). Both read `results` and nothing else.
* One exit rule, `_results_rc` (`cli.py:630-641`), used by both presentations. The single
  documented shape difference is now a **parameter**, not an emergent property of two code
  paths: single-id adds `AWAITING_SIGNOFF` to the OK set (`cli.py:661`), the batch rule
  stays "0 iff all COMPLETE/RESOLVED" (`cli.py:664-679`, unchanged semantics, brief: out of
  scope to change).
* `_report_single` **indexes** `results[iid]` (`cli.py:656`). No `.get`, no disk fallback —
  that fallback *was* the second authority C5/T1 named.
* Terminal recovery advice moved onto the shared path and made lineage-aware:
  `flow._terminal_hint` (`flow.py:691-727`) + `flow._lineage_children` (`flow.py:671-688`),
  printed by the one terminal filter (`flow.py:1121-1127`). A record carrying a `children`
  key is a split parent (`split.py:392-395`), so the destructive `rm -rf` advice is
  suppressed by the key's *presence* and the recovery names `pdca flow <child-ids>`.
* Dead import dropped: `cli.py` no longer uses `sources` (its only two uses were in the
  deleted short-circuit, `cli.py:617-618` on f7876f2).
* `flow.flow`'s docstring now records the seam (`flow.py:380-388`): it is the single-bundle
  *library* driver, not a CLI route, and anything that must report/exit on a disposition
  belongs on `flow_ids`. A test pins that `cli._flow` never calls it again.

Existing tests updated to the new contract (3 files, 37 changed lines): the three
`flow_ids` "skipped ids are absent from the map" assertions
(`test_flow_slice.py:404-418`, `:507-521`, `:522-529`), the RESOLVED one
(`test_state_resolved.py:145-154`), and the two CLI plumbing mocks that stubbed
`flow.flow` (`test_flow_slice.py:1718-1728`, `test_autoiterate.py:771-782`). Each still
asserts what it asserted before — "not driven" — but reads it off the disposition instead
of off an absence.

## 3. What I ruled out, with the measured cost

**(a) Repair the report layer again (round 2's shape), e.g. give `_report_batch` the same
disk fallback `_report_single` had.** Rejected on principle, not cost: it keeps *two*
inputs to one decision (the map + a disk read) and only makes them agree today. The brief
names an invariant to restore, so the target is the smallest change that restores it, not
the smallest diff. Cost is irrelevant when the alternative leaves the cause in place.

**(b) Make `flow.flow` a thin wrapper over `flow_ids` (the brief's other offered option),
so there is literally one cycle implementation.** Attractive, and I *measured* it rather
than guessing: I applied the wrapper (12-line body replacing `flow.py:367-425`) and ran
the offline suite.

```
$ cd template && PYTHONPATH=src python3 -m unittest discover -s tests
FAILED (failures=3, skipped=2)
  FAIL: test_flow_slice.FlowSlice.test_c6_blocks_accept_with_open_needs_human
  FAIL: test_flow_slice.FlowSlice.test_discontinue_disposition_without_c6
  FAIL: test_flow_slice.FlowSlice.test_iterate_do_then_complete
```

All three fail for one reason: they inject a decision by patching `leaves.run_signoff`
(the per-bundle leaf), and the wave path signs off through `leaves.run_signoff_batch`,
which loops `leaves._stub_signoff` in stub mode (`leaves.py:2993-3003`). Repairing them
means re-pointing three C6 / discontinue / iterate regression tests at a **stub internal**
(`leaves._stub_signoff`) instead of the documented leaf — i.e. paying for the unification
by weakening the three tests that guard the C6 accept-guard. The brief explicitly leaves
this choice to Do ("or `cli._flow` routes `len(ids) == 1` through the batch machinery —
Do's call, provided the parity is by construction"), so I took the option that does not
spend those three. The hole it leaves — a future contributor wiring `flow.flow` back into
a CLI route — is closed by a test, not a comment:
`test_single_id_routes_through_flow_ids_and_never_flow_flow` fails if `cli._flow` calls
`flow.flow` at all.

**(c) Delete `flow.flow` outright.** Cost = (b) plus migrating 12 call sites in three test
modules (`test_flow_slice.py`, `test_signoff_orphan.py`, `test_sweep.py`) to
`flow.flow_ids(cfg, [id])[id]`. Same weakening as (b), more churn, no extra invariant over
(b).

## 4. Behaviour deltas a reader should see (all deliberate)

1. **`pdca flow <terminal-id>` now prints its disposition on stdout**, not stderr — it is
   the same `state<TAB>path` line every other single-id run prints. Pre-fix the
   short-circuit printed to stderr (`cli.py:606-607` on f7876f2). Automation reading
   stdout now sees a terminal bundle it previously had to scrape from stderr.
2. **`pdca flow <ids…>` now reports and counts ids it skipped.** `flow DISC FILLER` prints
   `1/2 complete` and exits 1 where it printed `1/1 complete` and exited 0. That *is* the
   defect C3 named; the new number is the honest one.
3. **An id the Plan pre-pass could not brief now exits 1 on the batch shape too.** Both
   shapes still auto-plan an unbriefed id (`plan_missing=True`); if the planner briefs
   nothing, the id reports `UNPLANNED` and the run exits 1 — which is what the single-id
   shape has always done (`flow.flow` → `_plan_if_unplanned` false → `UNPLANNED` →
   `cli.py:648` on f7876f2 → rc 1) and what the batch shape used to hide by dropping the
   id from its map.
4. **A single id with an unresolvable `Depends on` now raises `ValueError` from
   `waves.check_dep_graph`** instead of being driven, because it takes the batch path
   (`flow.py:1132` → `_drive_and_act` → `compute_waves`). Same disk state, same behaviour
   on both shapes — which is the invariant — and the batch shape already did this
   (`test_flow_slice.py:1084-1090`). Neither shape prints a friendly message for it; that
   is pre-existing for the batch shape and out of scope here.
5. **One narrowing.** Pre-fix, `pdca flow <id>` returned **1** when the tracker said the
   issue was REOPENED *and* `sources.clear_resolved_marker` failed (`cli.py:618-622` on
   f7876f2). The shared path prints the same loud failure (from
   `sources.clear_resolved_marker`, `sources.py:203-205`) and then reports the bundle
   RESOLVED → rc 0. I did **not** re-add the rc-1 check in `cli._flow`: the brief is
   explicit that this decision must live once, on the shared path ("RESOLVED revalidation
   already exists in `flow_ids` at `flow.py:1005-1016` — do not duplicate it"), and the
   batch shape already exited 0 here. The trigger is an `OSError` on a single `rename`, so
   it is rare; the message is unchanged and loud. **Worth a glance at sign-off** — it is
   the one place where converging the two shapes chose the batch shape's weaker signal.

## 5. Refuting my own test (forced, recorded)

**(a) Genuine red?** Yes — proven by the project's own C4 gate, which reverts *only* the
production hunks and keeps the tests:

```
$ PDCA_WORKTREE=… PDCA_BUNDLE=… ./engine/scripts/run-verify.sh
== C4 green leg: … template/tests/test_flow_entrypoint_parity.py …
Ran 11 tests … OK          (and 60 + 98 + 28 in the three edited modules: OK)
== C4 red leg: bundle test(s) with the production change reverted
Ran 11 tests in 0.064s
FAILED (failures=11, errors=1)     ← 7 tests + 4 subTests, plus the PreflightError case
C4 PASS: red without the fix, green with it        (gate rc 0)
```

The red leg **imported** the module (no `unittest.loader._FailedTest`, which
`run-verify.sh:140-143` would have classified PDCA-UNVERIFIABLE): the test imports modules
only, never new symbols, per the brief. Two of the eleven tests are green on both legs by
design — `test_in_flight_bundle_agrees_across_shapes` and
`test_single_id_awaiting_signoff_presentation_preserved` assert *preserved* behaviour, so
a red there would mean I broke something.

**(b) Production path?** Yes. Every drive goes through `cli._flow` — the production CLI
entry — into production `flow.flow_ids` → `_drive_and_act` → `driver`/`leaves`. The leaves
are stubbed by **config** (`LeafConfig(mode="stub")`), which is the harness's own offline
mode, not a re-implementation. Fixtures are built with production code too: `leaves.do_plan`
for a brief, and a real terminal split parent via production `split.accept`
(`split.py:525`) — which writes the `children` lineage edge and the close marker — then
driven terminal through `cli._flow` (round 2 built that fixture with `flow.flow`; this
round uses no `flow.*` call anywhere, in fixtures or drives). Only three tests inject
anything, and each injects at the seam it is measuring: two spy on `flow.flow_ids` /
`flow.flow` to observe *routing*, one stubs the sign-off leaf to play "the human walked
away".

**(c) Fixture includes the fault?** Yes, and this is where round 2 leaked. Both shapes now
run against a **byte-identical fork of one seed tree** (`_fork` copytrees the whole root),
and the seed *contains the filler bundle in both forks* — the single-id run simply leaves
it untouched. So the multi-id run is not a differently-populated disk. The bundle under
test is the real failing element in each case: a really-DISCONTINUED bundle (driven there
through the CLI with a discontinue decision), a real RESOLVED marker, a real split parent
with a real `children` edge. And `_assert_parity` asserts the **batch rc** explicitly —
`rc2 == rc1` with a COMPLETING sibling — which is precisely the assertion round 2 omitted
(`iteration-v2/.../test_flow_entrypoint_parity.py:264`, the reviewer's C4/T5 finding).
Dispositions are read from **stdout only** (no stderr fallback), so a shape that omits the
id from its map cannot pass by having printed a skip note.

**Extra refutation — is it red on the REJECTED approach, not just on the base?** A test
that only distinguishes "base" from "my patch" would not have caught round 2. So I checked
directly: stashed this patch, applied `iteration-v2/patch.diff` to the clean base, dropped
**this** test module in, and ran it.

```
$ cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_entrypoint_parity
FAILED (failures=8)
  AssertionError: None != 'DISCONTINUED' : multi-id shape must report DISCONTINUED for
  DISC468 — a skipped id still belongs in the results map both shapes present
  … (COMPLETE, RESOLVED, split parent, and the 4 malformed-lineage subTests, same cause)
```

Eight of eleven fail on the round-2 patch, every one of them on map totality — the exact
defect C3/C5/T1 named. (Working tree restored afterwards: `git stash pop`, and the
regenerated `git diff` is byte-identical to the shipped `patch.diff`.)

## 6. The two standing NEEDS-HUMAN items from earlier rounds

**T3 / Copier (iteration 1).** Not reproducible here and no dependency is missing: copier
**9.17.0** is importable from `.venv` (the instance already registers this as a *required*
`[[doctor.checks]]` row, `pdca.toml:809-814`), and the render/update leg genuinely ran —
`== T3: template-repo suite (render + update-compat) / Ran 7 tests in 21.9s / OK`, no
skips — alongside the driver suite (`Ran 1633 tests … OK (skipped=2)`; both skips
pre-existing, none in the new module). Full log: `gate-logs/T3-suite.log`. Nothing to
declare — no NEEDS-HUMAN external dependency for this contribution.

Note on the brief's expected pre-existing red: the 11 `test_verify_base.py` failures appear
only when `PDCA_VERIFY_BASE` is inherited into the run. I ran every gate with `env -u
PDCA_VERIFY_BASE …`, and the suite is clean — confirming the brief's diagnosis that it is
an environment-isolation fault, not a code red.

**T4 / contribution artifacts (iterations 1 and 2).** This one Do genuinely cannot clear,
and I did not fake it. `commit-msg.txt` and `pr-description.md` are drafted by the
**publisher leaf at publish**, i.e. after sign-off; at Check time the T4 row therefore has
no subject. On the target, `cli._contribcheck` already declares that deferral
(`cli.py:1070-1094` on f7876f2, issue #401) instead of a bare green — but this *instance*
vendors a pre-#401 engine, so `./scripts/pdca contribcheck` exits 0 silently here (I ran
it: `T4 RC=0`, no output) and Check records a plain `pass` the reviewer cannot reproduce.
That gap is an instance-side engine update (an Act item for pdca-pdca), not something this
contribution to the target can change.

What the maintainer checks at sign-off, and the drafts that satisfy it (from
`docs/INTEGRATION.md` §8) — offered as *input for the publish leaf*, deliberately **not**
written into the bundle, because `publish.draft_texts` only drafts what is absent
(`publish.py:101-103`) and writing them here would silently pre-empt the publisher leaf:

* Commit subject (conventional, ≤72, imperative), body, and the two required trailers:

  ```
  fix(flow): report every requested id from one results map

  `pdca flow <id>` and `pdca flow <id> <id>` ran different machinery: the single-id
  route short-circuited on disk state and read a bare state string from `flow.flow`,
  while the batch route reported a results map — so the same bundle could get two
  dispositions and two exit codes. Route both shapes through `flow.flow_ids`, make its
  map total over the ids it was given, and derive both presentations and both exit
  codes from that one map. A terminal split parent is no longer told `rm -rf` (that
  deletes the only on-disk record of the split); it is told to drive its children.

  Signed-off-by: Eduard Ralph <eduard@ralphovi.net>
  Fixes #468
  ```
* PR body must open with a non-empty `**User impact:**` line *before* Root cause, and
  carry `Closes #468` (the `require-linked-issue` check). Suggested opener: "**User
  impact:** `pdca flow <id>` and `pdca flow <id> <id>` now report the same disposition and
  the same exit code for the same bundle, and a split parent is never told to `rm -rf`
  itself."

## 7. Gates run here (all through the project's own runners)

| Gate | Command | Result |
|---|---|---|
| C4 | `./engine/scripts/run-verify.sh` | **PASS** — red without the fix, green with it (rc 0) |
| T3 | `./engine/scripts/run-suite.sh` | root suite OK (7 render/update, no skips), driver suite OK (1633) |
| T2 | `./engine/scripts/run-docs-check.sh` | `lint_docs: OK`, `render_site: link audit OK` (22 pages) |
| T4 | `./scripts/pdca contribcheck` | rc 0 — no subject yet (see §6) |

Commit-readiness: the target has **no** formatter, linter, pre-commit config or
`core.hooksPath` (checked: no `pyproject.toml` / `.flake8` / `.pre-commit-config.yaml`, no
lint job in `.github/workflows/`), so "commit-ready" means matching the file conventions.
Verified: `git diff --check` clean, `python -m compileall` clean on all six files, and no
added line exceeds 95 characters (the convention in these modules).

## 8. Out of scope, untouched

Split-child adoption (children of the split parent stay PLANNED here); `_drive_and_act`'s
wave/fold/budget semantics; `waves.py`; `split.py`; publish and Act; `flow_batch`'s return
shape (its caller passes no ids, so it can only be told what was driven — the docstring at
`flow.py:1073-1079` says why the two differ); and `_report_batch`'s multi-id exit rule.
