# Build notes — issue 651 / reword-stale-strict-levelling-comment (iteration 3)

Target: `eduralph/pdca-harness` `main` @ `41210bc`, worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`.
Line numbers say **base** (41210bc) or **patched** (worktree with `patch.diff` applied).

## What changed

One file, comment lines only: `template/src/pdca_harness/flow.py`, inside `_drive_and_act`.
`git apply --numstat`: 15 added, 7 removed.

- **Paragraph 1** (base `flow.py:2141-2144` → patched `flow.py:2141-2145`). Removed "exactly as
  before" and "adoption never relaxes it". It now says the named batch is levelled strictly
  (`compute_waves` raises on a cycle or an unresolvable dependency) and that since #590 there is
  one relaxation: a `Depends on` / `Depends on (merged)` edge to a child a recovery seed offers.
  The stale `waves.py:243-246` line reference is replaced by a symbol reference
  (`waves.partition_schedulable`'s own docstring). The quoted text is at patched
  `waves.py:278-279` (waves.py is unchanged by this patch).
- **Paragraph 2** (RE-levelling, base `2146-2155` → patched `2147-2156`): unchanged.
- **Paragraph 3** (base `flow.py:2157-2159` → patched `flow.py:2158-2167`, directly above
  `offered = _offered_by_seeds(...)` at patched `:2168`). Rewritten so it states both facts the
  brief requires (resolvable here but no edge in `compute_waves`; ordered at the seed splice),
  plus the `Stacks on` refusal and what happens to a loop through the child. It now ends with a
  "Pinned by" sentence naming the runtime test, in the same style paragraph 2 already uses
  (patched `flow.py:2153-2154`).

## Each claim in the new wording, with the code and the test that proves it

| Claim (patched flow.py line) | Code on the target | Runtime test (template/tests/test_flow_adopt_recovery.py) |
|---|---|---|
| Named batch levelled strictly; `compute_waves` raises on a cycle or unresolvable dep (2141-2142) | `waves.py:184` (`compute_waves` → `check_dep_graph`), `:102-109` (unresolvable → raise), `:116-133` (cycle → raise) | `:809` `test_without_the_seed_or_off_its_lineage_the_edge_is_still_refused`, `:844` `test_a_child_not_offered_is_still_refused_up_front` |
| `Depends on` / `Depends on (merged)` edge to an offered child is resolvable instead of raising (2144-2145, 2159-2160) | `flow.py:2168-2170` patched (`offered = _offered_by_seeds(...)`; `compute_waves(..., offered=offered)`), `waves.py:95-96` (`continue`), docstring `:74-79` | `:769` `..._is_driven_after_it`, `:788` grandchild, `:900` `Depends on (merged)` |
| ...but adds NO edge in `compute_waves`, so a loop through the child is not seen there (2160-2161) | `waves.py:95-96` (no `edges.append`), `:195-198` (`compute_waves` adds only in-batch edges; the child is not in `bundles` yet) | `:948` `test_a_loop_through_an_offered_child_is_held_never_a_raise` |
| The child joins the schedule only at the `k=-1` splice, which re-levels with it in place; that splice orders the edge (2161-2163) | `flow.py:2176-2179` patched (the `k=-1` call), `:1714-1716` (`_reschedule(remaining + children)`), `:1727` (`wave_list[k + 1:] = tail`), `:1730-1731` (children join `bundles`) | `:769` asserts waves `[[601], [602], [810]]` |
| The splice holds such a loop instead of raising (2163) | `flow.py:1521` (`partition_schedulable`), `waves.py:319-323` (cycle members held, "dependency cycle") | `:948` (rc 1, both ends "held this run — dependency cycle") |
| A `Stacks on` edge to an offered child still refuses (2164) | `waves.py:95` (`dep not in stacks`) falls through to `:102-109` (raise), docstring `:79-80` | `:918` `test_stacks_on_an_offered_child_is_still_refused_up_front` |

## The carry-forward, and what is different this time

Both earlier attempts shipped a comment-only patch with no test. The wording passed review (C1,
C3 and C5 PASS, "No implementation defect found"). Each time, C4 exited 77 ("patch ships no
test"), the reviewer raised "decide whether source comparison suffices", and the auto-iterate
sent it back to Do.

What build work cannot change: C4 will exit 77 again. I re-ran the gate on this patch
(`PDCA_BUNDLE=… ./engine/scripts/run-verify.sh` from pdca-pdca): `PDCA-UNVERIFIABLE: patch
ships no test`, exit 77. The only way to make C4 go red→green is to ship a test path in the
patch. The brief rules that out twice: the Success criterion says "no other file changes"
(brief.md:12), and Falsifiability says "Do must NOT add a token test or a code change to
manufacture a red leg" (brief.md:13). The patch also changes no code that runs (proof below),
so there is no runtime red→green for the patch itself to show. C4 → §6 NEEDS-HUMAN is the
outcome the brief calls correct (brief.md:13, :23). Whether the evidence below is enough is the
human's call at sign-off, not something a fourth build can settle.

What is new, so the evidence is no longer just "source comparison":

1. **Runtime evidence for every claim, with mutation checks.** For each claim I broke the
   behaviour it describes in the production source (one line), ran the eight #590 tests
   (`test_flow_adopt_recovery.py:769-972`), and restored the tree. Each claim's test goes red
   when the behaviour is removed and green on the real code:

   | Run | One-line change to production source | #590 tests (8) |
   |---|---|---|
   | REAL | none (patched tree) | 8 ok |
   | M1 | patched `flow.py:2168` → `offered = frozenset()`. This is exactly the program the **old** comment described ("adoption never relaxes it"). | **6 FAIL**: `:769`, `:788`, `:874`, `:900`, `:918` (the "depends on one child, stacks on the other" sub-case: the refusal names 601, not 602), `:948`. All fail on the up-front refusal "is neither in this batch nor an existing COMPLETE bundle". The 2 "still refused" boundary tests stay ok. |
   | M2 | `waves.py:95` → `if dn in offered:` (drop `and dep not in stacks`) | **3 FAIL**: all three sub-cases of `:918` (rc 0 instead of 2). The other 7 ok. |
   | M3 | patched `flow.py:2176` → `if False and adopt_seeds:` (no seed splice) | **4 FAIL**: `:769`, `:788`, `:900` (rc 1: 810 never built, because without the splice nothing schedules the child), `:948` (no wave driven, nothing held). |

   So the old comment's central claim is false at runtime on 41210bc (M1), and every claim in
   the new wording is held in place by a test that drives production code. After each run:
   `git checkout -- flow.py waves.py && git apply patch.diff`, then `diff <(git diff) patch.diff`
   came back empty. No "MUTATION" marker is left in `template/src`.
2. **The comment now points at that test** ("Pinned by
   `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it` and the other #590 cases
   beside it"), so a reviewer reading only the patch can check the claims by running code. That
   test pins both required facts: under M1 it fails on the refusal, under M3 it fails on the
   ordering. The other cases sit under the `# -- #590:` header at
   `test_flow_adopt_recovery.py:725`.
