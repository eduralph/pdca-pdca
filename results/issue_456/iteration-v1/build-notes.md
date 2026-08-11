# Build notes — issue #456 (split-lineage-record)

## What changed and why

`template/src/pdca_harness/split.py`:

- New constants `LINEAGE = "split-lineage.json"` and `LINEAGE_VERSION = 1`
  (`split.py:36-41`, adjacent to `PROPOSAL`).
- `_bundle_id(bundle)` — the tracker id encoded in `issue_<id>`, deliberately
  more permissive than the existing `_parent_number` (which restricts to
  digits only, because it feeds `gh issue create --parent`). A lineage id can
  be any token `validate()` accepts (`[A-Za-z0-9._-]+`).
- `read_lineage(bundle)` — the one tolerant reader the brief's item 4
  requires: absent file, unreadable (I/O error), malformed JSON, a non-object
  payload, or the wrong `version` all return `None`; nothing raises.
- `_merge_parent_lineage(parent, children_ids)` — builds the parent's
  post-accept record by reading whatever is already there and carrying
  `parent` / `siblings` / `depth` forward untouched, then setting `children`.
  This is the fix for the previous attempt's defect (brief item 3): that
  attempt replaced the record wholesale with a `role`-discriminated one, so a
  parent that was itself a depth-1 child lost its `parent`/`siblings` edges
  the moment it was split again.
- `materialise()` now takes a required `parent` kwarg and writes each child's
  `split-lineage.json` into the *same staged directory* as `brief.md`
  (`split.py` — the loop now writes two files per staged child), so it moves
  atomically with the rest under `accept`'s existing staging discipline
  (`split.py:406-427`, unchanged). `materialise`'s only caller is `accept`
  (confirmed via `grep -rn "materialise("`), so widening its signature is
  safe.
- `accept()` writes the parent's merged lineage record in the same
  try/except region that archives the abandoned attempt and writes
  `build-notes.md` + `CLOSE_MARKER`, and **before** both of those — matching
  the brief's item 6 ("the parent's record is written before CLOSE_MARKER").
  Prior bytes are captured before the block runs; on any exception in that
  block the prior bytes are restored (or the file is removed if there were
  none), on top of the existing `_rollback(created)` + marker-unlink
  discipline.

`docs/07-crosscutting.md` — one new paragraph under `### The split`
(`:174-218` region cited by the brief) describing the artifact, its schema,
the merge behaviour, and its deliberate absence from
`state.DOWNSTREAM_OF_BRIEF`.

