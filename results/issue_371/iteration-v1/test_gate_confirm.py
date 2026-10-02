"""Confirm-once for a failed gating row (issue #371, stdlib unittest).

A gating row is ONE sample. A downstream instance lost a round's verdict to a single
`cargo test` red that six earlier rounds, the C4 run seconds later, the reviewer's own run
and a manual re-run all contradicted. The harness already records "the oracle gave no
answer" as `unverifiable` (#46, #368); a fail contradicted by an immediate pass of the
same command is the same situation one step later. So at Check a failed gating row is
re-run exactly once and both samples are kept:

  (1) fail → pass  ⇒ `pass` + `flaky`, `attempts = ["fail", "pass"]`, two runs;
  (2) fail → fail  ⇒ `fail` with the confirm run's evidence;
  (3) fail → no clean answer (timeout / unverifiable / deferred / exception) ⇒ the first
      `fail` stands with the FIRST run's evidence; `attempts` names the second outcome;
  (4) bounds — one confirm only; non-gating / passing / cmd_error / raised-first rows run
      once; `[gates] confirm_gating_fail = false` and a per-row `confirm_fail = false`
      (on `[[gates.checks]]` AND `[gates] host_ci`) turn it off;
  (4b) Check only — `run_gates` / `run_gates_dry`; the working-tree, integration and
      publish host-CI re-gates (which call `_run_one` with the switch off) run once;
  (5) the gate log holds both runs, each in its own block;
  (6) a `flaky` row becomes one HUMAN §6 item; `overall` counts it as a pass.

Real gate commands through the real `gates._run_one` — a small shell script that counts
its own runs in a marker file. No Claude / Docker. Run from the template root:
PYTHONPATH=src python3 -m unittest tests.test_gate_confirm
"""

from __future__ import annotations

import json
import shlex
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pdca_harness import assemble, gates, progress
from pdca_harness.config import Config, LeafConfig


def _stub_config(root: Path) -> Config:
    # Mirrors tests/test_gate_logs.py:_stub_config.
    return Config(
        root=root,
        bundle_root=root / "results",
        process_dir=root / "process",
        templates_dir=root / "templates",
        default_branch="main",
        tracker_system="github",
        tracker_url="",
        issue_id_example="#1",
        builder=LeafConfig(mode="stub", family="claude"),
        reviewer=LeafConfig(mode="stub", family="codex"),
    )


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cfg = _stub_config(self.tmp)
        self.marker = self.tmp / "runs"

    # A command that appends one line per run to the marker, prints `run-<n>`, then runs
    # the shell `tail` with $n bound to the run number (1-based).
    def _cmd(self, tail: str) -> str:
        m = shlex.quote(str(self.marker))
        return (f"echo x >> {m}; n=$(wc -l < {m} | tr -d ' '); "
                f"echo \"output-of-run-$n\"; {tail}")

    def flaky_cmd(self) -> str:  # fails on run 1, passes from run 2 on
        return self._cmd('echo "evidence-run-$n"; [ "$n" -ge 2 ]')

    def runs(self) -> int:
        if not self.marker.exists():
            return 0
        return len(self.marker.read_text().splitlines())

    def _bundle(self, iid: str = "B") -> Path:
        d = self.cfg.bundle(iid)
        d.mkdir(parents=True)
        (d / "brief.md").write_text("- **Slug:** gc\n", encoding="utf-8")
        (d / "patch.diff").write_text("--- a\n+++ b\n", encoding="utf-8")
        return d

    def _chk(self, cmd: str, **kw) -> dict:
        return {"id": "C4-confirm", "tier": "C4", "label": "verify", "scope": "bundle",
                "gating": True, "cmd": cmd, **kw}

    def _row(self, result: dict, rule_id: str = "C4-confirm") -> dict:
        return next(r for r in result["rows"] if r["rule_id"] == rule_id)

    def _check_run(self, chk: dict) -> dict:
        """The row as the Check matrix records it (run_gates — the confirming caller)."""
        self.cfg.gates_checks = [chk]
        self.result = gates.run_gates(self._bundle(), self.cfg)
        return self._row(self.result)


# -- (1) / (2) / (3): the combination rule -------------------------------------------

