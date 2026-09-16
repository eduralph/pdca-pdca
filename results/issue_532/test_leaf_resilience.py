"""Leaf resilience (issues #138, #506) — stdlib unittest, no deps.

A Check reviewer/advisory leaf that exits non-zero used to collapse to an opaque §6
placeholder whose only diagnostic was the exit code, and a transient `claude -p`
blip (usage/rate limit, 5xx) wedged sign-off the same as a substantive failure.
`_invoke_leaf_resilient` now: (1) persists the failed attempts' stderr tail to an
error log, (2) retries a *transient* (no-output) failure with backoff before
degrading, and (3) classifies the placeholder transient-vs-substantive.

#506 makes **an attempt the unit of accountability** for every leaf the harness
spawns: the *builder* runs under the same wrapper (it was the only leaf never
retried), each attempt's record is flushed — and must LAND — before the next attempt
starts, a retried builder is told its predecessor died mid-flight and that any
artifact present is that attempt's residue, an exhausted retry says so and names a
next action true for the residue actually on disk, and no artifact a dead attempt
left behind is harvested as a live one's output.

Production path exercised (nothing here re-implements what it asserts — the only
stand-ins are `time.sleep`, i.e. the backoff's wall clock, and `_invoke`, i.e. the
vendor spawn, where a stub *leaf process* would not add anything):

    BuilderRetriesLikeEveryOtherLeaf  → leaves.do_build → _do_build_command →
        _invoke_leaf_resilient → _invoke → progress.run_with_heartbeat → subprocess
        (the "leaf" is a real python3 child; nothing in leaves.py is stubbed)
    AKilledLeafIsRecoveredNotRetired  → leaves._run_review_sandboxed +
        leaves.run_advisory_leaves + driver._resume_interrupted_check →
        leaves.review_never_ran / _leaf_ran_and_failed / leaf_run_incomplete
    DeadAttemptOutputIsNeverHarvested → leaves._run_review_sandboxed /
        _run_advisory_sandboxed / run_plan_advisory → _invoke_leaf_resilient →
        _withdraw_residue → the sites' `if produced.exists()` harvest

Run with:
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

from pdca_harness import driver, leaves, state
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
    """Stand-in for `time.sleep` that skips only the retry BACKOFF (>= 1s, #506), so a case
    driving a leaf to its attempt budget costs no wall clock — without weakening the
    wrapper's shipped defaults, and without turning any sub-second poll elsewhere in the
    process into a busy-wait."""
    if seconds < 1:
        _REAL_SLEEP(seconds)


def _kill_during_backoff(seconds: float) -> None:
    """A run killed WHILE it waits to retry — Ctrl-C, an OOM kill, a closed session. That
    window is what the per-attempt flush exists for. `KeyboardInterrupt` is not an
    `Exception`, so it tears the wrapper down without its handlers catching it, exactly as
    a signal would. Sub-second waits are the harness's own polling, not the backoff."""
    if seconds < 1:
        _REAL_SLEEP(seconds)
        return
    raise KeyboardInterrupt


class _BrokenStderr(io.StringIO):
    """A console that is gone — the shape a detached/piped-away run leaves behind. Every
    write raises `BrokenPipeError`, which IS an `OSError`, so an unguarded report can
    replace the very failure it was reporting."""

    def write(self, _s: str) -> int:
        raise BrokenPipeError(32, "Broken pipe")


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
#: instrumented from the inside: it counts its invocations in $CNT and saves, under $PROBE,
#: the prompt it was given and the CONTENT OF $ERRLOG AT THAT MOMENT. $RESIDUE (os.pathsep-
#: separated) names files it half-writes before dying — a builder that wrote patch.diff and
#: then lost its API connection.
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
    "[open(p, 'w').write('half\\n') "
    " for p in os.environ.get('RESIDUE', '').split(os.pathsep) if p]; "
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

#: Killed from OUTSIDE mid-run — the shape a leaf gets from the #420 memory cap's OOM
#: SIGKILL. No stream event either, so `.transient` is True for it as well; the returncode
#: is what tells them apart (negative: the child did not choose its own exit status).
_SIGKILLED_BUILDER = (
    "import os, signal, sys; "
    "open(os.environ['CNT'], 'a').write('x'); sys.stdin.read(); "
    "sys.stderr.write('Killed\\n'); "
    "os.kill(os.getpid(), signal.SIGKILL)"
)

#: The same death one wrapper deep: `argv[0]` is a shell / `docker run` / a local-executor
#: script, and what the harness sees is the WRAPPER's exit status for a child killed by
#: signal N — 128+N, a POSITIVE number (137 = SIGKILL).
_WRAPPER_KILLED_BUILDER = (
    "import os, sys; "
    "open(os.environ['CNT'], 'a').write('x'); sys.stdin.read(); "
    "sys.stderr.write('Killed\\n'); sys.exit(137)"
)

#: Dies transiently on attempt 1, then builds on attempt 2 (writes $RESIDUE, exits 0).
_FLAKY_BUILDER = (
    "import os, sys; "
    "cnt = os.environ['CNT']; "
    "n = len(open(cnt).read()) + 1 if os.path.exists(cnt) else 1; "
    "open(cnt, 'a').write('x'); sys.stdin.read(); "
    "sys.stderr.write('overloaded_error 529\\n') if n == 1 else None; "
    "sys.exit(1) if n == 1 else None; "
    "[open(p, 'w').write('whole\\n') "
    " for p in os.environ.get('RESIDUE', '').split(os.pathsep) if p]; "
    "print('{\"type\": \"result\"}')"
)


def _cfg(root: Path, *, builder: LeafConfig, reviewer: LeafConfig | None = None,
         plan_advisory: list[dict] | None = None,
         advisory: list[dict] | None = None) -> Config:
    cfg = Config(
        root=root,
        bundle_root=root / "results",
        process_dir=root / "process",
        templates_dir=root / "templates",
        default_branch="main",
        tracker_system="github",
        tracker_url="",
        issue_id_example="#1",
        builder=builder,
        reviewer=reviewer or LeafConfig(mode="stub", family="codex"),
        worktree=False,          # edit in place — keep the slice free of git
    )
    cfg.plan_advisory_leaves = list(plan_advisory or [])
    cfg.advisory_leaves = list(advisory or [])
    return cfg


def _command_leaf(script: str) -> LeafConfig:
    """A claude-family COMMAND leaf that is a Python interpreter, so the stream path — the
    only one that yields the "did a session start" signal — engages."""
    return LeafConfig(mode="command", family="claude",
                      argv=[sys.executable, "-c", script], interactive=False)


class BuilderRetriesLikeEveryOtherLeaf(unittest.TestCase):
    """#506 (i)/(ii)/(iii)/(iv). `_do_build_command` called plain `_invoke`, so the ONE leaf
    the harness never retried was the most expensive one to lose. These drive the real
    `do_build` → `_invoke_leaf_resilient` → `_invoke` → `progress` → `subprocess` path with
    a builder that is a Python interpreter; only `time.sleep` is patched, so the shipped
    attempt/backoff defaults are exercised as they ship, without spending their wall clock."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.probe = self.tmp / "probe"
        self.probe.mkdir()
        self.cnt = self.tmp / "count.txt"
        self.cfg = _cfg(self.tmp, builder=_command_leaf(_DYING_BUILDER))
        self.d = self.cfg.bundle("506")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text(
            "- **Slug:** attempt-accountability\n"
            "- **Test file:** `test_attempts.py`\n", encoding="utf-8")
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
        self.assertEqual(self._runs(), 3)      # the wrapper's shipped budget, not 1
        self.assertIn("retry 1/2 in 4s", out)  # …with the shipped backoff between attempts
        self.assertIn("retry 2/2 in 8s", out)
        text = self.log.read_text(encoding="utf-8")
        self.assertEqual(text.count("overloaded_error 529"), 3)  # every attempt accounted
        self.assertIn("attempt 3", text)

    def test_a_substantive_builder_failure_is_still_not_retried(self) -> None:
        self.cfg.builder = _command_leaf(_SUBSTANTIVE_BUILDER)
        out = self._failing_build()
        self.assertEqual(self._runs(), 1)  # it read the brief and failed on the merits
        self.assertNotIn("retry", out)     # …so nothing is retried, exactly as today
        self.assertIn("the brief contradicts itself",
                      self.log.read_text(encoding="utf-8"))
        self.assertNotIn("TRANSIENT", out)  # nor is it reported as absorbed infra

    def test_a_builder_killed_by_a_signal_is_not_retried(self) -> None:
        """#510 stays #510. A leaf SIGKILLed from outside — the #420 memory cap's OOM kill
        is the shipped way to earn one — produced no stream event either, so it reads
        `transient`. Retrying it would re-run, twice more, the very build that exhausted
        its bound, and would tell the operator the failure was absorbed infra while
        build.error.log says otherwise. One spawn, re-raised: exactly today's behaviour."""
        self.cfg.builder = _command_leaf(_SIGKILLED_BUILDER)
        out = self._failing_build()
        self.assertEqual(self._runs(), 1)
        self.assertNotIn("retry", out)
        self.assertNotIn("TRANSIENT", out)  # no claim that the harness absorbed it

    def test_a_signal_death_reported_one_wrapper_deep_is_not_retried_either(self) -> None:
        """The same kill, seen through a wrapper argv (`sh -c …`, `docker run`, a local
        executor): the harness gets the WRAPPER's status for a child killed by signal N —
        128+N, positive — so an exclusion written as `returncode < 0` misses it entirely
        and the OOM is repeated three times. `_died_of_a_signal` reads both spellings."""
        self.cfg.builder = _command_leaf(_WRAPPER_KILLED_BUILDER)
        out = self._failing_build()
        self.assertEqual(self._runs(), 1)
        self.assertNotIn("retry", out)
        self.assertNotIn("TRANSIENT", out)
        self.assertIn("Killed", self.log.read_text(encoding="utf-8"))

    def test_a_recovered_build_is_reported_exactly_as_a_clean_one(self) -> None:
        # The retry that works must leave the bundle indistinguishable from a build that
        # never failed: patch.diff present, no error log, nothing raised.
        self.cfg.builder = _command_leaf(_FLAKY_BUILDER)
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

    def test_a_retry_never_starts_without_its_predecessors_account_on_disk(self) -> None:
        """(ii) is a CONTINGENCY, not merely a flush order: attempt N+1 may start only once
        attempt N's account is DURABLY on disk. A wrapper that writes best-effort and
        retries regardless leaves exactly the window it exists to close — the next attempt
        runs while nothing on disk explains the first, and a run killed in that window
        leaves the bundle no account of either."""
        real_write = Path.write_text

        def refuse_the_log(self_, *a, **kw):
            if self_.name == leaves.BUILD_ERROR_LOG:
                raise OSError("read-only bundle")
            return real_write(self_, *a, **kw)

        with mock.patch.object(Path, "write_text", refuse_the_log):
            out = self._failing_build()
        self.assertEqual(self._runs(), 1, "no second attempt over an unrecorded first")
        self.assertIn("could not write", out)
        self.assertIn("not starting another attempt", out)
        # …and the SAME builder against a writable bundle does retry: what stopped it was
        # the unrecorded predecessor, not the failure class.
        self.cnt.unlink()
        self._failing_build()
        self.assertEqual(self._runs(), 3)

    def test_a_broken_stderr_never_replaces_the_builders_own_failure(self) -> None:
        """Criterion (i): the final failure is captured and RE-RAISED either way. Every
        report this path added goes to stderr, and a console that is gone raises
        BrokenPipeError — an OSError — so an unguarded print hands `flow._isolate` an
        exception about REPORTING the failure instead of the failure itself. The spawn is
        stubbed here so the only stderr writers left are the ones this slice added."""
        with mock.patch.object(leaves, "_invoke", side_effect=leaves.LeafError(
                1, ["claude"], output="overloaded_error 529")) as invoked, \
                redirect_stdout(io.StringIO()), redirect_stderr(_BrokenStderr()):
            with self.assertRaises(leaves.LeafError):
                leaves.do_build(self.d, self.cfg)
        self.assertEqual(invoked.call_count, 3)   # …and the retries still ran
        self.assertIn("overloaded_error 529", self.log.read_text(encoding="utf-8"))

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
        self.assertIn("after 3 attempt(s)", out)        # what it actually cost
        self.assertIn(leaves.BUILD_ERROR_LOG, out)      # where its account is
        self.assertIn("reads BUILT", out)               # what the residue did to the bundle
        self.assertIn("runs CHECK", out)                # what a plain re-run would do
        self.assertIn("iterate-do", out)                # a next action that actually works
        self.assertTrue((self.d / "patch.diff").exists(),
                        "the report describes the bundle; it never edits it")
        # …and the claim is TRUE of the real state machine, not just a nice sentence.
        self.assertEqual(state.state(self.d), state.BUILT)

    def test_the_exhausted_report_asks_the_state_machine_not_the_residues_shape(self) -> None:
        """The advice must be derived from `state.state`, not from "is there a patch.diff".
        `state.state` is a waterfall: patch.diff AND check-gates.json reads CHECKED, whose
        next beat is assembly — so a patch-shaped guess is false exactly on the bundle its
        own previous advice creates (let Check run, then Do dies again)."""
        (self.d / "check-gates.json").write_text("{}\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"RESIDUE": str(self.d / "patch.diff")}):
            out = self._failing_build()
        self.assertEqual(state.state(self.d), state.CHECKED)
        self.assertIn("reads CHECKED", out)
        self.assertIn("ASSEMBLES SUMMARY.md", out)
        self.assertNotIn("runs CHECK on the residue", out)  # that sentence is false here

    def test_the_exhausted_report_names_the_residue_without_inventing_its_author(self) -> None:
        # No patch.diff, so the bundle still reads PLANNED and a plain re-run DOES re-drive
        # Do — over a half-written build-notes.md and the brief's test file, which that
        # fresh builder gets with no retry notice attached. Say so; do not report "inputs
        # intact" while an unfinished attempt's residue sits in the bundle. And do not
        # claim WHO wrote it: a transient death produced nothing by definition, so these
        # files are as likely an earlier round's, and the harness cannot tell.
        residue = [self.d / "build-notes.md", self.d / "test_attempts.py"]
        with mock.patch.dict(os.environ, {"RESIDUE": os.pathsep.join(map(str, residue))}):
            out = self._failing_build()
        self.assertEqual(state.state(self.d), state.PLANNED)
        self.assertIn("reads PLANNED", out)
        self.assertIn("re-drives Do", out)
        self.assertIn("build-notes.md", out)
        self.assertIn("test_attempts.py", out)  # the file the brief names, left half-written
        self.assertIn("which may predate this attempt", out)
        self.assertNotIn("the interrupted attempt left", out)  # authorship it cannot know
        self.assertIn("WITHOUT the retry notice", out)
        self.assertTrue(all(p.exists() for p in residue))  # reported, never deleted


class AKilledLeafIsRecoveredNotRetired(unittest.TestCase):
    """#506 (ii) against #369. Flushing each attempt's record as it happens is what lets a
    retried leaf — and a post-mortem — read its predecessor's account. But the error log is
    also the #369 discriminator ("the leaf ran and FAILED"), so a log left MID-RETRY must
    not retire a leaf the death window merely interrupted: that would leave the bundle with
    no review of the diff at all, and it would still reach sign-off."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = _cfg(self.tmp, builder=LeafConfig(mode="stub", family="claude"),
                        reviewer=LeafConfig(mode="command", family="claude", argv=["claude"]),
                        advisory=[{"id": "lens", "mode": "stub", "family": "codex"}])
        self.d = self.cfg.bundle("506")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text("- **Slug:** s\n", encoding="utf-8")
        (self.d / "patch.diff").write_text("--- a/x\n", encoding="utf-8")
        (self.d / "check-gates.json").write_text("{}\n", encoding="utf-8")
        self.log = self.d / state.REVIEW_ERROR_LOG
        slept = mock.patch.object(leaves.time, "sleep", side_effect=_skip_backoff)
        slept.start()
        self.addCleanup(slept.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _kill_the_reviewer_mid_retry(self) -> None:
        """Attempt 1 dies transiently; the run is killed during the backoff."""
        def dying(leaf, workdir, prompt, **kw):
            raise leaves.LeafError(1, ["claude"], output="connection reset by peer")

        with mock.patch.object(leaves, "_invoke", side_effect=dying), \
                mock.patch.object(leaves.time, "sleep", side_effect=_kill_during_backoff), \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                leaves._run_review_sandboxed(self.d, self.cfg)

    def _reviewer_that_dies_then_writes_nothing(self, first_writes: str):
        """Attempt 1 leaves an artifact in the sandbox and dies transiently; attempt 2 comes
        back alive and writes nothing. The wrapper KEEPS the error log there — it is the
        only surviving copy of the withdrawn text — so that log belongs to a loop that
        FINISHED and must not read as one still in flight."""
        calls: list[Path] = []

        def flaky(leaf, workdir, prompt, **kw):
            calls.append(Path(workdir))
            if len(calls) == 1:
                (Path(workdir) / "check-review.md").write_text(first_writes,
                                                               encoding="utf-8")
                raise leaves.LeafError(1, ["claude"], output="connection reset by peer")

        return flaky

    def test_a_reviewer_killed_mid_retry_leaves_its_account_and_is_still_recovered(self) -> None:
        self._kill_the_reviewer_mid_retry()
        # (ii): the dead attempt's account is on disk, written while the retry was pending.
        self.assertIn("connection reset by peer", self.log.read_text(encoding="utf-8"))
        self.assertTrue(leaves.leaf_run_incomplete(self.log))  # …and flagged unfinished
        self.assertFalse((self.d / "check-review.md").exists())
        self.assertEqual(state.state(self.d), state.CHECKED)

        # #369 unchanged: the driver's CHECKED-resume must still recover the reviewer.
        def alive(leaf, workdir, prompt, **kw):
            (Path(workdir) / "check-review.md").write_text(
                "| Item | Verdict | Basis |\nrecovered\n", encoding="utf-8")

        with mock.patch.object(leaves, "_invoke", side_effect=alive), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            driver._resume_interrupted_check(self.d, self.cfg, "")
        self.assertIn("recovered", (self.d / "check-review.md").read_text(encoding="utf-8"))
        self.assertFalse(self.log.exists(), "the recovered run cleared its predecessor's log")

    def test_a_leaf_that_spent_its_whole_budget_is_still_not_re_run(self) -> None:
        # The other half of the #138/#369 discriminator, unchanged: a COMPLETE error log
        # means the leaf ran and gave up, and the resume leaves it alone. Written here by
        # the production wrapper itself, so the two halves cannot drift apart.
        leaf = _leaf(_TRANSIENT)
        with mock.patch.dict(os.environ, {"CNT": str(self.tmp / "c")}), \
                redirect_stderr(io.StringIO()):
            leaves._invoke_leaf_resilient(
                leaf, self.tmp, "review please", error_log=self.log,
                attempts=2, backoff=0.0, stream_json=True)
        self.assertFalse(leaves.leaf_run_incomplete(self.log))  # it gave up, not interrupted
        with mock.patch.object(leaves, "_invoke") as invoked, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            driver._resume_interrupted_check(self.d, self.cfg, "")
        invoked.assert_not_called()
        self.assertFalse((self.d / "check-review.md").exists())

    def test_a_finished_loop_is_never_left_flagged_in_flight(self) -> None:
        """The log the wrapper deliberately KEEPS (a dead attempt's artifact was withdrawn
        and the winning attempt wrote none) is written by a loop that FINISHED. Left with
        the in-flight trailer of its last retry, `leaf_run_incomplete` contradicts its own
        docstring — and the #369 recovery would re-run a leaf that already ran out."""
        dies_then_nothing = self._reviewer_that_dies_then_writes_nothing(
            "| Item | Verdict |\nhalf")
        with mock.patch.object(leaves, "_invoke", side_effect=dies_then_nothing), \
                redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertIn("half", self.log.read_text(encoding="utf-8"))  # evidence kept
        self.assertFalse(leaves.leaf_run_incomplete(self.log))

    def test_a_dead_attempts_artifact_ending_in_the_marker_is_not_the_trailer(self) -> None:
        """Whether a run finished is a property of the harness's own trailer, never of what
        a leaf wrote — and in THIS repo a verdict quoting the marker is an ordinary day.
        The withdrawn artifact is embedded verbatim in the log, so one ending ON the marker
        would otherwise BE the log's last line and speak for the run that quoted it."""
        # The marker alone on the artifact's LAST line — a verdict quoting the source line
        # it is reviewing, which is exactly where the withdrawn text lands in the log.
        quoted = f"| Item | Verdict |\nit reads:\n{leaves._LEAF_IN_FLIGHT}\n"
        dies_then_nothing = self._reviewer_that_dies_then_writes_nothing(quoted)
        with mock.patch.object(leaves, "_invoke", side_effect=dies_then_nothing), \
                redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertIn("it reads:", self.log.read_text(encoding="utf-8"))  # kept, verbatim
        self.assertFalse(leaves.leaf_run_incomplete(self.log))

    def test_a_leaf_whose_stderr_quotes_the_marker_is_still_read_as_spent(self) -> None:
        """The same hazard through the other door: the tail `_format_leaf_attempt` writes is
        the leaf's OWN stderr — a builder editing this file, a reviewer quoting it. A leaf
        that ran out of attempts must still read as spent, or #369 re-runs a leaf that
        already gave up (and pays for it again)."""
        noisy = leaves.LeafError(1, ["claude"],
                                 output=f"echo of the source: {leaves._LEAF_IN_FLIGHT}")
        with mock.patch.object(leaves, "_invoke", side_effect=noisy), \
                redirect_stderr(io.StringIO()):
            leaves._invoke_leaf_resilient(self.cfg.reviewer, self.tmp, "review please",
                                          error_log=self.log, attempts=2, backoff=0.0)
        self.assertIn("echo of the source", self.log.read_text(encoding="utf-8"))
        self.assertFalse(leaves.leaf_run_incomplete(self.log))
        # …and the #369 resume agrees: a spent leaf is not re-run.
        with mock.patch.object(leaves, "_invoke") as invoked, \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            driver._resume_interrupted_check(self.d, self.cfg, "")
        invoked.assert_not_called()

    def test_an_advisory_leaf_killed_mid_retry_is_recovered_too(self) -> None:
        # The same discriminator, second spelling (`only_missing`, leaves.py) — a leaf
        # interrupted mid-retry is missing, not spent.
        log = leaves.advisory_error_log(self.d, "lens")
        with mock.patch.dict(os.environ, {"CNT": str(self.tmp / "c")}), \
                mock.patch.object(leaves.time, "sleep", side_effect=_kill_during_backoff), \
                redirect_stderr(io.StringIO()):
            with self.assertRaises(KeyboardInterrupt):
                leaves._invoke_leaf_resilient(
                    _leaf(_TRANSIENT), self.tmp, "advise", error_log=log,
                    attempts=3, backoff=4.0, stream_json=True)
        self.assertTrue(log.exists())  # the interrupted attempt's account
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves.run_advisory_leaves(self.d, self.cfg, only_missing=True)
        self.assertTrue(leaves.advisory_artifact(self.d, "lens").exists())


class DeadAttemptOutputIsNeverHarvested(unittest.TestCase):
    """#506 (v). The three harvest sites copy their artifact `if produced.exists()`, with no
    notion of WHICH attempt wrote it — so a truncated verdict a dead attempt left in the
    sandbox is adopted as the output of the attempt that succeeded. These drive the real
    harvest sites; only the vendor spawn (`_invoke`) is stubbed."""

    TRUNCATED = "| Item | Verdict | Basis |\n| 1.1 Root cause | PA"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = _cfg(self.tmp, builder=LeafConfig(mode="stub", family="claude"),
                        reviewer=LeafConfig(mode="command", family="claude", argv=["claude"]),
                        advisory=[{"id": "lens", "mode": "command", "family": "codex",
                                   "argv": ["codex"]}])
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

    def _flaky(self, calls: list[Path], artifact: str, *, second_writes: str = ""):
        """Attempt 1 writes half a verdict, then the connection drops. Attempt 2 comes back
        alive and writes ``second_writes`` (by default nothing — so nothing reviewed the
        diff, and the only file at that path is its dead predecessor's)."""
        def flaky(leaf, workdir, prompt, **kw):
            calls.append(Path(workdir))
            if len(calls) == 1:
                (Path(workdir) / artifact).write_text(self.TRUNCATED, encoding="utf-8")
                raise leaves.LeafError(1, ["claude"], output="connection reset by peer")
            if second_writes:
                (Path(workdir) / artifact).write_text(second_writes, encoding="utf-8")
        return flaky

    def test_a_dead_attempts_half_written_verdict_is_not_adopted_as_the_reviews(self) -> None:
        calls: list[Path] = []
        with mock.patch.object(leaves, "_invoke",
                               side_effect=self._flaky(calls, "check-review.md")), \
                redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertEqual(len(calls), 2)  # the transient death was retried, as before
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertNotIn("1.1 Root cause | PA", review)  # the dead attempt's file, refused
        self.assertIn("NOT COMPLETED", review)           # the honest verdict: none produced
        self.assertIn("NEEDS-HUMAN", review)

    def test_the_withdrawn_verdict_is_readable_in_the_bundle_afterwards(self) -> None:
        # Withdrawing a dead attempt's claim must not destroy its work: the sandbox it sat
        # in is a TemporaryDirectory that dies with the run, so the text is kept in the
        # bundle's own error log — the file the placeholder above already points at.
        calls: list[Path] = []
        with mock.patch.object(leaves, "_invoke",
                               side_effect=self._flaky(calls, "check-review.md")), \
                redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        log = (self.d / state.REVIEW_ERROR_LOG).read_text(encoding="utf-8")
        self.assertIn("1.1 Root cause | PA", log)
        self.assertIn("check-review.md", log)  # …named as what it was, and whose it was
        self.assertIn("attempt 1", log)

    def test_the_live_attempts_own_artifact_is_still_harvested(self) -> None:
        # The ownership check must not cost a leaf its own work: a retry that RE-writes the
        # artifact is harvested exactly as today.
        calls: list[Path] = []
        with mock.patch.object(leaves, "_invoke", side_effect=self._flaky(
                calls, "check-review.md",
                second_writes="| Item | Verdict | Basis |\nfull verdict\n")), \
                redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertIn("full verdict", review)
        self.assertNotIn("1.1 Root cause | PA", review)

    def test_an_advisory_leafs_dead_attempt_is_refused_the_same_way(self) -> None:
        calls: list[Path] = []
        leaf = leaves._advisory_leaf(self.cfg.advisory_leaves[0], "advisory", "lens")
        with mock.patch.object(leaves, "_invoke", side_effect=self._flaky(
                calls, "check-advisory-lens.md")), redirect_stderr(io.StringIO()):
            leaves._run_advisory_sandboxed(self.d, self.cfg, leaf,
                                           self.cfg.advisory_leaves[0], "lens")
        found = leaves.advisory_artifact(self.d, "lens").read_text(encoding="utf-8")
        self.assertNotIn("1.1 Root cause | PA", found)
        self.assertIn("NOT COMPLETED", found)

    def test_the_plan_advisory_site_owns_the_file_it_later_harvests(self) -> None:
        # The third site. Its target checkout is pinned per-run, so assert the wiring the
        # other two prove behaviourally: the path handed to the wrapper for ownership is
        # exactly the path the harvest copies out of the sandbox.
        cfg = _cfg(self.tmp, builder=LeafConfig(mode="stub", family="claude"),
                   plan_advisory=[{"id": "lens", "mode": "command", "family": "codex",
                                   "argv": ["codex"]}])
        d = cfg.bundle("PLAN")
        d.mkdir(parents=True)
        (d / "brief.md").write_text("- **Slug:** s\n", encoding="utf-8")
        seen: dict = {}

        def fake(leaf, cwd, prompt, **kw):
            seen["artifact"] = kw.get("artifact")
            seen["cwd"] = Path(cwd)
            (Path(cwd) / "plan-advisory-lens.md").write_text("findings\n", encoding="utf-8")

        with mock.patch.object(leaves, "_invoke_leaf_resilient", side_effect=fake), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves.run_plan_advisory(d, cfg)
        self.assertEqual(seen.get("artifact"), seen["cwd"] / "plan-advisory-lens.md")
        self.assertIn("findings", leaves.plan_advisory_artifact(d, "lens")
                      .read_text(encoding="utf-8"))

    def test_ownership_that_cannot_be_enforced_stops_the_retries(self) -> None:
        """Fail CLOSED. If a dead attempt's file cannot be withdrawn, the next attempt would
        run over a path the wrapper no longer owns — and a success that writes nothing would
        hand the harvest that dead file. Stop instead: the leaf's own failure is returned,
        the placeholder is written, and nothing dead is adopted."""
        calls: list[Path] = []
        real_unlink = Path.unlink

        def refuse(self_, *a, **kw):  # only the artifact: the error log must still clear
            if self_.name == "check-review.md":
                raise OSError("read-only sandbox")
            return real_unlink(self_, *a, **kw)

        err = io.StringIO()
        with mock.patch.object(leaves, "_invoke",
                               side_effect=self._flaky(calls, "check-review.md")), \
                mock.patch.object(Path, "unlink", refuse), redirect_stderr(err):
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertEqual(len(calls), 1, "no further attempt over an unowned artifact path")
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertNotIn("1.1 Root cause | PA", review)
        self.assertIn("NOT COMPLETED", review)
        self.assertIn("stopping the retries", err.getvalue())


if __name__ == "__main__":
    unittest.main()
