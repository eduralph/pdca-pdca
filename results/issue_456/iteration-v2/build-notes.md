# Build notes — issue #456 (split-lineage-record), iteration 2

Target: `eduralph/pdca-harness` @ `main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt`,
HEAD `6668172` = `origin/main`). All line citations below are **post-patch** lines in that
worktree unless marked "base".

## The carry-forward, and what changed because of it

Iteration 1 was rejected on C3 for one boundary: the parent-lineage snapshot
(`prior_lineage_bytes = lineage_path.read_bytes() if lineage_path.exists() else None`)
sat in the **gap between `accept`'s two protected regions** — after the children were
moved into place (base `split.py:406-427`), before the `try` whose `except` runs
`_rollback(created)`. A `read_bytes()` that raises there (a directory at
`split-lineage.json`, a permissions error) escaped with the children materialised and the
parent left un-marked: a part-applied accept, the exact state the module exists to
prevent.

I reproduced it rather than taking it on trust. With the snapshot put back in that gap
(mutation 2 below), against a parent holding a directory at the record path:

```
raised: IsADirectoryError [Errno 21] Is a directory: .../issue_500/split-lineage.json
child 601 left on disk: True
child 602 left on disk: True
parent marked terminal: False
```

Everything else from iteration 1 is kept as the sign-off directed (mixed-role merge,
tolerant reader, staging discipline, `DOWNSTREAM_OF_BRIEF` exclusion).

### The fix I chose, and why not the one the review suggested verbatim

The sign-off offered two routes: "move the snapshot inside the protected try … **or
otherwise ensure a snapshot-read failure triggers `_rollback(created)`**". I took a third
position on the same axis, strictly stronger than the first: **take the snapshot in the
pre-write phase**, right after `validate()` (`split.py:525-547`), and refuse the accept
with `SplitError` if the record cannot be read.

Why not literally "move it inside the try":

1. **It leaves the failure mode, it only cleans up after it.** The operator still gets
   two child bundles created and destroyed and (on the no-`--ids` path) two *real,
   un-withdrawable* tracker issues filed, for a fault that was knowable before anything
   was written. Refusing up front means nothing is staged, moved or filed —
   `moved.assert_not_called()` in `test_an_unreadable_prior_record_refuses_before_anything_is_written`
   (`test_split_lineage.py:297`) proves it.
2. **It is not actually safe as written.** The review's parenthetical — "(the restore
   logic already handles None vs bytes)" — does not hold for the very case it names. With
   a directory at the path the snapshot fails, `prior_lineage_bytes` is `None`, and the
   handler's `lineage_path.unlink(missing_ok=True)` raises `IsADirectoryError` *from
   inside the except block* — masking the original exception and skipping the
   `CLOSE_MARKER` cleanup below it. Fixing that shape needs a `snapshotted` flag (3 extra
   lines) **plus** a tolerant restore; the pre-write read needs neither.
3. **It is what the module already promises.** "everything is validated **before anything
   is written**" (base `split.py:15-22`) — a snapshot that cannot be taken is a validation
   failure, not a rollback event.

Cost, concretely: pre-write snapshot = **+21 lines** in `accept` (`split.py:525-547`,
comment included: 3 lines of code, the rest is the why). The literal in-try variant would
be **+3 lines** at the same site *plus* a `lineage_snapshotted` flag (declare, set, guard
= 3 lines) *plus* the same `_restore_lineage` guard I ship anyway — so ~the same size, and
it keeps a failure path that files tracker issues it then cannot withdraw.

`SplitError` rather than a bare `OSError` is deliberate: `cli._split` catches `SplitError`
from `accept` (base `cli.py:765-786`) and prints the already-filed child ids plus the exact
`--accept --ids …` retry. An `OSError` escapes to a traceback with the filed issue numbers
nowhere on screen — the one failure this feature must not have (base `cli.py:767-772`).

`_restore_lineage` (`split.py:426-444`) is the second half: the rollback handler must be
**total**. If putting the record back fails too, the operator must still see the exception
that broke the accept, and the marker cleanup after it must still run — otherwise
"children rolled back" and "parent still terminal" can coexist, which is precisely what
the existing write-ordering comment (`split.py:596-602`) exists to prevent. It reports on
stderr instead of raising, the same discipline as `_rollback` (base `split.py:365-383`).

