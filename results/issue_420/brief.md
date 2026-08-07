# Brief — issue 420 / bound-leaf-subprocess-memory

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** bound-leaf-subprocess-memory
- **Defect:** Leaf subprocesses are spawned with **no resource bound of any kind**, so one
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

- **Success criterion:** On `eduralph/pdca-harness` @ `main`, a new test
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

- **Falsifiability:** RED is produced on the environment Do is pointed at — this instance's
  C4 gate (`engine/scripts/run-verify.sh`, pdca-pdca) on the reconstructed `$PDCA_WORKTREE`.
  It reverts the patch's production hunks and keeps the test (`:72-81`), then runs
  `cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_memory_cap`
  (`:55-65`). With `leaves.py` / `config.py` reverted, the recorded argv is the unwrapped
  argv → assertions (1) and (2) fail → non-zero → red. Green with the patch.

  **The red must be earned by an ASSERTION, not by an import/attribute error.** Under
  `unittest` an `AttributeError`/`TypeError` also exits non-zero and would *look* red, but
  it proves the symbol is missing rather than that the behaviour is absent — the exact
  "no-evidence scored as evidence" shape #434 is about. Concretely: the test must **not**
  pass the new key as a `Config(...)` constructor kwarg (that raises `TypeError` on the
  reverted tree before any behaviour is exercised); it must build the `Config` as the
  existing suites do and then `setattr` the bound onto it, so the reverted tree runs the
  real spawn path and simply fails the argv comparison. Same for the per-leaf key.

  Gate-evaluability confirmed against `pdca.toml` `[[gates.checks]]`: `C4-verify` is the
  only `gating = true` bundle row; the named module is stdlib-only, is not behind any
  feature/env flag (so it cannot compile to a vacuous `0 tests … ok`), and every symbol it
  touches (`leaves._invoke`, `config.Config`, `LeafConfig`) is importable from
  `template/src`. **Base:** the scheduler places this bundle in **wave 1** (verified — see
  Ordering note), so there is no `Onto branch` / `$PDCA_BASE`, but the driver **does** export
  `$PDCA_VERIFY_BASE` = the run's folded integration branch, and the gate must verify against
  it rather than `origin/main` — the precedence `$PDCA_BASE > $PDCA_VERIFY_BASE >
  $PDCA_BRIEF_BASE` published at `template/engine/scripts/run-verify.sh:12-34`. This
  instance's gate honours it by construction: it needs no base handling of its own because
  the driver reconstructs base + patch in `$PDCA_WORKTREE` before any gate runs
  (`engine/scripts/run-verify.sh:4-10`). The folded base carries #411's and #434's diffs;
  the only file this bundle shares with either is `docs/07-crosscutting.md` (non-behavioral
  for C4, and Do generates its patch against the folded tree), so the patch applies cleanly.

