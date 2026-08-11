# Build notes — issue_469, flow: adopt split children mid-run on the unified drive path

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) off the wave base `e955b79`
(`pdca-integrate: issue_468` — child-1's accepted unified drive path, i.e. `stack-base =
pdca-integration/main`). Every `path:line` below is that tree **with the patch applied**.

## What I built

Re-landed #449's adoption mechanics **once**, on the shared wave path #468 created, plus
the recovery seed on `flow_ids`:

| Piece | Where (post-patch) |
|---|---|
| shared held-report (was inline in `flow_batch`) | `flow.py:768`, reused at `flow.py:928`, `flow.py:1379` |
| `SPLIT_DISPOSITION` marker value | `flow.py:801` |
| `_is_split_parent` — TERMINAL **and** marker == `split`, total catch | `flow.py:804` |
| `_adoptable` — read `split.read_lineage`, filter (dup / path-escape / known / no brief / terminal), walk-on list | `flow.py:831` |
| `_children_of_split` — the one detect+validate step | `flow.py:908` |
| `_reschedule` — `partition_schedulable` tolerance + `compute_waves` | `flow.py:916` |
| `_adopt_split_children` — queue, splice into `wave_list[k+1:]`, announce REAL wave | `flow.py:939` |
| `_drive_wave` returns the passes it consumed | `flow.py:1041`, `:1073`, `:1103`, `:1112` |
| run-wide pool, sized off the ORIGINAL schedule | `flow.py:1181` |
| seed pre-pass (`k=-1`) | `flow.py:1188` |
| pool binds between waves | `flow.py:1201` |
| per-wave allowance = `min(allowance, budget - spent)` | `flow.py:1234` |
| mid-wave splice after the wave that split | `flow.py:1240` |
| `last` → live `len(wave_list) - 1` (the list grows) | `flow.py:1287` |
| `flow_ids`: terminal-on-split id becomes an adoption **seed** (keeps #468's skip note + hint + its own disposition in the results map) | `flow.py:1479`, `:1482`, `:1485` |
| docs / prompts that stated the opposite | `docs/07-crosscutting.md` §The split + §The iteration budget, `template/agents/planner.md.jinja`, `leaves.py` `_plan_prompt`, `config.py` `max_passes` comment |

Reused rather than re-derived, per the brief's peer-callsite list: `_lineage_children`
(`flow.py:678`, child-1's tolerant `children` reader — so the terminal hint and adoption
cannot disagree about what a record names), `_point_at_integration` (`flow.py:637`, adopted
waves go through the ordinary call at `flow.py:1230`, asserted by
`test_adopted_children_go_through_the_same_integration_reconciliation`), `_warn_abandoned`'s
not-terminal predicate (`flow.py:738`), the held-report shape (verbatim text from the old
`flow_batch` lines), and `tests/test_flow_slice.py:32-55` for the offline fixture.

## What #468 let me delete from the v5 design (and why that is not a regression)

The preserved v5 patch (`results/issue_449/iteration-v5/patch.diff`) carried three pieces
that existed **only** to keep two drive paths in step. On the unified path they are dead
weight, and shipping them would re-create the thing #468 removed:

* `_RunSoFar` (dataclass + `carried=` parameter + `wave_offset` threading through
  `_adopt_split_children`) — 41 lines in v5 (`patch.diff:305-323`, `:458-461`, `:471-474`,
  `:631-634`, `:666-669`). It existed because `flow.flow` drove wave 0 in its own loop and
  the adoption tail had to be told "you are wave 1 of a run that already spent N". Here
  there is one loop, so the announced index **is** the schedule index (`flow.py:1017-1018`).
* `flow.flow`'s adoption tail + its `spent` accounting + the terminal short-circuit
  (v5 `patch.diff:221-269`, ~35 lines) — `cli._flow` never calls `flow.flow` after #468
  (`cli.py:613-622`), so a tail there would be an unreachable second implementation. I
  added a docstring paragraph at `flow.py:387-392` saying so, rather than code.
* the `_isolate` `PreflightError` carve-out (v5 `patch.diff:199-217`, 8 lines) — v5 needed
  it because its tail ran `_drive_and_act` *inside* `_isolate`. Here `_drive_and_act` is
  called directly, so a refusal propagates to `cli._flow`'s existing `except
  flow.PreflightError` for both arities. Proven, not assumed:
  `test_a_refused_adopted_wave_exits_1_at_either_arity` fails on the red leg (rc 0) and
  passes green (rc 1, one line, children PLANNED) — i.e. the parity that carve-out bought is
  now structural.

Net: the production hunks are 390 changed lines in `flow.py` against v5's ~470 for the same
mechanics, and there is exactly one call site per beat.

## Decisions, and the alternatives I rejected

**Adoption in `_drive_and_act`, not in `flow_ids` alone.** `flow_ids` can only see the ids
it was given at t=0; the mid-run split (criterion 1) happens *inside* the wave loop, and the
recovery case (criterion 2) needs the same splice. Putting the splice in `flow_ids` would
have meant re-entering `_drive_and_act` per generation — a second budget, a second wave
numbering, and the exact "two paths, kept in step by hand" failure mode.

**Pool = `allowance × max(1, len(original waves))`, not a flat `allowance`.** A flat pool
would truncate ordinary batches that adopt nothing: a four-deep `Depends on` chain at
`--max-passes 1` finishes today (4 waves × 1) and would strand three bundles under a flat
pool. That is not a hypothetical — it is
`test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`, which passes on **both** legs
(it is one of the three deliberate preservation guards, green pre-fix by design).

**Strict `compute_waves` for the ids the operator NAMED; tolerant
`partition_schedulable` only for what adoption ADDS** (`flow.py:1175`, `flow.py:927`). Using
tolerance for the whole set would make `pdca flow 800 801` (a cycle) stop raising as soon as
some unrelated bundle on disk carried a lineage record — one command line, two behaviours
depending on disk state. Pinned by `test_a_named_id_list_keeps_its_strict_scheduling_contract`.

**Kept #468's terminal skip note + `_terminal_hint` for a seed parent, and added one line
after it** (`flow.py:1470-1481`). Suppressing the hint for split parents would have been
"cleaner" output but breaks `test_terminal_split_parent_names_children_never_rm_rf`
(`test_flow_entrypoint_parity.py:344`), which exists because deleting a split parent
destroys the only on-disk record of the split. The hint stays right: the parent itself is
still not driven, and `--accept`'s `pdca flow <child-ids>` remains the answer for a child
that was held.

**Docs/prompts included** (48 + 31 + 16 lines). Not strictly in the brief's Scope list, but
`leaves.py:582-591` and `planner.md.jinja:163-179` currently tell the planner "EVERY OTHER
SHAPE … drives exactly the ids it was given and never looks for new ones", which this patch
makes false — a prompt that lies is a defect the next Plan beat acts on. The wording keeps
every token the existing doctrine tests assert (`test_split.py:1269-1284`: `csv`,
`flow 500 501`, `flow <child-ids>`, and no "or several ids"), and T2 docs lint + link audit
are green.

## Evidence

* **C4 (the project's own runner, `./engine/scripts/run-verify.sh` with `PDCA_BUNDLE` /
  `PDCA_WORKTREE`):** `C4 PASS: red without the fix, green with it` — green leg 19/19 OK;
  red leg (production hunks reverted, test kept) **16 failures**.
* **T3 `./engine/scripts/run-suite.sh`:** `root suite OK, driver suite OK` — 1652 tests in
  `template/tests` (1633 pre-existing + 19 new), nothing else moved. (The brief warned about
  a pre-existing `test_verify_base.py` red under an inherited `PDCA_VERIFY_BASE`; it did not
  appear in this environment.)
* **T2 `./engine/scripts/run-docs-check.sh`:** `lint_docs: OK`, `render_site: link audit OK`.
* `git diff --check` clean; no formatter/linter/commit hook is configured in the target
  (`.pre-commit-config.yaml` absent, `core.hooksPath` unset, CONTRIBUTING names only the
  offline suite + DCO trailer, which publish adds).

### The three tests that are green pre-fix — deliberately

`test_a_run_that_adopts_nothing_keeps_a_full_budget_per_wave`,
`test_a_named_id_list_keeps_its_strict_scheduling_contract`,
`test_an_unreadable_close_marker_never_kills_the_run`. Each asserts that something did **not**
change, so "green before and after" is their contract; the other 16 (including both guards
that could have been written as no-change assertions — the non-terminal parent and the
path-escape — which is why each carries a second leg that *does* adopt) are red pre-fix.

## Forced self-refutation

**(a) Genuine red?** Yes — actually reverted, not reasoned about. `run-verify.sh` reverts the
production hunks (`git apply -R --exclude=tests/* --exclude=template/tests/*`) and re-runs the
module: `FAILED (failures=16)`, e.g. `test_cli_flow_drives_the_children_of_a_mid_run_split`
→ `AssertionError: 'PLANNED' != 'COMPLETE'` for issue_601, and
`test_a_refused_adopted_wave_exits_1_at_either_arity` → rc `0 != 1`. Then it re-applies and
the module is 19/19 green.

**(b) Production path?** Yes. Every test drives `cli._flow(cfg, argv-namespace)` — the real
CLI entry — which calls the real `flow.flow_ids` → `_drive_and_act` → `_drive_wave` →
`driver.advance`. Nothing is re-implemented: the split fixtures call the **production**
`split.accept` (`split.py:525`), so the close marker, `split-lineage.json` and the child
bundles are byte-for-byte what `pdca split --accept` writes; the stranded-split fixture is
built with the production `flow._drive_wave` (which has never adopted) rather than by hand.
The only substitutions are the six leaf stubs the offline suite already uses, a scripted
sign-off decision (`iterate-plan` / `iterate-do`, written into the real
`leaves.SIGNOFF_DECISION` file the real `_apply_decision` consumes), and pass-through spies
that record and then call the real `_build_all` / `_drive_wave` / `_point_at_integration` /
`flow_ids` and hand back their real return values.

**(c) Fixture includes the fault?** Yes. The bundle that splits is *in the drive set* and is
driven to terminal by the run under test (criterion 1), or is the *named id* that is already
terminal on a split with its children PLANNED on disk (criterion 2 — asserted PLANNED before
the run starts, `_strand_a_split`). The hostile inputs are really present, not curated away:
the escaping lineage id `"../../etc"` sits in the real record next to a legitimate sibling
that must still be adopted; the duplicate `["601", "601", "602"]` is in the real record; the
held child really carries an unresolvable `Depends on: GHOST`; the corrupt marker is real
non-UTF-8 bytes; the refused run really executes a failing `[driver].lane_preflight` against
a genuinely pooled (lanes=2, two runnable) adopted wave.

## Not done / for the human

* `flow.flow` (the single-bundle **library** driver, `flow.py:367`) does not adopt — by
  design, argued above and recorded in its docstring. If the reviewer reads the brief's
  "so `flow`, `flow_ids` and `flow_batch`'s drive phase inherit it from one implementation"
  as requiring a tail there too, that is the one place my reading of the brief could be
  contested; adding it would re-introduce v5's `_RunSoFar` (≈41 lines) and a second budget,
  against #468's `test_flow_entrypoint_parity`.
* Publishing/folding of adopted waves is inherited (`_publish_bundle`, `integrate.fold` run
  from the same loop) but not asserted here: the new tests run `--no-publish`, like the peer
  parity suite, so no test needs git remotes. `_point_at_integration` coverage is the
  structural stand-in.
* No external dependency was missing; everything ran offline with python3 + git.
