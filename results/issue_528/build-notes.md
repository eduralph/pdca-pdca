# Build notes — issue 528

## What changed and why

Three files, target `eduralph/pdca-harness @ main` (HEAD `4050da2`, confirmed equal to
`origin/main` in the worktree before editing):

1. `template/process/act-log.md.jinja:7` — replaced "Newest entries on top." with "New
   entries are appended at the end of this file — never prepended, never inserted between
   existing entries." This was the one place on `origin/main` that told a session to
   prepend (confirmed with `git grep -n "Newest entries on top"` in the worktree — only
   hit). It now agrees with `act.append_entry` (`act.py:664-666`, opens the file `"a"`)
   and the Act role prompt (`act.md.jinja:16`, "appended").

2. `template/src/pdca_harness/handoff.py`:
   - `session()` (`:373-380` post-fix): the act-role baseline now also carries
     `act_log_text` — the full session-start text of `process/act-log.md`, not just its
     length and sha. The append-only check needs the actual content to tell "inserted
     somewhere other than the end" apart from "existing text was itself changed" — length
     alone can't distinguish those (both leave the length changed and the sha different).
     Captured at the same place the existing `act_log_len`/`act_log_sha` pair already is,
     per the brief's "If the check needs more from the session-start baseline than length
     + sha, capture it at the same place (`handoff.session`)."
   - `check_act()` (`:206-254` post-fix): rewritten around the new baseline text.
     - Baseline missing `act_log_text` (a hand-built dict, e.g. the kept
       `test_named_entry_must_postdate_the_baseline`): falls back to the OLD length/sha
       logic verbatim, so that test's behaviour is unchanged.
     - `text == prev_text` → "unchanged" (criterion f, kept).
     - `text.startswith(prev_text)` → the clean append path: entry must be in the tail,
       else the "predates this session" message (criteria b/e, kept — this is the exact
       shape of the existing `test_named_entry_must_postdate_the_baseline`, now reached
       through a literal-prefix check instead of a length-index check).
     - Otherwise (not a clean append): `_is_pure_insertion()` decides which of the two
       remaining messages fires.
   - `_is_pure_insertion()` (`:183-206` post-fix, new): longest-common-prefix +
     longest-common-suffix check. If together they cover the whole of the baseline text,
     nothing inside the baseline was touched — the difference is one contiguous block of
     new material landing somewhere that isn't the very end (prepended, or spliced between
     two existing entries) → criterion (c) message ("must be appended at the end").
     Otherwise some baseline content itself was altered or is missing → criterion (d)
     message (names "append-only").

3. `template/tests/test_handoff.py` — six new tests appended to `ActContract`
   (`:275-402` in the patched file), after the existing three the brief says must stay
   green. Each drives a real baseline through `handoff.session(cfg, "act")` and reads the
   verdict through `handoff.run_check(cfg, <date>, role="act", environ=env)`, per the
   brief's own wording of the success criterion and its citation of
   `test_act_session_carries_the_baseline` as the peer to mirror for that shape:
   - `test_append_at_the_end_passes` — (b).
   - `test_prepended_entry_fails_whichever_date_is_named` — (c), the exact repro shape
     from the brief (prepend), asserting BOTH the new date and the older date fail, both
     with the "appended at the end" message.
   - `test_entry_inserted_between_existing_entries_fails` — (c), the other shape the
     brief names (insert between two existing entries).
   - `test_editing_existing_text_fails_even_with_a_correct_append` — (d), the brief's
     other repro shape (change a word in the old entry, then append correctly). Asserts
     the message names "append-only" and does NOT say "appended at the end" (that's the
     (c) message, a different defect).
   - `test_older_entry_named_after_a_correct_append_still_fails` — (e), kept, now proven
     through a real session instead of only a hand-built baseline.
   - `test_unchanged_log_and_absent_date_both_fail` — (f), kept, same treatment.

## What I considered and ruled out

- **Just fixing the header, leaving `check_act` alone.** Ruled out per the brief's own
  "Self-test": with the header fixed but the check untouched, case (c) with the older date
  still PASSES on the reverted-production-only tree (confirmed below, the genuine red
  leg) — a session following the corrected header (append at the end) would pass, but the
  check still can't catch the OLD wrong pattern (prepend) if someone follows it anyway,
  and case (d) still passes regardless. Both the header and the check had to change,
  exactly as the brief's "Invariant to restore" says.

- **Just fixing `check_act`, leaving the header alone.** Ruled out for the same reason in
  reverse — every session would still be told "Newest entries on top" and get flagged for
  following the header's own instruction. Both had to change together (criterion a).

