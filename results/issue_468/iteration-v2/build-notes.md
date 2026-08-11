# Build notes — issue #468 (flow entrypoint parity) — **iteration 2**

Target: `eduralph/pdca-harness @ main`, base `f7876f2`. All edits made in
`$PDCA_WORKTREE = /home/eddie/pdca/pdca-harness.pdca-wt`. Pre-fix citations are `f7876f2`
line numbers; post-fix citations are the patched worktree.

---

## 0. What changed since iteration 1 (the carry-forward)

The previous attempt was rejected on **C3 FAIL / T5 FAIL**, one concrete defect:

> `children = 7` makes `cli._flow` raise `TypeError` because the new formatter joins an
> unvalidated value at `flow.py:670` — contradicting the nonfatal-malformation contract at
> `split.py:376`.

That finding is correct and is fixed at its cause, not guarded at the symptom:

* **`flow._lineage_children` (`flow.py:662-680`)** — a value-level tolerant reader that
  mirrors the target's own peer pattern, `split._recorded_depth` (`split.py:405-421`,
  *"the reader abstains on a file it cannot parse; this abstains on a VALUE it cannot
  compute with … tolerating the file but not its contents would only move the throw one
  line down"*). Non-list values, non-string entries and empty strings are dropped; nothing
  raises.
* **`flow._terminal_hint` (`flow.py:682-719`)** — the predicate for "this is a split
  parent" is now the **presence of the `children` key**, not the usability of its value. So
  a record with `children: 7` still suppresses the destructive `rm -rf` advice (the brief's
  criterion is literally *"a lineage record with a `children` key* is never told `rm -rf`"),
  and only the *naming* of the ids degrades. A hand-edited provenance file changes the
  hint, never the run.
* **Bound by a test**, not just by inspection:
  `test_malformed_lineage_children_degrades_the_hint_not_the_run` drives `cli._flow` over
  four hand-edited records (`7`, `"469"`, `[1, None, {}, ""]`, `[]`). Re-introducing
  iteration 1's naive `" ".join(record["children"])` turns three of the four red — see §5(a).

Two further improvements over iteration 1, both prompted by re-reading its diff rather than
by the review:

* Iteration 1 **deleted** the #302 RESOLVED remediation text with the CLI short-circuit and
  weakened `tests/test_state_resolved.py:422` from `assertIn("resolved outside a cycle")`
  to `assertIn("already terminal (RESOLVED), skipped")`. This patch **moves the text onto
  the shared path** (`flow._terminal_hint`, `flow.py:707-716`) instead, so
  `test_state_resolved.py` is **untouched and still green** — and the guidance a single-id
  operator used to get is now given on *both* shapes. Parity in the direction that keeps
  the guidance, not the one that drops it.
* Iteration 1 left `tests/test_autoiterate.py:773` mocking `cli.flow.flow`, which after the
  routing change no longer intercepts anything — that flag-plumbing test silently began
  driving a full stubbed cycle. Re-pointed at `flow_ids` (`test_autoiterate.py:774-780`).

The other two carry-forward items were **environmental, not patch defects**; evidence for
the human is in §6.

---

## 1. The defect, and where it lived

`cli._flow` routed the two CLI shapes through structurally different machinery:

| | single id (`f7876f2`) | several ids (`f7876f2`) |
|---|---|---|
| pre-run gate | short-circuit on raw disk state, `cli.py:605-636` | none (`flow_ids` decides) |
| drive call | `flow.flow(...)` → **state string**, `cli.py:639` | `flow.flow_ids(...)` → **results map**, `cli.py:652` |
| `PreflightError` | **uncaught** — traceback out of `cli._flow` | caught → rc 1, `cli.py:655-657` |
| report + exit | derived from that one string, `cli.py:641-648` | derived from the map, `_report_batch`, `cli.py:660-674` |

The asymmetry is the defect (five iterations of #449 broke the contract by a new route each
round). Its sharpest symptom: a terminal **split parent** — a bundle whose
`split-lineage.json` carries a `children` edge (`split.py:392-395`, written by
`split.accept`, `split.py:525`) — was told `rm -rf <bundle>` (`cli.py:607`), which destroys
the only on-disk record of the split (`split.py:38-47`) and orphans the children.

## 2. The change

**`cli.py`** — one route, two presentations:

* `cli.py:604-620` — both shapes now make the **same** `flow.flow_ids(cfg, ids,
  plan_missing=True, …)` call inside the **same** `try/except flow.PreflightError`. There is
  exactly one call site left; the arity only chooses a presentation
  (`_report_single` / `_report_batch`, `cli.py:620`).
