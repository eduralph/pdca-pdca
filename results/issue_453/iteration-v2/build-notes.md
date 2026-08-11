# Build notes — issue 453 / apply-orphaned-signoff-decision (iteration 2)

Target: `eduralph/pdca-harness` @ `main`, base `b95aa58`. All work done in
`$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt-l1`; `git status --short` there
shows exactly two paths (`M template/src/pdca_harness/flow.py`,
`A template/tests/test_signoff_orphan.py`) and `git apply --check -R patch.diff` succeeds,
so the diff is exactly base + this change.

## The invariant, and what restores it

`signoff-decision` is a **bundle file**, so by the project's own state rule it is
un-consumed *input* to the driver — "The state of an issue **is** the set of files in its
bundle directory … Keeping state in the filesystem is what makes the pipeline resumable and
inspectable" (`template/src/pdca_harness/state.py:1-6`). Pre-fix the driver read that file
only through the variable of the call that had just launched the session, so a run that died
in between (a `^C` — `_isolate` deliberately does not contain `KeyboardInterrupt`,
`template/src/pdca_harness/flow.py:50-69`) left the decision non-resumable. The fix is
**read before asking**, at every site that is about to ask, plus **never author over a
decision this driver did not write**. Three sites, one module, no new transition path.

### 1. `_signoff_and_apply` — single-issue drive path
Pre-patch `flow.py:213-218` ran `leaves.run_signoff` unconditionally. Post-patch
`flow.py:231-239`: read `leaves.signoff_decision(d)` first; if set, announce and route it
through the **existing** `_apply_decision` (`flow.py:132-210`, untouched), returning its
result — so `REASSEMBLE` / `None` / an action reach the caller's existing handling at
`flow.py:376-386` (pre-patch `flow.py:344-354`) unchanged. Only `"blocked"` (a C6-refused
accept) falls through to a fresh session, which is the brief's one exception.

### 2. `_maybe_auto_iterate` — never clobber a decision it did not author
Pre-patch `autoiterate.write_decision(d, items)` at `flow.py:271` was unconditional, so an
auto-iterate pass could overwrite an orphaned human `accept` with its own `iterate-do`.
Post-patch `flow.py:264-274`: a decline placed **before** `assemble.collect_needs_human`,
`autoiterate.count` and `write_decision` — so no decision is authored, no classification is
paid for, and no budget is spent (`autoiterate.bump` is only reached from `write_decision`,
`autoiterate.py:107-117`).

### 3. `_drive_wave` — batch drive path
Pre-patch `flow.py:686-695` chunked **all** of `pending` into `leaves.run_signoff_batch`.
Post-patch `flow.py:720-739` splits `pending` into "already decided → pre-apply now"
(`flow.py:729-738`) and `needing_session`, and only the latter is chunked
(`flow.py:739`). The pre-apply uses the *exact* shape the brief names as the peer to mirror
(the post-session apply, now `flow.py:746-748`):
`_isolate(d, …, lambda d=d: _apply_decision(cfg, d, by=by, today=today, apply_now=False))`
— same deferred-apply semantics, same isolation, same return handling. The no-progress exit
(`flow.py:703-719`, pre-patch `flow.py:668-685`) is untouched: an orphan-holding bundle now
transitions, so it stops being the "no progress but pending non-empty" case by itself.

Every apply without a session is announced on stderr naming **the bundle and the action**
(`flow.py:233-234`, `flow.py:734-735`) — the brief's Scope clause. (This is a concrete
delta from iteration 1, whose message named only the bundle; the new tests assert both
tokens appear.)

## What I did NOT change (brief's out-of-scope list)

`VALID_DECISIONS` / the decision grammar (`leaves.py:78`); what C6 blocks or how §9 is
written (`signoff.record` — reused unmodified); `_isolate`'s `KeyboardInterrupt` contract
(`flow.py:56-58` — a `^C` must still stop the run); the no-progress/`max_passes` accounting
beyond what falls out of the pre-apply; the interactive sign-off prompts.

One behavioural consequence worth naming for the reviewer: `_apply_decision` does **not**
unlink the decision file when it returns `"blocked"` (`flow.py:175-177`), so a C6-refused
accept stays on disk. With site 2 in place, auto-iterate now declines for such a bundle
where pre-fix it could have rebuilt it. That is the intended reading of the invariant — the
human's refused `accept` is still their un-consumed call, and C6 says they must come back —
and both drive paths still offer that bundle a session in the same pass
(`test_drive_wave_c6_refused_accept_still_gets_a_fresh_session`,
`test_signoff_and_apply_c6_refused_accept_still_gets_a_fresh_session`), so nothing stalls.

