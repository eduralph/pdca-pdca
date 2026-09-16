# Build notes — #536 attempt-owned leaf records and harvests (iteration 5)

Target: `eduralph/pdca-harness` @ `main`, base `acb214a`. All `path:line` below are the
patched worktree (`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt-l0`), i.e.
base + `patch.diff`.

## What this iteration is

Round 4's sign-off: *"The slice and the design are right and have been stable for four
rounds … Same slice, same mechanism. Do NOT re-scope, do not split, do not refactor.
Close these three findings, all in code this patch introduced."* So this is
iteration-v4's patch plus a **focused delta** that closes those three findings and takes
the one optional item it offered. Nothing else in the design moved.

Size, measured three ways (`git apply --numstat` for the base-relative columns):

| file | v4 vs base (+/−) | now vs base (+/−) | this round |
|---|---|---|---|
| `template/src/pdca_harness/leaves.py` | 409 / 27 | 436 / 28 | **+37 / −11** |
| `template/tests/test_attempt_ownership.py` | 857 / 0 | 1044 / 0 | **+187** |
| `assemble.py`, `driver.py`, `state.py` | 41 / 15 | 41 / 15 | unchanged |

The last column is the direct v4→now diff (`git diff <v4 blob> <now blob> --numstat`), not
the difference of the two base-relative counts — rewriting a line v4 had *added* changes
the content without changing either count, so the base-relative figures under-report churn.
Of those 37 added `leaves.py` lines, **27 are docstring rationale** (this file's norm) and
**10 are code**, in 4 hunks in one function-family; no site was refactored.
The +187 test lines are 5 cases + 1 stand-in class — ~31 lines each including their
rationale docstrings, against the file's existing ~40 (857 lines / 21 cases), so the
additions are denser than what is already there rather than a new tier of verbosity.

## Finding 1 — a discriminator that could raise instead of answer

**Was** (`leaves.py:919` region): `leaf_run_incomplete` read the log with
`read_text(encoding="utf-8")` under `except OSError`, while its own docstring promised
"absent or unreadable ⇒ False". A `UnicodeDecodeError` (a `ValueError`, not an `OSError`)
therefore escaped a discriminator that this patch put on `driver.advance`'s critical path
— the cycle aborts where it should degrade. The reachable route is this change's own
premise: a log the **pre-patch** non-atomic write left truncated mid-multibyte, read by
the new discriminator on the next `advance` after the upgrade.

**Now** — `leaves.py:919`: `read_text(encoding="utf-8", errors="replace")`, the defensive
read `_residue_record` already used (`:1027`), with the reasoning recorded at `:912-917`.

**Why `errors="replace"` and not `except (OSError, ValueError): return False`** — the
sign-off allowed either, and they are *not* equivalent: they answer differently for the
log that actually occurs. The trailer is ASCII the harness wrote on its own last line, so
a replacement anywhere in the body still leaves it readable ⇒ **the interrupted leaf is
recovered**. Degrading to `False` instead reads that same log as "ran and failed" ⇒ the
reviewer is retired and the bundle can reach sign-off with no review of the diff — the
exact failure this slice exists to remove, re-introduced through the error path. Mutation
**M8** below runs the alternative and the new case catches it, so the choice is pinned by
the suite, not by prose.

**Paired reader, same defect** — `_settle_leaf_record` (`leaves.py:977`) re-reads the same
file one call later, at the harvest, outside any `try`. Guarding only the first reader
would have moved the crash by one line, which is symptom-guarding; `except (OSError,
ValueError)` closes it (the file already uses that exact tuple twice: `:463`, `:1818`).
It **returns** rather than rewriting with replacement characters: settling by *damaging*
the preserved evidence is the one thing this slice will not do. Consequence, deliberate:
an undecodable log keeps its marker after the outcome is filed. Inert — every reader
short-circuits on the placeholder first (`review_never_ran` tests `check-review.md`,
`:2456`). Cost of the alternative: a lossy in-place rewrite of the operator's only copy of
a dead attempt's verdict, for archive tidiness.

## Finding 2 — an unbounded read inside the handler that must not raise

**Was** (`leaves.py:1027` region): `_residue_record` read the **whole** dead artifact into
the driver and applied the `_RESIDUE_KEEP` bound afterwards, under `except OSError`. It is
called from inside the `except` block of "a failed leaf must never crash the cycle"
(`:759-760`, handler at `:750`) — where a raise is *no longer covered by that handler*:
it escapes `_invoke_leaf_resilient` and the caller files neither placeholder nor error
log. How big that file is, is the dead leaf's decision (a runaway loop writes gigabytes),
so this put the leaf in charge of an allocation made in the one place that cannot afford
one. The same escape reaches the two advisory callers, which have no `try` of their own
(`:2863` reviewer, `:3241` advisory, `:3546` plan-advisory — all three rely on the wrapper
*returning* the failure rather than raising).

**Now** — `leaves.py:1026-1031`: bounded read (`fh.read(_RESIDUE_KEEP + 1)` — the `+1` is
what tells it the file was longer) and `except Exception` with a `noqa: BLE001` and the
reason at `:1015-1023`. Both halves are needed and both are individually bound (M3, M5).

**Truncation notice reworded** (`:1032`): `… truncated ({len(text)} characters in all)` →
`… truncated (the first 20000 characters)`. The old count *required* the unbounded read
that is the defect. Rejected alternative: keep a size by adding `size =
artifact.stat().st_size` in the same `try` and printing it — 3 extra lines
(`size` assignment, a `text, size = …` failure branch, a wrapped f-string) to report a
number in **bytes** where the old message said **characters**, i.e. a different quantity
under the old wording. In a slice whose invariant is "never file a false account", a
cheaper-but-approximate figure is worse than an exact statement of what the reader has.

## Finding 3 — the second recovery discriminator, exercised by nothing

**Was:** `run_advisory_leaves(only_missing=True)` (`leaves.py:3202-3203`) is the second of
the two #369 discriminators criterion (v) names, and reverting it to the base's bare
`advisory_error_log(...).exists()` left the whole driver suite green.

**Now:** production unchanged (it was already correct); the hole was in the tests.
`AnInterruptedAdvisoryLeafIsRecoveredToo`
(`template/tests/test_attempt_ownership.py:975`) drives the production resume pass end to
end with a real `python3` child leaf, on **both** legs:

* `:1015` an in-flight log + no artifact ⇒ the leaf **is** re-run (`_runs() == 1`, and the
  bundle gains an account of it). The log's bytes are the production wrapper's own, taken
  while a retry was pending (`_probe_attempts`), not hand-written;
* `:1028` a spent log (written by `_invoke_leaf_resilient` itself) ⇒ still **not** re-run
  (`_runs() == 0`), so the fix cannot be "always run" in disguise.

M1/M2 below show each leg catches its own mutation, including the exact revert the
sign-off performed.

## Optional item taken — the no-output fallback (`leaves.py:1074`)

`_format_leaf_attempt` defanged only `tail`; the `(no output captured) …` fallback quotes
the exception, whose text carries the configured argv (`LeafError`) or the binary path
(`FileNotFoundError`). One line: the defang now wraps the whole body expression.

**Not separately tested, and here is why** rather than an omission: that body is a single
line and `repr` escapes newlines, so the fallback can never place the marker **alone on a
final line** — the shape `leaf_run_incomplete` matches. It closes the channel by
construction; there is no honest behavioural red for it. M7 shows the combined defang is
bound by the existing stderr-impersonation case, so the call cannot be deleted silently.
(The code-review lens had judged this outside criterion (iv)'s two named channels and
declined to gate on it; the sign-off marked it optional.)

## Refutation — the three questions, answered with evidence

**(a) Genuine red?** Yes, at both levels, both through the project's own C4 gate
(`./engine/scripts/run-verify.sh`, which reverts only the production hunks and keeps every
`template/tests/*` hunk):

* **vs. the base** (`acb214a`): green leg `Ran 31 tests … OK`; red leg
  `Ran 31 tests … FAILED (failures=23, errors=4)` → `PDCA-EVIDENCE: C4 PASS`.
* **vs. iteration-v4** — the delta is what this round is judged on, so v4's `leaves.py`
  was put back under this round's tests (`git checkout acb214a -- leaves.py` +
  `git apply --include=…/leaves.py iteration-v4/patch.diff`) and the suite re-run through
  `./engine/scripts/run-suite.sh`: `FAILED (errors=3)` — exactly
  `test_a_runaway_residue_is_quoted_without_being_read_whole`,
  `test_a_residue_the_read_fails_on_still_leaves_a_placeholder_and_an_account` and
  `test_an_undecodable_log_is_answered_not_raised_out_of_the_discriminator`. The two
  finding-3 cases are green there **by design** (v4 already had that production line; the
  finding was that nothing tested it) — they are bound by mutation instead, below.

