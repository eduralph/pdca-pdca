# build-notes — issue 316 / pdca-triage — iteration 2

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l1`, base
dfd0427 — same base as iteration 1). All `path:line` cites are against that tree
with the patch applied. `patch.diff` is byte-identical to `git diff` of the
restored worktree (verified with `diff -q` after the red-leg round-trips).

## What this iteration is

The sign-off rejected iteration 1 on **two substantiated implementation defects,
approach sound, brief unchanged**. This patch is iteration 1 (its rationale stands —
see `iteration-v1/build-notes.md`; I do not repeat it here) **plus the two fixes the
carry-forward prescribes**, each bound by a new shipped test that is red on the v1
code and green now. Nothing else was redesigned: the carry-forward explicitly
endorses the approach, so gratuitous churn would only re-open reviewed ground.

## Fix 1 — C3/T3: registration recovery was unreachable

**Defect (reviewer-reproduced):** after a held Act session lock, run 1 had already
filed the BUG issue and written the per-PR record, then exited 1 before
registering. The prescribed re-run pulled the same findings, found nothing NEW, and
hit the `if not new: return 0` fast path **before** the registration section — so
the ledger stayed permanently empty and the v1 build-notes' "self-heals from the
full record history" claim was false: the recovery code existed but was unreachable
(v1 triage.py:448 vs :497).

**Fix — the record is now a recovery journal (`pending` flags):**

- Every finding is written to the record marked `"pending": true` **before** the
  Act lock is taken (triage.py:545-553) — same durable-before-lock order as v1
  (filing stays non-repeatable), but now the record also encodes "registered yet?".
- The fast path exits 0 only when there is nothing new **and** nothing pending
  (triage.py:497-506); pending findings re-enter the register+log batch rebuilt
  from the record, not from a fresh pull (`_finding_of`, triage.py:329-334;
  batch assembly triage.py:560-561), with their filed issue numbers riding along so
  the recovered act-log entry credits `filed tracker issue #N` without re-filing.
