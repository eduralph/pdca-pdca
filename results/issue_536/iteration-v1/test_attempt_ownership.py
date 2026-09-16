"""An attempt is the unit of accountability (issue #506) — stdlib unittest, no deps.

Three leaves already retry (`_invoke_leaf_resilient`, #138), and nothing tied what a leaf
left behind to the *attempt that produced it*:

  * the attempt records were written only once the retry loop ended, so while attempt 2 ran
    there was nothing on disk explaining attempt 1 — and a run killed mid-retry lost them
    all, including the account a post-mortem would read;
  * the three harvest sites copied their artifact on a bare `.exists()`, so a truncated
    verdict a DEAD attempt left in the sandbox was adopted as the output of the attempt
    that succeeded — no evidence filed as a verdict, which `engine/README.md` forbids;
  * an error log now exists WHILE a leaf is still retrying, so the #369 recovery
    discriminators must read "interrupted", not "gave up" — otherwise a reviewer the death
    window merely interrupted is retired and the bundle reaches sign-off with no review of
    the diff. And since the log quotes the leaf's own text (its stderr tail, a withdrawn
    artifact), a leaf must not be able to write the harness's in-flight trailer for it.

Production path exercised — nothing here re-implements what it asserts, and no symbol this
patch adds is named anywhere below (the assertions are behavioural, through pre-existing
entry points):

    AttemptRecordsLandBeforeTheNextAttemptStarts → leaves._invoke_leaf_resilient →
        _invoke → progress.run_with_heartbeat → subprocess (the "leaf" is a real python3
        child, instrumented to read the error log from INSIDE the retry loop)
    DeadAttemptOutputIsNeverHarvested            → leaves._run_review_sandboxed →
        _invoke_leaf_resilient → the site's `if produced.exists()` harvest
    AnInterruptedLeafIsRecoveredNotRetired       → the same two, then
        leaves.review_never_ran (the #369 discriminator)

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

from pdca_harness import leaves, state
from pdca_harness.config import Config, LeafConfig

# The stub-leaf harness, copied from tests/test_leaf_resilience.py:23-40 rather than
# imported across modules: a claude-family leaf so `_invoke`'s stream path engages (the
# only path that yields the "did a session start" signal), whose argv is a python
# interpreter running an inline script; `_invoke` appends --output-format/--verbose
# (ignored) and feeds the prompt on stdin. Each script counts its own invocations into
# $CNT so a case can assert how many attempts a leaf actually cost.
_TRANSIENT = (  # dies at invocation: only stderr, no stdout → no session started
    "import os,sys; open(os.environ['CNT'],'a').write('x'); "
    "sys.stderr.write('overloaded_error 529\\n'); sys.exit(1)"
)

# The same death, instrumented from the INSIDE: before dying, each attempt saves what
# $ERRLOG held AT THAT MOMENT under $PROBE. That observation is the only way to tell "each
# attempt's record was flushed as it happened" from "the records were written once the loop
# ended" — after the loop the two are indistinguishable on disk.
_PROBING = """\
import os, sys
cnt = os.environ['CNT']
n = len(open(cnt).read()) + 1 if os.path.exists(cnt) else 1
open(cnt, 'a').write('x')
log = os.environ['ERRLOG']
seen = open(log, encoding='utf-8').read() if os.path.exists(log) else '(absent)'
probe = os.path.join(os.environ['PROBE'], 'errlog%d' % n)
open(probe, 'w', encoding='utf-8').write(seen)
sys.stderr.write('overloaded_error 529\\n')
sys.exit(1)
"""

# A reviewer whose FIRST attempt half-writes check-review.md into its sandbox and then
# loses its connection (stderr only, no stream event → transient), and whose second attempt
# comes back alive and writes $SECOND_WRITES — by default nothing at all, so the only file
# at that path is its dead predecessor's.
_REVIEWER = """\
import os, sys
cnt = os.environ['CNT']
n = len(open(cnt).read()) + 1 if os.path.exists(cnt) else 1
open(cnt, 'a').write('x')
if n == 1:
    open('check-review.md', 'w', encoding='utf-8').write(os.environ['FIRST_WRITES'])
    sys.stderr.write('connection reset by peer\\n')
    sys.exit(1)
if os.environ.get('SECOND_WRITES'):
    open('check-review.md', 'w', encoding='utf-8').write(os.environ['SECOND_WRITES'])
