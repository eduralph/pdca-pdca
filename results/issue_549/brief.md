# Brief — issue 549 / csv-batch-plan-reap-rereads-the-briefs-it-wrote

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** csv-batch-plan-reap-rereads-the-briefs-it-wrote
- **Defect:** On the CSV/default batch-Plan path the session-end contract check never re-reads
  a brief. `do_plan_batch` registers no bundle set there, because the planner picks its ids
  mid-session (`template/src/pdca_harness/leaves.py:1195-1205`: `seeded = []` when
  `ids is None`). So `handoff.stop_problems` falls to its no-registered-bundles tail
  (`template/src/pdca_harness/handoff.py:622-625`): if any `/handoff` passed, it returns with
  nothing about the briefs. A session that runs `/handoff issue_7` and then writes
  `issue_8/brief.md` with an empty **Success criterion** (or empty `Slug` /
  `Repo + branch target`) ends with nothing reported. Nothing later catches those three empty
  fields. `state.py` only treats an unfilled template copy as UNPLANNED, and `plan_policy`
  checks size and dependencies only. So the empty criterion reaches Do (no stated end result)
  and Check (SUMMARY §1 is assembled from the empty field). The id-seeded path is not
  affected: its bundles are registered and each brief is re-read (`handoff.py:609-621`).
- **Success criterion:** With the patch, a `planner` session opened through `handoff.session`
  with **no registered bundles** reports at reap, bundle-prefixed and report-only, every
  `check_planner` problem in every `issue_*/brief.md` under `cfg.bundle_root` that the session
  **created or changed** (its content differs from session start, or it did not exist then).
  This holds whether or not a `/handoff` passed during the session. Concretely:
  (i) the issue's case: `/handoff` recorded for `issue_7` (discharged brief), then
  `issue_8/brief.md` written with an empty Success criterion → the reap prints
  `issue_8: brief.md field 'success criterion' is empty …`;
  (ii) a brief that existed before the session and is **byte-unchanged** is not re-read (even
  if malformed). It is not this session's work, which matches the
  `_brief_snapshot`/`_fresh_plan_briefs` "new or rewritten" rule the plan-advisory pass
  already uses (`leaves.py:3640-3669`);
  (iii) a session that changed no brief keeps today's behavior exactly: a passed `/handoff`
  ⇒ nothing about the session; no pass ⇒ the existing "registered no bundle set at spawn and
  verified none" item;
  (iv) when it changed briefs and all of them pass `check_planner`, nothing is reported for
  them and no "verified none" item is added, even without a `/handoff`. This is the rule the
  registered path already follows (`stop_problems` docstring, `handoff.py:579-584`: "a
  session that discharged them without ever typing `/handoff` is discharged too");
  (v) the unreadable-`[[doctor.checks]]`-table rule still holds. It is one item for the
  session, and the re-read briefs are then checked with `dependencies=False`, as for
  registered bundles (`handoff.py:606-614`). A brief whose check raises is its own
  `could not check (…)` item and never hides the others (`:615-620`).
  (vi) the registered paths (single Plan, id-seeded batch, sign-off, publish) and the `act`
  role are unchanged, and nothing in the reap writes, moves or deletes a file under the
  project root. Shown by the named test going red on the base (criterion (i) prints nothing
  about `issue_8`) and green with the fix, with every existing test in that module still
  green (including `test_a_broken_doctor_table_is_reported_at_every_planner_reap`,
  `:623-656`, whose "CSV batch" subtests pre-write their brief **before** the session, so
  criterion (ii) keeps them at their current item count).
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11),
  in the target checkout Do gets. `template/tests/test_handoff_reap.py` already has the
  harness. `Base.reap(role, bundles=None, during=...)` (`:173-191`) opens a real
  `handoff.session` and runs `during(env)` inside it as the stand-in leaf. `during` can call
  `handoff.record_pass(Path(env[handoff.ENV_STATE]), "issue_7")` and write
  `issue_8/brief.md` with `_brief_text(criterion="")` (`:93-101`). On the base the returned
  stderr has no `issue_8` item, so an `assertIn` on it fails for a real reason. The
  planner Config is interactive (`_cfg`, `:119-139`), so the contract is active.
