# Build notes — #541 (no dead attempt's artifact harvested as a live one's)

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`) on top of child-1's accepted result
(`480fa6b pdca-integrate: issue_540`). All `path:line` citations below are **post-patch**
line numbers in that worktree unless marked "base".

## What the change is

One new owner, `leaves._LeafHarvest` (`template/src/pdca_harness/leaves.py:781`), holds the
artifact path a retried leaf writes to, for the whole retry loop. The three harvest sites
construct one and call `.run(...)`:

* reviewer — `leaves.py:2744` (was `if produced.exists(): shutil.copy2(...)` at base
  `leaves.py:2592-2596`);
* Check advisory — `leaves.py:3099` (base `leaves.py:2926-2929`);
* plan advisory — `leaves.py:3402` (base `leaves.py:3227-3230`).

`_invoke_leaf_resilient` gains one optional parameter, `harvest` (`leaves.py:682`), and two
call-outs:

* after each failed attempt's record is appended, `records.append(harvest.withdraw(attempt))`
  (`leaves.py:751`) — placed **before** the transient/stop-rule test at `leaves.py:753-754`, so
  the *last* attempt's residue is preserved exactly like every earlier one's;
* on the success branch, `harvest.leaf_succeeded("".join(records))` (`leaves.py:740`)
  immediately before #540's `error_log.unlink()` — the owner keeps the dead attempts'
  account in hand because the log is about to be removed.

`withdraw()` (`leaves.py:843`) reads what the dying attempt left, **unlinks it**, and returns
it quoted through `state.neutralize_leaf_text` as that attempt's record block. `run()`
(`leaves.py:820`) then files the live attempt's own file, or degrades. `_preserve()`
(`leaves.py:878`) writes the account back into the bundle's `*.error.log` on the degrade path
only, closed with `_WITHDRAWN_TRAILER` (`leaves.py:777`) — no settlement marker, so
`state.leaf_ran_and_failed` stays False and every #540 reader treats it exactly as an absent
log (the leaf may be re-run, which is the remedy).

New failure class `_FAIL_UNOWNED` (`leaves.py:2770`) → new marker
`assemble.LEAF_STATUS_UNOWNED` (`assemble.py:92`) → new §6 label (`assemble.py:99`), with
prose at `leaves.py:2850`.

## Why each criterion is met, and the two judgment calls

**1 — no dead attempt's artifact filed, at all three sites.** The residue is removed from the
path as its author dies, so by the time any harvest runs, anything present was written by the
live attempt. Proven at all three sites by
`test_no_site_files_a_dead_attempts_artifact_as_a_live_ones` (a subTest per site) and, for the
un-removable case, `test_a_residue_that_cannot_be_withdrawn_is_refused_at_every_site`.
`test_all_three_sites_go_through_the_one_owner` swaps the owner for a recording subclass and
drives each site, so "the fix landed at two of three" fails mechanically, not by review.

**2 — the dead attempt's text is preserved, not merely deleted.** JUDGMENT CALL (the one place
this child touches child-1's ground): #540 ruled that a leaf which SUCCEEDS leaves no error log
(`leaves.py:733-741`, its test at base `template/tests/test_attempt_ownership.py:275-288`), and
the brief puts "the record half" out of scope "except where this child's own change makes one
false". A withdrawn residue flushed mid-retry would be deleted by that unlink — destroying the
very text criterion 2 protects. I did **not** revisit #540's rule; I scoped the preservation to
exactly the condition criterion 2 states — *"a real verdict must not be destroyed **while the
operator is told none was produced**"*. So:

* live attempt files its own artifact ⇒ log cleared, byte-identical to #540
  (`test_the_live_attempts_own_artifact_is_harvested_at_every_site` asserts the log is absent);
* nothing filed (empty, or refused) ⇒ `_preserve()` puts the account back, and the placeholder's
  "See `…error.log`" ref (`leaves.py:2860-2862`) then points at something that exists.

Rejected alternative: keep the log unconditionally. Cost is not size (it is ~2 lines either
way) — it is that it contradicts an accepted result: a bundle would carry
`check-review.error.log` beside a **real** `check-review.md`, which
`test_attempt_ownership.py:288` names "a lie". Also rejected: a new `*.residue.log` file — the
criterion says `*.error.log`, and a second post-mortem path is a fifth reader for the next
child to keep in step.

**3 — today's behaviour where nothing changed.** `test_the_live_attempts_own_artifact_is_
harvested_at_every_site` (live text lands verbatim) and
`test_a_leaf_that_exits_0_writing_nothing_still_degrades_as_today` (placeholder + the existing
`human-empty` marker + no error log). Both stay GREEN on the red leg — deliberately: they are
regression guards for the unchanged path, and the defect legs carry the red.

**4 — the leaf-status label tells the truth.** The refusal is a run whose last attempt
**exited 0**, so routing it to `LEAF_STATUS_INFRA` would print "leaf did not run (transient
infra — safe to re-run)" about a run that did — the falsehood the brief names at base
`assemble.py:84-85`. It gets its own status + label instead (`assemble.py:92,99`), and the
label is asserted from §6 in `test_the_label_never_says_a_run_that_exited_0_did_not_run`
(never starts with "leaf did not run", says "exited 0", stays `HUMAN` so #264 auto-iterate can
never fire on it). One defensive addition at `assemble.py:190-191`: a marker present but
**unrecognised** now takes a generic label instead of `""`. Without it, adding a status in
`leaves` and forgetting the label in `assemble` silently drops the HUMAN forcing and hands an
empty artifact to auto-iterate as if a leaf had reviewed the diff — the same twin-blindness
this child exists to remove, one module over. 4 lines, guarded by
`test_an_unrecognised_status_is_still_a_placeholder_never_a_verdict`.

**5 — the retry contract is NOT narrowed.** Implemented exactly as the brief rules: a residue
that cannot be withdrawn sets `_unowned` (`leaves.py:899`) and the loop continues untouched —
no exception, no early return, attempt count / transient rule / backoff schedule unchanged
(`leaves.py:843-867` contains no `raise`). The refusal is paid later, on the success branch
(`leaves.py:836-841`). `test_an_unwithdrawable_residue_does_not_narrow_the_retry_contract`
is the `_runs() == 3` analogue of `test_leaf_resilience.py:62`, driven through
`_run_review_sandboxed`. Note the refusal is deliberately conservative: if the live attempt
wrote its own file *and* an older residue could not be removed, we still refuse — we cannot
tell the two apart, and "no verdict + a §6 row" is the only safe direction.

**6 — one implementation, not three copies.** The three sites now hold only what differs (the
two paths, their own placeholder callback, their own §6 prose). Countable: 25 hand-copied
lines deleted across the three sites (9 + 8 + 8 in the diff), replaced by three ~7-line
constructions and one shared owner. I kept `failed_reason` / `empty_reason` as per-site
strings rather than deriving them, so the placeholder prose the shipped tests and operators
read is unchanged word-for-word ("reviewer produced no check-review.md" vs "produced no
artifact").

## Ruled out

* **Making the harvest attempt-aware by stamping the artifact** (mtime/inode/hash captured
  before each attempt, compared after). It answers "did *this* attempt write it?" without
  removing anything — but it silently *keeps* the dead attempt's file at the path (criterion 2
  needs it preserved in the error log, so the read+quote is needed anyway) and it is
  defeated by a leaf that rewrites the same bytes. Same size, weaker.
* **Fresh sandbox per attempt.** It would fix criterion 1 outright, but the brief puts "a
  lane/worktree reset between attempts" out of scope, and it discards the mid-retry
  observability #540 just built.
* **Reusing `_FAIL_SUBSTANTIVE` for the refusal** (0 new lines). Its §6 label is "leaf produced
  no usable verdict (needs a human)" — which asserts something about the *verdict* when the
  actual fact is about attribution, and it gives the operator no hint that the remedy is
  clearing the residue and re-running. Criterion 4 asks the label to be true for every run the
  classification can now describe; this one costs 3 lines in `leaves` + 4 in `assemble`.
* **A structural/source-scanning test for criterion 6** (e.g. counting `shutil.copy2` in
  `leaves.py`). Brittle against formatting; replaced by the recording-subclass drive, which
  fails if any site stops going through the owner.

## Refuting my own test (forced check)

* **(a) Genuine red?** YES — proven by the project's own gate, not by hand:
  `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
  `== C4 green leg … Ran 9 tests … OK`, then with the production hunks reverted
  `Ran 9 tests … FAILED (failures=9, errors=2)` → `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`. The red leg fails at **all three** sites by name
  (`(site='review')`, `(site='advisory')`, `(site='plan-advisory')`) with
  `AssertionError: 'DEAD-ATTEMPT-VERDICT-b3f1' unexpectedly found in …` — i.e. the base really
  does file the dead attempt's verdict. The module still IMPORTED on the red leg (9 tests ran,
  no `unittest.loader._FailedTest`), so this is a red, not a C4 `PDCA-UNVERIFIABLE`.
