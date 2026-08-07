# Brief — issue 384 / no-issue-mode-into-the-t4-gate

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** no-issue-mode-into-the-t4-gate
- **Defect:** `publish()` relaxes a **failed** T4 contribution gate to a printed flag whenever
  it runs under `--no-issue` (`template/src/pdca_harness/publish.py:195-206`). The premise is
  that the one thing legitimately missing is the not-yet-assigned tracker id — but the gate is
  never told which mode it ran in (`_t4_passes` exports only `PDCA_BUNDLE`,
  `publish.py:713-718`), so the amnesty covers the **whole** checker: a PR body with no
  `**User impact:**` opener, an opener that falls after Root cause, a broken commit message —
  everything `contribcheck` would have caught (`template/src/pdca_harness/cli.py:1086-1117`) is
  waved through as "pending id" and pushed. The checker already has the narrow mode
  (`contribcheck --no-issue` → `contribution_problems(d, no_issue=True)` drops *only* the
  tracker-id requirement, `cli.py:228-229,1110-1116`); publish simply never uses it.
  Secondary defect in the same function, from the #338 rework: the immediate pre-run announce
  line was dropped in favour of the heartbeat alone, so publish's first action after its guards
  is silent until the first tick — the very "reads as a hang" finding of #181. The peer gate
  runner still announces (`template/src/pdca_harness/gates.py:504`).
- **Success criterion:** With the patch applied, under `--no-issue` a bundle whose contribution
  artifacts fail T4 for **any reason other than the missing tracker id** (e.g. no
  `**User impact:**` opener) is REFUSED — publish returns non-zero and pushes nothing — while a
  bundle whose only T4 problem is the absent tracker id proceeds; and in the default (id-known)
  mode the tracker-id requirement is still enforced. The mode reaches the checker as
  `$PDCA_PENDING_ID` derived from the flag on each run, never inherited from the ambient
  environment (an inherited value is scrubbed, not honoured), and the shipped gate row consumes
  it as `contribcheck --no-issue`. Demonstrable by C4-verify alone: the named test module is red
  with the production hunks reverted and green with them applied.
- **Falsifiability:** RED is producible offline on the environment Do gets — `publish.publish(…,
  dry_run=True, pending_id=True)` is already driven in-process with a fake gate command by
  `template/tests/test_publish_slice.py:362-375` and `template/tests/test_t4_publish_gate.py`,
  needing no network, `gh`, or remote. A test asserting that a *non-tracker-id* T4 failure
  blocks a `--no-issue` publish fails on `origin/main` today: the relax branch prints and
  continues. Note that `test_publish_slice.py:362 test_no_issue_relaxes_failing_t4_to_a_flag`
  **encodes the behaviour being deleted** — Do must replace it with the new contract, not leave
  it asserting the defect. The pdca-pdca C4 wrapper counts
  `template/src/pdca_harness/publish.py` and `template/pdca.toml.jinja` as production and
  `template/tests/*.py` as tests (`engine/scripts/run-verify.sh:39-53`), so reverting the
  production hunks with the tests in place gives a real red leg.