class CombinationRule(_Base):
    def test_fail_then_pass_records_pass_flaky_after_two_runs(self) -> None:
        row = self._check_run(self._chk(self.flaky_cmd()))
        self.assertEqual(self.runs(), 2, "the failed gating row was not re-run exactly once")
        self.assertEqual(row["result"], "pass")
        self.assertIs(row.get("flaky"), True)
        self.assertEqual(row.get("attempts"), ["fail", "pass"])
        self.assertEqual(self.result["overall"], "pass")

    def test_fail_then_fail_records_fail_with_confirm_run_evidence(self) -> None:
        row = self._check_run(self._chk(self._cmd('echo "evidence-run-$n"; exit 1')))
        self.assertEqual(self.runs(), 2)
        self.assertEqual(row["result"], "fail")
        self.assertFalse(row.get("flaky"))
        self.assertEqual(row.get("attempts"), ["fail", "fail"])
        self.assertEqual(row["path_line"], "evidence-run-2")
        self.assertEqual(self.result["overall"], "fail")

    def _first_fail_stands(self, row: dict, second: str) -> None:
        self.assertEqual(self.runs(), 2)
        self.assertEqual(row["result"], "fail")
        self.assertFalse(row.get("flaky"))
        self.assertEqual(row.get("attempts"), ["fail", second])
        self.assertEqual(row["path_line"], "evidence-run-1")
        self.assertEqual(self.result["overall"], "fail")

    def test_fail_then_timeout_first_fail_stands(self) -> None:
        tail = 'if [ "$n" -ge 2 ]; then sleep 5; fi; echo "evidence-run-$n"; exit 1'
        row = self._check_run(self._chk(self._cmd(tail), timeout_secs=1))
        self._first_fail_stands(row, "unverifiable")

    def test_fail_then_unverifiable_first_fail_stands(self) -> None:
        tail = ('if [ "$n" -ge 2 ]; then echo "PDCA-UNVERIFIABLE: no oracle"; exit 77; fi; '
                'echo "evidence-run-$n"; exit 1')
        row = self._check_run(self._chk(self._cmd(tail)))
        self._first_fail_stands(row, "unverifiable")

    def test_fail_then_deferred_first_fail_stands(self) -> None:
        # A bundle-scoped T4 row is re-gated at publish, so it may declare `deferred`
        # (gates._deferrable → publish.publish_gates).
        tail = ('if [ "$n" -ge 2 ]; then echo "PDCA-DEFERRED: audited at publish"; exit 0; fi; '
                'echo "evidence-run-$n"; exit 1')
        chk = {"id": "T4-confirm", "tier": "T4", "label": "contrib", "scope": "bundle",
               "gating": True, "cmd": self._cmd(tail)}
        self.cfg.gates_checks = [chk]
        self.result = gates.run_gates(self._bundle(), self.cfg)
        self._first_fail_stands(self._row(self.result, "T4-confirm"), "deferred")

    def test_fail_then_exception_first_fail_stands(self) -> None:
        real = progress.run_with_heartbeat
        calls = []

        def second_raises(*a, **kw):
            calls.append(1)
            if len(calls) == 2:
                raise OSError("confirm run could not start")
            return real(*a, **kw)

        with mock.patch.object(progress, "run_with_heartbeat", side_effect=second_raises):
            row = self._check_run(self._chk(self._cmd('echo "evidence-run-$n"; exit 1')))
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.runs(), 1)  # the confirm run never started the command
        self.assertEqual(row["result"], "fail")
        self.assertFalse(row.get("flaky"))
        self.assertEqual(row.get("attempts"), ["fail", "error"])
        self.assertEqual(row["path_line"], "evidence-run-1")

    def test_check_dry_regate_confirms_too(self) -> None:
        self.cfg.gates_checks = [self._chk(self.flaky_cmd())]
        result = gates.run_gates_dry(self._bundle(), self.cfg)
        row = self._row(result)
        self.assertEqual(self.runs(), 2)
        self.assertEqual((row["result"], row.get("flaky")), ("pass", True))
        self.assertEqual(result["overall"], "pass")


# -- (4): bounds ------------------------------------------------------------------------

