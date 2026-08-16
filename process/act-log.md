# Act log — pdca-pdca

> Append-only, cross-cycle (docs 02 §ACT). Each entry records which frozen
> bundles an Act review considered, what their records exposed, the concrete
> process deltas applied (each located by a path / rule ID / template field), and
> how the next review will judge whether the delta worked. Act never re-decides a
> contribution's disposition. Newest entries on top.

<!-- Template for a new entry:

# Act review — <date> — cycles considered: <issue_ids>

## What the cycles' records exposed
- <pattern across one or more cycles, citing SUMMARY §6/§7/§10>

## Process deltas
- Spec template: <field added/clarified/removed>            (path)
- Ruleset: <rule added/retired/relaxed/tightened>           (path:line)
- Gates: <check added/promoted/moved>                       (path:line)
- Agent role prompts: <agents/*.md / skill adjustment>      (path:line)

## Follow-ups routed (not process deltas — work handed to an owner)
- Another bug (project/component): filed <tracker> #NNNN    (link)
- Design issue: <name> → dedicated design phase, owner <who>
- Harness/driver issue: this repo's tracker | template feedback upstream  (link)
- Other open Act item: <item> → owner <who>, next step <…>

## How effectiveness will be judged
- The next Do phases should not recreate <specific issue>. Watch the next K cycles.
-->

# Maintenance record — 2026-08-13 — template update to v0.57.0

**Not an Act review** — no bundle was considered and no disposition was touched.
This records the discharge of the open Act item carried by the last five reviews
(2026-08-05 through 2026-08-10), so the next review can judge the effectiveness
criteria those reviews set. The review itself is still owed.

## What was done
- `copier update` v0.56.0 → **v0.57.0**; `.copier-answers.yml` now pins it.
- **The two standing stopgap reverts, per the 2026-08-02 criterion.** The T3
  verdict-line hack and the #31 gate-log tee are gone from
  `engine/scripts/run-suite.sh`: #370 (native `gate-logs/<rule_id>.log`) and
  #402/#428 (a gate declares its own evidence) both ship in the release. Every
  engine gate now declares a `PDCA-EVIDENCE:` verdict on **both** its green and
  its red path — corrected 2026-08-13 after a codex review: the first cut left
  `run-docs-check.sh` and `run-host-ci.sh` under `set -e`, so a failing checker
  aborted the script before its declaration and the undeclared-evidence fallback
  (`gates.py:771`, the last output line) stayed in force on exactly the red row a
  human opens. `run-verify.sh`'s exit-77 paths were already correct: a
  `PDCA-UNVERIFIABLE:` reason becomes the row's evidence through its own branch
  at `gates.py:765`.
- Wired from the release: `dependency_halt`, `leaf_memory_max = "16G"`,
  `[gates] default_timeout_secs = 3600`, a `host_ci` row running the target's
  docs-check.yml on the pushed tree, and `[records] mode = "commit"`.

## What the next review must judge (the criteria the earlier reviews set)
- The T2/T3/T4-oracle-unreproducible and C4-false-unverifiable §6 classes should
  stop recurring. **Recurrence after this date is the signal**; before it is not.
- T4 Check rows should read `deferred`, not a vacuous PASS. Confirmed on the
  offline selftest; confirm it on real bundles.
- A red T3 should carry an inspectable `gate-logs/` file. Confirmed present.
- The 2026-08-02 criterion for the stopgap revert: if the decoy-path evidence
  reappears now that `PDCA-EVIDENCE:` carries it, **reopen upstream #402 rather
  than re-adding the stopgap**.

## Carried forward, unchanged
- **#474 did not make the cut.** The `PDCA_BASE` ambient-env leak — the
  classified cause of the recurring T3 red on stacked bundles — is still open
  upstream. A stacked-bundle T3 red after this update is #474, not a regression.
- **The size-signal re-tighten is now due but NOT done.** v0.57.0 carries #446,
  so the discounting is live; re-tightening is a calibration judgment against
  the corpus (`scripts/size-calibrate`), not a config edit, and belongs to the
  next review. The loosened thresholds stand until then.

## Found while updating — new, for the next review to route
- **A shipped test pair cannot both pass in an instance that enables
  `[leaves.sandbox]`** (this instance enabled it at the 2026-08-01 review, for
  the T5 prior-art check). `test_families.test_leaves_sandbox_is_declared_exactly_once`
  requires exactly one `[leaves.sandbox]` header counting commented ones;
  `test_the_commented_example_parses_when_uncommented` requires a commented one
  to exist. Activating the table makes them mutually exclusive — demonstrated,
  not inferred. This is the issue **#386** class (a suite that ships into
  instances may assert only what holds in every sanctioned posture) and it is
  the sole remaining `make check` failure. **Not a regression: it predates the
  update** — the pre-update baseline was 4 failures, of which v0.57.0 fixes one
  (`test_remote_control_docs.test_it_stays_off_by_default`) and this change
  fixes two (the `[driver.size_signal]` example pair). Filed upstream as
  **eduralph/pdca-harness#507** (bug, Milestone 0.60.0).
- **The same #386 class, hit during the update:** v0.57.0's new
  `test_verify_red_leg.py` / `test_verify_base.py` assert the C4 *skeleton's*
  prose is present in `engine/scripts/run-verify.sh` — wording a filled-in gate
  legitimately replaces, and which the skeleton (`:2`) and `engine/README.md`
  (`:31`, `:84`) tell every instance to replace. Eight failures. Resolved by
  restoring the published contract above this instance's implementation; kept
  on the human's call pending the upstream fix, and marked TEMPORARY in the file.
  **Correction to the first reading:** that restoration is defensive, not
  necessary — `engine/README.md` also ships to instances, is not a fill-in file,
  and carries the same contract and truth table (`:56-67`), so the rule survives
  for any instance that replaces the skeleton. Documented inside #507 rather
  than filed separately, so the split stays the maintainer's call.
- **`host_ci` fetches the network at publish.** The target's `render_site.py`
  pulls mermaid, mirroring the target's own CI. A network blip now blocks a
  push rather than failing a PR check after the fact. Bounded at 900s by a
  ROW-LEVEL `timeout_secs`, not by the `[gates] default_timeout_secs` fallback —
  see below.
- **`[gates] default_timeout_secs` does not reach a `host_ci` row at publish**
  (codex review, 2026-08-13). The fallback is applied by
  `gates._run_one(default_timeout=…)`, and the Check-time caller passes it
  (`gates.py:427`) while the publish-time re-run does not (`publish.py:930`), so
  the parameter defaults to `None`. A row's own `timeout_secs` travels in the
  check dict and binds in both (`gates._gate_timeout` reads it first), which is
  how this instance now bounds the row. Left unfiled pending the maintainer's
  view — the harness's own comment presents the fallback as covering "every row
  without its own bound", which holds at Check and not at the seam where a push
  is waiting.

# Act review — 2026-08-10 — cycles considered: issue_413, issue_458, issue_459, issue_472, issue_473

Seventh Act review — five bundles frozen since the 2026-08-09 review (the index
carried all 42; the 37 previously reviewed were considered only for
effectiveness follow-up). All five merged-wider. **No process delta warranted**
— the wave's dominant class is caused by upstream test machinery and its symptom
clears with the release; the deltas from the last two reviews are holding. Seven
follow-ups routed, one of them against the Act instrumentation itself.

## What the cycles' records exposed
- **The wave's dominant §6 class is a false proposition in a test guard, and the
  last review's log-retention delta is what let it be settled.** "Supply
  `copier` / rerun the 7 render/update tests" lands in **4 of 5** cycles (413,
  458, 459, 472). The retained `gate-logs/T3-suite.log` in **every one of them**
  shows those 7 tests *running* and passing under the gate (`Ran 7 tests … OK`,
  verbose, with names) — so issue_472 §10's conclusion that "the gate
  environment lacks copier" is refuted by its own bundle's log. The real cause,
  verified on the host: `copier 9.17.1` is installed as a CLI at
  `~/.local/bin/copier`, shebanged to its own venv
  (`~/.local/share/copier-venv/bin/python3`), while all three root modules gate
  on **library importability in the running interpreter** and then report it as
  **tool installation** — `try: from copier import run_copy` → `HAVE_COPIER` →
  `@unittest.skipUnless(HAVE_COPIER, "copier not installed")`
  (`tests/test_render_and_run.py:22-31`, `tests/test_update_compat.py:33-37`,
  `:232`, `tests/test_render_cli_name.py:47-52`). The gate leg is green only
  because this instance works around it: `run-suite.sh` runs the root suite with
  `.venv/bin/python3` and `[install].extra_bootstrap` (`pdca.toml:217`)
  pip-installs copier into that venv. The reviewer has no such workaround, so it
  correctly reported coverage it could not obtain. Routed as **#495**.
- **The Act instrumentation could not have found that class — and did not.** A
  recurring signal is keyed on the **first eight words** of the finding
  (`src/pdca_harness/act.py`, `_norm` → `" ".join(words[:8])`). Run over this
  wave, the one class appearing 4 of 5 times yields four distinct keys —
  `supply \`copier\` and decide whether render/update compatibility is` /
  `rerun render and \`copier update\` compatibility with copier` /
  `install/import copier and rerun the seven root render/update` / `accept the
  runtime baseline only after rerunning the` — count 1 each, so **no ledger
  entry and no line in the index's recurring-signals list**. It was found only
  by reading the five bundles by hand. What the index *did* flag as recurring is
  largely formulaic openers ("t4 contribution — decide whether to rely on"), two
  of which are near-duplicates of each other, so the same class is split at one
  end and double-counted at the other. The instrumentation measures *phrasing*,
  not *class*, and is biased toward findings whose wording is boilerplate. This
  is the same open question as triage's recurrence identity (routed as a design
  item on 2026-08-01, unresolved); routed as **#501**, explicitly linked so both
  call sites get one answer.
- **The oracle-absence classes are gone — #31's local work CONFIRMED
  EFFECTIVE.** "T2 Shape — the docs runner is absent", "C4 — the verify oracle
  is a skeleton", "T4 — no runnable contribcheck" dominated every earlier wave
  and appear in **zero** of these five cycles. The resolvable `./scripts/pdca`
  wrapper + wired engine scripts removed them.
- **The size-backstop retune is holding.** At `rounds = 3` it fired only on
  issue_472 (4 rounds) and issue_473 (3 rounds) — both genuinely multi-round
  implementation slices in the adoption core — and stayed silent on 413/458/459.
  No firing this wave was noise. No re-tune; still provisional pending #446/#477
  via the release.
- **#474's stacked-bundle T3 red did not recur.** issue_459 and issue_473 are
  both stacked on `pdca-integration/main`, and both have green T3 rows with
  clean retained logs. #474 is still open upstream, so this is "not observed",
  not "fixed" — recorded so the next review doesn't read it as either.
- **Two of the five bundles were driven by a newer driver than the other
  three.** issue_472 and issue_473 carry `C4-verify.log`, `T2-docs.log` and
  `T4-contribution.log` — native per-gate retention (#370/#415) that the
  v0.56.0 driver this instance vendors cannot write; 413/458/459 have only the
  `T3-suite.log` the local `run-suite.sh` tee produces. Gate *verdicts* stay
  comparable across the wave (the oracles are this instance's own `pdca.toml`
  rows and `engine/scripts/*`, identical for all five); only evidence capture
  differs, and the two odd bundles are the *richer* records, not the poorer.
  Recorded because the naive reading is backwards — it looks like three bundles
  lost their evidence. One caveat kept for a later reader: 472/473 *are* the
  split-adoption core and 473's §6 states it was verified on folded integration
  content, so the driver running them plausibly contained the change under
  review; the run is therefore not independent evidence about adoption itself.
  Bounded, because Check's verdicts come from the gates rather than the driver's
  own behaviour, and both were signed off on that basis.
- **issue_449 still has not frozen** — second review running. Its tracker issue
  is closed (the split happened; children 472/473 shipped), but the bundle sits
  at `AWAITING_SIGNOFF` with `close-disposition = split` already written. That
  is the #481 symptom exactly; the human closing it by hand is the workaround,
  not evidence the path works.
- **Structural, unchanged, no delta possible:** T4 contribution artifacts
  withheld from the reviewer (all five cycles — the artifacts do not exist at
  Check by design; upstream #401 chain) and validation fitness-to-purpose (all
  five — human-only by the sign-off contract).

## Process deltas
- **None.** The dominant class's symptom clears with v0.57.0 (#403 hands the
  reviewer the gate log it currently cannot see), its cause is upstream test
  machinery (#495), and patching it here would deepen exactly the
  `engine/scripts/` divergence we have already agreed to unwind on the update.
- **A delta was considered and rejected**, recorded so the next review does not
  re-propose it: a `[[doctor.checks]]` row probing `python3 -c 'import copier'`
  for the *reviewer's* interpreter. It would encode the same category error as
  the guard it was meant to compensate for — probing importability for a tool
  that is legitimately installed as a CLI — and would report a correctly
  provisioned host as broken. The existing `.venv` row (`pdca.toml:817-823`)
  stays as-is: it is correct there, because `run-suite.sh` deliberately runs the
  root leg with `.venv/bin/python3`.
- Ledger (`process/act-ledger.json`): the copier class registered **by hand**
  (the driver's first-8-words identity split it into four keys — #501), located
  to #495 with the post-update recurrence criterion; the size-backstop entry
  updated to record the retune holding; the T2/C4/T4 oracle-absence entries
  annotated as cleared by #31.

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, test machinery): copier skip guards conflate
  importability with installation, and a wholesale skip of the render/update
  suites passes silently — issue_413/458/459/472 §6 vs. their retained logs →
  filed https://github.com/eduralph/pdca-harness/issues/495
- Harness/driver issue (upstream): the "a split never aborts the flow" contract
  is unpinned — three mutants survive all 27 tests — issue_472 §5/§10 → filed
  https://github.com/eduralph/pdca-harness/issues/496
- Harness/driver issue (upstream): single-id `pdca flow` rc flips 0→1 for an
  unfinished adopted child while stdout stays byte-identical
  (`cli.py:657`/`:661`) — issue_472 §6 → filed
  https://github.com/eduralph/pdca-harness/issues/497
- Harness/driver issue (upstream): `pdca split --accept` prints the `pdca flow
  <child-ids>` hint inside a flow that will adopt them; following it races the
  run, and there is no drive-path lock — issue_472 §10 → filed
  https://github.com/eduralph/pdca-harness/issues/498
- **Design issue** (routed to the human to schedule, outside the cycle): a
  bundle declaring `Depends on <split parent>` is never re-pointed at the
  children that replaced it — the four candidate semantics each imply different
  changes to `waves.check_dep_graph`, the lineage schema and what `split
  --accept` must collect. Filed as a tracked, explicitly design-first item so it
  is not picked up as a fix: https://github.com/eduralph/pdca-harness/issues/499
  No brief authored.
- Harness/driver issue (upstream, re-filed): merge mode should *retarget* a
  wrong-based PR to the real shared base and refuse only if the retarget fails —
  carried since 2026-08-05 as a comment on the **closed** #411, which is not a
  routing destination; now its own issue →
  https://github.com/eduralph/pdca-harness/issues/500
- Harness/driver issue (upstream, Act instrumentation): recurring-signal
  identity is the finding's first eight words, so a wave's dominant class can go
  unregistered while boilerplate openers cluster — evidence above; linked to the
  open triage recurrence-identity design question so one answer serves both →
  filed https://github.com/eduralph/pdca-harness/issues/501
- Open Act item (human-owned, outside Act): close out the **issue_449** result
  bundle at sign-off — Act does not touch a contribution's disposition. Until it
  freezes it stays outside the Act corpus, so the next review's cycle count is
  understated by one.
- Open Act item (human-owned, the release chain, unchanged): cut **v0.57.0**,
  `copier update` this instance, then revert the `engine/scripts/run-suite.sh`
  verdict-line stopgap and the #31 tee.
- Open Act item (carried from 2026-08-01, **sixth review**): triage rubric
  should state five buckets explicitly (issue_316 §10). No triage-class brief
  has appeared in any interval since. If none appears by the next review, retire
  it explicitly rather than carry it indefinitely — a permanently-carried item
  is indistinguishable from a forgotten one.

## How effectiveness will be judged
- **#495:** after it lands and reaches this instance, a reviewer on a
  CLI-installed-copier host must either run the render/update suites or say
  precisely "not importable in this interpreter" while reading the gate log —
  and the T3 §6 item should stop. "Supply copier" recurring *after* the update
  is the signal the fix missed a layer. Recurrence before the update is expected
  and means nothing.
- **#501:** the criterion is about the *instrument*, not the symptom — at the
  next review, the index's recurring-signals list must contain the class a
  hand-read of the bundles also identifies as dominant. If the next wave's
  dominant class is again absent from that list, the fix (or the identity
  representation chosen) is wrong. Until then, treat the recurring-signals
  section as a lower bound and keep reading the bundles.
- **#403 / v0.57.0 chain:** unchanged criterion — recurrence of the reviewer
  reproducibility classes *after* the update lands is the signal.
- **Size backstop:** unchanged criterion. It should keep firing only on slices
  with genuinely implementation-shaped rounds; re-calibrate with
  `scripts/size-calibrate` once #446/#477 arrive, rather than by feel.
- **#496–#500:** verify tracked and progressing at the next review. #500
  specifically tests a routing habit, not code: an item re-filed from a comment
  on a closed issue should still be visible next time.

---

# Act review — 2026-08-09 — cycles considered: issue_448, issue_453, issue_456, issue_457, issue_468, issue_469

Sixth Act review — six bundles frozen since the 2026-08-06 review (the index
carried all 37; the 31 previously reviewed were considered only for
effectiveness follow-up). Four merged-wider fixes (453, 456, 457, 468), two
split closes (448, 469). issue_449 has a split close-disposition on disk but is
not yet frozen in the index — excluded, to be considered next review. All this
wave's upstream PRs are already merged: upstream has **zero open PRs**.

## What the cycles' records exposed
- **The standing T3 mystery is solved — and the #31 log-retention delta is
  CONFIRMED EFFECTIVE.** The 2026-08-06 criterion ("the next T3 red must carry
  a failing test name") was met on its first opportunity: issue_457's retained
  `gate-logs/T3-suite.log` names 11 failures, all
  `test_verify_base.VerifyBaseExport`, all of the shape
  `'origin/pdca-integration/main' != 'UNSET'`. Mechanism, verified in code:
  `src/pdca_harness/gates.py:397` exports `PDCA_VERIFY_BASE=origin/<stack-base>`
  to **every** gate of a stacked bundle — including the repo-scoped T3 suite —
  and this self-hosting target's own `test_verify_base.setUp` never masks the
  ambient variable while `run_gates` merges ambient env into the test's gate
  subprocess. Correlation is exact: the only two stacked bundles in the corpus
  (419, 457) are precisely the T3 reds with this signature, and a hand rerun at
  sign-off has no export — which is why every earlier rerun came back green.
  The pre-retention reds (384/396/436/442, none stacked) stay unclassified but
  any recurrence is now classifiable. Routed upstream as **#474** (two layers:
  scope the export to the verify gate; make the tests hermetic). **No local
  stopgap** — the human's call at this review: wait for v0.57.0, which is being
  worked on now, rather than diverge `run-suite.sh` further.
- **The size backstop fired in 4 of the 6 cycles (453, 456, 457, 468), at
  exactly rounds=2/threshold 2, and every firing was noise** — the new top
  recurring signal. issue_453 §10 names the cause: the rounds were spent on
  environment losses (a missing `copier` in the verifier) and permanently-human
  §6 classes (T4 artifacts withheld, validation), not implementation-shaped
  findings. The discounting fix is issue_436's own contribution (#446), merged
  upstream but in no release. The human's calibration judgment at this review:
  the backstop is too eager for this corpus — 20–30% over target is acceptable
  given the estimator's accuracy. Delta applied below.
- **The v0.57.0 chain is fully unblocked — the only remaining step is the
  cut.** All five prior drafts (#444–#447, #450) are merged; upstream has zero
  open PRs; the latest release is still v0.56.0 and `.copier-answers.yml` still
  pins v0.56.0. Agreed at this review: the human is working toward the cut,
  then `copier update`, then revert the `run-suite.sh:19-49` stopgap and the
  #31 tee per the standing criterion.
- **#31 partially delivered** (local PRs #32/#33/#34: C4 nothing-ran guards,
  T3 evidence tee, resolvable T4 CLI row + doctor rows, leaf policy) — visible
  in this wave's records: issue_457's T4 row now names `./scripts/pdca
  contribcheck`, and every bundle has a retained `gate-logs/T3-suite.log`.
  Issue #31 remains open for the rest of its list.
- **Two one-off §10 defects, both real, both upstream:** issue_453's
  `flow._apply_recorded_decision` prints "no new session" *before* the C6
  accept-guard runs, so a C6-refused accept contradicts it one line later
  (`flow.py:254`); issue_456's `docs/07-crosscutting.md` falsely claims
  `split.read_lineage` returns `None` for a nonnumeric depth — and that false
  claim was the actual source of the reviewer's C3/T2 FAIL on issue_456.
- **Structural/expected, no delta:** the split-close confirm class (448, 469 —
  the split path asks the human to confirm by design; ledger marked
  structural); the T4-artifacts-withheld class (all four merged cycles —
  awaiting the release + the #403 reachability chain, unchanged criterion).

## Process deltas
- Gates/config (this repo, instance-owned): `pdca.toml [driver.size_signal]`
  uncommented and retuned per the human's calibration — `rounds = 3` (fires
  only once the full `max_auto_iters` budget is actually spent), `patch_kb =
  125`, `patch_files = 25` (~25% loosening, inside the human's 20–30%-over-
  target tolerance). Rationale comment in the file cites this entry. Explicitly
  provisional: once v0.57.0 + `copier update` deliver #446's environment-round
  discounting, re-tighten against the corpus with `scripts/size-calibrate`.
- No spec-template, ruleset, or agent-skill delta. The T3 leak fix belongs
  upstream (#474) and the human declined a local stopgap in favor of the
  imminent release — recorded so the next review doesn't re-propose it.
- Ledger: size-backstop signal marked **applied** (located above); split-close
  signal marked **structural** (process/act-ledger.json).

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, template machinery): stacked-bundle
  verify-base export leaks into repo-scoped gates + `test_verify_base` not
  hermetic against ambient bases — issue_457 §5/§10 evidence, answers the
  2026-08-06 open Act item → filed
  https://github.com/eduralph/pdca-harness/issues/474
- Harness/driver issue (upstream): flow's "no new session" notice printed
  before the C6 check — issue_453 §10 → filed
  https://github.com/eduralph/pdca-harness/issues/475
- Harness/driver issue (upstream, docs): `read_lineage` nonnumeric-depth
  clause is false and cost issue_456 a reviewer C3/T2 FAIL — issue_456 §10 →
  filed https://github.com/eduralph/pdca-harness/issues/476
- Harness/driver issue (upstream): size-signal rounds driven only by
  permanently-human finding classes (T4 withheld-by-design, validation
  fitness) still count against the slice — the residual half of issue_453 §10
  that #446's deliberately-narrow environment-only discounting does not cover;
  the local retune masks the noise, this is the cause → filed
  https://github.com/eduralph/pdca-harness/issues/477
- Tracker hygiene (upstream, at the human's direction): the four issues filed
  above labeled (bug / enhancement) and milestoned **0.60.0**; the stray
  **0.67.0** milestone emptied — #472/#473 (split children of #469, filed
  bare + mis-milestoned, i.e. #467's metadata-drop bug in action) moved to
  **0.57.0** with the lineage root #449's `enhancement` label, #469 labeled
  likewise, and #467/#471 (not required for the cut) moved to **0.60.0**.
- Open Act item (human-owned, updated — the release chain): cut **v0.57.0**
  (all prerequisites merged, zero open PRs), `copier update` this instance,
  then revert the `engine/scripts/run-suite.sh:19-49` stopgap and the #31 tee;
  #474 is a candidate to include in the cut since the release is still being
  worked on.
- Open Act item (closed — ANSWERED): "classify the recurring T3 driver-suite
  red once logs are retained" (2026-08-06) → classified at this review as the
  #474 env leak for the stacked cases; the pre-retention non-stacked reds
  remain unknown but any recurrence now self-classifies via the retained log.
- Open Act item (new): issue_449 — frozen after the index was built; consider
  it at the next review alongside whatever freezes next.
- Open Act item (carried from 2026-08-01, unchanged): triage rubric should
  state five buckets explicitly (issue_316 §10) → owner: next triage brief
  author; still no triage-class brief this interval.

## How effectiveness will be judged
- Size-backstop retune: over the next cycles, the backstop should stop firing
  on 2-round bundles whose rounds are environment/human-class noise, while a
  genuinely oversized slice (3 rounds of implementation-shaped findings, or a
  >125 KB / >25-file patch) still raises the item. If it goes silent on a
  bundle that then visibly churns, the loosening overshot — re-tighten with
  `scripts/size-calibrate` rather than by feel. Re-calibrate regardless once
  #446 lands via the update; #477 (human-class round discounting) is the
  cause-level fix that would let the calibrated defaults return.
- #474: after it lands and reaches this instance, a stacked bundle's T3 row
  must be green with a clean retained log. A stacked-bundle T3 red recurring
  *after* that is the signal the fix missed a layer.
- v0.57.0 chain: unchanged criterion — recurrence of the T2/T3/T4/C4 oracle
  classes *after* the update lands is the signal; recurrence before it is
  expected and not evidence of anything.
- #475/#476: small; verify closed at next review, no recurrence expected.

---

# Act review — 2026-08-06 — cycles considered: issue_384, issue_396, issue_419, issue_436, issue_442

Fifth Act review — five bundles frozen since the 2026-08-05 review (the index
carried all 31; the 26 previously reviewed were considered only for
effectiveness follow-up). All five merged-wider at sign-off; all five upstream
PRs (#444–#447, #450) are still open drafts awaiting the human's ready/merge.
At the human's direction this review additionally ran a **cross-instance
comparison against getwyrd/wyrd-pdca** (rendered from the same template
v0.56.0) as a calibration input.

## What the cycles' records exposed
- **New recurring signal — an unclassifiable T3 driver-suite red in 5 of 5
  cycles.** Every frozen T3 row is the identical `== T3: root suite OK, driver
  suite FAILED (rc 1)` with no test name. Unreproducible everywhere: issue_384
  §10 records five sign-off reruns green *including the exact oracle*; the
  reviewers on 419/436/442 ran the driver suite green. Gate-record timestamps
  show 384/396 were written 0.5 s apart (concurrent flows — the §10
  interference hypothesis), but 442 (03:56), 436 (15:03) and 419 (19:29) hit
  the same red running **alone**, so concurrency cannot be the sole cause. The
  red is unclassifiable for a compounding reason: the 2026-08-02 verdict-line
  stopgap keeps only the last output line, and this instance's v0.56.0
  `gates.py` retains no gate log. Third occurrence of the issue_420 §10 class,
  now at wave scale.
- **The release pipe is still the bottleneck — and now blocks strictly more.**
  Progress since 2026-08-05: prerequisite drafts #438/#439/#440 are merged
  (plus #443), so upstream main now carries every previously-routed fix *and*
  native gate-log retention *and* leaf memory bounding. But v0.57.0 is still
  uncut, the instance still renders from v0.56.0, and this wave added five new
  open drafts. The familiar §6 classes (T2/T3 oracle absent, T4 artifacts
  withheld, C4 marker mid-line match) recur exactly as the previous entry
  predicted — expected, not evidence of anything new.
- **issue_442's garbled §6 C4 "unverifiable" line** is the #428 mid-line
  marker match via this instance's stale local `src/pdca_harness/gates.py:443`
  — already ledgered 2026-08-05, cured by the update; no new delta.
- **issue_436's size backstop fired** (2 rounds / threshold 2) and sign-off
  merged anyway — fittingly, that cycle *is* the fix that stops charging
  environment-lost rounds (like these T3 flake rounds) to the slice.
- **Effectiveness confirmations:** T5 network grant (PR #25) — 0/5
  network-unreachable classes, stays confirmed. T3 verdict-line stopgap — 0/5
  decoy paths, stays confirmed; but its last-line-only nature is precisely
  what makes the new T3 red unclassifiable.

## Cross-instance comparison (wyrd-pdca, same template v0.56.0)
- Same agent roster, same sandbox network grant — **every difference is
  instance-authored configuration.** Gaps in this instance that map directly
  onto its recurring §6/§10 pain: lane-safe gate scripts (`$PDCA_LANE`
  scoping — wyrd's `run-verify.sh` is explicitly lane-safe, ours are not,
  see finding 1); retained gate logs; gate-row CLI resolvability (wyrd's
  `scripts/pdca` wrapper vs our bare `pdca-pdca` T4 row the reviewer cannot
  run — the issue_402 §10 / upstream #441 class, solvable instance-side
  today); `[gates] default_timeout_secs` (this instance *built the knob
  upstream* in issue_368 and never set it locally; wyrd: 7200);
  `confirm_gating_fail = true`; doctor coverage (3 rows vs 19, incl. hygiene
  probes); `run-verify.sh` hardening (zero-tests-ran + red-leg-failed-without-
  a-test guards — the #439 class); leaf model/effort policy (per-leaf pins,
  builder escalation ladder, variant roster, difficulty-conditional adversary
  leaf that we ship in `agents/` but never invoke). Gate-depth gaps of design
  scale: gating repo-scoped CI via a `[gates] runner` wrapper, mechanical C5
  (mutation testing over `patch.diff`), gating batched pre-PR rubric review,
  a standing review rubric written into the target repo. Checked non-gaps:
  `[[plan.source]] role="tracker"` already covers wyrd's `notes_cmd` seam;
  Rust-specific doctor rows don't transfer.
- **Meta-insight (agreed with the human):** two instances rendered from the
  same template version landed in different operational safety classes because
  the setup instructions never surface these knobs and nothing validates a
  setup before it runs — this instance ran ~31 real cycles under-configured,
  and the harness never noticed. That is itself the process gap, and it was
  routed upstream (below) rather than patched quietly here.

## Process deltas
- **None applied in-beat — deliberate.** At the human's direction, every
  agreed change (including the previously-proposed `run-suite.sh` gate-log
  tee) is recorded as tracked work instead, so the instance hardening lands
  through the normal Plan→Do→Check cycle with its own gates rather than as an
  Act side-edit: the full located change list is
  https://github.com/eduralph/pdca-pdca/issues/31 (8 concrete changes +
  design-scale follow-ups).

## Follow-ups routed (not process deltas — work handed to an owner)
- Another bug (this repo — instance config values/scripts per the
  template-vs-instance boundary): the wyrd-pdca-derived hardening list —
  lane-safe gates, T3 log-retention tee, CLI-resolver wrapper for gate rows,
  timeout, confirm-once, doctor coverage, run-verify guards, leaf policy →
  filed https://github.com/eduralph/pdca-pdca/issues/31
- Harness/driver issue (upstream, template setup docs): feed these insights
  back into the setup instructions — a production-instance checklist
  enumerating each knob with when-you-need-it guidance → filed
  https://github.com/eduralph/pdca-harness/issues/451 (Milestone 0.60.0)
- Harness/driver issue (upstream): **setup validation** — render-time gate
  scaffolding, doctor form-validation of the setup itself, and `flow`
  refusing (or demanding an explicit waiver) on an under-configured instance;
  "this shouldn't have been running without everything properly configured" →
  filed https://github.com/eduralph/pdca-harness/issues/452 (supersets #441;
  Milestone 0.60.0). All three cross-linked.
- Design issues (named for the human to schedule, outside the cycle; listed
  as follow-ups in #31, no briefs authored): gating repo-scoped CI runner
  wrapper; mechanical C5 mutation gate; batched pre-PR rubric review;
  standing review rubric in the target repo.
- Open Act item (carried, updated): the v0.57.0 chain — prerequisites now
  merged upstream; the release cut now additionally waits on this wave's
  drafts #444–#447/#450 getting ready/merge; then `copier update`, then
  revert the `engine/scripts/run-suite.sh:19-49` stopgap **and** #31's tee
  (item 2) per the standing criterion.
- Open Act item (new): classify the recurring T3 driver-suite red
  (concurrent-lane interference vs environment) once #31 item 2 retains the
  first failing log — issue_384 §10's question, unanswerable until then.
- Open Act item (carried from 2026-08-01, unchanged): triage rubric should
  state five buckets explicitly (issue_316 §10) → owner: next triage brief
  author; still no triage-class brief this interval.

## How effectiveness will be judged
- #31: once its lane-safety + log-retention changes land, the next T3 red must
  carry a failing test name — and the concurrency question becomes decidable.
  If the red never recurs after lane-scoping alone, interference is confirmed
  retroactively.
- #451/#452: judged at the next instance render or `copier update` — an
  under-configured setup should be impossible to run silently. Recurrence of
  a "ran N cycles without knob X" discovery after they land is the signal.
- v0.57.0 chain: unchanged criterion from 2026-08-05 — recurrence of the
  T2/T3/T4/C4 oracle classes *after* the update lands is the signal;
  recurrence before it is expected and not evidence of anything.

---

# Act review — 2026-08-05 — cycles considered: issue_401, issue_402, issue_403, issue_411, issue_420, issue_428, issue_434

Fourth Act review — seven bundles frozen since the second 2026-08-02 review (the
index carried all 26; the 19 previously reviewed were considered only for
effectiveness follow-up, not re-reviewed). All seven merged-wider. Four of the
seven (401, 402, 403, 428) are this instance **fixing its own previously-routed
upstream issues** — pdca-harness #401, #402, #403 and #428 were all closed on
2026-08-05 by these cycles' PRs.

## What the cycles' records exposed
- **The template→instance return pipe is now the bottleneck, not any open defect.**
  The fixes for #401 (T4 `deferred` at Check), #402 (`PDCA-EVIDENCE` verdict line),
  #403 (reviewer oracle reachability / gate-log seeding) and #428 (line-start
  marker matching) are merged to upstream **main**, but the latest release is
  still **v0.56.0** (2026-07-28) — exactly what this instance is rendered from
  (`.copier-answers.yml: _commit: v0.56.0`). Every one of the recurring §6
  classes in these seven cycles (T2/T3 oracle unreproducible, T4 vacuous green,
  C4 oracle skeleton) traces to a fix that exists upstream and has not reached
  here. Two §10 candidates are direct casualties of that gap: issue_434's "sync
  this project's `gates.py`" (verified: `src/pdca_harness/gates.py:443` here
  still matches the marker mid-line — the exact defect #428 fixed, and it turned
  #434's rc-0 C4 PASS into a false `unverifiable` **on 2026-08-05**, three months
  of nothing but the release lag) and issue_420's "retain failing gate output"
  (upstream main already writes `gate-logs/<rule_id>.log` rows; not in v0.56.0).
- **The 2026-08-02 T3 verdict-line stopgap is CONFIRMED EFFECTIVE.** The
  `/tmp/…/issue_500/split-proposal.md` decoy appears in **0 of the 7** new
  cycles' §6, and where T3 was genuinely red the evidence now names the failing
  suite (issue_411's record: "the recorded `./engine/scripts/run-suite.sh`
  driver suite exited 1"). The prior entry's criterion is met. What remains
  unresolved on a T3 red is *classification* — no retained log (issue_420 §10,
  twice on one bundle, unreproducible both times; reviewer ran the driver suite
  green) — which is the gate-log retention fix above, awaiting release.
- **The T5 network grant (PR #25) stays effective.** No "could not reach
  `api.github.com`" class in any of the seven. issue_420's T5 item is a
  *different* complaint (prior art unsettleable "from the three supplied
  artifacts" — artifact-set completeness, not network) — read per the #429
  policy, not string-matched into the old class.
- **Three of these cycles' upstream PRs are still open drafts** — #438
  (issue_411), #439 (issue_434), #440 (issue_420) — awaiting the human's
  ready/merge, which also blocks cutting the release that closes the pipe.
- **§10 one-offs confirmed still live upstream and routed below:** issue_401's
  stale `gates.py` doc sentence ("the one marker that can change a `result`" —
  verified still on main at line 38, directly above the `PDCA-DEFERRED`
  paragraph that contradicts it); issue_402's "every 5/5/1 gate should have a
  runner script, and nothing checks it" (T4's `contribcheck` is a driver
  subcommand with no runner script, read by the reviewer as an absent gate);
  issue_411's "retarget instead of refuse" merge-mode follow-up (upstream #411
  still open, no comment carried it).

## Process deltas
- None to this repo's spec template, ruleset, gates, or agent skills — agreed
  with the human. Every recurring class is covered by a closed upstream fix
  awaiting release; a local change would duplicate copier-managed machinery the
  next `copier update` delivers (and did bite issue_434 precisely because the
  local copy is stale — the cure is the update, not more local divergence).
- Ledger: the five driver-appended recurring signals annotated — the two
  split-proposal T3 signals marked **applied** (pre-stopgap records only;
  stopgap confirmed effective), the T2 oracle signal tied to #403-awaiting-
  release, the Mermaid-fetch signal marked one-off pre-network-grant, the C4
  run-verify-skeleton signal tied to open #419 + new #441
  (process/act-ledger.json).

## Follow-ups routed (not process deltas — work handed to an owner)
- Open Act item (human-owned, agreed at this review): once the open bugs are
  resolved, upstream cuts **v0.57.0** and this instance consumes it via
  `copier update`. That single chain delivers #401/#402/#403/#428 + gate-log
  retention, retires issue_420's and issue_434's §10 items, and should collapse
  the recurring T2/T3/T4/C4 §6 oracle classes. Prerequisite: drafts #438/#439/
  #440 get the human's ready/merge. **Then revert the `engine/scripts/
  run-suite.sh:19-49` stopgap** per the standing 2026-08-02 criterion.
- Harness/driver issue (upstream, comment on open #411): merge mode should
  *retarget* a wrong-based PR to the real shared base (`gh pr edit --base`) and
  only refuse if the retarget fails — issue_411 §10 →
  https://github.com/eduralph/pdca-harness/issues/411#issuecomment-5198287452
- Harness/driver issue (upstream, new): nothing checks that every configured
  5/5/1 gate has a runner — setup helper at render + doctor-style form
  validation — issue_402 §10 → filed
  https://github.com/eduralph/pdca-harness/issues/441
- Harness/driver issue (upstream, new): `gates.py` module doc still calls
  `PDCA-UNVERIFIABLE` "the one marker that can change a `result`", false since
  `PDCA-DEFERRED` — issue_401 §10 → filed
  https://github.com/eduralph/pdca-harness/issues/442
- Open Act item (carried from 2026-08-01, unchanged): triage rubric should
  state five buckets explicitly (issue_316 §10) → owner: next triage brief
  author; still no triage-class brief this interval, so nothing to judge yet.

## How effectiveness will be judged
- After v0.57.0 + `copier update`: the T2/T3/T4 oracle-unreproducible and
  C4-false-unverifiable §6 classes should stop recurring, T4 Check rows should
  read `deferred` instead of a vacuous PASS, and a T3 red should carry an
  inspectable `gate-logs/` file. Recurrence **after** the update lands is the
  signal; recurrence before it is expected and not evidence of anything.
- The run-suite.sh stopgap revert (post-update): confirm the upstream
  `PDCA-EVIDENCE` line alone keeps T3 evidence meaningful — if the decoy path
  reappears, reopen upstream #402 rather than re-adding the stopgap.
- #441/#442 and the #411 retarget comment: continued §6/§10 recurrence of their
  classes is expected while open; check their state next review.
- T5 network grant and the T3 verdict-line stopgap: both now confirmed
  effective; re-open only on recurrence.

---

# Act review — 2026-08-02 (second review of the day) — cycles considered: issue_356, issue_379, issue_380, issue_386, issue_387

Third Act review — five bundles frozen since the earlier 2026-08-02 review (the
index carried all 19; the 14 previously reviewed were considered only for
effectiveness follow-up, not re-reviewed). All five merged-wider.

## What the cycles' records exposed
- **A false-unverifiable in the gate classifier — new, filed as harness #428.**
  `_classify` honours the `PDCA-UNVERIFIABLE:` marker as a bare substring on *any*
  output line, with no check that the **gate itself** emitted it
  (`template/src/pdca_harness/gates.py:595`). #329 closed the `rc != 0` half; the
  exit-0 half is open. issue_387's frozen C4 row proves it fires: `result:
  "unverifiable"` on a **gating** row, with a reason that is a fragment of a code
  comment the bundle's test read back — ``"<reason>` and exit 77\n# (-> SUMMARY §6
  NEEDS-HUMAN, non-gating)…"``. Structural for this instance, because our target
  *is* the harness and its own suite echoes that literal as fixture data
  (`template/tests/test_gates_unverifiable.py:28,32,103`,
  `test_prod_path_gate.py:51-89`). Effect: the one gating correctness check stops
  being a verdict — `unverifiable` is not a failure and does not reach `overall`.
- **The "T3 fixture flake" is a misdiagnosis, and the red is already fixed.**
  Reproduced directly: `tests.test_split` is **green** (96 tests OK), and the
  `/tmp/…/issue_500/split-proposal.md` lines are *leaked stdout* printed after the
  summary — production CLI code (`cli.py:787`, `print(child)`) driven by tests that
  do not capture it, block-buffered under a pipe so it flushes last. The harness
  then files that last line as the gate's evidence. A full wrapper run against a
  current target: root suite `Ran 7 tests … OK`, driver suite `Ran 1468 tests …
  OK (skipped=2)`, **RC=0** — a *passing* gate whose recorded evidence reads like a
  failure path. The historical `T3-suite: fail` rows (311, 317, 340, 341, 368, 370,
  372, 376, 379, 380, 386, 387) were genuine and were resolved by #417/#418 — i.e.
  by this instance's own issue_369 and issue_372 cycles. What recurs in §6 now has
  no failure behind it at all.
- **#403 is a reachability + invocation-contract gap, not a seeding gap**
  (issue_386 §10). The wrappers exist at the instance root and require cwd + a set
  `$PDCA_WORKTREE` + the instance venv; the reviewer works from `$PDCA_TARGET`,
  where neither holds. Intermittent — same gates, same wrappers, cleared on
  issue_356 and escalated on 380/386/387 — which points at guidance, not machinery.
- **The 2026-08-01 T5 network delta (PR #25) is confirmed effective.** The
  "could not reach `api.github.com`" prior-art class appears in **0 of the 9**
  cycles frozen since it landed (317, 332, 356, 369, 370, 372, 379, 380, 386, 387).
  The earlier entry's criterion (absent over ~3 cycles) is met.
- **Known-open classes recurring — expected, no new delta.** T2/T3 oracles
  unreachable (380/386/387 → #403), vacuous T4 contribcheck green (all five → #401,
  whose evidence string is literally empty in issue_387's record), C4 stash
  reproduction (→ #419). All still OPEN upstream.
- **"C4 unverifiable on a test-only/docs-only patch" (379, 386, 387) has two
  halves.** The genuine one is by design — no production hunk to revert means no
  red→green, so #165 routes it to §6. The other half is #428 above. Only the
  second is a defect.

## Process deltas
- Gates (this repo, instance-owned): `engine/scripts/run-suite.sh:19-49` — the T3
  wrapper now runs both suites to completion, ends on a deterministic verdict line
  (`== T3: root suite OK, driver suite OK`) and exits with the preserved rc, so the
  harness's last-line evidence rule captures a verdict instead of whatever the
  suite leaked. Verified both ways: green tree → verdict last, `RC=0`; synthetic red
  tree that *prints a decoy* `/tmp/…/issue_500/split-proposal.md` → `== T3: root
  suite FAILED (rc 1), driver suite FAILED (rc 1)`, `RC=1`, decoy not captured.
  **Explicitly a stopgap, and marked so in the file:** the fix belongs upstream in
  #402: revert this block and take the upstream version once #402 lands.
- No spec-template, ruleset, or agent-skill delta warranted. The reviewer role
  prompt (the natural home for the #403 invocation contract) is copier-managed
  (`agents/` renders from the template), so a local edit would be clobbered on
  `copier update` — it belongs upstream.

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, template machinery): the `PDCA-UNVERIFIABLE`
  marker is matched anywhere in captured output, flipping a green gating C4 to
  unverifiable → filed https://github.com/eduralph/pdca-harness/issues/428
- Harness/driver issue (upstream, correction to an open issue filed on a false
  premise): #402 says the `issue_500` fixture flakes; it does not and never failed.
  Posted the reproduction, the leak's origin (`cli.py:787`) and the last-line
  evidence rule →
  https://github.com/eduralph/pdca-harness/issues/402#issuecomment-5160169457
- Harness/driver issue (upstream, added evidence to open #403): the wrappers are
  present but the reviewer runs them from the wrong root without `$PDCA_WORKTREE`;
  cleared on 356, escalated on 380/386/387 →
  https://github.com/eduralph/pdca-harness/issues/403#issuecomment-5160031102
- Open Act item (carried from 2026-08-01, unchanged): triage rubric should state
  five buckets explicitly (issue_316 §10) → owner: next triage brief author; still
  no triage-class brief in this interval, so nothing to judge yet.
- Design issue **CLOSED — declined by the human at this review** (was: routed
  2026-08-01 for a dedicated design phase): triage recurrence-identity
  representation, broad class vs class+keyword vs semantic slug (issue_316 §6 C5,
  `template/src/pdca_harness/triage.py:108`). Decision: do **not** redesign the
  identity grammar; accept reading through the reviews to judge whether two
  findings are the same complaint. Rationale: the alternative that actually
  detects synonyms is a semantic slug, which puts a model in charge of naming
  ledger identities and makes those names unstable across model versions — a
  worse trade than doing the comparison by hand on a path that runs rarely.
  No further scheduling; do not re-route this at the next review.
- **Consequence of that decision, binding on future Act reviews:** for
  `codex-pr:*` triage signals, the absence of a recurrence is **not** evidence
  that a delta worked. `act.py:522 recurrences()` matches signals by exact string
  (`act.py:535`) and `triage.py:108` keys them on class **+ the matched keyword**,
  so synonyms inside one class ("untested" / "missing test", `triage.py:81`)
  register as separate signals that each look like a first occurrence. A future
  review must read the findings themselves before calling a triage-class delta
  effective. This does NOT affect the §6-derived signals from our own bundles —
  including this review's "confirmed effective" call on the T5 network grant,
  which rests on §6 text, not on the triage grammar.
  **Routed upstream as default policy** (the human's call — this is not a
  pdca-pdca lesson, it holds for every instance): state it in the Act role prompt
  (`template/agents/act.md.jinja`, `## What you read`) and beside the existing
  blind-spot precedent in `docs/07-crosscutting.md:167` → filed
  https://github.com/eduralph/pdca-harness/issues/429
- Ledger: T5 network signal annotated **confirmed effective**; the C4-unverifiable
  signal annotated with its two halves (#165 structural / #428 defect); T4
  contribution signal left open pending #401 (process/act-ledger.json).

## How effectiveness will be judged
- The next frozen cycles' T3 rows should carry `== T3: root suite …, driver suite …`
  as their evidence, and the `/tmp/…/issue_500/split-proposal.md` string should
  disappear from §6 entirely. If it survives, the last-line assumption is wrong and
  the delta should be reverted rather than patched.
- #428: C4 rows should stop reading `unverifiable` on bundles that merely *mention*
  the marker. Until it lands, expect the class to keep appearing on harness-facing
  work — that is not evidence against the filing.
- When #402 lands, revert `engine/scripts/run-suite.sh:19-49` and confirm the
  upstream fix alone keeps the evidence line meaningful.
- T5 prior-art class: recorded confirmed effective this review; re-open only if it
  reappears.

---

# Act review — 2026-08-02 — cycles considered: issue_317, issue_332, issue_369, issue_370, issue_372

Second Act review — five bundles frozen since the 2026-08-01 review (the index
carried all 14; the nine previously reviewed were considered only for
effectiveness follow-up, not re-reviewed). Four merged-wider, one closed as a
split (issue_332).

## What the cycles' records exposed
- **Known upstream classes recurring while their fixes are still open — expected,
  no new delta.** T2/T3 oracle wrappers absent from the reviewer sandbox
  (317, 369, 370, 372 §6 → harness #403); T4 contribcheck vacuous/unreproducible
  at Check (317, 369, 370, 372 §6 → harness #401); the synthetic
  `issue_500/split-proposal.md` T3 fixture flake (317, 370, 372 §6 → harness
  #402). Per the 2026-08-01 entry's own effectiveness criteria, recurrence
  *before* those issues land is expected; recurrence after they ship via
  `copier update` is the signal to watch.
- **New recurring finding — reviewer sandbox git index is read-only, blocking
  C4 red→green reproduction** (issue_317 §6 C4: "Git stash could not write the
  read-only worktree index"; issue_372 §6 C4: "git stash could not run because
  this worktree's git index is read-only"). Distinct from #403: even with the
  oracles present, the reviewer cannot stash the patch to reproduce the pre-fix
  red, so C4 lands in §6 as a judgment call instead of a mechanical re-check.
- **Early effectiveness signal for the 2026-08-01 T5 delta (PR #25 network
  grant):** the "could not reach `api.github.com`" prior-art class appears in
  none of the five new cycles' §6. Tentative — same-day cycles, small sample —
  but the first evidence the delta worked. Keep watching.
- **The 4× "Validation — fitness-to-purpose — human sign-off must decide"
  recurring signal is structural, not a gap:** validation fitness is human-only
  by design (the sign-off contract), so this class will appear in §6 of every
  cycle and no process delta can or should remove it.
- **issue_332** (split close, no patch built) exposed nothing recurring — the
  split path produced a clean one-item §6 and a confirmable disposition.

## Process deltas
- None to this repo's spec template, ruleset, gates, or agent skills — agreed
  with the human. Every recurring finding is either already-filed upstream
  harness machinery (#401–#403, open) or structural (validation is human-only);
  a local change would paper over the former and mis-frame the latter.
- Ledger: "validation — fitness-to-purpose — human sign-off must decide" marked
  **structural** (by design, no delta possible) instead of open
  (process/act-ledger.json).

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, sandbox machinery per the template-vs-instance
  boundary): reviewer sandbox's read-only git index blocks stash-based C4
  red→green reproduction (issue_317 + issue_372 §6 C4) → filed
  https://github.com/eduralph/pdca-harness/issues/419
- Open Act item (carried from 2026-08-01, unchanged): triage rubric should state
  five buckets explicitly (issue_316 §10) → owner: next triage brief author;
  no triage-class brief ran this interval, so nothing to judge yet.

## How effectiveness will be judged
- C4 stash-reproduction NEEDS-HUMAN (317/372 class) should stop recurring once
  upstream #419 lands and reaches this instance; recurrence after it ships is
  the signal.
- T5 prior-art network class: if it stays absent over the next ~3 cycles, record
  the PR #25 delta as confirmed effective at the next review.
- #401–#403 classes: continued recurrence is expected while open; re-check their
  status next review before drawing any conclusion.

---

# Act review — 2026-08-01 — cycles considered: issue_311, issue_316, issue_331, issue_340, issue_341, issue_359, issue_368, issue_375, issue_376

First Act review of the instance — nine frozen bundles, all merged-wider.

## What the cycles' records exposed
- **T5 prior-art check unresolvable — 6 of 9 cycles** (311, 316, 340, 359, 375,
  376 §6): the codex reviewer sandbox cannot reach `api.github.com`, so "confirm
  no closed/rejected work duplicates this" lands in §6 every time (the ledger's
  open recurring signal). Root cause: upstream pdca-harness#277 closed COMPLETED
  via PR #287, but the fix is an **opt-in** (`[leaves.sandbox] network_access`)
  this instance had never enabled — `pdca.toml` still carried it commented out.
- **T4 contribcheck vacuous/unreproducible at Check — 9 of 9 cycles** (§6
  everywhere; named by issue_341 §10): contribcheck is default-open before the
  publish artifacts exist (by design, re-gated at publish per harness #339), but
  the Check matrix records a plain green PASS the reviewer cannot reproduce, so
  it is escalated every cycle.
- **T3 advisory red on the synthetic `issue_500/split-proposal.md` fixture —
  6 of 9 cycles** (311, 331, 340, 341, 368, 376): a pre-existing driver-suite
  fixture flake, unrelated to any bundle's patch, at a transient `/tmp` path
  nobody can inspect; issue_311 §10 additionally showed the T3 evidence
  extractor capturing arbitrary fixture stdout as its evidence line.
- **T2/T3 oracles absent from the reviewer sandbox — 4 of 9 cycles** (331, 341,
  368, 375 §6): the gate runners the frozen records name
  (`engine/scripts/run-docs-check.sh`, `run-suite.sh`) are not in the reviewer's
  permitted target; issue_375 §10 also noted no preflight checks the sandbox
  interior (doctor checks the host).
- **One-off (issue_331 §10):** the deliberate-abandon escape hatch shipped as a
  raw `python3 .claude/hooks/handoff_guard.py --abandon` invocation — should be
  a rendered `/abandon` slash command.
- **One-offs (issue_316):** §10 — the triage rubric's "one of four" wording vs
  an accepted 5th (unclassified-remainder) bucket caused a sign-off ruling;
  §6 C5 — recurrence identity is keyword-derived (`triage.py:108`), so synonyms
  split what should be one signal.

## Process deltas
- Gates/config (this repo): enabled `[leaves.sandbox]` `network_access = true`
  (pdca.toml:676–677) so the codex reviewer leaf can reach `api.github.com` for
  the T5 closed/rejected-PR prior-art check. Trade-off accepted with the human:
  the codex network grant opens the network layer for every command in that
  leaf (no per-domain scoping); filesystem confinement unchanged. Shipped as
  draft PR https://github.com/eduralph/pdca-pdca/pull/25 (human marks
  ready/merges). Ledger signal "t5 judgment — confirm no closed or rejected"
  marked applied.
- No spec-template, ruleset, or agent-skill delta warranted this review — the
  remaining findings are harness-machinery issues, routed upstream below rather
  than papered over locally.

## Follow-ups routed (not process deltas — work handed to an owner)
- Harness/driver issue (upstream, template machinery): Check-matrix reporting of
  a default-open T4 as PASS → filed
  https://github.com/eduralph/pdca-harness/issues/401
- Harness/driver issue (upstream): `issue_500/split-proposal.md` suite-fixture
  flake + T3 evidence extractor capturing arbitrary fixture stdout → filed
  https://github.com/eduralph/pdca-harness/issues/402
- Harness/driver issue (upstream): reviewer sandbox lacks the T2/T3 gate
  oracles; no sandbox-interior preflight → filed
  https://github.com/eduralph/pdca-harness/issues/403
- Harness/driver issue (upstream, follow-up on open #331): render an `/abandon`
  slash command wrapping the handoff-guard escape hatch → filed
  https://github.com/eduralph/pdca-harness/issues/404
- Open Act item: triage rubric should state five buckets explicitly (issue_316
  §10) → owner: next triage brief author; revisit next review.
- Design issue (routed to human to schedule, outside the cycle): triage
  recurrence-identity representation — broad class vs class+keyword vs semantic
  slug (issue_316 §6 C5, `template/src/pdca_harness/triage.py:108`). Needs a
  design decision, not a bug fix; no brief authored.

## How effectiveness will be judged
- The T5 "confirm no closed or rejected work" NEEDS-HUMAN class should stop
  recurring once PR #25 merges — the ledger will flag the signal as
  likely-ineffective if it recurs after 2026-08-01.
- T4/T3/oracle §6 noise should drop as upstream #401–#403 land and reach this
  instance via `copier update`; if the same classes recur over the next ~3
  cycles with the issues still open, that is expected — recurrence *after* they
  ship is the signal to watch.

---

