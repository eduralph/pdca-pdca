<!-- pdca:split-proposal v1 -->
# Split proposal — issue 395

<!-- Each child is a COMPLETE brief, not a sketch. A filled Slug alone makes `state.state`
     classify the materialised file as PLANNED, so `pdca flow` skips Plan and sends it
     straight to Do — a child missing `Repo + branch target` then builds successfully and
     has nowhere to publish. Fill every field. -->

<!-- Delimiters are HTML comments, not headings, DELIBERATELY: each child body is a full
     draft brief and may contain arbitrary headings and fenced code blocks, so anything
     that could also appear inside a child cannot be its boundary. `pdca split --accept`
     parses these markers; keep them exactly as written. -->

## Why this slice is oversized

Nine iterations carried three separate outcomes in one patch (about 125 KB at iteration 9).
Two of them are defects that exist on `main` today and have nothing to do with the
same-wave check. They came in as carry-forwards from sign-off (iteration 7 and iteration 8):

1. **`cli._signoff` leaves a stale `signoff-decision` file behind.** `cli._signoff`
   (`template/src/pdca_harness/cli.py:1504`) records §9 at :1530 and re-drives at :1540,
   but never deletes `signoff-decision`. `flow._apply_decision` does delete it
   (`template/src/pdca_harness/flow.py:205`). Any bundle whose flow accept was refused by
   C6 keeps `accept` on disk. If the human then runs `pdca signoff <id> --iterate-plan`,
   the bundle is re-planned and rebuilt, and the next flow run's pre-apply
   (flow.py:2516-2522) applies the old `accept` to the new build with no review. This is a
   sign-off contract bug. It needs no wave, no trial and no fold.
2. **`waves.diff_files` misreads Git-quoted paths.** `_DIFF_GIT_RE`
   (`template/src/pdca_harness/waves.py:329`) matches `diff --git a/(.+) b/(.+)`, so a
   header Git quotes, such as `diff --git "a/caf\303\251.txt" "b/caf\303\251.txt"`, yields
   no path (or a mangled one). The advisory `_audit_wave_overlap` (flow.py:1586-1592) then
   misses an overlap on any non-ASCII or special-character path. A parser bug with its own
   unit test.
3. **The core: refuse a same-wave conflicting accept, and refuse when the check cannot
   complete.** Everything else in the parent brief: the accept-time trial, the §6 row, the
   bounded re-offer (leg h), parking an in-session iterate-plan until the next run, the
   iteration-6 fixes, the 2026-10-27 check-failure policy, and the docs paragraphs.

The core is NOT split further, and that choice is deliberate. The sizer and the 2026-10-27
ruling agree on it. Splitting "detected conflict" from "check failure" would force the core
to ship with some interim failure policy. That gap is what sank iteration 9. Leg h, the
parked iterate-plan and the check-failure legs can each only be tested once the refusal
exists, so they ship with it.

Honest caveat: child-3 is still a high-difficulty slice and may size `watch` or even
`oversized` on its own. It is smaller than the parent by the two carry-forwards, by the
dropped shared-path fallback (the 2026-10-27 ruling removes it), and by the decision-file
cleanup moving to child-1.

## Wave sketch

- **Wave 0: child-1 and child-2, in parallel.** They are independent. Child-1 edits
  `cli.py` (`_signoff`) and adds a sign-off test. Child-2 edits `waves.py` (`diff_files`)
  and adds a waves test. They touch no file in common, and neither needs the other's
  result. So neither declares the other.
- **Wave 1: child-3, after child-1.** `Depends on: child-1`. Child-3's recovery path tells
  the human to run `pdca signoff <id> --iterate-plan` on a refused bundle (or the
  in-session iterate-plan, which is parked to the next run). That path is only safe once
  the standalone sign-off consumes the stale `accept`. Without child-1, a trial-refused
  bundle is auto-accepted and published on the next run with no review. That is the
  iteration-7 finding. Child-3 must build on child-1's accepted result, and its re-plan
  leg becomes a regression check, not a fix.
- **Child-3 does not depend on child-2.** The 2026-10-27 ruling dropped the shared-path
  fallback, so the core no longer reads `diff_files`. It also does not conflict with
  child-2: child-3 leaves `waves.py` and `_audit_wave_overlap` alone. Child-3 could run in
  wave 0 next to child-2 if it did not need child-1.