- **Invariant to restore:** *A leaf runs inside a resource bound the driver owns — a leaf
  that exceeds its budget fails as itself, and the failure is attributable to that leaf.*
  Stated over the category: every subprocess the driver spawns on a leaf's behalf, headless
  and interactive alike, and every resource the harness already bounds elsewhere — never
  "the reviewer leaf". A leaf whose footprint is unbounded is not an isolated failure
  domain, and its death takes the run's siblings and the driver with it. Source (internal,
  Tier C — this repo's own written rules; `docs/principles.md` §6 mapping is empty for this
  instance, so this is reference-layer, not a gated category):
  - `template/src/pdca_harness/progress.py:66-74` (#368) — the harness's stated rule that a
    per-invocation resource is bounded by the driver and its expiry is "a distinguishable
    'the oracle did not answer' outcome, never a verdict the child produced";
  - `template/src/pdca_harness/config.py:313-320` (#297) — the same rule for disk: "left
    unbounded, the footprint … has exhausted disk quotas and false-redded gating gates
    mid-run";
  - `template/src/pdca_harness/leaves.py:298-314` (#138) — a failed leaf "must never crash
    the cycle"; today an OOM does exactly that.

- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** (none)
- **Conflicts with:** 411
- **Ordering note:** No dependency in either direction — #420 and #411 are independent
  fixes. They are declared conflicting because both land user-facing driver documentation in
  the **same file**, `docs/07-crosscutting.md`: this bundle in §Parallel lanes &
  housekeeping (`:300-332`, `:359-380`), #411 in §Waves in execution (`:333-358`). Adjacent
  sections in one file are exactly the shared-resource case the wave scheduler exists to
  separate, so they must not be built blind on the same base. Which of the two goes first is
  the scheduler's call, not the brief's; verified by running the real scheduler over the
  three bundles (`waves.compute_waves`): **wave 0 = {411, 434}, wave 1 = {420}** — this
  bundle builds on the folded result of the other two. Code files do not overlap at all — this bundle owns
  `template/src/pdca_harness/{leaves,config}.py` + `template/pdca.toml.jinja`; #411 owns
  `template/src/pdca_harness/merge.py` + `template/tests/test_merge.py`; #434 owns
  `template/engine/**`.
- **Surfaces:** data
- **Difficulty:** high — the change is centralized at one spawn site but its effect reaches
  **every** leaf invocation in the system (planner, sizer, splitter, builder, reviewer,
  advisory, sign-off, publisher, Act — `leaves.py:313, 388, 538, 1068, 1151, 1379, 2670,
  2699, 2746, 2838, 2903`), across two spawn shapes (headless with a heartbeat/stream
  reader; interactive with an inherited tty and a seed positional), and it adds a new public
  `pdca.toml` surface that has to be parsed, defaulted fail-safe, documented and rendered.
  A diff-reviewer must hold `leaves.py`, `config.py`, `pdca.toml.jinja` and the docs in view
  together, and reason about the case where the wrapper misbehaves — which breaks the whole
  harness, not one bundle. Rated up deliberately.
- **Scope:** Give the driver an **optional, configured memory bound applied to every leaf
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

- **Repro instruction:** On a clean worktree of `origin/main` in `../pdca-harness`:
  1. `git -C ../pdca-harness grep -n "MemoryMax\|systemd-run\|setrlimit\|ulimit\|cgroup\|OOMPolicy" -- template/src template/agents template/engine template/scripts`
     → no output. No leaf spawn carries any memory bound.
  2. `git -C ../pdca-harness show origin/main:template/src/pdca_harness/leaves.py | sed -n '246,286p'`
     → the whole spawn path: argv is assembled and handed straight to `subprocess.run`
     (`:259`, interactive) or `progress.run_with_heartbeat` (`:276`, headless), with no
     bound and no wrapper hook.
  3. `git -C ../pdca-harness show origin/main:template/src/pdca_harness/progress.py | sed -n '35,50p;120,135p'`
     → `run_with_heartbeat` takes `timeout` (a wall-clock bound, #368) and `Popen`s with
     `start_new_session`; there is no memory analogue.
  4. The live failure, for the record (not reproducible on demand and not required to be):
     two concurrent reviewer leaves building cold trees drove `user@1000.service` past the
     oomd pressure threshold and the whole `ptyxis-spawn-….scope` was killed. The
     *criterion* above is what Do must make go red→green; this step is context.
- **External dependencies:** none
  (the four criterion cases are all exercised with the spawn
  stubbed (record the argv; stub the facility-present and facility-absent host by patching
  the availability probe), so nothing beyond the base toolchain — python3 + git — is needed
  to build or to move the criterion red→green. Do MUST NOT write a test that requires a real
  systemd/cgroup host, a real OOM, or root: that would make the criterion unrunnable on CI
  and unfalsifiable here. If Do believes an unlisted dependency is genuinely required, it
  must declare it rather than work around it.)
- **Test file:** `template/tests/test_leaf_memory_cap.py` (new). A new file, not an
  append: no existing suite owns leaf-spawn resource bounds (`test_leaf_resilience.py` owns
  retry/`LeafError`, `test_progress.py` owns the heartbeat/stream reader, `test_preflight.py`
  owns #213). This instance's C4 gate accepts either shape — it reverts production hunks and
  keeps every test (`engine/scripts/run-verify.sh:72-81`) — so this is a cohesion choice,
  not a gate constraint. The module is run as `tests.test_leaf_memory_cap` from `template/`,
  so the filename must match exactly.
- **Citations expected:** Do must cite path:line on `origin/main` for every change.
  Peer callsites to mirror (Do MAY open these):
  - **`template/src/pdca_harness/leaves.py:246-285` (`_invoke`)** — the single spawn choke
    point. Both branches (`:259` interactive, `:276` headless) must be covered by the same
    decision, or the bound is a lie for half the leaves. Note `cfg` is `Config | None` here:
    a `None` cfg must degrade to no wrapping, never crash.
  - **`template/src/pdca_harness/progress.py:66-74` + `:127-130`** — **the peer to mirror
    for the bound itself** (#368): an optional per-invocation resource bound whose unset
    default is "today's unbounded behaviour, unchanged", whose child is started in its own
    session so a *grandchild* is reaped too, and whose expiry is reported as a
    distinguishable outcome rather than a verdict. Mirror that reasoning and that
    default-off discipline.
  - **`template/src/pdca_harness/config.py:313-320` (field + doc) and `:625-631` (parse)** —
    **the peer to mirror for the `[driver]` knob**: how `sweep_worktrees` documents the
    resource it bounds, states the failure it prevents, and parses with a *fail-safe*
    fallback that prints a note rather than accepting nonsense silently.
  - **`template/src/pdca_harness/config.py:519-529` (`leaf()`)** — **the peer to mirror for
    the per-leaf override key**: how a `[leaves.*]` key becomes a `LeafConfig` field
    (`config.py:45-67`), including the "explicit argv always wins" escape-hatch convention.
  - `template/src/pdca_harness/preflight.py:27-56` (#213) — how the harness treats a
    declared-but-missing host resource (opt-in, resource-agnostic, a clean no-op when
    nothing is declared). The facility-absent case should feel like this, not like an error.
  - `template/pdca.toml.jinja` — the rendered config must carry the new keys as commented
    documentation in the same voice as the existing `[driver]` knobs.
- **Prior-art check (triage cycles):** Searched by affected file path and by keyword.
  `git -C ../pdca-harness log --oneline origin/main -n 15 -- template/src/pdca_harness/leaves.py`
  → 15 commits, none about resource bounds (the nearest are `900d638` interactive exit
  contract and `a5a4d25`/`63ccdf4` Check recovery). Tracker
  (`gh search issues --repo eduralph/pdca-harness "memory" / "MemoryMax" / "oom"
  / "systemd-run"`): **#421 open** — *doctor/install: no host memory or swap preflight,
  though free disk has one (#297)* — is the adjacent, complementary issue (a host preflight
  in `doctor`/`preflight`, not a per-leaf cap); it is **not** in this batch and shares no
  file with this bundle, so no ordering field is set for it, but the two should not be
  merged into one change. **#422 open** (reviewer scratch is per-run and disposable) and
  **#419** (writable reviewer clone) are the footprint-multiplying direction this cap is
  meant to make safe — related, not duplicative. Closed and complementary: #297 (disk
  sweep), #368 (gate timeout), #213 (lane preflight), #244 (keep-awake), #379 (reviewer
  scratch discipline). No open PRs on the repo (`gh pr list` → empty). Not previously
  proposed and rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the issues surfaced by the advisory review (C3 FAIL / T5 FAIL), confirmed against the target tree at sign-off. The design is right — keep it. The defect is a documented knob that silently does nothing. What to change next: 1. `memory_max` is honoured only for the NAMED leaf tables (config.py's LeafConfig constructor). It is silently dropped for the array-form leaf tables: - `[[leaves.advisory]]` — spec dict at leaves.py:2243 - `[[leaves.plan_advisory]]` — spec dict at leaves.py:2432 - `[[leaves.builder_escalation]]` / `[[leaves.builder_variant]]` — `_leaf_from_spec` at leaves.py:757 The first two must read `memory_max` from the spec (validated through `config.memory_max_value`, as the named path does); `_leaf_from_spec` must INHERIT it from `default` the way it already inherits `model`, so a variant does not lose its base leaf's override or its `"off"` opt-out. 2. This is what makes it a shipping defect rather than a nit: the patch's own public docs claim the broader behaviour — `docs/07-crosscutting.md` ("Any `[leaves.*]` table takes `memory_max`") and `template/pdca.toml.jinja:385` ("Any leaf table below also takes `memory_max`"). Either the code matches that claim (preferred) or the docs are narrowed to the named tables. Do not ship the mismatch. 3. Extend `template/tests/test_leaf_memory_cap.py` to pin the fix: a per-leaf override AND a `"off"` opt-out on at least one array-form leaf, plus a variant derived from a base leaf that carries an override. The current 11 tests never exercise those constructors, which is why the gap survived a green C4. Not the reason for iterating — do not regress these: - The driver-level cap ALREADY reaches every leaf, including advisory ones (cfg is passed through to `_invoke`), so the containment that would have prevented the observed incident is in place. Only the per-leaf override/opt-out is lost. - The four brief criteria are met and independently replayed red->green. Keep the default-off byte-identical argv, the absent-facility no-op, and the interactive TTY inheritance exactly as they are. Open §6 items carried into the next round (not cleared, not blocking this iterate): - C5: the capability probe runs per bounded spawn and is never cached — a transient systemd hiccup silently unbounds that leaf. Worth resolving the facility decision once per run while the file is open. - Validation: coverage is stubbed argv only; no live bounded leaf, real scope or real OOM was exercised. Operational containment is still unproven by test. - T3: the recorded red is NOT attributable to this patch — the driver suite was re-run three times at sign-off in the patched worktree, green each time (1552 tests, rc 0), and the builder recorded it green too. No gate log was retained to attribute it.
- Failing gate: T3 runtime: render/update-compat + offline driver suites (advisory) — == T3: root suite OK, driver suite FAILED (rc 1)
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
