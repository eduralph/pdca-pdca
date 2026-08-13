#!/usr/bin/env python3
"""C5 advisory gate — the reference #154 heuristic, scoped to the target's driver suite.

`scripts/checks/test_exercises_production.py` ships with the harness and asks one question
of every NEWLY ADDED test file in `patch.diff`: does it import the production package, or
might it be exercising a hand-ported copy of it? It has been in this repo since the render
commit, with its own suite (`tests/test_prod_path_gate.py`), and was never wired.

The reason it needs a wrapper is that the target has TWO test roots and the question is
only meaningful in one of them:

  * `template/tests/…` — the offline driver suite, run with PYTHONPATH=src. It exercises
    `pdca_harness` directly, and 72 of its 78 modules import it. IN SCOPE.
  * `tests/…` — the template-repo suites (render, update-compat). They RENDER the template
    into a throwaway project and drive it as a subprocess, so importing `pdca_harness` is
    exactly what they must not do; 1 of 3 does. Asking the question there produces a §6
    item on correct code, so those files are reported out of scope instead.

The reference checker takes no path filter, and it is template-shipped — editing it would
fork a file `copier update` re-applies and break its shipped suite. So this wrapper reuses
its logic unmodified: `added_test_blocks` does the diff parsing, and the in-scope blocks
are handed back to `unverifiable_reason` as a synthetic diff so its import test (regex
included) stays the single source of truth.

KNOWN FALSE POSITIVE, worth recognising at sign-off rather than suppressing: six driver
suites assert on WORDING — they read a file and make claims about its text instead of
importing anything (test_verify_red_leg, test_remote_control_docs, test_settings_permissions,
test_suite_output_hygiene, test_leaf_scratch_discipline, test_prod_path_gate). A new test of
that shape is legitimately import-free and will be flagged. That is ~8% of the suite, the
gate is advisory and always exits 0, and the alternative — teaching the heuristic to
recognise them — would blunt the one thing it is for.

Run: PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py   (needs $PDCA_BUNDLE)
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

INSTANCE = Path(__file__).resolve().parents[2]
REFERENCE = INSTANCE / "scripts" / "checks" / "test_exercises_production.py"

# The target's driver suite — the only root where "does this import production?" is a fair
# question. Keep in step with docs/INTEGRATION.md §3 (test placement) and with
# engine/scripts/run-verify.sh, which splits the same two roots for the C4 legs.
IN_SCOPE = "template/tests/"

EVIDENCE = "PDCA-EVIDENCE:"
UNVERIFIABLE = "PDCA-UNVERIFIABLE:"


def _reference():
    """The shipped checker, imported as a module (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("pdca_prod_path_reference", REFERENCE)
    if spec is None or spec.loader is None:                      # pragma: no cover
        raise ImportError(f"cannot load the reference checker at {REFERENCE}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _synthetic_diff(blocks: dict[str, list[str]]) -> str:
    """Re-emit `blocks` as a diff the reference checker parses back to the same blocks.

    Round-tripping through its own parser is what keeps the import test — and the regex
    behind it — owned by the shipped file rather than copied into this one."""
    out: list[str] = []
    for path, added in blocks.items():
        out += [f"diff --git a/{path} b/{path}", "new file mode 100644",
                "--- /dev/null", f"+++ b/{path}"]
        out += [f"+{line}" for line in added]
    return "\n".join(out) + "\n"


def main() -> int:
    pkg = os.environ.get("PDCA_PROD_PACKAGE", "pdca_harness").strip()
    bundle = os.environ.get("PDCA_BUNDLE", "")
    patch = Path(bundle, "patch.diff") if bundle else None
    if not patch or not patch.is_file() or not patch.read_text(encoding="utf-8").strip():
        # A close / no-fix disposition has nothing to assert — the reference's own reading.
        print(f"{EVIDENCE} no patch to check (close / no-fix disposition)")
        return 0

    ref = _reference()
    diff = patch.read_text(encoding="utf-8", errors="replace")
    blocks = ref.added_test_blocks(diff)
    if not blocks:
        print(f"{EVIDENCE} patch adds no new test file — nothing to assert")
        return 0

    scoped = {p: lines for p, lines in blocks.items() if p.startswith(IN_SCOPE)}
    skipped = sorted(set(blocks) - set(scoped))
    for path in skipped:
        print(f"out of scope (template-repo suite, renders rather than imports): {path}")

    if not scoped:
        print(f"{EVIDENCE} no new driver-suite test in this patch — "
              f"{len(skipped)} added test file(s) out of scope")
        return 0

    reason = ref.unverifiable_reason(_synthetic_diff(scoped), pkg)
    if reason:
        print(f"{UNVERIFIABLE} {reason} — if the new test asserts on a file's WORDING "
              f"rather than exercising the package, that is the known import-free shape "
              f"(see this script's header); confirm that at sign-off")
        return 0

    print(f"{EVIDENCE} {len(scoped)} added driver-suite test(s) import the production "
          f"package '{pkg}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
