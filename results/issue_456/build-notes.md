# Build notes — issue #456, `split-lineage-record` (iteration 3)

Target: `eduralph/pdca-harness` @ `main`, worktree `/home/eddie/pdca/pdca-harness.pdca-wt`
at base `6668172` ("Merge pull request #460 …"). Every `path:line` below is against that
tree with the patch applied.

## What this iteration changes relative to iteration 2

The v2 attempt was accepted on structure (mixed-role merge, staging discipline,
`DOWNSTREAM_OF_BRIEF` exclusion, pre-write snapshot) and **rejected on the tolerant
reader**:

> C3 Change | FAIL | The reader must abstain for every unreadable or malformed record, but
> invalid UTF-8 bytes raise `UnicodeDecodeError` because the decode at
> `template/src/pdca_harness/split.py:387` is outside the `ValueError` handler; a consumer
> can still be crashed by the provenance file.
> — `iteration-v2/check-review.md:7` (C4 FAIL at `:8` for the same reason)

That is brief item 4 outright ("It never raises"), so it had to be fixed here; re-shipping
v2 unchanged would have re-shipped a reader that throws into a beat. Two concrete holes,
both empirically confirmed on this machine (python 3.14.4, and the same on 3.11+ because
both exceptions predate it):

| corrupt record | exception | v2 handler that missed it |
|---|---|---|
| bytes that are not UTF-8 | `UnicodeDecodeError` | raised by `read_text`, whose arm caught only `OSError`; it *is* a `ValueError`, but the `ValueError` arm wrapped `json.loads`, one statement too late |
| deeply nested JSON array | `RecursionError` | not a `ValueError` at all — a `RuntimeError`; no "malformed JSON" enumeration covers it |

**The fix** (`template/src/pdca_harness/split.py:396-402`): one `try` around read + decode +
parse, `except Exception: return None`. The catch is total on purpose and the docstring
says why (`:382-390`): a function whose entire contract is "never raises" cannot be written
as a predicate over the failure modes someone happened to think of — that is exactly how v2
failed. `BaseException` still propagates, so Ctrl-C / `SystemExit` are untouched.