* **(b) Production path?** YES — every leg calls the real site entry points
  (`leaves._run_review_sandboxed`, `leaves._run_advisory_sandboxed`,
  `leaves._run_plan_advisory_sandboxed`) with a real `LeafConfig(mode="command", family="claude")`
  whose argv is a Python interpreter, so the real spawn (`progress.run_with_heartbeat`), the
  real stream/transient classification, the real sandbox and the real retry loop all run. No
  `_invoke` substitution, no re-implementation. The only patched thing is `leaves.time` —
  a stand-in that delegates every attribute to the real `time` and no-ops `sleep`, so the
  shipped 3-attempt budget and backoff *schedule* are exercised without 12s of wall clock
  (`test_attempt_harvest.py:109-121`).
* **(c) Fixture includes the fault?** YES — the failing element is the fixture: the stub leaf
  itself writes the truncated verdict into the sandbox and then dies at invocation (stderr,
  no stdout ⇒ the genuine transient signal), and the un-withdrawable case is produced by the
  dying leaf doing `os.chmod(".", 0o500)` on its own sandbox — a real EACCES from the real
  kernel, not a mocked `unlink`. Nothing is curated out: the harvest sees exactly the sandbox
  the dead attempt left behind.

## Runner / environment notes

* Runner used: the project's own gates — `./engine/scripts/run-verify.sh` (C4, red→green) and
  `./engine/scripts/run-suite.sh` (T3): `PDCA-EVIDENCE: root suite OK, driver suite OK`
  (1812 tests). `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` (C5):
  `1 added driver-suite test(s) import the production package 'pdca_harness'`.
* Headless-safe: stdlib + `pdca_harness` only; the "leaf" is `sys.executable -c`.
* Two legs `skipIf(os.geteuid() == 0)`: as root the read-only directory does not refuse the
  unlink, so the refusal cannot be produced. Non-root (local + GH `ubuntu-latest` runner) runs
  them; the criterion-1/2 legs do not depend on that and never skip.
* No external dependency beyond the base toolchain — the brief's `External dependencies: none`
  held.
* Target repo has no formatter/linter config and no repo hooks (`.pre-commit-config.yaml`,
  `ruff`/`flake8`/`pyproject` lint sections all absent; `CONTRIBUTING.md:21-27` states the
  discipline as "keep the offline suite green"). Added lines stay ≤ 97 chars, matching the
  files' existing width.
* `git commit -s` (DCO) is publish's step, not mine; no PR opened, nothing pushed.
