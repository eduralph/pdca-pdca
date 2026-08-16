# Build notes — issue 476 / lineage-reader-doc-matches-the-reader (iteration 2)

Target branch: `eduralph/pdca-harness @ main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`,
base `acb214a`, identical to `origin/main`). Docs-only, one hunk, one paragraph.

## What the patch says, and the line each claim comes from

Patched paragraph: `docs/07-crosscutting.md:277-290`. Pre-patch text: `:277-282`.

| Clause in the new prose | Production line it is read off |
|---|---|
| "abstains rather than raising on **anything it can't turn into a version-1 record**" | `template/src/pdca_harness/split.py:606-611` — the two `return None` sites, plus `LINEAGE_VERSION = 1` at `split.py:49` |
| "absent, unreadable, malformed JSON, a non-object payload and an unrecognised `version` all return `None`" | Lifted verbatim from the reader's own docstring, `split.py:586-587` |
| "the first three cover *any* way of failing to parse the file at all, down to bytes that aren't valid UTF-8" | `split.py:606-609` — the TOTAL `except Exception` around `read_text` + `json.loads`; the docstring at `split.py:592-600` names the UTF-8 case as the reason the catch is total |
| "the last two parse cleanly and are turned away on shape and version" | `split.py:610-611` — `not isinstance(data, dict) or data.get("version") != LINEAGE_VERSION`, evaluated on ALREADY-PARSED data |
| "A `depth` that isn't a number is in neither group — … the reader hands the record straight back" | `split.py:606-612`: `{"depth": "one"}` passes the parse, `isinstance` and `version` checks, so line 612 returns it |
| "the depth arithmetic one layer down absorbs the value it can't compute with, counting it as unknown (`0`) so the child lands at depth 1" | `split._recorded_depth`, `split.py:615-631` (test at `:628-631`: non-bool `int` and `>= 0`, else `0`) |
| "The parent's own record keeps `"one"` verbatim **by a separate route**: the merge copies an existing `depth` through rather than recomputing it" | `split._merge_parent_lineage`, `split.py:643-657` — the loop at `:654-656` copies `parent`/`siblings`/`depth` from the existing record; it never calls `_recorded_depth` |
| "Provenance that can throw into a beat is worse than provenance that abstains, so a hand-edited record degrades the hint and never the run." | Unchanged rationale sentence — kept byte-identical, so it shows as diff CONTEXT, not as a rewrite |

