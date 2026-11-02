# Build notes — issue 839, iteration 5

Line numbers are against the worktree as I left it: `origin/main` at `b19b5c1` plus this patch.
Nothing was committed or pushed.

## Do this first: the bundle still points at the old base

**The gates cannot run on this patch until you clear a stale marker, so the Check that follows this
build will fail with "worktree mismatch".**

`results/issue_839/stack-base` still names `pdca-integration/main-re715db900335` (tip `f5321ab`), left
by the Oct 31 run. A `flow` run clears a stale marker (`flow.py:1098`, `:1244`), but a standalone
`signoff --iterate-do` does not. So the driver gave me a worktree at `f5321ab`, and it will rebuild
on `f5321ab` for the gates too (`worktree.py:96-98`, `:280-288`).

You asked for a rebuild on `main` with #626, so I moved the worktree to `origin/main` and built there.
The patch cannot satisfy both bases:

| Base | `git apply --check` |
|---|---|
| `f5321ab` (what the marker pins) | fails in `flow.py` and `merged.py` |
| `origin/main` `b19b5c1` | clean |

**I left the marker alone.** It is the driver's state and it decides which base the gates vouch for, so
changing it is your call. I also did not shape the patch to apply on both bases: a green on `f5321ab`
would say nothing about the code #626 changed. I did not use the `NEEDS-HUMAN external dependency`
marker either, because this is not an external dependency.

**What happens next:** the running `pdca-pdca signoff 839 --iterate-do` goes straight into Check. No gate
runs, and you get one failed row, `C4 Verification (worktree mismatch)`. The reviewer still runs and is
paid for, on a lane left at `f5321ab` with no patch applied. Expect it to say the patch does not apply,
and ignore that.

**To get a real Check, once that process has stopped:**

```
cd /home/eddie/pdca/pdca-pdca/results/issue_839
rm stack-base stack-base-tip check-gates.json SUMMARY.md
cd ../.. && pdca-pdca run 839
```

I checked two steps of this on a scratch copy of the bundle with the real config: without the marker the
base is `origin/main`, and with the last two files gone the state is back to `BUILT`. I did not run the
whole recipe on the real bundle.

**Worth filing (Act):** a standalone `signoff --iterate-do` keeps a stale `stack-base`, so "rebuild on
main" silently rebuilds on the old line.

## Before you publish

- **The PR texts are stale.** `commit-msg.txt` and `pr-description.md` are still in the bundle from the
  last publish, and publish drafts them only if absent (`publish.py:73`). They do not mention the claim
  step. Delete or edit them.
- **Close #859 first.** You said the rebuilt PR replaces it. Publish force-pushes to the same branch name,
  and if `gh pr create` then fails because #859 is still open, the record gets an empty `pr_url`
  (`publish.py:413-439`). Not tested on a live host: that failure is GitHub behaviour as I understand it.

## What changed this round

**1. Rebuilt on `main`.** The previous patch went on with `git apply --3way`. Only two docstrings
conflicted, and I kept both sides of each (`flow.py:712-734`, the `merged.py` module docstring). One small
change of my own: `_merge_way_out` now asks `merged.counts_into` (`flow.py:1631`), #626's single rule,
instead of comparing the fields itself. Behaviour is the same at that point, because a `"stacked"` record
has already returned.

`main` moved again while I worked, from `fcc18c9` to `b19b5c1`. That was docs only, in files this patch
does not touch, and `patch.diff` came out byte-identical on the new tip.

**2. The claim, as you and Codex asked.**

| Where | Change |
|---|---|
| `flow.py:3295` | `_drive_and_act` passes the run's `claims` to the pre-wave step |
| `flow.py:1735` | `visit` takes the claim before anything reads the prerequisite: state, record or `gh` |
| `flow.py:1736-1741` | if refused, it records a note and the key in `busy`, and goes no further down |
| `flow.py:1760-1763` | a refused prerequisite blocks the merge of the one above it, with no read |
| `flow.py:1791-1793` | claims this walk took are let go when it ends |
| `flow.py:827-829`, `:896-900`, `:978` | `_runnable` holds the dependent, on its own line, with no `gh` read |
| `drive_claim.py:227-230` | new `Run.holds`, so the walk never lets go of a claim it did not take |

The hold line:

> flow: issue_D held — prerequisite(s) issue_P not known to be merged into main (org/repo); not built on
> a base that may be missing them. issue_P: it is held by another live `flow` run (pid 12), so this run did
> not judge or merge it; let that run finish (or stop it), then re-run.

A claim that cannot be recorded takes the same path, with its own reason and remedy, because
`drive_claim.py:21-26` says that fails closed.