- The flags clear **last**, only after `register_signals` + `append_entry` are
  durable (triage.py:586-592). A crash anywhere earlier leaves them set and the
  next run finishes the job. The worst residue of a crash in the narrow window
  between the log append and the flag clear is one duplicate, *visible* log entry —
  degradation is toward loud repetition, never silent loss (the same failure
  direction act.py's legacy-marker handling chooses, act.py:110-112).
- Filing is **not** re-decided on recovery (triage.py:513-516): a pending finding's
  filing decision was made at its own ingest (issue number in the record, or
  deliberately not filed — unmerged PR / SplitError). Tracker issues are
  irreversible, and blind retry is exactly what split's UncertainFiling rule
  forbids. The interrupted run's `bug_note` is persisted in the record and restored
  for the recovered log entry (triage.py:552, :554-555) so a not-filed BUG keeps
  its "why".

**Rejected alternatives, with cost:**

- *Always re-run registration on every "no new findings" exit* (no flag; ~3 lines
  smaller): registration itself is idempotent, but the **act-log append is not** —
  recovery must also regenerate the entry the interrupted run never appended
  (criterion (c) routes through that entry), and without a marker there is no way
  to know whether it was appended; every no-op re-run would either spam a duplicate
  entry or silently skip the lost one. The flag is the cheapest state that
  distinguishes the two (net +14 lines vs that sketch).
- *Take the Act lock before filing/record-write* (~2-line move): a held lock would
  then abort before anything durable happens — no half-state, no recovery needed —
  but it serializes the irreversible `gh issue create` (network, minutes on a big
  PR) inside the shared Act session lock, blocking every concurrent flow's auto-Act
  for the duration; v1 deliberately kept gh traffic outside the lock and the
  reviewer endorsed the approach. Rejected on that regression, not on line count.
- *`wait=True` on the lock* (1 word): turns a CLI command into an indefinite block
  behind a whole interactive Act review (`act_session` docstring, act.py:119-134 —
  non-blocking is the documented contract for manual paths like
  `act log --append`); and it still would not heal a *crash* between record and
  register, which the journal does.

## Fix 2 — C5: pagination

**Defect:** reviews and comments were each fetched once with `per_page=100`
(v1 triage.py:422-423); a PR with >100 of either silently dropped the rest —
violating "register every finding" in the exact direction the module documents as
the one it must not degrade in.

**Fix:** `_api_list` (triage.py:143-166) follows pagination — `page=1, 2, …` until
a short page — and both endpoints go through it (triage.py:469-470). Any failed or
non-list page returns `None` so the existing fail-closed abort still covers a
*mid-pagination* failure: a partial pull is treated exactly like a failed one
(nothing ingested, exit 1), never a silent truncation.

**Rejected alternative, with cost:** `gh api --paginate` (would delete the 15-line
loop): without `--slurp` it emits the pages' JSON arrays concatenated back-to-back
— unparseable as one document by `json.loads` — and `--slurp` only exists in
recent gh releases, adding a version dependency the brief's "no new external
dependencies" note rules out. The stdlib loop costs 15 lines and zero new
requirements; it is also directly stubbable by the same canned-`gh` fake.

## Shipped-test deltas (template/tests/test_triage.py — 17 tests, was 15)

- `test_lock_contention_then_rerun_registers_recorded_findings`
  (test_triage.py:252) — the reviewer's exact scenario: run 1 under a held
  `act.act_session` (a second flock on the real lock file — fcntl locks conflict
  across open file descriptions even in-process) exits 1 *after* filing and
  recording; asserts the ledger is empty and the record is all-pending; the re-run
  exits 0, registers all four class-keyed signals, appends the recovered entry
  crediting issue #901, files nothing new, and clears the journal.
- `test_paginates_reviews_and_comments_beyond_100` (test_triage.py:157) — page 1
  of **both** endpoints is exactly full (100 items); the only BUG and TEST-GAP
  findings live on page 2. Asserts `page=2` was requested on both endpoints, all
  102 findings are recorded, the page-2-only signals reach the ledger, and the
  page-2 BUG still files its issue. The gh fake gained a paged-payload shape
  (`{"pages": […]}`, test_triage.py:90-108) — single-payload maps behave as before,
  so all 15 v1 tests run unchanged.

## Verification — through the project's configured runners

- **C4 gate** (`pdca.toml` → `./engine/scripts/run-verify.sh`, run from the
  instance root with `PDCA_BUNDLE`/`PDCA_WORKTREE` set):
  green leg `Ran 17 tests … OK`; red leg (production hunks reverted → main has no
  triage module) `FAILED (errors=1)` → `C4 PASS: red without the fix, green with it`.
- **Iteration-specific red** (same unittest invocation the gate runs internally,
  explicit timeout): with **v1 production code + v2 tests** in the worktree, both
  new tests FAIL — pagination: `no "page=2" request ever made` (AssertionError at
  test_triage.py:171); lock: `KeyError: 'pending'` (no recovery journal exists in
  v1, test_triage.py:267). Worktree then restored; `git diff` byte-identical to
  `patch.diff`.
- **T3 gate** (`./engine/scripts/run-suite.sh`): render/update-compat suite
  `Ran 7 tests … OK`; offline driver suite `Ran 1331 tests … OK (skipped=2 —
  pre-existing)`. Exit 0.

## Forced self-refutation (the three questions)

- **(a) Genuine red?** YES, twice over. The official C4 red leg (revert all
  production hunks) fails on ImportError — the brief's falsifiability claim. And
  the two *new* tests were additionally run against the **v1 production code**
  (the rejected patch, i.e. everything-but-the-two-fixes reverted): both FAIL with
  the exact defect signatures above, so each new test binds its carry-forward item,
  not merely the module's existence.
- **(b) Production path?** YES — the tests import `pdca_harness.triage/cli/act/split`
  from `template/src` (the production package, `PYTHONPATH=src` exactly as the
  target's CONTRIBUTING prescribes), drive `triage.run` and `cli.main(["triage", …])`
  end-to-end, and assert on the real artifacts production writes
  (`process/act-ledger.json`, `process/act-log.md`, `process/triage/pr-*.json`).
  The lock-contention test contends on the **real** `.act-session.lock` via the
  production `act.act_session` — no mocked lock. The only stub is the `gh`
  subprocess boundary, which the brief prescribes stubbing.
- **(c) Fixture includes the fault?** YES — the pagination fixture's page 1 is
  deliberately *full* (100 items) with the falsifying findings placed only on
  page 2 (curating them onto page 1 would prove nothing); the lock fixture holds
  the real lock during a run that has already done its irreversible work, which is
  precisely the half-state the reviewer demonstrated; and the v1 fixtures keep all
  their fault-carrying elements (body-less review, unmerged PR, 404 endpoint,
  identical re-run, post-`resolve` recurrence on a second PR).

## Commit-readiness

Unchanged from v1 and re-checked on this tree: the target repo configures no
pre-commit hooks and no formatter (no `.pre-commit-config.yaml`, no
ruff/flake8/pyproject formatter config); CONTRIBUTING requires the DCO
`Signed-off-by` trailer, which the publish machinery adds at commit time. No line
in the touched files exceeds the house ~95-col style (checked mechanically). Both
target suites pass on the patched tree.

## STOP discipline

Nothing pushed, no PR opened or marked ready. Patch + test + notes live in the
bundle only.
