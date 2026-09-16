"""Leaf resilience (issues #138, #506) — stdlib unittest, no deps.

A Check reviewer/advisory leaf that exits non-zero used to collapse to an opaque §6
placeholder whose only diagnostic was the exit code, and a transient `claude -p`
blip (usage/rate limit, 5xx) wedged sign-off the same as a substantive failure.
`_invoke_leaf_resilient` now: (1) persists the failed attempts' stderr tail to an
error log, (2) retries a *transient* (no-output) failure with backoff before
degrading, and (3) classifies the placeholder transient-vs-substantive.

#506 makes **an attempt the unit of accountability** for every leaf the harness
spawns: the *builder* runs under the same wrapper (it was the only leaf never
retried), each attempt's record is flushed before the next attempt starts, a retried
builder is told its predecessor died mid-flight and that any artifact present is that
attempt's residue, an exhausted retry says so and names a next action true for the
residue actually on disk, and no artifact a dead attempt left behind is harvested as a
live one's output. Run with:
    PYTHONPATH=src python -m unittest discover -s tests
"""

from __future__ import annotations

import io
import os
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import leaves, state
from pdca_harness.config import Config, LeafConfig

# A claude-family leaf so the stream path engages (that is the only path that yields
# the "did a session start" signal). argv is a python interpreter running an inline
# script; `_invoke` appends --output-format/--verbose (ignored) and feeds the prompt
# on stdin. The script counts its own invocations into $CNT so a test can assert the
# retry count.
_TRANSIENT = (  # dies at invocation: only stderr, no stdout → no session started
    "import os,sys; open(os.environ['CNT'],'a').write('x'); "
    "sys.stderr.write('overloaded_error 529\\n'); sys.exit(1)"
)
_SUBSTANTIVE = (  # ran (emitted a stream event on stdout) then failed
    "import os,sys; open(os.environ['CNT'],'a').write('x'); "
    "print('{\"type\": \"assistant\"}'); sys.stderr.write('boom\\n'); sys.exit(1)"
)


_REAL_SLEEP = time.sleep


def _skip_backoff(seconds: float) -> None:
    """Stand-in for `time.sleep` that skips only the retry BACKOFF (≥ 1s, #506), so a case
    driving `do_build` to its attempt budget costs no wall clock — without weakening the
    wrapper's shipped defaults, and without turning `run_with_heartbeat`'s own sub-second
    polls into a busy-wait."""
    if seconds < 1:
        _REAL_SLEEP(seconds)


def _leaf(script: str) -> LeafConfig:
    return LeafConfig(mode="command", family="claude",
                      argv=[sys.executable, "-c", script], interactive=False)