print('{"type": "result"}')
"""

# A reviewer that exits 0 having written nothing, ever — no dead predecessor either.
_SILENT_SUCCESS = """\
import os, sys
open(os.environ['CNT'], 'a').write('x')
print('{"type": "result"}')
"""

# A leaf whose captured stderr tail is whatever the case puts in $STDERR_TEXT — the tail
# `_format_leaf_attempt` embeds in the error log, and the same channel the #420 memory
# post-mortem rides in on (`leaves.py:663-665` appends it to `output`).
_NOISY = """\
import os, sys
open(os.environ['CNT'], 'a').write('x')
sys.stderr.write(os.environ['STDERR_TEXT'])
sys.exit(1)
"""

_REAL_SLEEP = time.sleep


def _skip_backoff(seconds: float) -> None:
    """Stand-in for `time.sleep` that skips only the retry BACKOFF (>= 1s), so a case
    driving a leaf to its attempt budget costs no wall clock — without weakening the
    wrapper's shipped defaults, and without turning `progress`' own 0.05s poll into a
    busy-wait."""
    if seconds < 1:
        _REAL_SLEEP(seconds)


def _leaf(script: str) -> LeafConfig:
    return LeafConfig(mode="command", family="claude",
                      argv=[sys.executable, "-c", script], interactive=False)


def _cfg(root: Path, reviewer: LeafConfig) -> Config:
    return Config(
        root=root, bundle_root=root / "results", process_dir=root / "process",
        templates_dir=root / "templates", default_branch="main", tracker_system="github",
        tracker_url="", issue_id_example="#1",
        builder=LeafConfig(mode="stub"), reviewer=reviewer,
        worktree=False)  # edit in place — keep the slice free of git


def _probe_attempts(root: Path, attempts: int = 3) -> dict[int, str]:
    """``{attempt: what the error log held while that attempt ran}``.

    Drives the production wrapper with the instrumented leaf above, in a fresh dir under
    ``root``. The observation is made from INSIDE the retry loop, which is the only vantage
    point from which a per-attempt flush is distinguishable from a post-loop write."""
    work = Path(tempfile.mkdtemp(dir=root))
    probe = work / "probe"
    probe.mkdir()
    log = work / "check-review.error.log"
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        leaves._invoke_leaf_resilient(
            _leaf(_PROBING), work, "review please", error_log=log,
            attempts=attempts, backoff=0.0, stream_json=True,
            env={"CNT": str(work / "count.txt"), "ERRLOG": str(log), "PROBE": str(probe)})
    seen = {}
    for n in range(1, attempts + 1):
        f = probe / f"errlog{n}"
        seen[n] = f.read_text(encoding="utf-8") if f.exists() else ""
    return seen


class AttemptRecordsLandBeforeTheNextAttemptStarts(unittest.TestCase):
    """Criterion (i). A retried leaf, and a post-mortem of a run killed mid-retry, must be
    able to read the predecessor's account — not a file that does not exist yet."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cnt = self.tmp / "count.txt"
        self.error_log = self.tmp / "check-review.error.log"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _runs(self) -> int:
        return len(self.cnt.read_text()) if self.cnt.exists() else 0

    def test_each_attempts_account_is_on_disk_before_the_next_one_starts(self) -> None:
        seen = _probe_attempts(self.tmp)
        self.assertEqual(seen[1], "(absent)")  # nothing has failed yet
        during_2 = seen[2]
        self.assertIn("attempt 1", during_2,
                      "attempt 2 ran with nothing on disk explaining attempt 1")
        self.assertIn("overloaded_error 529", during_2)
        self.assertIn("attempt 2", seen[3])

    def test_a_retry_never_starts_without_its_predecessors_account_on_disk(self) -> None:
        """The flush is a CONTINGENCY, not merely an ordering: attempt N+1 may start only
        once attempt N's account is durably on disk. A wrapper that writes best-effort and
        retries regardless leaves exactly the window it exists to close — the next attempt
        runs while nothing on disk explains the first, and a run killed in that window
        leaves the bundle no account of either."""
        real_write = Path.write_text
        log_name = self.error_log.name

        def refuse_the_log(self_, *a, **kw):
            if self_.name == log_name:
                raise OSError("read-only bundle")
            return real_write(self_, *a, **kw)

        err = io.StringIO()
        with mock.patch.object(Path, "write_text", refuse_the_log), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            leaves._invoke_leaf_resilient(
                _leaf(_TRANSIENT), self.tmp, "review please", error_log=self.error_log,
                attempts=3, backoff=0.0, stream_json=True, env={"CNT": str(self.cnt)})
        self.assertEqual(self._runs(), 1, "no second attempt over an unrecorded first")
        self.assertIn("could not write", err.getvalue())
        self.assertIn("not starting another attempt", err.getvalue())
        # …and the SAME leaf against a writable bundle does retry to its budget: what
        # stopped it above was the unrecorded predecessor, not the failure class.
        self.cnt.unlink()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves._invoke_leaf_resilient(
                _leaf(_TRANSIENT), self.tmp, "review please", error_log=self.error_log,
                attempts=3, backoff=0.0, stream_json=True, env={"CNT": str(self.cnt)})
        self.assertEqual(self._runs(), 3)


