# Build notes — issue 541, iteration 5

Line numbers are on the target branch **with the patch applied** (`main` @ `5daab65` +
`patch.diff`) unless marked "base", which means `5daab65` before the patch.

## What this round does

The v4 sign-off rejected on three implementation findings only, confirmed the B-simple design,
and said to fix exactly those three. This round makes the three fixes. It also had to **port the
whole v4 patch onto a newer base**, because the target moved (next section). Part A, the
reader-side guard in `assemble.leaf_status()` and the closed-table design are carried as built.
Every change beyond the three fixes is listed under "Changes the port forced", with the reason.

## Base drift — read this first

- The brief was planned against `pdca-integration/main` @ `480fa6b`. The harness gave this Do
  beat a worktree at `main` @ `5daab65` ("Merge pull request #574 from
  eduralph/pdca-integration/main"). `480fa6b` is **not** an ancestor of `5daab65`. #540 is on
  `main` through PR #543 (`4050da2`), so the declared dependency still holds.
  `PDCA_VERIFY_BASE` and `PDCA_BASE` were unset in my environment.
- In between, **#526** (PR #563, "plan review survives a sandbox that cannot start") landed and
  rewrote the plan-advisory site. The v4 patch no longer applied: `git apply --check` failed on
  `assemble.py` (the status-token block) and on `leaves.py` (the `_FAIL_*` block). I re-applied
  it with `git apply --3way` against the v4 patch's recorded blobs and resolved the six conflicts
  by hand.

What #526 put on the base that this patch has to live with:

1. **A fourth status token already exists**: `LEAF_STATUS_SANDBOX = "sandbox-empty"` (base
   `assemble.py:105`).
   **Deviation from the brief — please confirm at sign-off.** Criterion 4c and the Repro
   instruction say the recognised set is "exactly `{infra-empty, startup-empty, human-empty}`",
   three members. On this base that is false before #541 changes anything, and making it true
   would mean deleting #526's accepted token, which is far outside this slice. So the non-growth
   leg pins the set the base really has, `{infra-empty, startup-empty, sandbox-empty,
   human-empty}` (`template/tests/test_attempt_harvest.py:692-709`). #541 still adds **no**
   token: `unowned-empty` is not in the set and the un-owned case uses `human-empty`. The
   comments that said "closed at three" now say four and name #526 as the deliberate addition
   that met the bar (a machine consumer acts on it): `assemble.py:104-116`,
   `leaves.py:3265-3270`. The brief's own words "so a fifth cannot reappear later" happen to
   describe this exactly.
2. `_plan_advisory_prompt` now ends with #526's Write-tool fallback text (base
   `leaves.py:3207-3216`). The closing instruction goes after it (`leaves.py:3640-3642`).
3. `_run_plan_advisory_sandboxed` (base `leaves.py:3514-3590`) now reads the vendor sandbox's
   own evidence: a CLI refusal when the leaf fails, a dead-Bash stream probe when it exits 0,
   and a harness note added to a review delivered without Bash. See "Plan-advisory site".
4. `_note_bash_unavailable` (base `leaves.py:3593-3604`) appends that note at the **end** of
   the delivered review — below a closed review's trailer. See "The #526 note".
