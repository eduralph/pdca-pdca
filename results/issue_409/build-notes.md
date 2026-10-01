# Build notes — issue 409, attempt 5

Target: `eduralph/pdca-harness @ main` (base `9405658`, which is `origin/main`). Worktree:
`/home/eddie/pdca/pdca-harness.pdca-wt`. Every `path:line` below is on the patched worktree.

## What this attempt is

Attempt 4's patch (`iteration-v4/patch.diff`) applied unchanged, plus the three items in the
iteration-4 carry-forward and the optional cosmetic one. The design is otherwise as it was.
`patch.diff` is the whole change against `main` (15 files, +1940 / −217).

## Item 1 — C6 read the first §6 heading, which a leaf can quote

Cause: every §6 reader went through `signoff._section`, which takes the FIRST matching
heading. Assembly pastes review and advisory text into §5 verbatim, above the §6 it writes.
So a leaf that quoted a block of ticked §6 rows made `open_needs_human` return `[]`, and an
accept went through over the real §6's open rows. The unreadable-ledger row writer read the
same first heading, so it wrote its row into the quote.

Fix, in `template/src/pdca_harness/signoff.py`:
- One helper, `_needs_human_section` (`signoff.py:103`), takes the LAST `## 6. NEEDS-HUMAN`
  heading. Its docstring gives the reason the last heading is the assembled one.
- Every §6 reader uses it: `open_needs_human` (`:122`, the C6 read), `cleared_needs_human`
  (`:146`), and `unrecordable`'s §6 check (`:241`). `open_needs_human` loses its `last`
  keyword; there is only one way to read §6 now. `autoiterate.retire_cleared` calls it
  plainly (`autoiterate.py:409`).
- `ensure_needs_human_item` (`:169`) finds the last heading by line index (`_section_span`,
  `:352`, split out of `_section`, `:318`) and splices the row in by position (`:205`).
  Dedup now sees the copy assembly already wrote in the real §6, so no second row.
- `flow.accept_blockers` (`flow.py:214`) is unchanged in code. Both accept paths already go
  through it (`flow.py:176`, `cli.py:1450`), so both now read the real §6. Its docstring says
  why the writer and the reader must use the same §6.

Why splice by position: I found a case the carry-forward did not name. If a leaf quotes an
empty §6 at the end of its artifact, the quoted section is byte-for-byte the real one. The old
`text.replace(section, new, 1)` then writes into the first match, which is the quote, and C6
(reading the last heading) never sees the row. That is fail-open. Mutation M3 below shows the
test catches it.

Side effect, on purpose: `pdca run`, `pdca status`, `pdca queue` and the flow's report also
call `open_needs_human`, so they now count the real §6 too. Before, the queue could say
`[cheap: confirm]` for a bundle whose accept C6 refuses. Rejected: keeping `last` as an opt-in
and passing it only from `accept_blockers`. Same line count, but the displays would then
disagree with C6.

Docs: one sentence in the C6 section, `docs/05-check.md:753`.

## Item 2 — a fresh near-twin left open shielded an exactly-ticked ledger entry

Cause: protection matched an open row exactly against ledger entries only. An open row equal
to a FRESH rendered row fell through to the fuzzy tier and protected every entry it matched.

Fix (`autoiterate.py:412-416`): the exact tier runs over every rendered row (`rnorm`), as
the tick rule already did. An open row equal to a rendered row is that row. It protects its
entry if the row is a ledger entry, and nothing if it is a fresh finding. Only an open row
equal to no rendered row (an edit) protects every entry it fuzzy-matches. That keeps the
fail-closed tier for edited rows. Docstring: `autoiterate.py:377-388`. Docs:
`docs/07-crosscutting.md:472-474`.

## Item 3 — the ruling on review/gate rows that gave no verdict

Ruling: once a later round's review or gates recover, a stale missing-review or
gate-could-not-run row must not need clearing by hand at handover. Ordinary findings still
defer and still need a tick.

What I built: such rows are marked at the source and never written to the ledger.
- `NeedsHumanItem` gains `no_verdict: bool = False` (`assemble.py:53`), with the reason in a
  comment above it.
- `collect_needs_human` marks: the missing-review placeholder when `check-review.md` is
  absent (`assemble.py:325`); a gate that could not run (`:335`); and the harness's own
  placeholder row in a placeholder review or advisory artifact (`:322`, `:330`, applied in
  `_items_from_artifact`, `:303`).
- The placeholder row is recognised by its exact text. I moved the two placeholder sentences
  into `assemble` (`REVIEW_UNAVAILABLE_FINDING`, `ADVISORY_UNAVAILABLE_FINDING`,
  `assemble.py:175-185`), and `leaves` now writes them from there (`leaves.py:3416`,
  `:3767`). The output is byte-for-byte what `leaves` wrote before; the full suite passes
  unchanged. This touches `leaves.py`, which is not in the brief's file list. I did it so the
  writer and the recogniser share one definition instead of a copied string.
