# Cap how much memory a leaf may use, so one leaf can't kill the whole run

## Summary
**User impact:** A single leaf could take down everything you had running. Leaves
are model subprocesses doing real work in real checkouts, and with lanes several
run at once — but nothing limited how much memory any of them could take. On one
two-lane run, two reviewer leaves building cold trees pushed the session past the
kernel's memory-pressure threshold; the OOM killer took the whole terminal session
— the driver, both lanes, every bundle in flight — and left nothing in any log to
say why. From the outside the run just vanished mid-flight, and hours of work had
to be redone.

This adds an opt-in setting, `[driver].leaf_memory_max`, that caps every leaf the
driver spawns, so a leaf that overruns is killed *as itself*: it exits non-zero,
its failure is recorded against that leaf, and the run survives to report it.
Reported in [#420](https://github.com/eduralph/pdca-harness/issues/420).

## What to look at
The crux is one line in the single place every leaf is spawned from: when a bound
is configured, the leaf's command line is wrapped in a per-leaf systemd scope that
carries the cap; when it isn't, the command line is untouched. Two deliberate
non-behaviours are worth checking as carefully as the feature:

- **Unset means unset.** With no bound configured (the default) the spawn is
  byte-for-byte what it was before this setting existed — no wrapper, no extra
  process. There is no portable number to default to, and a cap set too low is its
  own way to kill a run.
- **A host that can't enforce it degrades, it doesn't fail.** Where there is no
  usable `systemd-run --user --scope` — no systemd, no user manager, some
  containers, macOS — the bound is a documented no-op: one note on stderr and the
  leaf runs exactly as it does today.

To try it on a systemd user session, set `leaf_memory_max = "64M"` in `[driver]`
and run any leaf that allocates past it: the leaf exits non-zero and the driver
and its siblings keep going. On a host without systemd, the same run prints the
note once and behaves exactly as before. The user-facing write-up is
`docs/07-crosscutting.md` ("Bounding what a leaf may use"), and the rendered
config documents both keys inline.

## Root cause
Leaf subprocesses were spawned with no resource bound of any kind — the harness
already bounds a gate's wall clock and the workspace's disk footprint, but memory
was left unbounded. Worse than the overrun itself is that it is unattributable:
`systemd-oomd` kills the *cgroup* under pressure, not the offending process, so
the whole session dies together and no log names which leaf caused it.

## Fix
`_invoke` — the one place every leaf is spawned, headless and interactive alike —
now prepends a memory-bound wrapper to the argv when one is configured. The
facility is a transient systemd *scope*, chosen so the leaf stays a direct child
in the caller's session: interactive leaves keep the terminal they are REPLs in,
and stdio, exit status and process group behave exactly as an unwrapped spawn. The
kernel reaps the offender inside that scope, so the leaf exits non-zero and
surfaces through the existing leaf-failure path instead of taking the driver with
it.

The bound is configurable at two levels: `[driver].leaf_memory_max` for all
leaves, and `memory_max` on any `[leaves.*]` table to override it for one leaf (or
`memory_max = "off"` to opt that leaf out). That includes the array-form tables —
`[[leaves.advisory]]` and `[[leaves.plan_advisory]]`, the pool a run fans out
concurrently — and variants/escalations inherit the leaf they vary rather than
silently losing its cap or its opt-out. Values are validated at load; an
unparseable bound degrades to unbounded with a note rather than becoming a systemd
property that would make every spawn fail to start. The host facility is probed
once per run, not once per spawn, so a run is either bounded or it is not — never
half of each.

## Verification
- **Claim:** With a bound configured, the argv actually spawned is the leaf's argv
  wrapped in the bound — on the **headless** path.
  **Checked:** `template/src/pdca_harness/leaves.py:364-370` — the wrapper is
  prepended once, ahead of both per-branch tails, so it cannot cover one spawn
  shape and miss the other; resolution in `leaves.py:263-323`.
- **Claim:** Same on the **interactive** path, with the leaf still inheriting the
  parent terminal (a seeded REPL that loses its tty would be a regression).
  **Checked:** `template/src/pdca_harness/leaves.py:370-380` plus the `--scope`
  rationale at `leaves.py:218-232`; asserted by
  `template/tests/test_leaf_memory_cap.py:168-178`.
- **Claim:** With **no** bound configured — the default — the spawned argv is
  byte-for-byte today's argv.
  **Checked:** `template/src/pdca_harness/leaves.py:263-274` (unset, and an
  explicit `"off"`, both yield an empty prefix; a `None` config never crashes);
  asserted by `template/tests/test_leaf_memory_cap.py:180-188, 245-249`.
- **Claim:** With a bound configured but the host facility **absent**, the argv is
  byte-for-byte today's argv and the leaf still runs — a documented no-op, never a
  hard failure.
  **Checked:** `template/src/pdca_harness/leaves.py:277-323` (probe the exact argv;
  any failure, timeout or missing binary ⇒ unsupported, one note on stderr);
  asserted by `template/tests/test_leaf_memory_cap.py:189-206`.
- **Claim:** The per-leaf override reaches *every* config surface the docs claim,
  including the array-form tables and derived leaves.
  **Checked:** `template/src/pdca_harness/leaves.py:2256-2272` (one constructor for
  `[[leaves.advisory]]` and `[[leaves.plan_advisory]]`),
  `template/src/pdca_harness/leaves.py:885-895` (variants/escalations inherit),
  `template/src/pdca_harness/config.py:45-61` (validation),
  `config.py:364-365, 571-577, 683-684` (parsing).
- **Claim:** The behaviour is documented where a user will find it.
  **Checked:** `docs/07-crosscutting.md:333-378` and
  `template/pdca.toml.jinja:185-203, 388-398` — including the degradation on a host
  that cannot enforce the bound.
- **Test:** `template/tests/test_leaf_memory_cap.py` (new, 22 tests, stdlib-only,
  offline — the spawn and the host probe are stubbed, so no real OOM, systemd or
  root is needed). Fails pre-fix, passes post-fix: with the production hunks
  reverted and the tests kept, `python3 -m unittest tests.test_leaf_memory_cap`
  gives `Ran 22 tests … FAILED (failures=15)` — 15 **assertion** failures on
  unwrapped argv, 0 errors — and 22/22 OK with the change applied.
- **Also exercised by hand** (not in the automated suite, which must not require
  systemd or root): on a systemd user session with `leaf_memory_max = "64M"`, a
  leaf allocating 400 MiB was killed inside its own scope and surfaced as that
  leaf's non-zero exit (`rc = -9`) while the driver stayed alive; an in-budget leaf
  ran normally. Reproducible with
  `systemd-run --user --scope --property MemoryMax=64M -- python3 -c "bytearray(400*1024*1024)"`.
- **Suites:** the offline driver suite (1,563 tests) and the docs lint/link audit
  are green with the change.

Fixes #420