## What changed

`template/src/pdca_harness/split.py`

- `LINEAGE = "split-lineage.json"` / `LINEAGE_VERSION = 1` (`:39-48`), beside `PROPOSAL`,
  with the "not in `DOWNSTREAM_OF_BRIEF`" reason recorded at the constant.
- `_bundle_id()` (`:361-370`) — `issue_<id>` → `<id>`; deliberately more permissive than
  `_parent_number` (`:698`), which is all-digits because it feeds `gh issue create
  --parent`. A lineage id is any token `validate()` accepts, incl. `MANT-1`.
- `read_lineage()` (`:373-396`) — the one tolerant reader (item 4). Absent / unreadable /
  malformed / non-object / wrong-version → `None`, never raises.
- `_write_lineage()` (`:399-405`) — one serialiser for both edges (sorted keys, trailing
  newline) so a child's record and a parent's cannot drift.
- `_merge_parent_lineage()` (`:408-423`) — merge, never replace (item 3).
- `_restore_lineage()` (`:426-444`) — total, loud, never raises.
- `materialise(..., *, parent: Path)` (`:447-478`) — writes each child's record into the
  **staged** dir next to `brief.md`, so it moves with it (item 6). `depth` = parent's
  recorded depth + 1. Sole caller is `accept` (`grep -rn "materialise("` → `split.py:552`
  only), so widening the signature is safe.
- `accept()` — pre-write snapshot (`:525-547`), merged parent record written **before**
  the breadcrumb and `CLOSE_MARKER` (`:588-595`), restore in the rollback handler
  (`:614-618`).

`docs/07-crosscutting.md:217-239` — one paragraph in `### The split`: the artifact, the
schema, why the edges are independent with no `role`, the tolerant reader, the
`DOWNSTREAM_OF_BRIEF` exclusion, and the transactional guarantee.

`template/tests/test_split_lineage.py` — new module, 18 tests, 340 lines.

## Alternatives ruled out

- **A `role` discriminator** — foreclosed by the brief's schema section and by the defect
  it caused. Not re-attempted.
- **Two files** (`split-lineage-child.json` + `-parent.json`) — foreclosed by the brief;
  they drift, and #449 needs the parent edge where children 2-4 need the child edge.
- **Also checking the record in `preflight()`** (base `split.py:224-244`, the phase that
  runs *before* `gh issue create`): 3 lines, and it would refuse before any tracker issue
  is filed. Not shipped — it widens the slice's blast radius (preflight failures block
  filing for an environment fault), and the existing `SplitError` path already recovers
  cleanly: the ids are printed with the exact retry, and re-running after removing the
  stray directory succeeds. Worth reconsidering if a real operator ever hits it.
- **Tolerating an unreadable prior record and overwriting it** — strictly worse: with a
  directory at the path the merge write raises anyway, but *after* the children moved, so
  the failure lands back in the rollback path this iteration exists to fix.
- **Passing `depth`/`parent_id` scalars into `materialise` instead of `parent: Path`** —
  it needs the parent's *current* record for `depth`, so it needs the directory; passing
  both would derive the id from the path at the call site anyway.
- **Adding `LINEAGE` to `state.DOWNSTREAM_OF_BRIEF`** — explicitly out of scope; its
  absence is the point, asserted by name at `test_split_lineage.py:180-183`.

## Refutation (the three questions)

**(a) Genuine red?** Yes — three separate ways, all run through the project's own runner.

1. Full production revert (the C4 gate, `./engine/scripts/run-verify.sh` with
   `PDCA_BUNDLE`/`PDCA_WORKTREE`): green leg `Ran 18 tests … OK`; red leg `Ran 18 tests …
   FAILED (errors=18)`, every one an `AttributeError: module 'pdca_harness.split' has no
   attribute 'LINEAGE' / 'read_lineage'` — a real red, **not** an `ImportError` (the test
   imports only the module, per the brief), so no `PDCA-UNVERIFIABLE`. Verdict
   `C4 PASS: red without the fix, green with it`, exit 0.
