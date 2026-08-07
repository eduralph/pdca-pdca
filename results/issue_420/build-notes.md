# Build notes — issue 420 / bound-leaf-subprocess-memory (iteration 2)

Withheld from the reviewer. Line numbers are **post-patch**, in `$PDCA_WORKTREE`
(`/home/eddie/pdca/pdca-harness.pdca-wt`, the folded base `9c69256` = origin/main + #411 + #434).

## What this iteration changes, and why

Iteration 1's design was accepted at sign-off ("The design is right — keep it"); it was
rejected for a **documented knob that silently did nothing** on part of its documented
surface. Everything below is scoped to that rejection plus the one §6 item the sign-off
asked me to resolve "while the file is open". The four brief criteria, the default-off
byte-identical argv, the absent-facility no-op and the interactive TTY inheritance are
**unchanged** from v1 and re-proved red→green.

### 1. `memory_max` now reaches the ARRAY-form leaf tables (the rejection)

`Config.leaf()` (`config.py:564-579`) builds the six NAMED `[leaves.*]` tables, and v1
added `memory_max` there. The array-form tables are built from raw spec dicts inside
`leaves.py`, so the key was dropped on the floor for them:

- `[[leaves.advisory]]` — was `LeafConfig(mode=…, family=…, argv=…, agent=…, model=…,
  effort=…)` at the old `leaves.py:2243`;
- `[[leaves.plan_advisory]]` — the identical constructor at the old `leaves.py:2432`;
- `[[leaves.builder_variant]]` / `[[leaves.builder_escalation]]` / `[[leaves.sizer_escalation]]`
  — `_leaf_from_spec` (`leaves.py:874-897`).

Fix, two hunks:

- **`_advisory_leaf(spec, table, leaf_id)`** — `leaves.py:2256-2272`, one constructor now
  used by both advisory paths (`leaves.py:2390`, `leaves.py:2577`). It validates through
  the *same* `config.memory_max_value` as the named path (`config.py:45-61`), so an
  unparseable `[[leaves.advisory]] memory_max` degrades to "inherit" with a note instead
  of becoming a systemd property that would make every advisory spawn fail to start.
  I collapsed the two duplicated constructors into one deliberately rather than adding the
  kwarg twice: the *class* of bug is "a per-leaf key added to `Config.leaf()` silently
  misses the spec-dict tables", and two identical constructors are how it recurs. Cost of
  the collapse: +17/−6 lines, one new private function, no behaviour change for any
  existing key (the six kwargs are byte-identical to what both sites passed).
- **`_leaf_from_spec`** — `leaves.py:893-895`: the spec's own `memory_max` wins, else it
  **inherits** `default.memory_max`, the way `model` is already inherited
  (`leaves.py:889-892`). A variant/escalation is the same appetite as the leaf it varies,
  so silently losing the base leaf's cap would leave the *hungriest* builder the one
  unbounded — and silently losing an `"off"` would cap a leaf its owner opted out.

`doctor.py:271` also constructs a `LeafConfig` from specs; deliberately untouched — it
builds a throwaway leaf to check a CLI's *presence*, never spawns work.

### 2. The docs claim and the code now agree

The rejection's point 2: the patch's own docs claimed the broader behaviour. I took the
preferred branch (make the code match), and then made the claim *specific* rather than
leaving "any `[leaves.*]` table" to be read charitably:

- `docs/07-crosscutting.md:371-380` — names the array-form tables and states the
  inherit rule for variants/escalations;
- `template/pdca.toml.jinja:388-398` — same, in the rendered config's voice.

### 3. §6 C5 carry-forward: the facility is decided once per run, not once per spawn

`_MEMORY_CAP_DECISION` (`leaves.py:253-260`) memoises `bound → wrapper argv`;
`_memory_cap_prefix` (`leaves.py:295-309`) consults it and `_resolve_memory_cap`
(`leaves.py:311-323`) does the probing. Two reasons, and the second is the load-bearing
one: a per-spawn probe pays a `systemd-run … true` subprocess per leaf, and a transient
systemd hiccup would unbound *one* leaf of a run while its siblings stayed capped — a
half-bounded run is precisely the unattributable state this issue exists to remove. The
"this host cannot enforce it" note is now printed once per run rather than once per leaf.
Pinned by `test_the_host_facility_is_probed_once_per_run_not_once_per_leaf`.

Trade-off recorded honestly: caching the *negative* means a first-probe hiccup unbounds the
whole run rather than one leaf. I chose it anyway — one decision per run, stated once, is
what makes the outcome attributable; a run that is bounded for half its leaves is not
explainable from the logs, which is the whole failure mode of the original incident.

### 4. Test-module hygiene (T3 defensiveness, not a correctness change)

v1 stubbed the spawn with `setattr(leaves.subprocess, "run", …)` — `leaves.subprocess` *is*
the stdlib module, so that rebinds `subprocess.run` for the **whole interpreter** while the
test runs, inside a 1563-test `unittest discover`. Replaced by `StubSubprocess`
(`template/tests/test_leaf_memory_cap.py:51-65`), which swaps the module *reference inside
`leaves`* and proxies every other attribute to the real module. Strictly narrower; no
production code changed for it.

## Red→green, through the project's own runner

- **C4 gate** (`./engine/scripts/run-verify.sh`, the configured `C4-verify` cmd, run with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` exactly as the driver runs it):
  `C4 PASS: red without the fix, green with it` — green leg 22 tests OK; red leg
  `FAILED (failures=15)`, **15 failures, 0 errors**.
- **T3** (`./engine/scripts/run-suite.sh`): `== T3: root suite OK, driver suite OK`, rc 0.
- **T2** (`./engine/scripts/run-docs-check.sh`): `lint_docs: OK`, `render_site: link audit OK`, rc 0.

The red is **assertion-earned**, which the brief made a hard requirement: with the
production hunks reverted the module still imports, still builds its `Config`, still runs
the real spawn path, and fails on the argv comparison (`AssertionError: ['fake-vendor-cli',
'-p', '--flag'] == [...] : leaf spawned unwrapped`). No `TypeError`/`AttributeError`
anywhere in the red leg — the new bound is `setattr`'d onto `Config`/`LeafConfig`, never
passed as a constructor kwarg, and `_patch` tolerates a symbol that does not exist yet.

Red-leg failures include the new array-form tests — `advisory_leaf_honours_its_own_memory_max`,
`advisory_leaf_without_a_key_still_inherits_the_driver_bound`,
`an_unparseable_advisory_bound_is_validated_not_passed_through`,
`plan_advisory_leaf_honours_its_own_memory_max`,
`a_builder_variant_inherits_the_base_leafs_bound`,
`a_builder_variants_own_memory_max_wins`,
`a_builder_escalation_inherits_the_base_leafs_bound` — i.e. the gap that survived v1's
green C4 is now itself red pre-fix. The two `"off"` opt-out tests pass on the reverted tree
(unwrapped is unwrapped either way); they are regression guards, and I left them in
knowingly — the override tests carry the red for that surface.

## Forced self-refutation

**(a) Genuine red?** Yes — actually reverted, not reasoned about:
`git apply -R --exclude='tests/*' --exclude='template/tests/*' patch.diff` then
`cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_memory_cap` →
`Ran 22 tests … FAILED (failures=15)`, 0 errors. Re-applied and green (22/22). The C4 gate
does the same revert/restore itself and reports PASS.

**(b) Production path?** Yes. The tests drive `leaves._invoke` (`leaves.py:326-406`),
`leaves.run_advisory_leaves` (`leaves.py:2370`), `leaves.run_plan_advisory`
(`leaves.py:2829`), `leaves.select_builder` (`leaves.py:1318`) and `Config.load`
(`config.py:683-684`) — the actual functions the driver calls. Nothing is re-implemented in
the test module: the only stubs are the *spawn* itself (`progress.run_with_heartbeat` /
`leaves.subprocess.run`, so nothing executes) and the *host probe*
(`leaves._memory_cap_supported`, so the result is the same with or without systemd). The
argv asserted on is the argv the production code assembled and handed to the spawn.

**(c) Fixture includes the fault?** Yes. The failing element here is the leaf spawn itself,
and it is present in every case: the advisory tests go through the real
`run_advisory_leaves` → `_select_advisory` → `_advisory_leaf` → `_run_advisory_sandboxed` →
`_invoke_leaf_resilient` → `_invoke` chain with the real spec dicts (nothing hand-built
into a `LeafConfig`); the variant tests go through the real `select_builder` →
`_leaf_from_spec`. The facility-absent case is exercised by making the probe answer "no",
not by removing the bound. Nothing is curated out — the four criteria are asserted on both
spawn branches, including the interactive one that would otherwise be the half left unbound.

## Live operational validation (host-dependent — NOT in the shipped test)

The brief forbids a test needing real systemd/cgroups/root, so the automated coverage is
stubbed argv. I ran the real thing by hand on this host so the human isn't asked to take
containment on faith (a §6 carry-forward item from v1):

```
$ systemd-run --user --scope --quiet --collect --property MemoryMax=64M \
    --property MemorySwapMax=0 --property ManagedOOMMemoryPressure=kill \
    -- python3 -c "b=bytearray(400*1024*1024); print('allocated', len(b))"
Killed                                       # rc 137 — the child, not the session
$ python3 -c "b=bytearray(400*1024*1024); print('unbounded allocated', len(b))"
unbounded allocated 419430400                # rc 0 — same allocation, no bound
```

…and end-to-end through the production leaf path, `leaf_memory_max = "64M"`:

```
LIVE bounded leaf   -> LeafError rc = -9     # killed as itself; _invoke_leaf_resilient
LIVE in-budget leaf -> None                  # 8 MiB allocation: runs normally
driver still alive; wrapper argv = ['systemd-run', '--user', '--scope', …]
```

That is the invariant the brief names: the offender dies **inside its own scope**, the
failure arrives as *that leaf's* `LeafError` (`leaves.py:408-447`, #138), and the driver —
the thing that previously vanished with the whole cgroup — survives. Anyone can reproduce
it with the two commands above on a systemd host; on a host without one, the same run is a
documented no-op with a note on stderr.

Known, unchanged behaviour worth naming: a leaf SIGKILLed with **no** output on a
stream-capable family is classified transient by `_invoke_leaf_resilient` and retried
(bounded, then recorded as that leaf's failure). Re-classifying an OOM kill as substantive
is a retry-policy question, not this bundle's — the brief's requirement ("surfaces as that
leaf's non-zero exit through the existing LeafError path") holds either way.

## The v1 failing gate (T3), investigated

The iterate was triggered by `T3-suite`: `root suite OK, driver suite FAILED (rc 1)`,
which sign-off could not attribute (three re-runs green, no gate log retained). I could
not reproduce it either — with v1's patch applied verbatim I ran the driver suite 3× (rc 0,
1552 tests each) before touching anything, and with this iteration's patch 3× sequential
plus 2× **concurrent** (the `lanes = 2` shape) — all rc 0, 1563 tests. Plus the full
`run-suite.sh` twice, rc 0.

So I have no evidence it was this patch, and I did not chase it blind. What I did do is
remove the one real global-state hazard the patch introduced into a 1563-test process (the
stdlib `subprocess.run` rebind, §4 above), since that is the shape of thing that produces
an unreproducible cross-module failure. Standing suspicion for the human, unproven:
`tests/test_suite_output_hygiene.py:39-42` shells out with `timeout=300` and the failure
happened under two concurrent lanes on a memory-pressured host — a contention-flake
candidate that has nothing to do with this bundle.

## Alternatives considered and rejected

- **`resource.setrlimit(RLIMIT_AS)` in a `preexec_fn`** — no new process, no systemd
  dependency, ~8 lines. Rejected: `RLIMIT_AS` bounds *address space*, not resident memory,
  so a JIT/mmap-heavy vendor CLI dies at a number unrelated to the pressure that killed the
  run, and the kernel's answer is `MemoryError` inside the child rather than an attributable
  kill of the whole process tree. It also cannot reap a *grandchild* (the leaf's `cargo`/
  `node`), which is exactly what wrote the 69 GB. `preexec_fn` is additionally unsafe with
  threads — `progress.run_with_heartbeat` runs one.
- **`systemd-run --user` as a transient *service* (no `--scope`)** — better isolation, but
  it detaches the child from the session: the interactive leaves lose the terminal they are
  REPLs in, and stdout/stdin plumbing goes through the journal. Criterion (2) exists to
  forbid exactly that.
- **A cgroup written by hand under `/sys/fs/cgroup/…`** — no `systemd-run` dependency, but
  it needs delegation, cleanup on crash, and its own OOM plumbing; ~120 lines of
  host-specific code the harness would own forever, versus 5 argv tokens.
- **Bounding only the headless leaves** (the reviewer is the observed offender) — smaller
  diff by ~6 lines. Rejected on the brief's stated invariant: a bound covering half the
  spawn sites is a lie for the other half, and the invariant is over the *category*, not
  over the leaf that happened to fail.
- **Narrowing the docs to the named tables** (the rejection's non-preferred branch) —
  ~6 lines deleted instead of the ~30 added here. Rejected: the per-leaf override is most
  valuable exactly where it was missing (the advisory pool is what a run fans out
  concurrently), so narrowing the doc would document the accident rather than fix it.

## Commit-readiness

The target repo ships no formatter/linter hooks (no `.pre-commit-config.yaml`, no ruff/
black/flake8 config; CI is `docs-check` + `render-check` + `require-linked-issue`, and
`AGENTS.md:28` names the offline suite as the check). Both docs workflows are covered
locally by `run-docs-check.sh` (green), the render workflow by T3's root suite (green).
No added line exceeds 96 columns, matching the surrounding style. Commits need `-s` (DCO)
and a conventional prefix — a matter for publish, not the patch.

## Files

- `patch.diff` — 5 files, +690/−7 (docs 47, `pdca.toml.jinja` 31, `config.py` 54,
  `leaves.py` 157, new test 408).
- Test: `template/tests/test_leaf_memory_cap.py` (new, 22 tests, stdlib-only, offline).
