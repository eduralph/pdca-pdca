#!/usr/bin/env bash
# Per-fix correctness gate (C4) for pdca-pdca — target: eduralph/pdca-harness.
#
# Wired from pdca.toml as a bundle-scoped GATING check. The driver has already
# reconstructed base + patch.diff in $PDCA_WORKTREE (#296), so this script proves
# red→green by reverting and re-applying the patch's PRODUCTION hunks in place:
#   green leg — bundle tests with the fix applied MUST pass;
#   red leg   — with only the production hunks reverted they MUST fail.
# Exits 0 iff both hold. The three base exports — $PDCA_BASE / $PDCA_VERIFY_BASE /
# $PDCA_BRIEF_BASE (#54 / #273 / #387; the driver sets exactly one per bundle-scoped
# gate) — need no handling here: the driver prepares the tree on the correct base
# before any gate runs, so this script never resolves a base itself. That is also why
# it cannot drift from the base publish commits to.
#
# ---------------------------------------------------------------------------------
# The published C4 contract, verbatim from the template skeleton. This instance FILLED
# the gate in (below) — which is what the skeleton itself, and engine/README.md, tell
# every instance to do — but tests/test_verify_red_leg.py and tests/test_verify_base.py
# (new in v0.57.0) assert this wording is present in THIS file, so a filled-in gate that
# drops it turns the T3 suite red. Kept verbatim to satisfy them.
#
# TEMPORARY, pending eduralph/pdca-harness#507. The rule does NOT depend on this block:
# engine/README.md ships to every instance, is not a fill-in file, and states the same
# contract and truth table at engine/README.md:56-67 — the suite asserts against it in
# parallel. So once #507 scopes these assertions to the template checkout, delete this
# block and the section marker below; nothing is lost.
# ---------------------------------------------------------------------------------
# The driver exports $PDCA_BUNDLE = the bundle dir (results/issue_<id>/), which
# holds patch.diff and the brief that names the test. It also exports, when set:
#   - $PDCA_WORKTREE   — the tree Do edited (worktree isolation, #94); run/reset here.
#   - $PDCA_BASE / $PDCA_VERIFY_BASE / $PDCA_BRIEF_BASE — the base to reset to before
#       applying patch.diff. The driver sets EXACTLY ONE of these for every bundle-scoped
#       gate: the test base must never diverge from the base publish will commit to. Each is
#       already a fully-qualified remote-tracking ref (`<remote>/<branch>`) — use it as-is,
#       never `origin/$VAR` (that doubles the remote).
#         * $PDCA_BASE (issue #54) — the brief's `Onto branch`. Publish appends the fix as a
#           commit to that existing PR head, so the gate must prove red->green on IT.
#         * $PDCA_VERIFY_BASE (issue #273) — the wave's folded integration branch
#           (`origin/pdca-integration/<base>`) for a wave>0 bundle in a dependency batch, so a
#           dependent verifies against base+prereqs. Resetting to the brief's origin base
#           instead would false-fail "patch does not apply — stale" for a dependent that
#           shares a file with its prereq, or measure red->green against a tree LACKING it.
#         * $PDCA_BRIEF_BASE (issue #387) — the ordinary case: the brief's own
#           `Repo + branch target` base (or the project default branch when it names none),
#           resolved by the driver with the SAME parser publish uses. Do NOT re-derive it by
#           parsing brief.md in shell: that parse is subtle (a backticked ref counts only at
#           the START of the field, so `main (feature branch \`feat/x\`)` means `main`) and
#           a re-derivation drifts from the base publish commits to — the divergence #235
#           and #262 fixed in Python and this export removes from shell.
#       Resolve as: $PDCA_BASE > $PDCA_VERIFY_BASE > your own override > $PDCA_BRIEF_BASE.
# The contract this script must enforce, exiting 0 iff BOTH hold:
#   - WITHOUT the fix applied, the bundle's test FAILS (red) — proves the repro.
#   - WITH the fix (patch.diff) applied, the bundle's test PASSES (green).
# That validates THIS change, not the whole suite (see engine/README.md).
#
# Typical shape (pseudocode — replace with your project's apply/run/revert):
#   1. read the test path from $PDCA_BUNDLE/brief.md
#   2. revert the production change, run the test  -> expect a REAL red: a test that RAN
#      and failed (judge it by the two facts below, never by the exit code alone)
#   3. apply $PDCA_BUNDLE/patch.diff, run the test -> expect PASS (green)
#   4. exit 0 on red-then-green, non-zero otherwise
#
# JUDGE EVERY LEG BY TWO FACTS: the runner's exit code AND how many tests actually ran.
# A test runner exits non-zero for two unrelated reasons — the test RAN and failed (the red
# leg's proof), or NO test ran at all (it failed to compile/import/collect, the runner could
# not find it, the runner itself died). An exit code cannot tell those apart, so a leg judged
# on the exit code alone reports PASS for a bundle whose test never executed. That is an
# everyday shape, not a corner case: reverting the fix also removes any symbol the fix
# introduced, so a test that calls one cannot even build on the red leg.
# Capture BOTH per run: the exit code, and a COUNT of executed tests parsed from the runner's
# own machine-readable report (TAP, JUnit XML, `--format json`, `python -m unittest -v`, …).
# Never infer that count from the exit code.
#
#   exit code | tests ran | what it means -> what to report
#   ----------+-----------+---------------------------------------------------------------
#    0        |  0        | nothing ran -> PDCA-UNVERIFIABLE (77): no evidence either way
#    0        | >0        | test PASSED -> green leg: OK; red leg: C4 FAIL (green without
#             |           |                the fix — the test does not capture the defect)
#    non-zero | >0        | test FAILED -> red leg: the red you want; green leg: C4 FAIL
#    non-zero |  0        | nothing ran -> PDCA-UNVERIFIABLE (77), NEVER PASS: the runner
#             |           |                died before/while collecting, so its non-zero
#             |           |                exit proves nothing about the defect
#
# Keep the two "nothing ran" cases distinguishable in the reason you print — the human
# reading §6 needs different things from each: `no test executed (runner exited 0: nothing
# was selected — wrong test path or filter?)` vs `no test executed (runner exited <rc>: the
# test did not build/import — e.g. it calls a symbol the reverted fix added)`.
# THE RULE, for every leg you add here and for every other verification step: a step in
# which no test ran is UNVERIFIABLE — exit 77 / `PDCA-UNVERIFIABLE: <reason>` (-> SUMMARY §6
# NEEDS-HUMAN, non-gating) — never a pass and never a fail. A gate never turns "no evidence"
# into a verdict.
#
# CLASSIFY THE PATCH FIRST (issue #165). If the patch's only non-test change is a
# NON-BEHAVIORAL file a project must update but that can't move the test — a translation
# manifest / file-registration list / generated asset (e.g. po/POTFILES.{in,skip}) — there
# is nothing to revert that would go red. Emit `PDCA-UNVERIFIABLE: <reason>` and exit 77
# (-> SUMMARY §6 NEEDS-HUMAN, non-gating) instead of a red->green the bundle is guaranteed
# to fail (a false C4 fail for a verify-first test-only fix). Keep the non-production set as
# a config list of path globs. See engine/README.md (§The two gate shapes that matter).
# ---------------------------------------------------------------------------------
# How pdca-pdca realizes it.
# ---------------------------------------------------------------------------------
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