Mutations of *this round's* lines (each applied alone to the green tree, suite re-run,
then reverted; every one caught, by exactly the case that owns it):

| # | mutation | caught by |
|---|---|---|
| M1 | `only_missing` back to the base's bare `.exists()` (the sign-off's own revert) | `…_the_death_window_interrupted_is_re_run` |
| M2 | drop the error-log half of the skip entirely (never skip) | `…_that_spent_its_attempts_is_still_not_re_run` |
| M3 | `fh.read(_RESIDUE_KEEP + 1)` → `fh.read()` (guard kept) | `…_runaway_residue_is_quoted_without_being_read_whole` |
| M4 | `errors="replace"` → strict decode | `…_undecodable_log_is_answered_not_raised…` |
| M5 | `_residue_record`'s `except Exception` → `except OSError` | `…_residue_the_read_fails_on_still_leaves_a_placeholder…` |
| M6 | `_settle_leaf_record`'s `except (OSError, ValueError)` → `except OSError` | `…_undecodable_log_is_answered_not_raised…` |
| M7 | drop `_defang_in_flight` from `_format_leaf_attempt` | `…_leaf_whose_stderr_quotes_the_trailer_is_still_read_as_spent` |
| M8 | the *other* allowed fix: strict decode + `except (OSError, ValueError) → False` | `…_undecodable_log_is_answered_not_raised…` |

