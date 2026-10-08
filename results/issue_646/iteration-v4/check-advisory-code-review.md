# Advisory code review — issue_646 (stack-reissue-continues-batch-line)

Lens: correctness bugs the patch introduces, plus reuse / simplification / efficiency.
Advisory only. All gates in `check-gates.json` pass (C4 red→green per `gate-logs/C4-verify.log`,
T3 suite green). Lines below are on the patched tree at `$PDCA_TARGET`.

I found no correctness bug that blocks the success criterion. The shared
`flow._fold_and_regate` helper (`template/src/pdca_harness/flow.py:754-795`) removes the
duplicated fold + lock + tip-read + re-gate block, as the iteration-2 carry-forward asked.
Switching the in-run fold from `integ = {...}` to `integ.update(...)` is safe: the in-run
fold is cumulative and now always includes `carried`, so no target can drop out of `integ`.
The `_runnable` widening (`flow.py:719`) only affects out-of-batch ids that the carry put in
`held` and that are named in a plain `Depends on`, which matches the brief.

Smaller findings, none of which gate:

- `template/src/pdca_harness/integrate.py:527` and `:549` — `_gone_branch` calls
  `merged.merged_head` and then `merged.merge_commit`. Each one calls `merged.pr_state`
  again, which can be up to two `gh` calls each (`gh pr view` plus `gh pr list --head` when
  the recorded PR is CLOSED or `pr_url` is empty). So a squash-merged, deleted-branch
  prerequisite costs up to four host round trips per fold. The carry has already asked the
  same question at `flow.py:892`, and every later wave's fold repeats it because `carried`
  rides every fold. A simpler version calls `merged.pr_state` once in `_gone_branch` and
  reads `.head` / `.merge` from the result. This is about speed, not correctness: every
  answer comes from the same function, so they can't disagree.
- `template/src/pdca_harness/flow.py:863` — the dry-run branch of `_carry_finished` lists
  every fold candidate as "would carry", including one with no branch on record
  (`ref is None`). A real run would hold that one instead (`flow.py:886-890`). This fits
  criterion (7) ("asks no host, holds nothing"), but the plan it prints can name an id that
  the real run won't carry. Filtering on `ref is not None` here would make the plan match
  the real run without asking any host. Cosmetic.
- `template/src/pdca_harness/merged.py:171` — `_by_branch` compares
  `headRepositoryOwner.login` to the owner parsed from the checkout's remote URL, and the
  comparison is case-sensitive. This copies the existing `publish._existing_pr` rule
  (`publish.py:581-582`), so it isn't new debt in kind. But the patch now uses it in a place
  where a miss has a new effect: an owner whose case differs (for example `Eduralph` in the
  remote URL) would read as `"NONE"`, and the run would hold the dependents and say "open
  its PR by hand" even though the PR exists. Low likelihood; consider `.lower()` on both
  sides. Not filed as NEEDS-HUMAN.
- `template/src/pdca_harness/flow.py:995` and `:2223` — `stuck` (the bundles named as held
  for a blocked target) is computed once, at carry time, from the drive set as it was then.
  The wave filter at `:2223` also drops bundles that split adoption adds later. Today
  adoption can't add bundles of a blocked target, because its bundles are never driven, so
  this can't happen yet. If adoption ever reaches across targets, those bundles would be
  dropped without being named. Note only.

No NEEDS-HUMAN items from this lens.
