# Advisory review — adversary (issue #541, round 4)

Re-ran the asserted red→green on the target: green leg reproduces (17/17 OK, no skips,
`PYTHONPATH=src python -m unittest tests.test_attempt_harvest`), and the red-leg log
(`gate-logs/C4-verify.log`) shows 8 distinct tests genuinely red on the base — the C4 claim
itself is honest, and the tests drive the real site entry points (`_run_review_sandboxed`,
`_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`), not a re-implementation. Two
refutations landed anyway.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:962-964`: a dead attempt's
  residue is still filed as the live attempt's verdict when the live attempt only touched
  the file's METADATA. `_live_attempt_took_the_path` returns `True` the moment
  `_residue_identity` moves (`known is None → return True`), and that tuple includes
  `st_mtime_ns`/`st_ctime_ns` — both of which move with no byte changed. Measured, twice,
  through the production entry point (dying attempt writes a truncated verdict then
  `chmod(".", 0o500)` so the withdrawal is refused; the live attempt exits 0 having only run
  `os.utime(art, None)` — and, separately, only `os.chmod(art, 0o600)`): `check-review.md`
  in the bundle is byte-for-byte the dead attempt's text, with no `NOT COMPLETED`
  placeholder and no un-owned refusal. That is criterion 1 failing in exactly the lane the
  refusal exists for, and it contradicts the invariant the code claims for itself at
  `leaves.py:950` ("Only 'the same file, unchanged' is refused") — here the file IS
  unchanged and it is filed. Any leaf or wrapper that normalises timestamps/permissions on
  its outputs (a formatter, `chmod -R`, a `touch`, a copy tool) triggers it. Cheap fix
  inside the existing design: `_residues` already carries the digest, so when the identity
  has moved, cross-check the current `_artifact_digest` against the recorded digests and
  treat a byte-identical match as still-un-owned. (`st_ctime_ns` in the identity tuple is
  net-harmful: it is the only member a pure `chmod` moves.)

- NEEDS-HUMAN — `template/src/pdca_harness/assemble.py:88,95-97`: adding `unowned-empty` to
  `_LEAF_STATUS_LABEL` re-opens, for a RECOGNISED token, the exact demotion the round-2/3
  carry-forwards rejected for unrecognised ones — and it is self-triggering on this very
  bundle. `leaf_status` matches the marker anywhere in the text, so a REAL advisory/review
  artifact that quotes the new placeholder verbatim (any leaf reviewing #541 — this report
  had to mangle the marker to avoid it) has every finding relabelled and forced HUMAN at
  `assemble.py:188-193`. Measured against base with `collect_needs_human` on an artifact
  holding a fenced quote of the marker plus one genuine `[impl]`-marked finding
  ("off-by-one at foo.py:12"): base → `impl`, `autoiterate.eligible` True; patched → `human`, prefixed "leaf
  ran and exited 0, but no artifact could be attributed to it", `eligible` False. So the
  #264 `[impl]` routing is stripped from findings that exist, and the §6 row states
  something false about a leaf that ran fine — a regression against the base caused by this
  diff. The patch's guard (`tests/test_attempt_harvest.py:449`, token `some-future-status`)
  misses it by construction and is green pre-fix, so C4 covers none of it. Flagged for a
  human rather than `[impl]` because the remedy the round-3 carry-forward prescribed ("keep
  '' for an artifact that carries a verdict table / findings") collides with the shipped
  #278 guard `tests/test_leaf_status.py:194`
  (`test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl`), so the choice —
  scope the match to the artifact's own header, drop the new token's label, or accept the
  demotion — is a design call, not an iteration.

- Evidence caveat (no adjudication needed, context for the two above):
  `tests/test_attempt_harvest.py:304,324,340` — the three "a live verdict written over an
  un-withdrawable residue is still filed" legs, i.e. the round-2/3 carry-forward's core
  remedy — are green **pre-fix** as well as post-fix (the base files everything, so no
  over-refusal exists there to go red). That is unavoidable for a guard against a rejected
  patch, but it means the whole identity mechanism (`_residue_identity`, the digest
  fallback) carries no red→green proof, which is how the metadata-touch hole above survived
  into round 4. The `check-gates.json` C4 row ("red without the fix, green with it") is
  true, and is weaker than it reads for the parts of the patch added in this round.

Attempted and could not refute: the retry contract (criterion 5) really is untouched —
`withdraw` never breaks the loop and `_runs() == 3` holds under a locked sandbox; the
residue-de-dup (`_unchanged`, `leaves.py:905-907`) does account for an un-removable residue
exactly once across three deaths; criterion 6 is stronger than claimed — `_LeafHarvest.run`
is now the ONLY caller of `_invoke_leaf_resilient` in the package, so a fourth site cannot
grow its own copy; the preserved account cannot settle a leaf that exited 0
(`_WITHDRAWN_TRAILER` carries no marker, and the residue goes through
`state.neutralize_leaf_text`); no sandbox seeds a file at any site's artifact name
(`REVIEWER_INPUTS`, `PLAN_ADVISORY_INPUTS`, `<sandbox>/target`), so nothing but the leaf can
leave a residue; the forward reference `harvest: _LeafHarvest | None` at `leaves.py:684`
is safe on CI's Python 3.12 (`from __future__ import annotations` at `leaves.py:35`), not
merely on the 3.14 the gates ran; and the residue quote really is bounded head/tail with an
elision line, leaving no `.partial` sibling.
