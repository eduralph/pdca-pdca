# Advisory code review — issue #481

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/split.py:735-754` (`_archived_brief_source`)
  and `:757-787` (`_parent_split_brief`) only check the archived original's **Slug** field
  (`brief_mod.is_placeholder(bp)`, which reads Slug alone — see `brief.py:161-178`) before
  treating it as a valid source and copying its `Repo + branch target` field verbatim into
  the rebuilt parent brief. Nothing checks that field for emptiness or an unfilled `<…>`
  placeholder before the write. Reproduced directly against the target: an archived brief
  with an authored Slug but a still-placeholder `Repo + branch target` line makes
  `split.accept` succeed (children created, parent marked terminal with the close marker),
  and the new `parent/brief.md` it writes fails `handoff.check_planner` — exactly the
  criterion (b) the brief requires (`brief.md:29-31`: "`handoff.check_planner(parent, cfg)`
  returns `[]`"). `check_planner` (`handoff.py:131-134`) requires all three of Slug, Success
  criterion and Repo + branch target non-placeholder; `_parent_split_brief` only guarantees
  Success criterion (it rewrites that field unconditionally) and, via the Slug-only guard,
  Slug — not Repo + branch target. The realistic case the brief describes (a COMPLETE
  authored brief archived whole by `_archive_iteration`) is unaffected and is what the new
  test class exercises, so this gap is real but untested: an archived brief that is
  authored-but-incomplete (a shape `_archive_iteration` will happily archive, since it
  doesn't validate completeness either) produces a terminal split parent whose Plan
  artifact silently fails the Plan-exit contract. Worth tightening `_archived_brief_source`
  to check the same completeness `check_planner` will later demand (or reuse
  `handoff.check_planner`-style field checks) rather than only `is_placeholder`, and to
  raise `SplitError` in the pre-write validation phase the way the "no archive found" branch
  already does at `split.py:843-848`.

- `template/src/pdca_harness/split.py:732` (`_ITERATION_RE = re.compile(r"^iteration-v(\d+)$")`)
  duplicates `size_signal.py:70` (`_ITERATION_DIR`, the identical pattern) and the
  glob-then-match-then-sort-by-int shape at `size_signal.py:147-151`. Neither module exposes
  a public helper the other could import, so this isn't a straightforward reuse miss the
  patch introduced carelessly — just noting the third private copy of "parse the numbered
  `iteration-v<N>` archives" now living in the codebase (a fourth, non-regex version already
  exists in `driver.py:315-317`, `_next_iteration_no`, which only counts). Not blocking;
  a shared `iteration_archives(d) -> list[tuple[int, Path]]` helper in one module would
  remove all three/four copies if anyone touches this area again.

## Not flagged

The transaction discipline (`split.py:904-972`) is sound: `parent_had_brief` and
`brief_source` are captured in the pre-write validation phase before any write, the new
brief is written before the breadcrumb/marker so a later failure still rolls it back
(`wrote_parent_brief` gates the `unlink` in the except branch), and criterion (f) — a
parent that already has `brief.md` is never touched — is enforced structurally (the write
is inside `if not parent_had_brief:`) and is covered by
`test_a_parent_with_its_own_brief_is_untouched`. `state.py`'s restructured ladder preserves
the placeholder-brief behaviour for every pre-existing branch (verified by inspection: the
`else`/`if not has_do_artifact` split only changes what happens when a Do-artifact is
present with no brief.md — the new fall-through case — and leaves the brief-exists /
placeholder / patch-exists combinations exactly as before). No resource leaks, no
concurrency concerns (single-process, synchronous file I/O throughout), and the test class
exercises all six criteria (a)-(f) named in the brief.
