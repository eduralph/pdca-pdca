# Result — issue 528 / act-log-append-only-and-the-check-enforces-it

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The template gives three different rules for where a new act-log entry goes, and the
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
- Success criterion: (a) The template's act-log header no longer says "Newest entries on
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
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Make "append at the end" the single act-log rule: correct the template header, and
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

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — patch adds no new test file — nothing to assert

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review issue #528: make Act-log entries append at the end and reject changes to session-start text or handoffs naming older entries.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The chosen append-only rule has falsifiable session-level acceptance cases and preserves existing history; `brief.md:21`, `target/template/process/act-log.md.jinja:3`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production/header fix while retaining regression tests produced three assertion failures, including acceptance of edited history; `reviewer-red.log:3`, `target/template/tests/test_handoff.py:363`. |
| C3 Change | PASS | The three affected files address the stated inconsistency without changing the writer or reordering existing logs; the header agrees with the append writer and role contract; `target/template/process/act-log.md.jinja:7`, `target/template/src/pdca_harness/act.py:664`, `target/template/agents/act.md.jinja:16`. |
| C4 Verification (red→green) | PASS | Restoring the fix changed the same 41-test selection from three failures to all passing; real session checks also rejected deletion and a prepended log naming the old date; `reviewer-red.log:30`, `reviewer-green.log:3`, `target/template/tests/test_handoff.py:325`. |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether the legacy-baseline fallback is necessary or the original-prefix cause should also be removed there using the saved length/hash — current sessions always capture full text, but the fallback still accepts both original corruption cases; `target/template/src/pdca_harness/handoff.py:235`, `target/template/src/pdca_harness/handoff.py:433`. |
| T1 Structure | PASS | Baseline capture and validation remain in the existing session/exit-contract module; the insertion classifier only selects rejection diagnostics and cannot authorize a changed prefix; `target/template/src/pdca_harness/handoff.py:251`, `target/template/src/pdca_harness/handoff.py:425`. |
| T2 Shape | PASS | Independent diff whitespace check, documentation lint, site render and internal-link audit passed; frozen docs and host-CI logs corroborate the checks; `gate-logs/T2-docs.log:11`, `gate-logs/host-ci-docs.log:11`. |
| T3 Runtime | PASS | Independent offline suite passed 1,900 tests (two skips), and Copier render smoke tests passed; release-update coverage rests on the frozen successful run because the supplied target has no release tags; `reviewer-driver.log:1656`, `reviewer-root-copier.log:5`, `gate-logs/T3-suite.log:41`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent at Check; their substantive audit must rerun at publish; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm the affected-path prior-art conclusion, including closed/rejected work — the brief records the search, but independent local history contains only a synthetic base commit and no remote, so duplicate or rejected approaches cannot be excluded here; `brief.md:95`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Accept the end-append workflow for existing instances whose historical entries remain newest-first — automated checks establish enforcement, while operational suitability and the intentionally unmigrated history require sign-off; `brief.md:69`, `target/template/process/act-log.md.jinja:7`. |

Independent evidence and limitations:

- Red→green command: from `target/template`, run `PYTHONPATH=src python3 -m unittest discover -s tests -p test_handoff.py`, first with only the production/header changes stashed, then after `git stash pop`. The original patch was restored; no source changes were made by this review.
- Additional real-session checks observed append → exit 0; prepend and name old date → exit 1; delete old text then append → exit 1; edit old text then append → exit 1.
- C5 concerns compatibility, not a failure of the brief's newly captured-session cases. Independently calling `check_act` with the old `{act_log_len, act_log_sha}` baseline returned `[]` (accept) for both prepend/name-old and edit-old/append-new. The new missing-field guard preserves that weakness. This is not an eager/load-time capability problem; the corresponding causal alternative is to verify the old prefix against its stored hash rather than bypass prefix integrity when full text is absent. Existing direct-baseline tests are at `target/template/tests/test_handoff.py:283`.
- The C5 scanner's frozen output only says there is no new test file (`gate-logs/C5-prod-path.log:10`); it is not evidence that it audited the added test methods. Reading and running those methods independently confirmed calls through production `handoff.session` and `handoff.run_check` (`target/template/tests/test_handoff.py:312`).
- The default Python could not import Copier. Re-running with the actual installed Copier environment exercised rendering successfully (`reviewer-root-copier.log:1`); update compatibility skipped because the disposable checkout lacks release tags. The frozen T3 log explicitly shows five update-compatibility tests passing (`gate-logs/T3-suite.log:41`) and 24 root tests passing (`gate-logs/T3-suite.log:54`). This is a local evidence limitation, not an unmet build dependency or a patch defect.
- The prior-art investigation used `git log --all --oneline --` with all three affected paths and `git remote -v`: only `ac6aa45` (synthetic pre-fix base) was available and no remotes were configured. The brief records merged history by production/header paths and closed-unmerged searches across all three paths, but no independent closed/rejected-work evidence is supplied.
- The available integration template has no enumerated additional human-only items; its field remains a placeholder (`target/template/docs/INTEGRATION.md.jinja:80`). No stale-target or missing-gate-log caveat was found.

