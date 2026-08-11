# Build notes — issue 449 (Iteration 5) — flow adopts split children mid-run

**Target branch:** `eduralph/pdca-harness` @ `pdca-integration/main` (stack base), worktree
`$PDCA_WORKTREE = /home/eddie/pdca/pdca-harness.pdca-wt-l0`, base commit **`aaa797a`**
(`pdca-integrate: issue_456` — the `split-lineage.json` record this slice reads is already
in the base). All `path:line` citations are **post-patch line numbers in that worktree**
unless marked *(base)*.

---

## 1. What this iteration is

The Iteration-4 sign-off was explicit: *"The adoption mechanism is proven — C4 red→green
reproduced and mutation-tested (7/7 mutations caught) — keep it unchanged. Fix ONE narrow
defect, do not re-architect."* So this iteration **starts from the iteration-v4 patch,
byte-for-byte**, and changes only what the carry-forward named. Detect → validate → splice
→ report, the transitive bounded walk, the run-wide pass pool, `_RunSoFar`, the dedup — all
untouched.

The whole production delta v4 → v5 is **+34 / −4 lines**, of which **6 are executable
statements** — the rest is the rationale the next reader needs:

| File | Δ (v4 → v5) | Executable |
|---|---|---|
| `template/src/pdca_harness/flow.py` | +24 / −2 | 2 (`except PreflightError:` / `raise`) |
| `template/src/pdca_harness/cli.py` | +10 / −2 | 4 (`try` / `except` / `print` / `return 1`) |
| `docs/07-crosscutting.md` | +5 / −1 | — (one sentence) |
| `template/tests/test_flow_adopt_split.py` | +110 / −7 | 2 new tests, 4 helpers |

## 2. The defect, and why the fix is where it is

**Finding (Iteration 4):** the single-id adoption tail is wrapped in `_isolate`
(`flow.py:473`; `flow.py:451` in v4), and `_isolate` contains **every** `Exception`
(`flow.py:63` *(v4)*). `_drive_and_act` raises `PreflightError` when the first wave that
would actually fan out fails its declared per-lane preflight (`flow.py:1231`) — a refusal of
the whole run, which both batch entry points let out to the CLI, where it is printed and
turned into rc 1 (`cli.py:598` for `--from-csv`, `cli.py:663` for an id list). Adoption is
the *first* thing that can give a single-id run a wave wide enough to fan out, so it is the
first thing that can be refused one — and the tail swallowed that refusal. On byte-identical
disk, `pdca flow 500` exited **0** with its children still `PLANNED` where
`pdca flow 500 601` exited **1**. That contradicts the entry-point-consistency contract this
patch itself documents (`flow.py:1137` *(post-patch)*, `docs/07-crosscutting.md:256-262`) and
Iteration 1's RULING (b).

**The fix, in two halves — both required:**

1. **`_isolate` never contains a run-abort** (`flow.py:78-79`, rationale at
   `flow.py:66-74`, contract on the exception class at `flow.py:39-42`). `_isolate`'s
   contract is *per-bundle* containment — "skip **that** bundle and let the others proceed"
   — and a preflight refusal is not one bundle's fault: the instance's declared per-lane
   resources are absent, so every bundle the run fans out would come back false-red.
   Stating the rule in `_isolate` rather than at the one callsite that can raise it today is
   deliberate: containment sites are added over time (there are 11 in this file), and a
   run-abort must not become containable again by accident.
2. **The CLI's single-id route reports it like the batch routes** (`cli.py:639-648`).
   Without this, half the fix is worse than none: the exception escapes `cli._flow` as an
   **unhandled traceback** — verified, §4(a) — which is neither the batch route's one-line
   `flow: lane preflight failed …` nor a controlled rc 1. Measured directly: with the
   `flow.py` half applied and the `cli.py` half reverted, the CLI test **errors** rather
   than passing.

The comment at the tail callsite (`flow.py:456-462`) now says which failures it contains and
which it does not, so the next reader does not re-derive the question.

**Consequence for the aborted single-id run:** `_sweep_quietly` and the Act tail
(`flow.py:477-479`) are skipped, and no state string is returned. That is exactly what the
batch path already does on the same refusal (its sweep and Act live at the end of the
`_drive_and_act` that raised), so "abort" means the same thing at both entry points. The
parent's own publish has already run by then (`flow.py:442-450`), so nothing of the parent's
cycle is lost.

### Alternatives, with their costs

* **Scope `_isolate` to the detect/validate step instead** (the carry-forward's other
  option). Detect/validate lives *inside* `_drive_and_act` (`_adopt_split_children` →
  `_children_of_split`, already `_isolate`d at `flow.py:981`), so "scoping" means splitting
  the tail into a detect call plus an unguarded drive call — the seed pre-pass at
  `flow.py:1195-1197` would have to be hoisted out of `_drive_and_act` and re-invoked from
  `flow`, ~25 lines across two functions, and the single-id path would stop sharing one
  entry into the shared body. Rejected: more code, and it removes containment from failures
  that *should* be contained (a leaf that corrupts a child bundle mid-drive).
