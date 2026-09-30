"""A leaf's death is classified by what actually happened (issue #539) — stdlib unittest.

`LeafError.transient` used to be `not produced`: "did the child say anything?" standing in
for "did it die at invocation?". That proxy is wrong both ways. It refused to retry an
18-minute builder that did real work and *then* lost its API connection — the CLI's own
marked report named the cause, and the harness filed a substantive failure. And it retried
a leaf a signal killed before its first stream event — a memory-capped leaf OOM-killed at
start-up bought three more OOMs.

What this module holds the harness to, criterion by criterion:

* (i) a leaf whose stream ended on its MAIN session's marked report of a cause the vendor
  marked transient — a lost connection, an overload or 5xx, a rate-limit rejection — and
  then exited non-zero is retried, however much work came first;
* (ii) it is NOT retried when the vendor marked the cause permanent, stamped a kind this
  harness does not know, or stamped nothing; when the leaf merely quoted an error; when real
  main-session work followed the report (the CLI recovered); or when the report was a
  sub-agent's;
* (iii) a leaf a SIGNAL killed is never transient on the strength of having said nothing —
  as `-signum` from a direct child and as the shell's `128+signum` from a wrapper argv —
  while the harness's own wall-clock kill (`progress.TIMEOUT_RC`) keeps today's meaning;
* (iv) what the operator is told agrees with that: the retry line, the placeholder prose
  and the §6 label never say "did not run" / "no output" of a leaf that ran;
* (v) the report text is still retained, a recovered one included;
* (vi) nothing else moves — exit 0, a stream-less family, the codex format, `capture`.

Every case is a stub "leaf" that is a Python interpreter printing chosen stream events —
no vendor CLI, no API key, no network — driven through the production path
(`leaves._invoke_leaf_resilient` → `_invoke` → `progress.run_with_heartbeat`). Only API
that existed before this change is imported, so a red leg that reverts the fix fails on
assertions, never on an import. The event shapes are the vendor's; see
tests/fixtures/README.md for which are observed and which derived, and from which build.

Run from the project root: PYTHONPATH=src python -m unittest discover -s tests
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from pdca_harness import assemble, leaves, progress
from pdca_harness.config import LeafConfig

FIXTURES = Path(__file__).resolve().parent / "fixtures"

# The stub-leaf harness of tests/test_leaf_resilience.py, widened to die the ways a real
# leaf dies: argv is a python interpreter running an inline script; `_invoke` appends
# --output-format/--verbose (ignored) and feeds the prompt on stdin. The script counts its
# invocations into $CNT, prints $STREAM to stdout and $ERR to stderr, may sleep $SLEEP
# seconds, then either kills ITSELF with signal $SIG or exits $RC.
_STUB = (
    "import os,signal,sys,time\n"
    "open(os.environ['CNT'],'a').write('x')\n"
    "sys.stdout.write(os.environ['STREAM'])\n"
    "sys.stdout.flush()\n"
    "sys.stderr.write(os.environ['ERR'])\n"
    "sys.stderr.flush()\n"
    "time.sleep(float(os.environ.get('SLEEP') or 0))\n"
    "if os.environ.get('SIG'):\n"
    "    os.kill(os.getpid(), getattr(signal, os.environ['SIG']))\n"
    "sys.exit(int(os.environ['RC']))\n"
)


def _leaf() -> LeafConfig:
    return LeafConfig(mode="command", family="claude",
                      argv=[sys.executable, "-c", _STUB], interactive=False)


def _wrapped_leaf() -> LeafConfig:
    """The same stub behind a real WRAPPER argv: the shell forks it (the trailing `exit`
    stops the shell exec-ing it), so a signal that kills the stub reaches the harness as
    the shell's own exit status, 128 + signum — the `docker run` / `sh -c` spelling."""
    return LeafConfig(mode="command", family="claude",
                      argv=["sh", "-c", '"$0" -c "$1"; exit $?', sys.executable, _STUB],
                      interactive=False)