- **External conflicts the fields cannot carry.** The parent declares
  `Conflicts with: 464, 740`. `pdca split --accept` refuses tracker ids in a child's
  ordering fields (`split._validate_ordering`, `split.py:358-368`), so they are written
  in child-3's `Ordering note` instead. **After accepting, add `Conflicts with: 464, 740`
  to child-3's materialised brief by hand.** Both apply only to child-3: 464 gates the same
  wave/publish/fold block (flow.py:3021-3125), and 740 rewrites
  `docs/07-crosscutting.md:647-735`. Neither touches `cli._signoff` or `waves.diff_files`.

<!-- pdca:child child-1 -->
- **Slug:** standalone-signoff-consumes-decision
- **Kind:** bug
- **Defect / goal:** `pdca signoff <id> --accept|--iterate-do|--iterate-plan|--discontinue`
  (`cli._signoff`, `template/src/pdca_harness/cli.py:1504`) records the decision in §9
  (:1530) and drives the transition (:1540), but never deletes the bundle's
  `signoff-decision` file (`leaves.SIGNOFF_DECISION`). The flow's own apply,
  `flow._apply_decision`, deletes it once it records (`template/src/pdca_harness/flow.py:205`).
  So a decision left by an earlier flow session survives a standalone sign-off. The common
  case: a flow accept refused by C6 (flow.py:177-179) leaves `accept` on disk. The human
  runs `pdca signoff <id> --iterate-plan`, the bundle is archived, re-planned and rebuilt,
  and the next `pdca flow` run's pre-apply (`_drive_wave`, flow.py:2516-2522) reads the old
  `accept` and accepts the rebuilt bundle with no sign-off session. Goal: once
  `cli._signoff` has recorded a decision, the `signoff-decision` file is gone, as it is
  after `flow._apply_decision`.
- **Success criterion:**
  - (a) A bundle at AWAITING_SIGNOFF with `signoff-decision` = `accept` on disk. Run
    `cli._signoff` with `--iterate-plan` (leaves in stub mode). After it returns,
    `signoff-decision` does not exist in the bundle directory.
  - (b) End to end: after (a), bring the bundle back to AWAITING_SIGNOFF (stub Plan/Do/Check,
    or write a fresh SUMMARY), then drive `flow._drive_wave` with a stubbed
    `leaves.run_signoff_batch` that records the bundles it is offered and writes nothing.
    The bundle is still AWAITING_SIGNOFF, it is NOT COMPLETE, and `run_signoff_batch` was
    offered it (a fresh session). Red on `main`: the pre-apply accepts it.
  - (c) A standalone `--accept` refused by C6 (`cli.py:1515-1520`, returns before
    `signoff.record`) leaves `signoff-decision` untouched — nothing was recorded, so
    nothing is consumed. A `signoff.record` that raises `ValueError` (`cli.py:1532-1537`)
    also leaves it untouched.
  - (d) Each recording action (`accept`, `iterate-do`, `iterate-plan`, `discontinue`)
    removes the file. Parametrize.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** in a scratch instance, put a bundle at AWAITING_SIGNOFF with an open §6
  row, write `accept` to `signoff-decision`, run `pdca signoff <id> --iterate-plan`, then
  `ls results/issue_<id>/signoff-decision` — the file is still there. Re-plan, re-run
  `pdca flow`: the bundle goes straight to COMPLETE without a session.
- **Falsifiability:** RED on `main` at legs (a), (b) and (d): the file survives and the
  pre-apply accepts. Leg (c) is green on both sides and guards against an over-eager fix.
- **Invariant to restore:** a recorded sign-off decision is consumed by whichever route
  records it, so no decision outlives the attempt it was made about. Source: the C6
  accept-guard (an accept is never applied to a build nobody reviewed) and
  `flow._apply_decision`'s existing consume-on-record (flow.py:205).
