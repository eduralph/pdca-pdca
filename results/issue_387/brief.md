# Brief — issue 387 / single-source-the-brief-base-for-gate-scripts

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** single-source-the-brief-base-for-gate-scripts
- **Defect:** the harness defines a base-resolution precedence ladder for bundle-scoped verify
  gates whose **last rung it never supplies**. `template/engine/scripts/run-verify.sh:25-27`
  tells every instance to "Resolve as: `$PDCA_BASE` > `$PDCA_VERIFY_BASE` > your own override >
  the brief's `Repo + branch target` > origin/<default>", but the driver exports only the first
  two (`template/src/pdca_harness/gates.py:468-476`) and ships no accessor a shell gate can
  call for the fourth. So every instance that fills in the C4 skeleton must re-implement
  `publish._clean_ref` **in bash**, from a comment that states the ladder but not the parsing
  rule. That parse has already been got wrong twice in Python and fixed twice — #235 (closed
  2026-07-04) and #262 (closed 2026-07-09) — and `publish._clean_ref`
  (`template/src/pdca_harness/publish.py:531-545`) now honours a backtick span **only** when it
  starts the field. The bash re-derivations carry the pre-#235 unanchored rule, so the two
  implementations of one parse disagree: for
  `- **Repo + branch target:** getwyrd/wyrd @ main (feature branch \`feat/x-slice\`)` Python
  resolves `main` while the shell resolves `feat/x-slice`. Publish then opens the PR against one
  base and C4-verify validates against another — for a bundle whose real base is not `main`
  (a stacked slice, a dependency-wave bundle, a standalone `pdca gates <id>`) the verifier
  either false-fails "patch does not apply — the bundle is stale" or proves red→green against a
  tree that lacks the prereq. One bug, two languages, is exactly what produced #235 → #262 →
  this. **Where the two halves live (verified, and it decides Scope):** the buggy `_brief_base()`
  named in the report is *not* in this repo — `template/engine/scripts/run-verify.sh` is a
  53-line skeleton that says "SKELETON. Fill this in for your project", `template/engine/`
  contains only that file plus `README.md.jinja` (no `engine/tests/` at all), and
  `git -C ../pdca-harness log --all -S "_brief_base"` finds nothing. It lives in the reporting
  instance, getwyrd/wyrd-pdca, as instance-authored code (`engine/scripts/run-verify.sh:166-178`
  and its parity test `engine/tests/test_run_verify.sh:140-145`). This bundle fixes **the
  harness's half**: the missing rung that forces the re-implementation.
- **Success criterion:** a bundle-scoped gate command can obtain the brief's own base
  **without reading `brief.md`**, and the three-rung ladder stays mutually exclusive:
  (a) for every bundle-scoped gate invocation, **exactly one** base variable is exported —
  `PDCA_BASE` when the brief names an `Onto branch`; else `PDCA_VERIFY_BASE` when a wave
  stack-base marker is present; else `PDCA_BRIEF_BASE` carrying the brief's own base;
  (b) `PDCA_BRIEF_BASE` is a remote-tracking ref of the same shape as the other two
  (`<remote>/<branch>`), so a gate script can use whichever is set interchangeably and can never
  produce the doubled `origin/origin/main` the report describes;
  (c) its value comes from the **same anchored parser publish uses** — not a copy — so
  `… @ main (feature branch \`feat/x-slice\`)` yields `origin/main`, `… @ \`feat/x\`` yields
  `origin/feat/x`, and a brief with no `Repo + branch target` field yields the default branch;
  (d) `publish`'s own resolved behaviour is unchanged (#235/#262 stay fixed, their tests stay
  green);
  (e) `template/engine/scripts/run-verify.sh:25-27` names the export as the last rung instead of
  instructing instances to parse the brief, so no future instance re-derives the parse.
- **Falsifiability:** RED on the base toolchain, no services and no network, on the target
  checkout Do is given. `cd template && PYTHONPATH=src python3 -m unittest tests.test_verify_base`
  fails on `origin/main`: that module already runs a **real** bundle-scoped gate command whose
  `cmd` echoes the exported bases into the bundle and reads them back, printing `UNSET` for an
  absent one (`template/tests/test_verify_base.py:25-32`), so a case asserting the third export
  reads `UNSET` today and the anchored-parse cases have nothing to read at all. GREEN with the
  patch. C4-verify earns a real red→green: `gates.py` / `publish.py` / `brief.py` classify as
  production hunks under `engine/scripts/run-verify.sh:41-46`, the red leg reverts them and
  keeps the test. The stub `Config` the module builds (`:35-48`) already sets
  `base_remote="origin"`, so the ref shape in (b) is assertable without a git fixture.
