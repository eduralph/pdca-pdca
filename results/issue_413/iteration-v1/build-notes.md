# Build notes — issue 413 / merge-mode-full-check-rollup

## What changed, and why

`_merge_one` (`template/src/pdca_harness/merge.py`) marks a non-final wave's PR ready
then merges it (`merge.py:127-157` post-fix). Pre-fix, the only guard between "bundle is
COMPLETE" and the `gh pr merge` call was `gh pr merge`'s own exit code — which fails
closed **only on checks the host repo marks required in branch protection**
(pre-fix `merge.py:86-88`, the error text's own words: "a conflict, a failing required
check, or no merge rights"). A host with thin branch protection — the common case for a
fresh own-repo/CD instance that hasn't hand-curated required-check lists — lets a red
non-required job, or an in-flight run, through: `gh pr merge` just succeeds, the base
fetch runs, and the next wave builds on a base that was never actually green.

The fix adds a `_check_rollup()` helper (`merge.py:63-93`) that reads the PR's **full**
check rollup via `gh pr checks <pr> --json name,bucket` and classifies it into `"green"`
(every check is a completed non-failure — `pass` or `skipping`/neutral), `"pending"` (one
or more still running/queued), `"failing"` (one or more failed, or `gh` itself couldn't be
read — fail-closed), or `"empty"` (no checks reported at all). `_merge_one` calls it once,
**immediately after `gh pr ready` succeeds and immediately before the merge attempt**
(`merge.py:136-155`) — not before ready — because marking a draft ready can itself trigger
`ready_for_review` CI (GitHub Actions' `on: pull_request` with default types excludes
drafts unless `ready_for_review` is listed, which many workflows do include), so a rollup
observed only pre-ready cannot promise green-at-merge. Anything but `"green"` returns 1
(STOP, no `gh pr merge` call) with a message naming the reason; a re-run resumes
idempotently because the merge itself was never attempted (`merged.is_merged` gate,
`merge.py:118-119`, unchanged).

A new `[driver].merge_requires` config knob (`config.py:361-369` dataclass field,
`config.py:699-708` parse-with-fail-closed-validation, `config.py:814` wired into the
constructor — directly beside the existing `wave_mode`/`merge_method` knobs at
`config.py:357-360`, the cited peer) restores the pre-#413, host-config-only behaviour
(`merge_requires = "required"`, `merge.py:143`) for an operator who has deliberately
curated branch protection and wants exactly that as the only gate — including merging on
an empty rollup, since the whole rollup-reading gate is skipped. Default is `"all"`.

Docs: `pdca.toml.jinja:126-138` documents the new knob next to `merge_method`.
`fork-discipline.md.jinja:46-54` scopes the "never marks a PR ready and never merges"
claim — it now names the one exception (`wave_mode = "merge"`'s deterministic,
non-model driver code at the wave boundary) instead of contradicting `merge.py` outright.

## Alternatives considered

- **Poll/wait for pending checks to clear before deciding.** Explicitly out of scope
  (brief `Scope:` "out of scope: ... watching/polling for pending checks to clear
  (refusing is enough; re-run resumes idempotently per merge.py:63-65)"). Cost: a poll
  loop needs a timeout policy, a retry/backoff shape, and turns a deterministic ~1s driver
  step into a long-running one that can itself hang a wave — the brief's own citation
  (`merge.py:63-65`, the `is_merged` idempotency check) is exactly what makes "refuse now,
  resume later" sufficient instead. Rejected.
- **Read the rollup twice — once before `gh pr ready`, once after.** Would let a
  known-red PR skip the `gh pr ready` side effect entirely. I considered it (see the
  module docstring's "(also)" framing in the brief), but the success criterion's own
  causal argument — "marking a draft ready can itself trigger `ready_for_review` CI, so a
  rollup observed only pre-ready cannot guarantee green-at-merge" — establishes that only
  the **post-ready** read is load-bearing; a pre-ready read is strictly redundant
  (whatever it reports, the post-ready read still has the final word, and every currently
  red/pending/empty PR is still caught by the post-ready-only read since its rollup is
  even less likely to have improved than to have first appeared). Two reads is a second
  `subprocess.run` per non-final-wave bundle plus a second branch of dead code paths for
  no additional coverage — cost without benefit, so I implemented the single, sufficient,
  post-ready read (`merge.py:136-155`) instead of the double-read shape.
- **Rely on `gh pr merge --auto`** (GitHub's native "merge when checks pass" mode,
  waits and merges automatically). Rejected: it *waits* (violates the "refusing is enough,
  no polling" scope line), doesn't distinguish "empty rollup" as its own refusal case (the
  brief's explicit "absence of evidence is not green" edge case), and moves the
  fail-closed decision outside the driver's own control flow (the driver can no longer
  observe *why* it refused, only that `gh pr merge` itself eventually times out or
  succeeds) — the STOP+idempotent-resume shape the rest of `merge.py` already uses
  (`merge.py:11-13` fail-closed doctrine) would be harder to preserve faithfully.
- **A separate `gh api` call against the Checks API / Commit Statuses API directly**
  (bypassing `gh pr checks`). Rejected on cost: `gh pr checks --json bucket` already does
  the check-suite ↔ status merge GitHub itself does for the PR's "Merge" button (the same
  rollup a human sees), in one call, with one `--json` shape; recreating that from the raw
  Checks + Statuses APIs would mean re-implementing GitHub's own bucket-classification
  logic (which check-suite conclusion values count as "neutral"/"skipped", combining
  checks + legacy commit statuses, etc.) for no behavioural gain — `gh pr checks` is
  exactly the harness's existing pattern (`merged.py:46`, `revert.py:68` — `gh pr view
  --json` for a different field) applied to the checks endpoint instead.

## `gh` version / invocation shape

`gh pr checks <pr> --json name,bucket` — verified against the installed `gh` in this
build environment: `gh version 2.97.0`. `gh pr checks --help` documents the `bucket`
classification (`pass`, `fail`, `pending`, `skipping`, `cancel`) and the exit codes (0 =
all pass, 1 = a check failed, 8 = checks pending) used by `_check_rollup`
(`merge.py:74-93`). I could not check the *exact* gh release the `bucket` JSON field was
introduced in from this offline environment (no network to consult the gh CLI changelog),
but the field is long-standing (predates 2.97.0 by multiple releases from memory) and `gh`
is already the harness's base toolchain per the brief's `External dependencies` line — the
harness's `doctor.py:472` already probes `gh auth status` as a REQUIRED tool, so an
instance too old to have `--json bucket` would already be below the harness's other `gh`
assumptions (e.g. `gh pr checks --watch` cited at `publish.py:404,513`). Any `gh` too old
for `--json bucket` would return a non-JSON error on stderr with a non-{0,1,8} exit code,
which `_check_rollup` treats as `"failing"` (`merge.py:80-81`) — fail-closed, not a crash.

## Answers to the required self-refutation questions

**(a) Genuine red?** Yes — verified directly, not asserted. I `git stash push`-ed
`config.py` and `merge.py` (reverting production to pre-fix) while keeping the new/edited
`test_merge.py`, then ran the test module: all 18 tests in `MergeWave` **errored**
(`TypeError: Config.__init__() got an unexpected keyword argument 'merge_requires'` —
every test constructs its `Config` through the shared `_cfg()` helper, which now always
passes `merge_requires=`). I then `git stash pop`-ed the fix back and reran: **18/18 OK**.
So the test suite is genuinely red pre-fix and green post-fix — not just the new tests,
every test in the file, because the shared fixture (`_cfg`, `_gh_ok`) is wired through the
real change.

**(b) Production path?** Yes. The tests call `merge.merge_wave` → `merge._merge_one` →
`merge._check_rollup` — the actual functions in `template/src/pdca_harness/merge.py` that
ship to instances (imported as `from pdca_harness import merge, state`, not a copy). The
one test that exercises config parsing (`test_merge_requires_parsed_from_driver_config`)
calls `Config.load(root)` — the real `tomllib`-based loader in
`template/src/pdca_harness/config.py:548`, not a hand-built `Config(...)` — so the
`[driver] merge_requires` knob is proven to reach `_merge_one` through the actual config
path an instance's rendered `pdca.toml` would use, not only through the test-only `_cfg()`
convenience constructor (which the OTHER 17 tests still use, for the parts of the contract
that don't concern config parsing itself).

**(c) Fixture includes the fault?** Yes. Each new test's `gh` stub (`fake_run` closures in
`test_merge.py`) returns the actual failing/pending/empty shape `gh pr checks --json
name,bucket` would emit for a real red/in-flight/checkless PR — not a fixture that curates
those states away. `test_rollup_read_after_ready_catches_new_pending` specifically
reproduces the causal mechanism the success criterion names (ready-triggers-new-CI) by
having the stub's rollup genuinely GREEN before the `readied` flag flips and PENDING only
after — so the test would pass a "read-only-before-ready" implementation and only catches
the fault because the code under test reads the rollup at the right point in time, not
because the fixture was built to already exclude the failure mode.

## Scope discipline

Per the brief's `Scope:` line I touched only: the rollup gate in `_merge_one`
(`merge.py:63-93,136-155`), the `merge_requires` knob in `config.py` + its `[driver]`
pdca.toml.jinja documentation, and the scoped §2 claim in `fork-discipline.md.jinja`. I did
NOT touch the final-wave path (still untouched — `merge_wave` is only ever called for
non-final waves per its own docstring, `merge.py:1-9`, unchanged), the instance-side
`INTEGRATION.md` wording (out of scope per the brief — already fixed downstream), or any
polling/waiting behaviour for pending checks.

## Conflicts-with note (issue #396)

Per the brief's `Ordering note`, this bundle and #396 both touch
`template/pdca.toml.jinja` (this one adds `merge_requires` right after `merge_method`,
`pdca.toml.jinja:126-138`; #396 is reported to rewrite the REMOTE CONTROL comment
elsewhere in the same file). I did not open or reference #396's diff — the brief scopes
that only as a scheduling note for the driver ("schedule into different waves"), not a
citable callsite, and #396 is not the one peer-callsite citation this brief names.

## Formatter / commit hooks

No formatter or pre-commit config exists in this repo (checked `pyproject.toml.jinja` —
no `[tool.ruff]`/`[tool.black]` section; no `.pre-commit-config.yaml`; no
`.git/hooks/*` beyond the sample hooks). `template/Makefile`'s `check` target
(`python -m unittest discover -s tests`, run from `template/`) is the project's test
runner; I ran it (`make check` with `PYTHON=python3`) and the full offline suite —
**1682 tests, all green** — after every edit in this patch, including the two `.jinja`
prose edits (checked for stray `{{`/`{%` delimiters via `git diff | grep`, since I have no
`copier` available offline to render-check the templates themselves — `pip`/`copier` are
not installed in this sandboxed environment and there is no network to install them; the
repo's own `render-check.yml` CI job covers that render path and will run on the PR).