- **Scope (one logical fix) / out of scope:** `cli._signoff` deletes
  `leaves.SIGNOFF_DECISION` after `signoff.record` succeeds and before `driver.run_issue`,
  matching `flow._apply_decision`. Only the success path. / Out of scope: the session
  carry-forward capture (`state.SESSION_CARRY`, flow.py:201-204) — do not add it to the CLI
  here; any change to `flow._apply_decision`; the same-wave trial (#395 core, a sibling
  child); adding `signoff-decision` to `state.DOWNSTREAM_OF_BRIEF`.
- **External dependencies:** none
- **Test file:** `template/tests/test_signoff_consumes_decision.py` (new). Import modules
  only (`from pdca_harness import cli, flow, leaves, signoff, state`), never a symbol this
  change adds, so the red leg imports and fails on assertions. For leg (b), drive
  `flow._drive_wave` the way `template/tests/test_signoff_orphan.py:131-204` does, with a
  stubbed `leaves.run_signoff_batch`.
- **Citations expected:** Do cites path:line on the target branch for every change.
- **Difficulty:** low
- **Disposition hint:** likely-fix
- **Prior-art check:** found as a sign-off finding on #395 iteration 7
  (`results/issue_395/iteration-v9/brief.md:122`). No earlier fix on `main`.
<!-- pdca:end child-1 -->

<!-- pdca:child child-2 -->
- **Slug:** diff-files-git-quoted-paths
- **Kind:** bug
- **Defect / goal:** `waves.diff_files` (`template/src/pdca_harness/waves.py:332`) parses
  `diff --git` headers with `_DIFF_GIT_RE = r"^diff --git a/(.+) b/(.+)$"` (:329). Git
  quotes a path that holds non-ASCII bytes, a double quote, a backslash or a control
  character (`core.quotePath`): `diff --git "a/caf\303\251.txt" "b/caf\303\251.txt"`. The
  regex does not match that line, so the path is missing from the result. A mixed header
  (one side quoted) yields a path with a stray quote. The only caller today is the
  advisory `_audit_wave_overlap` (`template/src/pdca_harness/flow.py:1586-1592`), which
  then misses an overlap between two same-wave bundles that both edit such a file. Goal:
  `diff_files` returns the real repo-relative path for quoted headers, decoding Git's
  C-style escapes (octal byte escapes as UTF-8, `\"`, `\\`, `\t`, `\n`).
- **Success criterion:**
  - (a) A real-git patch (made with `git diff` in a temp repo, default `core.quotePath`)
    that edits `café.txt` → `diff_files` returns `{"café.txt"}`.
  - (b) Paths with a double quote, a backslash and a tab in the name each come back
    decoded.
  - (c) A rename between a quoted and an unquoted name returns both names.
  - (d) Unquoted headers, `/dev/null` sides and a missing file behave as today (existing
    `template/tests/test_waves.py` stays green).
  - (e) `_audit_wave_overlap` reports an overlap for two bundles whose patches both edit
    `café.txt` (drive it as the existing overlap-audit tests do). Red on `main`.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** `git init t && cd t && echo x > café.txt && git add . && git commit -m i
  && echo y > café.txt && git diff > p.diff`, then
  `python -c "from pathlib import Path; from pdca_harness import waves; print(waves.diff_files(Path('p.diff')))"`
  → `set()`.
- **Falsifiability:** RED on `main` at (a), (b), (c) and (e); (d) is green on both.
- **Invariant to restore:** `diff_files` returns the paths a patch touches, for every path
  Git can write in a header. Source: its own docstring (waves.py:333-340).
- **Scope (one logical fix) / out of scope:** the header parser in `waves.py` (regex and/or
  a small unquote helper) and its docstring. / Out of scope: making the audit a hard gate;
  what the audit does with an unparsable patch beyond today's behaviour; the ambiguous
  unquoted-path-with-a-space case the docstring already admits (fix it only if the quoted
  parser handles it for free); the #395 same-wave trial (a sibling child, which no longer
  reads `diff_files`).
- **External dependencies:** none
- **Test file:** `template/tests/test_waves_quoted_paths.py` (new). Import modules only
  (`from pdca_harness import flow, waves`), `unittest` style like
  `template/tests/test_waves.py` (no pytest fixtures). Build patches with real `git` in a
  `tempfile.TemporaryDirectory`; no network. For (e), call `flow._audit_wave_overlap` on two
  bundle directories and capture stderr.
