# Build notes — issue 401 / deferred-gate-row-for-default-open-t4

*(Builder rationale. Withheld from the reviewer by the driver.)*

Target branch: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) off the run's integration base
`bb50e56 pdca-integrate: issue_402` (which carries the brief's declared prerequisites
402 → 428). All `path:line` below are that tree **with the patch applied**.

## What the proposal asked for, and where each design point landed

The brief is itself the design proposal; I implemented its eight points, in its order.

| # | Design point | Where |
|---|---|---|
| 1 | The checker **declares** the deferral | `template/src/pdca_harness/cli.py:1088-1094` (marker constant `gates.DEFERRED_MARKER`, `gates.py:98`) |
| 2 | `_classify` recognises it → `("deferred", [reason])` | `gates.py:706,761-768` |
| 3 | Legitimate **only** where a later gate re-runs the row | `gates._deferrable`, `gates.py:690-703`; wired at `gates.py:544-547,568` |
| 4 | `_finalize` ignores it for `overall` | already true (`fail`-only); made explicit + cited at `gates.py:786-789` |
| 5 | `assemble` does **not** lift it into §6 | already true (`unverifiable`-only); the deliberate difference is now recorded where a future reader would otherwise "fix" it — `assemble.py:361-374` |
| 6 | `render_md` shows it with its reason | already generic (`gates.py:860-884` renders `result` + `path_line`, row cell at `:880`); pinned by test, no code change — see "What I did *not* change" |
| 7 | The reviewer is told what it means | `leaves.py:1486-1491` (driver-side `_REVIEW_PROMPT`) + `template/agents/reviewer.md.jinja:68-76` |
| 8 | The written contract follows the code | `04-validation-tooling.md:67,69,71`; `06-quality-cycle-guidelines.md:230-234` (new **C5b**); `08-glossary.md:157-163`; `02-cycle-artifacts.md:108`; `template/pdca.toml.jinja:922-927`; `docs/05-check.md:393-401` |

### The declaration rule is the one 428/402 settled (design point 1)

`_declared_deferred` (`gates.py:680-687`) is `_declarations(output, DEFERRED_MARKER)` — the
same single parser both existing markers use (`gates.py:640-657`). No second notion of "the
gate said this" was introduced; the #428 start-of-line rule and the #329 non-zero-exit rule
therefore apply to `deferred` for free, and both are pinned by tests
(`test_a_relayed_marker_is_not_a_declaration`, `test_a_non_zero_exit_fails_whatever_it_declared`).

Three deliberate narrowings beyond the proposal's text, all in `_classify`
(`gates.py:761-768`):

1. **Honoured on exit 0 only**, not on `UNVERIFIABLE_RC`. 77 *is* the unverifiable channel;
   honouring `PDCA-DEFERRED:` there would let a 77 exit be recorded as a non-§6 result and
   quietly drain the #46 route.
2. **`unverifiable` wins when a gate declares both.** The two differ precisely in whether a
   human is stopped; when a gate says both, the channel that stops must win. Pinned by
   `test_unverifiable_wins_when_a_gate_declares_both`.
3. **`deferrable` defaults to `False`** on the function signature, so a caller that does not
   assert "a later gate re-runs this row" cannot get a `deferred` out of `_classify`.
   Fail-closed: the guard is opt-in, not opt-out.

### The re-gate guard (design point 3) — where it had to live

`_classify(rc, output)` sees neither the check row nor the config, so the guard is resolved in
`_run_one`, which has both (`gates.py:544-547`), and passed in as a keyword. `_deferrable`
delegates the *selection* to `publish.publish_gates(cfg)` (`publish.py:668-710`) rather than
re-deriving "bundle-scoped T4 or `at_publish = true`" — single-sourced, so a change to what
publish re-runs can never drift from what may defer. The lazy `from . import publish` matches
the existing pattern in this module (`gates.py:529`, the import-cycle avoidance for
`read_stack_base`).

Consequences, both tested: a repo-scoped T4 row and a C4 row that print the marker keep their
`pass` (`test_a_row_nothing_re_gates_keeps_its_pass`,
`test_a_c4_row_cannot_defer_itself_out_of_scrutiny`). Host-CI parity rows
(`cfg.host_ci_checks`, `gates.py:411-427`) also go through `_run_one`; they are not in
`cfg.gates_checks`, so they are not deferrable — correct, publish re-runs those on its own
separate path.

## What I did *not* change, and why

