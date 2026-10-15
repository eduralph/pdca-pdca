# Build notes — issue 651 / reword-stale-strict-levelling-comment (iteration 4)

Target: `eduralph/pdca-harness` `main` @ `41210bc`, worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`
(clean at `41210bc` when I started; base blob of `flow.py` is `4e93c3f`, the one `patch.diff` names).
Line numbers say **base** (`41210bc`) or **patched** (worktree with `patch.diff` applied). `waves.py`
and every `flow.py` line above 2141 are the same in both.

## The short version

**The patch is byte-identical to iteration 3's, on purpose.** That patch had no defect: the v3
review passed C1, C3, C5, T1, T2 and T3 and said "No implementation defect found. C4 is the brief's
expected comment-only verification limitation, not a request to manufacture a test or alter runtime
behavior" (`iteration-v3/check-review.md:17`). All three send-backs (v1, v2, v3) came from the same
C4 row, which exits 77 because the patch ships no test. The brief requires that outcome
(`brief.md:12`, `:13`, `:23`), and **no build can change it**: the C4 script decides on file paths,
not content (details below). Rewording the comment just so the diff differs would mean re-checking
every claim for no gain, and C4 would still exit 77. So this round I kept the patch, re-ran all the
evidence from scratch, added one new mutation check (M4), and I'm handing the C4 decision to the human
in plain terms (see "For the human at sign-off").

## What changed

One file, comment lines only: `template/src/pdca_harness/flow.py`, inside `_drive_and_act`.
`git diff --numstat`: 15 added, 7 removed.

- **Paragraph 1** (base `flow.py:2141-2144` → patched `:2141-2145`). Removed "exactly as before" and
  "adoption never relaxes it". It now says the named batch is levelled strictly (`compute_waves`
  raises on a cycle or an unresolvable dependency) and that since #590 there is one relaxation, set
  out at the `offered` line: a `Depends on` / `Depends on (merged)` edge to a child a recovery seed
  offers. The stale `waves.py:243-246` line reference is replaced by the symbol reference
  (`waves.partition_schedulable`'s own docstring), which the brief allows. The quoted text "right for
  an explicit ``flow <ids>``" is at `waves.py:278-279`.
- **Paragraph 2** (RE-levelling, base `:2146-2155` → patched `:2147-2156`): unchanged.
- **Paragraph 3** (base `:2157-2159` → patched `:2158-2167`, directly above
  `offered = _offered_by_seeds(...)` at patched `:2168`). Rewritten to state both facts the brief
  requires: the edge is resolvable here but adds no edge in `compute_waves`, and the seed splice is
  what orders it. It also states the `Stacks on` refusal and what happens to a loop through the
  child, and ends with a "Pinned by" sentence naming the runtime test. Paragraph 2 already uses that
  style (patched `:2153-2154`).

## Each claim in the new wording, with the code and the test that pins it

| Claim (patched `flow.py` line) | Code on the target | Runtime test (`template/tests/test_flow_adopt_recovery.py`) |
|---|---|---|
| Named batch levelled strictly; `compute_waves` raises on a cycle or an unresolvable dep (2141-2142) | `waves.py:184` (`compute_waves` → `check_dep_graph`), `:102-109` (unresolvable → raise), `:116-133` (cycle → raise) | `:809` `test_without_the_seed_or_off_its_lineage_the_edge_is_still_refused`, `:844` `test_a_child_not_offered_is_still_refused_up_front` |
| Contract belongs to the request; `partition_schedulable`'s docstring calls raising "right for an explicit `flow <ids>`" (2142-2144) | `waves.py:277-279` | — (a quote, checked by reading) |
| One relaxation since #590: `Depends on` / `Depends on (merged)` edge to an offered child is resolvable instead of raising (2144-2145, 2159-2160) | patched `flow.py:2168-2170` (`offered = _offered_by_seeds(...)`, `compute_waves(..., offered=offered)`); `waves.py:95-96` (`continue`); docstring `:74-79` | `:769` `test_a_named_id_depending_on_a_seeds_child_is_driven_after_it`, `:788` (grandchild), `:900` (`Depends on (merged)`) |
| ...but adds NO edge in `compute_waves`, so a loop through the child is not seen here (2160-2161) | `waves.py:95-96` (no `edges.append`), `:110`; `:195-198` (`compute_waves` adds only in-batch edges, and the child is not in `bundles` yet) | `:948` `test_a_loop_through_an_offered_child_is_held_never_a_raise` |
| The child joins the schedule only at the `k=-1` splice, which re-levels with it in place; that splice orders the edge (2161-2163) | patched `flow.py:2176-2179` (the `k=-1` call); `:1714-1716` (`_reschedule(remaining + children)`); `:1526` (`compute_waves(schedulable)`, child now in-batch); `:1727` (`wave_list[k + 1:] = tail`); `:1730-1731` (child joins `bundles`) | `:769` asserts waves `[[601], [602], [810]]` |
| The splice holds such a loop instead of raising (2163) | `flow.py:1521-1522` (`partition_schedulable`, `_report_held`); `waves.py:319-323` (cycle members held, "dependency cycle") | `:948` (rc 1; both ends "held this run — dependency cycle") |
| A `Stacks on` edge to such a child still refuses (2163-2164) | `waves.py:95` (`dep not in stacks`) falls through to `:102-109` (raise); docstring `:79-80` | `:918` `test_stacks_on_an_offered_child_is_still_refused_up_front` |
| ...as does any other unresolvable dependency (2164-2165) | `waves.py:102-109` | `:809`, `:844` |

## Evidence I produced this round (all re-run on the final tree)

1. **The patch changes no code that runs.** With Python's `tokenize`, the token stream minus
   COMMENT/NL tokens is identical between `git show HEAD:template/src/pdca_harness/flow.py` and the
   patched file. `ast.dump` is identical. The patched file compiles. `git diff --check` is clean.
   Every changed line (plain diff, not `-w`) starts with `#`. Widest changed line: 92 characters,
   the width the block already uses.
