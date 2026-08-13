#!/usr/bin/env bash
# Host-CI parity (issue #311) — the target's docs-check.yml, run on the tree the push
# will actually build on. Wired from pdca.toml as a `[gates] host_ci` row, which is
# GATING by construction: the target's CI fails these on every PR regardless, so an
# advisory row here would just re-open the gap.
#
# Same two checkers as the T2 row (engine/scripts/run-docs-check.sh) and the same
# single-sourcing on the TARGET's own tools — but a different seam. The T2 row is an
# advisory Check-time reading; this one re-runs inside `pdca-pdca publish`, in an
# ephemeral worktree pinned to the exact base commit the pushed branch is built on, so
# a green certifies the pushed tree even when the base moved since Check.
#
# CWD: unlike every other engine script, a host_ci row already runs FROM the
# reconstructed base + patch.diff worktree. Do NOT cd anywhere — cd'ing is how this
# would end up auditing the wrong tree, which is the whole failure the feature closes.
#
# $PDCA_BUNDLE is the only absolute path a gate's environment carries, and it is not
# usable to find this script (an ephemeral publish-time worktree is elsewhere entirely),
# so the instance root comes from this file's own location: engine/scripts/ → ../../.
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INSTANCE="$(cd -- "$HERE/../.." && pwd)"

# markdown-it-py[linkify] + PyYAML live in the instance venv ([install] extra_bootstrap),
# never in whatever python the target tree happens to see.
PY="$INSTANCE/.venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

# A tree without the checkers is not a green — say so as UNVERIFIABLE (exit 77 → §6
# NEEDS-HUMAN) rather than pass silently. At publish, exit 77 blocks the push too.
for tool in docs/publishing/tools/lint_docs.py docs/publishing/tools/render_site.py; do
  [ -f "$tool" ] || {
    echo "PDCA-UNVERIFIABLE: $tool is not in this tree — the target moved its docs checkers; update engine/scripts/run-host-ci.sh and the T2 row to match"
    exit 77
  }
done

echo "== host CI parity: docs lint (Obsidian syntax)"
"$PY" docs/publishing/tools/lint_docs.py

echo "== host CI parity: site render + internal-link audit"
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
"$PY" docs/publishing/tools/render_site.py --check --out "$OUT/site"

# DECLARED evidence (issue #402, gates.py:91) — otherwise the row is filed under
# whichever line the renderer flushed last, a path under $OUT that is already gone.
echo "PDCA-EVIDENCE: host CI parity clean (docs lint + site render) on the patched tree"
