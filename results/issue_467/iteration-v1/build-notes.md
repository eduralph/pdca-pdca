# Build notes — issue 467 / split-children-inherit-release-metadata

## What changed and why

`split.py:986-1012` (`main`) built `gh issue create` with only `--repo`, `--title`,
`--body`, `--parent`. `file_children` (`split.py:1015-1093`) never read anything else off
the parent. So a split filed children with no milestone and no labels, breaking the
milestone count in both directions — exactly the observed getwyrd/wyrd defect the brief
describes.

Fix, three pieces, all in `template/src/pdca_harness/split.py`:

1. `_create_issue` (`split.py:986-1022` post-fix) gained two keyword-only parameters,
   `milestone: str = ""` and `labels: list[str] | None = None`, each appended to the argv
   only when truthy/non-empty — `--milestone <title>` once, `--label <name>` once per
   label (never comma-joined, so a name containing a comma or a space survives). Defaults
   mean `triage.py:530-535`'s five-positional-arg call is untouched, per the brief's
   out-of-scope note.

2. New `_parent_metadata(repo, parent_no, root)` (`split.py:1025-1061`) — the lookup. It
   mirrors `sources.tracker_issue_reopened` (`sources.py:150-176`), the peer callsite the
   brief cites: repo always explicit, non-zero exit ⇒ unknown, `json.loads` guarded, a
   non-object result (`null`, `[]`) ⇒ unknown, all via the SAME `subprocess`/`shutil` names
   `split.py` already patches for offline tests (`subprocess.run`, no new import). Returns
   `(milestone_title, label_names, ok)` — the third element is exactly the "could this be
   determined at all" bit, kept separate from "the parent genuinely has neither," which
   also produces `("", [], True)` and must NOT warn.