# ---------------------------------------------------------------------------------
# Stream events, in the shapes claude-code emits them (tests/fixtures/README.md).
# ---------------------------------------------------------------------------------
def _text(text: str) -> dict:
    return {"content": [{"type": "text", "text": text}]}


# Main-session work: the main loop's emitters hard-code `parent_tool_use_id: null`, and
# a main-session tool result arrives as a `user` event.
_WORK = {"type": "assistant", "parent_tool_use_id": None, "message": _text("Editing x.py")}
_TOOL_USE = {"type": "assistant", "parent_tool_use_id": None,
             "message": {"content": [{"type": "tool_use", "id": "toolu_01Main",
                                      "name": "Bash", "input": {"command": "make test"}}]}}
_TOOL_RESULT = {"type": "user", "parent_tool_use_id": None,
                "message": {"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": "toolu_01Main",
                     "content": "Ran 12 tests. FAILED (failures=1)"}]}}
# A sub-agent's traffic, forwarded with the Task's tool_use id.
_SUB_WORK = {"type": "assistant", "parent_tool_use_id": "toolu_01Task",
             "message": _text("sub-agent still draining")}
_SUB_TOOL_RESULT = {"type": "user", "parent_tool_use_id": "toolu_01Task",
                    "message": {"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": "toolu_02Sub",
                         "content": "ok"}]}}

_LOST = "API Error: Connection lost mid-response. The response above may be incomplete."
# Prose that names every transient category — used where a PERMANENT (or unreadable)
# cause must not be promoted by what its text happens to say.
_TEMPTING = ("API Error: 400 the service was overloaded (503), a rate limit hit, and the "
             "connection was lost mid-response")


def _report(kind: str | None = "server_error", text: str = _LOST, **extra) -> dict:
    """The CLI's own marked report of an API error, from the MAIN session."""
    ev = {"type": "assistant", "parent_tool_use_id": None, "is_api_error_message": True,
          "message": _text(text)}
    if kind is not None:
        ev["error"] = kind
    ev.update(extra)
    return ev


def _wrapup(subtype: str = "success", status: int | None = None,
            text: str = _LOST) -> dict:
    """The session's `result` record. Only the `success` variant carries the HTTP status
    of the API error that ended it; an `error_*` variant carries an `errors` list."""
    ev: dict = {"type": "result", "subtype": subtype, "is_error": True}
    if subtype == "success":
        ev["result"] = text
    else:
        ev["errors"] = [text]
    if status is not None:
        ev["api_error_status"] = status
    return ev


def _stream(*events: dict) -> str:
    return "".join(json.dumps(ev) + "\n" for ev in events)


@contextlib.contextmanager
def _stdout_fd_to(path: Path):
    """Point this process's fd 1 at ``path`` — a stream-less leaf inherits stdout, and its
    output must not land in the suite's own (a gate reads that as the run's verdict)."""
    sys.stdout.flush()
    saved = os.dup(1)
    with open(path, "w", encoding="utf-8") as sink:
        os.dup2(sink.fileno(), 1)
    try:
        yield
    finally:
        sys.stdout.flush()
        os.dup2(saved, 1)
        os.close(saved)


