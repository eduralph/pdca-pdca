"""One live driver per bundle, and a split hint that does not contradict it (#498).

Two linked defects. (a) `pdca split <id> --accept` ALWAYS ended with "run `pdca flow
<child-ids>` to drive the children" — also when a live flow was about to drive those
children (an id run adopts a split in its drive set; a CSV batch sweeps every in-flight
bundle after its Plan session). An operator following it started a second driver over the
same bundles. (b) Nothing kept two drivers apart at all: bundle state is plain files, and no
drive path took any ownership of a bundle, so any two `pdca flow` runs over overlapping ids
wrote the same artifacts with no ordering.

Every run here goes through the CLI entry points (`cli._flow`, `cli._split`), with all six
leaves stubbed and gates empty — the fixture shape of `tests/test_flow_adopt_split.py:43-63`
(copied, never imported). Where a run has to be paused mid-drive, a stand-in builder (or a
stand-in Plan session) waits on a file before handing back to the PRODUCTION stub, and the
competing driver is a REAL second process (`_spawn`): a claim could be per-process, and then
an in-process thread would pass for the wrong reason. Child processes get
`PYTHONPATH=<checkout>/template/src` and none of the gate's `PDCA_*` environment. Every wait
is bounded, so a red leg fails instead of hanging.

What goes red on the base (no claims, an unconditional hint): a second run drives a bundle a
live run holds; a run with no way to record a claim drives anyway; the sweep and adoption
drive bundles another live run holds; an accept the running flow will act on prints the
`run pdca flow …` instruction. The rest pin behavior the fix must NOT change or must get
exactly right — the instruction byte-identical where no live run will drive the children,
and a claim let go (or never given) where this run is not driving the bundle — and are
green on the base by design.

Modules are imported, never new symbols (`from pdca_harness import cli, …`): the C4 red leg
reverts the production hunks and keeps this file, and a symbol this patch adds would fail to
import there (`engine/scripts/run-verify.sh` records that as PDCA-UNVERIFIABLE, not red).

    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_single_driver
"""

from __future__ import annotations

import errno
import hashlib
import io
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pdca_harness import act, cli, leaves, split, state
from pdca_harness.config import Config, LeafConfig

#: The package under test, for the child processes (`template/src`, or a rendered `src`).
_SRC = Path(__file__).resolve().parents[1] / "src"
#: The render's ignore rules: `.gitignore.jinja` in the template checkout, `.gitignore` in a
#: rendered instance (the same dual home `test_seed_spill` reads).
_IGNORE = next((Path(__file__).resolve().parents[1] / n
                for n in (".gitignore", ".gitignore.jinja")
                if (Path(__file__).resolve().parents[1] / n).is_file()), None)
#: Where the docs say a run keeps its claims (docs 07 §Lanes), under the process dir.
_CLAIMS = ".drive-claims"
#: Upper bound on every wait in this file — a red leg must fail, never hang the C4 gate.
_WAIT = 60.0


def _stub_config(root: Path) -> Config:
    """All six leaves stubbed, gates empty — the shape of `test_flow_adopt_split.py:43-63`,
    including the hermetic toy checkout inside the tmp root."""
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


def _brief(slug: str, *extra: str) -> str:
    """An authored brief (a filled Slug, so `state` reads PLANNED, not a placeholder)."""
    return (f"# Brief — {slug}\n\n"
            f"- **Slug:** {slug}\n"
            f"- **Defect:** stub defect for {slug}.\n"
            "- **Success criterion:** the stub test passes.\n"
            "- **Repo + branch target:** example-repo @ main\n"
            "- **Test file:** test_stub.py\n"
            + "".join(line + "\n" for line in extra))


def _proposal(*slugs: str) -> str:
    """A `split-proposal.md` the production parser accepts (`split.parse`) — independent
    children, so every one of them can be scheduled on its own."""
    out = "<!-- pdca:split-proposal v1 -->\n# Split proposal\n\n"
    for i, slug in enumerate(slugs, 1):
        out += (f"<!-- pdca:child child-{i} -->\n{_brief(slug)}\n"
                f"<!-- pdca:end child-{i} -->\n\n")
    return out


def _args(ids: list[str], *, csv: str | None = None) -> SimpleNamespace:
    """The `pdca flow …` argv as `cli._flow` receives it (`--no-publish --no-act`)."""
    return SimpleNamespace(issue_ids=ids, from_csv=csv, from_briefs=None, no_publish=True,
                           no_act=True, by="", lanes=None, max_passes=None)


def _briefed(cfg: Config, iid: str, *extra: str) -> Path:
    d = cfg.bundle(iid)
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.md").write_text(_brief(f"slice-{iid}", *extra), encoding="utf-8")
    return d


def _ready_to_split(cfg: Config, iid: str, slugs: tuple[str, ...]) -> Path:
    """A briefed parent with a proposal on disk — what `pdca split <id>` leaves for the
    human to read before `--accept`."""
    d = _briefed(cfg, iid)
    (d / split.PROPOSAL).write_text(_proposal(*slugs), encoding="utf-8")
    return d


