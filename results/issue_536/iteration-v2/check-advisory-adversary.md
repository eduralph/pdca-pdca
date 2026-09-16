# Adversarial review — attempt-owned leaf records and harvests (#506 / issue_536)

Task under review: give `_invoke_leaf_resilient` and the three artifact harvests a notion of
*which attempt* produced what — flush each attempt's record as it happens, withdraw a dead
attempt's artifact (text preserved), keep the #369 recovery discriminators honest about the
new "in flight" state, and stop a leaf's own text from impersonating the harness's trailer.

I re-ran the asserted proof rather than reading it. **Post-fix:** `PYTHONPATH=src python3 -m
unittest tests.test_attempt_ownership` → 19 tests, OK. **Red leg** (production hunks reverted
via `git checkout` on `assemble.py`/`driver.py`/`leaves.py`/`state.py`, the new test file
kept — the same shape `engine/scripts/run-verify.sh:214` uses) → **14 failures + 1 error**,
with module-level imports resolving cleanly (no `PDCA-UNVERIFIABLE` import trap). Full
suite with the patch: **1777 tests, OK (skipped=2)**. The C4/T3/C5 rows in `check-gates.json`
are warranted as written. What follows is what survived that.

## Findings

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:871`: the whole-last-line
  match — the exact leg the brief singles out — is asserted in prose only; the suite cannot
  tell it from the defect round 3 shipped.** I mutated `return bool(tail) and tail[-1] ==
  _LEAF_IN_FLIGHT` into `return any(_LEAF_IN_FLIGHT in line for line in tail)` (a
  substring-anywhere sniff) and ran the whole suite: **1777 tests, OK**. Both impersonation
  cases (`test_attempt_ownership.py` `…ending_in_the_trailer_is_not_the_trailer`,
  `…stderr_quotes_the_trailer_is_still_read_as_spent`) stay green because `_defang_in_flight`
  neutralises the payload *before* the match ever runs, so only the belt is exercised and
  never the braces that `leaves.py:859-864` claims ("a substring sniff would let a leaf that
  MENTIONED the marker describe its own run… an impersonation has to defeat both"). The
  brief's Falsifiability §(iv) names this precisely — "the marker must be alone on its own
  final line — round 3 shipped this leg with the marker embedded mid-line". A one-line unit
  assertion closes it, no new fixture: hand-write a log whose *body* contains
  `"echo of the source: " + marker` on a non-final line and whose last non-blank line is
  ordinary text, and assert `leaves.leaf_run_incomplete(log)` is `False` — that goes red
  under the substring form and green under the shipped one. Severity is conformance, not a
  live exploit: I could not build a payload that defeats `_defang_in_flight` yet trips the
  match, so today the belt covers the braces — which is exactly why a regression that
  silently removed the braces would ship unnoticed.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:3135` and
  `template/src/pdca_harness/leaves.py:3439`: both advisory `_settle_leaf_record(error_log)`
  calls can be deleted and the suite stays green.** I removed both lines and re-ran: **1777
  tests, OK**. `BothAdvisoryHarvestsAreAttemptAwareToo` drives both twins but only asserts
  the *harvest* half (artifact contents + preserved residue); nothing reads back the
  advisory log's settled state, because `run_advisory_leaves(only_missing=True)`
  (`leaves.py:3079-3081`) short-circuits on `advisory_artifact(...).exists()` — the
  placeholder — before it ever reaches `_leaf_ran_and_failed`. The reviewer's twin *is*
  covered (`test_a_filed_outcome_settles_the_account`); its two copies are not. This is the
  same class the sign-off's finding 4 asked to close ("wiring either site … and the suite
  would stay green"), one call site over: parametrise the existing subTest to assert
  `leaves.leaf_run_incomplete(error_log)` is `False` after each advisory site returns.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/driver.py:178-179`: the operator-facing
  recovery message still says the leaf "never ran", which the patch has just made false.**
  `_resume_interrupted_check` prints `"Check — reviewer never ran (beat was interrupted
  after the gate write); recovering it…"` on every `review_never_ran(d)` — and since
  `leaves.py:2351-2352` that predicate is now *also* true for a reviewer that ran, died
  transiently, flushed `overloaded_error 529` to `check-review.error.log`, and was killed
  during the backoff. The operator is told the beat died *before* the leaf, over a bundle
  that visibly contains that leaf's error log. The diff reworded the paired text in
  `assemble.py:435-437` for exactly this reason ("the reviewer leaf never ran, **or the Check
  beat died while it was still running**") and states the rule at `assemble.py:419-422`
  ("they must not tell the operator three different stories about it") — the fourth reader,
  sixteen lines below the `driver.py:154-162` docstring the patch *did* update, was missed.
  Wording-only fix.

- **NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:737` + `leaves.py:2825`: the #278
  inversion the sign-off asked to close survives in the commoner shape — a transient death
  that wrote no artifact.** `_empty_run_class` can only classify what `withdrew` kept, and
  `leaves.py:737` keeps the log **only** when a dead attempt left a *file* behind. Driven
  end to end through `leaves._run_review_sandboxed` with a reviewer whose attempt 1 emits
  `overloaded_error 529` on stderr and exits 1 (i.e. `test_leaf_resilience.py:28-31`'s own
  `_TRANSIENT`, the canonical transient death — it writes nothing) and whose attempt 2 exits
  0 having written nothing, I get:

      attempts: 2 · error log exists: False · infra-empty: False · human-empty: True
      "Failure class: **substantive — needs a human.** The leaf ran but did not yield a
       usable verdict; do not assume an infra blip"

  — the exact sentence `leaves.py:2820-2823` says #278's marker exists to prevent, and attempt
  1's 529 is deleted outright by the `error_log.unlink()` at `leaves.py:740-741`, so §6 has
  no pointer to the infra death at all. This needs a human call, not a reflex: closing it
  means keeping the log whenever `records` is non-empty and the artifact is absent, which
  reads against criterion (vi)'s "a success still leaves no error log behind" and stretches
  criterion (iii)'s "still degrades to today's placeholder" — but leaving it means
  criterion (ii)'s "a dead attempt's text is preserved rather than merely deleted" holds
  only for attempts that happened to write a file, which is not what "an attempt is the unit
  of accountability" says. (No existing test blocks the change: `test_leaf_resilience.py`
  has no retry-then-succeed case.)

- **NEEDS-HUMAN — `template/src/pdca_harness/leaves.py:2772` (twins `:3131`, `:3434`): the
  patch made the *discriminator's* file crash-atomic and left the *verdict's* file a
  non-atomic `shutil.copy2`, so a kill inside the harvest still files a truncated verdict —
  and blocks the recovery that would replace it.** Driving `_run_review_sandboxed` with a
  reviewer that succeeds and writes a full verdict, killed inside the bundle-side `copy2`:

      check-review.md exists : True
      content                : '# Review\n\n| Item | Verdi'
      review_never_ran       : False   ← the driver will NOT recover it

  A one-third-written `check-review.md` reaches sign-off as the review, and
  `leaves.py:2351` retires the leaf because the artifact "exists". The non-atomicity
  predates this diff, but the diff is what put attempt ownership on this line, and the
  invariant it restores ("no truncated verdict a dead attempt left may be adopted as the
  leaf's output") has an exact analogue here that the `_settle_leaf_record` docstring's
  absolute framing (`leaves.py:888-890`, "then no kill on either side of it leaves an
  interrupted Check looking spent") papers over. Whether hardening the harvest belongs to
  this slice or to a sibling is a scope call, not a builder reflex — the same `os.replace`
  helper the patch already added (`leaves.py:788`) would do it in one line per site.

- **NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:807-808`: the "inert" claim
  about a stranded temp sibling is slightly stronger than the code supports (minor).** The
  docstring argues the orphan is harmless *because* "no `state.DOWNSTREAM_GLOBS` pattern
  claims it" — but that is also why nothing ever removes it: `driver.py:431` archives by
  those same globs (`state.py:127` = `("check-advisory-*.md", "*.error.log",
  "*.memory.jsonl")`, none of which match `check-review.error.log.tmp.<pid>`), and
  `_invoke_leaf_resilient`'s staleness clear at `leaves.py:716-719` only unlinks the log and
  its memory twin. So each kill inside `_atomic_write_text` leaves one file that survives
  every subsequent iterate, inside a bundle directory that is committed in consumer repos.
  The repo's own precedent for an orphanable temp is to gitignore it (`leaves.py`'s #313
  seed spill: "a SIGKILLed session can still orphan one, which is why the name is
  gitignored"); this name is in no `.gitignore`. Either sweep `*.error.log.tmp.*` in the
  staleness clear, or soften the claim.

## Attempted and could not refute

- **The red→green is real, and it is the production path.** Reproduced independently in a
  copy of `$PDCA_TARGET`; the 14 failures + 1 error under reverted production are behavioural
  (`AssertionError: '1.1 Root cause | PA' unexpectedly found in …`, `'infra-empty' not found`,
  `2 != 1`), not symbol-existence, and the file imports only pre-existing API at module
  level. Mutation-testing confirmed the suite is not a mirror where it counts:
  dropping `_defang_in_flight` in `_withdraw_residue` (`leaves.py:947`) or in
  `_format_leaf_attempt` (`leaves.py:968`) each turns the suite red.
- **Impersonation via the stderr channel.** I ran 15 payloads through the production wrapper
  (exact marker; leading/trailing spaces; tab-, NBSP-, VT-, FF- and zero-width-padded; CR
  terminated; doubled internal space; repeated; trailing blank lines) — every one left
  `leaf_run_incomplete=False` / `_leaf_ran_and_failed=True` on the spent log. `str.strip()`
  and the substring-scoped defang cover the whitespace-variant space; a payload that dodges
  the defang necessarily dodges the equality test too.
- **The three harvests point at the right paths.** `produced = sandbox / "check-review.md"`
  (`leaves.py:2753`) and `out = sandbox / f"check-advisory-{leaf_id}.md"` (`leaves.py:3117`) /
  `sandbox / f"plan-advisory-{leaf_id}.md"` (`leaves.py:3421`) are all sandbox-local, so
  `artifact=` can never unlink a previously shipped bundle artifact; `REVIEWER_INPUTS` (`leaves.py:68`) seeds none of those three names into a
  sandbox, so no seeded input can be mistaken for a dead attempt's residue.
- **`_settle_leaf_record` cannot corrupt a log**: its pop loop (`leaves.py:903-908`) is
  gated by `leaf_run_incomplete`, so it only ever strips blank lines and the trailer.
- **No fourth reader drifted.** Repo-wide grep finds the discriminator read in exactly
  `leaves.review_never_ran`, `run_advisory_leaves(only_missing=True)` and
  `assemble._missing_review_text` — all three converted. `state.has_cycle_evidence` sees an
  in-flight log as *more* evidence, never less. Lanes cannot collide on the temp sibling
  (`.tmp.<pid>` is per-path, and `run_advisory_leaves` is a sequential loop).
- **`template/tests/test_leaf_resilience.py` is untouched** (clean in `git status`) **and
  green**, as criterion (vi) requires.
- The staleness clear at `leaves.py:716` still destroys a preserved dead-attempt verdict on a
  recovery re-run. I am **not** filing it: the sign-off adjudicated it as a deliberate
  deferral for Act, and criterion (vi) freezes that line.
