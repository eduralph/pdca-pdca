"""Offline slice for issue #468 — `cli._flow` must route the single-id and multi-id
CLI shapes through ONE drive path (`flow.flow_ids`) returning ONE results map, with the
single-id presentation DERIVED from that map rather than a separate `flow.flow` call
deriving a bare state string.

Fixture shape mirrors `tests/test_flow_slice.py:31-56` (all six leaves stubbed, gates
empty) — no Claude, no TTY, no Docker. Every drive here goes **through `cli._flow`**,
never a hand-picked `flow.*` call, per the brief's Falsifiability.

Run from the project root:
    PYTHONPATH=src python -m unittest tests.test_flow_entrypoint_parity
"""

from __future__ import annotations

import io
import json
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

from pdca_harness import cli, flow, leaves, signoff, split, state
from pdca_harness.config import Config, LeafConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def _stub_config(root: Path) -> Config:
    """All six leaves stubbed, gates empty (all-PASS stub rows) — same fixture shape
    as `tests/test_flow_slice.py:31-56`, the peer callsite the brief names."""
    return Config(
        root=root,
        bundle_root=root / "results",
        process_dir=root / "process",
        templates_dir=root / "templates",  # empty → planner stub uses its fallback brief
        default_branch="main",
        tracker_system="github",
        tracker_url="",
        issue_id_example="#1",
        builder=LeafConfig(mode="stub", family="claude"),
        reviewer=LeafConfig(mode="stub", family="codex"),
        planner=LeafConfig(mode="stub", family="claude", interactive=True),
        signoff=LeafConfig(mode="stub", family="claude", interactive=True),
        publisher=LeafConfig(mode="stub", family="claude", interactive=True),
        act=LeafConfig(mode="stub", family="claude", interactive=True),
        act_cadence=1,
        repo_checkouts={"example-org/example-repo": str(root / "example-repo")},
    )


def _args(ids: list[str]) -> SimpleNamespace:
    return SimpleNamespace(issue_ids=ids, from_csv=None, from_briefs=None,
                           no_publish=True, no_act=True, by="", lanes=None)


def _state_for(iid: str, out: str) -> str | None:
    """The disposition token printed for `iid`, whichever CLI shape produced `out`:
    single-id prints `state<TAB><path ending in issue_<iid>>`; multi-id (`_report_batch`)
    prints `state<TAB><iid>`. One reader for both, so a comparison never favours either
    shape's format."""
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and (parts[1] == iid or parts[1].endswith(f"issue_{iid}")):
            return parts[0]
    return None


_TERMINAL_SKIP_RE = re.compile(r"already terminal \((\w+)\)")


def _disposition(iid: str, out: str, err: str) -> str | None:
    """`_state_for`, plus the batch shape's stderr-only path: an id already terminal
    BEFORE this run never enters the results map (`flow_ids`'s terminal filter,
    `flow.py:1039-1043`) — mirrored by both CLI shapes, so it never reaches the printed
    table at all; its disposition is the state named in the terminal-skip note."""
    s = _state_for(iid, out)
    if s is not None:
        return s
    for line in err.splitlines():
        if f"issue_{iid} " in line:
            m = _TERMINAL_SKIP_RE.search(line)
            if m:
                return m.group(1)
    return None


def _split_proposal(child_labels: list[str]) -> str:
    body = "<!-- pdca:split-proposal v1 -->\n\n"
    for label in child_labels:
        body += (
            f"<!-- pdca:child {label} -->\n"
            f"- **Slug:** {label}\n"
            f"- **Defect / goal:** stub child body for {label}.\n"
            f"- **Success criterion:** stub.\n"
            f"<!-- pdca:end {label} -->\n\n"
        )
    return body