- **Citations expected:** Do cites path:line on the target branch for every change.
- **Difficulty:** low
- **Disposition hint:** likely-fix
- **Prior-art check:** found as a sign-off finding on #395 iteration 8
  (`results/issue_395/iteration-v9/brief.md:127`). No earlier fix on `main`.
<!-- pdca:end child-2 -->

<!-- pdca:child child-3 -->
- **Slug:** same-wave-conflict-refused-at-accept
- **Kind:** enhancement
- **Goal:** In a `pdca flow` run in stack mode, in a wave the fold runs after
  (`k < len(wave_list) - 1`, `do_publish`, publisher not `stub`, not a dry run — the
  condition of the fold's non-dry `held_out`, flow.py:3108-3118), a bundle is not accepted
  if its branch would textually conflict with an already-accepted bundle of its own wave,
  judged by the fold's own #674 rule in the fold's order. Nor is it accepted when that
  check cannot complete. The driver refuses such an accept the way C6 refuses one today:
  the bundle stays AWAITING_SIGNOFF with an open §6 row. Siblings are accepted and
  published as before. The last wave, one-wave runs, single-issue `flow`, `--no-publish`,
  merge mode, dry runs and the standalone `pdca signoff --accept` do not change. Partial
  fix of #395 (`refs #395`).
- **Defect:** two real batches (2026-07 and 2026-08-01) published same-wave PRs that
  conflict, with no `Conflicts with` declared. Since #674 the fold holds one of them, but
  only after both PRs are open.
- **Rulings (binding):**
  - 2026-10-25: every accepted bundle ends in a PR. Do NOT rebuild the iteration-1..5
    "hold after accept" design (`conflict-hold.json`, a COMPLETE bundle with no PR).
  - 2026-10-23: "a conflict" = the accepted siblings plus the candidate, folded in name
    order, make the fold hold more bundles than the accepted siblings alone. The
    conflict-row override loophole is accepted. The split-during-last-wave case is a
    follow-up.
  - 2026-10-27, check-failure policy: when the check cannot complete (it cannot run, or it
    breaks the shared integration worktree), the accept is REFUSED. A tick on that row
    means "retry the check", never "publish anyway": the next accept runs the check again,
    and if it fails again the row is re-opened unticked. There is NO shared-path fallback.
    Row keys never include the free-text error cause.
- **Success criterion:** on the real-git `StackFoldGit` fixture
  (`template/tests/test_integrate_stack_bases.py`), `gh` stubbed, publisher in `command`
  mode. Every accept goes through the real `flow._drive_wave` → `flow._apply_decision`
  path: Do+Check stubbed, the decision written to `leaves.SIGNOFF_DECISION`, nothing calls
  `signoff.record(... "accept")` directly. A later wave exists in every leg except (g).
  - (a) A and B in wave 0, no `Conflicts with`, patches change the same lines of a shared
    file, both carry `accept`. A is COMPLETE, pushed, `gh pr create` called for it. B is
    AWAITING_SIGNOFF; B's §6 has an open row naming A and the shared file, returned by
    `signoff.open_needs_human`. B's branch is not on origin; no `gh pr create` names B;
    `holds` has no entry for B; `cli._results_rc` is 1. A wave-1 bundle that depends on
    neither still builds and completes.
  - (b) A and B change different lines of the same file: both COMPLETE, both published,
    no §6 row.
  - (c) Order independence: with B's decision applied first (B carries a recorded
    decision the pre-apply at flow.py:2516-2522 applies; A's comes from the session), A
    is refused. Exactly one of the pair is COMPLETE and `holds` is empty.
  - (d) Override in the SAME run: after B's refusal, the session ticks B's conflict row
    and writes `accept`. B is accepted and published; the fold holds B as `"conflict"`
    as on `main` (#674). The row is not added twice (`signoff.ensure_needs_human_item`,
    `signoff.py:177-207`).
  - (e) Check cannot run: A is accepted; inject a failure of the trial's git step (a
    fetch, or building a would-be commit) for every later trial. B (same target as A,
    sharing NO file with A) is refused with a §6 "check could not complete" row whose
    text names no free-text error cause — no shared-path fallback lets it through. A
    bundle whose accept needs no check (no accepted same-wave sibling on its target yet)
    is accepted and published as today. Nothing is accepted on a check that did not
    complete.
  - (e2) Retry semantics: after (e), the session ticks B's check-failure row and writes
    `accept` while the fault is STILL injected. B is refused again, and its row is
    re-opened unticked. Then clear the fault, tick, `accept`: the check runs, finds no
    conflict, and B is accepted and published.
  - (e3) Broken tree: inject `integrate.IntegrationTreeError` (or `_LineBroken`) from the
    trial. The accept is refused under the same retry semantics as (e)/(e2) — the run
    does NOT stop at accept time (stopping there would leave already-accepted siblings
    COMPLETE with no PR). B is never accepted while the fault persists, including after a
    tick. The fold after the wave keeps its existing stop on a broken tree
    (flow.py:3001-3009, 3118-3125), unchanged. The first error is chained (`raise … from`)
    through the trial's `finally` resets.
  - (e4) Stable row key: two check failures with different error messages produce ONE
    row, not two, and a tick on it is honoured by the next attempt (which then re-runs
    the check per e2).
  - (f) The row lives only in SUMMARY §6, not in `assemble.collect_needs_human`
    (`assemble.py:389`) or any Check artifact. Reassemble B's SUMMARY with the driver's
    own assembly step, write `accept`, drive another pass: B is refused again and the row
    is back, unticked.
  - (g) Last wave: the same conflicting A/B as the only wave. Both accepted and
    published, exit code as on `main`.
  - (h) Bounded re-offer: with `max_passes = 20` and B's session stub writing nothing
    after the refusal, B is offered at most one session after the refusing pass
    (`leaves.run_signoff_batch` calls naming B ≤ 2). The wave ends with B
    AWAITING_SIGNOFF; the stderr line names the conflict, the partner and the step, and
    does NOT say "raise [driver].max_passes". A plain C6 refusal keeps today's behaviour.
  - (h2) A session that raises is not counted as B's one more session: count only after
    `run_signoff_batch` returns.
  - (h3) Re-run: on a second `pdca flow` run with B's row still unticked, B is offered one
    session again, then parked with the conflict step — not spun to the pass budget. The
    "offered" record is reset per run, not deleted.
  - (i) In-session iterate-plan on a refused bundle is parked: the session writes
    `iterate-plan` for B; B is not re-planned, rebuilt or re-checked in the same run, and
    the row / wave-end text says it will be re-planned on the next run.
  - (j) Standalone re-plan (regression check on the sibling child that fixes
    `cli._signoff`): refuse B, `pdca signoff B --iterate-plan`, re-plan, re-run — B
    reaches AWAITING_SIGNOFF and gets a fresh session, not auto-accepted.
