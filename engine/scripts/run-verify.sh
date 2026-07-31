#!/usr/bin/env bash
# Per-fix correctness gate (C4) for pdca-pdca — target: eduralph/pdca-harness.
#
# Wired from pdca.toml as a bundle-scoped GATING check. The driver has already
# reconstructed base + patch.diff in $PDCA_WORKTREE (#296), so this script proves
# red→green by reverting and re-applying the patch's PRODUCTION hunks in place:
#   green leg — bundle tests with the fix applied MUST pass;
#   red leg   — with only the production hunks reverted they MUST fail.
# Exits 0 iff both hold. $PDCA_BASE/$PDCA_VERIFY_BASE need no handling here: the
# driver prepares the tree on the correct base before any gate runs.
#
# Classification (issue #165, engine/README.md): a patch that ships no test, or
# whose only non-test changes are non-behavioral for the deterministic suites
# (docs/, .github/, Markdown — incl. the template's .md.jinja role prompts —
# LICENSE/NOTICE/DCO), has no revert that can go red: emit PDCA-UNVERIFIABLE and
# exit 77 (→ SUMMARY §6 NEEDS-HUMAN, non-gating), never a guaranteed C4 fail.
#
# pdca-harness has two test roots, invoked differently (CONTRIBUTING.md):
#   tests/…            the template-repo suites — run from the target root;
#   template/tests/…   the offline driver suite — run from template/, PYTHONPATH=src.
set -euo pipefail

BUNDLE="${PDCA_BUNDLE:?run from the driver — \$PDCA_BUNDLE must be set}"
WT="${PDCA_WORKTREE:?worktree isolation must be on — \$PDCA_WORKTREE must be set}"
PATCH="$BUNDLE/patch.diff"

# The instance venv's python (copier + docs deps live there — extra_bootstrap);
# the gate's cwd is the instance root.
PY="$(pwd)/.venv/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

[ -s "$PATCH" ] || { echo "PDCA-UNVERIFIABLE: bundle has no patch.diff"; exit 77; }

cd "$WT"

# Every path the patch touches (numstat col 3 parses the patch, applied or not).
mapfile -t CHANGED < <(git apply --numstat "$PATCH" | awk -F'\t' '{print $3}')

TESTS=() PROD=()
for p in "${CHANGED[@]}"; do
  case "$p" in
    tests/*.py|template/tests/*.py) TESTS+=("$p") ;;
    docs/*|.github/*|*.md|*.md.jinja|LICENSE|NOTICE|DCO) ;;   # non-behavioral
    *) PROD+=("$p") ;;
  esac
done

if [ "${#TESTS[@]}" -eq 0 ]; then
  echo "PDCA-UNVERIFIABLE: patch ships no test (changed: ${CHANGED[*]})"; exit 77
fi
if [ "${#PROD[@]}" -eq 0 ]; then
  echo "PDCA-UNVERIFIABLE: no behavioral production change to revert (test-only or docs-only patch)"; exit 77
fi

run_tests() {
  local rc=0 t mod
  for t in "${TESTS[@]}"; do
    mod="tests.$(basename "$t" .py)"
    case "$t" in
      template/tests/*) (cd template && PYTHONPATH=src "$PY" -m unittest "$mod") || rc=1 ;;
      tests/*)          "$PY" -m unittest "$mod" || rc=1 ;;
    esac
  done
  return "$rc"
}

echo "== C4 green leg: bundle test(s) with the fix applied: ${TESTS[*]}"
run_tests || { echo "C4 FAIL: bundle test red WITH the fix applied"; exit 1; }

# Red leg: revert only the production hunks; the tests stay in place. Restore on
# every exit path so later gates always see base + full patch.
EXCLUDES=(--exclude=tests/* --exclude=template/tests/*)
restore() { git apply "${EXCLUDES[@]}" "$PATCH" 2>/dev/null || true; }
trap restore EXIT
git apply -R "${EXCLUDES[@]}" "$PATCH"

echo "== C4 red leg: bundle test(s) with the production change reverted"
if run_tests; then
  echo "C4 FAIL: bundle test still green WITHOUT the fix — it does not capture the defect"
  exit 1
fi

echo "C4 PASS: red without the fix, green with it"