- **Invariant to restore:** The session-end check re-reads every artifact the session
  produced. A passing `/handoff` is the session naming its work, not a replacement for
  checking what it wrote. So a malformed brief cannot leave any Plan path unreported, whether
  or not the driver could register the bundle set at spawn. Source: internal project
  invariant (Tier C), the target's own written contract. `handoff.py:497-502`
  (`report_at_reap`: "What only this report catches is an artifact that is present but
  malformed: a brief whose Success criterion is empty") and
  `docs/01-render-and-integrate.md:175-187` describe this check as what stops a session from
  closing silently with a bad artifact. `docs/principles.md` §5/§6 are unfilled scaffolds in
  this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here re-verified against it)
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** No ordering fields, on purpose. This instance's driver is rendered v0.57.0,
  so a batch run stays one wave (a second wave stacks and hits target #474's false T3 red).
  Nothing else in this batch (#498, #550) touches `handoff.py`, `test_handoff_reap.py` or
  `docs/01-render-and-integrate.md`. The issue's "lands after #534" is satisfied: #534 merged
  as PR #555. Open issues #558 and #559 also edit `handoff.py` (the doctor-table read and the
  dependency-clause exception, near `stop_problems` / `check_planner`). They are not in this
  batch, so whichever lands second rebases.
- **Surfaces:** data
- **Difficulty:** medium — one production module (`handoff.py`: the session-start snapshot in
  `session`, the reap in `stop_problems`, three docstrings), one doc paragraph, one test
  module. The change is local, but a reviewer must keep in mind the four registration shapes
  that share `stop_problems` and the existing tests that pin each one.
- **Scope:** Remove the gap where an unregistered planner session's written briefs are never
  re-read at reap. The work set is derived by `handoff.py` itself from the bundle root at
  session start versus reap, so no caller changes (`do_plan_batch` and the `/handoff`
  command are untouched). Update the text that promises the old behavior: the `handoff.py`
  module docstring (`:13-18`), `report_at_reap` (`:483-487`), `stop_problems` (`:586-588`),
  and `docs/01-render-and-integrate.md:181-184` ("…and does not re-read what that session
  wrote"). / out of scope: the `act` role's no-bundles rule (it has no brief to re-read);
  the id-seeded path's `allow_absent` wrinkle; a brief deleted during the session; the
  `[[doctor.checks]]` read itself (#558) and the dependency-clause exception handling
  (#559); `leaves.py` (including `_brief_snapshot` / `_fresh_plan_briefs`: do not import
  `leaves` into `handoff.py`, which is kept import-light for the hook, `handoff.py:120`, `:392`); the
  `/handoff` command and `run_check`; making the reap blocking.
- **Repro instruction:** On a clean checkout of `eduralph/pdca-harness@70ea12b`, from
  `template/`, in a scratch test using `tests/test_handoff_reap.py`'s `Base`:
  `self.reap("planner", None, during=lambda env: (handoff.record_pass(Path(env[handoff.ENV_STATE]), "issue_7"), <write issue_7 authored brief>, <write issue_8/brief.md with _brief_text(criterion="")>))`
  → the returned stderr is empty. `stop_problems` returns `out` at `handoff.py:622-623`
  because `passed` is non-empty. `PYTHONPATH=src python3 -m unittest tests.test_handoff_reap`
  is green today.
- **External dependencies:** none — the base toolchain (Python ≥ 3.11) suffices; no leaf CLI
  is spawned.
- **Test file:** `template/tests/test_handoff_reap.py` (append, in the `ReportedAtReap` class
  or a sibling class). The C4 gate (`engine/scripts/run-verify.sh`) runs every touched test
  module whole, reverts only the production hunks (the docs hunk is non-behavioral), and keeps
  the test hunks, so an appended test earns a real red. Import no new symbol at module level;
  drive it through `handoff.session` via `Base.reap`. Cover (i), (ii), (iii)'s no-change
  case and (iv) at minimum. C5 (advisory) will say "patch adds no new test file"; that is
  expected for an append.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cue: the `act` role already captures a session-start baseline inside
  `handoff.session` and carries it through the scratch file into the reap
  (`handoff.py:426-441`, read back at `:551`). Mirror that shape for the planner-without-
  bundles case. Keep what the driver registered authoritative over what the session could
  rewrite in the scratch file (`:458-465`), so a leaf cannot empty its own baseline. For the
  "created or changed" rule and the placeholder semantics, the plan-advisory pass's snapshot
  (`leaves.py:3640-3669`) is the behavior to match. Match it, don't import it.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 8 --
  template/src/pdca_harness/handoff.py` → `f8779bd` (#528 act-log append-only), `5ced9bd`
  (#481), `e9e5982` (#534, reap-time report), `900d638` (#331, the contract). None re-reads
  briefs on the unregistered path. The retired #331 Stop hook had the same gap, so it is not
  new in #534. Closed-unmerged PRs touching `handoff.py` / `test_handoff_reap.py` /
  `docs/01-render-and-integrate.md` (INTEGRATION §5 filter): none. Open PRs: none.
  Adjacent open issues on the same file: #558, #559 (see Ordering note).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Approach and tests are right; fix the two error-handling gaps the reviewer showed, both inside this brief's scope: 1. Take the session-start brief snapshot in handoff.session() ONLY when no bundle set is registered (planner with bundles empty/None). Today it runs for every planner session, so one unreadable old brief anywhere under the bundle root makes setup raise OSError and a registered single/id-seeded Plan loses its exit contract entirely — breaks criterion (vi). It is also wasted work on those paths. 2. Make brief discovery tolerate per-brief read errors (_brief_sha / _changed_plan_briefs, handoff.py:315). One unreadable brief must become its own "<bundle>: could not check (…)" item, and every other changed brief must still be checked and reported — criterion (v). Today the read raises before the per-bundle try/except and hides the others. Add tests for both: (a) a registered planner session with an unrelated unreadable brief still reports its own bundle's empty criterion; (b) an unregistered session with one unreadable brief plus one empty-criterion brief reports both. Also fix the session() docstring: it claims to "mirror leaves._brief_snapshot" but deliberately does not exclude placeholders — say what it actually does.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Approach and tests are right; fix the two error-handling gaps the reviewer showed, both inside this brief's scope:
  1. Take the session-start brief snapshot in handoff.session() ONLY when no bundle set is registered (planner with bundles empty/None). Today it runs for every planner session, so one unreadable old brief anywhere under the bundle root makes setup raise OSError and a registered single/id-seeded Plan loses its exit contract entirely — breaks criterion (vi). It is also wasted work on those paths.
  2. Make brief discovery tolerate per-brief read errors (_brief_sha / _changed_plan_briefs, handoff.py:315). One unreadable brief must become its own "<bundle>: could not check (…)" item, and every other changed brief must still be checked and reported — criterion (v). Today the read raises before the per-bundle try/except and hides the others.
  Add tests for both: (a) a registered planner session with an unrelated unreadable brief still reports its own bundle's empty criterion; (b) an unregistered session with one unreadable brief plus one empty-criterion brief reports both.
  Also fix the session() docstring: it claims to "mirror leaves._brief_snapshot" but deliberately does not exclude placeholders — say what it actually does.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
