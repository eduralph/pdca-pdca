"""A re-issued stack-mode `pdca flow <ids>` continues its batch's integration line (#646).

The recovery for a run that stopped part-way is to issue the same command again. That run
skips the ids an earlier run finished (COMPLETE) — before the fix it then built a dependent
of one of them on the plain base, without its prerequisite: the finished id was never in the
fold, `_runnable` let the dependent through on COMPLETE alone, and its stack base was
cleared. The run's first in-run fold then force-pushed a fresh line over the earlier run's,
stranding any bundle whose recorded line tip was on it.

These cases drive the real `flow._drive_and_act` the way `flow_ids` calls it for a
re-issued run (`[D]` driven, `batch=["P", "D"]`), with the real fold against real git — a
bare ``origin`` and a primary checkout, the ``StackFoldGit`` shape of
``tests/test_integrate_stack_bases.py`` — and the real ``publish.publish`` (no PR opened).
Only the build/sign-off step (``flow._drive_wave``: accept each bundle with the patch its
build "produced", recording the stack base it was pointed at) and ``gh`` (``merged``'s
``subprocess``: answered from a table) are stubbed.

Only modules are imported, never a symbol the fix adds, so with the production change
reverted these cases still load and run — and fail.
    PYTHONPATH=src python -m unittest tests.test_flow_resume_stack_prereqs
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import flow, integrate, merged, publish, signoff, state
from pdca_harness.config import Config, LeafConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
# A well-formed commit id no test repository ever holds.
ABSENT = "0123456789abcdef0123456789abcdef01234567"


def _cfg(root: Path, primary: Path) -> Config:
    """A config whose publisher is NOT a stub: a stub turns every fold into a dry-run."""
    return Config(
        root=root, bundle_root=root / "results", process_dir=root / "process",
        templates_dir=TEMPLATES, default_branch="main", tracker_system="github",
        tracker_url="", issue_id_example="#1",
        builder=LeafConfig(mode="stub"), reviewer=LeafConfig(mode="stub"),
        publisher=LeafConfig(mode="command", family="claude", interactive=True),
        gates_checks=[], base_remote="origin", repo_checkouts={"org/repo": str(primary)})


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def _git(repo: Path, *args: str) -> str:
    r = _run(repo, *args)
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed in {repo}: {r.stderr}")
    return r.stdout


def _identity(repo: Path) -> None:
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "Tester")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "fetch.prune", "false")


def _brief(d: Path, *, extra: str = "") -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.md").write_text(
        f"- **Slug:** {d.name.removeprefix('issue_').lower()}\n"
        f"- **Repo + branch target:** org/repo @ main\n{extra}", encoding="utf-8")


def _accept(d: Path) -> None:
    """Make bundle ``d`` COMPLETE (accepted at sign-off)."""
    (d / "check-gates.json").write_text("{}", encoding="utf-8")
    shutil.copyfile(TEMPLATES / "SUMMARY.md.tpl", d / "SUMMARY.md")
    signoff.record(d / "SUMMARY.md", action="accept", by="Tester", date="2026-10-05")


def _new_file(name: str, text: str) -> str:
    return (f"diff --git a/{name} b/{name}\nnew file mode 100644\n--- /dev/null\n"
            f"+++ b/{name}\n@@ -0,0 +1 @@\n+{text}\n")


def _edit_p() -> str:
    """A patch that only applies on a tree holding P's ``p.txt``."""
    return ("diff --git a/p.txt b/p.txt\n--- a/p.txt\n+++ b/p.txt\n"
            "@@ -1 +1 @@\n-p\n+p and d\n")


class _GhTable:
    """``merged``'s view of ``subprocess``: a ``gh`` call is answered from ``prs`` (PR url →
    the JSON ``gh pr view`` prints; a url not in it fails as ``gh`` does), or raises
    ``FileNotFoundError`` when ``missing``; anything else runs for real."""

    def __init__(self, prs: dict[str, dict], *, missing: bool = False) -> None:
        self.prs, self.missing, self.calls = prs, missing, []

    def run(self, args, *a, **kw):
        if args and args[0] == "gh":
            self.calls.append(list(args))
            if self.missing:
                raise FileNotFoundError(2, "No such file or directory", "gh")
            answer = self.prs.get(args[3])
            if answer is None:
                return subprocess.CompletedProcess(
                    args, 1, "", "GraphQL: Could not resolve to a PullRequest\n")
            return subprocess.CompletedProcess(args, 0, json.dumps(answer), "")
        return subprocess.run(args, *a, **kw)

    def __getattr__(self, name: str):
        return getattr(subprocess, name)


