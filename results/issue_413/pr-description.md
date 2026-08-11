## Summary
**User impact:** With auto-merge mode switched on, a batch could keep going after a
wave's work broke the build. The tool merged each finished PR to hand the next round
of work a fresh starting point — but it accepted "GitHub let me merge it" as proof
the work was good. On a repository that doesn't insist on every test passing before a
merge, a failing test, or one that hadn't finished running yet, went through
unnoticed, and everything built afterwards sat on top of a broken base. The docs made
it worse: they promised the automation "never marks a PR ready and never merges",
which stopped being true for anyone who turned merge mode on.

This PR makes the tool check the pull request's own test results itself, right before
it merges, and stop the run if anything is failing, still running, or missing —
instead of trusting each repository's merge settings. The documentation now says what
actually happens, including the one case where the automation does merge, and what
guards it.

Reported in [#413](https://github.com/eduralph/pdca-harness/issues/413).

## What to look at
The new refusal path in merge mode: the tool reads the PR's check results after it
marks the PR ready and immediately before merging, and refuses to merge unless every
check has finished and none failed — a PR with nothing reported at all is refused too,
because nothing reported is not the same as everything passing. Refusing costs little:
re-run the same command once CI is green and the run picks up where it stopped. Both
the read and its verdict are printed in the run log, next to the `gh pr ready` and
`gh pr merge` lines already there, so a merge that was gated looks different from one
that wasn't.

To try it: enable `wave_mode = "merge"`, push a batch whose first PR has a failing job
that the repository does *not* mark required, and run the flow. Before this change the
PR merged and the next wave built on it; now the run stops with a message naming the
failing check. Setting `merge_requires = "required"` in `pdca.toml` restores the old
behaviour for anyone who deliberately wants the repository's own merge rules to be the
only word.

Also worth a read: the reworded draft-only rule in `template/docs/fork-discipline.md.jinja`
— it now separates what always holds (no model leaf ever readies or merges; the last PR
of a run stays a draft for you) from the one opt-in exception.

## Root cause
`_merge_one` went straight from "this bundle is COMPLETE and has a recorded PR" to the
ready-mark and the merge (`template/src/pdca_harness/merge.py:73-83` on `main`), with
`gh`'s exit code as the only verification gate — and its error text said so ("a
conflict, a failing **required** check, or no merge rights", `merge.py:86-88`). `gh pr
merge` enforces only what the host repo marks required in branch protection, so on a
thin protection config a red non-required job or an unfinished run does not stop the
merge. Nothing between the COMPLETE-state check and the merge ever consulted the check
rollup, so the module's own fail-closed doctrine — "the next wave must never build on
an unmerged base" (`merge.py:11-13`) — held only in the letter, not in its intent:
merged, but not merged *green*. `template/docs/fork-discipline.md.jinja:46-48` stated
the never-ready/never-merge rule without the merge-mode carve-out that has existed
since #279.

## Fix
- `template/src/pdca_harness/merge.py:66-124` — `_check_rollup()` reads the PR's full
  rollup with `gh pr checks <pr> --json name,bucket` and classifies it: `green` /
  `pending` / `failing` / `empty` / `unreadable`. Only `green` may merge. `pass` and
  `skipping` are completed non-failures; a bucket the harness does not recognise counts
  as failing (never guess green); no JSON at all is `empty` when gh says "no checks
  reported", `unreadable` otherwise — both refuse. The bucket vocabulary is gh's own
  (`gh pr checks --help`: pass / fail / pending / skipping / cancel), pinned in a
  comment at `merge.py:44-51`.
- `template/src/pdca_harness/merge.py:167-194` — the gate itself, placed after the
  ready-mark (`merge.py:158-165`) and immediately before the merge call
  (`merge.py:196-197`): marking a draft ready can trigger `ready_for_review` CI, so a
  rollup observed only pre-ready cannot promise green at merge time. It refuses with a
  message naming the offending check and the way out, and returns non-zero so the wave
  STOPs; on the green path it logs what it verified (`merge.py:194`).
  `merge.py:200-203` drops the stale "a failing required check" wording from the
  post-merge error.
- `template/src/pdca_harness/config.py:361-368,700-707,813` — `[driver].merge_requires`
  (`"all"`, the default, or `"required"`), parsed next to `merge_method`; an unknown
  value falls back to `"all"` with a note, so a typo cannot silently buy the looser
  behaviour. `template/pdca.toml.jinja:126-141` documents it in the rendered config.
- `template/docs/fork-discipline.md.jinja:46-60` — the draft-only rule now states what
  binds unconditionally (every model leaf; every final-wave PR) and names the one
  exception, with the two guards that stand in for the human's ready-mark: the
  per-bundle sign-off, and this rollup gate. `docs/07-crosscutting.md:486-498` — the
  merge-mode section, which enumerates `[driver].merge_method` for the operator
  enabling merge mode, gains the new fail-closed condition and `merge_requires` beside
  it, so a stopped wave reads as designed behaviour rather than a bug.

## Verification
- **Claim:** merge mode merges a non-final wave's PR only when its full check rollup is
  green at merge time — read after the ready-mark, immediately before the merge — and
  refuses on failing, pending or empty rollups regardless of the host's branch
  protection; `merge_requires = "required"` restores the old semantics on explicit
  opt-in.
- **Checked:** `template/src/pdca_harness/merge.py:167-194` on the PR branch — the gate
  sits between the ready-mark (`merge.py:158-165`) and the merge call
  (`merge.py:196-197`), so no path reaches the merge without a green verdict unless
  `merge_requires` is `"required"`.
- **Test:** `template/tests/test_merge.py:216-373` — 11 new cases: a failing
  non-required check refuses and never shells `gh pr merge`; a pending one refuses; an
  empty rollup refuses; an unreadable one refuses; skipped/neutral alongside a pass
  proceeds; an unknown bucket is failing; a check that only appears *after* `gh pr
  ready` is still caught (the stub flips its rollup on the ready call); a red member
  stops the wave before the next bundle's PR is touched; `merge_requires = "required"`
  skips the read and merges; and `[driver] merge_requires` is read through the real
  `Config.load`, not a hand-built `Config`. Red pre-fix (8 behavioural failures — the
  merge went through — plus 2 errors for the knob that does not exist yet), green
  post-fix: 21 tests OK (`cd template && PYTHONPATH=src python3 -m unittest
  tests.test_merge`). Both target suites stay green: `python3 -m unittest discover -s
  tests` and the offline driver suite, plus the docs lint and the 22-page site
  render/link audit.

Fixes #413