`template/tests/test_split_lineage.py` — new module, `from pdca_harness import
split` only (per the brief's ImportError-vs-AttributeError instruction), plus
`from pdca_harness import state` for the one assertion that needs
`DOWNSTREAM_OF_BRIEF` by name (import of the `state` module itself is
pre-existing API, so this does not reintroduce the ImportError risk — only a
`from pdca_harness.split import <new_name>` would).

## Alternatives considered and ruled out

- **A `role` field ("parent"/"child"/"both").** Explicitly rejected by the
  brief's schema section — one filename with one role field cannot express a
  bundle that is both, which is exactly the previous attempt's shipped
  defect. Not re-attempted.
- **Two files** (`split-lineage-child.json` + `split-lineage-parent.json`).
  Ruled out by the brief for the same reason two files were rejected there:
  they can drift, and #449 needs the parent→children edge in the same place
  children 2-4 need the child→parent/siblings edge. Implementing two files
  would be a **larger** diff for a schema the brief already settled against —
  no cost sketch needed since the brief forecloses the option outright.
- **Passing `parent_id: str` into `materialise()` instead of `parent: Path`.**
  Considered, but `materialise()` also needs the parent's *current* lineage
  record (to compute `depth`), so it needs the directory, not just the
  id — passing both would mean deriving the id from the path anyway at every
  call site. One `parent: Path` kwarg is fewer moving parts.
- **Adding `LINEAGE` to `state.DOWNSTREAM_OF_BRIEF`.** Explicitly out of
  scope per the brief ("its *absence* from it is the point") — never
  attempted; `test_lineage_filename_is_not_in_downstream_of_brief` in the new
  test module asserts this by name, per the brief's instruction not to bury
  it in a comment.

## Refutation (the three questions)

**(a) Genuine red?** Yes — confirmed both by hand and by the project's own
runner. `cd template && PYTHONPATH=src python3 -m unittest tests.test_split_lineage`
with `split.py` reverted to `main` (i.e. the pre-fix state) produces
`AttributeError: module 'pdca_harness.split' has no attribute 'read_lineage'`
/ `'LINEAGE'` for every one of the 14 tests — a real `AttributeError`, not an
`ImportError` (confirmed by importing only the module, never the new
symbols, per the brief's instruction). Also confirmed through
`engine/scripts/run-verify.sh` (the project's C4 gate, run from `pdca-pdca`
with `PDCA_BUNDLE`/`PDCA_WORKTREE` set) — its red leg reverts only the
production hunks (test file untouched) and reports "Ran 14 tests … FAILED
(errors=14)", then `C4 PASS: red without the fix, green with it`, exit 0.

**(b) Production path?** Yes. The test drives `split.accept`, `split.materialise`
(indirectly, through `accept`), `split.read_lineage`, and
`state.DOWNSTREAM_OF_BRIEF` directly — the real production functions in
`template/src/pdca_harness/split.py`, not a copy or a stand-in. No mocking of
the lineage logic itself; the one `mock.patch.object(Path, "write_text", …)`
in the two failure-path tests only injects a write failure at
`build-notes.md` to exercise the rollback branch — the lineage
read/merge/write code under test runs unmocked in every test.

**(c) Fixture includes the fault?** Yes. `test_a_parent_that_is_itself_a_child_keeps_both_edges`
and `test_depth_accumulates_through_a_mixed_role_parent` construct exactly
the reproduction the brief names: a parent bundle that already carries a
child's `split-lineage.json` (`parent`/`siblings`/`depth` set), then runs a
real `split.accept` on it and asserts all three of the parent's own edges
survive **and** `children` is added — the specific case the previous attempt
got wrong (it kept only `depth`). The two rollback tests use a real forced
`OSError` mid-`accept` (not a curated success-only path) and assert the
parent's prior lineage bytes are exactly restored, `CLOSE_MARKER` is absent,
and both child bundles are gone — the actual failure element (a
build-notes.md write that fails after the lineage merge but before the
marker) is present in the fixture, not excluded.

## Verification run

```
$ cd /home/eddie/pdca/pdca-pdca
$ PDCA_BUNDLE=.../results/issue_456 PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt \
    ./engine/scripts/run-verify.sh
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_split_lineage.py
Ran 14 tests in 0.065s
OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 14 tests in 0.016s
FAILED (errors=14)
C4 PASS: red without the fix, green with it
$ echo $?
0
```

Also re-ran the full offline suite (`cd template && PYTHONPATH=src python3 -m
unittest discover -s tests`) post-fix: **1613 tests, OK (skipped=2)** — no
regression in the pre-existing `test_split.py` (96 tests, all pass) or
elsewhere. Ran the target's own docs checkers since this patch touches
`docs/07-crosscutting.md`: `python3 docs/publishing/tools/lint_docs.py` →
`lint_docs: OK`; `python3 docs/publishing/tools/render_site.py --check` →
`render_site: link audit OK`.

## External dependencies

None beyond what the brief listed. `copier` was not needed to build or
verify this slice — the seven copier-gated tests are outside
`template/tests/` and this patch doesn't touch `copier.yml` or the template's
Jinja surface, so they're unaffected either way; not verified here since the
brief scopes the render/`copier update` compatibility suites as the target
root's own concern, not this bundle's C4 gate.

## Scope discipline

Touched only `template/src/pdca_harness/split.py`, one `docs/07-crosscutting.md`
paragraph, and the new test module — exactly the brief's scope. Did not touch
`sizing.py`, `plan_policy.py`, leaf prompts, `flow.py`, `pdca.toml.jinja`, or
`state.py`'s `DOWNSTREAM_OF_BRIEF` list.