5. `_plan_findings` now reads through `_plan_advisory_outcomes` (base `leaves.py:3291-3304`),
   which also feeds `_plan_not_completed` (#526). It is still one call of
   `assemble.leaf_status` (`leaves.py:3730`) — the brief's third reader — so it converts with
   the same guard. I added one assertion each to the 4a leg (`test_attempt_harvest.py:604`)
   and the 4b leg (`:687`) so the completion record is covered too.

## The three carry-forward fixes

1. **Composition order.** The instruction is no longer inside `_REVIEW_PROMPT`; the constant is
   back to its base text (`leaves.py:2552-2601`, ends at `:2600` exactly as base
   `leaves.py:2218`). It is appended at the composition sites, after the rubric:
   - review: `_REVIEW_PROMPT + rubric_mod.for_reviewer(d, cfg) + _COMPLETION_INSTRUCTION…`
     (`leaves.py:3167-3171`);
   - advisory: `(…) + rubric + _COMPLETION_INSTRUCTION…` (`leaves.py:3423-3424`);
   - plan advisory: last, after #526's text (`leaves.py:3640-3642`); this site takes no rubric.
   `_COMPLETION_INSTRUCTION` now starts with `"\n\n"` so it is its own final paragraph and does
   not run on from the rubric's last bullet (`leaves.py:2532-2541`). Its text is otherwise
   unchanged from v4.
   The 4e leg now asserts on the **composed** prompt: it drives each of the three real site
   entry points with the stub leaf, with a non-empty `rubric-snapshot.md` in the bundle, and
   the stub copies the prompt it received on stdin to a file (`test_attempt_harvest.py:86-87`,
   `:719-742`). It checks that the prompt's last line holds the trailer, names that site's
   artifact and ends with "Nothing may follow it.", and (review, advisory) that the rubric sits
   before the trailer. Mutation-checked — see M1/M2 below: putting v4's order back fails
   exactly the `review` and `advisory` sub-cases, with the rubric line reported as the last line.
2. **Stale "neither" in `_unavailable_classification`.** Now reads: "Its leaf RAN and exited 0,
   so "leaf did not run" would be false of it; it takes the default `human-empty` instead, which
   is true of it" (`leaves.py:3258-3260`). The paragraph after it states the rule the brief asked
   for: the trailer decides whether an artifact is real, the marker only says why it is not, the
   table is closed (at four on this base) and the un-owned case shares `human-empty`
   (`leaves.py:3265-3270`).
3. **Overstated "cannot have closed itself".** Softened to "is very unlikely to have … it would
   need to be cut off exactly on a line that quotes the trailer" in `leaf_status()`'s docstring
   (`assemble.py:160-163`) and the test module docstring (`test_attempt_harvest.py:31-35`). The
   same claim also appeared in a third place, the comment of
   `test_the_trailer_counts_only_as_the_artifacts_last_non_blank_line` ("a truncated attempt
   cannot have written"); softened the same way (`test_attempt_harvest.py:650-652`). Wording
   only; `_residue_identity` and `_LeafHarvest`'s withdrawal logic are untouched.

## Changes the port forced (beyond the three)

- **Plan-advisory site on the shared owner, keeping #526.** `_run_plan_advisory_sandboxed` now
  goes through `_LeafHarvest` like the other two sites (`leaves.py:4012-4022`). #526's two
  "why nothing was filed" readings ride in as one optional hook, `explain`
  (`leaves.py:855-867`), implemented at the site as `sandbox_account` (`leaves.py:3988-4005`):
  a CLI refusal on failure, or every Bash call dying in sandbox startup on a run that exited 0
  and wrote nothing, gives `(reason, _FAIL_SANDBOX)` with #526's exact reason strings; otherwise
  `None` keeps the generic account. `run()` consults it only on those two paths
  (`leaves.py:886-896`) and now returns whether it filed the live attempt's artifact
  (`leaves.py:875-901`); the site uses that to add #526's note (`leaves.py:4023-4025`). The
  withdrawal / ownership / identity / preserve code is unchanged. The other two sites are
  unchanged apart from fix 1. `_LeafHarvest.run` is still the only caller of
  `_invoke_leaf_resilient` in the package (criterion 6 kept).
  #526's own suite (`test_plan_advisory.py`) passes unmodified, and it does bind this hook:
  removing it (M4) fails `test_a_sandbox_that_cannot_start_is_filed_as_sandbox_infra` and
  `test_a_cli_that_refuses_to_start_without_its_sandbox_is_sandbox_infra`.
- **The #526 note keeps a closed review closed.** Appending below the trailer would un-close
  the review, so a closed review quoting a marker would be read as a placeholder again: its
  finding dropped from `_plan_findings`, its leaf recorded as not completed. That is the 4a
  defect coming back through the harness's own annotation, and it would also defeat 4e for
  this path (a leaf that follows the instruction could never earn 4a). `_note_bash_unavailable`
  now puts the note just above a closing trailer and leaves every other artifact byte-for-byte
  as #526 wrote it (`leaves.py:4028-4049`; the `else` branch produces the same bytes as base
  `leaves.py:3598-3604`). New leg:
  `test_the_harness_note_on_a_review_delivered_without_bash_keeps_it_closed`
  (`test_attempt_harvest.py:626-645`), driven through the real site on #526's pinned vendor
  stream `template/tests/fixtures/claude_sandbox_cannot_start.stream.jsonl` (read only; nothing
  added under `fixtures/`). Mutation M3 (append below again) turns it red.
- **Comments the new base made false, or that were false already.**
  - `assemble.py:136-141` said the fall-through marker search "finds a marker only where the
    harness itself wrote one". It does not: for an artifact without the trailer it still
    matches a quoted marker anywhere (the next comment block and the 4b leg both say so). Now
    says the search is unchanged, including its old misreading, which only the trailer fixes.
  - `_FAIL_UNOWNED`'s comment said the only thing any machine reader asks a marker is "is this
    a placeholder?". #526 added a reader that records the status and prints its label in §10.
    Reworded to what is true for both shapes (`leaves.py:3192-3200`).
  - `_LeafHarvest`'s docstring said the sites "used to end with the same hand-copied three
    lines"; on this base the plan site's tail was #526's longer variant of the same bare
    existence test. Reworded (`leaves.py:819-824`).
  - v4's comments said rounds 2–4 of #541 "each added or generalised a token". Round 3 was
    the 8-line header window, not a token change. Since I was rewriting both sentences anyway
    (three → four), they now list what each round did (`assemble.py:111-113`,
    `test_attempt_harvest.py:695-697`).
  - `_note_bash_unavailable`'s docstring opened with "Append"; for a closed review it now
    inserts, so it says "Add" (`leaves.py:4029`).

### Alternatives for the plan-advisory integration (with the cost)

| Option | What it costs | Verdict |
|---|---|---|
| **Chosen:** one optional `explain` hook + `run()` returns `bool` | `_LeafHarvest`: net +17 lines against v4 (+28 / −11 by `difflib` on the class; 6 of each are the docstring rewording): the param, the attribute + comment, the two changed placeholder calls in `run()`, the returns, a 3-line helper. Site: an 18-line `sandbox_account` + 3 lines for the note, replacing #526's 24-line tail (base `leaves.py:3567-3590`). Review and advisory sites: 0 lines. | kept |
| Subclass `_PlanAdvisoryHarvest(_LeafHarvest)` | Needs the same `run()` change to have methods to override, plus ~25 lines of subclass. And it breaks `test_all_three_sites_go_through_the_one_owner`, which swaps `leaves._LeafHarvest` for a recording subclass: a subclass bound at import still inherits the original, so the plan site would record nothing. Fixing that means editing a part-A leg. | rejected |
| `run()` returns the error; the site keeps #526's tail | The site would have to write its own placeholders and call `_preserve()` itself — a second copy of the degrade path at one of three sites, which is exactly what criterion 6 forbids. | rejected on criterion 6, not cost |
| Three hooks (`failed`, `empty`, `filed`) | Same logic in three parameters instead of one hook + a return value. | rejected, more surface for nothing |
| Re-classify inside the site's `unavailable` lambda | Only sees `(reason, failure)`: cannot read `err.output` for the refusal, and would have to string-match the reason to tell "failed" from "wrote nothing". | rejected on correctness |

Known edge I left alone: if a residue is un-owned **and** the live attempt's Bash was dead and
it wrote nothing, the placeholder says "un-owned" (the harvest's own finding), not
"sandbox-empty". Both are true; un-owned wins because `explain` is only asked when nothing is
at the path. Reaching it needs a dying attempt that locks its own sandbox on a host whose
sandbox cannot start.

## Red→green accounting (C4)

Run through the project's own C4 runner: `PDCA_BUNDLE=… PDCA_WORKTREE=…
./engine/scripts/run-verify.sh` → `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
Green leg: 24/24. Red leg (production hunks reverted, the module still loads — "Ran 24 tests",
no `_FailedTest`): 14 of 24 legs fail (13 failures + 5 errors = 18 entries, counting sub-cases).

Genuine red→green — the base has the defect, the fix removes it:
- 4a (part B): `test_a_closed_artifact_is_real_at_every_reader_whatever_it_quotes` (the brief's
  three readers plus #526's completion record), `test_a_closed_advisory_keeps_its_impl_routing_into_section_6`,
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
- `test_all_three_sites_go_through_the_one_owner` (criterion 6) — red because `_LeafHarvest`
  does not exist on the base; it proves structure, not a defect.
- 4e: `test_every_instructable_leaf_closes_its_artifact_and_no_placeholder_does` — red only
  because the base has no trailer anywhere. The brief expected the 4e legs to be green pre-fix;
  the prompt and stub halves cannot be, since they assert something the patch adds. Its
  placeholder half is green pre-fix by construction. What it does prove is shown by M1/M2.

Green pre-fix by construction — guards against a regression this patch could cause, not proof
of the defect (not padded into the count above):
- 4b: `test_an_artifact_without_the_trailer_classifies_exactly_as_today`.
- 4c(ii): `test_the_recognised_status_set_does_not_grow`.
- `test_every_leaf_status_the_harness_can_write_has_a_label`,
  `test_an_artifact_that_quotes_an_unknown_status_early_keeps_its_findings` (the leg the v3
  adversary called vacuous — it is kept as a guard, not as evidence),
  `test_a_placeholder_with_an_unknown_status_is_still_never_auto_iterated`.
- A.3: `test_the_live_attempts_own_artifact_is_harvested_at_every_site`,
  `test_a_leaf_that_exits_0_writing_nothing_still_degrades_as_today`.
- Over-refusal guards (the base files whatever is at the path, so they pass there):
  `test_a_live_verdict_written_over_an_unwithdrawable_residue_is_still_filed`,
  `test_a_live_verdict_identical_to_the_residue_is_still_filed`,
  `test_a_live_verdict_replacing_an_unreadable_residue_is_still_filed`.
- 4d: `template/tests/test_leaf_status.py` is not in the patch; `:194`
  (`test_an_impl_tagged_finding_in_a_placeholder_cannot_smuggle_in_impl`) and `:204`
  (`test_a_real_advisory_finding_is_untouched`) pass unmodified.

The part-B classification legs carry no skip guard. The 8 `@unittest.skipUnless(_rootless())`
legs are the seven part-A legs that need an unwritable directory or unreadable file, plus the
4c(i) label leg, which needs the same lock to produce an un-owned path. All 8 ran here (not
root).

### Mutation checks (each undoes one change in place, runs the leg, restores; worktree verified identical to `patch.diff` afterwards)

| # | Change undone | Result |
|---|---|---|
| M1 | review: instruction before the rubric (v4 order) | 4e leg fails, sub-case `prompt='review'`, last line = the rubric rule |
| M2 | advisory: instruction before the rubric (v4 order) | 4e leg fails, sub-case `prompt='advisory'`, same |
| M3 | `_note_bash_unavailable` appends below the trailer (#526 original) | the note leg fails |
| M4 | plan site drops `explain=sandbox_account` | `test_plan_advisory`: 2 of #526's sandbox legs fail |
| M5 | plan site drops the note on a filed review | #526's `test_a_review_delivered_without_bash_is_kept_and_says_so` and the note leg fail |

## Refuting my own test

- **(a) Genuine red?** Yes. `run-verify.sh` reverted the production hunks and 14 legs failed with
  the module loaded (not a load failure). The two legs that bind this round's fixes also go red
  against the **v4** code, not only the base: M1/M2 (composition order) and M3 (the note).
- **(b) Production path?** Yes. The harvest legs, the 4e composed-prompt leg and the note leg
  call the real entry points `_run_review_sandboxed` / `_run_advisory_sandboxed` /
  `_run_plan_advisory_sandboxed`. The only stand-in is the leaf process itself (a Python
  interpreter in the leaf's argv), which goes through the production spawn, stream reader,
  retry loop, sandbox and harvest. The prompt the 4e leg checks is the one the site piped into
  that process, not a constant. The classification legs call the three production readers
  (`assemble._items_from_artifact`, `size_signal._review_drove_the_iterate`,
  `leaves._plan_findings` / `_plan_not_completed`) directly.
- **(c) Fixture includes the fault?** Yes. The 4a probe quotes a token the base recognises
  (`infra-empty`), so the base really misreads it (an unknown token would be green pre-fix).
  The 4e leg has a non-empty rubric configured, the case the sign-off said the old leg missed.
  The note leg replays #526's pinned vendor stream of a sandbox that could not start, so the
  site really sees dead Bash and really writes its note. The part-A legs really kill attempts,
  lock the sandbox and make residues unreadable.

## Other shipped suites

None edited. The stub trailer made no existing expectation false: the full offline suite passes
(1990 tests, OK, 2 skips that are pre-existing template-checkout skips). `test_leaf_resilience.py`,
`test_attempt_ownership.py` and `test_leaf_status.py` are not in the patch.

## Gates I ran

- C4 `./engine/scripts/run-verify.sh`: PASS (see above).
- T3 `./engine/scripts/run-suite.sh`: `PDCA-EVIDENCE: root suite OK, driver suite OK` (root
  24 tests incl. the copier render + update-compat, driver 1990 tests). One earlier T3 run
  overlapped my mutation script, which edits `leaves.py` in place for a few seconds, so I did
  not count it; the final run was on the untouched final tree, after which the worktree still
  matched `patch.diff` byte for byte.
- C5 `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py`: "1 added
  driver-suite test(s) import the production package 'pdca_harness'".
- No docs touched, so T2 / host-ci-docs are not affected.

## Commit readiness

The target has no formatter or commit-hook config: no `.pre-commit-config.yaml`, no
ruff/black/flake8 config, no installed hooks in `.git/hooks`. CONTRIBUTING.md asks for the
offline suite and the root suite to be green (both are) and a DCO `Signed-off-by` on the commit,
which publish adds. Added lines follow the files' existing width (all under 100 columns; the
files already have lines up to 110).

## Small things to know

- **Size.** `patch.diff` is ~97 KB (v4 was ~86 KB): the #526 integration and the two new test
  pieces. The sign-off already ruled the 80 KB backstop is byte-count only.
- **Module-level imports in the test.** The brief says to import only `assemble, leaves,
  size_signal` at module scope. The file (as built in v4) also imports `autoiterate`, `state`
  and `config.Config/LeafConfig`. All exist on the base, so there is no red-leg import trap —
  the C4 red leg loaded the module and ran all 24 legs. Left as built.
- **Comment wording carried from v4:** `_COMPLETION_INSTRUCTION`'s comment says "One sentence";
  the instruction is two short sentences. Left alone as harmless.
- **A file outside the allowed roots.** I captured the first C4 run's output to
  `/tmp/c4-541.log`. That was a mistake (scratch files belong in the worktree); everything after
  it was piped instead. The file holds only that gate's log.
- **No PR.** Nothing was pushed or opened.