- **Invariant to restore:** the brief's base ref has **exactly one parse** in the harness, and
  every consumer — Python or shell, in-tree or in a rendered instance — obtains the resolved
  value from that one implementation rather than re-deriving it. Quantified over the category:
  it binds every consumer of the field, not the one instance that got it wrong — a patch that
  corrected only `publish.py` (already correct) or only one instance's bash would leave the next
  instance to re-derive the parse and visibly fails it, and so does one that adds a second
  parser anywhere. Self-test: could Do satisfy this by guarding a single module? No — the defect
  is that the parse is *reachable only from Python* while the ladder the harness publishes
  terminates in shell. Source: the twice-recurring failure the rule prevents (#235, #262, both
  against `publish._clean_ref`) plus the governing rule already stated at
  `template/src/pdca_harness/gates.py:450-467` — "the TEST base and the DEPLOY base must not
  diverge … these two exports are MUTUALLY EXCLUSIVE" (PR #282 review). Internal rule, Tier C
  per `docs/principles.md` §5; §5/§6 are an unfilled scaffold in this instance, so no §6
  category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** supply the ladder's missing last rung from the harness's single existing parse, so
  no gate script has to parse `brief.md` — the anchored parse becomes reachable as one accessor,
  the driver resolves the brief's base with it, the bundle-scoped base export is extended to
  cover that rung while staying mutually exclusive, and the C4 skeleton's guidance cites the
  export. / out of scope, explicitly: **getwyrd/wyrd-pdca's `engine/scripts/run-verify.sh` and
  `engine/tests/test_run_verify.sh`** — instance-owned files in a different repository; the
  report's fix items 1 and 2 are downstream work, filed as getwyrd/wyrd-pdca#204, and landing
  this change reduces that fix to deleting `_brief_base` and reading the exported ref. Also out
  of scope: changing `publish`'s resolved behaviour or `_clean_ref`'s rule (already correct);
  the mutual-exclusion contract between `PDCA_BASE` and `PDCA_VERIFY_BASE`; the fact that
  `gates.py:476` composes `origin/` inline rather than from `cfg.base_remote` (match the shape
  the existing exports use — do not go fix that inconsistency here); generating a shell case
  table from the Python tests; and filling in the C4 skeleton itself.
- **Repro instruction:** on a clean checkout of the target base —
  1. `git -C ../pdca-harness show origin/main:template/engine/scripts/run-verify.sh | sed -n '15,27p'`
     → the published ladder, ending in "the brief's `Repo + branch target`";
  2. `git -C ../pdca-harness grep -n "PDCA_BASE\|PDCA_VERIFY_BASE" origin/main -- template/src/pdca_harness/gates.py`
     → only the two exports at `:471` / `:476`; nothing supplies the last rung, and nothing
     outside `publish.py` can reach the anchored parse (`git grep -n "_clean_ref" origin/main`
     → `publish.py:531,553,559` only).
  3. The downstream symptom, **read-only — do not edit anything outside the target checkout**:
     `/home/eddie/wyrd/wyrd-pdca/engine/scripts/run-verify.sh:166-178` is the bash
     re-implementation with the unanchored rule, and `:186-192` shows it feeding
     `printf 'origin/%s'`. It is evidence, not a file this bundle touches.

  The named test automates (a)–(c) → red pre-fix.
- **External dependencies:** none
- **Test file:** `template/tests/test_verify_base.py` — append to the existing module; it was
  written for exactly this export path (#273) and already drives a real bundle-scoped gate
  command with a stub `Config` and no network. Appending earns its red fine here:
  `run-verify.sh:70-75` reverts **production** hunks only and keeps the test in place.
- **Citations expected:** Do must cite path:line on the target branch for every change. This is
  a composition slice — the new rung must compose into the existing export block, not sit beside
  it. The peer callsite is `template/src/pdca_harness/gates.py:450-476`: the commented
  resolution order and the `if onto … else read_stack_base …` chain that keeps the exports
  mutually exclusive; add the last rung *inside* that chain and extend the comment's contract to
  three. Do MAY open that one callsite. Supporting facts, already verified, that need no
  exploration: the anchored parse is `publish._clean_ref` (`publish.py:531-545`) and its caller
  `_resolve_target` (`:548-559`) splits the field on `@`; `brief.py` already houses the public
  per-field accessors this kind of value belongs in — `onto_branch` (`:281`), `depends_on`
  (`:196`), `test_files` (`:181`) — so an accessor there keeps `publish` importing one parse
  rather than owning it; `gates._run_one` (`gates.py:431-434`) does not currently receive `cfg`,
  while both of its callers (`gates.py:355`, `:383`) and `publish.py:855` do.
- **Prior-art check (triage cycles):** by affected file path —
  `git -C ../pdca-harness log --oneline origin/main -- template/src/pdca_harness/publish.py`
  → #235 and #262 both fixed `_clean_ref` **in Python only**, leaving no shell-side counterpart;
  `git -C ../pdca-harness log --oneline origin/main -- template/engine/scripts/run-verify.sh`
  → `2ef3e28` (#273 review, `Onto branch` precedence), `8e9b5fb` (#273), `71e12fa` (#165),
  `f7931d3` — the file has only ever been a skeleton + guidance;
  `git -C ../pdca-harness log --all -S "_brief_base"` → no such function has ever existed here.
  `gh search issues --repo eduralph/pdca-harness "base parser"` → #235, #262 (both closed, both
  Python-side), #336 (closed, unrelated), #387 (this).
  `gh pr list -R eduralph/pdca-harness --state open` → empty. Not fixed, not in flight, and no
  closed/rejected attempt on this seam.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
