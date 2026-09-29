# Advisory code review — issue #539 (what a transient leaf death is)

Lenses: bugs the patch introduces, and reuse / simplification / efficiency. Line numbers are
on the patched target at `$PDCA_TARGET`. I found no correctness bug that breaks a stated
criterion. The classifier follows the shape of `_is_session_event`, runs once per decoded line
(no extra JSON parse in the hot loop), and degrades to `False` for codex and stream-less
families. C4 went red for real on the pre-fix leg: assertion failures, not import errors or
missing fixtures. The `PinnedVendorRecords` cases ran rather than skipped, since both
`*.stream.jsonl` fixtures already exist on the base. The findings below are the edges worth a look.

- NEEDS-HUMAN — `template/tests/test_terminal_error_retention.py:368-401`: the brief says not
  to touch child-1's `test_terminal_error_retention.py`. The patch edits it anyway: it renames
  `NothingIsClassified` to `RetryCountsArePinned` and flips three assertions from "1 run /
  produced True" to "3 runs / produced False". The flip can't be avoided, because those
  guards pinned exactly the old behaviour that criterion (i) changes. They would go red under
  any correct fix, and C4's red leg shows the three failures. A human should confirm this
  counts as the necessary edit and not a scope breach. The other options were to delete the
  guards or move them into the new file.
- NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:2202-2204`: the patch rewrites the
  "transient" message inside `_do_build_command`, and the brief puts that function out of
  scope (it belongs to #537). The edit is only a string, and without it this restatement
  would still say "without emitting any work", which is false. So it is arguably required by
  criterion (iv). But it is a hunk in #537's function, which means a merge conflict with that
  sibling is likely. A human should decide whether to keep it or hand it to #537.
- `template/src/pdca_harness/progress.py:776-800` (`_TRANSIENT_CAUSE_RE`): the fallback for
  the `unknown` kind is broad. Bare `\btimeout\b`, `\bterminated\b`, `409`, and any
  standalone `5\d\d` all count as transient. The vendor builds `unknown` text as
  `API Error: ${e.message}` for *any* thrown `Error`, so an unrelated message that happens to
  contain a number like 512 or the word "timeout" will be retried. The damage is bounded:
  only `unknown` reports with no typed `api_error` reach this regex, and the cost is at most
  `attempts-1` extra runs. Tightening it would help, for example by anchoring the status
  alternative to `status|HTTP|code` context or dropping `\b5\d\d\b` and relying on the
  worded 5xx phrases. Advisory, not a blocker.
- `template/src/pdca_harness/progress.py:59` (`is_signal_death`): for a *direct* child, any
  real exit code from 129 to 192 is now read as a signal death and never retried. The test
  `test_a_bare_exit_137_is_read_as_the_same_death` (`tests/test_terminal_error_classification.py:361`)
  pins this on purpose. This only ever holds back a retry and never adds one, so it's the
  safe direction. Still, a CLI that uses a code in that range for a transient startup failure
  would lose #138's retry. I know of none today. Recording it so the trade-off is visible,
  not as a defect.
- `template/src/pdca_harness/progress.py:261-267`: after main-session work clears the verdict,
  the kept record still has the `_REPORT` shape. A later `result` wrap-up that carries a
  transient `api_error_status` therefore can't be kept (lower precedence) and can't set the
  verdict again. In practice a fresh API-error death emits its own `_REPORT`, which is kept
  and re-sets the verdict, so I don't see this misfire on real CLI output. It's a quiet
  coupling between `_note_terminal` precedence and the verdict, and one comment line would
  save a future reader from rediscovering it.

Reuse and simplification: nothing to flag. `_reports_transient_cause` reuses
`_stream_event`, `_is_subagent_event` and `_claude_message_texts` instead of duplicating them.
`_note_terminal` returning `bool` is the smallest change that keeps the verdict tied to the
kept record.