Docs: `docs/07-crosscutting.md:584-590` and `:996-1001`, `docs/11-troubleshooting.md:94-96`, and the
docstrings at `drive_claim.py:8`, `:19-20`, `merge.py:111` and `flow.py:1690-1698`.

## Two calls you may want to overrule

**1. A claimed prerequisite holds its dependent even if its PR has merged or it ships nothing.** That is
your wording ("hold its dependents when another run holds the claim") and Codex's. It has a real cost. A
run keeps its drive-set claims for its whole life, so if run A merges P at a wave boundary and then builds
for hours, run B's D waits until A ends, though P is already on `main`. The hold is safe, and a re-run
clears it.

To release on a merge instead, move the check below the merge read in `_runnable`, three lines moved:

```diff
-                if (p.name, repo, base) in merge_busy:
-                    busy.append(p.name)
-                    continue
                 if merged.merged_into(cfg, dep, repo, base):
                     ...
                     continue
+                if (p.name, repo, base) in merge_busy:
+                    busy.append(p.name)
+                    continue
```

That adds one `gh` read of a bundle another run holds, and readies or merges nothing.
`test_a_merged_prereq_another_run_holds_holds_too` and `test_a_close_prereq_another_run_holds_holds_too`
(`test_merge_resume_stranded_prereq.py:1923`, `:1937`) would flip. I did not build this.

**2. The walk keeps every claim it took until it ends, including on prerequisites it will not merge.** So
during that step another run naming one of those bundles is refused, and a sweep skips it. With
`merge_wait_secs = 300`, each marked prerequisite can add about 5 minutes or more to that window. Letting
go early saves that, but it needs the `claimed` cache and `ours` list reworked and a re-take before the
blocker read, which I estimate at 8-10 lines. I kept it simple because the window is short and a re-run
clears it.

## What I ruled out

- **Checking drive-set names instead of adding `Run.holds`.** `{b.name for b in bundles}` is about 2 lines
  against about 6 for `holds` and its call, but `drive_claim.py:39-40` says a symlinked alias shares its
  bundle's claim. Name matching would release a drive-set claim reached through an alias. `holds` reads
  the fact itself. No test uses an alias: that part follows from `_claim_file`, and I did not exercise it.
- **Keeping prerequisite claims for the whole run**, as drive-set claims are kept. Run A would then hold
  up every other run's dependents of P for hours, after A has already finished with P.
- **Printing the claim hold on the existing `not merged` line.** Nothing was read, so "not merged" could be
  false. Likewise the chain note says "not known to be merged" only when a blocker is claimed
  (`flow.py:1768`), and keeps the text you accepted otherwise.

## Left as is

- **Reads outside the claim.** A split child adopted mid-run is not walked, so `_runnable` reads its
  prerequisite's record with no claim. That is a read only, and it merges nothing. The walk runs once.
- **Single-step verbs.** `pdca publish` and `pdca signoff` take no claim, as `drive_claim.py:43-47` already
  documents.
- **Your §10 follow-ups are unchanged:** the same-run wave-boundary merge of an old head, `merged_into` not
  checking the hash, and the `fork-discipline.md.jinja:74` wording.

## Size

`patch.diff` is 180 KB against the 125 KB backstop, up from 152 KB, so that §6 item fires again. Most of it
is the test file (2,185 lines, 375 of them new). `sizing.json` already proposes the split.

## Refutation

**(a) Genuine red? Yes.** `run-verify.sh` reverted the production hunks and reported `C4 PASS — red without
the fix, green with it`:

| Module | Green leg | Red leg |
|---|---|---|
| `test_merge_resume_stranded_prereq` | 128 tests, OK | `failures=159, errors=14` (counts include subtests) |
| `test_flow_out_of_batch_prereq_hold` | 31 tests, OK | `failures=1` (the rewrite the brief names) |
| `test_merge_review_remarks` | 30 tests, OK | 30 tests, OK (only its count was narrowed) |

109 of the 128 tests go red. I read the errors. Most are behaviour: a dependent built when it should be
held, or a merge that never happened. Some come from symbols the fix adds (`merged.patch_hash`,
`merged.has_patch`, `_merge_one(held=…)`), so those fail on the missing symbol, not on behaviour.

16 of the 21 new tests go red. The 5 that stay green are guards against doing too much, or only bind
against code that claims:

- `test_a_merged_prereq_keeps_the_walk_off_one_another_run_holds_below_it`
- `test_a_named_prereq_another_run_holds_refuses_the_run_before_the_walk`
- `test_a_run_that_publishes_nothing_is_not_held_by_a_claim`
- `test_the_walk_claims_a_prereq_it_will_not_merge_and_lets_that_go_too`
- `test_the_walk_never_lets_go_of_what_the_run_drives`