class _ReviewerHarness(unittest.TestCase):
    """Shared fixture: a bundle whose reviewer leaf is a real python3 child, driven through
    the production harvest site `leaves._run_review_sandboxed`. Only the retry backoff's
    wall clock is stood in for; the wrapper's shipped attempt budget is exercised as it
    ships."""

    TRUNCATED = "| Item | Verdict | Basis |\n| 1.1 Root cause | PA"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cnt = self.tmp / "count.txt"
        self.cfg = _cfg(self.tmp, _leaf(_REVIEWER))
        self.d = self.cfg.bundle("506")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text("- **Slug:** attempt-ownership\n", encoding="utf-8")
        (self.d / "patch.diff").write_text("--- a/x\n+++ b/x\n", encoding="utf-8")
        self.log = self.d / state.REVIEW_ERROR_LOG
        slept = mock.patch.object(leaves.time, "sleep", side_effect=_skip_backoff)
        slept.start()
        self.addCleanup(slept.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _runs(self) -> int:
        return len(self.cnt.read_text()) if self.cnt.exists() else 0

    def _review(self, *, first_writes: str = "", second_writes: str = "") -> str:
        """Run the reviewer harvest site end to end; return the bundle's check-review.md."""
        env = {"CNT": str(self.cnt), "SECOND_WRITES": second_writes,
               "FIRST_WRITES": first_writes or self.TRUNCATED}
        with mock.patch.dict(os.environ, env), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        return (self.d / "check-review.md").read_text(encoding="utf-8")


class DeadAttemptOutputIsNeverHarvested(_ReviewerHarness):
    """Criteria (ii) and (iii). The harvest copied its artifact `if produced.exists()`,
    with no notion of WHICH attempt wrote it — so a truncated verdict a dead attempt left
    in the sandbox was adopted as the output of the attempt that succeeded."""

    def test_a_dead_attempts_half_written_verdict_is_not_adopted_as_the_review(self) -> None:
        review = self._review()
        self.assertEqual(self._runs(), 2)  # the transient death was retried, as before
        self.assertNotIn("1.1 Root cause | PA", review)  # the dead attempt's file, refused
        self.assertIn("NOT COMPLETED", review)           # the honest verdict: none produced
        self.assertIn("NEEDS-HUMAN", review)

    def test_the_withdrawn_verdict_is_readable_in_the_bundle_afterwards(self) -> None:
        """Withdrawing a dead attempt's claim must not destroy its work: the sandbox it sat
        in is a TemporaryDirectory that dies with the run, so the text has to be kept in the
        bundle's own error log — and the placeholder must point at it. A real verdict must
        not be destroyed while the operator is told none was produced."""
        review = self._review()
        self.assertTrue(self.log.exists(),
                        "the dead attempt's text died with the sandbox — nothing kept it")
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("1.1 Root cause | PA", log)
        self.assertIn("check-review.md", log)  # named as what it was, and whose it was
        self.assertIn("attempt 1", log)
        self.assertIn(self.log.name, review)   # …and the placeholder sends the human there

    def test_the_live_attempts_own_artifact_is_still_harvested(self) -> None:
        # The ownership check must not cost a leaf its own work: a retry that RE-writes the
        # artifact is harvested exactly as today, and leaves no error log behind.
        review = self._review(second_writes="| Item | Verdict | Basis |\nfull verdict\n")
        self.assertIn("full verdict", review)
        self.assertNotIn("1.1 Root cause | PA", review)
        self.assertFalse(self.log.exists(), "a leaf that worked leaves no error log")

    def test_a_leaf_that_exits_zero_writing_nothing_still_degrades_as_today(self) -> None:
        # No dead predecessor, so there is nothing to preserve: the placeholder is the one
        # this site has always written, with no error log and no pointer to one.
        self.cfg.reviewer = _leaf(_SILENT_SUCCESS)
        review = self._review()
        self.assertEqual(self._runs(), 1)
        self.assertIn("NOT COMPLETED", review)
        self.assertIn("NEEDS-HUMAN", review)
        self.assertFalse(self.log.exists())
        self.assertNotIn(state.REVIEW_ERROR_LOG, review)


class AnInterruptedLeafIsRecoveredNotRetired(_ReviewerHarness):
    """Criteria (iv) and (v). An error log is the #138/#369 discriminator — "the leaf ran
    and FAILED". Flushing per attempt means one now also exists while a leaf is still
    retrying, so a log left mid-retry must read as INTERRUPTED (recover the leaf), a log a
    finished loop left must read as SPENT (leave it alone) — and neither a leaf's stderr nor
    a leaf's artifact may decide which."""

    def _bundle_with_log(self, text: str) -> Path:
        """A bundle carrying exactly that error log and no review — the state the #369
        recovery discriminator reads."""
        b = Path(tempfile.mkdtemp(dir=self.tmp))
        (b / state.REVIEW_ERROR_LOG).write_text(text, encoding="utf-8")
        return b

    def _harness_trailer(self) -> str:
        """The harness's own in-flight trailer, read off a log the harness actually wrote.
        Never named as a constant here: the impersonation legs below must use the real
        string, and asserting through it keeps them behavioural rather than a check that
        some symbol exists."""
        in_flight = _probe_attempts(self.tmp, attempts=2)[2]
        self.assertIn("overloaded_error 529", in_flight,
                      "no account of attempt 1 was on disk while the retry was pending")
        lines = [line.strip() for line in in_flight.splitlines() if line.strip()]
        trailer = lines[-1]
        self.assertNotIn("overloaded_error", trailer,
                         "the log's last line is the leaf's own text, not the harness's")
        return trailer

    def test_a_leaf_interrupted_mid_retry_is_recovered_not_retired(self) -> None:
        # The window this slice creates: the run dies between attempt 1's flush and attempt
        # 2 finishing. The bundle is left with an error log and no review — and if that
        # reads as "ran and failed", the reviewer is never re-run and the bundle reaches
        # sign-off with no review of the diff at all.
        in_flight = _probe_attempts(self.tmp, attempts=2)[2]
        self.assertIn("overloaded_error 529", in_flight)
        self.assertTrue(
            leaves.review_never_ran(self._bundle_with_log(in_flight)),
            "a reviewer the death window merely interrupted must still be recovered")

    def test_a_leaf_that_spent_its_attempts_is_still_not_re_run(self) -> None:
        # The other half of the #138/#369 discriminator, unchanged: a COMPLETE error log
        # means the leaf ran and gave up. Written here by the production wrapper itself, so
        # the two halves cannot drift apart.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves._invoke_leaf_resilient(
                _leaf(_TRANSIENT), self.tmp, "review please", error_log=self.log,
                attempts=2, backoff=0.0, stream_json=True, env={"CNT": str(self.cnt)})
        spent = self.log.read_text(encoding="utf-8")
        self.assertIn("overloaded_error 529", spent)
        self.assertFalse(leaves.review_never_ran(self._bundle_with_log(spent)),
                         "a leaf that ran out of attempts must not be re-run")

    def test_a_dead_attempts_artifact_ending_in_the_trailer_is_not_the_trailer(self) -> None:
        """Whether a run finished is a property of the harness's own trailer, never of what
        a leaf wrote — and in THIS repo a verdict quoting that marker is an ordinary day.
        The withdrawn artifact is embedded in the log, so one whose LAST line is the marker
        would otherwise be the log's last line and speak for the run that quoted it."""
        quoted = (f"| Item | Verdict | Basis |\n1.1 Root cause | PA\nthe log ends:\n"
                  f"{self._harness_trailer()}\n")
        self._review(first_writes=quoted)
        self.assertTrue(self.log.exists())
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("the log ends:", log)  # kept — the evidence is not destroyed
        self.assertFalse(
            leaves.review_never_ran(self._bundle_with_log(log)),
            "a leaf's own artifact declared the harness's loop unfinished, so a reviewer "
            "that already ran out of attempts would be paid for a second time")

    def test_a_leaf_whose_stderr_quotes_the_trailer_is_still_read_as_spent(self) -> None:
        """The same hazard through the other door: the tail `_format_leaf_attempt` writes is
        the leaf's OWN stderr — a builder editing this file, a reviewer quoting it — and the
        #420 memory post-mortem rides in on that same `output`. Neutralising the marker must
        leave every other byte of the tail intact."""
        post_mortem = "memory telemetry: peak 3.9G of 4.0G · 2 procs; kernel: oom-kill"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves._invoke_leaf_resilient(
                _leaf(_NOISY), self.tmp, "review please", error_log=self.log,
                attempts=2, backoff=0.0, stream_json=True,
                env={"CNT": str(self.cnt),
                     "STDERR_TEXT": f"{post_mortem}\n{self._harness_trailer()}\n"})
        log = self.log.read_text(encoding="utf-8")
        self.assertIn(post_mortem, log)  # the #420 post-mortem survives verbatim
        self.assertFalse(leaves.review_never_ran(self._bundle_with_log(log)),
                         "a leaf's stderr wrote the harness's in-flight trailer for it")


if __name__ == "__main__":
    unittest.main()
