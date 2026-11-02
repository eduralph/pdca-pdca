# Build notes — issue 464 / wave-mode-none (iteration 3)

Target: `eduralph/pdca-harness @ main`, worktree base `3c11556` (= `origin/main`).
Line numbers are on the patched tree unless marked "base".

This iteration keeps iteration 2's patch and fixes the four findings in the iteration 2
carry-forward. Everything earlier iterations did is still in the patch (summary at the end).

## The four findings and what changed

### 1. C5 — a failed publish with no later wave still exited 0

Before: the failure accounting sat inside `if k < len(wave_list) - 1` (base `flow.py:3078`),
so an independent bundle, or any bundle in the last wave, could fail to publish and the run
still returned 0 with `holds = {}`. And a `gh pr create` failure after the push counts as
pushed (`_publish_bundle`, `flow.py:642-665`), so moving the old loop alone would have missed
it, as the reviewer said.

Now:

- `flow.py:3230-3234` — a `"none"` block of its own, ahead of the carry code. It runs after
  EVERY wave, the last one too, then `continue`s. So the stack and merge block
  (from base `flow.py:3073` on) is back to its base text, byte for byte: iteration 2's edits
  inside it (the `left` message and the `continue`) are gone, and the diff has no hunk there.
- `flow.py:677-697` — `_hold_without_pr`. It looks only at bundles publish contributes (a
  patch and a usable target, `integrate._fold_candidates`):
  - this run pushed no branch → `"unpushed"` (`integrate.unpublished`, the same test stack
    mode uses, so a stale record from an earlier attempt does not count);
  - branch pushed, no PR url on record → a new reason, `"no-pr"`. This reads the publication
    outcome itself, which is what the reviewer asked for.
- `flow.py:3340` — `"no-pr"` goes into `holds`. `cli._results_rc` turns any hold into 3, so
  no code change was needed there, only its docstring (`cli.py:739-741`).

Result: independent bundles, a single-id run and the last wave of a batch all exit 3 when a
publish leaves no PR. Stack mode keeps its answer on purpose (pinned by
`test_stack_mode_keeps_its_answer_for_a_failed_publish`): the brief rules out any change to
it, so its last-wave gap remains. It is unchanged, and you may want a separate issue for it.

### 2. A prerequisite with no `Repo + branch target` blocked its dependent forever

Now `flow.py:858-863`: if `integrate._fold_candidates([p])` is empty, no PR of `p` can ever
exist, so there is nothing to wait for and `p` counts as ready. That covers a no-patch
prerequisite (`merged.merged_into` already said True) and a patched one with no usable
target (publish skips it, and `integrate.unpublished` at `integrate.py:263` excludes it).
The second kind prints one stderr line, because the dependent is built without its work.
Same result as stack mode for the same input: both built, exit 0
(`test_a_prerequisite_with_no_target_builds_its_dependent_in_stack_mode_too`).

### 3. A `gh` failure looked like "not merged yet" and exited 3

