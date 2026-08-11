# Build notes — issue 413 / merge-mode-full-check-rollup (iteration 2)

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt-l0`, base `36300ee`). All `path:line`
citations below are against that tree; base-file citations say "base" explicitly.

---

## 1. What the invariant is, and why this is the smallest change that restores it

The brief names an **Invariant to restore**, so the target is not the smallest diff — it
is the smallest change that makes the invariant hold:

> A later wave must never build on a base whose verification is not green — and the
> harness's correctness must not hinge on per-instance host config.

Base `merge.py:11-13` already claims the fail-closed doctrine ("the next wave must never
build on an unmerged base"), but the only thing standing between "bundle is COMPLETE" and
the merge was `gh`'s own exit code (base `merge.py:73-83`), and base `merge.py:86-88` says
out loud what that buys: "a failing **required** check". `gh pr merge` enforces exactly
the checks the host marks required in branch protection — nothing else. On a thin
protection config a red non-required job, or a run still in flight, merges, and every
later wave builds on a base that never went green. So the fix has to put the verification
*in the harness*, at the merge boundary, where no host setting can weaken it.

The change (production, 3 files):

| Where | What |
|---|---|
| `template/src/pdca_harness/merge.py:66-123` | `_check_rollup()` — read the PR's FULL rollup with `gh pr checks <pr> --json name,bucket`, classify `green`/`pending`/`failing`/`empty`/`unreadable` (+ `_bucket`/`_names` helpers at `:116-123`) |
| `template/src/pdca_harness/merge.py:166-190` | the gate: after the ready-mark (`:157-164`), immediately before the merge call (`:192-193`); non-green ⇒ message + `return 1` (STOP) |
| `template/src/pdca_harness/merge.py:196-199` | drops the stale "a failing **required** check" wording from the post-merge error (base `:86-88`) |
| `template/src/pdca_harness/merge.py:1-32` | module docstring: the doctrine extended from "merged" to "merged green"; the bucket constants `_ROLLUP_OK` / `_ROLLUP_PENDING` at `:44-51` |
| `template/src/pdca_harness/config.py:361-368, 700-707, 813` | `[driver].merge_requires` (`"all"` default \| `"required"`), parsed beside `merge_method`; unknown value → `"all"` + a note |
| `template/pdca.toml.jinja:126-141` | the knob documented in the rendered instance config |
| `template/docs/fork-discipline.md.jinja:46-60` | the never-ready/never-merge claim scoped (base `:46-48` stated it flatly) |

Wave-level consequence is real, not asserted: a non-zero `merge_wave` breaks the wave loop
at `template/src/pdca_harness/flow.py:1593-1596` ("STOPPING — later waves not run"), so a
refusal genuinely prevents the next wave from building on a non-green base.

### Design points that were decisions, not defaults

- **The read is AFTER `gh pr ready`.** Marking a draft ready can itself trigger
  `ready_for_review` CI, so a rollup observed only pre-ready says nothing about green *at
  merge time*. Pinned by `test_check_triggered_by_the_ready_mark_is_caught` — the stub is
  green before the ready call and pending after it, so a pre-ready-only implementation
  passes every other test and fails that one.
- **Refuse, don't wait.** Out of scope per the brief, and correct: a re-run resumes
  idempotently (`merge.py:148-150`, base `:63-65`), and the refusal message says so.
- **`!= "required"` rather than `== "all"`** at `merge.py:174` — `Config.load` already
  coerces unknown values, but this module is the one that must not merge past a red
  rollup, so an unexpected value gates rather than merges.
- **Unknown bucket ⇒ failing** (`merge.py:107`). If a later `gh` grows a sixth bucket, the
  harness refuses instead of guessing green. Pinned by
  `test_unknown_bucket_is_treated_as_failing`.
- **`empty` vs `unreadable`.** Both refuse under the default, so the split only buys an
  honest message: gh reports a rollup with nothing in it as an error, not as `[]`
  (`merge.py:90-98`). If gh rewords that message, the case falls to `unreadable` — which
  also refuses. No merge decision rides on the string.

## 2. The `gh` invocation shape (the brief asked Do to verify it)

Verified against the installed CLI — `gh version 2.97.0 (2026-07-31)` — using
`gh pr checks --help`, which documents both halves the brief asked about:

- *"When the `--json` flag is used, it includes a `bucket` field, which categorizes the
  `state` field into `pass`, `fail`, `pending`, `skipping`, or `cancel`."* → the five
  buckets `_ROLLUP_OK` / `_ROLLUP_PENDING` are written against (`merge.py:44-51`);
- *"Additional exit codes: 8: Checks pending"* → with 0 (all pass) and 1 (a check failed)
  from `gh help exit-codes`.

Chose `gh pr checks --json name,bucket` over `gh pr view --json statusCheckRollup`
deliberately: the latter returns the raw per-context union (CheckRun *and* StatusContext,
different fields — `conclusion` vs `state`), so the harness would have to re-derive gh's
own bucket mapping across ~10 GitHub states (SUCCESS / NEUTRAL / SKIPPED / CANCELLED /
FAILURE / TIMED_OUT / ACTION_REQUIRED / PENDING / EXPECTED / ERROR) — roughly 20 extra
lines of translation to keep in sync with GitHub forever, for the same verdict gh already
publishes as a documented field.

**No minimum-version floor is documented or enforced** — deliberately. I looked: the
project pins no `gh` version anywhere (`template/pdca.toml.jinja` has no `gh` doctor row,
no docs mention one), and it doesn't need to: a `gh` too old for `pr checks --json` exits
non-zero printing no JSON, which lands in `unreadable` → refuse. The degradation is
already fail-closed, so a floor would add a check that can only produce false alarms. Said
in the docstring at `merge.py:79-85`, and covered by
`test_rollup_gh_could_not_read_refuses`.

**Residual (honest):** the tests stub `gh` (as every test in this module always has), so
what is verified is the invocation shape against gh's own documented contract, not a live
API round-trip. The one thing I could not observe live is which shape a *real* empty
rollup takes (`[]` + exit 0, or gh's "no checks reported" error). Both are handled, and
both refuse under the default, so no merge decision depends on which one it is. Manual
validation, if the human wants it, is in §6.

## 3. Alternatives considered — with their costs

- **"Tell operators to configure branch protection" (0 lines).** Cheapest possible, and
  rejected outright: it *is* the status quo, and the invariant explicitly says the
  harness's correctness must not hinge on per-instance host config. Cost is not the
  deciding axis when an invariant is named.
- **Wait for pending checks (`gh pr checks --watch`) instead of refusing.** Concretely:
  `--watch` blocks in-process with no timeout, so it needs a bounded poll loop plus a new
  `[driver].merge_wait_secs` knob (config field + parse + ctor + jinja docs ≈ 25 lines,
  mirroring `merge_requires`) plus the loop and its timeout branch in `merge.py` (≈ 25
  lines) plus at least 2 more tests (≈ 30 lines) — ~80 lines to avoid a re-run that is
  already idempotent. Out of scope per the brief, and the brief is right.
- **Read the rollup only *before* the ready-mark.** Same line count, and it fails the
  success criterion: a `ready_for_review`-triggered job is invisible to it. That is the
  scenario `test_check_triggered_by_the_ready_mark_is_caught` exists to nail down.
- **Read it both before *and* after ready** (so a doomed PR is never marked ready).
  +1 `gh` call on every merge and ~8 lines; buys nothing for safety — the brief already
  settles that refusing after the ready-mark is safe, and the refusal message tells the
  operator the PR stays ready. Deferred as a nicety, not shipped.
- **Symptom-guard check:** this is not a probe added around a symptom — the cause is the
  *absent* verification at the merge boundary, and the fix supplies it there. Nothing is
  wrapped in a try/except, no capability is sniffed, and the old behaviour survives only
  behind an explicit opt-in.

## 4. Refuting my own test (forced — the three questions)

**(a) Genuine red?** Yes, and behaviourally so. Ran through the project's own runner,
`./engine/scripts/run-verify.sh` (it reverts the production hunks and keeps the appended
tests):

```
== C4 green leg: … Ran 21 tests … OK
== C4 red leg: bundle test(s) with the production change reverted
  Ran 21 tests … FAILED (failures=8, errors=2)
