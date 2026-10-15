# Advisory code review — issue 694 (round 4)

Overall: no correctness bug found that blocks this patch. The two points from earlier rounds that this lens can check are fixed. Partners are now judged after every pass, against the final `took` (`template/src/pdca_harness/integrate.py:635-652`). So a partner that comes later in the order, or one that is already on origin's line, gets named. A partner that a #672 hold takes back off is not named as carried. Criterion (2)'s test now asserts text that only the fix prints (`template/tests/test_flow_reissue_after_conflict_hold.py:536-537`). The C4 red leg shows all 22 tests failing without the fix (`gate-logs/C4-verify.log`). `_report_conflict_holds` now shares `_CONFLICT_STEP` with the carry hint (`template/src/pdca_harness/flow.py:1004-1005`, `:1268-1272`), so the two messages cannot drift apart. That is good reuse.

Minor findings. None of them needs a human.

- `template/src/pdca_harness/integrate.py:1150-1154`: `_merge_over` reads `git ls-files -u -z` with `text=True`. With `-z`, git prints paths as raw bytes with no quoting, so a conflicting file whose name is not valid UTF-8 raises `UnicodeDecodeError`. That error is not an `IntegrationError`, so `_clash` (`:1240-1243`) and the carry's `except integrate.IntegrationError` (`flow.py:1186`) both miss it, and the run crashes instead of falling back to `"line"`. The nearby `_merge` (`:1125`) uses `diff --name-only` without `-z`, which quotes such names, so this exposure is new. It is rare. A fix is to pass `errors="surrogateescape"` (and the same to `update-index`), or to catch the decode error and raise `IntegrationError`.
- `template/src/pdca_harness/integrate.py:1246-1271` and `:1274-1306` (efficiency, advisory only): for each conflicting id, `_partners` runs up to two full trials (checkout, merges, reset, checkout back) for every carried id in `took`. `_built_on` also runs one `merge-base --is-ancestor` per pair of tips. That is fine for the batch sizes the tests use. On a large re-issue with several conflicts it could be hundreds of git processes. A cheap filter would help: skip a candidate whose diff from the base touches none of the files the skipped branch changes. This is optional and only runs on the conflict path.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->
