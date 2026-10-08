"""A stack-mode run carries its bundles' earlier, unmerged prerequisites (#616).

The recovery for a stack-mode run that stopped part-way is to re-issue `pdca flow <ids>`.
Before the fix that run built a dependent on a base without its prerequisite: the
prerequisite finished in the earlier run, so it is skipped as terminal and never enters
this run's fold; with nothing folded yet the dependent's stack base is cleared, so it is
cut from the plain target base; and `_runnable` lets it through, since COMPLETE only means
a draft PR was opened.

These cases pin the fix. Before wave 0 the run folds each out-of-batch `Depends on`
prerequisite that is COMPLETE, published and whose PR is open onto the integration line its
own in-run folds use (the per-batch name, #591), and points every wave-0 bundle of that
target at it; the fold after wave 0 continues that line without force, and keeps it through
a wave that accepts nothing of its target. The PR's state is asked first: a merged
prerequisite needs nothing, however old its record. A prerequisite the line must not carry
holds exactly the dependents of its target, by name, and the rest of the run goes on: no
published branch; a record older than its latest sign-off (an earlier attempt's); a PR
closed without merging (rejected work, which no same-target PR may carry); no PR URL on
record, or a host that cannot answer (`gh` failing or missing — never a traceback). A
dependent held on one prerequisite starts no line for another. One with no patch, or of
another target, needs nothing; a pre-wave fold that fails, or whose re-gate is red, stops
the run before wave 0; a dry run asks no host and holds nothing. `Depends on (merged)`
still waits for the merge, and a legacy `Stacks on` edge starts no line: its bundle still
builds on the parent's branch — unless a `Depends on` gave its target a line before wave
0, which then carries that parent too.

Real git against a bare ``origin`` and a primary checkout (the ``StackFoldGit`` shape of
``tests/test_integrate_stack_bases.py``). Build and sign-off are stubbed by patching
``flow._drive_wave``; publishing by patching ``flow._publish_bundle`` with a real push and
``publish.json``, written after the accept as publish writes it. The publisher is NOT in
stub mode (but in the one dry-run case), so every fold is a real one (a stub publisher
makes each fold a dry-run that records no line). ``gh`` is a fake that answers
``merged``'s own calls, so ``merged`` runs as shipped.

Only modules are imported (never a symbol the fix adds), so with the production change
reverted these cases still load and run — and fail.
    PYTHONPATH=src python -m unittest tests.test_flow_resume_stack_prereqs
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import tempfile
import types
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from pdca_harness import flow, integrate, merged, publish, signoff, state, worktree
from pdca_harness.config import Config, LeafConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"
TODAY = "2026-10-04"
HOUR_NS = 3_600 * 10**9


def _cfg(root: Path, primary: Path) -> Config:
    return Config(
        root=root, bundle_root=root / "results", process_dir=root / "process",
        templates_dir=TEMPLATES, default_branch="main", tracker_system="github",
        tracker_url="", issue_id_example="#1",
        builder=LeafConfig(mode="stub"), reviewer=LeafConfig(mode="stub"),
        # NOT "stub": a stub publisher turns every fold into a dry-run, and a dry-run never
        # records an integration branch — every assertion below would be vacuous.
        publisher=LeafConfig(mode="command", interactive=True), gates_checks=[],
        base_remote="origin", repo_checkouts={"org/repo": str(primary)})


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


def _brief(d: Path, *, extra: str = "", target: str = "org/repo @ main") -> None:
    d.mkdir(parents=True, exist_ok=True)
    (d / "brief.md").write_text(
        f"- **Slug:** {d.name.removeprefix('issue_').lower()}\n"
        f"- **Repo + branch target:** {target}\n{extra}", encoding="utf-8")


def _patch_text(files: dict[str, str]) -> str:
    return "".join(f"diff --git a/{n} b/{n}\nnew file mode 100644\n--- /dev/null\n"
                   f"+++ b/{n}\n@@ -0,0 +1 @@\n+{t.rstrip(chr(10))}\n"
                   for n, t in files.items())


def _accept(d: Path) -> None:
    """Make bundle ``d`` COMPLETE (accepted at sign-off, recorded in SUMMARY.md §9)."""
    (d / "check-gates.json").write_text("{}", encoding="utf-8")
    shutil.copyfile(TEMPLATES / "SUMMARY.md.tpl", d / "SUMMARY.md")
    signoff.record(d / "SUMMARY.md", action="accept", by="Tester", date=TODAY)


def _url(iid: str) -> str:
    return f"https://example.test/pr/{iid}"


def _no_gh(argv: list[str], **_kw) -> subprocess.CompletedProcess:
    """``subprocess.run`` on a host with no ``gh`` installed."""
    raise FileNotFoundError(2, "No such file or directory", argv[0])


class ResumeStackPrereqs(unittest.TestCase):

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
        self.changes: dict[str, dict[str, str]] = {}   # drive-set bundle → the files it adds
        self.waves: list[dict[str, dict]] = []          # what each driven wave was built on
        # PR url → (state, head) the host reports; state "FAIL" makes `gh` exit non-zero.
        self.prs: dict[str, tuple[str, str]] = {}
        self.gh_calls: list[list[str]] = []

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- origin ----------------------------------------------------------------------------

    def _tip(self, branch: str) -> str:
        return _git(self.origin, "rev-parse", f"refs/heads/{branch}").strip()

    def _has(self, branch: str) -> bool:
        return _run(self.origin, "rev-parse", "--verify", "--quiet",
                    f"refs/heads/{branch}").returncode == 0

    def _ancestor(self, commit: str, of: str) -> bool:
        return _run(self.origin, "merge-base", "--is-ancestor", commit, of).returncode == 0

    def _line(self, batch: list[str]) -> str:
        """The integration line a run asked to drive ``batch`` folds onto (#591)."""
        return integrate.integration_branch(self.cfg, "main", batch)

    # -- bundles ---------------------------------------------------------------------------

    def _cut(self, d: Path, files: dict[str, str], *, cut_from: str) -> None:
        """Publish's git steps: cut ``fix/<iid>`` off ``cut_from``, commit ``files`` signed
        off and push it to origin. ``patch.diff`` is that commit's diff."""
        branch = f"fix/{d.name.removeprefix('issue_')}"
        _git(self.primary, "fetch", "-q", "origin")
        _git(self.primary, "checkout", "-q", "-B", branch, cut_from)
        for name, text in files.items():
            (self.primary / name).write_text(text, encoding="utf-8")
        _git(self.primary, "add", "--all")
        _git(self.primary, "commit", "-q", "-s", "-m", f"fix {d.name}")
        (d / "patch.diff").write_text(_git(self.primary, "diff", "HEAD~1", "HEAD"),
                                      encoding="utf-8")
        _git(self.primary, "push", "-q", "origin", branch)
        _git(self.primary, "checkout", "-q", "main")

    def _record(self, d: Path, *, pr_base: str, stacked: bool = False,
                pr_url: str | None = None) -> None:
        """Publish's last write, once the push succeeded: ``publish.json``, with the PR
        url (the PR left open) — or ``pr_url`` as given ("": ``gh pr create`` failed after
        the push, and publish recorded none)."""
        iid = d.name.removeprefix("issue_")
        url = _url(iid) if pr_url is None else pr_url
        (d / "publish.json").write_text(json.dumps(
            {"mode": "stacked-pr" if stacked else "new-pr", "branch": f"fix/{iid}",
             "base": pr_base, "repo": "org/repo", "pr_url": url}), encoding="utf-8")
        if url:
            self.prs.setdefault(url, ("OPEN", ""))

    def _earlier(self, iid: str, files: dict[str, str], *, published: bool = True,
                 target: str = "org/repo @ main", pr_url: str | None = None) -> Path:
        """A bundle an EARLIER run finished, in the cycle's order: Do's patch, the accept,
        then — ``published`` — publish (its branch pushed, ``publish.json`` written last,
        the PR left open). Unpublished, it keeps a non-empty patch and no record."""
        d = self.cfg.bundle(iid)
        _brief(d, target=target)
        if published:
            self._cut(d, files, cut_from="origin/main")
        else:
            (d / "patch.diff").write_text(_patch_text(files), encoding="utf-8")
        _accept(d)
        if published:
            self._record(d, pr_base=publish._resolve_target(d)[1], pr_url=pr_url)
        self.assertEqual(state.state(d), state.COMPLETE)
        return d

    def _iterated(self, d: Path, files: dict[str, str]) -> None:
        """``d`` (published) was iterated, rebuilt with ``files`` and accepted again, but
        its re-publish failed before the push: the attempt is archived, its branch on
        origin and its publish.json are still the rejected attempt's — and that record,
        written an hour before the new accept, is older than it."""
        archive = d / "iteration-v1"
        archive.mkdir()
        for name in ("patch.diff", "check-gates.json", "SUMMARY.md"):
            (d / name).rename(archive / name)
        (d / "patch.diff").write_text(_patch_text(files), encoding="utf-8")
        _accept(d)
        self._age_record(d)
        self.assertEqual(state.state(d), state.COMPLETE)

    def _age_record(self, d: Path) -> None:
        """Date ``d``'s publish.json an hour before its SUMMARY.md (its latest sign-off)."""
        signed = (d / "SUMMARY.md").stat().st_mtime_ns
        os.utime(d / "publish.json", ns=(signed - HOUR_NS, signed - HOUR_NS))
        self.assertLess((d / "publish.json").stat().st_mtime_ns, signed)

    def _planned(self, iid: str, files: dict[str, str], *, extra: str = "",
                 target: str = "org/repo @ main") -> Path:
        """A bundle this run drives: briefed, not built. ``files`` is what its Do adds."""
        d = self.cfg.bundle(iid)
        _brief(d, extra=extra, target=target)
        self.changes[d.name] = files
        return d

    def _merge_pr(self, iid: str) -> None:
        """The maintainer merges ``fix/<iid>``'s PR into main; the host reports it merged."""
        head = self._tip(f"fix/{iid}")
        _git(self.human, "fetch", "-q", "origin")
        _git(self.human, "checkout", "-q", "-B", "main", "origin/main")
        _git(self.human, "merge", "-q", "--no-ff", "--no-edit", f"origin/fix/{iid}")
        _git(self.human, "push", "-q", "origin", "main")
        self.prs[_url(iid)] = ("MERGED", head)

    # -- the stubbed leaves ----------------------------------------------------------------

    def _drive_wave(self, cfg: Config, wave: list[Path], *, by: str, today: str,
                    max_passes: int | None = None) -> int:
        """Stands in for build → Check → sign-off: records what each bundle of the wave is
        built on — its stack base (what Do's worktree and $PDCA_VERIFY_BASE read), the
        line commit recorded with it, that line's commit on origin right now, and the ref
        Do's worktree branches off (``worktree._target``, as shipped) — then makes it
        COMPLETE."""
        seen: dict[str, dict] = {}
        for d in wave:
            line = publish.read_stack_base(d)
            seen[d.name] = {"line": line, "tip": publish.read_stack_base_tip(d),
                            "origin": self._tip(line) if line and self._has(line) else None,
                            "do_base": worktree._target(d, cfg)[1]}
            (d / "patch.diff").write_text(_patch_text(self.changes[d.name]), encoding="utf-8")
            _accept(d)
        self.waves.append(seen)
        return 1

    def _publish_bundle(self, cfg: Config, d: Path, *, by: str, today: str,
                        texts_prevalidated: bool = False) -> bool:
        """Stands in for publish: cuts the PR branch where publish cuts it — the recorded
        line commit, else the stack-base or legacy `Stacks on` parent branch
        (``publish._stack_base_branch``), else the base — and pushes it, so the fold has
        it. publish.json is written after the push, as publish writes it."""
        base = publish._resolve_target(d)[1]
        tip, parent = publish.read_stack_base_tip(d), publish._stack_base_branch(cfg, d)
        self._cut(d, self.changes[d.name], cut_from=tip or f"origin/{parent or base}")
        self._record(d, pr_base=base if publish.read_stack_base(d) else parent or base,
                     stacked=bool(parent))
        return True

    def _gh(self, argv: list[str], **_kw) -> subprocess.CompletedProcess:
        """``gh pr view <url> --json <fields>``, answered from ``self.prs``."""
        self.gh_calls.append(list(argv))
        if argv[:3] != ["gh", "pr", "view"]:
            raise AssertionError(f"unexpected command through merged: {argv}")
        st, head = self.prs.get(argv[3], ("OPEN", ""))
        if st == "FAIL":
            return subprocess.CompletedProcess(argv, 1, stdout="",
                                               stderr="HTTP 502: Bad Gateway")
        out = {"state": st, **({"headRefOid": head} if "headRefOid" in argv[-1] else {})}
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(out), stderr="")

    def _drive(self, bundles: list[Path], *, batch: list[str], gh=None,
               ) -> tuple[dict[str, str], str, list[list[str]]]:
        """``flow._drive_and_act`` as a re-issued ``pdca flow <batch>`` calls it, publishing
        in stack mode. Returns its results map, its stderr, and every push the fold made.
        ``gh`` replaces the fake host (``_no_gh``: none installed)."""
        pushes: list[list[str]] = []
        real_git = integrate._git

        def spy(repo: Path, *args: str) -> int:
            if args[:1] == ("push",):
                pushes.append(list(args))
            return real_git(repo, *args)

        err = io.StringIO()
        with mock.patch.object(flow, "_drive_wave", self._drive_wave), \
                mock.patch.object(flow, "_publish_bundle", self._publish_bundle), \
                mock.patch.object(flow.publish, "draft_texts", return_value=True), \
                mock.patch.object(merged, "subprocess",
                                  types.SimpleNamespace(run=gh or self._gh)), \
                mock.patch.object(integrate, "_git", spy), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            results = flow._drive_and_act(self.cfg, bundles, do_publish=True, do_act=False,
                                          by="Tester", today=TODAY, batch=batch)
        return results, err.getvalue(), pushes

    def _driven(self) -> list[str]:
        return [name for wave in self.waves for name in wave]

    def _held_line(self, err: str, prereq: str) -> str:
        """The one stderr line that holds ``prereq``'s dependents (#616)."""
        found = [ln for ln in err.splitlines()
                 if ln.startswith(f"flow: {prereq} ") and "held this run" in ln]
        self.assertEqual(len(found), 1, f"no single hold line for {prereq}:\n{err}")
        return found[0]

    def _held_exactly(self, held: str, names: str) -> None:
        """The hold line ``held`` names exactly the bundles ``names`` (", "-joined)."""
        self.assertEqual(held.split(" lack it: ")[1].split(". ")[0], names, held)

    def _on_the_plain_base(self, *names: str) -> None:
        """Each of ``names`` was built on main itself: no stack base, Do off origin/main."""
        for name in names:
            self.assertEqual(self.waves[0][name], {"line": "", "tip": "", "origin": None,
                                                   "do_base": "origin/main"}, name)

    # -- the criterion ---------------------------------------------------------------------

    def test_an_earlier_runs_unmerged_prerequisite_is_on_the_line_wave_0_builds_on(
            self) -> None:
        # The earlier run `pdca flow P D E U` stopped once P was COMPLETE and published; its
        # PR is still open. Re-issued, P is skipped as terminal, so the drive set is D (on
        # P), E (on D) and U (on nothing) — all org/repo @ main.
        self._earlier("P", {"p.txt": "p\n"})
        p_head = self._tip("fix/P")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        e = self._planned("E", {"e.txt": "e\n"}, extra="- **Depends on:** D\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "E", "U"]
        line = self._line(batch)

        results, err, pushes = self._drive([d, e, u], batch=batch)

        self.assertNotIn("did not integrate", err)
        self.assertNotIn("Traceback", err)
        # P is carried, not driven: it stays out of the run's results map.
        self.assertEqual(results, {"D": state.COMPLETE, "E": state.COMPLETE,
                                   "U": state.COMPLETE})
        self.assertEqual([sorted(w) for w in self.waves],
                         [["issue_D", "issue_U"], ["issue_E"]])
        wave0, wave1 = self.waves
        # Before D's wave is driven, the run's line on origin holds P's branch head, and D's
        # recorded stack base names that line — and so does U's, which does not depend on P
        # but shares the target (as every later-wave bundle already is).
        for name in ("issue_D", "issue_U"):
            seen = wave0[name]
            self.assertEqual(seen["line"], line, f"{name} was not pointed at the line")
            self.assertEqual(seen["do_base"], f"origin/{line}")
            self.assertIsNotNone(seen["origin"], f"no {line} on origin when {name} built")
            self.assertTrue(self._ancestor(p_head, seen["origin"]),
                            f"{line} did not hold P when {name} built")
            self.assertEqual(seen["tip"], seen["origin"])   # the line commit it builds on
        # D's PR branch is cut from that commit, so it carries P.
        self.assertTrue(self._ancestor(p_head, self._tip("fix/D")))
        # The fold after wave 0 continues the same line: P and D on it, E pointed at it.
        seen = wave1["issue_E"]
        self.assertEqual(seen["line"], line)
        self.assertIsNotNone(seen["origin"])
        self.assertTrue(self._ancestor(p_head, seen["origin"]))
        self.assertTrue(self._ancestor(self._tip("fix/D"), seen["origin"]))
        self.assertTrue(self._ancestor(wave0["issue_D"]["origin"], seen["origin"]),
                        "the line was rewritten, not appended to")
        # Two folds: the run's first (pre-wave) starts the line fresh with a force-push; the
        # one after wave 0 continues it WITHOUT force.
        self.assertEqual(len(pushes), 2, pushes)
        self.assertIn("--force", pushes[0])
        self.assertEqual([a for a in pushes[1] if a.startswith("--force")], [], pushes[1])
        self.assertEqual(pushes[0][-1], line)
        self.assertEqual(pushes[1][-1], line)

    def test_the_line_outlives_a_wave_that_accepts_nothing_of_its_target(self) -> None:
        # Waves {U} → {D}. D (org/repo @ main) depends on an earlier run's P (main, PR
        # open) and on U, which targets another base (dev). Wave 0 accepts nothing of main,
        # yet the fold after it must keep main's line — else D, in wave 1, has its stack
        # base cleared and builds without P after all.
        _git(self.origin, "branch", "dev", "main")
        self._earlier("P", {"p.txt": "p\n"})
        p_head = self._tip("fix/P")
        u = self._planned("U", {"u.txt": "u\n"}, target="org/repo @ dev")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P, U\n")
        batch = ["P", "U", "D"]
        line = self._line(batch)

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertNotIn("did not integrate", err)
        self.assertEqual(results, {"D": state.COMPLETE, "U": state.COMPLETE})
        self.assertEqual([sorted(w) for w in self.waves], [["issue_U"], ["issue_D"]])
        self.assertEqual(self.waves[0]["issue_U"]["line"], "")   # dev: nothing to stack on
        seen = self.waves[1]["issue_D"]
        self.assertEqual(seen["line"], line)
        self.assertIsNotNone(seen["origin"])
        self.assertTrue(self._ancestor(p_head, seen["origin"]))
        # main's line was continued (no force) by the fold after wave 0, never replaced.
        self.assertEqual([p for p in pushes if p[-1] == line and "--force" not in p],
                         [["push", "origin", line]])

    # -- companion cases: holds ------------------------------------------------------------

    def test_a_prerequisite_with_no_published_branch_holds_its_dependents(self) -> None:
        # (a) P is COMPLETE, patched and targeted, but no branch was ever published: there
        # is nothing of it to fold, so D must not build — and the rest of the run goes on.
        self._earlier("P", {"p.txt": "p\n"}, published=False)
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertNotIn("issue_D", self._driven())          # held, not built
        self.assertEqual(results["D"], state.PLANNED)
        self.assertEqual(results["U"], state.COMPLETE)       # the rest of the run went on
        held = self._held_line(err, "issue_P")
        self.assertIn("no published branch", held)
        self.assertIn("Publish it (`pdca publish P`)", held)
        self._held_exactly(held, "issue_D")
        self.assertEqual(pushes, [])                         # nothing folded
        self.assertFalse(self._has(self._line(batch)))

    def test_a_hold_is_per_dependent_another_targets_dependent_still_builds(self) -> None:
        # P (org/repo @ main) is COMPLETE and patched but never published. D (main) and D2
        # (org/repo @ dev) both depend on it. Only D could have been carried onto a line —
        # main's — so only D is held, and the hold names exactly D. D2, of another target,
        # builds as it always has: no line of dev could carry P.
        _git(self.origin, "branch", "dev", "main")
        self._earlier("P", {"p.txt": "p\n"}, published=False)
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        d2 = self._planned("D2", {"d2.txt": "d2\n"}, extra="- **Depends on:** P\n",
                           target="org/repo @ dev")
        batch = ["P", "D", "D2"]

        results, err, pushes = self._drive([d, d2], batch=batch)

        self.assertEqual(results, {"D": state.PLANNED, "D2": state.COMPLETE})
        self.assertEqual(self._driven(), ["issue_D2"])
        held = self._held_line(err, "issue_P")
        self._held_exactly(held, "issue_D")
        self.assertNotIn("issue_D2 skipped", err)
        self.assertEqual(self.waves[0]["issue_D2"]["do_base"], "origin/dev")
        self.assertEqual(pushes, [])

    def test_a_record_older_than_the_latest_sign_off_holds_its_dependents(self) -> None:
        # P was published, then iterated: rebuilt, re-accepted — and its re-publish failed
        # before the push. Its publish.json and fix/P on origin are still the REJECTED
        # attempt's, and the record is older than P's latest sign-off. Carrying that branch
        # would build D on the rejected P, so D is held and P named; U goes on.
        p = self._earlier("P", {"p.txt": "rejected\n"})
        self._iterated(p, {"p.txt": "accepted\n"})
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertEqual(results, {"D": state.PLANNED, "U": state.COMPLETE})
        self.assertEqual(self._driven(), ["issue_U"])
        held = self._held_line(err, "issue_P")
        self.assertIn("older than its latest sign-off", held)
        self.assertIn("Re-publish it (`pdca publish P`)", held)
        self._held_exactly(held, "issue_D")
        self.assertEqual(pushes, [])                         # the rejected branch is not folded
        self.assertFalse(self._has(self._line(batch)))
        self._on_the_plain_base("issue_U")

    def test_a_prerequisite_whose_pr_was_closed_unmerged_holds_its_dependents(self) -> None:
        # P's PR was closed without merging — rejected — but fix/P is still on origin. No
        # line may carry it: every same-target PR built on the line would carry the rejected
        # work. So D, which needs P, is held and named, and P is never folded — even though
        # the line is started for D3's open prerequisite P3, and U builds on it.
        self._earlier("P", {"p.txt": "p\n"})
        self.prs[_url("P")] = ("CLOSED", "")
        self._earlier("P3", {"p3.txt": "p3\n"})
        p_head, p3_head = self._tip("fix/P"), self._tip("fix/P3")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        d3 = self._planned("D3", {"d3.txt": "d3\n"}, extra="- **Depends on:** P3\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "P3", "D", "D3", "U"]
        line = self._line(batch)

        results, err, pushes = self._drive([d, d3, u], batch=batch)

        self.assertEqual(results, {"D": state.PLANNED, "D3": state.COMPLETE,
                                   "U": state.COMPLETE})
        held = self._held_line(err, "issue_P")
        self.assertIn(f"{_url('P')} closed without merging", held)
        self._held_exactly(held, "issue_D")
        self.assertIn("carrying earlier runs' unmerged prerequisite(s) issue_P3 onto", err)
        for name in ("issue_D3", "issue_U"):
            seen = self.waves[0][name]
            self.assertEqual(seen["line"], line, name)
            self.assertIsNotNone(seen["origin"], name)
            self.assertTrue(self._ancestor(p3_head, seen["origin"]), f"no P3 under {name}")
            self.assertFalse(self._ancestor(p_head, seen["origin"]),
                             f"the rejected P is under {name}")
        self.assertFalse(self._ancestor(p_head, self._tip(line)))

    def test_a_merged_prerequisite_with_no_pr_url_holds_only_its_dependents(self) -> None:
        # P was published, but `gh pr create` failed after the push, so its publish.json
        # records no PR URL. The human opened the PR by hand, it merged into main, and fix/P
        # was deleted. Nothing can ask whether P merged, so D is held and named — but the run
        # is NOT stopped (a fold of P would find no branch and no merge to judge it by): U
        # still builds, on main.
        self._earlier("P", {"p.txt": "p\n"}, pr_url="")
        self._merge_pr("P")
        _git(self.origin, "branch", "-D", "fix/P")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertNotIn("did not integrate", err)
        self.assertNotIn("STOPPING", err)
        self.assertEqual(results, {"D": state.PLANNED, "U": state.COMPLETE})
        held = self._held_line(err, "issue_P")
        self.assertIn("records no PR URL", held)
        self.assertIn("`pr_url`", held)
        self._held_exactly(held, "issue_D")
        self._on_the_plain_base("issue_U")
        self.assertEqual(self.gh_calls, [])                  # no URL: nothing to ask
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))

    def test_a_gh_failure_holds_only_that_prerequisites_dependents(self) -> None:
        # The host does not answer for P's PR (`gh pr view` exits non-zero). Whether P merged
        # — whether main already has it — is not known, so D is held and named. Only D: D3's
        # open prerequisite P3 still starts the line, and D3 and U build on it.
        self._earlier("P", {"p.txt": "p\n"})
        self.prs[_url("P")] = ("FAIL", "")
        self._earlier("P3", {"p3.txt": "p3\n"})
        p_head, p3_head = self._tip("fix/P"), self._tip("fix/P3")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        d3 = self._planned("D3", {"d3.txt": "d3\n"}, extra="- **Depends on:** P3\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "P3", "D", "D3", "U"]
        line = self._line(batch)

        results, err, pushes = self._drive([d, d3, u], batch=batch)

        self.assertNotIn("did not integrate", err)
        self.assertEqual(results, {"D": state.PLANNED, "D3": state.COMPLETE,
                                   "U": state.COMPLETE})
        self.assertIn(f"merged: could not read PR state for P ({_url('P')})", err)
        held = self._held_line(err, "issue_P")
        self.assertIn("state could not be read", held)
        self.assertIn(f"`gh pr view {_url('P')}`", held)
        self._held_exactly(held, "issue_D")
        for name in ("issue_D3", "issue_U"):
            seen = self.waves[0][name]
            self.assertEqual(seen["line"], line, name)
            self.assertIsNotNone(seen["origin"], name)
            self.assertTrue(self._ancestor(p3_head, seen["origin"]), f"no P3 under {name}")
            self.assertFalse(self._ancestor(p_head, seen["origin"]), f"P is under {name}")

    def test_no_gh_holds_the_dependents_and_never_crashes_the_run(self) -> None:
        # A plain `Depends on` now asks the host about P's PR. With no `gh` installed it
        # cannot: "not known", never a traceback out of the run — D is held and named, U
        # builds on main.
        self._earlier("P", {"p.txt": "p\n"})
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch, gh=_no_gh)

        self.assertNotIn("Traceback", err)
        self.assertEqual(results, {"D": state.PLANNED, "U": state.COMPLETE})
        self.assertIn("merged: could not read PR state for P", err)
        self._held_exactly(self._held_line(err, "issue_P"), "issue_D")
        self._on_the_plain_base("issue_U")
        self.assertEqual(pushes, [])

    def test_a_dependent_held_on_one_prerequisite_starts_no_line_for_another(self) -> None:
        # D needs P (published, PR open: carryable) AND P2 (COMPLETE, never published). P2
        # holds D, so no bundle that can build needs P on a line: none is started, P is not
        # folded, and U — same target — stays on the plain base instead of carrying P's
        # changes for nothing.
        self._earlier("P", {"p.txt": "p\n"})
        self._earlier("P2", {"p2.txt": "p2\n"}, published=False)
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P, P2\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "P2", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertEqual(results, {"D": state.PLANNED, "U": state.COMPLETE})
        self._held_exactly(self._held_line(err, "issue_P2"), "issue_D")
        self.assertNotIn("carrying", err)
        self.assertEqual(self._driven(), ["issue_U"])
        self._on_the_plain_base("issue_U")
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))

    # -- companion case: the pre-wave fold fails -------------------------------------------

    def test_a_failing_pre_wave_fold_stops_the_run_before_wave_0(self) -> None:
        # (d) The host reports P's PR open — not merged — but fix/P was deleted: the fold
        # cannot carry P. The run stops before wave 0 — nothing is driven, nothing is built
        # on a base known to be missing a prerequisite — and says so without a traceback.
        self._earlier("P", {"p.txt": "p\n"})
        _git(self.primary, "fetch", "-q", "origin")          # a stale tracking ref to prune
        _git(self.origin, "branch", "-D", "fix/P")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertIn(["gh", "pr", "view", _url("P"), "--json", "state"], self.gh_calls)
        self.assertEqual(self.waves, [])                     # no wave driven
        self.assertEqual(results, {"D": state.PLANNED, "U": state.PLANNED})
        stop = [ln for ln in err.splitlines() if "did not integrate" in ln]
        self.assertEqual(len(stop), 1, err)
        for part in ("flow: ", "issue_P", "origin/fix/P", "STOPPING"):
            self.assertIn(part, stop[0])
        self.assertNotIn("Traceback", err)
        self.assertNotIn("held this run", err)
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))

    def test_a_red_re_gate_of_the_pre_wave_line_stops_the_run_before_wave_0(self) -> None:
        # With the between-waves re-gate on, the line the pre-wave fold built is gated like
        # any folded line before a wave builds on it — and a red re-gate stops the run there,
        # nothing driven.
        self.cfg.regate_between_waves = True
        self._earlier("P", {"p.txt": "p\n"})
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        with mock.patch.object(flow.gates, "run_integration",
                               return_value={"overall": "fail"}) as regate:
            results, err, pushes = self._drive([d, u], batch=batch)

        regate.assert_called_once()
        self.assertEqual(self.waves, [])
        self.assertEqual(results, {"D": state.PLANNED, "U": state.PLANNED})
        stop = [ln for ln in err.splitlines() if "re-gate FAILED" in ln]
        self.assertEqual(len(stop), 1, err)
        self.assertIn("the pre-wave fold of issue_P", stop[0])
        self.assertIn("STOPPING", stop[0])
        self.assertNotIn("Traceback", err)

    # -- companion cases: nothing to carry -------------------------------------------------

    def test_a_merged_prerequisite_is_not_folded(self) -> None:
        # (b) P's PR has merged: its work is in the base, so nothing is folded for it and D
        # builds on the base as it always has.
        self._earlier("P", {"p.txt": "p\n"})
        self._merge_pr("P")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        batch = ["P", "D"]

        results, err, pushes = self._drive([d], batch=batch)

        self.assertEqual(results, {"D": state.COMPLETE})
        self._on_the_plain_base("issue_D")
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))
        self.assertTrue(self._ancestor(self._tip("main"), self._tip("fix/D")))

    def test_a_merged_prerequisite_never_holds_however_old_its_record(self) -> None:
        # P's PR merged. Then its SUMMARY.md was written again (a second sign-off record, a
        # hand edit), so its publish.json is now older than its latest sign-off — what the
        # stale-record check reads as a possibly rejected attempt's. Whether P merged is
        # asked FIRST: it did, its work is the base, so D is not held and builds on main.
        p = self._earlier("P", {"p.txt": "p\n"})
        self._merge_pr("P")
        self._age_record(p)
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        batch = ["P", "D"]

        results, err, pushes = self._drive([d], batch=batch)

        self.assertEqual(results, {"D": state.COMPLETE})
        self.assertNotIn("held this run", err)
        self._on_the_plain_base("issue_D")
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))

    def test_a_prerequisite_with_no_patch_is_not_folded_and_holds_nothing(self) -> None:
        # (c) A close / no-fix prerequisite ships nothing: an empty patch.diff, or none at
        # all behind a close disposition. Nothing to fold, nothing to wait for, no `gh`.
        empty = self._earlier("P0", {}, published=False)
        self.assertEqual((empty / "patch.diff").read_text(encoding="utf-8"), "")
        closed = self.cfg.bundle("P1")
        _brief(closed)
        (closed / state.CLOSE_MARKER).write_text("no-fix\n", encoding="utf-8")
        _accept(closed)
        self.assertEqual(state.state(closed), state.COMPLETE)
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P0, P1\n")
        batch = ["P0", "P1", "D"]

        results, err, pushes = self._drive([d], batch=batch)

        self.assertEqual(results, {"D": state.COMPLETE})     # not held
        self._on_the_plain_base("issue_D")
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))
        self.assertEqual(self.gh_calls, [])
        self.assertNotIn("skipped", err)
        self.assertNotIn("held this run", err)

    def test_a_prerequisite_no_line_of_the_dependents_target_could_carry_is_left_alone(
            self) -> None:
        # A line is per (repo, base): a prerequisite of another target — here another base
        # of the same repo — can never be carried into D's base, so nothing is folded for it
        # and D builds as it always has. Nor can one whose brief.md is gone (a COMPLETE
        # bundle may have none left, #481): it names no target, and reading one must not
        # raise out of the run.
        self._earlier("R", {"r.txt": "r\n"}, target="org/repo @ release")
        gone = self._earlier("G", {"g.txt": "g\n"})
        (gone / "brief.md").unlink()
        self.assertEqual(state.state(gone), state.COMPLETE)
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** R, G\n")
        batch = ["R", "G", "D"]

        results, err, pushes = self._drive([d], batch=batch)

        self.assertNotIn("Traceback", err)
        self.assertEqual(results, {"D": state.COMPLETE})
        self._on_the_plain_base("issue_D")
        self.assertEqual(pushes, [])
        self.assertEqual(self.gh_calls, [])
        self.assertFalse(self._has(self._line(batch)))

    def test_a_run_with_no_out_of_batch_prerequisite_is_unchanged(self) -> None:
        # Nothing outside the batch is depended on: no host call, no fold, no stack base.
        u = self._planned("U", {"u.txt": "u\n"})
        v = self._planned("V", {"v.txt": "v\n"})

        results, err, pushes = self._drive([u, v], batch=["U", "V"])

        self.assertEqual(results, {"U": state.COMPLETE, "V": state.COMPLETE})
        self.assertEqual(self.gh_calls, [])
        self.assertEqual(pushes, [])
        self.assertEqual([w["line"] for w in self.waves[0].values()], ["", ""])

    def test_a_dry_run_asks_no_host_and_holds_nothing(self) -> None:
        # A stub publisher makes every fold a dry run: nothing is pushed and no line is
        # recorded, so before wave 0 the run only plans the fold — and says so. It asks the
        # host nothing (an offline rehearse stays offline) and holds no one, as the in-run
        # dry fold holds no one.
        self.cfg.publisher = LeafConfig(mode="stub")
        self._earlier("P", {"p.txt": "p\n"})
        self._earlier("P2", {"p2.txt": "p2\n"}, published=False)
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P, P2\n")
        batch = ["P", "P2", "D"]

        results, err, pushes = self._drive([d], batch=batch)

        self.assertEqual(results, {"D": state.COMPLETE})
        self.assertEqual(self.gh_calls, [])
        self.assertNotIn("held this run", err)
        self.assertIn("dry run — the integration line would first carry earlier runs' "
                      "prerequisite(s) issue_P, issue_P2", err)
        self.assertEqual(pushes, [])
        self._on_the_plain_base("issue_D")

    # -- `Depends on (merged)` and `Stacks on` -------------------------------------------

    def test_depends_on_merged_still_waits_for_the_merge(self) -> None:
        # #186, unchanged: an out-of-batch `Depends on (merged)` prerequisite is never
        # folded — its dependent waits until the PR genuinely merges.
        self._earlier("P", {"p.txt": "p\n"})
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on (merged):** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertEqual(results["D"], state.PLANNED)
        self.assertNotIn("issue_D", self._driven())
        self.assertIn("issue_D skipped — prerequisite(s) not ready (P)", err)
        self.assertEqual(list(self.waves[0]), ["issue_U"])
        self._on_the_plain_base("issue_U")
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))

    def test_a_stacks_on_edge_keeps_building_on_its_parents_branch(self) -> None:
        # A legacy `Stacks on: P` (#123), P an earlier run's, published, PR open. It starts
        # no line: D builds on P's own branch and opens its PR against it, as before #616,
        # and U, of the same target, is not re-pointed either. No fold, no `gh`.
        self._earlier("P", {"p.txt": "p\n"})
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Stacks on:** P\n")
        u = self._planned("U", {"u.txt": "u\n"})
        batch = ["P", "D", "U"]

        results, err, pushes = self._drive([d, u], batch=batch)

        self.assertEqual(results, {"D": state.COMPLETE, "U": state.COMPLETE})
        self.assertEqual(self.waves, [{
            "issue_D": {"line": "", "tip": "", "origin": None, "do_base": "origin/fix/P"},
            "issue_U": {"line": "", "tip": "", "origin": None, "do_base": "origin/main"}}])
        # Publish's own reading: no recorded stack base, so P's branch is the one D's PR
        # branch is cut from and, on an own-repo setup, its PR's `--base` (publish.py:236-282).
        self.assertEqual(publish.read_stack_base(d), "")
        self.assertEqual(publish._stack_base_branch(self.cfg, d), "fix/P")
        self.assertEqual(pushes, [])
        self.assertFalse(self._has(self._line(batch)))
        self.assertEqual(self.gh_calls, [])

    def test_a_line_a_depends_on_starts_carries_a_stacks_on_parent_of_its_target(
            self) -> None:
        # D `Depends on` P, so main gets a line before wave 0, and every wave-0 bundle of
        # main builds on it — W too, which `Stacks on` Q (also an earlier run's, published,
        # PR open). W built on a line without Q would miss its parent, so the line carries
        # Q as well: both P and Q are on it before W and D are built.
        self._earlier("P", {"p.txt": "p\n"})
        self._earlier("Q", {"q.txt": "q\n"})
        p_head, q_head = self._tip("fix/P"), self._tip("fix/Q")
        d = self._planned("D", {"d.txt": "d\n"}, extra="- **Depends on:** P\n")
        w = self._planned("W", {"w.txt": "w\n"}, extra="- **Stacks on:** Q\n")
        batch = ["P", "Q", "D", "W"]
        line = self._line(batch)

        results, err, pushes = self._drive([d, w], batch=batch)

        self.assertEqual(results, {"D": state.COMPLETE, "W": state.COMPLETE})
        for name in ("issue_D", "issue_W"):
            seen = self.waves[0][name]
            self.assertEqual(seen["line"], line, name)
            self.assertEqual(seen["do_base"], f"origin/{line}", name)
            self.assertIsNotNone(seen["origin"], name)
            self.assertTrue(self._ancestor(p_head, seen["origin"]), f"no P under {name}")
            self.assertTrue(self._ancestor(q_head, seen["origin"]), f"no Q under {name}")
        self.assertEqual(len(pushes), 1, pushes)              # one fold: the pre-wave one


if __name__ == "__main__":
    unittest.main()