* **Catch `PreflightError` only at the tail callsite** (`except PreflightError: raise`
  inline). Same 2 executable lines, but it re-states `_isolate`'s reporting or nests two
  handlers, and it leaves the other 10 `_isolate` sites silently able to swallow a future
  run-abort. Rejected on the invariant, not on size: the rule is about what `_isolate`
  *means*.
* **Make `PreflightError` a `BaseException`.** One line, and wrong: every `except
  Exception` in the tree that legitimately wants to log-and-continue would stop seeing it,
  and it would sail through the CLI's own guards too.
* **Re-architect the single-id path through `_drive_and_act` wholesale.** Ruled out in
  Iteration 4 with a measured cost (~90 rewritten lines on the hottest path,
  `flow.py:390-421`/`:423-432`/`:455-458` *(v4)*); the carry-forward again says "do not
  re-architect". Unchanged verdict.

## 3. New tests

Both live in the brief's file, `template/tests/test_flow_adopt_split.py`, and drive the real
entry points. The suite goes 15 → 17 tests.

| Test | Binds |
|---|---|
| `test_a_refused_run_aborts_both_entry_points_identically` (`:425`) | `flow.flow` and `flow.flow_ids` on identical disk both raise `flow.PreflightError`, with the same message and the same states left behind (parent COMPLETE, both children PLANNED) |
| `test_the_cli_exits_1_on_a_refused_run_however_many_ids_it_was_given` (`:461`) | the operator-visible half: `pdca flow 500` and `pdca flow 500 999` both return **1** and print the **same** single `flow: lane preflight failed …` line |

Supporting fixture work, all defaulted so no existing test changes behaviour:
`_stub_config(..., lanes=1, lane_preflight="")` (`:39`), threaded through `_instance`
(`:117`) and `_reset` (`:123`); `_SIBLING_TWO` (`:96`) — the independent second child, which
is what makes the adopted children land in **one** wave of two runnable bundles (the shape
that pools, `flow._wave_pools`); `_arm_a_refused_adoption` (`:264`); `_complete_bystander`
(`:246`) — a real bundle driven to COMPLETE by production code, so naming it changes the
command's **arity** (which is what selects the entry point, `cli.py:602`) without changing
what the run drives; `_flow_args` (`:257`).

Why the second test goes through `cli._flow` and not just the two `flow.*` functions: the
finding is stated in exit codes ("exits 0 … where … exits 1"), and the arity switch that
picks the entry point lives in the CLI. `cli._flow` is the CLI's route *into* `flow.flow` /
`flow.flow_ids`, not a bypass of them — the brief's "never call an internal helper" rule is
about not skipping the entry points, and this skips nothing. The same `SimpleNamespace` argv
shape the existing suite uses (`test_flow_slice.py:385` *(base)*).

## 4. Forced refutation — the three questions

**(a) Genuine red? Yes — three separate mutations, all through the project's runner
(`./engine/scripts/run-verify.sh`, the configured C4 gate cmd, with `PDCA_BUNDLE` /
`PDCA_WORKTREE` set).**

*Whole patch (production hunks reverted to base `aaa797a`, tests kept — the gate's own red
leg):*

```
== C4 green leg: … Ran 17 tests … OK
== C4 red leg:   … Ran 17 tests … FAILED (failures=21, errors=1)
C4 PASS: red without the fix, green with it
```

*Iteration-targeted (the one that matters — a whole-patch red would also be produced by v4's
code): **iteration-v4's `flow.py` + base `cli.py`, under THIS iteration's tests.*** Exactly
the two new tests fail; the other 15 stay green:

```
FAIL: test_a_refused_run_aborts_both_entry_points_identically (entry='flow')
        AssertionError: PreflightError not raised        ← the swallowed abort
        (the entry='flow_ids' subtest PASSES on v4 — which is the asymmetry itself)
FAIL: test_the_cli_exits_1_on_a_refused_run_however_many_ids_it_was_given
        AssertionError: 0 != 1                            ← "exits 0 with children PLANNED"
Ran 17 tests … FAILED (failures=2, errors=1)
```

*Half-fix (v5 `flow.py`, **base `cli.py`**) — proves the CLI hunk is load-bearing, not
decorative:*

```
ERROR: test_the_cli_exits_1_… (entry='flow', argv=['500'])
        PreflightError escaping cli._flow as an unhandled traceback
        (flow.py:473 → _isolate → _drive_and_act → raise)
Ran 17 tests … (2 errors)
```