3. `file_children` (`split.py:1091-1114` post-fix) calls `_parent_metadata` once, only when
   `parent_no` is truthy (a parent with no number already files flat and has no issue to
   look up — brief's citation of `split.py:1035-1042`), before the `for child in children`
   loop. On `ok=False` it prints exactly one `advisory(...)` line to stderr, naming the
   parent number, and proceeds to file every child without the metadata. The lookup is
   NOT inside the per-child `try/except BaseException` — a lookup failure is not a filing
   failure, and nothing has been filed yet when it runs, so there is nothing to roll back
   or report as "already created."

## Alternatives ruled out

- **Per-child lookup** (call `gh issue view` inside the loop): rejected — criterion (d)
  requires exactly one lookup, and the parent's metadata cannot change mid-batch, so N
  lookups for one answer is pure waste and multiplies the number of places a warning could
  fire (criterion (d) says exactly one warning).
- **Comma-joining label names into one `--label` value**: rejected outright by criterion
  (b) — a label name may itself contain a comma or a space ("help wanted"), which a joined
  value would corrupt. Went with one `--label <name>` flag per label, matching how `gh`
  itself accepts repeated flags.
- **Catching `BaseException` in `_parent_metadata`**: rejected. `except Exception` lets a
  genuine `KeyboardInterrupt` during the lookup propagate immediately, before anything is
  filed — consistent with the existing `_create_issue`/`file_children` split.py convention
  of treating Ctrl-C as an ordinary operator action distinct from an ordinary error, and
  cheaper than adding a new interrupt-handling branch before the loop even starts (nothing
  has been filed yet, so there's nothing to report).
- **A brand-new subprocess-calling seam** (e.g., importing `sources._run_capture`):
  rejected — `split.py` already patches `pdca_harness.split.subprocess` directly (its own
  module-level name, not `sources`'s), and the existing tests patch exactly that name
  (`test_split.py:690-694`). Importing `sources._run_capture` would call through
  `sources.subprocess`, a DIFFERENT patched name, so every existing offline fake would stop
  intercepting the lookup and the test suite would try to shell out to a real `gh`. Wrote
  the `subprocess.run(...)` call directly in `split.py`, exactly as `_create_issue` already
  does, keeping the single patched seam.

## Fake `gh` updates (sanctioned in scope)

The brief flagged that adding one `gh issue view` call before the filing loop shifts every
call-count-based index in the existing fakes. Added one module-level helper to
`test_split.py` (`_is_metadata_lookup`, plus a shared `_NO_PARENT_METADATA` no-metadata
response) and used it to make each listed fake recognise-and-skip the lookup call before
its existing counting/indexing logic runs, rather than weakening or deleting any existing
assertion:

- `_gh` (`test_split.py`, `FilingChildIssues`, was 666-688)
- `_run_returning` (`CodexReviewHardening`, was 1035-1039) — needed because
  `test_the_command_is_an_argv_list_so_the_shell_never_sees_it` indexes `self.calls[0]`,
  which would otherwise be the lookup call, not the create call carrying the shell-escape
  payload under test.
- the inline `run` fakes in `test_an_unexpected_exception_still_names_what_was_filed`
  (was :1068), `CodexRound4.test_the_recovery_command_uses_the_installed_program_name`
  (was :1342), `TheWholeChainUnmocked._fake_gh` (was :1401),
  `test_a_gh_failure_midway_names_the_issue_it_already_filed` (was :1457), and three of the
  four `IrreversibleStateIsNeverLost` fakes (was :1675, :1694, :1715) — each uses a
  call-count trigger (`n == 2`, etc.) to fire a specific failure on a specific child, and an
  unfiltered lookup call would shift that trigger onto the wrong (or no) child.

**Not changed, deliberately:**
- `test_split.py`'s `IrreversibleStateIsNeverLost.test_ctrl_c_stays_an_interrupt` (was
  :1734) — its fake raises `KeyboardInterrupt` unconditionally for every call, with no
  call-count logic and no assertion on which call raised it. Filtering the lookup out of
  this one would remove the only call that raises anything before the loop, which is not
  its purpose (it deliberately doesn't care which `gh` subcommand caused the interrupt).
  Verified it still passes as-is (see red→green run below).
- `test_split_stub_guard.py`'s `_gh` (:69-77) — read it and traced every call site: it is
  reachable only through `_patched()`, used by exactly two tests, both of which assert
  `self.calls == []` because the stub-guard refuses filing (and therefore any `gh` call,
  lookup included) before `can_file` is even consulted. The fake is never actually invoked
  in this file, so there is nothing for the new lookup to shift. Left it untouched rather
  than editing dead code.

## Test file

`template/tests/test_split_child_metadata.py` (new), 11 tests, `ChildrenInheritParentMetadata`,
fixture mirrors `test_split.py:638-662`'s `FilingChildIssues` (repro instruction). Covers:
- (a)+(b): milestone title and label names reach every child, one `--label` per name.
- (c): `{}` (no milestone, no labels) produces argv byte-identical in *shape* to pre-fix
  (`--repo`, `--title`, `--body`, `--parent` only). Also covers `{"milestone": null,
  "labels": []}` — the shape `gh` actually returns for an issue with a milestone-key but no
  milestone set.
- (d): the lookup happens exactly once, before any create call; a non-zero exit, a raised
  exception, a non-object JSON result (`null`), and unparseable output all still file every
  child and print exactly one warning line.
- (e): the `--ids` path (`split.accept`) and a non-GitHub tracker never call `gh` at all —
  asserted with a fake that raises `AssertionError` if invoked.
- (f): id-list length and metadata-on-every-call are asserted TOGETHER in one test, so a
  regression that inherited metadata for only the first child (or silently dropped a child
  to keep indices aligned) cannot pass.

## Refutation (forced questions)

**(a) Genuine red?** Yes. Set aside `split.py` and `test_split.py`'s changes with
`git stash push -u` (leaving the new test file in place, since it targets pre-existing
`split.parse`/`split.file_children` API only) and ran
`PYTHONPATH=src python3 -m unittest tests.test_split_child_metadata -v` from `template/`:
7 of 11 tests failed — exactly the ones asserting `--milestone`/`--label` presence, the
once-only lookup, and the warning on a failed lookup. The other 4 (argv-shape-with-no-
metadata, the two "no lookup" tests, and the missing-milestone-key test) passed even
pre-fix, since they assert the ABSENCE of something the old code also never added — that's
expected and correct, not a weak test. Then restored the fix (`git stash apply` + `git
stash drop` on the correct stash index) and reran the full offline suite: 1799 tests, OK.

**(b) Production path?** Yes. Every test calls `split.file_children` / `split.accept`
directly — the real functions the patch changes — with only `pdca_harness.split.subprocess`
and `pdca_harness.split.shutil` replaced (the same two names `test_split.py`'s own fixture
patches), never a copy or reimplementation of the filing logic.

**(c) Fixture includes the fault?** Yes. The fixture is a two-child real proposal
(`_proposal(_ONE, _TWO_INDEP)`) filed against a `github` tracker with an explicit numeric
parent (`issue_500`) — the exact shape that triggers the lookup. The failing-lookup tests
inject the actual fault modes named in criterion (d): a non-zero exit, a raised exception,
and non-JSON/non-object output, each routed through the same fake `gh` the create calls
use, not a hand-picked "healthy" fixture that excludes them.

## Full suite run

`cd template && PYTHONPATH=src python3 -m unittest discover -s tests` (the runner named in
`CONTRIBUTING.md`): **1799 tests, OK (skipped=2)** — both before this change (skips are
pre-existing/unrelated — the root-suite copier cases that need a separate entry point) and
after, confirming no regression across the rest of the harness.

## Formatter / commit hooks

No `pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml`, or `.git/hooks/*`
(besides samples) exist in this checkout — `CONTRIBUTING.md`'s only commit-time requirement
is a DCO `Signed-off-by:` trailer (`git commit -s`), which is a per-commit human action at
publish time, not something to run here. Nothing to format-check.

## Scope notes

- Did not implement the out-of-scope "milestone the tracker rejects at create time"
  handling (e.g. a closed milestone) — the brief says this is optional and not required. It
  is NOT cheap to do safely: distinguishing "milestone rejected" from any other
  `gh issue create` failure would mean parsing `gh`'s stderr text for a specific phrase (no
  structured exit code for "unknown/closed milestone" exists), which is exactly the kind of
  brittle string-matching the rest of `split.py` avoids for real failures. Left the existing
  behavior: a rejected milestone fails that child's `gh issue create` like any other `gh`
  failure, reported through the existing partial-filing path (`split.py:1102-1136` region),
  which is `UncertainFiling`/`SplitError` — the same architecture as any other `gh` error.
- `assignees` was not touched, per the brief's explicit out-of-scope note.
