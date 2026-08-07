"""Engine tests: the leaf model/effort policy this instance configures (#31 item 8).

These are config invariants, not driver behaviour — the driver already has upstream tests.
What they pin is that THIS pdca.toml routes the way it claims to, because the failure modes
are silent: a ladder that does not outrank the tier it escalates from re-runs the model that
just failed, an advisory leaf whose `when` never matches costs nothing and reviews nothing,
and a `substring` list (wyrd-pdca stages one locally, pending upstream) raises inside
`_when_matches` on the version vendored here.

Run: python3 -m unittest discover -s engine/tests
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

INSTANCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(INSTANCE / "src"))

from pdca_harness import leaves                      # noqa: E402
from pdca_harness.config import Config               # noqa: E402

# The tiers, as the ladder orders them. `model` is the CLI id in argv; `effort` the flag.
BASE = ("sonnet", "high")
HIGH_ROUTE = ("opus", "xhigh")
ESCALATED = ("opus", "max")

BRIEF = """\
# Brief — issue_{id}

- **Difficulty:** {difficulty}
{do_model}
## Problem

Placeholder.
"""


def _argv_model(leaf) -> str:
    """The CLI model id from argv — the value that actually reaches the backend."""
    argv = list(leaf.argv)
    for flag in ("--model", "-m"):
        if flag in argv:
            return argv[argv.index(flag) + 1]
    return ""


def _tier(leaf) -> tuple[str, str]:
    return (_argv_model(leaf), leaf.effort)


class LeafPolicy(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = Config.load(INSTANCE)

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pdca-leaf-policy-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _bundle(self, *, difficulty: str, do_model: str = "") -> Path:
        d = self.tmp / "issue_1"
        d.mkdir(exist_ok=True)
        pin = f"- **Do model:** {do_model}\n" if do_model else ""
        (d / "brief.md").write_text(
            BRIEF.format(id=1, difficulty=difficulty, do_model=pin), encoding="utf-8")
        return d

    # --- the base tier is pinned ---------------------------------------------------

    def test_builder_pins_model_and_effort(self) -> None:
        """Unpinned, Do runs on whatever the CLI defaults to that day — which makes
        loop-telemetry incomparable across cycles and the ladder below meaningless."""
        self.assertEqual(_tier(self.cfg.builder), BASE)

    def test_reviewer_pins_effort(self) -> None:
        self.assertEqual(self.cfg.reviewer.effort, "high")

    # --- routing -------------------------------------------------------------------

    def test_low_difficulty_first_attempt_uses_the_base(self) -> None:
        d = self._bundle(difficulty="low")
        self.assertEqual(_tier(leaves.select_builder(d, self.cfg, 1)), BASE)

    def test_high_difficulty_first_attempt_auto_routes_up(self) -> None:
        d = self._bundle(difficulty="high")
        self.assertEqual(_tier(leaves.select_builder(d, self.cfg, 1)), HIGH_ROUTE)

    def test_second_attempt_escalates(self) -> None:
        d = self._bundle(difficulty="low")
        self.assertEqual(_tier(leaves.select_builder(d, self.cfg, 2)), ESCALATED)

    def test_escalation_outranks_the_high_difficulty_route(self) -> None:
        """The invariant that makes iterating worth anything: a `high` bundle that failed
        on opus/xhigh must not iterate back onto opus/xhigh."""
        d = self._bundle(difficulty="high")
        first = _tier(leaves.select_builder(d, self.cfg, 1))
        second = _tier(leaves.select_builder(d, self.cfg, 2))
        self.assertEqual(first, HIGH_ROUTE)
        self.assertEqual(second, ESCALATED)
        self.assertNotEqual(first, second)

    def test_brief_pin_overrides_the_difficulty_route(self) -> None:
        d = self._bundle(difficulty="high", do_model="sonnet")
        self.assertEqual(_tier(leaves.select_builder(d, self.cfg, 1)), BASE)

    def test_every_variant_is_pinnable_by_name(self) -> None:
        """A roster entry no brief can name, and no `when` selects, is dead config. The
        codex tier carries no CLI model flag on purpose — its default is left to codex."""
        expected = {
            "sonnet":   ("sonnet", "high"),
            "fable":    ("fable", "high"),
            "opus":     ("opus", "xhigh"),
            "opus-max": ("opus", "max"),
            "codex":    ("", "high"),
        }
        names = [str(v.get("model", "")) for v in self.cfg.builder_variants]
        self.assertEqual(sorted(names), sorted(expected))
        for name, tier in expected.items():
            d = self._bundle(difficulty="low", do_model=name)
            chosen = leaves.select_builder(d, self.cfg, 1)
            self.assertEqual(_tier(chosen), tier, f"pin {name!r} routed wrong")

    def test_the_cross_vendor_pin_switches_family(self) -> None:
        d = self._bundle(difficulty="low", do_model="codex")
        self.assertEqual(leaves.select_builder(d, self.cfg, 1).family, "codex")
        self.assertEqual(self.cfg.builder.family, "claude")   # the default is unchanged

    def test_only_one_variant_auto_routes(self) -> None:
        """More than one `when` and the FIRST match wins silently — order becomes load-
        bearing config nobody reads. Keep exactly one auto-route; the rest are pin-only."""
        routed = [v for v in self.cfg.builder_variants if v.get("when")]
        self.assertEqual(len(routed), 1, routed)
        self.assertEqual(routed[0]["model"], "opus")

    # --- the adversary advisory leaf -----------------------------------------------

    def _adversary(self) -> dict:
        specs = [s for s in self.cfg.advisory_leaves if s.get("id") == "adversary"]
        self.assertEqual(len(specs), 1, self.cfg.advisory_leaves)
        return specs[0]

    def test_adversary_is_enabled(self) -> None:
        """It shipped in agents/adversary.md and was never invoked — mode stayed "stub"."""
        self.assertEqual(self._adversary()["mode"], "command")

    def test_adversary_runs_only_on_high_difficulty(self) -> None:
        spec = self._adversary()
        self.assertTrue(leaves._advisory_applies(spec, self._bundle(difficulty="high")))
        self.assertFalse(leaves._advisory_applies(spec, self._bundle(difficulty="medium")))
        self.assertFalse(leaves._advisory_applies(spec, self._bundle(difficulty="low")))

    def test_adversary_agent_prompt_exists(self) -> None:
        argv = self._adversary()["argv"]
        agent = argv[argv.index("--agent") + 1]
        self.assertTrue((INSTANCE / "agents" / f"{agent}.md").is_file())
        self.assertTrue((INSTANCE / ".claude" / "agents" / f"{agent}.md").is_file())

    # --- the portability trap ------------------------------------------------------

    def test_no_when_uses_a_substring_list(self) -> None:
        """`_when_matches` does `(when.get("substring") or "").lower()` on the version
        vendored here, so a list raises AttributeError mid-Do. wyrd-pdca's config uses
        lists — it stages that extension locally, pending upstream. Do not copy it in."""
        whens = [v.get("when") for v in self.cfg.builder_variants]
        whens += [s.get("when") for s in self.cfg.advisory_leaves]
        whens += [s.get("when") for s in self.cfg.plan_advisory_leaves]
        for when in [w for w in whens if w]:
            self.assertIsInstance(when.get("substring"), str, when)


if __name__ == "__main__":
    unittest.main()
