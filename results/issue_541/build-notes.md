# Build notes — issue 541, iteration 6

Line numbers are on the target branch **with the patch applied** (`main` @ `5daab65` +
`patch.diff`) unless marked "base", which means `5daab65` before the patch.

## What this round does

The v5 sign-off rejected on one finding (adversary, SUMMARY §6 item 4): wording only, no logic
change, everything else stays as built. This round changes exactly two things, both in
`template/src/pdca_harness/leaves.py`, and nothing else:

1. **The runtime instruction `_COMPLETION_INSTRUCTION`** (`leaves.py:2541-2545`), which every
   reviewer leaf receives (review, advisory, plan-advisory). It used to say the trailer "is how
   the harness tells your finished report from a half-written one left behind by an attempt
   that died, and an artifact it cannot tell apart is not read as your verdict." Both claims
   were false, and the second gave a leaf a reason to leave the trailer off on purpose. It now
   uses the sign-off's suggested text word for word:

   > When {artifact} is complete, end it with this exact line, on its own, as the very last line
   > of the file: `<!-- pdca:leaf-complete -->` — it tells the harness this file is your
   > finished report. Nothing may follow it.

   Each claim in it is true on this patch: a report whose last non-blank line is the trailer is
   read as a real verdict (`assemble.py:169-171`). It says nothing about a report without it.
2. **The block comment above it** (`leaves.py:2523-2540`). It said the trailer is how
   `leaf_status` tells a finished report "from a file a dying attempt left at the same path —
   which is a question no amount of reading the report's TEXT can answer". Both halves were
   wrong: the trailer is itself read from the text, and dead-attempt leftovers are kept out by
   `_LeafHarvest`, not by the trailer. It now says:
   - the trailer is the leaf's own statement that it finished the file, and an artifact that
     ends with it is read as a real verdict whatever its body quotes;
   - its absence changes nothing: an artifact without it is classified exactly as before, and
     whether an artifact is filed never depends on it — keeping a dead attempt's leftover out of
     the bundle is `_LeafHarvest`'s ownership check, which does not read the trailer (confirmed:
     the only readers of `LEAF_COMPLETE_TRAILER` are `assemble.py:170` and
     `_note_bash_unavailable` at `leaves.py:4047`; `_LeafHarvest` (`leaves.py:816-1046`) and
     its helpers `_read_residue` / `_residue_identity` / `_artifact_digest`
     (`leaves.py:1047-1116`) have none);
   - the instruction must not threaten a cost for leaving the trailer off, because there is
     none and a leaf told otherwise could hold a report back. This line is there so the next
     editor does not put the threat back.
   I also changed "One sentence" to "One instruction" in the same sentence I was rewriting: the
   instruction is two sentences (round 5 noted this and left it; this round rewrote that
   sentence anyway). The rest of the comment (why the leaf writes it rather than the harness
   stamping it; why it goes last, after the rubric) is unchanged.

Nothing else changed. Against `iteration-v5/patch.diff`, the only content differences are those
two blocks; everything else is `index` and `@@` line-number shifts (+4 lines in `leaves.py` below
line 2541). `template/tests/test_attempt_harvest.py` is byte-identical to round 5's (checked
with `cmp`). Part A, the reader-side guard in `assemble.leaf_status()`, the prompt composition
order and all tests are as built.

### What proves this round's change — honestly: no test does

No test tells the round-5 wording from the round-6 wording, and I did not add one:

- The sign-off said "all tests stay as built".
- The 4e leg (`test_attempt_harvest.py:711-768`) checks the composed prompt's last line holds
  the trailer, names the site's artifact and ends with "Nothing may follow it." Both wordings
  pass it. Round 5's C4 green leg ran this same test file against the old wording and passed.
- A test that bans certain phrases from the prompt would only catch those exact phrases, not
  the next false claim. I ruled it out as a check on wording, not behaviour.

What the new text says is backed by behaviour that existing legs already pin, and those same
legs show the old text was false:

- "A report without the trailer is not read as your verdict" was false.
  `test_the_live_attempts_own_artifact_is_harvested_at_every_site` (`test_attempt_harvest.py:350-358`)
  files `_LIVE_TEXT` (`:116`, no trailer) byte-for-byte at all three sites, and
  `test_an_artifact_without_the_trailer_classifies_exactly_as_today` (`:666-690`) pins that
  absence changes no classification.
