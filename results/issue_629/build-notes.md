# Build notes — issue 629 / hold-conflicts-with-partner-of-unpushed-bundle (iteration 2)

Target: `eduralph/pdca-harness` `main`. Worktree `$PDCA_WORKTREE` =
`/home/eddie/pdca/pdca-harness.pdca-wt-l1`, at `41210bc` (current `main`). Line numbers are
**post-patch** on that tree unless marked "base" (= `41210bc` without the patch).

## The base moved since the brief

The brief was verified on `b5f5c29`; `main` is now 22 commits later (`41210bc`). #623 and
#632, both named in the brief's Ordering note, have merged, so this builds on them as the
brief intended. None of the merged commits touch `_runnable` or the wave loop; only line
numbers shifted:

| brief (`b5f5c29`) | base (`41210bc`) |
|---|---|
| `_runnable` `flow.py:681-767` | same, `flow.py:681-767` |
| `_runnable` call `flow.py:2161-2165` | `flow.py:2208-2210` |
| announcement `flow.py:2289-2291` | `flow.py:2334-2336` |
| docs sentence `docs/07-crosscutting.md:672-673` | `:676-677` (#623 added `:672-675` above it) |
| `integrate.fold` early return `integrate.py:343-345` | `integrate.py:362-364` |

The flow.py changes on `main` since `b5f5c29` are #652 in `_carry_finished` /
`_cascade_not_clean` (base `flow.py:866-1001`) and nothing else.

## Carry-forward (iteration 1): the held line's advice

The rejected line told the operator: "publish them (`pdca publish <id>` …), then re-run."
That leads back to the bug. After CA is published by hand:

- a re-run without CA drops the edge: `waves.conflict_map` keeps only edges between bundles
  in the drive set (`waves.py:136-153`);
- a re-run naming CA again skips CA as finished, and the pre-wave carry starts only from a
  drive-set bundle's plain `Depends on` (`_carry_finished`, `flow.py:923`; the loop that
  finds what to carry reads `brief.depends_on` only, `flow.py:955`).

Either way CJ is built on a base without CA. Only CA's PR merging into the base puts CA's
work under CJ.

New line, `flow.py:779-786`:

```
flow: issue_702 held — it `Conflicts with` issue_701, which pushed no branch this run, so no
line of this run holds that work; not built on a base missing it. To build it, publish them
(`pdca publish <id>` for 701) and wait until their PR merges into main (org/repo), then re-run.
```

- "publish them" stays: CA has no PR at all yet (it pushed nothing), so there is nothing to
  merge until it is published.
