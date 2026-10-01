# Advisory code review — issue 409 (autoiterate-budgets-defer-ledger)

Lens: bugs the patch introduces, plus reuse/simplification. Advisory only. The gates pass (C4 red→green, T3 suite green). I found no blocking correctness bug. The tests for clauses 1–4 are present and are built to tell the wrong designs apart (`template/tests/test_autoiterate.py:944`, `:960`, `:988`, `:997`, `:1065`).

## Correctness

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/autoiterate.py:126`: in `_same_finding`, the containment test (`a in b or b in a`) skips `_MATCH_FLOOR`. A short ticked row can therefore match any ledger entry that contains it as a substring. Example: a human trims a row to a few words, or ticks a short unrelated row such as a gate line. In `retire_cleared` (`autoiterate.py:~310-316`), a single such hit retires the entry unless an open row protects it. That only happens when the entry's own row is no longer open verbatim (the human deleted or ticked it). So the risk is small, but it fails open, and the brief says "absence is not consent". Fix: apply the floor to containment too (require `min(len(a), len(b)) >= _MATCH_FLOOR` before the substring test). Then add one test with a short ticked row that is a substring of a deleted entry.
- `template/src/pdca_harness/autoiterate.py:233-235`: if `write_text` or `os.replace` fails, `_write_ledger` leaves `.deferred-findings.json.<pid>.tmp` in the bundle. The file is harmless (no reader globs it), but it is never cleaned up and is not archived. Low priority: a `try/finally` that unlinks the tmp file on failure would handle it.
- `template/src/pdca_harness/autoiterate.py:238-260` (`defer`): deduplication uses exact normalised text only, so a reviewer who rewords the same HUMAN concern each round adds one ledger entry per round. The handover §6 then has near-duplicate rows (at most `max_auto_iters` of them), and the human must tick each one. The brief chose this on purpose ("never deduplicated fuzzily"), so this is a note, not a defect.

## Reuse / simplification

- `template/src/pdca_harness/assemble.py:446` (`_deferred_needs_human`) rewrites `autoiterate._norm` inline (`" ".join(t.split()).casefold()`), even though the function already imports `autoiterate` locally. Calling `autoiterate._norm` keeps defer-time and assembly-time dedup on one definition, so they cannot drift.
- `template/src/pdca_harness/signoff.py:159-166` (`ensure_needs_human_item`) repeats the checkbox list and normalisation from `autoiterate._BOXES` / `_row_text`. `signoff` cannot import `autoiterate` (that would be an import cycle). The cleaner direction is to move `_norm`/`_row_text` into `signoff` and have `autoiterate` import them from there. Cosmetic.
- `template/src/pdca_harness/flow.py:216-230`: `_hold_unreadable_ledger` parses the ledger on every accept, even when auto-iterate never ran. `deferred()` returns early when the file is absent, so the cost is one `exists()` call. No action needed.

Nothing else found on either lens. Two things I checked and found correct: retirement runs in both iterate branches in `driver.py`, and `_hold_unreadable_ledger` runs before the C6 check in `_apply_decision`.
