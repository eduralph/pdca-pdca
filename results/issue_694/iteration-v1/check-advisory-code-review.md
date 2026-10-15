# Advisory code review — issue 694 (reissue-after-conflict-hold-names-the-partner)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. All lines are on `$PDCA_TARGET` with the patch applied.

## Correctness

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/integrate.py:594-595`: `_clash` gets `list(took.items())` as its partner candidates. `took` only holds the ids this pass has already reached (`integrate.py:558`, filled at `:603`). So a batch id that is already on origin's line from the earlier run, but comes *later* in the carry's order, is never tried as a partner. The carry goes in the order asked for (`flow.py:963-973`, `:1114`), while the line name ignores order (`integrate.py:131-132`). Re-issuing the same ids as `11 10 …` instead of `10 11 …` continues the same line, which already holds `issue_10`. `issue_11` is tried first with `took` empty, so it falls to the `"line"` kind ("work already on the line that no bundle of this batch accounts for") and `issue_10` is not named. The brief's Scope says partners include ids "already on origin's line from the earlier run", and the `_clash` docstring (`integrate.py:1136`, "or found there already") claims this too. Suggested fix: also offer every other id of `bundles` whose head is already an ancestor of `start_ref` (`_in_line(wt, read[n], …, of=start_ref)`), or work out clashes after the pass ends. Add a test that re-issues in reversed order.
- NEEDS-HUMAN [impl] — `template/tests/test_flow_reissue_after_conflict_hold.py:421-446`: criterion (2)'s test passes without the fix. The C4 red leg shows `.F` (`gate-logs/C4-verify.log`): only test (1) fails there. The old "cross-wave overlap … get issue_11's PR open" line already names no other id and has no `Conflicts with`. So nothing checks that the new `"base"` branch (`integrate.py:1144-1146`, `flow.py:1031-1033`, hint `base_conflict` at `flow.py:1012-1013`) is taken. Assert something only the fix prints, e.g. `conflicts with origin/main itself` or `rebuild issue_11 on the current origin/main`, and `assertNotIn("cross-wave", said)`.
- `template/src/pdca_harness/integrate.py:594-597` with `:615-622`: a clash is recorded during one pass, but the next pass can take a named partner off the line, because `_hold_work` drops ids that hold a skipped id's work. The message would then say the partner is "finished in this batch and on the line" (`flow.py:1028-1030`) when it is no longer on the pushed line. This is a rare edge case and the advice is still roughly right. You could re-check partners against the final `took` before reporting.
- `template/tests/test_flow_reissue_after_conflict_hold.py:439-440`: `_not_carried("11")` is called twice. Harmless, but the first call can just be assigned to `said`.

## Reuse / simplification

- `template/src/pdca_harness/flow.py:1196-1198` (`ids=`) repeats the `", ".join(p.removeprefix("issue_") …)` from `_report_conflict_holds` (`flow.py:1246`), and the `conflict` hint (`flow.py:1010-1011`) copies its wording by hand. If either one changes, the "same advice whichever step reports it" rule from the brief breaks without anyone noticing. A small shared formatter for the `Conflicts with` proposal would keep them the same.
- `template/src/pdca_harness/integrate.py:1148-1151`: the one-trial-per-partner loop is the same pattern as `_held_by`'s partner loop (`integrate.py:1124`), just on a different base. That's fine as it is. Noting it in case a later change wants one helper for both.
- `template/src/pdca_harness/flow.py:1169`: `(cands[name][2] or ("", name, False))[1]` handles a missing publish ref that can't happen for an id that reached the fold. A clean id always has a ref, so `cands[name][2][1]` would read more simply.
- Efficiency: each refused id costs 1 + N trial merges plus up to N² `merge-base --is-ancestor` calls (`integrate.py:1144-1155`). This only runs on the carry's conflict path for small batches, so it is not a concern.

The gates (C4, T2 docs/host-CI, T3 suite) all pass according to their logs. T4 is deferred until publish.

<!-- pdca:leaf-complete -->