Now `flow.py:871-875`: `merged.pr_state` is read first. `None` goes to a new `unreadable` list
with its own line (`flow.py:955-959`, "could not be read … make sure `gh` can read their
PR"). The dependent is not added to `waiting`, so it is PLANNED with no hold: exit 1, the same
as stack mode. Covers `gh` failing and `gh` missing (`_pr_view` guards the `OSError`).

### 4. A chain got no hold past the first dependent

Now `flow.py:847-852`: a prerequisite that is not COMPLETE but is in `waiting` puts `d` in
`behind`, and `d` is recorded as waiting too. `waiting` changed from a set to a dict: bundle →
the merges it waits for, in order (`flow.py:1021`). `d`'s line then names the whole order
(`flow.py:943-954`), e.g.:

    flow: issue_12 held — prerequisite(s) issue_11 not merged into main (org/repo) (issue_11
    not built yet, held for issue_10); wave_mode = "none" builds every bundle on main itself,
    so it is not built on a base missing them. To build it, merge the PRs of issue_10,
    issue_11 in that order, re-running after each merge.

Exit 3 at every link, then 0 once the last has merged. A chain above a real failure (no PR, an
unreadable PR) is not a wait: the top link stays `"skipped — not ready"` and the run exits 1.
An untargeted dependent keeps #186's "not ready", as it does for a direct edge.

## Two things beyond the four, for the same reason

- **A fetched base that cannot be checked now exits 1, not 3** (`flow.py:1019-1020`, the
  `all(known …)` clause). It was a deferred finding, and iteration 2 flagged it as a one-line
  choice. Finding 3's reasoning applies word for word ("every run looks like a normal hold
  while the host cannot be asked"), and leaving it would make an unreadable PR exit 1 but an
  unfetchable base exit 3. Leg (b2) only asks for "still held". A base known to lack the merge
  stays `"unmerged"`, exit 3. Clear or reverse this at sign-off: it is one clause.
- **A closed PR gets a re-open step** (`flow.py:880-881`, `:947`). Without it the line says
  "merge their PR" for a PR that cannot be merged, the class of fault finding 2 names. The
  carry already treats CLOSED as needing a re-open (`flow.py:1427-1428`, `_CARRY_HINTS` at
  `flow.py:1446`).
  Still a hold, exit 3: nothing failed, and it waits on a human.

## Choices the human should confirm at sign-off

1. Leg (c) (config validation) is in scope — the brief flags it.
2. A dry-run holds nothing (decided in iteration 2).
3. **A no-target prerequisite counts as ready**, and the dependent is built without its work,
   with a stderr line. The alternative is to hold it with a line saying it can never land.
   I chose ready because that hold has no way out except editing a brief, and stack mode
   builds both. The brief's general rule, read strictly, would hold it.
4. **`"no-pr"` and `"unpushed"` exit 3, not 1.** Same as stack mode's `"unpushed"`, and the
   reviewer called exit 3 visible. If you want a failed publish to read as failed, add both to
   `cli._FAILED_REASONS` (`cli.py:715`): that is one line for `"no-pr"`, but `"unpushed"` is
   shared with stack mode, so it would need splitting.
5. An unreadable PR and an uncheckable base exit 1 (above).

## Not addressed — still open for you

These stay in `deferred-findings.json`. I changed nothing for them:

- **A prerequisite on another base or repo, or an `Onto branch` one, can never release its
  dependent**, and the line says "merge their PR into main" (`merged.py:109-115`). The brief
  asks for exactly this rule, so it is a scope call.
- **An iterated prerequisite whose re-publish cannot open a second PR.** I confirmed the
  flow's side with a probe: `gh pr create` fails on the second publish, `publish.json` gets
  `pr_url: ""` (`publish.py:412-452`), the bundle is `"no-pr"`, the dependent is held for "no
  PR on record", and the advice (`pdca publish 10`) would hit the same refusal. My probe stubs
  `gh`, so I have not seen real `gh` refuse it. The real fix belongs in publish: on that
  failure, look up the open PR for the branch (`_existing_pr`, `publish.py:582`, already does
  this for `Onto branch`) and record it. It would change stack mode's record too, which is why
  I left it.
- **A stale `stack-base` marker outside a flow** (advisory, not tagged). Inside `pdca flow` the
  marker is cleared (`flow.py:3169`, `_point_at_integration` → `publish.clear_stack_base`), and
  a probe confirmed it. A standalone `pdca publish` after switching mode still reads it. The
  PR still opens against the real base (`publish.py:253`, `:284`), but is cut from the line
  commit. Closing it takes three sites (`publish.py:238`, `:761`, `gates.py:568`) and a decision
  about what happens when a patch built on the line does not apply to the base. It only
  bites a mode switch with bundles in flight.
- **Two reference docs still list only two values**: `template/PCDA/quality-cycle/08-glossary.md:290`
  and `template/PCDA/quality-cycle/09-parallel-lanes.md:67`. The brief's scope names only the
  jinja block and `docs/07-crosscutting.md`, so I left them. About 5 lines if you want them.

## Alternatives ruled out (with cost)

- **Ask `merged_into` first, then `pr_state` only when it says False:** 2 `gh` reads on the
  common OPEN path, against 1 now. The chosen order costs 2 reads only once a PR has merged.
- **Make `merged_into` return three states:** about 6 lines in `merged.py`, in a function stack
  mode's holds also call, to save one `gh` read on the MERGED path. Not worth touching it.
- **Reuse `"unpushed"` for a pushed branch with no PR:** 2 lines smaller (no `held_no_pr` set,
  no `holds` line), same exit code. But `holds` would say "unpushed" about a branch that is on
  origin. I kept the reason honest for 2 lines.
- **Keep `waiting` a set and name only the direct prerequisite:** 3 lines smaller, but the line
  could not say which merge comes first in a chain longer than two, which is the way out the
  brief asks for.
- **Run the accounting by moving the existing stack-mode loop out of the guard:** it would
  change stack mode's exit code for a last-wave failure (0 → 3), which the brief rules out, and
  still miss the pushed-with-no-PR case.

## Test — `template/tests/test_flow_wave_mode_none.py` (43 cases)

Drives `flow._drive_and_act` on `StackFoldGit` (loaded by path, as
`test_flow_same_wave_conflict.py:36-39`); the three `test_pdca_flow_*` cases go through
`cli._flow`, so their exit code is the one the process returns. Stubbed: the build and sign-off
leaves (`flow._drive_wave`), drafting of the publish texts (`publish.draft_texts`), and `gh` (in
front of `subprocess.run`). NOT stubbed: `_runnable`, `_hold_without_pr`, `_publish_bundle` →
`publish.publish` (real cut, commit, push to the bare origin), `integrate.unpublished`,
`merged.pr_state`, `merged.merged_into`, `_base_lacks_merge` (real fetch and ancestry),
`worktree._target`, `Config.load`, `cli._results_rc`, `cli._waves`.

New this round:

| case | finding |
|---|---|
| independent bundle, texts fail: `"unpushed"`, exit 3, sibling published | 1 |
| independent bundle, PR not opened: `"no-pr"`, exit 3 | 1 |
| one-bundle run, publish fails: exit 3 | 1 |
| last wave of a batch, PR not opened: `"no-pr"`, exit 3 | 1 |
| no-target and no-patch bundles are not reported as having no PR: exit 0 | 1 |
| stack control: a failed publish keeps exit 0 with no later wave, and its own line with one | 1, (d) |
| no-target prerequisite: dependent built on main, note, no `gh pr view`, exit 0 | 2 |
| no-target prerequisite in stack mode: both built, exit 0, no note | 2, (d) |
| no-patch prerequisite: dependent built, no note, no `gh pr view`, exit 0 | 2 |
| `gh pr view` fails: held "could not be read", exit 1; `gh` back: ordinary hold, exit 3 | 3 |
| `gh` missing: same, exit 1 | 3 |
| fetch fails after the merge: held "is not known to have", exit 1 | above |
| 3-link chain walked to the end: exit 3, 3, 0, each PR on main | 4 |
| 4-link chain names every merge in order | 4 |
| chain through `Stacks on` and `Depends on (merged)` | 4 |
| two paths to one prerequisite: each merge named once | 4 |
| chain above a failed publish: exit 1, top link "not ready" | 4 |
| chain above an unreadable PR: exit 1 | 4 |
| a wait and a failure together: not counted as waiting, exit 1 | 4 |
| untargeted dependent behind a chain: "not ready", exit 1 | 4 |
| `pdca flow` itself: a chain exits 3, 3, 0; one id exits 3; a host fault exits 1 | criterion (a) |
| closed PR: re-open step named, exit 3 | above |
| squash merge with the branch deleted: dependent released | extra |
| merge into another base does not release the dependent | `merged_into` still decides |
| stack control extended to a 3-link chain: a line, all built, exit 0 | (d) |

The 17 cases from iteration 2 stay, plus 26 new. Two existing cases changed: the PR-not-opened
case now expects `{"10": "no-pr"}` where it expected `{}`, and the stack control grew to the
3-link chain in the last row.

## Refuting my own test

- **(a) Genuine red? Yes.** The project's C4 runner (`engine/scripts/run-verify.sh`,
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set, under `timeout 900`), on the final `patch.diff`: green leg
  `Ran 43 tests … OK`; red leg (production hunks reverted, test kept) `Ran 43 tests … FAILED
  (failures=35)`, no errors, no import failure, `PDCA-EVIDENCE: C4 PASS — red without the fix,
  green with it`. An earlier run had one `IndexError` in the red leg, so I made that case assert
  the hold first: every red is now an assertion. The 8 that stay green without the fix are
  controls by design: the 3 stack-mode cases, known values load, `--no-publish`, the no-patch
  prerequisite, bundles publish skips, and `test_pdca_flow_exits_1_when_the_host_cannot_be_asked`
  (stack mode's #647 hold already exits 1 there; the binding case for that fault is
  `test_a_pr_the_host_cannot_read_is_not_a_wait_for_a_merge`).
