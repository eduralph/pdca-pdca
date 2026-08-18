# Build notes — #536 attempt-owned leaf records and harvests (iteration 4)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All `path:line` below are the
patched worktree (`$PDCA_WORKTREE`), i.e. base + `patch.diff`.

## What this iteration is

Round 3's sign-off rejected **on the findings, not on approach or slicing** — "the
mechanism is holding up … Same slice, same design. Close the items below and keep the diff
from growing." So this is iteration-v3's patch plus a **focused delta** that closes its
four carry-forward items. The delta is 85 added / 34 removed lines in `leaves.py` and
121 / 10 in the test file; nothing else in the design moved.

Diff shape (base → now): `assemble.py` 18, `driver.py` 32, `leaves.py` 430,
`state.py` 6, `template/tests/test_attempt_ownership.py` +822 (new file).

## Carry-forward item 1 — the withdraw-before-persist kill window

**Was:** `_withdraw_residue` read the dead attempt's text into memory *and* unlinked the
artifact, and only afterwards did the caller persist the record. A kill in that gap loses
**both** the text and the account — the exact no-artifact/no-account state this slice
exists to remove.

**Now** (`leaves.py:752-773`), exactly the ordering the sign-off prescribed:

1. `_residue_record(artifact, attempt)` (`leaves.py:981`) — **reads and quotes only**;
2. `_write_attempt_records(..., in_flight=may_retry)` (`:763`) with
   `may_retry = transient and attempt < attempts` (`:762`) — the record, residue included,
   is on disk;
3. `_withdraw_residue(artifact, attempt)` (`:1014`) — **unlinks only**, returns `owned`;
4. `if may_retry and not owned:` re-flush `in_flight=False` (`:768-769`) — a path the
   wrapper no longer owns ends the run, so the account just written is final after all;
5. the stop rule `not (may_retry and recorded and owned)` (`:773`).

The fail-closed stop on a refused withdrawal is unchanged in behaviour (`:1014-1035`), and
the retry set is untouched — `may_retry`'s transient/attempt terms are the shipped rule
verbatim, with the two extra *stop* conditions only ever narrowing it.

Splitting the old function in two (rather than passing a flag) is what makes the ordering
legible at the call site: the reviewer of this diff can see "quote → persist → unlink" in
five consecutive lines instead of reasoning about a parameter.

## Carry-forward item 2 — a stale in-flight marker beside a filed failure

**Was:** the three `err is not None` branches filed their `*_unavailable` placeholder and
relied on the loop's last `_write_attempt_records(..., in_flight=False)` having landed.
When *that* write is the one the filesystem refuses — after an earlier attempt's in-flight
write already landed — the log keeps a marker for a retry that will never come while a
"leaf failed" verdict sits in the bundle.

**Now:** `_settle_leaf_record(error_log)` in all three `err` branches —
`leaves.py:2854` (reviewer), `:3225` (advisory), `:3529` (plan-advisory) — mirroring the
`else` branches at `:2871` / `:3232` / `:3537`. Rationale recorded at the call site and in
the function docstring (`:925-946`).

**Why this end and not `_write_attempt_records`'s failure path** (the sign-off allowed
either): stripping the trailer inside the failed write would settle the account *before*
the outcome is filed, which is the one ordering this slice forbids — a kill between that
strip and the placeholder leaves an interrupted Check reading "ran and failed", the
reviewer is never recovered, and a bundle can reach sign-off with no review of the diff.
It is also wrong for the *success* path caller (`:746`), where an in-flight log is the
intended state until the harvest lands. Cost of the chosen fix: 3 call lines + 6 comment
lines; the alternative would have needed a condition distinguishing those two callers and
would have re-opened the window it closed.

## Carry-forward item 3 — two claim-accuracy defects (prose/rationale only)

**3a. `_FAIL_TRANSIENT`'s account** (`leaves.py:2964-2969`, class comment `:2877`). Two
runs now reach this class: one whose every attempt exited non-zero with no output, and one
whose retry *came back alive and produced nothing* (`_empty_run_class`, `:2900`). The
shipped sentence said "retries did not recover", which is false of the second — the class
(`infra-empty`) and the action ("safe to re-run") were right, the account was not. Widened
rather than given a fourth class: a new class would need its own `assemble` mapping and §6
row, which is a bigger change than the sentence being wrong warrants.

The test that asserted only the class and `"safe to re-run"` (true of the wrong sentence
too) is strengthened at `tests/test_attempt_ownership.py:355-374`: it now pins
`self._runs() == 2` (attempt 2 *did* recover), asserts the false account is absent, and
asserts the sentence that describes this run's actual shape.

