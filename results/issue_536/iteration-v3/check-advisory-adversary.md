# Adversarial review — issue_536 (attempt-owned leaf records and harvests)

Verdict up front: **I could not break the mechanism.** The red→green was reproduced
independently, twelve targeted mutations of the new production logic were all caught by the
new test file, and the 1780-test driver suite is green. The two findings below are
claim-accuracy defects in what the patch *tells the operator and the next maintainer*, in a
slice whose whole invariant is "never file a false account of a run" — both are cheap
builder edits, neither is a behavioural break.

## Findings

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/leaves.py:2910` — the §6 text the new
  `_empty_run_class` path (`leaves.py:2866`, used at `:2819`, `:3175`, `:3478`) routes into
  states something that did not happen. Concrete case, run against the patched target: a
  reviewer whose attempt 1 exits 1 with `overloaded_error 529` and whose attempt 2 exits 0
  having written nothing yields a placeholder reading *"**transient infra — safe to
  re-run.** The leaf exited non-zero with no output **and retries did not recover**…"* — but
  the retries *did* recover; the recovered attempt produced no verdict. `_FAIL_TRANSIENT`'s
  prose was written for the retries-exhausted shape only, and the builder updated the
  adjacent internal comment for exactly this reason (`leaves.py:2829`, now "retries didn't
  recover") while leaving the operator-facing sentence untouched. The class (`infra-empty`)
  and the action ("safe to re-run") are right; only the account of what happened is wrong.
  The new test cannot catch it: `template/tests/test_attempt_ownership.py:363-365` asserts
  only `LEAF_STATUS_INFRA`, `not LEAF_STATUS_HUMAN` and the substring `"safe to re-run"` —
  an assertion that is true of the wrong sentence too. Either widen the prose to cover "the
  run contained a transient death; the attempt that came back produced nothing", or give
  the empty-run shape its own wording.

- **NEEDS-HUMAN [impl]** — `template/src/pdca_harness/leaves.py:919-921` and
  `template/tests/test_attempt_ownership.py:607-609`, `:523-525` — the stated consequence of
  `_settle_leaf_record` is unwarranted. Both the docstring and the two tests justify the
  settle with "otherwise a leaf that gave up looks recoverable forever and is re-run (and
  re-paid for) on every `advance`". That cannot happen: at every one of the three sites the
  settle runs *after* the `*_unavailable(...)` placeholder has been written, and every reader
  of the marker short-circuits on that artifact first — `review_never_ran` requires
  `check-review.md` absent (`leaves.py:2388-2389`), `run_advisory_leaves(only_missing=True)`
  checks `advisory_artifact(...).exists()` first (`leaves.py:3120-3122`), and
  `assemble._missing_review_text` is only reached when the review is absent
  (`assemble.py:185`, `:261`). Demonstrated: with `leaves.py:2823`'s settle deleted, the same
  end-to-end reviewer run leaves the log carrying `_LEAF_IN_FLIGHT` and
  `review_never_ran(d)` is **still `False`** — nothing is recovered or re-paid for. The
  settle is archive hygiene (a bundle must not archive a finished leaf as unfinished), and
  `test_a_filed_outcome_settles_the_account` only bites because it transplants the log into a
  synthetic bundle that has no `check-review.md` — a state that cannot arise once the outcome
  is filed. The genuinely load-bearing half — settle *after* the placeholder, never before —
  is correct and is separately proven (I mutated the order and
  `test_a_kill_before_the_outcome_is_filed_is_recovered_not_retired` went red). Fix the
  rationale, not the code, so a later maintainer does not read the settle as a recovery guard.

## Attempted refutations that failed

- **The evidence.** Reproduced from the frozen inputs, not taken on trust: patched target →
  `Ran 22 tests … OK`; production hunks reverted with the test kept (the `run-verify.sh` red
  leg) → `FAILED (failures=17, errors=1)`; full driver suite on the patched tree →
  `Ran 1780 tests … OK (skipped=2)`. The five tests green pre-fix are exactly the
  unchanged-behaviour guards for criteria (iii)/(vi), which is what they should be. The suite
  drives real `python3` child leaves through `_invoke_leaf_resilient`,
  `_run_review_sandboxed`, `_run_advisory_sandboxed` and `_run_plan_advisory_sandboxed` —
  no parallel re-implementation, and nothing under test is mocked away (the only patches are
  the backoff sleep, `os.environ`, and the two deliberate `Path.write_text`/`Path.unlink`
  failure injections). 8 consecutive runs, no flake.
- **Test blindness (mutation testing, full suite each time).** All twelve were caught, with
  the failing test naming the exact property: drop `_defang_in_flight` from the stderr tail
  (`leaves.py:1005`) or from the withdrawn residue (`:984`); relax `leaf_run_incomplete`
  (`:904`) to a last-line substring or a whole-file sniff; keep the log even when the
  artifact was produced (`:743`); make the flush non-atomic (`:815`); settle before the
  placeholder (`:2818`); make `_empty_run_class` always substantive (`:2866`); delete both
  advisory settles (`:3176`, `:3480`); retry without ownership of the artifact (`:759`);
  retry over an unrecorded predecessor (`:761`); revert `assemble.py:425` to a bare
  `.exists()`. Round 2's two demonstrated blind spots are closed.
- **Impersonation.** I could not construct a leaf-controlled payload that flips either
  discriminator: the marker is defanged in both quoted bodies and matched as the whole last
  non-blank line, and trailing whitespace, a defanged copy, a marker straddling the
  `_RESIDUE_KEEP` truncation and a marker mid-body all fail. The one body that is *not*
  defanged — the `(no output captured) {type(exc).__name__}: {exc}` fallback at
  `leaves.py:1007` — carries `CalledProcessError`'s own text (argv + exit code), which is
  operator config rather than leaf output, and its worst case is a wasted re-run, not a
  missing review; criterion (iv) names only the two quoted bodies, so I am not filing it.
- **Paths the tests do not drive.** A 3-attempt run mixing a residue-less death, a
  residue-leaving death and a silent success files all three records in order, withdraws only
  the dead attempt's file, keeps the account, classifies it infra and leaves no stray
  `*.tmp.<pid>`. On the give-up path a flush that fails to land can leave a log still marked
  in flight (no settle runs there), but it is inert for the same reason as finding 2 — the
  placeholder exists, so every reader short-circuits.
- **Already adjudicated, deliberately not re-filed:** a `#369` recovery re-run destroys the
  dead attempt's preserved text via the frozen staleness clear at `leaves.py:718`. That is
  the round-1 adversary finding the human explicitly deferred to Act under criterion (vi);
  the composition (preserve at `:753` → destroy at `:718`) is unchanged by this round.
