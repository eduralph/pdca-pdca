# Build notes — issue 464 / wave-mode-none (iteration 4)

Target: `eduralph/pdca-harness @ main`, worktree base `3c11556` (= `origin/main`).
Line numbers are on the patched tree unless marked "base".

This iteration keeps iteration 3's patch and fixes the findings in the iteration 3
carry-forward. Everything earlier iterations did is still in the patch (summary at the end).

## The findings and what changed

### 1. C5 — a fault on a second `gh` read became an ordinary hold (exit 3)

Before: `_runnable` read the PR with `merged.pr_state`, then `merged.merged_into` read it again.
If the second read failed, `merged_into` said False, and the bundle was filed as waiting for a
merge, told to merge a PR that had merged.

Now one read decides (`flow.py:914`). `merged.merged_into` is no longer called on this path. Its
record rule moved to `merged.lands_on` (`merged.py:119`), which `merged_into` also uses
(`merged.py:110`, the same condition, inverted), so the rule still lives in one place. The later
`merge_and_head` read, which the #729 base check makes, already reported a failure as "not known"
(exit 1). The same fault now ends there.

### 2. T5 — the promised host-free rehearsal, and an out-of-run `Depends on (merged)`

I kept the gate and documented it. This is a choice for you (below). In a `--no-publish` or stub
run under `"none"`, plain edges still wait for nothing and ask no host. An out-of-batch `Depends on
(merged)` keeps #186's gate: it reads the PR, holds the bundle, exits 1. That is what stack mode
does, so the docs' "as in the other modes" is now true. Two changes:

- `flow.py:982`: under `"none"` that line no longer says "no line of this run carries them".
- `docs/07-crosscutting.md`, the `"none"` bullet: names the exception.

### 3. An iterated prerequisite whose draft PR is still open blocked its dependents for good

Real `gh` refuses a second PR for a head and base, and publish then recorded `pr_url: ""`. Now, under
`"none"` only (`publish.py:432-433`), a refused `gh pr create` looks up the open PR of that branch and
base (`_open_pr_of_branch`, `publish.py:618`, built on the existing `_existing_pr`) and records it. The
push has already updated that PR, so it holds this work. Publish returns 0. So:

- 10 iterated with its PR open: `holds={'11': 'unmerged'}`, exit 3, "merge the PR of issue_10". After
  the merge, 11 builds, and `main` has the rebuilt text.