2. **Mutation 1 — the previously-shipped defect.** `_merge_parent_lineage` changed to keep
   only `depth` (i.e. overwrite the child record with a parent one):
   `FAILED (errors=2)` — `test_a_parent_that_is_itself_a_child_keeps_both_edges` and
   `test_the_record_survives_the_archive_accept_itself_performs`, on `KeyError: 'parent'`.
   The mixed-role assertion binds the actual defect, not just symbol existence.
3. **Mutation 2 — this iteration's defect.** Snapshot moved back into the gap between the
   protected regions: `FAILED (errors=1)` —
   `test_an_unreadable_prior_record_refuses_before_anything_is_written`, on
   `IsADirectoryError` escaping `accept` (transcript at the top of these notes, with both
   children left on disk). Only this new test catches it; the other 17 stay green, which
   is why iteration 1 shipped past it.

**(b) Production path?** Yes. Every test calls the real `split.accept` /
`split.read_lineage` / `split.materialise` (via `accept`) in
`template/src/pdca_harness/split.py`, and `state.DOWNSTREAM_OF_BRIEF` by name. No copy, no
stand-in, no re-implementation. Mocking is confined to *injecting the fault*: a
`Path.write_text` that raises for one filename (a full disk mid-accept), a `Path.write_bytes`
that raises (a restore that cannot complete), and one `mock.patch("shutil.move",
wraps=shutil.move)` **spy** that calls straight through and only records whether anything
was moved. The lineage read/merge/write/restore code under test runs unmocked in all 18.

**(c) Fixture includes the fault?** Yes, in each failure test the failing element is
present, not curated out:
- mixed role — the parent bundle really carries a child record
  (`parent`/`siblings`/`depth`) before `accept` runs (`test_split_lineage.py:102-119`);
- the unreadable record — a real directory at `split-lineage.json`, the case the reviewer
  named (`:279-307`);
- the rollback tests — a real `OSError` raised mid-`accept`, once *before* the marker and
  once *after the marker has landed on disk*, so the marker cleanup is genuinely exercised
  rather than passing vacuously (`:251-277`, `:309-338`);
- the archive test — the parent really holds a `patch.diff`, and the test asserts it *was*
  archived before asserting the lineage record was not (`:185-203`), so it cannot pass by
  the archive silently not running.

## Verification run (project runners only)

```
C4  ./engine/scripts/run-verify.sh          → C4 PASS: red without the fix, green with it (exit 0)
                                              green: Ran 18 tests OK · red: Ran 18 FAILED (errors=18)
T2  ./engine/scripts/run-docs-check.sh      → lint_docs: OK · render_site: link audit OK (exit 0)
T3  ./engine/scripts/run-suite.sh           → root suite Ran 7 tests OK (copier REALLY ran —
                                              .venv/bin/python3 -c 'import copier' → 9.17.0, so the
                                              render + update-compat tests did not skip themselves)
                                              offline driver suite Ran 1617 tests OK (skipped=2)
```

Also: `git worktree add --detach /tmp/verify-base origin/main && git apply --check patch.diff`
→ applies clean to the brief's target branch (`6668172`).

## Commit-readiness

The target defines no formatter or linter config (no `.pre-commit-config.yaml`, no
`.flake8`/`setup.cfg`/`ruff`/`black` settings, no repo hooks in `.git/hooks`). Its CI is
`docs-check.yml` (`lint_docs.py`, `render_site.py --check`) and `render-check.yml`
(`tests.test_render_and_run`, `tests.test_update_compat`) — all four commands ran green
above via the T2/T3 wrappers. New lines are ≤ 93 columns, inside the file's existing range
(max 96). One logical change; DCO sign-off is the publish step's.

## External dependencies

None missing. The brief's one named dependency — `copier importable (.venv)` — is present
(9.17.0) and the seven root tests **ran** rather than skipping. No NEEDS-HUMAN external
dependency to declare.

## Scope discipline

Touched exactly `template/src/pdca_harness/split.py`, one paragraph of
`docs/07-crosscutting.md`, and the new test module. No consumer wired up (`sizing.py`,
`plan_policy.py`, leaf prompts, `flow.py` all untouched), no `state.py` edit, no
`pdca.toml.jinja` change, no weight/cutoff/remedy wording.
