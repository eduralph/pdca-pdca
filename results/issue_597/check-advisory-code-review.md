# Advisory code review — issue 597 (flow-never-drives-a-briefless-bundle)

Lens: bugs the patch introduces, plus reuse / simplification. Grounded on the patched tree at `$PDCA_TARGET`.

**Verdict: no correctness bugs found.** The four carry-forward points from iteration 1 are all cleared:

- The dead `plan is None or` check is gone. `plan is None` now only returns True (`template/src/pdca_harness/flow.py:1025-1028`), and the lineage message fires only for an empty or missing lineage (`flow.py:1029-1036`).
- The SplitError text is cut down to its reason, with one flow-side remedy (`flow.py:1019-1024`).
- The sweep test now compares rc against a control (`template/tests/test_flow_briefless_split_parent.py:302-317`).
- Claim release is now tested on all three intake paths (`test_flow_briefless_split_parent.py:258-291`).

Reuse is right. The rebuild calls `split._parent_plan`, `split._split_parent_brief` and `flow._lineage_children` and copies none of their logic. The write uses the same `write_text(..., encoding="utf-8")` as `split.py:1007`, so the bytes match (and the test checks it). Every `_admit` call runs after the claim: `flow.py:1407` comes after `_refused_child`, `flow.py:2040` comes after `_claim_swept`, and named ids are claimed in `cli._flow`. `release` is safe to call twice (`drive_claim.py:229`), so the later `dropped` and `held` releases do not conflict with it.

Minor notes (none blocks; none needs a human):

- `template/src/pdca_harness/flow.py:1019` — the trim splits on the literal `" — refusing to split"`, which ties it to the wording in `split.py:813,829,833`. If that wording changes, the full `split --accept` text and its "re-run" remedy come back into flow output. `_assert_skipped` would catch this (`assertNotIn("refusing to split")`, `test_flow_briefless_split_parent.py:177-180`), so this is a coupling note, not a bug.
- `template/src/pdca_harness/flow.py:2040-2045` — when every swept bundle is skipped as briefless, `flow_batch` returns `{}`, so `pdca flow --from-csv` exits 0 even though it named bundles it would not drive. This matches the existing "could not claim" return just above it, and the brief only asks for a non-zero exit on the named-id path (`flow_ids`, #468). It is a known gap, not a regression.
- `template/src/pdca_harness/flow.py:1407` vs `:1422` — in adoption, the brief is rebuilt before `_reschedule`. If the reschedule then fails, the child keeps a newly written brief but is not driven this run. The write is the correct brief and happens under this run's claim, so it does no harm. The next run simply takes the "has brief.md" path.
