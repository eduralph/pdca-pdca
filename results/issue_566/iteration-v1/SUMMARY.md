# Result — issue 566 / split-hint-honest-about-a-live-run

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: Through `cli._split` and `cli._flow`, with the patch:
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
- Repo + branch target: eduralph/pdca-harness @ main (base `70ea12b` plus the sibling
  child's accepted change; line numbers here are on `70ea12b`, verified 2026-09-19 —
  re-locate them on the stacked base)
- Scope (one logical fix) / out of scope: 

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review `split --accept` hints during live flows and the end-of-run report of split children that a flow did not drive (#566).

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The brief defines observable live-run, standalone, reporting, and collision outcomes with an offline reproduction; `brief.md:22`, `brief.md:49`, `brief.md:64`. |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production patch reproduced four behavioral assertion failures; the additional missing `_retry_wait` error is not counted as behavioral evidence; `reviewer-red.log:1`, `target/template/tests/test_split_hint_live_run.py:287`. |
| C3 Change | FAIL | Completed children are falsely reported as in-flight, and post-sweep CSV accepts promise a report that never appears; both violate the specified operator guidance (findings 1–2); `target/template/src/pdca_harness/flow.py:1543`, `target/template/src/pdca_harness/flow.py:1897`. |
| C4 Verification (red→green) | PASS | After stash/pop, the eight submitted tests pass, confirming the covered red→green behaviors; they do not cover the counterexamples below; `reviewer-green.log:3`, `target/template/tests/test_split_hint_live_run.py:409`, `target/template/tests/test_split_hint_live_run.py:490`. |
| C5 Causal adequacy | FAIL | Five timed attempts cannot guarantee that a hint probe never causes false driver refusal; a deterministic paused probe reproduced that refusal (finding 3); `target/template/src/pdca_harness/drive_claim.py:192`, `reviewer-probes.log:6`. |
| T1 Structure | PASS | The changes remain within CLI reporting, flow accounting, and the existing claim module, without a second ownership mechanism; `target/template/src/pdca_harness/drive_claim.py:269`, `target/template/src/pdca_harness/flow.py:1485`. |
| T2 Shape | PASS | Independently reran docs lint, 22-page rendering/link audit, and diff whitespace checks successfully; frozen docs and host-parity logs agree; `gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | Independent driver suite: 1,963 tests, two skips, no failures; frozen root suite: 24 passing tests; local root rerun lacks importable Copier, a host caveat rather than a patch defect; `reviewer-suite.log`, `gate-logs/T3-suite.log:54`, `reviewer-root-suite.log`. |
| T4 Contribution | N/A | Contribution artifacts are drafted after Check; their substantive audit is deferred to the mandatory publish rerun; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm prior-art coverage includes the affected claim module and closed/rejected work — the brief records path-based CLI/flow history and #498 attempts, but this one-commit target has no remote or independently searchable review history; `brief.md:126`, `target/template/src/pdca_harness/drive_claim.py:101`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the conditional hint and final recovery command give operators sufficient guidance once the demonstrated defects are addressed — passing the submitted tests does not establish the brief's no-orphan/no-false-refusal promise; `brief.md:28`, `brief.md:39`, `brief.md:49`. |

1. **CSV sweep marker outlives the sweep.** `flow_batch` evaluates `_drive_and_act(...)` before executing its `finally`, so the marker remains held during the entire drive (`target/template/src/pdca_harness/flow.py:1897`, `:1904`). Through real `cli._flow --from-csv`, the probe creates and accepts parent 900 during the build of already-swept bundle 8. The hint says a running flow holds 900 and will list un-driven children when it ends, but 900 belongs to neither its drive set nor its seeds. Children 901/902 remain PLANNED and no report names them (`reviewer-probes.log:3`). Release the marker when sweeping/claim selection finishes, before driving the selected bundles; cover an accept after that boundary.

2. **Terminal children are advertised as unfinished work.** The lineage walk appends every existing, non-split child outside the final drive set without checking its terminal state (`target/template/src/pdca_harness/flow.py:1535`, `:1543`). The probe completes parent 500 and children 601/602, then runs `flow 500 8`. It prints `601, 602 left in-flight; drive them with pdca flow 601 602` although both children are COMPLETE (`reviewer-probes.log:1`). Exclude terminal non-split children while preserving traversal through terminal split children. The submitted tests omit this required no-report case.

3. **A delayed probe still causes a false ownership refusal.** `held()` takes the real exclusive lock, while `take()` gives up after five attempts with only 10 ms total requested sleep (`target/template/src/pdca_harness/drive_claim.py:111`, `:192`, `:276`). There is no bound on how long the OS may deschedule a probe while it holds that lock. The deterministic probe pauses the actual `held()` call immediately after successful acquisition, then invokes `Run.take()` using the real lock primitive and normal retry delays. With no driving run present, it returns `held by another live flow run` (`reviewer-probes.log:6`). The shipped test releases the blocker on the first retry, so it cannot expose this failure (`target/template/tests/test_split_hint_live_run.py:478`). Distinguish observation from ownership without depending on a short scheduling delay.

Independent evidence is retained in `reviewer-red.log`, `reviewer-green.log`, `reviewer-suite.log`, and `reviewer-probes.log`. Reproduce the three additional observations from this directory with:

```sh
TMPDIR="$PWD/review-tmp" PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$PWD/target/template/src:$PWD/target/template" \
python3 reviewer-probes.py
```

The C5 production-import scanner also passed independently. The C4 red leg's missing `_retry_wait` attribute is a test error, alongside four genuine assertion failures, not an additional reproduced behavioral failure. The local root runner exited 77 because Copier is not importable; the frozen T3 log explicitly records successful render/update cases, so there is no undischarged dependency inferred from this reviewer host alone. T4 remains deferred, not a missing check. No capability-present/load-time guard smell was found. The only available INTEGRATION §4 is the template, whose project-specific human-only list is still TODO (`target/template/docs/INTEGRATION.md.jinja:80`). The target was current and readable; production edits were restored after the red leg and left unchanged. These findings are advisory and do not gate acceptance.

### Advisory — code-review

# Advisory code review — issue #566

Scope: correctness bugs introduced by this patch, plus reuse/simplification/efficiency.
Grounded on the patched target tree (`$PDCA_TARGET`), not build-notes.

## Findings

- `template/src/pdca_harness/flow.py:1461-1482` (`_split_marked`) duplicates the three-line
  close-marker read in `_is_split_parent` (`flow.py:907-930`) verbatim, differing only in the
  terminal-state gate. The docstring on `_split_marked` explains *why* the two predicates must
  answer differently (one must see a split before sign-off confirms it, the other must not),
  which is a real reason not to merge them into one predicate — but `_is_split_parent` could
  still be rewritten as `state.state(d) in _TERMINAL and _split_marked(d)` to drop the second
  copy of the try/except read without changing either's behavior. Cosmetic; not a defect.

- `template/src/pdca_harness/flow.py:1634-1652`: when `_drive_and_act` is entered with an
  empty `bundles` and only `adopt_seeds` (the "named id is itself an already-terminal split
  parent, nothing else to drive" shape from `flow_ids`), and the seed's pre-pass adopts no
  child at all, the function returns `{}` right there — before the tail that now calls
  `_warn_stranded_split_children` (`flow.py:1811`). I checked every branch that can leave
  `bundles` empty after that pre-pass (no brief, held by a sibling parent, claim refused by
  another live run, reschedule failure) and each already prints its own explicit stderr line
  (`_adoptable`'s prints, `_report_held`, `_report_refused`, the "could not be scheduled"
  message) — so in practice nothing is left silently orphaned on this path today. But it does
  mean the new end-of-run report is not literally reached on every return from
  `_drive_and_act`, which is narrower than the brief's "just before `_drive_and_act` returns"
  wording. Worth a second look if a future change adds a way to leave `bundles` empty on this
  path *without* its own report — right now it's redundant-safe, not silent.

## Everything else checked and clean

- `drive_claim.held()` / the `Run.take()` retry loop (`drive_claim.py:170-297`): retry count,
  wait scheduling, handle lifecycle (no leaked file descriptors on any exit branch), and the
  fail-open-the-opposite-way contract between `take()` (fail closed) and `held()` (fail open)
  all check out. The forced-collision test (`test_take_retries_past_a_forced_peek_collision...`)
  correctly pins the retry against a real OS lock via a deterministic hook rather than
  wall-clock timing.
- `flow_batch`'s new `try/finally` around the sweep marker (`flow.py:1854-1990ish`): the two
  existing "nothing to drive" messages were re-wrapped across two string literals when the
  block gained a level of indentation, but the concatenated text is byte-identical to before
  — confirmed by diffing the two literal halves. No message text actually changed.
- `_warn_stranded_split_children`'s walk mirrors `_adopt_split_children`'s lineage walk
  (`_lineage_children`, `_PLAIN_ID`, `_real`, `_inside_bundle_root`) faithfully; it correctly
  reuses those helpers rather than re-implementing bundle-name validation.
- C4's red leg (`gate-logs/C4-verify.log`) fails 4 of 8 new tests plus 1 `AttributeError` on
  the reverted production code and the green leg passes all 8 — the new test file does
  exercise the fix, not a copy of it (confirmed independently of C5's prod-path check, which
  also passes).
- T3's full offline suite is green (1963 tests, 2 skipped) with the patch applied; the
  "FAILED" lines inside `T3-suite.log` belong to an unrelated nested-harness fixture printing
  its own log, not this patch's tests.
- Docs/planner/leaves.py wording updates (`docs/07-crosscutting.md:339-352`,
  `template/agents/planner.md.jinja:152-192`, `template/src/pdca_harness/leaves.py:1116-1477`)
  match what `cli._split` and `flow._warn_stranded_split_children` actually print — no drift
  between the model-facing text and the code.

No NEEDS-HUMAN items — nothing here rises to an architectural or scope question; the one open
item above is a defensive-depth note, not a bug to route back to Do.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm prior-art coverage includes the affected claim module and closed/rejected work — the brief records path-based CLI/flow history and #498 attempts, but this one-commit target has no remote or independently searchable review history; `brief.md:126`, `target/template/src/pdca_harness/drive_claim.py:101`.
- [ ] Validation — fitness-to-purpose — Decide whether the conditional hint and final recovery command give operators sufficient guidance once the demonstrated defects are addressed — passing the submitted tests does not establish the brief's no-orphan/no-false-refusal promise; `brief.md:28`, `brief.md:39`, `brief.md:49`.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on finding 2 — the end-of-run stranded-child report names finished children as unfinished work. `flow._warn_stranded_split_children`'s lineage walk (patch.diff:319-328) implements only half of brief (iii). It skips a child that is in the run's final drive set, and walks through a child that is itself split-marked, but it never checks the child's own state. So a COMPLETE / DISCONTINUED / RESOLVED child gets appended to `stranded` and printed as "left in-flight" with a `pdca flow <ids>` command pointing at work that is already done. Reviewer probe: parent 500 with COMPLETE children 601/602 under a real `flow 500 8` run prints `601, 602 left in-flight` (check-review.md finding 2; reviewer-probes.log:1). The only `state.state` calls in the new flow code are in the unrelated batch sweep — there is no terminal check anywhere in the walk. What to change: - Skip a lineage child whose state is terminal, per brief (iii) "not terminal and not in the run's final drive set". Both conditions, not just the second. - Keep walking THROUGH a terminal split child. That traversal is deliberate and correct — a split parent is terminal by design, and its grandchildren must still be reached. Do not fix this by gating the whole walk on non-terminal. - Pin the missing branch with a test. Brief (iii) says "No such children → no line" and (vi) requires a test for every branch that changes whether the report fires; none of the 8 submitted tests covers a split parent whose children are all finished. Scope of this iterate: finding 2 only. Change nothing else. The human reviewed the other two reviewer findings at sign-off and accepted the current behaviour on both — do not "also fix" them: - Finding 1 (flow_batch holds the CSV sweep marker for the whole drive, because `return _drive_and_act(...)` is evaluated inside the `try` before the `finally` releases it): accepted as-is, no fix wanted. - Finding 3 (`Run.take`'s bounded 5-retry past a `held()` peek vs brief (iv)'s absolute "never cause a false refusal"): no work wanted now. The conditional-line half of the change was not rejected.
- By / date: Eduard Ralph / 2026-09-19

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