**3b. the settle's stated justification.** "Otherwise a leaf that gave up looks recoverable
forever and is re-run on every `advance`" is unwarranted — every reader short-circuits on
the filed placeholder first (`review_never_ran` tests `check-review.md` at
`leaves.py:2429`; `only_missing` tests the advisory artifact at `:3175-3176`). Restated at
`leaves.py:941-949` as what it is: **archive hygiene**, plus the genuinely load-bearing
half — *settle after the outcome is filed, never before* — with an explicit warning that
reading it as a recovery guard is what would tempt a later maintainer to move it before the
write, the one place it does damage. Same correction in the two test docstrings
(`tests/test_attempt_ownership.py:712-723` and the advisory comment at `:600-603`).

## Tests: what was added, and what each one binds

Four new cases plus one strengthened, all through pre-existing entry points
(`leaves._invoke_leaf_resilient`, `leaves._run_review_sandboxed`,
`leaves._run_advisory_sandboxed`, `leaves._run_plan_advisory_sandboxed`,
`leaves.review_never_ran`, `assemble._missing_review_text`); the module still imports only
pre-existing API (`from pdca_harness import assemble, leaves, state` + `config`), so the C4
red leg loads it with the production hunks reverted (no `PDCA-UNVERIFIABLE` import trap).

| Test | Binds |
|---|---|
| `test_a_kill_at_the_withdrawal_loses_neither_the_text_nor_the_account` (`:508`) | item 1 — the persist-before-unlink ordering |
| `test_a_refused_withdrawal_leaves_no_retry_pending_in_the_account` (`:475`) | item 1 — the `in_flight=False` re-flush after a refused withdrawal |
| `test_a_failed_flush_leaves_no_stale_marker_beside_a_filed_failure` (`:730`) | item 2 — the reviewer `err`-branch settle |
| `test_a_failed_flush_leaves_no_stale_marker_at_either_site` (`:608`, parametrized) | item 2 — the advisory + plan-advisory `err`-branch settles |
| `test_the_preserved_death_is_filed_as_the_infra_death_it_was` (`:355`, strengthened) | item 3a — the sentence, not just the class |

Both new "failed flush" cases refuse the write **whose body contains `attempt 2`**, so
attempt 1's in-flight write lands first — the gap the previous write-failure test could not
create (it refused every write from attempt 1, so nothing landed to leave a stale marker).

## Refutation — the three questions, answered with evidence

**(a) Genuine red?** Yes, twice over, both through the project's own C4 gate
(`./engine/scripts/run-verify.sh`, which reverts only the production hunks and keeps every
`template/tests/*` hunk):

- **vs. the base** (`acb214a`): green leg `Ran 26 tests … OK`; red leg
  `Ran 26 tests … FAILED (failures=19, errors=4)` → `PDCA-EVIDENCE: C4 PASS`.
- **vs. iteration-v3** (delta patch v3→now fed to the same gate): green `Ran 26 … OK`; red
  leg fails exactly the four legs this iteration adds —
  `test_a_kill_at_the_withdrawal…`, `test_a_failed_flush…_beside_a_filed_failure`,
  `test_a_failed_flush…_at_either_site` (both subtests) and
  `test_the_preserved_death…` → `FAILED (failures=5)`. So each carry-forward item is red
  against the *previous attempt*, not merely against the base.

Targeted mutations of the new lines (green leg run under each, then reverted):

- **M1** disable the `in_flight=False` re-flush (`leaves.py:768-769`) →
  `FAILED (failures=1)`: `test_a_refused_withdrawal_leaves_no_retry_pending_in_the_account`.
