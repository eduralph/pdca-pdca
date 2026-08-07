## Summary
**User impact:** Every cycle ends with the same item waiting on the human's sign-off
checklist, and nobody can do anything about it. The contribution check is reported as a
green pass, but the reviewer cannot confirm it — the files that check reads are not
written until later in the cycle — so the reviewer marks the row unconfirmed and it lands
in the "needs human" list. It fired on all 9 of the last 9 completed cycles and was
cleared unread every time, which slowly teaches the human to tick that list without
reading it — and that list is the last human guard before a fix is accepted.

This change lets a check that runs before its subject exists say so: the row is now
recorded as *deferred — the real audit runs at publish* instead of a green nobody can
reproduce, and it no longer asks the human to clear anything. The audit itself is
unchanged and still has to pass before anything is pushed.

Reported in [#401](https://github.com/eduralph/pdca-harness/issues/401).

## What to look at
The change adds a fourth value to the small vocabulary a gate row can record —
`pass` / `fail` / `unverifiable` / `deferred` / `none` — and one rule about who may use
it: a row may only defer if something genuinely re-runs it later, so "deferred" is a
hand-off to a named later check, never a way to skip one. Everything else about the
contribution check is untouched.

To try it: take a bundle that has a `patch.diff` but no `pr-description.md` yet (any
bundle at Check time), run the gates, and read `check-gates.md` — the contribution row
now reads `deferred` with the reason "not drafted yet — the substantive T4 audit runs at
publish" instead of a bare `pass`, and `SUMMARY.md` §6 no longer carries an item for it.
Draft the two artifacts and re-run: the row records the substantive `pass` (or `fail`)
exactly as before.

Best read in the order the review trail below lists: the checker's declaration, the
classifier that recognises it, the guard that restricts who may declare it, then the
docs. It builds on the marker rules in #431 and #432 and reuses their single declaration
parser, so it is easiest to merge after those two.

## Root cause
The T4 contribution row is bundle-scoped and default-open before the publish artifacts
exist: at Check time `commit-msg.txt` and `pr-description.md` have not been drafted, so
`cli._contribcheck` returned a bare `0` with nothing linted, and the matrix recorded that
non-event as a `pass` with an empty evidence string. The layering is deliberate — the
substantive audit happens at publish (`publish._t4_passes`) — but the result vocabulary
had no way to express "ran, found nothing to audit yet", so the only channel for the
reviewer's honest "I cannot reproduce this green" was §6 NEEDS-HUMAN, which is exactly
where a by-design condition must not go.

## Fix
`deferred` becomes a member of the gate-result vocabulary, declared by the gate itself in
the same family as `PDCA-UNVERIFIABLE:`:

- `cli._contribcheck` prints `PDCA-DEFERRED: <reason>` on its default-open path and still
  exits 0 (`cli.py:1088-1094`); no caller has to learn a new exit code.
- `gates._classify` recognises the declaration and returns `("deferred", [reason])`
  (`gates.py:706,761-768`) — on exit **0** only (77 stays the `unverifiable` channel), and
  `unverifiable` wins when a gate declares both, because that is the channel that stops
  for a human.
- `gates._deferrable` (`gates.py:690-703`) is the guard: it delegates the selection to
  `publish.publish_gates` (`publish.py:668-710`), so only a row publish genuinely re-runs
  may defer, and what may defer can never drift from what is actually re-gated. It
  defaults to `False`, so a caller that does not assert the re-gate cannot get a
  `deferred` out of `_classify`.
- `overall`, the matrix render and the §6 lift needed no behavioural edit — `overall`
  counts gating `fail` only (`gates.py:789`), the matrix renders result + reason
  generically (`gates.py:878-883`), and the §6 lift filters on `unverifiable`
  (`assemble.py:376-380`). Adding a `deferred` branch to any of the three would have been
  dead code that only looks like the feature, so each is instead pinned by a test and its
  intent recorded where a future reader would otherwise "fix" it.
- The written contract follows the code: the result vocabulary and an upgrade note
  (`04-validation-tooling.md:67,69,71`), a new rule C5b (`06-quality-cycle-guidelines.md
  :230-234`), the glossary (`08-glossary.md:157-163`), the reviewer's contract
  (`template/agents/reviewer.md.jinja:68-76` and the driver-side review prompt,
  `leaves.py:1486-1491`), and the registration comment that used to promise "default-open
  … so Check-time gates pass" (`template/pdca.toml.jinja:922-927`).

`publish` is deliberately untouched: `_t4_passes`, `publish_gates` and the `--no-issue`
relax branch are not edited.

Known follow-up, not fixed here: the `gates.py` module docstring still calls
`PDCA-UNVERIFIABLE` "the one marker that can change a `result`" (`gates.py:38`) — stale
now, and a one-sentence fix best made where the surrounding text is being rewritten
anyway.

## Verification
All `path:line` are on this branch (target `main`); tests are
`template/tests/test_gate_deferred.py` (new, 17 tests) unless noted.

- **Claim:** a Check-time contribution row on a bundle with `patch.diff` and no
  `pr-description.md` records `deferred` — not `pass`, not `unverifiable`.
  **Checked:** `template/src/pdca_harness/cli.py:1088-1094` (the checker declares it) →
  `template/src/pdca_harness/gates.py:98` (marker), `:706,761-768` (classification).
  **Test:** `test_check_time_row_with_a_patch_and_no_pr_body_is_deferred` — drives the
  real gate runner over a real bundle directory with the real checker as the gate command
  in a subprocess. Fails pre-fix (`AssertionError: 'pass' != 'deferred'`), passes post-fix.
- **Claim:** a deferred row is neither a green nor a gating failure.
  **Checked:** `gates.py:786-790` — `overall` is computed from gating `fail` alone.
  **Test:** `test_deferred_does_not_count_toward_overall`.
- **Claim:** it is not lifted into `SUMMARY.md` §6, and the accept-guard is not blocked —
  while `unverifiable` still is.
  **Checked:** `assemble.py:361-380` — the lift filters on `unverifiable`; the deliberate
  difference is documented in place.
  **Test:** `test_no_needs_human_item_and_accept_is_not_blocked` (runs the real summary
  assembly and the real accept-guard) with `test_an_unverifiable_row_still_reaches_section_6`
  as the control.
- **Claim:** what is owed at publish stays visible to the human.
  **Checked:** `gates.py:878-883` (matrix row) and `assemble.py` §5 evidence lines.
  **Tests:** `test_the_matrix_shows_deferred_with_its_reason`,
  `test_the_row_is_still_visible_in_section_5_with_its_reason`.
- **Claim:** a row nothing re-gates cannot defer itself out of scrutiny.
  **Checked:** `gates.py:690-703` (`_deferrable` → `publish.publish_gates`,
  `publish.py:668-710`), wired at `gates.py:544-547,568`.
  **Tests:** `test_a_row_nothing_re_gates_keeps_its_pass`,
  `test_a_c4_row_cannot_defer_itself_out_of_scrutiny`.
- **Claim:** nothing else changes — drafted artifacts still record the substantive
  `pass`/`fail`, a non-zero exit still fails whatever it printed, a relayed marker is
  still not a declaration, and publish still hard-gates the row before any push.
  **Tests:** `test_drafted_artifacts_still_record_the_substantive_pass` / `…_fail`,
  `test_a_non_zero_exit_fails_whatever_it_declared`,
  `test_a_relayed_marker_is_not_a_declaration`,
  `test_unverifiable_wins_when_a_gate_declares_both`,
  `test_a_close_bundle_with_no_patch_still_just_passes`,
  `test_publish_still_hard_gates_the_row_before_any_push`.
- **Claim:** the existing assertion that encoded the old silent default-open behaviour is
  brought into step.
  **Checked / test:** `template/tests/test_publish_slice.py:913-927` —
  `test_default_open_before_artifacts_are_drafted` now asserts the declaration; the exit
  code is unchanged. Fails pre-fix, passes post-fix.
- **Suites:** offline driver suite green (1526 tests, 2 skipped) plus the render and
  update-compatibility suite; docs lint and the site link audit clean (22 pages).

Fixes #401
