# Brief — issue 528 / act-log-append-only-and-the-check-enforces-it

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** act-log-append-only-and-the-check-enforces-it
- **Defect:** The template gives three different rules for where a new act-log entry goes, and the
  Act exit check enforces its own assumption loosely enough to let a wrong answer through.
  (1) The act-log header shipped to every instance says "Append-only … Newest entries on top."
  (`template/process/act-log.md.jinja:3,7`), which tells a session to PREPEND. (2) `act.append_entry`
  (`template/src/pdca_harness/act.py:659-666`) and the Act role prompt
  (`template/agents/act.md.jinja:16`, "A dated entry appended to `process/act-log.md`") both add at
  the END. (3) `handoff.check_act` (`template/src/pdca_harness/handoff.py:183-211`) confirms the
  log changed since session start (sha check, `:202-205`). It then only requires the named id to
  appear in `text[prev_len:]` (`:206-210`), i.e. it assumes an append but never checks that the
  session actually appended. Result: a session that follows the header and prepends gets
  "'<date>' appears only in act-log text that predates this session" for the entry it really
  wrote. Worse, naming an OLDER entry then PASSES, because the old tail has shifted past
  `prev_len`. Reproduced during Plan on an export of `origin/main`: prepend a 2026-08-15 entry
  above a 2026-07-01 one, and `run_check("2026-08-15")` → 1 (FAIL) while
  `run_check("2026-07-01")` → 0 (PASS). The check also passes a session that rewrites earlier
  entries and then appends, which the header's own "Append-only" forbids. The baseline
  (`act_log_len` / `act_log_sha`) is captured at `handoff.py:374-377` and came in with 900d638 (#331).
- **Decision (human, at Plan):** the act log is append-only and new entries always go at the
  END. "Newest entries on top" is the rule that is wrong; `act.append_entry` and the Act prompt
  already follow the chosen rule.
- **Success criterion:** (a) The template's act-log header no longer says "Newest entries on
  top". It states that entries are appended at the end, and it agrees with `act.append_entry` and
  `agents/act.md.jinja`. With the session-start baseline taken by the driver's own capture
  (`handoff.session(cfg, "act")`, `handoff.py:354-412`) and the verdict read through
  `handoff.run_check(cfg, <date>, role="act", environ=<that session's env>)`:
  (b) a session that APPENDS a new dated entry at the end and names its date → PASS;
  (c) a session whose new entry is NOT at the end (put at the top, or inserted between existing
  entries) → FAIL, whichever date it names, including the older entry's date that passes on main
  today. The message says entries must be appended at the end of the log;
  (d) a session that changes or removes text that was in the log at session start, even if it
  also appends a correct new entry → FAIL, with a message naming the append-only rule;
  (e) appending a new entry but naming an OLDER entry's date → FAIL (kept);
  (f) an unchanged log → FAIL, and a date absent from the log → FAIL (both kept).
  The existing `ActContract` tests in `template/tests/test_handoff.py:275-301` stay green without
  edits.
- **Falsifiability:** RED on the offline driver suite with no extra environment. On `origin/main`,
  case (c) with the older date PASSES (reproduced during Plan through `handoff.session` +
  `handoff.run_check` on an export of `origin/main`), and case (d) PASSES as long as the new entry
  is appended, because nothing compares the session-start text. The test uses only pre-existing
  API (`handoff.session`, `handoff.run_check`, `handoff.check_act`), so the C4 red leg imports
  cleanly and fails on an assertion. The patch touches `handoff.py`, so C4 classifies it as a
  production change and earns a real red. The header edit is `.md.jinja`, which the gate counts
  as docs; the `handoff.py` change is what makes the bundle verifiable.
- **Invariant to restore:** The act log is append-only, and the Act exit contract accepts exactly
  that: a session passes only when the text present at session start is unchanged and the named
  entry is in what the session added after it. One written rule, the same in the header, the
  writer (`act.append_entry`), the role prompt and the check. Source (internal, Tier C): the
  header's own "Append-only" (`act-log.md.jinja:3`); `check_act`'s docstring (`handoff.py:184-190`:
  the baseline "is what distinguishes an entry THIS session wrote from one that predates it");
  the human's decision recorded above. Self-test: fixing only the header leaves the check passing
  a wrong answer (c)/(d); fixing only the check leaves the header telling every instance to
  prepend and fail (a). Both have to change.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:**
- **Conflicts with:**
- **Ordering note:** Run 4 of `plan-0.60-bug-order.md`, after #534 (merged, e9e5982), which rewrote
  the session/reap half of `handoff.py` but not `check_act`. This bundle owns
  `template/src/pdca_harness/handoff.py`, `template/tests/test_handoff.py` and
  `template/process/act-log.md.jinja` for the run. #508 was briefed to stay out of the first two,
  so the two share a wave.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** Make "append at the end" the single act-log rule: correct the template header, and
  make the Act exit check enforce it (unchanged session-start text, the named entry in what was
  added after it). Fix the check's messages so a session that prepends is told to append. If the
  check needs more from the session-start baseline than length + sha, capture it at the same place
  (`handoff.session`). Also change `agents/act.md.jinja:16` or `act.py` wording if either still
  reads ambiguously after the header change, but no behaviour change there; both already append.
  / out of scope: reordering any existing instance's log. pdca-pdca's `process/act-log.md` is
  newest-on-top today (entries from 2026-09-15 at line 32 down to 2026-08-01 at line 1113); after
  this lands its next entries go at the end, and cleaning up that order is instance housekeeping.
  Also out of scope: removing pdca-pdca's two HTML-comment workaround trailers (instance-side,
  after this lands); `/handoff` command wiring (#508); any other process file.
- **Repro instruction:** On `origin/main`, in a temp instance: write `process/act-log.md` as
  `# Act log\n\n# Act review — 2026-07-01 — cycles considered: 1\n`; enter
  `handoff.session(cfg, "act")` (captures the baseline); rewrite the log as header + a new
  `# Act review — 2026-08-15 — …` entry + the old entry; then
  `handoff.run_check(cfg, "2026-08-15", role="act", environ=env)` → 1 and
  `handoff.run_check(cfg, "2026-07-01", role="act", environ=env)` → 0. For (d): keep the old entry
  but change a word in it, append a new 2026-08-15 entry, and `run_check("2026-08-15")` → 0 on main.
- **External dependencies:** none
- **Test file:** template/tests/test_handoff.py (append to the `ActContract` class, `:275`)
- **Citations expected:** Do must cite path:line on `origin/main` for every change. Peer tests to
  mirror: `test_named_entry_must_postdate_the_baseline` (`test_handoff.py:283-296`) for (b) and
  (e), and `test_act_session_carries_the_baseline` (`test_handoff.py:323-…`) for driving a real
  session baseline through `handoff.session`. The session reports at reap on stderr, so capture it
  as the existing session tests do. For (a): "Newest entries on top" appears only at
  `act-log.md.jinja:7` on `origin/main` (checked with `git grep` during Plan), and no test pins it.
  The render suite (`tests/` at the target root) renders the header, so run it as a smoke check.
- **Prior-art check (triage cycles):** by path,
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/handoff.py template/process/act-log.md.jinja`:
  e9e5982 (#534, session/reap rework; `check_act` unchanged), 900d638 (#331, introduced the
  baseline and the suffix check); the act-log template last changed in e991a71 and 983463b
  (unrelated to ordering). Closed-unmerged PRs touching `handoff.py`, `test_handoff.py`,
  `act-log.md.jinja`: none. Open PRs: none.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