- `autoiterate.deferrable` (`autoiterate.py:300`) is now the one definition of "what a round
  holds": HUMAN, not `no_verdict`, deduplicated. `defer` records it (`:329`), and
  `rationale` (`:446`) and the flow's notice (`flow.py:377`) count it. Writing the test
  showed the old count was wrong: it counted a re-worded duplicate twice while the ledger
  held it once. The flow's notice also says how many no-verdict rows were left for the next
  Check (`flow.py:381`).

Why exact text for placeholders, not "every row of a placeholder artifact": an artifact can
read as a placeholder and still carry real findings, namely a report that quoted a status
marker and never wrote the completion trailer (`assemble.leaf_status`). Marking all its rows
would drop real findings nobody ticked. The marking test pins this (mutation M8).

Why gate rows are marked at the source, not recognised later by text: the gate row has the
shape `<gate label> unverifiable — <evidence>`. Unconfigured gate rows use the canonical
labels (`C5 Causal adequacy`, `T5 Judgment`, …), so a reviewer finding such as
`C5 Causal adequacy unverifiable — no test drives the prod path` has the same shape. Text
recognition would drop it.

Scope: I included advisory-leaf placeholders. The ruling names "missing-review placeholder,
gate-could-not-run", but its rule is "stale/recovered infrastructure findings", and an
advisory leaf is re-run by every Check like the reviewer. Plan-advisory placeholders are not
marked: they are not Check artifacts and are not re-run per round. Leaf placeholders of every
status are marked, the substantive (`human-empty`) one included: a later usable verdict
supersedes an earlier missing one whatever caused it. A HUMAN-element gate that RAN and
failed is not marked, because it is a verdict. If the human wants a narrower or wider set,
it is one line each in `collect_needs_human`.

### The design choice: never written, instead of written and dropped later

The ruling says "drop that infra entry from the ledger instead of re-entering it in §6".
Taken literally, that means writing the row to the ledger and removing it once the fresh
finding is gone. I did not do that, because the copy in the ledger could never reach §6:
- While the problem lasts, the current Check raises the row itself, and assembly renders it
  once, as the fresh row.
- Once it has recovered, the rule drops it.

So the visible result (§6, C6, `accept_blockers`) is the same either way. The cost of the
literal version, counted against this patch:
- The ledger needs a second key saying which entries are no-verdict rows: read, validate and
  write in `deferred` / `_write_ledger` / `defer`, about 25 lines.
- Text recognition instead of a key is unsafe for gate rows (see above).
- A drop step at assembly or at the iterate, about 10 lines.
- Assembly and `retire_cleared` must both leave recovered entries out of the rendered rows,
  about 8 lines.
- Tests for the new key, about 30 lines.

The one difference that remains: a ledger seeded BY HAND with a missing-review row would
still render and need a tick. No product path writes one. Brief clause 2 says HUMAN items
beside IMPL items are written to the ledger. The ruling carves these rows out of that, and
the code and docs say so (`autoiterate.py:23-26`, `assemble.py:47-52`,
`docs/07-crosscutting.md:458-464`, `template/pdca.toml.jinja:66-68`, `README.md:166`). If
the human reads the ruling as requiring the rows in the ledger file, that is the reviewer's
or the human's call to flag.

## Cosmetic item

`assemble._deferred_needs_human` uses `autoiterate._norm` instead of an inline copy
(`assemble.py:505`).

## Tests (`template/tests/test_autoiterate.py`, copied into the bundle)

New:
- `C6ReadsTheAssembledSection6` (`:957`):
  - `test_a_quoted_block_of_ticked_rows_does_not_pass_an_accept` (`:986`) — the flow path,
    with a control that the real tick does accept;
  - `test_a_quoted_block_of_ticked_rows_does_not_pass_a_cli_accept` (`:1006`) — `pdca
    signoff --accept`;
  - `test_the_unreadable_ledger_row_lands_in_the_real_section6_once` (`:1020`) — three
    cases: broken before assembly (no duplicate), broken after (row in the real §6), and a
    quote identical to the real §6.
- `test_a_fresh_near_twin_left_open_shields_nothing` (`:1296`) — the carry-forward's pair,
  plus two controls: the same row edited still protects, and the same text not rendered
  by this Check is an edit and protects.
- `test_a_review_or_gate_that_recovered_needs_no_clearing_at_handover` (`:707`) — the test
  the ruling asked for, end to end through `flow._maybe_auto_iterate` → rebuild → Check →
  assembly. Four cases: review missing, review placeholder, advisory placeholder, gate could
  not run. In each, round 2's review, advisory and gates are clean. The row is gone from §6
  and `accept_blockers`, and the ordinary finding is still in the ledger, §6 and the
  blockers. It replaces `test_a_missing_review_beside_a_red_gate_is_deferred`, which
  pinned the overruled behaviour.
- `test_only_a_review_or_gate_with_no_verdict_is_left_to_the_next_check` (`:768`) — which
  rows are marked, including the misread-placeholder case.

Extended: `test_write_decision_defers_the_human_items_before_spending_the_round`
(`:1604`) — a no-verdict item is not written, and the rationale count is the ledger's.
Helpers: `_section6` now reads the last heading (`:95`); `_quoted_section6` reads the first
(`:101`).

