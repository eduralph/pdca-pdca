# Build notes — issue 532 (an-attempt-is-the-unit-of-accountability), iteration 2

Withheld from the reviewer. Every `path:line` is on the **target branch**
(`eduralph/pdca-harness` @ `main`, base `acb214a`) as edited in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`), i.e. line numbers **after** the patch unless
marked "(base)".

---

## 1. What the patch does, in one paragraph

`_do_build_command` called plain `_invoke` (base `leaves.py:1824`) — the builder was the one
leaf the harness never retried. It now runs under the same `_invoke_leaf_resilient` the
reviewer/advisory/plan-advisory leaves use (`leaves.py:2108-2119`), with the shipped
attempts/backoff defaults and the memory log left to the wrapper's `_memory_log_for`
derivation. Making a leaf retryable *after* it has produced work opened three ownership
holes, so the wrapper also (a) flushes each attempt's record before the next attempt starts
(`:766`), marking a log whose loop has not finished (`_LEAF_IN_FLIGHT`, `:785`); (b)
withdraws — and preserves — whatever a **dead** attempt left at the artifact path
(`_withdraw_residue`, `:828-864`), which the three harvest sites now hand it
(`:2807`, `:3148`, `:3449`); and (c) appends a retry notice to the builder's prompt from
attempt 2 on (`_BUILD_RETRY_NOTE`, `:2035-2045`). When the retries are spent, `do_build`
reports the class of failure, where each attempt's account is, what residue is in the
bundle, and a next action derived from `state.state` (`:1975-2022`).

## 2. The six carry-forward findings — how each is closed

**1. Fail-closed artifact ownership** (was `leaves.py:783` — rename + fallback unlink, both
suppressed). The set-aside is gone; `_withdraw_residue` (`:828-864`) *reads* the residue,
then `unlink()`s it. If the unlink raises, it returns `ok=False`, the loop stops
(`:764`, `:767`) and the wrapper returns the leaf's own failure — so the caller takes its
`err is not None` branch (`:2813`, `:3152`, `:3453`), writes the §6 placeholder and **never
reaches the harvest**. There is no path on which control continues over an artifact path the
wrapper could not take ownership of. Test: `tests/test_leaf_resilience.py:597`
(`test_ownership_that_cannot_be_enforced_stops_the_retries` — `Path.unlink` refuses for
`check-review.md` only; asserts exactly one attempt, the placeholder, and no adoption).

**2. The #369 trap door.** The per-attempt flush is criterion (ii), so the flush stays and
the *discriminator* learns the third state. A log written while a retry is pending carries
`_LEAF_IN_FLIGHT` (`:785`, written at `:795-796`); `leaf_run_incomplete` (`:804-813`) reads
it and `_leaf_ran_and_failed` (`:816-819`) is the one predicate both call sites now use —
`review_never_ran` (`:2398`) and `run_advisory_leaves(only_missing=…)` (`:3106`). So
"interrupted" recovers exactly like "never ran", while "ran and gave up" is still left alone.
I chose the marker over an in-flight *suffix* because the retried builder is pointed at
`build.error.log` by name (`_BUILD_RETRY_NOTE`); a suffixed file would make that instruction
false, or force a rename the operator would see mid-run. `assemble._missing_review_text`
(`assemble.py:417`) needs no change: the CHECKED-resume runs *before* assembly
(`driver.py:128`) and the wrapper clears the stale log at `:731`, so assembly can only see a
completed log or none. Tests: `tests/test_leaf_resilience.py:432` (killed mid-retry → the
account survives **and** the reviewer is recovered), `:451` (a spent budget is still not
re-run), `:467` (the same for the advisory `only_missing` spelling).

**3. Signal-death scope leak.** `_builder_retryable` (`:1947-1963`) is the builder's rule:
`_transient_death` **minus** a death the child did not choose (a negative `returncode` —
where `subprocess` puts a signal death and where `progress.TIMEOUT_RC` sits). It does not
touch the classifier, does not add a class, and leaves #510's case at exactly today's
behaviour: one spawn, re-raised. It is passed only at the builder call site
(`retry_when=_builder_retryable`, `:2112`), so the reviewer/advisory contract is unchanged —
criterion (vi). The same predicate gates the exhausted-retry report (`:1938`), so a signal
death no longer gets a "the harness absorbed this" sentence stderr could not back up.
Test: `tests/test_leaf_resilience.py:305` (a child that SIGKILLs itself: 1 spawn, no retry
line, no TRANSIENT claim).

**4. Exhausted-retry next action.** `_next_action_after_a_dead_do` (`:2002-2022`) asks
`state.state(d)` and maps the *state* to what `pdca run` would do: PLANNED → Do again,
BUILT → Check on the residue, CHECKED → assemble to sign-off, anything else → "`pdca status`
names the beat". Nothing infers from "is there a patch.diff". Tests:
`tests/test_leaf_resilience.py:353` (BUILT) and `:370` (patch.diff **plus**
check-gates.json → CHECKED: the exact bundle the adversary showed the old advice creates —
asserts `reads CHECKED`, `ASSEMBLES SUMMARY.md`, and `assertNotIn("runs CHECK on the
residue")`).

**5. The withdrawn artifact must survive in the bundle.** It does — as text in the bundle's
own `*.error.log`, appended to the failing attempt's record (`:854-856`). See §4 for why
that file and not a sibling copy. Tests: `tests/test_leaf_resilience.py:535` (the truncated
verdict is readable in `check-review.error.log` in the **bundle** afterwards). The
"produced no artifact" placeholders now name the log too (`:2819-2825`, `:3159`, `:3459-3461`),
so the pointer exists on the one path where the dead attempt's text is all there is.

**6. The residue list is reported, in every branch.** `_do_residue` (`:1966-1972`) resolves
patch.diff, build-notes.md **and the brief's named test file(s)** (via `brief.test_files`,
the same resolution `_stub_build` uses), and `_report_exhausted_do_retries` prints it before
the next-action line whatever the state is (`:1992-1997`) — including the sentence the
finding asked for: a re-driven Do inherits that residue **without** the retry notice.
Test: `tests/test_leaf_resilience.py:383` (no patch.diff; asserts PLANNED, `re-drives Do`,
`build-notes.md`, `test_attempts.py`, `WITHOUT the retry notice`, and that nothing was
deleted).