- **Against iteration 2's production code** (test kept, v2 production hunks swapped in, then
  swapped back; the worktree diff is byte-identical to `patch.diff` afterwards, checked with
  `cmp`): `Ran 43 tests … FAILED (failures=19)`, all assertions, no errors: the last-wave, no-PR,
  no-target, unreadable-PR, fetch, chain and closed-PR cases. So the new cases bind this round's
  findings. `test_pdca_flow_exits_1_when_the_host_cannot_be_asked` is one of the 19: green on
  the base, red on iteration 2, which exited 3.
- **Mutations** (`.cache/mutate3.py`, git-ignored): 22, each applied alone to the final `flow.py`,
  each run through the test module, file restored after each (same sha256 before and after).
  All 22 went red, none survived. Examples: accounting skipped on the last wave → 5 red;
  pushed-with-no-PR not recorded → 3; no-target treated as unpublished → 1; unreadable treated
  as OPEN → 4; unknown base counted as waiting → 1; no chain handling → 6; chain ignores the
  dependent's target → 1; chain message loses earlier merges → 2; `"none"` falls through to the
  fold → 9; accounting runs in a dry-run → 2; PR state decides without `merged_into` → 1.
- **(b) Production path? Yes.** See the not-stubbed list above. The failed publishes are real:
  `draft_texts` returning False makes `_drive_and_act` skip `_publish_bundle`; a failing `gh pr
  create` reaches the real `publish.publish` after its real push, which writes `pr_url: ""`. The
  unreadable PR goes through the real `merged.pr_state`, the missing `gh` raises the real
  `FileNotFoundError` shape, and the fetch failure is a real `git fetch` against a remote URL
  that does not exist. The stubbed pieces are the model leaves and the `gh` host, as peer tests
  stub them.
