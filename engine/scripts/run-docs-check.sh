#!/usr/bin/env bash
# T2 shape gate — the target's docs conventions, ADVISORY. Mirrors the target's
# own docs-check.yml exactly (single-sourced on the TARGET's checkers, not a
# re-implementation): the Obsidian-syntax lint plus the full site render with
# the internal-link audit. Renders into a temp dir so the worktree stays clean.
# Needs markdown-it-py[linkify] + PyYAML in the instance venv (extra_bootstrap).
set -euo pipefail

WT="${PDCA_WORKTREE:?worktree isolation must be on — \$PDCA_WORKTREE must be set}"

PY="$(pwd)/.venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

cd "$WT"

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT

# Each checker runs to completion and reports; `|| rc=$?` keeps `set -e` from aborting
# the script at the first red. That is what lets the declaration below describe BOTH legs
# — and, more to the point, lets a FAILING run declare anything at all. Aborting at the
# first checker would leave the row's evidence as whatever that checker flushed last
# (gates.py:771 falls back to the final output line), which is the decoy-path problem this
# marker exists to close, still open on exactly the path a human most needs to read.
lint_rc=0
render_rc=0

echo "== T2: docs lint (Obsidian syntax)"
"$PY" docs/publishing/tools/lint_docs.py || lint_rc=$?

echo "== T2: site render + internal-link audit"
"$PY" docs/publishing/tools/render_site.py --check --out "$OUT/site" || render_rc=$?

_verdict() {
  if [ "$1" -eq 0 ]; then echo "clean"; else echo "FAILED (rc $1)"; fi
}

# DECLARED evidence (issue #402, gates.py:91) on every exit path, pass or fail.
echo "PDCA-EVIDENCE: docs lint $(_verdict "$lint_rc"), site render + link audit $(_verdict "$render_rc")"

[ "$lint_rc" -eq 0 ] || exit "$lint_rc"
[ "$render_rc" -eq 0 ] || exit "$render_rc"
