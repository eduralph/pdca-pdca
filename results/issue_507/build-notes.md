# Build notes — issue 507 / shipped-suites-assert-only-sanctioned-postures

## What changed, and why

Three shipped test modules assert a property that only holds in the template's own
*default* posture, so a rendered instance that follows the template's own published
instructions inherits a permanently red `make check` (T3) for something it did nothing
wrong. Per the brief's Invariant, a suite shipped **into** rendered instances may assert
only what holds in every posture the template sanctions; a template-default-only property
must be scoped to the template checkout, and where a real protection hides behind the
default, the protection (not the default) is what has to bind every posture. I applied the
#386 precedent (`template/tests/test_remote_control_docs.py`, commit `75294d1`) to the
three loose ends the brief names.

### `template/tests/test_families.py` (`ShippedPdcaTomlExamples`, patched lines 357–427)

Split the old two-test pair into three, matching the brief's Scope (i) exactly:

- `test_leaves_sandbox_is_declared_at_most_once_active` (line ~394) — binds **every**
  posture: at most one *active* (uncommented) `[leaves.sandbox]` header. Replaces the old
  combined-count regex (`^#?\s*\[leaves\.sandbox\]\s*$`, which counted commented headers
  too) with an active-only one (`^\[leaves\.sandbox\]\s*$`, line 337), so an active table
  next to a *kept* commented example no longer double-counts.
- `test_the_commented_example_round_trips_when_present` (line ~403) — binds **every**
  posture: *if* a commented example is present it must still parse to one table with an
  unquoted boolean; if absent, the test is a no-op pass (an instance may delete the
  now-redundant copy-paste text once enrolled).
- `test_the_commented_example_is_still_present` (line ~416) — binds the **template
  checkout only** (`skipTest` when `rendered`), preserving the one property that really is
  template-default-only: the example's mere presence.

`_source()` (line 375) now returns `(text, rendered)` instead of only `text` — the brief
cited this exact gap (`test_families.py:340-351` in the pre-patch file) as the reason the
posture wasn't exposed at the assertion site the way `RENDERED` is in
`test_remote_control_docs.py:35`. `SOURCE_TEXT`/`SOURCE_RENDERED` (lines 369–370) are
overridable class attributes, `None` by default (falls through to the real file) — this is
what lets `ShippedPdcaTomlExamplePostures` (line 430) drive the *real* `ShippedPdcaTomlExamples`
suite against synthetic text without touching the checkout or spawning a subprocess.

`ShippedPdcaTomlExamplePostures` builds all four postures the Success criterion enumerates
as synthetic `pdca.toml` text in a temp string (no temp *directory* was needed here — the
whole check is string-only, so an in-memory string is the smaller, equally-synthetic
fixture; a temp dir would only be needed if the code under test read the filesystem, which
`ShippedPdcaTomlExamples._source()` does, but we bypass that path entirely via the
override attributes, matching the brief's stated preference for asserting over synthetic
text directly, no subprocess) and runs the whole `ShippedPdcaTomlExamples` TestCase against
each via `unittest.TestSuite`/`TestResult`, in-process:

