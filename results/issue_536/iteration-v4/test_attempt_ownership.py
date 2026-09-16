"""An attempt is the unit of accountability (issue #506) — stdlib unittest, no deps.

Three leaves already retry (`_invoke_leaf_resilient`, #138), and nothing tied what a leaf
left behind to the *attempt that produced it*:

  * the attempt records were written only once the retry loop ended, so while attempt 2 ran
    there was nothing on disk explaining attempt 1 — and a run killed mid-retry lost them
    all, including the account a post-mortem would read. Nor did anything keep them once a
    later attempt came back alive but produced nothing: the `overloaded_error 529` was
    deleted one step before the operator was told the leaf "did not yield a usable verdict;
    do not assume an infra blip";
  * the three harvest sites copied their artifact on a bare `.exists()`, so a truncated
    verdict a DEAD attempt left in the sandbox was adopted as the output of the attempt
    that succeeded — no evidence filed as a verdict, which `engine/README.md` forbids;
  * an error log now exists WHILE a leaf's outcome is unsettled, so the #369 recovery
    discriminators must read "interrupted", not "gave up" — otherwise a reviewer the death
    window merely interrupted is retired and the bundle reaches sign-off with no review of
    the diff. And since the log quotes the leaf's own text (its stderr tail, a withdrawn
    artifact), a leaf must not be able to write the harness's in-flight trailer for it.

Because the marker is what makes an interrupted leaf recoverable, the kill windows around
it are tested as first-class cases (`_Kill` below): a flush caught half-done, and a leaf
that returned before its outcome reached the bundle.

Production path exercised — nothing here re-implements what it asserts, and every case runs
through a pre-existing entry point. Nothing this patch adds is imported at MODULE level
(only `pdca_harness.{assemble,leaves,state,config}`), so the file still loads — and the
assertions still bite — with the production change reverted; the two cases that must read
the record's own state (an account that is filed vs one still in flight) ask production for
it by name rather than re-deriving it here:

    AttemptRecordsLandBeforeTheNextAttemptStarts → leaves._invoke_leaf_resilient →
        _invoke → progress.run_with_heartbeat → subprocess (the "leaf" is a real python3
        child, instrumented to read the error log from INSIDE the retry loop)
    DeadAttemptOutputIsNeverHarvested            → leaves._run_review_sandboxed →
        _invoke_leaf_resilient → the site's `if produced.exists()` harvest
    BothAdvisoryHarvestsAreAttemptAwareToo       → leaves._run_advisory_sandboxed and
        leaves._run_plan_advisory_sandboxed — the reviewer's two near-identical twins,
        each asserted on BOTH halves (what it harvests, and how it leaves the account)
    AnInterruptedLeafIsRecoveredNotRetired       → the same, then leaves.review_never_ran
        and assemble._missing_review_text (the #369 discriminator and its third reader)

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
from contextlib import redirect_stderr, redirect_stdout, suppress
from pathlib import Path
from unittest import mock

from pdca_harness import assemble, leaves, state
from pdca_harness.config import Config, LeafConfig


class _Kill(BaseException):
    """The process stopping dead at one point — a SIGKILL, an OOM kill, a Ctrl-C.

    A ``BaseException`` on purpose: the harness catches ``Exception`` all over (a failed
    leaf must never crash the cycle), and a kill is precisely the thing no ``except`` gets
    to handle. Raised from inside a production write, it leaves the disk in exactly the
    state that write had reached — which is what these cases read back."""


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

# A leaf whose FIRST attempt writes $FIRST_WRITES into $ARTIFACT in its sandbox and then
# loses its connection (stderr only, no stream event → transient), and whose second attempt
# comes back alive and writes $SECOND_WRITES — by default nothing at all, so the only file at
# that path is its dead predecessor's. An EMPTY $FIRST_WRITES is the canonical transient
# death: the child dies at invocation, before it could write anything, leaving only a 529 on
# stderr. Drives all three harvest sites; only $ARTIFACT differs.
_WRITES_THEN_DIES = """\
import os, sys
cnt = os.environ['CNT']
n = len(open(cnt).read()) + 1 if os.path.exists(cnt) else 1
open(cnt, 'a').write('x')
if n == 1:
    if os.environ.get('FIRST_WRITES'):
        open(os.environ['ARTIFACT'], 'w', encoding='utf-8').write(os.environ['FIRST_WRITES'])
    sys.stderr.write('overloaded_error 529\\n')
    sys.exit(1)
