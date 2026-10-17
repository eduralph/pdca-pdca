# Advisory code review — issue_724 (dependency-scoped bundle bases, #463)

Lenses: correctness bugs the patch introduces, and reuse / simplification / efficiency.
Grounded on the patched tree at `$PDCA_TARGET`. Gates: C4 (red pre-fix, green post-fix), T3
(2573 tests OK, 2 skipped) and host-ci-docs all pass in `gate-logs/`.

Overall: I found no correctness bug that needs the builder to iterate. All five
round-1 findings are fixed in this diff:
- the closure now follows edges from carried bundles (`_closure` `flow.py:845`, `_ordered_after` `:885`, `_cut_above` `:924`);
- `Conflicts with` is read over drive-set plus carried bundles (`flow.py:985`);
- a base build now records the head it took (`merged_heads`, `integrate.py:867-868`, folded
  into `carried_heads` at `flow.py:1017`), and carried ids get the end-of-run check
  (`flow.py:2829-2831`);
- a `Conflicts with` partner that never completed is no longer walked through (`_closure`, `flow.py:845-883`,
  test at `test_flow_dependency_scoped_bases.py:356`);
- the old line-push race in `test_integrate_carried_rewrite_late.py` is kept as its own case
  (1d) instead of being replaced.

Minor notes (advisory, no action required):

- `template/src/pdca_harness/flow.py:981` — the `_bundle_bases` docstring says that on a failure
  "the caller stops the run before the wave builds and records nothing". That holds for the
  stack-base records. But if bundle 2 of a wave fails, bundle 1's base is already pushed to
  origin, and `carried_heads` was already updated at `:1017`. Today nothing goes wrong:
  `line_stopped` skips the end-of-run check (`:2829-2831`), and cleaning up per-bundle bases is out
  of scope per the brief. The wording could say "records no stack base" so a later reader
  doesn't rely on `carried_heads` being untouched.
- `template/src/pdca_harness/flow.py:837` — `_point_at_integration` now takes keys that are
  either a bundle name or a `(repo, base)` tuple. The flow only ever passes name keys
  (`:2691`). The tuple path is kept only for the older direct callers in
  `test_integrate.py:351,362` and `test_integrate_stack_bases.py:1100`. That's fine as a way
  to keep old callers working; a name-only signature would be simpler, but changing it would
  mean editing tests that criterion (10) says to leave alone, so leaving it is reasonable.
- `template/src/pdca_harness/flow.py:950-951` — `_cut_above` returns False on any git error. This
  fails closed on purpose and is documented: a base missing the partner's work is then refused
  by `build_bundle_base`, which names the partner, and the run stops. The cost is that a
  transient git failure here shows up as a foreign-work stop, not as the real git error. This
  is acceptable until #725 turns those stops into holds.
- Efficiency: each runnable bundle with members now gets its own fetch, merge and push under
  the integration lock (`flow.py:1009-1017` → `integrate.py:811-868`), on top of the line fold.
  The brief asks for this design. Any of those network steps failing now stops the run before
  the wave (`flow.py:2683-2687`), which the brief also accepts until #725.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->
