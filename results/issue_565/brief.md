# flow: two `pdca flow` runs can drive the same bundle at once — nothing on the drive path claims a bundle, so their writes interleave

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file. Split out of #498 at its
> third Plan; the sibling child makes `split --accept`'s closing line honest and depends
> on this one.

- **Slug:** one-live-driver-per-bundle
- **Defect / goal:** Nothing stops two drivers from holding the same bundle. No drive-path
  code takes any ownership of a bundle; the only cross-process claim in the driver is Act's
  session lock (`template/src/pdca_harness/act.py:125-159`). Bundle state is plain files in
  `results/issue_<id>/`, so two `pdca flow` runs over overlapping ids (named ids, a CSV
  batch's in-flight sweep, split adoption) write the same bundle's artifacts with no
  ordering. The same race is how following `split --accept`'s printed `pdca flow
  <child-ids>` inside a live run goes wrong (#498).
- **Success criterion:** Through the CLI entry point `cli._flow`, with the patch:
  (i) **A second driver over a held bundle is refused.** While run A (`pdca flow` naming 7)
  is mid-drive, run B — a `pdca flow` whose named ids include 7 — exits non-zero **before it
  changes any bundle's state** (before `flow_ids`' RESOLVED revalidation, `flow.py:1747-1756`,
  and its Plan pre-pass, `:1760-1766`), printing a line that names `issue_7` as held by
  another run. Nothing under `results/` changes because of B.
  (ii) **Implicit reach is skipped, not refused.** A CSV batch's in-flight sweep
  (`flow.py:1678-1692`) and split adoption (`_adopt_split_children`, `flow.py:1119`) each
  skip a bundle another live run holds, print a line naming it, and the rest of that run
  continues.
  (iii) **The claim ends with the run.** After A returns — normally or by raising — a new
  run over 7 proceeds. A run whose process is killed (SIGKILL) leaves nothing that stops a
  later run.
  (iv) **A run never refuses itself.** A's own in-process steps, and every leaf or command A
  spawns (including `pdca split --accept` run from A's Plan or sign-off session), are not
  refused or blocked by A's claims. A bundle A adopts becomes A's under the same rules.
  (v) **A claim that cannot be recorded fails closed.** If the claim cannot be opened or
  locked for a reason other than another run holding it (an unwritable process dir, a
  filesystem without locks), a named id refuses the run non-zero before any write, and an
  implicitly reached one is skipped with a line saying why — the way `act_session` reports
  and skips when its lock cannot be opened (`act.py:143-151`).
  (vi) **A bundle the run decides not to drive is let go at that decision**, so another run
  can take it while A goes on: a named id `flow_ids` skips (no brief, `flow.py:1774-1777`;
  terminal, `:1778-1798` — a split parent handed on as an adoption seed is let go once its
  adoption pre-pass, `flow.py:1482-1484`, is done), a swept bundle `waves.partition_schedulable` holds
  (`flow.py:1692-1697`, including the "nothing schedulable" return), children whose
  reschedule fails (`flow.py:1242-1247`), and a child a later reschedule retracts
  (`flow.py:1261-1270`). **Every one of these release points has a test that fails if that
  release is deleted** (the v2 adversary deleted five such lines with all 63 tests still
  green).
  (vii) **A resume line agrees with the refusal.** When a run prints `resume with \`pdca
  flow N\`` for a bundle it still holds and then keeps running (`_warn_abandoned`,
  `flow.py:777`, reached mid-run from `_drive_wave` `:1362` / `:1399`), the run keeps the
  claim — it still sweeps that bundle's footprint (`flow.py:1641`) and may run Act — and the
  line says the command applies once this run has ended (today's text stays a prefix, so
  existing assertions hold). A `pdca flow N` from another shell meanwhile is refused per (i).
  (viii) **Nothing else changes.** A single run with no second driver behaves and prints
  exactly as today apart from (vii)'s suffix; `split --accept`'s closing line
  (`cli.py:843-844`) is byte-identical (the sibling child owns it); the whole
  `template/tests` suite stays green.
  Shown by the named test going red on the base (B proceeds and drives 7) and green with
  the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11
  + git), stub leaves, empty gates. `template/tests/test_flow_adopt_split.py:43-63`
  (`_stub_config`) drives real `cli._flow` runs with every leaf stubbed, and `:190-216`
  swaps a stub leaf for a stand-in that acts mid-run. Pause run A inside a stand-in leaf
  and start run B while A is paused: on the base B returns 0 with 7's files changed.
  **B must be a real subprocess** (the claim may be per-process, so an in-process thread
  could pass for the wrong reason). Bound every wait with a timeout so the red leg fails
  instead of hanging C4. The SIGKILL half of (iii) is shown by a subprocess killed while
  holding the claim. v2's suite showed this red on the base for real reasons.
- **Invariant to restore:** At most one live driver advances a given bundle at a time, and
  a claim lives exactly as long as the run that took it — on every CLI drive path (named
  ids, CSV batch sweep, split adoption), not only the split case. Source: internal project
  invariant (Tier C). The target states bundle state is only the files in the bundle
  (`template/CLAUDE.md.jinja:13-14`, "nothing is hidden in a database"), so two writers
  have nothing to serialize on; Act's session lock states the same rule for its own
  resource (`act.py:125-141`). Structural (process lifetime / ownership): Scope names no
  mechanism, and no single module's guard satisfies it.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `70ea12b`; every `path:line`
  here verified against it on 2026-09-19)
