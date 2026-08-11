# split: report convergence before --accept files irreversible tracker issues

- **Slug:** split-convergence-report
- **Defect / goal:** `pdca split --accept` files real, unrevokable tracker sub-issues
  without ever running the estimate over the staged children. `preflight`
  (`split.py:224-245`) checks only the reasons acceptance would fail — a missing proposal, a
  parent already marked, ordering that names a non-sibling or forms a cycle
  (`_validate_ordering`, `:247-265`). Nothing asks the one question that matters: *does this
  split actually make the children smaller?* A split that leaves every child `oversized` is
  discovered one full cycle later, when each child's guard fires and the planner is pointed
  at `pdca split` again. Report it at the only point where it can still change the decision.
- **Success criterion:**
  (a) **both** acceptance paths emit the report before anything irreversible happens:
      `pdca split <id> --accept` (the auto-filing branch, which reaches `preflight` at
      `cli.py:733`) **and** `pdca split <id> --accept --ids a,b` (which calls
      `split.accept` directly at `cli.py:764` and never reaches `preflight` today). The
      `--ids` path is the one the docs call *required* for a tracker `pdca` cannot reach
      (`docs/07-crosscutting.md:192-197`) — i.e. the operator who has already paid for the
      issues by hand and most needs the verdict. Reproduced on the rejected attempt:
      `pdca split 500 --accept --ids 601,602` materialised both children and printed nothing
      but `issue_500 marked split; run `pdca flow 601 602``;
  (b) the report names, per staged child, its structural band against the parent's and which
      feature carries its score — `SizeEstimate.reasons` already carries this — and says
      plainly when the split does not lower the band for most children;
  (c) it is **not blinded by child-2's exclusion.** A `Conflicts with` edge *between*
      siblings is the splitter's statement that those two children edit a shared resource
      (`leaves.py:1274` calls those fields "the point"), so a proposal whose children all
      conflict pairwise is a split that separated nothing, and must be reported as NOT
      converged. The report therefore reads child-2's exposed sibling-conflict count rather
      than seeing an excluded 0 and reading the proposal as clean;
  (d) **its own output can never abort the acceptance.** A stderr that fails part-way — what
      `pdca split 500 --accept 2>&1 | head` produces — must not change the exit code or the
      set of bundles created. On the rejected attempt a `BrokenPipeError` from the second
      report line escaped `preflight` and produced either an unhandled traceback or the
      flatly *wrong* `split: issue_500 has no split-proposal.md — run `pdca split 500`
      first` with rc 1 on a bundle whose proposal was fine, because `cli.py:726-737` wraps
      `preflight` in an `except OSError` that means "no proposal". Guard these writes the way
      `cli.py:755-762` already guards
      its own (`except OSError: pass`), and cover it with a test that fails the stream;
  (e) it is **advisory and deterministic**: it never blocks, never prompts, and never
      changes what is filed or materialised — matching the size guard's warn-only stance and
      the same calibration argument (`plan_policy.py:88-102`).
- **Constraints (verified against `main`):** at `preflight` time the children have no
  tracker ids — every ordering ref is a sibling **label** by construction
  (`_validate_ordering`, `:247-259`), so a staged estimate must present those labels as the
  sibling set for child-2's exclusion to apply the same rule the live estimator will. Child
  labels are pinned to `child-\d+` by `_LABEL_RE` (`split.py:41`), so composing a temporary
  path from a label cannot traverse. Keep the ordering guarantee `preflight` exists for: it
  runs **before** `file_children` (`cli.py:733` then `:742`), and nothing added here may
  file, write into the instance, or leave anything behind on failure.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Falsifiability:** RED on `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_split_convergence`. Pre-fix no convergence report exists on either path, so
  every assertion on its output fails and the report helper raises `AttributeError`;
  criterion (d) is falsifiable by driving `preflight` with a stderr that raises on its second
  write and asserting the exit code and created-bundle set are unchanged — pre-fix that
  raises out. **Wave-3 bundle**: gate runs on the folded integration branch carrying children
  1-3 (`PDCA_VERIFY_BASE`, `gates.py:379-397`); note this child edits `split.py`, which
  child-1 also edited, and the folded base is precisely what makes that apply cleanly. Drive
  `split.preflight` / `split.accept` directly so no `gh`, network or container is needed.
- **Reproduction:** `pdca split <id> --accept` on any proposal — the children are filed and
  materialised with no estimate ever run over them; and `pdca split <id> --accept --ids a,b`
  never even calls `preflight` (`cli.py:764`).
- **Scope (one logical fix) / out of scope:** `template/src/pdca_harness/split.py` (the
  report and its call site), `template/src/pdca_harness/cli.py` (the `--ids` path and the
  stderr guarding), `docs/07-crosscutting.md` — **restricted to `### The split`**
  (`:174-218`, the `pdca split` / `--accept` section, including the `--ids` prose at
  `:192-197`). Leave `### The process` (`:36-99`) to child-3 and `### The estimate`
  (`:100-173`) to child-2; child-3 and child-4 are scheduled into different waves precisely
  because they share this file. **Out of scope:** `plan_policy.py`, `sizing.py`,
  `leaves.py`; making the report blocking or interactive; changing what `--accept` files,
  validates or materialises; a `max_split_depth` cap (held in reserve deliberately — the
  earlier children remove the *reason* depth grows, a cap only truncates the symptom).
- **External dependencies:** `copier importable (.venv)` — the patch changes files under
  `template/`, so the target's render and `copier update` compatibility root suites exercise
  it; without copier those seven tests skip themselves and T3 reports a green that tested
  nothing. Otherwise python3 ≥ 3.11 stdlib + git only; the test runs in the offline driver
  suite with no tracker, network or container — in particular it must not require `gh`, so
  drive `preflight` / `accept` directly rather than through a filing path.
- **Test file:** `template/tests/test_split_convergence.py` — a new module in the offline
  driver suite. The C4 gate reverts only the PRODUCTION hunks and keeps the test
  (`run-verify.sh:121-130`), so a new file earns its red. **Import the module, never the new
  symbols** — `from pdca_harness import split, sizing`, then attribute access inside test
  bodies; a module-level `from pdca_harness.split import <helper>` raises ImportError on the
  red leg, giving 0 tests run and exit 77 `PDCA-UNVERIFIABLE` (`run-verify.sh:145`) instead
  of a red that proves anything.
- **Difficulty:** medium
- **Depends on:** 457
- **Conflicts with:** 458

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Reviewer C4 FAIL: criterion (d) is not fully met. A persistently broken stderr still raises OSError after both bundles are created — the later status write at template/src/pdca_harness/cli.py:830 is unguarded — so the advisory report can change the exit code. The shipped test masks this: its fake stderr fails only once (fail_at counter), while a real broken pipe raises on every write. Next attempt: guard ALL stderr writes on the acceptance path (cli.py:830 and any others) the same way as the existing except-OSError guards, and strengthen the test's fake stream to fail persistently (raise on every write from the first failure on), asserting the exit code and created-bundle set are unchanged.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
