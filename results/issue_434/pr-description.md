## Summary

**User impact:** The check that is supposed to prove a fix works reports success even when
the fix's test never ran at all. The test can fail to build, fail to import, be filtered
out, or the runner can die before it starts anything — and the result is filed as proof
that the test catches the bug. A change nobody has actually verified then arrives at
review with a green tick on it, indistinguishable from one that really was proven. This is
not a rare accident: it happens whenever a test uses something the fix itself introduced,
and it has already bitten a real project built from this template.

This PR changes the verification instructions the harness publishes so a project decides
each run from two things — whether the runner failed **and** whether any test actually ran
— and reports "no evidence, a human should look" instead of success when nothing ran.

Reported in [#434](https://github.com/eduralph/pdca-harness/issues/434).

## What to look at

The harness never runs anyone's gate; it ships an outline plus written instructions that
each project fills in. So this is a wording change with a test holding the wording in
place — three files, no code path touched:

- `template/engine/scripts/run-verify.sh` — the header comment a project reads while
  writing its own per-fix check. This is the load-bearing file.
- `template/engine/README.md.jinja`, section "The two gate shapes that matter" — the
  longer explanation, sitting next to the sibling rule it belongs with.
- `template/tests/test_verify_red_leg.py` (new) — asserts the two documents say the rule
  and no longer say the old one.

To see the problem on `main`, read the pseudocode in the outline's header — it says
"revert the production change, run the test -> expect FAIL (red)", with the exit code as
the only input — and note that nothing under `template/engine/` mentions how many tests
ran (`grep -rn "tests ran\|executed" template/engine/` finds nothing there today). To
exercise the change, from `template/`:

```
PYTHONPATH=src python3 -m unittest tests.test_verify_red_leg
```

Standard library only; no network, no Docker.

## Root cause

The published instructions make the runner's exit code the sole input to the without-the-
fix verdict. A runner exits non-zero for two unrelated reasons — the test ran and failed
(the proof), or no test ran at all (compile/import/collect failure, or the runner dying) —
so anyone following the instructions writes a check that cannot tell proof from absence of
proof and calls both a pass. Because reverting a fix also removes any symbol the fix
introduced, the second case is an ordinary outcome, not an exotic one. Nothing in the
harness's own code is wrong here: the outline is deliberately unimplemented, so the
instructions are the only place the defect can live and the only place it can be fixed.

## Fix

- `run-verify.sh`: the pseudocode no longer treats any failure as the red; the header now
  states the rule — judge every leg by the runner's exit code **and** a count of tests
  that actually executed, parsed from the runner's own machine-readable report and never
  inferred from the exit code. All four outcomes are given as a table, so the bad row is
  data rather than a caveat: non-zero exit with zero tests run is `PDCA-UNVERIFIABLE`
  (exit 77), **never** PASS. The two "nothing ran" causes are kept distinguishable in the
  reason a gate prints, since a human reading them needs different things from each. The
  rule is stated for *every* verification step, not just this one leg.
- `README.md.jinja`: the same four outcomes plus the reasoning, naming the wrong verdict
  in plain terms ("PASS for a bundle whose test never executed").
- No new vocabulary: this reuses the existing `PDCA-UNVERIFIABLE:` / exit-77 channel that
  already routes a row to SUMMARY §6 for a human.

## Verification

- **Claim:** the published instructions decide a leg from two facts — the exit code and
  whether any test ran — and name "runner exited non-zero, no test ran" as
  `PDCA-UNVERIFIABLE` (exit 77), never PASS; the same for "exited 0, no test ran", and the
  two are told apart in the reason printed.
- **Checked:** `template/engine/scripts/run-verify.sh:42` on `main` — today's pseudocode
  reads `-> expect FAIL (red)`, the whole defect in one line; `:46-52` on `main` is the
  existing exit-77 wording this change speaks in rather than inventing a second dialect.
- **Checked:** `template/src/pdca_harness/gates.py:82-85` and `:746-773` on `main` — exit
  77 and the `PDCA-UNVERIFIABLE:` marker already turn a gate row into "unverifiable → for
  a human", so the new wording describes a consequence that exists rather than promising
  one that does not.
- **Checked:** `template/engine/README.md.jinja:26-43` on `main` — the C4 bullet already
  carries the sibling classification rule (#165); the new explanation lands directly under
  it, where a reader writing a gate is already looking.
- **Test:** `template/tests/test_verify_red_leg.py` (new, 11 tests) — fails pre-fix,
  passes post-fix, checked with the project's own red→green runner: production hunks
  reverted → `FAILED (failures=11, errors=0)`; patch applied → `OK`. `errors=0` matters:
  every red is a failing assertion, not an import error, so the red is earned by the
  wording and not by a broken test file. Reverting only `run-verify.sh` and keeping the
  README hunk still goes red (`failures=7`), confirming the shipped instructions — not the
  prose — carry the proof.
- **Suites:** the offline suite CONTRIBUTING.md names (`unittest discover -s tests` from
  `template/`) → `Ran 1537 tests … OK (skipped=2)`; the render/update-compat suite →
  `Ran 7 … OK` (it runs the *rendered* instance's copy, which is why the new test resolves
  `README.md.jinja` or `README.md`); docs lint and link audit → OK.

Fixes #434
