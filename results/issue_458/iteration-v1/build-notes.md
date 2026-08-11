# build-notes — issue 458 (split-child-remedy-and-hatch)

## What I read

`brief.md` only, plus the one cited-peer inspection the brief's own "narrow exception"
permits: none was actually named (no "mirror this callsite" pointer in this brief — the
Scope section names the files and line ranges to touch, not a peer pattern to copy), so I
did not open anything outside the target files the brief scopes: `plan_policy.py`,
`leaves.py` (only `_plan_prompt` / `_split_prompt` / the sizer), and
`docs/07-crosscutting.md`'s `### The process` section. I did read `split.py`'s
`read_lineage` / `materialise` and `sizing.py`'s `estimate` / `combine` because the brief's
own text (child 601/500, siblings, "N conflict(s) declared") only resolves against the
shape those two modules already define — `split-lineage.json`'s `siblings` edge and
`brief.conflicts_with`'s id list — and getting that shape wrong is exactly the class of
mistake (child-2's inflated-readout worry) the brief is warning against. Reading the two
data producers, not writing to them, stayed inside "consumes the signal, doesn't own it"
(the brief's own out-of-scope line for `sizing.py`).

## The fix

`plan_policy.size_reasons` (`template/src/pdca_harness/plan_policy.py:141-179` on the
target branch, `main`, pre-fix numbering — see the diff for exact post-fix lines): inside
the existing `elif before_do:` branch (the only one criterion (iv) allows to change), read
`split.read_lineage(d)`. If the bundle is a split child (`"parent" in lineage`), compute
which of its OWN declared `Conflicts with:` ids (`brief.conflicts_with(d / "brief.md")`)
also appear in the lineage's `siblings` list. Only a NON-EMPTY intersection swaps the
remedy for the honest line naming `(child {id} of a split of #{parent}, depth {depth})` —
mere lineage presence (round-1's bug) never does; an organic-only child (siblings
intersection empty) falls straight through to the unchanged `consider \`pdca split\` first`
detail string, byte-identical to today. The honest line also appends
`"; N sibling conflict(s) not counted"` — the missing clarifying clause the brief's failure
#1 named by name, so the message never again says "driven by inherited/sibling fields"
beside an uncounted "N conflict(s) declared" that includes sibling AND organic ids without
saying which is which.

The `else:` branch (`before_do=False`, the iterate-plan wording) is untouched — I did not
even read `lineage` there — so criterion (iv) holds structurally, not just by test
assertion: there is no code path from the new lookup into that branch.

`leaves._plan_prompt` and `leaves._split_prompt`: added one shared helper,
`_split_provenance_note(d)` (`leaves.py`, just above `_plan_prompt`), returning `""` when
`split.read_lineage(d)` has no `"parent"` edge, else one sentence naming the parent id and
warning that an inherited sibling conflict is not on its own a reason to split again. Spliced
into both prompts at the point each already talks about splitting, via `+ note +` inserted
into the existing (already `+`-joined) string-literal concatenation — no other sentence in
either prompt was reworded, satisfying "without otherwise rewording the existing split
instructions". Because the helper returns `""` for every non-lineage bundle, prompt output
for the common case is unaffected (empty-string concatenation), matching criterion (vi)'s
spirit even though (vi) is stated for the driver advisory specifically.

`docs/07-crosscutting.md`: within `### The process` only. The `A5`/`A7` fork (line ~50-52
pre-edit) now shows both branches of Entry A's "yes"; `B5`'s label (line ~59 pre-edit) gets
a one-line annotation that Entry B has no such fork (it never did, and criterion (iv) keeps
it that way); the prose after "artificial seams, not a real decomposition." (originally
lines 86-87) gains one new paragraph stating the same fork in prose and explicitly noting
Entry B's route is unconditional. I did not touch `### The estimate` or `### The split`
(child-2's and child-4's territory) or anything in Entry P / the `S1-S5` mechanics, which
this change does not affect.

## What I ruled out, with cost

**Keying on lineage presence alone (the rejected first attempt).** Cost: a NEGATIVE
diff — deleting the `siblings`/`conflicts_with` intersection check (~14 lines) and testing
only `if lineage and "parent" in lineage:`. Rejected on the brief's own reproduction: it is
demonstrably false for an organic-only child (test `test_ii_organic_only_conflicts_get_
the_ordinary_remedy` goes red under that simpler predicate — I verified this by hand-tracing
it against the round-1 description before writing the real fix, not by re-implementing the
rejected patch to check).

**A blocking `hold` on the sibling-conflict case.** Out of scope per the brief's own
"Out of scope" line (`plan_policy.py:88-102`'s calibration docstring: 50% recall / 62%
precision, `hold` deliberately unimplemented) — not revisited.

**Re-deriving the sibling/organic split inside `sizing.py`** (e.g. a new
`SizeEstimate.sibling_conflicts` field computed during `estimate()`). Cost: touches
`sizing.py` (~15-20 lines: a new dataclass field, a new parameter threading `d`'s lineage
into a currently bundle-path-only function, `combine()`'s signature) plus every existing
`sizing.estimate()` call site that doesn't have a bundle dir handy — `scripts/size-calibrate`
calls `estimate()` over bare brief paths with no bundle context, so a lineage-aware
`estimate()` needs a bundle-optional signature, which is real surface. Rejected: the brief's
own Scope section names `sizing.py` out of scope ("child-2 owns the signal and this child
only consumes it") — computing the sibling/organic split in `plan_policy.py`, which already
has `d` (the bundle dir) in hand, costs 0 lines of `sizing.py` change and reads the same two
already-public functions (`split.read_lineage`, `brief.conflicts_with`) any consumer would.

**Testing through `plan_policy.evaluate()` for every case.** Used `size_reasons()` directly
for (i)/(ii)/(iv)/(vi) so the dependency-guard's `hold` default (`Config.dependency_guard`)
can never be a confound — a brief that later grows an `External dependencies:` line would
change `evaluate()`'s early-return but not `size_reasons()`'s own behaviour, and the failing
criteria here are stated purely in terms of `size_reasons`. `evaluate()` is used ONLY for
(iii), because (iii)'s whole point is proving the real `leaves.run_sizer` → `leaves.
_stub_sizer` path runs, and that path is only reached from `evaluate()` (`size_reasons`
alone never calls the sizer — `evaluate` calls `size_reasons` which does).

## Refutation (forced, before declaring done)

**(a) Genuine red?** Yes — reverted `template/src/pdca_harness/plan_policy.py`,
`leaves.py`, `docs/07-crosscutting.md` (`git stash push` on those three, kept the new test
file untracked) and re-ran `PYTHONPATH=src python3 -m unittest
tests.test_plan_policy_split_child -v` from `template/`. `test_i_sibling_conflict_gets_
the_honest_provenance_line` FAILED — `AssertionError: 'scores large for a split child
(child 601 of a split of #500, depth 1) — driven by inherited/sibling fields; prefer
building over re-splitting' not found in 'oversized — consider \`pdca split\` first
(difficulty=high; brief 15.7 KB (cutoff 12 KB); 1 conflict(s) declared; structurally
predicts a large patch (~100 KB+); sizer says ok (confidence low))'` — exactly the
reproduction the brief's Falsifiability section describes as the load-bearing red.
`test_ii`, `test_iii`, `test_iv`, `test_vi` all stayed green on the red leg, exactly as
the brief predicts ("(ii) and (iii) pass on the red leg by construction ... which is why
they must live in the same module as (i)"). `git stash pop` restored the fix; re-ran — all
5 green.

**(b) Production path?** Yes. The test imports `from pdca_harness import leaves,
plan_policy, sizing, split` (module import, never a symbol import, per the brief's own
instruction) and calls `plan_policy.size_reasons` / `plan_policy.evaluate` directly — the
same functions `driver.advance` calls in production (`plan_policy.py`'s own module
docstring: "consulted by driver.advance before every work-dispatching beat"). `test_iii`
additionally reads back `sizing.json` written on disk by the real `leaves._stub_sizer`
(not a mock) to prove the sizer leg actually ran — `self.assertTrue(verdict.get("stub"))`.

**(c) Fixture includes the fault?** Yes. Every test writes a real `split-lineage.json`
(`split.LINEAGE`, the actual filename `split.py:493` writes) with the exact edge shape
`split.materialise` produces (`version`/`id`/`parent`/`siblings`/`depth`), not a stand-in
schema, and a real `brief.md` with a `Conflicts with:` field parsed by the real
`brief.conflicts_with`. `test_i` declares a conflict against an ACTUAL sibling id from that
same lineage record (`602`, present in `siblings`); `test_ii`/`test_iii` declare conflicts
against ids that are provably NOT in `siblings` (`811-814`) — the fixture is built to
include the exact discriminator the fix keys on, in both directions, not to curate it out.

## Runner used

`cd template && PYTHONPATH=src python3 -m unittest tests.test_plan_policy_split_child` —
exactly the invocation the brief's Falsifiability section names, which is also how
`Makefile`'s `check` target (`python3 -m unittest discover -s tests`, `PYTHONPATH=src`
exported) runs the whole suite. I ran the full suite too (`PYTHON=python3 make check`):
1679 tests, `OK (skipped=2)`, exit 0 — no regressions. I additionally created a scratch
`git worktree` off `origin/main`, applied `patch.diff` with `git apply --check` then for
real, and re-ran the new test there in isolation (green) to prove the diff is
self-contained and applies cleanly to a clean target checkout — not just to the
already-edited working tree I built it in. The worktree was removed after
(`git worktree remove --force`).

## Formatter / commit hooks

No Python formatter/linter is wired into this repo's CI or `Makefile` (checked: no
`.pre-commit-config.yaml`, no `[tool.black]`/`[tool.ruff]` in `template/pyproject.toml.jinja`,
`Makefile` runs only `unittest discover`). The one CI lint that touches files I edited is
`docs-check.yml` (Markdown/Mermaid lint + full-site render with a dangling-link audit) —
ran both steps locally against the edited `docs/07-crosscutting.md`:
`python3 docs/publishing/tools/lint_docs.py` → `lint_docs: OK`, and
`python3 docs/publishing/tools/render_site.py --check --out /tmp/site_build` → `render_site:
link audit OK`. New/changed Python lines were checked against the file's own prevailing line
length (nothing I added exceeds 99 columns; the file already runs many lines past 92-100,
so there is no narrower convention to violate).

## External dependencies

None beyond the brief's own list. `copier` was not needed to exercise the target
falsifiability test (it runs directly via `unittest`, not through a render pipeline); the
brief already scopes the `copier`-only suites as "not this test's responsibility" (they
exist to confirm the changed template files still render, a separate, non-gating concern
for this bundle, and I did not need to touch that path to satisfy criteria (i)-(vi)).
