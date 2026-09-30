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

Review issue #541: prevent dead attempts’ artifacts from becoming live verdicts, and preserve completed reports’ findings when they quote leaf-status markers.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | NEEDS-HUMAN | Reconcile the exact-three-token requirement with the base’s existing #526 `sandbox-empty` status — preserving host-failure routing leaves four tokens, and the new test explicitly pins four; `brief.md:68`, `target/template/src/pdca_harness/assemble.py:119`, `target/template/tests/test_attempt_harvest.py:705`, `review-readers.log:6`. |
| C2 Reproduction (red pre-fix) | PASS | Independent pre-fix execution reproduced dead-artifact harvesting and quoted-marker misclassification: 24 tests yielded 13 failures and 5 errors, including substantive assertions at every harvest site; `review-red.log:172`, `review-red.log:245`, `target/template/tests/test_attempt_harvest.py:281`. |
| C3 Change | PASS | Within the compatibility question in C1, live verdicts and placeholders remain distinguishable, all three composed prompts close after their rubric, and the harness annotation preserves closure; `target/template/tests/test_attempt_harvest.py:725`, `target/template/src/pdca_harness/leaves.py:4043`. |
| C4 Verification (red→green) | PASS | Stashing production changes reproduced red; restoring them passed all 87 targeted tests without skips, including the 24 new tests and unmodified #278 protections; separate probes verified all three reader transitions; `review-green.log:88`, `review-readers.log:21`, `target/template/tests/test_leaf_status.py:194`. |
| C5 Causal adequacy | PASS | Actual subprocess deaths and filesystem permission failures exercise production ownership; completed-report classification is corrected at the shared reader, with no added optional-capability probe masking a load-time cause; `target/template/src/pdca_harness/leaves.py:755`, `target/template/src/pdca_harness/assemble.py:169`, `review-prod-path.log:1`. |
| T1 Structure | PASS | One owner handles all three harvest sites and is the package’s sole caller of the retry function, preventing site-specific ownership rules from diverging; `target/template/src/pdca_harness/leaves.py:884`, `target/template/src/pdca_harness/leaves.py:3160`, `target/template/src/pdca_harness/leaves.py:3553`, `target/template/src/pdca_harness/leaves.py:4012`. |
| T2 Shape | PASS | Independent whitespace check, documentation lint, 22-page render and internal-link audit passed using the target’s CI commands; `target/.github/workflows/docs-check.yml:33`, `review-docs-lint.log:1`, `review-docs-render.log:3`; frozen parity evidence agrees at `gate-logs/host-ci-docs.log:10`. |
| T3 Runtime | PASS | Independent offline driver suite passed 1,990 tests with two skips; the frozen root-suite log separately shows all 24 render/update-compat tests passed; `review-suite.log:1656`, `gate-logs/T3-suite.log:54`. |
| T4 Contribution | N/A | Contribution artifacts are intentionally absent during Check; the deferred gate’s substantive audit must run at publish; `gate-logs/T4-contribution.log:10`. |
| T5 Judgment | NEEDS-HUMAN | Confirm current merged and closed/rejected prior art by affected file path — the brief records an older search, but this checkout exposes only one flattened base commit and no remotes, so upstream equivalence cannot be independently settled; `brief.md:307`, `review-prior-art.log:1`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether demonstrated rejection of dead artifacts and preservation of actionable findings satisfy the intended sign-off workflow — automated correctness does not settle operational fitness; `target/template/tests/test_attempt_harvest.py:281`, `target/template/tests/test_attempt_harvest.py:606`. |

Independent evidence and boundaries:

- All source citations above ground in the supplied `$PDCA_TARGET`. Reverse patch applicability passed; the patch was restored after both stash/pop investigations. No implementation files were edited.
- The separate constant-artifact probe produced `human → impl`, ambiguous-review `True → False`, and plan-finding count `0 → 1`. Both trees already have the same four status tokens. Thus C1 is a specification/base reconciliation, not a newly added status or a verification failure.
- C4’s pre-fix result contains genuine assertion failures, not merely missing new symbols. The process ran as UID 1000, so permission-dependent regression tests executed. Trailer absence and the closed status set are compatibility guards, not red→green claims.
- Gate wrappers belong to the unavailable instance root. I reran their available target-side checks and read every supplied gate log; root render/update compatibility is credited specifically to its frozen log, not claimed as independently rerun. No unmet external dependency was found for the fix’s Python/git reproduction.
- The prior-art investigation ran `git log --all -- <affected paths>` and `git remote -v`: one synthetic base commit, no remotes. The brief describes rejected earlier approaches, but their archives and current upstream history are not supplied. The target’s only integration document is the template; its human-only enumeration remains TODO (`target/template/docs/INTEGRATION.md.jinja:80`).
- The accepted metadata-only-touch limitation and shared `human-empty` classification remain accepted boundaries, not new findings. No confirmed implementation defect was found.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Advisory review — adversary (issue #541, iteration 5)

Lens: refute the red→green evidence and the reviewer's verdict; find the input that breaks the
fix. Scope: the three carry-forward items from the v4 sign-off, plus the delta as a whole.

**Bottom line:** I could not refute any of the three carry-forward fixes. One wording finding
remains in the same class as carry-forward item 3 (an overstated claim), this time in the prompt
text the leaf reads. One exotic edge is noted below the bar.

## Evidence I re-ran myself

- Re-ran `PYTHONPATH=src python3 -m unittest tests.test_attempt_harvest` at `$PDCA_TARGET/template`:
  24/24 OK. `tests.test_leaf_status` is unmodified by the patch and passes 15/15, so 4d holds.
  The full offline suite (`discover -s tests`) passes: 1990 tests OK, 2 skipped. This matches
  `gate-logs/C4-verify.log` (green 24 OK; red FAILED, failures=13, errors=5) and
  `gate-logs/T3-suite.log`.
- **Mutation, carry-forward item 1 (prompt order).** In a copy of the target, I moved
  `_COMPLETION_INSTRUCTION` back in front of the rubric at the review site
  (`template/src/pdca_harness/leaves.py:3170-3171`). The extended 4e leg went red with
  `review: the prompt does not END with the closing instruction — its last line is
  '- RUBRIC-RULE-5e1: no bare unwrap()'`. I did the same at the advisory site
  (`leaves.py:3423-3424`) and it went red on `prompt='advisory'`. So the new assertions at
  `template/tests/test_attempt_harvest.py:733-742` catch the v4 bug, and they check the prompt
  actually fed on stdin, not a copy of the constant.
- Caveat for whoever cites C4 as proof of item 1: in the C4 red leg the 4e test dies with an
  `AttributeError` on `assemble.LEAF_COMPLETE_TRAILER` (`test_attempt_harvest.py:718`) before it
  reaches the prompt-order assertions. C4 therefore does **not** show that those assertions would
  catch the v4 ordering. The mutation runs above do. This is not a defect, just a limit on what
  the C4 row proves.
- I tried to find text added to the prompt after it is composed. `_invoke` only *prepends* the
  role-injection prefix (`leaves.py:618`, `:630`) and nothing is appended, so the instruction
  stays last for every family, not only the claude-family stub the test drives.
- I tried to make a harness placeholder end with the trailer, which would break #278. Every
  placeholder's last line is fixed prose that ends after the interpolated `reason`
  (`leaves.py:3236-3237`, `:3585-3586`, `:4072-4073`). Even a multi-line `reason` cannot make
  the last line equal the trailer. Could not refute.
- Carry-forward items 2 and 3 (wording): the half-deleted "neither…" sentence is gone
  (`leaves.py:3258-3263` now says plainly that "leaf did not run" would be false and the default
  `human-empty` applies). "cannot have closed itself" is softened in `assemble.py:162-165` and in
  the test module docstring. Grepping the patch finds no remaining "cannot have closed",
  `unowned-empty` or `LEAF_STATUS_UNOWNED`. Could not refute.
- Not a refutation, recorded so nobody re-raises it: the brief says the status set is exactly
  three tokens, but `test_the_recognised_status_set_does_not_grow` pins four, including
  `sandbox-empty`. The base already has `LEAF_STATUS_SANDBOX` (#526; unchanged context at
  `assemble.py:119`). The builder read the base correctly and the brief's count was out of date.

## Findings

- NEEDS-HUMAN — **The trailer instruction tells every reviewer leaf two things this patch makes
  false** (`template/src/pdca_harness/leaves.py:2538-2540`): "it is how the harness tells your
  finished report from a half-written one left behind by an attempt that died, and an artifact
  it cannot tell apart is not read as your verdict." (a) Dead attempts' leftovers are separated
  by `_LeafHarvest.withdraw` (`leaves.py:907`), whether or not they carry a trailer. The trailer
  only changes how a *quoted* status marker is read. (b) By criterion 4b, an artifact *without*
  the trailer **is** read as the verdict. The patch's own leg shows this:
  `test_the_live_attempts_own_artifact_is_harvested_at_every_site`
  (`test_attempt_harvest.py:350`) files `_LIVE_TEXT` (`:116`), which has no trailer, as the live
  verdict, and `leaf_status` returns `""` for it. The block comment above has the same problem
  (`leaves.py:2524-2526`: "a question no amount of reading the report's TEXT can answer", when
  the trailer is itself read from the text). This is the same class as carry-forward item 3,
  except that here it is in model-facing text, not a docstring. A leaf that believes a report
  without the trailer "is not read as your verdict" could leave the trailer off a partial report
  on purpose to hold it back, and the harness would file it anyway. It is wording only, with no
  code change. Not tagged `[impl]` because the sign-off limited this round to exactly three
  fixes. The human decides whether to fold it in now or defer it. Suggested wording: "…it tells
  the harness this file is your finished report; nothing may follow it."
- (Below the bar for a round on its own; recorded, not escalated.) `_note_bash_unavailable`
  re-implements the "is the last non-blank line the trailer?" test with
  `text.rstrip().rpartition("\n")` (`leaves.py:4043-4044`). `assemble.leaf_status` uses
  `splitlines()` (`assemble.py:169`). The two split lines differently. Measured: a closed plan
  review whose trailer follows a U+2028 line separator classifies `""` before the Bash note is
  added and `infra-empty` after, so the note un-closes it. LF, CRLF and bare CR all behave
  correctly, because `read_text` normalises CR. The input is exotic. A shared "last non-blank
  line" helper would remove this second copy of the trailer test, which scope item 2 warns
  against in spirit.

Attempted to refute: the prompt-order fix at both sites, the stale-docstring and overstated-claim
fixes, #278 placeholder safety, the non-growth guard, and the full-suite regression. Could not
refute any of them. The only substantive finding is the prompt wording above.

### Advisory — code-review

# Advisory code review — issue #541 (lens: correctness + reuse/simplification)

No correctness bug found in this round's changes. All three carry-forward fixes from the v4 sign-off are in:

- Composition order: the completion instruction now comes after the rubric at the review site (`template/src/pdca_harness/leaves.py:3169-3171`, `_REVIEW_PROMPT + rubric + _COMPLETION_INSTRUCTION`) and the advisory site (`leaves.py:3423-3424`). It is already last at the plan-advisory site (`leaves.py:3641-3642`). The 4e leg now drives the real entry points with a rubric configured and asserts on the composed prompt read from the leaf's stdin (`template/tests/test_attempt_harvest.py:725-742`). That leg would have failed under the old order.
- The stale "neither … would be true" docstring is reworded (`leaves.py:3256-3262`).
- "cannot have closed itself" is softened in `assemble.leaf_status` (`template/src/pdca_harness/assemble.py:161-165`) and in the test module docstring (`test_attempt_harvest.py:31-34`). A grep of the tree finds no other copy of the phrase.

The reader-side guard is one anchored check at the head of the shared function (`assemble.py:168-172`). All three readers go through it (`assemble.py:247`, `size_signal.py:233`, `leaves.py:3730`), so no second classifier was added. The #526 note now goes above the trailer instead of after it (`leaves.py:4043-4047`), which fixes a real way a closed review could be "un-closed". A leg covers it (`test_attempt_harvest.py:626-645`).

Findings:

- NEEDS-HUMAN — The non-growth leg pins **four** status tokens (`infra-empty`, `startup-empty`, `sandbox-empty`, `human-empty`) at `template/tests/test_attempt_harvest.py:705-709`. The brief (criterion 4c and Repro 4c(ii)) says "exactly three" and leaves out `sandbox-empty`. The patch is right about the code: `LEAF_STATUS_SANDBOX` is already in the base (`assemble.py:119,126`, #526), and the patch neither adds nor removes it. So this is an error in the brief, not the patch. The comments at `assemble.py:107` and `leaves.py:3268` also say "four". A human should confirm that "closed at four" is what 4c meant, so nobody later "fixes" the test down to three by deleting `sandbox-empty`.
- Minor, no action needed: `_note_bash_unavailable` (`leaves.py:4043-4046`) rebuilds the text as `f"{above.rstrip()}\n\n{note}\n{closing}"`. If the artifact is only the trailer line, `above` is empty and the file starts with two blank lines. That's cosmetic, and the trailer stays last, so the classification is correct.
- Minor, no action needed: `_read_residue` (`leaves.py:1068-1072`) decodes each `readline(1000)` chunk separately, so a multi-byte UTF-8 character split across a 1000-byte boundary shows up as U+FFFD (the "replacement character" shown for undecodable bytes) in the quoted residue. Only the quoted copy in `*.error.log` is affected. The digest covers the raw bytes and is unaffected. This is baseline code the brief put out of scope, noted only for completeness.
- Minor naming nit: `_WITHDRAWN_TRAILER` (`leaves.py:786`, the closing line of a preserved error log) and `LEAF_COMPLETE_TRAILER` (`assemble.py:142`) both say "trailer" but have unrelated jobs, and only the second counts in classification. A different name for the first (for example `_WITHDRAWN_FOOTER`) would stop a future reader from thinking they are related. This is optional and does not change behaviour.

Gate evidence checked: `gate-logs/C4-verify.log` shows the red leg failing (13 failures, 5 errors) and ends `C4 PASS — red without the fix, green with it`. T3 suite passes. Nothing here blocks.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C1 Spec — Reconcile the exact-three-token requirement with the base’s existing #526 `sandbox-empty` status — preserving host-failure routing leaves four tokens, and the new test explicitly pins four; `brief.md:68`, `target/template/src/pdca_harness/assemble.py:119`, `target/template/tests/test_attempt_harvest.py:705`, `review-readers.log:6`.
- [ ] T5 Judgment — Confirm current merged and closed/rejected prior art by affected file path — the brief records an older search, but this checkout exposes only one flattened base commit and no remotes, so upstream equivalence cannot be independently settled; `brief.md:307`, `review-prior-art.log:1`.
- [ ] Validation — fitness-to-purpose — Decide whether demonstrated rejection of dead artifacts and preservation of actionable findings satisfy the intended sign-off workflow — automated correctness does not settle operational fitness; `target/template/tests/test_attempt_harvest.py:281`, `target/template/tests/test_attempt_harvest.py:606`.
- [ ] **The trailer instruction tells every reviewer leaf two things this patch makes false** (`template/src/pdca_harness/leaves.py:2538-2540`): "it is how the harness tells your finished report from a half-written one left behind by an attempt that died, and an artifact it cannot tell apart is not read as your verdict." (a) Dead attempts' leftovers are separated by `_LeafHarvest.withdraw` (`leaves.py:907`), whether or not they carry a trailer. The trailer only changes how a *quoted* status marker is read. (b) By criterion 4b, an artifact *without* the trailer **is** read as the verdict. The patch's own leg shows this: `test_the_live_attempts_own_artifact_is_harvested_at_every_site` (`test_attempt_harvest.py:350`) files `_LIVE_TEXT` (`:116`), which has no trailer, as the live verdict, and `leaf_status` returns `""` for it. The block comment above has the same problem (`leaves.py:2524-2526`: "a question no amount of reading the report's TEXT can answer", when the trailer is itself read from the text). This is the same class as carry-forward item 3, except that here it is in model-facing text, not a docstring. A leaf that believes a report without the trailer "is not read as your verdict" could leave the trailer off a partial report on purpose to hold it back, and the harness would file it anyway. It is wording only, with no code change. Not tagged `[impl]` because the sign-off limited this round to exactly three fixes. The human decides whether to fold it in now or defer it. Suggested wording: "…it tells the harness this file is your finished report; nothing may follow it."
- [ ] The non-growth leg pins **four** status tokens (`infra-empty`, `startup-empty`, `sandbox-empty`, `human-empty`) at `template/tests/test_attempt_harvest.py:705-709`. The brief (criterion 4c and Repro 4c(ii)) says "exactly three" and leaves out `sandbox-empty`. The patch is right about the code: `LEAF_STATUS_SANDBOX` is already in the base (`assemble.py:119,126`, #526), and the patch neither adds nor removes it. So this is an error in the brief, not the patch. The comments at `assemble.py:107` and `leaves.py:3268` also say "four". A human should confirm that "closed at four" is what 4c meant, so nobody later "fixes" the test down to three by deleting `sandbox-empty`.

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
- Iteration delta (if iterating): Rejected on one finding only (adversary, SUMMARY §6 item 4). Round 5's three carry-forward fixes are confirmed, and the design (B-simple: completion trailer, no new status token) must NOT be re-opened. Part A, the reader-side guard in assemble.leaf_status(), the prompt composition order and all tests stay as built. This is meant to be the last round. Fix exactly this, wording only, no logic change: 1. The runtime string `_COMPLETION_INSTRUCTION` in leaves.py is sent to every reviewer leaf (review, advisory, plan-advisory). It currently says the trailer "is how the harness tells your finished report from a half-written one left behind by an attempt that died, and an artifact it cannot tell apart is not read as your verdict." Both claims are false for this patch: dead-attempt leftovers are separated by _LeafHarvest's ownership check, not by the trailer, and a report WITHOUT the trailer IS still read as the verdict (criterion 4b). A leaf that believes this could leave the trailer off on purpose to hold a report back. Replace it with a plain, true statement, e.g. "When {artifact} is complete, end it with this exact line, on its own, as the very last line of the file: <trailer> — it tells the harness this file is your finished report. Nothing may follow it." 2. The block comment above `_COMPLETION_INSTRUCTION` says whether a report is finished is "a question no amount of reading the report's TEXT can answer", but the trailer is itself read from the text. Reword so it says what is true: the trailer is the leaf's own statement that it finished, and absence of it changes nothing. Leave the four-token non-growth test (it includes #526's sandbox-empty, already in the base) as it is.
- By / date: Eduard Ralph / 2026-09-28

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