- **(c) Fixture includes the fault? Yes.** Each case has the real fault in it: no `publish.json`
  at all; a pushed branch on the bare origin with `pr_url: ""`; a real stale record from a real
  earlier publish; a patched bundle with no target line in its brief; a real unreachable origin
  for the fetch; a real squash merge and a really deleted branch on the bare origin; a chain whose
  middle link really stays PLANNED. The bare origin can show an integration line (the stack
  control sees one), so "no line in `"none"`" is not vacuous.

I also ran throwaway probes (`.cache/probe3.py`, not in the patch) on inputs the tests do not
drive: a patch that does not apply in the last wave (`"unpushed"`, exit 3), a stale record with
failed texts in the last wave (`"unpushed"`, exit 3), a fork layout with `base_remote =
upstream` (built from and cut from `upstream/main`, PR on main, exit 3 then 0), a mode switch
with the prerequisite still open (`"unmerged"`, exit 3), and a stale stack-base marker in a flow
(cleared, built on `origin/main`).

## Other gates run

- **T3 (`engine/scripts/run-suite.sh`, under `timeout 3000`, on the final patch):** root suite
  `Ran 50 tests … OK`, no skips, so render and update-compat ran with copier over the changed
  `pdca.toml.jinja` (`test_render_then_slice`, `test_merge_leaves_no_conflict_markers`,
  `test_merged_config_still_loads`). Driver suite `Ran 2690 tests … OK (skipped=2)` (iteration 2:
  2664; +26 new here; the 2 skips are elsewhere). So (d) holds: the stack- and merge-mode suites
  are unchanged and green.
