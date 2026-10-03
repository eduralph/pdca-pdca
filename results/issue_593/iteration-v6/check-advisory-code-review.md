# Advisory code review — issue 593 (stack-mode append-only fold, real-base PRs)

Lens: bugs the patch introduces, plus reuse / simplification / efficiency. Grounded on the
patched tree at `$PDCA_TARGET`. I found no correctness bug that needs a human or a Do
iteration. The fold, gone-branch, publish-guard and hold paths match the brief's contract.
The required cases (7, 8, 14b, 15) are real-git tests that check commit identity and pushes,
not just output text. C4 shows them red on the base and green with the fix, and T3 shows the
full suite green (2265 tests). Low-priority notes:

- `template/src/pdca_harness/publish.py:691` (`_line_tip_refusal`) repeats the
  "commit exists? then `merge-base --is-ancestor` → 0 yes / 1 no / anything else is a git
  failure" logic already in `template/src/pdca_harness/integrate.py:448` (`_carries`) and
  `:478` (`_in_line`). A direct import isn't possible (integrate imports publish, so the
  reverse would be circular). A small shared helper in a neutral module, or one in publish
  that integrate calls, would keep the two rc readings in sync. Optional cleanup, not a bug.
- `template/src/pdca_harness/merged.py:62` (`merged_head`) copies `is_merged`'s
  `gh pr view` call, its stderr message and its fail-closed parsing (`merged.py:32-57`),
  changing only the `--json` fields. A private `_pr_view(pr_url, fields) -> dict | None`
  used by both would remove the copy. The brief says `is_merged` must stay unchanged, so
  leaving the copy is defensible. The two functions also handle a missing `gh` binary
  differently: only the new one catches `OSError`.
- `template/src/pdca_harness/integrate.py:425` passes `d.name.removeprefix("issue_")` to
  `merged_head`, which looks the bundle up again with `cfg.find_bundle`, even though the
  caller already has `d`. It gives the same result. Mentioned only because a
  `merged_head(cfg, d)` signature would skip the lookup round-trip.
- Efficiency, minor: a real wave>0 publish now fetches `origin` up to three times before
  pushing: the tip guard (`publish.py:706`, `--prune`), `_host_ci_passes` when host CI is
  declared, and the plan's own `fetch` step (`publish.py:299`). This only matters on a
  slow remote. Clearer than reordering it.
- Side effect to be aware of: the fold (`integrate.py:522`) and the publish tip guard
  (`publish.py:706`) now run `git fetch --prune origin` in the user's primary target
  checkout. Before, it was a plain `fetch`. Stale remote-tracking refs (the local copies of
  branches deleted on origin) get dropped from that checkout. The brief asks for the prune
  ((ii-b)) and it is harmless in normal use. It is listed only because it changes the
  user's clone outside the harness's own worktree.
- `template/src/pdca_harness/flow.py:665`: the "pushed this run" signal compares
  `publish.json`'s `st_mtime_ns`. On a filesystem with coarse timestamps (FAT, some network
  mounts), a rewrite in the same tick as an earlier write would read as "not pushed". That
  errs toward holding the bundle, and a stale record always comes from an earlier run, so
  the window is effectively zero. No action needed.

No NEEDS-HUMAN items from this lens.
