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

# --- interim T3 evidence log (issue #31 item 2) -------------------------------------
# The verdict line above is the only thing the frozen record keeps, so a red T3 freezes
# as `driver suite FAILED (rc 1)` and NOTHING ELSE — no failing test name, no traceback.
# The 2026-08-06 wave recorded exactly that in 5/5 cycles; issue_384 alone cost five blind
# sign-off reruns because nothing survived to diagnose from.
#
# So keep the full output next to the bundle. The driver exports $PDCA_BUNDLE to every
# gate (src/pdca_harness/gates.py:367), and `gate-logs/<rule_id>.log` is the name the
# harness itself uses for this, so the interim log lands where the native one will.
#
# STOPGAP — REVERT THIS. eduralph/pdca-harness#370 already implements native gate-log
# retention (it was built by THIS instance, PR #415, merged); it is in the target's `main`
# at template/src/pdca_harness/gates.py:192 but not in the v0.56.0 we vendor. Delete this
# block, and the verdict-line stopgap above, once the update that consumes it lands.
#
# Best-effort: an unset $PDCA_BUNDLE (running the script by hand) or an unwritable bundle
# leaves LOG empty and changes nothing. A gate must never fail over its own logging.
LOG=""
if [ -n "${PDCA_BUNDLE:-}" ] && mkdir -p "$PDCA_BUNDLE/gate-logs" 2>/dev/null; then
  LOG="$PDCA_BUNDLE/gate-logs/T3-suite.log"
  : > "$LOG" 2>/dev/null || LOG=""
fi

# Captured rather than streamed so stderr lands in the log too — unittest writes its report
# there (the failing test names and tracebacks, the whole point of this). Echoed to stdout
# as well, so the gate's own captured output carries the detail even when $PDCA_BUNDLE is
# unset. Each suite has exited and flushed before its header is printed, and the verdict is
# echoed after both, so the last-line rule still holds.
_record() {  # <header> <captured-output>
  printf '%s\n%s\n' "$1" "$2"
  if [ -n "$LOG" ]; then
    printf '%s\n%s\n\n' "$1" "$2" >> "$LOG" 2>/dev/null || true
  fi
}

root_hdr="== T3: template-repo suite (render + update-compat)"
root_out="$("$PY" -m unittest discover -s tests -v 2>&1)" || root_rc=$?
_record "$root_hdr" "$root_out"

driver_hdr="== T3: offline driver suite (template/tests, PYTHONPATH=src)"
driver_out="$( (cd template && PYTHONPATH=src "$PY" -m unittest discover -s tests) 2>&1 )" || driver_rc=$?
_record "$driver_hdr" "$driver_out"

_verdict() {
  if [ "$1" -eq 0 ]; then echo "OK"; else echo "FAILED (rc $1)"; fi
}

# The last line, and the only one the frozen record keeps.
echo "== T3: root suite $(_verdict "$root_rc"), driver suite $(_verdict "$driver_rc")"

[ "$root_rc" -eq 0 ] || exit "$root_rc"
[ "$driver_rc" -eq 0 ] || exit "$driver_rc"
