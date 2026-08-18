# Keep a failed leaf's own report of why it died

## Summary
**User impact:** When a model run (a builder, a reviewer, any leaf) dies of an API
failure, the log the harness leaves behind says nothing about the cause — it reads
`(no output captured)` next to the exit code. The vendor CLI had reported the failure
in plain words, but the only surviving copy was inside its own session transcript under
`~/.claude/projects/`, so anyone investigating had to know that file existed and go
digging by hand. In the incident that prompted this, an 18-minute build died, an
identical re-run minutes later succeeded, and the log explained neither.

This PR keeps the CLI's own error report and puts it in that log, beside the exit code
and the stderr tail — without changing what gets retried.

Reported in [#538](https://github.com/eduralph/pdca-harness/issues/538).

## What to look at
One production file, `template/src/pdca_harness/progress.py`: the stream reader already
read every line the CLI emitted (to tell whether real work happened and to show the
current tool label) and then dropped it; it now also holds on to the one line where the
CLI reports the failure it is giving up on, and appends it to the output the run
returns. Three judgement calls are worth a reviewer's eye and each has its own tests:
a report the CLI forwarded for a **sub-agent** is kept *labelled* rather than presented
as the leaf's own death; when several candidate records arrive, the one nearest the
leaf's own death wins in either arrival order; and a report longer than the line budget
says it was cut instead of presenting a fragment as the whole story.

To try it, offline, from `template/`:

```
PYTHONPATH=src python3 -m unittest tests.test_terminal_error_retention -v
```

The cases drive a stub "leaf" that emits real stream records and exits non-zero, and
assert on the `*.error.log` the harness actually writes. Revert the `progress.py` hunk
and the same log reads `(no output captured) LeafError: …` — the artifact this PR ends.
Two of the cases replay bytes a real CLI wrote (`template/tests/fixtures/`, with a note
recording which claims about the record shape are observed and which derived).

## Root cause
`run_with_heartbeat` reads a leaf's stdout stream, extracts a session flag and a tool
label, and discards the line (`template/src/pdca_harness/progress.py:150-158`); what it
keeps is a bounded **stderr** tail (`:143`, `:162-168`), which is all `output` carries
when `capture` is off (`:255`, `:257`). The CLI's own API-error report arrives as a
stream event on **stdout**, so it was read and thrown away, leaving
`_format_leaf_attempt` to fall back to `(no output captured)`
(`template/src/pdca_harness/leaves.py:729`) — the very artifact the module's own comment
calls "a post-mortem artifact that explains nothing" (`leaves.py:641-647`).

## Fix
The stream drain keeps the CLI's **marked** report — the message the vendor itself flags
as its API-error report (`is_api_error_message` in the stream spelling,
`isApiErrorMessage` in the persisted transcript) — never prose, so a leaf merely *writing
about* an API error is never mistaken for one dying of it. The held text is appended to
`output`, the same route the stderr tail takes and the same one the memory post-mortem
already rides (`leaves.py:663-666`), so it reaches the existing `*.error.log` with no
reader change anywhere downstream.

Around that: retention is unconditional (any marked report is kept whatever its cause,
including one the session then recovered from); ownership comes from a single predicate
answering both spellings of "this was a sub-agent's" (`parent_tool_use_id`,
`isSidechain`), and a sub-agent's report is retained with a prefix saying so; a
precedence order by *how near a record is to the leaf's own death* stops a `result`
wrap-up (which names only the effect) or a sub-agent's report from burying the report
that named the cause, in either arrival order. Non-`claude` stream formats and
stream-less families fall through to today's behaviour rather than guessing at a
vendor's error text. Each drained line is now decoded once and shared by all three
classifiers, replacing one JSON parse per classifier per line in a loop that runs for
the life of a session.

## Verification
- **Claim:** the CLI's own marked terminal error report reaches the leaf's `*.error.log`.
  **Checked:** `template/src/pdca_harness/progress.py:150-158` on `main` — the drain reads
  and drops each line; `:143` + `:255` — `output` is the stderr tail alone with `capture`
  off; `template/src/pdca_harness/leaves.py:729` — that empty tail becomes
  `(no output captured)`. **Test:** `template/tests/test_terminal_error_retention.py:218`
  (`ReportReachesTheErrorLog`) — asserts on the file `_invoke_leaf_resilient` writes
  (`leaves.py:720`); fails pre-fix, passes post-fix.
- **Claim:** retention is unconditional — a report is kept whatever its cause, including
  one the session then recovered from. **Checked:** the retention path is not reached
  through any cause/kind test. **Test:** `test_terminal_error_retention.py:268`
  (`RetentionIsUnconditional`) — recovered-then-died, permanent, and report-only streams.
- **Claim:** a sub-agent's report is kept labelled, never presented as the leaf's own
  death. **Test:** `test_terminal_error_retention.py:292` (`SubAgentReportsAreLabelled`) —
  both spellings labelled, main-session report not.
- **Claim:** among several candidates the nearest the leaf's own death wins, in either
  arrival order. **Test:** `test_terminal_error_retention.py:320` (`NearestRecordWins`) —
  wrap-up and sub-agent report, each before and after the main report; a newer main report
  replaces an older one; a wrap-up alone is still kept.
- **Claim:** nothing is classified — `produced`, `LeafError.transient` and the retry
  counts are unchanged for every input. **Checked:** `leaves.py:657` (the leaf spawn) and
  `leaves.py:641-647` on `main` — the only consumer of `produced`; it is returned exactly
  as before. **Test:** `test_terminal_error_retention.py:368` (`NothingIsClassified`) —
  explicit invocation counts (3 retries stay 3, 0 stays 0), green on both sides by design
  so a later change cannot move them silently.
- **Claim:** nothing else changes — raw `capture` is byte-identical, other stream formats
  and stream-less families are untouched, a clean exit is reported as today. **Checked:**
  all four `run_with_heartbeat` call sites on `main` — `gates.py:559`, `publish.py:833`
  and `leaves.py:752` pass `capture=True` (the append is skipped there), and only the leaf
  spawn `leaves.py:657` does not, so a gate's evidence line cannot pick up the appended
  text. **Test:** `test_terminal_error_retention.py:398` (`NothingElseChanges`).
- **Claim:** the retained records match what the shipped CLI emits. **Test:**
  `test_terminal_error_retention.py:481` (`PinnedVendorRecords`) — replays pinned bytes
  from `template/tests/fixtures/`, skipping rather than erroring if the fixtures are
  absent; `template/tests/fixtures/README.md` records the greps that re-derive each field
  from the binary and marks every claim observed or derived.
- **Whole change:** with the `progress.py` hunk reverted, 23 of the 34 new cases fail
  (the module still imports, so this is a real failure, not a load error); with it, all 34
  pass. The offline suites are green on the patched tree (root suite, driver suite 1,792
  tests), `git diff --check` is clean, and the docs lint / rendered-site link audit pass.

Fixes #538