- "The trailer tells the harness this file is your finished report" is true.
  `test_a_closed_artifact_is_real_at_every_reader_whatever_it_quotes` and
  `test_the_trailer_counts_only_as_the_artifacts_last_non_blank_line` (`:647-664`) pin it.

I checked the rendered instruction directly. For the review site,
`_COMPLETION_INSTRUCTION.format(artifact="check-review.md")` gives
`'\n\nWhen check-review.md is complete, end it with this exact line, on its own, as the very
last line of the file: <!-- pdca:leaf-complete --> — it tells the harness this file is your
finished report. Nothing may follow it.'`. The 4e leg confirms that this exact text is the last
line of the prompt each of the three real sites pipes to its leaf, with a rubric configured.

So the wording fix is verified by inspection plus the existing behaviour legs, not by its own
red→green. If the human wants that to be a mechanical check, it needs a test change, which the
sign-off ruled out for this round.

## Base drift (carried from round 5, still true)

- The brief was planned against `pdca-integration/main` @ `480fa6b`. The harness gave this Do
  beat a worktree at `main` @ `5daab65` ("Merge pull request #574 from
  eduralph/pdca-integration/main"). `480fa6b` is **not** an ancestor of `5daab65`. #540 is on
  `main` through PR #543 (`4050da2`), so the declared dependency still holds. `PDCA_VERIFY_BASE`
  and `PDCA_BASE` were unset in my environment. `iteration-v5/patch.diff` applied cleanly to
  `5daab65` (`git apply --check`), so this round started from it.
- #526 (PR #563) is on this base. It added a fourth status token,
  `LEAF_STATUS_SANDBOX = "sandbox-empty"` (base `assemble.py:105`), so the non-growth leg pins
  four tokens, not three (`test_attempt_harvest.py:692-709`). The v5 sign-off confirmed this:
  "Leave the four-token non-growth test … as it is." #541 still adds **no** token.

## Earlier rounds' work, as carried (line numbers updated)

Round 5's three carry-forward fixes, confirmed at the v5 sign-off:

1. **Composition order.** `_REVIEW_PROMPT` is back to its base text (`leaves.py:2556-2605`, last
   text line `:2604` = base `leaves.py:2218`). The instruction is appended after the rubric where
   each prompt is composed: review `leaves.py:3171-3175`, advisory `leaves.py:3427-3428`,
   plan-advisory last, after #526's text, `leaves.py:3644-3646` (this site takes no rubric).
2. **`_unavailable_classification` docstring.** "Its leaf RAN and exited 0, so "leaf did not
   run" would be false of it; it takes the default `human-empty` instead" (`leaves.py:3262-3267`),
   then the rule paragraph (`leaves.py:3269-3274`).
3. **"cannot have closed itself" softened** to "is very unlikely to have … cut off exactly on a
   line that quotes the trailer": `assemble.py:160-163`, `test_attempt_harvest.py:31-35` and
   `:650-652`.

Round 5's port onto the #526 base:

- **Plan-advisory site on the shared owner, keeping #526.** `_run_plan_advisory_sandboxed` goes
  through `_LeafHarvest` (`leaves.py:4016-4026`). #526's two sandbox readings ride in as the
  optional `explain` hook (`leaves.py:855-867`), implemented at the site as `sandbox_account`
  (`leaves.py:3992-4009`). `run()` consults it only when nothing was filed
  (`leaves.py:886-896`) and returns whether it filed the live attempt's artifact
  (`leaves.py:875-901`); the site uses that for #526's note (`leaves.py:4027-4029`).
  `_LeafHarvest.run` is still the only caller of `_invoke_leaf_resilient` (criterion 6).
- **The #526 note keeps a closed review closed.** `_note_bash_unavailable`
  (`leaves.py:4032-4052`) puts the note just above a closing trailer (`:4046-4048`). Every other
  artifact gets the same bytes as base `leaves.py:3598-3604` (`:4049-4050`).
- Comments made true for this base: `assemble.py:136-141`, `leaves.py:3196-3204`
  (`_FAIL_UNOWNED`), `leaves.py:819-824` (`_LeafHarvest` docstring), `assemble.py:111-113` and
  `test_attempt_harvest.py:695-697` (what rounds 2–4 did), `leaves.py:4033` ("Add", not
  "Append").
- The `_plan_findings` reader still converts through the one guard: `leaves.py:3734`.

### Alternatives for the plan-advisory integration (round 5, unchanged)

| Option | What it costs | Verdict |
|---|---|---|
| **Chosen:** one optional `explain` hook + `run()` returns `bool` | `_LeafHarvest`: net +17 lines against v4. Site: an 18-line `sandbox_account` + 3 lines for the note, replacing #526's 24-line tail (base `leaves.py:3567-3590`). Review and advisory sites: 0 lines. | kept |
| Subclass `_PlanAdvisoryHarvest(_LeafHarvest)` | Same `run()` change plus ~25 lines of subclass, and it breaks `test_all_three_sites_go_through_the_one_owner` (a subclass bound at import escapes the recording swap), which would mean editing a part-A leg. | rejected |
| `run()` returns the error; the site keeps #526's tail | A second copy of the degrade path at one of three sites — what criterion 6 forbids. | rejected on criterion 6 |
| Three hooks (`failed`, `empty`, `filed`) | Same logic spread over three parameters. | rejected |
| Re-classify inside the site's `unavailable` lambda | Cannot read `err.output` and would have to string-match the reason. | rejected on correctness |

## Red→green accounting (C4), final tree

Run through the project's own C4 runner (the configured gate `cmd`):
`PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. Green leg: 24/24 OK. Red leg
(production hunks reverted; the module loaded and "Ran 24 tests", no `_FailedTest`): 14 of 24
legs fail (13 failures + 5 errors = 18 entries, counting sub-cases). Same result as round 5.
This red→green is the slice's; this round's wording change adds nothing to it (see above).

Genuine red→green (the base has the defect, the fix removes it):
- 4a (part B): `test_a_closed_artifact_is_real_at_every_reader_whatever_it_quotes`,
  `test_a_closed_advisory_keeps_its_impl_routing_into_section_6`,
  `test_the_trailer_counts_only_as_the_artifacts_last_non_blank_line` (its first three
  assertions; the fenced / inline "must not trip" assertions are guards),
  `test_the_harness_note_on_a_review_delivered_without_bash_keeps_it_closed`.
- Part A: `test_no_site_files_a_dead_attempts_artifact_as_a_live_ones` (3 sites),
  `test_the_preserved_account_never_reads_as_a_leaf_that_spent_its_attempts`,
  `test_a_preserved_residue_is_bounded_where_it_lands_in_the_bundle`,
  `test_an_unwithdrawable_residue_is_accounted_for_once_not_once_per_attempt`,
  `test_an_unreadable_residue_is_refused_when_nothing_replaced_it`,
  `test_a_residue_that_cannot_be_withdrawn_is_refused_at_every_site` (3 sites),
  `test_an_unwithdrawable_residue_does_not_narrow_the_retry_contract`.
- 4c(i): `test_the_label_never_says_a_run_that_exited_0_did_not_run` — red on the base because
  the base files the dead attempt's residue, so there is no placeholder at all.

Red, but not evidence that the base had a defect:
- `test_all_three_sites_go_through_the_one_owner` (criterion 6): red because `_LeafHarvest` does
  not exist on the base. It proves structure, not a defect.
- 4e: `test_every_instructable_leaf_closes_its_artifact_and_no_placeholder_does`: red only
  because the base has no trailer anywhere. Its placeholder half is green pre-fix by
  construction.

Green pre-fix by construction (regression guards, not proof of the defect, not counted above):
- 4b: `test_an_artifact_without_the_trailer_classifies_exactly_as_today`.
- 4c(ii): `test_the_recognised_status_set_does_not_grow`.
- `test_every_leaf_status_the_harness_can_write_has_a_label`,
  `test_an_artifact_that_quotes_an_unknown_status_early_keeps_its_findings` (the leg the v3
  adversary called vacuous, kept as a guard only),
  `test_a_placeholder_with_an_unknown_status_is_still_never_auto_iterated`.
- A.3: `test_the_live_attempts_own_artifact_is_harvested_at_every_site`,
  `test_a_leaf_that_exits_0_writing_nothing_still_degrades_as_today`.
- Over-refusal guards: `test_a_live_verdict_written_over_an_unwithdrawable_residue_is_still_filed`,
  `test_a_live_verdict_identical_to_the_residue_is_still_filed`,
  `test_a_live_verdict_replacing_an_unreadable_residue_is_still_filed`.
- 4d: `template/tests/test_leaf_status.py` is not in the patch; `:194` and `:204` pass
  unmodified (driver suite green).

The part-B classification legs have no skip guard. The 8 `@unittest.skipUnless(_rootless())`
legs all ran here (not root).

### Mutation checks (round 5, still valid; the code they cover is unchanged)

| # | Change undone | Result |
|---|---|---|
| M1 | review: instruction before the rubric (v4 order) | 4e leg fails, sub-case `prompt='review'` |
| M2 | advisory: instruction before the rubric (v4 order) | 4e leg fails, sub-case `prompt='advisory'` |
| M3 | `_note_bash_unavailable` appends below the trailer (#526 original) | the note leg fails |
| M4 | plan site drops `explain=sandbox_account` | 2 of #526's sandbox legs in `test_plan_advisory.py` fail |
| M5 | plan site drops the note on a filed review | #526's `test_a_review_delivered_without_bash_is_kept_and_says_so` and the note leg fail |

Not run this round: "put the round-5 instruction wording back". The answer is known without
running it: it stays green (see "no test does" above).

## Refuting my own test

- **(a) Genuine red?** For the slice, yes: `run-verify.sh` reverted the production hunks on the
  final tree and 14 of 24 legs failed with the module loaded. For **this round's wording
  change**, no: no leg fails if the round-5 wording is put back. That is the sign-off's call
  ("all tests stay as built"). The wording is checked by the diff against round 5 and the
  rendered string above. I am saying so here rather than counting it as red→green.
- **(b) Production path?** Yes. The 4e leg drives the three real entry points
  (`_run_review_sandboxed` / `_run_advisory_sandboxed` / `_run_plan_advisory_sandboxed`) and
  checks the prompt each site actually piped to the leaf process. That prompt now ends with the
  new `_COMPLETION_INSTRUCTION` text, and the leg passes on it. The harvest legs use the same
  entry points; the only stand-in is the leaf process itself, a Python interpreter in the
  leaf's argv. The classification legs call the production readers directly.
- **(c) Fixture includes the fault?** For the slice, yes: the 4a probe quotes a token the base
  recognises (`infra-empty`); the 4e leg has a non-empty rubric; the note leg replays #526's
  pinned vendor stream (`template/tests/fixtures/claude_sandbox_cannot_start.stream.jsonl`, read
  only, nothing added under `fixtures/`); the part-A legs really kill attempts, lock the
  sandbox and make residues unreadable. For this round the "fault" was false prose in a prompt,
  so there is no fixture to include it in. See (a).

## Other shipped suites

None edited. `test_leaf_resilience.py`, `test_attempt_ownership.py` and `test_leaf_status.py`
are not in the patch. No other suite refers to `_COMPLETION_INSTRUCTION` or its text.

## Gates I ran (all on the final tree)

- C4 `./engine/scripts/run-verify.sh`: PASS (above).
- T3 `./engine/scripts/run-suite.sh`: `PDCA-EVIDENCE: root suite OK, driver suite OK` (root 24
  tests incl. copier render + update-compat; driver 1990 tests, OK, 2 existing skips).
- C5 `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py`: "1 added driver-suite
  test(s) import the production package 'pdca_harness'".
- No docs touched, so T2 / host-ci-docs are not affected.
- After the gates, the worktree still matched `patch.diff` byte for byte (`git diff HEAD` with
  the new test file marked intent-to-add, then `cmp`; the intent-to-add mark was removed
  again afterwards).

## Commit readiness

The target has no formatter or commit-hook config: no `.pre-commit-config.yaml`, no
ruff/black/flake8 config, no `core.hooksPath`, and only `.sample` files in the hooks directory.
`git diff --check` is clean. Every changed line in this round is under 100 columns, matching the
file. CONTRIBUTING.md asks for the offline and root suites to be green (both are) and a DCO
`Signed-off-by` on the commit, which publish adds.

## Small things to know

- **Size.** `patch.diff` is 97,519 bytes (round 5: 97,169). The v4 sign-off ruled the 80 KB
  backstop is byte-count only.
- **Module-level imports in the test** (carried): besides `assemble, leaves, size_signal` the
  file imports `autoiterate`, `state` and `config.Config/LeafConfig`. All exist on the base, so
  there is no red-leg import trap (the red leg loaded the module and ran all 24 legs).
- **A scratch file in the worktree.** I sent the T3 run's output to `.t3-541.log` at the
  worktree root. It is untracked, not in `patch.diff`, and holds only that gate's log.
- **No PR.** Nothing was pushed or opened.