- **M2** delete all three `err`-branch settles (`:2854`, `:3225`, `:3529`) →
  `FAILED (failures=3)`: the reviewer case and *both* advisory subtests, i.e. each of the
  three calls is individually bound (deleting any one reddens its own site's case).
- The ordering swap (persist ↔ withdraw) is M-equivalent to the v3 delta red leg above.

**(b) Production path?** Yes. Every case drives the shipped functions in
`pdca_harness.leaves` / `pdca_harness.assemble`; the only stand-ins are (i) the "leaf"
itself — a real `python3` child process spawned through `_invoke` →
`progress.run_with_heartbeat`, exactly as a vendor CLI is — and (ii) `time.sleep` for the
retry **backoff** only (`_skip_backoff` passes anything < 1s through, so `progress`'s own
poll still runs). The attempt budget, the retry rule, the flush, the withdrawal, the
harvest and the discriminators are all the production ones. The C5 gate agrees:
`PDCA-EVIDENCE: 1 added driver-suite test(s) import the production package 'pdca_harness'`.

**(c) Fixture includes the fault?** Yes. The failing element is present in every case, not
curated out: the dead attempt's *actual file* is written into the sandbox by the child and
then read back out of the bundle's `*.error.log`; the kill is raised **inside the
production write/unlink** (`_Kill(BaseException)`, so no `except Exception` in the harness
can swallow it) and the assertions read what that kill left on disk; the write/unlink
refusals are raised from `Path.write_text` / `Path.unlink` themselves, i.e. at the syscall
boundary the real failure occurs at. The canonical transient death (`FIRST_WRITES=""` —
attempt 1 dies before writing anything) is exercised alongside the truncated-verdict shape,
because a rule keyed on a withdrawn *file* would miss it entirely. Each injected failure is
also **pinned to have fired**: both stale-marker cases assert the run cost exactly 2
attempts (`tests/test_attempt_ownership.py:626-627`, `:753`), so a refusal that silently
stopped matching — leaving the loop to end with an ordinary settled flush — fails the case
instead of passing it vacuously.

## Gates run (project runners, not hand-rolled)

- `./engine/scripts/run-verify.sh` — `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`.
- `./engine/scripts/run-suite.sh` — `root suite OK` (7 tests), `driver suite OK`
  (**1784 tests**, 2 skipped). `template/tests/test_leaf_resilience.py` is **untouched**
  (`git status` shows only the four production files + the new test) and green inside that run.
- `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` — C5 evidence above.
- `./engine/scripts/run-docs-check.sh` — `docs lint clean, site render + link audit clean`.

Commit-readiness: the target ships **no** formatter/linter config (no `pyproject.toml`,
`.flake8`, `.pre-commit-config.yaml`; CI is render-check / docs-check /
require-linked-issue). CONTRIBUTING's discipline is "one logical change per PR", "ships
with the means to verify it", "keep the offline suite green" — all satisfied. Patch has no
trailing whitespace and no added line over 96 columns (the file's own norm). DCO sign-off
is publish's step.

## Scope held (what I deliberately did NOT do)

- **The staleness clear** at `leaves.py:718` — left alone. Criterion (vi) freezes it and
  three sign-offs have now adjudicated the "recovery re-run deletes the preserved verdict"
  interaction as a deliberate **Act** deferral. Unchanged from v3.
- **No `_harvest_leaf` refactor.** Closing item 2 by hand is 3 call lines + comments; the
  shared-helper refactor would rewrite three ~12-line harvest bodies (≈ 40 lines moved) in a
  patch already flagged oversized. Noted as an Act candidate, as the sign-off asked.
- **Untouched:** the retry set, `LeafError.transient`, `progress.py` (sibling #538), the
  builder path (`_do_build_command`, `do_build`, `_build_prompt`, `_stub_build`),
  `template/tests/test_leaf_resilience.py`, `template/tests/fixtures/`, and
  `test_terminal_error_classification.py` (both #533's).

## Known limitations / Act candidates (carried forward, not fixed here)

1. `assemble.py:85` labels the `infra-empty` §6 row "leaf did not run (transient infra —
   safe to re-run)". For the empty-run shape the *last* attempt did run (and produced
   nothing), so the label is loose — "nothing reviewed the diff" is what the INFRA marker
   means, which is true. Fixing the label would also require editing
   `template/tests/test_leaf_status.py:135`, i.e. a second test file in a patch the sign-off
   asked to keep from growing. Flagged rather than changed.
2. The verdict copy at the three harvests is still a non-atomic `shutil.copy2`, and
   `_atomic_write_text` can strand a `*.error.log.tmp.<pid>` sibling on a kill (inert: no
   `state.DOWNSTREAM_GLOBS` pattern claims it). Both were noted as Act candidates by the
   previous sign-off and are not hardened here.
3. A refused withdrawal now ends the run with a *settled* account before the placeholder is
   filed; a kill in that sliver leaves "ran and failed" with no placeholder — identical to
   the base's behaviour for a leaf that spends its attempts, and honest (the leaf did run
   and fail). This is the ordering the sign-off prescribed for item 1.

## External dependencies

None beyond the base toolchain (pure-stdlib Python ≥ 3.11 + git). Every leg is driven by a
stub "leaf" that is a Python interpreter — no vendor CLI, no API key, no network, no
container. Nothing was blocked; no NEEDS-HUMAN external dependency to declare.