- A lone iterated bundle: exit 0, the same as stack mode.
- `pdca publish 10`, the way out the lines name, now works.
- The lookup filters on `--base` and `--state open`, and `_existing_pr` checks the owner, so a PR for
  another base, another fork, or an old merged PR is never taken. The call is guarded
  (`publish.py:624-627`): it runs after the push, and a raise would lose the record (#632).
- The test stub now refuses a second create as the host does, so the whole test module runs against
  that behaviour, not only the new cases.
- `gh pr create`'s failure message under `"none"` now says a PR opened by hand counts only once a
  re-run of `pdca publish` records it (`publish.py:440-441`).

### 4. One run after a failed re-publish, the dependent was released on the old, rejected PR

Each publish record now keeps the sha256 of the `patch.diff` it published (`patch_sha256`,
`publish.py:455`, `:577`). `publish.accepted_pr` (`publish.py:691`) gives the record's PR only when
that hash matches the current patch. `_runnable` (`flow.py:908`) and `_hold_without_pr`
(`flow.py:678`) read it. So the record itself says it is an earlier attempt's, in every later run.
Reproduced case: 10 iterated, texts fail, re-run, then the old PR merges. Every one of those runs now
gives `holds={}`, exit 1, "no PR of that work is on record", with no `gh pr view` at all, and 11 is
not built.

### 5. The hold could tell the user to do something that cannot help

`_no_merge_counts` (`flow.py:699`) asks, with no host call, whether any merge of the prerequisite's PR
could count for the dependent's base: the record says where the PR went, and before a current PR
exists, the brief says where one will go. If not, the bundle gets its own line (`flow.py:996`): "no
merge of their PR counts as landing on main (org/repo), so none will release issue_11", with a way out
that works (remove the edge, or rebuild the prerequisite against that base). This covers a PR for
another base or repo, open or merged, an `Onto branch` commit, a prerequisite not yet published, and a
link of a chain not yet built.

The hold itself is unchanged: `"unmerged"`, exit 3. Whether such edges should be refused up front or
count as ready is your call (it stays in the deferred list). I only fixed the line.

### 6. A chain above a merged PR the fetched base lacks got the wrong advice

`waiting` used to hold names to merge. It now holds the steps that release a bundle, each as it stands
(`flow.py:884`, `:903`, `:921`, `:934`): a merge to make, a PR to re-open, a fetch to fix, an edge to
change. So:

    flow: issue_12 held — prerequisite(s) issue_11 not merged into main (org/repo) (issue_11 not built
    yet, held too); wave_mode = "none" builds every bundle on main itself, so it is not built on a base
    missing them. To build it, make sure org/repo's checkout can fetch origin, so origin/main has the
    merge of issue_10, then merge the PR of issue_11 into main, re-running after each step.

This also fixes the same fault for a closed PR under a chain, which said "merge" for a PR that first
needs re-opening.

### Two low-severity review notes, done because they were free

- `_hold_without_pr` takes the wave's `complete` (`flow.py:3281`), not the cumulative `accepted`, so
  the "already named" checks are gone.
- Finding 1's single read removes the double `gh pr view`.

## Choices the human should confirm at sign-off

1. Leg (c) (config validation) is in scope — the brief flags it.
2. **The rehearsal exception (finding 2).** The alternative honours the bypass for every edge: one
   line (`dep in merged_deps and cfg.wave_mode != "none"` at `flow.py:942`), plus a test and the docs
   sentence. I did not take it because a real `--no-publish` build would then run on a base missing a
   prerequisite whose brief says it must be merged, where stack mode holds it. The cost of keeping the
   gate: a `"none"` dry-run with that edge can ask `gh`, and exits 1.
3. **A PR that can never land stays exit 3** (`"unmerged"`), though only a human edit can clear it.
   Nothing failed, and the brief's rule is a hold. Exit 1 would take a new hold reason or dropping
   the bundle from `waiting`: about 2 lines.
4. **A record with no `patch_sha256` counts as current** (`publish.py:691-703`). Treating it as stale
   would hold every long-merged prerequisite of an instance switching to `"none"`, and `pdca publish`
   could not clear it, since the patch no longer applies. The cost: finding 4's fault remains for a
   bundle published before this change, iterated after it, whose re-publish then fails. In that run it
   is still caught (`unpushed`); a later run takes the old record.
5. **`patch_sha256` is written in every mode.** It is one more key in `publish.json`; nothing in
   stack or merge mode reads it. The full suite shows no reader minds. I count this as within (d), but
   it is the one byte stack mode's output changes.
6. A dry-run holds nothing (decided in iteration 2); a no-target prerequisite counts as ready;
   `"no-pr"` and `"unpushed"` exit 3; an unreadable PR and an uncheckable base exit 1. All from
   iteration 3, all unchanged.

## Not addressed — still open for you

- **The deferred list** stays yours, unchanged by me: scope of leg (c), `Conflicts with` in this mode,
  and whether a PR for another base should be refused up front.
- **The adopted PR keeps its old title and description** (the publish line says so). `gh pr edit`
  would fix it, about 4 lines. Stack mode has the same gap, so I left it.
- **A PR opened by hand and merged before `pdca publish` records it** leaves no way out through the
  harness: `pdca publish` cannot apply the patch to a base that has it. The failure message warns
  about this. Removing the edge from the dependent's brief still works.
- **Stack mode keeps both faults found here**: `pr_url: ""` on a refused create (flow still counts the
  branch as pushed), and no hold for a failed publish in its last wave. The brief rules out changing
  it. Dropping `and cfg.wave_mode == "none"` at `publish.py:432` would fix the first, and would change
  that publish's rc from 1 to 0; you may want an issue for it.
- **A stale `stack-base` marker outside a flow**, and **two reference docs that list only two values**
  (`template/PCDA/quality-cycle/08-glossary.md:290`, `09-parallel-lanes.md:67`): as in iteration 3.
- **A byte-identical rebuild whose texts fail** is `"unpushed"` for that one run (dependents exit 1),
  and correct on the next, though the old PR does hold that patch. It errs toward holding, and the
  fix costs a second test of the record. Pinned by a test so it is at least visible.
- **Not run against real `gh`.** Everything here is a stub. I did check the installed `gh` (2.103.3)
  accepts `pr list --base`, `--head`, `--state`, `--json` with those fields. The refusal itself comes
  from the repo's own note (base `flow.py:651-652`). Worth one real iterate on a sandbox repo at
  sign-off; the Validation row asks for this anyway.
- **Size.** `sizing.json` calls this oversized, and each iteration has added to it. Production is
  now 354 added lines, the test 1,476. The seams it proposes are still valid; that is your call.

## Alternatives ruled out (with cost)

- **Mark a record stale at the iterate, not by hash:** about 4 lines in `driver._archive_iteration`,
  rewriting `publish.json` in every mode at every iterate. It would cover old records too. But it
  misses a `patch.diff` replaced any other way, and calls a byte-identical rebuild stale. The hash
  takes 1 line per write site, a 3-line helper and a 5-line reader.
- **Compare `patch.diff` and `publish.json` mtimes:** about 2 lines and no new field. Rejected: a clone
  or copy of `results/` reorders mtimes, and a merged prerequisite wrongly read as stale has no way
  out.
- **Keep the earlier URL when `gh pr create` fails, with no lookup:** about 3 lines. Rejected: it
  could keep a closed or merged PR's URL, the fault of finding 4 again.
- **Do the lookup first and skip `gh pr create`:** the same line count, but a `gh` call on every normal
  publish, in the mode's most common path.
- **Make `merged_into` return three states:** about 6 lines in a function stack mode's holds also call.
  `lands_on` is 3 lines plus the docstring, with stack's behaviour byte-identical.
- **In a chain, point at the blocker's line above and drop the steps:** about 8 lines smaller, but
  the top link would not name the first thing to do. Chosen: every line stands alone.

## Test — `template/tests/test_flow_wave_mode_none.py` (72 cases)

Drives `flow._drive_and_act` on `StackFoldGit` (loaded by path, as
`test_flow_same_wave_conflict.py:36-39`); the `test_pdca_flow_*` cases go through `cli._flow`, so their
exit code is the one the process returns. Stubbed: the build and sign-off leaves (`flow._drive_wave`),
drafting of the publish texts (`publish.draft_texts`), and `gh` (in front of `subprocess.run`). NOT
stubbed: `_runnable`, `_hold_without_pr`, `_no_merge_counts`, `_publish_bundle` → `publish.publish` and
`_publish_stacked` (real cut, commit, push to the bare origin), `publish.accepted_pr`,
`driver._archive_iteration` (a real iterate), `merged.pr_state`, `_base_lacks_merge`, `worktree._target`,
`Config.load`, `cli._results_rc`, `cli._waves`.

New this round:

| case | finding |
|---|---|
| first `gh pr view` good, next fails: held "not known", exit 1, then released | 1 |
| `--no-publish` / stub: out-of-run merged edge held, one read, no "line" wording, exit 1, then released | 2 |
| `--no-publish` / stub: in-run merged edge and out-of-run plain edge ask nothing | 2 |
| stack mode keeps its words about a line | 2, (d) |
| iterated, PR open: same PR recorded, branch updated, exit 3, merge releases, `main` has the new text | 3 |
| lone iterated bundle: `pdca flow` exits 0 | 3 |
| old PR merged: a new PR is opened; old PR merged and create fails: not taken | 3 |
| lookup fails: `"no-pr"`, exit 1 for the dependent; `pdca publish` clears it | 3 |
| PR opened by hand: told so, and `pdca publish` records it | 3 |
| `gh` missing on the lookup: branch still recorded | 3 |
| open PR for another base, or of another owner: not taken | 3 |
| stack and merge keep `pr_url: ""`, no lookup, exit 0 | 3, (d) |
| iterated, texts fail: held on that run, the re-run, and after the old PR merges | 4 |
| `pdca flow` exits 1 on each of those | 4 |
| `pdca publish` again: the open PR takes the work, 3 then 0, `main` has the new text | 4 |
| same patch rebuilt: `"unpushed"` that run, an ordinary hold the next | 4 |
| record with no hash still counts | 4 |
| real publish against `dev`: named, no `gh pr view`, open and merged | 5 |
| another repo on record | 5 |
| real `Onto branch` publish: named, open and after its PR merges into main | 5 |
| no PR yet: judged by the brief, for another base and for `Onto branch` | 5 |
| chain link bound for another base: named before it is built | 5 |
| rebuilt for the right base: not judged by its old record | 5 |
| a merge into a bundle's own base counts on `dev` too | 5 |
| chain above: a closed PR, a merge the fetched base lacks, a PR that cannot land | 6 |

Two existing cases changed: chain cases assert the new step wording, and the "another base" case now
does a real publish against `dev` rather than editing the record.

## Refuting my own test

- **(a) Genuine red? Yes.** The project's C4 runner (`engine/scripts/run-verify.sh`,
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout 580`), on the final `patch.diff`: green leg `Ran 72
  tests … OK`; red leg (production hunks reverted, test kept) `Ran 72 tests … FAILED (failures=61)`, no
  errors, no import failure, `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it`. An earlier run
  had 3 `IndexError`s in the red leg, so those cases now assert one hold line first (`_held_line`): every
  red is an assertion. The 61 count subtests. 12 of the 72 stay green without the fix, as controls by
  design: 5 stack-mode and other-mode cases, the 2 rehearsal cases that wait for nothing, known values
  load, `--no-publish`, the no-patch prerequisite, bundles publish skips, and
  `test_pdca_flow_exits_1_when_the_host_cannot_be_asked` (stack mode's #647 hold already exits 1 there).
- **Against iteration 3's production code** (the final test, run against a copy of iteration 3's
  sources built from `iteration-v3/patch.diff`, so the worktree was not touched): `Ran 72 tests … FAILED
  (failures=24)`, all assertions. So the new cases bind this round's findings: the host fault, the
  rehearsal's wording, the iterated PR, the stale record, the unlandable PR, and the chain steps.
- **Mutations** (`.cache/mutate4.py`, git-ignored): 43, each applied alone to a copy of the package, each
  run through the test module. 42 went red, each with assertions only. Examples: a second host read back
  → 1 red; no lookup after a refused create → 5; lookup in every mode → 2; lookup unguarded → 1; lookup
  not filtered on base → 1, or on state → 1; hash not compared → 3; record with no hash counted stale →
  1; raw record read in `_runnable` → 2; `unpushed` set not consulted → 1; unlandable check dropped → 8;
  `Onto branch` ignored → 1; brief not read before a PR exists → 3; merged PR named as a merge (the
  adversary's surviving mutant) → 1; closed PR named as a plain merge → 2.
- **The one survivor is equivalent:** `_hold_without_pr` reading the raw `pr_url` rather than
  `accepted_pr`. That line only sees bundles pushed this run, whose record was just written with the
  current hash, so the two cannot differ. I kept `accepted_pr` so there is one reader of the rule.
- **(b) Production path? Yes.** See the not-stubbed list above. An iterate is the real
  `driver._archive_iteration`, so "an iterate keeps `publish.json`" is exercised, not assumed. A refused
  create reaches the real `publish.publish` after its real force-push, and the test reads the new text
  off the bare origin. The `Onto branch` case is a real `_publish_stacked`, and the other-base case a real
  publish against a real `dev` branch. The stubbed pieces are the model leaves and the `gh` host, as peer
  tests stub them.
- **(c) Fixture includes the fault? Yes.** The stub refuses a second create for one head and base, the
  fault the last round's stub hid, and it applies to all 72 cases. Each case has the real fault in it: a
  real stale record from a real earlier publish; a real merge of the old PR into the bare origin; a `gh
  pr view` that really fails on its second read; a `gh pr list` that fails; `gh` raising as missing; an open
  PR on the host for another base or owner.

I also ran throwaway probes (`.cache/probe4.py`, not in the patch) on inputs the tests do not drive. A
fork layout with `base_remote = upstream` and an iterated open PR gave the same record, exit 3 then 0. An
adopted PR later closed said "re-open", exit 3. One prerequisite merged, one open, one closed named only
the two left. Two dependents with the host failing between them gave one hold and one fault, exit 1. A
corrupt or non-object `publish.json` gave "no PR on record", exit 1. A bundle published under stack and
depended on under `"none"` worked, with exit 3 then 0. A dry-run over a stale record asked nothing and
held nothing.

## Other gates run

All on the final `patch.diff`:

- **T3 (`engine/scripts/run-suite.sh`, under `timeout 3000`):** root suite `Ran 50 tests … OK`, no skips,
  so render and update-compat ran with copier over the changed `pdca.toml.jinja`. Driver suite `Ran 2719
  tests … OK (skipped=2)` (iteration 3: 2690; +29 new here; the 2 skips are elsewhere). So (d) holds: the
  stack- and merge-mode suites are unchanged and green, and `merged_into`'s refactor to `lands_on` broke
  nothing.
- **T2 (`engine/scripts/run-docs-check.sh`):** `docs lint clean, site render + link audit clean`. The CI
  link checker (`.github/docs-check/docs_links.py`): 458 relative links in 67 files, 0 broken.
- **C5 (`engine/scripts/run-prod-path.py`):** `1 added driver-suite test(s) import the production package
  'pdca_harness'`.
- **Host CI parity (`engine/scripts/run-host-ci.sh`, run from the patched tree):** docs lint clean, site
  render and link audit clean.
- **Not run:** T4. It audits the contribution texts, which are drafted at publish.

## Commit-ready

The target has no pre-commit hooks, no `core.hooksPath`, and no formatter or linter config (no
`.pre-commit-config.yaml`, no ruff/black/flake8 settings); its CI is render-check, docs-check,
docs-immutability, DCO. Every line this patch adds is ≤ 100 columns. `git apply --cached --check
--whitespace=error-all` of `patch.diff` against a fresh `origin/main` index passes. DCO sign-off is
added by publish (`git commit -s`).

## Housekeeping

- The builder guard hook blocked one of my Bash commands: a heredoc holding an edit script whose text
  had `gh` commands beside backticks, which it cannot verify statically. No `gh` command ran. I did not
  try to get past it. I made those edits with the Edit tool.
- The worktree's `.cache/` (git-ignored) holds the logs, `mutate4.py`, `probe4.py`, `reflow_none_bullet.py`,
  `v3tree/` (iteration 3's sources, for the comparison above) and throwaway indexes. None of it is in the
  patch. Not removed (cleanup is the harness's).
- Beyond `brief.md` I read `iteration-v3/` and `deferred-findings.json`, because the carry-forward block
  points at them, and the source files the brief and the findings cite. I did not read the conformance
  ruleset.
- For quick runs while editing I used the test command INTEGRATION §3 names, under `timeout`. The red→green
  and suite evidence below comes from the C4 and T3 wrappers. The mutation, comparison and probe runs use
  the same command against a copy of the package.

## What earlier iterations did, still in this patch

- `config.py:42` `WAVE_MODES`; `config.py:744-747` (base `config.py:733`) unknown value → note,
  falls back to `"stack"`, same shape as `merge_requires` (base `config.py:738-742`).
- `flow.py:3077` (base :2888) no `_carry_finished` in `"none"`; `flow.py:3090` (base :2901)
  `hold_unmerged` False, so `own_bases` is False: no `_base_plans` / `_bundle_bases`, and
  `_point_at_integration` with an empty `integ` clears stale markers.
- `flow.py:3101` `wait_for_merge`: publishing on, `"none"`, not a dry-run.
- `flow.py:3139` (base :2936-2938) `conflicts=None` in `"none"`: a `Conflicts with` edge only orders
  the build.
- `flow.py:3279-3283` the `"none"` block of the wave boundary: runs after every wave, the last one
  too, then `continue`s; the stack and merge block below it is byte-for-byte the base text.
- `flow.py:893-898` a prerequisite with no patch or no usable target is ready, the second with a note.
- `flow.py:927-935` the #729 check, `_base_lacks_merge`, runs with no line (base `flow.py:807-809`
  skipped it).
- `flow.py:1067-1069` an unknown fetched base, an unreadable PR, or no PR on record is not a wait:
  exit 1.
- `cli.py:706-710` `_UNMERGED_HOLD`, `_UNBUILT_HOLDS`; `cli.py:760` (base :741) counts it as
  held before built → exit 3; `cli.py:1119-1122` (base :1099-1100) `pdca waves` wording.
- `publish.py:242` (base :239) no "Stacks on with no branch" refusal in `"none"`; `publish.py:818`
  (base :765) `_stacks_on_branch` → None in `"none"`, so publish cuts from `origin/<base>` (base
  :265) and opens against the base (base :282).
- `docs/07-crosscutting.md:914-973` and `template/pdca.toml.jinja:127-138`.
