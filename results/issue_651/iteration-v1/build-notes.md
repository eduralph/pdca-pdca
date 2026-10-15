# Build notes — issue 651 / reword-stale-strict-levelling-comment

Target: `eduralph/pdca-harness` `main` @ `41210bc`, worktree `$PDCA_WORKTREE`.
Patch: `patch.diff` — one file, `template/src/pdca_harness/flow.py`, 11+/7-, comment lines only.

## What changed (line numbers on the patched tree)

1. `flow.py:2141-2145` (was `:2141-2144`). Dropped "exactly as before" and "adoption never
   relaxes it". The paragraph now says the named batch is levelled strictly
   (`compute_waves` raises on a cycle or an unresolvable dependency) and that since #590 it
   has exactly one relaxation, which the paragraph next to the `offered` call spells out.
   The stale `waves.py:243-246` line reference is removed; the comment now names the
   symbol only (`waves.partition_schedulable`'s own docstring), which the brief allows. The
   quoted text "right for an explicit `flow <ids>`" is at `waves.py:278-279` (docstring
   opens at `:277`), checked on the tree.
2. `flow.py:2158-2163` (was `:2157-2159`). The #590 paragraph now states both facts the
   criterion needs:
   - a `Depends on` / `Depends on (merged)` edge to a seed's in-flight child is resolvable
     instead of raising, but adds NO edge in `compute_waves` (`waves.py:95-96`:
     `if dn in offered and dep not in stacks: continue` — skips without `edges.append`);
   - the child joins the schedule only at the `k=-1` splice, which re-levels with it in
     place, so that splice orders the edge (`flow.py:2164-2166` compute `offered` and pass
     it to `waves.compute_waves`; the splice is `_adopt_split_children(..., k=-1, ...)`
     just below, `flow.py:2173`);
   - a `Stacks on` edge to such a child still refuses (`waves.py:95` `dep not in stacks`,
     docstring `waves.py:74-80`).
   The middle "RE-levelling" paragraph (`flow.py:2147-2156`) is unchanged; its "It is not
   a promise about the RE-levelling" still reads correctly after the first paragraph.

Why split across two paragraphs instead of one: the first paragraph is the contract, the
last sits directly above the `offered` code it describes. Moving all the #590 detail up
would put it ten lines away from the code; leaving the first paragraph silent would keep
the contradiction. A forward pointer ("described with the `offered` call below") keeps
the block one consistent statement.

## Checks run

- `git diff -w -U0 | grep '^[+-] ' | grep -v '^[+-]\s*#'` → empty: no non-comment line
  changed. `git diff --stat` → only `flow.py`.
- Offline suite (T3): `cd template && PYTHONPATH=src python3 -m unittest discover -s tests`
  (run under `timeout 900`) → `Ran 2423 tests ... OK (skipped=2)`.
- Formatter / commit hooks: the target repo configures none (no `.pre-commit-config.yaml`,
  no line-length setting in `template/pyproject.toml.jinja`). New lines are ≤ 91 chars,
  within the width the surrounding block already uses (up to 92).

## Refute-your-own-test (a/b/c)

No test is shipped, per the brief (Test file: none; Falsifiability). A comment cannot be
tested; C4 is expected to report `PDCA-UNVERIFIABLE` (exit 77) and route this to §6 for a
human read. I did not add a token test or a code change to fake a red leg.
- (a) Genuine red? No — not applicable; there is no test to revert against.
- (b) Production path? Not applicable; the change is a comment in the production file.
- (c) Fixture includes the fault? Not applicable.
Human check at sign-off: read `flow.py:2141-2166` on the patched tree against
`waves.py:74-80` and `:95-96`.

## Other stale wording found (not fixed — out of scope)

Grepped `template/src` for "exactly as before" / "never relaxes". The other hits
(`gates.py:348`, `gates.py:576`, `lane.py:11`, `progress.py:194`, `config.py:334`,
`flow.py:2414`) are about unrelated features (lanes, gates, progress output, clamp) and
none mentions strict levelling or adoption. No other stale strict-levelling comment found.
