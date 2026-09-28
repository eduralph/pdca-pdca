# Brief — issue 541 / no-dead-attempts-artifact-harvested-as-a-live-ones

> **RE-PLAN after four rounds.** The v3 sign-off (`iteration-v3/SUMMARY.md` §9) ruled
> `iterate-plan`, kept criteria 1/2/3/5/6 as built, and re-specified criterion 4 with the
> design already chosen. This brief transcribes that ruling and — deliberately, on the
> human's instruction — **specifies the route, not only the destination**. Three rounds
> were each given the destination and left to guess the route; each closed the previous
> hole and opened a new one in the same mechanism. Naming the mechanism here is the
> considered exception to `docs/principles.md` §3.1, taken by the human at sign-off, not
> an oversight.
>
> **The redesign is a REPLACEMENT, not an addition** (confirmed with the human at re-plan,
> option "B-simple"). The leaf-written completion trailer becomes *the* test of whether an
> artifact is real; the `pdca:leaf-status` token table only explains WHY when it is not, and
> **that table does not grow**. An earlier draft of this brief kept the round-4 fourth token
> alongside the trailer — that was the rejected design in new clothes, and it is struck. The
> price, accepted knowingly, is in criterion 4c.

- **Slug:** no-dead-attempts-artifact-harvested-as-a-live-ones
- **Defect:** Two faces of one root — a leaf artifact is classified with no notion of *who
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
- **Success criterion:** Two parts. Part A is **already built** and must survive; part B is
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
- **Falsifiability:** RED is available and I **measured it on the base**
  (`pdca-integration/main`, `480fa6b`), offline, from `template/` with `PYTHONPATH=src`. The
  probe artifact — **the same one in both columns** — is a real report with a fenced quote of
  `<!-- pdca:leaf-status infra-empty -->` in its body **and the completion trailer as its last
  non-blank line**. That the trailer is present in the RED leg too is the point: the base
  ignores it, the fix honours it, so the artifact's classification flips while the artifact
  itself is constant.

  | Reader | Base (RED) | Required post-fix (GREEN) |
  |---|---|---|
  | `assemble._items_from_artifact` | `kind=human`, text prefixed "leaf did not run (transient infra — safe to re-run)" | `kind=impl`, text unprefixed |
  | `size_signal._review_drove_the_iterate` (clean all-PASS review, no NEEDS-HUMAN, no FAIL cell) | `True` | `False` |
  | `leaves._plan_findings` (one `- NEEDS-HUMAN` bullet) | `0` | `1` |

  **The quoted token MUST be one the base already recognises — use `infra-empty`.** Quote any
  token the base does not know and every leg goes **green pre-fix**: `_LEAF_STATUS_LABEL.get()`
  returns `""` for an unrecognised token, so nothing is relabelled and there is no red to
  measure. That vacuity is exactly what the v3 adversary named (`test_attempt_harvest.py:449`,
  token `some-future-status`, green pre-fix and therefore proving nothing) and is how the
  round-4 hole survived to a fourth round. Do not repeat it. Note this is now the *only*
  reason the legs work: under B-simple no new token exists, so the red can only come from a
  token that is already in the table. The part-A legs are red because the `Baseline` production hunks are part of
  this patch and the C4 red leg reverts them.

  **Which legs are red→green and which are non-regression guards — state this honestly in
  `build-notes.md` rather than letting the adversary discover it.** The three rows above, plus
  the part-A legs, are genuine red→green. The 4b legs (an artifact *without* the trailer
  classifies identically pre- and post-fix), 4d (`test_leaf_status.py` unmodified) and the 4e
  write-site legs are **green pre-fix by construction** — they guard against a regression this
  patch could introduce, which is a legitimate thing to ship but is *not* evidence the defect
  existed. Do not dress them as red→green, and do not pad the count.
