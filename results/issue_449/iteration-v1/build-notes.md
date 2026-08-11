# Build notes — issue 449 (flow adopts split children mid-run)

Target: `eduralph/pdca-harness` @ `main`. Built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`) off `aaa797a` ("pdca-integrate: issue_456"),
i.e. **with 456's `split-lineage.json` already landed** — the record this slice reads.
The brief's citations were verified at `b95aa58`; line numbers below are against the
worktree head (453 + 456 shifted them).

## What the change is

One detection point, one splice, and the same wave machinery for everything else.

* **Detect** — `flow.py:723 _is_split_parent` (terminal **and** `close-disposition ==
  "split"`), called after the wave drives at `flow.py:1050` and on the single-id exit at
  `flow.py:420`.
* **Validate** — `flow.py:740 _adoptable` reads the child ids out of the parent's
  `split-lineage.json` via the tolerant production reader `split.read_lineage`
  (`split.py:373`), then applies exactly `flow_ids`' own filters (missing / UNPLANNED /
  already-terminal / already in the drive set). No prose parse of the `build-notes.md`
  breadcrumb (`split.py:627-634`).
* **Splice** — `flow.py:817 _adopt_split_children` replaces `wave_list[k+1:]` with
  `_reschedule` (`flow.py:795`) over *the run's remaining bundles + the children*, using
  `waves.partition_schedulable` + `waves.compute_waves` — the resume path's tolerance, so
  an unresolvable dependency **holds** and the run continues.
* **Report** — one line per adoption, `flow: issue_500 split → adopted children
  issue_601, issue_602 into wave 1` (`flow.py:863-865`, and the single-id twin at
  `flow.py:894`); holds go through the shared `_report_held` (`flow.py:701`), which
  `flow_batch` now also calls (`flow.py:1189`) so the two reports cannot drift.
* **Single-id path** — `flow.py:868 _adopt_after_split` hands the children to
  `_drive_and_act` as a fresh drive set *before* the publish/Act tail, with what is LEFT
  of the run's `max_iters` (`spent`, `flow.py:390`).

### The one structural trick, and why it is safe

`_drive_and_act` iterated `for k, wave in enumerate(wave_list)` and cached
`last = len(wave_list) - 1`. I kept the `for` and dropped the cache
(`flow.py:1097`: `if k < len(wave_list) - 1`). A CPython list iterator holds an index and
re-reads the list each step, so a slice assignment to `wave_list[k+1:]` *is* picked up —
which means an adopted child's wave is driven, signed off, published and folded by exactly
the code every other wave goes through. No parallel loop, no second scheduler, no second
publish path. The alternative (a `while k < len(wave_list)` loop) forces restructuring the
`if not runnable: continue` body around the manual increment: +6 lines and a new
infinite-loop failure mode if a future `continue` skips the increment. I wrote the reliance
on list-iterator semantics into the comment at `flow.py:1015-1019` so it is not a silent
assumption.

Everything else the brief asks for falls out of joining `bundles` / `batch_names`
(`flow.py:1008`, `flow.py:861-862`): the results map, the final `_sweep_quietly`,
`_runnable`'s in-batch prereq rule, and `_point_at_integration` — the child is pointed at
its own `(repo, base)` integration branch by the *existing* per-wave call, not a second
mechanism.

### Detection point: one, not two

The Design lists two (after a wave drives, **and** after `_build_all`'s serial Plan
pre-pass). I implemented one, deliberately: a bundle split during the Plan pre-pass takes
the close fast path in the *same* wave (`driver.advance` BUILT branch → close gates →
close review note → AWAITING_SIGNOFF → sign-off), so it is terminal-with-`split` by the
time the wave ends and the post-wave detection sees it. The test proves exactly this path
(the split happens inside a re-plan, mid-`_drive_wave`). The only case a second detection
point would add is a parent left **AWAITING_SIGNOFF** — a split whose close nobody has
confirmed yet — and adopting there would spend a whole wave on a decomposition the next
sign-off may reopen (`iterate-do` archives the split marker, `driver._close_class`
comment). That is why `_is_split_parent` requires terminal.

## Alternatives ruled out

* **Re-enumerate `results/` between waves.** One line, and wrong for the reason the brief
  gives: every explicit-id flow silently becomes a disk sweep. Locked out by a test
  (`test_adoption_follows_the_lineage_edge_not_a_disk_sweep`, which leaves an unrelated
  in-flight `issue_STRANGER` on disk and asserts it is neither driven nor in the results).
* **Parse child ids out of `build-notes.md`.** Works today (`split.py:630`), but that
  string is prose for a human; 456 shipped the record precisely for this consumer.
* **Adopt into the current wave.** The wave's fold happens once at its end
  (`flow.py:1097-1140`); a child arriving mid-wave would build on a base about to move.
* **Give the children a fresh run (`flow_ids` re-entry with default budget).** Rejected on
  the brief's own constraint — they must share the run's budget, not reset it. Hence the
  `max_iters - spent` deduction on the single-id path. Note the asymmetry I chose
  knowingly: in `_drive_and_act` the run's `max_passes` is already a *per-wave* budget, so
  adopted children get the same per-wave allowance as any other wave (no deduction is
  possible without changing what `max_passes` means for every existing run); on the
  single-id path there is no wave structure to bound recursion, so the remainder is
  deducted and a spent budget is reported with a resume hint instead of driving on.

## Scope calls (two files beyond `flow.py`)

The brief's Motivation quotes the planner's runtime prompt as *"the planner's own runtime
prompt documents the limitation instead of the harness fixing it"*. Shipping the fix while
that prompt still tells every planning session "EVERY OTHER SHAPE … drives exactly the ids
it was given and never looks for new ones" would leave the product asserting the defect it
just fixed — the model would keep steering humans to restart by hand. So:

* `leaves.py:581-589` (`_plan_prompt`) — rewritten to state adoption, the held case, and
  that `--accept`'s printed command remains right for a split accepted **outside** a
  running flow (which the brief keeps in place).
* `template/agents/planner.md.jinja:162-175` — the same claim in the role file (the code
  comment at `leaves.py:572-575` says both are stated on purpose). Per `INTEGRATION.md` §4
  this is a project-defined NEEDS-HUMAN item (agent role prompts are human-judged) — the
  human should read the new wording at sign-off.
* `docs/07-crosscutting.md:243-263` — one paragraph in "Size & split", where the lineage
  record is already documented, describing adoption, its scope boundary and the two
  degrade paths. `docs/**` is non-behavioural for C4, and T2 (`lint_docs` + link audit)
  is green.

## Verification

Runner: the project's own gate scripts (`pdca.toml [[checks]]`), not a hand-rolled
invocation.

* `./engine/scripts/run-verify.sh` (C4, gating) → **`C4 PASS: red without the fix, green
  with it`**. Green leg: 5 tests OK. Red leg (production hunks reverted,
  `--exclude=template/tests/*`): `FAILED (failures=5)`, no import failure.
* `./engine/scripts/run-suite.sh` (T3) → `root suite OK, driver suite OK` (both the
  template-repo suites and the whole offline driver suite).
* `./engine/scripts/run-docs-check.sh` (T2) → `lint_docs: OK`, `render_site: link audit
  OK`.

No formatter/linter is configured in the target (no pre-commit config, no ruff/flake8);
the house style is hand-held. Added lines are ≤ 95 chars, matching the file.

### The three refutation questions

**(a) Genuine red?** Yes — and not by inspection: `run-verify.sh` itself reverts the
production hunks and re-runs the module. All **5/5** cases fail without the fix
(`AssertionError: 'PLANNED' != 'COMPLETE'` for the adopted children, `None != 'COMPLETE'`
for the results map, and the missing stderr announcements). The module still *imports* on
the red leg — the test touches no symbol this patch adds, so the verifier's
`unittest.loader._FailedTest` trap (exit 77 PDCA-UNVERIFIABLE) is not hit.

**(b) Production path?** Yes. The test drives `flow.flow_ids` and `flow.flow` — the real
entry points, whose frozen drive set *is* the defect — never an internal helper and never
a re-implementation. The split itself is not simulated either: `_split_now` calls the
production `split.accept`, so the parent's `close-disposition`, its merged
`split-lineage.json` `children` record, the archived attempt and the child bundles are
byte-for-byte what `pdca split --accept` leaves. The only stubs are the leaves (the six
model calls) and a spy around `flow._drive_wave` that records wave membership and then
calls the real one.

**(c) Fixture includes the fault?** Yes. The failing element is present, not curated out:
the parent really goes terminal on a `split` disposition **inside** the run (the documented
Entry-B path — the first sign-off session records `iterate-plan`, the driver re-opens the
bundle, and the next pass's Plan pre-pass splits it), and the assertion is on the state of
the *children on disk* plus the run's results map. The scope test additionally leaves an
unrelated in-flight bundle in `results/` (the thing a naive disk sweep would wrongly
adopt); the hold test leaves a child with an unresolvable `Depends on` in place rather than
removing it; the degradation test deletes the lineage record and asserts the run still
finishes and says so. `test_flow_ids_drives_the_children_of_a_mid_run_split` asserts the
exact wave sequence `[[issue_500], [issue_601], [issue_602]]`, so "in a wave AFTER the
parent's, honouring their own `Depends on`" is measured, not assumed.

No external dependency beyond python3 ≥ 3.11 stdlib + git was needed; nothing was stubbed
in place of a real tool.

## Known limits (for the reviewer's attention at sign-off)

* Adoption termination rests on each adopted child being new to the run (`known` /
  `examined`) over a finite set of on-disk bundles; a *live* recursive splitter is bounded
  by that plus the per-wave pass budget, not by a separate depth cap. 448/456's `depth`
  field exists if a future slice wants a hard cap — out of scope here (the brief: "must
  merely not enable an infinite one").
* A child held at adoption is reported and left in flight, and (unlike a driven child) is
  not re-checked later in the same run; the operator's `pdca flow <id>` remains the remedy,
  which is what `--accept` already prints.
