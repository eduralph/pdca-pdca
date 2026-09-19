# Check advisory — code review (correctness + reuse/simplification)

## Production change (leaves.py:3710-3711)

Clean. The new `extra_argv=_bundle_grant(with_findings, cfg, cfg.profile(cfg.planner))`
is a byte-for-byte mirror of every other bundle-scoped grant call site (`leaves.py:3752`
for sign-off, `:3902` for Act, `:3972` for publish) — same three-argument shape, same
`cfg.profile(<the leaf being spawned>)` pattern. No new helper, no duplicated logic: it
reuses `_bundle_grant`/`_grant_argv` exactly as the brief's composition cue specified.
The grant computation sits inside the existing `try/except` (the whole call is one
expression), so a `_bundle_grant` failure is contained the same way an `_invoke` failure
already was — no change to the exception's blast radius. No resource leak, no
off-by-one, no altered control flow. One line, correctly scoped.

## Test additions (test_leaf_workspace_admission.py)

- NEEDS-HUMAN [impl] — `test_leaf_workspace_admission.py:26-27`: bullet (i) of the module
  docstring still reads "each of the **six** admits the primary checkout...", but the
  paragraph just above it (lines 20-27) now says the revision pass is "a seventh
  interactive spawn... covered below by the bundle-scoped rule (i)" — i.e. rule (i) now
  governs seven spawns, not six. The brief's own scope line asked to "update the ...
  module docstring, which says 'six' interactive spawns, so it names the seventh" — the
  new paragraph does that, but the itemized criterion (i) a few lines down was missed and
  is now internally inconsistent with the paragraph above it. One-word fix.

Two of the three new tests are weaker than they look, though this isn't something the
patch invented — it inherits an existing test-helper convention rather than misusing it:

- `_admits_nothing` (`test_leaf_workspace_admission.py:169-175`) treats "extra_argv key
  never passed" (`None`) and "extra_argv passed but empty" (`[]`) as the same outcome —
  by design, per its own docstring ("Empty and absent are the same spawn... The contract
  is 'no grant', not a representation"). That means
  `test_plan_revision_admits_nothing_when_its_bundles_checkout_is_absent`
  (`:246-264`) and `test_plan_revision_generic_family_planner_spawns_with_no_admission`
  (`:266-273`) both pass identically whether or not the production fix at
  `leaves.py:3710-3711` is present, because pre-fix `extra_argv` is `None` (the kwarg was
  never passed) and post-fix it's `[]` (an empty grant) — both falsy. The C4 gate log
  confirms this directly: reverting the one production line fails exactly one of the
  three new tests (`test_plan_revision_admits_the_bundles_checkouts`), not three. This
  matches the pre-existing sibling test `test_a_bundle_scoped_session_never_widens_to_the_known_targets`
  (`:335-366`), which the brief explicitly asked the new negative test to mirror, and
  which has the identical property — so this is established convention in this file, not
  a defect this diff introduced. Flagging for visibility only, not as something this
  patch needs to fix: the gate's own bar ("the named test going red on the base") was met
  by the one test that actually flips, and that's consistent with how the file already
  verifies the six original spawns.

No other issues found — no leaks, no concurrency concerns, no missed edge case in the
call site itself, nothing duplicated that an existing helper doesn't already cover.