Counts: `test_autoiterate` 101 tests, `test_size_signal` 56 (unchanged this round).

## Refuting my own tests

**(a) Genuine red?** Yes.
- C4 gate, the project's runner (`./engine/scripts/run-verify.sh` with
  `PDCA_BUNDLE`/`PDCA_WORKTREE`, under `timeout 900`), on the final patch: "PDCA-EVIDENCE:
  C4 PASS". Green leg 101 + 56 OK. Red leg (production reverted to `main`): 30 failures and
  41 errors in `test_autoiterate`, no load failure. `test_size_signal` is green on both
  legs, which the brief expects for fixture adaptations.
- Against attempt 4's production code (the actual defects), with my test file:
  - both C6 tests fail on behaviour (`[] != ['- [ ] the retry path is still unguarded']`;
    CLI exit `0 != 1`);
  - the ledger-row test fails in all three cases (row count 2; row missing from the real
    §6, twice);
  - the near-twin test fails (entry kept);
  - the recovery test fails in all four cases: the recovered row is back in round 2's §6.
  - The marking test errors there (no `no_verdict` field), as a new field must.
- Mutations of my own code, one at a time, both modules run each time:

| Mutation | Result |
|---|---|
| M1 C6 reads the first §6 heading | 6 fail: both accept tests, all 3 row cases, the quoted-§6 retirement test |
| M2 row writer uses the first heading | 3 fail: all row cases |
| M3 row placed by text match, not position | 1 fails: the identical-quote case |
| M4 protection as in attempt 4 | 1 fails: the near-twin test |
| M5 `deferrable` keeps no-verdict rows | 5 fail: 4 recovery cases + the write_decision test |
| M6 missing review not marked | 2 fail |
| M7 gate that could not run not marked | 2 fail |
| M8 every row of a placeholder-looking artifact marked | 1 fails: the marking test |
| M9 no placeholder row marked | 3 fail: 2 recovery cases + the marking test |

  Each file was restored from a git blob after its mutation, and I checked the hashes. The
  worktree matches `patch.diff` byte for byte.

**(b) Production path?** Yes. The tests call `flow._apply_decision`, `flow.accept_blockers`,
`cli._signoff`, `flow._maybe_auto_iterate` (which runs `driver.run_issue` → archive → stub
build → gates → review → `assemble.assemble_summary`), `assemble.collect_needs_human`,
`autoiterate.retire_cleared`, `autoiterate.write_decision` and `autoiterate.rationale`. No
copies. The review and advisory leaves are replaced in round 2 only by functions that write
a clean artifact, since a real leaf needs a model. The placeholders come from the real
writers, `leaves._review_unavailable` and `leaves._advisory_unavailable`.

**(c) Fixture includes the fault?** Yes.
- The quoted §6 is an advisory artifact that production assembly pastes into §5.
  Preconditions assert the first §6 heading has only ticked rows and the real one has the
  open row. For the identical-quote case, they assert the two sections are byte-equal.
- The fresh near-twin is passed as `fresh`, and a precondition asserts the matcher cannot
  tell the pair apart.
- In the recovery test, round 1's §6 really shows the no-verdict row (precondition), the
  round really fires and archives `iteration-v1/`, and round 2's gates really pass.

## Gates and commit-readiness

- T2 `./engine/scripts/run-docs-check.sh`: docs lint clean, 22-page render and link audit
  clean.
- T3 `./engine/scripts/run-suite.sh`: root suite 24 OK, driver suite 2135 OK (2 skipped).
- The target has no formatter, linter or pre-commit hook: no ruff/black/flake config, no
  `.pre-commit-config.yaml`, only sample git hooks. CI runs the render/update tests and the
  docs checks (both green above) plus the linked-issue check (publish's job). Every changed
  `.py` parses with warnings as errors, and `git diff --check` is clean. New lines stay
  within 100 columns, except the `--auto-iterate` help string, which follows `cli.py`'s
  existing long argparse lines. The publish commit needs a DCO `Signed-off-by`
  (`CONTRIBUTING.md`).

## Seen, out of scope — worth follow-up issues

- `signoff.record` and `outcome_token` still read the FIRST `## 9. Check sign-off` heading.
  A leaf quoting a §9 block in §5 can still make `state` read an outcome from the quote. This
  is the round-4 note; round 1 put the shared heading reader out of scope.
- `act._sections` / `act._find` (`act.py:810`, `:825`) read §6 for `pdca act index`. With
  a quoted heading worded differently from the real one, `_find` returns the quote first.
  Act tooling only; C6 is not affected.
- The cause-level fix for all three: neutralise `## ` lines in the leaf text assembly pastes
  into §5 (`assemble.py`, the review text and advisory block). About 6 lines plus tests. It
  changes the §5 text the human reads, so it is the human's call.
- Patch size is 170 KB (attempt 4: 138 KB). The human weighed the size backstop and ruled
  "do not split".

## Housekeeping

I wrote no files outside the worktree and this bundle. The docs gate script makes its own
`mktemp` render directory under `/tmp`; that is the project's script. I kept the mutation
restore points as git blobs (`git hash-object -w`), not files. No commits, pushes or PRs.