- (i) unrendered checkout — unchanged, still green.
- (ii) active table, no example (this instance's own posture) — green, was red.
- (iii) active table + kept example — green, was red.
- (v) two ACTIVE headers (PR #292 defect) — still red, with an assertion that names which
  case failed, plus a `tomllib.TOMLDecodeError` negative control proving the underlying
  defect is real, not an artefact of the loosened regex.

### `template/tests/test_verify_red_leg.py` (`C4RedLegVerdictRule`, lines 32–42, 73–166; `C4SkeletonWordingPostures`, lines 168–221)

`run-verify.sh` carries no `.jinja` suffix (copier copies it verbatim per the file's own
comment at line 34), so — unlike `pdca.toml` — its *filename* never signals posture. I read
the posture instead off the project root's `pdca.toml`/`pdca.toml.jinja`, the same signal
`test_families.py` and `test_remote_control_docs.py:33-35` use (`_TOML`/`RENDERED` at
lines 40–42).

`C4RedLegVerdictRule.setUp` (line 84) now `skipTest`s when rendered, with an overridable
`SKELETON_TEXT`/`RENDERED` pair (lines 79–80) — same shape as the sandbox class. The 7
existing test methods and their two helper methods (`_two_factor_block`, `_verdict_for`)
are **untouched** except for reading through `self.RENDERED`/`self.SKELETON_TEXT` in
`setUp`; the brief's Scope explicitly forbids touching `run-verify.sh` or
`README.md.jinja`, and I didn't.

`C4SkeletonWordingPostures` (line 168) drives the real `C4RedLegVerdictRule` suite
in-process against:

- (i) the real skeleton text, unrendered — unchanged, still green.
- (iv) a synthetic filled-in gate (`_FILLED_IN`, lines 175–181: a plausible real
  `pytest`-based gate that quotes none of the skeleton's vocabulary) under `rendered=True`
  — green, was 7 failures.
- A negative control: the same fixture under `rendered=False` — still fails all 7, proving
  the previous case is exercising the *skip*, not a fixture that happens to pass anyway.

### `template/tests/test_verify_base.py` (`VerifyBaseExport.test_the_c4_skeleton_names_the_export_as_the_last_rung`, lines 55–63, 82–89, 293–314; `C4BaseLadderPostures`, lines 332–367)

Same treatment, applied to exactly the one method the brief names — **not** the whole
`VerifyBaseExport` class, which has 16 other methods that bind every instance via real
gate subprocesses and stay untouched. `RENDERED`/`SKELETON_TEXT` are overridable
attributes on the class (lines 88–89), but only this one method reads them; every other
method ignores them (their own `setUp` at line 92 is unmodified). `C4BaseLadderPostures`
runs just this one method (via `unittest.TestCase(methodName)`) against posture (i)
[green, unchanged] and posture (iv) [green, was 1 of the 8 failures], plus the same
negative control.

Together, `C4SkeletonWordingPostures` + `C4BaseLadderPostures` prove the "8 failures"
claim precisely: 7 from the red-leg suite, 1 from the base-ladder assertion — I confirmed
this by running the *unpatched* classes against the same synthetic fixture (see (a) below).

## What I ruled out

- **A shared helper module for the `RENDERED` signal.** The brief's Scope confines the
  patch to `template/tests/*.py`, and a new shared module would still be `tests/*.py`, so
  it wasn't forbidden — but the `_TOML`/`RENDERED` snippet is 3 lines, already duplicated
  once between `test_families.py` and `test_remote_control_docs.py` (the latter untouched,
  out of scope), and the brief's own composition cue points at *that* file as the pattern
  to mirror, not at extracting a library. Sharing it would touch a 4th file for a
  3-line saving and diverge further from the precedent I was told to mirror. Ruled out.
- **Deleting the skeleton-wording tests instead of scoping them.** The brief is explicit
  ("must be scoped, not deleted") — the property is real, it just doesn't bind every
  instance; deleting it would let a template regression on the skeleton's own wording ship
  silently. Ruled out on the brief's own text.
- **Subprocess-driven whole-module runs, mirroring `RemoteControlPostures`'s
  `_run_this_module_against` (`test_remote_control_docs.py:275-304`) verbatim.** The
  brief's fork-storm constraint (added after two OOM-killed Do attempts on this exact
  brief) explicitly prefers no subprocess at all and says the Success criterion already
  mandates that shape. I used in-process `unittest.TestSuite`/`TestResult` runs instead —
  same "drive the real TestCase" property, zero process spawns.
- **Reimplementing the checks as a second, parallel assertion function** for the posture
  regressions (e.g., a free `c4_wording_ok(text) -> bool`) instead of running the actual
  `TestCase` classes. This is the "copy of production" trap the refutation checklist
  warns about — a bug in the *real* 7-assertion logic could still pass the copy. Running
  the actual classes via `TestSuite`/`TestResult` costs nothing extra (a few lines) and
  drives production directly.
- **A temp *directory* + real file I/O for every posture** (mirroring `_rendered_config`
  writing files in `test_remote_control_docs.py:236-254`). For `test_families.py` the
  checked property is purely string-shaped (regex + `tomllib.loads` on a string), so a
  temp dir would add I/O with no behavioural difference — reverted to plain in-memory
  strings, which is still "synthetic file text," per the Success criterion's own wording,
  just not written to disk first.

## Refutation (forced check before declaring done)

**(a) Genuine red?** Yes, verified twice, independently of the delivered synthetic-posture
tests:
  - `template/tests/test_families.py`: ran the **old** (pre-patch, `git show HEAD:...`)
    regexes directly against the three synthetic postures in a scratch script — reproduces
    the brief's own claim exactly: (ii) PASS/FAIL, (iii) FAIL/PASS, (v) FAIL/FAIL.
  - `template/tests/test_verify_red_leg.py` + `test_verify_base.py`: copied the **old**
    (pre-patch) file content plus `template/src/pdca_harness` into a scratch tree
    (`/tmp/507_old_check`), wrote a synthetic filled-in `engine/scripts/run-verify.sh`
    (no skeleton wording) and a bare `pdca.toml`, and ran
    `PYTHONPATH=src python3 -m unittest tests.test_verify_red_leg tests.test_verify_base`
    from that scratch root: `FAILED (failures=8)` — the exact number the brief predicts
    (7 `C4RedLegVerdictRule` + `test_the_c4_skeleton_names_the_export_as_the_last_rung`).
  - The brief also declares this a test-only, C4-UNVERIFIABLE bundle (no production hunks
    to revert), so the usual "revert `patch.diff`, rerun the named test" shape doesn't
    apply here — the fix *is* the test file, so the above scratch-tree run against the
    pre-patch class bodies is the closest honest analogue, and it went red as required.
- **(b) Production path?** Yes. Every posture-regression assertion runs the **actual**
  `ShippedPdcaTomlExamples`, `C4RedLegVerdictRule`, or the one
  `VerifyBaseExport.test_the_c4_skeleton_names_the_export_as_the_last_rung` method — the
  same classes/methods the live (real-checkout) run uses — via `unittest.TestSuite` /
  `TestCase(methodName)` + `TestResult`, never a reimplementation. The only thing swapped
  in is the *input* (`SOURCE_TEXT`/`SKELETON_TEXT`/`RENDERED` override attributes), not the
  assertion logic.
- **(c) Fixture includes the fault?** Yes. Postures (ii)/(iii)/(v) are literally
  `[leaves.sandbox]` tables built the way an operator's uncomment-and-edit would produce
  them (verified posture (v) additionally raises `tomllib.TOMLDecodeError`, the real PR
  #292 defect, not just a test-suite artefact). Posture (iv)'s `_FILLED_IN` fixture is a
  plausible real project gate (`pytest -q --junitxml=...`) that genuinely contains none of
  the skeleton's marker phrases — confirmed by the negative-control test in each file,
  which shows the identical fixture DOES fail all 7/1 assertions when the posture scope
  is turned off.

## Test run (post-fix, exact Success-criterion command)

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_families tests.test_verify_red_leg tests.test_verify_base
```
→ `Ran 71 tests ... OK` (was 60 tests, both suites green, pre-patch — the pre-patch count
excludes the new posture-regression cases; the pre-patch numbers-that-would-fail are the
scratch-tree runs documented under (a) above, since the live checkout can only show ONE
posture — the unrendered template — at a time, which is exactly why the Falsifiability
section requires synthetic construction).

## Gate posture

Per the brief's explicit declaration, this bundle's patch touches only
`template/tests/*.py`, so `engine/scripts/run-verify.sh` classifies it test-only and C4
exits 77 `PDCA-UNVERIFIABLE` → SUMMARY §6 NEEDS-HUMAN, non-gating (not a false red). I did
not add or touch any production file to manufacture a red C4 leg, per the brief's explicit
instruction not to. No `NEEDS-HUMAN external dependency` marker applies — the target
toolchain (stdlib Python ≥ 3.11, no services, no network) was sufficient for everything
Do needed to verify, including the ad hoc pre-patch scratch-tree runs documented above.

## Formatting / commit hooks

No formatter or pre-commit config exists in the target repo (`eduralph/pdca-harness`) —
checked for `.pre-commit-config.yaml`, `pyproject.toml`, `setup.cfg`, a `ruff.toml`/
`.flake8`, and a populated `.git/hooks/` (git-common-dir, since this is a worktree): none
present. No formatter run required before this patch is committable.
