# Build notes — issue 413 / merge-mode-full-check-rollup (iteration 3)

Target branch: `eduralph/pdca-harness @ main`, worktree `$PDCA_WORKTREE =
/home/eddie/pdca/pdca-harness.pdca-wt-l0`, base `36300ee` (= `origin/main`).
Every `path:line` below is that worktree with `patch.diff` applied unless it says
"on `main`".

---

## 1. What the fix does, and why this shape

**Invariant to restore** (brief): *a later wave must never build on a base whose
verification is not green* — the module's own fail-closed doctrine
(`merge.py:11-13` on `main`) read at its intent, not merely "merged".

The cause is a **delegation**: `_merge_one` handed the green-ness decision to
`gh pr merge`, i.e. to whatever the host repo marks *required* in branch
protection (`merge.py:82-88` on `main`, error text and all). The fix **removes the
delegation** for the driver's own merge rather than probing around it: the driver
reads the PR's full rollup itself and decides.

- `template/src/pdca_harness/merge.py:66-124` — `_check_rollup()` runs
  `gh pr checks <pr> --json name,bucket` and classifies the rollup into
  `green | pending | failing | empty | unreadable`. Only `green` may merge.
- `template/src/pdca_harness/merge.py:44-51` — the bucket vocabulary is gh's own,
  pinned in a comment: `pass | fail | pending | skipping | cancel` (verified against
  the installed CLI, §5). `pass`/`skipping` are completed non-failures; `pending`
  blocks; **anything else, including a bucket a future gh grows, counts as failing** —
  the fail-safe direction is refuse, never guess green.
- `template/src/pdca_harness/merge.py:167-194` — the gate, placed **after** the
  ready-mark (`merge.py:158-165`) and **immediately before** the merge call
  (`merge.py:196-197`). `gh pr ready` can itself trigger `ready_for_review` CI, so a
  rollup read only pre-ready cannot promise green *at merge time*.
  `merge.py:176`/`merge.py:194` echo the read and its verdict into the run log next
  to the existing `→ gh pr ready` / `→ gh pr merge` lines, so a gated merge is
  visibly different from a blind one.
- `template/src/pdca_harness/merge.py:200-203` — the post-merge error no longer
  claims "a failing **required** check" is what stopped it; that sentence was the
  written form of the defect.
- `template/src/pdca_harness/config.py:361-368` (field), `:700-707` (parse, next to
  `merge_method`), `:813` (wiring) — `[driver].merge_requires = "all" | "required"`,
  default `"all"`. An unknown value falls back to `"all"` **with a note on stderr**:
  a typo must not silently buy the looser behaviour.
  `template/pdca.toml.jinja:126-141` documents it in the rendered instance config.
- `template/docs/fork-discipline.md.jinja:46-60` — the never-ready/never-merge claim
  is scoped: unconditional for **every model leaf** and **every final-wave PR**, with
  the one `wave_mode = "merge"` exception named together with the two guards that
  stand in for the human's ready-mark (per-bundle sign-off; this rollup gate).
- `docs/07-crosscutting.md:486-498` — the repo's own merge-mode section, which
  enumerates `[driver].merge_method` for the operator turning merge mode on, gains the
  new fail-closed condition and `merge_requires`. Not named in the brief's Scope
  line, included deliberately: it is the *only other place* in the tree that tells an
  operator what merge mode fails closed on (`grep -rn merge_method` finds
  `docs/07-crosscutting.md`, `config.py`, `flow.py`, `pdca.toml.jinja` and nothing
  else), and shipping a docs-truth fix that leaves the sibling doc under-describing
  the same behaviour would re-file this bug at another path. Cost: **+8 lines, one
  file, no code**.

`!= "required"` (not `== "all"`) guards the gate at `merge.py:175`: `Config.load`
already coerces unknown values, but this module is the one that must not merge past a
red rollup, so an unexpected value gates here too.

## 2. Alternatives considered and rejected (with their cost)

1. **Also read the rollup *before* `gh pr ready`** (so a red PR is never readied).
   Rejected — it *deadlocks merge mode on a large class of repos*: many repos don't
   run CI on drafts at all (or key workflows to `types: [ready_for_review]`), so a
   draft's rollup is **empty**, and empty refuses under the default. Merge mode would
   then never merge anything on those repos. Making it work needs a *second*, weaker
   policy for the pre-ready read ("empty is fine before ready, not after"): ~8 lines
   for the extra gate + ~6 lines and a new config concept for the split policy, to buy
   only "don't ready a PR you won't merge". The brief already declares the residual
   safe — a refusal after the ready-mark costs nothing because a re-run resumes
   idempotently (`merge.py:150`; `merge.py:63-65` on `main`), and `gh pr ready --undo`
   exists for the operator who wants the draft back.
2. **Wait for pending checks (`gh pr checks --watch`) instead of refusing.**
   Out of scope per the brief, and it puts unbounded wall-clock inside a wave boundary
   with no timeout knob (a stuck runner hangs the whole batch). Refusing + an
   idempotent re-run reaches the identical end state.