- **A second stored field instead of the full text** (e.g. storing just the tail hash of
  where the last entry's heading starts). Rejected: it still can't distinguish "inserted
  before the end" from "content edited", which is exactly the distinction criteria (c) and
  (d) require different messages for. Storing the full baseline text is a few hundred
  bytes to a few KB (the whole act log) written once per Act session into a scratch JSON
  file already used for exactly this kind of session bookkeeping (`record_pass`,
  `record_abandon`) — not a meaningfully heavier cost than what's already there.

- **A line-based diff (e.g. `difflib.SequenceMatcher` over lines) instead of the
  prefix+suffix check.** Considered, but the brief's own repro constructs entries with
  embedded content changes ("change a word in it") that a coarse line-level match would
  still classify correctly in this case, but a pure character-level insertion between two
  untouched entries (criterion c's second shape) is exactly the case the simpler
  prefix+suffix computation handles in O(n) with no extra dependency and no ambiguity
  about how "a line" is defined for a markdown file that isn't line-delimited in a fixed
  way. Kept the simpler, dependency-free version; it is proven against both of the brief's
  named repro shapes (prepend, insert-between) and the changed-word case below.

- **Not touching `agents/act.md.jinja:16` / `act.py`.** The brief said to change either
  "if either still reads ambiguously after the header change, but no behaviour change
  there." I checked both (`act.md.jinja:16`: "A dated entry appended to
  `process/act-log.md`"; `act.py:659-666` `append_entry`, opens the file in append mode)
  and neither says or implies "top" or "prepend" — both already read as append-at-the-end.
  Left unedited to keep the diff to what's actually needed.

## The three refutation questions

**(a) Genuine red?** Yes. I stashed only the two production files (`handoff.py`,
`act-log.md.jinja`, kept the test file in place) with
`git stash push -u -- template/src/pdca_harness/handoff.py template/process/act-log.md.jinja`,
then ran `PYTHONPATH=src python3 -m unittest tests.test_handoff.ActContract -v` from
`template/`. Three of the six new tests failed:
- `test_editing_existing_text_fails_even_with_a_correct_append`: `AssertionError: 0 != 1`
  — the OLD check genuinely returns PASS (rc=0) for a session that edited existing text
  and then appended correctly at the end. A real, unqualified false pass: exactly
  criterion (d)'s bug (also the brief's own repro: `run_check("2026-08-15")` → 0 on main
  for the changed-word case).
- `test_entry_inserted_between_existing_entries_fails`: `'appended at the end' not found`
  — the OLD check DOES fail this case (rc=1, since the entry ends up left of the session-
  start length cutoff, so `entry not in text[prev_len:]`), but with the wrong message
  ("appears only in act-log text that predates this session"), not the brief's required
  "entries must be appended at the end of the log" (criterion c). A right-verdict/
  wrong-message failure is still a failure of the brief's own success criterion — (c)
  spells out what the message must say.
- `test_prepended_entry_fails_whichever_date_is_named`: same wrong-message failure on its
  first assertion (the new date's FAIL message), which is the brief's literal repro shape
  (prepend a newer entry above an older one). The test never reached its second half (the
  older date) because the first `assertIn` already raised — but the brief's own repro
  instructions independently establish that the older-date half is the one that actively
  PASSES (`run_check("2026-07-01")` → 0) on `origin/main`, which is the sharper form of
  this same bug: not just a wrong message, a wrong verdict.

  The other three new tests ((b), (e), (f)) passed even pre-fix, because those paths were
  already correct on `origin/main` — expected, since the brief only asks (b)/(e)/(f) to
  stay "kept".

  Then I restored the stash (`git stash apply <sha>` + `git stash drop`, never a bare
  `stash pop`, per the shared-stash-stack rule) and reran the full suite green (41/41).

**(b) Production path?** Yes. Every new test calls `handoff.session` and
`handoff.run_check` — the same two entry points `/handoff`'s hook
(`.claude/hooks/handoff_guard.py`) and the driver's reap (`report_at_reap`) call in
production. No mock, no re-implementation; `check_act` and `_is_pure_insertion` are
exercised through their real call path, not called directly except where the brief's own
peer test (`test_named_entry_must_postdate_the_baseline`) already calls `check_act`
directly and is kept unedited.

**(c) Fixture includes the fault?** Yes. Every new test writes the ACTUAL fault shape into
`process/act-log.md` inside the temp instance root (`self.cfg.process_dir`) — the
prepended entry, the entry spliced between two real existing entries, and the edited word
inside the old entry — using the same `_log()` helper the existing tests use, not a
curated fixture that excludes the wrong shape.

## Test run summary

- `cd template && PYTHONPATH=src python3 -m unittest tests.test_handoff -v` — 41/41 green
  with the fix; 3 genuine failures with only the production hunks reverted (see (a)
  above).
- `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` — 1900 tests, OK
  (skipped=2, pre-existing/unrelated — a sandboxed worktree case and a git-tag-less
  render case, neither touches `handoff.py` or the act log).
- `python3 -m unittest discover -s tests -v` (root suite: render + update-compat, copier
  IS importable in this environment) — 24/24 green. This is the brief's named smoke check
  for the header edit (`.md.jinja` renders through `test_render_and_run.py`).

No formatter / pre-commit config exists in this repo (`.pre-commit-config.yaml` absent, no
`[tool.ruff]`/`[tool.black]` in `pyproject.toml`) — `CONTRIBUTING.md` names only DCO
sign-off (`git commit -s`, a publish-time trailer, not a patch-time concern) and the two
test suites above, both green.
