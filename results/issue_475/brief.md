# Brief — issue 475 / no-new-session-notice-waits-for-the-guard

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** no-new-session-notice-waits-for-the-guard
- **Defect:** `flow._apply_recorded_decision`
  (`template/src/pdca_harness/flow.py:223-249`) announces the outcome **before** the outcome is
  decided. It prints, at `:247-248`:
  `flow: <bundle> — applying the '<action>' sign-off decision already recorded in the bundle;
  no new session` — and only then calls `_apply_decision` (`:249`), where the C6 accept-guard
  runs: an `accept` with §6 NEEDS-HUMAN still open prints
  `flow: <bundle> — cannot accept, §6 NEEDS-HUMAN still open (C6)` and returns `"blocked"`
  (`:176-178`). `"blocked"` is the one outcome that deliberately falls through
  (`_signoff_and_apply`, `:258-262`; the batch path, `:1366-1379`), so a **fresh sign-off
  session is opened immediately** — the very thing the operator was just told would not happen.
  The operator reads a promise and its withdrawal one line apart, on the path where they are
  being asked to come back and look. Confirmed on the target base: the notice is
  unconditional, and nothing between `:247` and the guard can suppress it.
  Surfaced as a §10 Act candidate on this instance's issue_453 cycle and routed upstream at the
  2026-08-09 Act review (`process/act-log.md`).
- **Success criterion:** With the patch, on a bundle carrying a recorded `accept` that C6
  refuses (§6 NEEDS-HUMAN still open), the run's stderr **does not claim that no new session
  will be opened** — while the C6 refusal message, the fall-through to a fresh session, the
  return value `"blocked"` and every state transition stay exactly as they are; and on a
  decision that **is** applied without a session (an `accept` that C6 permits, and every
  `iterate-do` / `iterate-plan` / `discontinue`), the operator is still told, in the same terms,
  that the recorded decision was applied with no new session. Both drive paths — the single-issue
  `_signoff_and_apply` and the batch sweep — behave identically, since both call the same
  function. Demonstrable by C4-verify on the existing offline slice.
- **Falsifiability:** RED is reachable on the base toolchain — pure-stdlib Python ≥ 3.11, no
  network, no services — in the target checkout Do is given. `template/tests/test_signoff_orphan.py`
  already builds exactly this scenario twice: `test_c6_refused_accept_still_gets_a_fresh_session`
  at `:168` (single-issue) and `:241` (batch), both with stderr captured via `redirect_stderr`.
  Asserting there that the captured stderr does **not** contain the "no new session" claim in the
  C6-refused case fails today — that is the red — while the companion assertion (the notice is
  still printed when the decision really is applied without a session) keeps a fix that simply
  deletes the notice from passing. C4's red leg reverts `flow.py` and keeps every
  `template/tests/*.py` hunk (`engine/scripts/run-verify.sh:214-217`), so appended cases earn a
  genuine red.