3. **`gh pr merge --auto`.** Rejected: auto-merge lands when the *required* checks
   pass — exactly the host-config dependence the invariant says must not decide
   correctness — and it merges asynchronously, after the driver has moved on, so the
   next wave could start building before the merge exists.
4. **`gh pr checks --required`.** That *is* the legacy semantics under another name;
   it is what `merge_requires = "required"` expresses, and there we skip the read
   entirely so the behaviour is bit-for-bit the pre-#413 one.
5. **Parse `gh pr view --json statusCheckRollup` instead.** Rejected on cost: that
   payload mixes two node shapes (`CheckRun` with `status`/`conclusion`,
   `StatusContext` with `state`), so the harness would re-implement gh's own bucketing
   — ~25 lines of state/conclusion mapping that must track GitHub adding a conclusion.
   `gh pr checks --json bucket` is gh's documented, already-normalised classification
   (5 values), and drift surfaces as an *unknown bucket*, which we already fail closed
   on.
6. **Keeping the iteration-2 code design.** Kept deliberately: the previous round's
   advisory review PASSed C1–C5, T1–T3 and T5 on it; the sign-off's failing item was
   the T4 *contribution-artifact evidence* (§4), not the code. Re-architecting green,
   reviewed code to look different would have been churn. What changed this round:
   the shipped-and-proven contribution artifacts (§4), the run-log echo of the rollup
   read + verdict (`merge.py:176`, `merge.py:194`), the green-path check count
   (`merge.py:114`), and `docs/07-crosscutting.md`.

## 3. Refuting my own test (forced, recorded)

- **(a) Genuine red?** **Yes.** `./engine/scripts/run-verify.sh` reverts the
  production hunks (keeping the test hunks) and re-runs: `Ran 21 tests … FAILED
  (failures=8, errors=2)`, then `Ran 21 tests … OK` with the fix →
  `C4 PASS: red without the fix, green with it` (full log `/tmp/c4-verify-do3.log`).
  The 8 failures are behavioural — without the gate the merge *goes through* and
  `rc == 0` where the test demands `1`; the 2 errors are the `merge_requires` knob
  that does not exist on `main`.
- **(b) Production path?** **Yes.** The tests call `merge.merge_wave(...)` → the real
  `_merge_one` → the real `_check_rollup`. Only three seams are mocked, all of them
  the process boundary, never the logic under test: `subprocess.run` (the `gh` CLI),
  `state.state`, `merged.is_merged` (`template/tests/test_merge.py:231-234`). The
  config case goes through the **real** `Config.load` against a written `pdca.toml`,
  not a hand-built `Config` (`test_merge.py:355-373`).
- **(c) Fixture includes the fault?** **Yes.** Each refusal case puts the failing /
  pending / unknown-bucket check *in* the stubbed rollup, and the stub makes
  `gh pr merge` **succeed** (`returncode 0` for every verb it is not asked to fail —
  `test_merge.py:53-66`) — i.e. the
  fixture reproduces the exact defect (a host whose branch protection does not require
  the red job), so nothing but the new gate can produce the refusal. Nothing is
  curated out: `test_merge.py:297-322` flips the rollup to pending *on the ready call*
  so the fault only exists post-ready, and `test_merge.py:324-343` keeps the healthy
  sibling bundle in the wave to prove it is never touched after the red one.

## 4. The carry-forward item (T4 Contribution) — what I changed, and what only the human can close

Rounds 1 and 2 were both iterated for the same reviewer row:

> T4 Contribution — Confirm `commit-msg.txt` and `pr-description.md` contain a
> user-impact opener and tracker reference `#413` — neither artifact was supplied, so
> the asserted contribution-gate PASS cannot be independently reproduced.

Two separate facts sit behind it, and I fixed the one that was fixable:

1. **The gate could have been passing vacuously.** `contribcheck` is deliberately
   default-open before publish: *no `pr-description.md` yet ⇒ pass*
   (`/home/eddie/pdca/pdca-pdca/src/pdca_harness/cli.py:1036-1038`, the harness this
   instance runs; on the target branch the same rule is recorded at
   `template/src/pdca_harness/publish.py:755` — the artifacts "do not exist at Check
   time, so Check cannot have validated them"). A `pass` row on an absent
   artifact is not evidence. **Fixed:** both artifacts ship in the bundle now, and I
   proved the gate is *non-vacuous* on them:

   ```
   $ ./scripts/pdca contribcheck 413                      # as shipped
   exit=0
   $ # same files copied to a scratch bundle, User-impact opener removed and the
   $ # commit trailer's #413 dropped:
   contribcheck: PR body must open with a non-empty `**User impact:**` line …
   contribcheck: commit-msg.txt does not reference the tracker id #413
   exit=1
   ```

   That green→red pair is the reproduction the reviewer asked for; anyone can re-run
   the first line in two seconds.
2. **The reviewer structurally cannot see those two files.** Its input set is fixed:
   `REVIEWER_INPUTS = ["patch.diff", "brief.md", "check-gates.json"]` and nothing else
   — the harness this instance is *running* states exactly that to the reviewer
   (`/home/eddie/pdca/pdca-pdca/src/pdca_harness/leaves.py:1395-1397`: "You have ONLY
   patch.diff, brief.md and check-gates.json"), and `build-notes.md` is withheld by
   contract (`leaves.py:1464`, the independence assertion). So *no* Do-side action can
   turn that row PASS: the
   reviewer will emit NEEDS-HUMAN on it however good the artifacts are. **This is not
   a defect in the patch and not something a third iterate-do can clear** — re-running
   Do changes nothing about it. It is a genuine §6 item for the human, and it is cheap:

   ```
   cd /home/eddie/pdca/pdca-pdca
   ./scripts/pdca contribcheck 413 && echo "T4 OK"      # exits 0
   head -1 results/issue_413/pr-description.md ; grep -n "User impact" results/issue_413/pr-description.md
   tail -1 results/issue_413/commit-msg.txt             # -> "Fixes #413"
   ```

   **Act candidate** (for the human to fold into SUMMARY §10 — deliberately *not*
   changed here: it is a second logical change, and CONTRIBUTING.md asks for one per
   PR). The target's `main` has already closed half of this gap — every gate row's full
   output is frozen to `gate-logs/<rule_id>.log` and referenced from the row's `log`
   key (`template/src/pdca_harness/gates.py:589`, `:606`), and the reviewer is now told
   it has those logs (`template/src/pdca_harness/leaves.py:1615-1622`). The instance
   running *this* cycle predates that (its `check-gates.json` rows carry no `log` key,
   and its `gate-logs/` holds only `T3-suite.log`). But even after the instance catches
   up the row stays unreproducible, because **`contribcheck` prints nothing on
   success** (`template/src/pdca_harness/cli.py:1097`f — output only on failure), so
   `gate-logs/T4-contribution.log` would be a header over an empty body. The one-line
   delta that would settle it for good: have `contribcheck` print what it verified
   ("user-impact opener OK; `#413` present in commit-msg.txt and pr-description.md") on
   the success path, so its evidence lands in the log the reviewer already receives.
   Until then, every bundle burns auto-iterate rounds on this row.

## 5. External dependencies / `gh` version

None beyond the harness's existing toolchain — the tests stub `gh` entirely (no
network). The CLI shape was verified against the `gh` on this host:

```
$ gh --version           → gh version 2.97.0 (2026-07-31)
$ gh pr checks --help    → "When the `--json` flag is used, it includes a `bucket`
                            field, which categorizes the `state` field into `pass`,
                            `fail`, `pending`, `skipping`, or `cancel`."
                           "Additional exit codes: 8: Checks pending"
                           JSON FIELDS: bucket, …, name, …
```

That is exactly the invocation and vocabulary `_check_rollup` uses, and the exit code
is deliberately **not** used as the verdict (gh prints the JSON *and* sets 0/1/8 to
summarise the rollup — the buckets are the evidence). **No version floor is enforced
and none is needed**: a `gh` too old for `--json` on `pr checks` exits non-zero with no
JSON, which classifies as `unreadable` → refuse. The degradation is already fail-closed,
so an old CLI stalls a wave instead of merging one blind (`merge.py:79-85` docstring
records this).

## 6. Gates run locally (this iteration's patch)

| Gate | Command | Result |
|---|---|---|
| C4 | `./engine/scripts/run-verify.sh` | `C4 PASS: red without the fix, green with it` (21 tests; red leg 8F/2E) |
| T2 | `./engine/scripts/run-docs-check.sh` | `lint_docs: OK`; `render_site: 22 page(s)`, `link audit OK` |
| T3 | `./engine/scripts/run-suite.sh` | root suite `Ran 7 … OK`; driver suite `Ran 1685 … OK (skipped=2)` |
| T4 | `./scripts/pdca contribcheck 413` | exit 0, and red on a mutated copy (§4) |

Commit-readiness for the target: the target repo has **no** pre-commit hooks and no
formatter/linter config (`ls /home/eddie/pdca/pdca-harness/.git/hooks` → none;
no `pyproject`/`ruff`/`flake8`/`.pre-commit-config.yaml` at the root — its CI is
`docs-check.yml`, `render-check.yml`, `require-linked-issue.yml`, all covered above).
`git diff --check` is clean, every touched Python file compiles, added lines stay
inside the files' existing width conventions (≤95 for `merge.py`, ≤97 for `config.py`,
≤82 for `docs/07-crosscutting.md` whose existing max is 144), and
`require-linked-issue` is satisfied by `Fixes #413` in both artifacts.

## 7. STOP discipline

Nothing pushed, no branch created, no PR opened or marked ready. All edits are in
`$PDCA_WORKTREE`; the bundle carries `patch.diff`, `test_merge.py`, `commit-msg.txt`,
`pr-description.md` and this file.
