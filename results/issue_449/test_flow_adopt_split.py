"""A split must not strand its own children on the run that caused it (#449).

Before this, the drive set froze at the start of the run: `flow_ids` built its bundle list
once and `_drive_and_act` computed `wave_list` once, so when a bundle reached
`close-disposition = split` mid-run the parent went terminal, the children materialised by
`pdca split --accept` sat PLANNED and undriven, and the operator restarted the whole thing
by hand with `pdca flow <child-ids>`.

Everything here is the ordinary offline driver suite: all six leaves stubbed (the fixture
mirrors `test_flow_slice.py`), gates empty, no tracker / network / `gh` / container. The
split itself is not simulated — the tests call the PRODUCTION `split.accept`, so the
parent's close marker, its `split-lineage.json` children record and the child bundles are
byte-for-byte what `pdca split --accept` leaves on disk.

Adoption is exercised only through the real entry points (`flow.flow_ids`, `flow.flow`) —
the defect was that the ENTRY POINTS freeze their drive set, so calling an internal helper
would prove nothing. Per the brief: import MODULES, never new symbols, so the red leg
(production hunks reverted) fails on a real assertion rather than an ImportError the
verifier would classify PDCA-UNVERIFIABLE.

    cd template && PYTHONPATH=src python3 -m unittest tests.test_flow_adopt_split
"""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

from pdca_harness import cli, flow, leaves, split, state
from pdca_harness.config import Config, LeafConfig


