# Brief — issue 386 / remote-control-test-holds-in-both-postures

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** remote-control-test-holds-in-both-postures
- **Defect:** `template/tests/test_remote_control_docs.py:69-75`
  (`test_it_stays_off_by_default`) walks every line of `pdca.toml` and asserts each line
  containing `--remote-control` starts with `#`. That is right for the **unrendered template**,
  where the flag ships as a commented example. But this suite renders into every instance — it
  is explicitly written to run in both postures (`:19-24` picks `pdca.toml.jinja` or
  `pdca.toml` and derives `RENDERED`; `:45` already skips a rendered-only case) — so an
  instance that **enables** the seam, which is the entire point of documenting it (#337),
  inherits a permanently red test and must carry a local test delta forever. getwyrd/wyrd-pdca
  runs Remote Control on all four interactive leaves (its #176) and had to adapt this test
  during the v0.56.0 template update (its #195). The test pins a template-only *default* as if
  it were a universal invariant.
- **Success criterion:** with the patch, `template/tests/test_remote_control_docs.py`
  (a) passes on the unrendered template, where the flag is commented; (b) passes on a rendered
  instance whose `pdca.toml` carries an **uncommented** `--remote-control` in the argv of
  `interactive = true` leaves (planner / signoff / publisher / act) — this is the case that is
  red today; and (c) still **fails** on a rendered instance whose `pdca.toml` carries an
  uncommented `--remote-control` in a **headless** leaf's argv (builder / reviewer / any
  advisory leaf), because that flag starts an interactive session with no human to reach and
  hangs the flow. The existing doc-phrase assertions (`APPEND`, "do not add a second",
  `CLAUDE-ONLY`, "headless builder/reviewer must NOT carry it") and the duplicate-argv check
  keep passing unchanged in both postures.
- **Falsifiability:** RED on the base toolchain, no services, on the target checkout Do is
  given. Posture (c) — the protective half — is the leg that can go red today and must stay
  able to: it is currently **not asserted at all**, so a headless argv carrying the flag passes.
  Posture (b) is red on `origin/main`: construct a rendered-shaped `pdca.toml` with the flag
  uncommented on `[leaves.planner]` and run the module's assertion against it — it fails on the
  unpatched tree and passes with the patch. Because the module today reads only the repo's real
  `pdca.toml`, the regression cases must drive the assertion over **synthetic config text** in
  a temp dir rather than the live file; that is the shape that makes both legs falsifiable in
  one run of `cd template && PYTHONPATH=src python3 -m unittest tests.test_remote_control_docs`.
  **Gate posture — declared, not a gap:** this bundle's patch is confined to
  `template/tests/*.py`, so `engine/scripts/run-verify.sh:51-53` classifies it **test-only** and
  C4-verify exits 77 `PDCA-UNVERIFIABLE` → SUMMARY §6 NEEDS-HUMAN rather than a false red. That
  is the sanctioned path for this class (issue #165 discipline; docs/INTEGRATION.md §4 names an
  UNVERIFIABLE C4 as a project-defined human-only item). The human judges it by reading the diff
  plus the unittest command above; do **not** invent a production edit to manufacture a red leg.
- **Invariant to restore:** a test the template ships **into** rendered instances may assert
  only properties that hold in **every posture the template sanctions**; a property that holds
  solely in the unrendered template must be scoped to it, and where a real protection exists it
  is the protection — not the default — that gets asserted. Quantified over the category: this
  binds every posture-sensitive assertion in the shipped suites, not just this one method — a
  patch that merely silenced `test_it_stays_off_by_default` in the enabled posture, leaving the
  headless-leaf case unasserted, visibly fails it. Source: the file's own precedent at
  `template/tests/test_remote_control_docs.py:45-52`, where
  `test_no_leaf_block_declares_argv_twice` is already `skipUnless(RENDERED, …)` for exactly this
  class of reason ("counts are only meaningful after Jinja branches resolve") — internal rule,
  Tier C per `docs/principles.md` §5. §5/§6 are an unfilled scaffold in this instance, so no
  §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** make the shipped assertion posture-correct — the off-by-default property is
  asserted where it holds, and the property that holds in every posture (the flag rides only
  `interactive = true` leaves, never a headless argv) is asserted in both. / out of scope:
  changing `pdca.toml.jinja`'s Remote Control guidance or its doc phrases in any way (issue
  #396 is open against that block — leave it alone so the two can land independently);
  enabling or disabling the seam anywhere; the other assertions in this module; any driver or
  engine code.
- **Repro instruction:** on a clean checkout of the target base, take the rendered posture the
  template sanctions: copy `template/pdca.toml.jinja`'s Remote Control block into a
  `pdca.toml`-shaped file with `--remote-control` **uncommented** on `[leaves.planner]`'s argv,
  point the module's `TOML` at it, and run
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_remote_control_docs` →
  `test_it_stays_off_by_default` fails with
  `--remote-control is active, not commented: …`. Conversely, put the uncommented flag on
  `[leaves.builder]` (the genuinely dangerous case) and the suite passes — the protection that
  matters is absent. Cross-check against the live instance:
  `git -C ../pdca-harness show origin/main:template/tests/test_remote_control_docs.py`.
- **External dependencies:** none
- **Test file:** `template/tests/test_remote_control_docs.py` — the defect *is* this file, so
  the regression ships in it. Appending to an existing test file is fine for this project's C4
  red leg (`run-verify.sh:70-75` reverts production hunks only and keeps the tests), though as
  stated under Falsifiability this particular bundle has no production hunks and will classify
  UNVERIFIABLE regardless.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cue: the posture-scoping idiom to mirror is in the same file —
  `template/tests/test_remote_control_docs.py:19-24` (the `TOML` / `RENDERED` resolution) and
  `:45-52` (`@unittest.skipUnless(RENDERED, …)` with a docstring stating *why* the assertion is
  posture-bound). Follow that precedent rather than inventing a new mechanism, and keep each
  assertion's docstring stating which posture it binds.
- **Prior-art check (triage cycles):** by affected file path —
  `git -C ../pdca-harness log --oneline origin/main -- template/tests/test_remote_control_docs.py`
  → a single commit, `a641742` ("docs(leaves): document the Remote Control seam on the
  interactive leaves (#337)"), which introduced the method; nothing has revisited it.
  `gh search issues --repo eduralph/pdca-harness "remote-control"` → #337 (closed, the origin),
  #386 (this), #396 (open — the doc example's flag/positional-seed collision, in
  `pdca.toml.jinja`, a different file; excluded above so the two do not collide).
  `gh pr list -R eduralph/pdca-harness --state open` → empty. Not fixed, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