3. **Mechanical proof the patch is comment-only** (it changes no code that runs): with Python's
   `tokenize`, the token stream minus COMMENT/NL tokens is identical between `git show
   HEAD:…/flow.py` and the patched file. `ast.dump` (positions ignored) is identical too. The
   file compiles, and `git diff --check` is clean.

## Refute-your-own-test (forced answers)

- **(a) Genuine red?** For a test of the *patch*: **no**, and none is possible. No test ships
  (brief: "Test file: none"), and reverting the patch changes no code that runs (identical
  token stream and AST), so no test can be red before and green after without testing the
  comment's text, which the brief forbids. That is why C4 is 77. For the *claims* the comment
  makes: **yes**. M1/M2/M3 above turn the cited tests red (6/8, 3 sub-cases, 4/8), and the real
  code turns them green (8/8). I actually ran each one and restored after each.
- **(b) Production path?** **Yes.** The cited tests drive `cli._flow` (`:185-188`) →
  `flow_ids` → `_drive_and_act` → `_offered_by_seeds` / `waves.compute_waves(offered=…)` /
  `_adopt_split_children(k=-1)`. Only the six leaves are stubbed, and the wave/pass spies call
  the production functions and pass their results through (`:22-27`, `:324-338`). The mutations
  were made in the production files themselves, not in a copy or a mock.
- **(c) Fixture includes the fault?** **Yes.** The stranded split is built by production
  `split.accept` and `flow._drive_wave` (`:252-265`). The offered child really is in flight.
  The `Stacks on`, loop, and "another live process holds the claim" cases (`:739-767`, a real
  second process) are all in the fixtures.

## Suites (project runner)

`./engine/scripts/run-suite.sh` (the T3 row, pdca-pdca `pdca.toml:1375`) from the pdca-pdca
root with `PDCA_WORKTREE` set, on the final tree: root suite `Ran 24 tests … OK`, driver suite
`Ran 2423 tests … OK (skipped=2)`, `PDCA-EVIDENCE: root suite OK, driver suite OK`, exit 0. Log:
`do-t3-suite-run.log` in this bundle. Targeted runs used the test file's own documented command
(`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery…`, see
`test_flow_adopt_recovery.py:33`) under `timeout 600`, with the pdca-pdca `.venv` python the
runner uses.

## Alternatives ruled out

- **A token test that greps flow.py for the stale phrase.** It would make C4 go red→green, but
  only by testing comment text. That is the manufactured red leg brief.md:13 bans, and it is a
  second changed file, which brief.md:12 bans.
- **A new behavioural test of the #590 claims.** It is green before *and* after the patch (no
  executed code changes), so C4 would report "not red pre-fix", a gate failure and worse than
  77. It would also repeat the eight existing tests at `test_flow_adopt_recovery.py:769-972`
  and add a second file.
- **Keep a line reference, corrected to `waves.py:278-279`.** The brief allows it, but a line
  reference is exactly what went stale here (243-246 drifted about 35 lines as waves.py grew).
  The symbol reference cannot drift.