class _StubLeafCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.cnt = self.tmp / "count.txt"
        self.error_log = self.tmp / "check-review.error.log"
        self.stderr = ""

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _env(self, stream: str, err: str, rc: int, sig: str, sleep: float) -> dict:
        return {"CNT": str(self.cnt), "STREAM": stream, "ERR": err, "RC": str(rc),
                "SIG": sig, "SLEEP": str(sleep)}

    def _run(self, stream: str, *, err: str = "", rc: int = 1, sig: str = "",
             leaf: LeafConfig | None = None, stream_json: bool = True):
        """Through the production leaf path, with the shipped attempt budget spelled as
        tests/test_leaf_resilience.py spells it. Keeps what the harness printed."""
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            err_ = leaves._invoke_leaf_resilient(
                leaf or _leaf(), self.tmp, "review please", error_log=self.error_log,
                attempts=3, backoff=0.0, stream_json=stream_json,
                env=self._env(stream, err, rc, sig, 0))
        self.stderr = buf.getvalue()
        return err_

    def _heartbeat(self, stream: str, *, rc: int = 1, sleep: float = 0,
                   timeout: int | None = None, capture: bool = False,
                   fmt: str = "claude-stream-json"):
        env = {**os.environ, **self._env(stream, "", rc, "", sleep)}
        with contextlib.redirect_stderr(io.StringIO()):
            return progress.run_with_heartbeat(
                [sys.executable, "-c", _STUB], env=env, capture=capture, stream_json=True,
                tee_stderr=True, stream_format=fmt, timeout=timeout)

    def _runs(self) -> int:
        return len(self.cnt.read_text()) if self.cnt.exists() else 0

    def _log(self) -> str:
        self.assertTrue(self.error_log.exists(), "no error log was written")
        return self.error_log.read_text(encoding="utf-8")

    def _assert_retried(self, err) -> None:
        self.assertIsInstance(err, leaves.LeafError)
        self.assertTrue(err.transient, f"expected transient; rc={err.returncode}")
        self.assertEqual(self._runs(), 3, "a transient death is retried to the budget")
        self.assertEqual(leaves._failure_class(err), leaves._FAIL_TRANSIENT)

    def _assert_not_retried(self, err) -> None:
        self.assertIsInstance(err, leaves.LeafError)
        self.assertFalse(err.transient, f"expected substantive; rc={err.returncode}")
        self.assertEqual(self._runs(), 1, "a non-transient death is not re-run")
        self.assertEqual(leaves._failure_class(err), leaves._FAIL_SUBSTANTIVE)


class TransientCauseAfterWorkIsRetried(_StubLeafCase):
    """(i) the vendor marked the cause transient ⇒ retried, however much work came first."""

    def test_a_lost_connection_after_real_work_is_retried(self) -> None:
        # The incident: work, then the CLI's own report of the dropped connection, exit 1.
        self._assert_retried(self._run(_stream(_WORK, _TOOL_USE, _TOOL_RESULT, _report())))

    def test_however_much_work_came_first(self) -> None:
        long_session = [_WORK, _TOOL_USE, _TOOL_RESULT] * 60
        self._assert_retried(self._run(_stream(*long_session, _report())))

    def test_each_kind_the_vendor_treats_as_transient(self) -> None:
        # claude-code's own transient kinds (tests/fixtures/README.md): the connection /
        # 5xx kind, the overload kind, and the mid-session rate-limit rejection.
        for kind in ("server_error", "overloaded", "rate_limit"):
            with self.subTest(kind=kind):
                self.cnt.unlink(missing_ok=True)
                self._assert_retried(self._run(_stream(_WORK, _report(kind))))

    def test_an_unclassified_report_whose_text_names_a_lost_connection(self) -> None:
        # `unknown` is the vendor saying "I could not classify this": the one kind whose
        # text is read, and only for the categories the harness promises to retry.
        self._assert_retried(self._run(_stream(_WORK, _report("unknown",
                                                              "API Error: terminated"))))

    def test_the_wrapup_that_follows_the_report_does_not_bury_its_cause(self) -> None:
        # The `result` wrap-up names the effect; the report before it names the cause.
        for wrap in (_wrapup(), _wrapup("error_during_execution",
                                        text="[ede_diagnostic] turn aborted")):
            with self.subTest(wrapup=wrap["subtype"]):
                self.cnt.unlink(missing_ok=True)
                self._assert_retried(self._run(_stream(_WORK, _report(), wrap)))

    def test_a_wrapup_carrying_a_429(self) -> None:
        # 429 is not in the 5xx range, so only the transient-status set can admit it.
        self._assert_retried(self._run(_stream(_WORK, _wrapup(status=429))))

    def test_a_wrapup_carrying_a_5xx(self) -> None:
        self._assert_retried(self._run(_stream(_WORK, _wrapup(status=503))))

    def test_a_sub_agent_that_keeps_draining_does_not_clear_the_report(self) -> None:
        # Only MAIN-session work means the CLI recovered: a Task's trailing traffic is not
        # the session carrying on.
        self._assert_retried(self._run(_stream(_WORK, _report(), _SUB_WORK,
                                               _SUB_TOOL_RESULT)))