- **Invariant to restore:** A message the driver prints about an outcome must not be emitted
  before the code that decides that outcome has run — a notice may describe what the driver
  **did**, or what it is **attempting**, never a result a guard downstream can still withdraw.
  Stated over the category rather than this one line: it binds every announce-then-decide pair
  on the sign-off path, which is why the fix is either to move the notice past the decision or
  to reword it so it asserts nothing the guard owns. Source: internal project invariant
  (Tier C) — the harness's own rule that sign-off authority is the human's and C6 is the guard
  that enforces it (`CLAUDE.md` §"Check sign-off"; `flow.py:214-220`, which documents
  `"blocked"` as the one outcome that DOES fall through to a session).
  `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6 category gate
  applies. This is a behavioural defect in code the project owns, so principle 1.2's minimalism
  governs: the smallest reviewable delta that restores the invariant.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves, and a
  wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds. Ordering
  lives in the run boundaries. `flow.py` is touched by no other bundle in this run (480 and 496,
  which do, are held to runs 3 and 6), so this slice is file-disjoint from its wave-mates.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** The announce-before-decide pair in `flow._apply_recorded_decision` — one function,
  one message, no behaviour change beyond what is printed and when. **Out of scope:** the C6
  guard itself and its message (`flow.py:176-178`), which is correct; the fall-through contract
  for `"blocked"` (`:258-262`, `:1366-1379`), which is the documented and intended behaviour;
  `_apply_decision`'s repair paths (`:161-192`); anything about §9 recording, the carry-forward
  channel, or the auto-iterate decline; the interactive sign-off leaf's own output.
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline, from `template/`:
  1. `PYTHONPATH=src python3 -m unittest tests.test_signoff_orphan -v` — green today;
     `test_c6_refused_accept_still_gets_a_fresh_session` (`:168`, `:241`) already constructs a
     bundle with a recorded `accept` and an open §6 item and asserts that a fresh session *is*
     opened.
  2. Print the captured stderr in that case (or read `flow.py:247-249` beside `:176-178` and
     `:258-262`): it carries `…already recorded in the bundle; no new session`, immediately
     followed by `cannot accept, §6 NEEDS-HUMAN still open (C6)` — and a session is then opened.
- **External dependencies:** none — the offline driver suite exercises the whole path with
  stub leaves, so the slice builds and goes red→green on the base toolchain.
- **Test file:** `template/tests/test_signoff_orphan.py` — append to the existing suite. It is
  the module that owns the read-before-asking contract (#453) and already has both drive paths,
  the C6-refused fixture and stderr capture in place. C4's red leg keeps all
  `template/tests/*.py` hunks and reverts only `flow.py`, so appended cases earn their red.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues: the sibling notices that already get this right are `flow.py:154`
  (`sign-off recorded no decision`) and `:162-163` (`decision '<action>' but no SUMMARY.md …;
  skipping record, will re-drive`) — both are printed **after** the condition they describe is
  established; match that voice and that placement. The docstring at `:238-242` ("Never silent:
  an apply with no session names the bundle and the action on stderr") is the contract the fix
  must keep true for the cases where the apply really happens.
  A regression test must not import a symbol this patch introduces at module level: C4's red leg
  reverts production first, and a module that then fails to import is recorded
  `PDCA-UNVERIFIABLE`, not red (`engine/scripts/run-verify.sh:231-234`).

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/src/pdca_harness/flow.py` — recent commits are `96c9704` (drive a split's children),
  `4814b3d` (#468, one results map for both flow shapes) and the #453 read-before-asking work
  that introduced this very notice; none revisits its placement.
  `gh pr list -R eduralph/pdca-harness --state open` → **no open PRs**. Open issues touching
  `flow.py`: #480 (split children never get the plan-advisory pass), #496 (a split never aborts
  the flow), #497 (single-id exit code — verified already fixed, see that bundle), #509
  (crash-resume) — none of them is this message, and 480/496 are held to later runs. Not
  previously attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the findings both review lenses agree on (reviewer C3/T5 + advisory code-review): the new notice gate `if outcome != "blocked":` (flow.py:252-256) is broader than "the decision was actually applied". It also admits the two outcomes where the decision was explicitly NOT recorded -- `None` from the missing-SUMMARY.md drop (flow.py:161-165) and `REASSEMBLE`/`None` from `_repair_unsignable` (flow.py:114-130). On those paths the run prints "decision '<action>' not recorded (...); bundle returned to ... to reassemble" and then, on the very next line, "applied the '<action>' sign-off decision ...; no new session". That is the same announce-a-result-a-downstream-step-can-withdraw defect this slice exists to remove, reappearing one guard downstream of the C6 one it targeted. What to change next: - Gate on genuine success -- e.g. `if outcome == action:` -- not `!= "blocked"`. - Fix the docstring at flow.py:245-247, which restates the same false dichotomy (it conflates "not blocked" with "successfully applied"). - Add the missing red case: an orphaned recorded decision whose bundle also lost or mangled SUMMARY.md, reached via `_apply_recorded_decision` rather than a live session. C4's current red/green covers only the "blocked" case and the ordinary successful applies, which is why this passed every gate undetected. - Minor, optional: the two new assertions re-derive inline what `_Base._announced` (test_signoff_orphan.py:111-115) already computes. Keep as-is -- do not re-do this part: the targeted announce-before-decide reordering and the C6-refused case staying silent on "no new session" are correct and covered on both drive paths (single `_signoff_and_apply` and the batch sweep).
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the findings both review lenses agree on (reviewer C3/T5 + advisory
  code-review): the new notice gate `if outcome != "blocked":` (flow.py:252-256) is
  broader than "the decision was actually applied". It also admits the two outcomes
  where the decision was explicitly NOT recorded -- `None` from the missing-SUMMARY.md
  drop (flow.py:161-165) and `REASSEMBLE`/`None` from `_repair_unsignable`
  (flow.py:114-130). On those paths the run prints "decision '<action>' not recorded
  (...); bundle returned to ... to reassemble" and then, on the very next line,
  "applied the '<action>' sign-off decision ...; no new session". That is the same
  announce-a-result-a-downstream-step-can-withdraw defect this slice exists to remove,
  reappearing one guard downstream of the C6 one it targeted.

  What to change next:
  - Gate on genuine success -- e.g. `if outcome == action:` -- not `!= "blocked"`.
  - Fix the docstring at flow.py:245-247, which restates the same false dichotomy
    (it conflates "not blocked" with "successfully applied").
  - Add the missing red case: an orphaned recorded decision whose bundle also lost or
    mangled SUMMARY.md, reached via `_apply_recorded_decision` rather than a live
    session. C4's current red/green covers only the "blocked" case and the ordinary
    successful applies, which is why this passed every gate undetected.
  - Minor, optional: the two new assertions re-derive inline what `_Base._announced`
    (test_signoff_orphan.py:111-115) already computes.

  Keep as-is -- do not re-do this part: the targeted announce-before-decide reordering
  and the C6-refused case staying silent on "no new session" are correct and covered
  on both drive paths (single `_signoff_and_apply` and the batch sweep).
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