- **Name all eight #590 tests in the comment.** The names are 52-66 characters, so each needs
  its own comment line: about 8-9 extra lines, against 2 for one name plus "the other #590 cases
  beside it". I chose the short form. The one named test covers both required facts.
- **Fold paragraph 3 into paragraph 1.** That would leave the RE-levelling paragraph directly
  above `offered = …`, the line paragraph 3 explains. I kept three paragraphs. Paragraph 1 now
  names the exception itself, so it is true read alone. Paragraph 3 opens "The #590 relaxation:"
  rather than "That relaxation". v2's advisory review noted, as a minor point, that "That" made
  the reader look back across paragraph 2.
- **Describe the "adoption does not take the child" case** (v2 had a sentence on it). Left to
  `_offered_by_seeds`'s docstring (base and patched `flow.py:2018-2020`), which paragraph 3
  names. The brief does not require it, and it would cost 1-2 more lines.

## Commit-readiness

The target has no formatter, linter or commit hook configured: no `.pre-commit-config.yaml`, no
ruff/black/flake8 settings in `template/pyproject.toml.jinja` or `template/Makefile`, no
`core.hooksPath`, and no non-sample hooks in the common git dir. `CONTRIBUTING.md:9-17` asks
for a DCO `Signed-off-by` on commits; that belongs to the publish step's commit, not the patch.
Every changed line is ≤ 92 characters, the same width the rest of the block keeps (its widest
lines are 92 characters). `git diff --check` is clean.

## Other stale mentions (out of scope, noted only)

None found. `flow.py:2005-2009` (`_offered_by_seeds` docstring) describes the pre-#590 refusal
in the past tense and the fix correctly. The other "exactly as before" hits (`gates.py:348`,
`:576`, `lane.py:11`, `progress.py:194`, `config.py:334`, base `flow.py:2410` = patched
`:2418`) are about other things. `docs/07-crosscutting.md:343` mentions recovery seeds but not strict levelling.

## Ordering note (#674)

My hunks span patched `flow.py:2138-2170` and add 8 net lines. #674's held-bundle state at
`flow.py:2134` is above them and unchanged. Its wave-loop work at base `2269-2350` moves to
patched `2277-2358`. The hunks do not overlap.

## What I read

`brief.md`; the code the comment describes (`flow.py` `_drive_and_act`, `_offered_by_seeds`,
`_adopt_split_children`, `_reschedule`; `waves.py` `check_dep_graph`, `compute_waves`,
`partition_schedulable`); the C4/T3 gate scripts and `pdca.toml` rows the brief cites; and,
because the carry-forward points at them, `iteration-v1/` and `iteration-v2/` (`patch.diff`,
`session-carry-forward`, v2's `check-review.md`, `check-advisory-code-review.md`,
`check-gates.md`, `gate-logs/C4-verify.log`). I also read the #590 tests, to find runtime
evidence for each claim. I did not read `deferred-findings.json`; the carry-forward says those
are not build work.

## My own mistake during the build

The first T3 run's output was redirected into the worktree root as `.git-suite-run.log`
(untracked, not git-ignored). I could not stop that run safely: a kill by script name could hit
another worktree's gate run. So I moved the file into this bundle while the run was going (same
filesystem, so a rename, and the open file kept being written). After that, `git status` showed
only `flow.py`. That run passed. The final run above, on the final tree, overwrote the same log
and is the one cited. The worktree is clean apart from the patch.

## For the human at sign-off

C4 will show `unverifiable` (exit 77) → §6. To clear it, read patched `flow.py:2141-2167`
against `waves.py:74-80`, `:95-96`, `:102-109`, `:195-198` and patched `flow.py:2168-2179`.
To re-check the runtime evidence yourself, from the worktree root:

```
cd template && PYTHONPATH=src python3 -m unittest -v tests.test_flow_adopt_recovery   # 22 ok
# M1 (old comment's world): in src/pdca_harness/flow.py set the line
#   `offered = _offered_by_seeds(cfg, list(adopt_seeds)) if adopt_seeds else frozenset()`
#   to `offered = frozenset()`, re-run: 6 of the 8 #590 tests fail on the up-front refusal.
# M2: in src/pdca_harness/waves.py:95 drop `and dep not in stacks`: the 3 Stacks-on sub-cases fail.
# M3: change `    if adopt_seeds:` (the k=-1 splice) to `if False and adopt_seeds:`: 4 fail.
# Restore each with: git checkout -- <file> && git apply <bundle>/patch.diff
```

Process note for Act (not build work): the auto-iterate has now sent this bundle back to Do
twice for a C4 `unverifiable` row that the brief itself declares expected (brief.md:13, :23),
and that the reviewer worded as a human decision ("Decide whether…"). A third send-back would
meet the same wall. A rule that does not auto-iterate on C4 = 77 when the brief's `Test file`
is "none" and its Falsifiability names exit 77 as the expected outcome would have saved two
cycles.