- **T2 (`engine/scripts/run-docs-check.sh`, under `timeout 900`):** `lint_docs: OK`,
  `render_site: link audit OK` (22 pages). The CI link checker
  (`.github/docs-check/docs_links.py`): 458 relative links in 67 files, 0 broken.
- **C5 (`engine/scripts/run-prod-path.py`):** `1 added driver-suite test(s) import the production
  package 'pdca_harness'`.
- **Host CI parity (`engine/scripts/run-host-ci.sh`, run from the patched tree):** docs lint
  clean, site render and link audit clean. My first try ran it from the instance root and it
  reported "unverifiable", because the script expects to start in the tree it checks.
- **Not run:** T4. It audits the contribution texts, which are drafted at publish.

## Commit-ready

The target has no pre-commit hooks, no `core.hooksPath`, and no formatter or linter config (no
`.pre-commit-config.yaml`, no ruff/black/flake8 settings); its CI is render-check, docs-check,
docs-immutability, DCO. Every line this patch adds outside the test is ≤ 100 columns, as is the
test. `git apply --cached --check --whitespace=error-all` of `patch.diff` against a fresh
`origin/main` index passes. DCO sign-off is added by publish (`git commit -s`).

## Housekeeping

- The builder guard hook blocked one of my Bash commands: a heredoc that wrote an edit script
  contained the text of a `gh` command beside backticks, which it cannot verify statically. It
  ran no `gh` command. I did not try to get past the check; I made those edits with the Edit tool.
- The worktree's `.cache/` (git-ignored) holds the logs, `mutate3.py`, `probe3.py`, `check-index`
  (the throwaway index for the apply check) and other scratch files. None of it is in the patch.
  Not removed (cleanup is the harness's).
- Beyond `brief.md` I read `iteration-v2/` because the carry-forward block points at it, and the
  source files the brief and the findings cite. I did not read the conformance ruleset.
- For quick runs while editing I used the test command INTEGRATION §3 names, under `timeout`.
  All evidence above comes from the C4 and T3 wrappers, except the mutations and probes.

## What earlier iterations did, still in this patch

- `config.py:42` `WAVE_MODES`; `config.py:743-747` (base `config.py:733`) unknown value → note,
  falls back to `"stack"`, same shape as `merge_requires` (base `config.py:738-742`).
- `flow.py:3029` (base :2888) no `_carry_finished` in `"none"`; `flow.py:3042` (base :2901)
  `hold_unmerged` False, so `own_bases` is False: no `_base_plans` / `_bundle_bases`, and
  `_point_at_integration` with an empty `integ` clears stale markers.
- `flow.py:3052-3053` `wait_for_merge`: publishing on, `"none"`, not a dry-run.
- `flow.py:3088-3090` (base :2936-2938) `conflicts=None` in `"none"`: a `Conflicts with` edge
  only orders the build.
- `flow.py:864-870` a prerequisite with no PR of its accepted work on record → `unpublished`,
  with its own line (`flow.py:960-967`), exit 1.
- `flow.py:885-892` the #729 check, `_base_lacks_merge`, runs with no line (base `flow.py:807-809`
  skipped it).
- `cli.py:706-710` `_UNMERGED_HOLD`, `_UNBUILT_HOLDS`; `cli.py:760` (base :741) counts it as
  held before built → exit 3; `cli.py:1119-1122` (base :1099-1100) `pdca waves` wording.
- `publish.py:241` (base :239) no "Stacks on with no branch" refusal in `"none"`; `publish.py:771`
  (base :765) `_stacks_on_branch` → None in `"none"`, so publish cuts from `origin/<base>` (base
  :265) and opens against the base (base :282).
- `docs/07-crosscutting.md:914-958` and `template/pdca.toml.jinja:127-137`, updated this round for
  chains, no-PR reporting, faults and closed PRs.
