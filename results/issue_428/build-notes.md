# Build notes — issue 428 / unverifiable-marker-provenance

Target: `eduralph/pdca-harness` @ `main` (base `9fb4860`). All edits made in
`$PDCA_WORKTREE = /home/eddie/pdca/pdca-harness.pdca-wt-l1`; line numbers below are that tree
(= target branch + this patch).

## The invariant restored

> An `unverifiable` verdict is reached only when **the gate itself declares it**; output a gate
> merely *relayed* from a child process never changes the recorded verdict.

`_classify` reached `unverifiable` from a **bare substring** test over every output line
(`template/src/pdca_harness/gates.py:614-618` on `origin/main`). That is provenance-blind: any
line the gate *relayed* — a child's log, an assertion diff, a source comment a test read back —
carried the same authority as the gate's own declaration. The fix makes the *declaration* the
thing the classifier looks for, so the smallest change that restores the invariant is a change
to how a declaration is recognised, not a filter bolted on afterwards.

## The rule chosen

**A declaration is a line whose first text is the marker** (leading whitespace ignored).
Extracted as `_declared_unverifiable(output)` — `template/src/pdca_harness/gates.py:599-614` —
and called from `_classify` at `:645-648`. It returns the reason (possibly `""`) or `None`;
`None` means "the gate declared nothing", so classification falls through to the real verdict.

Why this rule and not the other two candidates the issue named:

- **Last output line only.** *Rejected on correctness, not cost.* It does not satisfy the
  brief's own repro: `echo '# see the docs: emit PDCA-UNVERIFIABLE: <reason> and exit 77';
  exit 0` has the relayed line as its last line, so the rule still records `unverifiable`.
  Concretely, `test_a_relayed_marker_on_the_only_output_line_still_passes`
  (`template/tests/test_gates_unverifiable.py:142-147`) stays **red** under it. It is also
  orthogonal to provenance — it is the *evidence-line* question, which is issue 402 and
  explicitly out of scope here.
- **Exit-77 channel only** (drop the exit-0 marker path). *Rejected — it deletes a documented,
  in-use channel the criterion requires to keep working.* Cost, counted, not adjectival:
  - `template/scripts/checks/test_exercises_production.py` is ADVISORY *by construction* and
    declares on `return 0` twice (`:76-78` unset-package, `:83-86` no-production-import) with
    the module docstring stating "it always exits 0" (`:11-13`). Under an exit-77-only rule
    both deferrals silently become **`pass`** — a fabricated green exactly where #46 exists to
    prevent one — unless that script is changed too (docstring + 2 `return` statements).
  - Its contract tests then move: `template/tests/test_prod_path_gate.py:59` and `:88` assert
    `rc == 0` on the two declaring paths (6 `assertEqual(rc, 0)` in the module, at `:50,59,67,
    72,82,88`).
  - Plus 2 gate `cmd`s in `template/tests/test_gates_unverifiable.py:28,113`, 1 in
    `template/tests/test_autoiterate.py:31`, and the 3 normative doc sentences.
    ≈ **7 files** vs the 5 this patch touches — and, unlike this patch, it is a *breaking*
    change for every existing instance: a `copier update` would convert their exit-0
    deferrals into greens, silently (the opposite direction from #329's newly-red, which the
    upgrade note warns about because it surfaces loudly).

The chosen rule is non-breaking in the dangerous direction: every emitter in the tree already
prints the marker first on the line (`test_exercises_production.py:76,85`
`print(f"{UNVERIFIABLE} …")`; `engine/scripts/run-verify.sh:32,49,52` in this instance
`echo 'PDCA-UNVERIFIABLE: …'`), so no real declaration changes verdict; only relayed text does.
Where it *does* change an instance's behaviour (a gate that prefixed its declaration, e.g.
`echo "C4: PDCA-UNVERIFIABLE: …"`), the direction is `unverifiable → pass/fail`, i.e. the gate's
real verdict — and the upgrade note says so explicitly.

## Shape mirrored from #329 (the composition cue)

Same three moves as `c6784ec`'s tightening of the same contract: narrow the rule · record why in
`_classify`'s own docstring · align the normative doc sentence.

| Change | Path:line |
|---|---|
| Narrow the rule | `template/src/pdca_harness/gates.py:599-614` (new `_declared_unverifiable`), `:645-648` (`_classify` body) |
| Why, in the docstring | `template/src/pdca_harness/gates.py:636-644` (the #428 paragraph, alongside #329's) |
| Module contract | `template/src/pdca_harness/gates.py:19-25` |
| Normative spec sentence | `template/PCDA/quality-cycle/04-validation-tooling.md:67` |
| Upgrade note (both tightenings) | `template/PCDA/quality-cycle/04-validation-tooling.md:69-81` |
| C5a rule | `template/PCDA/quality-cycle/06-quality-cycle-guidelines.md:226` |
| Glossary | `template/PCDA/quality-cycle/08-glossary.md:152-156` |
| Tests | `template/tests/test_gates_unverifiable.py:35-46` (fixtures), `:130-158` (3 cases), `:1-13` (module docstring) |

Deliberately **not** touched: `assemble._unverifiable_items` → §6 → C6 (unchanged downstream
meaning), the evidence-line rule `output.strip().splitlines()[-1:]` (issue 402), the T4 row
status (401), and the `rc != 0` half (#329 — its test
`test_the_marker_does_not_launder_a_non_zero_exit`, `:91-98`, still passes).

## Self-poisoning avoidance (the brief's caution)

The engine classifying *this* bundle's own gates is the unfixed one, so the new test must never
put the literal `PDCA-UNVERIFIABLE:` anywhere in the C4 gate's captured output. The new fixtures
compose it from the production constant instead — `_M = gates.UNVERIFIABLE_MARKER`
(`template/tests/test_gates_unverifiable.py:41-46`) — and no new docstring first line or
assert-statement source line spells it (unittest prints both on a failure, so the red leg would
otherwise leak it). Verified empirically: the full C4 run's combined output contains **0**
occurrences of the literal (`grep -c 'PDCA-UNVERIFIABLE:'` over the captured run → `0`), on both
the green and the red leg.

## Red → green, through the project's runner

Ran the configured C4 gate command itself (`pdca.toml [gates].checks` id `C4-verify` →
`./engine/scripts/run-verify.sh`), with `PDCA_BUNDLE` / `PDCA_WORKTREE` set as the driver sets
them, under a `timeout`:

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_gates_unverifiable.py
Ran 12 tests … OK
== C4 red leg: bundle test(s) with the production change reverted
FAIL: test_a_declaration_after_relayed_text_is_still_honoured
FAIL: test_a_relayed_marker_does_not_override_a_green_gate
FAIL: test_a_relayed_marker_on_the_only_output_line_still_passes
Ran 12 tests … FAILED (failures=3)
C4 PASS: red without the fix, green with it        (exit 0)
```

