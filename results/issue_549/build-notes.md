# Build notes — issue 549 / csv-batch-plan-reap-rereads-the-briefs-it-wrote (iteration 2)

Target: `eduralph/pdca-harness @ main`, base `70ea12b`. Line numbers below are on the
fixed tree (base + `patch.diff`) unless marked "base".

## What this iteration changes relative to v1

Sign-off accepted v1's approach and tests and asked for two error-handling fixes, two new
tests, and a docstring fix. All are in:

1. **Snapshot only when no bundle set is registered.** `session()` now takes the brief
   snapshot under `elif role == "planner" and not bundles:`
   (`template/src/pdca_harness/handoff.py:489-494`). A single Plan or id-seeded batch Plan
   reads no other brief at spawn, so an unreadable brief elsewhere can no longer make
   setup raise and cost that session its exit contract. `not bundles` is exactly the
   condition `stop_problems` uses to decide whether it needs the snapshot
   (`handoff.py:676-683`): both look at the same list, since `registered["bundles"]` is
   built from the `bundles` argument and wins over the scratch file at reap
   (`handoff.py:521`). v1's build notes argued an id-seeded batch with `ids == []` would
   lose the re-read under this gate; it does not, because that session also registers an
   empty list and so also takes the snapshot.
2. **Per-brief read errors never hide other briefs.** `_brief_fingerprints`
   (`handoff.py:293-312`) wraps each brief's read in its own `try`. A brief that exists
   but cannot be read gets the fingerprint `unreadable (<error>)` instead of a sha256, so
   one bad brief neither aborts the spawn snapshot nor the reap's re-scan. At reap, a
   changed unreadable brief lands in the work set like any other, and the existing
   per-bundle `try/except` around `check_bundle` (`handoff.py:685-690`, unchanged from base
   `:615-620`) turns it into `<bundle>: could not check (<error>)`. `check_planner` does
   raise on such a brief: `brief.is_placeholder` → `whole_field` → `read_text`
   (`template/src/pdca_harness/brief.py:62`, `:177`). The tests prove that for each fixture
   instead of assuming it (`check_error`, `test_handoff_reap.py:412-422`).
3. **Docstring fixed.** The `session()` docstring (`handoff.py:457-467`) no longer claims
   to mirror `leaves._brief_snapshot`. It says what the code does: every brief is
   fingerprinted, placeholder or not, unlike `leaves._brief_snapshot`
   (`leaves.py:3640-3649`), which leaves placeholders out of its "before" picture. The
   reason is criterion (ii): an untouched template copy must not be re-read as the
   session's work.
4. **New tests (a) and (b)** — see the test list below.

## The whole change (fixed tree)

- `handoff.py:293-312` `_brief_fingerprints(cfg)`: `{bundle name: fingerprint}` for every
  `issue_*` dir whose `brief.md` exists. Presence is `bp.exists()`, the same test
  `check_planner` uses (`handoff.py:126`) and `leaves._fresh_plan_briefs` uses
  (`leaves.py:3667`); v1 used `is_file()`, which silently skipped a directory sitting at
  `brief.md` that `check_planner` would report as "could not check".
- `handoff.py:315-331` `_changed_briefs(cfg, baseline)`: the bundles whose fingerprint
  differs from the spawn snapshot, or that had none then, sorted by name. With no
  snapshot in `baseline` it returns `[]`: a hand-built state (e.g.
  `tests/test_handoff.py:467-469`) keeps today's behavior, and the reap never turns into
  a scan of every bundle. The module docstring rules out scan mode (`handoff.py:9-12`).
- `handoff.py:489-494`: the snapshot, stored as `baseline["briefs"]` in the
  driver-registered dict. At reap `registered` is merged over the scratch file
  (`handoff.py:521`, unchanged), so a leaf cannot blank or forge it.
- `handoff.py:675-683`: `kw` is now computed before the `if bundles:` branch instead of
  inside it (same values, base `:611-614`). For a planner with no registered bundles,
  `bundles` becomes `_changed_briefs(...)`. From there the existing loop (`:684-691`) and
  the existing `/handoff` tail (`:692-695`) run unchanged. So:
  - changed briefs → each is checked and reported, and there is no "verified none" item
    even without `/handoff` (criteria (i), (iv));
  - no changed brief → exactly base's tail: passed ⇒ nothing, else "verified none"
    (criterion (iii));
  - broken `[[doctor.checks]]` table → one item, and the re-read briefs are checked with
    `dependencies=False` through the shared `kw` (criterion (v)).
- Docstrings that described the old behavior: module (`handoff.py:13-31`), `session`
  (`:457-467`), `report_at_reap` (`:541-546`), `stop_problems` (`:645-653`).
- `docs/01-render-and-integrate.md:181-187`: the paragraph no longer says the batch Plan's
  writes are not re-read.