**(b) Production path? Yes.** Every assertion is produced by the real
`flow.flow` / `flow.flow_ids` / `cli._flow`, with stub *leaves* only (the shipped
`mode="stub"` implementations, the fixture shape of `test_flow_slice.py:32-55` *(base)*).
The refusal is the **production** `preflight.lane_preflight` running the instance's declared
`[driver].lane_preflight` command and failing — not a patched-in raise, not a mocked
preflight. The split is still produced by the production `split.accept`
(`test_flow_adopt_split.py:143`), so the close marker, `split-lineage.json` and the child
bundles are byte-for-byte what `pdca split --accept` leaves. The only doubles are the leaf
stubs (standing in for interactive human sessions) and two pass-through spies that record
and then call the production function.

**(c) Fixture includes the fault? Yes — twice over.** The fault under test is *the abort*,
and the fixture creates a genuine one: `lanes=2` plus a `lane_preflight` that exits non-zero,
with two **independent** adopted children so the adopted wave really is wide enough to fan
out (a curated fixture using the default dependent sibling would put each child in its own
wave, never pool, and never preflight — it would pass vacuously; I checked that the
independent sibling is required). Nothing is excluded: the assertions read the states of
the parent **and both** children after the abort (`:450-459`), and the CLI test asserts on
disk that 601 is still `PLANNED` inside each subtest, so a run that "aborted" after quietly
driving something would fail.

## 5. Gates run locally (project runners — no hand-rolled invocation)

| Runner | Result |
|---|---|
| `./engine/scripts/run-verify.sh` (C4, gating) | `C4 PASS: red without the fix, green with it` |
| `./engine/scripts/run-suite.sh` (T3) | `== T3: root suite OK, driver suite OK` — root **7 tests OK**, driver suite **1639 tests OK** (skipped=2) |
| `./engine/scripts/run-docs-check.sh` (T2) | `lint_docs: OK`, `render_site: link audit OK` (22 pages) |

T3 was run with `env -u PDCA_VERIFY_BASE`. The 11 `template/tests/test_verify_base.py`
failures that failed the last four iterations are the **pre-existing** harness
test-isolation fault the carry-forward rules out of scope (`PDCA_VERIFY_BASE` leaking from
the driver into the suite's subprocesses). Without that leak the suite is fully green here,
which both confirms the diagnosis and shows this patch adds no failure: 1639 tests, 0
failures — 2 more than iteration 4's 1637, exactly the two tests added above. **Expect the
same non-gating red on the driver's own T3 run; it is not this patch's.**

## 6. Commit-readiness

The target repo (`eduralph/pdca-harness`) configures **no** formatter/linter hooks — no
`.pre-commit-config.yaml`, no `pyproject.toml` / `setup.cfg` / `.flake8` / `.editorconfig`,
no `.git/hooks` beyond samples (verified in the worktree). Its CI is `docs-check.yml`,
`docs.yml`, `render-check.yml`, `require-linked-issue.yml`: the first three are what the
T2/T3 runners above execute (green), the fourth is satisfied by the `Fixes #449` trailer the
publish step writes. `CONTRIBUTING.md:22-27` asks for one logical change per PR, a test, a
green offline suite (all hold) and a DCO `Signed-off-by` trailer, which `git commit -s` adds
at publish. Added lines stay inside the files' existing widths (longest added line: 93 chars
in `flow.py`, 96 in `cli.py`, against existing maxima of 106 and 147). `patch.diff` was
re-verified to apply cleanly with `git apply --check` against a pristine `aaa797a`.

## 7. What I deliberately did NOT do

* **Did not touch the adoption mechanism** — no change to detect/validate/splice/report, the
  budget pool, the wave numbering, the dedup or the transitive walk. The carry-forward says
  keep it; the 15 pre-existing tests pass unmodified against it.
* **Did not make the aborted single-id run still sweep / still run Act** (a `try/finally`
  around the tail). It would make the single-id path do *more* on an abort than the batch
  path does, re-opening the divergence from the other side.
* **Did not widen the re-raise to a list of "run-aborting" types.** `PreflightError` is the
  only `Exception` in the tree that means "the run is refused" (sole raise site,
  `flow.py:1231`); `KeyboardInterrupt` / `SystemExit` already propagate because only
  `Exception` was ever contained. A speculative tuple would be untested surface.
* **Did not touch `test_verify_base.py` / the `PDCA_VERIFY_BASE` leak** — explicitly out of
  scope per four consecutive carry-forwards. It remains a real harness defect worth its own
  bundle.
* **Did not revisit Iteration 3's fitness call** (a recovery run's pool is one wave's worth):
  documented at `docs/07-crosscutting.md:335-340`, unchanged.

## 8. STOP discipline

No branch pushed, no PR opened, nothing marked ready or merged. `patch.diff`, the test at
the brief's path (`template/tests/test_flow_adopt_split.py`, also copied into the bundle as
`test_flow_adopt_split.py`) and these notes are the whole deliverable.
