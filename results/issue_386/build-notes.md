# Build notes — issue 386 / remote-control-test-holds-in-both-postures

Target: `eduralph/pdca-harness @ main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`,
base `5e655c2`). One file touched: `template/tests/test_remote_control_docs.py`
(+165 / −2).

## What the defect actually is

`test_it_stays_off_by_default` (base file `:69-75`) asserted a **template default** —
"every line mentioning `--remote-control` is commented" — over a file that ships into
rendered instances (`:19-24` resolves `pdca.toml.jinja` **or** `pdca.toml`). The moment an
instance does the thing #337 documented (uncomment the flag on an interactive leaf), it
inherits a permanently red test. Meanwhile the property that *does* hold in every posture —
the flag rides only an `interactive = true` leaf, never a headless one — was **not asserted
at all**: the blanket comment-check caught a headless-leaf argv only *by accident*, as a
side effect of forbidding every uncommented occurrence.

So the invariant to restore is not "silence the false red"; it is "assert the protection
instead of the default". A patch that only silences it is refuted below with a run.

## The change (path:line on the patched worktree)

1. `template/tests/test_remote_control_docs.py:38-51` — `_sections(text)`: `(header, body)`
   for every `[...]` table, the same line-anchored `re.split` idiom the existing
   duplicate-argv check uses at `:104`, widened from `^\[leaves\.` to `^\[` so an active
   flag parked outside a leaf block cannot slip past.
2. `:53-73` — `remote_control_offenders(text)`: every **uncommented** line carrying
   `--remote-control` that is not inside a `[leaves.*]` block declaring `interactive = true`.
   This is the posture-independent property. Commented lines never count (the template's
   commented example is the whole point); an enabled interactive leaf is legitimate; a
   headless leaf is not.
3. `:117-128` — new `test_the_flag_rides_only_an_interactive_leaf`, running in **both**
   postures, asserting `remote_control_offenders(self.text) == []`. This is criterion (c):
   a rendered instance with the flag on `builder` / `reviewer` / any advisory leaf fails
   here, naming the leaf.
4. `:130-146` — `test_it_stays_off_by_default` kept, now `@unittest.skipIf(RENDERED, …)`,
   docstring stating which posture it binds. Mirrors the file's own precedent at `:93-94`
   (`@unittest.skipUnless(RENDERED, …)` on the duplicate-argv count) — the composition cue
   the brief named; no new mechanism invented.
5. `:150-188` — `_rendered_config(enabled_leaf)`: builds a rendered-shaped `pdca.toml`
   (two headless leaves, the doc block with its four phrase anchors, four interactive
   leaves) with the flag **uncommented** on one named leaf. This is the synthetic posture
   the module cannot otherwise see.
6. `:191-238` — `RemoteControlPostures`: two direct assertions on the helper (enabled
   interactive leaf → no offender, for all four leaves; headless leaf → exactly one
   offender naming it, for builder and reviewer) **plus** two end-to-end cases that copy
   this very file into a temp checkout whose `pdca.toml` is the synthetic config and run
   `python3 -m unittest discover` there — i.e. the brief's Repro instruction executed
   rather than described. `_CHILD` (`:154`, `:224`, `:231`) skips the two spawning cases in
   the child so the harness cannot recurse.
7. Module docstring `:11-16` states the shipped-suite rule (a test that ships into
   instances may assert only what holds in every sanctioned posture).

Out of scope and untouched, as the brief required: `template/pdca.toml.jinja` (issue #396
is open against its Remote Control block), the seam's enablement anywhere, the other
assertions in this module, all driver/engine code.

## Refutation — the three forced questions

**(a) Genuine red?** Yes, and for the right reason. Two runs, both with the *fix* reverted
and the *tests* kept (the harness in `/tmp/rc386/redcheck.py` copies a chosen version of the
module into the synthetic instance and runs it; the fixture builder comes from the patched
module):

*Base module (`git show HEAD:template/tests/test_remote_control_docs.py`):*

```
=== flag uncommented on [leaves.planner] -> rc=1
AssertionError: False is not true : --remote-control is active, not commented:
  'argv = ["claude", "--agent", "planner", "--permission-mode", "acceptEdits", "--remote-control"]'
FAILED (failures=1)
=== flag uncommented on [leaves.builder] -> rc=1
AssertionError: False is not true : --remote-control is active, not commented:
  'argv = ["claude", "-p", "--agent", "builder", ... "--remote-control"]'
FAILED (failures=1)
```