Act, sign-off, publish and every registered planner path run the same code as on base:
the `act` branches in `session` and `stop_problems` are untouched, and a non-planner role
or a registered planner never reaches the new lines.

## Tests (appended, `template/tests/test_handoff_reap.py:382-593`)

New sibling class `UnregisteredPlanRereadsWhatItWrote(Base)`, driven through the real
`handoff.session` via the existing `Base.reap` harness. No new module-level import.

| Test (line) | Criterion | Base (70ea12b) | v1 `handoff.py` | This patch |
|---|---|---|---|---|
| `test_a_handoff_for_one_issue_does_not_hide_a_brief_written_for_another` (:424) | (i), plus a rewritten pre-existing brief | red (stderr empty) | green | green |
| `test_a_session_cannot_blank_its_own_spawn_snapshot` (:445) | Citations: driver-registered baseline wins | red | green | green |
| `test_a_session_that_changed_no_brief_is_judged_as_before` (:460) | (ii) + (iii): 7 kinds of pre-existing untouched brief, incl. template copy and 2 unreadable kinds | green (pins old behavior) | red (unreadable brief breaks spawn) | green |
| `test_changed_briefs_that_all_pass_report_nothing_without_a_handoff` (:493) | (iv) | red ("verified none") | green | green |
| `test_a_broken_doctor_table_is_one_item_and_the_briefs_are_still_checked` (:507) | (v), table rule | red | green | green |
| `test_a_brief_that_cannot_be_read_is_its_own_item_and_hides_no_other` (:530) | carry-forward (b) / (v) | red | red (both subtests) | green |
| `test_an_unreadable_brief_elsewhere_does_not_disable_a_registered_plan` (:553) | carry-forward (a) / (vi) | green (pins old behavior) | red (both subtests) | green |
| `test_the_reread_changes_nothing` (:579) | (vi), report only | red | green | green |

Carry-forward (b)'s v1 failures are the reviewer's exact finding. With no read
permission, v1 printed `could not check the planner session's exit contract
(PermissionError: … issue_17/brief.md) — no contract item was reported`. With a directory
in its place, v1 silently skipped it and reported only issue_18. I first wrote (b) with
an extra pre-existing unreadable brief. Against v1 that made both subtests fail at spawn,
which hid whether the reap-time half was caught. So I removed it (the (ii)/(iii) test
already covers a pre-existing unreadable brief) and put the directory case first, so a
no-permission file left over from one subtest can't be the reason the other fails.

## What I ruled out, with costs

- **Emitting the unreadable item straight from discovery** (discovery returns
  `(bundle, error)` pairs, `stop_problems` prints `could not check (error)` for those and
  runs `check_bundle` for the rest). Cost: a tuple-returning helper plus a second
  item-building branch in `stop_problems`, about 6–8 more lines, and the `could not
  check (…)` wording in two places. What I did instead reuses the existing loop at
  `handoff.py:684-691` with zero changes. Its one dependency, that `check_planner` raises
  on an unreadable brief, is asserted per fixture by `check_error`.
- **Always re-reading a brief that cannot be read**, even one that failed the same way at
  spawn. Rejected. It would report a pre-existing, untouched unreadable brief at every
  CSV-batch reap, which breaks criterion (ii) ("not this session's work"). My rule: the
  same read error at spawn and at reap counts as unchanged.
- **Adding size + mtime to the unreadable fingerprint** so a session that rewrites a brief
  it still can't read is noticed. Cost: about 5 lines (a nested `try` around
  `bp.stat()`). Not done: it only matters for a session that writes into a brief it
  cannot read (for example mode 0200) and leaves it that way. This is the one known gap
  in the rule; the human may want it.
