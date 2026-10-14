# Build notes — issue 651 / reword-stale-strict-levelling-comment (iteration 2)

Target: `eduralph/pdca-harness` `main` @ `41210bc`, worktree `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, clean at `41210bc` before the edit).
Patch: `patch.diff`, one file, `template/src/pdca_harness/flow.py`, 14 added / 7 removed,
all `#` comment lines. No test ships (brief.md:23, "Test file: none").

Recommendation: likely-fix. Accept after the reading check under "Human check" below.

## The carry-forward, and why this rebuild cannot close it

The iteration-1 carry-forward (brief.md:36-39) re-ran Do for one finding: "C4 Verification
(red→green) — Accept source comparison as sufficient verification … the gate explicitly
exits 77 because no test ships". That finding asks the **human** to accept a reading check.
Build work cannot close it:

- Nothing executable changes, so no behaviour test can go red. I checked this, not just
  argued it. With the patch reverted, `tests.test_flow_adopt_recovery` runs 22/22 OK, the
  same as with the patch (details under "Refute" below).
- The only test that could go red is one that reads the comment text. brief.md:13 forbids
  that ("Do must NOT add a token test or a code change to manufacture a red leg"), and so
  do my own instructions (no stand-in test that passes without proving anything).
- So C4 will again print `PDCA-UNVERIFIABLE: patch ships no test` and exit 77
  (pdca-pdca `engine/scripts/run-verify.sh:142-143`), which routes to §6. The brief calls
  that the correct outcome (brief.md:13, same shape as #476).

Another auto-iterate on that C4 item will hit the same exit 77. It needs the human's
reading check, not a third build.

What I changed instead of re-shipping v1 as-is: the wording now also covers the two cases
where an offered edge is resolvable but **not** ordered by `compute_waves`. These are a loop
through the offered child, and a child that adoption then does not take. Both follow from
"adds NO edge here". v1 left them out, so v1's first paragraph ("`compute_waves` raises
on a cycle", one relaxation) could still be read as "a loop through an offered child is
refused up front". It is not, since #590 (pinned by
`test_a_loop_through_an_offered_child_is_held_never_a_raise`,
`template/tests/test_flow_adopt_recovery.py:948-972`). This also answers iteration 1's
"fitness-to-purpose" item: the text now keeps "resolvable here" apart from "ordered or held
later" in every case. I also added a per-claim evidence table below (each claim → the code
→ an existing test that pins it), so the reading check is backed by tests that run.

## What changed (line numbers on the patched tree; base numbers in brackets)

1. `flow.py:2141-2145` [base `:2141-2144`]. Removed "exactly as before" and "adoption never
   relaxes it". Now: the named batch is levelled strictly (`compute_waves` raises on a cycle
   or an unresolvable dependency); that contract belongs to the request; since #590 it has
   one relaxation, a `Depends on` / `Depends on (merged)` edge to a child a recovery seed
   offers, set out at the `offered` call below. The stale `waves.py:243-246` reference is
   gone (on `41210bc` those lines are the inner `visit` of `_cycle_members`). The comment
   now names the symbol only, which the brief allows (brief.md:12). The quoted text "right
   for an explicit `flow <ids>`" is at `waves.py:278-279`, inside the docstring that opens
   at `:277`.
2. `flow.py:2147-2156` [base `:2146-2155`]: the RE-levelling paragraph, unchanged.
3. `flow.py:2158-2166` [base `:2157-2159`]: the #590 paragraph, rewritten to state the
   whole relaxation next to the code it describes (`flow.py:2167`, `:2169`).

Why the relaxation sits in two places: paragraph 1 is the contract, and paragraph 3 sits
directly above the `offered` call. Putting all the detail in paragraph 1 would leave the
RE-levelling paragraph directly above `offered = …`, which it does not describe. Leaving
paragraph 1 silent would keep the contradiction. Paragraph 1 names the edge kinds but says
"set out … below" rather than "accepted". The brief warns that "accepted" alone would
suggest `compute_waves` orders the edge (brief.md:12).

## Each claim in the new wording → code → existing test that pins it

