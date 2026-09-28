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

Review issue #541: prevent dead-attempt artifacts from becoming live verdicts, preserve completed reports that quote status markers, and make the completion instruction accurately describe that contract.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The latest carry-forward resolves the earlier three/four-token discrepancy and requires truthful completion wording without reopening the accepted design; the instruction and inert-absence behavior agree with that scope (`brief.md:344`; `target/template/src/pdca_harness/leaves.py:2523`; `target/template/src/pdca_harness/assemble.py:169`). |
| C2 Reproduction (red pre-fix) | PASS | Stashing production changes reproduced dead-text harvest at all three sites and loss of real findings; the 24-test run had 13 assertion failures and 5 errors, with independent assertion failures establishing the defect rather than missing-symbol errors (`reviewer-red.log:1`; `target/template/tests/test_attempt_harvest.py:280`). |
| C3 Change | PASS | Reviewer leaves receive a truthful completion instruction, while omitted trailers retain legacy classification; composed-prompt, placeholder, and unchanged #278 tests passed, preserving the agreed compatibility boundary (`target/template/src/pdca_harness/leaves.py:2541`; `target/template/tests/test_attempt_harvest.py:666`; `target/template/tests/test_attempt_harvest.py:711`). |
| C4 Verification (red→green) | PASS | Restoring the patch changed the regression suite from red to green; all 24 new tests plus 15 unchanged leaf-status tests passed without skips, and the independent three-reader probe produced every specified transition (`reviewer-green.log:54`; `reviewer-probe-red.log:1`; `reviewer-probe-green.log:1`; `target/template/tests/test_attempt_harvest.py:574`). |
| C5 Causal adequacy | PASS | Ownership is checked at harvest and completion at the shared classifier, addressing the two demonstrated causes; no optional-capability probe masks an eager/load-time failure, and tests invoke production readers and real subprocess harvest paths (`target/template/src/pdca_harness/leaves.py:884`; `target/template/src/pdca_harness/assemble.py:169`; `reviewer-prod-path.log:1`). |
| T1 Structure | PASS | All three harvest sites share one owner and one resilient-invocation callsite; the three classification consumers still share one classifier, preventing divergent treatment of the same report (`target/template/src/pdca_harness/leaves.py:816`; `target/template/src/pdca_harness/leaves.py:884`; `target/template/tests/test_attempt_harvest.py:475`). |
| T2 Shape | PASS | Independent docs lint, 22-page render/link audit, production-import scanner, and diff whitespace checks passed; frozen docs and host-CI logs corroborate the same checks (`gate-logs/T2-docs.log:10`; `gate-logs/host-ci-docs.log:10`; `reviewer-prod-path.log:1`). |
| T3 Runtime | PASS | Independent driver suite: 1,990 tests, OK with two skips; frozen evidence additionally shows all 24 root render/update tests passing, while the local root rerun lacks importable Copier and version tags (`gate-logs/T3-suite.log:38`; `gate-logs/T3-suite.log:54`; `reviewer-suite.log:1656`; `reviewer-root.log:33`). |
| T4 Contribution | N/A | Contribution artifacts are intentionally drafted after Check; the substantive contribution audit must rerun at publish, so this deferred row supplies no contribution verdict yet (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Confirm the recorded affected-path prior-art search covers the applicable merged and closed/rejected work — this one-commit snapshot has no remotes or upstream history to independently establish that the patch is not superseded (`brief.md:307`; `reviewer-history.log:1`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the demonstrated ownership/classification behavior and truthful prompt satisfy the intended review workflow — automated evidence establishes emitted instructions and artifact handling; acceptance of their fitness for the configured reviewer leaves remains the sign-off decision (`target/template/src/pdca_harness/leaves.py:2541`; `target/template/tests/test_attempt_harvest.py:711`). |

No patch defect found within the agreed scope. The accepted metadata-only-touch limitation and the decision to keep this as one slice are not reopened. The existing `sandbox-empty` token remains, as explicitly directed by the latest carry-forward; no new status token was introduced.

Independent evidence: in the disposable target, `git stash push` retained the new test file while restoring pre-fix production; `PYTHONPATH=src python3 -m unittest tests.test_attempt_harvest` reproduced red. After `git stash pop`, `PYTHONPATH=src python3 -m unittest -v tests.test_attempt_harvest tests.test_leaf_status` passed all 39 tests. Runs used a non-root user, so the permission-sensitive harvest legs executed. Scratch files were confined under this review directory through `TMPDIR`.

A separate constant-input probe checked each reader without stopping after the first failed assertion: pre-fix results were `human` with the incorrect “leaf did not run” prefix, `review_drove_iterate=true`, and zero plan findings; restored results were unprefixed `impl`, `false`, and one finding. See `reviewer-classification-probe.py`, `reviewer-probe-red.log`, and `reviewer-probe-green.log`. Legacy absence and unchanged placeholder tests are non-regression evidence, not claims of additional pre-fix defects.

Host/evidence caveat: the local root runner exited 77 because Copier is not importable by this Python and the disposable snapshot has no version tags. This is not a patch failure or an unmet fix dependency: the frozen T3 log explicitly records actual render and update-compat execution with 24 passing tests. All six named gate logs were readable; instance-scoped wrapper absence was not treated as a finding. The production-import reference scanner was also rerun directly from the target. The available INTEGRATION template has no enumerated additional human-only decisions (`target/template/docs/INTEGRATION.md.jinja:80`).

Grounding: source citations refer to the supplied patched `target/`. Reverse-application checking of the complete `patch.diff` passed after restoration, and only the original two modified production files plus the new test remained. No target-state staleness was observed. The affected-path history investigation returned only synthetic base commit `3e1fd44`; the brief records a path-based merged-history search and rejected local approaches, but their underlying history is outside the supplied evidence.

<!-- pdca:leaf-complete -->

### Advisory — adversary

# Advisory review — adversary (issue 541, round 6)

Lens: try to refute the red→green proof and the fix. Result: **I could not refute the fix.**
Nothing below needs a human decision, so no bullet here is marked for §6. (I quote the
leaf-status marker only by name, never in its literal comment form, so this file cannot be
misread as a placeholder by the harness that is running it.)

## What I re-ran

- **Red→green reproduced** at `template/tests/test_attempt_harvest.py`. I ran it offline on a
  scratch copy of `$PDCA_TARGET`: patched tree 24/24 OK; with `assemble.py` and `leaves.py`
  restored from the base commit (`git show HEAD:…`), FAILED (failures=13, errors=5). That
  matches `gate-logs/C4-verify.log` exactly. The 5 errors are real failures, not load
  failures. Two are missing new symbols referenced inside test bodies (`_LeafHarvest`,
  `LEAF_COMPLETE_TRAILER`). The other three are the base misbehaving: a PermissionError crash
  in `copy2` on an unreadable residue, and two cases where no error log was preserved. The
  module imports only `assemble, autoiterate, leaves, size_signal, state` at module level, so
  the red leg is not UNVERIFIABLE.
- **Each of the three readers flips independently** (`assemble.py:169-171`). The shipped leg
  `test_attempt_harvest.py:574-604` checks the three readers one after another in a single
  test body, so the gate's red leg only proves the first one (it stops at `:586`). I probed all
  three on their own with the brief's artifact: a fenced quote of the infra-empty marker, with
  the trailer as the last line. Results, base → patched:
  `_items_from_artifact` `['human']` → `['impl']`; `_review_drove_the_iterate` `True` →
  `False`; `_plan_findings` `0` → `1`. That matches the brief's Falsifiability table.
- **4d holds.** `test_leaf_status`, `test_leaf_resilience` and `test_attempt_ownership` are
  unmodified (the patch touches only `assemble.py`, `leaves.py` and the new test file) and
  pass: 31 tests OK.

## Refutation attempts that failed

- **Can a harness placeholder end with the trailer?** That would let a placeholder pass as a
  real review and smuggle in `[impl]`, breaking the #278 contract. No. All three placeholders
  end with a line the harness writes itself: `leaves.py:3240-3241`, `:3587-3588`,
  `:4075-4076`. The leaf-derived `reason` sits in the middle of a line, never at the end of the
  file. So a leaf output that ends with the trailer cannot become a placeholder's last line.
- **Does anything else in the harness write into a leaf's artifact after the leaf finishes?**
  Only `_note_bash_unavailable` (`leaves.py:4032-4052`). When there is no trailer, its output
  is byte-identical to the base: `"\n" + note` gives the same bytes as the old literal, so 4b
  holds. When there is a trailer, the note goes above it and the trailer stays last. The plan
  revision pass writes only `brief.md`, not the plan-advisory file (`_plan_revision_prompt`),
  and I found no other writes to `check-advisory-*` / `plan-advisory-*` in the package.
- **Is the closing instruction really the last thing the leaf reads?** Yes. `_invoke` only
  *prefixes* the prompt (`leaves.py:630`, `prompt_prefix + prompt`). The instruction is added
  after the rubric at the review and advisory sites (`leaves.py:3174-3175`, `:3427-3428`) and
  last at the plan site (`:3645-3646`). Each builder has exactly one caller. The 4e leg checks
  the prompt as actually sent, captured from the stub leaf's stdin, with a non-empty rubric.
- **This round's wording change** (`leaves.py:2522-2545`). The runtime string now claims only
  that the trailer "tells the harness this file is your finished report". That is true: it
  makes `leaf_status` return "" at all three readers. It no longer threatens that a report
  without the trailer is ignored, which would be false under 4b. The block comment now states
  what is true: absence changes nothing, and filing never depends on the trailer, because
  `_LeafHarvest` does not read it. No logic changed. `.format(artifact=…)` is applied only to
  the instruction, so braces in a rubric or `leaf_id` cannot break it.
- **Edge inputs to the guard.** CRLF line endings and a trailer padded with non-breaking
  spaces are both recognised. A zero-width character after the trailer is not, so that file
  falls through to today's behaviour. That is 4b working as designed, not a defect.
- **Un-owned path that could not even be `stat`-ed** (`leaves.py:980`, `_unidentified`). This
  refuses a file the live attempt provably wrote. Example: a dead attempt leaves a symlink loop
  at the artifact path, and the live attempt removes it and writes a real file. The docstring
  documents this as intentionally conservative, the brief puts the harvest structure out of
  scope, and the case is exotic, so I am not filing it.

## Notes (not escalated)

- `assemble.py:132-134` still says a report quoting the trailer inside a fenced block "cannot
  stamp itself complete — the fence's closing line is the last one". That fails when the fence
  is never closed. On the patched tree, a text ending with an open code fence followed by the
  trailer line returns `''` from `leaf_status`. `test_attempt_harvest.py:651` says the same
  thing ("what a quotation cannot forge"). Round 5 softened this same overstatement in
  `leaf_status`'s own docstring (`:162-164`), which sits right below and already names the
  exception. It does no harm: only text a leaf wrote can reach this shape, and that text is a
  real report anyway. It is wording only, and it is the truncation gap the human has already
  accepted, so I am leaving it out of §6. The human ruled this the last round.
- The `test_attempt_harvest.py:718` red is only an AttributeError on the new constant, not
  evidence of the defect. That is fine for a 4e write-site guard, but it should not be counted
  as a red→green. I could not see `build-notes.md`, so I cannot check how it was counted there.

Attempted to refute: the C4 evidence, the reader guard, placeholder spoofing, post-harvest
writes, prompt order, this round's wording, and edge line endings. I could not refute any of
them.

### Advisory — code-review

# Advisory code review — issue 541 (correctness + reuse lens)

**Verdict: no correctness bugs found in this diff.** No NEEDS-HUMAN items. Two small notes on reuse and efficiency follow. Neither is worth another round on its own.

What I checked, against the patched tree at `$PDCA_TARGET`:

- **Reader guard.** `template/src/pdca_harness/assemble.py:156` (`leaf_status`) takes the last non-blank line, compares it after strip, and returns `""` on a match. Otherwise it falls through to the unchanged `_LEAF_STATUS_RE.search`. Trailing blank lines, surrounding whitespace, a trailer quoted in a fence, and a trailer mentioned inline are all handled correctly. The one function is still the only classifier: its three callers are `assemble.py:247`, `leaves.py:3734` and `size_signal.py:233`.
- **Status table.** `leaves.py:3275-3279` sends `_FAIL_UNOWNED` to the default `human-empty`. No fourth or fifth token was added. The docstring at `leaves.py:3262-3274` and the block comment at `assemble.py` (above `LEAF_STATUS_INFRA`) now describe the design that shipped. The old "neither …" leftover from the struck design is gone.
- **Write sites.** Review (`leaves.py:3173-3175`), advisory (`leaves.py:3427`) and plan-advisory (`leaves.py:3646`) each append `_COMPLETION_INSTRUCTION` last, after the rubric. The runtime text at `leaves.py:2541` no longer claims that a report without the trailer goes unread. The three stubs emit the trailer. The three `_*_unavailable` placeholders do not.
- **Harvest refactor.** Behaviour is preserved at all three sites. There is one small change on the "exited 0, wrote nothing" path: the placeholder now receives `error_log`. It only mentions the log when `_preserve` has actually rewritten it, which is the intended outcome. With no dead attempts, the log does not exist and the text matches today's. The plan-advisory `sandbox_account` closure (`leaves.py:3992-4009`) reproduces the old #526 branches exactly. The only difference is that `bash.sandbox_start_failure()` is now read only when something was filed or when `explain(None)` runs.
- **`_note_bash_unavailable`.** When no trailer is present, the output is byte-identical to the old append. When a trailer is present, the note goes above it and the trailer stays last.
- **Gates.** C4 (the red/green check that the new test fails without the fix and passes with it) is genuinely red: 13 failures and 5 errors, no load failure. T3 (the full test suite) passes, 1990 tests OK.

Notes (advisory only, no action required):

- `template/src/pdca_harness/leaves.py:4047` — `_note_bash_unavailable` works out "is the last non-blank line the trailer?" with its own `text.rstrip().rpartition("\n")`. That is a second copy of the check at `assemble.py:169-170`. The two agree for `\n` and `\r\n` line endings. They only differ on exotic separators that `str.splitlines` also splits on (`\x0c`, `\u2028`, …). A shared helper such as `assemble.is_closed(text) -> bool`, used by both places, would keep the rule in one spot. That matches the brief's "do not add a second classifier" intent. The copy here only decides where to insert the note, not how the artifact is classified, so this is a clean-up, not a defect.
- `template/src/pdca_harness/assemble.py:169` — `leaf_status` builds a full `splitlines()` list of the artifact just to read its last non-blank line. `artifact_text.rstrip().rpartition("\n")[2].strip()` gives the same answer without the list. This is tiny at today's artifact sizes, and the shared helper from the note above would fix it in the same place.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T5 Judgment — Confirm the recorded affected-path prior-art search covers the applicable merged and closed/rejected work — this one-commit snapshot has no remotes or upstream history to independently establish that the patch is not superseded (`brief.md:307`; `reviewer-history.log:1`).
- [x] Validation — fitness-to-purpose — Decide whether the demonstrated ownership/classification behavior and truthful prompt satisfy the intended review workflow — automated evidence establishes emitted instructions and artifact handling; acceptance of their fitness for the configured reviewer leaves remains the sign-off decision (`target/template/src/pdca_harness/leaves.py:2541`; `target/template/tests/test_attempt_harvest.py:711`).

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-09-28

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