class ResumedStackRun(unittest.TestCase):

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.origin = self.tmp / "origin.git"
        self.primary = self.tmp / "repo"
        subprocess.run(["git", "init", "--bare", "-q", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.primary)], check=True)
        _identity(self.primary)
        (self.primary / "base.txt").write_text("base\n", encoding="utf-8")
        _git(self.primary, "add", "-A")
        _git(self.primary, "commit", "-q", "-m", "base")
        _git(self.primary, "remote", "add", "origin", str(self.origin))
        _git(self.primary, "push", "-q", "origin", "main")
        self.human = self.tmp / "human"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.human)],
                       check=True, capture_output=True)
        _identity(self.human)
        self.cfg = _cfg(self.tmp, self.primary)
        self.patches: dict[str, str] = {}     # bundle → the patch its build produces
        self.seen: dict[str, tuple[str, str]] = {}   # bundle → (stack base, tip) at its wave
        self.line_at: dict[str, str | None] = {}     # bundle → origin's line tip at its wave
        self.driven: list[str] = []
        self.line = ""

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- origin ---------------------------------------------------------------------------

    def _tip(self, branch: str) -> str | None:
        r = _run(self.origin, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
        return r.stdout.strip() if r.returncode == 0 else None

    def _ancestor(self, commit: str | None, of: str | None) -> bool:
        if not commit or not of:
            return False
        return _run(self.origin, "merge-base", "--is-ancestor", commit, of).returncode == 0

    # -- bundles --------------------------------------------------------------------------

    def _finished(self, iid: str, files: dict[str, str], *, record: bool = True,
                  pr_url: bool = True) -> Path:
        """A bundle an earlier run finished: its branch ``fix/<iid>`` cut off main, committed
        and pushed, its patch.diff that commit's diff, accepted (COMPLETE), and — with
        ``record`` — its publish.json naming the branch (and, with ``pr_url``, its PR)."""
        d = self.cfg.bundle(iid)
        _brief(d)
        branch = f"fix/{iid}"
        _git(self.primary, "fetch", "-q", "origin")
        _git(self.primary, "checkout", "-q", "-B", branch, "origin/main")
        for name, text in files.items():
            (self.primary / name).write_text(text, encoding="utf-8")
        _git(self.primary, "add", "--all")
        _git(self.primary, "commit", "-q", "-s", "-m", f"fix {iid}")
        (d / "patch.diff").write_text(_git(self.primary, "diff", "HEAD~1", "HEAD"),
                                      encoding="utf-8")
        _git(self.primary, "push", "-q", "origin", branch)
        _git(self.primary, "checkout", "-q", "main")
        _accept(d)
        if record:
            rec = {"mode": "new-pr", "branch": branch, "base": "main", "repo": "org/repo"}
            if pr_url:
                rec["pr_url"] = self._url(iid)
            (d / "publish.json").write_text(json.dumps(rec), encoding="utf-8")
        return d

    @staticmethod
    def _url(iid: str) -> str:
        return f"https://example.test/pr/{iid}"

    def _planned(self, iid: str, patch: str, *, extra: str = "") -> Path:
        """A PLANNED bundle whose build will produce ``patch``."""
        d = self.cfg.bundle(iid)
        _brief(d, extra=extra)
        self.patches[d.name] = patch
        return d

    # -- the run --------------------------------------------------------------------------

    def _accept_wave(self, cfg: Config, wave: list, **_kw) -> int:
        """Stands in for build + gates + sign-off: record what the bundle was pointed at,
        then accept it with the patch its build produced and the texts publish needs."""
        for d in wave:
            self.driven.append(d.name)
            self.seen[d.name] = (publish.read_stack_base(d), publish.read_stack_base_tip(d))
            self.line_at[d.name] = self._tip(self.line) if self.line else None
            (d / "patch.diff").write_text(self.patches[d.name], encoding="utf-8")
            (d / publish.COMMIT_MSG).write_text(f"fix {d.name}\n", encoding="utf-8")
            (d / publish.PR_BODY).write_text(f"Fixes {d.name}\n", encoding="utf-8")
            _accept(d)
        return 1

    def _drive(self, drive: list[Path], batch: list[str], *, prs: dict[str, dict] | None = None,
               gh_missing: bool = False, do_publish: bool = True):
        """``flow._drive_and_act(drive, batch=batch)`` as ``flow_ids`` calls it on a
        re-issued run. Returns (results, stderr, stdout, the git pushes the fold made, gh)."""
        gh = _GhTable(prs or {}, missing=gh_missing)
        pushes: list[list[str]] = []
        real_git, real_publish = integrate._git, publish.publish

        def spy_git(repo: Path, *args: str) -> int:
            if args[:1] == ("push",):
                pushes.append(list(args))
            return real_git(repo, *args)

        def no_pr(cfg: Config, issue_id: str, **kw) -> int:
            return real_publish(cfg, issue_id, open_pr=False, **kw)

        err, out = io.StringIO(), io.StringIO()
        with mock.patch.object(merged, "subprocess", gh), \
                mock.patch.object(integrate, "_git", spy_git), \
                mock.patch.object(flow, "_drive_wave", self._accept_wave), \
                mock.patch.object(publish, "draft_texts", lambda cfg, d, **kw: True), \
                mock.patch.object(publish, "publish", no_pr), \
                mock.patch.object(publish, "_warn_if_squash_only"), \
                redirect_stdout(out), redirect_stderr(err):
            results = flow._drive_and_act(self.cfg, drive, do_publish=do_publish,
                                          do_act=False, by="T", today="2026-10-05",
                                          batch=batch)
        return results, err.getvalue(), out.getvalue(), pushes, gh

    def _line_of(self, *ids: str) -> str:
        self.line = integrate.integration_branch(self.cfg, "main", list(ids))
        return self.line

    @staticmethod
    def _forced(pushes: list[list[str]]) -> list[list[str]]:
        return [p for p in pushes if any(x.startswith("--force") for x in p)]

    def _hold_lines(self, err: str, name: str) -> list[str]:
        return [ln for ln in err.splitlines()
                if ln.startswith(f"flow: {name} finished in an earlier run")]

    # -- (1) the dependent builds on a line holding its finished prerequisite --------------

    def test_1_a_dependent_builds_on_the_line_holding_its_finished_prerequisite(self) -> None:
        self._finished("P", {"p.txt": "p\n"})
        d = self._planned("D", _edit_p(), extra="- **Depends on:** P\n")
        line = self._line_of("P", "D")
        results, err, _out, _pushes, _gh = self._drive(
            [d], ["P", "D"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertEqual(self.driven, ["issue_D"], err)
        tip = self.line_at["issue_D"]
        self.assertIsNotNone(tip, f"no {line} on origin before D's wave\n{err}")
        self.assertTrue(self._ancestor(self._tip("fix/P"), tip), "the line lacks P")
        self.assertEqual(self.seen["issue_D"], (line, tip))
        # The real publish cut D's branch from that tip, so its patch (which needs P's
        # file) applied, and its PR branch carries P.
        self.assertEqual(results.get("D"), state.COMPLETE)
        rec = json.loads((d / "publish.json").read_text(encoding="utf-8"))
        self.assertTrue(self._ancestor(self._tip("fix/P"), self._tip(rec["branch"])))
        self.assertNotIn("Traceback", err)

    # -- (2) continue the earlier run's line, never replace it -----------------------------

    def test_2_the_earlier_runs_line_is_continued_never_replaced(self) -> None:
        p = self._finished("P", {"p.txt": "p\n"})
        line = self._line_of("P", "D", "E")
        # The earlier run of the same batch: its fold put P on the line, and H was built on
        # that line commit (accepted, never published — its tip is all it has to publish by).
        integrate.fold(self.cfg, [p], folded_this_run={}, batch=["P", "D", "E"])
        old = self._tip(line)
        self.assertIsNotNone(old)
        h = self.cfg.bundle("H")
        _brief(h)
        publish.write_stack_base(h, line, old)
        d = self._planned("D", _new_file("d.txt", "d"), extra="- **Depends on:** P\n")
        e = self._planned("E", _new_file("e.txt", "e"), extra="- **Depends on:** D\n")
        _results, err, _out, pushes, _gh = self._drive(
            [d, e], ["P", "D", "E"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertNotIn("STOPPING", err)
        self.assertEqual(self._forced(pushes), [], pushes)
        self.assertTrue(self._ancestor(old, self._tip(line)), "the line was replaced")
        with redirect_stderr(io.StringIO()):
            refusal = publish._line_tip_refusal(h, self.primary, old, line)
        self.assertEqual(refusal, "")

    # -- (3) append-only across waves -----------------------------------------------------

    def test_3_the_fold_after_wave_0_continues_the_carried_line(self) -> None:
        self._finished("P", {"p.txt": "p\n"})
        d = self._planned("D", _new_file("d.txt", "d"), extra="- **Depends on:** P\n")
        e = self._planned("E", _new_file("e.txt", "e"), extra="- **Depends on:** D\n")
        line = self._line_of("P", "D", "E")
        results, err, _out, pushes, _gh = self._drive(
            [d, e], ["P", "D", "E"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertNotIn("STOPPING", err)
        self.assertNotIn("did not integrate", err)
        self.assertEqual(len(pushes), 2, pushes)              # the carry, then after wave 0
        self.assertEqual(self._forced(pushes[1:]), [], pushes)
        tip = self._tip(line)
        self.assertTrue(self._ancestor(self._tip("fix/P"), tip), "the line lacks P")
        d_rec = json.loads((d / "publish.json").read_text(encoding="utf-8"))
        self.assertTrue(self._ancestor(self._tip(d_rec["branch"]), tip), "the line lacks D")
        self.assertEqual(self.seen["issue_E"][0], line)
        self.assertTrue(self._ancestor(self.line_at["issue_D"], self.seen["issue_E"][1]))
        self.assertEqual(results.get("E"), state.COMPLETE, err)

    # -- (4) a finished prerequisite that cannot be carried holds only its dependents -------

    def _assert_held(self, results: dict, err: str, *parts: str) -> None:
        self.assertNotIn("issue_D", self.driven, err)
        self.assertIn("issue_U", self.driven, err)
        self.assertEqual(results.get("D"), state.PLANNED)
        self.assertEqual(results.get("U"), state.COMPLETE, err)
        lines = self._hold_lines(err, "issue_P")
        self.assertEqual(len(lines), 1, err)
        for part in ("issue_D", "re-issue the same command", *parts):
            self.assertIn(part, lines[0])
        self.assertNotIn("issue_U", lines[0])
        self.assertNotIn("Traceback", err)
        self.assertIsNone(self._tip(self.line))               # P is in no fold

    def _held_case(self, *, prs: dict | None = None, gh_missing: bool = False, **finished):
        self._finished("P", {"p.txt": "p\n"}, **finished)
        d = self._planned("D", _edit_p(), extra="- **Depends on:** P\n")
        u = self._planned("U", _new_file("u.txt", "u"))
        self._line_of("P", "D", "U")
        results, err, _out, _pushes, _gh = self._drive(
            [d, u], ["P", "D", "U"], prs=prs, gh_missing=gh_missing)
        return results, err

    def test_4a_no_branch_on_record_holds_its_dependents(self) -> None:
        results, err = self._held_case(record=False)
        self._assert_held(results, err, "no published branch", "`pdca publish P`")

    def test_4c_a_closed_pr_holds_its_dependents(self) -> None:
        results, err = self._held_case(prs={self._url("P"): {"state": "CLOSED"}})
        self._assert_held(results, err, "CLOSED", "re-open", "re-drive P")

    def test_4d_no_pr_on_record_holds_its_dependents(self) -> None:
        results, err = self._held_case(pr_url=False)
        self._assert_held(results, err, "could not be read", "no PR on record")

    def test_4d_a_gh_failure_holds_its_dependents(self) -> None:
        results, err = self._held_case(prs={})
        self._assert_held(results, err, "could not be read", self._url("P"))

    def test_4d_gh_missing_holds_its_dependents_without_a_traceback(self) -> None:
        results, err = self._held_case(gh_missing=True)
        self._assert_held(results, err, "could not be read", "`gh` could not be run")

    # -- (5) nothing to carry; a merged PR goes to the fold ---------------------------------

    def _nothing_to_carry(self, patch_text: str | None) -> None:
        p = self._finished("P", {"p.txt": "p\n"})
        if patch_text is None:
            # A close / no-fix outcome: its close marker stands in for the patch, so it is
            # still COMPLETE (#60).
            (p / "patch.diff").unlink()
            (p / state.CLOSE_MARKER).write_text("close\n", encoding="utf-8")
            self.assertEqual(state.state(p), state.COMPLETE)
        else:
            (p / "patch.diff").write_text(patch_text, encoding="utf-8")
        d = self._planned("D", _new_file("d.txt", "d"), extra="- **Depends on:** P\n")
        self._line_of("P", "D")
        results, err, _out, pushes, _gh = self._drive(
            [d], ["P", "D"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertEqual(self.driven, ["issue_D"], err)
        self.assertEqual(results.get("D"), state.COMPLETE, err)
        self.assertEqual(self.seen["issue_D"], ("", ""))
        self.assertEqual(pushes, [])
        self.assertIsNone(self._tip(self.line))
        self.assertEqual(self._hold_lines(err, "issue_P"), [])

    def test_5_an_empty_patch_is_nothing_to_carry(self) -> None:
        self._nothing_to_carry("  \n")

    def test_5_a_missing_patch_is_nothing_to_carry(self) -> None:
        self._nothing_to_carry(None)

    def test_5_a_merged_pr_is_handed_to_the_fold(self) -> None:
        # P's PR merged into main and its branch was deleted: the fold judges it by the
        # head its PR merged with (the line, started off main, already has it).
        self._finished("P", {"p.txt": "p\n"})
        head = self._tip("fix/P")
        _git(self.human, "fetch", "-q", "origin")
        _git(self.human, "checkout", "-q", "-B", "main", "origin/main")
        _git(self.human, "merge", "-q", "--no-ff", "--no-edit", "origin/fix/P")
        _git(self.human, "push", "-q", "origin", "main")
        _git(self.origin, "branch", "-D", "fix/P")
        d = self._planned("D", _edit_p(), extra="- **Depends on:** P\n")
        line = self._line_of("P", "D")
        results, err, _out, _pushes, _gh = self._drive(
            [d], ["P", "D"], prs={self._url("P"): {"state": "MERGED", "headRefOid": head}})
        self.assertNotIn("STOPPING", err)
        self.assertEqual(self._hold_lines(err, "issue_P"), [])
        self.assertEqual(self.seen["issue_D"], (line, self.line_at["issue_D"]))
        self.assertTrue(self._ancestor(head, self.line_at["issue_D"]))
        self.assertEqual(results.get("D"), state.COMPLETE, err)

    # -- (6) a failing carry fold stops the run before wave 0 -------------------------------

    def test_6_a_failing_carry_fold_stops_before_wave_0(self) -> None:
        # P's branch is gone and its PR is still OPEN: the fold refuses (nothing of P to
        # merge, and not known to be merged).
        self._finished("P", {"p.txt": "p\n"})
        _git(self.origin, "branch", "-D", "fix/P")
        d = self._planned("D", _new_file("d.txt", "d"), extra="- **Depends on:** P\n")
        u = self._planned("U", _new_file("u.txt", "u"))
        self._line_of("P", "D", "U")
        results, err, _out, _pushes, _gh = self._drive(
            [d, u], ["P", "D", "U"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertEqual(self.driven, [], err)
        self.assertEqual(results.get("D"), state.PLANNED)
        self.assertEqual(results.get("U"), state.PLANNED)
        stop = [ln for ln in err.splitlines() if "did not integrate" in ln]
        self.assertEqual(len(stop), 1, err)
        self.assertIn("issue_P", stop[0])
        self.assertIn("STOPPING", stop[0])
        self.assertNotIn("Traceback", err)

    # -- (7) unchanged where nothing finished is depended on --------------------------------

    def test_7_no_dependency_on_a_finished_id_runs_as_before(self) -> None:
        self._finished("P", {"p.txt": "p\n"})
        d = self._planned("D", _new_file("d.txt", "d"))
        publish.write_stack_base(d, "pdca-integration/stale", ABSENT)   # a prior run's
        self._line_of("P", "D")
        results, err, _out, pushes, gh = self._drive(
            [d], ["P", "D"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertEqual(results.get("D"), state.COMPLETE, err)
        self.assertEqual(self.seen["issue_D"], ("", ""))      # stale stack base cleared
        self.assertEqual((pushes, gh.calls), ([], []))
        self.assertIsNone(self._tip(self.line))

    def test_7_stacks_on_and_depends_on_merged_do_not_carry(self) -> None:
        self._finished("P", {"p.txt": "p\n"})
        s = self._planned("S", _new_file("s.txt", "s"), extra="- **Stacks on:** P\n")
        m = self._planned("M", _new_file("m.txt", "m"),
                          extra="- **Depends on (merged):** P\n")
        self._line_of("P", "S", "M")
        results, err, _out, pushes, gh = self._drive(
            [s, m], ["P", "S", "M"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertEqual(pushes, [])
        self.assertIsNone(self._tip(self.line))
        self.assertEqual(self._hold_lines(err, "issue_P"), [])
        # Stacks on (#123): built once P is COMPLETE, its own stack base untouched by a line.
        self.assertEqual(results.get("S"), state.COMPLETE, err)
        self.assertEqual(self.seen["issue_S"], ("", ""))
        # Depends on (merged) (#186): waits for the merge, read with the merge gate's query.
        self.assertNotIn("issue_M", self.driven)
        self.assertIn("issue_M skipped — prerequisite(s) not ready (P)", err)
        self.assertEqual([c[-1] for c in gh.calls], ["state"])

    def test_7_a_dry_run_asks_no_host_holds_nothing_and_prints_the_plan(self) -> None:
        self.cfg.publisher = LeafConfig(mode="stub", interactive=True)
        self._finished("P", {"p.txt": "p\n"}, record=False)  # a real run would hold it
        d = self._planned("D", _new_file("d.txt", "d"), extra="- **Depends on:** P\n")
        line = self._line_of("P", "D")
        results, err, out, pushes, gh = self._drive([d], ["P", "D"])
        self.assertEqual(gh.calls, [])
        self.assertEqual(pushes, [])
        self.assertIsNone(self._tip(line))
        self.assertEqual(self.driven, ["issue_D"], err)
        self.assertEqual(self._hold_lines(err, "issue_P"), [])
        self.assertEqual(self.seen["issue_D"], ("", ""))
        self.assertIn(f"continue {line} if origin has it", out)
        self.assertIn("(issue_P)", out)
        self.assertEqual(results.get("D"), state.COMPLETE, err)

    def test_7_no_publish_and_merge_mode_carry_nothing(self) -> None:
        self._finished("P", {"p.txt": "p\n"})
        d = self._planned("D", _new_file("d.txt", "d"), extra="- **Depends on:** P\n")
        self._line_of("P", "D")
        results, err, _out, pushes, gh = self._drive(
            [d], ["P", "D"], prs={self._url("P"): {"state": "OPEN"}}, do_publish=False)
        self.assertEqual((pushes, gh.calls), ([], []))
        self.assertEqual(self.seen["issue_D"], ("", ""))
        self.assertEqual(results.get("D"), state.COMPLETE, err)
        self.assertFalse((d / "publish.json").exists())

        self.cfg.wave_mode = "merge"
        e = self._planned("E", _new_file("e.txt", "e"), extra="- **Depends on:** P\n")
        _results, err, _out, pushes, gh = self._drive(
            [e], ["P", "E"], prs={self._url("P"): {"state": "OPEN"}})
        self.assertEqual((pushes, gh.calls), ([], []))
        self.assertEqual(self.seen["issue_E"], ("", ""))
        self.assertIsNone(self._tip(integrate.integration_branch(self.cfg, "main",
                                                                 ["P", "E"])))

    # -- (8) an unrelated wave-0 bundle rides the carried line ------------------------------

    def test_8_an_unrelated_bundle_is_pointed_at_the_carried_line(self) -> None:
        self._finished("P", {"p.txt": "p\n"})
        d = self._planned("D", _edit_p(), extra="- **Depends on:** P\n")
        u = self._planned("U", _new_file("u.txt", "u"))
        line = self._line_of("P", "D", "U")
        results, err, _out, _pushes, _gh = self._drive(
            [d, u], ["P", "D", "U"], prs={self._url("P"): {"state": "OPEN"}})
        tip = self.line_at["issue_U"]
        self.assertIsNotNone(tip, err)
        self.assertEqual(self.seen["issue_U"], (line, tip))
        self.assertEqual(self.seen["issue_U"], self.seen["issue_D"])
        self.assertEqual(results.get("U"), state.COMPLETE, err)
        rec = json.loads((u / "publish.json").read_text(encoding="utf-8"))
        self.assertEqual((rec["mode"], rec["base"]), ("stacked-pr", "main"))   # #593


if __name__ == "__main__":
    unittest.main()
