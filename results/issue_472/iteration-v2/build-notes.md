# Build notes — issue_472 (flow-adopt-core), iteration 2

Target: `eduralph/pdca-harness` @ `main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt`,
HEAD `3e3b829` — the merge of PR #470/#468, so the brief's `Depends on (merged): 468` is
satisfied). Every `path:line` below is against that base **plus this patch**; the patch was
re-verified against a pristine extract of `3e3b829` (`git apply --check` clean, and applying
it reproduces the worktree byte-for-byte).

## What changed since iteration 1

Iteration 1's patch converged on every gate (C4 PASS, T2/T3/T4 pass) and the reviewer's
5/5/1 was all-PASS except the two permanently-human rows. The driver auto-iterated on the
adversary's **three implementation-level findings**. This iteration is v1 **plus** the
answers to those three, and nothing else — the adoption core (`_report_held`,
`SPLIT_DISPOSITION`, `_is_split_parent`, `_adoptable`, `_reschedule`,
`_adopt_split_children`, `_drive_wave` returning its pass count, the run-wide pool, the
splice call) is unchanged from the converged carve. Measured delta v1 → v2:

| finding | answer | size |
|---|---|---|
| `config.py:312-314` states an invariant the patch breaks | rewrote the `max_auto_iters` clamp comment (`config.py:311-327`) | +16 / −2 comment lines, **0 behaviour** |
| `test_…:821` (`…unreadable_close_marker…`) is green on the C4 red leg | rebuilt it around a second, READABLE split parent whose child must be adopted (`test_flow_adopt_split.py:863-903`) | +21 / −7 test lines |
| `flow.py:894` and `flow.py:898` (`_adoptable` guards) are unpinned | new `test_a_lineage_id_with_no_bundle_and_one_already_settled_are_both_reported` (`test_flow_adopt_split.py:666-706`) | +42 test lines |

Total delta from iteration 1: **1 production comment block, +63 / −7 lines in the test
module, nothing else** (measured: `diff -u` of v1's test file against this one is exactly the
two hunks above). Patch 87 804 → 93 215 bytes, still 7 files — both under the
`[driver.size_signal]` thresholds of 125 KB / 25 files.

### 1. `config.py:312-314` — the clamp text, not a floor

The finding: the comment promised "Clamped below `max_passes` so a wave's pass budget can't
run out mid-auto-iteration", and `flow.py:1221` hands an ADOPTED wave
`min(allowance, budget - spent)`, which can be below `max_passes`. The adversary offered two
exits — "either the clamp text must acknowledge the pool or the adopted wave's allowance
needs a floor". I took the text, and the reason is not cost, it is correctness:

* A floor lets a run spend **more passes than the operator allowed** — the one thing the pool
  exists to prevent, and the thing the brief's Success criterion states outright ("counted
  against ONE run-wide `max_passes` budget across original AND adopted waves"). Not an
  adjective: I wrote the floor and ran the module. Diff sketch (`flow.py:1220-1221`, 1 line
  wider):

  ```python
  -                             max_passes=min(allowance, budget - spent))
  +                             max_passes=min(allowance, max(budget - spent,
  +                                                           cfg.max_auto_iters + 1)))
  ```

  Result: 2 failures, both the run-wide cap —
  `test_an_adopted_wave_only_gets_what_is_left_of_the_run_budget` `AssertionError: 4 != 3`
  (a `--max-passes 3` run spends 4) and
  `test_a_wave_that_stalls_charges_the_run_pool_for_what_it_spent` `AssertionError: 5 != 4`
  (a `--max-passes 4` run spends 5). The floor buys the clamp back by breaking the criterion.
