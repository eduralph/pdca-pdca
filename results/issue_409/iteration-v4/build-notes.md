# Build notes — issue 409, attempt 4

Target: `eduralph/pdca-harness @ main` (base `9405658`). Worktree:
`/home/eddie/pdca/pdca-harness.pdca-wt`. All `path:line` below are on the patched worktree
unless marked "main".

## What this attempt is

Attempt 3's patch (`iteration-v3/patch.diff`) applied unchanged, plus fixes for the three
retirement defects in the iteration-3 carry-forward. The design is as it was; nothing
outside the retirement path changed. `patch.diff` is the whole change against `main`.

## Defect 1 — a §6 block a leaf quoted could retire a deferred finding

Cause: `signoff._section` takes the FIRST matching heading (main `signoff.py:231`, the
`break` at `:258`). Assembly pastes review and advisory text into §5 verbatim, above
the §6 it writes (`assemble.py:413-419`). So a leaf that quotes a `## 6. NEEDS-HUMAN`
block with a row ticked put that tick where the tick reader looked first.

Fix:
- `signoff._section` gains an opt-in `last=False` keyword (`signoff.py:300-301`,
  `:323-325`, `:332`). With `last`, the last matching heading wins. Every existing caller
  keeps the first heading, so C6 and §9 reads do not change.
- `cleared_needs_human` (the tick reader) reads the last §6 heading
  (`signoff.py:128-150`). Its docstring gives the reason: nothing after the assembled §6
  is a leaf's multi-line text. §6 rows are one line each, and §9's iteration delta is
  flattened to one line on the flow path (`flow.py:182`).
- `open_needs_human` gains the same opt-in `last` (`signoff.py:102`, `:120`), and
  `retire_cleared` reads open rows with it (`autoiterate.py:382-383`).

Why the open-row side changed too: switching only the tick side opens a new hole. Ticks
would come from the real §6, but the rows that protect entries would still come from the
quoted block. An edited open row in the real §6 would then protect nothing, which brings
#335 back. Mutation M1b below shows this: ticks last, open rows first, fails
`test_a_section6_quoted_by_a_leaf_is_not_the_humans`.

Not done: the carry-forward's second option, "skip retirement when §9 was written by
auto-iterate". It adds nothing once the reader takes the last heading. An auto round's
ticks then come from the §6 assembly just wrote, where every row is `- [ ]`. On its own it
would also leave the human path open: `test_a_quoted_tick_is_not_the_humans_on_a_human_iterate_either`
is a human iterate-do, which a skip-on-auto rule never covers. Cost if added: a §9
`By / date` reader (about 12 lines plus a test). A human can spoof it with
`--by auto-iterate`. It would also throw away ticks a human made before re-running
`flow` with auto-iterate on.

Rejected: reading open rows from the union of every §6 section (mutation M1c). It is the
same size, but a leaf could then make a deferred finding unclearable by quoting its row
open. The control in `test_a_section6_quoted_by_a_leaf_is_not_the_humans`
(`test_autoiterate.py:1101`) pins that the human's own tick still retires the entry.

## Defect 2 — a tick on a fresh finding retired a different, deferred finding

The carry-forward's rule is implemented as stated. A ticked row equal to a row assembly
rendered from a FRESH finding clears that finding, never a ledger entry. Only rows the
human edited are matched fuzzily.

- `retire_cleared(d, summary_path, *, fresh)` (`autoiterate.py:322`). `fresh` is this
  Check's own findings. The function builds `rendered` = ledger entries first, then each
  fresh row that is not already an entry, deduplicated on normalised text
  (`autoiterate.py:376-381`). This mirrors assembly, which renders a re-raised deferred
  finding once, as the entry (`assemble.py:446-470`).
- The tick rule (`autoiterate.py:392-397`): exact match over every rendered row first,
  else `_same_finding` over every rendered row. A tick retires only when it hits exactly
  one row, that row is a ledger entry, and nothing protects it.