- **No snapshot ⇒ treat every brief as changed** (v1's fallback). Rejected. For any state
  without a snapshot it re-reads every brief in the bundle root, which is the scan mode
  the module rules out (`handoff.py:9-12`). It would also change the output of hand-built
  states in `tests/test_handoff.py:467-469`.
- **Importing `leaves._brief_snapshot` / `_fresh_plan_briefs`**. Out of scope per the
  brief (`handoff.py` stays import-light for the hook). The mirrored logic is 2 small
  helpers (`handoff.py:293-331`).

## Flag for the human: `/handoff` command text now understates the reap

`template/.claude/commands/handoff.md.jinja:21-24` (model-facing, read by the planner
during the very session this fix covers) still says: "in a session that picks its own
issues, or an Act session, it checks that a `/handoff` passed instead of re-reading what
the session wrote." After this patch that is wrong for a Plan that picks its own issues:
the briefs it wrote are re-read. I did **not** edit it. The brief's Scope says "`do_plan_batch`
and the `/handoff` command are untouched" and lists the command as out of scope, and the
brief's conflict analysis did not cover that file. The wrong text is harmless: it
understates the check and still tells the model to run `/handoff` per id. It is a
one-sentence follow-up, and any rewrite must keep
`ModelFacingTextPromisesNoEnforcement` (`test_handoff_reap.py`) green.

## Verification (all through the instance's own gate scripts, each under `timeout`)

- **C4** `engine/scripts/run-verify.sh` (PDCA_BUNDLE = this bundle, PDCA_WORKTREE = the
  lane worktree): exit 0, `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
  Green leg: `Ran 37 tests … OK`. Red leg (production hunks reverted, tests kept): `Ran 37
  tests … FAILED (failures=7)`. The 7 are the tests marked red in the table above, each
  failing because base never re-reads what an unregistered session wrote. Criterion (i)
  fails with an empty stderr, as the brief's Falsifiability predicts. The gate restored
  the tree: `git diff` is byte-identical to `patch.diff` afterwards.
- **T3** `engine/scripts/run-suite.sh`: root suite `Ran 24 tests … OK`; driver suite
  `Ran 1928 tests … OK (skipped=2)`. The 2 skips existed before this change; none of the new
  subtests skipped (I run as uid 1000, so the no-permission fixtures bite). This ran
  before I added `test_a_session_cannot_blank_its_own_spawn_snapshot`. That later change
  only adds a test to `test_handoff_reap.py`, which the final C4 run executed whole (37 OK).
- **T2** `engine/scripts/run-docs-check.sh`: `docs lint clean, site render + link audit
  clean` (22 pages).
- **Against v1**: swapped in v1's `handoff.py` (from `iteration-v1/patch.diff`), kept my
  tests, ran the new class. 6 failures, all described in the table (both carry-forward
  tests, both subtests each, plus the (ii)/(iii) unreadable steps). Then restored mine
  from `patch.diff` and confirmed with `cmp`.
- **Mutation**: flipped the reap's merge at `handoff.py:521` to let the scratch file win.
  `test_a_session_cannot_blank_its_own_spawn_snapshot` failed (`[] != ["issue_8: …"]`).
  Restored and confirmed.
- `git diff --check`: clean.

## Refute-your-own-test (forced)

- **(a) Genuine red?** Yes. With the production hunks reverted by the C4 script, 7 of the
  new tests fail. Examples: (i) gets an empty stderr where the `issue_8` item must be;
  (iv) gets the "verified none" item where nothing must print; (b) gets only "verified
  none" where both the unreadable and the empty-criterion brief must be named. The 2 tests
  that pass on base pin unchanged behavior, (ii)/(iii) and the registered path, and each
  fails against the rejected v1 code.
- **(b) Production path?** Yes. Every test opens the real `handoff.session` context manager
  (the one `do_plan_batch` opens with `seeded = []`, `leaves.py:1195-1205` per the brief).
  Its real `finally` reap runs `report_at_reap` → `stop_problems` → `_changed_briefs` /
  `_brief_fingerprints` → `check_bundle` → `check_planner`. No mock or copy. The only
  stand-in is `during(env)` for the leaf process, which writes files and calls the real
  `record_pass` into the real scratch file (the brief's Falsifiability prescribes it).
- **(c) Fixture includes the fault?** Yes. The malformed brief is written mid-session,
  after the spawn snapshot, next to a real passed `/handoff` for another id. Unreadable
  briefs are real: `chmod 0` on a real file and a real directory at `brief.md`, not mocked
  read errors. `check_error` asserts the planner check really raises on each one. If it
  doesn't (a root runner can read a mode-0 file), the subtest is **skipped**, never
  counted as a pass. The directory case bites for root too.

## Commit-readiness

The target has no formatter or linter config (no ruff/black/flake8/pre-commit anywhere,
no `core.hooksPath`, no non-sample git hooks). Its PR CI (`.github/workflows/`) runs
`docs-check` (= T2 above, clean) and `render-check` (= the T3 root suite, green). New
lines stay within the files' existing width (longest added line 91; `handoff.py` already
has 93, the test module 92).

## Housekeeping to disclose

- I accidentally wrote `/tmp/.unused` (a copy of `git diff` output) while comparing the
  patch. It is outside the roots I may write to. I did not remove it: cleanup is the
  harness's job, and it is harmless.
- Two untracked gate logs sit in the worktree: `.c4-run.log` and `.t3-run.log`. They are
  not in `patch.diff`, which is `git diff` of tracked files only.
- Python here is 3.14.4. On 3.11–3.13, `Path.exists()` raises for an issue dir without
  search permission, and 3.14 returns False. Both are handled: raised → `unreadable (…)`
  → `could not check`; False → absent, which matches what `check_planner` says on the
  same interpreter.