**The check that matters for this round.** With only the claim hand-off removed, which is the last attempt's
logic on the new base, the module gives `failures=15, errors=1`.

**Mutation pass.** I broke 21 claim decisions one at a time, each on a copy of the source, and the module
caught all 21. They include: claims not passed, a refusal ignored, the claim taken after judging, `_runnable`
ignoring it, blockers ignoring it, claims never let go, drive-set claims let go, `holds` always true or false,
a peek instead of a real claim, and the hold line losing its reason or way out.

**(b) Production path? Yes.** Most new tests go through the real `cli._flow`, which makes the run's claim
scope, into `flow_ids`, `_drive_and_act`, `_merge_prereqs`, `_runnable`, `_merge_one`, `merged_into` and
`worktree.ensure`, with real `drive_claim.Run` locks on real files. The sweep has its own case through
`flow_batch`. Only `gh`, the build leaf's work and the publish leaf are stubbed.

**(c) Fixture includes the fault? Yes.** Another run holds P's real lock while P is marked and open with a
green rollup, so only the claim stops the merge. That is Codex's probe
(`test_a_prereq_another_run_holds_is_not_touched_and_holds_its_dependent`, `:1880`). One case uses a real
second process, and its pid must appear on the line (`:1886`). `test_two_runs_reaching_one_marked_pr_never_both_touch_it`
(`:2076`) runs the race itself: a second run starts during the first run's `gh pr ready` on P. It is held, P
is readied and merged once, and it builds after a re-run.

**Not tested on a live host:** the `gh` calls are stubbed, as in every earlier round.

## What I ran

The driver's gates cannot run yet (see the top), so I ran the same scripts by hand, from the instance root
with `PDCA_BUNDLE` and `PDCA_WORKTREE` set.

| Check | Tree | Result |
|---|---|---|
| `engine/scripts/run-verify.sh` (C4) | `fcc18c9` + final patch | pass |
| `engine/scripts/run-suite.sh` (T3) | `fcc18c9` + final patch | root suite 50 tests OK, driver suite 2945 OK (skipped=2) |
| `engine/scripts/run-host-ci.sh` | `fcc18c9` + final patch | clean |
| `engine/scripts/run-prod-path.py` (C5) | `fcc18c9` + final patch | pass |
| `engine/scripts/run-docs-check.sh` (T2) | `b19b5c1` + final patch | docs lint, site render and link audit clean |
| The 3 changed modules plus `test_flow_single_driver` | `b19b5c1` + final patch | 212 tests OK |
| Claim module, 2 more runs to look for flakiness | before the last test was added | OK each time |

I did not re-run the full suite on `b19b5c1`. The commits since `fcc18c9` are docs only.

**Not run:** T4 (`contribcheck`), which needs the publish texts and runs at publish.

**Formatter and hooks:** the target has no pre-commit or ruff config, and `docs/INTEGRATION.md` names no
formatter, so there was nothing to run. `git diff --check` is clean, an `ast` script found no unused imports
in the changed Python files (pyflakes is not installed), and no added line is over 100 columns. The DCO
`Signed-off-by` is added by publish's commit.

## Process notes

- **I read beyond the brief.** The carry-forward points at `iteration-v4/`, so I read that attempt's patch,
  notes, reviews and `SUMMARY.md`. I read Codex's finding on #859 with read-only `gh` calls. To place the
  fix and trace the marker I read much more of the target than the brief cites, plus `pdca.toml`,
  `docs/INTEGRATION.md` and the engine scripts. Listing the bundle also printed `sizing.json`,
  `loop-telemetry.json` and `deferred-findings.json` (which is empty).
- **I moved the worktree's HEAD**, from `f5321ab` to `origin/main`, with `git checkout --detach`. The next
  gate read resets it anyway.
- **The builder guard blocked one command**, because a Python heredoc editing a docstring had `gh pr` next to
  backticks. It ran nothing. I made those edits with the Edit tool instead.
- **A delete in my mutation script.** Its first version had a `shutil.rmtree` for a mutant folder left by an
  earlier run. No such folder existed, so it never fired, and I removed it. Mutants now go in a new folder
  each run.
- **Production source was not edited for checks,** except by `run-verify.sh` itself, which restores it. After
  the gates I confirmed the tree matches `patch.diff` (`cmp` on the full diff).
- **Left behind:** gitignored working files in the worktree's `.cache/v5/` (logs, mutants, scripts, a private
  git index), which the next gate read wipes, so the tables above are the record; `git add -N` on the new
  test, so `git diff` includes it; and the empty `prod.tmp.diff` in the bundle from an earlier attempt.
- The bundle also holds a copy of the test file, identical to the one in `patch.diff`.
