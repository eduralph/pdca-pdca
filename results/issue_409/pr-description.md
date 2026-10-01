## Summary
**User impact:** with `--auto-iterate` on, a bundle that Check found broken often got no
automatic rebuild at all. If Check raised even one question for a person next to fixable
implementation work, the run stopped and waited for the human. The rebuild fired on only
13.5% of the attempts that were checked for it, and two bundles reported as broken got
zero rounds.

This PR lets the rebuild go ahead and holds the human questions until handover. Every one
still has to be cleared by the human before an accept. No new setting is added. The loop
still stops on the existing hard cap (`max_auto_iters`) or the size backstop.

Reported in [#409](https://github.com/eduralph/pdca-harness/issues/409). Also fixes #335
(an unticked finding could be dropped because a similar one was ticked).

## What to look at
- **The rule change:** a human finding beside implementation work is deferred, not a
  reason to stop. The only human finding that still stops the loop is the size backstop's
  ("this change is too big to keep rebuilding").
- **The deferral file:** `deferred-findings.json` in the bundle. It survives a rebuild,
  its entries come back as open rows in the NEEDS-HUMAN section of `SUMMARY.md`, and an
  entry leaves only when the human ticks its row.
- **Accept safety:** the accept guard now reads the NEEDS-HUMAN section that assembly
  wrote, not a copy quoted earlier in the summary by a review.
- **Docs:** the two stop rules are described once, in `docs/07-crosscutting.md` (the
  auto-iterate section). `docs/05-check.md` and `template/pdca.toml.jinja` point there.

To try it: run a bundle with `auto_iterate = true` whose Check returns one `[impl]` finding
plus one ordinary human finding. Before this PR it halts at once. After it, the rebuild
fires, and the human finding shows up as an open row at handover. The flow tests in
`TwoStops` and `DefersHumanFindings` drive exactly this.

## Root cause
`autoiterate.eligible()` required every non-implementation item to be a standing row, so
any human finding vetoed the rebuild. The veto, not the round limits, was what stopped the
loop; the hard cap and the size backstop rarely got the chance to.

## Fix
- `autoiterate.eligible()` is true when there is at least one implementation item and no
  size-backstop item. The size item is matched by kind (`size_signal.is_size_item` on a
  human item), so the same text tagged `[impl]` still rebuilds.
- `write_decision` records the deferrable findings (human, not a no-verdict row,
  deduplicated) in `deferred-findings.json` before it spends the round. The file is
  cycle evidence: it is not archived by an iterate.
- `assemble_summary` merges the file's entries into NEEDS-HUMAN, deduplicated against the
  fresh findings. An unreadable file becomes a NEEDS-HUMAN row that blocks accept on the
  shared decision path and on `pdca signoff --accept`.
- `driver` retires ticked entries just before an iterate archives `SUMMARY.md`
  (`retire_cleared`). Protection is exact-first: an open row equal to a rendered row is
  that row and protects only its own entry (nothing, if it is a fresh finding); an open row
  that matches no rendered row is an edit and protects every entry it could be an edit of.
  More than one fuzzy hit for a tick retires nothing. This closes #335, where the flat
  fuzzy rule left a pair of near-identical findings that could never be cleared.
- Rows from a review or gate that gave no verdict (missing review, placeholder review or
  advisory, gate that could not run) are marked `no_verdict` and not deferred. The next
  Check runs them again, so once they recover nobody has to clear them by hand.
- Every NEEDS-HUMAN reader in `signoff.py` uses one helper that takes the **last**
  `## 6. NEEDS-HUMAN` heading. The row writer splices by position, so a quote that is
  byte-identical to the real section cannot catch the row.
- The two placeholder sentences moved from `leaves.py` into `assemble.py`, so the writer
  and the recogniser share one definition. Output is byte-for-byte unchanged.

Not in this PR: #332 item 1 (a separate soft round budget) was dropped at design time. The
size backstop already stops the loop below the hard cap by default (2 rounds vs. 3), so a
third limit would never bind on a default install.

## Verification
- **Claim:** two stops, no new budget. A `[impl, human]` Check fires until
  `count == max_auto_iters` when the size backstop is off, and stops at 2 rounds on the
  size item by default.
  - **Checked:** `template/src/pdca_harness/autoiterate.py:198-224` (`eligible`);
    `template/src/pdca_harness/flow.py:302-388` (`_maybe_auto_iterate`).
  - **Test:** `TwoStops` (`template/tests/test_autoiterate.py:1052`):
    `test_there_is_no_soft_budget_key`, `test_mixed_checks_fire_until_the_hard_cap`
    (`:1087`), `test_mixed_checks_stop_at_the_size_backstop_first_by_default` (`:1101`).
- **Claim:** human findings defer and return at handover; an empty NEEDS-HUMAN still
  never auto-accepts; an unreadable file blocks accept on both paths.
  - **Checked:** `autoiterate.py:300-346` (`deferrable`, `defer`), `:454` (`write_decision`);
    `template/src/pdca_harness/state.py:174` (`CYCLE_EVIDENCE_ONLY`);
    `template/src/pdca_harness/flow.py:214-248` (`accept_blockers`).
  - **Test:** `DefersHumanFindings` (`test_autoiterate.py:669`), including
    `test_an_unreadable_ledger_blocks_accept_on_the_shared_decision_path` (`:886`) and
    `..._on_the_cli_path_too` (`:914`); `test_empty_section6_halts_and_never_auto_accepts`
    (`:438`) passes unchanged.
- **Claim:** only a positive tick retires an entry (#335).
  - **Checked:** `autoiterate.py:165` (`_same_finding`), `:348-430` (`retire_cleared`);
    `template/src/pdca_harness/driver.py:135`, `:141`, `:317` (retire before the archive,
    both iterate branches); `template/src/pdca_harness/signoff.py:146`
    (`cleared_needs_human`).
  - **Test:** `RetiresOnlyWhatTheHumanTicked` (`test_autoiterate.py:1126`):
    `test_335_an_annotated_open_row_survives_a_similar_ticked_new_finding` (`:1179`),
    `test_an_edited_open_row_matching_two_near_twins_protects_both` (`:1223`),
    `test_a_fresh_near_twin_left_open_shields_nothing` (`:1296`); `RetireAtTheIterate`
    (`:1486`).
- **Claim:** the size backstop stops by kind, not by "any human item".
  - **Test:** `test_the_size_item_stops_by_kind_not_every_human_item`
    (`test_autoiterate.py:1586`) checks `[impl, human] → True` and
    `[impl, human, size] → False` together. `test_the_tag_is_the_mechanism`
    (`template/tests/test_size_signal.py`) passes in both directions.
- **Claim:** the accept guard reads the real NEEDS-HUMAN section.
  - **Checked:** `signoff.py:103` (`_needs_human_section`), `:122` (`open_needs_human`),
    `:169` (`ensure_needs_human_item`).
  - **Test:** `C6ReadsTheAssembledSection6` (`test_autoiterate.py:957`): a quoted block of
    ticked rows fails to pass an accept on the flow and CLI paths; the unreadable-file row
    lands in the real section exactly once.
- **Claim:** a review or gate that recovers needs no hand clearing.
  - **Checked:** `template/src/pdca_harness/assemble.py:53` (`no_verdict`), `:307-376`
    (`collect_needs_human`), `:485` (`_deferred_needs_human`).
  - **Test:** `test_a_review_or_gate_that_recovered_needs_no_clearing_at_handover`
    (`test_autoiterate.py:707`), end to end through a real rebuild round.
- **Red/green:** with the production changes reverted to `main` (940565897e0df93e11c20c0d7ea76ac5ffa803ca),
  `test_autoiterate` has 30 failures and 41 errors; with the patch, `test_autoiterate`
  (101) and `test_size_signal` (56) pass. Nine single-point mutations of the new code
  were each caught by at least one test. The full suite (2135 driver tests, 24 root) and
  the docs check pass.

## Known follow-ups (out of scope here)
- `signoff.record` / `outcome_token` still read the first `## 9.` heading, so a quoted
  sign-off block could still be misread. Same family as the NEEDS-HUMAN fix above.
- `pdca signoff --delta` is written raw into the sign-off section; a pasted
  NEEDS-HUMAN block there would become the "last" one. It should be flattened as
  `flow.py` already does.
- The decorrelation note `leaves.py` writes each Check is deferred like an ordinary
  finding; it could be treated as a no-verdict row.

Closes #335
Fixes #409