→ `test_the_whole_suite_passes_on_an_enrolled_instance` is **red** (rc=1, expected 0):
this is criterion (b), the defect. `test_the_whole_suite_fails_on_a_headless_leaf_carrying_the_flag`
is also **red**: the run fails, but the message never says `leaves.builder` — the failure
comes from the blanket default check, not from a protection.

*Note a small correction to the brief.* Its Repro instruction predicts "put the uncommented
flag on `[leaves.builder]` and the suite passes". It does not — the blanket check catches it
incidentally. The brief's substantive claim is still exactly right: the **protection** is
absent, and the accident evaporates the instant anyone scopes the default check, which every
enabled instance must do. Demonstrated:

*"Silence-only" alternative* (base module + `@unittest.skipIf(RENDERED, …)` on
`test_it_stays_off_by_default`, nothing else — the minimal-diff patch, 1 line):

```
=== flag uncommented on [leaves.planner] -> rc=0   OK (skipped=1)
=== flag uncommented on [leaves.builder] -> rc=0   OK (skipped=1)
```

A headless leaf carrying `--remote-control` is **fully green**. That is the patch the
brief's Invariant says must "visibly fail", and it does:
`test_the_whole_suite_fails_on_a_headless_leaf_carrying_the_flag` red on `assertNotEqual(rc, 0)`,
and `test_a_headless_leaf_carrying_the_flag_is_an_offender` red (no helper to call). So the
protective leg genuinely binds, and the cheaper 1-line alternative is refuted by execution,
not by adjective.

**(b) Production path?** Yes. The defect *is* this module, so the module is the production
artifact. The live-posture test calls `remote_control_offenders` on the real
`pdca.toml.jinja` / rendered `pdca.toml` read at `:77`; the two end-to-end cases copy
`Path(__file__)` — this exact shipped file, not a copy of its logic — into the synthetic
instance and run it under `unittest discover`. No mock, no re-implementation.

**(c) Fixture includes the fault?** Yes. `_rendered_config("builder")` puts the uncommented
flag **on the headless leaf itself** and keeps the headless leaves in the config (`:186`) —
the failing element is present, not curated out. The interactive fixture is exercised for
all four leaves (planner / signoff / publisher / act) and the headless one for builder and
reviewer.

## Runs (project's own runners)

- Post-fix, brief's command: `cd template && PYTHONPATH=src python3 -m unittest
  tests.test_remote_control_docs -v` → `Ran 10 tests … OK (skipped=1)` (the skip is
  `test_no_leaf_block_declares_argv_twice`, unchanged behaviour on the template checkout).
- Whole T3 runner: `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh` →
  `Ran 7 tests … OK` (render + update-compat; these copy the working tree, so the **rendered**
  posture of this module ran too) and `Ran 1473 tests … OK (skipped=2)` (offline driver suite).

## Gate posture

Patch is confined to `template/tests/*.py`, so `engine/scripts/run-verify.sh:51-53`
classifies it **test-only** → C4 exits 77 `PDCA-UNVERIFIABLE` → SUMMARY §6 NEEDS-HUMAN.
Declared by the brief, not a gap; no production edit was invented to manufacture a red leg.
The human judges it by reading the diff plus the two runs above (the "silence-only"
refutation is the one worth re-running: `RC_MODULE=<naive> python3 /tmp/rc386/redcheck.py`).

## Alternatives ruled out

- **Silence-only** (`skipIf(RENDERED)` and nothing more) — 1 line, smallest diff. Refuted
  above by execution: leaves the genuinely dangerous posture green. The brief names an
  Invariant to restore, so smallest-diff is not the axis; smallest change that restores the
  invariant is, and that requires the protection.
- **Delete the test** — same hole, plus loses the template-posture assertion that is still
  true and still worth pinning.
- **Parse the config with `tomllib`** instead of a line scan — cannot work in the
  unrendered posture (`pdca.toml.jinja` is not valid TOML: `{% if %}` branches), and the
  module must run in both. The line scan is also what lets "commented" be a first-class
  concept, which is the whole distinction here.
- **Making the module's `TOML` overridable by env var** so the regression could re-point it
  in-process — a new mechanism the file has no precedent for, and it would leak a test seam
  into every rendered instance's config resolution. The subprocess-in-temp-checkout gets the
  same coverage with no seam.
- **Changing `pdca.toml.jinja`'s guidance** to match — explicitly out of scope (#396 is open
  against that block; the two must land independently).