* Re-sizing the pool when the schedule grows is the honest alternative — and the brief puts
  it in the sibling child ("pool sized off the pre-adoption schedule … live re-sizing is the
  sibling child's").
* So the code is right and the sentence was stale. The new comment (`config.py:311-327`)
  says what is actually true and why, names the two lines that make it true (`flow.py:1221`
  for the share, `flow.py:1109` for the report) and the two tests that pin both halves — the
  cap (`test_the_pass_budget_is_one_cap_for_the_whole_run`) and "never silent"
  (`test_an_adopted_wave_only_gets_what_is_left_of_the_run_budget`, which already asserts
  `pass budget exhausted after 1 pass(es)` plus the `pdca flow 601` resume hint). It also
  keeps the original guarantee where it still holds: a run that adopts nothing cannot reach
  the pool (before wave *i*, `spent ≤ i·allowance` and `budget = n·allowance`), so the clamp
  is unchanged for every run that existed before this feature.

What I did **not** do: add an auto-iterate leg to the offline fixture. `cfg.auto_iterate`
is off in `_stub_config` (`test_flow_adopt_split.py:43-64`); turning it on needs the stub
reviewer to emit §6 items `autoiterate.eligible` classifies as implementation-level
(`flow.py:306-323`), which changes the pass accounting of **all 21** tests in the module,
not just the new one. The behaviour the comment now claims — "cut off, but named with its
allowance and a resume hint" — is pinned without auto-iterate by the test cited above,
because `_drive_wave`'s exhaustion exit is the same line either way (`flow.py:1109`).

### 2. `test_an_unreadable_close_marker_never_kills_the_run` — a control that makes it red

The finding was exact: every assertion the old test made (601 PLANNED, `_adoptions() == []`,
no `Traceback`, no `split adoption failed`, rc 0) is satisfied by a build with **no adoption
at all**, so it could not distinguish "the probe swallows `UnicodeDecodeError`" from "there
is no probe" — and it was one of the two survivors on the C4 red leg.

The fix is the one the adversary named: a second split parent, `700`, in the **same wave**,
whose marker is readable. Only 500's `close-disposition` is corrupted (`after_wave`, the one
window in which the marker is written but not yet re-read). Now the test asserts a
*difference* adoption makes — 500's children stay PLANNED **while 700's child `801` is
adopted into wave 1, driven to COMPLETE and announced** — so:

* it is **red pre-fix** (`801` stays PLANNED without adoption; measured — see below), and
* it still kills the narrow-handler mutation: `except Exception` → `except OSError` in
  `_is_split_parent` (`flow.py:832`) lets the `UnicodeDecodeError` out into `_isolate`, which
  prints `issue_500 — split adoption failed (UnicodeDecodeError: …)` and trips
  `assertNotIn("split adoption failed", err)` — verified, and it fails **only** this test.

`assertEqual(self._adoptions(), ["issue_700 …"])` is an exact list, so "500's children were
not announced" is still asserted, now next to the proof that announcements happen at all.

### 3. `flow.py:894` / `flow.py:898` — both `_adoptable` state guards pinned

One new test drives one hand-edited record naming three ids — `["601", "999", "900"]`:

* `999` has no bundle → `state.state` is UNPLANNED → the `flow.py:894` guard reports
  `issue_999 — child of issue_500 NOT adopted: no brief.md (brief it at Plan, then …)`.
* `900` is briefless with a `resolved` record — the tracker settled it outside a cycle
  (#302). `state.state` reports RESOLVED, which `flow._TERMINAL` (`flow.py:675`) counts as
  terminal, so the `flow.py:898` guard reports `… NOT adopted: already terminal (RESOLVED)`.
  I used #302 rather than hand-assembling a COMPLETE bundle (brief + patch + check-gates +
  a SUMMARY with an accept token, ~10 lines of fixture that duplicates `signoff`'s file
  format) because RESOLVED is reached through the production `state.is_resolved`
  (`state.py:147`) in 4 lines and is the more interesting case: adoption must not re-drive a
  bundle the tracker has closed.
* `601` is the control — still adopted, still driven, still announced, so the test also pins
  the blast radius (one unusable entry costs one child, not the sibling and not the run).

Both mutations verified killed, each by exactly this test and nothing else (below).

### T4 Contribution (`commit-msg.txt` / `pr-description.md`) — deliberately NOT supplied

The fourth §6 line the auto-iterate quoted is the reviewer's T4 row: the contribution texts
"were not supplied, so the asserted checker pass cannot be independently rerun". That is a
**cycle-order fact, not a defect in this patch**, and it is not the builder's artifact —
the target itself says so, in code, on the branch this patch targets:

