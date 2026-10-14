# Build notes — issue 674 / same-wave-conflict-holds-one-bundle-not-the-run (iteration 2)

## Base

The worktree (`$PDCA_WORKTREE`) is the stack base `pdca-integration/main-r8bf6d15b2de3` at
`420f8b4` (the bundle's `stack-base-tip`). It already holds #605, #629, #633, #651 and #658
on top of the brief's `41210bc`, so line numbers differ from the brief's. Every "base" line
below is on `420f8b4`; every "after" line is in the patched worktree. `patch.diff` applies
to `420f8b4` (checked: `git apply --check -R` from the patched tree is clean, and the C4 gate
reverts and re-applies its production hunks). It does not apply to plain `origin/main`,
because #633's `carried=` lines are part of its context.

## What this iteration changes (the carry-forward)

The finding: a bundle that declares `Conflicts with` a bundle the fold held for a same-wave
conflict was still built, on a line without that bundle's work. #629 already holds such a
partner when the held bundle *pushed no branch* (`held_unpushed`), but iteration 1 passed
only `held_unpushed` to `_runnable(unpushed=…)` and built `conflicts=` only `if
held_unpushed` (base `flow.py:2250-2254`), so `held_conflict` never reached the partner check
(base `flow.py:729-731`).

I reproduced it before fixing. With the iteration-1 code plus the new test case, the C4
green leg failed on exactly that case:

```
FAIL: test_a_conflicts_with_partner_of_a_held_bundle_is_held_too
AssertionError: 'issue_25' unexpectedly found in {… 'issue_21': ('pdca-integration/main-rbbeb3cd8a3f1',
  '1d374f9e…', '1d374f9e…'), 'issue_25': ('pdca-integration/main-rbbeb3cd8a3f1', '1d374f9e…', '1d374f9e…'),
  'issue_26': (…same line commit…)}
```

So `25` and `26` were built on the line commit `1d374f9`, which does not hold `11`.

The fix, all in `template/src/pdca_harness/flow.py`:

- `_runnable` gets one new keyword, `conflict_held: Mapping[str, Collection[str]] | None`
  (after `:687`): each bundle a fold held for a same-wave conflict, mapped to the bundles
  it conflicts with. Default `None`, so the five existing test calls, which pass only
  positional arguments (`test_flow_slice.py:1963-1984`,
  `test_flow_out_of_batch_prereq_hold.py:156`), are unchanged.
- A bundle tied by a `Conflicts with` edge (either side, the same `conflicts=` map #629
  uses) to one of them is held (after `:739-741`, `:806`). Its target is resolved for the
  message (after `:747-748`).
- It gets its own stderr line, one per such held partner (after `:798-805`), naming the
  conflict and the step. #629's "pushed no branch … publish them" text is not reused,
  because it is false here: the held bundle did push, and its draft PR exists. The line
  reads:
  `flow: issue_25 held — it `Conflicts with` issue_11, which this run's fold held out of
  the line (its change conflicts with issue_10's), so no line of this run holds that work;
  not built on a base missing it. To build it, wait until issue_11 is rebuilt on a base
  that holds issue_10 and its PR merges into main (org/repo), then re-run.`
  "Wait until its PR merges" has the same reason as #629's line: a re-run's carry starts
  only from a plain `Depends on`, never a `Conflicts with` (`_runnable` docstring, base
  `flow.py:716-724`).
- The `_runnable` call in the wave loop (after `:2307-2316`) now builds `conflicts=` when
  `held_unpushed or held_conflict`, and passes `conflict_held=` from `held_conflict`.
- The hold announcement (after `:1086-1089`) now says "bundles that depend on it or are its
  `Conflicts with` partners are held this run", which is #629's wording for its own case
  (base `flow.py:2378-2381`).
- Docstrings and comments: `_runnable` (after `:725-731`), `held_conflict` (after
  `:2217-2221`). `_conflict_partners` now takes `Collection[str]` (after `:1074`), since the
  new line passes it the mapping's values.

Docs, which said only dependents are held:

- `docs/07-crosscutting.md` (after `:698-707`): the paragraph iteration 1 added now says
  dependents *and* `Conflicts with` partners are held, and to re-run a held partner only
  once the rebuilt bundle's PR has merged.
- `template/PCDA/quality-cycle/09-parallel-lanes.md:69`: "with the bundles that depend on
  it" → "with the bundles that depend on it or share a `Conflicts with` edge with it".

Test (`template/tests/test_flow_same_wave_conflict.py`, a copy is in this bundle under
`template/tests/`):

- New case `test_a_conflicts_with_partner_of_a_held_bundle_is_held_too` (`:282-317`). It
  is the reviewer's scenario: `10` changes line 2 of a nine-line `shared.txt`, `11` lines 2
  and 8, `12` its own file, `25` declares `Conflicts with: 11` and changes line 8. I added
  `26`, which `11` names in *its* brief, so both sides of the edge are covered, and `21`
  (depends on `12`) to show the rest of wave 1 still builds. Asserted: no stop; `21` built
  on the line without `11`; `25` and `26` never built and PLANNED; one line each naming
  `issue_11`, `issue_10`'s conflict and the rebuild step, not "pushed no branch", printed
  before wave 1 builds; no brief edited.
- `_plan` takes `conflicts_with=` (`:81-88`). `_briefs_unchanged` now compares each brief
  to its text as planned (`:177-182`), instead of checking that "Conflicts with" is absent.
  That is stronger, and it still works when a test declares the field itself.

## Carried over unchanged from iteration 1

`integrate.py` is byte-for-byte iteration 1's change, and so is the rest of `flow.py`:

- `integrate._Conflict` (after `:92-99`) is raised by `_merge_published` for a textual
  conflict (base `:585-589`, after `:630`). Same message and base class as before.
- `integrate.fold(..., held_out=, wave=)` (after `:309-310`, docstring `:395-407`, loop
  `:517-546`). `pre` is the line tip before the wave's first merge, and `kept` is the wave's
  bundles merged so far. A wave bundle that fails with `_Conflict`, with at least one kept
  bundle, is held only when `_held_by` (after `:886-898`) names partners: its branch must
  merge cleanly onto `pre` alone (otherwise it clashes with earlier-wave work and the fold
  raises, as today), and partners are the kept bundles it conflicts with when tried one at
  a time. `_trial` (after `:901-929`) merges on a detached HEAD, so the line's branch never
  moves, and puts the tree back on the branch at its tip, clean, or raises `_LineBroken`.
  It runs inside `fold`'s `integ_lock` scope (base `integrate.py:449-458`).
- `flow._fold_lines` passes `held_out`/`wave` through (after `:838-839`, `:851-854`,
  `:863`). `_drive_and_act` keeps the run-wide `held_conflict` (after `:2221`). It is left
  out of every fold's bundle list, added to `_runnable(held=…)`, announced right after the
  fold (after `:2448-2463`), and repeated at the end of the run (after `:2488-2489`, next to
  `_warn_stranded_split_children`).

## Why this shape, and what I ruled out (this iteration)

- **Pass `held_unpushed | set(held_conflict)` as `unpushed=` (1 changed line).** Rejected:
  the partner would get #629's line, "pushed no branch this run … publish them (`pdca
  publish <id>` …)". That is false for a bundle that did push, and the reviewer named that
  wording as wrong for this case.
- **Turn `unpushed` into a name → reason mapping, one shared message.** Rejected. It
  changes #629's parameter type, its `partners` line (base `:730-731`), its message (base
  `:779-786`) and the caller, about 10 lines of code #629 owns. The brief says other
  in-flight work (629, in another batch) edits this same code. The chosen shape adds a
  parallel keyword (about 15 added lines) and changes one #629 line, the `repo, base`
  condition (after `:747`).
- **Don't hold partners (a scope call the carry-forward leaves to the human).** Not taken.
  `waves.compute_waves` turns each `Conflicts with` pair into a dependency edge, name-lower
  first (`waves.py:205-212`, `deps[hi].add(lo)`). So in the scheduler's own model the
  partner depends on the held bundle, and holding it stays within the Invariant's "the
  bundles that conflict (and those that depend on them)". If the human decides otherwise,
  backing it out is the `conflict_held=` argument at `flow.py:2316` (after), the `or
  held_conflict` at `:2315`, the docs sentences, and the new test case.

Iteration 1's reasons stand. Short version: I reused `fold`'s merge-in-order loop rather
than `skipped=` as-is, because `skipped` swallows every per-bundle error, including ones
that must still stop, and `fold` pushes before returning. The "merges onto the line
without them" test needs `pre`, which only the loop knows. `git merge-tree --write-tree`
(git ≥ 2.38) was not used, so **no new git feature or minimum git version** is added. The
tie-break is the fold's name order, as the brief confirms.

## Red → green (project runners)

C4, through `./engine/scripts/run-verify.sh` (from the pdca-pdca root, under `timeout`),
on the final `patch.diff`:

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_flow_same_wave_conflict.py
Ran 6 tests in 1.476s
OK
== C4 red leg: bundle test(s) with the production change reverted
ERROR: test_a_hold_leaves_the_integration_tree_clean_on_the_line … TypeError: fold() got an unexpected keyword argument 'held_out'
FAIL: test_a_conflicts_with_partner_of_a_held_bundle_is_held_too … 'did not integrate' unexpectedly found … "flow: wave 0 did not integrate (issue_11's branch origin/fix/11 does not merge cleanly …"
FAIL: test_a_same_wave_conflict_holds_the_later_bundle_and_the_run_goes_on … "flow: wave 0 did not integrate (issue_11's branch origin/fix/11 does not merge cleanly onto pdca-integration/main-r8d… (conflicts in shared.txt) …"
FAIL: test_of_a_three_way_chain_only_the_bundle_that_conflicts_is_held … 'did not integrate' unexpectedly found …
Ran 6 tests in 1.034s
FAILED (failures=3, errors=1)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The (3) clean-merge case and the earlier-wave-stop case pass on both legs, as the brief
expects: they guard against holding on file overlap alone and against swallowing an
earlier-wave conflict. The red leg's `ERROR` is a runtime `TypeError` inside one case, not
a load failure: the module imports only modules, all 6 cases ran.

Full suites through the T3 runner (`./engine/scripts/run-suite.sh`): root suite 24 tests OK,
driver suite 2448 tests OK (2 skipped), one more than iteration 1 (the new case). Docs
through the T2 runner (`./engine/scripts/run-docs-check.sh`): `lint_docs: OK`,
`render_site: link audit OK`.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes, at two levels.** With the whole fix reverted (the C4 red leg,
  `git apply -R --exclude=tests/*`), the new case fails because the run stops at wave 0
  (output above). With only this iteration's change reverted (iteration 1's code plus the
  new test), it fails because `25` and `26` are built on line commit `1d374f9`, which lacks
  `11` (output in the first section). That second red is the defect the carry-forward
  names, so the case binds this iteration's change and not just the run-goes-on behaviour.
- **(b) Production path? Yes.** The case calls `flow._drive_and_act` with the publisher in
  `command` mode. The hold runs through the real `integrate.fold` → `_merge_published` →
  `_held_by`/`_trial` against real git (a bare `origin`, the primary checkout, the real
  integration worktree, real pushes). The partner hold runs through the real `_runnable`
  and `waves.conflict_map`, which parse the real `Conflicts with` fields of the briefs on
  disk. Stubbed: the build and sign-off leaves (`flow._drive_wave`),
  `publish.draft_texts`, `flow._publish_bundle` (replaced by a real git cut, commit and
  push from the recorded line tip), and `gh`. The fix changes none of those.
- **(c) Fixture includes the fault? Yes.** `11`'s conflict with `10` is a real git
  conflict (same line of a committed file, different text). `25` really edits line 8,
  which `11` also edits. The `Conflicts with` edges are real brief fields, one declared on
  each side. All six bundles are in the batch and driven; nothing is left out.

## Commit-readiness

The target has no formatter, linter config, pre-commit config or installed git hooks (no
`.pre-commit-config.yaml`, `core.hooksPath` unset, only `*.sample` in hooks). Its CI runs
only the docs checks, which pass. Every added Python line is ≤ 100 columns. `flow.py` has
the same 3 longer lines before and after the patch. The DCO `Signed-off-by` belongs to the
publish commit, not the patch.

## For the human

- The 9 deferred findings in `deferred-findings.json` are not addressed here and I did not
  act on them; the carry-forward marks them as human judgement, not build work.
- Housekeeping: to generate the diff I marked the new test file intent-to-add (`git add
  -N`) in the worktree index, then put the index back (`git reset -q -- <file>`). The file
  is untracked again, as iteration 1 left it. No files were written outside the worktree
  and this bundle.