**(b) Production path?** Yes. Every case drives shipped functions in `pdca_harness.leaves`
/ `pdca_harness.assemble` through pre-existing entry points (`_invoke_leaf_resilient`,
`_run_review_sandboxed`, `_run_advisory_sandboxed`, `_run_plan_advisory_sandboxed`,
`run_advisory_leaves`, `review_never_ran`, `assemble._missing_review_text`). The new
advisory class drives the **whole** resume pass — `run_advisory_leaves(only_missing=True)`
→ `_advisory_applies` → `_select_advisory` → `_run_advisory_sandboxed` → `_invoke` →
`progress.run_with_heartbeat` → a real `python3` child. The only stand-ins are the "leaf"
itself (a real child process, exactly as a vendor CLI is), `time.sleep` for the retry
backoff, and the **file object** in the two residue cases — the production
`_residue_record` runs unmodified; what is stood in for is the thing it reads *from*.
Module-level imports are still pre-existing API only (`assemble`, `leaves`, `state`,
`config`), so the C4 red leg loads the file with the production hunks reverted (no
`PDCA-UNVERIFIABLE` import trap). C5 agrees: `PDCA-EVIDENCE: 1 added driver-suite test(s)
import the production package 'pdca_harness'`.

**(c) Fixture includes the fault?** Yes, and each injected fault is **pinned to have
fired** — the failure mode this iteration's own review would look for:

* the undecodable log's corruption is asserted to be real before it is used
  (`assertRaises(UnicodeDecodeError)` on the bytes, `test_attempt_ownership.py:940`), so a
  future edit that makes the splice a no-op fails the case instead of passing it;
* the runaway read records every interception and the case asserts it happened
  (`:560`) — without that pin, a production change that stopped reading the artifact
  through `Path.open` would leave the case green and asserting nothing about the bound;
* the refused read likewise (`:589`);
* both advisory legs assert the invocation **count** (`_runs()`), so a resume that silently
  stopped running anything cannot pass as a skip, nor a skip as a run;
* the dead attempt's artifact is written by the **child process** into the sandbox and read
  back out of the bundle's `*.error.log`; the kills are raised inside the production
  write/unlink (`_Kill(BaseException)`, so no `except Exception` can swallow them).

## Gates run (project runners, not hand-rolled)

* `./engine/scripts/run-verify.sh` — `PDCA-EVIDENCE: C4 PASS — red without the fix, green
  with it` (green 31 tests OK; red 23 failures + 4 errors).
* `./engine/scripts/run-suite.sh` — `PDCA-EVIDENCE: root suite OK, driver suite OK`
  (7 tests; **1789 tests**, 2 skipped — v4's 1784 plus this round's 5).
