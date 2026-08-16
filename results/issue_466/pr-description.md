## Summary
**User impact:** A fresh instance starts with the splitter running offline, where
`pdca split <id>` writes a *placeholder* proposal — two invented children literally
named `stub-child-one` and `stub-child-two`. Accepting it filed those placeholders as
real issues on the tracker: permanent sub-issues of your bundle's own issue, titled
after the fixture text, plus local bundles seeded from the same text. Nothing in the
run said the proposal was a placeholder, and tracker issues cannot be withdrawn — so
anyone who tried `split` before switching the splitter on had to close the issues and
delete the bundles by hand. It has happened for real: `getwyrd/wyrd#708` and `#709` are
still open as sub-issues of `#682` with exactly those names.

This change makes a placeholder proposal recognisable and makes `--accept` refuse to
file one, so the offline mode can be explored without leaving marks on a tracker.

Reported in [#466](https://github.com/eduralph/pdca-harness/issues/466).

## What to look at
Three small, connected pieces: the offline splitter now stamps the proposal it writes
as a placeholder; `pdca split <id>` says out loud, while it runs, that it wrote one; and
`pdca split <id> --accept` stops with a non-zero exit and an explanation naming the
remedy (`[leaves.splitter] mode = "command"`) instead of filing. Accepting with `--ids`
is untouched — that path files nothing, and the operator supplied real issue numbers
deliberately, so the documented offline round-trip still works end to end.

To try it, in an instance with `[leaves.splitter] mode = "stub"` and `gh` available:
run `pdca split <id>` (note the new stderr line and the marker at the top of
`split-proposal.md`), then `pdca split <id> --accept` — before this change it created
tracker issues; now it refuses and files nothing. Then repeat with
`--accept --ids <a>,<b>` and confirm that path behaves exactly as it did before.

## Root cause
The offline stub wrote a proposal that was byte-identical in *shape* to a real
splitter's — same `<!-- pdca:split-proposal v1 -->` header, same child delimiters — so
no fact on disk recorded where it came from, and `--accept` runs as a separate
invocation from `do_split`, where an in-memory flag could not have reached it
(`template/src/pdca_harness/leaves.py:1594-1602` and `:1605-1631` on `main`). Every
check on the filing path asked a different question: `preflight` checks structure only
and `can_file` (`template/src/pdca_harness/split.py:912-928`) asks merely whether the
tracker is reachable, never whether the proposal is fit to file — so the placeholder
passed all of them and `child_title` (`:939-`) then used the fixture slug as the issue
title verbatim.

## Fix
Two sides, because the two facts live in different processes:

- `leaves._stub_split` writes a second marker, `<!-- pdca:split-proposal-stub -->`,
  into the proposal itself, and `split.is_stub_proposal(text)` — a pure text predicate,
  next to the existing proposal parsing — reads it back. Provenance now survives the
  process boundary, and it is not a slug-name sniff: any placeholder carrying the marker
  is caught, not just this fixture's wording.
- `cli._split` keeps the proposal text alive past `split.parse` and, inside the `if not
  ids:` filing branch only, refuses a marked proposal *before* `split.can_file` is
  consulted and before any `gh issue create` — via `split.advisory(...)` plus a non-zero
  return, the same shape as the neighbouring `TrackerUnavailable` handler, never a raise
  into the CLI. The `--ids` branch is not touched.
- `leaves.do_split` prints the stub notice on stderr on the branch that chooses the
  stub, so a real splitter run never carries a message saying the opposite.

## Verification
- **Claim:** a stub-produced `split-proposal.md` is self-identifying on disk, readable by
  a process that never saw `do_split` run.
  **Checked:** `template/src/pdca_harness/leaves.py:1605-1631` on `main` — the placeholder
  carried only the same `v1` header a real proposal has; the new marker is written by the
  stub itself and read back through `split.is_stub_proposal`.
- **Claim:** `--accept` refuses a marked proposal before anything irreversible, naming the
  cause and the remedy, and exits non-zero without creating a child bundle or marking the
  parent split.
  **Checked:** `template/src/pdca_harness/cli.py:777-792` on `main` — the `if not ids:`
  branch went straight into `split.file_children`; the refusal is inserted ahead of it,
  before `split.can_file` (`template/src/pdca_harness/split.py:912-928`) is consulted.
- **Claim:** with the tracker reported *reachable*, no `gh issue create` runs at all — the
  failure worth locking is a refusal that filed the first child before erroring.
  **Checked:** asserted on the absence of the recorded argv, not on the exit code, with
  `can_file` forced to `(True, "acme/widgets")`.
- **Claim:** `--ids` still accepts a marked proposal unchanged, so the offline round-trip
  documented for a tracker the driver cannot reach keeps working.
  **Checked:** `template/src/pdca_harness/cli.py:749-755` and `:798-799` on `main` — ids
  supplied on the command line skip the filing branch entirely and go straight to
  `split.accept`, so the guard is not on their path; those lines are unchanged.
- **Test:** `template/tests/test_split_stub_guard.py` (new) — fails pre-fix, passes
  post-fix. With the production changes reverted and only the test kept, 4 of its 6 cases
  fail (a genuine failure, not an import error); with the fix applied, all 6 pass. It
  drives the real `leaves.do_split` and `cli._split` with only `gh` replaced by a
  recording fake, reusing `template/tests/test_split.py`'s harness. The full offline
  suite is green: 1764 tests, 2 skipped.

Fixes #466