- **Invariant to restore:** An amnesty is scoped to the thing that is legitimately missing.
  `--no-issue` states one fact — the tracker id does not exist yet — so it may relax exactly the
  tracker-id requirement; every other contribution rule stays in force, and what is left to fail
  is a real defect that blocks the push in either mode. Cited to the target's own written
  contract for the gate: T4 "audits THIS cycle's own contribution artifacts, not pre-existing
  code, so the usual 'T4 advisory' caveat does not apply" and is registered `gating = true`
  (`template/pdca.toml.jinja:920-938`); the checker's own docstring already draws the narrow
  line — "only for a real numeric ticket; a slug / `--no-issue` (pending-id) bundle legitimately
  carries no trailer" (`template/src/pdca_harness/cli.py:1108-1109`).
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** wave 0, alongside 428 and 403 — no file is shared with them
  (`publish.py` + `pdca.toml.jinja` vs `gates.py` vs `leaves.py`). **401** is briefed against the
  same T4 registration block in `template/pdca.toml.jinja` and against `contribcheck`'s
  default-open path in `cli.py`, so it declares the conflict on its side and lands in a later
  wave; nothing further is needed here. The downstream instance
  (getwyrd/wyrd-pdca#184 / #195) already ships and defends this change — it is a proven design,
  not a new one.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** one logical change — the publish-time T4 verdict must be evaluated in the mode the
  run is actually in, so the pending-id path relaxes only the tracker-id requirement and the
  blanket relax branch is deleted outright; plus the restored pre-run announce for the first
  T4 gate (with the heartbeat label unprefixed, since the announce already says "T4 gate").
  The mode must reach the shipped checker through the registered gate row in
  `template/pdca.toml.jinja`, so a rendered instance gets the behaviour without editing its own
  config. Keep the `id_pending` recording and the "add the id and re-gate before ready"
  discipline (`publish.py:369,388,489,497`) exactly as they are.
  / **out of scope:** how a *Check-time* default-open T4 row is recorded in the gate matrix
  (issue 401 — briefed separately, later wave); the `at_publish` selection rules (#339);
  any change to `contribution_problems`' lint rules themselves; the `texts_prevalidated`
  pre-pass path (`publish.py:185-190`), which must keep skipping T4 exactly as it does now.
- **Repro instruction:** from a clean worktree of `origin/main`, drive publish in dry-run
  pending-id mode as `template/tests/test_publish_slice.py:362-375` does, with a
  `pr-description.md` that has **no** `**User impact:**` opener and a `commit-msg.txt` with no
  tracker id: `publish.publish(cfg, "PEND", dry_run=True, pending_id=True)` returns 0 and prints
  the FLAGGED notice — the malformed PR body is waved through. It must return non-zero.
- **External dependencies:** `copier importable (.venv)` — the rendered config produced from
  the template is validated only by the target's root render suite, which skips itself when
  copier is not importable; the matching doctor row of exactly that id is already registered in
  this instance's config, so nothing new has to be provisioned.
- **Test file:** `template/tests/test_publish_slice.py` — extend the existing `--no-issue` group
  (replacing `test_no_issue_relaxes_failing_t4_to_a_flag:362`, which asserts the deleted
  behaviour); add the gate-side assertions to `template/tests/test_t4_publish_gate.py` if the
  env/announce contract is easier to pin there. This project's C4 gate reverts the *production*
  hunks and keeps the patch's test files (`engine/scripts/run-verify.sh:70-81`), so an edited or
  appended test earns its red; it does **not** classify on added test files. The gate runs each
  changed test module as `cd template && PYTHONPATH=src python3 -m unittest tests.<module>`.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cue — this is a composition slice, and the peer is `gates._run_check`: it derives
  each gate's environment per run (`template/src/pdca_harness/gates.py:493-502`, where
  `PDCA_BRIEF_BASE` / `PDCA_LANE` are added to `env` from the driver's own state, never
  inherited) and announces before the heartbeat at `gates.py:504`
  (`print(f"  · gate {label} …", file=sys.stderr, flush=True)`), then runs
  `progress.run_with_heartbeat(...)`. Do MAY open that callsite and mirror both — the derived
  env var and the announce-then-heartbeat shape — in `publish._t4_passes`
  (`publish.py:713-757`).
- **Prior-art check (triage cycles):** by affected file path against `origin/main` @ `9fb4860`
  (fetched 2026-08-02). `git log --oneline origin/main -- template/src/pdca_harness/publish.py`
  shows #338 (the heartbeat rework that dropped the announce) and #339 (`at_publish` selection)
  as the recent work on this function; nothing passes the mode into the gate. `gh search issues
  "contribcheck"` → #401 (open, the Check-side row status — briefed separately in this batch),
  #339/#331 (closed), and this issue. `gh pr list -R eduralph/pdca-harness --state open` → empty.
  The design is already merged and defended downstream in the wyrd-pdca instance
  (getwyrd/wyrd-pdca#184 review rounds, held through the v0.56.0 merge, #195) — this bundle
  carries it upstream.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Auto-iterate (round 1): Check found implementation-level items only, no architectural judgment required — T3 Runtime — Copier must be provided and the 7 root render/update tests rerun — all were skipped because Copier is not installed, so rendered-instance and update compatibility were not exercised despite the offline runtime suite passing.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