class EntrypointParity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- fixture builders --------------------------------------------------------

    def _fork(self, seed_root: Path) -> Path:
        """A byte-identical copy of `seed_root`'s disk state — so the single- and
        multi-id shapes each drive the SAME starting bytes, independently."""
        dst = Path(tempfile.mkdtemp()) / "root"
        shutil.copytree(seed_root, dst)
        self.addCleanup(shutil.rmtree, dst.parent, ignore_errors=True)
        return dst

    def _run(self, root: Path, ids: list[str]) -> tuple[int, str, str]:
        """Drive `ids` **through `cli._flow`** (never a hand-picked `flow.*` call)."""
        cfg = _stub_config(root)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = cli._flow(cfg, _args(ids))
        return rc, out.getvalue(), err.getvalue()

    def _inflight(self, root: Path, iid: str) -> None:
        cfg = _stub_config(root)
        leaves.do_plan(cfg.bundle(iid), cfg)  # PLANNED — nothing driven yet
        self.assertEqual(state.state(cfg.bundle(iid)), state.PLANNED)

    def _complete(self, root: Path, iid: str) -> None:
        cfg = _stub_config(root)
        final = flow.flow(cfg, iid, do_publish=False, do_act=False, today="2026-08-01")
        self.assertEqual(final, state.COMPLETE)

    def _discontinued(self, root: Path, iid: str) -> None:
        cfg = _stub_config(root)

        def discontinue_signoff(d: Path, cfg_: Config) -> None:
            (d / leaves.SIGNOFF_DECISION).write_text(
                "discontinue\nsuperseded, handled out-of-band\n", encoding="utf-8")

        orig = leaves.run_signoff
        leaves.run_signoff = discontinue_signoff
        try:
            final = flow.flow(cfg, iid, do_publish=False, do_act=False, today="2026-08-01")
        finally:
            leaves.run_signoff = orig
        self.assertEqual(final, state.DISCONTINUED)

    def _resolved(self, root: Path, iid: str) -> None:
        # Non-digit id: `sources.tracker_issue_reopened` bails at the `isdigit()` guard
        # (`sources.py:160-161`) without touching `gh` — deterministic offline.
        cfg = _stub_config(root)
        d = cfg.bundle(iid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "notes.json").write_text(json.dumps({
            "resolved": {"github_state": "CLOSED", "state_reason": "COMPLETED",
                        "closed_at": "2026-01-01T00:00:00Z",
                        "note": "settled outside a cycle"},
        }), encoding="utf-8")
        self.assertEqual(state.state(d), state.RESOLVED)

    def _split_parent(self, root: Path, iid: str, child_ids: list[str]) -> None:
        cfg = _stub_config(root)
        pd = cfg.bundle(iid)
        leaves.do_plan(pd, cfg)  # a normal brief first — a realistic split parent
        labels = [f"child-{i + 1}" for i in range(len(child_ids))]
        (pd / split.PROPOSAL).write_text(_split_proposal(labels), encoding="utf-8")
        split.accept(pd, child_ids, cfg)   # production split.accept, split.py:525
        final = flow.flow(cfg, iid, do_publish=False, do_act=False, today="2026-08-01")
        self.assertEqual(final, state.COMPLETE)
        record = split.read_lineage(pd)
        self.assertEqual(record.get("children"), child_ids)

    # -- structural proof: ONE drive path -----------------------------------------

    def test_single_id_routes_through_flow_ids_not_flow(self) -> None:
        """`cli._flow` must call the SAME `flow.flow_ids` the multi-id shape uses, for
        `len(ids) == 1` too — never a separate `flow.flow(...)` deriving a bare state
        string. Pre-fix, `flow.flow_ids` is never reached for a single id."""
        captured: dict = {}

        def spy(cfg, ids, **kw):
            captured["ids"] = ids
            captured["plan_missing"] = kw.get("plan_missing")
            return {"SOLO468": state.COMPLETE}

        orig = flow.flow_ids
        flow.flow_ids = spy
        try:
            cfg = _stub_config(self.tmp)
            outbuf, errbuf = io.StringIO(), io.StringIO()
            with redirect_stdout(outbuf), redirect_stderr(errbuf):
                rc = cli._flow(cfg, _args(["SOLO468"]))
            out = outbuf.getvalue()
        finally:
            flow.flow_ids = orig
        self.assertEqual(captured.get("ids"), ["SOLO468"])
        self.assertTrue(captured.get("plan_missing"))
        self.assertEqual(rc, 0)
        self.assertIn(f"{state.COMPLETE}\t", out)

    def test_preflight_error_same_rc_and_message_both_shapes(self) -> None:
        """An error meant to abort a run produces the SAME rc (and message) whichever
        shape it came through — pre-fix the single-id path had no `try/except` around
        its separate `flow.flow` call, so this raised uncaught for `len(ids) == 1`."""

        def boom(*_a, **_kw):
            raise flow.PreflightError("lane preflight failed for this stub")

        orig_ids, orig_flow = flow.flow_ids, flow.flow
        flow.flow_ids = boom
        flow.flow = boom
        try:
            cfg = _stub_config(self.tmp)
            out1, err1 = io.StringIO(), io.StringIO()
            with redirect_stdout(out1), redirect_stderr(err1):
                rc1 = cli._flow(cfg, _args(["A468"]))
            out2, err2 = io.StringIO(), io.StringIO()
            with redirect_stdout(out2), redirect_stderr(err2):
                rc2 = cli._flow(cfg, _args(["A468", "B468"]))
        finally:
            flow.flow_ids = orig_ids
            flow.flow = orig_flow
        self.assertEqual(rc1, 1)
        self.assertEqual(rc2, 1)
        self.assertEqual(err1.getvalue(), err2.getvalue())

    # -- behavioural parity across the state matrix -------------------------------

    def test_in_flight_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._inflight(seed, "IF468")
        rc1, out1, _err1 = self._run(self._fork(seed), ["IF468"])
        rc2, out2, _err2 = self._run(self._fork(seed), ["IF468", "FILLER468"])
        self.assertEqual(_state_for("IF468", out1), state.COMPLETE)
        self.assertEqual(_state_for("IF468", out1), _state_for("IF468", out2))
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)  # filler completes too → batch rule agrees here

    def test_complete_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._complete(seed, "DONE468")
        rc1, out1, err1 = self._run(self._fork(seed), ["DONE468"])
        _rc2, out2, err2 = self._run(self._fork(seed), ["DONE468", "FILLER468"])
        self.assertEqual(_state_for("DONE468", out1), state.COMPLETE)
        self.assertEqual(_state_for("DONE468", out1), _disposition("DONE468", out2, err2))
        self.assertEqual(rc1, 0)
        self.assertNotIn("rm -rf", err1)
        self.assertNotIn("rm -rf", err2)

    def test_discontinued_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._discontinued(seed, "DISC468")
        rc1, out1, _err1 = self._run(self._fork(seed), ["DISC468"])
        _rc2, out2, err2 = self._run(self._fork(seed), ["DISC468", "FILLER468"])
        self.assertEqual(_state_for("DISC468", out1), state.DISCONTINUED)
        self.assertEqual(_state_for("DISC468", out1), _disposition("DISC468", out2, err2))
        # DISCONTINUED is not a success on either shape's own rule.
        self.assertEqual(rc1, 1)

    def test_resolved_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._resolved(seed, "RES468")
        rc1, out1, _err1 = self._run(self._fork(seed), ["RES468"])
        _rc2, out2, err2 = self._run(self._fork(seed), ["RES468", "FILLER468"])
        self.assertEqual(_state_for("RES468", out1), state.RESOLVED)
        self.assertEqual(_state_for("RES468", out1), _disposition("RES468", out2, err2))
        self.assertEqual(rc1, 0)  # RESOLVED counts as a successful no-op (#302)

    def test_terminal_split_parent_names_children_never_rm_rf(self) -> None:
        """The brief's concrete defect: a terminal bundle with a `children` lineage edge
        (a split parent, `split.py:392-395`) must never be told `rm -rf` — that would
        destroy the one on-disk record of the split (`split.py:47`). Both shapes must
        name the recovery instead, and agree on the id's own disposition."""
        seed = self.tmp / "seed"
        self._split_parent(seed, "PARENT468", ["469", "470"])
        rc1, out1, err1 = self._run(self._fork(seed), ["PARENT468"])
        _rc2, out2, err2 = self._run(self._fork(seed), ["PARENT468", "FILLER468"])
        self.assertEqual(_state_for("PARENT468", out1), state.COMPLETE)
        self.assertEqual(_state_for("PARENT468", out1),
                         _disposition("PARENT468", out2, err2))
        self.assertEqual(rc1, 0)
        for err in (err1, err2):
            self.assertNotIn("rm -rf", err)
            self.assertIn("469", err)
            self.assertIn("470", err)
            self.assertIn("pdca flow", err)

    # -- preserved single-id presentation ------------------------------------------

    def test_single_id_awaiting_signoff_presentation_preserved(self) -> None:
        """Single-id keeps its own presentation — the §6 listing and rc-0
        stop-for-the-human semantics — as a PRESENTATION of the shared map, not a
        separate drive path (mirrors `tests/test_flow_slice.py`'s C6 fixture)."""

        def bad_signoff(d: Path, cfg: Config) -> None:
            (d / leaves.SIGNOFF_DECISION).write_text("accept\n", encoding="utf-8")
            # deliberately leaves §6 NEEDS-HUMAN open — C6 must refuse the accept

        # The unified drive path takes every pending bundle through the wave sign-off
        # (`_drive_wave` -> `leaves.run_signoff_batch` -> `_stub_signoff` in stub mode,
        # `flow.py:758-767`), not the single-bundle `leaves.run_signoff` — patch the
        # entry point this path actually calls.
        orig = leaves._stub_signoff
        leaves._stub_signoff = bad_signoff
        try:
            cfg = _stub_config(self.tmp)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli._flow(cfg, _args(["AWSF468"]))
        finally:
            leaves._stub_signoff = orig
        self.assertEqual(rc, 0)
        printed = out.getvalue()
        self.assertTrue(printed.startswith(f"{state.AWAITING_SIGNOFF}\t"))
        d = cfg.bundle("AWSF468")
        open_items = signoff.open_needs_human(d / "SUMMARY.md")
        self.assertTrue(open_items)
        for it in open_items:
            self.assertIn(f"    {it}", printed)


if __name__ == "__main__":
    unittest.main()
