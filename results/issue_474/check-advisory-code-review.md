# Check — advisory code review (issue #474)

Second lens: correctness bugs the patch introduces, and reuse/simplification/efficiency.
Grounded on `$PDCA_TARGET`'s `template/src/pdca_harness/gates.py`,
`template/tests/test_verify_base.py`, `template/pdca.toml.jinja`,
`template/engine/scripts/run-verify.sh` as patched.

## Correctness

No bugs found. Specifically checked and clean:

- `_verifies_base` (`template/src/pdca_harness/gates.py:473-495`) is a straightforward
  `chk.get("verifies_base", chk.get("tier") == "C4")` — the same "explicit key overrides a
  field-derived default, both directions" shape already used by `publish.publish_gates`'s
  `at_publish` resolution (`template/src/pdca_harness/publish.py:778`), which the docstring
  cites accurately. No off-by-one, no mutation of `chk`, no exception path.
- The gate site (`gates.py:554`, `if bundle is not None and _verifies_base(chk):`) is the
  only call site that matters — `_run_one` is reused unchanged for repo-scoped rows,
  bundle-scoped non-verifier rows, and the `host_ci_checks` loop (`gates.py:412-428`), so the
  fix closes the leak for all three without new branches per caller. Verified the `host_ci`
  loop *also* stops leaking the base to a typically non-`"C4"`-tiered row as a side effect,
  consistent with the brief's "a docs-lint row" example — not a scope violation since the
  brief only lists `host_ci` rows as "must keep doing so [resolving worktree]", not "must
  keep receiving the base".
- Backward compatibility (brief iii) is real: `chk.get("tier")` on a row with no `tier` key
  returns `None`, `None == "C4"` is `False`, so an untagged/mistagged row correctly loses the
  export, while an unmigrated `tier = "C4"` row (no `verifies_base` key at all) still gets
  `chk.get("verifies_base", True)` → `True`. Matches `test_a_predating_c4_row_keeps_its_base_with_no_config_edit`.
- Confirmed against `gate-logs/C4-verify.log`: the red leg (production reverted) fails
  exactly the three new falsifiability/invariant cases
  (`test_only_the_verifier_row_receives_the_ladder`,
  `test_the_unconditional_brief_base_rung_also_stays_off_non_verifier_rows`,
  `test_a_c4_row_can_opt_out_explicitly`) and none of the others — the two "still receives"
  cases (`test_an_explicitly_declared_non_c4_verifier_still_receives_the_base`,
  `test_a_predating_c4_row_keeps_its_base_with_no_config_edit`) correctly stay green on both
  legs, since unpatched `gates.py` already exported the base to every bundle-scoped row. The
  red leg is a genuine, targeted regression test of the introduced logic, not an
  import/collection failure dressed up as red.
- `run-verify.sh` and `pdca.toml.jinja` hunks are comments/docs only (no behavioural change),
  correctly kept in the same patch per the brief's "gate-evaluability trap" note about
  `test_verify_base.py`'s skeleton-wording string-match — `test_the_c4_skeleton_names_the_export_as_the_last_rung`
  (`template/tests/test_verify_base.py:403-…`) still passes because the ladder-resolution
  sentence at `run-verify.sh:36` (`Resolve as: $PDCA_BASE > $PDCA_VERIFY_BASE > your own
  override > $PDCA_BRIEF_BASE`) was left untouched; only surrounding prose changed.

One non-blocking observation, not a bug: `_verifies_base` has no scope guard — a row
explicitly declared `verifies_base = true` (or tagged `tier = "C4"`) while also
`scope = "repo"` would still receive the per-bundle base (`gates.py:554` only tests
`bundle is not None`, which is true for repo-scoped rows too inside `run_gates`'s
`scopes=("repo","bundle")`). This is consistent with the brief's explicit instruction to
make verifier-recognition "explicit and declared **rather than inferred from scope**", so
scope-independence looks intentional rather than an oversight, and every shipped example
places the verifier at `scope = "bundle"` by convention. Flagging only for completeness —
not escalating.

## Reuse / simplification / efficiency

- `_verifies_base` mirrors (but does not literally duplicate) the "declared key overrides a
  field-derived default" idiom `publish.publish_gates` already uses for `at_publish`. The two
  are one-liners in different modules serving different call sites (gate-env export vs.
  publish-time re-run selection); extracting a shared `_declared_or(chk, key, default)` helper
  would save one line and buy an extra layer of indirection for a two-occurrence idiom — not
  worth it here.
- No needless work added to the gate hot path: `_verifies_base` is a single dict lookup,
  called once per row per `_run_one` invocation, same order of work as the `gating`/`label`
  lookups already there.

## Verdict

Diff is clean on both lenses. No NEEDS-HUMAN items.