class LeafResilience(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cnt = self.tmp / "count.txt"
        self.error_log = self.tmp / "check-review.error.log"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _runs(self) -> int:
        return len(self.cnt.read_text()) if self.cnt.exists() else 0

    def test_transient_failure_retries_then_persists_classified(self) -> None:
        err = leaves._invoke_leaf_resilient(
            _leaf(_TRANSIENT), self.tmp, "review please",
            error_log=self.error_log, attempts=3, backoff=0.0,
            stream_json=True, env={"CNT": str(self.cnt)})
        self.assertIsInstance(err, leaves.LeafError)
        self.assertTrue(err.transient)            # no stdout → transient infra signal
        self.assertEqual(self._runs(), 3)         # retried up to the attempt budget
        self.assertTrue(self.error_log.exists())  # recoverable error text persisted
        self.assertIn("overloaded_error 529", self.error_log.read_text())

    def test_substantive_failure_is_not_retried(self) -> None:
        err = leaves._invoke_leaf_resilient(
            _leaf(_SUBSTANTIVE), self.tmp, "review please",
            error_log=self.error_log, attempts=3, backoff=0.0,
            stream_json=True, env={"CNT": str(self.cnt)})
        self.assertIsInstance(err, leaves.LeafError)
        self.assertFalse(err.transient)   # emitted a session event → substantive
        self.assertEqual(self._runs(), 1)  # no retry for a non-transient failure
        self.assertIn("boom", self.error_log.read_text())

    def test_success_leaves_no_error_log(self) -> None:
        ok = _leaf("import os; open(os.environ['CNT'],'a').write('x'); print('{}')")
        err = leaves._invoke_leaf_resilient(
            ok, self.tmp, "review please", error_log=self.error_log,
            attempts=3, backoff=0.0, stream_json=True, env={"CNT": str(self.cnt)})
        self.assertIsNone(err)
        self.assertEqual(self._runs(), 1)
        self.assertFalse(self.error_log.exists())

    def test_stale_error_log_cleared_on_success(self) -> None:
        self.error_log.write_text("stale tail from a prior cycle")
        ok = _leaf("print('{}')")
        leaves._invoke_leaf_resilient(
            ok, self.tmp, "review please", error_log=self.error_log,
            attempts=3, backoff=0.0, stream_json=True, env={"CNT": str(self.cnt)})
        self.assertFalse(self.error_log.exists())

    def test_placeholder_classification_transient_vs_substantive(self) -> None:
        leaves._review_unavailable(self.tmp, "reviewer leaf failed: x",
                                   failure=leaves._FAIL_TRANSIENT, error_log=self.error_log)
        txt = (self.tmp / "check-review.md").read_text()
        self.assertIn("transient infra", txt)
        self.assertIn("NEEDS-HUMAN", txt)

        leaves._review_unavailable(self.tmp, "reviewer produced no check-review.md")
        txt = (self.tmp / "check-review.md").read_text()
        self.assertIn("substantive", txt)


# ---------------------------------------------------------------------------------
# #506 — the builder is a leaf too, and an attempt is the unit of accountability.
# ---------------------------------------------------------------------------------

#: A builder that dies transiently (stderr only, no stream event → `produced is False`),
#: instrumented from the inside: it counts its invocations in $CNT, saves the prompt it was
#: given and the CONTENT OF $ERRLOG AT THAT MOMENT under $PROBE, and — when $RESIDUE names a
#: path — leaves a partial artifact behind, the way a builder that wrote patch.diff and then
#: lost its API connection does.
_DYING_BUILDER = (
    "import os, sys; "
    "cnt = os.environ['CNT']; "
    "n = len(open(cnt).read()) + 1 if os.path.exists(cnt) else 1; "
    "open(cnt, 'a').write('x'); "
    "probe = os.environ['PROBE']; "
    "open(os.path.join(probe, 'prompt%d' % n), 'w').write(sys.stdin.read()); "
    "log = os.environ['ERRLOG']; "
    "open(os.path.join(probe, 'errlog%d' % n), 'w')"
    ".write(open(log).read() if os.path.exists(log) else '(absent)'); "
    "res = os.environ.get('RESIDUE'); "
    "open(res, 'w').write('--- a/half\\n') if res else None; "
    "sys.stderr.write('overloaded_error 529\\n'); "
    "sys.exit(1)"
)

#: Same counter, but it emits a stream event first: it RAN and then failed on the merits.
_SUBSTANTIVE_BUILDER = (
    "import os, sys; "
    "open(os.environ['CNT'], 'a').write('x'); sys.stdin.read(); "
    "print('{\"type\": \"assistant\"}'); "
    "sys.stderr.write('the brief contradicts itself\\n'); sys.exit(1)"
)

#: Dies transiently on attempt 1, then builds on attempt 2 (writes $RESIDUE, exits 0).
_FLAKY_BUILDER = (
    "import os, sys; "
    "cnt = os.environ['CNT']; "
    "n = len(open(cnt).read()) + 1 if os.path.exists(cnt) else 1; "
    "open(cnt, 'a').write('x'); sys.stdin.read(); "
    "sys.stderr.write('overloaded_error 529\\n') if n == 1 else None; "
    "sys.exit(1) if n == 1 else None; "
    "open(os.environ['RESIDUE'], 'w').write('--- a/whole\\n'); "
    "print('{\"type\": \"result\"}')"
)


def _build_cfg(root: Path, script: str) -> Config:
    """A claude-family COMMAND builder that is a Python interpreter (so the stream path —
    the one that yields the transient signal — engages), editing in place (no git)."""
    return Config(
        root=root,
        bundle_root=root / "results",
        process_dir=root / "process",
        templates_dir=root / "templates",
        default_branch="main",
        tracker_system="github",
        tracker_url="",
        issue_id_example="#1",
        builder=LeafConfig(mode="command", family="claude",
                           argv=[sys.executable, "-c", script], interactive=False),
        reviewer=LeafConfig(mode="stub", family="codex"),
        worktree=False,
    )


class BuilderRetriesLikeEveryOtherLeaf(unittest.TestCase):
    """#506 (i)/(ii)/(iii)/(iv). `_do_build_command` called plain `_invoke`, so the ONE leaf
    the harness never retried was the most expensive one to lose. These drive the real
    `do_build` → `_invoke_leaf_resilient` → `progress` → `subprocess` path with a builder
    that is a Python interpreter; only `time.sleep` is patched, so the shipped attempt /
    backoff defaults are exercised as they ship, without spending their wall clock."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.probe = self.tmp / "probe"
        self.probe.mkdir()
        self.cnt = self.tmp / "count.txt"
        self.cfg = _build_cfg(self.tmp, _DYING_BUILDER)
        self.d = self.cfg.bundle("506")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text("- **Slug:** attempt-accountability\n",
                                         encoding="utf-8")
        self.log = self.d / leaves.BUILD_ERROR_LOG
        slept = mock.patch.object(leaves.time, "sleep",  # the backoff, minus its wall clock
                                  side_effect=_skip_backoff)
        slept.start()
        self.addCleanup(slept.stop)
        environ = mock.patch.dict(os.environ, {
            "CNT": str(self.cnt), "PROBE": str(self.probe), "ERRLOG": str(self.log)})
        environ.start()
        self.addCleanup(environ.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _runs(self) -> int:
        return len(self.cnt.read_text()) if self.cnt.exists() else 0

    def _probe(self, name: str) -> str:
        path = self.probe / name
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def _failing_build(self) -> str:
        """Run Do to its final failure; return what the operator saw on stderr."""
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            with self.assertRaises(leaves.LeafError):  # still re-raised for flow._isolate
                leaves.do_build(self.d, self.cfg)
        return err.getvalue()

    def test_a_transient_builder_death_is_retried_to_the_attempt_budget(self) -> None:
        out = self._failing_build()
        self.assertEqual(self._runs(), 3)  # the wrapper's shipped budget, not 1
        self.assertIn("retry 1/2 in 4s", out)  # …with the shipped backoff between attempts
        self.assertIn("retry 2/2 in 8s", out)
        self.assertIn(f"Do {self.d.name}", out)  # named by the bundle it belongs to
        text = self.log.read_text(encoding="utf-8")
        self.assertEqual(text.count("overloaded_error 529"), 3)  # every attempt accounted
        self.assertIn("attempt 3", text)

    def test_a_substantive_builder_failure_is_still_not_retried(self) -> None:
        self.cfg.builder = LeafConfig(mode="command", family="claude", argv=[
            sys.executable, "-c", _SUBSTANTIVE_BUILDER], interactive=False)
        out = self._failing_build()
        self.assertEqual(self._runs(), 1)  # it read the brief and failed on the merits
        self.assertNotIn("retry", out)     # …so nothing is retried, exactly as today
        self.assertIn("the brief contradicts itself",
                      self.log.read_text(encoding="utf-8"))
        self.assertNotIn("TRANSIENT", out)  # nor is it reported as infra

    def test_a_recovered_build_is_reported_exactly_as_a_clean_one(self) -> None:
        # The retry that works must leave the bundle indistinguishable from a build that
        # never failed: patch.diff present, no error log, nothing raised.
        self.cfg.builder = LeafConfig(mode="command", family="claude", argv=[
            sys.executable, "-c", _FLAKY_BUILDER], interactive=False)
        with mock.patch.dict(os.environ, {"RESIDUE": str(self.d / "patch.diff")}), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves.do_build(self.d, self.cfg)  # must NOT raise
        self.assertEqual(self._runs(), 2)
        self.assertTrue((self.d / "patch.diff").exists())
        self.assertFalse(self.log.exists(), "a leaf that worked leaves no error log")

    def test_each_attempts_account_is_on_disk_before_the_next_one_starts(self) -> None:
        # (ii) Read from INSIDE the child: what did build.error.log hold while attempt 2
        # ran? Written only after the loop, the answer is "nothing" — and the retry note
        # that points the retried builder at that file would be a false instruction.
        self._failing_build()
        self.assertEqual(self._probe("errlog1"), "(absent)")  # nothing failed yet
        during_2 = self._probe("errlog2")
        self.assertIn("attempt 1", during_2)
        self.assertIn("overloaded_error 529", during_2)
        self.assertIn("attempt 2", self._probe("errlog3"))

    def test_the_retried_builder_is_told_it_is_looking_at_a_dead_attempts_residue(self) -> None:
        # (iii) `worktree.ensure` ran once, before the wrapper: attempt 2 opens a tree
        # still carrying attempt 1's edits and a bundle that may already hold patch.diff.
        self._failing_build()
        first, second = self._probe("prompt1"), self._probe("prompt2")
        self.assertNotIn("RETRY NOTICE", first)   # attempt 1's prompt is unchanged
        self.assertIn("You are the Do builder", first)
        self.assertIn("You are the Do builder", second)  # …and still the whole task
        for expected in ("RETRY NOTICE", "died MID-FLIGHT", "INCOMPLETE RESIDUE",
                         "patch.diff", leaves.BUILD_ERROR_LOG):
            self.assertIn(expected, second)
        self.assertIn("RETRY NOTICE", self._probe("prompt3"))

    def test_the_exhausted_report_is_true_for_the_residue_actually_left(self) -> None:
        # (iv) The builder wrote a partial patch.diff and then died: the bundle now reads
        # BUILT, so a plain re-run would run CHECK on that partial patch, not Do. Saying
        # "just re-run Do" there would be false — and nothing may delete the patch to make
        # the simpler sentence true.
        with mock.patch.dict(os.environ, {"RESIDUE": str(self.d / "patch.diff")}):
            out = self._failing_build()
        self.assertIn("TRANSIENT", out)                 # the class of failure, named
        self.assertIn(leaves.BUILD_ERROR_LOG, out)      # where its account is
        self.assertIn("BUILT", out)                     # what the residue did to the bundle
        self.assertIn("CHECK", out)                     # what a plain re-run would do
        self.assertIn("iterate-do", out)                # a next action that actually works
        self.assertTrue((self.d / "patch.diff").exists(),
                        "the report describes the bundle; it never edits it")
        # …and the claim is TRUE of the real state machine, not just a nice sentence.
        self.assertEqual(state.state(self.d), state.BUILT)

    def test_the_exhausted_report_sends_a_bundle_with_no_patch_back_to_do(self) -> None:
        out = self._failing_build()  # no $RESIDUE — the leaf died before writing anything
        self.assertIn("TRANSIENT", out)
        self.assertIn("PLANNED", out)
        self.assertIn("re-drives Do", out)
        self.assertNotIn("would run CHECK", out)  # the BUILT sentence would be false here
        self.assertEqual(state.state(self.d), state.PLANNED)


class DeadAttemptOutputIsNeverHarvested(unittest.TestCase):
    """#506 (v). The three harvest sites copy their artifact `if produced.exists()`, with no
    notion of WHICH attempt wrote it — so a truncated verdict a dead attempt left in the
    sandbox is adopted as the output of the attempt that succeeded. Drives the real
    `_run_review_sandboxed` harvest; only the vendor spawn (`_invoke`) is stubbed."""

    TRUNCATED = "| Item | Verdict | Basis |\n| 1.1 Root cause | PA"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = _build_cfg(self.tmp, "")
        self.cfg.reviewer = LeafConfig(mode="command", family="claude", argv=["claude"])
        self.d = self.cfg.bundle("506")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text("- **Slug:** s\n", encoding="utf-8")
        (self.d / "patch.diff").write_text("--- a/x\n", encoding="utf-8")
        (self.d / "check-gates.json").write_text("{}\n", encoding="utf-8")
        slept = mock.patch.object(leaves.time, "sleep", side_effect=_skip_backoff)
        slept.start()
        self.addCleanup(slept.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_a_dead_attempts_half_written_verdict_is_not_adopted_as_the_reviews(self) -> None:
        calls: list[Path] = []

        def flaky(leaf, workdir, prompt, **kw):
            calls.append(Path(workdir))
            if len(calls) == 1:  # wrote half a verdict, then the connection dropped
                (Path(workdir) / "check-review.md").write_text(self.TRUNCATED,
                                                               encoding="utf-8")
                raise leaves.LeafError(1, ["claude"], output="connection reset by peer")
            # attempt 2 comes back alive but writes nothing — nothing reviewed the diff

        with mock.patch.object(leaves, "_invoke", side_effect=flaky), \
                redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)

        self.assertEqual(len(calls), 2)  # the transient death was retried, as before
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertNotIn("1.1 Root cause | PA", review)  # the dead attempt's file, refused
        self.assertIn("NOT COMPLETED", review)           # the honest verdict: none produced
        self.assertIn("NEEDS-HUMAN", review)

    def test_the_live_attempts_own_artifact_is_still_harvested(self) -> None:
        # The ownership check must not cost a leaf its own work: a retry that RE-writes the
        # artifact is harvested exactly as today.
        calls: list[Path] = []

        def flaky(leaf, workdir, prompt, **kw):
            calls.append(Path(workdir))
            (Path(workdir) / "check-review.md").write_text(
                self.TRUNCATED if len(calls) == 1 else "| Item | Verdict | Basis |\nfull\n",
                encoding="utf-8")
            if len(calls) == 1:
                raise leaves.LeafError(1, ["claude"], output="connection reset by peer")

        with mock.patch.object(leaves, "_invoke", side_effect=flaky), \
                redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertIn("full", review)
        self.assertNotIn("1.1 Root cause | PA", review)


if __name__ == "__main__":
    unittest.main()
