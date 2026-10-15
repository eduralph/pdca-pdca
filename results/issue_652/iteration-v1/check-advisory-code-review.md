# Advisory code review — issue_652

I found no correctness bug in the patch. The cascade (`_cascade_not_clean`, a loop that spreads "not clean" from a finished id to the finished ids that name it in `Depends on`) is right for the cases in the brief:

- It runs after the `bad` line check and the per-id judgement, and before the fold (`template/src/pdca_harness/flow.py:962`). So a cascaded id never reaches `_fold_lines`.
- The loop stops when nothing new is marked. That means chains of any length work, and a cycle cannot make it loop forever (`flow.py:888-896`).
- An id that already has its own reason keeps it and is not relabelled `built_on` (`flow.py:892`).
- The new hint gets `cause=` filled in. Older hints ignore the extra keyword, so `str.format` does not break them (`flow.py:987-989`).

The C4 log shows the three new tests red without the fix (`issue_D` built on a line carrying Q and R) and green with it. T3 passes: 2372 tests OK.

Findings, all minor:

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:963`: there is a typo, `clean =[d for d in ids ...]`, with the space missing after `=`. The line before the patch was `clean = [...]`. Restore the space.
- NEEDS-HUMAN [impl] — `template/tests/test_flow_resume_stack_prereqs.py` (new `_not_on_the_line` helper and its callers in the three new tests): every finished id in these tests is held, so nothing is folded before wave 0, and `_not_on_the_line` probably passes only because no line exists. The brief allows "if a line exists at all", and the `self.seen` / `_held` checks are the real RED. Still, no test covers a mixed target, where a clean, unrelated finished id IS carried while P and Q are held, so the line exists and has to leave out P's commit. Adding one more finished id (say `X`, OPEN, with a planned dependent) to the clause-1 test would make that check meaningful and test the "the rest is still carried" half of the invariant.
- `template/src/pdca_harness/flow.py:879-883` (simplification, no action needed): `_cascade_not_clean` reads each finished id's brief to build its `Depends on` list. `_carry_finished` already does the same read for drive-set bundles (`flow.py:927-931`). The two loops could share one small "plain Depends-on names in this set" helper. That is cosmetic, and the cost is trivial (a few brief reads per target).
- `template/src/pdca_harness/flow.py:871-896` (style, no action needed): the function both changes `why` in place and returns `causes`. The docstring says so, so the side effect is documented. Storing the cause in the `why` tuple would avoid a second dict, but it would also change the tuple shape that the "open"/"edge"/"line" paths share. The current choice is reasonable.

Out of scope and not filed, as the brief says: the fold-time skip case (`flow.py:974-975`), a cascade across different targets (the edges only cover `ids` of the same target), and prerequisites that are not requested ids.

<!-- pdca:leaf-complete -->
