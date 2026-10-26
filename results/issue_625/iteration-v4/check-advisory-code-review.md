# Advisory code review — issue 625 (round 4)

Scope: `tools/live/stack_mode_live.py`, `tests/test_stack_mode_live_tool.py`, the `CONTRIBUTING.md` section. I checked the tool's calls into the driver against the target source: `flow.flow_ids` keywords (`template/src/pdca_harness/flow.py:3370-3382`), `cli._results_rc(results, holds=)` (`cli.py:707`), `signoff.record` (`signoff.py:255`), `publish.COMMIT_MSG` / `PR_BODY` / `_publish_record` / `read_stack_base_tip` (`publish.py:40-41,644,698`), every `Config` field the tool passes (all exist, and all required ones are given), and the `origin/<branch>` ref shape `_gone_and_merged` expects (`integrate.py:241`). The em-dash wording in the E3 regexes matches `integrate.py:1434-1435` and `:1509-1511` byte for byte. Gates: C4 is red without the tool and green with it (`gate-logs/C4-verify.log`), and the T3 suite is green.

I found no correctness bug the patch introduces, and nothing that needs a human. The three fixes carried forward from earlier rounds are in place:
- `_is_ancestor` returns None for git's exit 128 (`tools/live/stack_mode_live.py:284-291`).
- The branch delete is checked, with `ls-remote --exit-code` confirming it (`:470-492`).
- A run 2 that raises is INCOMPLETE and makes `run` exit 1 (`:413-429`, `:601-607`). The file-list poll stops on stability alone, never on the expected value (`:686-691`).

Minor notes. None of them block, and none needs a human:

- `tools/live/stack_mode_live.py:740-747` — E3 relies on regexes that copy the prose of `integrate.py:1434-1436` and `:1509-1511`. The offline test copies the same strings by hand (`tests/test_stack_mode_live_tool.py:66-70`), so if that wording ever changes, both stay green while a live E3 reads `"gone and merged": null`. That is a complete-observation FAIL that would be filed as a driver bug. The run 2 stderr in `observations.json` shows the real cause, so the risk is low. A cheap guard would be a test that compiles the tool's patterns against lines built from the `integrate.py` format strings.
- `tools/live/stack_mode_live.py:340-360`, `:686-691` — when a PR's file list really does not change after an event (for example, B already shows only `b.txt` before "Update branch"), `_files` polls for the full `--settle-max` window (180 s by default) before it records the list. The result is correct, only slow. The docstring at `:37-43` already says this.
- `tools/live/stack_mode_live.py:481-490` — on the failure path, the `for … else` loop sleeps once more after the last `ls-remote` try before it raises (up to 10 s). This is harmless and only costs time.
- The `run` path (`Live`, `:245-575`) has no offline test. The brief accepts this, because the live run at Validation is the only check of `setup`/`run`/`teardown` and is a hard sign-off condition. So none of the driver wiring above has actually run yet.

<!-- pdca:leaf-complete -->