| Claim (patched `flow.py` line) | Code on `41210bc` | Pinned by (`template/tests/test_flow_adopt_recovery.py`) |
|---|---|---|
| Named batch levelled strictly; `compute_waves` raises on a cycle / unresolvable dep (:2141-2142) | `waves.py:184` → `check_dep_graph` raises at `:103-109` (unresolvable), `:120-125` (cycle) | `:809` `test_without_the_seed_or_off_its_lineage_the_edge_is_still_refused`; `:844` `test_a_child_not_offered_is_still_refused_up_front` |
| Raising is "right for an explicit `flow <ids>`" per `partition_schedulable`'s docstring (:2143-2144) | `waves.py:278-279` | — (quoted text) |
| The request includes the in-flight children seeds offer (:2158-2159) | `flow.py:2002-2052` (`_offered_by_seeds`); passed in at `flow.py:2167`, `:2169` | `:788` `test_a_seeds_grandchild_through_a_split_child_counts_as_offered` |
| `Depends on` / `Depends on (merged)` edge to one is resolvable here instead of raising (:2159-2160) | `waves.py:74-79`, `:95-96` (`if dn in offered and dep not in stacks: continue`) | `:769` `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it`; `:900` `test_depends_on_merged_on_an_offered_child_resolves_like_depends_on` |
| …but adds NO edge in `compute_waves` (:2160-2161) | `waves.py:95-96` skips the `edges.append` at `:93`; `compute_waves` adds only in-batch edges, `waves.py:195-198` | `:948` (the loop is invisible up front because no edge exists) |
| The child joins only at the `k=-1` splice, which re-levels with it in place, so the splice orders the edge (:2161-2162) | `flow.py:2176` (`_adopt_split_children(…, k=-1, …)`), `flow.py:1715-1716` (`remaining + children` → `_reschedule`), `flow.py:1526` (`compute_waves` on the re-levelled set), `flow.py:1727` (`wave_list[k + 1:] = tail`) | `:769` asserts waves `[["issue_601"], ["issue_602"], ["issue_810"]]`, i.e. 810 after the child 602 |
| A loop through the child is found and held at the splice, never a raise (:2162-2163) | `flow.py:1521` (`partition_schedulable`), `waves.py:283-286` (held when in a cycle) | `:948` `test_a_loop_through_an_offered_child_is_held_never_a_raise` (rc 1, both ends held, no refusal) |
| If adoption does not take the child, its dependent is held or skipped (:2163-2164) | `flow.py:2018-2020` (`_offered_by_seeds` docstring), `flow.py:681-714` (`_runnable`) | `:874` `test_an_offered_child_another_run_holds_is_held_never_a_raise` |
| A `Stacks on` edge to such a child still refuses, like anything else unresolvable (:2165-2166) | `waves.py:79-80`, `:95` (`dep not in stacks`), `:102-109` | `:918` `test_stacks_on_an_offered_child_is_still_refused_up_front`; `:809` |

All 22 tests in that module pass on the patched tree, and they pass on the base too (see
"Refute"). They run as part of the T3 driver suite.

## Checks run

- Comment-only, byte level: `git diff -U0 | grep '^[+-]' | grep -v '^[+-]\s*#'` (file
  headers excluded) prints nothing; the same holds under `git diff -w`. `git diff --stat`:
  only `template/src/pdca_harness/flow.py`, 14+/7-. `git diff --check`: clean.
- Comment-only, parser level: `ast.dump(ast.parse(base)) == ast.dump(ast.parse(patched))`
  → True; the non-comment token stream (`tokenize`, comments and NL/INDENT dropped) is
  identical → True; the patched file compiles.
- One slip I caught and fixed: my first edit lost the space in `offered = _offered_by…`
  (`flow.py:2167`). The byte-level check above was run after the fix and shows no code
  line changed.
- T3 through the project's wrapper (pdca-pdca `engine/scripts/run-suite.sh`,
  `PDCA_WORKTREE` = the worktree, under `timeout 580`):
  `Ran 24 tests … OK` (root suite), `Ran 2423 tests … OK (skipped=2)` (driver suite),
  `PDCA-EVIDENCE: root suite OK, driver suite OK`, rc 0.
- `patch.diff` is `git diff` of the worktree. After the revert run below I re-applied it
  with `git apply` and `cmp` showed the working-tree diff byte-identical to `patch.diff`.
- Formatter / commit hooks: the target configures none. There is no `.pre-commit-config.yaml`,
  no hooks under `.git/hooks` other than samples, no ruff/flake8/black/line-length settings
  in `template/pyproject.toml.jinja` or `template/Makefile`, and no lint step in
  `.github/workflows/` (only `docs-check.yml`, which lints Markdown under `docs/`). The new
  lines are at most 92 characters, the width the surrounding block already uses
  (`flow.py:2151` is 92). The one commit rule is DCO sign-off (`CONTRIBUTING.md:9-19`,
  `git commit -s`), which applies at publish, not to the patch.

## Rejected alternatives (with cost)

