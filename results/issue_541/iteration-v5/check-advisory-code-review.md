# Advisory code review — issue #541 (lens: correctness + reuse/simplification)

No correctness bug found in this round's changes. All three carry-forward fixes from the v4 sign-off are in:

- Composition order: the completion instruction now comes after the rubric at the review site (`template/src/pdca_harness/leaves.py:3169-3171`, `_REVIEW_PROMPT + rubric + _COMPLETION_INSTRUCTION`) and the advisory site (`leaves.py:3423-3424`). It is already last at the plan-advisory site (`leaves.py:3641-3642`). The 4e leg now drives the real entry points with a rubric configured and asserts on the composed prompt read from the leaf's stdin (`template/tests/test_attempt_harvest.py:725-742`). That leg would have failed under the old order.
- The stale "neither … would be true" docstring is reworded (`leaves.py:3256-3262`).
- "cannot have closed itself" is softened in `assemble.leaf_status` (`template/src/pdca_harness/assemble.py:161-165`) and in the test module docstring (`test_attempt_harvest.py:31-34`). A grep of the tree finds no other copy of the phrase.

The reader-side guard is one anchored check at the head of the shared function (`assemble.py:168-172`). All three readers go through it (`assemble.py:247`, `size_signal.py:233`, `leaves.py:3730`), so no second classifier was added. The #526 note now goes above the trailer instead of after it (`leaves.py:4043-4047`), which fixes a real way a closed review could be "un-closed". A leg covers it (`test_attempt_harvest.py:626-645`).

Findings:

- NEEDS-HUMAN — The non-growth leg pins **four** status tokens (`infra-empty`, `startup-empty`, `sandbox-empty`, `human-empty`) at `template/tests/test_attempt_harvest.py:705-709`. The brief (criterion 4c and Repro 4c(ii)) says "exactly three" and leaves out `sandbox-empty`. The patch is right about the code: `LEAF_STATUS_SANDBOX` is already in the base (`assemble.py:119,126`, #526), and the patch neither adds nor removes it. So this is an error in the brief, not the patch. The comments at `assemble.py:107` and `leaves.py:3268` also say "four". A human should confirm that "closed at four" is what 4c meant, so nobody later "fixes" the test down to three by deleting `sandbox-empty`.
- Minor, no action needed: `_note_bash_unavailable` (`leaves.py:4043-4046`) rebuilds the text as `f"{above.rstrip()}\n\n{note}\n{closing}"`. If the artifact is only the trailer line, `above` is empty and the file starts with two blank lines. That's cosmetic, and the trailer stays last, so the classification is correct.
- Minor, no action needed: `_read_residue` (`leaves.py:1068-1072`) decodes each `readline(1000)` chunk separately, so a multi-byte UTF-8 character split across a 1000-byte boundary shows up as U+FFFD (the "replacement character" shown for undecodable bytes) in the quoted residue. Only the quoted copy in `*.error.log` is affected. The digest covers the raw bytes and is unaffected. This is baseline code the brief put out of scope, noted only for completeness.
- Minor naming nit: `_WITHDRAWN_TRAILER` (`leaves.py:786`, the closing line of a preserved error log) and `LEAF_COMPLETE_TRAILER` (`assemble.py:142`) both say "trailer" but have unrelated jobs, and only the second counts in classification. A different name for the first (for example `_WITHDRAWN_FOOTER`) would stop a future reader from thinking they are related. This is optional and does not change behaviour.

Gate evidence checked: `gate-logs/C4-verify.log` shows the red leg failing (13 failures, 5 errors) and ends `C4 PASS — red without the fix, green with it`. T3 suite passes. Nothing here blocks.