if os.environ.get('SECOND_WRITES'):
    open(os.environ['ARTIFACT'], 'w', encoding='utf-8').write(os.environ['SECOND_WRITES'])
print('{"type": "result"}')
"""

# A leaf that exits 0 having written nothing, ever — no dead predecessor either.
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
        self.d = self.tmp / "bundle"          # what the #369 discriminator reads
        self.d.mkdir()
        self.cnt = self.tmp / "count.txt"
        self.error_log = self.d / state.REVIEW_ERROR_LOG

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
            # By PREFIX: an atomic write lands on a temp sibling of the log, and a bundle
            # this process cannot write refuses that file exactly as it refuses the log.
            if self_.name.startswith(log_name):
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

    def test_a_kill_during_a_flush_destroys_neither_the_marker_nor_the_predecessor(self):
        """The flush writes the very file the recovery discriminator reads, so a kill
        DURING it must not leave a state that lies about the run.

        Modelled at the syscall boundary, where the kill actually bites: the destination is
        opened for writing — which truncates it, as every write does first — and the process
        then stops before the bytes land. A non-atomic flush leaves an unmarked (here empty)
        log, and an unmarked log means "the leaf ran and gave up": the reviewer this window
        interrupted is never recovered, and the bundle can reach sign-off with no review of
        the diff — while attempt 1's account, the whole point of flushing early, is gone
        too. The base left NO log in this window and did recover, so nothing less than an
        atomic write keeps that guarantee."""
        real_write = Path.write_text
        log_name = self.error_log.name

        def die_mid_flush(self_, body, *a, **kw):
            if self_.name.startswith(log_name) and "attempt 2" in body:
                with self_.open("w"):      # the truncate every write does first…
                    pass
                raise _Kill("stopped between the truncate and the bytes")
            return real_write(self_, body, *a, **kw)

        with mock.patch.object(Path, "write_text", die_mid_flush), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                suppress(_Kill):           # a kill: nothing of this run runs after it
            leaves._invoke_leaf_resilient(
                _leaf(_TRANSIENT), self.tmp, "review please", error_log=self.error_log,
                attempts=3, backoff=0.0, stream_json=True, env={"CNT": str(self.cnt)})
        self.assertTrue(
            leaves.review_never_ran(self.d),
            "a kill inside the flush left a log reading 'ran and failed', so the reviewer "
            "it interrupted would never be re-run")
        # …and the complete record that HAD landed is still there, not truncated to a husk.
        self.assertTrue(self.error_log.exists(),
                        "the kill left nothing where a complete account already stood")
        self.assertIn("overloaded_error 529", self.error_log.read_text(encoding="utf-8"),
                      "the kill destroyed the predecessor's account the flush had landed")


class _ReviewerHarness(unittest.TestCase):
    """Shared fixture: a bundle whose reviewer leaf is a real python3 child, driven through
    the production harvest site `leaves._run_review_sandboxed`. Only the retry backoff's
    wall clock is stood in for; the wrapper's shipped attempt budget is exercised as it
    ships."""

    TRUNCATED = "| Item | Verdict | Basis |\n| 1.1 Root cause | PA"

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cnt = self.tmp / "count.txt"
        self.cfg = _cfg(self.tmp, _leaf(_WRITES_THEN_DIES))
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

    def _env(self, first_writes: str | None = None,
             second_writes: str = "") -> dict[str, str]:
        # `first_writes=""` is meaningful and NOT the default: it is the canonical transient
        # death, a child that died before it could write anything.
        return {"CNT": str(self.cnt), "SECOND_WRITES": second_writes,
                "ARTIFACT": "check-review.md",
                "FIRST_WRITES": self.TRUNCATED if first_writes is None else first_writes}

    def _review(self, *, first_writes: str | None = None, second_writes: str = "") -> str:
        """Run the reviewer harvest site end to end; return the bundle's check-review.md."""
        with mock.patch.dict(os.environ, self._env(first_writes, second_writes)), \
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

    def test_the_preserved_death_is_filed_as_the_infra_death_it_was(self) -> None:
        """#278's marker exists to stop exactly this inversion. The placeholder points the
        operator at a log reading `overloaded_error 529`, so it must not also tell them the
        leaf "ran but did not yield a usable verdict; do not assume an infra blip" —
        `assemble` keys the §6 row off that marker. The wrapper retries none but TRANSIENT
        failures, so a log that survives a successful return is by construction an infra
        death; no new information is needed to say so.

        The class is only half of it: the SENTENCE under the marker is what the operator
        reads, and this run's shape is "the retry came back alive and yielded nothing" —
        attempt 2 exited 0. A placeholder saying the retries "did not recover" describes
        the other shape, so it would be a false account of this run in a slice whose whole
        invariant is that the harness never files one. Asserting the class and a substring
        both sentences share would pass over exactly that defect."""
        review = self._review()
        self.assertEqual(self._runs(), 2)  # attempt 2 DID recover — it produced nothing
        self.assertIn(assemble.LEAF_STATUS_INFRA, review)
        self.assertNotIn(assemble.LEAF_STATUS_HUMAN, review)
        self.assertIn("safe to re-run", review)
        self.assertNotIn("retries did not recover", review)
        self.assertIn("came back alive and yielded nothing", review)

    def test_a_death_that_left_no_file_is_kept_and_classified_just_the_same(self) -> None:
        """The SHAPE THAT ACTUALLY OCCURS, and the one a rule keyed on a withdrawn *file*
        misses entirely: attempt 1 dies at invocation with `overloaded_error 529` and no
        artifact at all, attempt 2 comes back alive but produces nothing. There is no
        residue to withdraw — and if that is what decides whether the account survives, the
        529 is deleted one step before the placeholder tells the operator "substantive —
        needs a human … do not assume an infra blip" over a leaf that never reviewed
        anything. The evidence of a failure is kept, and it is filed as what it was."""
        review = self._review(first_writes="")
        self.assertEqual(self._runs(), 2)                 # the death WAS transient…
        self.assertIn("NOT COMPLETED", review)
        self.assertTrue(self.log.exists(),
                        "the only account of the death was deleted on the way out")
        self.assertIn("overloaded_error 529", self.log.read_text(encoding="utf-8"))
        self.assertIn(self.log.name, review)              # …the placeholder points at it…
        self.assertIn(assemble.LEAF_STATUS_INFRA, review)  # …and calls it infra, not human
        self.assertNotIn(assemble.LEAF_STATUS_HUMAN, review)

    def test_the_live_attempts_own_artifact_is_still_harvested(self) -> None:
        # The ownership check must not cost a leaf its own work: a retry that RE-writes the
        # artifact is harvested exactly as today, and leaves no error log behind.
        review = self._review(second_writes="| Item | Verdict | Basis |\nfull verdict\n")
        self.assertIn("full verdict", review)
        self.assertNotIn("1.1 Root cause | PA", review)
        self.assertFalse(self.log.exists(), "a leaf that worked leaves no error log")

    def test_a_log_that_cannot_be_removed_is_never_filed_as_a_failure(self) -> None:
        """The cleanup after a successful retry is a DISCARD, not a best-effort unlink.
        Swallow the removal failure and the log stands with the harness's in-flight trailer
        still on it; the harvest then settles that leftover, and the bundle archives ONE
        leaf as both a success (the verdict beside it) and a run that "ran and FAILED" — the
        conflation this whole change exists to remove. The leaf's own result is untouched
        either way: a log that cannot be removed must never turn a leaf that worked into a
        failure."""
        real_unlink = Path.unlink
        log_name = self.log.name
        err = io.StringIO()

        def refuse_the_log(self_, *a, **kw):
            # Only a REAL removal is refused, exactly as a filesystem would: the wrapper's
            # entry-time clear of a log that is not there still passes through.
            if self_.name == log_name and self_.exists():
                raise OSError("read-only bundle")
            return real_unlink(self_, *a, **kw)

        with mock.patch.object(Path, "unlink", refuse_the_log), \
                mock.patch.dict(os.environ, self._env(second_writes="full verdict\n")), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            leaves._run_review_sandboxed(self.d, self.cfg)
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertIn("full verdict", review)  # the leaf that worked is still a success…
        self.assertIn("could not remove", err.getvalue())   # …the operator is told…
        self.assertTrue(self.log.exists(), "retune: the removal landed after all")
        self.assertFalse(
            leaves._leaf_ran_and_failed(self.log),
            "the leftover was settled into a 'ran and failed' record beside the verdict "
            "the same leaf produced — one leaf archived as both success and failure")

    def test_a_leaf_that_exits_zero_writing_nothing_still_degrades_as_today(self) -> None:
        # No dead predecessor, so there is nothing to preserve: the placeholder is the one
        # this site has always written — same wording, same CLASS (a leaf that ran and
        # wrote nothing is substantive until something says otherwise), no error log and no
        # pointer to one.
        self.cfg.reviewer = _leaf(_SILENT_SUCCESS)
        review = self._review()
        self.assertEqual(self._runs(), 1)
        self.assertIn("NOT COMPLETED", review)
        self.assertIn("NEEDS-HUMAN", review)
        self.assertIn(assemble.LEAF_STATUS_HUMAN, review)
        self.assertNotIn(assemble.LEAF_STATUS_INFRA, review)
        self.assertFalse(self.log.exists())
        self.assertNotIn(state.REVIEW_ERROR_LOG, review)

    def test_an_artifact_that_cannot_be_withdrawn_stops_the_retries(self) -> None:
        """Withdrawal fails CLOSED. If a dead attempt's file cannot be removed, the wrapper
        no longer owns that path — and the one thing it must not do is run another attempt
        whose success would harvest the dead file as its own output. So the retries stop
        there, the operator is told why, and the text is still preserved."""
        real_unlink = Path.unlink
        err = io.StringIO()

        def refuse_the_artifact(self_, *a, **kw):
            if self_.name == "check-review.md":
                raise OSError("read-only sandbox")
            return real_unlink(self_, *a, **kw)

        with mock.patch.object(Path, "unlink", refuse_the_artifact), \
                mock.patch.dict(os.environ, self._env()), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            leaves._run_review_sandboxed(self.d, self.cfg)
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertEqual(self._runs(), 1,
                         "a second attempt ran over a file the wrapper could not withdraw")
        self.assertNotIn("1.1 Root cause | PA", review)
        self.assertIn("NEEDS-HUMAN", review)
        self.assertIn("could not withdraw", err.getvalue())
        self.assertIn("1.1 Root cause | PA", self.log.read_text(encoding="utf-8"))

    def test_a_refused_withdrawal_leaves_no_retry_pending_in_the_account(self) -> None:
        """The flush that PRECEDES the withdrawal says "a retry is pending" — true when it
        is written, false the moment the withdrawal is refused, because a path the wrapper
        no longer owns ends the run there. So the account is re-flushed as final, and a
        kill between the refusal and the placeholder finds a record that reads "ran and
        failed" rather than one promising an attempt that can never come."""
        real_unlink = Path.unlink
        real_write = Path.write_text
        bundle = self.d

        def refuse_the_artifact(self_, *a, **kw):
            if self_.name == "check-review.md":
                raise OSError("read-only sandbox")
            return real_unlink(self_, *a, **kw)

        def die_before_the_placeholder(self_, body, *a, **kw):
            if self_.name == "check-review.md" and self_.parent == bundle:
                raise _Kill("stopped between the refused withdrawal and the placeholder")
            return real_write(self_, body, *a, **kw)

        with mock.patch.object(Path, "unlink", refuse_the_artifact), \
                mock.patch.object(Path, "write_text", die_before_the_placeholder), \
                mock.patch.dict(os.environ, self._env()), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                suppress(_Kill):
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertFalse((self.d / "check-review.md").exists(),
                         "the kill landed after the outcome was filed — retune the case")
        self.assertIn("1.1 Root cause | PA", self.log.read_text(encoding="utf-8"))
        self.assertFalse(
            leaves.leaf_run_incomplete(self.log),
            "the account still promises a retry the wrapper has already ruled out")

    def test_a_kill_at_the_withdrawal_loses_neither_the_text_nor_the_account(self) -> None:
        """The withdrawal takes away the ONLY copy of the dead attempt's verdict — the
        sandbox holding it is a TemporaryDirectory that dies with the run — so the record
        that quotes it has to be on disk BEFORE the unlink, not after.

        Withdraw first and there is a window, however narrow, in which the artifact is gone
        and nothing accounts for it: a kill there leaves the bundle with no verdict, no
        residue and no record that an attempt ever ran (`runs=1`, no artifact, no error
        log) — precisely the no-artifact/no-account state this slice exists to remove.
        Modelled at the syscall the kill would land on."""
        real_unlink = Path.unlink

        def die_at_the_withdrawal(self_, *a, **kw):
            if self_.name == "check-review.md":
                raise _Kill("stopped between quoting the residue and unlinking it")
            return real_unlink(self_, *a, **kw)

        with mock.patch.object(Path, "unlink", die_at_the_withdrawal), \
                mock.patch.dict(os.environ, self._env()), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                suppress(_Kill):           # a kill: nothing of this run runs after it
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertEqual(self._runs(), 1, "the kill landed after a retry — retune the case")
        self.assertTrue(self.log.exists(),
                        "the kill left the bundle no account of the attempt that ran")
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("1.1 Root cause | PA", log,
                      "the dead attempt's verdict was taken away before it was preserved")
        self.assertIn("overloaded_error 529", log)
        self.assertTrue(
            leaves.review_never_ran(self.d),
            "the account the kill left reads as a leaf that gave up, so the reviewer this "
            "window interrupted would never be re-run")


