# Build notes — issue 315 / prepublish-review-stage

Target: eduralph/pdca-harness @ main (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`,
base `abd6f1e`). All `path:line` cites below are against that tree with the patch applied.

## What was built

A config-gated pre-publish review stage in the publish seam the brief names — after
`_t4_passes` and before any git step, covering **both** PR paths (the call site at
`publish.py:229` sits before the `Onto branch` dispatch at `publish.py:245`):

1. **Config** — `[publisher.review] {enabled, passes=3, max_iters=3}` →
   `Config.prepublish_review` (`config.py:137`, parsed `config.py:635`), read defensively
   by `_prepublish_cfg` (`publish.py:793`). `enabled` is strict-boolean (the
   `network_access` rule, `config.py:520-525`): a quoted `"true"` must not silently buy
   N model passes per publish. Disabled ⇒ `_prepublish_review_passes` returns before any
   read or write — criterion (e), asserted by `test_disabled_default_is_byte_identical`
   (zero calls into the pass runner, no files) and by the update-compat suite (green).

2. **N parallel passes via the existing reviewer machinery** —
   `leaves.run_prepublish_pass` (`leaves.py:2021`) drives the **same** `[leaves.reviewer]`
   leaf (the family the instance already configures, per the brief's External-dependencies
   note) through `_sandboxed_reviewer_invoke` (`leaves.py:1788`), which I extracted from
   `_run_review_sandboxed` (`leaves.py:1845`) so the independence contract (build-notes.md
   physically absent), sandbox seeding (#161/#261) and target grounding (#75) exist
   exactly once — the brief's "reuse `leaves.run_review`'s invocation path, do not build a
   second model-runner" made literal: there is one invocation path with two prompts.
   Parallelism is a `ThreadPoolExecutor` in `_prepublish_review_passes` (`publish.py:1010`
   region); each pass is its own sandbox + subprocess, so threads only wait on children.

3. **Union + dedup** — bullets parsed from each pass artifact (`_pass_findings`,
   `publish.py:839`), keyed by `_finding_key` (`publish.py:851`).
   **Open question 1 (dedup key), my proposal: normalized text, not file+line.** Line
   numbers shift between rounds *precisely because* Do re-enters; a positional key would
   re-open every carried finding on each round and the fixpoint could never close. The
   cost of under-dedup (two passes wording one defect differently) is one extra recorded
   finding, not a wrong verdict.

4. **Classification + rubric-drop** — reuses `triage.class_keywords` / `triage.classify`
   (`triage.py:224-254`), the deterministic, rubric-tunable, severity-first classifier
   #316 already ships — one classifier and one class vocabulary in the engine, no drift.
   Where a rubric is configured (`[project].rubric_file`), NOISE-class findings — the
   class whose keyword list a rubric's exclusion lines retune, i.e. "the classes the
   instance rubric explicitly rejects" — are **dropped**; with no rubric the drop step is
   skipped exactly as the brief scopes. The rubric *key/format* itself is untouched
   (companion issue): I consume the existing `- NOISE: kw, kw` class-line grammar
   `triage.class_keywords` already parses, inventing nothing.

5. **Bounded BUG re-entry** — open BUG findings are folded into the brief's carry-forward
   block (`_carry_forward_findings`, `publish.py:862` — the same
   `## Iteration N — carry-forward` heading `driver._carry_forward_into_brief`
   (`driver.py:248-279`) writes and the builder role contract reads; numbered past any
   existing block so headings never collide), then `leaves.do_build` rebuilds. The budget
   is the `autoiterate.py:50-91` shape verbatim: a `count` key in the stage record
   (`prepublish-review.json`, `publish.py:55`), bumped per re-entry, read with
   `autoiterate.count`'s tolerance (`_prepublish_count`, `publish.py:827`), **persisted
   and never archived** (the same reason `auto-iterate.json` is excluded from
   `DOWNSTREAM_OF_BRIEF`, `state.py:74-84`: archive the budget and the bound is no
   bound). On exhaustion publish refuses loudly with nothing pushed — never open-ended,
   even across repeated `pdca publish` attempts.

6. **Triaged fixpoint** — the exit is a round whose every finding is fixed or
   recorded-rejected, judged by **re-review**: a carried BUG no pass reports against the
   rebuilt diff is marked `fixed`; one that reappears after a fix round is re-opened. A
   pass completing with only rejected/dropped/fixed findings ⇒ proceed. Non-BUG classes
   are recorded-rejected (the stage fixes bugs; it does not re-litigate style at the
   publish boundary), and a **human** can record-reject any finding — including a BUG —
   by editing its `status` in the record; a recorded status is never re-decided.
   **Open question 2 (where recorded-rejected findings land), my proposal: the
   stage-local `prepublish-review.json`.** The stage runs *after* §6 was cleared and §9
   recorded — SUMMARY is a signed artifact at that point and appending to it would mutate
   the record the sign-off blessed. The refusal message names the file, so it is what the
   human reads either way.

Fail-closed edges: **no pass at all produced a review ⇒ refuse** (publishing unreviewed
is the exact churn the stage pays down); a raising `leaves.do_build` ⇒ refuse, never a
crashed publish.

## Decisions and rejected alternatives (with costs)

