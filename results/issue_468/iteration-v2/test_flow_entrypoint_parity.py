"""Offline slice for issue #468 — `cli._flow` must route the single-id and the multi-id
CLI shapes through ONE drive path (`flow.flow_ids`) returning ONE results map, with the
single-id presentation DERIVED from that map rather than a second drive path returning a
bare state string.

Every drive here goes **through `cli._flow`** — never a hand-picked `flow.*` call — because
that is the surface where iterations 4 and 5 of #449 both found parity breaks. Fixture shape
mirrors `tests/test_flow_slice.py:31-56` (all six leaves stubbed, gates empty): no Claude,
no TTY, no Docker, no tracker.

Modules are imported, never new symbols (`from pdca_harness import cli, flow, …`): a
`from pdca_harness.flow import <new helper>` would raise ImportError on the C4 red leg,
which `engine/scripts/run-verify.sh` classifies PDCA-UNVERIFIABLE rather than red.

Run from the project root:
    PYTHONPATH=src python3 -m unittest tests.test_flow_entrypoint_parity
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


def _stub_config(root: Path) -> Config:
    """All six leaves stubbed, gates empty (all-PASS stub rows) — the same fixture shape as
    `tests/test_flow_slice.py:31-56`, the peer callsite the brief names."""
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
        # Hermetic toy target inside this test's tmp root (same reason as test_flow_slice).
        repo_checkouts={"example-org/example-repo": str(root / "example-repo")},
    )


def _args(ids: list[str]) -> SimpleNamespace:
    return SimpleNamespace(issue_ids=ids, from_csv=None, from_briefs=None,
                           no_publish=True, no_act=True, by="", lanes=None)


def _state_for(iid: str, out: str) -> str | None:
    """The disposition token printed for `iid`, whichever shape produced `out`: the single-id
    shape prints `state<TAB><path ending in issue_<iid>>`, the multi-id one (`_report_batch`)
    prints `state<TAB><iid>`. ONE reader for both, so no comparison favours either format."""
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and (parts[1] == iid or parts[1].endswith(f"issue_{iid}")):
            return parts[0]
    return None


_TERMINAL_SKIP_RE = re.compile(r"already terminal \((\w+)\)")


def _disposition(iid: str, out: str, err: str) -> str | None:
    """`_state_for`, plus the batch shape's stderr-only case: an id already terminal BEFORE
    the run never enters the results map (the shared terminal filter in `flow_ids`), so it
    never reaches the printed table — its disposition is the state in the skip note."""
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
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    # -- fixture builders --------------------------------------------------------------

    def _fork(self, seed_root: Path) -> Path:
        """A byte-identical copy of `seed_root`'s disk state, so the two shapes each drive
        the SAME starting bytes independently."""
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
        # Non-digit id: `sources.tracker_issue_reopened` bails at its `isdigit()` guard
        # without touching `gh`, so the shared RESOLVED revalidation stays offline here.
        cfg = _stub_config(root)
        d = cfg.bundle(iid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "notes.json").write_text(json.dumps({
            "resolved": {"github_state": "CLOSED", "state_reason": "COMPLETED",
                         "closed_at": "2026-01-01T00:00:00Z",
                         "note": "settled outside a cycle"},
        }), encoding="utf-8")
        self.assertEqual(state.state(d), state.RESOLVED)

    def _split_parent(self, root: Path, iid: str, child_ids: list[str]) -> Path:
        """A REAL terminal split parent: production `split.accept` (`split.py:525`) writes
        the `children` lineage edge and the close marker; the flow then drives it terminal."""
        cfg = _stub_config(root)
        pd = cfg.bundle(iid)
        leaves.do_plan(pd, cfg)  # a normal brief first — a realistic split parent
        labels = [f"child-{i + 1}" for i in range(len(child_ids))]
        (pd / split.PROPOSAL).write_text(_split_proposal(labels), encoding="utf-8")
        split.accept(pd, child_ids, cfg)
        final = flow.flow(cfg, iid, do_publish=False, do_act=False, today="2026-08-01")
        self.assertEqual(final, state.COMPLETE)
        self.assertEqual((split.read_lineage(pd) or {}).get("children"), child_ids)
        return pd

    # -- structural proof: ONE drive path ----------------------------------------------

    def test_single_id_routes_through_flow_ids_not_flow(self) -> None:
        """`cli._flow` must call the SAME `flow.flow_ids` the multi-id shape uses for
        `len(ids) == 1` too — never a separate `flow.flow(...)` returning a bare state
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
        self.assertIn(f"{state.COMPLETE}\t", out)   # presentation DERIVED from that map

    def test_preflight_error_same_rc_and_message_both_shapes(self) -> None:
        """An error meant to abort a run produces the SAME rc (and message) on both shapes —
        pre-fix the single-id route had no `try/except` at all, so a `PreflightError` escaped
        `cli._flow` uncaught for `len(ids) == 1` while the batch route returned 1."""

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

    # -- behavioural parity across the state matrix ------------------------------------

    def test_in_flight_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._inflight(seed, "IF468")
        rc1, out1, _err1 = self._run(self._fork(seed), ["IF468"])
        rc2, out2, _err2 = self._run(self._fork(seed), ["IF468", "FILLER468"])
        self.assertEqual(_state_for("IF468", out1), state.COMPLETE)
        self.assertEqual(_state_for("IF468", out1), _state_for("IF468", out2))
        self.assertEqual(rc1, 0)
        self.assertEqual(rc2, 0)  # the filler completes too → the batch rule agrees here

    def test_complete_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._complete(seed, "DONE468")
        rc1, out1, err1 = self._run(self._fork(seed), ["DONE468"])
        _rc2, out2, err2 = self._run(self._fork(seed), ["DONE468", "FILLER468"])
        self.assertEqual(_state_for("DONE468", out1), state.COMPLETE)
        self.assertEqual(_state_for("DONE468", out1), _disposition("DONE468", out2, err2))
        self.assertEqual(rc1, 0)
        # A plain COMPLETE bundle (no lineage record) keeps the redo hint — and now BOTH
        # shapes print it, from the one shared terminal filter.
        for err in (err1, err2):
            self.assertIn("already complete — nothing to run", err)

    def test_discontinued_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._discontinued(seed, "DISC468")
        rc1, out1, err1 = self._run(self._fork(seed), ["DISC468"])
        _rc2, out2, err2 = self._run(self._fork(seed), ["DISC468", "FILLER468"])
        self.assertEqual(_state_for("DISC468", out1), state.DISCONTINUED)
        self.assertEqual(_state_for("DISC468", out1), _disposition("DISC468", out2, err2))
        # Unchanged from pre-fix, and the SAME rule the batch shape applies: the exit code
        # counts successful terminals, and a deliberately abandoned bundle is not one.
        self.assertEqual(rc1, 1)
        for err in (err1, err2):   # an abandoned bundle is never told to redo itself
            self.assertNotIn("rm -rf", err)

    def test_resolved_bundle_agrees_across_shapes(self) -> None:
        seed = self.tmp / "seed"
        self._resolved(seed, "RES468")
        rc1, out1, err1 = self._run(self._fork(seed), ["RES468"])
        _rc2, out2, err2 = self._run(self._fork(seed), ["RES468", "FILLER468"])
        self.assertEqual(_state_for("RES468", out1), state.RESOLVED)
        self.assertEqual(_state_for("RES468", out1), _disposition("RES468", out2, err2))
        self.assertEqual(rc1, 0)  # RESOLVED is a successful no-op (#302)
        # The #302 reopen remediation was single-id-only pre-fix; on the shared path both
        # shapes give it (parity in the direction that keeps the guidance, not drops it).
        for err in (err1, err2):
            self.assertIn("resolved outside a cycle", err)
            self.assertIn("notes.superseded-by-reopen.json", err)

    def test_terminal_split_parent_names_children_never_rm_rf(self) -> None:
        """The brief's concrete defect: a terminal bundle with a `children` lineage edge (a
        split parent, `split.py:392-395`) must never be told `rm -rf` — deleting it destroys
        the one on-disk record of the split (`split.py:47`) and orphans the children. Both
        shapes must name the recovery instead, and agree on the id's disposition."""
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
            self.assertIn("pdca flow 469 470", err)

    def test_malformed_lineage_children_degrades_the_hint_not_the_run(self) -> None:
        """A hand-edited lineage record must degrade the HINT, never abort the flow.

        `split.read_lineage` is tolerant by construction about the FILE (`split.py:373-402`)
        and `split._recorded_depth` about a VALUE it cannot compute with (`split.py:405`);
        a consumer that formats `children` without the same tolerance moves the throw one
        line down — `" ".join(7)` raises TypeError straight out of `cli._flow`. And a record
        that CARRIES a `children` key is a split parent whatever its value, so the
        destructive `rm -rf` advice must stay suppressed even when the ids are unreadable.
        """
        cases = {
            "non-list": 7,
            "string": "469",
            "junk-entries": [1, None, {}, ""],
            "empty-list": [],
        }
        for name, children in cases.items():
            with self.subTest(case=name):
                seed = self.tmp / f"seed-{name}"
                iid = f"BAD{name.upper().replace('-', '')}468"
                self._complete(seed, iid)
                cfg = _stub_config(seed)
                (cfg.bundle(iid) / split.LINEAGE).write_text(
                    json.dumps({"version": split.LINEAGE_VERSION, "id": iid,
                                "children": children}), encoding="utf-8")
                rc1, out1, err1 = self._run(self._fork(seed), [iid])
                _rc2, out2, err2 = self._run(self._fork(seed), [iid, "FILLER468"])
                self.assertEqual(rc1, 0)
                self.assertEqual(_state_for(iid, out1), state.COMPLETE)
                self.assertEqual(_state_for(iid, out1), _disposition(iid, out2, err2))
                for err in (err1, err2):
                    self.assertIn("already terminal (COMPLETE), skipped", err)
                    self.assertNotIn("rm -rf", err)   # a `children` key ⇒ a split parent
                    self.assertNotIn("Traceback", err)
                    # …and no invented recovery: `" ".join("469")` would offer
                    # `pdca flow 4 6 9`, which is worse advice than none.
                    self.assertNotIn("drive them instead", err)

    # -- preserved single-id presentation ----------------------------------------------

    def test_single_id_awaiting_signoff_presentation_preserved(self) -> None:
        """Single-id keeps its own presentation — the §6 listing and the rc-0
        stop-for-the-human semantics — as a PRESENTATION of the shared map, not as a
        separate drive path."""

        def bad_signoff(d: Path, cfg: Config) -> None:
            (d / leaves.SIGNOFF_DECISION).write_text("accept\n", encoding="utf-8")
            # deliberately leaves §6 NEEDS-HUMAN open — C6 must refuse the accept

        # The shared drive path takes every pending bundle through the wave sign-off
        # (`_drive_wave` → `leaves.run_signoff_batch` → `_stub_signoff` in stub mode), not
        # the single-bundle `leaves.run_signoff` — patch the entry point it actually calls.
        orig = leaves._stub_signoff
        leaves._stub_signoff = bad_signoff
        try:
            cfg = _stub_config(self.tmp)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                rc = cli._flow(cfg, _args(["AWSF468"]))
        finally:
            leaves._stub_signoff = orig
        self.assertEqual(rc, 0)                      # stop-for-the-human is not a failure
        printed = out.getvalue()
        self.assertTrue(printed.startswith(f"{state.AWAITING_SIGNOFF}\t"))
        d = cfg.bundle("AWSF468")
        open_items = signoff.open_needs_human(d / "SUMMARY.md")
        self.assertTrue(open_items)
        for it in open_items:
            self.assertIn(f"    {it}", printed)


if __name__ == "__main__":
    unittest.main()