class BothAdvisoryHarvestsAreAttemptAwareToo(unittest.TestCase):
    """Criterion (ii) at ALL THREE sites. The reviewer's two twins are near-identical code,
    and the difference that matters is invisible to a suite that drives only the reviewer:
    point `artifact=` at the BUNDLE path instead of the sandbox `out` and a dead attempt
    would unlink the previous round's shipped artifact while its residue — still standing in
    the sandbox — is harvested as the live attempt's work, with the suite still green."""

    TRUNCATED = "| Item | Verdict | Basis |\n| 1.1 Root cause | PA"
    SITES = ("advisory", "plan-advisory")

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cnt = self.tmp / "count.txt"
        self.cfg = _cfg(self.tmp, _leaf(_SILENT_SUCCESS))
        self.d = self.cfg.bundle("506")
        self.d.mkdir(parents=True)
        (self.d / "brief.md").write_text("- **Slug:** attempt-ownership\n", encoding="utf-8")
        slept = mock.patch.object(leaves.time, "sleep", side_effect=_skip_backoff)
        slept.start()
        self.addCleanup(slept.stop)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, kind: str, *, second_writes: str = "",
             script: str = _WRITES_THEN_DIES) -> tuple[Path, Path]:
        """Drive one advisory harvest site end to end; return ``(artifact, error_log)``."""
        leaf_id = "adversary"
        if kind == "advisory":
            artifact = leaves.advisory_artifact(self.d, leaf_id)
            error_log = leaves.advisory_error_log(self.d, leaf_id)
            site = leaves._run_advisory_sandboxed
        else:
            artifact = leaves.plan_advisory_artifact(self.d, leaf_id)
            error_log = self.d / f"plan-advisory-{leaf_id}.error.log"
            site = leaves._run_plan_advisory_sandboxed
        self.cnt.unlink(missing_ok=True)
        env = {"CNT": str(self.cnt), "ARTIFACT": artifact.name,
               "FIRST_WRITES": self.TRUNCATED, "SECOND_WRITES": second_writes}
        with mock.patch.dict(os.environ, env), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            site(self.d, self.cfg, _leaf(script),
                 {"id": leaf_id, "role": "refute it"}, leaf_id)
        return artifact, error_log

    def test_a_dead_attempts_artifact_is_not_harvested_at_either_site(self) -> None:
        for kind in self.SITES:
            with self.subTest(site=kind):
                artifact, error_log = self._run(kind)
                produced = artifact.read_text(encoding="utf-8")
                self.assertNotIn("1.1 Root cause | PA", produced,
                                 "a dead attempt's artifact was shipped as the leaf's own")
                self.assertIn("NEEDS-HUMAN", produced)
                self.assertIn("1.1 Root cause | PA",
                              error_log.read_text(encoding="utf-8"),
                              "the withdrawn text was destroyed instead of preserved")
                self.assertIn(assemble.LEAF_STATUS_INFRA, produced)
                # …and the other half of the site: the outcome is FILED, so the bytes left
                # in the bundle must stop claiming a retry is pending — one leaf described
                # two contradictory ways. Without this the two settle calls could be
                # deleted outright and the suite would stay green.
                self.assertFalse(
                    leaves.leaf_run_incomplete(error_log),
                    "the placeholder is filed, but the account still reads as in flight")

    def test_a_failed_flush_leaves_no_stale_marker_at_either_site(self) -> None:
        """The `err` branch of both twins, mirroring the reviewer's: attempt 1's in-flight
        flush lands, attempt 2's is refused, and the site files "the leaf failed" — over an
        account still marked as a run with a retry pending, unless the site settles what it
        filed. Asserted at both twins because they are near-identical code, and a suite
        that drives only the reviewer would stay green with either call deleted."""
        real_write = Path.write_text

        def refuse_the_second_flush(self_, body, *a, **kw):
            # By substring: an atomic write lands on a `<log>.tmp.<pid>` sibling first.
            if ".error.log" in self_.name and "attempt 2" in body:
                raise OSError("read-only bundle")
            return real_write(self_, body, *a, **kw)

        for kind in self.SITES:
            with self.subTest(site=kind):
                with mock.patch.object(Path, "write_text", refuse_the_second_flush):
                    artifact, error_log = self._run(kind, script=_TRANSIENT)
                self.assertEqual(len(self.cnt.read_text()), 2,
                                 "retune: attempt 2's flush is what must fail")
                self.assertIn("NEEDS-HUMAN", artifact.read_text(encoding="utf-8"))
                self.assertIn("overloaded_error 529",
                              error_log.read_text(encoding="utf-8"))
                self.assertFalse(
                    leaves.leaf_run_incomplete(error_log),
                    "a filed failure sits beside an account still claiming a retry is "
                    "pending")

    def test_a_live_attempts_artifact_is_still_harvested_at_either_site(self) -> None:
        for kind in self.SITES:
            with self.subTest(site=kind):
                artifact, error_log = self._run(kind, second_writes="the real finding\n")
                self.assertIn("the real finding", artifact.read_text(encoding="utf-8"))
                self.assertFalse(error_log.exists(),
                                 "a leaf that worked leaves no error log")