### Advisory — code-review

# Check — advisory code review (issue #528)

Scope: `template/process/act-log.md.jinja`, `template/src/pdca_harness/handoff.py`,
`template/tests/test_handoff.py` (this diff only).

## Correctness

No bugs found in the patch.

- `_is_pure_insertion` (`handoff.py:183-207`) — checked the math directly: bounding
  `lcs` to `remaining = len(baseline) - lcp` means `lcp + lcs` can never exceed
  `len(baseline)`, so hitting `lcp + lcs == len(baseline)` is not a heuristic — it
  proves `baseline[:lcp]` and `baseline[lcp:]` tile the whole of `baseline` with no
  gap or overlap, which means `text` really is `baseline` with one contiguous block
  spliced in at position `lcp`. Ran it against prepend / mid-splice / append /
  no-common-content / an edit-plus-append case by hand (`_is_pure_insertion("ab",
  "aXbY")` correctly returns `False` — two separate insertion points, not one
  contiguous block) — all matched the documented contract.
- `prev_text = baseline.get("act_log_text")` is checked with `is None`
  (`handoff.py:235`), not truthiness, so a session that starts from an empty
  act-log (`act_log_text == ""`) still takes the new full-text branch instead of
  silently falling back to the legacy len/sha path. Easy off-by-one to get wrong
  here; it wasn't.
- Branch order in `check_act` (`handoff.py:248-262`: unchanged → pure-append →
  pure-insertion-elsewhere → edited/removed) matches the four cases in the brief,
  and the case-(d) test (`test_handoff.py:365-378`, edit an existing entry's text
  *and* append a correct new one at the end) lands on the "append-only" message,
  not the "appended at the end" message, confirming the branches don't collide.
  C4's red leg (`gate-logs/C4-verify.log`) shows this test and the two
  insertion-shape tests genuinely failing pre-fix and passing post-fix — the new
  tests exercise the change, not a tautology.
- Backward compatibility: the legacy len/sha-only baseline path
  (`handoff.py:235-247`) is kept and still exercised by the pre-existing
  `ActContract` tests (`test_handoff.py:283-296` etc., built with hand-rolled
  `{"act_log_len", "act_log_sha"}` dicts, no `act_log_text` key) — C4's green leg
  reports all 41 tests passing, so the brief's "existing tests stay green without
  edits" criterion holds.
- Full suite (`gate-logs/T3-suite.log`): 1900 tests, OK. Docs/host-CI gates clean.

## Reuse / simplification / efficiency

Nothing to flag. `_is_pure_insertion` is new logic with no existing helper in the
codebase it duplicates (checked for `difflib`/`SequenceMatcher` use elsewhere — none).
The hand-rolled prefix/suffix scan is also the cheaper choice here versus
`difflib.SequenceMatcher` (linear vs. worst-case quadratic) for a file that can grow
to four-figure line counts per the brief's own account of a real instance's log — a
reasonable, not premature, efficiency choice for this hot(ish) content size, even
though `check_act` itself runs once per `/handoff`, not in a loop.

The one thing worth naming without treating it as a defect: `session()`
(`handoff.py:433-434`) now writes the *entire* act-log text into the session's JSON
scratch file on disk at session start (previously just length + a sha). This is
the smallest baseline that can satisfy the fix's correctness requirement — checking
"was old text preserved intact" cannot be done from a hash alone — and the file is
transient (state-prefixed, `unlink`ed on reap), so the cost is one extra text-sized
disk write per interactive Act session, not a hot path. Not flagging as a finding.

## Verdict

Diff is clean on both lenses. No NEEDS-HUMAN items from this leaf.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Decide whether the legacy-baseline fallback is necessary or the original-prefix cause should also be removed there using the saved length/hash — current sessions always capture full text, but the fallback still accepts both original corruption cases; `target/template/src/pdca_harness/handoff.py:235`, `target/template/src/pdca_harness/handoff.py:433`.
- [x] T5 Judgment — Confirm the affected-path prior-art conclusion, including closed/rejected work — the brief records the search, but independent local history contains only a synthetic base commit and no remote, so duplicate or rejected approaches cannot be excluded here; `brief.md:95`.
- [x] Validation — fitness-to-purpose — Accept the end-append workflow for existing instances whose historical entries remain newest-first — automated checks establish enforcement, while operational suitability and the intentionally unmigrated history require sign-off; `brief.md:69`, `target/template/process/act-log.md.jinja:7`.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-09-18

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