def _stub_config(root: Path, *, lanes: int = 1, lane_preflight: str = "") -> Config:
    """All six leaves stubbed, gates empty (all-PASS stub rows) — mirrors
    `test_flow_slice._stub_config`, including the hermetic toy checkout inside the tmp root
    (the sibling convention would resolve to a SHARED /tmp/example-repo).

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


class AdoptSplitChildren(unittest.TestCase):
    def setUp(self) -> None:
        self.cfg = self._instance()
        self.err = io.StringIO()
        self.waves_driven: list[list[str]] = []
        self.passes = 0                  # one `_build_all` call == one pass of one wave
        # BOTH sign-off leaves: the batch entry points run `run_signoff_batch`
        # (`flow.py:790`) and the single-id `flow` runs the per-bundle `run_signoff`
        # (`flow.py:260`). Stubbing only the batch one leaves the single-id Entry-B path —
        # iterate-plan at sign-off → re-plan → split, the brief's motivating case — unable
        # to reach its split at all.
        self._orig = (leaves.do_plan, leaves.run_signoff_batch, leaves.run_signoff,
                      flow._drive_wave, flow._build_all)

    def tearDown(self) -> None:
        (leaves.do_plan, leaves.run_signoff_batch, leaves.run_signoff, flow._drive_wave,
         flow._build_all) = self._orig

    def _instance(self, **cfg_kw) -> Config:
        """A fresh, hermetic instance root, removed at teardown."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return _stub_config(tmp, **cfg_kw)

    def _reset(self, **cfg_kw) -> None:
        """A second run of the same test, on a clean instance and unpatched leaves."""
        (leaves.do_plan, leaves.run_signoff_batch, leaves.run_signoff, flow._drive_wave,
         flow._build_all) = self._orig
        self.cfg = self._instance(**cfg_kw)
        self.err = io.StringIO()
        self.waves_driven = []
        self.passes = 0

    # -- the split, exactly as `pdca split --accept` leaves it ------------------------

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

    def _arm(self, *, split_at_plan: str, ids: list[str],
             bodies: list[str] | None = None, replan_first: bool = True,
             iterate_once: str = "", after_split=None) -> None:
        """Stub the leaves so the run splits `split_at_plan` mid-flight.

        ``replan_first`` is the documented Entry-B path: the first sign-off session on the
        parent records `iterate-plan`, the driver re-opens it to UNPLANNED, and the next
        pass's serial Plan pre-pass concludes it is too large and splits it. Without it the
        very first Plan beat splits (the single-id `pdca flow <id>` shape).
        ``iterate_once`` makes that bundle cost a second pass (an ordinary `iterate-do` on
        its first sign-off) — how a wave is made to want more budget than the run has.

        The scripted decisions are written ONCE and served to both sign-off leaves, so the
        two entry points are driven by the same human answers: the batch path calls
        `leaves.run_signoff_batch`, the single-id path `leaves.run_signoff`."""
        bodies = bodies or [_CHILD_ONE, _CHILD_TWO]
        real_plan, real_signoff_batch, real_signoff, real_wave, real_build_all = self._orig
        done: set[str] = set()

        def splitting_plan(d: Path, cfg: Config, csv: str | None = None) -> None:
            if d.name == f"issue_{split_at_plan}" and "split" not in done:
                done.add("split")
                self._split_now(d, ids, bodies)
                if after_split is not None:
                    after_split()
                return
            real_plan(d, cfg, csv)

        def decide(d: Path) -> bool:
            """Write this bundle's scripted decision, if it has one this pass. True ⇒ the
            session answered here; False ⇒ let the real stub clear §6 and accept."""
            if (replan_first and d.name == f"issue_{split_at_plan}"
                    and "replan" not in done):
                done.add("replan")
                (d / leaves.SIGNOFF_DECISION).write_text(
                    "iterate-plan\nthis slice is too large — decompose it\n",
                    encoding="utf-8")
                return True
            if d.name == f"issue_{iterate_once}" and "iterate" not in done:
                done.add("iterate")
                (d / leaves.SIGNOFF_DECISION).write_text(
                    "iterate-do\none more round\n", encoding="utf-8")
                return True
            return False

        def signoff_batch(cfg: Config, bundles: list[Path]) -> None:
            real_signoff_batch(cfg, [d for d in bundles if not decide(d)])

        def signoff_one(d: Path, cfg: Config) -> None:
            if not decide(d):
                real_signoff(d, cfg)  # stub: clears §6 + accepts

        leaves.do_plan = splitting_plan
        leaves.run_signoff_batch = signoff_batch
        leaves.run_signoff = signoff_one
        flow._drive_wave = self._spy_wave(real_wave)
        flow._build_all = self._counting_build_all(real_build_all)

    def _count_only(self) -> None:
        """Instrument the pass counter and the wave spy WITHOUT arming a split — for the
        runs that must be shown to behave exactly as they do today."""
        *_real_leaves, real_wave, real_build_all = self._orig
        flow._drive_wave = self._spy_wave(real_wave)
        flow._build_all = self._counting_build_all(real_build_all)

    def _counting_build_all(self, real_build_all):
        def counting(cfg: Config, wave: list[Path]) -> None:
            self.passes += 1
            real_build_all(cfg, wave)
        return counting

    def _spy_wave(self, real_wave):
        """Record the bundles of every wave the run drives — and hand the production
        return value straight back (post-fix it is the wave's pass count, which the run
        budget is kept in)."""
        def spy(cfg: Config, wave: list[Path], **kw):
            self.waves_driven.append([d.name for d in wave])
            return real_wave(cfg, wave, **kw)
        return spy

    def _drive_to_complete(self, cfg: Config, d: Path) -> None:
        """Carry one bundle to COMPLETE with production code and no adoption of its own
        (`_drive_wave` is the per-wave driver; it has never looked for children)."""
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            flow._drive_wave(cfg, [d], by="t", today="2026-08-08", max_passes=2)

    def _strand_a_split(self, cfg: Config, parent: str = "500",
                        ids: tuple[str, str] = ("601", "602")) -> None:
        """Leave `cfg`'s instance exactly as an EARLIER run that split `parent` did: the
        parent terminal on `close-disposition = split` with a children record, its children
        sitting PLANNED and undriven. Built by production code — `split.accept` for the
        split, `flow._drive_wave` to carry the parent through Check + sign-off."""
        self._split_now(cfg.bundle(parent), list(ids), [_CHILD_ONE, _CHILD_TWO], cfg=cfg)
        self._drive_to_complete(cfg, cfg.bundle(parent))
        # The fault the run has to recover is genuinely on disk before it starts.
        self.assertEqual(state.state(cfg.bundle(parent)), state.COMPLETE)
        self.assertEqual((cfg.bundle(parent) / state.CLOSE_MARKER).read_text(
            encoding="utf-8").strip(), "split")
        for cid in ids:
            self.assertEqual(state.state(cfg.bundle(cid)), state.PLANNED)

    def _complete_bystander(self, cfg: Config, iid: str) -> None:
        """A briefed bundle carried to COMPLETE by production code. Naming it alongside the
        parent changes the command's ARITY without changing what the run drives (`flow_ids`
        skips a terminal id, `flow.py:1462`) — which is how `pdca flow 500` and
        `pdca flow 500 999` are compared on identical disk."""
        d = cfg.bundle(iid)
        d.mkdir(parents=True, exist_ok=True)
        (d / "brief.md").write_text(_brief(f"bystander-{iid}"), encoding="utf-8")
        self._drive_to_complete(cfg, d)
        self.assertEqual(state.state(d), state.COMPLETE)

    def _flow_args(self, ids: list[str]) -> SimpleNamespace:
        """The `pdca flow <ids…>` argv as `cli._flow` receives it — the CLI's own arity
        switch (`cli.py:602`) is what routes one id to `flow.flow` and several to
        `flow.flow_ids`, so it has to be the thing under test, not a hand-picked call."""
        return SimpleNamespace(issue_ids=ids, from_csv=None, from_briefs=None,
                               no_publish=True, no_act=True, by="", lanes=None)

    def _arm_a_refused_adoption(self) -> None:
        """Disk + config for a run whose ADOPTED wave is refused: 500 splits mid-run into
        two INDEPENDENT children, so they land in one wave of two runnable bundles;
        `lanes=2` fans that wave out, and the declared preflight command fails."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)
        self._arm(split_at_plan="500", ids=["601", "602"],
                  bodies=[_CHILD_ONE, _SIBLING_TWO])

    def _run(self, fn, *args, **kwargs):
        with redirect_stderr(self.err), redirect_stdout(io.StringIO()):
            return fn(*args, **kwargs)

    def _state(self, issue_id: str, cfg: Config | None = None) -> str:
        return state.state((cfg or self.cfg).bundle(issue_id))

    # -- the criterion ----------------------------------------------------------------

    def test_flow_ids_drives_the_children_of_a_mid_run_split(self) -> None:
        """`pdca flow 500` (id-seeded): the re-plan splits 500, and THIS run drives 601
        and 602 to a terminal state — in waves AFTER the parent's, honouring the
        `Depends on` the split itself wrote into 602's brief, and announcing each child's
        REAL wave from the recomputed schedule (601 in wave 1, 602 in wave 2)."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)   # pre-briefed → drivable by id
        self._arm(split_at_plan="500", ids=["601", "602"])

        results = self._run(flow.flow_ids, self.cfg, ["500"], today="2026-08-08")

        self.assertEqual(self._state("500"), state.COMPLETE)
        self.assertEqual(self._state("601"), state.COMPLETE)  # adopted, not stranded
        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(results.get("601"), state.COMPLETE)  # and reported by the run
        self.assertEqual(results.get("602"), state.COMPLETE)
        # AFTER the parent's wave, and 602 after 601 — its own declared ordering.
        self.assertEqual(self.waves_driven,
                         [["issue_500"], ["issue_601"], ["issue_602"]])
        err = self.err.getvalue()
        self.assertIn("issue_500 split → adopted children issue_601 into wave 1", err)
        self.assertIn("issue_500 split → adopted children issue_602 into wave 2", err)

    def test_single_id_flow_drives_the_children_of_its_own_split(self) -> None:
        """`flow.flow` loops on ONE bundle and exits when it derives terminal, so a split
        during its run used to end with the children PLANNED. Same call, same budget: they
        must reach terminal too.

        Driven along ENTRY B, the brief's motivating case and the one the single-id path
        owns: the human's sign-off session records `iterate-plan`, the driver re-opens the
        bundle, and the re-plan concludes it is too large and splits it. That path runs
        through `leaves.run_signoff` — the per-bundle leaf only `flow.flow` calls
        (`flow.py:260`) — so a fixture that stubs only the batch leaf never reaches it."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)   # briefed, then re-planned below
        self._arm(split_at_plan="500", ids=["601", "602"])

        final = self._run(flow.flow, self.cfg, "500", today="2026-08-08")

        self.assertEqual(final, state.COMPLETE)               # the parent's own contract
        self.assertEqual(self._state("601"), state.COMPLETE)
        self.assertEqual(self._state("602"), state.COMPLETE)
        self.assertEqual(self.waves_driven, [["issue_601"], ["issue_602"]])
        err = self.err.getvalue()
        # Entry B really was walked, and through the single-id leaf: the parent is in no
        # driven wave above, so the `iterate-plan` that archived it and sent it back to
        # Plan can only have come from `flow.flow`'s own `leaves.run_signoff` session.
        self.assertIn("issue_500: iterate-to-Plan", err)
        self.assertTrue((self.cfg.bundle("500") / "iteration-v1").is_dir())
        # Wave 1 and 2 of THE RUN: its loop drove the parent as wave 0 before the tail
        # adopted — the same numbers `flow_ids` prints for the same children.
        self.assertIn("issue_500 split → adopted children issue_601 into wave 1", err)
        self.assertIn("issue_500 split → adopted children issue_602 into wave 2", err)

    def test_the_two_entry_points_announce_the_same_waves(self) -> None:
        """One event, one description. The CLI routes a single id to `flow.flow` and a list
        to `flow_ids`, and both are documented as doing the same thing to the same disk
        (`docs/07-crosscutting.md` §Size & split → The split) — so they must also NUMBER
        the waves the same. `flow.flow` drives its bundle in its own loop rather than as a `wave_list`
        entry, so an adoption tail reporting its LOCAL index announced waves 0/1 for the
        children `flow_ids` announced as 1/2: the same log line, two meanings, on identical
        disk state."""
        said: dict[str, list[str]] = {}
        for name, drive in (
            ("flow_ids", lambda cfg: flow.flow_ids(cfg, ["500"], do_publish=False,
                                                   today="2026-08-08")),
            ("flow", lambda cfg: flow.flow(cfg, "500", do_publish=False,
                                           today="2026-08-08")),
        ):
            with self.subTest(entry=name):
                self._reset()
                leaves.do_plan(self.cfg.bundle("500"), self.cfg)
                self._arm(split_at_plan="500", ids=["601", "602"])

                self._run(drive, self.cfg)

                said[name] = [ln.split("flow: ")[-1]
                              for ln in self.err.getvalue().splitlines()
                              if "split → adopted children" in ln]
                self.assertEqual(self._state("602"), state.COMPLETE)  # both really adopted

        self.assertEqual(said["flow_ids"], [
            "issue_500 split → adopted children issue_601 into wave 1",
            "issue_500 split → adopted children issue_602 into wave 2"])
        self.assertEqual(said["flow"], said["flow_ids"])

    def test_the_single_id_path_reports_the_runs_own_budget_totals(self) -> None:
        """The adoption tail is one run CONTINUING, so what it prints when the pool runs out
        has to be the run's arithmetic. `flow.flow` spends its whole allowance on the parent
        here (Entry B costs two passes: build → iterate-plan, then re-plan → split →
        accept), so the children are adopted with nothing left to drive them — and the
        operator is told the run was allowed 2 passes and drove 1 wave. The tail's own local
        totals, "0 pass(es) over 0 wave(s)", describe no run anyone can act on: a budget of
        zero is not a setting anyone can raise."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)
        self._arm(split_at_plan="500", ids=["601", "602"])

        final = self._run(flow.flow, self.cfg, "500", do_publish=False,
                          today="2026-08-08", max_iters=2)

        self.assertEqual(final, state.COMPLETE)               # the parent's own contract
        self.assertEqual(self.waves_driven, [])               # nothing left to drive them
        err = self.err.getvalue()
        self.assertIn("the run's pass budget is spent (2 pass(es) over 1 wave(s))", err)
        self.assertNotIn("0 pass(es) over 0 wave(s)", err)
        # Adopted and named all the same — un-driven work is never silent (#260).
        self.assertIn("issue_500 split → adopted children issue_601 into wave 1", err)
        self.assertIn("issue_601 [PLANNED] — resume with `pdca flow 601`", err)
        self.assertIn("issue_602 [PLANNED] — resume with `pdca flow 602`", err)

    def test_both_entry_points_recover_a_stranded_split_on_the_same_budget(self) -> None:
        """A split accepted in an EARLIER run leaves its children stranded PLANNED; naming
        the parent again is the operator's recovery, and it must mean the same thing at
        both entry points — the CLI routes one id to `flow.flow` and several to `flow_ids`.

        Driven at a budget that BINDS (the children need two passes; the run is allowed
        one), because agreeing only where nothing is scarce is not agreement: `flow`'s loop
        used to charge an iteration for merely OBSERVING the finished parent, so it handed
        adoption one pass less than `flow_ids` did on byte-identical disk state."""
        outcomes: dict[tuple[str, int], tuple[str, str]] = {}
        for budget in (1, 2):
            for name, drive in (
                ("flow_ids", lambda cfg, n=budget: flow.flow_ids(
                    cfg, ["500"], do_publish=False, today="2026-08-08", max_passes=n)),
                ("flow", lambda cfg, n=budget: flow.flow(
                    cfg, "500", do_publish=False, today="2026-08-08", max_iters=n)),
            ):
                with self.subTest(entry=name, max_passes=budget):
                    cfg = self._instance()
                    self._strand_a_split(cfg)
                    self.err = io.StringIO()

                    self._run(drive, cfg)

                    outcomes[(name, budget)] = (self._state("601", cfg),
                                                self._state("602", cfg))
                    self.assertIn("issue_500 split → adopted children issue_601",
                                  self.err.getvalue())

        # One pass buys the first child's wave and no more — the second is held, named,
        # and left for a resume; two passes buy both. Identical at both entry points.
        self.assertEqual(outcomes[("flow_ids", 1)], (state.COMPLETE, state.PLANNED))
        self.assertEqual(outcomes[("flow", 1)], outcomes[("flow_ids", 1)])
        self.assertEqual(outcomes[("flow_ids", 2)], (state.COMPLETE, state.COMPLETE))
        self.assertEqual(outcomes[("flow", 2)], outcomes[("flow_ids", 2)])

    def test_a_refused_run_aborts_both_entry_points_identically(self) -> None:
        """Agreement has to hold when the run does NOT finish, too.

        Adoption is the first thing that gives a single-id run a wave wide enough to fan
        out — so it is also the first thing that can be REFUSED one: the two adopted
        children are independent, they land in one wave of two runnable bundles,
        `lanes=2` pools it and the declared `[driver].lane_preflight` fails, which aborts
        the run (`flow.PreflightError`, `flow.py:1231`). That is a verdict on the run, not
        one bundle's fault: `flow_ids` lets it out to the CLI, which prints it and exits 1.
        The single-id tail ran inside `_isolate` — which contained EVERY `Exception` — so
        byte-identical disk finished quietly instead, children still PLANNED, rc 0.
        """
        outcome: dict[str, tuple] = {}
        for name, drive in (
            ("flow_ids", lambda cfg: flow.flow_ids(cfg, ["500"], do_publish=False,
                                                   today="2026-08-08")),
            ("flow", lambda cfg: flow.flow(cfg, "500", do_publish=False,
                                           today="2026-08-08")),
        ):
            with self.subTest(entry=name):
                self._reset(lanes=2, lane_preflight="exit 1")
                self._arm_a_refused_adoption()

                with self.assertRaises(flow.PreflightError) as caught:
                    self._run(drive, self.cfg)

                outcome[name] = (str(caught.exception), self._state("500"),
                                 self._state("601"), self._state("602"))

        self.assertIn("lane preflight failed for a lanes=2 batch", outcome["flow_ids"][0])
        # Same disk, same event, same report — and the same standing left behind: the
        # parent's own cycle finished, the children were adopted but never driven.
        self.assertEqual(outcome["flow"], outcome["flow_ids"])
        self.assertEqual(outcome["flow"][1:],
                         (state.COMPLETE, state.PLANNED, state.PLANNED))

    def test_the_cli_exits_1_on_a_refused_run_however_many_ids_it_was_given(self) -> None:
        """What the operator (and their automation) actually sees: the exit code.

        `pdca flow 500` and `pdca flow 500 999` here are the same run on the same disk —
        999 is already COMPLETE, so the batch route skips it and drives exactly the bundle
        the single-id route drives, adopting exactly the same children. Only the ARITY
        differs, and arity is what picks the entry point (`cli.py:602`). The batch route
        has reported this refusal as one line + rc 1 since #213 (`cli.py:663`); the
        single-id route had no refusal to report until adoption gave it a wave, and a
        contained one exited 0 — a script reading that code records a clean run over
        children still sitting PLANNED."""
        seen: dict[str, tuple[int, list[str]]] = {}
        for name, ids in (("flow_ids", ["500", "999"]), ("flow", ["500"])):
            with self.subTest(entry=name, argv=ids):
                self._reset(lanes=2, lane_preflight="exit 1")
                self._complete_bystander(self.cfg, "999")
                self._arm_a_refused_adoption()

                rc = self._run(cli._flow, self.cfg, self._flow_args(ids))

                seen[name] = (rc, [ln for ln in self.err.getvalue().splitlines()
                                   if ln.startswith("flow: lane preflight failed")])
                self.assertEqual(self._state("601"), state.PLANNED)  # nothing was driven

        self.assertEqual(seen["flow"][0], 1)                    # not 0, and not a traceback
        self.assertEqual(len(seen["flow"][1]), 1)               # one line, like the batch
        self.assertIn("lanes=2", seen["flow"][1][0])
        self.assertEqual(seen["flow"], seen["flow_ids"])

    def test_a_stale_chain_is_walked_through_its_terminal_generation(self) -> None:
        """Recovery has to follow the lineage as far as it actually goes. A run that
        stopped part-way through a chain (500 split → 601, 602; 601 then split → 701, 702)
        leaves 601 TERMINAL on a split — undrivable itself, but the only route to the
        grandchildren that are still stranded. Dropping it where the terminal filter finds
        it strands 701/702 forever."""
        cfg = self.cfg
        self._strand_a_split(cfg, parent="500", ids=("601", "602"))
        self._split_now(cfg.bundle("601"), ["701", "702"], [_CHILD_ONE, _CHILD_TWO])
        self._drive_to_complete(cfg, cfg.bundle("601"))
        self.assertEqual(self._state("601"), state.COMPLETE)   # terminal on ITS OWN split
        self.assertEqual(self._state("701"), state.PLANNED)

        results = self._run(flow.flow_ids, cfg, ["500"], do_publish=False,
                            today="2026-08-08")

        self.assertEqual(self._state("602"), state.COMPLETE)   # the drivable child
        self.assertEqual(self._state("701"), state.COMPLETE)   # …and the grandchildren
        self.assertEqual(self._state("702"), state.COMPLETE)
        self.assertEqual(results.get("702"), state.COMPLETE)
        err = self.err.getvalue()
        # Attributed to the parent that actually declared them, not to the run's seed.
        self.assertIn("issue_601 split → adopted children issue_701", err)
        self.assertIn("issue_601 split → adopted children issue_702", err)

    def test_the_pass_budget_is_one_cap_for_the_whole_run(self) -> None:
        """`[driver].max_passes` bounds the RUN, not each wave it grows into — otherwise
        every adopted wave silently multiplies the operator's budget. The parent's wave
        spends 2 passes (build → iterate-plan → re-plan → split → accept) and 601's spends
        1, so a run that set out to drive ONE wave at a budget of 3 is exhausted before
        602's wave: it is left PLANNED and NAMED, never driven on borrowed budget. One
        more pass and the same run finishes it."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)
        self._arm(split_at_plan="500", ids=["601", "602"])

        results = self._run(flow.flow_ids, self.cfg, ["500"], today="2026-08-08",
                            max_passes=3)

        self.assertEqual(results.get("601"), state.COMPLETE)   # adoption did happen
        self.assertEqual(self._state("602"), state.PLANNED)    # …but on the run's budget
        self.assertEqual(self.waves_driven, [["issue_500"], ["issue_601"]])
        err = self.err.getvalue()
        self.assertIn("the run's pass budget is spent (3 pass(es) over 2 wave(s))", err)
        self.assertIn("issue_602 [PLANNED] — resume with `pdca flow 602`", err)

        self.assertEqual(self.passes, 3)                       # spent, not overspent

        # The cap is what stopped it — not adoption. One more pass, everything lands.
        self._reset()
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)
        self._arm(split_at_plan="500", ids=["601", "602"])

        results = self._run(flow.flow_ids, self.cfg, ["500"], today="2026-08-08",
                            max_passes=4)

        self.assertEqual(results.get("602"), state.COMPLETE)
        self.assertEqual(self.passes, 4)
        self.assertNotIn("pass budget is spent", self.err.getvalue())

    def test_an_adopted_wave_only_gets_what_is_LEFT_of_the_run_budget(self) -> None:
        """The cap is not merely re-checked between waves, it is HANDED DOWN. 601 costs two
        passes (it iterates once), and the parent's wave already spent 2 of 3 — so 601 gets
        the ONE pass that is left, stops there and is named. Handing each wave the full
        budget again (the shape this replaces) would finish 601 on a 4th pass, i.e. spend
        more than the operator allowed the run."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)
        self._arm(split_at_plan="500", ids=["601", "602"], iterate_once="601")

        self._run(flow.flow_ids, self.cfg, ["500"], today="2026-08-08", max_passes=3)

        self.assertEqual(self.passes, 3)                       # never a 4th pass
        self.assertEqual(self._state("601"), state.ITERATE_DO)  # left mid-iteration…
        err = self.err.getvalue()
        self.assertIn("pass budget exhausted after 1 pass(es)", err)   # …its share of 3
        self.assertIn("issue_601 [ITERATE_DO] — resume with `pdca flow 601`", err)

    def test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave(self) -> None:
        """The run-wide pool must not become a NEW way for an ordinary batch to be
        truncated. A four-deep `Depends on` chain is four waves of one pass each: at
        `max_passes=1` every one of them completes, exactly as before adoption existed,
        because the pool is sized off the schedule the run set out to drive (1 × 4) — not
        one allowance shared by however many waves there turn out to be, which would strand
        810's three dependents at a setting that never truncated anything."""
        ids = ["810", "811", "812", "813"]
        for i, iid in enumerate(ids):
            d = self.cfg.bundle(iid)
            d.mkdir(parents=True)
            extra = [f"- **Depends on:** {ids[i - 1]}"] if i else []
            (d / "brief.md").write_text(_brief(f"chain-{iid}", *extra), encoding="utf-8")
        self._count_only()

        results = self._run(flow.flow_ids, self.cfg, ids, do_publish=False,
                            today="2026-08-08", max_passes=1)

        self.assertEqual([self.waves_driven], [[[f"issue_{i}"] for i in ids]])
        self.assertEqual(results, dict.fromkeys(ids, state.COMPLETE))
        self.assertEqual(self.passes, 4)                       # one per wave, as always
        self.assertNotIn("budget is spent", self.err.getvalue())

    def test_adoption_follows_the_lineage_edge_not_a_disk_sweep(self) -> None:
        """An explicit-id flow adopts the children of the ids it was GIVEN — never an
        unrelated in-flight bundle. The distinction between `flow_ids` and the CSV sweep
        is deliberate and must survive adoption."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)
        stranger = self.cfg.bundle("STRANGER")
        stranger.mkdir(parents=True)
        (stranger / "brief.md").write_text(_brief("unrelated-leftover"), encoding="utf-8")
        self._arm(split_at_plan="500", ids=["601", "602"])

        results = self._run(flow.flow_ids, self.cfg, ["500"], today="2026-08-08")

        self.assertEqual(results.get("601"), state.COMPLETE)  # the lineage edge WAS followed
        self.assertNotIn("STRANGER", results)                 # the disk was NOT swept
        self.assertEqual(self._state("STRANGER"), state.PLANNED)

    def test_a_named_id_list_keeps_its_strict_scheduling_contract(self) -> None:
        """Tolerance is for what adoption ADDS, never for what the operator asked for.
        `compute_waves` refuses an id list with a dependency cycle (`waves.py:243-246`
        calls raising "right for an explicit `flow <ids>`"), and that refusal must not
        depend on unrelated disk state — adding a stranded split parent to the same
        command line used to turn the whole run tolerant, so one id list behaved two
        ways."""
        for iid, dep in (("800", "801"), ("801", "800")):
            d = self.cfg.bundle(iid)
            d.mkdir(parents=True)
            (d / "brief.md").write_text(_brief(f"cyclic-{iid}",
                                               f"- **Depends on:** {dep}"),
                                        encoding="utf-8")
        self._strand_a_split(self.cfg)

        with self.assertRaises(ValueError) as bare:
            self._run(flow.flow_ids, self.cfg, ["800", "801"], do_publish=False,
                      today="2026-08-08")
        with self.assertRaises(ValueError) as with_seed:
            self._run(flow.flow_ids, self.cfg, ["500", "800", "801"], do_publish=False,
                      today="2026-08-08")

        self.assertIn("dependency cycle", str(bare.exception))
        self.assertIn("dependency cycle", str(with_seed.exception))
        self.assertEqual(self._state("601"), state.PLANNED)  # refused ⇒ nothing driven

    def test_an_unreadable_close_marker_never_kills_the_run(self) -> None:
        """The split probe runs over ids the operator merely NAMED, outside any `_isolate`.
        A `close-disposition` whose bytes are not UTF-8 raises `UnicodeDecodeError` — a
        `ValueError`, not the `OSError` a narrow handler expects — so a single corrupt
        marker would take down the whole explicit-id run and every drivable id in it. It is
        a hint: unreadable means "not a split", never a verdict on the run."""
        self._strand_a_split(self.cfg)
        (self.cfg.bundle("500") / state.CLOSE_MARKER).write_bytes(b"split\xff\n")
        drivable = self.cfg.bundle("777")
        drivable.mkdir(parents=True)
        (drivable / "brief.md").write_text(_brief("innocent-bystander"), encoding="utf-8")

        results = self._run(flow.flow_ids, self.cfg, ["500", "777"], do_publish=False,
                            today="2026-08-08")

        self.assertEqual(results.get("777"), state.COMPLETE)  # the named id still ran
        self.assertEqual(self._state("601"), state.PLANNED)   # not guessed at either

    def test_a_child_with_an_unresolvable_dependency_is_held_not_fatal(self) -> None:
        """Adopted children go through the resume path's tolerance: one whose declared
        prerequisite cannot be resolved is held loudly and left in-flight, and the run
        carries on with its sibling. A split must never abort the flow that caused it."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)

        def break_602() -> None:
            # A child brief that names a prerequisite outside the proposal (hand-edited
            # after the split, or re-planned since) — unresolvable at adoption time.
            bp = self.cfg.bundle("602") / "brief.md"
            bp.write_text(bp.read_text(encoding="utf-8") + "- **Depends on:** GHOST\n",
                          encoding="utf-8")

        self._arm(split_at_plan="500", ids=["601", "602"],
                  bodies=[_CHILD_ONE, _brief("child-second")], after_split=break_602)

        results = self._run(flow.flow_ids, self.cfg, ["500"], today="2026-08-08")

        self.assertEqual(results.get("601"), state.COMPLETE)  # the run continued
        self.assertEqual(self._state("602"), state.PLANNED)   # held, left in-flight
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
        self._count_only()

        results = self._run(flow.flow_ids, self.cfg, ["500"], do_publish=False,
                            today="2026-08-08")

        self.assertEqual(self.waves_driven, [["issue_601"], ["issue_602"]])  # once each
        self.assertEqual(results.get("601"), state.COMPLETE)
        self.assertEqual(results.get("602"), state.COMPLETE)
        err = self.err.getvalue()
        self.assertEqual(
            err.count("issue_500 split → adopted children issue_601 into wave 0"), 1)
        self.assertNotIn("issue_601, issue_601", err)

    def test_a_split_parent_without_a_children_record_is_reported_not_guessed(self) -> None:
        """No readable `split-lineage.json` ⇒ report it and degrade to today's behaviour
        (the operator's `pdca flow <child-ids>`). Never a crash, never a prose parse of the
        `build-notes.md` breadcrumb."""
        leaves.do_plan(self.cfg.bundle("500"), self.cfg)
        self._arm(split_at_plan="500", ids=["601", "602"],
                  after_split=lambda: (self.cfg.bundle("500") / split.LINEAGE).unlink())

        results = self._run(flow.flow_ids, self.cfg, ["500"], today="2026-08-08")

        self.assertEqual(results.get("500"), state.COMPLETE)  # the run finished cleanly
        self.assertEqual(self._state("601"), state.PLANNED)   # not driven, not lost
        self.assertIn("no readable children record", self.err.getvalue())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