class NotEveryReportIsTransient(_StubLeafCase):
    """(ii) permanent, unknown-to-us, unstamped, quoted, recovered or a sub-agent's ⇒ not."""

    def test_a_permanent_cause_is_not_promoted_by_its_prose(self) -> None:
        for kind in ("invalid_request", "authentication_failed", "billing_error",
                     "model_not_found"):
            with self.subTest(kind=kind):
                self.cnt.unlink(missing_ok=True)
                self._assert_not_retried(self._run(_stream(_WORK, _report(kind,
                                                                          _TEMPTING))))

    def test_a_kind_this_harness_does_not_recognise(self) -> None:
        self._assert_not_retried(self._run(_stream(_WORK, _report("quota_v2", _TEMPTING))))

    def test_a_report_the_vendor_left_unstamped(self) -> None:
        # No `error` kind at all: the message never went through the vendor's mapper, so
        # there is no vendor judgement to follow — and prose is not one.
        self._assert_not_retried(self._run(_stream(_WORK, _report(None, _LOST))))

    def test_an_unclassified_report_outside_the_categories(self) -> None:
        self._assert_not_retried(self._run(_stream(
            _WORK, _report("unknown", "API Error: Unexpected token in the body"))))

    def test_an_unclassified_report_the_vendor_typed_is_not_read_as_prose(self) -> None:
        # claude-code stamps `unknown` plus a typed `api_error` for a gateway sign-in
        # or credential failure: the vendor did type the cause, so its text is not read.
        self._assert_not_retried(self._run(_stream(_WORK, _report(
            "unknown", "API Error: gateway session timed out; connection lost",
            api_error="gateway_session_expired"))))

    def test_a_leaf_that_merely_quotes_an_error_is_untouched(self) -> None:
        # An UNMARKED assistant message is the leaf talking, whatever it says.
        quoted = {"type": "assistant", "parent_tool_use_id": None, "error": "server_error",
                  "message": _text(_LOST)}
        self._assert_not_retried(self._run(_stream(_WORK, quoted)))

    def test_recovered_through_more_assistant_work(self) -> None:
        self._assert_not_retried(self._run(_stream(_WORK, _report(), _WORK)))

    def test_recovered_through_a_main_session_tool_cycle(self) -> None:
        # A main-session tool result is a `user` event: the CLI recovered, ran a tool, and
        # the leaf then failed on its own merits.
        self._assert_not_retried(self._run(_stream(_WORK, _report(), _TOOL_RESULT)))

    def test_a_sub_agents_report_never_classifies(self) -> None:
        sub = _report("overloaded", parent_tool_use_id="toolu_01Task")
        side = {**_report("overloaded"), "isSidechain": True}
        del side["parent_tool_use_id"]  # the transcript spelling carries no such key
        for name, ev in (("stream", sub), ("transcript", side)):
            with self.subTest(spelling=name):
                self.cnt.unlink(missing_ok=True)
                self._assert_not_retried(self._run(_stream(_WORK, ev)))

    def test_the_status_on_an_execution_error_wrapup_is_not_read(self) -> None:
        # Only the `success` wrap-up is the CLI's "this session ended on my API-error
        # message"; an `error_*` one ends on whatever threw, whatever status it carries.
        wrap = {**_wrapup("error_during_execution", text="turn aborted"),
                "api_error_status": 503}
        self._assert_not_retried(self._run(_stream(_WORK, wrap)))

    def test_a_wrapup_status_no_retry_can_clear(self) -> None:
        for status in (400, None):
            with self.subTest(status=status):
                self.cnt.unlink(missing_ok=True)
                self._assert_not_retried(self._run(_stream(_WORK, _wrapup(status=status))))

    def test_the_leafs_newer_account_of_its_death_wins(self) -> None:
        self._assert_not_retried(self._run(_stream(_WORK, _report(),
                                                   _report("invalid_request", _TEMPTING))))

    def test_a_wrapup_status_cannot_overrule_the_reported_cause(self) -> None:
        self._assert_not_retried(self._run(_stream(
            _WORK, _report("invalid_request", _TEMPTING), _wrapup(status=503))))