class AnInterruptedLeafIsRecoveredNotRetired(_ReviewerHarness):
    """Criteria (iv) and (v). An error log is the #138/#369 discriminator — "the leaf ran
    and FAILED". Flushing per attempt means one now also exists while a leaf's outcome is
    unsettled, so such a log must read as INTERRUPTED (recover the leaf), a log a finished,
    filed run left must read as SPENT (leave it alone) — and neither a leaf's stderr nor a
    leaf's artifact may decide which."""

    def _bundle_with_log(self, text: str) -> Path:
        """A bundle carrying exactly that error log and no review — the state the #369
        recovery discriminator reads."""
        b = Path(tempfile.mkdtemp(dir=self.tmp))
        (b / state.REVIEW_ERROR_LOG).write_text(text, encoding="utf-8")
        return b

    def _in_flight(self) -> str:
        """The bytes the production wrapper leaves on disk while a retry is pending."""
        seen = _probe_attempts(self.tmp, attempts=2)[2]
        self.assertIn("overloaded_error 529", seen,
                      "no account of attempt 1 was on disk while the retry was pending")
        return seen

    def _harness_trailer(self) -> str:
        """The harness's own in-flight trailer, read off a log the harness actually wrote.
        Never named as a constant here: the impersonation legs below must use the real
        string, and asserting through it keeps them behavioural rather than a check that
        some symbol exists."""
        lines = [line.strip() for line in self._in_flight().splitlines() if line.strip()]
        trailer = lines[-1]
        self.assertNotIn("overloaded_error", trailer,
                         "the log's last line is the leaf's own text, not the harness's")
        return trailer

    def test_a_leaf_interrupted_mid_retry_is_recovered_not_retired(self) -> None:
        # The window this slice creates: the run dies between attempt 1's flush and attempt
        # 2 finishing. The bundle is left with an error log and no review — and if that
        # reads as "ran and failed", the reviewer is never re-run and the bundle reaches
        # sign-off with no review of the diff at all.
        self.assertTrue(
            leaves.review_never_ran(self._bundle_with_log(self._in_flight())),
            "a reviewer the death window merely interrupted must still be recovered")

    def test_a_kill_before_the_outcome_is_filed_is_recovered_not_retired(self) -> None:
        """The second half of the same window, and the one an early "the loop is over" stamp
        re-opens: the retry came back ALIVE but wrote nothing, so the wrapper's kept log is
        the run's only account — and the bundle still has no review. A kill here must read
        as interrupted; stamp the log settled before the placeholder lands and the reviewer
        is retired with no verdict of any kind in the bundle."""
        real_write = Path.write_text
        bundle = self.d

        def die_before_the_placeholder(self_, body, *a, **kw):
            if self_.name == "check-review.md" and self_.parent == bundle:
                raise _Kill("stopped between the leaf's return and its harvest")
            return real_write(self_, body, *a, **kw)

        with mock.patch.object(Path, "write_text", die_before_the_placeholder), \
                mock.patch.dict(os.environ, self._env()), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), \
                suppress(_Kill):
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertFalse((self.d / "check-review.md").exists(),
                         "the kill landed after the outcome was filed — retune the case")
        self.assertTrue(leaves.review_never_ran(self.d),
                        "a Check the death window interrupted was recorded as spent, so "
                        "the bundle can reach sign-off with no review of the diff")
        self.assertIn("1.1 Root cause | PA", self.log.read_text(encoding="utf-8"))

    def test_a_filed_outcome_settles_the_account(self) -> None:
        """The other ordering. Once the outcome IS filed, the bytes left in the bundle must
        stop claiming the run is unfinished: the bundle is archived per round, and a record
        reading "a retry is pending" beside a filed verdict describes one leaf two
        contradictory ways.

        Deliberately NOT claimed: that this stops a spent leaf being re-run. It does not —
        the filed placeholder short-circuits every reader before the marker is consulted,
        which is why the assertion below reads the SETTLED BYTES in a bundle of their own
        rather than pretending the real one would recover. The load-bearing property is the
        ordering (settle only after the outcome lands), proven by the two kill cases around
        this one."""
        self._review()
        self.assertTrue(self.log.exists())
        settled = self.log.read_text(encoding="utf-8")
        self.assertFalse(leaves.review_never_ran(self._bundle_with_log(settled)),
                         "the outcome was filed, but the account still reads as in flight")

    def test_a_failed_flush_leaves_no_stale_marker_beside_a_filed_failure(self) -> None:
        """The loop's LAST write is what normally settles the account of a leaf that gave
        up — so when that write is the one the filesystem refuses, after an earlier
        attempt's in-flight write already landed, the marker of a retry that will never
        come is left standing while the bundle files "the leaf failed". One leaf, two
        contradictory records — the conflation this change removes — so the harvest settles
        the account it filed instead of trusting a write it knows may not have landed.

        (The existing write-failure case refuses every write from attempt 1 on, so it never
        creates the stale marker: nothing lands to leave one.)"""
        self.cfg.reviewer = _leaf(_TRANSIENT)   # dies transiently on every attempt
        real_write = Path.write_text
        log_name = self.log.name

        def refuse_the_second_flush(self_, body, *a, **kw):
            if self_.name.startswith(log_name) and "attempt 2" in body:
                raise OSError("read-only bundle")
            return real_write(self_, body, *a, **kw)

        with mock.patch.object(Path, "write_text", refuse_the_second_flush), \
                mock.patch.dict(os.environ, self._env()), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves._run_review_sandboxed(self.d, self.cfg)
        self.assertEqual(self._runs(), 2, "retune: attempt 2's flush is what must fail")
        review = (self.d / "check-review.md").read_text(encoding="utf-8")
        self.assertIn("NEEDS-HUMAN", review)          # the outcome IS filed…
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("overloaded_error 529", log)    # …attempt 1's account survives…
        self.assertFalse(
            leaves.leaf_run_incomplete(self.log),
            "a filed failure sits beside an account still claiming a retry is pending")

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
            "a leaf's own artifact declared the harness's run unfinished, so a reviewer "
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

    def test_a_marker_quoted_in_the_body_does_not_speak_for_the_run(self) -> None:
        """The marker is read off the log's LAST non-blank line, matched WHOLE — not sniffed
        for anywhere in the file, and not sought inside a line.

        The two impersonation cases above route their payload through the harness's own
        neutralisation first, so a substring sniff still passes them; these logs are written
        by hand for exactly that reason. Both are ordinary days in THIS repo — a reviewer
        discussing this mechanism, a builder pasting a log into its notes — and both accounts
        are COMPLETE: a leaf that ran out of attempts must stay retired, or every `advance`
        recovers and re-pays for it."""
        trailer = self._harness_trailer()
        quoted_in_the_body = (
            f"----- attempt 1 — exit 1 -----\nthe harness ends an unfinished log with\n"
            f"{trailer}\nand strips it once the outcome is filed\n\n"
            f"----- attempt 2 — exit 1 -----\noverloaded_error 529\n")
        quoted_inside_the_last_line = (
            f"----- attempt 1 — exit 1 -----\noverloaded_error 529\n"
            f"the log's final line mentions {trailer} in passing\n")
        for name, body in (("in the body", quoted_in_the_body),
                           ("inside the last line", quoted_inside_the_last_line)):
            with self.subTest(marker=name):
                self.assertFalse(
                    leaves.review_never_ran(self._bundle_with_log(body)),
                    "a marker QUOTED in a complete account declared the run unfinished, so "
                    "a leaf that gave up would be recovered and paid for again")

    def test_the_missing_review_note_calls_an_interrupted_leaf_not_yet_run(self) -> None:
        """The third reader of this one file: `assemble` writes the §6 note a human reads
        when the review is absent. It must not tell them the reviewer "RAN AND FAILED … fix
        the cause" about a leaf the death window interrupted, while the two recovery
        discriminators say the opposite about the same bytes."""
        note = assemble._missing_review_text(self._bundle_with_log(self._in_flight()))
        self.assertIn("NEVER RAN", note)
        self.assertNotIn("RAN AND FAILED", note)

    def test_the_missing_review_note_still_names_a_spent_leaf_ran_and_failed(self) -> None:
        # …and the other half is untouched: a settled log still reads "ran and failed", so
        # the operator is still told to fix the cause rather than wait for a re-run.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            leaves._invoke_leaf_resilient(
                _leaf(_TRANSIENT), self.tmp, "review please", error_log=self.log,
                attempts=2, backoff=0.0, stream_json=True, env={"CNT": str(self.cnt)})
        note = assemble._missing_review_text(
            self._bundle_with_log(self.log.read_text(encoding="utf-8")))
        self.assertIn("RAN AND FAILED", note)
        self.assertNotIn("NEVER RAN", note)


if __name__ == "__main__":
    unittest.main()
