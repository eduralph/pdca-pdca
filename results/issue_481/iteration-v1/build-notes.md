# Build notes — issue 481 / split-parent-keeps-a-plan-artifact

Target branch: `eduralph/pdca-harness @ main`, base commit `4050da290242ac1c797c93d2bce997a00263ad47`
(worktree HEAD; `origin/main` tip). All citations below are against that commit + the
patch applied (i.e. the file as it now stands in `$PDCA_WORKTREE`).

## What I changed, and why

Two production modules, matching the brief's "Invariant to restore" (both are needed —
its own self-test proves neither alone is sufficient):

### 1. `template/src/pdca_harness/state.py:301-334` — `state()`

Before: a briefless bundle unconditionally fell to `RESOLVED if is_resolved(d) else
UNPLANNED` (old `state.py:301-307`). `is_resolved` requires a `resolved` key in
`notes.json` (`state.py:257-264`), so a briefless bundle carrying only the close marker —
no `notes.json`, or one without a `resolved` record — always landed on `UNPLANNED`. That
is the general shape behind both the realistic split-parent bug and the brief's (e)
falsifiability claim ("a bare bundle holding only `close-disposition` also derives
`UNPLANNED`").

After: `state()` computes `has_do_artifact = patch.diff or CLOSE_MARKER exists`
(`state.py:313`) BEFORE deciding on brief presence. When the brief is missing but a
Do-era artifact is present, it does **not** derive `UNPLANNED`/`RESOLVED` — it falls
through to the same past-Do ladder (`check-gates.json` → `SUMMARY.md` → sign-off
outcome) a briefed bundle already uses (`state.py:314-320`). This is the direct
application of the brief's own CLOSE_MARKER contract (`state.py:40-44`, cited by the
brief) — "the close marker is the Do artifact ... so the state machine reads it as past
Do" — which line `state.py:310` (unchanged) already honours for a BRIEFED bundle;
the fix is making the `not bp.exists()` branch respect the same equivalence instead of
special-casing it away.

I deliberately did NOT special-case `CLOSE_MARKER` only (leaving `patch.diff`
unhandled): the brief's Invariant paragraph names both ("a `patch.diff`, or the close
marker that stands in for one") and the existing equivalence at line-310's condition
already treats them identically for the has-Do check, so treating them differently one
line up would be an arbitrary asymmetry, not a narrower fix.

### 2. `template/src/pdca_harness/split.py` — `accept()`

Before: `accept()` (`split.py:811-878` pre-fix) always archived with
`include_brief=False` and never wrote a parent brief, so a parent that had already lost
its brief to `iterate-plan` before the split (the "realistic case" the module's own
comment at `split.py:888-897`, was `:824-826` pre-fix, names) ended up with the close
marker and no brief at all.

After (citations against the patched file):
- `split.py:833-848` — pre-write validation, before any write: if `parent/brief.md` is
  absent, resolve the most-recently-archived original via the new
  `_archived_brief_source` (`split.py:735-754`), which scans `iteration-v<N>/` highest-N
  first for an authored (non-placeholder) `brief.md`. If none exists, `accept()` raises
  `SplitError` — refusing while refusing is still free, before any child is staged. This
  is the one case this fix does NOT force through: a bundle that was genuinely never
  planned at all (no top-level brief, no archived one) has nothing to build a Plan
  artifact FROM, and the brief's own out-of-scope note keeps `leaves.do_split`'s refusal
  intact for the same reason. It never fires on the realistic case, because that case,
  by construction, always has `iteration-v1/brief.md`.
- `split.py:757-787` — `_parent_split_brief(source, created)` builds the new brief:
  `Slug` and `Repo + branch target` are copied verbatim from the archived original via
  `brief.whole_field` (so `handoff.check_planner`'s three mandatory fields — `slug`,
  `success criterion`, `repo + branch target`, `handoff.py:131-134` — are filled with
  values a human already authored, not re-derived or guessed); `Defect` and `Success
  criterion` are rewritten to describe the split outcome and enumerate every created
  child bundle by name (criterion (c)).
