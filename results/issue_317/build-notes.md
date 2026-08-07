# Build notes — issue 317 / pdca-record

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l0`, base
`710ec54`). All `path:line` cites below are against that tree with the patch applied
(pre-patch cites are marked).

## What was built

A `pdca record [<ids>…]` verb that commits terminal-finished result bundles to the
instance repo as one batch commit, with an opt-in one-PR-per-batch mode. Change map:

| File | Change |
|---|---|
| `template/src/pdca_harness/state.py:33-39` | `TERMINAL = frozenset({COMPLETE, DISCONTINUED, RESOLVED})` — the terminal-finished set, defined in the one module that owns the state names |
| `template/src/pdca_harness/record.py` (new, 225 lines) | `select()` (`:33`), `record()` (`:61`), `after_publish()` (`:185`) + `_repo_path`/`_format` helpers |
| `template/src/pdca_harness/config.py:397-412, 656-665, 738-742` | `[records]` table: `mode` (off\|commit\|pr, default off, unknown ⇒ off loudly), `branch`, `subject`, `issue` |
| `template/src/pdca_harness/cli.py:22-24, 392-405, 485-486` | `record` subparser (ids…, `--dry-run`) + dispatch |
| `template/src/pdca_harness/publish.py:34-37, 391-394, 500-503` | the call-in, strictly after each path's `publish.json` write |
| `template/pdca.toml.jinja:348-362` | commented `[records]` block (the config-table doc pattern every other table uses) |
| `template/tests/test_record.py` (new) | the brief's named test — 15 cases over criteria (a)–(e) |

## Design decisions, mapped to the brief

**(a)/(e) Selection is `state.state`, single-sourced.** The brief's motivation names the
drift failure ("two such enumerations drifting") explicitly, so the terminal-finished
set lives in `state.py:39` next to `HALTED` (`state.py:31` pre-patch, the cited peer),
and `record.select()` (`record.py:33-57`) tests membership via `state.TERMINAL` only.
The test locks this mechanically: `inspect.getsource(record)` must contain
`state.TERMINAL` and must NOT contain `state.COMPLETE`/`"COMPLETE"`/… in any quoted or
attribute form (`test_no_duplicated_state_enumeration_in_the_module`). Why a new set
rather than reusing `HALTED`: `HALTED` (`state.py:31`) includes UNPLANNED and
AWAITING_SIGNOFF — halted *for a human*, files still changing — which criterion (a)
explicitly excludes. An explicit id never overrides the predicate (a non-terminal id is
reported and excluded, `record.py:52-56`): the selection predicate *is* the safety
property, per the brief's Motivation.

**(b) One batch commit.** Steps mirror the deterministic git-step shape at
`publish.py:254-266` (pre-patch cite, per the brief): build the argv list, echo, run,
fail loudly on the first non-zero. Two deliberate deviations from the publish shape,
both because the repo here is the *instance's own working checkout*, not a dedicated
target checkout:

- **Pathspec-scoped `add`/`commit`** (`git commit -m <subject> -- <paths>`,
  `record.py:110-118`): publish stages with `add --all` because its checkout is clean
  by construction; here the operator may have unrelated work staged, and an unscoped
  commit would sweep it in.
- **No `checkout -B`** in pr mode (`record.py:120-134`): publish's `checkout -B`
  (`publish.py:257` pre-patch) runs in a stash-protected dedicated checkout. Flipping
  the instance repo's branch after committing would strip the just-committed bundle
  files from the working tree when checking back out. Instead: `git branch -f
  <branch> HEAD` + `push --force-with-lease -u origin <branch>` (the lease for the
  same re-run reason as `publish.py:276` pre-patch) — "branches, pushes and opens one
  PR" per criterion (c), without touching HEAD.

A staged-changes probe (`git diff --cached --quiet -- <paths>`, `record.py:153-168`)
makes "everything already recorded" a quiet rc-0 success instead of a failing
`git commit` ("nothing to commit") — re-running `pdca record` must be idempotent.

**(c) One PR per batch.** `gh pr create --draft --base <default_branch> --head
<branch>` with a generated body listing each bundle and its state (`record.py:129-142`).
Draft, consistent with every PR the engine opens (STOP discipline: ready/merge stay the
human's). The tracker reference reuses `cfg.issue_trailer` (`[tracker]` — no new config
key for the trailer format).

**(d) `mode = "off"` is byte-identical.** Three layers: the dataclass default is "off"
(`config.py:403`); `after_publish` returns before doing anything under "off"
(`record.py:195-196`), so the publish path is unchanged for every existing instance
including ones that don't version `results/`; an unknown mode fails CLOSED to "off",
loudly (`config.py:660-665`) — the opposite call from `sweep_worktrees`' fail-toward-
"clean" (#297), because recording *writes repo history* while sweeping reclaims
scratch; inventing commits is the unsafe direction. The explicit verb under "off"
refuses with rc 2 and a configure-me hint (`record.py:71-75`), running no subprocess
(locked by `test_off_is_the_default_and_runs_nothing`).

**Publish call-in point.** The brief's ordering note reserves exactly one `publish.py`
touch: "after `publish.json` is written". Wired in both publishing paths —
`publish.py:391-394` (new-PR, after the `publish.json` write at `publish.py:374`
pre-patch) and `publish.py:500-503` (stacked, after its write at `publish.py:487`
pre-patch) — on the success path only, and **best-effort**: `after_publish` catches
everything and reports with a manual fallback (`record.py:197-206`), because "changing
what publish itself does" is out of scope — a bookkeeping failure must never turn a
completed publish into rc 1. One shadowing gotcha: `publish()` builds a local
`record = {…}` dict (its publish.json payload, `publish.py:362` pre-patch), so the
module is imported as `record_mod` (`publish.py:34-37`).

**Open question (`issue = "ask"` headless), resolved as the brief proposed:** skip PR
mode and report. `record()` prompts only when interactive (`interactive=None` ⇒
`sys.stdin.isatty()`); headless or `--dry-run` downgrades to commit-only with a stderr
note naming the fix (`record.py:95-108`). A headless flow can therefore never hang on
`input()`.

## Alternatives ruled out (with cost)

- **Instance script** — rejected by the brief itself (re-implements `state.state` and
  drifts; the wyrd RESOLVED-guard defect). Zero engine lines but reintroduces the exact
  two-enumerations failure the issue documents.
- **Per-bundle PRs** — rejected by the brief (noise + collides with one-issue-per-PR).
  Also costs nothing less: the batch path is the same 4 git steps either way.
- **`checkout -B` + stash/restore like publish** (`publish.py:257, 332-343` pre-patch)
  — ~10 more lines (stash, orig-ref capture, try/finally restore) *and* a working-tree
  hazard on the operator's live repo (bundle files vanish from the tree between record
  and merge). The `branch -f` + `push HEAD` form is both smaller and safer here.
- **Reusing `HALTED` minus exclusions** (`HALTED - {UNPLANNED, AWAITING_SIGNOFF}` in
  record.py) — 1 line cheaper than the new set but puts the enumeration of exclusions
  in the consumer, which is the drift shape again; criterion (e) forbids it in the new
  module.

## Verification (the three forced questions)

- **(a) Genuine red?** Yes — reverted exactly as the C4 gate does (`git apply -R
  --exclude=tests/* --exclude=template/tests/* patch.diff`), then ran the project
  runner: `cd template && PYTHONPATH=src python3 -m unittest tests.test_record` →
  `FAILED (errors=1)` (ImportError: no `pdca_harness.record` — matching the brief's
  "red on current main: no record subparser exists"). Re-applied → 15/15 OK, and
  `git diff` byte-matches the shipped `patch.diff`.
- **(b) Production path?** Yes — the test imports the production modules
  (`pdca_harness.record`, `cli`, `publish`, `config`, `state`, `signoff`) and drives
  `record.record()`, `record.select()`, `cli.main(["record", …])` and the real
  `publish.publish()`; only `subprocess.run` / `_check_repo` are stubbed, exactly as
  the brief prescribes ("git/gh calls are stubbed as `template/tests/` already does
  for publish") and as `test_publish_slice.py:333-356` does.
- **(c) Fixture includes the fault?** Yes — the selection fixture builds the states
  that must be *excluded* (UNPLANNED, AWAITING_SIGNOFF, PLANNED, BUILT) alongside the
  three terminal ones, so a wrong predicate (e.g. `HALTED`) fails the test; the
  follows-the-state-files case starts from the excluded AWAITING_SIGNOFF bundle and
  flips it to COMPLETE by writing §9 (the real `signoff.record`), asserting the
  selection changes; the publish call-in spy asserts `publish.json` exists *at call
  time* (ordering, not just occurrence).

## Test runs (project runners, not hand-rolled)

- Bundle test: `cd template && PYTHONPATH=src python3 -m unittest tests.test_record`
  → 15/15 OK (green), FAILED with production hunks reverted (red).
- Whole offline driver suite (the brief's falsifiability suite): `cd template &&
  PYTHONPATH=src python3 -m unittest discover -s tests` → **1443 tests, OK
  (skipped=2)** — no regression from the `state.py` / `config.py` / `cli.py` /
  `publish.py` touches.
- Root template-repo suite (patch touches `pdca.toml.jinja`, which render/update-compat
  exercise): `.venv python3 -m unittest discover -s tests` from the target root →
  **7 tests, OK**.

## Commit-readiness

The target repo installs no local git hooks (checked `.git/hooks` of the primary
checkout — samples only) and configures no Python formatter (no pre-commit config, no
ruff/flake8/pyproject lint config at the root). Its PR CI is `docs-check.yml`
(Markdown lint over `docs/` — untouched by this patch) and `render-check.yml` (the
render suite — run above, green). Code follows the house style of the touched files
(≤ ~95-col lines, module docstrings, issue-number comments).

## Conflicts noted for the driver

As the brief's ordering note says: 316 adds a `cli.py` subparser in the same block
(this patch inserts `p_record` before `p_doctor`, `cli.py:392-405`); 311/315 edit
`publish.py` — this change touches it only at the two post-`publish.json` call-in
lines + the import. Different waves required; no build-on dependency.
