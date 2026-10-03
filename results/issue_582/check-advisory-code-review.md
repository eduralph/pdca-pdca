# Advisory code review — issue 582 / merge-wait-confirms-green

No correctness bugs found in this diff. The new `_wait_for_green` loop
(`template/src/pdca_harness/merge.py:171-193`) does what the brief asks:

- It always ends. Each pass through the outer `while True` either returns or sleeps a
  full `poll_interval` and adds it to `waited`, and a confirm is only taken when
  `wait_secs - waited >= poll_interval` (`merge.py:185-187`). So the sum of sleeps never
  goes over `wait_secs`.
- The confirm is never shortened. This was the iteration-1 rejection, and it is fixed:
  `_sleep(poll_interval)` at `merge.py:189` replaces the old `min(...)` step.
- A `pending`/`empty` confirm goes back into the inner wait. A `failing`/`unreadable`
  confirm comes back out through `if verdict != "green": return` (`merge.py:180-181`) with
  no extra read.
- `wait_secs <= 0` still does one read and returns it as-is (`merge.py:172-173`).
- `_merge_one` is unchanged. The new `pending` detail shows up in the existing "has not
  finished within Ns — …" refusal (`merge.py:268-269`), and the ready-undo still runs
  (`merge.py:282`).

The gate log `gate-logs/C4-verify.log` shows the new tests red without the fix and green
with it. The class-wide `_sleep` patch in `setUp` (`template/tests/test_merge.py:84-86`)
keeps the four green-path tests from sleeping for real. The suite ran in 0.079 s.

Findings (all minor):

- NEEDS-HUMAN — `template/src/pdca_harness/config.py:743-746`: any `merge_wait_secs` from
  1 to 14 now quietly refuses every PR under `merge_requires = "all"`. The patch only
  documents this in comments (`config.py:383`, `template/pdca.toml.jinja:153-155`).
  `Config.load` already warns about and corrects bad values (negative, non-integer), so
  a one-line warning for `0 < merge_wait_secs < 15` would match how it handles those.
  Whether to add it is a scope call: the brief lists only the comment edits for
  `config.py`, and the 15 s poll interval is a default argument in `merge.py:148`, not
  something `config.py` knows about.
- `template/src/pdca_harness/merge.py:176`: when the budget is not a multiple of 15
  (say 20 or 299), the inner wait still takes a short last step (`min(poll_interval,
  wait_secs - waited)`). A `green` read after that short step is then always refused as
  unconfirmed, because less than 15 s is left. This is fail-closed, so it is safe. The
  short step only changes which refusal message you get: it can catch a late `failing`
  instead of reporting `pending`. No change needed; mentioning it so nobody reads that
  short step as a path that can lead to a merge.
- `template/tests/test_merge.py:530-531` and `:584-585` assert the full refusal detail
  word for word ("green first seen with 0s of wait budget left, too little to confirm it
  15s later (2 checks)"). That is stricter than the brief, which only asks for
  `unconfirmed`/`confirm` in stderr, so any later rewording will break both tests.
  `test_green_with_no_budget_left_to_confirm_is_not_believed` already checks for
  `"confirm"` on its own (`:528`). This is a style choice, not a defect.

No reuse or efficiency problems: the change sits entirely inside the one function that
owned the wait, and there is no existing helper it should have used. The new
`_drive_reads` test helper (`test_merge.py:439-472`, with `_checks` at `:475`) is close to the inline fake in
`test_pending_then_green_merges` (`:296-310`). The brief only asks for that test's read
count to change, so leaving the old fake alone is the right call.