**Second half of the same defect** (`template/src/pdca_harness/split.py:405-421`,
`_recorded_depth`, used at `:486`): tolerating the *file* but not its *values* only moves
the throw one line down. `{"depth": "one"}` and `{"depth": null}` are valid JSON, so the
reader hands them back intact and v2's `parent_lineage.get("depth", 0) + 1` raised
`TypeError` **from inside `accept`** — a hand-edited provenance file crashing the split
just as a raising reader would, which is precisely the C3 wording ("a consumer can still be
crashed by the provenance file"). `_recorded_depth` returns the recorded depth iff it is a
non-negative, non-`bool` `int`, else 0. Booleans are excluded because `True is an int` in
Python and `"depth": true` should not mint a child at depth 2. The operator's own value is
still copied through the parent merge verbatim (`:442-448`) — abstaining from *computing*
with it is not licence to *rewrite* it.

Two new production-path tests and one new staging test come with it (below). Everything
else in the patch is iteration 2's, unchanged, including the iteration-1 carry-forward fix
(the prior-bytes snapshot moved into the pre-write phase, `:550-570`).

## The change, item by item against the brief's Success criterion

| # | Criterion | Where |
|---|---|---|
| 1 | child record: `parent`, `siblings`, `depth = parent's + 1` | `split.py:486` + `:493-499` (in `materialise`) |
| 2 | parent record: `children` | `split.py:619` (in `accept`), merged by `:442-448` |
| 3 | mixed role preserved — own `parent`/`siblings`/`depth` **and** `children` | `split.py:444-446`; test `test_split_lineage.py:104` |
| 4 | one tolerant module-level reader, never raises | `split.py:373-403` + `:405-421` |
| 5 | **not** in `state.DOWNSTREAM_OF_BRIEF` | asserted by name, `test_split_lineage.py:257`; `state.py:82-114` untouched |
| 6 | transactional: staged children, parent record before `CLOSE_MARKER`, prior bytes restored | `split.py:472-501` / `:619` (before `:635`) / `:642` |

Schema exactly as the brief settles it: one file, independent optional edges, no `role`
discriminator (`split.py:47-48`, `LINEAGE = "split-lineage.json"`, `LINEAGE_VERSION = 1`).
The docs row lands in the section the brief names — `docs/07-crosscutting.md:217-241`,
inside `### The split`, next to the `--accept` transactional guarantees.

Scope held: `split.py`, one docs paragraph, one new test module. No consumer was touched —
`grep` for `read_lineage|LINEAGE` outside `split.py` and the new test returns nothing, so
`sizing.estimate`, `plan_policy`, the leaf prompts, the convergence report and `flow.py`
are exactly as they were. `materialise` has a single caller (`split.py:576`), so the added
keyword-only `parent=` breaks nobody.

## Refutation — the three forced questions

**(a) Genuine red?** Yes, twice over.

1. *Against the target base* (the C4 gate, the project's own runner
   `./engine/scripts/run-verify.sh`, which reverts only the production hunks and keeps the
   test): green leg `Ran 23 tests … OK`; red leg `Ran 23 tests … FAILED (errors=23)`;
   `C4 PASS: red without the fix, green with it`. The module *loaded* on the red leg (23
   tests ran, no `unittest.loader._FailedTest`), because the brief's rule is obeyed — the
   test imports the module (`from pdca_harness import split`) and touches new symbols only
   inside test bodies, so the red is `AttributeError: module 'pdca_harness.split' has no
   attribute 'LINEAGE'`, not an `ImportError` that would have exited 77 UNVERIFIABLE.
2. *Against iteration 2* — the delta that matters this round. I restored v2's exact reader
   and depth arithmetic in place and re-ran the module: `FAILED (failures=2, errors=4)`,
   and the six are precisely the new cases —
   `test_reader_returns_none_on_bytes_that_are_not_utf8`,
   `test_reader_returns_none_on_a_pathologically_nested_payload`,
   `test_accept_survives_a_parent_record_that_is_not_utf8`,
   `test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number`, and the
   `use_non_utf8_bytes` / `use_deep_nesting` subtests of
   `test_reader_never_raises_on_any_of_the_above`
   (`UnicodeDecodeError('utf-8', b'\xff\xfe{"version": 1}', 0, 1, 'invalid start byte')`
   and `RecursionError: Stack overflow … while decoding a JSON array`). The 17 v2 tests
   stayed green, so the new cases bind *this* iteration's defect and nothing else. The file
   was restored from `/tmp/split_v3.py` afterwards and the final patch re-verified.

**(b) Production path?** Yes. The tests call `split.accept`, `split.materialise`,
`split.read_lineage` and `split.parse` — the shipped functions, through the real `Config`
(`pdca_harness.config.Config`) on a real temp-dir instance. There is no copy, no stub, no
re-implementation of the record format anywhere in the test module; the only `mock` use is
on `pathlib.Path.write_text` / `write_bytes` to *inject* a disk failure into the real
`accept`, and on `shutil.move` as a read-only spy (`wraps=shutil.move`). Two of the new
cases (`:214`, `:236`) exist specifically because a reader-only probe can be green while
the beat still dies one frame up — they push the corrupt record through `accept` itself and
assert the split *completes* (`CLOSE_MARKER` written, children recorded).

**(c) Fixture includes the fault?** Yes — every fixture contains the failing element rather
than curating it out:
- the mixed-role test *seeds a real child record on the parent* before accepting
  (`:104-121`), which is the exact bundle shape that regressed at depth ≥ 1;
- the tolerance tests write the actually-corrupt bytes (`b'{"version": 1, "id":
  "\xff\xfe500"}'`, `"[" * 60000 + "]" * 60000`, `{not json`, a *directory* at the record
  path), not a stand-in "unreadable" flag;
- the transactional tests inject a real `OSError` at the exact file that must fail
  (`build-notes.md`, `CLOSE_MARKER`) and then assert on the disk state: no children, no
  marker, prior bytes byte-for-byte (`:348`);
- `test_the_record_survives_the_archive_accept_itself_performs` (`:262`) first asserts the
  archive actually happened (`iteration-v1/patch.diff` exists) before asserting the record
  was *not* swept into it — so a fixture that quietly skipped the archive path would fail
  rather than pass vacuously.

## Alternatives considered, with costs

**Enumerate the exception types instead of a total catch.** The v2 shape, extended:
`except (OSError, ValueError, RecursionError)`. Cost is not size — it is one token wider
than what I shipped — it is that it re-commits the error that produced this iteration.
`UnicodeDecodeError` was already covered by v2's `ValueError` arm *by type* and still
escaped, because the failure came from a different **statement**; predicting the next such
pair (a `MemoryError` on a huge file, an `OverflowError`, a future parser's own type) is
not something the reader's contract permits me to get wrong. A total catch over a function
with no side effects and one job — return a hint or `None` — has no failure mode worse than
the one it prevents.

**Validate the record's shape in `read_lineage` and reject a bad `depth` outright.** ~8
lines instead of `_recorded_depth`'s 5 body lines, but wrong: rejecting the whole record
because one field is nonsense would drop `parent` and `siblings` too — the same edge loss
brief item 3 exists to prevent, arrived at from the other direction. Abstaining per *value*
keeps the readable edges readable.

**Refuse the accept when the parent's record exists but is unparseable** (symmetric with
the unreadable case at `:565-570`). Rejected on behaviour, not cost: an unparseable file
carries no edges any consumer could have read, so there is nothing to merge and nothing to
lose — while refusing would hand one corrupt hint the power to block the split beat
outright, which is the very failure the tolerant reader exists to prevent, one level up.
The *unreadable* case is genuinely different and still refuses: bytes that cannot be read
cannot be restored on rollback, so accepting would break item 6. Both halves are asserted
(`:214` completes; `:376` refuses with nothing staged — `shutil.move` never called).

**Guard the symptom instead of the cause** — e.g. wrap each *call site* of `read_lineage`
in `try/except`. Rejected outright: it is the reader's contract that item 4 names, there
are 2 call sites today and children 2-4 plus #449 add more, so the guard count grows
without bound while the cause stays. Cost of the shipped fix: 1 statement moved, 1
`except` clause; cost of the guard: 4 lines per consumer, forever.

## Iteration carry-forward — disposition

- **Iteration 1** (C3 FAIL: the parent snapshot read sat between `accept`'s two protected
  regions): fixed in v2 and **kept unchanged** here — `split.py:550-570` takes the snapshot
  in the pre-write phase, next to the proposal and id validation, and an unreadable record
  raises `SplitError` before anything is staged. Test `:376` proves it with a `shutil.move`
  spy (`moved.assert_not_called()`), which is stronger than "no children left behind".
- **Iteration 2** (T4 NEEDS-HUMAN: the contribution lint could not be confirmed against the
  actual commit/PR artifacts): **structural, and not fixable from Do.** `contribcheck` lints
  `commit-msg.txt` + `pr-description.md`, which *publish* drafts after sign-off; at Check
  they do not exist, and the target's own code says so at
  `template/src/pdca_harness/cli.py:1070-1095` — it prints `gates.DEFERRED_MARKER` and the
  substantive audit hard-gates the push later via `publish._t4_passes`. Drafting those two
  artifacts myself would pre-empt the publisher leaf and is out of this brief's scope. One
  thing worth the human's eye at sign-off: **this instance's own installed harness is an
  older render** — `src/pdca_harness/cli.py:1036` returns a bare `0` with no marker ("
  artifacts not drafted yet"), which is why `iteration-v2/check-gates.json` recorded T4
  `pass` rather than `deferred`. I confirmed it: `PDCA_BUNDLE=… ./scripts/pdca contribcheck`
  → exit 0, no output. So the T4 green in this bundle is vacuous either way; the real T4
  runs at publish. Nothing in this patch can or should change that (out of scope: no
  `cli.py`, no `pdca.toml.jinja`).
- **Iteration 2's review body** also carried the C3/C4 FAIL on the reader — that is the
  substantive work of this iteration, above.

## Gates run locally (the project's own runners, not hand-rolled)

| Gate | Command | Result |
|---|---|---|
| C4 | `PDCA_BUNDLE=… PDCA_WORKTREE=… ./engine/scripts/run-verify.sh` | `C4 PASS: red without the fix, green with it` — green 23/23, red 23 errors |
| T2 | `./engine/scripts/run-docs-check.sh` | `lint_docs: OK`; `render_site: wrote 22 page(s)`, `link audit OK` |
| T3 | `./engine/scripts/run-suite.sh` | root suite `Ran 7 tests … OK` (21.4s — copier 9.17.0 really imported, so the render/update-compat tests did **not** skip themselves); driver suite `Ran 1622 tests … OK (skipped=2)`, the 2 skips pre-existing and unrelated |
| T4 | `./scripts/pdca contribcheck` | exit 0, deferred by design (see above) |

**External dependencies:** the brief names `copier importable (.venv)` and it is present —
`.venv/bin/python3 -c "import copier"` → 9.17.0, and the 7 root tests actually ran (21s of
real render work, not a skip). No other dependency was needed: no network, tracker, `gh` or
container. **No NEEDS-HUMAN external dependency for this bundle.**

**Commit-readiness:** the target repo carries no formatter/linter config (no
`pyproject.toml`, `.pre-commit-config.yaml`, ruff/flake8 config at the root; its CI is
`docs-check.yml`, `docs.yml`, `render-check.yml`, `require-linked-issue.yml`). The two
checkers its hooks/CI do run are T2 (`lint_docs.py` + `render_site.py --check`) and T3
(both suites) — both green above. Every line I added to `split.py` and the test module is
within the file's existing 96-column convention (`awk` over both files: no line > 96); the
docs paragraph wraps at ~72 like its neighbours. The only over-96 lines in
`docs/07-crosscutting.md` are pre-existing and outside my hunk.

## STOP discipline

No branch pushed, no PR opened, nothing marked ready or merged. The patch lives in
`patch.diff`; the worktree holds the same change (3 files: `docs/07-crosscutting.md`,
`template/src/pdca_harness/split.py`, `template/tests/test_split_lineage.py`).
