## Summary
**User impact:** A review that a reviewer left half-written before it crashed could be
filed as the finished review of the attempt that ran after it, so a bundle reached sign-off
carrying a dead attempt's truncated text as its verdict and nothing told the human. Separately,
a perfectly good review that happened to *quote* one of the harness's "the reviewer did not
run" markers — which any review of the harness itself does — was treated as if the reviewer
had not run: its findings were relabelled, routed to the human instead of the builder, and
in the plan step thrown away.

This PR makes both decisions turn on who produced the file and whether they finished it,
not on what happens to be sitting at a path or mentioned in its text: a crashed attempt's
leftover is moved into the error log as that attempt's record before the next attempt runs,
and a reviewer now ends its report with a closing line that marks it complete.

Reported in [#541](https://github.com/eduralph/pdca-harness/issues/541).

## What to look at
Two things, both in `template/src/pdca_harness/`:

- **`leaves.py` — `_LeafHarvest`.** One class now owns the artifact path for all three
  places a retried reviewer's output is collected (Check reviewer, Check advisory, plan
  advisory). Read `withdraw` (what happens when an attempt dies) and `run` (what gets filed
  after the loop). The three call sites shrink to configuration of that class.
- **`assemble.py` — `leaf_status()`.** A four-line guard at the top: if the artifact's last
  non-blank line is `<!-- pdca:leaf-complete -->`, it is a real verdict, full stop. Everything
  after that guard is unchanged.

To try it offline, from `template/`:

```
PYTHONPATH=src python3 -m unittest tests.test_attempt_harvest
```

The suite's "leaf" is a Python interpreter that writes a partial file, dies on cue, and then
exits 0 on a later attempt, driven through the real site entry points. Revert the production
hunks and 14 of the 24 tests fail; with them, all pass.

## Root cause
The three harvest sites each ended in a hand-copied `if produced.exists(): copy2(...)`, and
every retry attempt runs in the same sandbox — so a file a dead attempt left behind was still
at the path when the next attempt exited 0, and nothing recorded which attempt wrote it.
`assemble.leaf_status()` had the same gap one level up: it decided "placeholder or real
verdict?" with an unanchored `_LEAF_STATUS_RE.search()` over the whole text, so a mention of
a marker anywhere counted as the artifact *being* a placeholder, and all three readers of that
answer (§6 assembly, the size signal, the plan-advisory finding count) acted on it.

## Fix
- **One owner for the artifact path.** `_LeafHarvest` (`leaves.py`) is passed into
  `_invoke_leaf_resilient` and is the only caller of it. As each attempt dies, `withdraw()`
  takes that attempt's file off the path and quotes it — bounded to 100 lines head and tail,
  since `*.error.log` is a tracked bundle file — into the attempt's record. On success,
  `run()` files what is at the path only if it is the live attempt's work: a leftover that
  could not be unlinked is settled by filesystem identity (`_residue_identity`) plus a digest,
  so a live attempt that wrote over it is still filed and only "the same file, unchanged" is
  refused. A refused path degrades to the site's usual placeholder, whose prose says the leaf
  exited 0 but nothing could be attributed to it; the dead attempts' records are put back in
  the error log rather than lost. The retry contract (three attempts) is unchanged.
- **A completion trailer decides realness; the status marker only explains why not.**
  `leaf_status()` returns `""` when the last non-blank line is `LEAF_COMPLETE_TRAILER`, then
  falls through to today's search. Absence of the trailer classifies nothing — an artifact
  without it behaves byte-for-byte as before, so third-party leaves, a leaf that forgets, and
  every existing bundle are unaffected.
- **Write sites.** The review, advisory and plan-advisory prompts get one closing instruction
  appended *after* the project rubric, so it is the last thing the leaf reads. The three
  offline stubs emit the trailer. The harness's placeholders never do. `_note_bash_unavailable`
  (#526) now inserts its note above a closing trailer instead of after it, so the note does
  not un-close a finished review.
- **No new status token.** The status table stays at its current four entries; the un-owned
  case reuses `human-empty` and carries its detail in the placeholder body. A test pins the
  table size.

## Verification
Line numbers are on `main` at `5daab65` before this patch unless marked "(patch)".

- **Claim:** No file written by a dead attempt is filed as a later attempt's output, at any of
  the three sites; the dead attempt's text is preserved in `*.error.log`.
  **Checked:** the bare existence tests at `template/src/pdca_harness/leaves.py:2788`,
  `:3138`, `:3580` are replaced by `_LeafHarvest.run`; `_invoke_leaf_resilient`
  (`leaves.py:680`) hands each death to `withdraw` before the stop rule.
  **Test:** `template/tests/test_attempt_harvest.py:280`
  (`test_no_site_files_a_dead_attempts_artifact_as_a_live_ones`, three sites), `:299`,
  `:309`, `:331` — red pre-fix, green post-fix.
- **Claim:** The live attempt's own artifact is filed exactly as today, including when it
  overwrote a leftover the harness could not remove; a leaf that exits 0 writing nothing still
  degrades to today's placeholder; the retry count stays at three.
  **Checked:** `_live_attempt_took_the_path` (patch) settles by identity and digest.
  **Test:** `test_attempt_harvest.py:350`, `:360` (guards, green pre-fix), `:372`, `:392`,
  `:408`, `:428`, `:444`, `:461` (red pre-fix, green post-fix).
- **Claim:** A closed artifact is a real verdict at all three readers even when it quotes a
  recognised status marker, inside a fenced block or as its second-to-last line.
  **Checked:** the readers all call the one classifier — `assemble.py:194`
  (`_items_from_artifact`), `size_signal.py:233` (`_review_drove_the_iterate`),
  `leaves.py:3304` (`_plan_findings`) — and the guard lands at `assemble.py:118-122`.
  **Test:** `test_attempt_harvest.py:574`, `:606`, `:626`, `:647` — red pre-fix (the base
  relabels the probe "leaf did not run", counts the round ambiguous, and reports 0 plan
  findings), green post-fix.
- **Claim:** Absence of the trailer changes no classification; the #278 placeholder contract
  holds (`[impl]` in a placeholder is still refused).
  **Checked:** `template/tests/test_leaf_status.py` is not in the patch and passes unmodified.
  **Test:** `test_attempt_harvest.py:666` (guard, green pre-fix by design).
- **Claim:** The placeholder for an un-attributable artifact never says "leaf did not run",
  and the status table does not grow.
  **Test:** `test_attempt_harvest.py:496` (red pre-fix), `:692` (guard).
- **Claim:** Every harness-authored prompt ends with the trailer instruction, after the rubric,
  and every stub emits the trailer; no placeholder does.
  **Test:** `test_attempt_harvest.py:711` — asserts on the prompt each real site actually
  piped to its leaf, with a non-empty rubric.
- **Suites.** From `template/`: the offline driver suite (1990 tests) and the root render /
  update-compat suite are green. `git diff --check` is clean. No docs are touched.

Known and accepted: an attempt that only touches an existing file's metadata (chmod/utime)
moves its identity and could let a leftover through. That is filed separately and is not
addressed here.

Fixes #541
