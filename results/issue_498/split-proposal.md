<!-- pdca:split-proposal v1 -->
# Split proposal — issue 498

## Why this slice is oversized

Issue #498 names two fixes and says "either useful alone": (1) a per-bundle lock on the
drive path, and (2) a split hint that does not send the operator into a live run. Two build
rounds show they are two outcomes, not one:

- The **drive claim** converged. Both Check rounds found it sound: refused before any write,
  released on return / raise / SIGKILL, a run never refuses itself. What is left on it is
  test coverage for the release paths and one message (see child-1).
- The **hint** failed both rounds for a reason in the brief, not the build. v2's criterion
  asked the hint to promise that the running flow *will* drive the children, and nothing at
  accept time can know that (the run's sign-off may go unanswered, the parent may sit behind
  an unready prerequisite, or the run may already be past the parent's adoption point). It
  needs a different design: a conditional line plus an end-of-run report (child-2).

With the claim in place, following today's hint no longer races the run: a second
`pdca flow <child-ids>` claims the children first and the live run's adoption skips them
as held. So child-1 alone fixes the user impact in the issue title; child-2 makes the
wording honest. Each is its own PR.

The v2 attempt (`results/issue_498/iteration-v2/patch.diff`, 8 files, 92 KB; its suite is
also at `results/issue_498/test_flow_single_driver.py`) is the starting point for child-1.
Carry-forwards from the 2026-09-19 sign-off: item 4 (unpinned release paths) and item 5
(resume line vs refusal) → child-1; items 1–2 (conditional hint, end-of-run line), item 4's
"passed"-path half, and item 6 (the probe's false refusal) → child-2.

## Wave sketch

Two waves. child-2 `Depends on: child-1`: it reads child-1's claim to decide what to print,
and both edit `template/src/pdca_harness/cli.py` and `flow.py`, so child-2 must build on
child-1's accepted result (the wave fold gives it that). No child can run in parallel with
the other.

On this instance (driver rendered v0.57.0) a stacked second-wave bundle can show a false
advisory T3 red (#474 is fixed upstream but not in this driver). T3 is advisory; read
child-2's T3 row with that in mind, or drive child-2 in a later run after child-1 merges.

<!-- pdca:child child-1 -->
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
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
# split --accept tells the operator to run `pdca flow <child-ids>` even when a live run may drive them — and no run names the split children it did not drive

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file. Split out of #498 at its
> third Plan; builds on the sibling child's drive claim (one live driver per bundle).

- **Slug:** split-hint-honest-about-a-live-run
- **Defect / goal:** `pdca split <id> --accept` always ends with
  `"<parent> marked split; run `pdca flow <child-ids>` to drive the children"`
  (`template/src/pdca_harness/cli.py:843-844`). Since #469/#473 a live run adopts the
  children of a split parent it is driving (`flow.py:1554`) or was handed as a seed
  (`flow.py:1784-1797`), and a CSV batch sweeps every in-flight bundle after its Plan
  session (`flow.py:1673-1692`), so the bare instruction tells the operator to start a
  second driver over bundles a live run may be about to drive. The model-facing text says
  the same (`template/agents/planner.md.jinja:155`, `:182-183`; `leaves.py:1119-1120`;
  `docs/07-crosscutting.md:340-343`). And when a live run does NOT reach a split parent's
  children (its sign-off goes unanswered, the parent sits behind an unready prerequisite,
  or the split lands after the parent's adoption point), nothing at the end of the run
  names them: they sit PLANNED with no line pointing at them.
  Two earlier rounds (#498 v1/v2) tried to make the line **promise** the run would drive
  the children; nothing at accept time can know that, so this brief asks for an honest
  conditional line plus an end-of-run report instead.
- **Success criterion:** Through `cli._split` and `cli._flow`, with the patch:
  (i) **In reach of a live run, the line is conditional.** When `split --accept` completes
  while (a) a live `pdca flow` run holds the parent (the sibling child's claim) — whether
  the accept runs from that run's own Plan or sign-off session or from another shell — or
  (b) a live CSV batch run (`pdca flow --from-csv`) has not yet swept its in-flight bundles
  (`flow.py:1678`), then today's line is **not** printed. In its place one line that: starts
  `<parent> marked split;`, names every child id, says that run drives them only if it
  reaches them and lists any it did not drive when it ends, and gives `pdca flow
  <child-ids>` (via `_prog()`, as today) for use after that run has ended. It never
  promises ("will drive") and never says "do not start another flow". Suggested wording:
  `issue_500 marked split; a running \`pdca flow\` holds issue_500 and drives its children
  (601 602) if it reaches them — it lists any it did not drive when it ends. After that
  run ends, drive any left with \`pdca flow 601 602\``.
  (ii) **Otherwise, today's line byte-identical.** A standalone accept, an accept after the
  run has ended (returned, raised or was killed), and an accept on a parent the live run
  has let go (e.g. a named id it skipped) print exactly
  `<parent> marked split; run \`<prog> flow <ids>\` to drive the children`.
  (iii) **End-of-run report.** Just before `_drive_and_act` returns (`flow.py:1641-1646`,
  so both CLI shapes and the CSV batch get it), for every split parent in the run's drive
  set or its adoption seeds, the run names on stderr every lineage child that is not
  terminal and not in the run's final drive set — one line per parent, with a
  `pdca flow <ids>` command. It walks through a child that is itself terminal on a split,
  as adoption does (`flow.py:1216-1231`). No such children → no line. The exit code is
  unchanged. Probe: `pdca flow 7 8` with 8 `Conflicts with: 7`, nobody answers 7's
  sign-off; while A drives 8, a split of 7 is accepted from another shell (the line is
  (i)'s conditional one, since A still holds 7); when A ends it names 7's children with
  `pdca flow 701 702`.
  (iv) **Checking never causes a false refusal.** Whatever the accept does to learn whether
  a live run holds the parent must never make a concurrent `pdca flow` over that bundle
  refuse it as "held by another run" when no run holds it. If the check can collide with a
  claim attempt, the claim side retries past it, pinned by a test that forces the
  collision deterministically.
  (v) **The text agrees.** `template/agents/planner.md.jinja:155` and `:182-183`, the
  planner seed prompt at `leaves.py:1119-1120`, and `docs/07-crosscutting.md:340-343` say
  what `--accept` now prints and when, and mention the end-of-run report.
  (vi) **Nothing else changes.** Every other line of `cli._split` and the existing
  adoption reports (`flow.py:980-985`, `:1041-1056`, `:1115`, `:1245`) are byte-identical;
  the whole `template/tests` suite stays green. Every branch that changes which line
  `--accept` prints, or whether the end-of-run report fires, has a test that fails if that
  branch is deleted.
  Shown by the named test going red on this child's base (the in-flow accept prints
  today's instruction; no end-of-run line) and green with the fix.
- **Falsifiability:** RED is reachable offline on the base toolchain (stdlib Python ≥ 3.11
  + git), stub leaves, empty gates, on the base this child builds on (the sibling child's
  accepted result: the drive claim exists, the line is still unconditional, no end-of-run
  report). `template/tests/test_flow_adopt_split.py:43-63` drives real `cli._flow` runs;
  `:190-216` swaps a stub leaf for a stand-in that acts mid-run — for the in-run case the
  stand-in calls `cli._split(cfg, SimpleNamespace(issue_id=…, accept=True, ids="601,602"))`
  and the test captures stderr. For "another shell" cases run A as a **real subprocess**
  paused inside a stand-in leaf, and call `cli._split` from the test process. Bound every
  wait with a timeout so the red leg fails instead of hanging C4. For (iii), the probe in
  the criterion is the red case: on the base A ends with 701/702 PLANNED and no line naming
  them.
- **Invariant to restore:** The driver never tells the operator something about a live run
  that the run cannot guarantee, and every child a split produced is either driven by the
  run that could reach it or named, with the command that drives it, by the time that run
  ends. Source: internal project invariant (Tier C) — the flow's own "never silent" rule
  for work it walks away from (#260, `_warn_abandoned` `flow.py:750-777`) and for held
  children (`_report_held` `flow.py:780-797`), applied to split children. Scope names no
  mechanism; guarding `cli.py`'s line alone cannot satisfy the second half.
- **Repo + branch target:** eduralph/pdca-harness @ main (base `70ea12b` plus the sibling
  child's accepted change; line numbers here are on `70ea12b`, verified 2026-09-19 —
  re-locate them on the stacked base)
- **Depends on:** child-1
- **Ordering note:** Depends on the drive-claim child: it reads that claim to decide what to
  print, and both edit `cli.py` and `flow.py`. On this v0.57.0 instance a stacked
  second-wave bundle may show a false advisory T3 red (#474, fixed upstream only).
- **Surfaces:** data
- **Difficulty:** medium — the tail of `cli._split`, the end of `_drive_and_act`, a
  live-holder check built on the sibling's claim, and model-facing text in three places.
- **Scope (one logical fix) / out of scope:** Make `split --accept`'s closing line depend
  on whether a live run can reach the children, word it as a condition rather than a
  promise, add the end-of-run report of split children the run did not drive, and update
  the text that describes `--accept`'s output. / out of scope: the claim mechanism itself
  and its refusal / release rules (the sibling child's); the adoption algorithm (what is
  adopted, wave levelling, budget); `_terminal_hint` (`flow.py:710-747`); the `--ids` /
  filing / error branches of `cli._split` (`cli.py:721-842`); the other adoption report
  lines listed in (vi); single-step verbs; cross-host coordination.
- **Reproduction:** On the sibling child's accepted result, from `template/`: with
  `tests/test_flow_adopt_split.py`'s stub fixture, make 500's stand-in Plan leaf call
  `cli._split(cfg, SimpleNamespace(issue_id="500", accept=True, ids="601,602"))` inside a
  `cli._flow` run over 500 — stderr carries `issue_500 marked split; run \`… flow 601
  602\` to drive the children` while the same run drives 601/602 itself. Then run the
  (iii) probe: A ends with 701/702 PLANNED and no line naming them.
- **External dependencies:** none — the base toolchain (Python ≥ 3.11, git) suffices; stub
  leaves, no vendor CLI, no network.
- **Test file:** `template/tests/test_split_hint_live_run.py` (**new**). **C4 red-leg import
  trap:** the red leg reverts this child's production hunks and keeps the test; a
  module-level import of a symbol THIS child adds fails to load and records
  `PDCA-UNVERIFIABLE`, not red. Import only modules on the base
  (`from pdca_harness import cli, flow, split, state`) and drive the behaviour through
  `cli._flow` / `cli._split`. Do not import helpers from `test_flow_single_driver.py` or
  any other test module; copy what you need. A subprocess leg must set `PYTHONPATH` to the
  checkout's `template/src` and must not inherit `PDCA_*` from the gate's environment.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  The line to replace: `cli.py:843-844`. The end-of-run point: `_drive_and_act`'s tail
  (`flow.py:1641-1646`); mirror the walk of `_adopt_split_children` (`flow.py:1216-1231`,
  via `_adoptable` `flow.py:913`) and the lineage read of `_lineage_children`
  (`flow.py:690-707`); keep the report shape of `_warn_abandoned` (`flow.py:773-777`). The
  live-holder check builds on the sibling child's claim — reuse it, do not add a second
  lock. From #498 v2 (`results/issue_498/iteration-v2/patch.diff`): its hint half answered
  "will drive" and was rejected for that; do not re-attempt it unchanged. Its CSV-batch
  "not swept yet" mark (`sweeping`) and its probe collision (`_held_now` vs `take()`
  without retry) are the known pitfalls for (i)(b) and (iv).
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main -n 6
  -- template/src/pdca_harness/cli.py template/src/pdca_harness/flow.py` → `6ddfca4` /
  `51a65a2` (#475), `9a19cb5` (#466), `a2eefe1` (#459), `389bf1a` / `96c9704` (#469/#473) —
  none conditions the closing instruction or reports un-driven split children. Open PRs
  touching `cli.py` / `flow.py` / `split.py`: none. Closed-unmerged: none. Prior attempts:
  #498 `iteration-v1/`, `iteration-v2/` (hint half sent back to Plan both times).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
<!-- pdca:end child-2 -->
