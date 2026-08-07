# Build notes — issue 420 / bound-leaf-subprocess-memory

Target: `eduralph/pdca-harness` @ `main`, built in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`, tip `9c69256 pdca-integrate: issue_434` — the
run's folded integration base carrying #411 + #434, as the brief's Ordering note says).
All `path:line` citations below are against that tree **after** the patch unless marked
"pre-patch".

## What the change is

One decision at the single spawn choke point, plus the config surface that feeds it.

| File | Lines (post-patch) | What |
|---|---|---|
| `template/src/pdca_harness/leaves.py` | `218-306` | the bound: facility argv, property tiers, availability probe, `_memory_cap_prefix` |
| `template/src/pdca_harness/leaves.py` | `347-353` | the one wiring line in `_invoke` — `argv = _memory_cap_prefix(leaf, cfg) + argv` (`:353`) |
| `template/src/pdca_harness/leaves.py` | `337-341` | `_invoke` docstring: both branches, unset ⇒ byte-identical |
| `template/src/pdca_harness/config.py` | `38-63` | `_MEMORY_MAX_RE` + `memory_max_value()` — fail-safe validation of one bound |
| `template/src/pdca_harness/config.py` | `93-100` | `LeafConfig.memory_max` field (`:100`) + doc |
| `template/src/pdca_harness/config.py` | `354-365` | `Config.leaf_memory_max` field (`:365`) + doc, next to `sweep_worktrees` (its #297 peer) |
| `template/src/pdca_harness/config.py` | `574-578` | per-leaf parse inside `leaf()` |
| `template/src/pdca_harness/config.py` | `681-684`, `780` | `[driver]` parse + the `Config(...)` kwarg |
| `template/pdca.toml.jinja` | `185-203` | `[driver].leaf_memory_max`, commented, at the END of `[driver]` |
| `template/pdca.toml.jinja` | `387-393` | the `[leaves.*].memory_max` override, documented above the leaf tables |
| `docs/07-crosscutting.md` | `333-370` | new §"Bounding what a leaf may use" inside §Parallel lanes & housekeeping |
| `template/tests/test_leaf_memory_cap.py` | new, 233 lines | the criterion, all four cases + the override/opt-out/tier/`cfg=None` edges |

Pre-patch citations the brief asked me to mirror, and what I took from each:

- `leaves.py:246-285` (pre-patch) — the choke point. Both branches (`:259` interactive
  `subprocess.run`, `:276` headless `progress.run_with_heartbeat`) are covered by **one**
  prepend, placed before the branch so it cannot drift apart. `cfg: Config | None` is
  honoured: `_leaf_memory_bound` returns `""` for a `None` cfg (test
  `test_a_none_cfg_never_crashes_the_spawn`).
- `progress.py:66-74` (#368) — the default-off discipline, copied verbatim in spirit:
  "`timeout=None` (the default) is today's unbounded behaviour, unchanged". Here `""` is
  that default and the test pins it byte-for-byte, both branches.
- `config.py:313-320`/`625-631` (#297, pre-patch) — how a `[driver]` knob documents the
  resource, names the failure it prevents, and parses with a *fail-safe* fallback that
  **prints a note** instead of silently accepting nonsense. `memory_max_value` is that
  shape, with the fallback direction inverted deliberately (see below).
- `config.py:519-529` (`leaf()`, pre-patch) — a `[leaves.*]` key becoming a `LeafConfig`
  field, including the "explicit setting always wins" escape hatch — which is why
  `memory_max = "off"` exists per leaf.
- `preflight.py:27-56` (#213) — a declared-but-missing host resource is opt-in and a clean
  no-op when nothing is declared. That is exactly the facility-absent path.

## Why this facility (a transient systemd scope), and what I ruled out

`systemd-run --user --scope --quiet --collect --property MemoryMax=<bound> …`

- **`--scope`, not a service unit / `--pty`.** With `--scope`, systemd-run registers the
  transient unit over D-Bus and then **execs the command in its own process**: same pid,
  same stdio, same cwd, same env, same process group and controlling terminal. That is
  what keeps criterion 2 honest — the interactive leaves are REPLs the human types into.
  Verified on a real host, not asserted: inside a pty,
  `systemd-run --user --scope --quiet --collect --property MemoryMax=1G -- sh -c 'test -t 0
  && echo TTY-IN; test -t 1 && echo TTY-OUT; tty'` prints `TTY-IN` / `TTY-OUT` /
  `/dev/pts/2`. A `--pty` or service unit would have moved the leaf under `user@.service`
  with its own pty and broken both the REPL and the exit-status contract (`leaves.py:293-300`
  pre-patch, #138's "a failed leaf must never crash the cycle").
- **`setrlimit(RLIMIT_AS)` via `preexec_fn` — rejected.** It bounds *virtual address space*,
  not RSS: every tool that maps large files or reserves arenas (any JVM, Go runtime, rustc,
  node) dies on a limit that has nothing to do with the memory actually resident, so the cap
  would have to be set so high it stops bounding anything. It also does not reach
  grandchildren reliably as a *shared* budget (each process gets its own copy of the limit,
  so N children × cap is unbounded again), and `preexec_fn` is unsafe with the harness's
  threaded stream reader (`progress.py:150-162`). The cgroup route bounds the **tree**,
  which is the unit that actually blew up: a reviewer leaf's build children, not the leaf.
- **`ulimit -v` / wrapping in a shell — rejected** for the same reason, plus it would put a
  shell between the driver and the leaf, breaking the `argv[0]`-on-PATH doctor row
  (`doctor.py:455`) and the exit-status pass-through.
- **A host-level memory preflight — deliberately not built.** That is open issue #421 and
  the brief puts it out of scope; it answers a different question ("is there enough RAM to
  start?") than this one ("whose failure was it?").
- **Caching the probe result — rejected.** One `systemd-run … true` (~20 ms) per leaf spawn
  against a leaf that runs for minutes is noise, and a process-lifetime cache would make the
  availability answer stale exactly when a lane's environment changes underneath a long
  `flow`. No cache means no stale-state bug class at all.

**Property tiers** (`leaves.py:244-248`): richest first —
`MemoryMax` + `MemorySwapMax=0` + `ManagedOOMMemoryPressure=kill`, then without the oomd
property, then `MemoryMax` alone. The probe picks the first this host accepts. Without the
tiers a systemd older than v247 (`ManagedOOM*`) or one without swap accounting would fall
all the way to *unbounded*, which is the wrong trade: a hard `MemoryMax` is the part that
restores the invariant, the other two are refinements. `ManagedOOMMemoryPressure=kill` is
included because it targets the observed failure directly — it gives systemd-oomd a
scope-sized victim, so pressure kills the leaf's own cgroup instead of the terminal's.

**Why the probe runs the real argv** (`leaves.py:269-284`): `shutil.which("systemd-run")`
answers the wrong question. The binary can be present with no reachable user manager (a
container, a bare ssh session with no lingering user@.service), or present and reject a
property name. Since a wrapper that fails to exec would break **every leaf in the system**
rather than bound one, the only honest availability answer is "does this exact wrapper run
`true` here". It is `capture_output`'d and `timeout`-bounded (15 s), and every failure mode
— non-zero, timeout, `FileNotFoundError` — degrades to the no-op.

**Fail-safe direction, deliberately inverted from #297.** `sweep_worktrees` falls back to
"still sweeps" because the risk is a silently growing quota. Here an unparseable bound falls
back to **unbounded** (`config.py:40-63`), because a wrong cap kills a run exactly as dead
as no cap — and a guessed number would be a cap the operator never chose. It prints a note,
so the degradation is never silent (pinned by
`ConfigParsing.test_a_nonsense_bound_degrades_to_unbounded_with_a_note`).

## Cost of the alternative I did not take

The rejected shape that *looks* cheaper is "bound only the headless leaves" — the reviewer
leaves are the ones that caused the incident, and `progress.run_with_heartbeat` already has
a `timeout` parameter to hang a `memory_max` next to. Concretely it is the same size, not
smaller: `progress.py` would need the parameter (+1 line), the wrapper build (+8 lines) and
a pass-through at `leaves.py:276` (+1) — versus the 1 line at `leaves.py:353` this patch
spends to cover both branches. And it would leave the interactive leaves (planner, splitter,
sign-off, publisher, Act — `leaves.py:491, 641, 1254, 2773, 2802, 2849, 2941, 3006`)
unbounded while `pdca.toml`
claimed a bound: the invariant the brief names is stated *over the category* ("every
subprocess the driver spawns on a leaf's behalf, headless and interactive alike"), so a
half-covering fix does not restore it at any price.

## Verification

Runner: the project's own gate, `./engine/scripts/run-verify.sh` (pdca-pdca C4, the only
`gating = true` bundle row), with `PDCA_BUNDLE` / `PDCA_WORKTREE` set as the driver sets
them. Not hand-rolled.

```
== C4 green leg: bundle test(s) with the fix applied: template/tests/test_leaf_memory_cap.py
Ran 11 tests in 0.002s   OK
== C4 red leg: bundle test(s) with the production change reverted
Ran 11 tests in 0.003s   FAILED (failures=8)
C4 PASS: red without the fix, green with it
```

Also green, unchanged by this patch:

- `./engine/scripts/run-suite.sh` (T3, both suites) — `== T3: root suite OK, driver suite OK`;
- `./engine/scripts/run-docs-check.sh` (T2) — `lint_docs: OK`, `render_site: link audit OK`
  (this patch edits `docs/07-crosscutting.md`, which the target's own docs CI lints, and the
  target ships no formatter/linter config or commit hooks beyond that — checked: no
  `.pre-commit-config`, no `pyproject.toml`, no ruff/flake8 anywhere; CONTRIBUTING.md's
  only mechanical requirement is `git commit -s` (DCO), which the publish step owns).

### The three refutation questions

**(a) Genuine red?** Yes — and earned by assertions, not by a missing symbol. The C4 red leg
reverts `leaves.py` + `config.py` and keeps the test: 8 failures, `FAILED (failures=8)` with
**zero errors**. Sample:
`AssertionError: ['fake-vendor-cli', '-p', '--flag'] == ['fake-vendor-cli', '-p', '--flag'] :
headless leaf spawned unwrapped — the bound is not applied` and `AssertionError:
'fake-vendor-cli' != 'systemd-run'`. Two deliberate design choices make that possible on the
reverted tree, both from the brief's falsifiability note: the `Config` is built exactly as
`test_families.py:22-35` builds one and the bound is `setattr`'d afterwards (a constructor
kwarg would raise `TypeError` before any behaviour ran), and the stub installer
`_patch` tolerates a missing attribute (`getattr(obj, name, _MISSING)`) so patching the
not-yet-existing `_memory_cap_supported` does not raise `AttributeError`. Both are commented
in the test at the point of use.

**(b) Production path?** Yes. Every test calls the production `leaves._invoke` and the
production `config.Config.load`; nothing is re-implemented. The only stubs are at the
*boundary*: `leaves.subprocess.run` / `progress.run_with_heartbeat` record the argv instead
of executing it, and `leaves._memory_cap_supported` stands in for the host. The argv under
assertion is the one production assembled.

**(c) Fixture includes the fault?** Yes. The fault is "the spawned argv carries no bound", so
the fixture *is* the spawned argv — recorded from the real code path, not curated. Nothing
failing is excluded: both branches are exercised (headless and interactive, and the two no-op
cases are checked on both), the facility-absent case flips the real decision point rather than
skipping the leaf, and the interactive case additionally asserts no stdio kwarg appeared (a
wrapper that took the tty would pass the argv assertions and still be a regression).

The one thing the offline test cannot include is a real OOM kill — the brief's External
dependencies section forbids requiring systemd/root/a real OOM, so this is by design, not an
omission. I validated that leg by hand on this host instead (evidence, reproducible):

```
$ systemd-run --user --scope --quiet --collect --property MemoryMax=64M \
    --property MemorySwapMax=0 --property ManagedOOMMemoryPressure=kill \
    -- python3 -c "b=bytearray(); [b.extend(bytes(10**7)) for _ in range(40)]; print('ALLOCATED')"
Killed
rc=137          # the offender died as itself (SIGKILL inside its own scope)
parent shell alive   # the caller — the driver's analogue — survived to report it
```

`rc=137` is what reaches `_invoke` and raises `LeafError` (`leaves.py:383-388`), which
`_invoke_leaf_resilient` (`leaves.py:391-430`) records as that leaf's failure — the
invariant the brief asks to restore. No NEEDS-HUMAN dependency is declared: nothing outside
the brief's stated toolchain (python3 + git) was needed to build or to move the criterion
red→green.

## Residual notes for sign-off

- The knob is off in the shipped `pdca.toml.jinja` (commented out). Rendering an instance
  changes no behaviour until someone sets a number.
- On a host that *does* support the bound, every leaf spawn now pays one extra ~20 ms
  `systemd-run … true` probe. Only when a bound is configured — with the default `""` the
  probe never runs.
- `_invoke_leaf_resilient` treats a non-zero exit that produced no stream output as
  transient and retries it. An OOM-killed leaf that had already produced output (the normal
  case — the kill happens deep into a build) is classified substantive and not retried; a
  leaf killed before any output would be retried up to the attempt budget, exactly as any
  other early death is today. Unchanged by this patch, noted because it is adjacent.
