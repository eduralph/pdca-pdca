# Brief — issue 498 / one-live-driver-per-bundle-and-a-truthful-split-hint

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** one-live-driver-per-bundle-and-a-truthful-split-hint
- **Defect:** Two linked problems.
  (a) **The hint is wrong inside a flow.** `pdca split <id> --accept` always ends with
  `"<parent> marked split; run `pdca flow <child-ids>` to drive the children"`
  (`template/src/pdca_harness/cli.py:843-844`). That was true before #469/#472. Now every CLI
  `pdca flow` shape drives the children of a split accepted during its own run. An id run
  hands a split parent to `_drive_and_act` as an adoption seed (`flow.py:1784-1803`) or adopts
  a mid-run split (`_adopt_split_children`, `flow.py:1119`). A CSV batch sweeps every
  in-flight bundle after its Plan session (`flow.py:1673-1698`). The planner role prompt
  says the same (`template/agents/planner.md.jinja:164-169`). So an operator who follows the
  printed instruction starts a second driver over bundles the first run is about to drive.
  (b) **Nothing stops two drivers from holding the same bundle.** No drive-path code takes any
  ownership of a bundle. The only cross-process claim in the driver is Act's
  (`act.py:125-159`), so the race is reachable by any two `pdca flow` runs over overlapping
  ids, with or without the hint. State is plain files in `results/issue_<id>/`, so two
  interleaved drivers write the same bundle's artifacts with no ordering.
- **Success criterion:** With the patch, through the CLI entry points (`cli._flow`,
  `cli._split`):
  (i) **A second driver over a bundle a live run holds is refused.** While run A (`pdca flow`
  naming id 7) is mid-drive, run B, a `pdca flow` whose named ids include 7, exits non-zero
  **before it changes any bundle's state**. That includes `flow_ids`' RESOLVED revalidation
  and its Plan pre-pass. It prints a line naming `issue_7` as held by another run. Nothing
  under `results/` changes because of B.
  (ii) **Implicit reach is excluded, not refused.** A CSV batch's in-flight sweep, and split
  adoption, both skip a bundle a different live run holds. Each prints a line naming it, and
  the rest of that run continues.
  (iii) **The claim ends with the run.** After A returns, normally or by raising, a new run
  over 7 proceeds. A run whose process dies (SIGKILL, host crash) leaves nothing that stops
  a later run.
  (iv) **A run never refuses itself.** A's own in-process steps, and every leaf or command
  spawned inside A (including `pdca split --accept` run from A's Plan session), are not
  refused or blocked by A's claim. Bundles A adopts become A's, so the same rules cover them.
  (v) **The hint is truthful.** When `split --accept` runs while a live run will drive that
  parent's children, it does not print the `run pdca flow <child-ids>` instruction. It says
  instead that the running flow will drive them. This covers the parent being in the run's
  drive set on an id run, and the Plan session of a CSV batch run. When no live run will
  drive them (a standalone accept from a shell, or an accept inside a run that is not
  driving that parent), the instruction is printed **byte-identical to today's**.
  (vi) Nothing else changes: a single run with no second driver behaves and prints exactly
  as today, apart from (v)'s line, and the whole `template/tests` suite stays green.
  Shown by the named test going red on the base (B proceeds and drives 7; the in-flow accept
  prints the instruction) and green with the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11 +
  git), with stub leaves and empty gates, in the target checkout Do gets.
  `template/tests/test_flow_adopt_split.py` already drives real `cli._flow` runs with all six
  leaves stubbed (`_stub_config`, `:43-63`). It also swaps a stub leaf for a stand-in that
  acts mid-run (`_arm` → `splitting_plan`, `:190-216`, which calls the production
  `split.accept`). For (v), the stand-in calls `cli._split(cfg, SimpleNamespace(issue_id=…,
  accept=True, ids="601,602"))` instead, so the real hint is printed and captured. For
  (i)/(iii), pause run A inside a stand-in leaf (for example, wait on an event) and start run
  B while A is paused. On the base, B proceeds and returns 0 with 7's files changed, so the
  assertion fails for a real reason. **B must be a separate process, or a separate thread
  that the mechanism cannot tell apart from a separate process.** If Do's claim is
  per-process, an in-process thread can pass for the wrong reason, so the test must then run
  B as a real subprocess. Bound every wait with a timeout, so the red leg fails instead of
  hanging the C4 gate. The SIGKILL half of (iii) may be shown by a subprocess killed while
  holding the claim. If that is not feasible offline, say so in `build-notes.md` and cover
  the "returns by raising" half.
