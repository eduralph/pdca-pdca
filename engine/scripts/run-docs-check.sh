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

echo "== T2: docs lint (Obsidian syntax)"
"$PY" docs/publishing/tools/lint_docs.py

echo "== T2: site render + internal-link audit"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
"$PY" docs/publishing/tools/render_site.py --check --out "$OUT/site"
