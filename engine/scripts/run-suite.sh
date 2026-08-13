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

# Each suite runs to completion and reports (no `set -e` abort partway), so the
# PDCA-EVIDENCE verdict at the bottom always describes BOTH.
root_rc=0
driver_rc=0

# Streamed, not captured: the driver keeps every gate's combined stdout+stderr in
# `gate-logs/T3-suite.log` itself (issue #370, gates.py:192), so the failing test
# names and tracebacks survive without this script teeing them anywhere. The local
# tee that used to live here — and the "end on a verdict line" ordering the old
# last-line rule forced — were 2026-08-02/08-06 stopgaps for a v0.56.0 driver that
# had neither; both upstream fixes ship in v0.57.0 and the stopgaps are gone.
echo "== T3: template-repo suite (render + update-compat)"
"$PY" -m unittest discover -s tests -v 2>&1 || root_rc=$?

echo "== T3: offline driver suite (template/tests, PYTHONPATH=src)"
(cd template && PYTHONPATH=src "$PY" -m unittest discover -s tests) 2>&1 || driver_rc=$?

_verdict() {
  if [ "$1" -eq 0 ]; then echo "OK"; else echo "FAILED (rc $1)"; fi
}

# DECLARED evidence (issue #402, gates.py:91): the driver files the last
# `PDCA-EVIDENCE:` line as the row's evidence whatever the suites flush afterwards,
# so a green run can no longer be filed under some child's scratch /tmp path.
echo "PDCA-EVIDENCE: root suite $(_verdict "$root_rc"), driver suite $(_verdict "$driver_rc")"

[ "$root_rc" -eq 0 ] || exit "$root_rc"
[ "$driver_rc" -eq 0 ] || exit "$driver_rc"
