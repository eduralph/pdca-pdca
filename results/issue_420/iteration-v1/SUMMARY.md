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

Review of issue #420: add an optional per-leaf subprocess memory bound without changing unbounded or unsupported-host spawn behavior.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is decidable: both spawn modes, default-off behavior, unsupported-host fallback, and driver/per-leaf configuration are explicitly observable at `template/tests/test_leaf_memory_cap.py:113`. |
| C2 Reproduction (red pre-fix) | PASS | On a clean target `HEAD` with only the new test retained, 11 tests ran and 8 failed by assertions (rc 1), including the unwrapped headless argv at `template/tests/test_leaf_memory_cap.py:117`; this is behavioral red rather than an import/attribute error. |
| C3 Change | FAIL | The promised per-leaf override must work for every leaf kind, but advisory and plan-advisory constructors omit `memory_max` at `template/src/pdca_harness/leaves.py:2346` and `template/src/pdca_harness/leaves.py:2535`, and variant/escalation reconstruction drops the inherited override at `template/src/pdca_harness/leaves.py:860`; those leaves silently fall back to the driver cap. |
| C4 Verification (red→green) | PASS | Independent retained-test replay produced assertion red on clean `HEAD` (8 failures, rc 1) and green on the patched target (11 tests, rc 0), covering the spawn contract beginning at `template/tests/test_leaf_memory_cap.py:113`. |
| C5 Causal adequacy | NEEDS-HUMAN | Decide whether the per-spawn capability probe is the intended root-cause treatment or should be replaced by a cached/lazy facility decision — it launches a transient scope for every bounded leaf at `template/src/pdca_harness/leaves.py:269`, so repeated load-time probing adds failure surface and overhead before each real spawn. |
| T1 Structure | PASS | The containment decision is centralized before the shared interactive/headless branch at `template/src/pdca_harness/leaves.py:353`, preserving one spawn choke point; the configuration propagation defect is separately called out in C3. |
| T2 Shape | NEEDS-HUMAN | Decide whether to accept the docs shape without reproducing its named oracle — `engine/scripts/run-docs-check.sh` is absent in the target, although `git diff --check` passed and the public template documents the knob at `template/pdca.toml.jinja:185`. |
| T3 Runtime | NEEDS-HUMAN | Resolve the oracle discrepancy before sign-off — the recorded `run-suite.sh` row is red, that script is absent here, while the directly runnable driver suite passed at `template/Makefile:74`; the exact failing runtime case cannot be attributed to this patch from available evidence. |
| T4 Contribution | NEEDS-HUMAN | Decide whether the contribution opener and tracker linkage meet project policy — the gate reports pass, but its PR-body artifacts are not among the reviewer inputs and therefore cannot be independently checked against the affected paths. |
| T5 Judgment | FAIL | The public claim that any leaf table may override the cap is not yet safe to ship because valid advisory and variant configurations lose that override at `template/src/pdca_harness/leaves.py:2346`; merged-history and closed issue/PR searches by affected path/keywords found no prior implementation to defer to. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether stubbed argv coverage is sufficient evidence that a real user scope preserves the interactive TTY and confines descendant memory — no live bounded leaf/OOM was exercised, so operational containment remains a sign-off judgment despite the offline red→green. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C5 Causal adequacy — Decide whether the per-spawn capability probe is the intended root-cause treatment or should be replaced by a cached/lazy facility decision — it launches a transient scope for every bounded leaf at `template/src/pdca_harness/leaves.py:269`, so repeated load-time probing adds failure surface and overhead before each real spawn.
- [ ] T2 Shape — Decide whether to accept the docs shape without reproducing its named oracle — `engine/scripts/run-docs-check.sh` is absent in the target, although `git diff --check` passed and the public template documents the knob at `template/pdca.toml.jinja:185`.
- [ ] T3 Runtime — Resolve the oracle discrepancy before sign-off — the recorded `run-suite.sh` row is red, that script is absent here, while the directly runnable driver suite passed at `template/Makefile:74`; the exact failing runtime case cannot be attributed to this patch from available evidence.
- [ ] T4 Contribution — Decide whether the contribution opener and tracker linkage meet project policy — the gate reports pass, but its PR-body artifacts are not among the reviewer inputs and therefore cannot be independently checked against the affected paths.
- [ ] Validation — fitness-to-purpose — Decide whether stubbed argv coverage is sufficient evidence that a real user scope preserves the interactive TTY and confines descendant memory — no live bounded leaf/OOM was exercised, so operational containment remains a sign-off judgment despite the offline red→green.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the issues surfaced by the advisory review (C3 FAIL / T5 FAIL), confirmed against the target tree at sign-off. The design is right — keep it. The defect is a documented knob that silently does nothing. What to change next: 1. `memory_max` is honoured only for the NAMED leaf tables (config.py's LeafConfig constructor). It is silently dropped for the array-form leaf tables: - `[[leaves.advisory]]` — spec dict at leaves.py:2243 - `[[leaves.plan_advisory]]` — spec dict at leaves.py:2432 - `[[leaves.builder_escalation]]` / `[[leaves.builder_variant]]` — `_leaf_from_spec` at leaves.py:757 The first two must read `memory_max` from the spec (validated through `config.memory_max_value`, as the named path does); `_leaf_from_spec` must INHERIT it from `default` the way it already inherits `model`, so a variant does not lose its base leaf's override or its `"off"` opt-out. 2. This is what makes it a shipping defect rather than a nit: the patch's own public docs claim the broader behaviour — `docs/07-crosscutting.md` ("Any `[leaves.*]` table takes `memory_max`") and `template/pdca.toml.jinja:385` ("Any leaf table below also takes `memory_max`"). Either the code matches that claim (preferred) or the docs are narrowed to the named tables. Do not ship the mismatch. 3. Extend `template/tests/test_leaf_memory_cap.py` to pin the fix: a per-leaf override AND a `"off"` opt-out on at least one array-form leaf, plus a variant derived from a base leaf that carries an override. The current 11 tests never exercise those constructors, which is why the gap survived a green C4. Not the reason for iterating — do not regress these: - The driver-level cap ALREADY reaches every leaf, including advisory ones (cfg is passed through to `_invoke`), so the containment that would have prevented the observed incident is in place. Only the per-leaf override/opt-out is lost. - The four brief criteria are met and independently replayed red->green. Keep the default-off byte-identical argv, the absent-facility no-op, and the interactive TTY inheritance exactly as they are. Open §6 items carried into the next round (not cleared, not blocking this iterate): - C5: the capability probe runs per bounded spawn and is never cached — a transient systemd hiccup silently unbounds that leaf. Worth resolving the facility decision once per run while the file is open. - Validation: coverage is stubbed argv only; no live bounded leaf, real scope or real OOM was exercised. Operational containment is still unproven by test. - T3: the recorded red is NOT attributable to this patch — the driver suite was re-run three times at sign-off in the patched worktree, green each time (1552 tests, rc 0), and the builder recorded it green too. No gate log was retained to attribute it.
- By / date: Eduard Ralph / 2026-08-05

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- T3 red with no retained gate log: only the last line survives, so an unreproducible suite failure (green on 3 re-runs at sign-off) cost sign-off time and could not be attributed — consider keeping failing gate output.
