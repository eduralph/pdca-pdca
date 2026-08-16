# Brief — issue 476 / lineage-reader-doc-matches-the-reader

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** lineage-reader-doc-matches-the-reader
- **Defect:** `docs/07-crosscutting.md:277-282` states that the lineage reader returns `None`
  "for a `depth` that isn't a number". It does not. Verified on the target base:
  `split.read_lineage` (`template/src/pdca_harness/split.py:583-612`) returns `None` for an
  absent, unreadable, malformed, non-object or wrong-version file — and for **nothing else**:
  `{"depth": "one"}` is valid JSON of the right version, so the reader hands the record straight
  back. The unusable value is absorbed one layer down by `split._recorded_depth` (`:615-631`),
  which answers `0` for anything that is not a non-negative non-boolean `int`, so a child of
  such a parent is written at depth 1 and the parent's own record keeps `"one"` verbatim. That
  behaviour is deliberate and already pinned:
  `template/tests/test_split_lineage.py:236-251`
  (`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number` — the child's depth is 1,
  and the parent's record still reads `"one"`).
  This is not cosmetic. The documented-but-untrue clause was the source of the reviewer's C3/T2
  FAIL findings on this instance's issue_456 cycle: the reviewer held a correct implementation
  against the doc's claim and filed findings against code that was right. Every later cycle
  that reads this paragraph is exposed to the same false negative. Surfaced as a §10 Act
  candidate on issue_456 and routed upstream at the 2026-08-09 Act review
  (`process/act-log.md`).
- **Success criterion:** With the patch, `docs/07-crosscutting.md`'s lineage paragraph states
  what the code does: `split.read_lineage` abstains (`None`) on a file it cannot **parse** —
  absent, unreadable including non-UTF-8 bytes, malformed, non-object, wrong version — and a
  `depth` it cannot **compute with** is absorbed by the depth arithmetic instead (treated as
  unknown, i.e. `0`, so the child lands at depth 1), with the tolerance rationale intact. No
  sentence in the file claims a `None` the reader never returns, and no other paragraph is
  edited. The two mechanical checks the target's own CI runs on every PR stay clean on the
  patched tree: `docs/publishing/tools/lint_docs.py` (Obsidian-syntax lint) and
  `docs/publishing/tools/render_site.py --check` (site render + internal-link audit) — this
  instance runs both as the advisory `T2-docs` row **and** as the forced-gating `host-ci-docs`
  parity row, which is re-run at publish against the exact base the push builds on.
- **Falsifiability:** This is a **docs-only** slice, and that determines what can go red where —
  declared here, not left for Do to discover.
  * **C4-verify will exit 77 `PDCA-UNVERIFIABLE`, by construction and correctly.**
    `engine/scripts/run-verify.sh:130-144` classifies `docs/*` and `*.md` as non-behavioural and
    exits 77 when the patch ships no test (or has no production change to revert), routing the
    row to SUMMARY §6 NEEDS-HUMAN, non-gating — never a false red. That is the sanctioned path
    for this class (issue #165 discipline; `docs/INTEGRATION.md` §4 names an UNVERIFIABLE C4 as a
    project-defined human-only item, "docs-only … you judge them by reading"). **Do must not
    invent a production edit or a token test to manufacture a red leg.**
  * **What CAN fail, and where:** the gating `host-ci-docs` row runs the target's own two
    checkers against the reconstructed patched tree, so a patch that breaks the doc's syntax or
    an internal link fails the gate — mechanically, on the base toolchain plus the venv's
    `markdown-it-py` and `PyYAML` (both registered doctor rows, both present here).
  * **The truth of the corrected sentence is falsifiable and already falsified in the repo:**
    `template/tests/test_split_lineage.py:236-251` fails if `read_lineage` ever starts returning
    `None` for a non-numeric depth, so the doc and the suite cannot silently drift apart again.
    The human's read at sign-off is the adjudication the §6 item asks for, and this brief gives
    them the exact command and the exact lines to check.
- **Invariant to restore:** A statement in the published docs about a named function's return
  contract must be true of that function on the branch the docs ship from. Stated over the
  category rather than this sentence: the reviewer and the human are instructed to hold an
  implementation against the written ruleset (`docs/INTEGRATION.md` §4, "cite each tier's rules
  back to the project's normative ruleset"), so a false claim in the ruleset does not merely
  misinform — it converts correct code into review findings, which is exactly what it did on
  issue_456. Source: internal project invariant (Tier C) — the target's own docs discipline;
  `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6 category gate
  applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves, and a
  wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds. Ordering
  lives in the run boundaries. **This bundle owns `docs/07-crosscutting.md` for the run** — the
  merge-mode section of that same file (`:539-575`) would otherwise have been the natural home
  for issue 462's new knob, so 462's brief explicitly excludes the file and documents its knob in
  `template/pdca.toml.jinja` instead. No other bundle in the run touches `docs/`.
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** The lineage paragraph of `docs/07-crosscutting.md` (`:277-282`) — correct the
  return-contract clause so the doc describes the reader that exists, keeping the two-layer
  tolerance story (the reader abstains on what it cannot parse; the depth arithmetic absorbs a
  value it cannot compute with) and the rationale sentence that follows it. **Out of scope:**
  `split.py` — the permissive reader and `_recorded_depth` are correct and stay untouched (the
  issue routes this to the doc deliberately); every other paragraph of `07-crosscutting.md`,
  including the merge-mode section 462 was kept out of; `template/docs/`; the split lineage
  suites, which already pin the behaviour; adding a docs-versus-behaviour consistency test (the
  behaviour is pinned at `test_split_lineage.py:236-251`; a prose-matching test would be new
  machinery this slice does not need).
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness):
  1. Read `docs/07-crosscutting.md:277-282` — "…which returns `None` for an absent, unreadable,
     malformed or wrong-version file rather than raising — for *any* way of failing to read it,
     down to bytes that aren't valid UTF-8, **and for a `depth` that isn't a number**".
  2. Read `template/src/pdca_harness/split.py:583-612`: the only `return None` paths are the
     total `except` around the read/parse and the `isinstance`/`version` check. A record whose
     `depth` is `"one"` passes both.
  3. Confirm it offline, from `template/`:
     `PYTHONPATH=src python3 -m unittest tests.test_split_lineage -v` — green, and
     `test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number` asserts the parent's
     record still reads `"one"` after being read back, i.e. the reader returned it.
  4. The consequence is in this instance's `results/issue_456/` — the reviewer's C3/T2 FAIL
     findings, raised against the doc's claim.
- **External dependencies:** none beyond the base toolchain and the docs-render dependencies the
  T2 and host-CI rows already require, which are registered doctor rows in this instance and
  present on this host.
- **Test file:** none — this slice ships no test, and that is the correct shape, not an omission.
  The behaviour the corrected sentence describes is already pinned by
  `template/tests/test_split_lineage.py:236-251`, and a patch confined to `docs/*.md` is
  classified non-behavioural by `engine/scripts/run-verify.sh:130-144`, so C4-verify records
  `PDCA-UNVERIFIABLE` (→ §6, human adjudication) whether or not a test file were added. See
  Falsifiability.
- **Citations expected:** Do must cite path:line on the target branch for every change — here
  that means citing `split.py:583-612` (what the reader actually returns) and `split.py:615-631`
  (`_recorded_depth`, where a non-numeric depth is absorbed) as the source of every corrected
  claim, plus `test_split_lineage.py:236-251` as the test that pins it. Match the file's existing
  register: `07-crosscutting.md` explains mechanism in prose with inline code spans, and the
  paragraph's closing rationale ("provenance that can throw into a beat is worse than provenance
  that abstains") is the sentence the correction must remain compatible with.

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `docs/07-crosscutting.md` — `079f260` (0.57.0 walkthrough), `a2eefe1` (#459 convergence
  reporting, which added the surrounding split narrative), `20c789e`, `92a1fd5`; the clause has
  been carried forward unchanged since the lineage feature landed (`5c83070`).
  `template/src/pdca_harness/split.py` — no commit has ever made the reader return `None` for a
  non-numeric depth, so the doc describes a behaviour that never shipped.
  `gh pr list -R eduralph/pdca-harness --state open` → **no open PRs**. Closed: #486 (#459) is
  the most recent editor of this file and is merged. No open issue duplicates this. Not
  previously attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected because the corrected paragraph still does not match the reader it documents — the precise failure this bundle exists to end. Three concrete changes for the rebuild: 1. The enumeration omits the NON-OBJECT case. `read_lineage` returns `None` on three grounds (`template/src/pdca_harness/split.py:606-611`): any exception during read/parse; `not isinstance(data, dict)`; and a wrong `version`. The patched sentence lists only "absent, unreadable, malformed or wrong-version file". The brief's own success criterion names "non-object" explicitly — the patch misses its stated criterion, and the omission was inherited from the pre-patch text rather than fixed. 2. The organising idea does not cover that case either. The patch says `None` comes back "for *any* way of failing to **parse** it" — but a valid-JSON non-object such as `[1,2,3]` parses fine and is rejected on SHAPE, not on parse. Reword so the framing spans both "could not parse it" and "parsed, but is not the right shape/version", otherwise adding "non-object" to the list contradicts the sentence around it. 3. Reuse the wording that is already correct: `read_lineage`'s own docstring (`split.py:586-587`) already reads "absent, unreadable, malformed JSON, a non-object payload and an unrecognised `version` all return `None`". The correct sentence exists in the file being documented — align the prose to it rather than re-deriving it. Also fix the prose-precision nit while in there: the patch attributes both consequences to the depth arithmetic ("treats it as unknown (`0`) so the child lands at depth 1 and the parent's own record is left untouched"). The parent's record surviving is a DIFFERENT mechanism — `_merge_parent_lineage` (`split.py:643-657`) copies `depth` through verbatim and never calls `_recorded_depth`; it would survive regardless of the arithmetic. Split into two independent clauses so no causal link is implied. Given this brief exists because imprecision in this exact paragraph produced false reviewer findings on issue_456, an implied-but-untrue causal link is the same class of defect being fixed. Scope is unchanged: still docs-only, still the one lineage paragraph of `docs/07-crosscutting.md`; `split.py` stays untouched and correct. C4 remaining "unverifiable" for a docs-only patch is accepted and is not a reason for this iterate.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected because the corrected paragraph still does not match the reader it documents —
  the precise failure this bundle exists to end. Three concrete changes for the rebuild:

  1. The enumeration omits the NON-OBJECT case. `read_lineage` returns `None` on three
     grounds (`template/src/pdca_harness/split.py:606-611`): any exception during
     read/parse; `not isinstance(data, dict)`; and a wrong `version`. The patched sentence
     lists only "absent, unreadable, malformed or wrong-version file". The brief's own
     success criterion names "non-object" explicitly — the patch misses its stated
     criterion, and the omission was inherited from the pre-patch text rather than fixed.

  2. The organising idea does not cover that case either. The patch says `None` comes back
     "for *any* way of failing to **parse** it" — but a valid-JSON non-object such as
     `[1,2,3]` parses fine and is rejected on SHAPE, not on parse. Reword so the framing
     spans both "could not parse it" and "parsed, but is not the right shape/version",
     otherwise adding "non-object" to the list contradicts the sentence around it.

  3. Reuse the wording that is already correct: `read_lineage`'s own docstring
     (`split.py:586-587`) already reads "absent, unreadable, malformed JSON, a non-object
     payload and an unrecognised `version` all return `None`". The correct sentence exists
     in the file being documented — align the prose to it rather than re-deriving it.

  Also fix the prose-precision nit while in there: the patch attributes both consequences
  to the depth arithmetic ("treats it as unknown (`0`) so the child lands at depth 1 and
  the parent's own record is left untouched"). The parent's record surviving is a DIFFERENT
  mechanism — `_merge_parent_lineage` (`split.py:643-657`) copies `depth` through verbatim
  and never calls `_recorded_depth`; it would survive regardless of the arithmetic. Split
  into two independent clauses so no causal link is implied. Given this brief exists because
  imprecision in this exact paragraph produced false reviewer findings on issue_456, an
  implied-but-untrue causal link is the same class of defect being fixed.

  Scope is unchanged: still docs-only, still the one lineage paragraph of
  `docs/07-crosscutting.md`; `split.py` stays untouched and correct. C4 remaining
  "unverifiable" for a docs-only patch is accepted and is not a reason for this iterate.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
