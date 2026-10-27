# Build notes — #738: hold a bundle whose own base cannot be built

Base: `pdca-integration/main-r547f8028520f` at `75a886e` (the worktree's HEAD). "base:N" below is
a line on `75a886e`; "now:N" is the same spot with `patch.diff` applied.

## What changed and why

**The stop is gone.** `_bundle_bases` re-raised every `IntegrationError` from a base build
(flow.py base:1019-1022) and the wave loop printed `STOPPING` and `break` (base:2759-2770).
Now `_bundle_bases` takes a `held` dict (now:1019), records the error under the bundle's name
and moves on (now:1045-1046), and skips pointing a held bundle (now:1049-1050). The wave loop
(now:2853-2871) prints one line per hold (`_announce_base_holds`, now:1063), adds the bundle
to `held_base` (declared now:2772, the peer of `held_unpushed` base:2584), drops it from
`runnable`, and goes on. If every runnable bundle of a wave was held, the wave is skipped
(`if not runnable: continue`, now:2870): nothing new was accepted, so there is nothing to
drive, publish or fold.

**Hold line = cause + fix.** The line is `flow: <B> held — could not build <B>'s own base
from <members>: <the error>. <B> is not built this run; bundles that depend on it or are its
`Conflicts with` partners are held with it, and the rest of the run goes on.` The cause and
fix come from where the cause is raised (integrate.py):
- moved base: `_member_clash` already says "Rebuild issue_A's branch on the new origin/main
  …, then re-run" (unchanged).
- rewrite: `_rewrite_stop(…, onto=…)` already gives the restore/re-publish remedy
  (unchanged).
- fetch: `_fetch`'s own message ("… the fold cannot see the branches it merges") has no fix
  and is wrong for a base build. I wrapped the one `_prepare_worktree` call in
  `build_bundle_base` (base:835 → now:848-855): "<cause>, so <branch> cannot be built —
  nothing was merged or pushed. Check that remote (its URL, the network, credentials) and
  that checkout, then re-run". No "rebuild" in it, as case (3) requires.
- push refused: the existing refusal (base:870-881, now:892-903) is kept as is.
- `checkout -B` failure (base:853) had no fix at all; now "… a git step failed: check that
  checkout, then re-run" (now:874-875).

**`Conflicts with` partners (v1 hole 1).** `_runnable` gets `unbuilt` (now:690), intersected
with the bundle's `Conflicts with` partners (now:769-771) exactly as `unpushed`/`conflict_held`
are (base:758-762), its own stderr line (now:863-871), and the runnable test includes it
(now:872-874). The wave loop passes `unbuilt=held_base` and computes `conflicts` when
`held_base` is non-empty (now:2793-2805; base:2702-2713). `held_base` is also added to
`held=` — dead for prerequisites today (a held bundle is never COMPLETE, so it is already
"not ready"), but it is the set the brief says `_runnable` must honour, and it costs one
token.

**Stale line after a rewrite hold (v1 hole 4).** A rewrite refusal is made before the wave's
other bundles are pointed, so it cannot name a seam cut from the line afterwards. `_Rewritten`
now carries `ref`, `lost` (the heads the branch lost) and `prs` (the PR owners its message
named) (integrate.py now:128-142, raised now:863-865). After the wave's bases,
`_built_on_lost_heads` (flow.py now:1074) names each bundle of the wave pointed at the line
(`line_cut`: "issue_S is cut from <line> at <tip>, which holds <head> from issue_A's branch
…") or at a base of its own (`bases_took`) that holds one of `lost`, with the fix
("Restore <ref> to <head> … or rebuild <S>'s PR on the rewritten branch before it merges").
The rewritten member is still excluded from the end-of-run check, as the brief requires
(`base_rewrites` replaces `stop_named`, set now:2861-2865, declared now:2777, read at
now:3015; base:2688/2769/2914).

**Exit code.** `cli._results_rc` (cli.py base:701) gets `_HELD_UNBUILT = "base"` (now:702):
a bundle held under "base" is PLANNED but does not count as a failure (now:736-738), so a
run whose only problem is a base hold exits 3. A dependent left PLANNED (case 7) or a
held `Conflicts with` partner (case 5) is not in `holds`, so the run exits 1 (decision 3).
`_drive_and_act` writes `"base"` for `held_base` (now:3027).

### Judgment calls the human should check

1. **When a rewrite hold fails the run.** The brief says (1)-(4) exit 3, including case (2)
   (rewrite, nothing else holds the old commits but the line) — so v1's "always add
   `A: rewritten`" is out. I fail the run (A → `"rewritten"`, exit 1) only when **a PR of the
   run** holds the lost commits: either the hold's own message named one (`exc.prs`), or a
   bundle built after the hold does (`_built_on_lost_heads`). That is #695/#727's rule ("a PR
   holds commits the branch no longer has" fails the run). The line alone holding them is a
   hold (exit 3). Recorded at flow.py now:2773-2778, 2864-2865 and 3018-3028.
2. **Four existing tests asserted the old `STOPPING`.** The brief's "existing suites stay
   green" can only mean "green with the patch": these tests pin the exact behaviour the
   brief removes. I changed each one to the new behaviour and kept every content check:
   - `test_flow_dependency_scoped_bases.py:503` (renamed `…_holds_its_bundle_naming_each_base_and_pr`):
     the hold line carries all the same parts; adds `holds == {"D": "base", "A": "rewritten"}`
     (PRs S, B, C hold the lost head → exit 1, per point 1).
   - `test_flow_dependency_scoped_bases.py:525` (renamed `…_cannot_be_built_for_a_clash_…`):
     holds gains `"C": "base"`.
   - `test_integrate_carried_rewrite_late.py:298` (1d): B held; **rc 1 → 3**. This is the
     brief's case (2) exactly (rewrite after the line's fold, B's base refuses it, no PR holds
     the old commits). It is the one assertion I weakened in rc terms; it follows the
     brief's explicit "(1)-(4) exit 3".
   - `test_integrate_carried_rewrite_late.py:355` (1e): B held, line also says "then re-run";
     rc stays 1 (the end check could not fetch: "unchecked").
   - helper `_stopped_at_b` → `_held_at_b` (`:208`), module docstring (`:34-38`).
3. **Every `IntegrationError` from a base build is held**, `IntegrationTreeError` included
   (v1 did the same). A broken integration worktree cannot cause a bad push: the next base
   build resets it first (`_reset_tree`, integrate.py now:872) and the next fold does too, and
   a fold that cannot reset it raises and stops the run there. So the worst case is a wave
   of holds followed by a stop at the fold, not wrong output.
4. **Case (6b), beyond the brief.** `_built_on_lost_heads` also names a bundle whose own base
   was built *before* the rewrite in the same wave (base builds of a wave run one after the
   other). Without this, holding instead of stopping would let that bundle publish stale
   commits unnamed — a regression of a race the old stop covered. I added
   `test_a_base_built_before_the_rewrite_in_the_same_wave_is_named` for it.

### Out of scope, still true after this patch

- Case (1) holds only because B's wave is the last. With a later wave, W (built on the moved
  `main`) clashes with A at the next fold and the run stops there — that is #739.