- **`_finalize` / `render_md` / `assemble._unverifiable_items` needed no behavioural edit.**
  `overall` is computed from `fail` alone (`gates.py:789-790`), the matrix renders `result` and
  `path_line` generically (`gates.py:880`), and the §6 lift filters on
  `result == "unverifiable"` (`assemble.py:376-380`). The proposal's points 4–6 are therefore
  *already-correct behaviour that had never been exercised* for a fourth value. I added
  comments/docstrings there instead of code, and **tests** that bind each one
  (`test_deferred_does_not_count_toward_overall`, `test_the_matrix_shows_deferred_with_its_reason`,
  `test_no_needs_human_item_and_accept_is_not_blocked`). Adding a `deferred` branch to any of
  the three would have been dead code that only *looks* like the feature.
- **`revalidate`** compares `result` strings generically (`revalidate.py:52-62`) and reserves
  `regression` for a gating `pass → fail` (`revalidate.py:71-73`), which is exactly the
  proposal's "a `pass → deferred` delta is a true statement, not a regression". Code change:
  none; the consequence is written into the `deferred` upgrade note
  (`04-validation-tooling.md:71`) as the proposal's *Impact & compatibility* asked.
- **`publish`** — untouched, per *out of scope*. `_t4_passes` / `publish_gates` /
  the `--no-issue` relax branch (#384's territory) are not edited; the shipped row is still
  selected to hard-gate the push, pinned by
  `test_publish_still_hard_gates_the_row_before_any_push`.
- **The exit code of `contribcheck` stays 0** on the deferral path. The deferral is declared,
  not signalled by a new exit code: a new code would have to be taught to every caller
  (`publish._t4_passes` at `publish.py:713-760`, `handoff.check_publisher`, and any instance
  wrapper), and any one that missed it would read the deferral as a *failure* and block a
  push. Declaring costs one `print`.
- **The instance's own rendered `pdca.toml`** (`/home/eddie/pdca/pdca-pdca/pdca.toml:844-857`)
  still carries the old "so Check-time gates pass" comment. That is a rendered artifact of the
  template I fixed; it updates via `copier update`, and editing it is not a target-repo change.

## Alternatives I weighed while building (beyond the proposal's own list)

- **A new `phase = "publish"` property on the row** (the proposal's rejected long-term option).
  I re-costed it rather than taking the rejection on faith: `_applies` (`gates.py:324-335`) is
  the only scheduling predicate, but the row would then be *absent* from the Check matrix, so
  `_assemble_matrix` (`gates.py:834-857`) would have to synthesise a T4 placeholder or the 5/5/1
  loses an element — plus `revalidate`'s row union (`revalidate.py:43-46`) would report the row
  as *removed* on every frozen bundle. Concretely: ~4 call sites and a matrix-alignment
  decision that this proposal does not have to make, against the 9 changed production lines
  (`_declared_deferred` 6, `_deferrable` 3 executable lines, 4 in `_classify`, 2 in `_run_one`,
  4 in `cli`) the declaration route costs. And `deferred` composes with it later: it becomes
  the state a phase-aware row reports before its phase.
- **Gating the deferral on `bundle is not None`** instead of on `publish_gates`. Cheaper (one
  `if`), and wrong for the invariant: it would let *any* bundle-scoped gate defer itself out of
  its own audit by printing one line. The invariant to restore is "a row records only a verdict
  the gate actually reached", and its safety half is "…and the verdict it owes is actually
  collected later". `publish_gates` is the only thing in the tree that knows the second half.
- **Suppressing the §6 item in `assemble` by matching on the T4 row** (no new vocabulary at
  all). It removes the recurring §6 item with a ~3-line filter — and leaves the frozen record
  still *asserting a pass*, which is the half of the defect the reviewer actually trips over.
  It would also be silent: nothing in `check-gates.json` would say why that row is special.

## Test — `template/tests/test_gate_deferred.py` (new module, 17 tests)

Named by the brief. It drives production only: the gate runner (`gates.run_gates`) over real
bundle directories with real shell gate commands, and — for the criterion itself — the real
`cli._contribcheck` as the gate's `cmd`, in a subprocess reading `$PDCA_BUNDLE` exactly as the
shipped registration does (`test_gate_deferred.py:78-85`). No Claude, no Docker, no network.

The module is deliberately **importable against an engine without `DEFERRED_MARKER`**
(`test_gate_deferred.py:49-56`): with the production hunks reverted, the red leg then fails on
the *behaviour* (`'pass' != 'deferred'`) instead of collecting an `ImportError` — a crash would
only prove the constant is absent, not that the record lies.

### The three refutation questions

**(a) Genuine red?** Yes — proven by the project's own C4 wrapper, which reverts the patch's
production hunks and keeps its tests
(`/home/eddie/pdca/pdca-pdca/engine/scripts/run-verify.sh:70-81`):

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_gate_deferred.py template/tests/test_publish_slice.py
Ran 17 tests … OK        (test_gate_deferred)
Ran 58 tests … OK        (test_publish_slice)
== C4 red leg: bundle test(s) with the production change reverted
FAIL: test_check_time_row_with_a_patch_and_no_pr_body_is_deferred  → AssertionError: 'pass' != 'deferred'
FAIL: test_declared_deferral_is_recorded_with_its_reason           → AssertionError: 'pass' != 'deferred'
FAIL: test_the_matrix_shows_deferred_with_its_reason               → '| deferred |' not found in …
FAIL: test_the_checker_declares_the_marker_at_the_start_of_a_line  → AssertionError: 0 != 1
Ran 17 tests … FAILED (failures=4)
FAIL: test_default_open_before_artifacts_are_drafted (test_publish_slice) → AssertionError: 0 != 1
C4 PASS: red without the fix, green with it
```

The red leg's first failure is the success criterion itself, end to end through the real
checker. The other 13 tests stay green in both legs on purpose — they pin behaviour the change
must **not** alter (a non-zero exit still fails, a relayed marker is still not a declaration,
an `unverifiable` row still reaches §6, drafted artifacts still record `pass`/`fail`, publish
still selects the row).

**(b) Production path?** Yes. `test_check_time_row_with_a_patch_and_no_pr_body_is_deferred`
runs `gates.run_gates` → `_run_one` → the real `cli._contribcheck` (subprocess, `$PDCA_BUNDLE`)
→ `_classify` → `_finalize` → the written `check-gates.json` / `.md`. The §6 test runs the real
`assemble.assemble_summary` and the real `cli._signoff` C6 accept-guard. Nothing is mocked,
stubbed or re-implemented; the only test-side helper is the stub `Config`, copied from the
sibling slice (`test_gates_unverifiable.py:47-59`).

**(c) Fixture includes the fault?** Yes, and it is asserted rather than assumed:
`self.assertFalse((d / "pr-description.md").exists())` — the bundle has `patch.diff` and is
*missing* the artifact whose absence is the whole condition. The negative controls carry the
same fault and differ only in what re-gates them (repo-scoped T4, C4), so the guard is measured
on the failing shape, not around it.

### Existing assertions brought into step

`template/tests/test_publish_slice.py:913-927` —
`test_default_open_before_artifacts_are_drafted` encoded "default-open ⇒ exits 0 and says
nothing". The exit code is unchanged; the silence is not, so the test now asserts the
declaration (and would have passed vacuously otherwise, since it only captured stderr).
`test_gate_logs.py`'s row-key assertion (`:120-122`) is an *additive* subset check and is
unaffected — `deferred` adds no key.

## Gates run locally (the instance's own, via its wrappers — not hand-rolled)

| Gate | Command | Result |
|---|---|---|
| C4 (gating) | `./engine/scripts/run-verify.sh` | **PASS** — red→green, above |
| T2 docs | `./engine/scripts/run-docs-check.sh` | lint OK; 22 pages rendered, link audit OK |
| T3 suites | `./engine/scripts/run-suite.sh` | root suite OK (7 tests, copier render + update-compat), driver suite OK (**1526 tests**, 2 skipped) |

Commit-readiness: the target repo configures no Python formatter/linter (no ruff/flake8/black
config; CI is `docs-check.yml` + `render-check.yml` + `require-linked-issue.yml`), and both
docs checkers pass. `CONTRIBUTING.md` requires a DCO `Signed-off-by` trailer — that belongs to
the publish commit, not to `patch.diff`.

## Risks I would put in front of the human at sign-off

1. **One class of §6 row stops reaching the human.** Deliberate, and the point of the change —
   but it is a real reduction in what §6 shows. It is bounded by `_deferrable`: only rows
   `publish` re-runs may take it, and publish's re-run still hard-gates the push.
2. **The token `deferred`** is the proposal's own open question (`pending` / `n/a-yet` were
   considered). It is one token; it appears in `gates.py:98,765`, four docs and two prompts,
   and the tests reference the constant, not the literal, wherever they can.
3. **This cycle's own T4 row will still record `pass`.** The pdca-pdca instance runs its
   *installed* engine, so the fix only shows up in this instance's own matrix after a
   `copier update`. Nothing to fix in the patch; worth knowing when reading this bundle's
   `check-gates.json`.

No external dependency beyond what the brief listed (`External dependencies: none`) was needed:
everything above ran offline with the instance venv and stdlib `unittest`.