* `cli.py:605-636` (the COMPLETE short-circuit **and** the duplicated RESOLVED
  revalidation) — **deleted**. Both decisions already live once on the shared path:
  RESOLVED revalidation at `flow.py:1070-1079`, the terminal skip at `flow.py:1100-1105`.
  Nothing is duplicated, so nothing can drift. `sources` is no longer imported by `cli.py`
  (`cli.py:22-24`); it was used only inside the deleted block.
* `cli.py:625-639` — `_FLOW_OK` + `_results_rc`: **one** exit-code rule over the results
  map, used by both shapes. The single documented difference (a single-id run counts
  `AWAITING_SIGNOFF` as a successful stop-for-the-human) is now a named argument in one
  place, instead of an emergent property of two drive paths.
* `cli.py:642-659` — `_report_single`: the preserved single-id presentation, **derived from
  the map** — the `state<TAB>path` line, the §6 NEEDS-HUMAN listing, rc 0 at
  AWAITING_SIGNOFF. An id the shared drive skipped as already-terminal never enters the map,
  so its disposition is read from disk — the *same* value `_drive_and_act` records for a
  bundle it did drive (`flow.py:976`). The CLI never re-decides *whether* to drive; only
  `flow_ids` does.
* `cli.py:662-673` — `_report_batch` keeps its table and its rule, now expressed as
  `_results_rc(results)`.

**`flow.py`** — one lineage-aware recovery hint on the shared terminal filter:

* `flow.py:1100-1105` — the terminal-skip note gained a second, indented line: the recovery
  advice, from `_terminal_hint`. Because both CLI shapes reach this one print, the advice
  cannot differ by arity — which is exactly how `rm -rf` came to be printed at a split
  parent on one shape and not the other.
* `flow.py:682-719` — `_terminal_hint`: split parent → name the children
  (`pdca flow 469 470`) and *do not delete*; RESOLVED → the #302 round-15 reopen
  remediation, verbatim from the deleted `cli.py:631-635`; COMPLETE → the ordinary redo hint
  (`rm -rf` is correct and non-destructive for a bundle with no lineage record);
  DISCONTINUED → nothing (as before).
* `flow.py:662-680` — `_lineage_children`, §0.
* `flow.py:28-30` — `flow` now imports `split` (no cycle: `split` imports only `state`,
  `split.py:35`).

**Tests that had to move with it** (both are implementation-detail mocks of the *drive entry
point*, not weakened assertions):

* `tests/test_flow_slice.py:1711-1720` — `MaxPassesConfig._run_cli` mocked `cli.flow.flow`
  and asserts `driven.called`; re-pointed at `flow_ids`. Same assertion, new entry point.
* `tests/test_autoiterate.py:774-780` — same, §0.

`tests/test_state_resolved.py` is deliberately **not** touched (§0).

## 3. Alternatives considered, with their cost