C4 PASS: red without the fix, green with it
```

The 8 **failures** are the behavioural red — with the gate reverted the wave merged a PR
whose rollup was red / pending / empty / unreadable (`AssertionError: 0 != 1` on the
refusal cases, plus the ready→checks→merge ordering case and the wave-stop case). This
matters: iteration 1's red leg was mostly *errors* from a `Config(merge_requires=…)`
kwarg that doesn't exist pre-fix, i.e. red for a construction reason. Here `_cfg()` takes
`**overrides` (`test_merge.py:34-41`) and passes nothing extra by default, so the
default-path tests construct fine on base production and fail because the merge *happened*.
Only the 2 tests that are *about* the knob error (`merge_requires` genuinely does not exist
pre-fix) — expected, and not the load-bearing red.

**(b) Production path?** Yes. The tests call `merge.merge_wave(...)` → the real
`_merge_one` / `_check_rollup` in `template/src/pdca_harness/merge.py`; only
`subprocess.run` (the `gh` boundary), `state.state` and `merged.is_merged` are stubbed —
the same seams the pre-existing tests in this file already used. No copy, no
re-implementation. The config test goes through the real `Config.load` reading a written
`pdca.toml` (`test_merge.py:355-372`), not a hand-built `Config`, so `[driver]
merge_requires` is proven to actually reach `_merge_one`.

**(c) Fixture includes the fault?** Yes — the fault is *in* the fixture, and the fixture is
deliberately hostile: in every refusal test `gh pr merge` is stubbed to **succeed**
(returncode 0), so nothing but the new gate can produce the refusal, and each test asserts
`gh pr merge` was never shelled at all (`_merged(calls)` is False). The failing check in
`test_failing_check_refuses_and_never_merges` sits *beside* a passing one
(`("build","pass"), ("lint","fail")`) — the exact "red non-required job next to green
required ones" shape from the defect — and the test asserts the message names `lint (fail)`.
The ready-triggered case flips its rollup on the `gh pr ready` call rather than starting
red, so it cannot pass by accident.

Full logs: green/red legs `/tmp/c4.log`, `/tmp/c4b.log` (re-run after the final docstring
edit); both `C4 PASS`.

Other gates, run through the project's own scripts (not hand-rolled):

- `./engine/scripts/run-suite.sh` → `== T3: root suite OK, driver suite OK` (render +
  `copier update` compat suites and the whole offline driver suite; the render suites copy
  the working tree, so the patch is exercised).
- `./engine/scripts/run-docs-check.sh` → `lint_docs: OK`, `render_site: link audit OK`
  (22 pages).
- Patch applies to a pristine base: `git archive HEAD` into a temp tree +
  `git apply --check` → clean, all 5 files.

## 5. The iteration-1 carry-forward (T4) — what I changed about it

Sign-off iterated with exactly one implementation-level item:

> T4 Contribution — Confirm the commit and PR artifacts contain a user-impact opener and
> tracker reference for #413 — those artifacts and the rendered `contribcheck` entry point
> were not supplied, so the asserted gate result cannot be independently reproduced.

The T4 row (`pdca.toml:994`) is `./scripts/pdca contribcheck`, and `_contribcheck` is
**default-open when the artifacts don't exist yet** (`src/pdca_harness/cli.py:1034-1036`):
in iteration 1 it returned 0 because there was nothing to lint. A green gate over an empty
input is precisely the "green mechanical check on something adjacent" this beat is
supposed to refuse — the reviewer was right.

So this iteration **ships the two contribution artifacts in the bundle**:
`commit-msg.txt` and `pr-description.md`. They are now real inputs, the gate lints them,
and the reviewer/human can read them next to the patch:

```
PDCA_BUNDLE=$PWD/results/issue_413 ./scripts/pdca contribcheck   → rc=0
# negative control, same artifacts with the opener stripped:
contribcheck: PR body must open with a non-empty `**User impact:**` line …  → rc=1
```

The negative control is the point: the gate is now *capable of failing* on these files, so
its pass carries information.

Two things the human should know about that choice:

1. **It does not take the drafting decision away from you.** `publish._ensure_texts` is
   only-if-missing (`src/pdca_harness/publish.py:45-55` in this instance), so publish will
   use these texts rather than re-drafting, and re-runs never clobber an edit. Edit or
   replace them at sign-off exactly as you would a publisher-drafted pair.
2. **Reproducing the gate without this instance's wrapper.** The reviewer works in the
   target worktree, where `./scripts/pdca` (a pdca-pdca file) does not exist — that is the
   "rendered entry point was not supplied" half of the finding. The target ships the same
   code, so the identical check runs from the target tree with:
   `cd $PDCA_WORKTREE/template && PDCA_BUNDLE=<bundle> PYTHONPATH=src python3 -m
   pdca_harness.cli contribcheck`.

Everything else in iteration 1 passed review (C1–C5, T1–T3, T5), so the approach — a
post-ready full-rollup gate plus an explicit opt-out knob — is unchanged by design; what
changed is the evidence quality: behavioural red instead of kwarg-error red, `empty` split
from `unreadable`, an unknown-bucket case, a wave-level stop case, offending checks named
in the refusal message, and the T4 artifacts that were the actual blocker.

## 6. What no offline test can prove — manual validation (optional, for sign-off)

Everything in the success criterion is covered by the shipped tests. The only unproven
layer is the live `gh` round-trip, which this module has never tested (all `gh` is
stubbed). If you want it end-to-end, on a scratch repo with `wave_mode = "merge"`:

1. Open a PR with a job that fails and is **not** in branch protection's required list.
2. `gh pr checks <pr> --json name,bucket` → confirm a `{"name":…,"bucket":"fail"}` entry.
3. Run the flow: it must print `!!! merge: … was NOT merged — a check is FAILING — <name>
   (fail)` and stop; `gh pr view <pr>` shows it still open (and now ready — expected).
4. Re-push a green commit and re-run: the wave resumes and merges.
5. `merge_requires = "required"` + the same red PR → merges again (host semantics restored).

No external dependency was missing for this build: `gh` is installed (2.97.0) and its
invocation shape was verified from its own `--help`; the tests need no network.