- **Invariant to restore:** At most one live driver advances a given bundle at a time, and a
  claim lives exactly as long as the run that took it. The driver never tells the operator to
  start a driver that would break this. This holds for every CLI drive path (named ids, CSV
  batch, split adoption), not only for the split-hint case. Source: internal project
  invariant (Tier C). The target states that bundle state is only the files in the bundle
  (`template/CLAUDE.md.jinja:13-14`: "nothing is hidden in a database"), so two writers have nothing to
  serialize on. The one existing cross-process claim, Act's session, states the
  same rule for its resource (`act.py:125-141`). `docs/principles.md` §5/§6 are unfilled
  scaffolds in this instance, so no §6 category gate applies. This is treated as a
  structural (process-lifetime / ownership) defect, so the Plan-exit gate was applied: Scope
  names no mechanism, and guarding `cli.py`'s hint alone cannot satisfy the invariant.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here re-verified against it. #481's accept-path change is already merged as PR #561.)
- **Depends on:** none
- **Conflicts with:** none
- **Ordering note:** No ordering fields, on purpose. This instance's driver is rendered v0.57.0,
  so a batch run stays one wave (a second wave stacks and hits target #474's false T3 red).
  Shared file in this batch: `leaves.py`. This slice changes only the planner-prompt sentence
  at `:1119-1120`; #550 changes `:3710`, about 2,600 lines away, so the hunks merge cleanly in
  either order. The prerequisite in `plan-0.60-bug-order.md` run 5 ("after 481 merged") is
  met. #496 (test-only pin of "a split never aborts the flow") is meant to run **after** this
  lands, so it pins the final behavior.
- **Surfaces:** data
- **Difficulty:** high — it changes who may drive a bundle across every CLI drive path
  (`flow_ids`, `flow_batch`, split adoption in `_adopt_split_children`) and the accept path
  in `cli.py`, adds a cross-process ownership rule with lifetime and self-exemption
  requirements, and updates model-facing text in three places. A reviewer must keep all of
  them in mind together.
- **Scope:** One logical fix: make bundle ownership by a live run exclusive for the life of
  the run, and make `split --accept`'s closing instruction depend on whether a live run will
  drive the children. Update the text that says `--accept` always prints the instruction:
  `template/agents/planner.md.jinja:155` and `:182-183`, the planner seed prompt at
  `leaves.py:1119-1120`, and `docs/07-crosscutting.md:340-343`. / out of scope:
  `pdca run`, `pdca signoff`, `pdca publish` and other single-step verbs (note the gap in
  `build-notes.md`; it is not fixed here); the library-only `flow.flow()` (`flow.py:379`, not
  a CLI route, does not adopt, `:401-406`); lane-level locking and worktree locks (`lane.py`,
  `worktree.py`); the adoption algorithm itself (what is adopted, wave levelling, budget);
  the `--ids`/filing branches of `split --accept` other than the final instruction; the
  "already marked split by another run" message (`cli.py:822-831`); `--from-briefs`
  seeding of *missing* bundles in `cli._flow` (`:577-588`); cross-host coordination (one
  host is assumed); Windows behavior beyond not breaking import (see Citations).
- **Repro instruction:** On a clean checkout of `eduralph/pdca-harness@70ea12b`, from
  `template/`: (a) read `src/pdca_harness/cli.py:843-844`, which is unconditional. With
  `tests/test_flow_adopt_split.py`'s stub fixture, make the parent's stand-in Plan leaf call
  `cli._split(cfg, SimpleNamespace(issue_id="500", accept=True, ids="601,602"))` inside a
  `cli._flow` run over 500. Captured stderr contains
  `issue_500 marked split; run \`… flow 601 602\` to drive the children`, and the same run
  then drives 601 and 602 itself. (b) Pause a stubbed `cli._flow` run over 7 inside a leaf and
  call `cli._flow` over 7 again. The second run drives 7 to COMPLETE while the first is still
  holding it. `grep -n "lock" src/pdca_harness/flow.py src/pdca_harness/driver.py` finds no
  ownership check.
- **External dependencies:** none — the base toolchain (Python ≥ 3.11, git) suffices; stub
  leaves, no vendor CLI, no network.
- **Test file:** `template/tests/test_flow_single_driver.py` (**new**). A new file, so C5
  (advisory, keys on newly added test files) checks it. **C4 red-leg import trap:** the red
  leg reverts the production hunks and keeps every `template/tests/*` hunk
  (`engine/scripts/run-verify.sh`). A module-level import of a symbol this patch adds fails
  to load on the red leg, and the gate records that as `PDCA-UNVERIFIABLE`, not red. Import
  only modules that already exist (`from pdca_harness import cli, flow, split, state`) and
  drive the behavior through the entry points that already exist (`cli._flow`, `cli._split`).
  Do not import helpers across test modules. Copy the stub fixture shape from
  `test_flow_adopt_split.py:43-63`. A subprocess leg, if used, must set `PYTHONPATH` to the
  checkout's `template/src` and must not inherit `PDCA_*` from the gate's environment.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Composition cue: `act.act_session` (`template/src/pdca_harness/act.py:125-159`) is the
  existing cross-process claim to mirror. It is non-blocking by default, reports rather than
  crashes when it cannot open its file, releases when its process ends, and uses the
  cross-platform `_lock_exclusive(fh, wait=False)` helper (`act.py:29-62`: a Unix branch
  and a Windows branch, with no hard `import fcntl` at load time). Its lock file is
  gitignored in the render (`template/.gitignore.jinja:38`). Any ownership record must also
  stay out of `state.state()`'s view and out of the results commits, so it can never be read
  as a bundle artifact. Take the claim in the process that drives. `pdca flow` may first
  re-exec itself under a keep-awake inhibitor (`cli.py:131-148`, called at `:433`). A claim
  taken before that exec is either lost or collides with the process that runs after it.
  Adoption's refusal lines should keep the shape of the existing "NOT adopted: …" reports
  (`flow.py:1041-1056`).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 8 --
  template/src/pdca_harness/cli.py template/src/pdca_harness/flow.py` → `9a19cb5` (#466 stub
  guard), `a2eefe1` (#459 convergence before accept), `96c9704` / `389bf1a` (#469/#473
  adoption), `4814b3d` (#468 one results map), `51a65a2` (#475). None touch the closing
  instruction's condition or add drive ownership. Closed-unmerged PRs touching `cli.py` /
  `flow.py` / `leaves.py` (INTEGRATION §5 filter): none. Open PRs: none. Tracker search
  `lock` / `concurrent`: #130 (closed: git maintenance under a live flow corrupting the
  *harness* checkout — a different resource), #19 (closed: in-driver lanes). No prior
  attempt at a drive-path claim.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Core claim mechanism is sound (OS lock, released on return/raise/SIGKILL, taken after the keep-awake re-exec). Rebuild to close these gaps from the Check review: 1. Fail closed when a claim cannot be recorded. Run.take() (drive_claim.py:128, :136) returns "" on an open failure or a non-contention lock failure, so the run proceeds without exclusivity (reviewer reproduced a second run writing a held bundle). Refuse named ids (cli._flow, exit non-zero, before any write) and skip implicit ones (CSV sweep, adoption), each with a report line — as act_session does when its lock cannot be opened (act.py:140). 2. Release swept claims the batch does not drive. flow.py ~:1729 claims every swept bundle before waves.partition_schedulable holds the unschedulable ones (~:1738); release every held name right after the partition (and on the "nothing schedulable" early return), matching adoption's dropped -> claims.release. Add tests for release paths (this case and adoption's dropped children) — none exist today. 3. The CSV-sweep hint needs a live run. drives_children (drive_claim.py:249) trusts an inherited SWEEP_ENV token; also check that the run holding that token is still live, and print today's instruction when it has ended. 4. Soften docs/07-crosscutting.md (~:469 "Those processes never share a bundle") to name the known gap: a CSV batch's Plan session runs before any claim and can rewrite briefs / split a bundle another run holds. Widening claims to the Plan session is out of scope (separate issue). 5. Criterion (v): the first sentence wins — when a live run will drive the parent's children, the hint must say so even if the accept runs from another shell. Check the parent's live claim regardless of RUN_ENV (the _held_now path); print today's instruction only when no live run holds the parent. 6. Narrow the drive_claim.py module docstring (:18-22): the two-runs-on-two-threads guarantee holds for the lock, not for the env-var hint state.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Core claim mechanism is sound (OS lock, released on return/raise/SIGKILL, taken after the keep-awake re-exec). Rebuild to close these gaps from the Check review:
  1. Fail closed when a claim cannot be recorded. Run.take() (drive_claim.py:128, :136) returns "" on an open failure or a non-contention lock failure, so the run proceeds without exclusivity (reviewer reproduced a second run writing a held bundle). Refuse named ids (cli._flow, exit non-zero, before any write) and skip implicit ones (CSV sweep, adoption), each with a report line — as act_session does when its lock cannot be opened (act.py:140).
  2. Release swept claims the batch does not drive. flow.py ~:1729 claims every swept bundle before waves.partition_schedulable holds the unschedulable ones (~:1738); release every held name right after the partition (and on the "nothing schedulable" early return), matching adoption's dropped -> claims.release. Add tests for release paths (this case and adoption's dropped children) — none exist today.
  3. The CSV-sweep hint needs a live run. drives_children (drive_claim.py:249) trusts an inherited SWEEP_ENV token; also check that the run holding that token is still live, and print today's instruction when it has ended.
  4. Soften docs/07-crosscutting.md (~:469 "Those processes never share a bundle") to name the known gap: a CSV batch's Plan session runs before any claim and can rewrite briefs / split a bundle another run holds. Widening claims to the Plan session is out of scope (separate issue).
  5. Criterion (v): the first sentence wins — when a live run will drive the parent's children, the hint must say so even if the accept runs from another shell. Check the parent's live claim regardless of RUN_ENV (the _held_now path); print today's instruction only when no live run holds the parent.
  6. Narrow the drive_claim.py module docstring (:18-22): the two-runs-on-two-threads guarantee holds for the lock, not for the env-var hint state.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: The claim/lock half is sound (refused before any write, released on return/raise/SIGKILL, a run never refuses itself) — keep it. The split-hint half has failed two rounds because criterion (v) asks for something no check at accept time can know: whether this run will actually reach the split parent's children (its sign-off may go unanswered, it may sit behind an unready dependency, or its adoption read may already be past). Re-plan criterion (v) so it is decidable: 1. Make the in-flow hint conditional and honest, e.g. "the running `pdca flow` will adopt the children (…) if issue_N closes as split in this run", instead of an unconditional "will drive them — do not start another flow". 2. Add an end-of-run line naming split children the run was expected to adopt but did not, with the command to drive them. 3. Consider splitting the hint into its own issue so the drive-claim lock can ship on its own (pdca-pdca split <id> there, if the planner judges it two outcomes). Carry into the next brief too: 4. Tests for the release/"passed" paths the adversary showed are unpinned (flow.py:1900-1901, :1291, :1314, :1562, :1705 — each deletable with all 63 tests green). 5. The run prints "resume with `pdca flow 7`" and then refuses it while it still holds 7: either keep the claim and say "once this run ends", or release it — pick one and make the line and drive_claim.py:15-19 agree. 6. Run.take() should retry on the transient _held_now probe collision the way _hold_new already does (drive_claim.py:197-206 vs :266-274), so no false "held by another run" refusal.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  The claim/lock half is sound (refused before any write, released on return/raise/SIGKILL, a run never refuses itself) — keep it. The split-hint half has failed two rounds because criterion (v) asks for something no check at accept time can know: whether this run will actually reach the split parent's children (its sign-off may go unanswered, it may sit behind an unready dependency, or its adoption read may already be past). Re-plan criterion (v) so it is decidable:
  1. Make the in-flow hint conditional and honest, e.g. "the running `pdca flow` will adopt the children (…) if issue_N closes as split in this run", instead of an unconditional "will drive them — do not start another flow".
  2. Add an end-of-run line naming split children the run was expected to adopt but did not, with the command to drive them.
  3. Consider splitting the hint into its own issue so the drive-claim lock can ship on its own (pdca-pdca split <id> there, if the planner judges it two outcomes).
  Carry into the next brief too:
  4. Tests for the release/"passed" paths the adversary showed are unpinned (flow.py:1900-1901, :1291, :1314, :1562, :1705 — each deletable with all 63 tests green).
  5. The run prints "resume with `pdca flow 7`" and then refuses it while it still holds 7: either keep the claim and say "once this run ends", or release it — pick one and make the line and drive_claim.py:15-19 agree.
  6. Run.take() should retry on the transient _held_now probe collision the way _hold_new already does (drive_claim.py:197-206 vs :266-274), so no false "held by another run" refusal.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
