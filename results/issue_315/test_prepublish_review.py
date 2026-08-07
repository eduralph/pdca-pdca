"""Pre-publish review stage (`[publisher.review]`, issue #315) — offline slice.

The churn this closes: the harness stops at the draft PR, so external review depth is
serialized AFTER publish (~1 new real finding per re-review round; 13 rounds observed
on one PR). The stage pays it up front: between the T4 gate and the first git step,
publish runs N parallel review passes over the bundle's FINAL diff, unions + dedups
the findings, drops classes the instance rubric rejects, records-rejected the non-BUG
classes, and re-enters Do on BUG-class findings under a bounded budget (the
auto-iterate shape). Publish proceeds only on a round whose every finding is fixed or
recorded-rejected — a triaged fixpoint, never reviewer silence.

Success criterion, asserted here with stubbed review leaves (command-mode `sh -c`
scripts through the REAL sandboxed reviewer invocation path, the way the leaf tests
stub leaves):
  (a) enabled, publish runs N passes between T4 and the first git step;
  (b) findings are unioned/deduped across passes; rubric-rejected classes dropped;
  (c) BUG-class findings feed the brief's carry-forward block and re-enter Do,
      bounded — never open-ended;
  (d) publish proceeds only when a round completes with every finding fixed or
      recorded-rejected (and refuses, with nothing pushed, otherwise);
  (e) disabled (the default) ⇒ publish byte-identical to today.

Red on pre-fix `main`: `publish()` goes straight from `_t4_passes` to
branch/apply/commit/push with no review seam in between, so the BUG-emitting stub
reviewer here never blocks anything. The git/gh subprocesses are stubbed the way this
suite already stubs them (`test_host_ci` / `test_publish_slice`); no Claude, no network.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from pdca_harness import publish, signoff
from pdca_harness.config import Config, LeafConfig

TEMPLATES = Path(__file__).resolve().parents[1] / "templates"


def _cfg(root: Path) -> Config:
    """Stub leaves, no configured gates, generic publish defaults (own-repo remotes)."""
    return Config(
        root=root,
        bundle_root=root / "results",
        process_dir=root / "process",
        templates_dir=TEMPLATES,
        default_branch="main",
        tracker_system="github",
        tracker_url="https://example.org/issues",
        issue_id_example="1",
        builder=LeafConfig(mode="stub"),
        reviewer=LeafConfig(mode="stub"),
        planner=LeafConfig(mode="stub", interactive=True),
        signoff=LeafConfig(mode="stub", interactive=True),
        publisher=LeafConfig(mode="stub", interactive=True),
        act=LeafConfig(mode="stub", interactive=True),
        gates_checks=[],
        base_remote="origin",
        # Hermetic: pin the (nonexistent) toy target inside this test's tmp root, so
        # neither the reviewer grounding nor publish resolves a real sibling checkout.
        repo_checkouts={"example-org/example-repo": str(root / "example-repo")},
    )


_FIX_BRIEF = (
    "- **Slug:** my-fix\n"
    "- **Repo + branch target:** example-org/example-repo @ main\n"
)
_STACK_BRIEF = _FIX_BRIEF + "- **Onto branch:** origin/feature/x\n"

# Command-mode pass scripts — the "stubbed review leaves": each runs through the REAL
# sandboxed reviewer invocation path (temp cwd holding only the reviewer inputs) and
# writes its pass artifact, addressed via $PDCA_REVIEW_ARTIFACT / $PDCA_REVIEW_PASS.
_ALWAYS_BUG = ('printf -- "- bug: the flag parse crashes on empty input (x.py:1)\\n" '
               '> "$PDCA_REVIEW_ARTIFACT"')
_BUG_TEXT = "bug: the flag parse crashes on empty input (x.py:1)"
_BUG_IF_MARKER = (
    'if grep -q MARKER_BAD patch.diff; then '
    'printf -- "- bug: MARKER_BAD crashes the parser (x.py:2)\\n" '
    '> "$PDCA_REVIEW_ARTIFACT"; '
    'else printf "No findings.\\n" > "$PDCA_REVIEW_ARTIFACT"; fi')
_SHARED_PLUS_PASS1_STYLE = (
    '{ printf -- "- bug: shared crash in the parser (p.py:3)\\n"; '
    'if [ "$PDCA_REVIEW_PASS" = "1" ]; then '
    'printf -- "- prefer a docstring tweak (p.py:9)\\n"; fi; } '
    '> "$PDCA_REVIEW_ARTIFACT"')


def _reviewer(script: str) -> LeafConfig:
    return LeafConfig(mode="command", family="generic", argv=["sh", "-c", script])


def _bundle(cfg: Config, issue_id: str, *, brief_body: str = _FIX_BRIEF) -> Path:
    """An accepted (COMPLETE) bundle with a non-empty patch — publish's precondition."""
    d = cfg.bundle(issue_id)
    d.mkdir(parents=True)
    (d / "brief.md").write_text(brief_body, encoding="utf-8")
    (d / "patch.diff").write_text("diff --git a/x b/x\n", encoding="utf-8")
    (d / "check-gates.json").write_text("{}", encoding="utf-8")
    shutil.copyfile(TEMPLATES / "SUMMARY.md.tpl", d / "SUMMARY.md")
    signoff.record(d / "SUMMARY.md", action="accept", by="Tester", date="2026-08-01")
    return d