- **Invariant to restore:** *A pipeline never turns "no evidence" into a verdict — and never
  turns a verdict into "no evidence".* The classification of a leaf artifact must be settled
  by **who produced it and whether they closed it**, never by what its text happens to
  mention. Source: `engine/README.md:68` — "A gate never turns 'no evidence' into a verdict"
  (internal project invariant, `docs/principles.md` §5 Tier C; authoritative for this repo,
  it is the engine's own written rule). Round 4 violated the second half: it destroyed real
  `[impl]` findings — evidence that existed — by reading a *mention* as a verdict about the
  artifact.
- **Repo + branch target:** eduralph/pdca-harness @ main
  (No `Onto branch` — deliberately. This bundle is a wave>0 dependent, so the driver exports
  `PDCA_VERIFY_BASE` from `stack-base`; setting `Onto branch` would export `PDCA_BASE` instead
  and, by the documented precedence `PDCA_BASE > PDCA_VERIFY_BASE`
  (`engine/scripts/run-verify.sh:50`), point C4 at a tree LACKING #540. Verified at Plan:
  `origin/pdca-integration/main` resolves to `480fa6b`, and the `Baseline` patch applies
  cleanly there.)
- **Depends on:** 540
- **Ordering note:** child-1 of the #536 split is **#540**
  (`per-attempt-record-and-one-error-log-meaning`) — the v3 brief said "child-1" and never
  resolved the id; resolved here. #540's accepted result is already folded into this bundle's
  base: `stack-base` reads `pdca-integration/main`, whose tip `480fa6b` is
  `pdca-integrate: issue_540`. The v3 T5 NEEDS-HUMAN on #540 sequencing was adjudicated at
  sign-off as a **publish-time** concern, not a patch defect. Siblings #537 (builder path) and
  #539 (what counts as a transient death) are out of scope, not ordering constraints —
  neither touches the files this brief does.
- **Difficulty:** high
- **Baseline:** **Start from `iteration-v3/patch.diff` in this bundle — apply it, then make
  the part-B delta.** The delta both ADDS and REMOVES: scope item 3 strips three lines back
  out of the baseline, so this is not a purely additive layer — read item 3 before you start.
  This is a Plan-authored, bounded exception to
  "read `brief.md` only" (same class as the `Citations expected` peer-callsite exception):
  you MAY read that one file. Verified at Plan: it applies **cleanly** to
  `pdca-integration/main` (`git apply --check`), 914 insertions / 30 deletions across
  `template/src/pdca_harness/assemble.py`, `template/src/pdca_harness/leaves.py`,
  `template/tests/test_attempt_harvest.py`. Rationale: the sign-off ruled criteria 1/2/3/5/6
  "keep as built"; the base does not contain them, and re-deriving 900 lines of
  three-rounds-hard-won code is how a fifth round starts. Ship ONE `patch.diff` containing
  baseline + delta — not two patches.
- **Scope:** Settle "did this leaf close this artifact?" positively and at a **fixed
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
- **Repro instruction:** From `template/` on a clean checkout of `pdca-integration/main`,
  offline, `PYTHONPATH=src python3 -m unittest tests.test_attempt_harvest`. For the part-B
  legs, build the probe artifact in-test (a real report whose body contains a fenced quote of
  `<!-- pdca:leaf-status infra-empty -->`, with and without the trailer as its last line) and
  drive the three readers directly: `assemble._items_from_artifact`,
  `size_signal._review_drove_the_iterate`, `leaves._plan_findings`. For the part-A legs, keep
  the baseline's stub-leaf harness (a Python interpreter as the "leaf", the `$CNT` counter,
  `[sys.executable, "-c", script]`) driving the three real entry points
  `_run_review_sandboxed` / `_run_advisory_sandboxed` / `_run_plan_advisory_sandboxed`.
  For **4e**, assert the write sites directly rather than by eye: each of the three prompt
  strings (`_REVIEW_PROMPT`, and the return of `_advisory_prompt(...)` /
  `_plan_advisory_prompt(...)`) contains the trailer token, and each of the three stub
  generators produces an artifact whose last non-blank line IS the trailer — while each of the
  three `_*_unavailable` placeholders produces one whose last line is NOT. Loop over the three
  sites in one test rather than writing three copies: a leg that lands at two of three leaves
  the third wrong, which is the "twin blindness" face this whole slice exists to remove.
  For **4c**, two legs. (i) The carried baseline leg
  `test_the_label_never_says_a_run_that_exited_0_did_not_run` keeps covering the falsehood,
  but **it needs one amendment, identified at Plan — do not just run it and be surprised.**
  It currently asserts `assertIn("exited 0", item.text)` against the §6 *item*. Under B-simple
  the §6 line is `human-empty`'s — "leaf produced no usable verdict (needs a human)" — which
  does not contain "exited 0", so that assertion fails. Move it: assert `"exited 0"` against
  the **artifact text** (the placeholder body, where the kept `_FAIL_UNOWNED` prose branch
  writes "the leaf RAN and exited 0"), and leave the §6 assertions as they are. Verified at
  Plan that the other two assertions still hold — `human-empty`'s label does not start with
  "leaf did not run", and still contains "leaf" so the row is still selected. That amendment
  *is* B-simple's bargain made mechanical: bluntness in §6, precision in the file.
  (ii) A **non-growth leg**: assert the recognised status set is
  exactly `{infra-empty, startup-empty, human-empty}` — read it off
  `assemble._LEAF_STATUS_LABEL` and off the `LEAF_STATUS_*` module attributes, and assert both
  agree and both have three members. This is the mechanical expression of the redesign: it is
  what stops a fifth token being added later by someone who never read this brief. It is green
  pre-fix (see the honesty note above) — ship it as the guard it is, not as evidence.
  **C4 red-leg import trap:** the red leg reverts the production hunks, which deletes every
  symbol this patch adds — so reference the trailer constant, `_FAIL_UNOWNED` and
  `_LeafHarvest` only **inside test bodies**, never at module level. A module-level reference
  makes the red leg a load failure, recorded `PDCA-UNVERIFIABLE`, not red
  (`engine/scripts/run-verify.sh:231-234`). Import only `from pdca_harness import assemble,
  leaves, size_signal` at module scope. **No skip guard on the part-B legs:** the baseline
  ships 8 `@unittest.skipUnless(_rootless())` legs (correctly — they need an unwritable
  directory), but the part-B legs are pure text classification and MUST run unconditionally,
  so the red leg still fails if the gate ever runs as root.