- **Ordering note:** No ordering fields: this child is independent. The sibling child depends on this one (it reads this claim and edits
  the same `cli.py` / `flow.py`), so it builds on this child's accepted result.
- **Surfaces:** data
- **Difficulty:** high — changes who may drive a bundle on every CLI drive path
  (`cli._flow`, `flow_ids`, `flow_batch`, `_adopt_split_children`), adds a cross-process
  ownership rule with lifetime, self-exemption and fail-closed requirements, and adds
  release points across several branches.
- **Scope (one logical fix) / out of scope:** Make bundle ownership by a live run exclusive
  for the life of the run on every CLI drive path, with the release, fail-closed and
  resume-line behaviour above. Document the rule in `docs/07-crosscutting.md`, and name the
  known gap there: a CSV batch's Plan session runs before any claim is taken and can rewrite
  or split a bundle another run holds. Keep any ownership record out of every bundle and out
  of results commits (gitignored in the render). / out of scope: **`split --accept`'s
  closing line and every text that describes it** (`cli.py:843-844`,
  `template/agents/planner.md.jinja:155` and `:182-183`, `leaves.py:1119-1120`,
  `docs/07-crosscutting.md:340-343`) — the sibling child's; `pdca run` / `signoff` /
  `publish` and other single-step verbs (note the gap in `build-notes.md`); the library-only
  `flow.flow()` (`flow.py:379`, not a CLI route); lane and worktree locks (`lane.py`,
  `worktree.py`); the adoption algorithm (what is adopted, wave levelling, budget);
  claiming during the Plan session itself; cross-host coordination; Windows beyond not
  breaking import.
- **Reproduction:** On `eduralph/pdca-harness@70ea12b`, from `template/`: with
  `tests/test_flow_adopt_split.py`'s stub fixture, pause a `cli._flow` run over 7 inside a
  stand-in leaf and run `cli._flow` over 7 in a second process. The second run drives 7 to
  COMPLETE while the first still holds it. `grep -n "lock" src/pdca_harness/flow.py
  src/pdca_harness/driver.py` finds no ownership check.
- **External dependencies:** none — the base toolchain (Python ≥ 3.11, git) suffices; stub
  leaves, no vendor CLI, no network.
- **Test file:** `template/tests/test_flow_single_driver.py` (**new**). **C4 red-leg import
  trap:** the red leg reverts the production hunks and keeps every `template/tests/*` hunk
  (`engine/scripts/run-verify.sh`); a module-level import of a symbol this patch adds fails
  to load on the red leg and records `PDCA-UNVERIFIABLE`, not red. Import only modules that
  exist on the base (`from pdca_harness import cli, flow, split, state`) and drive the
  behaviour through `cli._flow`. Do not import helpers across test modules; copy the stub
  fixture shape from `test_flow_adopt_split.py:43-63`. A subprocess leg must set
  `PYTHONPATH` to the checkout's `template/src` and must not inherit `PDCA_*` from the
  gate's environment.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  Peer to mirror: `act.act_session` (`template/src/pdca_harness/act.py:125-159`) — a
  non-blocking claim that reports rather than crashes when it cannot open its file and is
  released when its process ends — with the cross-platform `_lock_exclusive(fh, wait=False)`
  / `_unlock` helpers (`act.py:29-62`, no hard `import fcntl` at load time); its lock file
  is gitignored in the render (`template/.gitignore.jinja:34-38`). Take the claim in the
  process that drives: `pdca flow` may first re-exec itself under a keep-awake inhibitor
  (`cli.py:131-148`, called at `:433`), and a claim taken before that exec is lost or
  collides with the process after it. Adoption's skip line keeps the shape of the existing
  "NOT adopted: …" reports (`flow.py:1041-1056`). **Prior attempt to carve from:**
  `results/issue_498/iteration-v2/patch.diff` (reviewed sound on this half). Take its claim
  mechanism and CLI/flow wiring; leave out everything that exists only to answer the hint
  (`drive_claim.py`'s `_PASSED` / `Run.passed`, `_held_now`, `sweeping` and the sweep
  marks, `drives_children`; the `cli._split` hunk; the `planner.md.jinja` / `leaves.py`
  hunks). Its suite (`results/issue_498/test_flow_single_driver.py`) holds the lock tests
  to keep; the "(v) the hint is truthful" tests go to the sibling.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 6
  -- template/src/pdca_harness/cli.py template/src/pdca_harness/flow.py` → `6ddfca4` /
  `51a65a2` (#475), `9a19cb5` (#466), `a2eefe1` (#459), `389bf1a` / `96c9704` (#469/#473) —
  none adds drive ownership. Open PRs touching `cli.py` / `flow.py` / `split.py`: none.
  Closed-unmerged PRs touching them or a `drive_claim` module: none. Tracker search "drive
  claim OR concurrent flow OR lock bundle": #130 (closed; the harness checkout, a different
  resource). Prior attempts: #498 `iteration-v1/`, `iteration-v2/`.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