- **Re-entry = the builder leaf directly, not the driver's ITERATE_DO state machine.**
  The state-machine route (write `iterate-do` → archive → PLANNED → Do → gates → review →
  AWAITING_SIGNOFF) necessarily parks the bundle for a *fresh human sign-off* — the
  driver's iterate can never re-reach COMPLETE without an accept, and auto-accept is
  forbidden by construction (`autoiterate.py:29-31` "It only ever writes iterate-do").
  Publish would then have to abort every round and the "bounded pre-publish loop" of the
  brief's Goal would become one human sign-off per finding round — exactly the serialized
  churn being eliminated, moved in-house. The brief's citations point at the *budget
  shape* (`autoiterate.py:50-91`) and the *carry-forward* (`driver._carry_forward_into_brief`),
  not at `flow._apply_decision`; I read that as licensing this design. Concrete cost of
  the alternative: it cannot satisfy criterion (d) at all ("publish proceeds only when a
  pass completes…") without either auto-accepting (forbidden) or N human round-trips.
  Trade-off honestly stated: after a fix round, patch.diff differs from the one the gates
  ran on. The stage's own re-review passes re-judge the final diff, and the #311 host-CI
  gate (`publish.py:441` onward) still runs against the *final* base+patch tree before
  the push, but the C2/C4 gate rows are not re-run in-stage — re-running Check is scoped
  out by the brief ("the pre-publish review stage in the engine: N parallel passes …
  union+dedup, rubric-rejected-class drop, bounded BUG re-entry …, and the
  triaged-fixpoint proceed condition"). This is the same trust boundary external review
  rounds cross today *post*-publish, minus the churn.
- **A separate `[leaves.prepublish]` leaf** (rejected): duplicates a leaf config for the
  same reviewer family (~40 lines of config plumbing + a second doctor row) and
  contradicts the brief's "live runs use the reviewer family the instance already
  configures".
- **Reusing the T4 gate slot for the stage** (rejected): #339 (`publish_gates`,
  `publish.py:684-720`) exists because model reviews in the T4 slot re-sample a
  nondeterministic reviewer after sign-off with no fix loop — a gate row "can only
  block, not re-enter Do", the exact wyrd-stopgap limitation the brief's Alternatives
  section names.
- **Dry-run skips the passes** (`publish.py:229` gate on `not dry_run`; plan note at
  `publish.py:311-315`): a dry run pushes nothing, and the passes are paid samples of a
  nondeterministic reviewer — re-sampling one for a run that publishes nothing is the
  #339 lesson. The stage still runs on the flow's real publish path
  (`texts_prevalidated=True` included, since the seam is below that branch).
- **pdca.toml.jinja example uses trailing comments on the numeric lines** — the
  `test_size_signal.TheShippedExampleMatchesTheDefaults` scan greedily matches every
  `# key = N` line after `[driver.size_signal]` to EOF (`test_size_signal.py:449-468`);
  bare `# passes = 3` lines false-positived it. Fixing that test's over-greedy scan is a
  separate (pre-existing) nit I deliberately did not fold into this diff.

## Verification — the three forced answers

- **(a) Genuine red? YES.** Proven through the project's own C4 runner
  (`engine/scripts/run-verify.sh`, the `C4-verify` gate row in pdca.toml): green leg —
  all 15 tests pass with the patch applied; red leg — with only the production hunks
  reverted, `FAILED (failures=7, errors=7)` incl. the brief's falsifiability driver
  `test_bug_finding_blocks_publish_before_git` (publish pushed despite the BUG-emitting
  reviewer — the exact pre-fix `_t4_passes` → git-steps gap the brief cites). Runner
  output ends `C4 PASS: red without the fix, green with it`.
- **(b) Production path? YES.** The tests call the real `publish.publish()`; the passes
  run the real `leaves.run_prepublish_pass` → `_sandboxed_reviewer_invoke` →
  `_invoke_leaf_resilient` → `progress.run_with_heartbeat` → real `sh` subprocesses in a
  real temp sandbox holding only the reviewer inputs; classification runs the real
  `triage.classify` and `rubric.load`. Mocks are confined to the boundaries this suite
  already mocks for publish (`publish.subprocess.run` for git/gh, `_check_repo` —
  identical to `test_host_ci.py:172-179`) plus `leaves.do_build`, the *model* touchpoint —
  the "stubbed review leaves" the brief's success criterion itself prescribes.
- **(c) Fixture includes the fault? YES.** The stub reviewer genuinely emits the BUG
  finding into a real pass artifact (nothing curates it out); the fixpoint test's
  patch.diff really contains `MARKER_BAD` and the pass really greps the sandbox copy of
  the diff to find it; the budget test's reviewer stays noisy while the no-op builder
  really fails to fix — every block/proceed verdict is earned by the production loop, not
  arranged.

Suites run (all through the project's runners, on this host):
- `run-verify.sh` (C4): PASS red→green as above.
- `run-suite.sh` (T3): template-repo suite `Ran 7 — OK` (render + update-compat — also
  validates the pdca.toml.jinja edit renders), offline driver suite
  `Ran 1388 — OK (skipped=2; both pre-existing)`.
- `run-docs-check.sh` (T2, advisory): `lint_docs: OK`, `render_site: link audit OK`.

## Commit-readiness

The target repo configures no Python formatter or pre-commit hooks (no
`.pre-commit-config.yaml`, no ruff/black config; CI = docs lint, render suite,
linked-issue check). Its CI equivalents were run: render suite green, docs lint green.
New code follows the module's existing style (module-prefixed private helpers,
tolerant JSON reads, stderr refusals naming the artifact).

## External dependencies

None beyond the brief's declaration — the tests stub the review leaves; no network, no
Claude, no Docker. Nothing to declare NEEDS-HUMAN.
