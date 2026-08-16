# Build notes — issue 476 / lineage-reader-doc-matches-the-reader

## What changed

`docs/07-crosscutting.md:277-282` (target branch: eduralph/pdca-harness @ main, base commit
`acb214a`) — corrected the lineage-reader paragraph's return-contract clause. Only that
paragraph was touched; nothing else in `07-crosscutting.md` or elsewhere was edited (verified
with `git diff --stat`: 1 file, 7 insertions / 4 deletions, all inside lines 277-284).

Before:
> `split.read_lineage`, which returns `None` for an absent, unreadable, malformed
> or wrong-version file rather than raising — for *any* way of failing to read
> it, down to bytes that aren't valid UTF-8, and for a `depth` that isn't a
> number: provenance that can throw into a beat is worse than provenance that
> abstains, so a hand-edited record degrades the hint and never the run.

After:
> `split.read_lineage`, which returns `None` for an absent, unreadable, malformed
> or wrong-version file rather than raising — for *any* way of failing to
> **parse** it, down to bytes that aren't valid UTF-8. A `depth` it parses fine
> but can't compute with, like `"one"`, is handed straight back by the reader
> and absorbed one layer down instead, by the depth arithmetic, which treats it
> as unknown (`0`) so the child lands at depth 1 and the parent's own record is
> left untouched: provenance that can throw into a beat is worse than provenance
> that abstains, so a hand-edited record degrades the hint and never the run.

## Why this change, grounded in the cited code

- `template/src/pdca_harness/split.py:583-612` (`read_lineage`) — the only `return None`
  paths are the total `except` wrapping the read+`json.loads` (line 606-609, catching
  unreadable files, non-UTF-8 bytes, malformed JSON, pathological nesting — anything that
  fails to *parse*) and the `isinstance`/`version` guard (line 610-611, non-object payload
  or wrong version). A record like `{"depth": "one", "version": 1}` is valid JSON of the
  right shape, so `data` is returned as-is at line 612 — the reader never inspects `depth`
  at all. The old doc sentence claimed a `None` this function does not return.
- `template/src/pdca_harness/split.py:615-631` (`_recorded_depth`) — this is where the
  unusable `depth` is actually absorbed: line 628-629 accepts only a non-negative,
  non-boolean `int`; anything else (a string, `null`, a negative number, a bool) falls
  through to `return 0` at line 631. That `0` is what the doc now attributes to "the depth
  arithmetic" rather than to the reader.
- `template/tests/test_split_lineage.py:236-251`
  (`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number`) — pins exactly the
  corrected claim: it seeds a parent record with `depth="one"`, calls `split.accept`, and
  asserts (line 247) the created child's own `depth` reads `1` (the `0`-fallback + 1), while
  (line 251) the parent's own record — read back through `read_lineage` — still says
  `"one"` verbatim, i.e. the reader handed it back unchanged rather than returning `None`.

