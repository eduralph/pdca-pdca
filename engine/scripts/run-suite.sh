#!/usr/bin/env bash
# T3 runtime gate — the target's whole test suite, ADVISORY (engine/README.md:
# a whole-suite run audits code the current fix didn't introduce; C4 is the
# per-fix gate). Two suites, per CONTRIBUTING.md:
#   1. the template-repo suite at the target root (render + update-compat — both
#      copy the WORKING TREE into a throwaway repo, so the bundle's uncommitted
#      patch is exercised; render skips itself unless copier is importable, which
#      is why the doctor row for copier is required);
#   2. the offline driver suite run directly from template/ (fast, no copier).
set -euo pipefail

WT="${PDCA_WORKTREE:?worktree isolation must be on — \$PDCA_WORKTREE must be set}"

PY="$(pwd)/.venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

cd "$WT"

echo "== T3: template-repo suite (render + update-compat)"
"$PY" -m unittest discover -s tests -v

echo "== T3: offline driver suite (template/tests, PYTHONPATH=src)"
cd template && PYTHONPATH=src "$PY" -m unittest discover -s tests