The red leg reverts only the production hunks (`engine/scripts/run-verify.sh:72-75` excludes
`template/tests/*`), so the red is earned by the appended cases against unpatched `gates.py`.
Also green: `./engine/scripts/run-suite.sh` (T3 — "root suite OK, driver suite OK", exit 0) and
`./engine/scripts/run-docs-check.sh` (T2 — `lint_docs: OK`, `render_site: link audit OK`, exit 0;
the PCDA spec docs I edited are inside `lint_docs.py`'s `SPEC_ROOT`, `docs/publishing/tools/
lint_docs.py:33`).

**Commit-readiness:** the target ships no formatter/pre-commit config (no `pyproject.toml`,
no `.pre-commit-config.yaml`, no non-sample hook in `.git/hooks`); its PR CI is render-check +
docs-check + require-linked-issue, and both checker workflows are green above. New lines are
≤ 96 chars, matching the module's existing width.

## Forced refutation

- **(a) Genuine red?** **Yes** — mechanically, by the C4 red leg above: with the production hunks
  reverted (`git apply -R --exclude=template/tests/*`) all three new cases fail, the first two
  with `AssertionError: 'unverifiable' != 'pass'`. That is the frozen defect
  (`results/issue_387/check-gates.json` C4 row) reproduced from a shell one-liner.
- **(b) Production path?** **Yes** — the tests call `gates.run_gates(...)` from
  `pdca_harness.gates`, the module the patch changes, over a real bundle dir; the gate `cmd` runs
  as an actual subprocess and its captured stdout goes through `_run_checks` → `_classify`
  (`template/src/pdca_harness/gates.py:527`). No copy, no mock, no monkeypatch — the fixtures even
  take the marker string from the production constant rather than restating it.
- **(c) Fixture includes the fault?** **Yes** — the failing element *is* the relayed marker line,
  and it is present in the gate's output verbatim: `_QUOTE` is the contract sentence from
  `engine/scripts/run-verify.sh:49` (the exact text that flipped the frozen C4 row), echoed by the
  gate at `template/tests/test_gates_unverifiable.py:43-45`. Nothing is curated out: one case has
  it followed by a real evidence line, one has it as the *only* line (so the fix can't be a
  last-line hack), and one pairs it with a genuine declaration to prove the narrowing doesn't
  suppress real deferrals.