**Adjudicable production-path coverage** (the "vacuous C5 green" note). The patch adds no
new test file (the brief names the two it appends to), so the C5 gate still has no new file
to inspect. What I could do instead: state the path each class drives, in the file itself —
`tests/test_leaf_resilience.py:18-30` and `tests/test_build_error_log.py:14-18` now carry a
"Production path exercised" map naming the production entry point and the only two
stand-ins (`time.sleep` = the backoff's wall clock; `_invoke` = the vendor spawn). The
builder class stubs **nothing** in `leaves.py`: it drives `do_build → _do_build_command →
_invoke_leaf_resilient → _invoke → progress.run_with_heartbeat → subprocess` with a real
python3 child.

## 3. Red→green, through the project's own runners

* C4 gate, `./engine/scripts/run-verify.sh` (PDCA_BUNDLE=this bundle, PDCA_WORKTREE=the
  worktree): **`PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`**.
  - green leg: `test_build_error_log.py` 14 tests OK, `test_leaf_resilience.py` 23 tests OK;
  - red leg (production hunks reverted, both test hunks kept): `test_build_error_log.py`
    1 failure + 1 error, `test_leaf_resilience.py` 11 failures + 3 errors — **16 of the new
    cases red**, no `unittest.loader._FailedTest` (no module-level import of a symbol this
    patch adds, so the red is a real red, not `PDCA-UNVERIFIABLE`).
* T3 suite, `./engine/scripts/run-suite.sh`: `PDCA-EVIDENCE: root suite OK, driver suite OK`
  (7 + 1778 tests).

Green-on-base by design (regression guards, not red): `:296` substantive-not-retried,
`:305` signal-death-not-retried, `:451` spent-budget-not-re-run, `:549` the live attempt's
own artifact is still harvested. Each pins a behaviour this patch could plausibly have
broken; they are stated as such here so nobody counts them as evidence of the defect.

**Wall-clock trap** (brief §Falsifiability): `test_build_error_log.py:92`/`:201` and
`:274` all drive a transient LeafError, which is now retried — 4 s + 8 s each. Both setUps
patch `time.sleep` with `_skip_backoff` (`tests/test_build_error_log.py:43`), which skips
only waits ≥ 1 s and lets sub-second waits through (`progress._terminate_group` sleeps
0.05 s; turning that into a busy-loop would be worse than the backoff). The wrapper's
shipped `attempts=3, backoff=4.0` are untouched — the tests assert the real
`retry 1/2 in 4s` / `retry 2/2 in 8s` lines. Driver suite wall clock: 28.5 s (56.9 s when
I first ran it with the backoff unpatched — the trap is real).

## 4. Alternatives weighed, with their cost

**Where the withdrawn artifact goes.** The finding said "copy the disowned file into the
bundle". I put its *text* in `<leaf>.error.log` rather than a sibling file, because a
sibling has to be named, and every name is either dangerous or leaky:
* `check-advisory-lens.attempt1.md` — matches `assemble`'s `check-advisory-*.md` glob
  (`state.py:121`, `DOWNSTREAM_GLOBS`; `_plan_findings`, `leaves.py:3283` uses the same
  shape for plan-advisory). A dead attempt's partial verdict would then be read as a second
  advisory review and its NEEDS-HUMAN bullets would fold into §6 — precisely the invariant
  ("nothing a dead attempt left behind may be reported as a live attempt's work") inverted.
* `check-review.md.attempt1` — matches **no** archive glob, so `_archive_iteration` leaves
  it at the top level and it leaks into the next round.
The `*.error.log` namespace is the only one that is archived per round, never read as a
verdict, and already the leaf's post-mortem home — and the placeholder already points at it.
Cost of the chosen form: 11 lines (`leaves.py:846-864`) plus a 20 000-char cap (`:822-825`).

**Keeping the log on a recovered run.** Rejected: `test_a_successful_build_leaves_no_error_log`,
`test_stale_error_log_cleared_on_success` and the #280 staleness rule all say a leaf that
worked leaves no failure behind, and criterion (vi) freezes that. The one exception I did
take is narrow and evidence-driven (`:744-756`): the attempt exited 0 **without writing its
artifact**, so the log holds the only surviving copy of what a dead attempt produced, and
the caller is about to say "produced no artifact". Two lines of condition; without them,
`tests/test_leaf_resilience.py:535` fails (I found this by running it, not by reasoning).

**A lane/worktree reset between builder attempts.** Out of scope per the brief, and it would
have to decide what to do with an edit the operator may want; the bounded fix is the prompt
statement (`_BUILD_RETRY_NOTE`) plus the honest report. Cost if we had done it: a reset would
touch `worktree.ensure`'s contract (`worktree.py`) and every caller of `_do_build_command`'s
isolation branch (`leaves.py:2059-2086`, ~28 lines of branching) — and it would destroy the
residue the report is careful not to destroy.

**Persisting "the previous run died" across processes** (so a re-driven Do also gets the
notice, not just an in-process retry). Deliberately not done: it needs a new bundle marker
and a decision about when it expires — a state-machine change, not a leaf-invocation one.
The gap is instead *told* to the operator in so many words (`:1994-1997`). If the human
judges the prompt-level statement insufficient (the brief invites exactly this note), the
next slice is "a Do that died leaves a marker the next Do reads", and it belongs with #509
(crash-resume), not here.

**`retry_when` as a parameter vs. narrowing `.transient` itself.** Narrowing the classifier
would change the reviewer/advisory leaves' behaviour (a SIGKILLed reviewer is retried today)
and would step on #510's question. The parameter is 1 line in the signature (`:691`), 1 line
at the call site (`:2112`), and the other three call sites are byte-identical in behaviour.

## 5. Scope — what I did not touch

`progress.py` (untouched), the transient rule itself (untouched), no new `pdca.toml` knob,
no `tests/fixtures/`, no `test_terminal_error_classification.py` — all sibling child-2's or
explicitly out of scope. `flow._isolate`'s containment is unchanged: `_do_build_command`
still raises (`:2118-2119`) and `do_build` still re-raises (`:1944`). `_stub_build` and
`select_builder` are untouched, so a stub backend behaves exactly as today
(`test_a_stale_log_is_cleared_on_a_stub_rebuild_too`, `test_build_error_log.py:171`, green).

One deliberate cosmetic change inside the shared wrapper: the retry line now prefers the
leaf's `label` over `workdir.name` (`:770-775`). For a cwd-discovery builder `workdir` is
the *harness root*, which names no bundle at all; for the reviewer it is a
`pdca-review-XXXX` temp dir. No test asserted the old text.

## 6. Forced self-refutation (the three questions)

**(a) Genuine red?** Yes — measured, not asserted. `./engine/scripts/run-verify.sh` reverts
the production hunks and keeps the test hunks: 16 of the new cases fail (11 failures + 3
errors in `test_leaf_resilience.py`, 1 + 1 in `test_build_error_log.py`), and the gate
prints `C4 PASS — red without the fix, green with it`. The red is a *ran-and-failed* red,
not an import failure: the gate's own `LOAD_FAILED` check (`run-verify.sh:231`) is what
would have turned that into `PDCA-UNVERIFIABLE`, and it did not fire. The four
green-on-base guards are listed in §3 so they cannot be miscounted as red.

**(b) Production path?** Yes. `BuilderRetriesLikeEveryOtherLeaf` stubs **nothing** in
`leaves.py`: it runs the real `leaves.do_build` with a `[sys.executable, "-c", …]` builder,
through `_invoke` → `progress.run_with_heartbeat` → `subprocess`, and reads the prompt and
the error-log-at-that-instant from *inside* the child. `AKilledLeafIsRecoveredNotRetired`
drives the real `_run_review_sandboxed`, the real `run_advisory_leaves(only_missing=True)`
and the real `driver._resume_interrupted_check`. `DeadAttemptOutputIsNeverHarvested` drives
the real harvest sites. The only stand-ins anywhere are `time.sleep` (the backoff's wall
clock, per the brief's own instruction) and `_invoke` (the vendor spawn) in the review-side
cases — a stub *leaf process* there would add nothing the builder class does not already
prove. The map is in the test module docstring so a reviewer can adjudicate it without
re-deriving it.

**(c) Fixture includes the fault?** Yes. Nothing is curated out: the builder that dies is
the builder under test; the bundle in `test_the_exhausted_report_asks_the_state_machine…`
holds the *exact* pair (patch.diff + check-gates.json) that made the old advice false; the
fail-closed case makes the real `Path.unlink` refuse the real artifact (and only that
artifact, so the error-log clear still runs); the mid-retry kill is a real
`KeyboardInterrupt` raised in the real backoff window, which tears down the real wrapper.
The residue in each case is written by the child itself, at the path the harness watches —
not planted by the test after the fact.

## 7. Commit-readiness

The target repo has no formatter/linter hook to run: no `.pre-commit-config.yaml`, no
`ruff`/`flake8`/`setup.cfg` config anywhere in the checkout, no non-sample hook in
`.git/hooks`, and CI (`.github/workflows/render-check.yml`, `docs-check.yml`) runs the
suites, not a linter. I matched the file's own conventions instead: 4 added lines run 96-99
chars (the file already has lines up to 110 and both test files already carry 96-100-char
lines), docstrings first-person-plural-free, `#:` for module constants as the file does
elsewhere. `CONTRIBUTING.md`'s "keep the offline suite green" is satisfied
(`run-suite.sh`, §3). Commits are DCO-signed at publish (`git commit -s`) — not mine to do.

No external dependency was needed: pure-stdlib Python + git, offline, as the brief predicted.
