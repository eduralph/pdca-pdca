# Check advisory — code review (correctness + reuse/simplification), issue #64/#541

Scope: `template/src/pdca_harness/assemble.py`, `template/src/pdca_harness/leaves.py`,
`template/tests/test_attempt_harvest.py` (this patch only).

## Correctness

I traced the new `_LeafHarvest` ownership state machine (`withdraw` → `_residues` /
`_unidentified` → `run`'s `_live_attempt_took_the_path`) against every combination the
patch's own tests exercise (fresh residue, unwithdrawable residue re-seen on a later death,
unreadable residue, atomic-replace over an unreadable/unwithdrawable residue, deterministic
identical-bytes rewrite) and against the callers in `_invoke_leaf_resilient`
(`leaves.py:676-772`). The identity-then-digest fallback in
`_live_attempt_took_the_path` (`leaves.py` around `_LeafHarvest`) is sound: on the success
path, the only writer left after the last `withdraw()` call is the live attempt, so an
unrecognised filesystem identity is correctly attributable to it, and the digest fallback
only ever narrows (never widens) what counts as "unchanged." The failure path
(`err is not None`) correctly skips `_preserve()` because `_replace_record(...,
state.settled_record(...))` inside `_invoke_leaf_resilient` already wrote the full
withdrawn-residue account before returning — no double-write, no dropped account. I did not
find a bug in this state machine; the red→green C4 evidence (`gate-logs/C4-verify.log`)
also exercises exactly this logic (12 failures / 5 errors pre-fix, clean post-fix), which is
consistent with what the diff claims to fix.

- `leaves.py` — `_read_residue`'s chunked read caps each `readline()` at
  `_RESIDUE_READ` (1000) bytes to bound memory/line length, then decodes each chunk
  independently with `errors="replace"`. If a single logical line exceeds 1000 bytes and a
  multi-byte UTF-8 character straddles that boundary, the split half becomes a `U+FFFD`
  replacement character in the *quoted* head/tail text (the sha256 digest is unaffected,
  since it runs on raw bytes before decoding). Purely cosmetic — an occasional stray
  replacement glyph in a bundled `*.error.log` quote of a huge artifact — not a
  data-integrity or attribution bug, and the residue-identity/withdraw logic that actually
  gates correctness never touches this decoded text. Low priority.

## Reuse / simplification

- `leaves.py` — `_read_residue` and `_artifact_digest` each implement their own
  chunked-read sha256 loop (`digest = hashlib.sha256(); ...; digest.update(chunk)`). They
  can't fully share code because `_read_residue` also has to cap what it retains for the
  bounded head/tail quote in the same pass, while `_artifact_digest` only ever needs the
  digest (called later, after the live attempt has already run, to decide "same bytes or
  rewritten?"). A shared low-level "stream sha256 over a file in bounded chunks" helper
  would trim a few lines of duplication, but the two callers' contracts differ enough
  (bounded-quote-and-digest vs. digest-only) that inlining is a reasonable, non-hot-path
  cost. Not worth a finding on its own.

- No other duplicated logic found: both new readers of the completion trailer /
  leaf-status marker (`size_signal._review_drove_the_iterate`,
  `leaves._plan_findings`) go through the single `assemble.leaf_status` function rather
  than re-implementing marker matching, and all three harvest call sites
  (`_run_review_sandboxed`, `_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`)
  now share the one `_LeafHarvest` class instead of the three hand-copied
  `if produced.exists(): copy2(...) else: <placeholder>` blocks the patch describes
  replacing — verified the three `unavailable=` reason strings and `empty_reason`/
  `failed_reason` values against the git history's pre-patch text; they reproduce the
  original per-site prose exactly (`leaves.py:2995-3013`, `3336-3345`, `3640-3650`).

- The new `_invoke_leaf_resilient(..., harvest: _LeafHarvest | None = None, ...)` parameter
  defaults to `None` and is additive; `template/tests/test_leaf_resilience.py`'s four
  direct calls (no `harvest=` kw) are unaffected, matching the docstring's claim of being
  "byte-identical to #540" when no owner is passed.

## Tests

`test_attempt_harvest.py` genuinely drives the three production entry points
(`_run_review_sandboxed`, `_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`) through
a real subprocess stub rather than calling `_LeafHarvest` in isolation, and the C4 red leg
(reverting only the production hunks) fails with 12 failures/5 errors — real coverage of the
new code paths, not a vacuous test. No adequacy concerns from this lens (that's the
`reviewer` leaf's call in any case).

## Verdict

Nothing to route back to Do. The diff is clean on both lenses I was asked to apply
(patch-introduced correctness bugs; reuse/simplification/efficiency) beyond the one
low-priority cosmetic nit above.
