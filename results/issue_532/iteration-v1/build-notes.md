# Build notes — issue 532 (`an-attempt-is-the-unit-of-accountability`)

Withheld from the reviewer. Target: `eduralph/pdca-harness` @ `main`, base `acb214a`.
All `path:line` below are on the **patched** worktree (`$PDCA_WORKTREE`,
`/home/eddie/pdca/pdca-harness.pdca-wt-l0`) unless marked "base".

## What I changed and why (one line per criterion)

| Brief criterion | Change | Where |
|---|---|---|
| (i) transient builder death retried, substantive not; still captured + re-raised | `_do_build_command` calls `_invoke_leaf_resilient` instead of `_invoke`, then `raise err` | `template/src/pdca_harness/leaves.py:1984-1994` |
| (ii) each attempt's record on disk before the next attempt | `_write_attempt_records` called inside the loop; the post-loop write is gone | `leaves.py:742`, `leaves.py:758-767` |
| (iii) retried builder told about the residue | `retry_note=` param appended from attempt 2 on; `_BUILD_RETRY_NOTE` is Do's | `leaves.py:729-731`, `leaves.py:1912-1921`, wired `leaves.py:1987` |
| (iv) exhausted-retry report true for the residue on disk | `_report_exhausted_do_retries`, called only for a `.transient` final failure | `leaves.py:1864-1865`, `leaves.py:1869-1898` |
| (v) no dead attempt's artifact harvested as a live one's | `artifact=` param + `_disown_artifact`; passed at the three harvest sites | `leaves.py:727`, `leaves.py:770-790`, `:2676`, `:3009`, `:3310` |
| (vi) nothing else changes | see "What deliberately did not change" | — |

Supporting: `_has_content` (`leaves.py:802-809`) so `do_build`'s outer capture no longer
overwrites the per-attempt records it now finds (`leaves.py:1851-1859`).

## The three decisions that were not obvious

**1. Where the residue problem is solved — prompt for Do, ownership for the harvests.**
The two are not the same problem. A retried *builder* must SEE its predecessor's residue
(there is a worktree full of edits it may want to finish, and deleting it would destroy
evidence the operator may need) — so Do gets `retry_note=` and no `artifact=`, and
`_report_exhausted_do_retries` describes the bundle rather than tidying it. A retried
*reviewer* must NOT see its predecessor's file promoted to a verdict — nothing downstream
can tell a truncated `check-review.md` from a real one — so the three harvest sites get
`artifact=` and the wrapper withdraws the residue's claim before each attempt. Same
invariant, opposite mechanics, which is why the parameter is opt-in per call site
(documented at `leaves.py:704-713` and at the Do call site `leaves.py:1979-1982`).

**2. Rename, not delete, in `_disown_artifact` (`leaves.py:782`).** The alternative I
rejected was `artifact.unlink()` before each attempt: same effect on the harvest, but it
destroys the dead attempt's text while the run is still going, and the run's own
post-mortem (`*.error.log` + the sandbox) is the only place that text exists. Renaming to
`<name>.before-attempt<n>` costs one line more and keeps it readable. The `except OSError`
arm *does* unlink — deliberately fail-closed: residue that cannot be moved must not stay
harvestable, or the exact adoption this prevents happens on the day the rename fails.

**3. Attempt budget/backoff: reuse, do not parameterise.** The brief rules out a new
`pdca.toml` knob, so the builder inherits `attempts=3, backoff=4.0` from the wrapper
signature (base `leaves.py:679-680`). The wall-clock trap the brief flags is real —
`test_build_error_log.py`'s `LeafError(1, ["claude"], output="panic…")` has
`produced=False`, so it is transient and now retries. I did **not** weaken the defaults or
add a test-only knob; the tests patch `time.sleep` with `_skip_backoff`
(`tests/test_build_error_log.py:34-43`, `tests/test_leaf_resilience.py:51-60`), which
skips only delays ≥ 1 s. Cost, measured: the offline suite is **29.4 s for 1769 tests**
(base: ~28 s) — a naive `sleep` no-op instead turns `run_with_heartbeat`'s sub-second poll
into a busy loop (7054 spins in one case; that is why `_skip_backoff` has the `< 1`
branch), and no patch at all would add 12 s per failing case × 6 cases ≈ 72 s.

## What deliberately did not change (criterion vi)

* `_invoke_leaf_resilient`'s contract: same attempt count, same backoff formula, same
  staleness clear (`leaves.py:719-723`), same `_memory_log_for` derivation, same
  `_format_leaf_attempt` record format, same return type (`None` | the final exception).
* `memory_log=` is **not** passed at the Do call site — it is derived from
  `build.error.log` by `_memory_log_for`, exactly as the other three sites get theirs, and
  it resolves to the identical `build.memory.jsonl`. The pre-existing
  `test_leaf_memory_log.py:257-271` asserts precisely that and stays green, so #420's
  post-mortem still rides `output` into the same log.
* `progress.py` untouched; the transient *rule* untouched (that is sibling child-2). I
  avoided editing the four prose sites that restate the transient definition (the
  `LeafError` docstring, the `_invoke_leaf_resilient` transient paragraph, `_FAIL_TRANSIENT`,
  `_unavailable_classification`) — both because they are out of scope and because touching
  them would hand child-2 a textual conflict. My docstring additions sit *after* that
  paragraph.