- integrate.py's module docstring still describes the pre-#727 line model; docs, glossary
  and vendored spec are #740.
- Carried-from-an-earlier-run prerequisites as base members: #735. v1's substitute tests 2a
  and 5 are not carried over.

## Alternatives considered

- **Name S by dropping the late-check exclusion** (1 line: remove the `base_rewrites`
  filter at now:3015). Rejected on the brief, not cost: the brief keeps the exclusion, and
  without it case (2)'s end check reports the line's lost head as `"rewritten"` → exit 1,
  contradicting "(1)-(4) exit 3", and the rewrite is printed twice.
- **Hold S instead of naming it.** Rejected: S declares `Stacks on: A`, not `Depends on`/
  `Conflicts with: B`; the invariant says hold "nothing else".
- **Fix the fetch wording inside `_fetch`** (1 line instead of a 7-line wrapper). Rejected:
  `test_integrate_carried_rewrite_late.py:543-544` pins `_fetch`'s message word for word for
  the fold, and "the fold cannot see the branches it merges" is correct there.
- **Compute "lost head" in flow by re-reading git** instead of carrying it on `_Rewritten`.
  Rejected: needs a fetch + ancestry check per seam (a new git round trip and a new failure
  mode); the build already knows the lost heads, three attributes carry them.

