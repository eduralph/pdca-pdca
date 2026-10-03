# Advisory code review — issue 582 / merge-wait-confirms-green

No correctness bugs found. I traced the new wait loop at `template/src/pdca_harness/merge.py:168-187` through every case in brief (i)–(iv):

- green → green merges; green → failing or unreadable returns after 2 reads; green → pending/empty goes back into the wait.
- A green that shows up with `waited >= wait_secs` comes back as `pending` with the "unconfirmed" detail, and `_merge_one` (`merge.py:261-262`) shows it as "a check has not finished within Ns — green first seen with no wait budget left to confirm it (N checks)".
- A confirm read that is pending/empty after the budget is gone skips the inner loop and returns that verdict as-is, so the existing refusal messages still fit.
- `wait_secs <= 0` returns early (`merge.py:168-169`) with a single read.
- Every sleep is `min(poll_interval, wait_secs - waited)`, so the total sleep never goes over the budget. Each pass of the outer loop sleeps at least once while budget is left, so the loop always ends (for the only caller's `poll_interval=15`).

Gate logs agree: C4 is red before the fix and green after (`gate-logs/C4-verify.log`), and T3 ran 2221 tests OK in about 44 s, so the `setUp` sleep patch did its job (`gate-logs/T3-suite.log`).

Minor findings, none blocking:

- `template/src/pdca_harness/merge.py:173-176` and `merge.py:182-185`: the same four lines (step, sleep, add to `waited`, re-read) appear twice. A small inner helper, or folding the confirm into one loop with a `seen_green` flag, would remove the copy. Optional; the current form is easy to read.
- `template/tests/test_merge.py:439-462`: `_drive_reads` mostly repeats `_drive` (`test_merge.py:240-260`). The only differences are a list of rollup reads instead of one fixed result, and returning the sleep arguments. `_drive` could take an optional `reads=` instead. It also patches `_sleep` again on top of the new class-wide patch in `setUp`; that works because the patches nest, and it is needed to read the sleep arguments. Cosmetic only.
- The known gap (the confirm compares only the verdict, so `green(dco)` → `green(dco)` still merges) is stated in the brief, the docstring (`merge.py:157-159`) and the operator comments. It is not a defect in this patch, but the issue should not be closed as fully fixed. The brief already says Check must not count it closed.