## Alternatives considered, with costs

**A shared `_pre_apply(cfg, d, …)` helper wrapping check-then-apply once.** Rejected on
semantics, not on size — the two are within ~3 lines of each other (helper: 11 lines of def
+ docstring, 4 at the single-issue call, 6 in the wave loop = 21; inline as shipped: 7 +
12 = 19). The blocker is that `_apply_decision` returns `None` for *two* different things
("no decision on disk", `flow.py:152-154`, and "a decision that could not be recorded",
`flow.py:160-164`); a helper collapses them into one return value, and
`_signoff_and_apply` must distinguish them
(the first means "open a session", the second must not). Keeping `if leaves.signoff_decision(d):`
at the call site keeps `None` unambiguous in context. Second, the single-issue path calls
`_apply_decision` **without** `_isolate` by design (`_apply_decision`'s own docstring says
the single-issue flow has no `_isolate` around it, which is why it contains its own
`ValueError` backstop) while the wave path always isolates — a shared helper needs an
`isolate: bool` flag, i.e. more API surface than the thing it removes.

**Guarding inside `leaves.run_signoff` / `run_signoff_batch` ("don't open a session for a
decided bundle").** ~6 lines, the smallest possible diff, and rejected: it puts a driver
decision inside a model leaf, leaves `_maybe_auto_iterate`'s clobber unfixed (it never calls
a leaf), and still never *records* §9 — the bundle would sit at AWAITING_SIGNOFF with no
session and no transition, i.e. a quieter version of the same stall. The brief names the
invariant to restore, so the target is the smallest change that restores it, not the
smallest diff.

**Distinguishing "decision consumed but unrecordable" with a new sentinel** so the wave's
split could tell it from "nothing on disk": out of scope (it changes how §9 record failures
are reported) and unnecessary — folding it into "needs a session this pass" reproduces
exactly what the pre-existing code did in that corner, so behaviour there is unchanged.

## The three refutation questions

**(a) Genuine red?** Yes — proven by the project's own C4 runner, which reverts *only* the
production hunks (`--exclude=template/tests/*`) and keeps the test:
`PDCA_BUNDLE=results/issue_453 PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` →
`C4 PASS: red without the fix, green with it` (log: `/tmp/453_verify_final.log`).
Green leg `Ran 7 tests … OK`; red leg `Ran 7 tests … FAILED (failures=5)` — five real
assertion failures, no import/collection error (the gate exits 77 if the module fails to
load, and it did not). The two that pass on both legs are the C6-exception guards, which
must: that behaviour is deliberately unchanged. The red output carries the reported defect
verbatim:

```
AssertionError: Lists differ: ['issue_ORPHANWAVE'] != []
+ [] : a fresh sign-off session was opened for a bundle that already carried a
       decision on disk; §9 now records 'merged-wider'
```

— i.e. pre-fix the human's `iterate-do` is replaced by an `accept` they never gave, which is
exactly the brief's Falsifiability prediction.

**(b) Production path?** Yes. The tests call `flow._drive_wave`, `flow._signoff_and_apply`,
`flow._maybe_auto_iterate` and the public `flow.flow` — the three changed functions and the
entry point a human actually runs — with all six leaves in `stub` mode. `_apply_decision`,
`signoff.record`, `state.state`, `queue.awaiting_signoff`, `driver.run_issue` all run for
real against a real temp bundle whose `SUMMARY.md` the stub Check assembled. The only
patched names are `leaves.run_signoff` / `leaves.run_signoff_batch` /
`assemble.collect_needs_human`, used purely as **spies** to record whether a session was
opened — never to fake the decision logic. Imports are modules only (`from pdca_harness
import assemble, autoiterate, driver, flow, leaves, signoff, state`), so the red leg cannot
die on a missing new symbol, per the brief's instruction.

**(c) Fixture includes the fault?** Yes. Each test drives a bundle through the real stub
Plan→Do→Check pipeline to a genuine `AWAITING_SIGNOFF` halt (`driver.run_issue`, not a
hand-built SUMMARY), then writes the orphaned `signoff-decision` — the artifact state a
`^C`'d session leaves. Nothing is curated out: the spy sessions **do what a real session
does** (`_session_writes_accept` = clear §6 + write `accept`, byte-identical to
`leaves._stub_signoff`, `leaves.py:2974-2980`), so if a session is opened the human's
decision really is destroyed, and the red leg prints that destruction. The C6 tests
deliberately leave §6 open so the refusal is real, not simulated.