# --- what actually EXECUTED, not just what exited (issue #31 item 7) ----------------
# An exit status alone cannot carry either leg's verdict, and Python's unittest has its
# own version of the problem a compiled runner has:
#
#   * ZERO tests ran. A filter that matches nothing, or a module whose cases are all
#     skipped, exits 0 having asserted nothing. On the GREEN leg that is the absence of a
#     measurement, not a pass.
#   * The module never LOADED. When a test module fails to import, the loader substitutes
#     a synthetic `unittest.loader._FailedTest`, reports "Ran 1 test" and exits non-zero —
#     byte-for-byte the shape of a failing assertion. On the RED leg that is the dangerous
#     one: reverting the production hunks DELETES the symbols a net-new test imports, so
#     the test that never ran was being recorded as proof that it catches the defect. An
#     evidence gate failing toward *accept*.
#
# Both are exit 77 (PDCA-UNVERIFIABLE → §6 NEEDS-HUMAN), never a verdict on the patch: the
# leg produced no measurement, so it has none to hold against the fix in either direction.
# Upstream sibling: eduralph/pdca-harness#439.
TESTS_RAN=0
LOAD_FAILED=0

# Sum "Ran N tests in …" across every sub-run (each TESTS entry is its own invocation).
_ran_from() {
  printf '%s\n' "$1" \
    | sed -nE 's/^Ran ([0-9]+) tests? in .*/\1/p' \
    | awk '{ t += $1 } END { print t + 0 }'
}