- The driver supplies `fresh` from `assemble.collect_needs_human(d, cfg)`, the single
  source assembly rendered §6 from. It runs at the iterate transition, while the Check
  artifacts are still in place (`driver.py:317-340`, both call sites `:135`, `:141`). It
  skips all of this when the ledger is empty (`:332`). An unreadable ledger is left alone,
  as before (`:336`).
- The comment above `_MATCH_RATIO` now says why thresholds cannot settle this
  (`autoiterate.py:107-111`).

One step past the carry-forward's literal rule: fresh rows are fuzzy CANDIDATES too, not
only exact ones. Without that (mutation M2b), a human who annotates the fresh CLI-path row
before ticking it ("…the CLI path (fixed in round 2)") retires the deferred retry-path
entry whose row they deleted. That is the same fail-open, one edit away. The cost runs in
the safe direction. If the human annotates and ticks the ENTRY's own row while a fresh
near-twin exists, the edit matches both rows, so the entry stays one more round and comes
back unticked. The test pins this deliberately (`test_autoiterate.py:1093-1099`), and the
docs say so (`docs/07-crosscutting.md:458-467`).

Protection (the #335 tiers) is unchanged. A fresh open row that fuzzy-matches an entry
still protects it (round 1's item 4, "fresh near-twin fails closed — acceptable"). Now
that `fresh` reaches `retire_cleared`, item 4 could be fixed in about 2 lines (tier 1
would treat an open row equal to a fresh row as owning it). Not done: the human ruled it
out of scope.

Rejected: recording the rendered rows at assembly instead of re-deriving them at the
iterate. Cost: a new per-attempt bundle file written by `assemble_summary`, classified in
`state.DOWNSTREAM_OF_BRIEF`, and read by retirement. That is about 25 lines across three
modules plus a state-classification test, against 1 line in the driver.

Residual risk of re-deriving: if `pdca.toml`'s doctor rows change between assembly and
the iterate, an unregistered-dependency row can drop out of `fresh`. A tick on it would
then read as an edit. It could retire only a ledger entry it fuzzy-matches whose own row
the human deleted.

## Defect 3 — a separator-only edit of a short finding did not match itself

`_same_finding` now returns True when the texts are equal past the labels both rows share,
before the floor check (`autoiterate.py:180-181`), as the carry-forward specified. This is
equality, not a looser floor. `"C1 Spec: vague wording"` still does not match
`"C1 Spec — vague"` (`test_autoiterate.py:1162-1165`).

## Tests (in `template/tests/test_autoiterate.py`, copied into the bundle)

New:
- `test_a_tick_on_a_fresh_finding_never_retires_a_deferred_one` (`:1052`) covers the
  adversary's three pairs verbatim, the annotated fresh tick, a finding raised again, and
  the pinned cost.
- `test_a_section6_quoted_by_a_leaf_is_not_the_humans` (`:1101`) covers a quoted tick,
  protection read from the real §6, and a quoted open row that does not block.
- `test_a_quoted_tick_retires_nothing_on_an_auto_iterate_round` (`:1304`) is the test the
  carry-forward asked for. It runs end to end through `flow._maybe_auto_iterate` →
  `_apply_decision` → `driver.run_issue` → `advance`.
- `test_a_quoted_tick_is_not_the_humans_on_a_human_iterate_either` (`:1320`).
- `test_a_tick_on_a_fresh_finding_leaves_a_deferred_one_at_the_iterate` (`:1326`) proves
  the driver passes the real fresh rows.

Extended:
- `test_a_short_row_matches_only_exactly` gains the separator cases (`:1153-1165`).
- The `_retire` helper (`:960-975`) now takes `fresh=` and asserts the ledger file is not
  rewritten when nothing retires.

Counts: `test_autoiterate` 96 tests, `test_size_signal` 56.

## Refuting my own tests

**(a) Genuine red?** Yes.
- C4 gate (`./engine/scripts/run-verify.sh`, run with `PDCA_BUNDLE`/`PDCA_WORKTREE`):
  "PDCA-EVIDENCE: C4 PASS". Green leg 96 + 56 OK. Red leg (production reverted to
  `main`): 25 failures and 36 errors in `test_autoiterate`, and no load failure.
  `test_size_signal` is green on both legs, which the brief expects.
- Against attempt 3's production code (the actual defect): the three end-to-end tests fail
  on behaviour. The unit tests error there only because the old signature has no `fresh=`.
- So I also reverted each fix alone in my own code and re-ran both modules:

| Mutation | Result |
|---|---|
| M1 both readers first (attempt 3) | 3 tests fail |
| M1b ticks last, open rows first | `test_a_section6_quoted…` fails |
| M1c open rows from every §6 section | `test_a_section6_quoted…` fails |
| M1d ticks first, open rows last | 2 fail |
| M2 `fresh` ignored | both fresh-row tests fail |
| M2b fuzzy over ledger entries only | the fresh unit test fails |
| M2c driver passes `fresh=()` | the fresh end-to-end test fails |
| M3 no equality past the label | `test_a_short_row_matches_only_exactly` fails |
| M4 no "only an entry retires" guard | caught by the no-rewrite check |
| M7 fresh copies of entries kept | the "raised again" subtests fail |

- One mutation survives, and it cannot be caught. M5 does the exact match over ledger
  entries only instead of all rendered rows. It behaves identically: the fuzzy step
  includes fresh rows, and `_same_finding(x, x)` is True, so a tick equal to a fresh row
  always hits that row either way. I kept the explicit form because it states the rule.

**(b) Production path?** Yes. The tests call `autoiterate.retire_cleared`,
`autoiterate._same_finding`, `assemble.assemble_summary`, `driver.advance`, and
`flow._maybe_auto_iterate`, which reaches `driver._retire_cleared_deferrals` and
`assemble.collect_needs_human`. No copy or stand-in. The new end-to-end tests use the
config's stub builder and reviewer (the product's own offline mode) and mock nothing.

**(c) Fixture includes the fault?** Yes.
- The quoted §6 block sits in a `check-advisory-adversary.md` that production assembly
  pastes into §5, which is the real fault path. A precondition asserts the quoted
  `- [x]` is in the SUMMARY.
- The fresh finding is raised by an advisory artifact and rendered by production assembly.
- The deferred entry's own row is deleted from the real §6, which is the adversary's
  precondition.

## Gates and commit-readiness

- `./engine/scripts/run-docs-check.sh`: docs lint and site render with link audit both
  clean.
- `./engine/scripts/run-suite.sh`: root suite 24 OK, driver suite 2130 OK (2 skipped).
- The target has no code formatter or pre-commit hook: no ruff/black config, and no hooks
  in `.git/hooks`. Its CI runs the docs lint and render, the render/update tests, and the
  linked-issue check. The publish commit needs a DCO `Signed-off-by` (CONTRIBUTING.md).

## Observed, out of scope — worth a follow-up issue

The first-heading rule defect 1 exploited is also in the two readers this slice must not
touch. I checked this in memory against the patched `signoff` (unchanged behaviour from
`main`):
- **C6:** a §5 quote of a `## 6. NEEDS-HUMAN` block with no open rows makes
  `open_needs_human` return `[]` while the real §6 has open rows. An accept would pass.
- **§9:** a §5 quote of `## 9. Check sign-off` plus `- Outcome: merged-wider` is what
  `outcome_token` reads, so `state.state` (main `state.py:367-373`) would report COMPLETE
  with no sign-off.

The human scoped the shared heading reader out in round 1 (item 3), so I did not change
either. The cause-level fix is to defuse `## ` lines in the leaf text assembly pastes into
§5 (review text and advisory block, `assemble.py:416-417`). That is about 6 lines plus
tests, and it changes the §5 text the human sees. The `last` keyword added here is the
narrower alternative for those readers.

## Housekeeping

I wrote one file outside the harness roots by mistake: `/tmp/c4-409.log`, the output of
my C4 run. I did not remove it (cleanup belongs to the harness). Scratch versions for the
mutation runs were kept as git blobs (`git hash-object -w`), not files. The worktree was
restored and matches `patch.diff` byte for byte.