def _wait_for(path: Path, proc: subprocess.Popen | None = None) -> bool:
    deadline = time.monotonic() + _WAIT
    while time.monotonic() < deadline:
        if path.exists():
            return True
        if proc is not None and proc.poll() is not None:
            return False
        time.sleep(0.02)
    return False


def _pause_here(pause: Path, what: str) -> None:
    """Drop `pause/ready`, then wait (bounded) for `pause/go`: the run is held right here."""
    (pause / "ready").write_text(what, encoding="utf-8")
    _wait_for(pause / "go")


def _pausing_build(pause: Path, on: str | None = None):
    """Install a builder that pauses (`_pause_here`) on its FIRST call — or on the first
    build of bundle `on` — and then runs the PRODUCTION stub builder. Returns the original,
    for the caller to restore. This is how a run is held mid-drive."""
    real = leaves.do_build
    first = [True]

    def build(d: Path, cfg: Config) -> None:
        if first[0] and on in (None, d.name):
            first[0] = False
            _pause_here(pause, d.name)
        real(d, cfg)

    leaves.do_build = build
    return real


def _walking_away(name: str) -> None:
    """Install a sign-off that never offers bundle `name` a session: it stops at
    AWAITING_SIGNOFF, and its wave ends with it named as walked away from — the ordinary
    end of an interactive run whose human did not answer for it."""
    real = leaves.run_signoff_batch

    def signoff(cfg: Config, bundles: list[Path]) -> None:
        rest = [d for d in bundles if d.name != name]
        if rest:
            real(cfg, rest)

    leaves.run_signoff_batch = signoff


def _quiet_plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
    """A Plan session (pre-pass, or a CSV batch's) that briefs nothing."""


def _pausing_plan(pause: Path):
    """A Plan pre-pass that briefs each id it is given, drafts a two-child split proposal
    for it, and then pauses (`_pause_here`) — a run held INSIDE its Plan session, as it is
    while the human reads a proposal before accepting it."""
    def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
        for iid in ids or []:
            _ready_to_split(cfg, iid, ("child-a", "child-b"))
        _pause_here(pause, ",".join(ids or []))
    return plan


def _child_main(argv: list[str]) -> int:
    """Entry point of a child process (`_spawn`):

    * `split <root> <parent> <ids> [<gate>]` — `pdca split <parent> --accept --ids <ids>`
      through `cli._split`, after waiting (bounded) for the gate file when one is given;
    * `flow <root> <pause|-> [--pause-on=<bundle>] [--walk-away=<bundle>] <ids…>` —
      `pdca flow <ids…>` through `cli._flow`; its Plan pre-pass briefs nothing, and with a
      pause dir its first build (of `--pause-on`, if given) is held;
    * `csv <root> <pause|->` — `pdca flow --from-csv …` the same way;
    * `plan-pause <root> <pause> <ids…>` — `pdca flow <ids…>` held inside its Plan
      pre-pass (`_pausing_plan`).
    """
    mode, cfg = argv[0], _stub_config(Path(argv[1]))
    if mode == "split":
        if len(argv) > 4 and not _wait_for(Path(argv[4])):
            return 3
        return cli._split(cfg, SimpleNamespace(issue_id=argv[2], accept=True, ids=argv[3]))
    pause = None if argv[2] == "-" else Path(argv[2])
    opts = dict(a[2:].split("=", 1) for a in argv[3:] if a.startswith("--"))
    ids = [a for a in argv[3:] if not a.startswith("--")]
    leaves.do_plan_batch = _quiet_plan
    if mode == "plan-pause":
        leaves.do_plan_batch = _pausing_plan(pause)
    elif pause is not None:
        _pausing_build(pause, on=opts.get("pause-on"))
    if "walk-away" in opts:
        _walking_away(opts["walk-away"])
    if mode == "csv":
        return cli._flow(cfg, _args([], csv="tracker.csv"))
    return cli._flow(cfg, _args(ids))


#: The child's bootstrap: load THIS file by path and call `_child_main` — one fixture,
#: in one module, for both processes.
_BOOT = ("import importlib.util, sys\n"
         "spec = importlib.util.spec_from_file_location('single_driver_child', sys.argv[1])\n"
         "mod = importlib.util.module_from_spec(spec)\n"
         "spec.loader.exec_module(mod)\n"
         "sys.exit(mod._child_main(sys.argv[2:]))\n")


def _fingerprint(root: Path) -> dict[str, tuple]:
    """Every path under `root`, with enough of each file to see ANY write to it."""
    out: dict[str, tuple] = {}
    for p in sorted(root.rglob("*")):
        rel = str(p.relative_to(root))
        if p.is_dir():
            out[rel] = ("dir",)
        else:
            st = p.stat()
            out[rel] = (st.st_size, st.st_mtime_ns,
                        hashlib.sha256(p.read_bytes()).hexdigest())
    return out