- `split.py:924-933` — the write itself, inside the SAME protected `try` block as the
  lineage record / `build-notes.md` breadcrumb / `CLOSE_MARKER` write
  (`split.py:904-949` region), ordered right after the lineage write and before the
  breadcrumb — so it shares the existing transaction discipline the brief asks to keep
  (`split.py:828-878` in the brief's pre-fix citation): every write before the marker,
  and only for a parent that had no brief in the first place (`parent_had_brief`,
  captured at `split.py:839`, before any write) — a briefed parent's `brief.md` is never
  even opened for writing, which is what makes criterion (f) hold trivially, not by
  special-casing sameness after the fact.
- `split.py:964-969` — the failure path: if this call wrote a new parent brief
  (`wrote_parent_brief`, set at `split.py:933`) and a later write in the same block
  raises, the except handler removes it, alongside the existing `CLOSE_MARKER` /
  lineage rollback — "a failed accept must not leave a new parent brief behind either"
  (brief's Scope).

### Why one module was not enough (the brief's own self-test)

Fixing only `state()` would leave `split.accept` still writing no parent brief for the
realistic case — the close-marker bundle would stop reading `UNPLANNED` (state.py's
past-Do ladder returns `BUILT`), but `SUMMARY.md`'s §1 Spec is built FROM the brief
(`assemble.assemble_summary`, per the brief's citation) and there would be none, so (b)
fails exactly as the brief predicts. Fixing only `split.accept` would leave (e) failing
for ANY other path that leaves a bundle briefless + close-marked without going through
`split.accept` at all (the brief's own directly-constructed test case). Both are in this
patch.

## The three self-refutation questions

**(a) Genuine red?** Yes. I reverted `state.py` + `split.py` via a scoped `git stash`
(kept `test_split.py`'s new class), then ran
`PYTHONPATH=src python3 -m unittest tests.test_split.SplitParentKeepsAPlanArtifact -v`
from `template/`. Result: 5 of 7 new sub-tests failed —
`test_a_realistic_parent_is_not_unplanned_or_resolved_after_accept` (`AssertionError:
'UNPLANNED' == 'UNPLANNED'`), `test_a_realistic_parent_gets_a_complete_plan_artifact`
(`brief.md` did not exist), `test_the_new_parent_brief_names_every_child`
(`FileNotFoundError` on `brief.md`), and both (e)-shaped tests
(`test_close_marker_with_no_brief_never_derives_unplanned_however_it_arose`,
`test_a_bare_close_marker_bundle_is_still_not_unplanned_without_notes_json`) — same
`'UNPLANNED' == 'UNPLANNED'` failure. Then I re-applied the fix (`git stash apply` +
`git stash drop`) and re-ran: all 103 tests in `test_split.py` pass, and the full
offline driver suite (`python3 -m unittest discover -s tests`, `template/`) is
1901 tests, `OK (skipped=2)` — unchanged skip count from before this change, so nothing
else in the suite regressed.

**(b) Production path?** Yes. Every new test calls the real `split.accept`,
`state.state`, `handoff.check_planner`, and `driver._archive_iteration` — no
stand-in, no re-implementation. The (e) tests write the close marker directly (as the
brief's Test file note instructs, "build the briefless + close-marker shape directly")
but still read the verdict off the real `state.state`.

**(c) Fixture includes the fault?** Yes. `_make_realistic_parent` (test_split.py) seeds
a COMPLETE authored brief (slug, defect, success criterion, repo+branch target — per the
brief's Test file note, not `Accepting.setUp`'s bare `- **Slug:** parent`, which
`check_planner` would rightly reject as a rebuild source) and archives it through the
driver's OWN `driver._archive_iteration(self.parent, 1, include_brief=True)` — not
hand-placed — so the fixture is exactly the shape `iterate-plan` produces, and the
`split.accept` call that follows is the real transaction, not a curated-safe variant.

## What I ruled out

- **Refusing `accept` on a briefless parent outright.** The brief's Scope explicitly
  forbids this ("Refusing the accept on a briefless parent does NOT meet the criterion:
  the in-session split after iterate-plan is the realistic case and has to complete").
  I only refuse in the narrower, genuinely-unplannable case (no brief anywhere, top-level
  or archived) — which the realistic case never hits.
- **Deriving the parent brief from `split-proposal.md` instead of the archived
  original.** The proposal's children are drafted BRIEFS FOR THE CHILDREN, not a
  description of the parent — using it as the source would mean copying one child's
  content onto the parent (wrong Slug, wrong Repo+branch target) or fabricating those
  fields from nothing. The brief's Scope explicitly leaves the source as "Do's call" and
  the archived original already carries validated, human-authored Slug / Repo+branch
  target — reusing it is strictly less invented content than any alternative.
- **A brand-new intermediate state name for "past-Do, briefless".** Considered adding
  something like `PAST_DO_NO_BRIEF` instead of falling through to the existing ladder.
  Rejected: the brief's criterion (a) only requires "not `UNPLANNED` (and not
  `RESOLVED`)", never asks for a new label, and the existing past-Do ladder
  (`check-gates.json` → `SUMMARY.md` → sign-off) already answers the question correctly
  for a briefed bundle in the identical shape (patch.diff/marker present, downstream
  artifacts still absent) — reusing it is a ~20-line diff; a new state would mean
  touching `HALTED`, `TERMINAL`, the driver's dispatch table, and every consumer that
  switches on the state string, for no behavioural gain this brief asks for.
- **Guarding `assemble.assemble_summary` against a missing brief instead of restoring
  one.** That would be the "guard the symptom" shape the harness explicitly warns
  against: the SUMMARY assembler isn't broken, the absence of a Plan artifact is — and
  the brief's Invariant section says so directly ("state derivation never places such a
  bundle before Plan"), not "SUMMARY tolerates a missing brief".

## External dependencies

None. Everything here is pure filesystem + the pre-existing `split`, `state`, `brief`,
`handoff`, `driver` APIs, run through the target's own `python3 -m unittest` — no
network, no tracker, no Docker.