* `PDCA_PROD_PACKAGE=pdca_harness ./engine/scripts/run-prod-path.py` — C5 evidence above.
* `./engine/scripts/run-docs-check.sh` — `docs lint clean, site render + link audit clean`.

`template/tests/test_leaf_resilience.py` is **untouched** (`git status` shows only the four
production files + the new test file) and green inside the 1789.

Commit-readiness: the target ships **no** formatter/linter config (no `pyproject.toml`,
`.flake8`, `.pre-commit-config.yaml`; CI is render-check / docs-check /
require-linked-issue). Checked by hand over every touched file: no trailing whitespace, and
**no added line exceeds 96 columns** (the file's own norm; the 12 over-length lines in
`leaves.py` are all pre-existing). DCO sign-off is publish's step.

## Prior art / merge check (material for the open T5 §6 item)

The two routine NEEDS-HUMAN items from round 4 (T5 prior-art overlap on the four
non-`leaves.py` paths; fitness-to-purpose on re-running an interrupted reviewer) remain the
human's at sign-off. Evidence gathered so the first is cheap to adjudicate — open PRs on
the target and the files they touch (`gh pr list --json files`):

* **#519** merge.py/config.py, **#521** gates.py + `run-verify.sh`, **#522** flow.py,
  **#523** docs, **#525** root `tests/` — **no** overlap with `assemble.py`, `driver.py`,
  `state.py` or `template/tests/`;
* **#520** `leaves.py` at `do_split` (`@@ -1594`, `@@ -1611`) — distant;
* **#524** `leaves.py` inserting after `_format_leaf_attempt` (`@@ -730,6 +730,143`) —
  textually adjacent to this round's `_format_leaf_attempt` edit. Checked, not assumed:
  `gh pr diff 524 | git apply -3 --include=…/leaves.py` over this patch reports
  *"Applied patch to 'template/src/pdca_harness/leaves.py' cleanly"*. No conflict in
  either order.

## Scope held (what I deliberately did NOT do)

* **No re-scope, no split, no refactor**, as the sign-off directed. The shared
  `_harvest_leaf` helper for the three near-identical harvest sites stays an **Act**
  candidate.
* **The staleness clear** (`leaves.py:718`) — untouched. Criterion (vi) freezes it and four
  sign-offs have adjudicated the "a recovery re-run deletes the preserved verdict"
  interaction as a deliberate Act deferral.
* **Untouched:** the retry set, `LeafError.transient`, `progress.py` (sibling #538), the
  builder path (`_do_build_command`, `do_build`, `_build_prompt`, `_stub_build`),
  `template/tests/test_leaf_resilience.py`, `template/tests/fixtures/` and
  `test_terminal_error_classification.py` (both #533's).

## Known limitations / Act candidates (carried forward, not fixed here)

1. An **undecodable** log is left with its in-flight marker after its outcome is filed
   (`_settle_leaf_record` returns rather than rewrite it lossily). Inert: every reader
   short-circuits on the filed placeholder. Recorded at `leaves.py:966-972`.
2. `assemble.py:85` labels the `infra-empty` §6 row "leaf did not run (transient infra —
   safe to re-run)"; for the empty-run shape the last attempt *did* run and produced
   nothing. Fixing the label also means editing `template/tests/test_leaf_status.py:135`,
   a second test file in a patch already flagged oversized. Flagged, not changed.
3. The verdict copy at the three harvests is still a non-atomic `shutil.copy2`, and
   `_atomic_write_text` can strand a `*.error.log.tmp.<pid>` sibling on a kill (inert: no
   `state.DOWNSTREAM_GLOBS` pattern claims it). Both noted by earlier sign-offs as Act
   candidates.
4. A refused withdrawal ends the run with a *settled* account before the placeholder is
   filed; a kill in that sliver leaves "ran and failed" with no placeholder — identical to
   the base's behaviour for a leaf that spends its attempts, and honest. This is the
   ordering round 3's sign-off prescribed.

## External dependencies

None beyond the base toolchain (pure-stdlib Python ≥ 3.11 + git). Every leg is driven by a
stub "leaf" that is a Python interpreter — no vendor CLI, no API key, no container. `gh`
was used only for the prior-art/merge check above, which is evidence for the human's §6
item, not for building or verifying the fix. Nothing was blocked; no NEEDS-HUMAN external
dependency to declare.
