"""A split must not strand its own children on the run that caused it (#469).

Before this, the drive set froze at the start of the run: `flow_ids` built its bundle list
once and `_drive_and_act` computed `wave_list` once, so when a bundle reached
`close-disposition = split` mid-run the parent went terminal, the children materialised by
`pdca split --accept` sat PLANNED and undriven, and the operator restarted the whole thing
by hand with `pdca flow <child-ids>`.

Every drive here goes **through `cli._flow`** — never a hand-picked `flow.*` call — because
that is the surface the operator (and their automation) actually uses, and the surface
where four of #449's five iterations found their parity breaks. Both CLI shapes are the
same machinery since #468 (`cli.py:604-622`), so parity is asserted where it is now
observable: same bytes on disk, `flow <id>` and `flow <id> <sibling>`, same child states,
same announcements, same exit code.

Everything is the ordinary offline driver suite: all six leaves stubbed (the fixture
mirrors `tests/test_flow_slice.py:31-56`), gates empty, no tracker / network / `gh` /
container. The split itself is not simulated — the tests call the PRODUCTION `split.accept`
(`split.py:525`), so the parent's close marker, its `split-lineage.json` children record
and the child bundles are byte-for-byte what `pdca split --accept` leaves on disk.

Modules are imported, never new symbols (`from pdca_harness import cli, flow, …`): a
`from pdca_harness.flow import <new helper>` would raise ImportError on the C4 red leg,
which `engine/scripts/run-verify.sh` classifies PDCA-UNVERIFIABLE rather than red.

    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import signal
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

from pdca_harness import cli, flow, leaves, split, state
from pdca_harness.config import Config, LeafConfig


class _RunDidNotReturn(BaseException):
    """The deadline below, as a **BaseException**.

    `flow._isolate` contains `Exception` around every per-bundle step, adoption included
    (`flow.py:60-69`) — so a watchdog raising an ordinary exception is caught, logged as
    "split adoption failed", and the run limps on: the hang it was there to prove becomes a
    green test. `_isolate`'s docstring states the contract this uses instead — "only
    ``Exception`` is contained", KeyboardInterrupt / SystemExit propagate — so a
    BaseException reaches the test, where unittest records it as an error.
    """


@contextlib.contextmanager
def _deadline(seconds: float):
    """Turn a run that never returns into an ordinary test FAILURE.

    Adoption walks a lineage graph read off disk, and a `children` edge an operator can
    hand-edit into a CYCLE makes "bounded" and "unbounded" differ by whether the walk
    remembers what it has examined — a difference no outcome assertion can observe, because
    the unbounded version never reaches it: the test (and with it the whole module, and the
    C4 gate) simply hangs. SIGALRM is what makes that difference assertable.

    Best-effort by design: without SIGALRM (Windows), or off the main thread where the
    signal module refuses to install a handler, the body still runs unguarded — a watchdog
    that cannot arm must not fail a suite it is only there to protect.
    """
    if not hasattr(signal, "SIGALRM") or threading.current_thread() is not \
            threading.main_thread():
        yield
        return

    def _expired(_sig, _frame):
        raise _RunDidNotReturn(
            f"the run did not return within {seconds}s — the lineage walk is unbounded")

    previous = signal.signal(signal.SIGALRM, _expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def _stub_config(root: Path, *, lanes: int = 1, lane_preflight: str = "") -> Config:
    """All six leaves stubbed, gates empty (all-PASS stub rows) — the same fixture shape as
    `tests/test_flow_slice.py:31-56`, including the hermetic toy checkout inside the tmp
    root (the sibling convention would resolve to a SHARED /tmp/example-repo).

    `lanes` / `lane_preflight` are the two knobs a REFUSED run needs (issue #213): a wave
    pools only at `lanes > 1` with more than one runnable bundle, and a declared
    `[driver].lane_preflight` that exits non-zero is what refuses it. Both default to the
    serial values, so every other test is untouched."""
    return Config(
        lanes=lanes,
        lane_preflight=lane_preflight,
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


def _proposal(*bodies: str) -> str:
    """A `split-proposal.md` the production parser accepts (`split.parse`)."""
    out = "<!-- pdca:split-proposal v1 -->\n# Split proposal\n\n"
    for i, body in enumerate(bodies, 1):
        out += f"<!-- pdca:child child-{i} -->\n{body}\n<!-- pdca:end child-{i} -->\n\n"
    return out


#: child-2 declares an ordering edge on its sibling LABEL — `split.accept` rewrites it to
#: the real id, which is what makes the adopted children land in two waves.
_CHILD_ONE = _brief("child-first")
_CHILD_TWO = _brief("child-second", "- **Depends on:** child-1")
#: …and the independent sibling: no ordering edge, so the two children land in ONE wave.
#: That is the shape that FANS OUT (`flow._wave_pools`: lanes > 1 AND >1 runnable), which
#: is how an adopted wave can be refused by the per-lane preflight.
_SIBLING_TWO = _brief("child-second")

#: Driven ALONGSIDE the bundle under test so the multi-id shape really is a multi-id run,
#: without changing what the run drives in wave 0 (it is independent and completes).
FILLER = "FILLER469"


class AdoptSplitChildren(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = self._instance()
        self.err = io.StringIO()
        self.out = io.StringIO()
        self.waves_driven: list[list[str]] = []
        self.pointed: list[list[str]] = []
        self.results: dict[str, str] = {}
        self.passes = 0                  # one `_build_all` call == one pass of one wave
        # `cli._flow` reaches sign-off through `leaves.run_signoff_batch` only — the
        # per-bundle `leaves.run_signoff` belongs to the single-bundle library driver and
        # is not on the CLI path since #468 (`flow.py:380-387`).
        self._orig = (leaves.do_plan, leaves.run_signoff_batch, flow._drive_wave,
                      flow._build_all, flow._point_at_integration)
        self._orig_ids = flow.flow_ids
        self.addCleanup(self._restore_flow_ids)

    def _restore_flow_ids(self) -> None:
        flow.flow_ids = self._orig_ids

    def tearDown(self) -> None:
        (leaves.do_plan, leaves.run_signoff_batch, flow._drive_wave, flow._build_all,
         flow._point_at_integration) = self._orig

    # -- instance + capture -------------------------------------------------------------

    def _instance(self, **cfg_kw) -> Config:
        """A fresh, hermetic instance root, removed at teardown."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return _stub_config(tmp, **cfg_kw)

    def _reset(self, **cfg_kw) -> None:
        """A second leg of the same test, on a clean instance and unpatched leaves."""
        (leaves.do_plan, leaves.run_signoff_batch, flow._drive_wave, flow._build_all,
         flow._point_at_integration) = self._orig
        flow.flow_ids = self._orig_ids
        self.cfg = self._instance(**cfg_kw)
        self.err = io.StringIO()
        self.out = io.StringIO()
        self.waves_driven = []
        self.pointed = []
        self.results = {}
        self.passes = 0

    def _args(self, ids: list[str], *, max_passes: int | None = None,
              no_publish: bool = True) -> SimpleNamespace:
        """The `pdca flow <ids…>` argv as `cli._flow` receives it — arity is the CLI's own
        presentation switch (`cli.py:622`), so it has to be the thing under test rather
        than a hand-picked `flow.*` call.

        `no_publish` defaults to the suite's ordinary `--no-publish` (no git remotes), and
        is turned OFF by the one test that has to watch the wave BOUNDARY — publish + fold
        — which only exists when the run sequences its waves."""
        return SimpleNamespace(issue_ids=ids, from_csv=None, from_briefs=None,
                               no_publish=no_publish, no_act=True, by="", lanes=None,
                               max_passes=max_passes)

    def _cli(self, ids: list[str], *, cfg: Config | None = None,
             max_passes: int | None = None, no_publish: bool = True) -> int:
        """Run `pdca flow <ids…>` through `cli._flow` and return its exit code."""
        with redirect_stderr(self.err), redirect_stdout(self.out):
            return cli._flow(cfg or self.cfg,
                             self._args(ids, max_passes=max_passes, no_publish=no_publish))

    def _state(self, issue_id: str, cfg: Config | None = None) -> str:
        return state.state((cfg or self.cfg).bundle(issue_id))

    def _adoptions(self, err: str | None = None) -> list[str]:
        return [ln.split("flow: ")[-1] for ln in (err or self.err.getvalue()).splitlines()
                if "split → adopted children" in ln]

    # -- the split, exactly as `pdca split --accept` leaves it --------------------------

    def _split_now(self, parent: Path, ids: list[str], bodies: list[str],
                   cfg: Config | None = None) -> None:
        """Decompose `parent` into `ids` through the PRODUCTION `split.accept`: child
        bundles + each child's lineage record, the parent's merged `children` record, its
        build-notes breadcrumb and its `close-disposition = split` marker."""
        parent.mkdir(parents=True, exist_ok=True)
        if not (parent / "brief.md").exists():
            (parent / "brief.md").write_text(_brief("parent-slice"), encoding="utf-8")
        (parent / split.PROPOSAL).write_text(_proposal(*bodies), encoding="utf-8")
        split.accept(parent, ids, cfg or self.cfg)

    def _arm(self, splits: dict[str, list[str]], *, bodies: list[str] | None = None,
             iterate_once: str = "", walk_away: str = "", after_split=None) -> None:
        """Stub the leaves so each id in `splits` splits mid-flight, into its child ids.

        The path walked is the documented Entry B: the sign-off session records
        `iterate-plan`, the driver re-opens the bundle to UNPLANNED, and the next pass's
        serial Plan pre-pass concludes it is too large and splits it. `iterate_once` makes
        one bundle cost a second pass (an ordinary `iterate-do` on its first sign-off) —
        how a wave is made to want more budget than the run has left. `walk_away` is the
        session that is never answered for one bundle at all, which halts it at
        AWAITING_SIGNOFF — the ordinary end of an interactive run, and the only way an
        ADOPTED bundle finishes a run un-terminal without the run itself failing."""
        bodies = bodies or [_CHILD_ONE, _CHILD_TWO]
        real_plan, real_signoff_batch, real_wave, real_build_all, real_point = self._orig
        done: set[str] = set()

        def splitting_plan(d: Path, cfg: Config, csv: str | None = None) -> None:
            iid = d.name.removeprefix("issue_")
            if iid in splits and f"split:{iid}" not in done:
                done.add(f"split:{iid}")
                self._split_now(d, splits[iid], bodies, cfg=cfg)
                if after_split is not None:
                    after_split()
                return
            real_plan(d, cfg, csv)

        def decide(d: Path) -> bool:
            """Write this bundle's scripted decision, if it has one this pass. True ⇒ the
            session answered here; False ⇒ let the real stub clear §6 and accept."""
            iid = d.name.removeprefix("issue_")
            if iid in splits and f"replan:{iid}" not in done:
                done.add(f"replan:{iid}")
                (d / leaves.SIGNOFF_DECISION).write_text(
                    "iterate-plan\nthis slice is too large — decompose it\n",
                    encoding="utf-8")
                return True
            if iid == iterate_once and "iterate" not in done:
                done.add("iterate")
                (d / leaves.SIGNOFF_DECISION).write_text(
                    "iterate-do\none more round\n", encoding="utf-8")
                return True
            if iid == walk_away:
                # No decision written and the real session never offered it: the bundle
                # halts at AWAITING_SIGNOFF, pass after pass, until the wave stops making
                # progress (`flow._drive_wave`) and names it.
                return True
            return False

        def signoff_batch(cfg: Config, bundles: list[Path]) -> None:
            real_signoff_batch(cfg, [d for d in bundles if not decide(d)])

        leaves.do_plan = splitting_plan
        leaves.run_signoff_batch = signoff_batch
        self._instrument()

    def _instrument(self) -> None:
        """The wave / pass / integration spies, WITHOUT arming a split — for the runs that
        must be shown to behave exactly as they do today."""
        _plan, _signoff, real_wave, real_build_all, real_point = self._orig

        def counting(cfg: Config, wave: list[Path]) -> None:
            self.passes += 1
            real_build_all(cfg, wave)

        def spy_wave(cfg: Config, wave: list[Path], **kw):
            # The production return value is handed straight back — post-fix it is the
            # wave's pass count, which the run's shared budget is kept in.
            self.waves_driven.append([d.name for d in wave])
            return real_wave(cfg, wave, **kw)

        def spy_point(integ, runnable: list[Path]) -> None:
            self.pointed.append([d.name for d in runnable])
            return real_point(integ, runnable)

        flow._build_all = counting
        flow._drive_wave = spy_wave
        flow._point_at_integration = spy_point

    def _capture_results(self) -> None:
        """Record the results map `cli._flow` is handed, without becoming a second one.

        A pass-through wrapper around the PRODUCTION `flow.flow_ids`: it calls the real
        function and hands its exact return value on to `cli._flow`, so what is asserted
        is the map the CLI derives its report and exit code from (#468) — the only place
        "excluded from the results map" is observable, since the single-id presentation
        prints one line for the id it was given."""
        real = self._orig_ids

        def capture(cfg, ids, **kw):
            results = real(cfg, ids, **kw)
            self.results = dict(results)
            return results

        flow.flow_ids = capture

    def _watch_examined(self) -> list[str]:
        """Every parent the adoption walk examines, in order — a pass-through spy on the
        PRODUCTION `_children_of_split`, so "a parent is examined once" is asserted
        directly and not merely inferred from the run having terminated.

        Reached by `getattr`, like every other new name in this module: the helper is what
        the patch ADDS, so on the C4 red leg it is absent and the list simply stays empty
        (the test then fails on the states it asserts — the defect — rather than on a
        missing attribute)."""
        real = getattr(flow, "_children_of_split", None)
        seen: list[str] = []
        if real is None:
            return seen

        def spy(cfg: Config, d: Path, *, known: set[str]):
            seen.append(d.name)
            return real(cfg, d, known=known)

        flow._children_of_split = spy
        self.addCleanup(setattr, flow, "_children_of_split", real)
        return seen

    def _build_fails(self, iid: str) -> None:
        """One bundle's Do leaf raises on every pass — the ordinary way a wave STALLS.

        `_advance_one` contains it (`flow.py:458`), so the bundle's state never changes and
        nobody is left awaiting sign-off: the wave takes `_drive_wave`'s no-progress exit
        instead of running its allowance out. A pass-through spy — every OTHER bundle in
        the wave is built by the production leaf, so the fault is one injected failure, not
        a fixture that stops building."""
        real = leaves.do_build

        def failing(d: Path, cfg: Config) -> None:
            if d.name == f"issue_{iid}":
                raise RuntimeError(f"builder leaf failed for {d.name}")
            real(d, cfg)

        leaves.do_build = failing
        self.addCleanup(setattr, leaves, "do_build", real)

    def _silence_signoff(self) -> None:
        """A sign-off session the human walked away from: no decision written at all, so
        the bundle stays AWAITING_SIGNOFF — halted, and never terminal."""
        leaves.run_signoff_batch = lambda cfg, bundles: None

    # -- fixtures built by production code ----------------------------------------------

    def _drive_to_complete(self, cfg: Config, d: Path, max_passes: int = 2) -> None:
        """Carry one bundle to COMPLETE with production code and no adoption of its own
        (`_drive_wave` is the per-wave driver; it has never looked for children) — so a
        stranded split can be built without the very mechanism under test."""
        _plan, _signoff, real_wave, _build, _point = self._orig
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            real_wave(cfg, [d], by="t", today="2026-08-09", max_passes=max_passes)

    def _strand_a_split(self, cfg: Config, parent: str = "500",
                        ids: tuple[str, ...] = ("601", "602"),
                        bodies: list[str] | None = None) -> None:
        """Leave `cfg`'s instance exactly as an EARLIER run that split `parent` did: the
        parent terminal on `close-disposition = split` with a children record, its children
        sitting PLANNED and undriven. Built by production code — `split.accept` for the
        split, `flow._drive_wave` to carry the parent through Check + sign-off."""
        self._split_now(cfg.bundle(parent), list(ids),
                        bodies or [_CHILD_ONE, _CHILD_TWO], cfg=cfg)
        self._drive_to_complete(cfg, cfg.bundle(parent))
        # The fault the run has to recover is genuinely on disk before it starts.
        self.assertEqual(state.state(cfg.bundle(parent)), state.COMPLETE)
        self.assertEqual((cfg.bundle(parent) / state.CLOSE_MARKER).read_text(
            encoding="utf-8").strip(), "split")
        for cid in ids:
            self.assertEqual(state.state(cfg.bundle(cid)), state.PLANNED)

    def _briefed(self, iid: str, *extra: str, cfg: Config | None = None) -> Path:
        cfg = cfg or self.cfg
        d = cfg.bundle(iid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "brief.md").write_text(_brief(f"slice-{iid}", *extra), encoding="utf-8")
        return d

    def _complete_bystander(self, iid: str, cfg: Config | None = None) -> None:
        """A briefed bundle carried to COMPLETE by production code. Naming it alongside the
        parent changes the command's ARITY without changing what the run drives (`flow_ids`
        skips a terminal id, `flow.py:1121`) — which is how `pdca flow 500` and
        `pdca flow 500 999` are compared on identical disk."""
        cfg = cfg or self.cfg
        d = self._briefed(iid, cfg=cfg)
        self._drive_to_complete(cfg, d)
        self.assertEqual(state.state(d), state.COMPLETE)

    def _fork(self, cfg: Config) -> Config:
        """A byte-identical copy of `cfg`'s whole instance root, so two CLI shapes each
        start from the SAME bytes."""
        dst = Path(tempfile.mkdtemp()) / "root"
        shutil.copytree(cfg.root, dst)
        self.addCleanup(shutil.rmtree, dst.parent, ignore_errors=True)
        return _stub_config(dst, lanes=cfg.lanes, lane_preflight=cfg.lane_preflight)

    # -- criterion (1): a split INSIDE the run is driven by that run ---------------------

    def test_cli_flow_drives_the_children_of_a_mid_run_split(self) -> None:
        """`pdca flow 500`: the re-plan splits 500, and THIS run drives 601 and 602 to a
        terminal state — in waves AFTER the parent's, honouring the `Depends on` the split
        itself wrote into 602's brief, announcing each child's REAL wave read back from the
        recomputed schedule (601 in wave 1, 602 in wave 2), and reporting them in the one
        results map both CLI shapes present."""
        self._briefed("500")
        self._arm({"500": ["601", "602"]})

        rc = self._cli(["500"])

        self.assertEqual(self._state("500"), state.COMPLETE)
        self.assertEqual(self._state("601"), state.COMPLETE)  # adopted, not stranded
        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(rc, 0)
        # AFTER the parent's wave, and 602 after 601 — its own declared ordering.
        self.assertEqual(self.waves_driven,
                         [["issue_500"], ["issue_601"], ["issue_602"]])
        self.assertEqual(self._adoptions(), [
            "issue_500 split → adopted children issue_601 into wave 1",
            "issue_500 split → adopted children issue_602 into wave 2"])
        # …and the run reports them: the map `_report_single`/`_report_batch` read (#468)
        # is the drive set, which adoption extended.
        printed = self.out.getvalue()
        self.assertIn(f"{state.COMPLETE}\t{self.cfg.bundle('500')}", printed)

    def test_adopted_children_go_through_the_same_integration_reconciliation(self) -> None:
        """An adopted wave is an ORDINARY wave: its bundles are reconciled with this run's
        integration state by the same `_point_at_integration` call every other wave goes
        through (`flow.py:899`), not by a second mechanism bolted onto adoption."""
        self._briefed("500")
        self._arm({"500": ["601", "602"]})

        self._cli(["500"])

        self.assertEqual(self.pointed,
                         [["issue_500"], ["issue_601"], ["issue_602"]])

    def test_the_wave_a_split_happened_in_still_folds_for_its_adopted_wave(self) -> None:
        """Adoption GROWS the schedule, so "is this the last wave?" has to be read live.

        The wave boundary — publish, then fold the cumulative accepted work onto the
        run-scoped integration branch the NEXT wave builds on — is skipped on the final
        wave (`tests/test_flow_slice.py:1137`: the last wave folds nothing). Answer that
        from a `len(wave_list)` cached before the loop and a one-wave run that adopts folds
        NOTHING: wave 0's accepted patch never reaches the integration branch, and every
        adopted child is built and verified against a base that is missing its own parent's
        work — silently, because each bundle is green on its own.

        So this is the one test that runs with publishing ON (`--no-publish` off, stub
        publisher ⇒ `integrate.fold`'s dry-run, no git remotes), spying the production fold
        exactly as the peer wave test does (`tests/test_flow_slice.py:1122-1128`)."""
        self._briefed("500")
        self._arm({"500": ["601", "602"]})
        folds: list[list[str]] = []
        real_fold = flow.integrate.fold

        def spy_fold(cfg: Config, accepted: list[Path], *, dry_run: bool = False,
                     locks=None):
            folds.append([d.name for d in accepted])
            return real_fold(cfg, accepted, dry_run=dry_run, locks=locks)

        flow.integrate.fold = spy_fold
        self.addCleanup(setattr, flow.integrate, "fold", real_fold)

        rc = self._cli(["500"], no_publish=False)

        self.assertEqual(self._state("601"), state.COMPLETE)
        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(rc, 0)
        # Wave 0 folds before the adopted wave 1 builds, and wave 1 before wave 2; the
        # final wave still folds nothing. `accepted` is cumulative, so the second fold
        # carries the parent's work too — that is the base 602 is meant to build on.
        self.assertEqual(folds, [["issue_500"], ["issue_500", "issue_601"]])

    # -- criterion (2): recovery — the named bundle is ALREADY terminal on a split -------

    def test_cli_flow_recovers_children_stranded_by_an_earlier_run(self) -> None:
        """An id whose bundle is already terminal on a split is not work to drive — but its
        children may still be sitting PLANNED where an earlier run left them. Naming the
        parent again is the operator's recovery, and no pre-run short-circuit may swallow
        it: `flow_ids` skips the parent (with the hint #468 gave both shapes) AND hands it
        on as an adoption seed."""
        self._strand_a_split(self.cfg)
        self._instrument()

        rc = self._cli(["500"])

        self.assertEqual(self._state("601"), state.COMPLETE)
        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(rc, 0)
        self.assertEqual(self.waves_driven, [["issue_601"], ["issue_602"]])
        self.assertEqual(self._adoptions(), [
            "issue_500 split → adopted children issue_601 into wave 0",
            "issue_500 split → adopted children issue_602 into wave 1"])
        err = self.err.getvalue()
        # The parent itself is still skipped, and still gets #468's non-destructive hint.
        self.assertIn("already terminal (COMPLETE), skipped", err)
        self.assertNotIn("rm -rf", err)

    def test_a_stale_chain_is_walked_through_its_terminal_generation(self) -> None:
        """Recovery has to follow the lineage as far as it actually goes. A run that
        stopped part-way through a chain (500 split → 601, 602; 601 then split → 701, 702)
        leaves 601 TERMINAL on a split — undrivable itself, but the only route to the
        grandchildren that are still stranded. Dropping it where the terminal filter finds
        it strands 701/702 forever."""
        self._strand_a_split(self.cfg, parent="500", ids=("601", "602"))
        self._split_now(self.cfg.bundle("601"), ["701", "702"], [_CHILD_ONE, _CHILD_TWO])
        self._drive_to_complete(self.cfg, self.cfg.bundle("601"))
        self.assertEqual(self._state("601"), state.COMPLETE)   # terminal on ITS OWN split
        self.assertEqual(self._state("701"), state.PLANNED)
        self._instrument()

        self._cli(["500"])

        self.assertEqual(self._state("602"), state.COMPLETE)   # the drivable child
        self.assertEqual(self._state("701"), state.COMPLETE)   # …and the grandchildren
        self.assertEqual(self._state("702"), state.COMPLETE)
        err = self.err.getvalue()
        # Attributed to the parent that actually declared them, not to the run's seed.
        self.assertIn("issue_601 split → adopted children issue_701", err)
        self.assertIn("issue_601 split → adopted children issue_702", err)

    # -- criterion (3): the two CLI shapes agree on byte-identical disk ------------------

    def test_both_cli_shapes_adopt_identically_on_the_same_bytes(self) -> None:
        """One event, one description, one exit code. `pdca flow 500` and `pdca flow 500
        FILLER` are the same run on the same bytes — the filler is independent and
        completes, so it changes the command's arity and nothing else. Since #468 both
        shapes are one drive path; this pins the property that path exists to provide."""
        seen: dict[str, tuple[list[str], str, str, int]] = {}
        for shape, ids in (("single", ["500"]), ("multi", ["500", FILLER])):
            with self.subTest(shape=shape):
                self._reset()
                self._briefed("500")
                self._briefed(FILLER)
                self._arm({"500": ["601", "602"]})
                fork = self._fork(self.cfg)   # both shapes start from the SAME bytes

                rc = self._cli(ids, cfg=fork)

                seen[shape] = (self._adoptions(), self._state("601", fork),
                               self._state("602", fork), rc)

        self.assertEqual(seen["single"][0], [
            "issue_500 split → adopted children issue_601 into wave 1",
            "issue_500 split → adopted children issue_602 into wave 2"])
        self.assertEqual(seen["single"][1:], (state.COMPLETE, state.COMPLETE, 0))
        self.assertEqual(seen["multi"], seen["single"])

    def test_a_refused_adopted_wave_exits_1_at_either_arity(self) -> None:
        """Agreement has to hold when the run does NOT finish, too.

        Adoption is the first thing that can give a one-bundle run a wave wide enough to
        fan out — so it is also the first thing that can be REFUSED one: the two adopted
        children are independent, they land in one wave of two runnable bundles, `lanes=2`
        pools it and the declared `[driver].lane_preflight` fails, which aborts the run
        (`flow.PreflightError`). A verdict on the RUN, not one bundle's fault: `flow_ids`
        lets it out to `cli._flow`, which prints one line and exits 1 — the same at both
        arities (999 is already COMPLETE, so the multi-id run drives exactly what the
        single-id run drives)."""
        seen: dict[str, tuple[int, list[str], str]] = {}
        for shape, ids in (("single", ["500"]), ("multi", ["500", "999"])):
            with self.subTest(shape=shape):
                self._reset(lanes=2, lane_preflight="exit 1")
                self._complete_bystander("999")
                self._briefed("500")
                self._arm({"500": ["601", "602"]},
                          bodies=[_CHILD_ONE, _SIBLING_TWO])

                rc = self._cli(ids)

                seen[shape] = (rc, [ln for ln in self.err.getvalue().splitlines()
                                    if ln.startswith("flow: lane preflight failed")],
                               self._state("601"))

        self.assertEqual(seen["single"][0], 1)          # not 0, and not a traceback
        self.assertEqual(len(seen["single"][1]), 1)     # one line, like any refused batch
        self.assertIn("lanes=2", seen["single"][1][0])
        self.assertEqual(seen["single"][2], state.PLANNED)   # refused ⇒ nothing driven
        self.assertEqual(seen["multi"], seen["single"])

    def test_an_adopted_child_left_unfinished_exits_1_at_either_arity(self) -> None:
        """The other way a run does not finish — and the one that reaches the RESULTS MAP.

        `_report_single`'s rc-0 leniency is about the bundle the operator TYPED: stopping
        for the human who just typed `pdca flow 500` is that run's intended end, not a
        failure (`cli.py:637-639`). Adoption puts bundles in that same map which nobody
        typed, so applying the leniency map-wide makes `pdca flow 500` report total success
        — stdout `COMPLETE`, rc 0 — while an adopted child sits AWAITING_SIGNOFF, and makes
        the very same disk answer 1 as soon as a second id is on the command line. Criterion
        (3) is one exit code for both shapes, so the leniency is scoped to the ids named and
        an unfinished adopted child fails both.

        The scenario is the ordinary end of an interactive run, not an error path: the
        session answers 601 and walks away from 602."""
        seen: dict[str, tuple[int, list[str], str, str]] = {}
        for shape, ids in (("single", ["500"]), ("multi", ["500", FILLER])):
            with self.subTest(shape=shape):
                self._reset()
                self._briefed("500")
                self._briefed(FILLER)
                self._arm({"500": ["601", "602"]}, walk_away="602")
                fork = self._fork(self.cfg)   # both shapes start from the SAME bytes

                rc = self._cli(ids, cfg=fork)

                seen[shape] = (rc, self._adoptions(), self._state("601", fork),
                               self._state("602", fork))

        self.assertEqual(seen["single"][0], 1)                     # NOT a silent success
        self.assertEqual(seen["single"][2], state.COMPLETE)        # the sibling did finish
        self.assertEqual(seen["single"][3], state.AWAITING_SIGNOFF)  # …this one did not
        self.assertEqual(seen["single"][1], [
            "issue_500 split → adopted children issue_601 into wave 1",
            "issue_500 split → adopted children issue_602 into wave 2"])
        self.assertEqual(seen["multi"], seen["single"])   # same bytes, same verdict
        # …and the id the operator DID type keeps #468's stop-for-the-human rc 0
        # (`tests/test_flow_entrypoint_parity.py:388`): a single-id run halted at its own
        # sign-off is still not a failed run.
        self._reset()
        self._briefed("500")
        self._instrument()
        self._silence_signoff()

        rc = self._cli(["500"], max_passes=2)

        self.assertEqual(self._state("500"), state.AWAITING_SIGNOFF)
        self.assertEqual(rc, 0)

    # -- one run-wide pass budget --------------------------------------------------------

    def test_the_pass_budget_is_one_cap_for_the_whole_run(self) -> None:
        """`--max-passes` bounds the RUN, not each wave it grows into — otherwise every
        adopted wave silently multiplies the operator's budget. The parent's wave spends 2
        passes (build → iterate-plan → re-plan → split → accept) and 601's spends 1, so a
        run that set out to drive ONE wave at a budget of 3 is exhausted before 602's wave:
        it is left PLANNED and NAMED, never driven on borrowed budget. One more pass and
        the same run finishes it."""
        self._briefed("500")
        self._arm({"500": ["601", "602"]})

        self._cli(["500"], max_passes=3)

        self.assertEqual(self._state("601"), state.COMPLETE)   # adoption did happen
        self.assertEqual(self._state("602"), state.PLANNED)    # …but on the run's budget
        self.assertEqual(self.waves_driven, [["issue_500"], ["issue_601"]])
        err = self.err.getvalue()
        self.assertIn("the run's pass budget is spent (3 pass(es) over 2 wave(s))", err)
        self.assertIn("issue_602 [PLANNED] — resume with `pdca flow 602`", err)
        self.assertEqual(self.passes, 3)                       # spent, not overspent

        # The cap is what stopped it — not adoption. One more pass, everything lands.
        self._reset()
        self._briefed("500")
        self._arm({"500": ["601", "602"]})

        self._cli(["500"], max_passes=4)

        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(self.passes, 4)
        self.assertNotIn("pass budget is spent", self.err.getvalue())

    def test_an_adopted_wave_only_gets_what_is_left_of_the_run_budget(self) -> None:
        """The cap is not merely re-checked between waves, it is HANDED DOWN. 601 costs two
        passes (it iterates once), and the parent's wave already spent 2 of 3 — so 601 gets
        the ONE pass that is left, stops there and is named. Handing each wave the full
        budget again would finish 601 on a 4th pass, i.e. spend more than the operator
        allowed the run."""
        self._briefed("500")
        self._arm({"500": ["601", "602"]}, iterate_once="601")

        self._cli(["500"], max_passes=3)

        self.assertEqual(self.passes, 3)                        # never a 4th pass
        self.assertEqual(self._state("601"), state.ITERATE_DO)  # left mid-iteration…
        err = self.err.getvalue()
        self.assertIn("pass budget exhausted after 1 pass(es)", err)   # …its share of 3
        self.assertIn("issue_601 [ITERATE_DO] — resume with `pdca flow 601`", err)

    def test_a_wave_that_runs_its_allowance_out_still_charges_the_run_pool(self) -> None:
        """The pool only caps a run if a wave that does NOT finish charges it too.

        `_drive_wave` returns the passes it consumed on EVERY exit, and the budget-exhausted
        one (`flow.py:1112`) is exactly where "one pool, never multiplied" bites: the wave
        that ran its allowance out is the wave that spent the most. Here 810's session is
        walked away from, so wave 0 never goes all-terminal and burns the operator's whole
        4 — while the two independent children 500 split off ARE a runnable wave. The run
        must decline to open it, not spend a 5th pass on it.

        Asserted because it is unobservable from the finishing waves: an exhausted
        `_drive_wave` that reported 0 leaves `spent` untouched, so this same run drives both
        children to COMPLETE on 6 passes — over budget, and silently."""
        self._briefed("500")
        self._briefed("810")
        self._arm({"500": ["601", "602"]}, bodies=[_CHILD_ONE, _SIBLING_TWO],
                  walk_away="810")

        rc = self._cli(["500", "810"], max_passes=4)

        self.assertEqual(self.passes, 4)      # the operator's 4 — never a 5th
        self.assertEqual(self.waves_driven, [["issue_500", "issue_810"]])  # wave 1 unopened
        self.assertEqual(self._adoptions(),   # the children WERE adopted…
                         ["issue_500 split → adopted children issue_601, issue_602 into "
                          "wave 1"])
        self.assertEqual(self._state("601"), state.PLANNED)   # …and then left, not driven
        self.assertEqual(self._state("602"), state.PLANNED)
        err = self.err.getvalue()
        self.assertIn("the run's pass budget is spent (4 pass(es) over 1 wave(s))", err)
        self.assertIn("issue_601 [PLANNED] — resume with `pdca flow 601`", err)
        self.assertEqual(rc, 1)               # un-terminal work, named, never rc 0

    def test_a_wave_that_stalls_charges_the_run_pool_for_what_it_spent(self) -> None:
        """The same accounting on `_drive_wave`'s OTHER un-finished exit — the wave that
        stops making progress (`flow.py:1073`) rather than running its allowance out.

        820's Do leaf fails every pass, so once 500 has split, a whole pass changes nothing
        and the wave gives up after 3 of the run's 4. What is left is ONE pass, and that is
        what the adopted wave gets: 601 iterates once, so it is left ITERATE_DO and named.
        A stalled wave that reported 0 passes would hand the children a fresh allowance of
        4 and finish 601 on a fifth pass the operator never allowed."""
        self._briefed("500")
        self._briefed("820")
        self._arm({"500": ["601", "602"]}, bodies=[_CHILD_ONE, _SIBLING_TWO],
                  iterate_once="601")
        self._build_fails("820")

        self._cli(["500", "820"], max_passes=4)

        self.assertEqual(self.passes, 4)                      # 3 stalled + the 1 left
        self.assertEqual(self.waves_driven,
                         [["issue_500", "issue_820"], ["issue_601", "issue_602"]])
        err = self.err.getvalue()
        self.assertIn("a full pass made no progress", err)    # …the stall really happened
        self.assertIn("pass budget exhausted after 1 pass(es)", err)   # …its share of 4
        self.assertEqual(self._state("601"), state.ITERATE_DO)  # stopped mid-iteration
        self.assertEqual(self._state("602"), state.COMPLETE)    # its sibling did land

    def test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave(self) -> None:
        """The run-wide pool must not become a NEW way for an ordinary batch to be
        truncated. A four-deep `Depends on` chain is four waves of one pass each: at
        `--max-passes 1` every one of them completes, exactly as before adoption existed,
        because the pool is sized off the schedule the run set out to drive (1 × 4) — not
        one allowance shared by however many waves there turn out to be, which would
        strand 810's three dependents at a setting that never truncated anything."""
        ids = ["810", "811", "812", "813"]
        for i, iid in enumerate(ids):
            self._briefed(iid, *([f"- **Depends on:** {ids[i - 1]}"] if i else []))
        self._instrument()

        rc = self._cli(ids, max_passes=1)

        self.assertEqual(self.waves_driven, [[f"issue_{i}"] for i in ids])
        self.assertEqual([self._state(i) for i in ids], [state.COMPLETE] * 4)
        self.assertEqual(rc, 0)
        self.assertEqual(self.passes, 4)                       # one per wave, as always
        self.assertNotIn("budget is spent", self.err.getvalue())

    def test_an_adopted_child_that_splits_again_is_re_adopted_and_bounded(self) -> None:
        """Recursion, on the same pool. 601 is adopted, then splits in ITS wave; its own
        children are adopted into a later wave of the SAME run and driven — and they draw
        from the same budget, so the recursion is bounded rather than reset. Both halves
        are asserted, because either alone is satisfiable by the wrong implementation: a
        budget that reset would still finish the grandchildren, and a run that never
        re-examined an adopted child would still respect the cap."""
        self._briefed("500")
        self._arm({"500": ["601", "602"], "601": ["701", "702"]})

        self._cli(["500"], max_passes=20)

        self.assertEqual(self._state("701"), state.COMPLETE)
        self.assertEqual(self._state("702"), state.COMPLETE)
        self.assertIn("issue_601 split → adopted children issue_701 into wave 2",
                      self.err.getvalue())
        self.assertEqual(self.passes, 6)   # 2 (500) + 2 (601) + 1 + 1 — one pool, no reset

        # …and the pool BINDS across the recursion: the same run, allowed 5 passes, stops
        # inside the grandchildren rather than borrowing a fresh budget for the new wave.
        self._reset()
        self._briefed("500")
        self._arm({"500": ["601", "602"], "601": ["701", "702"]})

        self._cli(["500"], max_passes=5)

        self.assertEqual(self.passes, 5)
        self.assertEqual(self._state("702"), state.PLANNED)
        self.assertIn("the run's pass budget is spent (5 pass(es) over 3 wave(s))",
                      self.err.getvalue())

    # -- scope: the lineage edge, never a disk sweep -------------------------------------

    def test_adoption_follows_the_lineage_edge_not_a_disk_sweep(self) -> None:
        """An explicit-id flow adopts the children of the ids it was GIVEN — never an
        unrelated in-flight bundle. The distinction between `flow_ids` and the CSV resume
        sweep is deliberate and must survive adoption."""
        self._briefed("500")
        self._briefed("STRANGER")
        self._arm({"500": ["601", "602"]})

        self._cli(["500"])

        self.assertEqual(self._state("601"), state.COMPLETE)  # the lineage edge WAS followed
        self.assertEqual(self._state("STRANGER"), state.PLANNED)   # the disk was NOT swept
        self.assertNotIn("STRANGER", self.out.getvalue())

    def test_a_named_id_list_keeps_its_strict_scheduling_contract(self) -> None:
        """Tolerance is for what adoption ADDS, never for what the operator asked for.
        `compute_waves` refuses an id list with a dependency cycle (`waves.py:243-246`
        calls raising "right for an explicit `flow <ids>`"), and that refusal must not
        depend on unrelated disk state — adding a stranded split parent to the same
        command line must not turn the whole run tolerant."""
        self._briefed("800", "- **Depends on:** 801")
        self._briefed("801", "- **Depends on:** 800")
        self._strand_a_split(self.cfg)

        with self.assertRaises(ValueError) as bare:
            self._cli(["800", "801"])
        with self.assertRaises(ValueError) as with_seed:
            self._cli(["500", "800", "801"])

        self.assertIn("dependency cycle", str(bare.exception))
        self.assertIn("dependency cycle", str(with_seed.exception))
        self.assertEqual(self._state("601"), state.PLANNED)  # refused ⇒ nothing driven

    def test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost(self) -> None:
        """What the splice's tolerance does to the operator's OWN un-driven ids — asserted,
        because it is the one place the id list stops being levelled strictly.

        The splice re-levels `remaining + children`, and `remaining` is the tail of the id
        list the operator typed. So a named id whose prerequisite this run left un-terminal
        is HELD and reported in the resume shape, where a run that never spliced would have
        reached it and let `_runnable` skip it ("prerequisite(s) not ready"). Same end state
        (PLANNED, and the run fails), different line. What must NOT change is the answer the
        operator gets: an id they named stays in the results map even when it is held —
        unlike an adopted child, which is excluded because it is work the run did not do."""
        self._briefed("500")
        self._briefed("810")
        self._briefed("811", "- **Depends on:** 810")
        self._arm({"500": ["601", "602"]}, walk_away="810")
        self._capture_results()

        rc = self._cli(["500", "810", "811"], max_passes=3)

        self.assertEqual(self._state("601"), state.COMPLETE)   # the run carried on…
        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(self._state("810"), state.AWAITING_SIGNOFF)   # …the prereq halted
        self.assertEqual(self._state("811"), state.PLANNED)    # …its dependent was held
        self.assertIn("issue_811 held this run — unresolved dependency (810); left "
                      "in-flight", self.err.getvalue())
        self.assertEqual(self.results.get("811"), state.PLANNED)   # still answered for
        self.assertEqual(rc, 1)

    # -- guards --------------------------------------------------------------------------

    def test_a_split_marked_but_non_terminal_parent_is_not_adopted_from(self) -> None:
        """The marker is not the predicate — TERMINAL + the marker is. `split.accept`
        writes `close-disposition = split`, but the human still confirms the decomposition
        at sign-off, so a parent still AWAITING_SIGNOFF is a split nobody has accepted yet
        and driving its children would spend whole cycles on work the next sign-off may
        reopen.

        Both legs run the SAME on-disk split; the only difference is whether the sign-off
        session answered. (AWAITING_SIGNOFF rather than an `iterate-do` because an iterate
        ARCHIVES the close marker — a bundle that iterated is not "split-marked and
        non-terminal" at all, so it could not exercise the guard.)"""
        # Leg A — the human walked away: halted at AWAITING_SIGNOFF, marker still there.
        self._split_now(self.cfg.bundle("500"), ["601", "602"],
                        [_CHILD_ONE, _CHILD_TWO])
        self._silence_signoff()
        self._instrument()

        self._cli(["500"], max_passes=1)

        self.assertEqual(self._state("500"), state.AWAITING_SIGNOFF)   # NOT terminal
        self.assertEqual((self.cfg.bundle("500") / state.CLOSE_MARKER).read_text(
            encoding="utf-8").strip(), "split")                        # …but split-marked
        self.assertEqual(self._state("601"), state.PLANNED)            # not adopted
        self.assertEqual(self._state("602"), state.PLANNED)
        self.assertEqual(self._adoptions(), [])

        # Leg B — same bytes, the session accepts: NOW the parent is terminal on the split
        # and the very same children are adopted. The guard is the terminality, nothing else.
        self._reset()
        self._split_now(self.cfg.bundle("500"), ["601", "602"],
                        [_CHILD_ONE, _CHILD_TWO])
        self._instrument()

        self._cli(["500"], max_passes=4)

        self.assertEqual(self._state("500"), state.COMPLETE)
        self.assertEqual(self._state("601"), state.COMPLETE)
        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(self._adoptions(), [
            "issue_500 split → adopted children issue_601 into wave 1",
            "issue_500 split → adopted children issue_602 into wave 2"])

    def test_a_lineage_child_id_that_escapes_the_bundle_root_is_skipped(self) -> None:
        """`split-lineage.json` is a file an operator can hand-edit, and `cfg.bundle` would
        happily build a path outside the bundle root from a traversal id — the hazard
        `split.validate` guards at WRITE time (`split.py:296-311`) and this reader must
        guard at READ time. The escaping id is reported and skipped; the legitimate sibling
        in the same record is still adopted, so one bad entry costs one child, not the
        run."""
        # Independent children here: the escaping entry stands in for 601, so a 602 that
        # declared `Depends on: 601` would be held for the missing prerequisite and prove
        # nothing about the traversal guard.
        self._strand_a_split(self.cfg, bodies=[_CHILD_ONE, _SIBLING_TWO])
        record_path = self.cfg.bundle("500") / split.LINEAGE
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["children"] = ["../../etc", "602"]
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        self._instrument()

        self._cli(["500"])

        err = self.err.getvalue()
        self.assertIn("ignoring child id '../../etc'", err)
        self.assertIn("resolves outside", err)
        self.assertNotIn("Traceback", err)
        self.assertEqual(self._state("602"), state.COMPLETE)   # the sibling still ran
        self.assertEqual(self.waves_driven, [["issue_602"]])
        self.assertFalse((self.cfg.bundle_root / "issue_../../etc").exists())

    def test_a_child_with_an_unresolvable_dependency_is_held_not_fatal(self) -> None:
        """Adopted children go through the resume path's tolerance: one whose declared
        prerequisite cannot be resolved is held loudly, EXCLUDED from the results map (it
        is work the run did not do, and a map that claimed it would be read as a
        disposition), and left in-flight while the run carries on with its sibling. A split
        must never abort the flow that caused it."""
        self._briefed("500")

        def break_602() -> None:
            # A child brief that names a prerequisite outside the proposal (hand-edited
            # after the split, or re-planned since) — unresolvable at adoption time.
            bp = self.cfg.bundle("602") / "brief.md"
            bp.write_text(bp.read_text(encoding="utf-8") + "- **Depends on:** GHOST\n",
                          encoding="utf-8")

        self._arm({"500": ["601", "602"]}, bodies=[_CHILD_ONE, _SIBLING_TWO],
                  after_split=break_602)
        self._capture_results()

        rc = self._cli(["500"])

        self.assertEqual(self._state("601"), state.COMPLETE)  # the run continued
        self.assertEqual(self._state("602"), state.PLANNED)   # held, left in-flight
        self.assertEqual(rc, 0)                               # …and never an abort
        self.assertEqual(self.results.get("601"), state.COMPLETE)   # adopted and driven
        self.assertNotIn("602", self.results)                 # …the held one is NOT work
        err = self.err.getvalue()
        self.assertIn("issue_602 held this run", err)
        self.assertIn("GHOST", err)
        # …and never announced as adopted into a wave it is not in.
        self.assertNotIn("issue_602 into wave", err)

    def test_a_child_listed_twice_in_the_record_is_adopted_once(self) -> None:
        """`split-lineage.json` is a file on disk an operator can hand-edit, so the reader
        must not trust it to be a set. A child listed twice would ride into the reschedule
        twice, take two slots in the drive set the results map and the closing sweep are
        built from, and be announced twice — a run that reports more work than exists."""
        self._strand_a_split(self.cfg)                    # 500 split → 601, 602
        record_path = self.cfg.bundle("500") / split.LINEAGE
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["children"] = ["601", "601", "602"]        # hand-edited: 601 twice
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        self._instrument()

        self._cli(["500"])

        self.assertEqual(self.waves_driven, [["issue_601"], ["issue_602"]])  # once each
        self.assertEqual(self._state("601"), state.COMPLETE)
        self.assertEqual(self._state("602"), state.COMPLETE)
        err = self.err.getvalue()
        self.assertEqual(
            err.count("issue_500 split → adopted children issue_601 into wave 0"), 1)
        self.assertNotIn("issue_601, issue_601", err)

    def test_a_lineage_cycle_is_examined_once_and_the_run_returns(self) -> None:
        """The same hand-edited record, closed into a CYCLE: 500 split → 601, 602 and 601's
        `children` naming 500 back.

        The chain walk exists so a stale generation is walked THROUGH (a terminal-on-split
        child is undrivable but may hold stranded grandchildren), and that is exactly what
        makes an ancestor edge re-enter the queue: 500 is terminal on a split, so it comes
        back as another parent to examine, whose children include 601, whose children
        include 500… Only "a parent is examined once" ends it. Without that the run never
        returns at all — not a wrong answer, no answer — so the deadline is part of the
        assertion, and the run must still adopt everything the cycle did NOT poison."""
        self._strand_a_split(self.cfg)                      # 500 split → 601, 602
        self._split_now(self.cfg.bundle("601"), ["701"], [_CHILD_ONE])
        self._drive_to_complete(self.cfg, self.cfg.bundle("601"))
        record_path = self.cfg.bundle("601") / split.LINEAGE
        record = json.loads(record_path.read_text(encoding="utf-8"))
        record["children"] = ["500", "701"]                 # hand-edited: back to the root
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        self._instrument()
        examined = self._watch_examined()

        with _deadline(30):
            rc = self._cli(["500"])

        self.assertEqual(rc, 0)
        self.assertEqual(self._state("602"), state.COMPLETE)   # the drivable child…
        self.assertEqual(self._state("701"), state.COMPLETE)   # …and the grandchild
        # …and the bound itself, stated directly rather than inferred from termination:
        # 500 is NOT revisited through 601's back-edge. (602 and 701 appear because every
        # bundle a wave drives is examined for a split of its own — once each, too.)
        self.assertEqual(len(examined), len(set(examined)))
        self.assertEqual(sorted(examined),
                         ["issue_500", "issue_601", "issue_602", "issue_701"])
        err = self.err.getvalue()
        # The ancestor edge is not adopted (500 is terminal, and already examined) and is
        # never announced — one visit, one report, no second pass over the same parent.
        self.assertEqual(err.count("issue_601 split → adopted children issue_701"), 1)
        self.assertNotIn("adopted children issue_500", err)
        self.assertNotIn("Traceback", err)

    def test_a_child_already_named_in_the_run_is_not_adopted_twice(self) -> None:
        """`pdca flow 500 601` names a child the parent's record also names. It is already
        in the drive set, so adopting it again would schedule, drive, count and announce
        one bundle twice. Skipped — and said out loud, because a child the operator ALSO
        listed is the one skip they are most likely to be looking for in the log."""
        self._strand_a_split(self.cfg)                    # 500 split → 601, 602
        self._instrument()

        rc = self._cli(["500", "601"])

        self.assertEqual(self.waves_driven, [["issue_601"], ["issue_602"]])
        self.assertEqual(self._state("601"), state.COMPLETE)
        self.assertEqual(self._state("602"), state.COMPLETE)  # the sibling still adopted
        self.assertEqual(rc, 0)
        err = self.err.getvalue()
        self.assertIn("issue_601 — child of issue_500 not adopted again: already in this "
                      "run's drive set", err)
        self.assertEqual(self._adoptions(),
                         ["issue_500 split → adopted children issue_602 into wave 1"])

    def test_a_child_adopted_earlier_is_not_re_adopted_by_a_later_parent(self) -> None:
        """The drive set has to REMEMBER what it adopted, from one adoption call to the next.

        One run, two splits: 500's children are adopted by the seed pre-pass, then 700
        splits inside wave 0 with a record that also names 602 (hand-edited, or re-planned
        onto a slice its sibling already owns). The in-call `taken` set does not survive the
        call — only the run's drive set does — so a child adopted in an EARLIER call is
        skipped by the same "already in this run's drive set" rule that skips one the
        operator named. Without that, 602 is adopted twice: two slots in the drive set, two
        announcements, one bundle reported as work in two places."""
        self._strand_a_split(self.cfg)                    # 500 already split → 601, 602
        self._briefed("700")

        def claim_602() -> None:
            record_path = self.cfg.bundle("700") / split.LINEAGE
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["children"] = ["602", "801"]
            record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

        self._arm({"700": ["801"]}, bodies=[_CHILD_ONE], after_split=claim_602)

        rc = self._cli(["500", "700"])

        self.assertIn("issue_602 — child of issue_700 not adopted again: already in this "
                      "run's drive set", self.err.getvalue())
        self.assertEqual(self._adoptions(), [
            "issue_500 split → adopted children issue_601 into wave 0",
            "issue_500 split → adopted children issue_602 into wave 1",
            "issue_700 split → adopted children issue_801 into wave 1"])
        self.assertEqual(self.waves_driven,                # …and 602 is driven ONCE
                         [["issue_601", "issue_700"], ["issue_602", "issue_801"]])
        self.assertEqual([self._state(i) for i in ("601", "602", "801")],
                         [state.COMPLETE] * 3)
        self.assertEqual(rc, 0)

    def test_a_split_parent_without_a_children_record_is_reported_not_guessed(self) -> None:
        """No readable `split-lineage.json` ⇒ report it and degrade to today's behaviour
        (the operator's `pdca flow <child-ids>`). Never a crash, never a prose parse of the
        `build-notes.md` breadcrumb `split.accept` leaves for the human."""
        self._briefed("500")
        self._arm({"500": ["601", "602"]},
                  after_split=lambda: (self.cfg.bundle("500") / split.LINEAGE).unlink())

        rc = self._cli(["500"])

        self.assertEqual(self._state("500"), state.COMPLETE)  # the run finished cleanly
        self.assertEqual(rc, 0)
        self.assertEqual(self._state("601"), state.PLANNED)   # not driven, not lost
        self.assertIn("no readable children record", self.err.getvalue())

    def test_an_unreadable_close_marker_never_kills_the_run(self) -> None:
        """The split probe runs over ids the operator merely NAMED, outside any `_isolate`.
        A `close-disposition` whose bytes are not UTF-8 raises `UnicodeDecodeError` — a
        `ValueError`, not the `OSError` a narrow handler expects — so a single corrupt
        marker would take down the whole explicit-id run and every drivable id in it. It is
        a hint: unreadable means "not a split", never a verdict on the run."""
        self._strand_a_split(self.cfg)
        (self.cfg.bundle("500") / state.CLOSE_MARKER).write_bytes(b"split\xff\n")
        self._briefed("777")
        self._instrument()

        rc = self._cli(["500", "777"])

        self.assertEqual(self._state("777"), state.COMPLETE)  # the named id still ran
        self.assertEqual(self._state("601"), state.PLANNED)   # not guessed at either
        self.assertEqual(rc, 0)   # a run, not a crash: both named ids reached COMPLETE
        self.assertNotIn("Traceback", self.err.getvalue())
        self.assertEqual(self._adoptions(), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
