## Summary
**User impact:** An Act review that followed the act log's own instructions could not be
closed. The log header told every project to put new entries at the top. When a session
did that, `/handoff <date>` refused the entry it had just written, saying the entry
"predates this session". The session could only get out by breaking the log's stated order,
adding a filler line at the bottom, or abandoning a review it had actually finished. Naming
an *older* entry, which is wrong, was accepted. So was editing earlier entries, which the
header's own "Append-only" forbids.

This PR makes "append new entries at the end" the one rule. The header now says it, and
the exit check now enforces it, with messages that tell the session what to do instead.

Reported in [#528](https://github.com/eduralph/pdca-harness/issues/528).

## What to look at
- The one-line header change in the act-log template ("Newest entries on top" is gone).
- The rewritten act exit check in the handoff module. It now keeps the log's full text from
  session start and compares against it, where before it only had a length and a hash.
- To try it: in a rendered instance, start an Act session with an existing entry in
  `process/act-log.md`. Add a new dated entry at the **top** and run `/handoff <new-date>`.
  It fails and says entries must be appended at the end. Move the entry to the bottom and it
  passes. Change a word in the old entry and it fails with an append-only message.

Existing logs are not reordered. An instance whose log is newest-first today just puts its
next entries at the end. Cleaning up the old order is left to each instance.

## Root cause
The template gave two opposite rules. The act-log header said "Newest entries on top", while
`act.append_entry` and the Act role prompt both append at the end. The exit check assumed an
append (it only searched `text[prev_len:]`) but never checked that the session had actually
appended. That made a correct prepend fail and let a wrong answer or an edit to history pass.

## Fix
- `template/process/act-log.md.jinja`: the header says new entries are appended at the end,
  never prepended or inserted between existing entries.
- `handoff.session()` saves the full session-start text of the act log in the baseline
  (`act_log_text`), next to the existing `act_log_len` / `act_log_sha`.
- `check_act()` compares the current log with that text:
  - unchanged → fail (as before);
  - starts with the session-start text → pass only if the named entry is in the added tail
    (as before, now an exact prefix check instead of a length index);
  - session-start text intact but the new block is not at the end → fail, "entries must be
    appended at the end of the log";
  - anything else (session-start text edited or removed) → fail, naming the append-only rule.
- A new helper, `_is_pure_insertion()`, tells the last two cases apart using the longest
  common prefix plus the longest common suffix. It only chooses which failure message to
  show. It cannot turn a failure into a pass.
- A baseline without `act_log_text` (a hand-built dict, or a caller older than this change)
  falls back to the old length/hash checks, so existing callers and tests keep their current
  behaviour. That fallback keeps the old weakness for those callers. Sessions started through
  `handoff.session()` always capture the full text, so they get the new check.

`act.append_entry` and `template/agents/act.md.jinja` were already append-only and are
unchanged.

## Verification
Line numbers are on `main` at 4050da2 (pre-fix) and in the patched files (post-fix).

- **Claim:** the header and the writer agree on one rule, append at the end.
  - **Checked:** `template/process/act-log.md.jinja:7` on `main` was the only "Newest entries
    on top" in the tree (`git grep`). Post-fix it reads "appended at the end" (`:7-8`).
    `template/src/pdca_harness/act.py:659-666` opens the log in append mode, and
    `template/agents/act.md.jinja:16` says "appended". Both are unchanged.
- **Claim:** a prepended or mid-log entry fails whichever date is named, including the older
  date that passes on `main`.
  - **Checked:** on `main`, `template/src/pdca_harness/handoff.py:206-210` only tests
    `entry not in text[prev_len:]`. Post-fix, `handoff.py:251-259` requires an exact prefix
    match and otherwise sends a non-append insertion to the "appended at the end" failure.
    The helper is at `handoff.py:183-207`.
  - **Test:** `test_prepended_entry_fails_whichever_date_is_named` and
    `test_entry_inserted_between_existing_entries_fails` (`template/tests/test_handoff.py:328`,
    `:347`): both fail on `main`, pass with the fix.
- **Claim:** editing or removing session-start text fails even if a correct entry is also
  appended.
  - **Checked:** nothing on `main` compares the old text (`handoff.py:202-210` has only the
    hash and length). Post-fix, `handoff.py:260-262` fails with the append-only message.
  - **Test:** `test_editing_existing_text_fails_even_with_a_correct_append`
    (`test_handoff.py:364`): returns 0 (pass) on `main`, 1 with the fix, and the message
    names "append-only".
- **Claim:** the checks that were already right still hold: append-and-name passes, naming
  an older entry after a correct append fails, an unchanged log fails, an absent date fails.
  - **Checked:** baseline capture at `handoff.py:425-434` post-fix (was `:374-377` on `main`).
  - **Test:** `test_append_at_the_end_passes`,
    `test_older_entry_named_after_a_correct_append_still_fails`,
    `test_unchanged_log_and_absent_date_both_fail` (`test_handoff.py:317`, `:381`, `:394`).
    These pass before and after, as they should.
- **Claim:** the existing `ActContract` tests are unchanged and still green.
  - **Test:** `test_handoff.py:280-300`, not edited. All six new tests run through
    `handoff.session()` and `handoff.run_check()`, the same entry points `/handoff` and the
    driver use.
- **Suites:** `template/`: `PYTHONPATH=src python3 -m unittest discover -s tests` passes
  1900 tests (2 unrelated skips). The root render and update-compat suite passes 24 tests;
  it renders the changed header.

Fixes #528
