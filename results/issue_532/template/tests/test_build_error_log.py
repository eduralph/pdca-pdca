"""A failed Do builder leaves its error tail in the bundle (#279, secondary).

The reviewer / advisory leaves capture a failed leaf's stderr to `check-*.error.log`
(`_invoke_leaf_resilient`, #138), but the Do builder called `_invoke` directly — so a failed
Do left NO on-disk trace at all. Its stderr was only tee'd to the terminal, and a post-mortem
of a failed batch depended on terminal scrollback. `do_build` now captures the tail to
`build.error.log`, symmetric with the review leaves, and still re-raises so the flow's
`_isolate` drops just that bundle.

Since #506 the builder runs under `_invoke_leaf_resilient` like every other leaf, so this
file also pins what that does to the log's SHAPE: one record per attempt, written as each
attempt fails, and no log at all left behind by a build a retry recovered.

Production path exercised: `leaves.do_build` → `_do_build_command` → the real
`_invoke_leaf_resilient` retry loop and the real `do_build` capture. The classes below
differ only in where the stand-in sits — `_invoke` (the vendor spawn) for the capture
cases, nothing at all for `StreamlessFamiliesAreDiagnosableToo`, which spawns a real
child. `time.sleep` is patched throughout to skip the backoff's wall clock only.

Offline: no model, no network. Run from the project root:
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

from pdca_harness import driver, leaves, worktree
from pdca_harness.config import Config, LeafConfig

_REAL_SLEEP = time.sleep


def _skip_backoff(seconds: float) -> None:
    """Stand-in for `time.sleep` that skips only the retry BACKOFF (>= 1s, #506): a
    transient builder death is retried now, so every failing case here would otherwise
    spend the shipped 4s + 8s. The wrapper's defaults stay exactly as they ship — only
    their wall clock is skipped — and sub-second polls elsewhere still sleep (patching
    those away turns `run_with_heartbeat`'s wait into a busy-loop)."""
    if seconds < 1:
        _REAL_SLEEP(seconds)


def _cfg(root: Path) -> Config:
    return Config(
        root=root,
        bundle_root=root / "results",
        process_dir=root / "process",
        templates_dir=root / "templates",
        default_branch="main",
        tracker_system="github",
        tracker_url="",
        issue_id_example="#1",
        builder=LeafConfig(mode="command", family="claude", argv=["claude"]),
        reviewer=LeafConfig(mode="stub", family="codex"),
        worktree=False,          # edit in place — keep the slice free of git
    )


class BuildErrorLog(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = _cfg(self.tmp)
        self.d = self.cfg.bundle("ERR")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text("- **Slug:** e\n", encoding="utf-8")
        # A transient builder death is RETRIED now (#506), so these cases would each spend
        # the shipped backoff (4s + 8s) in real time. Patch the sleep, not the wrapper's
        # defaults: the retry logic under test still runs exactly as it ships.
        slept = mock.patch.object(leaves.time, "sleep", side_effect=_skip_backoff)
        slept.start()
        self.addCleanup(slept.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run_failing_build(self, exc: Exception) -> None:
        with mock.patch.object(leaves, "_invoke", side_effect=exc), \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(type(exc)):      # still propagates — _isolate handles it
                leaves.do_build(self.d, self.cfg)

    def test_a_failed_builder_persists_its_error_tail(self) -> None:
        self._run_failing_build(
            leaves.LeafError(1, ["claude"], output="panic: could not open the worktree"))
        log = self.d / leaves.BUILD_ERROR_LOG
        self.assertTrue(log.exists(), "a failed Do must leave a recoverable trace on disk")
        text = log.read_text(encoding="utf-8")
        self.assertIn("panic: could not open the worktree", text)
        self.assertIn("exit 1", text)

    def test_every_attempts_own_account_survives_in_the_log(self) -> None:
        """#506. The builder is retried now, and `build.error.log` is the bundle's whole
        post-mortem: it must carry EVERY attempt's account. The wrapper writes them as they
        happen — so `do_build`'s outer capture, which used to be the only writer, must not
        overwrite them with a single record of the last one."""
        self._run_failing_build(
            leaves.LeafError(1, ["claude"], output="overloaded_error 529"))
        text = (self.d / leaves.BUILD_ERROR_LOG).read_text(encoding="utf-8")
        self.assertIn("attempt 1", text)
        self.assertIn("attempt 3", text)  # the shipped budget, each attempt on the record
        self.assertEqual(text.count("overloaded_error 529"), 3)

    def test_a_transient_death_a_retry_recovers_leaves_no_log(self) -> None:
        """#506. The log's staleness rule end to end: a build that failed transiently and
        then SUCCEEDED on a retry is a build that worked, so the bundle must look exactly
        like one that never failed — no top-level log describing a failure this Do
        survived (the #280 review rule, now reachable within a single Do)."""
        with mock.patch.object(leaves, "_invoke", side_effect=[
                leaves.LeafError(1, ["claude"], output="overloaded_error 529"), None]), \
                redirect_stderr(io.StringIO()):
            leaves.do_build(self.d, self.cfg)  # must NOT raise
        self.assertFalse((self.d / leaves.BUILD_ERROR_LOG).exists())

    def test_a_missing_binary_is_captured_too(self) -> None:
        # The [Errno 2] 'claude' shape — no output to capture, so the exception text is.
        self._run_failing_build(FileNotFoundError(2, "No such file or directory", "claude"))
        text = (self.d / leaves.BUILD_ERROR_LOG).read_text(encoding="utf-8")
        self.assertIn("no output captured", text)
        self.assertIn("FileNotFoundError", text)

    def test_a_successful_build_leaves_no_error_log(self) -> None:
        with mock.patch.object(leaves, "_invoke", return_value=None):
            leaves.do_build(self.d, self.cfg)
        self.assertFalse((self.d / leaves.BUILD_ERROR_LOG).exists())

    def test_a_stale_log_is_cleared_on_the_next_attempt(self) -> None:
        # A prior cycle's failure must not masquerade as this one's.
        (self.d / leaves.BUILD_ERROR_LOG).write_text("stale failure\n", encoding="utf-8")
        with mock.patch.object(leaves, "_invoke", return_value=None):
            leaves.do_build(self.d, self.cfg)
        self.assertFalse((self.d / leaves.BUILD_ERROR_LOG).exists())

    def test_the_error_tail_is_archived_with_its_attempt(self) -> None:
        """PR #286 review (codex). A builder can write patch.diff and THEN die, so the bundle
        still reaches Check and sign-off, and the human iterates. `_archive_iteration` moved
        only DOWNSTREAM_OF_BRIEF + the advisory artifacts — leaving build.error.log at the top
        level, where the next build's clear deletes it. The one on-disk record of why Do failed
        was destroyed by the very rebuild it exists to explain."""
        for name in ("patch.diff", "build-notes.md", "check-review.md", "SUMMARY.md",
                     leaves.BUILD_ERROR_LOG):
            (self.d / name).write_text("x\n", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            driver._archive_iteration(self.d, 1, include_brief=False)

        archived = self.d / "iteration-v1" / leaves.BUILD_ERROR_LOG
        self.assertTrue(archived.exists(), "the failed attempt's error tail must be preserved")
        self.assertFalse((self.d / leaves.BUILD_ERROR_LOG).exists())  # not left to be deleted

    def test_the_check_leaves_error_tails_are_archived_too(self) -> None:
        # The same defect, pre-existing, for the reviewer/advisory logs: each is cleared at the
        # start of the next Check, so one left top-level is likewise destroyed on the rebuild.
        for name in ("patch.diff", "check-review.error.log",
                     "check-advisory-adversary.error.log"):
            (self.d / name).write_text("x\n", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            driver._archive_iteration(self.d, 1, include_brief=False)
        arch = self.d / "iteration-v1"
        self.assertTrue((arch / "check-review.error.log").exists())
        self.assertTrue((arch / "check-advisory-adversary.error.log").exists())

    def test_a_stale_log_is_cleared_on_a_stub_rebuild_too(self) -> None:
        # The clear now runs before EITHER backend, so a stub rebuild can't leave a top-level
        # log describing a failure this build never had.
        self.cfg.builder = LeafConfig(mode="stub", family="claude")
        (self.d / leaves.BUILD_ERROR_LOG).write_text("stale failure\n", encoding="utf-8")
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves.do_build(self.d, self.cfg)
        self.assertFalse((self.d / leaves.BUILD_ERROR_LOG).exists())

    def test_a_setup_failure_before_the_leaf_launches_is_captured(self) -> None:
        """PR #286 review (codex). The capture wrapped only `_invoke`, but Do can die in its
        SETUP — and the likeliest way is `worktree.ensure`, which deliberately RAISES
        WorktreeError when the target's base ref doesn't resolve (#235, fail-closed: it refuses
        to run Do in the operator's primary checkout). In a wave batch, an unpushed folded base
        is exactly that. Such a Do left no bundle-local trace at all — worse than before the
        log existed, since do_build had already cleared the stale one — so the post-mortem was
        back to terminal scrollback for the failure mode most likely to hit a WHOLE wave."""
        self.cfg.worktree = True
        boom = worktree.WorktreeError(
            "ERR: base ref 'origin/pdca-integration/main' does not resolve")
        with mock.patch.object(leaves.worktree, "ensure", side_effect=boom), \
                mock.patch.object(leaves, "_invoke") as invoked, \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(worktree.WorktreeError):
                leaves.do_build(self.d, self.cfg)
        invoked.assert_not_called()          # it died in setup — the leaf never launched
        text = (self.d / leaves.BUILD_ERROR_LOG).read_text(encoding="utf-8")
        self.assertIn("does not resolve", text)
        self.assertIn("WorktreeError", text)

    def test_capture_never_masks_the_real_failure(self) -> None:
        # If the log itself can't be written, the builder's exception still reaches the flow.
        with mock.patch.object(leaves, "_invoke",
                               side_effect=leaves.LeafError(1, ["claude"], output="boom")), \
                mock.patch.object(Path, "write_text", side_effect=OSError("read-only fs")), \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(leaves.LeafError):
                leaves.do_build(self.d, self.cfg)


class StreamlessFamiliesAreDiagnosableToo(unittest.TestCase):
    """PR #286 review (codex). The error tail was only ever captured on the vendor STREAM path
    (`run_with_heartbeat` kept stderr iff `capture or stream_json`), and `_invoke` passes neither
    for a family with no `stream_argv`. So for `generic` and `gemini` — the local/custom builders,
    the ones whose failures are least self-evident — `build.error.log` was written faithfully and
    said only "(no output captured)": a post-mortem artifact that explains nothing.

    These drive the REAL `_invoke` → `progress` → `subprocess` path with a child that writes a
    diagnosable line to stderr and dies. Mocking `_invoke` (as the tests above do) is what let the
    gap through: it hands the output in, so it can never observe that nothing was captured.
    """

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = _cfg(self.tmp)
        self.d = self.cfg.bundle("ERR")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text("- **Slug:** e\n", encoding="utf-8")
        slept = mock.patch.object(leaves.time, "sleep",  # see BuildErrorLog.setUp (#506)
                                  side_effect=_skip_backoff)
        slept.start()
        self.addCleanup(slept.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    FATAL = "toolchain is missing libfoo.so"

    def _build_with_a_dying_child(self, family: str) -> str:
        # The marker reaches the child through the ENV, never through argv. `_format_leaf_attempt`
        # echoes the failed command line into the log, so a marker written as an argv literal is
        # matched by that echo and the assertion passes with NO capture at all — the first cut of
        # this test was vacuous for exactly that reason. Env-borne, the only way it can reach the
        # log is by actually being captured off the child's stderr.
        self.cfg.builder = LeafConfig(mode="command", family=family, argv=[
            sys.executable, "-c",
            "import os, sys; sys.stderr.write(os.environ['PDCA_TEST_STDERR'] + chr(10));"
            " sys.exit(3)"])
        # stderr is TEE'd (echoed live AND kept), so send the live echo to /dev/null — the
        # assertion must read the LOG, not the console the tee also wrote to.
        with mock.patch.dict(os.environ, {"PDCA_TEST_STDERR": self.FATAL}), \
                open(os.devnull, "w", encoding="utf-8") as null:
            saved = os.dup(2)
            os.dup2(null.fileno(), 2)
            try:
                with self.assertRaises(leaves.LeafError):
                    leaves.do_build(self.d, self.cfg)
            finally:
                os.dup2(saved, 2)
                os.close(saved)
        return (self.d / leaves.BUILD_ERROR_LOG).read_text(encoding="utf-8")

    def _assert_diagnosable(self, family: str) -> None:
        text = self._build_with_a_dying_child(family)
        self.assertIn(self.FATAL, text, f"{family}: the child's real error must survive")
        self.assertNotIn("no output captured", text)

    def test_a_generic_builders_stderr_survives_in_the_log(self) -> None:
        self._assert_diagnosable("generic")

    def test_a_gemini_builders_stderr_survives_in_the_log(self) -> None:
        self._assert_diagnosable("gemini")

    def test_the_streaming_family_still_keeps_its_tail(self) -> None:
        # The claude path already tee'd; decoupling the tee from stream_json must not lose it.
        self._assert_diagnosable("claude")


if __name__ == "__main__":
    unittest.main()
