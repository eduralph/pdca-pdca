# Advisory code review — issue 589 (flow-dep-graph-refusal-not-traceback)

No correctness bugs found. The catch at `template/src/pdca_harness/cli.py:661` handles
only the new `waves.DependencyGraphError` subtype, so other `ValueError`s still propagate,
and `pdca waves` (`cli.py:1038-1041`, `except ValueError`) keeps working because the new
class subclasses `ValueError` (`waves.py:51`). `waves` was already imported in `cli.py`
(line 22), so no import was needed. The only strict call site is `flow.py:1694`, and it
runs before any wave builds, so the "no bundle was built" text is accurate. The tolerant
re-levelling (`flow.py:1142`) runs `partition_schedulable` first, so it never reaches the
new raise. C4 log shows 3 red / 1 green (by design) pre-fix and green post-fix.

Small, optional points (none block):

- `template/src/pdca_harness/waves.py:96-98` — the unresolved-dependency remedy says
  "if it landed outside the cycle". Here "cycle" means the PDCA cycle, but this text is
  printed next to errors that say "dependency cycle", so an operator could read it as a
  dependency cycle. Wording like "if it was fixed outside pdca" would be clearer. Cosmetic.
- `template/tests/test_flow_dependency_refusal.py:109` — `assertNotIn("Traceback", err)`
  can never fail. `redirect_stderr` only captures what is printed, and an uncaught
  exception goes to the test runner, not into `err`. The real guard is `_call`
  (`:113-119`), which turns a raised `ValueError` into a failure. This is harmless, but
  the line gives a false sense of coverage. It could be dropped or commented.
- `template/src/pdca_harness/waves.py:61-63, 96-98, 113-114` — the "ways out" text sits
  in the scheduling module as a `remedy` attribute, while the CLI adds the framing
  (`cli.py:665-666`). That is a fair split and matches `why.remedy` in `drive_claim`
  (`cli.py:613`), so there is no reuse gap. Noted only because `pdca waves`
  (`cli.py:1040`) does not print the remedy. The brief leaves that out of scope, so no
  change is needed.