* `template/src/pdca_harness/cli.py:1075-1083` (issue #401) documents exactly this
  condition — "at Check time the two artifacts it lints do not exist — publish drafts them
  later" — and `cli.py:1098` prints `gates.DEFERRED_MARKER` so the matrix records the row as
  **deferred with its reason**, "which is why every cycle escalated this by-design condition
  to SUMMARY §6 NEEDS-HUMAN". So the finding is the target's own designed behaviour, already
  shipped, and nothing this bundle can close from the Do side.
* Worth flagging for the human: this **instance's** engine predates that render —
  `DEFERRED_MARKER` does not exist in `pdca-pdca/src/pdca_harness/gates.py`, so the row here
  reported a bare `pass` rather than `deferred`, which is why the reviewer had to raise it as
  a judgment call at all. A `copier update` of this instance is what removes the noise, not a
  change to `template/`.
* The texts are drafted by the **publish** leaf on accept, and `_ensure_texts`
  (`template/src/pdca_harness/publish.py:52-62`) is **only-if-missing**. So a builder-written
  `commit-msg.txt` / `pr-description.md` would not be "an extra artifact for the reviewer to
  lint" — it would **silently become the shipped text** and skip the interactive publish
  drafting step the human owns, on a bundle whose §9 has not been recorded yet.
* `process/act-log.md` (2026-08-09) already classifies "T4 artifacts withheld" as a
  permanently-human §6 class that produced noise rounds.

So the honest disposition is: leave it open and let the human clear it at sign-off (it costs
one read), rather than fabricate release-facing text to make a row go green. Flagging it
here because build-notes is the file the human reads at sign-off.

## Carried over from iteration 1 (unchanged, and why)

* Adoption lives **once** on `_drive_and_act` (`flow.py:1115`, splice call at
  `flow.py:1226`), the shared path both CLI shapes and `flow_batch` reach since #468 — not
  in `flow_ids`/`flow()`. A second site is
  the divergence #449 spent five iterations chasing, and outside `_drive_and_act` there is
  no `wave_list` to splice into and no run-scoped budget, so children would get a *fresh*
  `max_passes` each. Recorded as a docstring at `flow.py:389-394`.
* `_children_of_split` folded into `_adoptable` (v3's wrapper existed for the recovery
  **seed**, which is the sibling child's); the `onward` chain-walk dropped (+95 test lines
  for a path reachable only through a hand-edited record in this child's scope — measured
  against v3's `test_flow_adopt_split.py:47-89`, `:335-355`, `:382-389`, `:1011-1049`).
  Boundedness is still asserted by `test_an_adopted_child_that_splits_again_is_re_adopted_
  and_bounded`.
* The announced wave index is read back from the recomputed schedule, never `k + 1`
  (saves 4 lines and is wrong the moment two children of one parent are ordered by
  `Depends on` — the default fixture case).
* Two boundaries stay documented rather than changed, both raised by the v1 adversary and
  **deferred to sign-off** (`deferred-findings.json`), so they are still open for the human:
  a bundle that declared `Depends on <parent>` is levelled by its own edges and can share a
  wave with the children the parent decomposed into (`flow.py:970-974`); and
  `pdca split --accept`'s hint still prints `pdca flow <child-ids>`, which is right outside a
  running flow and redundant inside one (`cli.py:794`).

## Verification — through the project's own runners only

| runner | result |
|---|---|
| `./engine/scripts/run-verify.sh` (C4, gating) | **`C4 PASS: red without the fix, green with it`** — green leg 21 + 19 tests OK; red leg **20 of 21 failing** |
| `./engine/scripts/run-suite.sh` (T3) | `== T3: root suite OK, driver suite OK` — root 7 OK, offline driver suite **1654 tests OK (skipped=2)** |
| `./engine/scripts/run-docs-check.sh` (T2) | `lint_docs: OK`, `render_site: link audit OK` (22 pages) |
| `./scripts/pdca contribcheck` (T4) | rc 0 |

No hand-rolled runner was used for the legs: `run-verify.sh` is the gate command `pdca.toml`
registers, and it runs `cd template && PYTHONPATH=src python3 -m unittest tests.<module>`
itself. The five mutation probes below were run with an explicit `timeout 120`, each against
the full module, with `flow.py` restored and re-diffed against `patch.diff` afterwards.

### Mutation evidence (each mutation, then the full module; restored after)

| mutation | failures |
|---|---|
| the rejected floor `max(budget - spent, cfg.max_auto_iters + 1)` (`flow.py:1221`) | `…only_gets_what_is_left_of_the_run_budget` (4 != 3), `…stalls_charges_the_run_pool…` (5 != 4) |
| `except Exception` → `except OSError` in `_is_split_parent` (`flow.py:832`) | exactly `test_an_unreadable_close_marker_never_kills_the_run` |
| delete the no-brief guard (`flow.py:894-897`) | exactly `test_a_lineage_id_with_no_bundle_and_one_already_settled_are_both_reported` |
| delete the already-terminal guard (`flow.py:898-901`) | exactly the same test |
| the brief's mandated `known=batch_names \| taken` → `known=batch_names` (`flow.py:985`) | exactly `test_two_parents_splitting_in_one_wave_adopt_a_shared_child_once` (whose name the docstring cites at `flow.py:961`) |

## The three refutation questions

**(a) Genuine red?** Yes — actually reverted and re-run through the gate, not assumed. The
C4 red leg (`git apply -R --exclude=tests/* --exclude=template/tests/*`) leaves **20 of 21**
tests failing. Iteration 1 had **18 of 20**; the two fixes above converted one survivor
(`…unreadable_close_marker…`) into a red one and added a red one. Exactly **one** test is
green on the red leg, deliberately: `test_a_run_that_adopts_nothing_keeps_a_full_budget_
per_wave` is a NO-REGRESSION test — green pre-fix is its entire point (it asserts an
un-adopting run behaves exactly as before), and it binds by mutation instead
(`budget = allowance * len(wave_list)` → `budget = allowance` fails it, verified in v1).

**(b) Production path?** Yes. Every test drives `cli._flow` (`cli.py:558`) with a real
`argparse.Namespace`, which routes through the production `flow.flow_ids` → `_drive_and_act`
— the code this patch changes. The fixture builds the split with the **production**
`split.accept` (`split.py:525`), so the close marker, `split-lineage.json` and the child
bundles are byte-for-byte what `pdca split --accept` writes; the new test's RESOLVED bundle
is classified by the production `state.is_resolved` (`state.py:147`), not asserted by
fiat. The only patched functions are **pass-through spies** (`_build_all`, `_drive_wave`,
`_point_at_integration`, `flow.flow_ids`, `integrate.fold`) that record and then call the
real one and return its exact value. Leaves are the repo's own offline stubs — the
`test_flow_slice.py:32-33` fixture shape — which is how the whole driver suite runs headless
(no display, no network, no container).

**(c) Fixture includes the fault?** Yes, and this iteration is specifically about that. The
split happens *inside the run being measured* (sign-off records `iterate-plan` → the bundle
re-opens → the next pass's Plan splits it — the documented Entry B), so the parent goes
terminal mid-run with its children PLANNED: the #449/#469 defect itself. The guard fixtures
inject the real fault rather than curating it out — a record holding `"../../etc"`, the same
id twice, an id the operator also named, an id with **no bundle**, an id the tracker
**already settled**, a child brief with an unresolvable `Depends on: GHOST`, a deleted
`split-lineage.json`, a `close-disposition` written as non-UTF-8 bytes, a Do leaf that raises
every pass, a sign-off session nobody answers. The v1 weakness was precisely a fixture in
which the fault made no observable difference; the corrupted-marker test now carries a
**readable second parent as the control**, so "nothing was adopted" can no longer pass for
"the failure was contained".

## Commit-readiness

The target configures no formatter or linter: no `.pre-commit-config.yaml`, no
`ruff.toml`/`.flake8`/`setup.cfg`/`tox.ini`, and no `[tool.*]` lint config (there is no
root `pyproject.toml` at all). Its CI is `docs-check.yml`, `docs.yml`, `render-check.yml`,
`require-linked-issue.yml` — the first and third are exactly the T2 and T3 gates run above.
CONTRIBUTING.md's only mechanical requirement is the DCO trailer (`git commit -s`), which
the publish step adds. Checked by hand anyway over the whole patch: **0 added lines wider
than 95 characters, 0 with trailing whitespace** (byte-length outliers are multi-byte `→`/`…`
in prose). No external dependency beyond python3 ≥ 3.11 stdlib + git was needed — nothing to
declare.
