# Advisory code review — issue 672 (carry keeps a fold-time skip off the line)

Bottom line: I found no bug that lets a skipped id's commits reach the line, and no
double push. The restart loop (`integrate.py:535-594`) only runs when `skipped` is set.
So the in-run folds compute no work sets, as the brief requires. Each pass leaves out at
least one more bundle, so the loop ends. `_merge_published` has no output side effects,
so merging again on a restarted line is safe. The pushed tip is checked once, after the
loop. The gates agree: C4 is red before the fix (6 of 24 tests fail, including the new
cases) and green after it; T3 passes (2465 tests). Below are two test gaps and one
cause-wording nit.

- NEEDS-HUMAN [impl] — The hold spreads in more than one step (`_hold_work`, `template/src/pdca_harness/integrate.py:1031-1048`), but no test covers a second step: R holds only a commit that Q wrote, while Q is held for P's work. Without such a case, a change that drops `work[n] = _work(...)` at `integrate.py:1042` (the `work[n]` line) would still pass every test at `template/tests/test_flow_resume_stack_prereqs.py:520-623`. A test where R is `_finished_on("R", "Q")` and has no edge to P would pin it.
- NEEDS-HUMAN [impl] — No test covers a bundle that merged in the first pass and then fails on the restarted line (`integrate.py:592-594` restarts, and the next pass sends the failure to `new` again). That is the path where "each pass leaves out one more" and the later call to `_hold_work` both matter. Every new test restarts only once with no new failure. One case would cover it: a bundle that merges cleanly only on top of a bundle that is later held.
- NEEDS-HUMAN [impl] — `_built_on_skipped` (`integrate.py:1051-1070`) names a failed holder's cause only when the other failed id's *tip* is in its history (`tips[c] in mine`, `integrate.py:1064-1065`). The brief's invariant uses *any* of that id's work. Example: Q is cut from P's `p1`, P then adds a conflicting `p2`, and Q also conflicts on its own. Q's line then reports its own conflict, not "built on issue_P", although it holds `p1`. Nothing leaks (Q is off the line either way, and D is held). Using the tip breaks the tie when two failed ids share history, which is a fair reason. But this case is not one of the wording exemptions the brief allows ((ii)–(iv)), so either document it or check against `work[c]`, with the earlier-in-fold-order rule to break ties.
- `_work` (`integrate.py:1004-1005`) silently drops a head that the clone does not have, so that head's work set comes out empty. That would let a holder through. Today the risk is covered upstream: `_finished_head` (`flow.py:989-990`) refuses a PR head that does not resolve in the same checkout the fold's worktree shares objects with (`integrate.py:220`, `:1113-1116`), and branch tips come from the clone itself. No action needed, but the docstring's "a git failure raises" could say that a missing head counts as no work.
- On simpler code: `_hold_work` and `_built_on_skipped` both do the same "first earlier id in fold order whose commits are in my history" scan, but they test different things (any work vs. the tip), so I would not merge them. Using rev-list to build a set, instead of the existing `_in_line` / `_carries` helpers, is right here: the code needs the whole commit set, not a yes/no ancestry check. Recomputing `reach` once per pass (`integrate.py:1029`) costs one `git rev-list` per merged bundle per pass, which is fine for a carry.
- `flow.py:1121-1130`: clearing `holds` on an `IntegrationError` and then merging `holds` into `causes` is correct. Every key in `holds` also has an entry in `skipped`, so `skipped[name]` at `flow.py:1129` cannot raise `KeyError`.

<!-- pdca:leaf-complete -->