class Bounds(_Base):
    def test_exactly_one_confirm_run(self) -> None:
        # Fails on runs 1 AND 2, would pass on run 3 — a second confirm must not happen.
        row = self._check_run(self._chk(self._cmd('echo "evidence-run-$n"; [ "$n" -ge 3 ]')))
        self.assertEqual(self.runs(), 2)
        self.assertEqual(row["result"], "fail")
        self.assertEqual(row.get("attempts"), ["fail", "fail"])

    def test_non_gating_failing_row_runs_once(self) -> None:
        row = self._check_run(self._chk(self.flaky_cmd(), gating=False))
        self.assertEqual(self.runs(), 1)
        self.assertEqual(row["result"], "fail")
        self.assertNotIn("attempts", row)

    def test_passing_row_runs_once(self) -> None:
        row = self._check_run(self._chk(self._cmd("exit 0")))
        self.assertEqual(self.runs(), 1)
        self.assertEqual(row["result"], "pass")
        self.assertNotIn("attempts", row)
        self.assertNotIn("flaky", row)

    def test_cmd_error_row_is_not_confirmed(self) -> None:
        calls = []
        real = progress.run_with_heartbeat

        def counting(*a, **kw):
            calls.append(1)
            return real(*a, **kw)

        chk = {"id": "C4-confirm", "tier": "C4", "label": "verify", "scope": "bundle",
               "gating": True, "subcmd": "verify"}  # subcmd but no [gates] runner
        with mock.patch.object(progress, "run_with_heartbeat", side_effect=counting):
            row = self._check_run(chk)
        self.assertEqual(calls, [])
        self.assertEqual(row["result"], "fail")
        self.assertNotIn("attempts", row)

    def test_raised_before_exit_code_is_not_confirmed(self) -> None:
        calls = []

        def raises(*a, **kw):
            calls.append(1)
            raise OSError("cannot spawn")

        with mock.patch.object(progress, "run_with_heartbeat", side_effect=raises):
            row = self._check_run(self._chk(self.flaky_cmd()))
        self.assertEqual(len(calls), 1)
        self.assertEqual(row["result"], "fail")
        self.assertNotIn("attempts", row)

    def test_project_switch_off_runs_once(self) -> None:
        self.cfg.gates_confirm_gating_fail = False
        row = self._check_run(self._chk(self.flaky_cmd()))
        self.assertEqual(self.runs(), 1)
        self.assertEqual(row["result"], "fail")
        self.assertNotIn("flaky", row)

    def test_project_switch_parsed_from_pdca_toml(self) -> None:
        for body, expected in (("", True),
                               ("confirm_gating_fail = true\n", True),
                               ("confirm_gating_fail = false\n", False),
                               ('confirm_gating_fail = "false"\n', False)):
            with self.subTest(body=body):
                (self.tmp / "pdca.toml").write_text(
                    '[paths]\nbundle_root = "results"\n[gates]\n' + body, encoding="utf-8")
                self.assertIs(Config.load(self.tmp).gates_confirm_gating_fail, expected)

    def test_row_switch_off_on_gates_checks(self) -> None:
        row = self._check_run(self._chk(self.flaky_cmd(), confirm_fail=False))
        self.assertEqual(self.runs(), 1)
        self.assertEqual(row["result"], "fail")
        self.assertNotIn("attempts", row)

    def _host_ci_row(self, extra: str) -> dict:
        """A `[gates] host_ci` row as Config.load normalizes it (`_normalize_host_ci`)."""
        cmd = self.flaky_cmd().replace("\\", "\\\\").replace('"', '\\"')
        (self.tmp / "pdca.toml").write_text(
            '[paths]\nbundle_root = "results"\n[gates]\n'
            f'host_ci = [{{ id = "host-ci-x", cmd = "{cmd}"{extra} }}]\n',
            encoding="utf-8")
        rows = Config.load(self.tmp).host_ci_checks
        self.assertEqual(len(rows), 1)
        return rows[0]

    def _run_host_ci_at_check(self, chk: dict) -> dict:
        # The Check matrix's host-CI branch (gates._run_checks), with the patched tree
        # supplied explicitly — the same tree `run_gates` would get from worktree.for_gate.
        self.cfg.host_ci_checks = [chk]
        wt = self.tmp / "wt"
        wt.mkdir()
        rows = gates._run_checks(self.cfg, cwd=self.cfg.root, bundle=self._bundle(),
                                 scopes=("repo", "bundle"), worktree_override=wt,
                                 confirm=True)
        return next(r for r in rows if r["rule_id"] == "host-ci-x")

    def test_host_ci_row_confirms_at_check(self) -> None:
        row = self._run_host_ci_at_check(self._host_ci_row(""))
        self.assertEqual(self.runs(), 2)
        self.assertEqual((row["result"], row.get("flaky")), ("pass", True))

    def test_row_switch_off_on_host_ci_survives_normalization(self) -> None:
        chk = self._host_ci_row(", confirm_fail = false")
        self.assertIs(chk.get("confirm_fail"), False)
        row = self._run_host_ci_at_check(chk)
        self.assertEqual(self.runs(), 1)
        self.assertEqual(row["result"], "fail")
        self.assertNotIn("attempts", row)


# -- (4b): Check-time only ----------------------------------------------------------------