## Refute-your-own-test (forced)

- **(a) Genuine red? Yes.** Ran the project's C4 gate, `engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set. Green leg: 25 + 15 + 8 tests OK. Red leg (production
  hunks reverted, tests kept): all 8 new cases FAIL (each a real assertion failure on
  `STOPPING` / the unrelated bundle not COMPLETE — no import failure), plus the 4 updated
  ones. Verdict `PDCA-EVIDENCE: C4 PASS`. Before writing any production code I also ran the
  new file on the untouched tree: 7/7 failed, each on `'STOPPING' unexpectedly found`.
  Separately I disabled each hole fix alone: passing `unbuilt=frozenset()` turns only case
  (5) red; skipping `_built_on_lost_heads`' loop turns only (6) and (6b) red.
- **(b) Production path? Yes.** The tests call `flow._drive_and_act` and `cli._results_rc`;
  `integrate.build_bundle_base`, `_bundle_bases`, `_runnable`, `integrate.fold` and every git
  step run for real against a bare origin. Stubbed: the build/sign-off leaves, publish's
  mechanics (cut + push, done with real git), `gh`, and — for one bundle only — the fetch
  (the real `_prepare_worktree` runs with its `git fetch` failing, so the error is the real
  `_fetch` one) and the push of that bundle's base branch (the `integrate._git` push of that
  one branch returns 1, so `build_bundle_base`'s own refusal at now:902 fires). No stub
  touches the `except` the fix adds.
- **(c) Fixture includes the fault? Yes.** Case (1) pushes a clashing `a.txt` to the real
  `main` after the real fold; (2)/(6)/(6b) force-push the real `fix/A` after the line (or B's
  base) took it, and (6)/(6b) assert from git that S's / B's published head contains the lost
  commit; (3)/(4) fail the real git step for B only, while W, Z, A run unstubbed in the same
  run. The unrelated bundle W is in every case and must reach COMPLETE.

## Commit-readiness

The target has no formatter, linter or commit hook configured (no `.pre-commit-config`, no
ruff/black/flake8 config, no hooks in `.git/hooks` or `core.hooksPath`); CONTRIBUTING.md asks
only for the DCO sign-off (publish adds it) and green suites. Every added line is ≤ 100
columns (the file's style), and all touched files parse.

## Suite runs

- Brief's named suites + the new file + `test_integrate_carried_rewrite_late`: 168 tests OK.
- Full offline driver suite before updating the four old tests: 2601 run, exactly those four
  failed (all asserting `STOPPING` on a base failure).
- T3 (`engine/scripts/run-suite.sh`, both suites) after the update: root suite 24 tests OK,
  driver suite 2602 OK (2 skipped) — `PDCA-EVIDENCE: root suite OK, driver suite OK`.
- After that I changed one message (a seam is now "is cut from <line>", an own base "is built
  on its own base <branch>") and the two assertions on it. Re-ran: C4 gate PASS again (green
  25/15/8 OK; red 2/2/8 failures), full driver suite 2602 OK. The root suite does not read
  flow messages, so I did not re-run it for a string change.

## Housekeeping slips (mine)

- I redirected the first full-suite run's output to `/tmp/pdca738-driver-suite.log`, outside
  the two roots I may write to. It holds only test output. I did not delete it (no `rm`).
- A mutation check left an untracked backup, `template/src/pdca_harness/flow.py.orig738`, in
  the worktree (my `mv` to `/dev/null` failed). It is the patched `flow.py` before the last
  message tweak, is not in `patch.diff`, and unittest discovery ignores it (not a `.py`
  file). The harness reclaims the worktree.