## Carry-forward from iteration 1 — both items addressed with evidence

**T3 Runtime — "the root render/update suite executed zero tests (all 7 skipped) because
`copier` is unavailable".** That skip is a property of the *reviewer's* interpreter, not of
this instance: the gate runs `.venv/bin/python3` (`engine/scripts/run-suite.sh:14-15`,
`[ -x "$PY" ] || PY="$(command -v python3)"`), and `.venv/bin/python3 -c 'import copier'`
reports **copier 9.17.0** here — which is why `[[doctor.checks]] id = "copier importable
(.venv)"` is `required = true` in `pdca.toml:809-814`. Re-run independently by me, on this
patch, through the project's own T3 runner:

```
PDCA_BUNDLE=/tmp/453_t3 PDCA_WORKTREE=… ./engine/scripts/run-suite.sh   # rc 0
== T3: template-repo suite (render + update-compat)   Ran 7 tests in 21.258s   OK
== T3: offline driver suite (template/tests)          Ran 1598 tests in 25.231s  OK (skipped=2)
== T3: root suite OK, driver suite OK
```

So the render + `copier update` compat suite **executed** (7 tests, not skipped) with this
patch in the working tree — those suites copy the working tree into a throwaway repo, so
they exercised the patched `flow.py` as it will be rendered into instances. 1598 = the
pre-existing 1591 + the 7 new tests; no regression. Bare `python3` (3.14.4, outside the
venv) has no `copier` — anyone reproducing this must use `.venv/bin/python3` or the gate
script. This is a documented, satisfied instance dependency, not a missing one, so no
NEEDS-HUMAN external-dependency marker is warranted.

**T4 Contribution — "`commit-msg.txt`, `pr-description.md` … were not among the permitted
inputs".** They do not exist yet, by design: `contribcheck` returns 0 early when
`pr-description.md` is absent — *"artifacts not drafted yet (Check-time gate, pre-publish) —
nothing to lint"* (`src/pdca_harness/cli.py:1035-1036` in this instance). Publish drafts
both artifacts and the same row runs **again** at publish (`pdca.toml:954-975`, the
`at_publish` note), which is where the tracker-id and user-impact-opener assertions actually
bite. Verified now for this bundle: `PDCA_BUNDLE=results/issue_453 ./scripts/pdca
contribcheck` → **rc 0**, no output, and `ls results/issue_453` shows no `pr-description.md`
/ `commit-msg.txt`. So the frozen T4 pass means "nothing to lint yet", not "the PR body was
audited" — a fact about the gate's ordering, and nothing in this patch's scope
(`template/src/pdca_harness/flow.py`) can change it. The real audit is unavoidable at
publish, so accepting this row costs nothing.

Neither item indicated a defect in the patch (the reviewer PASSed C1–C5, T1, T2, T5); both
were evidence the reviewer's sandbox could not reproduce. Iteration 2 therefore reproduces
the evidence and additionally strengthens the change itself: the announcement now names the
action (a Scope clause iteration 1 missed), and the test count went 4 → 7 with the batch C6
exception, the accept-completes path, and an end-to-end `flow.flow` case added.

## Runner used

The project's own gate scripts, per `docs/INTEGRATION.md` §3 — never a hand-rolled
invocation:
- C4 red→green: `./engine/scripts/run-verify.sh` (gating) — PASS.
- T3 both suites: `./engine/scripts/run-suite.sh` — root OK, driver OK.
- T2 docs: `./engine/scripts/run-docs-check.sh` — `lint_docs: OK`, `render_site: link audit OK`.
- T4: `./scripts/pdca contribcheck` — rc 0 (see above).

## Commit-readiness for the target repo

`eduralph/pdca-harness` configures **no** Python formatter or linter: no `pyproject.toml`,
`setup.cfg`, `.pre-commit-config.yaml`, `.flake8`, `ruff.toml` or `.editorconfig` at the
target root, no `.git/hooks/*` beyond the samples, and its CI (`.github/workflows/`) runs
only `lint_docs.py`, `render_site.py --check` and the two unittest suites — all four of
which I ran green above. CONTRIBUTING.md's engineering discipline is "one logical change
per commit", "a change ships with the means to verify it", "keep the offline suite green"
(`CONTRIBUTING.md:21-26`) — satisfied: one logical change, one new test module, suite green.
Style checked by hand against the file's own conventions: `git diff --check` clean (no
trailing whitespace/tabs), longest added line 93 chars against an existing maximum of 106 in
`flow.py`, test module max 92.
