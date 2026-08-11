# Build notes — issue #459 (iteration 2)

**Target:** `eduralph/pdca-harness` @ `main`, built and verified in the worktree
`/home/eddie/pdca/pdca-harness.pdca-wt` (detached at `92a1fd5`, the tip of
`origin/pdca-integration/main` — this bundle's `stack-base`). All `path:line` citations
below are against that tree **after** the patch unless marked "pre-fix".

---

## 1. What the carry-forward asked for, and what changed because of it

Iteration 1 was rejected at C4 with one concrete finding:

> criterion (d) is not fully met. A persistently broken stderr still raises OSError after
> both bundles are created — the later status write at `cli.py:830` is unguarded […] The
> shipped test masks this: its fake stderr fails only once (`fail_at` counter), while a
> real broken pipe raises on every write.

Both halves are addressed, and neither by patching the one line:

* **The guard is now a property of the path, not of the writes someone remembered to
  wrap.** One definition — `split.advisory` (`split.py:238-273`) — is used by the report
  *and* by every notice on the acceptance path: all eleven writes in `cli._split`
  (`cli.py:771`, `:775`, `:784`, `:790`, `:796`, `:801`, `:806`, `:813`, `:819`, `:828`,
  `:829`), the rollback/restore notices (`split.py:677`, `:729`) and `file_children`'s two
  (`split.py:1022`, `:1072`). Guarding only the status line would have left the same class of
  bug in eight other writes, including the stdout `print(child)` that the criterion's own
  reproduction (`… 2>&1 | head`) breaks first.
* **The fake stream is now a broken pipe, not a hiccup.** `_BrokenStream`
  (`test_split_convergence.py:47-88`) trips by write ordinal *or by content* and, once
  tripped, raises `BrokenPipeError` on **every** subsequent `write` and on `flush`. Three
  tests drive it: broken from write 1, broken only from the post-`accept` status line
  (`fail_on="marked split"`), and broken on stdout.

Refutation against the rejected code is in §5 — the new tests are red on iteration 1's
patch, at `cli.py:830`, the exact line the reviewer named.

## 2. The shape of the fix

**One report, at one call site, reached by both shapes.**

* `split.convergence_report` (`split.py:393-466`) computes the report; it returns lines and
  prints nothing, so a stream is touched in exactly one place.
* `split._emit_convergence_report` (`split.py:469-488`) prints them through `advisory`, and wraps the
  *computation* too: an advisory estimate that raised would otherwise escape `preflight`.
* `preflight` calls it last, after `_validate_ordering` (`split.py:305`). That ordering is
  load-bearing twice over: only an acceptable proposal is worth reporting on, and
  `_validate_ordering` is what proves every `Conflicts with` ref names a sibling — the
  invariant the report leans on.
* `cli._split` hoists parse + `preflight` **above** the `if not ids:` branch
  (`cli.py:756-776`), so `--accept --ids a,b` reaches it too. That is the whole of the
  `--ids` fix: 3 lines moved, not a second call site to keep in step. `accept()` re-runs
  every one of those checks itself (`split.py:757` → `validate` → `_validate_ordering`), so the hoist cannot change what is
  filed or materialised — it only moves the refusal (and now the report) earlier.

**Staging.** `_staged_estimates` (`split.py:344-370`) calls the production
`materialise()` into a `TemporaryDirectory`, passing the child **labels** where the ids go.
Three consequences, all wanted:

1. the staged bundle is assembled by the same writer `--accept` uses, so the report cannot
   describe a bundle built differently from the one about to land;
2. the lineage record it writes lists the **sibling labels**, which is what makes
   `sizing.estimate` apply #457's sibling-conflict exclusion here exactly as it will once
   the children exist (the brief's Constraints paragraph);
3. nothing is written into the instance and nothing survives the call — `preflight`'s
   standing guarantee, asserted by `test_the_report_writes_nothing_into_the_instance`.

`_LABEL_RE` pins labels to `child-\d+` (`split.py:54`), so composing a path from one cannot
traverse.

**Not blinded by the exclusion (criterion c).** The per-child count is read from
`SizeEstimate.sibling_conflicts` via `_exposed_sibling_conflicts` (`split.py:373-390`) —
never from `score`/`reasons`, which is precisely where #457 removes those declarations. The
identities can only come from the proposal (no id exists yet), so the estimate's *count*
gates how many declared edges are credited (`declared[:conflicts]`), and the split is
reported as having "separated nothing" when the symmetric edge set is complete. Verified
live on the folded base: with #457 in force, child-1 scores `0 / no structural signal` and
the report still prints `[1 sibling conflict(s) declared]` and `NOT CONVERGED — … separated
nothing` (§4).

## 3. Alternatives considered, with their costs

**(a) Guard only `cli.py:830` (the literal carry-forward reading).** 1 line. Rejected: the
same failure survives in `print(child)` (stdout — the first thing `2>&1 | head` breaks), in
`filed N child issue(s)`, and in every failure-path notice. The measured difference is 11
call sites converted vs 1; the diff cost of doing it properly is ~14 lines net
(`cli.py` +49/−45 includes the `--ids` hoist), because the helper replaces existing
`try/except OSError` blocks rather than adding to them — iteration 1's inline guard at
`cli.py:794-798` disappears.

**(b) Hard-require #457 (`est.sibling_conflicts`, no fallback).** This is the C5 question
the reviewer raised. Rejected **on evidence about the base, not on taste**:
`origin/pdca-integration/main` is `92a1fd5` today and carries no `sibling_conflicts`
(`git grep -c sibling_conflicts origin/pdca-integration/main -- …/sizing.py` → nothing);
the wave-2 fold that did carry it (`ef00e6e`) was overwritten by another run's integrate
(`pdca-integration/main` reflog, `@{0} commit: pdca-integrate: issue_413`). The gate
reconstructs on that ref (`worktree._target` → `publish._stack_base_branch` → the bundle's
`stack-base`), so a hard requirement would make the green leg error on `AttributeError` —
one burnt iteration for a purity gain.
Instead the fallback is **named, not masked**, which is the actual C5 concern: when the
estimator exposes no count the report prints `note: this estimator exposes no
`sibling_conflicts` count (#457) …` (`split.py:463-466`, asserted both ways by
`test_an_estimator_that_exposes_no_count_is_named_not_absorbed` and
`test_the_sibling_conflict_count_is_read_from_the_estimate_not_its_score`). The substituted
number is not a second definition of the feature: at `preflight` time `_validate_ordering`
has just proven every `Conflicts with` ref names a sibling, so "declared" and
"sibling-only" are the same quantity — and on a base *with* #457 the exposed count is used
and the note never prints. **Cost of removing the fallback later: delete 4 lines**
(`_exposed_sibling_conflicts`'s `None` branch, the `unexposed` flag, the note) — it is a
transitional 4 lines, not an architecture.

**(c) Recompute the sibling-conflict count in `split.py` instead of reading the estimate.**
Rejected: it would make one shared feature name denote two quantities, the exact drift
`sizing.sibling_conflict_count`'s docstring warns about, and it would satisfy criterion (c)
only by accident — the report would be *unblinded* but would no longer be reading the thing
#457 exposes for this purpose.

**(d) Make the report blocking, or prompt.** Out of scope by the brief, and wrong by the
same calibration argument as `plan_policy.size_reasons`: 62% precision at best, and a gate
at that rate is one people learn to override.

**(e) A `file=` parameter on `preflight` (iteration 1 had one).** Removed. It was a test
seam; patching `split.sys.stderr` drives the **real default path** instead, which is
stronger evidence for exactly the criterion it serves.

## 4. Evidence

| What | Command (project runner) | Result |
|---|---|---|
| C4 red→green | `engine/scripts/run-verify.sh` | green leg 19/19 OK; red leg 4 failures + 15 errors → `C4 PASS: red without the fix, green with it` |
| T3 suites | `engine/scripts/run-suite.sh` | `root suite OK, driver suite OK` (root 7 tests, **not** skipped — `copier` 9.17.0 importable; driver 1703 tests, skipped=2 pre-existing) |
| T2 docs | `engine/scripts/run-docs-check.sh` | `lint_docs: OK`; `render_site: 22 pages, link audit OK` |
| Applies on the folded base | `GIT_INDEX_FILE=… git read-tree 9bc0c94 && git apply --cached --check` | clean (9bc0c94 = #457 + #458 folded) |
| Behaves on the folded base | folded tree at `/tmp/fold459` (`git archive 9bc0c94` + this patch) | new module 19/19 OK; **whole offline suite 1719 tests OK (skipped=2)** — composes with #457's and #458's own tests |

Report as printed on the folded base (exclusion active — this is criterion (c) end to end):

```
split: convergence report for issue_500 (advisory, changes nothing) — parent bands watch (score 6)
split:   child-1: ok (score 0) — LOWER than the parent — no structural signal [1 sibling conflict(s) declared]
split:   child-2: watch (score 6) — same band as the parent — difficulty=high; 1 external dependency token(s) [1 sibling conflict(s) declared]
split: NOT CONVERGED — every pair of children declares a `Conflicts with` edge, so the split separated nothing: …
```

## 5. Refuting my own test (forced, recorded)

**(a) Genuine red?** Yes, twice over.
*Against no fix:* the C4 gate reverts the production hunks and keeps the test — 19/19 red
(4 failures, 15 errors).
*Against the rejected iteration-1 fix* (the sharper question, since the carry-forward is
about a defect iteration 1 already half-fixed): a scratch tree at `/tmp/prev459` =
`92a1fd5` + `iteration-v1/patch.diff` + **this** test module runs 19 tests → 8 failures, 4
errors, and the criterion-(d) tests fail for the right reason:

```
ERROR: test_a_stderr_that_breaks_after_the_report_still_exits_zero
  File "/tmp/prev459/template/src/pdca_harness/cli.py", line 830, in _split
    print(f"{d.name} marked split; …", file=sys.stderr)
BrokenPipeError: [Errno 32] Broken pipe
```

`cli.py:830` is the exact line the reviewer's C4 cited. Also red there:
`test_a_broken_stderr_…` (persistent stream), `test_a_broken_stdout_…` (the unguarded
`print(child)`), `test_a_report_that_cannot_be_produced_…` (iteration 1 wrapped the write
but not the computation), and `test_a_persistently_broken_stderr_leaves_preflight_itself_unharmed`
(iteration 1's stream stopped failing after one raise; the assertion `raised >= 2` is what
the carry-forward asked for).

**(b) Production path?** Yes. The tests drive `cli._split`, `split.preflight`,
`split.accept` and `split.convergence_report` — the shipped functions, in the shipped
package, through the real CLI entry (`SimpleNamespace` args are what `argparse` hands it;
`test_split.py:596` does the same). No re-implementation exists anywhere in the test
module. Two tests substitute `sizing.estimate` — that is the **dependency** (#457, not in
this checkout), never the unit under test, and the same behaviour is additionally exercised
against the real estimator on both bases (§4), which is what makes the substitution
honest rather than load-bearing.

**(c) Fixture includes the fault?** Yes.
*The broken stream is really broken:* every stream test asserts `stream.raised >= N`, so a
guard that silently skipped the write (or a fake that quietly healed) fails the test — the
fault is asserted to have been hit, not merely tolerated.
*The irreversible half really happened:* the same tests assert
`self._bundles() == {"issue_500", "issue_601", "issue_602"}` — the exit code is checked
*with the bundles on disk*, which is the state the reviewer found broken.
*The exclusion is really applied:* `test_the_sibling_conflict_count_is_read_from_the_estimate_not_its_score`
feeds an estimate whose `score`/`reasons` are clean and whose count is 1 — a report reading
the score would pass vacuously; it fails. And the folded-base run has the *real* exclusion
in force.
*Nothing is curated out:* the proposals in the fixtures include the conflicting children,
the heavy children that don't shrink, and the free pair that must **not** be reported as
pairwise (`test_a_proposal_with_a_free_pair_is_not_reported_as_separating_nothing`).

## 6. Notes for sign-off

* **No NEEDS-HUMAN external dependency.** The brief's one external dependency, `copier
  importable (.venv)`, is present (9.17.0) and the seven root render/update-compat tests
  **ran** rather than skipping — `Ran 7 tests … OK` in `gate-logs/T3-suite.log`.
* **Base drift worth a glance at sign-off (not a blocker).** This bundle's `stack-base` is
  `pdca-integration/main`, which another run reset to `92a1fd5`; the wave-2 fold carrying
  #457/#458 is only in `fix/458-split-child-remedy-and-hatch` (`9bc0c94`). The patch is
  verified on **both** (§4), so whichever the gate picks up is green — but the PR should be
  stacked on #457's, since `Depends on: 457` is real: without it the report still works and
  says so in its own output, with it the bands are the calibrated ones.
* Scope kept: `split.py`, `cli.py`, and `docs/07-crosscutting.md` **inside `### The split`
  only** (the new paragraph sits at `:209-224`, between the `--ids` prose and the
  close-disposition paragraph; `### The process` and `### The estimate` are untouched — the
  only reference to the latter is a link, `[size guard](#the-estimate)`).
* No `gh`, network, container or tracker is needed by the test: `file_children` is
  substituted in the one auto-filing test and `--ids` covers the rest.
