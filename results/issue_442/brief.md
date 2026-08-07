# Brief — issue 442 / gates-doc-stale-one-marker-claim

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.
> The field labels below are parsed by the driver — keep the `- **Label:** value`
> shape. The success criterion is the load-bearing field: it is the sentence
> Check tests "did this work" against.

- **Slug:** gates-doc-stale-one-marker-claim
- **Defect:** The evidence-marker paragraph of the `gates.py` module doc
  (`template/src/pdca_harness/gates.py:38` on the target's `main`) still claims
  "``PDCA-UNVERIFIABLE`` stays the one marker that can change a ``result``." Twenty lines
  below, the same docstring introduces ``PDCA-DEFERRED`` (issue #401, `gates.py:55-68`,
  constant at `gates.py:98`) — a second marker that changes a `result` (to `deferred`).
  The sentence predates #401 and is now false; pdca-pdca's issue_401 cycle flagged it
  (SUMMARY §10: "stale once PDCA-DEFERRED lands; fix the sentence in a follow-up") and
  the follow-up never happened.
- **Success criterion:** The module doc's evidence-marker paragraph no longer claims
  exclusivity for ``PDCA-UNVERIFIABLE``: it names both ``PDCA-UNVERIFIABLE`` and
  ``PDCA-DEFERRED`` as the declarations that can change a ``result`` (e.g. the issue's
  suggested wording "…and only the ``PDCA-UNVERIFIABLE``/``PDCA-DEFERRED`` declarations
  can change a ``result``"). A shipped test reads `gates.__doc__` and fails against the
  stale sentence, passes against the corrected one.
- **Falsifiability:** RED is producible offline on any Do checkout: a test asserting the
  corrected claim over `pdca_harness.gates.__doc__` fails on current `main` (the stale
  sentence is at `gates.py:38`, verified at `0fbfa26`). The instance's C4 script reverts
  production hunks and keeps briefed tests; `gates.py` is classified production, so the
  revert restores the stale docstring and the test goes red mechanically.
- **Invariant to restore:** A module doc's normative claims must match the contract the
  module implements — an exclusivity claim ("the one marker") is invalidated the moment a
  second member joins the set it describes. Source: the same docstring's own #401
  paragraph (`gates.py:55-68`), which defines ``deferred`` as a result-changing
  declaration with the same declaration rule.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** correct the one false sentence in the `gates.py` module docstring (and ship
  the doc-consistency assertion that pins it) / out of scope: any behavioral change to
  gates.py, any rewording of the rest of the docstring, the stale "rounds rule ships
  disabled" comment in size_signal.py (separate defect, not this issue).
- **Repro instruction:** `git -C ../pdca-harness show origin/main:template/src/pdca_harness/gates.py | sed -n '38p'`
  → prints the exclusivity claim; `grep -n "PDCA-DEFERRED" template/src/pdca_harness/gates.py`
  → shows the second result-changing marker the sentence denies.
- **External dependencies:** none
- **Test file:** template/tests/test_gate_deferred.py (append to the #401 suite: assert
  the module doc names ``PDCA-DEFERRED`` alongside ``PDCA-UNVERIFIABLE`` in the
  result-changing claim and no longer contains the "stays the one marker" wording. An
  appended test earns its red under this instance's C4 contract — run-verify.sh reverts
  production hunks and runs the changed test modules.)
- **Citations expected:** Do must cite path:line on the target branch for every change —
  the sentence at `template/src/pdca_harness/gates.py:38`, the #401 paragraph at
  `gates.py:55-68`, `DEFERRED_MARKER` at `gates.py:98`.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- template/src/pdca_harness/gates.py` — #401's fix landed the deferred paragraph
  (`07766ed`) but never touched line 38; the stale sentence is present at `0fbfa26`
  (current origin/main). No open PRs (`gh pr list -R eduralph/pdca-harness` → empty).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