class SingleDriver(unittest.TestCase):
    def setUp(self) -> None:
        # Hermetic environment: nothing the gate (or an enclosing flow) exported under
        # PDCA_* may reach these runs, in this process or in any child.
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        for key in [k for k in os.environ if k.startswith("PDCA_")]:
            del os.environ[key]
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cfg = _stub_config(self.tmp / "instance")
        self.cfg.bundle_root.mkdir(parents=True)
        self._orig = (leaves.do_plan_batch, leaves.do_build)
        self.addCleanup(self._restore)
        self.err = io.StringIO()
        self.out = io.StringIO()

    def _restore(self) -> None:
        leaves.do_plan_batch, leaves.do_build = self._orig

    # -- running things ------------------------------------------------------------------

    def _cli(self, ids: list[str], *, csv: str | None = None) -> int:
        """`pdca flow <ids…>` (or `pdca flow --from-csv`) in THIS process — a fresh capture
        per call."""
        self.err, self.out = io.StringIO(), io.StringIO()
        with redirect_stderr(self.err), redirect_stdout(self.out):
            return cli._flow(self.cfg, _args(ids, csv=csv))

    def _split_here(self, parent: str, kids: str) -> tuple[int, str]:
        """`pdca split <parent> --accept --ids <kids>` in THIS process — a shell of its own,
        with no run around it unless the test put one there."""
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            rc = cli._split(self.cfg, SimpleNamespace(issue_id=parent, accept=True, ids=kids))
        return rc, err.getvalue()

    def _spawn(self, *argv: str, tag: str) -> subprocess.Popen:
        """A second process running `_child_main(argv)`, as a separate shell would: no
        `PDCA_*` inherited. Output goes to files (a paused child must never block on a full
        pipe); it is killed at teardown if still alive."""
        out = (self.tmp / f"{tag}.out").open("w")
        err = (self.tmp / f"{tag}.err").open("w")
        env = {k: v for k, v in os.environ.items() if not k.startswith("PDCA_")}
        env["PYTHONPATH"] = str(_SRC)
        proc = subprocess.Popen(
            [sys.executable, "-c", _BOOT, str(Path(__file__).resolve()), *argv],
            stdout=out, stderr=err, env=env, cwd=str(self.tmp))

        def reap() -> None:
            if proc.poll() is None:
                proc.kill()
            try:
                proc.wait(timeout=_WAIT)
            finally:
                out.close()
                err.close()

        self.addCleanup(reap)
        return proc

    def _finish(self, proc: subprocess.Popen, tag: str) -> tuple[int, str]:
        rc = proc.wait(timeout=_WAIT)
        return rc, (self.tmp / f"{tag}.err").read_text(encoding="utf-8")

    def _run_child(self, *argv: str, tag: str) -> tuple[int, str]:
        return self._finish(self._spawn(*argv, tag=tag), tag)

    def _hold(self, mode: str, *ids: str, tag: str) -> tuple[subprocess.Popen, Path]:
        """Run A in ANOTHER process — `mode` is a `_child_main` flow mode, `ids` its ids and
        options — and return once it is paused (in a build, or in its Plan session for
        `plan-pause`), holding whatever it holds. Writing `<pause>/go` lets it finish."""
        pause = self.tmp / f"{tag}-pause"
        pause.mkdir()
        proc = self._spawn(mode, str(self.cfg.root), str(pause), *ids, tag=tag)
        if not _wait_for(pause / "ready", proc):
            self.fail(f"run {tag} never reached its pause: rc={proc.poll()}\n"
                      + (self.tmp / f"{tag}.err").read_text(encoding="utf-8"))
        return proc, pause

    def _state(self, iid: str) -> str:
        return state.state(self.cfg.bundle(iid))

    def _broken_claims_dir(self) -> None:
        """A regular file where the run keeps its claims: no claim can be opened."""
        self.cfg.process_dir.mkdir(parents=True, exist_ok=True)
        (self.cfg.process_dir / _CLAIMS).write_text("not a directory\n", encoding="utf-8")

    @staticmethod
    def _held_lines(text: str, name: str) -> list[str]:
        return [ln for ln in text.splitlines() if name in ln and "held by another" in ln]

    @staticmethod
    def _unclaimable_lines(text: str, name: str) -> list[str]:
        return [ln for ln in text.splitlines() if name in ln and "could not record" in ln]

    @staticmethod
    def _instruction(parent: str, kids: str) -> str:
        """The instruction line exactly as the base prints it (`cli.py:843-844`)."""
        return (f"issue_{parent} marked split; run `{cli._prog()} flow {kids}` to drive the "
                "children")

    @staticmethod
    def _instruction_lines(text: str, parent: str, kids: str) -> list[str]:
        """The instruction in ANOTHER process's output: the same bytes, whatever command
        name that process resolved for itself (`cli._prog`)."""
        shape = re.compile(rf"issue_{parent} marked split; run `\S+ flow {kids}` to drive "
                           r"the children")
        return [ln for ln in text.splitlines() if shape.fullmatch(ln)]

    # -- (i) a second driver over a bundle a live run holds is refused ---------------------

    def test_a_second_flow_over_a_bundle_a_live_run_holds_is_refused(self) -> None:
        """Run A (`pdca flow 7`) is paused mid-drive; run B — `pdca flow 7`, a separate
        process — must exit non-zero, name issue_7 as held by another run, and change
        nothing under results/. On the base B simply drives 7 to COMPLETE under A.

        Then (iii), the normal-return half: once A has returned, a new run over 7 is not
        refused."""
        _briefed(self.cfg, "7")
        pause = self.tmp / "pause"
        pause.mkdir()
        orig_build = _pausing_build(pause)
        self.addCleanup(setattr, leaves, "do_build", orig_build)
        result: dict[str, int] = {}
        a = threading.Thread(target=lambda: result.update(rc=self._cli(["7"])),
                             name="run-A", daemon=True)
        a.start()

        def release_a() -> None:
            (pause / "go").write_text("", encoding="utf-8")
            a.join(timeout=_WAIT)

        self.addCleanup(release_a)
        self.assertTrue(_wait_for(pause / "ready"), "run A never reached its build")

        before = _fingerprint(self.cfg.bundle_root)
        rc_b, err_b = self._run_child("flow", str(self.cfg.root), "-", "7", tag="B")

        self.assertNotEqual(rc_b, 0, f"run B drove a bundle run A holds:\n{err_b}")
        self.assertTrue(self._held_lines(err_b, "issue_7"),
                        f"run B did not name issue_7 as held by another run:\n{err_b}")
        self.assertEqual(_fingerprint(self.cfg.bundle_root), before,
                         "run B changed results/ while run A held the bundle")

        release_a()
        self.assertFalse(a.is_alive(), "run A did not finish")
        self.assertEqual(result.get("rc"), 0, self.err.getvalue())
        self.assertEqual(self._state("7"), state.COMPLETE)

        # (iii) A has returned: its claim went with it.
        rc_c, err_c = self._run_child("flow", str(self.cfg.root), "-", "7", tag="C")
        self.assertEqual(rc_c, 0, err_c)
        self.assertEqual(self._held_lines(err_c, "issue_7"), [], err_c)

    def test_a_named_id_list_is_refused_whole_before_its_plan_pre_pass(self) -> None:
        """`pdca flow 3 7` while another process holds 7: refused before ANY bundle is
        touched — 3's Plan pre-pass (it has no brief yet) never runs, and no bundle
        directory is created for it."""
        _briefed(self.cfg, "7")
        a, _pause = self._hold("flow", "7", tag="A")
        planned: list[list[str]] = []
        leaves.do_plan_batch = lambda cfg, csv=None, ids=None: planned.append(list(ids or []))
        before = _fingerprint(self.cfg.bundle_root)

        rc = self._cli(["3", "7"])

        err = self.err.getvalue()
        self.assertEqual(rc, 1, err)
        self.assertTrue(self._held_lines(err, "issue_7"), err)
        self.assertEqual(planned, [], "the Plan pre-pass ran for a refused run")
        self.assertEqual(_fingerprint(self.cfg.bundle_root), before)
        self.assertIsNone(a.poll(), "run A should still be alive and holding 7")

    # -- fail closed: a claim that cannot be recorded is never driven around -----------------

    def test_a_run_that_cannot_open_its_claim_refuses_rather_than_drive_unclaimed(
            self) -> None:
        """No claim file can be opened (a regular file sits where the claims live). A bundle
        driven unclaimed has nothing keeping a second run off it, so `pdca flow 7` refuses —
        non-zero, naming issue_7, nothing under results/ changed. On the base it drives."""
        _briefed(self.cfg, "7")
        self._broken_claims_dir()
        before = _fingerprint(self.cfg.bundle_root)

        rc = self._cli(["7"])

        err = self.err.getvalue()
        self.assertEqual(rc, 1, err)
        self.assertTrue(self._unclaimable_lines(err, "issue_7"), err)
        self.assertEqual(_fingerprint(self.cfg.bundle_root), before)
        self.assertEqual(self._state("7"), state.PLANNED)

    def test_a_run_whose_filesystem_cannot_lock_refuses_rather_than_drive_unclaimed(
            self) -> None:
        """The claim file opens but the lock itself fails for a reason that is NOT another
        holder (ENOLCK — a filesystem without lock support). Same answer: refused, not
        driven unclaimed."""
        _briefed(self.cfg, "7")
        before = _fingerprint(self.cfg.bundle_root)

        def no_locks(fh, *, wait: bool = True) -> None:
            raise OSError(errno.ENOLCK, "No locks available")

        with mock.patch.object(act, "_lock_exclusive", no_locks):
            rc = self._cli(["7"])

        err = self.err.getvalue()
        self.assertEqual(rc, 1, err)
        self.assertTrue(self._unclaimable_lines(err, "issue_7"), err)
        self.assertIn("No locks available", err)
        self.assertEqual(_fingerprint(self.cfg.bundle_root), before)

    # -- (iii) the claim ends with the run -----------------------------------------------

    def test_a_run_that_raises_leaves_nothing_behind(self) -> None:
        """A run that ends by RAISING (a ^C inside the builder) releases its claim: the next
        run over the same bundle, in another process, drives it."""
        _briefed(self.cfg, "7")

        def interrupted(d: Path, cfg: Config) -> None:
            raise KeyboardInterrupt

        leaves.do_build = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self._cli(["7"])
        self._restore()

        rc, err = self._run_child("flow", str(self.cfg.root), "-", "7", tag="after-raise")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._held_lines(err, "issue_7"), [], err)
        self.assertEqual(self._state("7"), state.COMPLETE)

    @unittest.skipUnless(hasattr(signal, "SIGKILL"), "needs SIGKILL")
    def test_a_killed_run_holds_nothing_and_blocks_nothing(self) -> None:
        """While run A (another process) holds 7, a run here is refused and changes nothing;
        once A is SIGKILLed mid-drive — no cleanup of its own at all — a run here drives 7."""
        _briefed(self.cfg, "7")
        a, _pause = self._hold("flow", "7", tag="A")
        before = _fingerprint(self.cfg.bundle_root)

        rc = self._cli(["7"])

        err = self.err.getvalue()
        self.assertEqual(rc, 1, f"a second driver ran while another process held 7:\n{err}")
        self.assertTrue(self._held_lines(err, "issue_7"), err)
        self.assertEqual(_fingerprint(self.cfg.bundle_root), before)

        a.send_signal(signal.SIGKILL)
        a.wait(timeout=_WAIT)

        rc = self._cli(["7"])

        err = self.err.getvalue()
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._held_lines(err, "issue_7"), [], err)
        self.assertEqual(self._state("7"), state.COMPLETE)

    # -- (ii) implicit reach is excluded, not refused --------------------------------------

    def test_the_csv_sweep_skips_a_bundle_another_live_run_holds(self) -> None:
        """A CSV batch sweeps every in-flight bundle after its Plan session. With 7 held by a
        live run in another process, the sweep names 7, leaves it untouched, and drives the
        rest (8) to COMPLETE."""
        _briefed(self.cfg, "7")
        _briefed(self.cfg, "8")
        a, _pause = self._hold("flow", "7", tag="A")
        leaves.do_plan_batch = _quiet_plan
        seven = self.cfg.bundle("7")
        before = _fingerprint(seven)

        rc = self._cli([], csv="tracker.csv")

        err = self.err.getvalue()
        self.assertTrue([ln for ln in self._held_lines(err, "issue_7") if "NOT driven" in ln],
                        err)
        self.assertEqual(_fingerprint(seven), before, "the sweep drove a bundle A holds")
        self.assertEqual(self._state("8"), state.COMPLETE)
        self.assertNotIn("\t7", self.out.getvalue())       # not in this run's results
        self.assertEqual(rc, 0, err)
        self.assertIsNone(a.poll())

    def test_the_csv_sweep_skips_every_bundle_it_cannot_claim(self) -> None:
        """Fail closed on the implicit path: with no claim file openable, the sweep drives
        NOTHING — each in-flight bundle is named and left as it was, rather than driven with
        nothing keeping a second run off it. On the base both are driven."""
        _briefed(self.cfg, "7")
        _briefed(self.cfg, "8")
        self._broken_claims_dir()
        leaves.do_plan_batch = _quiet_plan
        before = _fingerprint(self.cfg.bundle_root)

        self._cli([], csv="tracker.csv")

        err = self.err.getvalue()
        for name in ("issue_7", "issue_8"):
            self.assertTrue([ln for ln in self._unclaimable_lines(err, name)
                             if "NOT driven" in ln], err)
        self.assertEqual(_fingerprint(self.cfg.bundle_root), before)

    def test_split_adoption_skips_a_child_another_live_run_holds(self) -> None:
        """`pdca flow 500` splits 500 at its Plan pre-pass into 601 and 602; before the
        run gets to adopt them, another process starts driving 601. Adoption names 601 as
        NOT adopted, leaves it alone, and still adopts and drives 602."""
        holder: list[subprocess.Popen] = []

        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            parent = _ready_to_split(cfg, "500", ("child-a", "child-b"))
            split.accept(parent, ["601", "602"], cfg)
            holder.append(self._hold("flow", "601", tag="A")[0])

        leaves.do_plan_batch = plan

        rc = self._cli(["500"])

        err = self.err.getvalue()
        self.assertEqual(len(holder), 1, err)
        self.assertTrue([ln for ln in self._held_lines(err, "issue_601")
                         if "NOT adopted" in ln], err)
        self.assertEqual(self._state("601"), state.PLANNED, "601 was driven under its holder")
        self.assertEqual(self._state("602"), state.COMPLETE, err)
        self.assertEqual(self._state("500"), state.COMPLETE, err)
        self.assertEqual(rc, 0, err)
        self.assertIsNone(holder[0].poll())

    def test_split_adoption_skips_a_child_it_cannot_claim(self) -> None:
        """Fail closed in adoption: the claim on 601 cannot be LOCKED (a non-contention
        failure, ENOLCK); 601 is named as NOT adopted and left PLANNED, and 602 is still
        adopted and driven. On the base 601 is adopted and driven."""
        real = act._lock_exclusive

        def no_lock_for_601(fh, *, wait: bool = True) -> None:
            if Path(fh.name).name.startswith("issue_601-"):
                raise OSError(errno.ENOLCK, "No locks available")
            real(fh, wait=wait)

        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            parent = _ready_to_split(cfg, "500", ("child-a", "child-b"))
            split.accept(parent, ["601", "602"], cfg)

        leaves.do_plan_batch = plan

        with mock.patch.object(act, "_lock_exclusive", no_lock_for_601):
            rc = self._cli(["500"])

        err = self.err.getvalue()
        self.assertTrue([ln for ln in self._unclaimable_lines(err, "issue_601")
                         if "NOT adopted" in ln], err)
        self.assertEqual(self._state("601"), state.PLANNED, err)
        self.assertEqual(self._state("602"), state.COMPLETE, err)
        self.assertEqual(rc, 0, err)

    # -- a claim covers what the run DRIVES: let go of what it will not ----------------------

    def test_a_swept_bundle_the_scheduler_holds_is_let_go_while_the_batch_runs(self) -> None:
        """A CSV batch (another process) sweeps 7 and 8, but 8 declares a dependency nothing
        can satisfy, so the scheduler holds it and the batch tells the operator to resolve
        it and re-run. While the batch is still driving 7: `pdca flow 7` is refused (red on
        the base), and — once 8's brief is fixed — `pdca flow 8` is NOT refused by the batch
        that stopped driving it: it drives 8 to COMPLETE."""
        _briefed(self.cfg, "7")
        eight = _briefed(self.cfg, "8", "- **Depends on:** 999")
        a, _pause = self._hold("csv", tag="batch")

        rc = self._cli(["7"])
        self.assertEqual(rc, 1, self.err.getvalue())
        self.assertTrue(self._held_lines(self.err.getvalue(), "issue_7"), self.err.getvalue())

        (eight / "brief.md").write_text(_brief("slice-8"), encoding="utf-8")
        rc = self._cli(["8"])

        err = self.err.getvalue()
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._held_lines(err, "issue_8"), [], err)
        self.assertEqual(self._state("8"), state.COMPLETE, err)
        self.assertIsNone(a.poll(), "the batch should still be alive, driving 7")
        batch_err = (self.tmp / "batch.err").read_text(encoding="utf-8")
        self.assertIn("issue_8 held this run — unresolved dependency (999)", batch_err)

    def test_an_adopted_child_the_reschedule_holds_is_let_go_while_the_run_goes_on(
            self) -> None:
        """Run A (another process) drives 500, which is already split into 601 and 602;
        602's brief declares a dependency nothing can satisfy, so the reschedule holds it
        and A drives only 601. While A is inside 601's build: `pdca flow 601` is refused —
        an adopted child is A's (red on the base) — and, once 602's brief is fixed,
        `pdca flow 602` is NOT refused by the run that dropped it."""
        parent = _ready_to_split(self.cfg, "500", ("child-a", "child-b"))
        split.accept(parent, ["601", "602"], self.cfg)
        six02 = self.cfg.bundle("602") / "brief.md"
        fixed = six02.read_text(encoding="utf-8")
        six02.write_text(fixed + "- **Depends on:** 999\n", encoding="utf-8")
        a, pause = self._hold("flow", "500", tag="A")
        self.assertEqual((pause / "ready").read_text(encoding="utf-8"), "issue_601")

        rc = self._cli(["601"])
        self.assertEqual(rc, 1, self.err.getvalue())
        self.assertTrue(self._held_lines(self.err.getvalue(), "issue_601"),
                        self.err.getvalue())

        six02.write_text(fixed, encoding="utf-8")
        rc = self._cli(["602"])

        err = self.err.getvalue()
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._held_lines(err, "issue_602"), [], err)
        self.assertEqual(self._state("602"), state.COMPLETE, err)
        self.assertIsNone(a.poll(), "run A should still be alive, driving 601")

    def test_a_named_id_the_run_skips_is_not_its_to_speak_for(self) -> None:
        """Run A is `pdca flow 7 9`; 9 has no brief and its Plan pre-pass writes none, so A
        skips 9 and drives 7. With A still mid-drive, 9 is briefed and split from another
        shell: no live run will drive 901/902 (A is not driving 9), so the accept prints
        the instruction byte-identical — and following it is not refused."""
        _briefed(self.cfg, "7")
        a, _pause = self._hold("flow", "7", "9", tag="A")
        _ready_to_split(self.cfg, "9", ("child-a", "child-b"))

        rc, err = self._split_here("9", "901,902")

        self.assertEqual(rc, 0, err)
        self.assertIn(self._instruction("9", "901 902"), err.splitlines())
        self.assertNotIn("will drive the children", err)

        rc = self._cli(["901", "902"])
        err = self.err.getvalue()
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._state("901"), state.COMPLETE, err)
        self.assertIsNone(a.poll(), "run A should still be alive, driving 7")

    def test_a_parent_whose_wave_is_behind_the_run_is_not_its_to_speak_for(self) -> None:
        """Run A is `pdca flow 7 8`, 8 declaring `Conflicts with: 7`, so 8 has a wave of its
        own after 7's. Nobody answers 7's sign-off, so A walks away from 7 and moves on to
        8. With A inside 8's build it still HOLDS 7 — but the one point where it adopts a
        split of 7 (the splice after 7's wave) is behind it. A split of 7 accepted now, from
        another shell, is not one A will drive: the instruction, byte-identical — and
        following it is not refused."""
        _briefed(self.cfg, "7")
        _briefed(self.cfg, "8", "- **Conflicts with:** 7")
        a, _pause = self._hold("flow", "--pause-on=issue_8", "--walk-away=issue_7", "7", "8",
                               tag="A")
        self.assertEqual(self._state("7"), state.AWAITING_SIGNOFF)
        (self.cfg.bundle("7") / split.PROPOSAL).write_text(_proposal("child-a", "child-b"),
                                                          encoding="utf-8")

        rc, err = self._split_here("7", "701,702")

        self.assertEqual(rc, 0, err)
        self.assertIn(self._instruction("7", "701 702"), err.splitlines())
        self.assertNotIn("will drive the children", err)

        rc = self._cli(["701", "702"])
        err = self.err.getvalue()
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._state("701"), state.COMPLETE, err)
        self.assertIsNone(a.poll(), "run A should still be alive, driving 8")
        rc = self._cli(["7"])                   # …and 7 itself is still A's
        self.assertEqual(rc, 1, self.err.getvalue())
        self.assertTrue(self._held_lines(self.err.getvalue(), "issue_7"), self.err.getvalue())

    # -- (v) the hint is truthful ------------------------------------------------------------

    def test_an_accept_inside_the_run_driving_the_parent_does_not_say_run_flow(self) -> None:
        """`pdca flow 500`, and 500's Plan session runs `pdca split 500 --accept --ids
        601,602`. The run adopts and drives both children, so the accept must not tell the
        operator to start `pdca flow 601 602` — it says the running flow will drive them."""
        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            _ready_to_split(cfg, "500", ("child-a", "child-b"))
            cli._split(cfg, SimpleNamespace(issue_id="500", accept=True, ids="601,602"))

        leaves.do_plan_batch = plan

        rc = self._cli(["500"])

        err = self.err.getvalue()
        self.assertNotIn(self._instruction("500", "601 602"), err)
        self.assertIn("issue_500 marked split; the running", err)
        self.assertIn("will drive the children (601 602)", err)
        self.assertEqual(self._state("601"), state.COMPLETE, err)   # …and it does
        self.assertEqual(self._state("602"), state.COMPLETE, err)
        self.assertEqual(rc, 0, err)

    def test_a_split_command_spawned_by_the_run_is_neither_blocked_nor_told_to_run_flow(
            self) -> None:
        """The same, with `pdca split --accept` as a REAL child process of the run (as it is
        from an interactive Plan session): it is not blocked by the run's claim on the
        parent (it returns promptly, rc 0), and prints the truthful line rather than the
        instruction."""
        spawned: list[tuple[int, str]] = []

        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            _ready_to_split(cfg, "500", ("child-a", "child-b"))
            spawned.append(self._run_child("split", str(cfg.root), "500", "601,602",
                                           tag="accept"))

        leaves.do_plan_batch = plan

        rc = self._cli(["500"])

        err = self.err.getvalue()
        self.assertEqual(len(spawned), 1, err)
        rc_split, err_split = spawned[0]
        self.assertEqual(rc_split, 0, err_split)
        self.assertEqual(self._instruction_lines(err_split, "500", "601 602"), [], err_split)
        self.assertIn("will drive the children (601 602)", err_split)
        self.assertEqual(self._state("601"), state.COMPLETE, err)
        self.assertEqual(self._state("602"), state.COMPLETE, err)
        self.assertEqual(rc, 0, err)

    def test_an_accept_from_another_shell_while_a_live_run_holds_the_parent(self) -> None:
        """Run A (`pdca flow 500`, another process) sits in its Plan pre-pass with 500's
        proposal drafted. The operator accepts the split from a SECOND shell — no run around
        that command at all. A holds 500, so A will adopt the children: the accept says so
        instead of printing the instruction (red on the base). Then A is let go, and does."""
        a, pause = self._hold("plan-pause", "500", tag="A")

        rc, err = self._split_here("500", "601,602")

        self.assertEqual(rc, 0, err)
        self.assertNotIn(self._instruction("500", "601 602"), err)
        self.assertIn("will drive the children (601 602)", err)

        (pause / "go").write_text("", encoding="utf-8")
        rc_a, err_a = self._finish(a, "A")
        self.assertEqual(rc_a, 0, err_a)
        self.assertEqual(self._state("601"), state.COMPLETE, err_a)
        self.assertEqual(self._state("602"), state.COMPLETE, err_a)

    def test_an_accept_inside_a_csv_batch_plan_session_does_not_say_run_flow(self) -> None:
        """`pdca flow --from-csv …`: the batch's Plan session splits 500. The sweep after the
        session drives every in-flight bundle, the children included — so no instruction."""
        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            _ready_to_split(cfg, "500", ("child-a", "child-b"))
            cli._split(cfg, SimpleNamespace(issue_id="500", accept=True, ids="601,602"))

        leaves.do_plan_batch = plan

        rc = self._cli([], csv="tracker.csv")

        err = self.err.getvalue()
        self.assertNotIn(self._instruction("500", "601 602"), err)
        self.assertIn("will drive the children (601 602)", err)
        self.assertEqual(self._state("601"), state.COMPLETE, err)
        self.assertEqual(self._state("602"), state.COMPLETE, err)
        self.assertEqual(rc, 0, err)

    def test_an_accept_after_the_csv_batch_has_ended_prints_the_instruction(self) -> None:
        """A `split --accept` started inside a CSV batch's Plan session, but which only
        accepts AFTER the batch has ended (here: by raising, before its sweep) — nothing will
        drive the children any more, so it prints the instruction, byte-identical. A mark
        inherited from a run that is gone must not speak for it."""
        late: list[subprocess.Popen] = []
        gate = self.tmp / "gate"

        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            _ready_to_split(cfg, "500", ("child-a", "child-b"))
            late.append(self._spawn("split", str(cfg.root), "500", "601,602", str(gate),
                                    tag="late"))
            raise KeyboardInterrupt           # the batch ends here, before its sweep

        leaves.do_plan_batch = plan

        with self.assertRaises(KeyboardInterrupt):
            self._cli([], csv="tracker.csv")
        gate.write_text("", encoding="utf-8")
        rc, err = self._finish(late[0], "late")

        self.assertEqual(rc, 0, err)
        self.assertEqual(len(self._instruction_lines(err, "500", "601 602")), 1, err)
        self.assertNotIn("will drive the children", err)

    def test_a_standalone_accept_prints_the_instruction_byte_identical(self) -> None:
        """No run at all — an accept typed in a shell: the instruction, exactly as today."""
        _ready_to_split(self.cfg, "500", ("child-a", "child-b"))

        rc, err = self._split_here("500", "601,602")

        self.assertEqual(rc, 0, err)
        self.assertIn(self._instruction("500", "601 602"), err.splitlines())

    def test_an_accept_inside_a_run_not_driving_that_parent_keeps_the_instruction(
            self) -> None:
        """`pdca flow 7`, whose Plan session also accepts a split of 900 — a bundle this run
        is NOT driving. Nothing will drive 901/902, so the instruction stays, byte-identical."""
        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            _briefed(cfg, "7")
            _ready_to_split(cfg, "900", ("child-a", "child-b"))
            cli._split(cfg, SimpleNamespace(issue_id="900", accept=True, ids="901,902"))

        leaves.do_plan_batch = plan

        rc = self._cli(["7"])

        err = self.err.getvalue()
        self.assertIn(self._instruction("900", "901 902"), err.splitlines())
        self.assertEqual(self._state("7"), state.COMPLETE, err)
        self.assertEqual(self._state("901"), state.PLANNED)
        self.assertEqual(rc, 0, err)

    # -- the ownership record is never a bundle artifact -------------------------------------

    def test_claims_live_outside_every_bundle_and_are_gitignored_in_the_render(self) -> None:
        """A batch that claims bundles and adopts a split leaves its ownership record ONLY
        under the process dir (docs 07 §Lanes names `process/.drive-claims/`) — never inside
        a bundle, where `state.state` and a results commit would see it — and everything it
        leaves there is ignored by the render's `.gitignore`."""
        git = shutil.which("git")
        if git is None or _IGNORE is None:
            self.skipTest("needs git and the render's .gitignore")
        _briefed(self.cfg, "7")

        def plan(cfg: Config, csv: str | None = None, ids: list[str] | None = None) -> None:
            _ready_to_split(cfg, "500", ("child-a", "child-b"))
            cli._split(cfg, SimpleNamespace(issue_id="500", accept=True, ids="601,602"))

        leaves.do_plan_batch = plan

        rc = self._cli([], csv="tracker.csv")
        self.assertEqual(rc, 0, self.err.getvalue())

        in_bundles = [p for p in self.cfg.bundle_root.rglob("*")
                      if _CLAIMS in p.parts or p.suffix == ".sweep"]
        self.assertEqual(in_bundles, [])
        left = ([p for p in self.cfg.process_dir.rglob("*") if p.is_file()]
                if self.cfg.process_dir.is_dir() else [])
        # The record exists — this is not a vacuous pass over nothing (red on the base,
        # which records no ownership at all) …
        self.assertTrue([p for p in left if _CLAIMS in p.parts],
                        f"no ownership record under {self.cfg.process_dir}")
        # … and every bit of it is ignored by the render, so no commit can carry it.
        repo = self.tmp / "ignore-check"
        repo.mkdir()
        subprocess.run([git, "init", "-q", str(repo)], check=True, capture_output=True)
        shutil.copyfile(_IGNORE, repo / ".gitignore")
        for p in left:
            rel = p.relative_to(self.cfg.root).as_posix()
            probe = subprocess.run([git, "-C", str(repo), "check-ignore", "-q", "--no-index",
                                    rel], capture_output=True)
            self.assertEqual(probe.returncode, 0, f"{rel} is not ignored by {_IGNORE.name}")


if __name__ == "__main__":
    unittest.main()