- **Falsifiability:** RED on `StackFoldGit`. Today `_apply_decision` (flow.py:134-213) only
  checks C6 (flow.py:177-179), so in (a) both bundles reach COMPLETE, the publish loop
  (flow.py:3034-3070) pushes both and calls `gh pr create` twice before the fold
  (flow.py:3108-3118) holds B. `test_signoff_orphan.py:131-204` shows how to drive the
  real `_drive_wave`. Do NOT copy `test_flow_same_wave_conflict.py:119-129`, which stubs
  `_drive_wave` and accepts with `sb._accept` — every leg would pass on both sides.
- **Invariant to restore:** in a `pdca flow` run, an accepted (COMPLETE) bundle is one the
  run can publish without a same-wave textual conflict, and an accept is never granted on
  a check that did not complete. Sources: the 2026-10-25 ruling; project CLAUDE.md ("On an
  accept, publish … the driver opens a draft PR"); the C6 accept-guard. Binds every accept
  route of a flow run (pre-apply flow.py:2516-2522, post-session apply :2530-2532, both via
  `_apply_decision`).
- **Design pointers:**
  - Accept path: `flow._apply_decision` (flow.py:134, C6 refusal :177-179 returning
    `"blocked"`), `flow.accept_blockers` (:215), the two routes in `flow._drive_wave`
    (:2447). `_drive_wave` is called from `_drive_and_act` (:3021), which knows `k`,
    `wave_list` and `do_publish`.
  - Row: `signoff.ensure_needs_human_item` (`signoff.py:177`), as `accept_blockers` uses
    for the unreadable-ledger row (flow.py:235-237). Key each row by kind + partner(s) +
    file(s) for a detected conflict, and by kind alone for a check failure.
  - Rule to mirror, not reinvent: `integrate.fold` with `held_out` / `wave`
    (`integrate.py:354`, contract :472-480, hold :646-660), `integrate._held_by`
    (:1785), `integrate._trial` (:2095). A sibling's would-be commit is its `patch.diff`
    on publish's `checkout_base` (`publish.py:261-265`), built locally, never pushed, in
    the fold's shared integration worktree under the fold's lock (per target, a
    `contextlib.ExitStack` as `_fold_lines` does, flow.py:1253). Leave the tree reset on
    every exit path.
  - "Offered once" marker: Do's choice, but it lives in the bundle's files, is reset (not
    deleted) at wave start of each run, and does not change the plain C6 path.
  - Prior attempt, mechanics only: Do MAY open
    `/home/eddie/pdca/pdca-pdca/results/issue_395/iteration-v9/patch.diff` and
    `/home/eddie/pdca/pdca-pdca/results/issue_395/iteration-v5/patch.diff`. Do NOT carry
    over v5's `conflict-hold.json` / `held_conflict` code, or v9's shared-path fallback
    (`same_wave_overlap`) and its tick-means-publish handling of check failures.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Reproduction:** n/a (new behaviour); leg (a) shows today's double publish.
- **Scope (one logical fix) / out of scope:** the accept-time same-wave refusal in a flow
  run's stack-mode non-final waves, every accept route in `_drive_wave`, the check-failure
  policy above, the bounded re-offer and parked iterate-plan, and
  `docs/07-crosscutting.md` (same-wave paragraph :719-731 gets the refusal, the override,
  the retry-only check-failure rule, and the fact that a line-plus-sibling conflict, #747
  `_held_by_line`, is still caught only at the fold; exit-code paragraph :734-745 says a
  refused bundle is unfinished, exit 1). / Out of scope: `cli._signoff` decision cleanup
  and `waves.diff_files` (sibling children); the last wave and one-wave runs;
  re-sequencing a refused bundle within the run and writing `Conflicts with`
  automatically; #747 line-work conflicts; the issue's layer 1 (Plan-exit advisory);
  the standalone `pdca signoff --accept`; merge mode; `_audit_wave_overlap`
  (flow.py:1586); documenting "accepted ⇒ PR" with its two existing exceptions.
- **External dependencies:** none
- **Test file:** `template/tests/test_flow_same_wave_accept_trial.py` (new). Import modules
  only (`from pdca_harness import assemble, autoiterate, cli, flow, integrate, leaves,
  publish, signoff, state`), so the red leg imports and fails on assertions
  (`engine/scripts/run-verify.sh:222-240`). Load the fixture by path as
  `test_flow_same_wave_conflict.py:36-39` does; reuse its `_edit` (:44-49), `gh` stub
  (:108-117) and `_publish_bundle` / `publish.draft_texts` stubs (:131-157). Stub
  `flow._build_all`; do not stub `flow._drive_wave`. The copy of this file sitting in
  `results/issue_395/` is from iteration 9 and is not an input.
- **Citations expected:** Do cites path:line on the target branch for every change.
- **Difficulty:** high
- **Ordering note:** the parent declares `Conflicts with: 464, 740`; tracker ids cannot go
  in this proposal's ordering fields, so add them to this brief's `Conflicts with` after
  `pdca split --accept`. 464 adds a wave mode that gates the same wave/publish/fold block
  (flow.py:3021-3125). 740 rewrites `docs/07-crosscutting.md:647-735`. Neither is a
  build-on dependency.
- **Disposition hint:** new-feature
- **Prior-art check:** `git -C ../pdca-harness log --oneline origin/main --
  template/tests/test_flow_same_wave_conflict.py` → 0c263a9 (#674), 89c2017 (#727),
  d51849a (#747); none checks before accept. Parent #395 iterations 1–9 are the prior
  attempts (1–5 rejected design; 6–9 this design, rejected on gaps the rulings now close).
- **Depends on:** child-1
<!-- pdca:end child-3 -->
