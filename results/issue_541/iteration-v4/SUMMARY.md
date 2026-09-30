# Result — issue 541 / no-dead-attempts-artifact-harvested-as-a-live-ones

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Two faces of one root — a leaf artifact is classified with no notion of *who
  produced it*.
  1. **Harvest (SOLVED — carried in as baseline, see `Baseline`).** The three harvest sites
     copy their artifact on a bare existence test — `leaves.py:2592-2596` (`check-review.md`),
     `:2926-2929` (advisory), `:3227-3230` (plan advisory) — so a truncated verdict a **dead**
     attempt left in the sandbox is adopted as the live leaf's own output.
  2. **Classification (STILL OPEN — this round's work).** `assemble.leaf_status()`
     (`assemble.py:92-96`) decides "is this a harness placeholder or a real verdict?" with
     `_LEAF_STATUS_RE.search()` — an **unanchored match anywhere in the text**. So a *real*
     report that merely **quotes** a status marker is misread as a placeholder, and all three
     of its readers act on that: `assemble.py:168` relabels every finding and forces HUMAN
     (stripping the #264 `[impl]` routing), `size_signal.py:240` counts the round as
     ambiguous, `leaves.py:3057` discards the plan-advisory's findings. Measured on the base,
     all three (see `Falsifiability`). This is a **pre-existing** defect, not one round 4
     introduced; round 4 only made it *self-triggering* by adding a fourth token that any
     advisory reviewing this very issue must quote. It is also why criterion 4 cannot be met
     by adding a token to the current mechanism — three rounds proved that.
- Success criterion: Two parts. Part A is **already built** and must survive; part B is
  this round's work.

  **A — KEEP AS BUILT (do not re-derive, do not re-open).** All three lenses confirmed these
  in round 4; the code-review lens found no correctness bug at all. Carrying the `Baseline`
  patch satisfies them by construction, so the burden here is *non-regression*. (The numbering
  1/2/3/5/6 is the v3 brief's own and is kept deliberately so the sign-off's rulings map
  one-to-one; 4 is missing here because it is part B. Not a typo.)
  1. No artifact written by a dead attempt is copied out as a successful attempt's output, at
     **all three** harvest sites.
  2. A dead attempt's text is preserved in the bundle's `*.error.log` rather than deleted.
  3. The live attempt's own artifact is harvested exactly as today, and a leaf that exits 0
     having written nothing still degrades to today's placeholder.
  5. The retry contract is NOT narrowed — `_runs() == 3` under a locked sandbox.
  6. The three harvest sites share ONE implementation. (`_LeafHarvest.run` is the only caller
     of `_invoke_leaf_resilient` in the package, so a fourth site cannot grow its own copy —
     stronger than the original criterion asked. Keep that property.)

  **B — RE-SPECIFIED (criterion 4, the leaf-status label/marker).**
  4a. **A closed artifact is never relabelled, whatever it quotes.** An artifact whose LAST
      non-blank line is the completion trailer is a real verdict at **all three readers**
      (`assemble.py:168`, `size_signal.py:240`, `leaves.py:3057`) even when its body quotes a
      recognised `pdca:leaf-status` marker anywhere — including inside a fenced block, and
      including as its own second-to-last line.
  4b. **Absence of the trailer, on its own, classifies NOTHING.** An artifact without the
      trailer behaves **byte-for-byte as it does today**. No leaf, no legacy artifact and no
      bundle in the back catalogue changes classification because it lacks the trailer.
  4c. **The label no longer lies, and the status table does NOT grow.** A run whose last
      attempt exited 0 but whose artifact path could not be attributed to it must NOT be
      labelled "leaf did not run" — that is the falsehood criterion 4 exists to remove. It
      reuses the EXISTING `human-empty` status; the specifics live in the placeholder's own
      prose, which already spells them out. **Do not add a fourth status token.** The set of
      tokens stays exactly `infra-empty` / `startup-empty` / `human-empty`, and a test pins
      that count so a fifth cannot reappear later without someone deciding to.

      *This is a deliberate softening of the v3 sign-off's wording, decided with the human at
      re-plan (option "B-simple").* The sign-off asked for a label that was neither "did not
      run" nor "merely produced no usable verdict". The second half is given up on purpose:
      buying that extra precision costs a fourth entry in the very list the redesign exists to
      stop growing, and the detail is one file-open away in the placeholder body. Removing the
      falsehood was the point; perfecting the shade of the truth was not.

      *Known and accepted consequence — do not raise it as a defect.* This makes the un-owned
      case and criterion A.3's "exited 0 having written nothing" case carry the **same**
      machine-readable token, so no automated consumer can tell them apart. That is not a
      regression: before #541 there was no un-owned classification at all, and every consumer
      that exists reads the token only to answer "is this a placeholder?", which is true of
      both. The two are distinguished where a human reads them — in the placeholder's prose.
      If a machine consumer ever genuinely needs to split them, that is the evidence for a
      fourth token, and it returns as its own issue.
  4d. **The #278 contract holds.** `tests/test_leaf_status.py:194`
      (`test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl`) and `:204`
      (`test_a_real_advisory_finding_is_untouched`) still pass unmodified — a harness
      placeholder carries no trailer, so it is still a placeholder and its `[impl]` tag is
      still refused.
  4e. **Every leaf that can be instructed is instructed.** The three harness-authored prompts
      and the three stub generators emit/require the trailer, so a *future* artifact earns 4a
      rather than only a hand-written one.
- Repo + branch target: eduralph/pdca-harness @ main
  (No `Onto branch` — deliberately. This bundle is a wave>0 dependent, so the driver exports
  `PDCA_VERIFY_BASE` from `stack-base`; setting `Onto branch` would export `PDCA_BASE` instead
  and, by the documented precedence `PDCA_BASE > PDCA_VERIFY_BASE`
  (`engine/scripts/run-verify.sh:50`), point C4 at a tree LACKING #540. Verified at Plan:
  `origin/pdca-integration/main` resolves to `480fa6b`, and the `Baseline` patch applies
  cleanly there.)
- Scope (one logical fix) / out of scope: Settle "did this leaf close this artifact?" positively and at a **fixed
  position**, so classification stops depending on what a report mentions, and convert the
  three readers through the one function they already share. Concretely — and this route is
  binding, not a suggestion:

  1. **A positive completion trailer — the exact token is `<!-- pdca:leaf-complete -->`**
     (pinned here, not left to Do: the test legs below and the prompt text must agree, and a
     floating name is one more thing to guess). Recognised **only** as the artifact's last
     non-blank line, whole-line exact match after strip. A quote inside a fenced block never
     trips it: the fence's closing line is the last line, not the trailer.
  2. **The trailer is THE test of realness; the status token only explains WHY when the
     artifact is not real.** One anchored guard at the head of `assemble.leaf_status()`
     (`assemble.py:92-96`): last non-blank line is the trailer ⇒ return `""`; otherwise fall
     through to today's `_LEAF_STATUS_RE.search()` unchanged. That is the whole reader-side
     change — and it converts all three readers together *because they all call this one
     function* (`assemble.py:168`, `size_signal.py:240`, `leaves.py:3057`). Do not add a second
     classifier anywhere; two parsers for one artifact is the bug this repo has already paid
     for twice (PR #294 review, and rounds 2–4 here).
  3. **Do NOT add a fourth status token — strip it back out of the baseline.** This is the
     point of the re-plan: the token list is what the redesign replaces, so growing it by one
     more would ship the rejected design wearing the new one's clothes. Against
     `iteration-v3/patch.diff` the delta is exactly **three deletions**:
     - `assemble.py` — drop `LEAF_STATUS_UNOWNED = "unowned-empty"`;
     - `assemble.py` — drop its entry in `_LEAF_STATUS_LABEL`;
     - `leaves.py` — drop `_FAIL_UNOWNED: assemble.LEAF_STATUS_UNOWNED,` from the status dict
       in `_unavailable_classification`. Nothing replaces it: the dict's existing default,
       `.get(failure, assemble.LEAF_STATUS_HUMAN)`, already yields `human-empty`.

     **KEEP** the other two un-owned additions — they are the half that carries the detail:
     the `_FAIL_UNOWNED = "unowned"` failure class, and its `elif failure == _FAIL_UNOWNED:`
     prose branch ("**un-owned artifact — the leaf RAN and exited 0, but nothing could be
     filed as its work.** …"). That prose *is* where the precision now lives, which is what
     makes 4c's softening acceptable. **And correct every comment the baseline wrote to
     justify the fourth token** — they become false the moment it is struck. At least two:
     the `_unavailable_classification` docstring paragraph ("The un-owned shape (#541) is its
     own marker") and the block comment the baseline added above `_LEAF_STATUS_LABEL` in
     `assemble.py`, which argues the case for the new token. Replace both with the actual
     rule: the trailer decides whether an artifact is real; the token table only explains why
     when it is not; the table is closed at three; the un-owned case shares `human-empty` and
     carries its distinction in prose. A stale comment justifying a design that was struck is
     how the next person re-adds it.
  4. **Write sites.** Append the trailer instruction to the three harness-authored prompts —
     `_REVIEW_PROMPT` (`leaves.py:1990`), `_advisory_prompt` (`:2770`), `_plan_advisory_prompt`
     (`:2975`) — one sentence each: end the artifact with this exact line, on its own, as the
     very last line. And emit it from the three stub generators — `_stub_review` (`:2703`),
     `_stub_advisory` (`:2932`), `_stub_plan_advisory` (`:3233`). The harness's own
     **placeholders** (`_review_unavailable`, `_advisory_unavailable`,
     `_plan_advisory_unavailable`) must NOT carry it — they did not close.

  **Why absence is inert (this answers the sign-off's five questions in one rule; do not
  "improve" on it):** *(1) non-cooperating leaves* — leaves are arbitrary commands and a
  third-party one cannot be compelled, so it must behave exactly as today, never "permanently
  read as failing"; *(2) false incomplete* — a model leaf that finishes and forgets the trailer
  must not read as a failure, so absence is corroborated by the harness's own signals (a
  recorded failure — which is what writes a `pdca:leaf-status` marker — or `_LeafHarvest`'s
  un-owned determination) and never trusted alone; *(3) legacy* — no artifact in any bundle
  carries the trailer, and "no trailer AND no recorded failure ⇒ legacy, stay quiet" falls out
  of the fall-through for free, so the back catalogue and the corpus/size-signal scripts are
  unaffected on the day this lands; *(4)* #278 holds because a placeholder has no trailer;
  *(5)* the three readers convert together at one seam. The trailer earns its keep as a
  **truncation** signal — a dying attempt's half-written report cannot have closed itself,
  which a harness-written "exited 0" stamp could never tell you.

  **Out of scope** — each of these was decided at sign-off; re-opening any is a defect:
  - **The metadata-only-touch hole is ACCEPTED and lived with.** `_residue_identity`
    (`leaves.py` in the baseline patch) includes `st_mtime_ns`/`st_ctime_ns`, so a live attempt
    that only `chmod`s or `utime`s an artifact moves the tuple and a dead attempt's artifact can
    still be harvested. Do **NOT** change `_residue_identity`, do **NOT** remove `st_ctime_ns`,
    do **NOT** add a digest cross-check on a moved identity. It is filed as its own issue and
    recorded in the v3 SUMMARY §10; if observed in the wild it returns as its own issue. The
    related Validation / fitness-to-purpose question (may real leaves perform metadata-only
    permission repair) is answered by that same acceptance.
  - **The harvest structure.** `_LeafHarvest.run` / `withdraw` / `_live_attempt_took_the_path` /
    `_disown` / `_preserve` / `_read_residue` / `_artifact_digest` are carried unchanged. In
    particular: do NOT make `_preserve` record whether the dead attempt's residue carried the
    trailer, however tempting — it is the same one-more-thing that grew rounds 2–4.
  - The record half (#540): the per-attempt flush, the unsettled marker, the four `*.error.log`
    readers — except where this round's own change makes one false.
  - The builder path (#537); what counts *as* a transient death (#539); a lane/worktree reset
    between attempts; any new `pdca.toml` knob; #371; #510's remedy; the nine other leaves
    still on plain `_invoke`. Do **not** create `template/tests/fixtures/`.
  - No re-split and no re-slice: the human ruled at sign-off that this stays one slice.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Review of issue #541: prevent dead-attempt artifacts from being harvested as live work and prevent completed reports that quote status markers from being misclassified as placeholders.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract makes closure positive and position-bound while leaving absence inert, so legacy and non-cooperating leaves retain their existing classification (`template/src/pdca_harness/assemble.py:101`). |
| C2 Reproduction (red pre-fix) | PASS | With the new oracle retained and production changes stashed, the independent run failed with 12 failures and 5 errors at the three-reader reproduction; restoring production passed all 23 tests (`template/tests/test_attempt_harvest.py:561`). |
| C3 Change | PASS | Attribution has one owner used by all three harvest sites, and classification changes once at the shared reader, avoiding divergent per-site decisions (`template/src/pdca_harness/leaves.py:809`, `template/src/pdca_harness/assemble.py:126`). |
| C4 Verification (red→green) | PASS | Independent red→green was reproduced locally, the patch reverse-checks cleanly, and the focused post-fix oracle passes 23/23 (`template/tests/test_attempt_harvest.py:267`). |
| C5 Causal adequacy | PASS | Failed-attempt residue is withdrawn before retry and a completed artifact is recognized by an exact final-line stamp; this removes both attribution causes without a capability probe or symptom-only fallback (`template/src/pdca_harness/leaves.py:746`, `template/src/pdca_harness/assemble.py:138`). |
| T1 Structure | PASS | The scoped production files plus one net-new regression suite form one coherent change, and all three call sites route through the sole harvest implementation (`template/src/pdca_harness/leaves.py:2945`, `template/src/pdca_harness/leaves.py:3311`, `template/src/pdca_harness/leaves.py:3616`). |
| T2 Shape | PASS | Independent diff/compile checks and docs lint/render/link audit are clean, while one loop pins all prompt, stub, and placeholder trailer shapes (`template/tests/test_attempt_harvest.py:669`). |
| T3 Runtime | PASS | The independent full offline suite passed 1,826 tests with two expected skips, including the unmodified legacy leaf-status contract and the 23 new production-path cases (`template/tests/test_attempt_harvest.py:267`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the deferred gate reports that its substantive PR-description audit reruns at publish. |
| T5 Judgment | NEEDS-HUMAN | Confirm that prerequisite #540 will be published ahead and that the affected-path prior-art search remains collision-free — this synthetic one-commit target has no remotes or rejected-work archives, so ordering and closed/in-flight overlap cannot be mechanically settled here. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether cooperative final-line closure with inert absence is operationally fit — a finished leaf that omits the trailer and quotes a recognized status remains conservatively subject to legacy misclassification (`template/src/pdca_harness/assemble.py:107`). |

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Advisory review — adversary (issue 541, round 5)

Lens: refute the red→green, find the input that breaks the fix, name the unwarranted claim.
I reproduced both legs myself in a scratch copy of `$PDCA_TARGET` (post-fix: 23 tests OK; the
same module with `assemble.py`/`leaves.py` reverted to HEAD: 12 failures + 5 errors), so the
C4 row is not taken on trust. The three part-B legs go red for the right reason
(`test_the_trailer_counts_only_as_the_artifacts_last_non_blank_line`,
`test_a_closed_artifact_is_real_at_every_reader_whatever_it_quotes`,
`test_a_closed_advisory_keeps_its_impl_routing_into_section_6`) and they drive the three
production readers, not copies.

## Findings

- NEEDS-HUMAN [impl] — **The completion instruction is not the leaf's last word at two of the
  three write sites, and the 4e leg cannot see it.** `_COMPLETION_INSTRUCTION` is appended to
  the *constant* (`leaves.py:2400`, `leaves.py:3181`), but the prompt actually handed to the
  leaf is `_REVIEW_PROMPT + rubric_mod.for_reviewer(d, cfg)` (`leaves.py:2952`) and
  `(… + instruction) + rubric` (`leaves.py:3182`). Concrete case: any project with a standing
  rubric configured (`rubric.for_reviewer` returns non-empty, `rubric.py:270-283`) — I composed
  it and the review/advisory prompts then end with the host's rubric text, with "…as the very
  last line of the file … Nothing may follow it" buried mid-prompt. The 4e leg
  (`tests/test_attempt_harvest.py:684`) asserts `assertIn(_TRAILER, prompt)` against
  `leaves._REVIEW_PROMPT` / `leaves._advisory_prompt(_SPEC, _ADVERSARY)` with **no rubric**, so
  it passes either way and would not catch the instruction being pushed further from the end.
  Cheap fix: assert on the composed prompt (pass a non-empty rubric in the leg), and/or append
  the instruction at the composition site. Only the plan-advisory site (`leaves.py:3389`) has
  it genuinely last.

- NEEDS-HUMAN — **The mechanism's load-bearing claim is false for exactly the artifact class
  this issue is about.** `assemble.py:132` (and the brief, Scope §4/§"Why absence is inert")
  states "a dying attempt's half-written report cannot have [closed itself]". It can: an
  advisory that *quotes* the trailer — which every advisory reviewing #541 must — and is cut
  off at that line ends with the trailer as its last non-blank line. I ran it: a report
  containing a `pdca:leaf-status` marker in its body and truncated immediately after a quoted
  trailer inside an unclosed fence returns `leaf_status(...) == ""`, i.e. **read as a real
  closed verdict**. I could not find a *reachable* production path for it on its own — the
  harvest withdraws such a residue, and the sandbox is a fresh `TemporaryDirectory`
  (`leaves.py:2899`) — but it composes with the explicitly-accepted metadata-only-touch hole in
  `_residue_identity`: in that scenario a dead attempt's truncated text is both filed *and*
  read as a closed verdict, i.e. one accepted hole upgrades the other. This needs no code
  change if the human accepts the claim as approximate; what I am asking for is that the
  sentence in the docstring (and the brief's rationale) not be left asserting an impossibility
  that is merely improbable, since that sentence is what a sixth round would rely on.

- NEEDS-HUMAN [impl] — **A stale-edit leftover in a comment the brief made a binding scope
  item.** Scope §3 required every comment justifying the struck fourth token to be replaced
  with the actual rule. `leaves.py:3032` reads "so neither \"leaf did not run\" would be true
  of it" — a half-deleted "neither … nor …" from the rejected design (the second arm, "nor
  'produced no usable verdict'", is what B-simple gave up). As written it is ungrammatical and
  its remaining meaning is the opposite of what the paragraph then concludes (`human-empty`
  *is* taken). One-line reword; the same paragraph is otherwise correct.

- (Not a defect, an observation on the brief.) The brief's honesty note classes "the 4e
  write-site legs" as **green pre-fix by construction**. They are not: pre-fix the symbols do
  not exist and `test_every_instructable_leaf_closes_its_artifact_and_no_placeholder_does`
  errors on `assemble.LEAF_COMPLETE_TRAILER` (`tests/test_attempt_harvest.py:677`) — visible in
  the frozen `gate-logs/C4-verify.log`. The patch is stronger than the brief credited it,
  and `check-gates.json`'s C4 wording claims nothing beyond what I verified.

## Attempted and could not refute

- **A forged "closed" artifact.** 13 probes against `assemble.leaf_status` (`assemble.py:138`):
  quoted trailer followed by a closing fence, blockquoted, inline in prose, with a trailing
  period, followed by a footer comment, CRLF, indented, trailing blank/NBSP lines, empty input.
  Every one falls through to today's behaviour; only a genuine last-line trailer returns real.
- **A new false-placeholder.** The guard is strictly a widening of "real", so 4b holds by
  construction: for any artifact whose last non-blank line is not the trailer the function is
  byte-identical to HEAD. The three hard-excluded suites are untouched (`git diff --stat HEAD
  -- template/tests/` is empty) and `test_leaf_status.py` + `test_leaf_resilience.py` +
  `test_attempt_ownership.py` pass unmodified (31 tests).
- **A fourth, unconverted reader.** Repo-wide search for `leaf_status` / `LEAF_STATUS` /
  `pdca:leaf-status` finds exactly the three readers the brief names (`assemble.py:216`,
  `size_signal.py:240`, `leaves.py:3452`) and no shell/script/doc reader; no second classifier
  (`NOT COMPLETED` appears only at the three write sites).
- **A fourth harvest site / a narrowed retry contract.** `_LeafHarvest.run` (`leaves.py:868`) is
  the only caller of `_invoke_leaf_resilient` in `src/`; the surviving direct callers are tests.
- **Two harvest scenarios the suite does not cover**, driven through the real entry points:
  two consecutive deaths then a live write (filed, `_runs == 3`, no error log), and a dead
  attempt leaving a *complete, closed* artifact (refused, preserved unsettled in the error log,
  placeholder `human-empty`) — both behave as the design says.
- **Import-time breakage on the supported floor (≥3.11).** The forward reference
  `harvest: _LeafHarvest | None` at `leaves.py:684` precedes the class, but
  `from __future__ import annotations` is present (`leaves.py:35`), so this is not a
  3.14-only pass.
- **Un-owned prose that lies.** `_FAIL_UNOWNED` can only be reached after a withdrawal, so the
  account the prose points at (`leaves.py:3062`) always exists except on a best-effort write
  failure; and `review_never_ran` (`leaves.py:2538`) is not tripped by the preserved unsettled
  log, because the placeholder artifact exists.

<!-- pdca:leaf-complete -->

### Advisory — code-review

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

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] T5 Judgment — Confirm that prerequisite #540 will be published ahead and that the affected-path prior-art search remains collision-free — this synthetic one-commit target has no remotes or rejected-work archives, so ordering and closed/in-flight overlap cannot be mechanically settled here.
- [ ] Validation — fitness-to-purpose — Decide whether cooperative final-line closure with inert absence is operationally fit — a finished leaf that omits the trailer and quotes a recognized status remains conservatively subject to legacy misclassification (`template/src/pdca_harness/assemble.py:107`).
- [ ] **The completion instruction is not the leaf's last word at two of the
- [ ] **The mechanism's load-bearing claim is false for exactly the artifact class
- [ ] **A stale-edit leftover in a comment the brief made a binding scope
- [ ] size backstop — this slice is behaving oversized: patch is 84 KB (threshold 80 KB). Recommend answering `iterate-plan` at sign-off and authoring the split in the re-plan (`pdca split`), rather than `iterate-do`: a slice that is too big yields implementation-shaped findings every round, and splitting authors briefs, which is Plan's beat.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the adversary's three implementation findings only; the design (B-simple, completion trailer, closed three-token table) is confirmed and must NOT be re-opened. Part A and the reader-side guard in assemble.leaf_status() stay as built. Fix exactly these three, nothing more: 1. Composition order: at the review and advisory sites the prompt handed to the leaf is `<constant incl. _COMPLETION_INSTRUCTION> + rubric`, so with a project rubric configured the "end with this exact line ... Nothing may follow it" instruction is not the prompt's last word (leaves.py _REVIEW_PROMPT + rubric_mod.for_reviewer(...) at _run_review_sandboxed; `(... + instruction) + rubric` in _advisory_prompt). Append the instruction AFTER the rubric at the composition site for both, matching what the plan-advisory site already does. Extend the 4e leg to assert on the COMPOSED prompt with a non-empty rubric, so the trailer instruction is the final sentence — the current leg tests the constant with no rubric and passes either way. 2. Stale comment: the _unavailable_classification docstring paragraph reads "so neither \"leaf did not run\" would be true of it" — a half-deleted "neither ... nor" from the struck fourth-token design. Reword to say plainly: it exited 0, so "leaf did not run" would be false; it takes the default `human-empty`. Scope item 3 made correcting these comments binding. 3. Overstated claim: leaf_status()'s docstring and the test module docstring assert a dying attempt's half-written report "cannot have closed itself". Soften to "is very unlikely to have" / "would need to be cut off exactly on a quoted trailer line" — the adversary showed the exact case, reachable only through the already-accepted metadata-only-touch hole. Wording only; no code change and do NOT touch _residue_identity or _LeafHarvest. Size backstop (84 KB > 80 KB) is byte-count only: sizing.json band ok, one outcome, and the v3 ruling "one slice, do not split" stands. Not grounds for iterate-plan.
- By / date: Eduard Ralph / 2026-09-28

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