class SignalDeathIsNotTransient(_StubLeafCase):
    """(iii) the manner of the kill: a signal death is never re-run for having said
    nothing, in either returncode spelling; the harness's own timeout keeps its meaning."""

    def test_a_silent_leaf_killed_by_sigkill_is_not_re_run(self) -> None:
        err = self._run("", err="", sig="SIGKILL")
        self.assertEqual(err.returncode, -9)
        self._assert_not_retried(err)

    def test_a_silent_leaf_killed_by_sigterm_is_not_re_run(self) -> None:
        err = self._run("", sig="SIGTERM")
        self.assertEqual(err.returncode, -15)
        self._assert_not_retried(err)

    def test_the_wrapper_spelling_of_a_sigkill(self) -> None:
        # A real wrapper argv: the shell outlives the killed stub and exits 128 + 9.
        err = self._run("", sig="SIGKILL", leaf=_wrapped_leaf())
        self.assertEqual(err.returncode, 137)
        self._assert_not_retried(err)

    def test_a_bare_exit_137_is_read_as_the_same_death(self) -> None:
        err = self._run("", rc=137)
        self._assert_not_retried(err)

    def test_the_kill_outranks_a_transient_report(self) -> None:
        # What ended the leaf was the signal, not the API it reported on.
        self._assert_not_retried(self._run(_stream(_WORK, _report()), sig="SIGKILL"))

    def test_an_ordinary_silent_death_is_still_retried(self) -> None:
        # #138 unchanged: a non-zero exit before any work, no signal involved. 128 is the
        # shell's base alone (no signal 0) and 255 is past every signal number.
        for rc in (1, 2, 128, 255):
            with self.subTest(rc=rc):
                self.cnt.unlink(missing_ok=True)
                err = self._run("", err="overloaded_error 529\n", rc=rc)
                self.assertEqual(err.returncode, rc)
                self._assert_retried(err)

    def test_the_harness_timeout_keeps_todays_meaning(self) -> None:
        # TIMEOUT_RC is "the oracle did not answer": a silent timed-out leaf reads
        # transient as before, and one that worked is not re-labelled by its stream.
        self.assertTrue(leaves.LeafError(progress.TIMEOUT_RC, ["x"],
                                         produced=False).transient)
        self.assertFalse(leaves.LeafError(progress.TIMEOUT_RC, ["x"],
                                          produced=True).transient)
        rc, _, produced = self._heartbeat(_stream(_WORK, _report()), sleep=30, timeout=1)
        self.assertEqual(rc, progress.TIMEOUT_RC)
        self.assertTrue(produced)


class WhatTheOperatorIsTold(_StubLeafCase):
    """(iv) every message about the decision states the same true thing."""

    def test_the_retry_line_does_not_say_no_output_of_a_leaf_that_worked(self) -> None:
        self._run(_stream(_WORK, _report()))
        self.assertIn("retry 1/2", self.stderr)
        self.assertNotIn("no output", self.stderr)

    def test_the_section6_row_for_the_headline_leaf(self) -> None:
        # From the stream to the row the human reads at sign-off.
        err = self._run(_stream(_WORK, _TOOL_USE, _TOOL_RESULT, _report()))
        with contextlib.redirect_stderr(io.StringIO()):
            leaves._review_unavailable(self.tmp, f"reviewer leaf failed: {err}",
                                       failure=leaves._failure_class(err),
                                       error_log=self.error_log)
        text = (self.tmp / "check-review.md").read_text(encoding="utf-8")
        self.assertEqual(assemble.leaf_status(text), assemble.LEAF_STATUS_INFRA)
        items = assemble._items_from_artifact(text)
        self.assertTrue(items)
        for it in items:
            self.assertNotIn("did not run", it.text)
            self.assertIn("safe to re-run", it.text)

    def test_the_label_and_the_placeholder_name_both_shapes(self) -> None:
        label = assemble._LEAF_STATUS_LABEL[assemble.LEAF_STATUS_INFRA]
        prose = leaves._unavailable_classification(leaves._FAIL_TRANSIENT, None)
        for said in (label, prose):
            with self.subTest(said=said[:40]):
                self.assertNotIn("did not run", said)
                self.assertNotIn("with no output", said)
                self.assertIn("before", said)   # died before emitting any work …
                self.assertIn("report", said)   # … or on its own transient report


