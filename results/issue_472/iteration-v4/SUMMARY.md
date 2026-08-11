# Result — issue 472 / flow-adopt-core

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: 
- Success criterion: exercised **through `cli._flow`** on byte-identical disk state:
  a run whose Plan/re-plan beat splits a drive-set bundle drives that bundle's children
  to a terminal state within the same call — in a wave AFTER the parent's, honouring
  their `Depends on` / `Conflicts with`, counted against ONE run-wide `max_passes`
  budget across original AND adopted waves (pool sized off the pre-adoption schedule —
  the converged v3 mechanics; live re-sizing is the sibling child's), each adoption
  announced on stderr with the child's REAL wave index from the recomputed schedule. A
  child with an unresolvable dependency is held loudly in the existing held-report
  shape, excluded from the results map, and the run continues — never aborts. Adoption
  is lineage-scoped and transitive (only descendants of the ids given), never a disk
  sweep; an adopted child that itself splits is re-adopted within the same shared budget
  — bounded, no recursion reset. Guards proven by test, not just present: a split-marked
  but NON-terminal parent (e.g. sign-off recorded `iterate-do`) does NOT have its
  children adopted; a parent whose lineage record is unreadable is reported and skipped,
  never a crash; a lineage child id that escapes the bundle root (e.g. `"../../etc"`) is
  skipped with a report; an id already in the run's drive set is not adopted twice —
  dedup against the batch, against a duplicate id within one record, AND against a child
  already taken by another parent adopted in the SAME wave (two parents splitting in one
  wave, the second's record also naming the first's child — the #469-v3 adversary's
  unpinned-`taken` mutation; the docstring's test citation must name this test).
  Demonstrable by C4-verify on the patch alone.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: adopt the children of a bundle that goes `close-disposition = split` while
  in the drive set — detect (read `split.read_lineage`; a parent with the marker but no
  readable record is reported and skipped, never a crash), validate
  (`waves.partition_schedulable` tolerance; held children reported in the existing
  "held this run — <reason>; left in-flight" shape and EXCLUDED from the results map),
  splice (children join after the current wave; pointed at the same per-target
  integration branch via the existing `_point_at_integration`; one run-wide `max_passes`
  pool across original AND adopted waves, sized as converged in v3; adopted children
  join the set `_warn_abandoned` / final sweep cover), report (stderr announcements
  with real wave indices) — on the unified drive path, so every CLI shape inherits it
  from one implementation. Includes the same-wave two-parents dedup test (v3 carry-
  forward 3) and the corrected docstring citation, and the ancillary
  `template/tests/test_verify_base.py` environment cleanup the v3 review accepted as
  discharging an iteration carry-forward, not scope expansion.
  / out of scope: **terminal-parent recovery** (a run handed an id ALREADY terminal on a
  split — the pre-run short-circuit stays for now; sibling child) and **shape-parity
  assertions against that recovery path**; **single-id stdout reporting of adopted
  dispositions** and **budget re-sizing on adoption** (sibling child); changing why
  recursive splits happen (#448's line — merely never enable an infinite one); a disk
  sweep in `flow_ids` (the distinction from the CSV sweep is deliberate and stays); the
  `--accept` hint printing `pdca flow <child-ids>` (still right for a split accepted
  outside a running flow); `waves.compute_waves` / `partition_schedulable` semantics
  (reused as-is); the split command, `split.accept`, or the lineage schema (#456 shipped
  it); publish/fold semantics beyond the existing reconciliation.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: new-feature
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: pass — == T3: root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — ./scripts/pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of the mid-run split-adoption core: make one `pdca flow` call schedule, drive, budget, and report newly split children without widening beyond the driven lineage.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The behavioral boundary is decidable: adopt only mid-run lineage children, keep terminal-parent recovery out of scope, and preserve loud held-child continuation (`docs/07-crosscutting.md:243`). |
| C2 Reproduction (red pre-fix) | PASS | With only production hunks reversed, all 25 tests executed and 24 failed, including children remaining non-terminal where the criterion requires COMPLETE (`template/tests/test_flow_adopt_split.py:333`). |
| C3 Change | PASS | The patch stays within the adoption core and its declared documentation/test cleanup: it re-waves only the un-driven tail and explicitly preserves the terminal-parent boundary (`template/src/pdca_harness/flow.py:1105`). |
| C4 Verification (red→green) | PASS | After restoring the patch, all 25 focused tests passed; the 1,658-test offline driver suite passed (2 skipped), all 7 Copier render/update tests passed, and the docs link audit passed (`template/tests/test_flow_adopt_split.py:322`). |
| C5 Causal adequacy | PASS | The frozen-schedule cause is removed by splicing the recomputed tail into the live list iterator, with no capability probe or downstream symptom guard (`template/src/pdca_harness/flow.py:1114`). |
| T1 Structure | PASS | Adoption is composed once into the shared `_drive_and_act` path, so every CLI shape inherits the same scheduling, integration, publishing, and budget machinery (`template/src/pdca_harness/flow.py:1256`). |
| T2 Shape | PASS | `git diff --check` and the rendered-site link audit passed, and the operator contract consistently describes lineage scope, held children, and the shared pool (`docs/07-crosscutting.md:257`). |
| T3 Runtime | PASS | Independent execution passed the focused 25 tests, the full 1,658-test driver suite, and all 7 root render/update-compat tests under the Copier interpreter (`template/tests/test_flow_adopt_split.py:346`). |
| T4 Contribution | NEEDS-HUMAN | Release-text approval is owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the recorded checker pass cannot be rerun and the user-impact opener plus #472 linkage remain unaudited (`template/pdca.toml.jinja:960`). |
| T5 Judgment | PASS | The contribution remains one logical feature and affected-path checks found prerequisite PR #470 already merged at the target, with no open or closed-unmerged competing implementation (`template/src/pdca_harness/flow.py:787`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Ship-or-iterate approval is owed — the human must decide whether same-call lineage adoption with loud, results-excluded holds is the right operator contract because that product trade-off determines fitness (`docs/07-crosscutting.md:257`). |

### Advisory — adversary

# Adversarial review — issue_472 (flow-adopt-core), advisory

Evidence re-run at `$PDCA_TARGET` (`/home/eddie/pdca/pdca-harness.pdca-wt`, base `3e3b829`):
C4 red leg reproduced by reverting only the production hunks (`flow.py`, `config.py`,
`cli.py`, `leaves.py`) and keeping the new test — **24 of 25 fail**; green leg 25/25. The
one pre-fix pass is `test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`, which is
a no-regression guard and is *supposed* to be green on both legs. The suite drives through
`cli._flow` → the production `flow_ids`/`_drive_and_act` (`flow.py:1364`) and builds
fixtures with the production `split.accept` (`split.py:525`), so it is not a parallel
re-implementation. Full offline driver suite: 1658 tests, OK.

## Findings

- **NEEDS-HUMAN [impl]** — `flow.py:914` (with `flow.py:696`): a lineage record whose
  `children` array holds a **non-string** entry drops that child **silently**, in the one
  branch of `_adoptable` that prints nothing. Concrete case, run at the target: parent 500
  splits into 601/602, then `split-lineage.json` is hand-edited to `"children": [601,
  "602"]` (ints — the shape any non-`split.accept` writer or a hand edit produces).
  `_lineage_children` filters `601` out at `flow.py:696` *before* `_adoptable`'s loop, so
  none of the four report branches (`flow.py:933`, `:939`, `:953`, `:957`) ever sees it and
  `ids` is non-empty so the "no readable children record" line at `flow.py:916` does not
  fire either. Observed result: **601 never adopted and never named on stderr; 602 adopted
  then immediately held on the `Depends on: 601` `split.accept` itself wrote; parent
  COMPLETE, both children left PLANNED, and the run exits 0.** The only line an operator
  gets is `issue_602 held this run — unresolved dependency (601)`, which reads as "601 does
  not exist" while a briefed PLANNED bundle sits next to it. That is precisely the
  stranded-children end state the feature exists to end, reached quietly. Every neighbouring
  malformed-id class in this diff is loud by design (`_PLAIN_ID`, `_inside_bundle_root`, no
  brief, already terminal), and the brief's guard list demands "skipped **with a report**";
  this one is the exception. `_adoptable`'s own docstring (`flow.py:897-904`) claims "Each
  id is then filtered exactly as `flow_ids` filters an explicitly named one" — it is not,
  for ids discarded upstream of the loop. Fix is small: have `_adoptable` count/report the
  entries `_lineage_children` refused, and pin it with a `_record(iid, [601, "602"])` test.

- **NEEDS-HUMAN [human]** — `flow.py:849` and the carve-out its docstring makes at
  `flow.py:841-846`: `_inside_bundle_root` now resolves symlinks (correctly closing the
  previous round's escape), but deliberately still accepts an `issue_<id>` that is a symlink
  to **another bundle inside the same root**. Probed at the target: with
  `results/issue_601 -> results/issue_910`, where `910` is an id the operator also named and
  which is still *un-driven*, the run adopts `issue_601` and schedules **`issue_601` and
  `issue_910` into the same wave** — the same directory driven as two bundles
  (interleaved `→ issue_601: Do…` / `→ issue_910: Check…` on one bundle dir), which under
  `lanes>1` is two lanes writing one bundle. The docstring's justification only covers the
  *already-finished* alias ("skipped as terminal like any other" — which I confirmed holds);
  the in-flight alias is the case it declines, on the grounds that re-keying the drive set by
  resolved path is a wider change. That is a defensible scope call, but it is a
  data-corruption class reached from the same hand-edited-record threat model the two guards
  beside it were added for, so a human should decide whether it ships as-is or gets a cheap
  resolved-path dedup in `_adoptable`.

- **NEEDS-HUMAN [impl]** — `flow.py:775`: the docstring the patch writes for the newly
  hoisted `_report_held` asserts, unconditionally, "a held bundle is never counted as work
  the run did". The patch's own comment eleven hundred lines later
  (`flow.py:1305`) says the opposite for the case it introduced: a **named** id held by the
  re-levelling is "PLANNED, in the results map, the run fails" — and
  `test_a_named_id_in_the_re_scheduled_tail_is_held_not_lost:595-596` pins exactly that
  (`results["811"] == PLANNED`, `rc == 1`). One helper, three call sites, two different
  downstream consequences; the shared docstring should state the child-only scope rather
  than the universal claim, since this is the file where a reader goes to learn what "held"
  costs a run.

## Refutations attempted and defeated

I could not break the following, and record the attempts so the absence is legible:

- **Mutation testing of the new code** (16 mutants against the bundle suite): `known =
  batch_names | taken` → `batch_names`; drop `_is_split_parent`'s terminal gate; lexical
  `_inside_bundle_root`; permissive `_PLAIN_ID`; hardcode the announced wave to `k+1`;
  per-wave allowance instead of `min(allowance, budget - spent)`; drop the `spent >= budget`
  break; drop the `named` protection; drop the duplicate-id dedup; cache a stale `last` for
  the fold boundary; make `_drive_wave` report 0 on each of its two un-finished exits; drop
  the retraction; report the refusal eagerly; make `_reschedule` strict. **All 15 real
  mutants were killed by named tests** (the 16th "survivor" was a no-op mutation I wrote:
  `wave_list[k:] = [wave_list[k]] + tail` is `wave_list[k+1:] = tail`). Notably the brief's
  required mutation — `known=batch_names` — is killed by
  `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once`, which the docstring at
  `flow.py:1062` cites by name as required.
- **The budget claim.** `budget = allowance * len(wave_list)` (`flow.py:1315`) with the
  break at `flow.py:1325`: for `k < len(wave_list)`, `spent ≤ allowance*k < budget`, so the
  pool is provably non-binding for a non-adopting run — the docstring/`config.py:312-325`
  claim holds. `allowance ≥ 1` is guaranteed (`config.py:675`, `cli.py:572`), so
  `min(allowance, budget - spent) ≥ 1` at the call site and the adoption recursion is
  bounded by `budget` waves; no zero-pass wave, no reset.
- **Termination / unbounded splice.** Adoption only runs after a driven wave, each driven
  wave costs ≥1 pass, a non-runnable wave `continue`s without adopting; `wave_list` cannot
  grow without spending the pool.
- **`flow_ids` totality.** `skipped | _drive_and_act(...)` (`flow.py:1595`) — I checked the
  case where an id the operator named was skipped UNPLANNED and is then materialised and
  adopted by a mid-run split: the right-hand map wins, so it is reported COMPLETE, not
  UNPLANNED.
- **Edge probes run at the target, all correct:** child bundle deleted between split and
  adoption (reported "no brief.md"); `children: []` and `children: [null, 601]` (both hit the
  loud "no readable children record"); record naming the parent itself (refused as already in
  the drive set); alias to an *already-completed* in-root bundle (skipped as terminal);
  adoption under `lanes=2` with the pooled beat sweep (waves and states correct).
- **Citation audit.** Every `path:line` the patch adds resolves on the merged base:
  `flow.py:679/694/759/1240/1354/1359`, `config.py:686`, `split.py:47/281/297/373/382-390/
  405/525/635`, `waves.py:243-246`, `gates.py:782`, the refreshed `cli.py:609-610` pointers
  (`flow.py:1549-1563`, `:1584-1590`), and all nine cited test names exist. The three docs
  anchors added to `docs/07-crosscutting.md` (`#the-split`, `#the-iteration-budget`,
  `#waves-in-execution`) resolve to real headings.
- **The ancillary `test_verify_base.py` hunk genuinely red→greens:** with
  `PDCA_VERIFY_BASE=some/branch` in the ambient environment, pre-hunk 11 of 19 fail,
  post-hunk 19/19 pass — it is a real hermeticity fix, not a cosmetic edit.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T4 Contribution — Release-text approval is owed — `commit-msg.txt` and `pr-description.md` were not supplied, so the recorded checker pass cannot be rerun and the user-impact opener plus #472 linkage remain unaudited (`template/pdca.toml.jinja:960`).
- [ ] Validation — fitness-to-purpose — Ship-or-iterate approval is owed — the human must decide whether same-call lineage adoption with loud, results-excluded holds is the right operator contract because that product trade-off determines fitness (`docs/07-crosscutting.md:257`).
- [ ] size backstop — this slice is behaving oversized: 3 round(s) already spent (threshold 3). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.
- [ ] `flow.py:1001` (`wave_list[k + 1:] = tail`, splice) with the
- [ ] `cli.py:794`: `pdca split <id> --accept` — the command the Plan /
- [ ] Fitness-to-purpose, for sign-off: a first-reschedule-held child is
- [ ] T4 in `check-gates.json` is the one gating row that carries an

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
- Iteration delta (if iterating): Rejected on the round-3 adversary's implementation findings; the core mechanism is converged and must not be re-derived — fix narrowly: 1. `flow.py:914` (with `:696`): a lineage record whose `children` array holds a non-string entry (e.g. `[601, "602"]`) drops that child SILENTLY — never adopted, never named on stderr, run exits 0 with the child left PLANNED. Every neighbouring malformed-id class is loud; make `_adoptable` count/report the entries `_lineage_children` refused, and pin it with a `_record(iid, [601, "602"])` test. 2. `flow.py:775`: `_report_held`'s docstring claims unconditionally "a held bundle is never counted as work the run did", contradicted by the named-id case at `flow.py:1305` (PLANNED in the results map, rc=1). Scope the docstring to the child-only case. 3. `flow.py:849`: an in-flight `issue_<id>` symlink aliasing another named, un-driven bundle inside the root gets one directory driven as two bundles in the same wave (two lanes writing one dir under lanes>1). Close it with the cheap resolved-path dedup in `_adoptable` — not the wider re-keying of the drive set by resolved path.
- By / date: Eduard Ralph / 2026-08-09

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