The rewrite keeps the two-layer tolerance story (reader abstains on what it cannot parse;
arithmetic absorbs what it cannot compute with) and the closing rationale sentence
("provenance that can throw into a beat is worse than provenance that abstains, so a
hand-edited record degrades the hint and never the run") verbatim, per the brief's Scope
and Citations-expected sections.

## What I ruled out

- **Adding a docs-vs-behaviour consistency test.** Brief's Scope explicitly excludes this
  ("adding a docs-versus-behaviour consistency test... a prose-matching test would be new
  machinery this slice does not need"). The behaviour is already pinned by
  `test_split_lineage.py:236-251`; that test's own existence going red is what would catch
  a future drift, not a new test I'd add here.
- **Touching `split.py` or `_recorded_depth`.** Brief's Scope: "the permissive reader and
  `_recorded_depth` are correct and stay untouched (the issue routes this to the doc
  deliberately)." Verified by reading both functions (cited above) — they behave exactly as
  the corrected doc now says; nothing to fix in code.
- **Editing the merge-mode section (`:539-575`) or any other paragraph.** Out of scope per
  the brief's Ordering note (462's knob is deliberately kept out of this file) and Scope
  ("every other paragraph... out of scope"). Confirmed via `git diff --stat` that only lines
  277-284 changed.
- **A token/manufactured test to force a red C4-verify leg.** Brief's Falsifiability
  section is explicit: this is docs-only, `engine/scripts/run-verify.sh:130-144` correctly
  classifies it non-behavioural and will exit 77 `PDCA-UNVERIFIABLE` — inventing a
  production edit or a token test to fake a red leg was explicitly disallowed and would
  have been dishonest evidence.

## Test file

**None**, per the brief's own Test-file line: "this slice ships no test, and that is the
correct shape, not an omission." The behaviour the corrected sentence describes is already
pinned by `test_split_lineage.py:236-251`, run and confirmed green below.

## Mechanical checks run (the project's own runner)

Ran `engine/scripts/run-docs-check.sh` (the T2-docs / host-ci-docs runner named in the
brief's Success criterion) against `$PDCA_WORKTREE`, both pre-fix and post-fix:

- **Post-fix (patch applied):**
  ```
  == T2: docs lint (Obsidian syntax)
  lint_docs: OK
  == T2: site render + internal-link audit
  render_site: wrote 22 page(s) to /tmp/.../site
  render_site: link audit OK
  PDCA-EVIDENCE: docs lint clean, site render + link audit clean
  ```
- **Pre-fix (patch `git stash`'d, original paragraph restored):** identical clean output.

This confirms both mechanical checks stay clean either way — expected, since they check
Obsidian syntax and internal links, not prose truth (a false-but-well-formed sentence lints
clean). They are not the red/green leg for this slice; per Falsifiability, that leg does not
exist mechanically here.

Also ran the cited pinning test, exactly as the brief's Repro instruction specifies, from
`template/`:
```
PYTHONPATH=src python3 -m unittest tests.test_split_lineage -v
```
→ 23 tests, all `ok`, including
`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number` — unaffected by this
docs-only patch, as expected, since `split.py` was not touched.

## Self-refutation (forced questions)

- **(a) Genuine red?** N/A in the mechanical sense — there is no test to revert-and-rerun,
  and the brief is explicit that inventing one would be dishonest (Falsifiability section).
  The genuine "red" for this slice is the *prior* state of the doc itself: before the patch,
  `docs/07-crosscutting.md:278-281` asserted `read_lineage` "returns `None` ... for a
  `depth` that isn't a number," which is false — falsified by reading
  `split.py:583-612` (no code path there inspects `depth`) and by
  `test_split_lineage.py:236-251` (asserts the opposite: the parent's non-numeric `depth`
  is read back unchanged, not turned into `None`). That falsity is what this patch removes.
- **(b) Production path?** N/A — no test drives production code for a prose fix. The
  corrected prose is checked directly against the production function bodies
  (`split.py:583-612`, `:615-631`) cited above, read on the target branch, not against a
  copy or paraphrase of them.
- **(c) Fixture includes the fault?** N/A for the same reason — there is no fixture. The
  "fault" was the doc sentence itself, at `docs/07-crosscutting.md:277-282` on the base
  commit (`acb214a`), which is exactly the text this patch replaces; the diff shows the
  faulty clause is what's removed, not something adjacent left standing.

Per the brief's Falsifiability section, `C4-verify` will legitimately report `PDCA-UNVERIFIABLE`
(exit 77) for this bundle — that is the sanctioned, non-gating outcome for a docs-only slice
with no production change to revert, and it routes to SUMMARY §6 for the human's read, which
this brief already points at the exact lines to check
(`split.py:583-612`, `:615-631`, `test_split_lineage.py:236-251`).

## External dependencies

None beyond what the brief names. `engine/scripts/run-docs-check.sh` needs
`markdown-it-py[linkify]` + `PyYAML` in the instance venv; both were present and the script
ran to completion (see mechanical-checks output above) — no NEEDS-HUMAN external-dependency
gap to declare.

## Formatter / commit hooks

No `.pre-commit-config.yaml`, `.editorconfig`, or markdown-formatter config found in the
target worktree (checked repo root and `CONTRIBUTING.md`). `docs/publishing/tools/
lint_docs.py` *is* the target's own mechanical check for this file's syntax and it passed
clean (above) — that is the commit-time gate this edit is subject to, and it's green.