* `_stub_build` / `select_builder` / `_record_loop_attempt` untouched. Note
  `_record_loop_attempt` stays **outside** the retry loop on purpose: `loop-telemetry.json`
  counts *iterations* (#135 escalation), and an infra retry is not an iteration — recording
  it would corrupt the go/no-go metric the file exists for.
* One operator-visible string did change inside the wrapper body I own: the in-flight retry
  line now names the leaf by its `label` when it has one (`leaves.py:747-753`). For the
  reviewer `workdir.name` is its sandbox; for a cwd-discovery builder it is the harness
  root, which names no bundle at all — the message would have read
  `leaves: pdca-harness — leaf exited 1 …` for every bundle in a wave. The transient
  wording itself is unchanged.

## Alternatives ruled out

* **A lane/worktree reset between attempts** (delete the dead attempt's edits, re-`ensure`).
  Out of scope by the brief, and it is the destructive twin of the same mistake: it throws
  away work that may be 90 % done and evidence the operator may need. The prompt-level
  statement is the bounded fix; I did not find it insufficient (see the open question below).
* **A `retries` knob in `pdca.toml`.** Explicitly out of scope, and there is no evidence
  yet to tune it with.
* **Timestamp-based attempt ownership** (compare `st_mtime_ns` against the attempt's start)
  instead of the rename. Same 20 lines, but it silently degrades on any filesystem with
  coarse mtime granularity, and a wrong answer there is the failure mode we are fixing.
* **Changing `_invoke_leaf_resilient`'s return type** to carry "which attempt produced
  what" back to the callers. That is ~4 call sites × unpacking plus a new result type, and
  every existing caller reads `err is not None`; the opt-in `artifact=` gets the same
  guarantee with one keyword per site and no contract change.

## Forced refutation of my own test (recorded per the builder contract)

**(a) Genuine red?** Yes — reverted exactly the way the C4 gate does
(`git apply -R --exclude='tests/*' --exclude='template/tests/*' patch.diff`,
`engine/scripts/run-verify.sh:214-217`) and re-ran both files through the project's runner
(`cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_resilience
tests.test_build_error_log`):

```
Ran 28 tests   FAILED (failures=7, errors=2)     # production hunks reverted
Ran 28 tests   OK                                # patch applied
```

Red-leg failures, per criterion: retry budget stays 1 (i), `build.error.log` is empty while
attempt 2 runs (ii), attempt 2's prompt is `''` because there is no attempt 2 (iii), no
`TRANSIENT` report at all (iv), the dead attempt's `| 1.1 Root cause | PA` is copied out as
the review (v). `grep -c "unittest.loader._FailedTest"` on the red leg = **0** and the same
28 tests ran on both legs, so this is a real red, not the `PDCA-UNVERIFIABLE` import
failure `run-verify.sh:231-233` warns about. No appended test imports a symbol this patch
adds at module level (only `leaves`, `state`, `Config`, `LeafConfig` — all pre-existing).

**(b) Production path?** Yes. The builder cases drive `leaves.do_build` → the real
`_invoke_leaf_resilient` → `progress.run_with_heartbeat` → a real `subprocess`; the "leaf"
is a Python interpreter (the harness the brief points at, `test_leaf_resilience.py:28-40`
on base), so the transient classification is produced by the production stream reader, not
asserted into existence. The (v) cases drive the real `leaves._run_review_sandboxed`
(sandbox seeding, retry, harvest, placeholder) and stub only `leaves._invoke` — the vendor
spawn boundary, which is how the shipped suite already drives that function
(`tests/test_driver_slice.py:324-333`). Nothing is re-implemented in the test.

**(c) Fixture includes the fault?** Yes — the failing element is present, not curated out:
the dying attempt really runs and really exits 1 with stderr only; in (iv)/(iii) it really
writes the partial `patch.diff` into the bundle before dying (`RESIDUE`), and the test then
asserts the file is **still there** afterwards plus `state.state(d) == state.BUILT`
(`tests/test_leaf_resilience.py:308-310`) — so the operator sentence is checked against the
production state machine, not just string-matched; in (v) the truncated `check-review.md`
is really written into the real sandbox by the attempt that then dies. The companion
`test_the_live_attempts_own_artifact_is_still_harvested` (`:367`) pins that the ownership
check does not cost a live attempt its own work.

## Gates / suites run here

* offline driver suite (the T3 second leg): `Ran 1769 tests … OK (skipped=2)` in 29.4 s.
* template-repo suite (T3 first leg, render + `copier update` compat) under the instance
  venv (copier importable): `Ran 7 tests … OK`.
* No formatter/linter is configured in the target (no ruff/black/pre-commit config, and
  CONTRIBUTING.md names only "keep the offline suite green"); the longest line I add is 96
  chars, inside the file's existing norm (`leaves.py` already carries lines up to 110).
* Docs: nothing in `template/docs`, `README.md` or `pdca.toml.jinja` documents the
  reviewer/advisory-only retry, so no doc goes stale (grepped for
  `_invoke_leaf_resilient|bounded retry|retried|retries` outside `*.py`: one unrelated hit,
  `pdca.toml.jinja:586`, about interactive leaves).

## Open questions for the human at sign-off

1. **Is the prompt-level residue statement enough?** The brief asked me to say so here if I
   concluded otherwise. I did not: with `_BUILD_RETRY_NOTE` the retried builder is told the
   residue is incomplete and told where the predecessor's account is, and the wrapper now
   guarantees that account exists when it reads it. What remains uncovered is a builder that
   ignores the note — a model-behaviour risk no bounded harness change removes. A lane reset
   would remove it by destroying the work; that trade belongs to its own slice.
2. **Merge order.** As the brief says: this child first, then child-2. Child-2 widens what
   counts as transient, which is exactly what makes a leaf retryable *after* it produced
   work — this child is what makes that safe.
3. No external dependency was missing; everything here runs on pure-stdlib Python + git,
   offline. Nothing to declare under `NEEDS-HUMAN external dependency:`.
