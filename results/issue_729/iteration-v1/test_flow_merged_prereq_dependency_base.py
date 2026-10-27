"""A merged prerequisite is judged on the base the dependent is actually built on (#729).

In stack mode a dependent ``D`` of an out-of-batch prerequisite ``P`` — a ``Depends on
(merged): P``, or a plain ``Depends on: P`` the run was not asked for (#647) — waits until
``P``'s PR merges into ``D``'s own target base (``merged.merged_into``). Since #727 a ``D``
that only declares edges to bundles this run built is built on a base of its own
(``integrate.build_bundle_base``), built from the base as fetched when its wave starts. So
once ``P`` has merged, that base has the merge, even when the run's line, started before the
merge, does not: ``D`` is not held for the line (#655's check), and is built on a base that
holds ``P``'s merge commit. A ``P`` not merged into the base still holds ``D``. A ``D`` a
seam keeps on the line is still judged on the line: tests/test_flow_merged_prereq_on_line.py.

These cases drive ``flow._drive_and_act`` against real git through the helpers of
tests/test_flow_merged_prereq_on_line.py (the ``StackFoldGit`` fixture, the ``gh`` stub, the
stubbed build and publish leaves), loaded by path and used as a helper object, as that suite
uses ``StackFoldGit``. Only modules are imported (never a symbol the fix adds), so with the
production change reverted these cases still load and run — and fail on their assertions.
    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_merged_prereq_dependency_base
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from pdca_harness import state

_SPEC = importlib.util.spec_from_file_location(
    "merged_prereq_on_line_helpers",
    Path(__file__).with_name("test_flow_merged_prereq_on_line.py"))
ol = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(ol)


class MergedPrereqOnADependencyBase(unittest.TestCase):

    def setUp(self) -> None:
        self.h = ol.MergedPrereqOnTheLine()   # a helper object: its setUp, stubs and runs
        self.h.setUp()
        self.addCleanup(self.h.doCleanups)

    # -- (1) merged after the first fold: D is built on its own base, which has it --------

    def _built_on_its_own_base_with_the_merge(self, edge: str) -> None:
        h = self.h
        h._prereq()
        h.after_first_fold = h._merge          # P's PR merges into main after W's fold
        h._run(h._wd(edge), ["W", "D"])
        self.assertEqual(h.results["W"], state.COMPLETE, h.err)
        # The run's line was started before the merge and does not have it (#655's case) …
        self.assertFalse(h.fx._ancestor(h.merge_oid["P"], h.line))
        self.assertFalse(h.fx._ancestor(h.fx._tip("fix/P"), h.line))
        # … yet D is not held for it: it is COMPLETE, built on a base of its own (not the
        # line), and that base holds P's merge commit and W's branch.
        self.assertNotIn("does not have that merge", h.err)
        self.assertNotIn("is not known to have that merge", h.err)
        self.assertEqual([x for x in h.err.splitlines() if "issue_D held" in x], [], h.err)
        tip = h._built_on_line()               # D built; on its own base, as #727 builds it
        base, _tip = h.seen["issue_D"]
        self.assertEqual(base, f"{h.line}-bD", h.err)
        self.assertNotEqual(base, h.line)
        self.assertEqual(h.results["D"], state.COMPLETE)
        self.assertTrue(h.fx._ancestor(h.merge_oid["P"], tip))
        self.assertTrue(h.fx._ancestor(h.fx._tip("fix/W"), tip))

    def test_a_merge_after_the_first_fold_builds_a_depends_on_merged_dependent(self):
        self._built_on_its_own_base_with_the_merge(ol.MERGED_EDGE)

    def test_a_merge_after_the_first_fold_builds_a_plain_depends_on_dependent(self):
        # The #647 edge: a plain `Depends on: P`, P not in the batch.
        self._built_on_its_own_base_with_the_merge(ol.PLAIN_EDGE)

    # -- (2) not merged: still held (#647) ----------------------------------------------

    def _held_unmerged(self, edge: str) -> None:
        h = self.h
        h._prereq()                            # P's PR stays OPEN
        h._run(h._wd(edge), ["W", "D"])
        self.assertEqual(h.results["W"], state.COMPLETE, h.err)
        self.assertNotIn("issue_D", h.seen, h.err)
        self.assertEqual(h.results["D"], state.PLANNED)
        lines = [x for x in h.err.splitlines() if "issue_D held" in x and "issue_P" in x]
        self.assertEqual(len(lines), 1, h.err)
        self.assertIn("not merged into main", lines[0])

    def test_an_unmerged_depends_on_merged_prerequisite_still_holds_the_dependent(self):
        self._held_unmerged(ol.MERGED_EDGE)

    def test_an_unmerged_plain_depends_on_prerequisite_still_holds_the_dependent(self):
        self._held_unmerged(ol.PLAIN_EDGE)


if __name__ == "__main__":
    unittest.main()