**(A) Make `flow.flow` a thin wrapper over `flow_ids`** (the brief's other suggested shape).
Rejected on a measured cost: `flow.flow` has **12 call sites across 3 test modules**
(`test_flow_slice.py` ×9 — lines 68, 89, 107, 157, 164, 1423, 1425, 1430, 1434;
`test_sweep.py`:350,364; `test_signoff_orphan.py`:272), **8 of which bind its string
return** (`final = flow.flow(...)`; `assertEqual(final, state.X)`). Changing its return type
edits all 12; keeping the signature means unwrapping the map back into a string inside
`flow.flow` — which *preserves* the "results map → state string" seam the brief asks to
remove, and adds a second entry into `flow_ids` for the CLI to pick between. My route edits
**2 mock targets (5 changed lines in 2 test files)** and deletes the seam outright.

**(B) Keep both drive paths; add a lineage check to the single-id short-circuit.** ~6 added
lines in `cli.py` — cheaper than this patch's +65/−64 in `cli.py`. Rejected, and not on
cost: the brief names an invariant to restore ("both shapes do the same thing to the same
disk"), and the smallest change that restores an invariant is not the smallest diff
(`docs/principles.md` §1.2, §2). (B) restores nothing — it adds a *sixth* special case to
the very branch whose accumulation of special cases is the defect, and leaves the
state-string/results-map divergence, the missing `except PreflightError`, and the
pre-run-disk-state gate untouched. It would also have to be repeated for every future
terminal class.

**(C) Put the tolerant `children` accessor in `split.py`** (next to `_recorded_depth`, its
natural home). Rejected: the brief puts `split.py` out of scope. The accessor lives in the
consumer (`flow.py:662`) and cites the pattern it mirrors.

**(D) Include terminal-skipped ids in `flow_ids`'s results map** so the single-id shape
needs no disk fallback. Rejected: it changes `_report_batch`'s output *and* its rc for
multi-id sets (a DISCONTINUED id in a batch would flip rc 0 → 1) — explicitly out of scope
("the batch shapes' `_report_batch` exit rule for multi-id sets … stays").

## 4. Behaviour changes a human should be aware of

1. **Single-id `state<TAB>path` for a terminal bundle now goes to stdout** (it went to
   stderr from the short-circuit at `cli.py:606`/`:626`). The driven case always printed to
   stdout (`cli.py:641`), so this makes the machine-readable line unconditional rather than
   route-dependent. Exit codes for COMPLETE/RESOLVED are unchanged (0).
2. **A single id now runs as a one-bundle wave** (`flow_ids` → `_drive_and_act`) instead of
   `flow.flow`'s sequential loop. Same beats, same leaves, same isolation; the sign-off leaf
   is reached via `leaves.run_signoff_batch` rather than `leaves.run_signoff`, and Plan via
   `do_plan_batch(ids=[iid])` rather than `do_plan(d)` (a superset: it seeds `notes.json` +
   `sources/` the same way, `leaves.py:631-632` vs `:504`, and filters RESOLVED before the
   session). **This is the operator-experience judgment the reviewer flagged as
   fitness-to-purpose NEEDS-HUMAN last round; it is inherent to the unification the brief
   asks for, and it is a human call.** `pdca try 468` opens a shell in the patched worktree
   if you want to drive a real single-id flow by hand.
3. **Both shapes now print the recovery hints** (COMPLETE redo, RESOLVED reopen, split
   children). Previously the single-id shape had them and the batch shape had none.
4. `DISCONTINUED` single-id still exits 1 (unchanged from `cli.py:648`): the exit code
   counts successful terminals, and an abandoned bundle is not one.

## 5. The three refutation questions

**(a) Genuine red?** Yes — established twice.

*Whole fix reverted*, via the project's own C4 runner
(`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh`, which reverts only the
production hunks and keeps the tests):

```
== C4 green leg: template/tests/{test_autoiterate,test_flow_entrypoint_parity,test_flow_slice}.py
Ran 60 tests OK · Ran 9 tests OK · Ran 98 tests OK
== C4 red leg (production change reverted)
Ran 60 tests OK · Ran 9 tests FAILED (failures=8, errors=1) · Ran 98 tests FAILED (failures=1)
C4 PASS: red without the fix, green with it
```

The 9 red-leg findings in the new module: `test_single_id_routes_through_flow_ids_not_flow`,
`test_preflight_error_same_rc_and_message_both_shapes` (ERROR — the `PreflightError`
escapes `cli._flow` uncaught pre-fix), `test_complete_…`, `test_resolved_…`,
`test_terminal_split_parent_names_children_never_rm_rf`, and all four subtests of
`test_malformed_lineage_children_…`. Three tests are green on both legs by design
(`in_flight`, `discontinued`, `awaiting_signoff_presentation_preserved`) — they assert
*preservation*, so a red there would mean the patch broke something.

*Iteration 1's specific defect re-introduced* (the reviewer's C3/T5 finding): with only
`kids = _lineage_children(record)` swapped back to `kids = record.get("children")` —

```
ERROR  … (case='non-list')     TypeError: can only join an iterable
ERROR  … (case='junk-entries') TypeError: sequence item 0: expected str instance, int found
FAIL   … (case='string')       'drive them instead' unexpectedly found in
                               '… drive them instead with `pdca flow 4 6 9` …'
Ran 9 tests — FAILED (failures=1, errors=2)
```

so the tolerance is bound by the test, not merely asserted in a docstring. (`flow.py` was
restored from a byte copy afterwards; the final patch was regenerated and re-gated after
that.)

**(b) Production path?** Yes. Every assertion drives **`cli._flow`** with a real `Config`
— the brief's named surface — never a hand-picked `flow.*` call standing in for it. The two
exceptions are deliberate and are *about* the production routing: the spy in
`test_single_id_routes_through_flow_ids_not_flow` and the raiser in
`test_preflight_error_…` replace `flow.flow_ids`/`flow.flow` to observe **which one
`cli._flow` actually calls**. Fixtures use production code throughout: `leaves.do_plan`,
`flow.flow`, `split.accept` (`split.py:525`), `split.read_lineage`, `state.state`.

**(c) Fixture includes the fault?** Yes.

* The split parent is built by **production `split.accept`** — a real brief, a real
  `split-proposal.md`, real child ids — and the test asserts the produced record really
  carries `children == ["469","470"]` before driving anything. Not a hand-rolled dict.
* The malformed-lineage fixtures write **real `split-lineage.json` files** with a valid
  `version`, so production `split.read_lineage` returns them rather than filtering them out
  (a record the reader rejected would prove nothing).
* The RESOLVED fixture writes a real `notes.json` `resolved` object read by production
  `state.is_resolved`; the DISCONTINUED one goes through a real sign-off decision.
* Both shapes drive **byte-identical disk state**: `_fork()` `copytree`s one seed root, so
  neither shape sees the other's mutations, and neither fixture is curated per shape.

## 6. For the human at sign-off — the two carried-forward §6 items

**T3 Runtime (carried forward: "Copier is absent … all 7 root render/update tests
skipped").** Not reproducible here — copier **is** installed in this instance
(`.venv/bin/python3 -c 'import copier'` → 9.17.0) and the required doctor row for it already
exists (`pdca.toml:809-814`), so no dependency is unregistered. Ran the project's T3 gate
against this patch:

```
== T3: template-repo suite (render + update-compat)
test_render_then_slice … ok        test_namespaced_cli_name_reaches_every_rendered_command … ok
test_instance_edits_survive_the_merge … ok   test_merge_leaves_no_conflict_markers … ok
test_merged_config_still_loads … ok          test_no_model_work_is_newly_enabled … ok
test_shipped_contribution_gate_survives … ok
Ran 7 tests in 20.286s — OK          (ran, NOT skipped; full log: gate-logs/T3-suite.log)
== T3: offline driver suite — Ran 1631 tests in 25.144s — OK (skipped=2)
== T3: root suite OK, driver suite OK
```

The render/update suites copy the **working tree**, so those 7 tests exercised this patch.
If the reviewer's sandbox again cannot see `.venv`, the skip is a *reviewer-environment*
fact, not a patch fact — this log is the evidence to clear the row with.

**T4 Contribution (carried forward: commit message / PR body not among the review inputs).**
Structural, not fixable in a patch: those two artifacts are drafted by the **publisher** at
Check's closing step, *after* sign-off, which is why `contribcheck` is default-open before
they exist and `pdca publish` hard-gates T4 after drafting them (`pdca.toml:954-975`). To
help the publisher get it right first time — user impact: *"`pdca flow <id>` and
`pdca flow <id> <id>` now behave identically for the same bundle, and a completed split is
no longer told to `rm -rf` itself"*; tracker refs: `Fixes #468` trailer + `Closes #468` in
the PR body.

**No unregistered external dependency was hit.** python3 ≥ 3.11 stdlib + git only; no
tracker, network, `gh`, or container was touched by any fixture or by any run above — as the
brief's `External dependencies: none` says.

## 7. Runner, gates, and commit-readiness

| What | Command (the project's own runner) | Result |
|---|---|---|
| C4 red→green | `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` | **C4 PASS** |
| T3 runtime | `./engine/scripts/run-suite.sh` | root OK (7), driver OK (1631) |
| T2 shape | `./engine/scripts/run-docs-check.sh` | `lint_docs: OK`, 22 pages, `link audit OK` |
| Focused module | `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_entrypoint_parity` | 9 tests OK (0.04 s) |
| Patch is self-contained | `git archive f7876f2 \| tar -x -C /tmp/base468x`, `git apply` there, run both suites | applies clean; 1631 OK |

**Commit hooks / formatter:** the target ships **no** formatter or linter config — no
`pyproject.toml`, `setup.cfg`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` or
`.editorconfig` at the repo root or under `template/`, and
`$(git rev-parse --git-common-dir)/hooks` contains only `*.sample`. `CONTRIBUTING.md`
requires exactly: DCO sign-off (`git commit -s` — publish's job), one logical change per PR,
and "keep the offline suite green" (1631 OK). The target's CI is `docs-check.yml`,
`render-check.yml`, `require-linked-issue.yml` — the first two are the T2/T3 gates run
above. House style: longest line I add is 94 chars, against an existing maximum of 106 in
`flow.py` and 236 in `cli.py`; no line was left with trailing whitespace
(`git diff --check` clean).

**STOP discipline:** nothing pushed, no branch created, no PR opened or marked ready.
