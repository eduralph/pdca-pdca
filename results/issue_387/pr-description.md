# PR description

## Summary
**User impact:** a project's per-fix verification check could test a change against a
different branch from the one the tool later opens the pull request against. When the
two disagreed, the check either rejected a perfectly good change ("this no longer
applies — it's stale") or reported a clean pass on a branch that was missing the work
the change builds on, so the pass proved nothing. It hit precisely the setups that most
need the branch to be right: stacked slices, batched dependent work, and any project
whose base branch is not the default one. Some setups landed on a branch name that
cannot exist at all (`origin/origin/main`), and the check just failed.

The cause was that the harness asked every project to work the branch out for itself by
re-reading the plan document, and the reading rule is subtle enough that it has been got
wrong repeatedly. This PR has the harness hand the check the already-resolved branch
instead, computed by the same single piece of code the publishing step uses, so the two
can no longer disagree.

Reported in [#387](https://github.com/eduralph/pdca-harness/issues/387).

## What to look at
Two small things. First, `template/engine/scripts/run-verify.sh` — the checked-in
skeleton each project fills in — now ends its list of "which branch to test against"
with a variable the driver actually sets (`$PDCA_BRIEF_BASE`), rather than telling the
project to parse the plan document itself. Second, the driver now sets exactly one such
variable on every per-bundle check run, always as a complete `<remote>/<branch>` name,
so a script can use whichever one is present without any further work.

To try it: point a check command at `printf '%s\n' "${PDCA_BRIEF_BASE-UNSET}"` and run
it over a bundle whose target line reads ``owner/repo @ main (feature branch
`feat/x-slice`)`` — before this change nothing was exported and every project
hand-rolled the answer (mostly getting `feat/x-slice`); after it, the value is
`origin/main`, the same branch the pull request will target. Or run the suite:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_verify_base`.

## Root cause
The base-resolution ladder published to gate scripts
(`template/engine/scripts/run-verify.sh:25-27` on main) ends in "the brief's
`Repo + branch target` > origin/<default>", but the driver exported only its first two
rungs (`template/src/pdca_harness/gates.py:471` and `:476` on main) and shipped no
accessor a gate could call for the last one — the anchored parse lived in
`publish._clean_ref` (`template/src/pdca_harness/publish.py:531-545`), reachable only
from Python (`git grep -n _clean_ref origin/main` → `publish.py:531,553,559`). So each
instance re-implemented that parse in shell from a comment that stated the precedence
but not the rule, and inherited the pre-#235 unanchored version: one parse, two
languages, two answers.

## Fix
- `brief._clean_ref` / `brief.repo_target` / `brief.base_branch` (new,
  `template/src/pdca_harness/brief.py:299-345`): the parse moves verbatim next to the
  other per-field accessors (`test_files`, `depends_on`, `onto_branch`) and gains a
  public accessor for the brief's own base, with the project default branch as fallback.
- `publish._resolve_target` (`publish.py:531-544`) now calls `brief.repo_target`;
  `publish._clean_ref` is **deleted**, not aliased or re-exported — a second name for one
  implementation is what invites the next copy. Resolved values are unchanged.
- `gates._run_one` (`gates.py:468-495`) gains the third rung *inside* the existing
  mutually-exclusive chain: `Onto branch` → `PDCA_BASE`; else a wave stack-base marker →
  `PDCA_VERIFY_BASE`; else `PDCA_BRIEF_BASE = <cfg.base_remote>/<brief base or default>`.
  Exactly one is set for every bundle-scoped gate invocation — previously the ordinary
  bundle got none. `cfg` becomes a required keyword on `_run_one` (all three call sites
  already had it: `gates.py:355`, `:384`, `publish.py:840`); required rather than
  optional, since an optional one silently restores the hole for any caller that forgets.
- `run-verify.sh:15-34`: the published ladder now terminates in `$PDCA_BRIEF_BASE`,
  states that all three variables are already fully-qualified refs (never `origin/$VAR`,
  which doubles the remote), and says explicitly not to re-derive the parse in shell.

## Verification
- **Claim:** the ladder's last rung is published to every instance but never supplied by
  the driver. **Checked:** `template/engine/scripts/run-verify.sh:25-27` on main (the
  ladder text) against `template/src/pdca_harness/gates.py:450-476` on main — only
  `PDCA_BASE` (`:471`) and `PDCA_VERIFY_BASE` (`:476`) are exported, and the `else` branch
  for an ordinary bundle exports nothing.
- **Claim:** the resolved base equals the ref publish commits against, on the configured
  remote. **Checked:** `template/src/pdca_harness/publish.py:244` on main —
  `checkout_base = f"{base_remote}/{base}"`; the new export composes `cfg.base_remote`
  for the same reason, since `base_remote` defaults to `upstream` under the fork model
  (`template/src/pdca_harness/config.py:122`). A literal `origin/` would have shipped a
  fresh divergence in the commit that closes one.
- **Claim:** publish's own behaviour is untouched, so the #25/#235/#262 regressions stay
  fixed. **Checked:** `template/tests/test_publish_slice.py:422-472` on main (the
  backticks-and-prose, parenthetical-base and trailing-aside cases) pass unmodified
  against the refactored `_resolve_target`.
- **Test:** `template/tests/test_verify_base.py` — 9 cases appended to the existing
  module (19 total), each driving `gates.run_gates` with a **real** gate command that
  records the three variables as the gate process actually received them: the export for
  an ordinary bundle; the anchored-parse pair (``… @ main (feature branch
  `feat/x-slice`)`` → `origin/main`; `` … @ `feat/x` `` → `origin/feat/x`); no
  target field → the project default branch; `<remote>/<branch>` shape on a configured
  `base_remote = "upstream"`; agreement with `publish._resolve_target` over four field
  styles (the one-implementation invariant, asserted as an equality between the two
  consumers); each higher rung suppressing this one; exactly-one-of-three over all four
  `(onto, marker)` combinations; and the skeleton's ladder text. Fails pre-fix — with the
  production hunks reverted and the tests kept, 11 cases fail on `PDCA_BRIEF_BASE=UNSET`
  — and passes post-fix (19 tests OK). Full offline driver suite: 1478 tests OK
  (2 skipped); template render/update suite: 7 tests OK; `bash -n` on the skeleton parses.

Fixes #387