class CheckTimeOnly(_Base):
    def test_run_one_without_the_switch_runs_once(self) -> None:
        # What publish's host-CI gate (publish.py `_run_one(chk, cfg=…, cwd=wt, …)`) and
        # every non-Check caller pass: no confirm switch.
        row = gates._run_one(self._chk(self.flaky_cmd()), cfg=self.cfg, cwd=self.tmp,
                             bundle=self._bundle())
        self.assertEqual(self.runs(), 1)
        self.assertEqual(row["result"], "fail")
        self.assertNotIn("flaky", row)

    def test_publish_host_ci_rows_run_once(self) -> None:
        # The publish host-CI gate runs `cfg.host_ci_checks` through `_run_one` exactly as
        # publish.py does — a fail→pass command still refuses (one run, recorded fail).
        self.cfg.host_ci_checks = [{"id": "host-ci-x", "tier": "T4", "scope": "bundle",
                                    "gating": True, "cmd": self.flaky_cmd()}]
        d = self._bundle()
        rows = [gates._run_one(chk, cfg=self.cfg, cwd=self.tmp, bundle=d,
                               runner=self.cfg.gates_runner, worktree_path=self.tmp)
                for chk in self.cfg.host_ci_checks]
        self.assertEqual(self.runs(), 1)
        self.assertEqual([r["result"] for r in rows], ["fail"])

    def test_working_tree_regate_runs_once(self) -> None:
        self.cfg.gates_checks = [self._chk(self.flaky_cmd(), scope="repo")]
        result = gates.run_working_tree(self.cfg)
        self.assertEqual(self.runs(), 1)
        self.assertEqual(self._row(result)["result"], "fail")
        self.assertEqual(result["overall"], "fail")

    def test_integration_regate_runs_once(self) -> None:
        self.cfg.gates_checks = [self._chk(self.flaky_cmd(), scope="repo")]
        wt = self.tmp / "integ"
        wt.mkdir()
        result = gates.run_integration(self.cfg, wt, hold_lock=False)
        self.assertEqual(self.runs(), 1)
        self.assertEqual(self._row(result)["result"], "fail")
        self.assertEqual(result["overall"], "fail")


# -- (5): evidence -------------------------------------------------------------------------

class Evidence(_Base):
    def test_log_holds_both_runs_with_combined_outcome_header(self) -> None:
        self._check_run(self._chk(self.flaky_cmd()))
        text = (self.cfg.bundle("B") / "gate-logs" / "C4-confirm.log").read_text("utf-8")
        head, _, rest = text.partition("# ==== attempt 1")
        self.assertTrue(rest, f"no per-attempt block in the log:\n{text}")
        # The top-level header shows the row's recorded (combined) result.
        self.assertIn("# outcome: pass\n", head)
        one, _, two = rest.partition("# ==== attempt 2")
        self.assertTrue(two, f"no second attempt block in the log:\n{text}")
        self.assertIn("# exit: 1\n", one)
        self.assertIn("# outcome: fail\n", one)
        self.assertIn("output-of-run-1\nevidence-run-1\n", one)
        self.assertIn("# exit: 0\n", two)
        self.assertIn("# outcome: pass\n", two)
        self.assertIn("output-of-run-2\nevidence-run-2\n", two)

    def test_single_run_log_unchanged(self) -> None:
        self._check_run(self._chk(self._cmd("exit 0")))
        text = (self.cfg.bundle("B") / "gate-logs" / "C4-confirm.log").read_text("utf-8")
        self.assertNotIn("attempt", text)
        self.assertIn("# exit: 0\n# outcome: pass\n", text)


# -- (6): routing ---------------------------------------------------------------------------

class Routing(_Base):
    def test_flaky_row_is_one_human_section6_item(self) -> None:
        row = self._check_run(self._chk(self.flaky_cmd()))
        d = self.cfg.bundle("B")
        self.assertEqual(json.loads((d / "check-gates.json").read_text())["overall"], "pass")
        (d / "check-review.md").write_text("# Review\n\nNo findings.\n", encoding="utf-8")
        items = [it for it in assemble.collect_needs_human(d, self.cfg)
                 if row["check"] in it.text]
        self.assertEqual(len(items), 1, items)
        item = items[0]
        # HUMAN even though C4 is a gate element (which would be IMPL for a plain fail).
        self.assertEqual(item.kind, assemble.HUMAN)
        self.assertIn("fail", item.text)
        self.assertIn("pass", item.text)

    def test_clean_pass_adds_no_item(self) -> None:
        row = self._check_run(self._chk(self._cmd("exit 0")))
        d = self.cfg.bundle("B")
        (d / "check-review.md").write_text("# Review\n\nNo findings.\n", encoding="utf-8")
        self.assertFalse([it for it in assemble.collect_needs_human(d, self.cfg)
                          if row["check"] in it.text])


if __name__ == "__main__":
    unittest.main()