Behaviour pins in the shipped suite (nothing new needed):
`template/tests/test_split_lineage.py:133` (absent), `:136` (unreadable), `:141` (malformed),
`:145` (not an object), `:149` (wrong version), `:155` (non-UTF-8 bytes), `:174` (never raises),
`:236-253` (`test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number` — child depth 1,
parent's record still `"one"`).

## How iteration 1's four rejections are addressed

1. **Non-object case was missing.** Now enumerated explicitly ("a non-object payload"),
   from `split.py:610`. Empirically confirmed below, and pinned at
   `test_split_lineage.py:145`.
2. **Organising idea didn't span the shape rejection.** The framing is no longer "any way
   of failing to *parse* it" — it is "anything it **can't turn into a version-1 record**",
   and the next sentence splits the enumeration into its two actual grounds: the first
   three are parse failures (`split.py:606-609`), the last two "parse cleanly and are
   turned away on shape and version" (`split.py:610-611`). `[1,2,3]` — valid JSON, rejected
   on shape — is now covered by the sentence around it rather than contradicted by it.
3. **Reuse the wording that is already correct.** The list is the reader's own docstring,
   `split.py:586-587`, copied word for word rather than re-derived.
4. **The implied causal link.** Split into two independent sentences with different
   subjects: the depth arithmetic (`split.py:615-631`) explains only the CHILD landing at
   depth 1; the parent's `"one"` surviving is attributed to "a separate route: the merge
   copies an existing `depth` through rather than recomputing it" (`split.py:643-657`).
   No "so" or "and" links the two — the second consequence holds regardless of the first,
   which is exactly what `_merge_parent_lineage` does.

## Evidence (run in the worktree)

**Every clause checked against the production reader** — not against a copy. Driven through
the real `pdca_harness.split` module (`PYTHONPATH=src`, imported from
`template/src/pdca_harness/split.py`):

```
absent            -> None
non-UTF-8 bytes   -> None
malformed JSON    -> None
non-object        -> None          <- the case iteration 1 omitted
wrong version     -> None
depth "one"       -> {'version': 1, 'id': '500', 'depth': 'one'}   <- NOT None
  _recorded_depth -> 0                                             (child lands at 1)
  _merge_parent   -> {'version': 1, 'id': '500', 'depth': 'one', 'children': [...]}
                                                                   (copied through verbatim)
```

**Falsification of the corrected sentence (the "would-be red").** The brief claims the new
prose is falsifiable by the shipped suite. I checked that rather than asserting it: I
temporarily inserted, after `split.py:611`, the behaviour the OLD doc sentence described —
`if "depth" in data and not isinstance(data["depth"], int): return None` — and ran the
suite through the target's own runner:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_split_lineage
FAILED (errors=1)
  test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number
  KeyError: 'parent'   (test_split_lineage.py:249)
```

So the sentence the patch REMOVES describes a reader the suite forbids, and the sentence it
ADDS is the one the suite enforces. The experiment was reverted (`git checkout --
template/src/pdca_harness/split.py`); the suite is green again and `git status` shows only
`docs/07-crosscutting.md` modified. **`split.py` ships unmodified** — the patch is
`docs/07-crosscutting.md` alone.

**Gates re-run locally on the patched tree** (project runners, not hand-rolled):

- `PDCA_WORKTREE=… ./engine/scripts/run-docs-check.sh` (the `T2-docs` row) → rc 0:
  "docs lint clean, site render + link audit clean".
- `engine/scripts/run-host-ci.sh` executed from the patched worktree (the gating
  `host-ci-docs` parity row, same two checkers as the target's
  `.github/workflows/docs-check.yml`) → rc 0.
- Target offline suite, the command `AGENTS.md` documents:
  `cd template && PYTHONPATH=src python3 -m unittest discover -s tests` → `Ran 1758 tests …
  OK (skipped=2)`.
- `template/tests/test_split_lineage.py` alone → `Ran 23 tests … OK`.
- `git apply --check` of the shipped `patch.diff` against the stashed (clean `origin/main`)
  tree → applies clean.

## The three refutation questions

- **(a) Genuine red?** **No test ships, by design — this is the brief's declared shape**
  ("Test file: none", Falsifiability §). A patch confined to `docs/*.md` is classified
  non-behavioural by `engine/scripts/run-verify.sh:130-144`, so C4 records
  `PDCA-UNVERIFIABLE` (→ §6, human adjudication) whether or not a test file existed; the
  brief forbids inventing a production edit or token test to manufacture a red. What I did
  instead is the honest equivalent, above: I made the reader match the OLD sentence and the
  **existing** pin `test_split_lineage.py:236-253` went red, then reverted. That is a real
  red→green over the claim the prose makes, using a test that was already in the tree.
- **(b) Production path?** **Yes.** Every clause was read off, and exercised against,
  `template/src/pdca_harness/split.py` as imported by the shipped suite — no stub, no copy,
  no re-implementation. The doc gates likewise run the *target's own* checkers
  (`docs/publishing/tools/lint_docs.py`, `render_site.py --check`), not a re-implementation.
- **(c) Fixture includes the fault?** **Yes.** The check above includes precisely the cases
  the old sentence got wrong: the non-object payload (`[1,2,3]`), and `{"depth": "one"}`
  where the reader returns the record rather than `None`. Nothing was curated out; the
  non-object case that iteration 1 dropped is the one I made sure to drive.

## Alternatives ruled out, with the cost shown

- **Change the code to match the doc** (make `read_lineage` return `None` on a non-numeric
  `depth`). Rejected: the brief puts `split.py` out of scope, and the experiment above shows
  the cost concretely — it turns `test_split_lineage.py:236-253` red, and would silently
  drop a hand-editing operator's `parent`/`siblings` from the parent's merged record
  (`split.py:652-657` starts from `read_lineage(parent) or {}`). It also contradicts the
  reader's own docstring at `split.py:586-600`. Wrong direction: the code is right.
- **Add a docs-versus-behaviour consistency test** (parse the paragraph, assert against
  `read_lineage`). Rejected on scope and cost: it is new machinery — a new test module plus
  a prose parser — for a claim already pinned by 7 existing cases
  (`test_split_lineage.py:133,136,141,145,149,155,236`), and it would not change C4's
  verdict (`run-verify.sh:140` exits 77 on "no behavioural production change to revert" for
  a docs-only patch even when a test ships). The brief lists it as out of scope.
- **Re-wrapping the rest of the paragraph.** Rejected: it would turn a 4-removed/12-added
  hunk into a ~20-line hunk of pure reflow noise that a reviewer must diff word-by-word to
  confirm is a no-op. Instead I used a balanced (DP) wrap over only the replaced sentences,
  keeping every line at 71-78 cols (the file's prose band is 73-81 here), never breaking an
  inline code span across a line, and choosing break points so the closing rationale line
  stays **byte-identical** and appears as context in the diff.

## Commit-readiness

The target has no `.pre-commit-config.yaml` and no installed git hooks
(`$(git rev-parse --git-common-dir)/hooks` holds only samples); its commit-time gate for
this file is `.github/workflows/docs-check.yml`, i.e. the two checkers above — both run
green on the patched tree, twice (T2 seam and host-CI parity seam). Nothing else in the
repo formats Markdown. `AGENTS.md`'s DCO sign-off / conventional-prefix subject are
publish-step concerns, not builder edits.

No external dependency beyond the ones the brief already registered
(`markdown-it-py[linkify]`, `PyYAML` in the instance venv) was needed; nothing to declare.

## For the human at sign-off (C4 is UNVERIFIABLE by construction — this is the read)

1. `git diff` the single hunk in `docs/07-crosscutting.md:277-290`.
2. Open `template/src/pdca_harness/split.py:583-612` and check the sentence's list against
   `:606-611`; then `:615-631` for the depth-1 clause and `:643-657` (loop at `:654-656`)
   for the "separate route" clause.
3. `cd template && PYTHONPATH=src python3 -m unittest tests.test_split_lineage -v` → 23 OK;
   `test_accept_survives_a_parent_whose_recorded_depth_is_not_a_number` is the pin that
   fails the moment the reader starts doing what the OLD sentence claimed.