class RetentionIsUnchanged(_StubLeafCase):
    """(v) child-1's retention holds under the new verdict."""

    def test_every_attempt_keeps_its_report(self) -> None:
        self._run(_stream(_WORK, _report()))
        self.assertEqual(self._log().count(_LOST), 3)

    def test_a_recovered_report_is_kept_though_it_is_not_the_verdict(self) -> None:
        self._assert_not_retried(self._run(_stream(_WORK, _report(), _TOOL_RESULT)))
        self.assertIn(_LOST, self._log())
        self.assertNotIn("(no output captured)", self._log())


class NothingElseChanges(_StubLeafCase):
    """(vi) the verdict moves nothing but the retry decision on a failed run."""

    def test_a_leaf_that_exits_zero_is_reported_as_today(self) -> None:
        for stream in (_stream(_WORK, _report()), _stream(_report(), _WORK)):
            with self.subTest(stream=stream[:30]):
                self.cnt.unlink(missing_ok=True)
                self.assertIsNone(self._run(stream, rc=0))
                self.assertEqual(self._runs(), 1)
                self.assertFalse(self.error_log.exists())

    def test_exit_zero_keeps_produced_as_it_was(self) -> None:
        # The verdict describes a run that FAILED: a session that ended on a transient
        # report and still exited 0 did work, and `produced` keeps saying so.
        rc, _, produced = self._heartbeat(_stream(_WORK, _report()), rc=0)
        self.assertEqual(rc, 0)
        self.assertTrue(produced)

    def test_a_stream_less_family_still_reports_substantive(self) -> None:
        # No stream parse, so no verdict: the `produced=True` fallback is untouched.
        with _stdout_fd_to(self.tmp / "inherited-stdout.txt"):
            err = self._run(_stream(_WORK, _report()), stream_json=False)
        self._assert_not_retried(err)

    def test_the_codex_format_does_not_read_a_claude_report(self) -> None:
        codex_work = {"type": "item.completed", "item": {"type": "agent_message"}}
        _, _, produced = self._heartbeat(_stream(codex_work, _report()),
                                         fmt="codex-stream-json")
        self.assertTrue(produced)

    def test_capture_still_returns_the_childs_raw_stdout(self) -> None:
        stream = _stream(_WORK, _report())
        _, output, _ = self._heartbeat(stream, capture=True)
        self.assertEqual(output, stream)


class PinnedVendorRecords(_StubLeafCase):
    """The same rules against bytes a real CLI wrote (tests/fixtures/README.md)."""

    def _fixture(self, name: str) -> str:
        path = FIXTURES / name
        if not path.is_file():
            self.skipTest(f"pinned vendor fixture {name} is not present")
        return path.read_text(encoding="utf-8")

    def test_the_observed_incident_record_after_work_is_retried(self) -> None:
        record = self._fixture("claude_api_error_death.stream.jsonl")
        self._assert_retried(self._run(_stream(_WORK) + record))

    def test_the_observed_permanent_record_after_work_is_not(self) -> None:
        record = self._fixture("claude_api_error_permanent.stream.jsonl")
        self._assert_not_retried(self._run(_stream(_WORK) + record))


if __name__ == "__main__":
    unittest.main()