- **External dependencies:** none — the base toolchain (pure-stdlib Python ≥ 3.11 + git)
  suffices; every leg is offline and every "leaf" is a Python interpreter.
- **Test file:** `template/tests/test_attempt_harvest.py` — the same file the `Baseline` patch
  adds, extended with the part-B legs. It stays a **net-new** file relative to the base, which
  is what the C5-prod-path advisory keys on; the C4 gate (`engine/scripts/run-verify.sh`)
  reverts production hunks and keeps tests, so appending to it earns a genuine red. Verified at
  Plan: C4 runs every `template/tests/*.py` the patch touches, from `template/` with
  `PYTHONPATH=src` — the named module executes under the gate's own invocation, with no `cfg` /
  feature / env flag that could compile it away. **Hard-excluded, no exceptions:**
  `test_leaf_resilience.py`, `test_attempt_ownership.py`, `test_leaf_status.py` — 4d requires
  the last of these to pass **unmodified**, which is the proof the #278 contract survives. Any
  *other* shipped suite may be updated only where the stub trailer (scope item 4) makes an
  existing expectation literally false; list every such edit in `build-notes.md` with the
  assertion it broke.
- **Citations expected:** Do must cite path:line on the target branch for every change. Two
  files may be opened beyond this brief: `iteration-v3/patch.diff` (the `Baseline`), and the
  peer callsite for the marker-write pattern — `_unavailable_classification`,
  `leaves.py:2646-2683`, the single site that writes a `pdca:leaf-status` marker today. Mirror
  its shape when adding the un-owned status; the trailer is its inverse and belongs at the
  *end* of the artifact, written by the leaf, not at the top written by the harness.