- **A test that reads the comment** (e.g. assert "never relaxes" is absent from
  `flow.py`): about 15 lines in a new `template/tests/test_*.py`. It would go red→green
  under C4, but brief.md:13 forbids it, and it checks text, not behaviour. It would turn C4
  green without proving anything the diff doesn't already show. Rejected.
- **A new behaviour test of the #590 relaxation**: it would be green on both sides. I
  showed this: the 8 existing #590 tests (`:769`-`:972`) pass with the patch reverted.
  C4 would flag it as not red before the fix. It would also duplicate those 8 tests.
  Rejected.
- **A general checker that every `file.py:NNN` reference in a comment points at its text**:
  `template/src` has 74 such references. At least two others are already stale and out of
  scope (below), so the checker would stay red after this patch unless I fixed them too.
  That breaks brief.md:20. Rejected.

## Refute-your-own-test (a/b/c)

No test ships, so these answers are about the evidence, not a test of mine.

- **(a) Genuine red? No, and none is possible here.** I reverted the patch
  (`git checkout -- template/src/pdca_harness/flow.py`, `git diff` empty) and ran
  `tests.test_flow_adopt_recovery` (cwd `template`, `PYTHONPATH=src`, `timeout 300`): 22
  `... ok`, `OK`, the same as on the patched tree. This shows that no behaviour test binds
  a comment-only change. With the patch reverted, the base comment's "adoption never
  relaxes it" (`flow.py:2144` on base) sits next to `:769`, a passing test that only works
  because adoption relaxes the check. That pair is the "red" side; it shows up on reading,
  not in a test run.
- **(b) Production path? Yes, for the evidence.** Those tests call `cli._flow`
  (`test_flow_adopt_recovery.py:185-188`), which reaches `_drive_and_act` →
  `waves.compute_waves(…, offered=…)` → `_adopt_split_children(k=-1)` in production code.
  Only the Plan/build/sign-off leaves are stubbed and the wave driver is spied on (`_arm`,
  `:269-277`). The dependency checks and adoption are not stubbed.
- **(c) Fixture includes the fault? Yes.** `_strand_a_split` (`:252-260`) leaves a real
  split parent with in-flight children on disk, written by production code. The cases
  include a `Stacks on` edge to an offered child (`:918`), a loop through one (`:948`),
  and a child whose claim another live process holds, through a real subprocess (`:874`,
  `_hold_claim` at `:739-767`).

C4 will report `unverifiable` → §6. That is the honest result for this slice.

## Human check (what to read at sign-off)

```
cd "$PDCA_WORKTREE"
sed -n '2141,2169p' template/src/pdca_harness/flow.py          # the reworded block
sed -n '74,80p;90,109p;184p;195,198p;278,279p' template/src/pdca_harness/waves.py
sed -n '2018,2020p;2167,2178p' template/src/pdca_harness/flow.py
```

Confirm that: the block no longer says "exactly as before" or "never relaxes"; it says the
offered `Depends on` / `Depends on (merged)` edge is resolvable but adds no edge in
`compute_waves`, and that the `k=-1` splice orders it; `Stacks on` still refuses; and there
is no line number left except symbol references.

## Other stale wording found (not fixed; out of scope per brief.md:20)

- `flow.py:2070-2071` (`_drive_and_act` docstring): "`compute_waves` orders the batch into
  dependency waves (rejecting a cycle / unresolved dep up front)". This is borderline. An
  edge to an offered child is not "unresolved", so that half still holds. But since #590 a
  loop through an offered child is not rejected up front; it is held at the splice
  (`:948`). Possibly worth a follow-up issue.
- Two stale line references in `_adopt_split_children`'s docstring, not about strict
  levelling: `flow.py:1600` cites `flow.py:1424` for the `_point_at_integration` call, but
  that call is at `flow.py:2254` on `41210bc` (`:2261` with this patch); line 1424 is a
  comment about `repr`-quoting.
  `flow.py:1621` cites `flow.py:1370-1379` for "a held named id stays in the map", but
  those lines are now inside `_adoptable`'s docstring about reading `split-lineage.json`.
- The other "exactly as before" hits (`flow.py:2417`, `config.py:334`, `lane.py:11`,
  `gates.py:348`, `gates.py:576`, `progress.py:194`) are about other features and say
  nothing about strict levelling or adoption.

## Ordering with #674 (brief.md:16-17)

This patch's hunks are at base `flow.py:2141-2144` and `:2157-2159`. #674 works at base
`:2134` and `:2269-2350`. They don't overlap. This patch adds 7 net lines above #674's later
hunks, so on the folded line those hunks move down by 7 (e.g. base `:2269` → `:2276`).
