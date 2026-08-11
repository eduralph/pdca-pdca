# Build notes — issue 448 / split-lineage-and-deratchet-sizing

Target: `eduralph/pdca-harness` @ `main` (`b95aa58`), built in `$PDCA_WORKTREE` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`. All `path:line` citations below are against
that worktree with the patch applied, except where a `b95aa58` anchor is named.

## What was built, item by item (the brief's *Design*)

### 1. Lineage, written at materialisation

* `template/src/pdca_harness/split.py:64` — `LINEAGE = "split-lineage.json"`, `:69`
  `LINEAGE_VERSION = 1`. One filename in both directions, `role` distinguishing them,
  exactly the schema the brief fixes (the contract issue 449 consumes).
* `:258` `lineage(bundle)` — THE reader. Missing / unreadable / non-dict / wrong-version /
  unknown-`role` all yield `None`; fields are normalised (`id`, `parent` → `str`, the id
  list → `list[str]`, `depth` → non-negative `int`) so no consumer has to guess what a
  hand-edited file put there. Catches `OSError, ValueError, TypeError` only, but every
  path through it returns rather than raises — asserted at
  `template/tests/test_split_lineage.py:147`.
* `:551` `materialise(..., *, parent=None)` writes each child's record **into `staging`**
  (`:581`), so it is moved with the brief by the existing staged-write discipline
  (`split.py:406-427` @ `b95aa58`, now `:639-655`) — the peer callsite the brief named.
  Called with `parent=parent` from `accept` at `:639`.
* `:695` — the parent's inverse record, written **after** the `build-notes.md` breadcrumb
  and **before** `CLOSE_MARKER` (`:698`), preserving the guarantee the surrounding comment
  states: a failed write leaves the parent un-marked and the printed retry works.
  `parent_depth` is read at `:633`, *before* that write, because the write replaces a
  child record with a parent one and its `depth` is the only source of a grandchild's.
* `:634-637` + `:708-717` — the parent's previous record is captured and **restored** on
  the rollback path. Without it a failed accept would leave a parent edge naming children
  that were just rolled back, and (for a parent that was itself a split child) would have
  destroyed its own child record. Same belt-and-braces as the existing `CLOSE_MARKER`
  unlink two lines above.
* Provenance, not attempt output: `split.LINEAGE` is deliberately **not** added to
  `state.DOWNSTREAM_OF_BRIEF` (`state.py:82-110` @ `b95aa58`), asserted at
  `test_split_lineage.py:142`.

### 2. The estimator stops scoring the split's own artifacts

* `sizing.py:226` `_split_lineage(brief_path)` reads `brief_path.parent` — a real `Path`
  inside `estimate` — exactly as the brief directs. `AprioriBrief`'s allowlist
  (`sizing.py:363`, `:400-407` @ `b95aa58`) is untouched and unwidened; the docstring says
  why it must stay that way.
* `sizing.py:277-281` — sibling refs are subtracted from the conflict count. Organic
  conflicts (any id not listed as a sibling) still count at full weight: asserted at
  `test_split_lineage.py:186`.
* `sizing.py:103` — `split_child: 0` joins `DEFAULT_WEIGHTS`, read through `_weights`, so
  `[driver.sizing]` retunes it without patching the engine — the `is_plan_pointer` peer
  pattern (`sizing.py:94` @ `b95aa58`). Documented in `template/pdca.toml.jinja:259` (the
  example block is asserted key-for-key against `DEFAULT_WEIGHTS` by
  `template/tests/test_act_index_sizing.py:236`, so this is required, not decorative).
* `sizing.py:316-326` — a reason line is emitted whatever the weight, naming the parent,
  the depth and how many sibling conflicts were *not* counted. A score whose basis is
  invisible is a score nobody can check, and both `size_reasons` and the convergence
  report quote `SizeEstimate.reasons`.

### 3. The remedy is depth- and evidence-aware

* `plan_policy.py:145-156` — a new branch between the two existing ones, the same shape as
  the "large but coherent" carve-out immediately above it (the peer the brief named,
  `plan_policy.py:134-139` @ `b95aa58`): for a bundle with child lineage,
  ``consider `pdca split` first`` is emitted **only** when `est.model_band == OVERSIZED`.
  The `before_do=False` (`iterate-plan`) branch is untouched — asserted at
  `test_split_lineage.py:263`.
* `split.py:325` `lineage_phrase` / `:351` `lineage_note` — one definition of the phrase
  and one of the sentence, because three surfaces quote them. Injected into
  `leaves.py:560,579` (`_plan_prompt`, ahead of the existing split instructions) and
  `leaves.py:1260,1265` (`_split_prompt`). Neither prompt is otherwise reworded, and both
  are byte-identical for a bundle with no lineage (asserted, `test_split_lineage.py:269`).

### 4. Convergence checked before irreversible filing

* `split.py:369` `convergence_report` — each child body written to a temp dir **with a
  staged lineage record** (`:396-398`), then `sizing.estimate`d, and its band compared with the
  parent's. The staged record is what makes the report honest: inside a proposal every
  ordering ref is a sibling label by construction (`_validate_ordering`, `:450-462`), so
  without it the report would print a band no materialised child will ever have. Asserted
  directly at `test_split_lineage.py:302`.
* `split.py:443` — called from `preflight` after `_validate_ordering`, i.e. before
  `file_children` (`cli.py:733` runs preflight, `cli.py:742` files). Wrapped in
  `try/except Exception` (`:446`): an advisory that fails must never be the reason a valid
  split cannot be accepted.

## The ordinal, and the one place I deviated from a literal reading

The brief's remedy wording is "child N of a split of #X, depth D". The child record's
schema is fixed by the brief and carries `siblings` (the *other* ids) — not the child's
own position, and inventing one by sorting the ids would print a number the proposal never
declared. Rather than add a key to a schema that is a contract with issue 449, the ordinal
is recovered from the **parent's** record, whose `children` list is the ordered id list
(`split.py:695-697`, read back at `:344`). That is the inverse edge earning its keep, and
it degrades to "child of a split of #X, depth D" when the parent bundle is unreachable.

Second, success criterion (c) says "`split.materialise` writes a `split-lineage.json` into
each child **and the parent**". The *Design* section is explicit that the parent's is
written "next to the `build-notes.md` breadcrumb and BEFORE `CLOSE_MARKER`
(`split.py:453-461`)", which `materialise` cannot do — the parent is not staged, and its
write has to be ordered against the close marker. I followed the Design section; `accept`
writes it (`split.py:695`), and `materialise`'s docstring says so out loud (`:567-569`) so
a reader is not left hunting. The observable end result criterion (c) asks for — a record
in each child and in the parent after `--accept` — holds, and is asserted at
`test_split_lineage.py:96` and `:106`.

## Alternatives ruled out, with costs

* **A `Split of:` brief FIELD instead of a JSON file.** Ruled out by the brief, and the
  reason is checkable: `sizing.apriori_text` measures the brief's own bytes, so a new field
  moves `brief_bytes` — the very feature being de-ratcheted — and it cannot carry the
  ordered children list 449 needs.
* **Widening `AprioriBrief._DELEGATED` with `parent`** to read the record through the
  brief object. One word of diff, and it re-opens the exact hole `_DELEGATED` exists to
  close: `ap.parent` hands back a real `Path` whose `read_text()` returns the whole brief
  including carry-forward. `estimate` already holds the real `Path`; using it costs
  nothing (`sizing.py:277`).
* **A separate `split-children.json` for the parent edge.** Two files, two writers, two
  readers — and the drift would be invisible (the brief's own argument). One filename with
  a `role` field costs the three-line `ids_key`/`role` branch in `lineage` (`split.py:280-284`, `:294-296`).
* **Making the convergence report blocking.** Rejected for the reason `size_guard` has no
  `hold` mode: 62% best precision (`plan_policy.py:91-101` @ `b95aa58`). It prints and
  returns; `test_the_report_never_blocks_an_acceptance` pins that.
* **A `max_split_depth` cap** — out of scope per the brief, and `depth` is now recorded so
  the cap remains a two-line change if the Act cadence ever wants it.
* **Shipping `split_child` at −2** (the brief's open question 1) — specified as 0, built as
  0. A one-line change at sign-off; the test asserts both that the default is 0 and that a
  configured −2 actually moves the score (`test_split_lineage.py:199`), so the sign-off
  edit is pre-verified either way.
* **Not touching `docs/07-crosscutting.md`.** The weights table there enumerates the five
  features; leaving it would have shipped a doc that disagrees with `DEFAULT_WEIGHTS` on
  the day of the change. Seven lines, no behaviour (`docs/07-crosscutting.md:127-134`).

Nothing in `flow.py` was touched (the brief forbids it — mid-run adoption of children is
issue 449). No existing weight or cutoff moved.

## Refuting my own test

**(a) Genuine red?** Yes — proved by the project's own C4 gate, not by hand:
`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` → `C4 PASS: red without the
fix, green with it`, exit 0. The gate reverts **only** the production hunks
(`--exclude=template/tests/*`) and re-runs: green leg `Ran 19 tests … OK`; red leg `Ran 19
tests … FAILED (failures=7, errors=13)` with **no** `unittest.loader._FailedTest` marker,
i.e. the module imported and 19 tests really executed. 15 of the 19 distinct tests go red:

```
ERROR: test_each_child_records_its_parent_siblings_and_depth
ERROR: test_the_parent_records_the_inverse_edge
ERROR: test_depth_counts_recursion_without_anyone_counting
ERROR: test_the_record_is_staged_like_every_other_per_child_write
ERROR: test_lineage_is_provenance_not_attempt_output
ERROR: test_an_unreadable_record_reads_as_absent_and_never_raises
ERROR: test_the_weight_is_registered_and_ships_at_zero
ERROR: test_the_staged_estimate_treats_ordering_refs_as_siblings
ERROR: test_a_bundle_without_lineage_keeps_todays_remedy
FAIL:  test_a_child_scores_below_the_cutoff_where_it_scores_9_today      (criterion a)
FAIL:  test_an_organic_conflict_still_counts_at_full_weight
FAIL:  test_a_split_child_is_not_told_to_split_again_on_structure_alone  (criterion b)
FAIL:  test_preflight_reports_each_staged_childs_band_against_the_parent (criterion c)
FAIL:  test_the_report_reaches_the_operator_BEFORE_the_issues_are_filed  (criterion c)
FAIL:  test_the_planner_and_splitter_prompts_carry_the_same_context
```

The four that stay green are deliberately the invariance controls — a bundle with no
lineage is scored exactly as today; the sizer's `oversized` verdict still earns the split
remedy; the `iterate-plan` wording is unchanged after Do; the report never blocks. They
assert that nothing moved, so a green pre-fix is what they are *for*, and each is paired
with a red counterpart in the same class.

Modules are imported, never new symbols (`test_split_lineage.py:34`) — a
`from pdca_harness.split import lineage` would have raised ImportError on the red leg,
which `run-verify.sh:98,138-141` classifies PDCA-UNVERIFIABLE (77) rather than red.

**(b) Production path?** Yes. The fixtures are produced by `split.accept` /
`split.materialise` / `split.preflight` / `cli._split` themselves and read back by
`sizing.estimate`, `plan_policy.size_reasons`, `leaves._plan_prompt` and
`leaves._split_prompt` — the production functions the patch changes. Nothing is
re-implemented in the test: the only hand-written JSON is the *corrupt* input in
`test_an_unreadable_record_reads_as_absent_and_never_raises`, which exists to prove the
reader abstains. The single `mock.patch` of production code is
`pdca_harness.leaves.run_sizer` (to supply a model verdict without a model — the same
technique `template/tests/test_size_guard.py:226` already uses) and one
`mock.patch("pdca_harness.sizing.estimate", side_effect=RuntimeError)` used solely to
prove the advisory swallows a failure.

**(c) Fixture includes the fault?** Yes. The child that must score below the cutoff is a
child a real `--accept` materialised, carrying the exact three inherited features the
brief names (`Difficulty: high`, one `External dependencies` token, sibling `Conflicts
with`) — the failing element is *in* the fixture, not curated out: the same brief text
copied to a directory **without** the lineage file is asserted to still score ≥ 7 /
`oversized` in the same test (`test_split_lineage.py:172-178`), so the delta is the fix and
nothing else. The ordering claim in criterion (c) is likewise proved by the fault being
present rather than assumed: `file_children` is replaced by a filer that snapshots the
captured stderr *at the moment it is called*, and the report must already be in it
(`test_split_lineage.py:312`).

## Gates run locally (project runners only — no hand-rolled invocation)

* `./engine/scripts/run-verify.sh` (C4, gating) — **PASS**, exit 0.
* `./engine/scripts/run-suite.sh` (T3) — `root suite OK, driver suite OK`
  (7 render/update-compat tests + 1610 offline driver tests, 2 skipped).
* `./engine/scripts/run-docs-check.sh` (T2) — `lint_docs: OK`, `link audit OK`.
* The target repo configures no formatter, linter or commit hook (no `.pre-commit-config`,
  no `ruff`/`black` config, no `core.hooksPath`, `.git/hooks` holds only samples); CI is
  `render-check` + `docs-check` + `require-linked-issue`, and the first two are the two
  suites above. Line lengths in the touched Python files stay inside the file's existing
  convention (≤ 95 cols); the one long line in `pdca.toml.jinja:238` (102 cols) matches its
  immediate neighbours at `:45`/`:49`.
* `test_render_cli_name` caught a bare ``pdca split --accept`` in my first draft of the
  `pdca.toml.jinja` comment — a namespaced render would have shipped the wrong command
  name. Now `{{ cli_name }} split --accept` (`template/pdca.toml.jinja:238`).

## Not done / left for the human

* No external dependency beyond python3 ≥ 3.11 stdlib + git was needed; nothing to
  declare.
* `preflight` — and therefore the convergence report — runs on the **filing** path
  (`cli.py:733`, no `--ids`). An operator who filed the issues by hand and passes
  `--ids` reaches `validate` instead and sees no report. That is the existing structure of
  the command and the brief scopes the report to `preflight`; worth a sign-off opinion if
  you want it on both paths (it would be a two-line call in `cli._split`'s `--ids` branch).
* Open question 1 (ship `split_child` at 0 or −2) is answered 0, per the brief. Changing it
  is `sizing.py:103` + `template/pdca.toml.jinja:259` and the existing tests cover both.