class PrepublishConfig(unittest.TestCase):
    """`[publisher.review]` parses; absent / non-boolean ⇒ the stage stays off."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _load(self, toml: str) -> Config:
        (self.tmp / "pdca.toml").write_text(toml, encoding="utf-8")
        return Config.load(self.tmp)

    def test_publisher_review_parses(self) -> None:
        cfg = self._load("[publisher.review]\nenabled = true\npasses = 2\n"
                         "max_iters = 1\n")
        self.assertEqual(cfg.prepublish_review,
                         {"enabled": True, "passes": 2, "max_iters": 1})
        self.assertEqual(publish._prepublish_cfg(cfg), (True, 2, 1))

    def test_absent_defaults_off(self) -> None:
        # Criterion (e) at the config layer: nothing declared ⇒ disabled, defaults 3/3.
        cfg = self._load("[publisher]\nfix_branch_pattern = 'fix/{id}-{slug}'\n")
        self.assertEqual(cfg.prepublish_review, {})
        self.assertEqual(publish._prepublish_cfg(cfg), (False, 3, 3))

    def test_non_bool_enabled_stays_off_loudly(self) -> None:
        # The network_access rule: a quoted "true" must not buy N model passes per
        # publish — strict boolean, reported, treated as FALSE (off = today).
        cfg = self._load("[publisher.review]\nenabled = 'true'\n")
        err = io.StringIO()
        with redirect_stderr(err):
            enabled, _p, _m = publish._prepublish_cfg(cfg)
        self.assertFalse(enabled)
        self.assertIn("boolean", err.getvalue())


class PrepublishStage(unittest.TestCase):
    """The stage in `publish()`: after T4, before the first git step — both PR paths."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.cfg = _cfg(self.tmp)
        self.calls: list[list[str]] = []

    def _fake_run(self, cmd, *a, **k):
        self.calls.append(list(cmd))
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def _enable(self, *, passes: int = 1, max_iters: int = 0) -> None:
        self.cfg.prepublish_review = {"enabled": True, "passes": passes,
                                      "max_iters": max_iters}

    def _publish(self, issue_id: str, *, do_build=None, dry_run: bool = False):
        """Real (non-dry by default) publish with git/gh stubbed and Do re-entry mocked
        at the leaf boundary (`leaves.do_build` — the model touchpoint)."""
        db = do_build if do_build is not None else mock.MagicMock()
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.ExitStack() as st:
            st.enter_context(mock.patch.object(publish, "_check_repo", return_value=0))
            st.enter_context(mock.patch.object(publish.subprocess, "run",
                                               side_effect=self._fake_run))
            st.enter_context(mock.patch.object(publish.leaves, "do_build", db,
                                               create=True))
            st.enter_context(redirect_stdout(buf))
            st.enter_context(redirect_stderr(err))
            rc = publish.publish(self.cfg, issue_id, by="Tester", today="2026-08-01",
                                 dry_run=dry_run)
        return rc, buf.getvalue(), err.getvalue(), db

    def _record(self, d: Path) -> dict:
        return json.loads((d / "prepublish-review.json").read_text(encoding="utf-8"))

    # -- (a)+(d): a BUG-class finding blocks publish before any git step -------------
    def test_bug_finding_blocks_publish_before_git(self) -> None:
        d = _bundle(self.cfg, "A1")
        self._enable(passes=1, max_iters=0)          # no re-entry budget: block at once
        self.cfg.reviewer = _reviewer(_ALWAYS_BUG)
        rc, _out, err, db = self._publish("A1")
        self.assertEqual(rc, 1, err)
        self.assertEqual(self.calls, [])             # no git step ran at all
        db.assert_not_called()                       # budget 0 ⇒ no Do re-entry either
        self.assertFalse((d / "publish.json").exists())
        self.assertTrue((d / "prepublish-review-pass-1.md").exists())
        record = self._record(d)
        self.assertEqual(record["overall"], "blocked")
        (finding,) = record["findings"]
        self.assertEqual(finding["class"], "BUG")
        self.assertEqual(finding["status"], "open")
        self.assertIn(_BUG_TEXT, err)                # the refusal names the finding

    # -- (e): disabled (the default) is byte-identical -------------------------------
    def test_disabled_default_is_byte_identical(self) -> None:
        d = _bundle(self.cfg, "E1")
        self.cfg.reviewer = _reviewer(_ALWAYS_BUG)   # would block IF the stage ran
        with mock.patch.object(publish.leaves, "run_prepublish_pass",
                               create=True) as passes:
            rc, _out, err, _db = self._publish("E1")
        self.assertEqual(rc, 0, err)
        passes.assert_not_called()                   # zero extra work
        self.assertTrue(any("push" in c for c in self.calls))
        self.assertFalse((d / "prepublish-review.json").exists())
        self.assertEqual(list(d.glob("prepublish-review-pass-*")), [])

    # -- (c)+(d): BUG re-enters Do via the carry-forward, fixpoint proceeds ----------
    def test_bug_reenters_do_then_fixpoint_proceeds(self) -> None:
        d = _bundle(self.cfg, "R1")
        (d / "patch.diff").write_text("diff --git a/x b/x\nMARKER_BAD\n",
                                      encoding="utf-8")
        self._enable(passes=1, max_iters=2)
        self.cfg.reviewer = _reviewer(_BUG_IF_MARKER)

        def fix(bundle, cfg):                        # the re-entered Do fixes the diff
            (bundle / "patch.diff").write_text("diff --git a/x b/x\nfixed\n",
                                               encoding="utf-8")

        rc, _out, err, db = self._publish("R1", do_build=mock.MagicMock(side_effect=fix))
        self.assertEqual(rc, 0, err)
        self.assertEqual(db.call_count, 1)           # one bounded re-entry sufficed
        self.assertTrue(any("push" in c for c in self.calls))       # then published
        brief_text = (d / "brief.md").read_text(encoding="utf-8")
        self.assertIn("carry-forward", brief_text)   # the finding fed the brief…
        self.assertIn("MARKER_BAD crashes the parser", brief_text)  # …verbatim
        record = self._record(d)
        self.assertEqual(record["overall"], "proceed")
        self.assertEqual(record["count"], 1)         # the auto-iterate-shaped budget
        (finding,) = record["findings"]
        self.assertEqual(finding["status"], "fixed") # judged by RE-REVIEW of the diff
        self.assertTrue((d / "publish.json").exists())

    # -- (c): the re-entry budget bounds the loop — never open-ended -----------------
    def test_reentry_budget_is_bounded(self) -> None:
        d = _bundle(self.cfg, "B1")
        self._enable(passes=1, max_iters=2)
        self.cfg.reviewer = _reviewer(_ALWAYS_BUG)   # a noisy reviewer: BUG every round
        rc, _out, err, db = self._publish("B1")      # do_build no-op: nothing gets fixed
        self.assertEqual(rc, 1, err)
        self.assertEqual(db.call_count, 2)           # exactly max_iters re-entries
        self.assertEqual(self.calls, [])             # nothing pushed
        record = self._record(d)
        self.assertEqual(record["overall"], "blocked")
        self.assertEqual(record["count"], 2)
        self.assertIn("budget", err)

    # -- (b): union + dedup across the parallel passes -------------------------------
    def test_findings_unioned_and_deduped_across_passes(self) -> None:
        d = _bundle(self.cfg, "U1")
        self._enable(passes=3, max_iters=0)
        self.cfg.reviewer = _reviewer(_SHARED_PLUS_PASS1_STYLE)
        rc, _out, _err, _db = self._publish("U1")
        self.assertEqual(rc, 1)                      # the shared BUG blocks
        record = self._record(d)
        self.assertEqual(len(record["findings"]), 2)     # union, deduped
        by_class = {f["class"]: f for f in record["findings"]}
        self.assertEqual(by_class["BUG"]["passes"], [1, 2, 3])   # all 3 raised it once
        self.assertEqual(by_class["CONVENTION"]["passes"], [1])  # pass 1's distinct one
        self.assertEqual(by_class["CONVENTION"]["status"], "rejected")

    # -- (b): classes the instance rubric rejects are dropped ------------------------
    def test_rubric_rejected_class_is_dropped(self) -> None:
        d = _bundle(self.cfg, "N1")
        self.cfg.rubric_file = "AGENTS.md"           # a rubric IS configured…
        (d / "rubric-snapshot.md").write_text(       # …and the bundle snapshot is read
            "Review rubric.\n- NOISE: bikeshed\n", encoding="utf-8")
        self._enable(passes=1, max_iters=0)
        self.cfg.reviewer = _reviewer(
            'printf -- "- bikeshed: repaint the shed (s.py:1)\\n" '
            '> "$PDCA_REVIEW_ARTIFACT"')
        rc, _out, err, _db = self._publish("N1")
        self.assertEqual(rc, 0, err)                 # dropped ⇒ nothing blocks
        self.assertTrue(any("push" in c for c in self.calls))
        (finding,) = self._record(d)["findings"]
        self.assertEqual(finding["status"], "dropped")
        self.assertIn("rubric", finding["reason"])

    # -- (d): a non-BUG class is recorded-rejected (no rubric ⇒ no drop step) --------
    def test_non_bug_class_recorded_rejected_and_proceeds(self) -> None:
        d = _bundle(self.cfg, "N2")
        self._enable(passes=1, max_iters=0)
        self.cfg.reviewer = _reviewer(
            'printf -- "- nit: cosmetic spacing (s.py:2)\\n" > "$PDCA_REVIEW_ARTIFACT"')
        rc, _out, err, _db = self._publish("N2")
        self.assertEqual(rc, 0, err)
        (finding,) = self._record(d)["findings"]
        self.assertEqual(finding["status"], "rejected")
        self.assertIn("non-BUG", finding["reason"])

    # -- (d): a human-recorded rejection unblocks a re-run ---------------------------
    def test_human_recorded_rejection_unblocks(self) -> None:
        d = _bundle(self.cfg, "H1")
        self._enable(passes=1, max_iters=0)
        self.cfg.reviewer = _reviewer(_ALWAYS_BUG)
        (d / "prepublish-review.json").write_text(json.dumps({
            "count": 0,
            "findings": [{"key": publish._finding_key(_BUG_TEXT), "text": _BUG_TEXT,
                          "class": "BUG", "status": "rejected",
                          "reason": "human: false positive"}]}), encoding="utf-8")
        rc, _out, err, _db = self._publish("H1")
        self.assertEqual(rc, 0, err)                 # recorded-rejected ⇒ proceed
        self.assertTrue(any("push" in c for c in self.calls))

    # -- fail CLOSED: no pass produced a review ⇒ refuse, never publish unreviewed ---
    def test_all_passes_failed_fails_closed(self) -> None:
        d = _bundle(self.cfg, "F1")
        self._enable(passes=1, max_iters=0)
        self.cfg.reviewer = _reviewer("exit 1")
        rc, _out, err, _db = self._publish("F1")
        self.assertEqual(rc, 1)
        self.assertEqual(self.calls, [])
        self.assertEqual(self._record(d)["overall"], "blocked")
        self.assertTrue((d / "prepublish-review-pass-1.error.log").exists())
        self.assertIn("fail closed", err)

    # -- the stacked `Onto branch` path pushes too — the stage sits before it --------
    def test_stacked_onto_branch_path_is_gated_too(self) -> None:
        _bundle(self.cfg, "S1", brief_body=_STACK_BRIEF)
        self._enable(passes=1, max_iters=0)
        self.cfg.reviewer = _reviewer(_ALWAYS_BUG)
        rc, _out, _err, _db = self._publish("S1")
        self.assertEqual(rc, 1)
        self.assertEqual(self.calls, [])             # refused before any git/gh call

    # -- offline determinism: the stub reviewer finds nothing and proceeds -----------
    def test_stub_reviewer_proceeds_without_findings(self) -> None:
        d = _bundle(self.cfg, "T1")
        self._enable(passes=2, max_iters=0)          # reviewer stays mode="stub"
        rc, _out, err, _db = self._publish("T1")
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._record(d)["overall"], "proceed")
        self.assertIn("No findings",
                      (d / "prepublish-review-pass-1.md").read_text(encoding="utf-8"))

    # -- --dry-run pushes nothing, so it skips the paid passes but names the stage ---
    def test_dry_run_skips_the_stage_but_names_it(self) -> None:
        d = _bundle(self.cfg, "D1")
        self._enable(passes=1, max_iters=0)
        self.cfg.reviewer = _reviewer(_ALWAYS_BUG)   # would block IF the passes ran
        rc, out, _err, _db = self._publish("D1", dry_run=True)
        self.assertEqual(rc, 0)
        self.assertFalse((d / "prepublish-review.json").exists())
        self.assertIn("pre-publish review stage", out)


if __name__ == "__main__":
    unittest.main()