- **Prior-art check (triage cycles):** Searched by affected file path against
  `pdca-integration/main` and `origin/main` — `git -C ../pdca-harness log --oneline -- <path>`
  for `template/src/pdca_harness/assemble.py`, `template/src/pdca_harness/leaves.py`,
  `template/src/pdca_harness/size_signal.py`. No merged or in-flight change touches the
  `leaf_status` classifier. Pickaxed to be sure —
  `git log origin/main -G"leaf_status|LEAF_STATUS" -- template/src/pdca_harness/assemble.py`
  returns exactly two commits, both #278's: `af7375d` (introduced the marker) and `4e250a1`
  (#278 review, added `startup-empty`). Nothing since, and nothing in flight — no open PR or
  branch touches it. The nearest neighbours are #540
  (`fix/540-per-attempt-record-and-one-error-log-meaning`, already in this base) and #538
  (`fix/538-a-leafs-own-account-of-its-death-is-kept`), neither of which touches `leaf_status`. Closed/rejected work: the four attempts archived in this bundle's
  `iteration-v1..v3` — rejected approaches, **do not re-attempt any of them**: (v2) match the
  marker anywhere and label unknown tokens — holed by a quoted marker; (v3) an 8-line header
  window `_LEAF_STATUS_HEADER_LINES` — holed by a fenced block opening at line 5; (v4) make
  `unowned-empty` a recognised token — self-triggers on any artifact quoting it. Each closed
  the previous hole and opened a new one in the same mechanism, which is why this brief
  replaces the mechanism rather than tightening it.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 4 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the adversary's three implementation findings only; the design (B-simple, completion trailer, closed three-token table) is confirmed and must NOT be re-opened. Part A and the reader-side guard in assemble.leaf_status() stay as built. Fix exactly these three, nothing more: 1. Composition order: at the review and advisory sites the prompt handed to the leaf is `<constant incl. _COMPLETION_INSTRUCTION> + rubric`, so with a project rubric configured the "end with this exact line ... Nothing may follow it" instruction is not the prompt's last word (leaves.py _REVIEW_PROMPT + rubric_mod.for_reviewer(...) at _run_review_sandboxed; `(... + instruction) + rubric` in _advisory_prompt). Append the instruction AFTER the rubric at the composition site for both, matching what the plan-advisory site already does. Extend the 4e leg to assert on the COMPOSED prompt with a non-empty rubric, so the trailer instruction is the final sentence — the current leg tests the constant with no rubric and passes either way. 2. Stale comment: the _unavailable_classification docstring paragraph reads "so neither \"leaf did not run\" would be true of it" — a half-deleted "neither ... nor" from the struck fourth-token design. Reword to say plainly: it exited 0, so "leaf did not run" would be false; it takes the default `human-empty`. Scope item 3 made correcting these comments binding. 3. Overstated claim: leaf_status()'s docstring and the test module docstring assert a dying attempt's half-written report "cannot have closed itself". Soften to "is very unlikely to have" / "would need to be cut off exactly on a quoted trailer line" — the adversary showed the exact case, reachable only through the already-accepted metadata-only-touch hole. Wording only; no code change and do NOT touch _residue_identity or _LeafHarvest. Size backstop (84 KB > 80 KB) is byte-count only: sizing.json band ok, one outcome, and the v3 ruling "one slice, do not split" stands. Not grounds for iterate-plan.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the adversary's three implementation findings only; the design (B-simple, completion trailer, closed three-token table) is confirmed and must NOT be re-opened. Part A and the reader-side guard in assemble.leaf_status() stay as built.
  Fix exactly these three, nothing more:
  1. Composition order: at the review and advisory sites the prompt handed to the leaf is `<constant incl. _COMPLETION_INSTRUCTION> + rubric`, so with a project rubric configured the "end with this exact line ... Nothing may follow it" instruction is not the prompt's last word (leaves.py _REVIEW_PROMPT + rubric_mod.for_reviewer(...) at _run_review_sandboxed; `(... + instruction) + rubric` in _advisory_prompt). Append the instruction AFTER the rubric at the composition site for both, matching what the plan-advisory site already does. Extend the 4e leg to assert on the COMPOSED prompt with a non-empty rubric, so the trailer instruction is the final sentence — the current leg tests the constant with no rubric and passes either way.
  2. Stale comment: the _unavailable_classification docstring paragraph reads "so neither \"leaf did not run\" would be true of it" — a half-deleted "neither ... nor" from the struck fourth-token design. Reword to say plainly: it exited 0, so "leaf did not run" would be false; it takes the default `human-empty`. Scope item 3 made correcting these comments binding.
  3. Overstated claim: leaf_status()'s docstring and the test module docstring assert a dying attempt's half-written report "cannot have closed itself". Soften to "is very unlikely to have" / "would need to be cut off exactly on a quoted trailer line" — the adversary showed the exact case, reachable only through the already-accepted metadata-only-touch hole. Wording only; no code change and do NOT touch _residue_identity or _LeafHarvest.
  Size backstop (84 KB > 80 KB) is byte-count only: sizing.json band ok, one outcome, and the v3 ruling "one slice, do not split" stands. Not grounds for iterate-plan.
- Full previous attempt preserved in `iteration-v4/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).

## Iteration 5 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on one finding only (adversary, SUMMARY §6 item 4). Round 5's three carry-forward fixes are confirmed, and the design (B-simple: completion trailer, no new status token) must NOT be re-opened. Part A, the reader-side guard in assemble.leaf_status(), the prompt composition order and all tests stay as built. This is meant to be the last round. Fix exactly this, wording only, no logic change: 1. The runtime string `_COMPLETION_INSTRUCTION` in leaves.py is sent to every reviewer leaf (review, advisory, plan-advisory). It currently says the trailer "is how the harness tells your finished report from a half-written one left behind by an attempt that died, and an artifact it cannot tell apart is not read as your verdict." Both claims are false for this patch: dead-attempt leftovers are separated by _LeafHarvest's ownership check, not by the trailer, and a report WITHOUT the trailer IS still read as the verdict (criterion 4b). A leaf that believes this could leave the trailer off on purpose to hold a report back. Replace it with a plain, true statement, e.g. "When {artifact} is complete, end it with this exact line, on its own, as the very last line of the file: <trailer> — it tells the harness this file is your finished report. Nothing may follow it." 2. The block comment above `_COMPLETION_INSTRUCTION` says whether a report is finished is "a question no amount of reading the report's TEXT can answer", but the trailer is itself read from the text. Reword so it says what is true: the trailer is the leaf's own statement that it finished, and absence of it changes nothing. Leave the four-token non-growth test (it includes #526's sandbox-empty, already in the base) as it is.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on one finding only (adversary, SUMMARY §6 item 4). Round 5's three carry-forward fixes are confirmed, and the design (B-simple: completion trailer, no new status token) must NOT be re-opened. Part A, the reader-side guard in assemble.leaf_status(), the prompt composition order and all tests stay as built. This is meant to be the last round.
  Fix exactly this, wording only, no logic change:
  1. The runtime string `_COMPLETION_INSTRUCTION` in leaves.py is sent to every reviewer leaf (review, advisory, plan-advisory). It currently says the trailer "is how the harness tells your finished report from a half-written one left behind by an attempt that died, and an artifact it cannot tell apart is not read as your verdict." Both claims are false for this patch: dead-attempt leftovers are separated by _LeafHarvest's ownership check, not by the trailer, and a report WITHOUT the trailer IS still read as the verdict (criterion 4b). A leaf that believes this could leave the trailer off on purpose to hold a report back. Replace it with a plain, true statement, e.g. "When {artifact} is complete, end it with this exact line, on its own, as the very last line of the file: <trailer> — it tells the harness this file is your finished report. Nothing may follow it."
  2. The block comment above `_COMPLETION_INSTRUCTION` says whether a report is finished is "a question no amount of reading the report's TEXT can answer", but the trailer is itself read from the text. Reword so it says what is true: the trailer is the leaf's own statement that it finished, and absence of it changes nothing.
  Leave the four-token non-growth test (it includes #526's sandbox-empty, already in the base) as it is.
- Full previous attempt preserved in `iteration-v5/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
