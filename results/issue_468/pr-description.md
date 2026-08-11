## Summary

**User impact:** Running `pdca flow` on one id and on a list of ids could give
different answers about the same bundle on the same disk. A discontinued bundle
failed the run when asked about alone but silently vanished from the tally when a
healthy sibling ran beside it; an error that cleanly aborts a batch run crashed the
single-id run with a raw traceback; and a bundle that had been split into child
work items was told "to redo it: rm -rf <bundle>" — advice that, if followed,
deletes the only record connecting the split's children to their parent.

This change routes both command shapes through one drive path returning one per-id
results table, so the report, the exit code and the recovery advice are the same
however many ids you pass — and a split parent is now told to drive its children,
never to delete itself.

Reported in [#468](https://github.com/eduralph/pdca-harness/issues/468).

## What to look at

Two modules: `template/src/pdca_harness/cli.py` (the `flow` command's routing and
reporting) and `template/src/pdca_harness/flow.py` (the shared drive path and the
new terminal-recovery hint). The shape of the change: the single-id command no
longer has its own machinery — both shapes make the same call, get back one table
with an answer for *every* id asked for, and differ only in how they print it. The
one intended difference between them — a single-id run stopping for your sign-off
exits 0, an unfinished member of a batch exits 1 — is now an explicit parameter of
one shared exit rule instead of a side effect of two code paths.

To try it: pick a bundle in any settled state (complete, discontinued, resolved, or
a split parent) and run `pdca flow <id>` and `pdca flow <id> <other-id>` against
the same tree. Both report the same disposition for it and apply the same exit
rule; a split parent's skip note names `pdca flow <child-ids>` and never `rm -rf`.

Three visible behaviour changes are deliberate, not oversights: a terminal
bundle's disposition now prints on stdout (the ordinary `state<TAB>path` line)
rather than as a stderr-only notice; a batch run now reports and counts the ids it
skipped, so a discontinued id plus a completing one says `1/2 complete` and exits
1 where it said `1/1 complete` and exited 0; and an id the planner declines to
brief now exits 1 on the batch shape too, as it always did on the single-id shape.

## Root cause

`cli._flow` had a dedicated `len(ids) == 1` branch: a pre-run short-circuit on raw
disk state that printed the `rm -rf` hint (`template/src/pdca_harness/cli.py:604-608`
on `main`), then a call to `flow.flow` whose bare state-string return the CLI turned
into a report and exit code (`cli.py:638-648`), with no handler for
`flow.PreflightError` — while lists went through `flow.flow_ids` and `_report_batch`
(`cli.py:651-656`). Worse, `flow_ids` returned a map covering only the bundles it
*drove* (its filter dropped skipped ids, `template/src/pdca_harness/flow.py:1033-1046`
on `main`), so each caller had to invent dispositions for the rest — and the two
shapes invented different ones.

## Fix

Every non-empty id list now drives through one `flow.flow_ids` call inside one
`except flow.PreflightError` (`cli.py:604-620` in this PR), and `flow_ids`'s map is
total over the ids it was given: a skipped id's disposition is its state on disk,
the identical value recorded for a driven bundle (`flow.py:1113-1132`, contract in
the docstring at `flow.py:1069-1079`). The two presentations, `_report_single` and
`_report_batch`, read that map and nothing else — `_report_single` indexes it
rather than falling back to disk (`cli.py:656`), because a second authority is
exactly what let the shapes disagree. One exit rule, `_results_rc`
(`cli.py:630-641`), serves both; the single-id shape passes AWAITING_SIGNOFF as an
extra success state (`cli.py:661`) and the batch rule is unchanged. The terminal
recovery hint moves onto the shared path and becomes lineage-aware
(`flow.py:691-727`): a lineage record carrying a `children` key is a split parent,
so the destructive `rm -rf` advice is suppressed by the key's presence and the hint
names `pdca flow <child-ids>` instead, degrading gracefully on a hand-edited record
(`flow.py:671-688`). `flow.flow` remains as the single-bundle library driver, its
docstring now saying so (`flow.py:380-388`), and a test pins that the CLI never
routes through it again.

One narrowing to be aware of: previously a single-id run returned 1 when the
tracker had reopened a resolved issue *and* clearing the local resolved marker
failed (`cli.py:618-622` on `main`). The shared path keeps the loud failure message
but reports the bundle RESOLVED with exit 0 — the batch shape's existing behaviour,
kept rather than duplicating the revalidation decision in the CLI.

## Verification

- **Claim:** on byte-identical disk state, both shapes report the same disposition
  for the shared id and derive their exit code from the same rule, for every state
  in {in-flight, COMPLETE, DISCONTINUED, RESOLVED, terminal split parent}.
  **Checked:** `cli.py:604-648` on `main` — two routes, two authorities; in this PR
  one call and one map (`cli.py:604-622`). **Test:**
  `template/tests/test_flow_entrypoint_parity.py` — every case drives `cli._flow`
  itself (never a hand-picked internal call) twice over byte-identical copies of one
  seeded tree, single-id and with a completing sibling, and asserts disposition,
  both exit codes, and that adding the sibling cannot move the verdict.
- **Claim:** an error meant to abort a run yields the same exit code and message on
  both shapes. **Checked:** `cli.py:637-648` on `main` — the single-id route had no
  `try/except` at all; in this PR both shapes share one (`cli.py:614-620`).
  **Test:** `test_preflight_error_same_rc_and_message_both_shapes`.
- **Claim:** a terminal split parent is never told `rm -rf`; its message names
  `pdca flow <child-ids>`. **Checked:** `cli.py:606` on `main` printed the hint
  unconditionally; `flow.py:691-727` in this PR suppresses it on a `children`
  lineage edge. **Test:** `test_terminal_split_parent_names_children_never_rm_rf`,
  with the parent built by the production split-accept path, and
  `test_malformed_lineage_children_degrades_the_hint_not_the_run` for hand-edited
  records (the hint degrades; the run never aborts).
- **Claim:** the map is total, so no caller re-derives an answer from disk.
  **Checked:** `flow.py:1033-1046` on `main` dropped skipped ids; `flow.py:1113-1132`
  in this PR answers for every id. Existing tests updated to the new contract assert
  totality directly (`template/tests/test_flow_slice.py:404-418`, `:514-529`,
  `template/tests/test_state_resolved.py:145-154`). **Test:**
  `test_single_id_report_and_rc_come_from_the_map_not_from_disk` — a map that
  disagrees with the bytes on disk wins, proving there is no second authority.
- **Claim:** the single-id presentation is preserved as a presentation — the
  `state<TAB>path` stdout line, the listing of open sign-off items, and exit 0 when
  stopping for the human. **Test:**
  `test_single_id_awaiting_signoff_presentation_preserved` pins both sides: same
  disposition on both shapes, exit 0 single / 1 in a batch.
- **Test:** `template/tests/test_flow_entrypoint_parity.py` (new, 11 tests) — with
  the production hunks reverted and the test kept, 11 failures plus one uncaught
  `PreflightError`; with them restored, 11/11 green. Run with
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_entrypoint_parity`.
- **Suites:** offline driver suite green at 1633 tests; template render and
  `copier update` compatibility suites green at 7 tests with copier 9.17 actually
  installed (no self-skips); docs lint and the 22-page site render/link audit green.

Fixes #468
