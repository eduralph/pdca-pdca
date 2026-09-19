# Check advisory — code review (issue #526)

Read the whole diff against target source, traced the new `_BashSandboxProbe` /
`_sandbox_refusal` / `_seed_plan_sandbox_settings` machinery through `progress.py`'s
existing #506 retention plumbing and the retry loop in `_invoke_leaf_resilient`, and
cross-checked the gate logs (C4 shows all 9 new tests failing on real assertions
pre-fix, passing post-fix; T3 is 1901/1901 green).

## Findings

- No correctness bug found in the new stream-watching path. One thing worth a human's
  eye rather than a rebuild: `_seed_plan_sandbox_settings`
  (`template/src/pdca_harness/leaves.py:2699-2701`) denies only `Edit(<path>/**)`, never
  `Write(<path>/**)`, to keep the target/bundle read-only while granting the leaf `Write`
  as its no-Bash delivery route. That's deliberate and matches this repo's own established
  fact (`template/tests/test_settings_permissions.py:13-16`: Claude Code's file-permission
  checker only ever consults `Edit(path)` rules, and an `Edit` deny is documented there to
  cover `Write` too) — not a gap, just flagging the dependency so a reviewer knows where the
  safety property actually lives.
  - NEEDS-HUMAN — The stronger version of the same point: the double-slash absolute-path
    spelling `Edit(/{path}/**)` (`template/src/pdca_harness/leaves.py:2699-2701`, asserted
    verbatim in `template/tests/test_plan_advisory.py:363`) is a claim about Claude Code's
    own path-rule syntax that no test in this diff exercises against the real vendor CLI —
    the only test that touches it (`test_the_seeded_policy_keeps_the_target_and_the_bundle_read_only`)
    mocks `_invoke_leaf_resilient` out entirely and just checks the JSON the harness writes,
    never that the vendor actually honors it. Criterion (d) rests on this rule actually
    blocking `Write`, and the docstring says it was "observed" live that *without* the rule
    Write escaped to the target — but there's no equivalent observed-live confirmation in
    the diff, brief, or gate evidence that the rule *with* the leading `//` actually stops
    it. If that live confirmation happened during the build and just isn't reflected here,
    this is a non-issue; if not, it's worth one live rerun before relying on it as the
    fail-closed boundary criterion (d) requires.

- Efficiency / reuse: `_sandbox_refusal` (`template/src/pdca_harness/leaves.py:3498-3502`)
  regexes `err.output` for the CLI's "sandbox required but unavailable" text. That text
  reaches `output` through the pre-existing #506 retention path in
  `template/src/pdca_harness/progress.py:316-325` (`_terminal_error` → `terminal["text"]`
  appended to `output`) plus the stderr tail capture — the patch correctly builds a
  classifier on top of that existing evidence-retention plumbing instead of adding a new
  parallel capture path. No duplication to flag here; noting it because it's easy to
  mistake for a second capture mechanism on a first read.

- Retry-loop interaction checked and clean: `_invoke_leaf_resilient` reuses the same
  `on_event=bash` probe instance across retry attempts, but the two failure shapes this
  patch adds either never raise (rc=0, cannot-start case: `_BashSandboxProbe` only sees one
  attempt) or aren't classified as transient (`result` event counts as "produced," so
  `exc.transient` is `False` and the refusal case doesn't retry either) — so the probe is
  never fed events from more than one attempt in practice. Confirmed by the gate log:
  32 tests in well under a second, no multi-second retry backoff observed.

If nothing else turns up on a live rerun of the read-only test, this patch is clean on
both lenses: no bugs introduced, and the one duplication risk I went looking for (a second
artifact-status walk, called out in the brief's carry-forward note) was actually
consolidated into the shared `_plan_advisory_outcomes` generator
(`template/src/pdca_harness/leaves.py:3282-3295`).