run_tests() {
  local rc=0 t mod out sub_rc
  TESTS_RAN=0
  LOAD_FAILED=0
  for t in "${TESTS[@]}"; do
    mod="tests.$(basename "$t" .py)"
    sub_rc=0
    # Captured rather than streamed: the counts and the loader marker below are only
    # readable off the output. Echoed straight back so the gate log is unchanged.
    case "$t" in
      template/tests/*) out="$( (cd template && PYTHONPATH=src "$PY" -m unittest "$mod") 2>&1 )" || sub_rc=$? ;;
      tests/*)          out="$("$PY" -m unittest "$mod" 2>&1)" || sub_rc=$? ;;
    esac
    printf '%s\n' "$out"
    [ "$sub_rc" -eq 0 ] || rc=1
    TESTS_RAN=$(( TESTS_RAN + $(_ran_from "$out") ))
    case "$out" in *"unittest.loader._FailedTest"*) LOAD_FAILED=1 ;; esac
  done
  return "$rc"
}

echo "== C4 green leg: bundle test(s) with the fix applied: ${TESTS[*]}"
GREEN_RC=0
run_tests || GREEN_RC=$?

# "Nothing ran" is checked BEFORE the exit status, because the status does not settle it in
# either direction: unittest exits 0 on a zero-case discovery run and non-zero on a named
# module with no cases ("NO TESTS RAN"). Neither is a green, and neither is a patch defect.
if [ "$TESTS_RAN" -eq 0 ]; then
  echo "PDCA-UNVERIFIABLE: 0 tests ran with the fix applied, so the green leg asserted nothing — the test is filtered out, skipped, or names no case"
  exit 77
fi
# A module that fails to import WITH the fix applied is a real defect, so it falls through
# to the fail below (it reports "Ran 1 test", so the guard above does not swallow it).
if [ "$GREEN_RC" -ne 0 ]; then
  echo "PDCA-EVIDENCE: C4 FAIL — bundle test red WITH the fix applied"
  exit 1
fi

# Red leg: revert only the production hunks; the tests stay in place. Restore on
# every exit path so later gates always see base + full patch.
EXCLUDES=(--exclude=tests/* --exclude=template/tests/*)
restore() { git apply "${EXCLUDES[@]}" "$PATCH" 2>/dev/null || true; }
trap restore EXIT
git apply -R "${EXCLUDES[@]}" "$PATCH"

echo "== C4 red leg: bundle test(s) with the production change reverted"
RED_RC=0
run_tests || RED_RC=$?

# The red leg's verdict comes from the status AND what ran:
#
#   rc  ran  load  verdict        why
#   --  ---  ----  ------------   -----------------------------------------------------
#    0   >0    -   FAIL           ran and passed without the fix — no red, a real defect
#    0    0    -   UNVERIFIABLE   exited clean having asserted nothing
#   !=0   -    1   UNVERIFIABLE   the module never imported; nothing was measured
#   !=0  >0    0   PASS           a test ran and failed without the fix — the genuine red
if [ "$LOAD_FAILED" -eq 1 ]; then
  echo "PDCA-UNVERIFIABLE: the red leg's test module failed to IMPORT, so no test ran and no red was established — this is NOT 'red without the fix'. The usual cause is a test that imports production API this patch ADDS, so reverting the fix removes the symbol it needs. Exercise the behaviour through pre-existing API, or record at sign-off why this slice has no isolable red"
  exit 77
fi
if [ "$TESTS_RAN" -eq 0 ]; then
  echo "PDCA-UNVERIFIABLE: 0 tests ran with the production change reverted, so no red could be established — this is NOT 'the test passes without the fix', the test never ran"
  exit 77
fi
if [ "$RED_RC" -eq 0 ]; then
  echo "PDCA-EVIDENCE: C4 FAIL — bundle test still green WITHOUT the fix, it does not capture the defect"
  exit 1
fi

echo "PDCA-EVIDENCE: C4 PASS — red without the fix, green with it"