- "wait until their PR merges into {base} ({repo}), then re-run" is the shape of the #647
  unmerged-prerequisite line (`flow.py:769-775`). `{base}` / `{repo}` are the held bundle's
  OWN target, as in that line (CJ's base is what CJ is built on). `_resolve_target` is now
  also called for a bundle that has partners but no deps (`flow.py:737`; it only reads the
  brief, `publish.py:594-607`). With no target of its own the clause is just "wait until
  their PR merges" (`flow.py:781`).
- I did not offer "name it in the same `pdca flow` command" (the #647 line's other option):
  the carry never starts from a `Conflicts with` edge, so that advice would be false.

The test pins it: `_assert_held` (`test:174-183`) requires the line to end with `WAIT`
(`test:44`). A mutation run with the rejected wording put back fails 3 of 4 cases (all three
hold cases; see Runs).

The same "wait for the merge" rule is in the `_runnable` docstring (`flow.py:715-724`) and
in the docs (below).

## What changed (full patch)

1. `template/src/pdca_harness/flow.py:681-686`: `_runnable` takes two new keyword args,
   `unpushed` (the run's `held_unpushed`) and `conflicts` (a name → names map). Defaults
   `frozenset()` / `None` leave every other caller unchanged (the #646 carry calls
   `_runnable` with `held=` only; existing tests call `_runnable(cfg, [d], {...})`).
2. `flow.py:726-731`: per wave bundle, `partners = conflicts[d.name] ∩ unpushed`.
3. `flow.py:737`: resolve the bundle's own target when it has deps OR partners (for the
   advice). `targeted` is used only inside the deps loop, so deps behaviour is unchanged.
4. `flow.py:779-787`: any partner → ONE new stderr line (who is held, by what, why, what to
   do; never the word "prerequisite") and the bundle is left out of `runnable`. Its own
   dependents cascade through the existing not-COMPLETE check (base `flow.py:731-733`):
   criterion (d).
5. `flow.py:2231-2237`: the wave loop passes `unpushed=held_unpushed` and
   `conflicts=waves.conflict_map(cfg, bundles)`, built from the LIVE `bundles` list on every
   wave (adoption grows it in place, `flow.py:1752`, and filters it in place, `:1771`), and
   only when `held_unpushed` is non-empty, so the common run reads no extra briefs. Reuses
   `waves.conflict_map` (`waves.py:136-153`) as the brief asks: symmetric, limited to the
   drive set, so `held_finished` ids (not in the drive set) never match.
6. `flow.py:2361-2364`: announcement — "bundles that depend on it or are its `Conflicts
   with` partners are held this run" (criterion (e)).
7. `docs/07-crosscutting.md:676-685`: "holds only the bundles that depend on it" now
   includes `Conflicts with` partners (declared on either side) and why; plus one sentence:
   re-run a held partner only once that PR has merged, because the carry starts only from a
   plain `Depends on`.
8. Outside the brief's named file, the same rule in two shipped places (each a one-clause
   edit; nothing depends on them, drop them if the patch should stay to the brief's list):
   - `template/PCDA/quality-cycle/09-parallel-lanes.md:69` (reference model, same
     sentence);
   - `template/pdca.toml.jinja:124-126` (config comment: "holds only its dependents").
   Leaving either would ship a statement the code now contradicts.

## Test — `template/tests/test_flow_conflict_partner_hold.py`

Stub set copied from `test_flow_out_of_batch_prereq_hold.py` (config, `_brief`, `gh` stub,
`_run` via `flow.flow_ids`). Driven through `flow.flow_ids`, stack mode, publisher
`command` (not a dry-run), publishing on. Four cases:

1. `test_partner_of_an_unpushed_bundle_is_held_and_the_run_goes_on` (`test:187`): the
   brief's fixture (701 CA, 702 CJ `Conflicts with: 701`, 704, 703 `Depends on: 704`, 705
   `Depends on: 702`); CA's publish returns False. Checks (a)–(e), the advice, and that the
   run did not stop.
2. `test_the_edge_declared_on_the_unpushed_side_holds_the_partner_too` (`test:214`): same,
   but CA declares `Conflicts with: 702` and CJ declares nothing ("either direction").
3. `test_a_split_childs_partner_adopted_mid_run_is_held` (`test:225`): the brief's "live
   bundles" requirement. 706 splits in wave 0 through the PRODUCTION `split.accept` into
   707 and 708 (`Conflicts with: child-1` → 707; `split.accept` only allows ordering edges
   between siblings, `split.py:358-376`), the run adopts them into waves 1 and 2, 707 is
   accepted but pushes nothing, 708 must be held.
4. `test_partner_builds_when_the_first_pushed_its_branch` (`test:245`): the "Unchanged"
   control — CA pushes its branch, all five are built, CA before CJ, no conflict or
   "pushed no branch" text.

Changes from iteration 1's test, each for a reason:

- Cases 1–3 now run the REAL `flow._fold_lines` → `integrate.fold` (iteration 1 stubbed
  `_fold_lines` everywhere). With the fix, no bundle given to the fold is a candidate (CA is
  held out, the rest have no target or are held), so `integrate.fold` returns `{}` at
  `integrate.py:362-364` before any git step — exactly the brief's Falsifiability argument.
  Without the fix, the real fold tries to merge CJ's pushed branch and stops the run
  ("checkout not found") — the defect itself: CJ was built and pushed on a base without CA.
- Only case 4 stubs `_fold_lines` (`test:149-153`): a pushed branch needs a real git
  checkout with an origin, and that case pins scheduling only.
- `_publish` (`test:131-141`) now mirrors production for a bundle with no target: no
  record, False (`flow._publish_bundle` reads the record, `flow.py:642-665`;
  `publish.publish(skip_if_no_target=True)` writes none).
- `_drive_wave` (`test:113-129`) also records the split parent's sign-off, because the run
  adopts children only from a terminal split parent (`_is_split_parent`, `flow.py:1268-1291`).
- Each bundle's patch adds its own file (`_patch`), so the run's undeclared-overlap audit
  never prints a "`Conflicts with`" warning that would pollute the stderr checks.

## Runs (all through the project's own gate scripts, from the instance root)

- C4, `engine/scripts/run-verify.sh` with `PDCA_BUNDLE` / `PDCA_WORKTREE` set, `timeout
  600`: **`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`**, rc 0.
  - green leg: `Ran 4 tests … OK`;
  - red leg (production hunks reverted): `FAILED (failures=3)` — case 1 and case 2 fail at
    `assertNotIn("issue_702", self.built)` (built: `['issue_701', 'issue_704', 'issue_702',
    'issue_703']`, then "wave 1 did not integrate (checkout not found …); STOPPING"); case 3
    fails at `assertNotIn("issue_708", self.built)`. Case 4 passes on both legs, as a
    control should.
- Mutation 1 (map built ONCE before the wave loop, from the starting `bundles`): only case 3
  fails (`'issue_708' unexpectedly found in ['issue_706', 'issue_707', 'issue_708']`).
  Reverted.
- Mutation 2 (the rejected advice "publish them (…), then re-run." put back): cases 1–3
  fail on the `WAIT` check. Reverted.
- After both reverts, the worktree diff is byte-identical to `patch.diff` (`cmp`).
- T3, `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`; driver suite
  `Ran 2427 tests … OK (skipped=2)`; `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- T2, `engine/scripts/run-docs-check.sh`: `lint_docs: OK`, `render_site: link audit OK`.
- Commit-readiness: the target has no formatter, pre-commit config or git hooks (no
  `.pre-commit-config.yaml`; `.git/hooks` holds only samples; CI = docs-check / docs /
  render-check / issue workflows). `git diff --check` is clean; no added line is over 100
  characters (the three >100 lines in `flow.py` are pre-existing); both files parse.
  Neither pyflakes nor ruff is installed; imports checked by hand, all used.

## Refute-your-own-test

- **(a) Genuine red?** Yes. With the production hunks reverted (C4's red leg, same fixture,
  same test file), cases 1–3 FAIL on assertions — CJ (and 708) is built — not on an import
  or a traceback (the test imports only modules, never a symbol the fix adds). Case 4 stays
  green, as a control should.
- **(b) Production path?** Yes. `flow.flow_ids` → `_drive_and_act` → the real
  `waves.compute_waves`, `_carry_finished`, `_runnable`, `waves.conflict_map`,
  `integrate.unpublished`, `held_unpushed`, the real `_fold_lines` / `integrate.fold` in
  cases 1–3, the real `split.accept` and `_adopt_split_children` in case 3. Stubbed: the
  build/sign-off leaves (`_drive_wave`), `_publish_bundle`'s result, `publish.draft_texts`,
  `gh`, and `_fold_lines` in case 4 only — all named by the brief or outside the changed
  code.
- **(c) Fixture includes the fault?** Yes. CA is a targeted, patched, accepted bundle whose
  publish returns False and records no branch — the #593 "pushed no branch" case — and
  stderr shows the real `issue_701 pushed no branch this run` announcement in both legs. CJ
  declares (or is named by) the conflict edge, so `compute_waves` puts it in wave 1. In
  case 3 the unpushed bundle and its partner are both children adopted mid-run.

## Ruled out

- Folding the conflict edge into `held` / `declared_deps`: the hold would print the
  "prerequisite(s) not ready" line, which criterion (b) forbids, and would also hold partners
  of `held_finished` ids, which the brief puts out of scope.
- Building the map once before the loop: misses adopted children (mutation 1 shows the test
  catches it). Cost of the live build: one `conflict_map` call (one brief read per drive-set
  bundle) per wave, and only on runs where `held_unpushed` is non-empty.
- Re-reading `Conflicts with` from briefs inside `_runnable`: the brief asks to reuse
  `waves.conflict_map`.
- Advising "add `Depends on: <CA>` to the partner's brief and re-issue with both ids": the
  carry would then put CA on the line if its PR is open and clean, but it means editing a
  Plan artifact from a stderr hint. Waiting for the merge is always true and needs no edit.

## Known gaps (for sign-off)

- From the brief: a partner of a partner (CK `Conflicts with: CJ`, CJ held here) still
  builds, on a line without CJ — the same as today for a partner of any bundle that is not
  COMPLETE for another reason.
- A bundle with BOTH a `Depends on` and a `Conflicts with` edge to the same unpushed bundle
  prints two lines (the existing "skipped — prerequisite(s) not ready" and the new "held"
  line). Both are true; not deduplicated.
- A partner with no target of its own is held too, though it would never have been pointed
  at a line. That matches the existing `Depends on` hold of an unpushed bundle, which does
  not check the dependent's target either (`flow.py:765-768`), and the brief's "exactly as
  for a `Depends on` edge".

## Process note

While running the T3 gate I redirected its output to `/tmp/claude-suite-629.log`, outside
the roots I was given. That file is still there; I did not remove it (cleanup is the
harness's). Every later run piped its output instead.
