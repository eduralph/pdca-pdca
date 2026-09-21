# Check advisory — code review (correctness + reuse/simplification)

- NEEDS-HUMAN [impl] — `test_sandbox_cannot_start_is_classified_infra_not_human`
  (`template/tests/test_plan_advisory.py:185`, target) fails its RED leg for the
  wrong reason. `gate-logs/C4-verify.log:48-54` shows the "production change
  reverted" run erroring with `AttributeError: module 'pdca_harness.assemble' has
  no attribute 'LEAF_STATUS_SANDBOX'` — the assertion never gets far enough to
  compare the placeholder's actual marker, because the test's own RHS
  (`assemble.LEAF_STATUS_SANDBOX`) is the symbol this patch adds. brief.md's
  Falsifiability section says exactly this shape "proves nothing" and must be
  avoided ("It must NOT fail only because it mocks or imports a symbol the fix
  adds; a red that comes from an AttributeError proves nothing... Do not patch a
  function the fix introduces"). The C4 gate still shows green-after/red-before
  mechanically, but the RED evidence for criterion (a) is not what the brief asked
  for — pre-fix, this scenario in fact misclassifies as `human-empty` (today's
  bug), and the test could show that with a literal string (`"sandbox-empty"`) or
  by asserting on the rendered marker text instead of the new constant, giving a
  real behavioral red instead of an AttributeError.

- `_plan_advisory_completed` (`template/src/pdca_harness/leaves.py:3270-3288`)
  re-implements the same glob → skip-decorrelation-note → read-text →
  `assemble.leaf_status` loop that `_plan_findings` (`leaves.py:3249-3267`) already
  has, rather than sharing one iterator/helper between them. Per bundle this is a
  third full pass over `plan-advisory-*.md` (`_plan_findings` itself is already
  called twice, at `leaves.py:3603` and `:3621`) and a second place that has to be
  kept in step if the exclusion rule (decorrelation note, placeholder detection)
  ever changes. Not a correctness bug — worth folding into one shared helper (e.g.
  a generator yielding each artifact's status) that both functions consume.

No other correctness bugs found in this diff: `_invoke`'s new `keep_final_text`/
`capture_into` params are additive and off by default (verified byte-identical
behavior for existing callers), `capture_into.append(output)` runs before the
`rc != 0` branch so a successful run's output is captured too, and it correctly
rides through `_invoke_leaf_resilient`'s `**kw` on every retry attempt.
`_final_assistant_text`/`final_text["text"]` in `progress.py` only overwrite on a
non-empty match, so a trailing tool-only `assistant` event can't clobber the real
last answer with `""`. The new `LEAF_STATUS_SANDBOX` / `_FAIL_SANDBOX` constants
are wired consistently everywhere the existing INFRA/STARTUP ones are (the
`_unavailable_classification` map, `assemble._LEAF_STATUS_LABEL`,
`assemble._items_from_artifact`'s forced-HUMAN routing for placeholders).
