# Result — issue 420 / bound-leaf-subprocess-memory

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: Leaf subprocesses are spawned with **no resource bound of any kind**, so one
  leaf's build footprint can take down the whole run — driver, every lane, every bundle —
  and does so *unattributably*. Observed live on a two-lane `pdca flow` (wyrd-pdca,
  2026-08-02): both Check reviewer leaves ran the independent re-verification
  `agents/reviewer.md` mandates (stash → confirm red, unstash → confirm green), wrote ~69 GB
  of cold build trees in ~13 minutes, and `systemd-oomd` killed the **entire terminal
  cgroup** for memory pressure (53.4 G peak). Neither reviewer had written
  `check-review.md`; the run's whole Check band was lost, with nothing in any gate log to
  say why — because oomd kills the *cgroup*, not the offending process, the failure surfaces
  as the driver simply vanishing.

  Verified on `origin/main`: `leaves._invoke` (`template/src/pdca_harness/leaves.py:218-285`)
  is the single spawn choke point for every leaf — interactive leaves via
  `subprocess.run(argv + [seed], …)` at `:259`, headless leaves via
  `progress.run_with_heartbeat(argv, …)` at `:276` (which `Popen`s at
  `template/src/pdca_harness/progress.py:127-130`). Neither path applies any memory bound,
  and a repo-wide grep for `MemoryMax` / `systemd-run` / `setrlimit` / `ulimit` / `cgroup` /
  `OOMPolicy` across `template/src/`, `template/agents/`, `template/engine/`,
  `template/scripts/` returns **zero** hits. The harness already bounds the two *other*
  resources a leaf can exhaust — wall clock (`progress.run_with_heartbeat(timeout=…)`, #368,
  `progress.py:66-74`) and disk (`[driver].sweep_worktrees`, #297, `config.py:313-320`) —
  memory is the one dimension left unbounded.
- Success criterion: On `eduralph/pdca-harness` @ `main`, a new test
  `template/tests/test_leaf_memory_cap.py` fails before the change and passes after it,
  pinning all four of:
  1. with a memory bound configured, the argv `leaves._invoke` actually spawns is the
     leaf's argv **wrapped** in the bound, for the **headless** path;
  2. …and for the **interactive** path, with the leaf still inheriting the parent terminal
     (a seeded REPL that loses its tty is a regression, not a fix);
  3. with **no** bound configured — the default — the spawned argv is byte-for-byte today's
     argv (unchanged behaviour, opt-in knob);
  4. with a bound configured but the host facility **absent**, the spawned argv is
     byte-for-byte today's argv and the leaf still runs (a documented no-op, never a hard
     failure on a host that cannot enforce it).

  All four are demonstrable by C4-verify on the patch alone, offline, with the spawn stubbed
  — no real OOM, no systemd, no network.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: Give the driver an **optional, configured memory bound applied to every leaf
  spawn**, so a leaf that overruns dies as itself and the flow survives to report it:
  - a `[driver]`-level bound applying to all leaves, with a per-leaf `[leaves.*]` override
    (the issue proposes `[driver].leaf_memory_max` and `[leaves.*].memory_max`; keep those
    names — they are the public config surface and the docs/`pdca.toml.jinja` text has to
    match them);
  - **unset ⇒ today's behaviour exactly** — no wrapping, no new process, byte-identical
    argv. This is an opt-in knob: no portable numeric default exists, and a wrong cap is
    itself a way to kill a run;
  - **facility absent ⇒ a documented no-op**, not an error: the harness runs on hosts with
    no cgroup/systemd facility at all, and a configured-but-unenforceable bound must degrade
    to today's behaviour with the degradation stated in the docs;
  - the interactive leaves keep their inherited terminal (they are REPLs the human types
    into) and the headless leaves keep their stdin-fed prompt, heartbeat and stream reader
    (`leaves.py:253-285`);
  - a leaf killed for exceeding its bound must surface as **that leaf's** non-zero exit
    through the existing `LeafError` / `_invoke_leaf_resilient` path (`leaves.py:280-326`),
    so the bundle records a leaf failure instead of the driver disappearing.

  **Which containment facility is used is Do's call** — the issue's suggestion (a capped
  transient scope, with the kill policy set so the kernel reaps the offender *inside* the
  scope and the leaf survives to report) is a suggestion, not a specification. Do should
  choose it against the constraints above and cite the peer callsites below.

  Out of scope: bounding **gate** commands (`gates.py` runs the instance's own scripts on a
  different spawn path — a separate defect if it is one); a host-level memory/swap
  preflight, which is the open issue **#421** and must not be absorbed here; CPU, file-
  descriptor or disk bounds (disk is #297, already shipped); changing what the reviewer
  *does* (its re-verification mandate is correct — #422/#419 are that thread); any
  behavioural change when the knob is unset.

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — == T3: root suite OK, driver suite FAILED (rc 1)
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Task under review: add an opt-in per-leaf subprocess memory cap that preserves existing spawns when unset or unenforceable and supports driver, named-leaf, advisory-array, and variant overrides.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The decision surface is explicit—contain every leaf while preserving default and unsupported-host behavior—and the target documents those operational consequences at `docs/07-crosscutting.md:333`. |
| C2 Reproduction (red pre-fix) | PASS | Reverting only `config.py` and `leaves.py` in a temporary target-derived tree ran all 22 tests and produced 15 assertion failures on unwrapped argv (not import/collection errors), including the core expectation at `template/tests/test_leaf_memory_cap.py:163`. |
| C3 Change | PASS | The previously rejected public-contract gap is closed: the shared spawn choke point wraps both paths at `template/src/pdca_harness/leaves.py:370`, while variant inheritance and array-form advisory construction retain per-leaf policy at `template/src/pdca_harness/leaves.py:888` and `template/src/pdca_harness/leaves.py:2253`. |
| C4 Verification (red→green) | PASS | Independent replay in a clean temporary tree gave red = 22 run/15 assertion failures and green = 22 run/0 failures; the green cases cover interactive TTY inheritance and unsupported-facility no-op at `template/tests/test_leaf_memory_cap.py:168` and `template/tests/test_leaf_memory_cap.py:189`. |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether a runtime capability probe is the right root-cause boundary or whether facility readiness should be resolved eagerly elsewhere—the probe at `template/src/pdca_harness/leaves.py:277` can intentionally turn a configured cap into an unbounded run, so containment depends on that policy choice. |
| T1 Structure | PASS | Centralizing policy at `_invoke` makes the bound apply across both spawn shapes, and the single array-form constructor prevents configuration drift across advisory pools (`template/src/pdca_harness/leaves.py:326`, `template/src/pdca_harness/leaves.py:2253`). |
| T2 Shape | NEEDS-HUMAN | Decide whether to accept the recorded docs pass without independent replay—the asserted `run-docs-check.sh` runner is absent from the target checkout, so its link-audit result could not be reproduced; the new public section starts at `docs/07-crosscutting.md:333`. |
| T3 Runtime | PASS | The recorded advisory red is not reproducible: the patched target independently completed the driver suite with 1,563 tests, rc 0 (2 skipped), and the root suite with 7 tests skipped/rc 0; the focused runtime contract is at `template/tests/test_leaf_memory_cap.py:153`. |
| T4 Contribution | NEEDS-HUMAN | Decide whether the frozen contribution-gate pass is sufficient—the required commit message and PR-description inputs were not supplied, so the tracker-id/user-impact check could not be independently rerun. |
| T5 Judgment | NEEDS-HUMAN | Decide whether prior-art clearance is complete: merged history was checked by every affected path and showed no earlier memory-cap change, but closed/rejected tracker work cannot be mechanically settled from the three supplied artifacts; the public behavior being cleared is at `docs/07-crosscutting.md:370`. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether stubbed argv evidence is enough for operational containment—no real scope or OOM was exercised; on a systemd user session, set `leaf_memory_max` low, run a leaf that allocates past it, and confirm that leaf exits non-zero while the driver and a sibling survive, matching `docs/07-crosscutting.md:335`. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] C5 Causal adequacy — Decide whether a runtime capability probe is the right root-cause boundary or whether facility readiness should be resolved eagerly elsewhere—the probe at `template/src/pdca_harness/leaves.py:277` can intentionally turn a configured cap into an unbounded run, so containment depends on that policy choice.
- [x] T2 Shape — Decide whether to accept the recorded docs pass without independent replay—the asserted `run-docs-check.sh` runner is absent from the target checkout, so its link-audit result could not be reproduced; the new public section starts at `docs/07-crosscutting.md:333`.
- [x] T4 Contribution — Decide whether the frozen contribution-gate pass is sufficient—the required commit message and PR-description inputs were not supplied, so the tracker-id/user-impact check could not be independently rerun.
- [x] T5 Judgment — Decide whether prior-art clearance is complete: merged history was checked by every affected path and showed no earlier memory-cap change, but closed/rejected tracker work cannot be mechanically settled from the three supplied artifacts; the public behavior being cleared is at `docs/07-crosscutting.md:370`.
- [x] Validation — fitness-to-purpose — Decide whether stubbed argv evidence is enough for operational containment—no real scope or OOM was exercised; on a systemd user session, set `leaf_memory_max` low, run a leaf that allocates past it, and confirm that leaf exits non-zero while the driver and a sibling survive, matching `docs/07-crosscutting.md:335`.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-08-05

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- T3 red with no retained gate log, now twice on this bundle (v1 and v2) and unreproducible both times (reviewer: driver suite 1,563 tests rc 0) — recurrence of the v1 §10 candidate; consider retaining failing gate output.
