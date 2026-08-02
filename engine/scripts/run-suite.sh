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

# Act 2026-08-02 — the gate's EVIDENCE line. The harness records a gate's last
# output line as the evidence in check-gates.json, and this suite does not end on
# one: the target's tests drive CLI code that prints created bundle paths to stdout
# without capturing them, and under a pipe that block-buffered stdout flushes after
# unittest's own (stderr) report. So a GREEN run was filed as
# `/tmp/tmp9n1xzuc2/results/issue_500/split-proposal.md` — a scratch path that reads
# like a failure, escalated to §6 NEEDS-HUMAN in 12 of 19 frozen cycles.
# Both halves are upstream (leak + last-line rule): eduralph/pdca-harness#402,
# and #428 for the related marker scan. This ends on a verdict line meanwhile.
# REVERT once #402 lands — the fix belongs there, this is a local stopgap.
#
# Each suite runs to completion and reports (no `set -e` abort partway), so the
# verdict below always describes BOTH. Ordering is safe: each `python3` has exited
# and flushed before the next line is echoed.
root_rc=0
driver_rc=0

echo "== T3: template-repo suite (render + update-compat)"
"$PY" -m unittest discover -s tests -v || root_rc=$?

echo "== T3: offline driver suite (template/tests, PYTHONPATH=src)"
( cd template && PYTHONPATH=src "$PY" -m unittest discover -s tests ) || driver_rc=$?

_verdict() {
  if [ "$1" -eq 0 ]; then echo "OK"; else echo "FAILED (rc $1)"; fi
}

# The last line, and the only one the frozen record keeps.
echo "== T3: root suite $(_verdict "$root_rc"), driver suite $(_verdict "$driver_rc")"

[ "$root_rc" -eq 0 ] || exit "$root_rc"
[ "$driver_rc" -eq 0 ] || exit "$driver_rc"