2. **C4 still exits 77.** From the pdca-pdca root:
   `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` printed
   `PDCA-UNVERIFIABLE: patch ships no test (changed: template/src/pdca_harness/flow.py)`, exit 77.
3. **The #590 tests on the real (patched) tree:** `tests.test_flow_adopt_recovery`, 22 tests, OK
   (the 8 #590 cases at `:769-972` among them).
4. **Mutation checks: break each claim's behaviour in production code, watch its test go red.** One
   line changed per run, the 8 #590 tests run, and the file restored in a `finally` block. After all
   runs, `git diff` was byte-identical to `patch.diff`.

   | Run | One-line change to production source | Result (8 #590 tests) |
   |---|---|---|
   | REAL | none | 8 OK |
   | M1 | patched `flow.py:2168` → `offered = frozenset()`. This is the program the **old** comment described ("adoption never relaxes it"). | **6 FAIL**: `:769`, `:788`, `:874`, `:900`, `:918` (sub-case "depends on one child, stacks on the other"), `:948`. The 2 "still refused" boundary tests stay OK. |
   | M2 | `waves.py:95` → `if dn in offered:` (drop `and dep not in stacks`) | **3 FAIL**: all three sub-cases of `:918` |
   | M3 | patched `flow.py:2176` → `if False and adopt_seeds:` (no seed splice) | **4 FAIL**: `:769`, `:788`, `:900`, `:948` |
   | M4 (new this round) | `flow.py:1521` → `schedulable, held = list(remaining), {}` (strict re-level at the splice, not tolerant) | **2 FAIL**: `:948` (the loop is no longer held), and `:874`: the strict re-level raises "neither in this batch nor an existing COMPLETE bundle" for 810's edge to the child adoption did not take, `_reschedule` catches it ("could not re-wave"), and the test forbids that refusal text. |

   So, at runtime on `41210bc`: the old comment's central claim is false (M1), and each claim in the
   new wording is held in place by a test that drives production code (M1-M4). M4 is new: it pins
   "it holds such a loop instead of raising", which v3 could only cite.
5. **T3, through the configured runner** (`./engine/scripts/run-suite.sh`, pdca-pdca
   `pdca.toml:1375`, from the pdca-pdca root with `PDCA_WORKTREE` set): root suite
   `Ran 24 tests … OK`; driver suite `Ran 2423 tests … OK (skipped=2)`;
   `PDCA-EVIDENCE: root suite OK, driver suite OK`; exit 0. Log: `do-t3-suite-run.log` in this
   bundle (overwrites v3's).

Targeted runs used the test module's own documented command (`test_flow_adopt_recovery.py:33`:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_recovery`), the same shape
`run-verify.sh` uses, with the pdca-pdca `.venv` python and a timeout.

## Why the carry-forward cannot be cleared by a build

The finding is worded as a decision: "Decide whether source comparison suffices for this
comment-only correction". That is the human's call. Here is why no Do round can turn it into a pass:

- `run-verify.sh:133-138` sorts the patch's changed **paths**. Only `tests/*.py` or
  `template/tests/*.py` count as tests (`:136`). With no test path, `:142-143` print
  `PDCA-UNVERIFIABLE: patch ships no test` and exit 77, whatever the patch contains. Any patch that
  meets the Success criterion ("no other file changes", `brief.md:12`) has no test path, so it exits
  77.
- The only way to get a red→green there is a test that fails on base and passes on the patch. The
  patch changes no executed code (identical tokens and AST, above), so such a test would have to
  read the comment's text. `brief.md:13` forbids that by name ("Do must NOT add a token test or a
  code change to manufacture a red leg").

Alternatives ruled out, with their cost:

- **Token test that greps `flow.py` for the stale phrase.** About 15-20 lines in a new
  `template/tests/` file. C4 would go red→green, but only by testing comment text. It breaks
  `brief.md:12` (a second changed file) and `:13` (a token test).
- **New behavioural test of the #590 claims.** It is green before and after the patch (no executed
  code changes), so C4's red leg would report "green without the fix", a gate **fail**, which is
  worse than 77. It is also a second file (`brief.md:12`), and it would repeat the 8 existing tests at
  `test_flow_adopt_recovery.py:769-972`.
- **Reword the comment so this round's diff differs from v3.** It would not move C4 (the path rule
  above), and every reworded claim would need re-checking against the 8 table rows. The v3 wording
  already passed C1/C3/C5. That is churn with no gain, so I didn't do it.
- **Keep a line reference, corrected to `waves.py:278-279`.** The brief allows it, but a line
  reference is exactly what went stale here (243-246 drifted about 35 lines). The symbol reference
  can't drift.
- **Name all eight #590 tests in the comment.** The names are 50-67 characters, one per comment line:
  about 8-9 extra lines, against 2.5 for one name plus "the other #590 cases beside it". The one
  named test covers both required facts (it fails under M1 on the refusal and under M3 on the
  ordering).
- **Describe the "adoption does not take the child" case in the comment.** Left to
  `_offered_by_seeds`'s docstring (`flow.py:2018-2020`), which paragraph 3 names. The brief doesn't
  require it, and it would cost 1-2 more lines.

## Refute-your-own-test (forced answers)

- **(a) Genuine red?** For a test of the *patch*: **no, and none is possible.** No test ships
  (`brief.md:23`: "Test file: none"), and reverting the patch changes no executed code, so no test can
  be red before and green after without reading the comment text, which the brief forbids. That is
  why C4 is 77. For the *claims* the comment makes: **yes.** M1-M4 turn the cited tests red (6, 3
  sub-cases, 4, 2 of 8) and the real code turns them green (8/8). I ran each one this round and
  restored after each.
- **(b) Production path?** **Yes, for the claims.** The cited tests drive the real CLI path
  (`cli._flow`, test file `:185-188` → `flow_ids` → `_drive_and_act` → `_offered_by_seeds` /
  `waves.compute_waves(offered=…)` / `_adopt_split_children(k=-1)`). The mutations were made in the production files themselves, not in
  a copy or a mock.
- **(c) Fixture includes the fault?** **Yes.** The stranded split is built by production code (the
  test module's docstring, `:25-27`: the fixture is carried to COMPLETE by the production
  `flow._drive_wave`). The offered child really is in flight. The `Stacks on` case, the loop case,
  and the "another live process holds the claim" case (a real second process, `:739-767`) are all in
  the fixtures.

## Commit-readiness

The target has no formatter, linter or commit hook to run: no `.pre-commit-config.yaml`, no
`[tool.ruff|black|flake8|isort|pylint]` section in `template/pyproject.toml.jinja`, no lint or format
target in `template/Makefile`, no Python linter in `.github/workflows/*`, `core.hooksPath` unset, and
no non-sample hooks in the common git dir (none of ruff/black/flake8/pre-commit is installed here
either). `git diff --check` is clean and the changed lines stay within the block's existing 92
columns. `CONTRIBUTING.md:9-17` asks for a DCO `Signed-off-by` on commits; that belongs to the
publish commit, not the patch.

## Other stale mentions (out of scope, noted only, not fixed)

- **New this round:** `template/tests/test_flow_adopt_split.py:598-599`, the docstring of
  `test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost`, calls the splice "the one place the id
  list stops being levelled strictly". Since #590 there is a second place: the up-front levelling
  accepts an edge to an offered child (`waves.py:95-96`). It is a test docstring, so it is low-stakes,
  but it makes the same "only one relaxation" mistake in a different spot. The brief puts it out of
  scope (`brief.md:20`), so I left it alone.
- `flow.py:2005-2009` (`_offered_by_seeds`'s docstring) describes the pre-#590 refusal in the past
  tense and then the fix. It is correct.
- The other "exactly as before" hits (`gates.py:348`, `:576`, `lane.py:11`, `progress.py:194`,
  `config.py:334`, base `flow.py:2410` = patched `:2418`, and several tests and docs) are about other
  features. No doc under `docs/` says adoption never relaxes the strict check.

## Ordering note (#674)

My hunks span patched `flow.py:2138-2170` (context included) and add 8 net lines. #674's held-bundle
state at `flow.py:2134` is above them and unchanged. Its wave-loop work at base `:2269-2350` moves to
patched `:2277-2358`. The hunks don't overlap.

## What I read

`brief.md`; the code the comment describes (`flow.py` `_drive_and_act`, `_offered_by_seeds`,
`_adopt_split_children`, `_reschedule`; `waves.py` `check_dep_graph`, `compute_waves`,
`partition_schedulable`); the #590 tests in `test_flow_adopt_recovery.py`, to tie each claim to a
runtime check; the C4 and T3 scripts and `pdca.toml` rows the brief cites; and, because the
carry-forward points at them, `iteration-v3/patch.diff`, `iteration-v3/check-review.md`,
`iteration-v3/build-notes.md`, `iteration-v3/session-carry-forward`, and `deferred-findings.json`
(which I only read; per the carry-forward its items are not build work).

## My own mistake during the build

My second `Edit` dropped the space after `=` in the code line `offered = _offered_by_seeds(...)`
(patched `:2168`). The first patch comparison against v3 caught it (`offered =_offered_by_seeds`). I
fixed it before running anything else. `git diff -w` would have hidden it, which is why the
comment-only check above uses the plain diff. The final `patch.diff` is byte-identical to v3's, and
the token/AST check confirms that no code line changed.

## For the human at sign-off

C4 will show `unverifiable` (exit 77) → §6. It is not a defect in this patch, and a fifth build
would hit the same wall. To clear it, read patched `flow.py:2141-2167` against `waves.py:74-80`,
`:95-96`, `:102-109`, `:195-198` and patched `flow.py:2168-2179`. If you also want the runtime
evidence, run these from the worktree root:

```
cd template && PYTHONPATH=src python3 -m unittest -v tests.test_flow_adopt_recovery   # 22 OK
# M1 (the old comment's world): in src/pdca_harness/flow.py change
#   `offered = _offered_by_seeds(cfg, list(adopt_seeds)) if adopt_seeds else frozenset()`
#   to `offered = frozenset()`; re-run: 6 of the 8 #590 tests fail on the up-front refusal.
# M2: in src/pdca_harness/waves.py:95 drop `and dep not in stacks`: the 3 Stacks-on sub-cases fail.
# M3: change `    if adopt_seeds:` (the k=-1 splice) to `    if False and adopt_seeds:`: 4 fail.
# M4: in flow.py:1521 use `schedulable, held = list(remaining), {}`: the loop test and :874 fail.
# Restore each with: git checkout -- <file> && git apply <bundle>/patch.diff
```

**Process note for Act (not build work).** The auto-iterate has now sent this bundle back to Do
three times for the same C4 row, and each time the reviewer worded it as a human decision
("Decide whether…"). By v3 the reviewer also wrote "No implementation defect found". Each round
cost a full Do + Check (attempts 2-4 at max effort, `loop-telemetry.json`). A rule that would have
stopped this after round 0: **don't count a C4 row as an implementation-level finding when its gate
log says `PDCA-UNVERIFIABLE: patch ships no test` and the brief's `Test file:` field says none.** That
row belongs in §6 for the human. It is not a reason to rebuild.
