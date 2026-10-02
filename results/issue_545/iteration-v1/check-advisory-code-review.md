# Advisory code review — issue 545 (split parent close + split depth bound)

No correctness bug found. I checked the close rule, the depth refusal, the `--force` plumbing and the new tests against the target source. What follows is small cleanups and test nits; none of them needs a human decision.

## Correctness (checked, no defect found)

- `template/src/pdca_harness/cleanup.py:379-384` — the split-parent branch runs before the recorded-PR checks and the empty-patch close, as P9 and P7 require. `flow._is_split_parent` already requires a terminal state, and the added `st == state.COMPLETE` test keeps DISCONTINUED parents on today's path (Open question 5). No import cycle: `flow.py:29-31` does not import `cleanup`.
- `template/src/pdca_harness/cleanup.py:260-289` — every child ends up in exactly one of `still_open`, `unknown` or `reasons`, so `reasons[c]` in the `listed` join cannot raise a `KeyError`. The lambda captures function locals (not loop variables), so there is no late-binding bug. Unknown or non-numeric ids never act, which matches the fail-closed rule of `_issue_state` (`cleanup.py:76-91`).
- `template/src/pdca_harness/split.py:319-349` + `cli.py:814` — the depth check sits in `preflight`, which runs before any `gh issue create`. `split.accept` → `validate` (`split.py:885-910`) does not call `preflight` again, so `--force` is not lost on a second check. `getattr(args, "force", False)` keeps the roughly twenty bare-`SimpleNamespace` callers working. `_recorded_depth` (`split.py:665-681`) already turns damaged values, including `true`, into 0, so D4 holds without new code.

## Reuse / simplification

- `template/src/pdca_harness/cleanup.py:56` — `cleanup` now imports all of `flow` (which in turn loads `act`, `gates`, `integrate`, `lane`, `merge`, `waves`, …) only to call two private helpers, `flow._lineage_children` and `flow._is_split_parent` (`cleanup.py:246`, `:379`). The brief asked Do to reuse `_lineage_children`, so this is allowed. A later cleanup could move both helpers, plus `SPLIT_DISPOSITION` (`flow.py:852`), into `split.py`, next to `read_lineage`/`_recorded_depth`. Then `cleanup` would not reach into another module's private names or pull in the whole flow driver. Advisory only; not needed for this slice.
- `template/src/pdca_harness/cleanup.py:168-173,190` — pulling out `_bundle_comment` also removes the old double read of `tracker-comment.md`. Good reuse. Behaviour for ordinary bundles is unchanged (`prefer_bundle_comment` defaults to True).

## Nits

- `template/src/pdca_harness/cleanup.py:186` — the edited `_close_issue` docstring line is 120 characters, longer than the lines around it. Rewrap it.
- `template/src/pdca_harness/cleanup.py:275-277` — a child id that is not a number (e.g. a hand-edited record) is reported as "state unknown … (gh failed or not a tracker number)" on every run and can never resolve on its own. Unlike the empty-children line (`:248-251`), this message does not say "close by hand". Consider adding that for the non-numeric case.
- `template/tests/test_split_parent_lifecycle.py:830-834` — `test_d1_a_bare_namespace_without_force_is_refused_too` passes `force=False`, so the namespace is not bare. The real bare case is already covered by `test_d1_depth_two_or_more_is_refused_without_force` (`:818-828`, no `force` attribute). Rename the test (e.g. "explicit force=False is refused") or drop the kwarg.
- `template/tests/test_split_parent_lifecycle.py:743-752` (P8) — the test checks that the children are named but not that the hand-written note is kept. The code keeps it (`cleanup.py:285-286`). One more `assertIn("Hand-written closing note.", comment)` would lock that in. This is optional; the brief left the combining to Do.
