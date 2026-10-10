# Build notes — issue 604 / signoff-delta-cannot-forge-section6

Target: eduralph/pdca-harness @ main, `b5f5c29` (worktree `$PDCA_WORKTREE`).
Line numbers: `old` = on `b5f5c29`, `new` = with the patch applied.

## The change

One rule, in one place: `signoff.record`'s `set_field` helper now replaces each run of
line-boundary characters in the value with one space before it writes the field.

- `template/src/pdca_harness/signoff.py:35-42` (new) — `_LINE_BREAKS_RE`, the character
  class `[\n\r\v\f\x1c\x1d\x1e\x85  ]+`. That is exactly the set `str.splitlines`
  splits on (the split `_section` uses, `signoff.py:345` old). The test checks this
  equality over every code point (`test_every_splitlines_boundary_…`), so a missed boundary
  would fail the test, not slip through. `\r\n` and mixed runs collapse to one space.
- `signoff.py:296` (new; inside `set_field`, `:277-284` old) — `value = _LINE_BREAKS_RE.sub(" ", value)`
  runs before the callable `repl`. The value still goes through the callable (#529). Nothing
  about backslashes changes.
- `signoff.py:285-295` (new) — the #529 docstring now says "literally … except line breaks,
  which become spaces", and explains why.
- `signoff.py:122-123` (new; `:114-115` old) — `_needs_human_section`'s docstring no longer
  says "the flow flattens"; it says `record` writes every §9 value on one line.

Because the fix sits in `set_field`, it covers every caller without touching any of them:
`cli._signoff` (`cli.py:1473-1474`), `flow._apply_decision` (`flow.py:182-186`, already
flat, so no behaviour change there), and `cleanup._discontinue` (`cleanup.py:154`). It also
covers both values: `delta`, and `by` (written as `f"{by} / {date}"`). `Outcome` is a
constant, so it is unaffected. A value with no line break is unchanged byte-for-byte. All
four existing #529 tests in the file pass unchanged.

Expected side effect, as the brief says: `signoff.iteration_delta` (`_DELTA_RE`, `:33`)
used to cut a multi-line delta to its first line. The carry-forward (`driver.py:371`) now
gets the whole flattened text instead.

### Alternatives considered

- Flatten at each call site (`cli.py:1474`, `cleanup.py:154`): 2 one-line edits. Ruled
  out by the brief's invariant ("whichever entry point writes it … any later caller of
  `signoff.record`"). A new caller would bring the bug back.
- Use the flow's `" ".join(x.split())`: it also collapses tabs and repeated spaces. That
  would change single-line values that #529 promises to record byte-for-byte (my test's
  plain-text control has tabs and double spaces). Ruled out.
- Raise `ValueError` on a line break: the CLI already reports `ValueError` as "cannot sign
  off". But the brief's rule is to replace with a space, and rejecting the input would throw
  away the human's rationale. Ruled out.
- Change `_needs_human_section`'s last-heading rule: out of scope (#607).

## The test

`template/tests/test_signoff_verbatim.py:170-300` (new) — new class
`ForgedSection6InSignoffTextRetiresNothing`, plus `_stub_config` / `_PASS_GATE` (`:155-167`).
I also updated the module docstring (`:1-3`, `:25-32`) and imports (`:38-47`). The file is
copied to the bundle as `test_signoff_verbatim.py`.

Fixture (`setUp`): the bundle is at `cfg.bundle("604")` and built the way
`test_autoiterate._Base._bundle` (`test_autoiterate.py:133-150`) builds one: stub config,
`brief.md`, `patch.diff`, `check-review.md`, `gates.run_gates`, `assemble.assemble_summary`.
I wrote `deferred-findings.json` = `{"items": ["E1","E2"]}` **before** assembly, so
assemble's own §6 renders `- [ ] E1` / `- [ ] E2` (the test asserts both are open, and that
state is AWAITING_SIGNOFF).

Legs:
1. `test_a_multi_line_delta_cannot_forge_section6`: the brief's exact `delta`. Ledger stays
   `[E1, E2]`, the signed SUMMARY has exactly one `## 6. NEEDS-HUMAN` line, `notes` and `E1`
   are on the delta line, and `human` is on the By line.
2. `test_a_multi_line_by_cannot_forge_section6`: the brief's exact `by`, with the same checks.
3. `test_a_multi_line_by_ending_in_a_line_break_cannot_retire_an_entry`: see the deviation below.
4. `test_positive_control_a_real_tick_retires_its_entry`: ticks `E1` in assemble's §6 and
   uses a one-line delta. Ledger becomes `[E2]`. This passes both pre-fix and post-fix, which
   shows the retire step really runs on this fixture.
5. `test_every_splitlines_boundary_is_flattened_and_plain_text_is_untouched`: every
   `splitlines` boundary (computed, not hardcoded), plus `\r\n` and `\n\n\r`, in both `delta`
   and `by`, gives one §6 heading and a one-space join. A plain value with tabs, double
   spaces and `\W` is recorded byte-for-byte.

### Deviations from the brief (deliberate)

- **No separate `driver.advance` call.** `cli._signoff` already applies the transition: it
  calls `driver.run_issue` at `cli.py:1483`, which loops `driver.advance` until the bundle
  halts. So the ITERATE_DO beat (retire → archive → stub rebuild → Check) runs inside the
  sign-off call. A first draft called `advance` again afterwards, and my "SUMMARY archived"
  assertion failed: the SUMMARY on disk was the next round's. The test now reads the signed
  SUMMARY from `iteration-v1/SUMMARY.md`. It asserts its Outcome is `iterated-to-Do`, which
  proves the ITERATE_DO beat ran, and that the bundle is back at AWAITING_SIGNOFF.
- **The brief's `by` value does not retire `E1` pre-fix.** The brief predicted `[E2]`.
  `record` writes `f"{by} / {date}"`, so the forged row reads `- [x] E1 / 2026-10-10`, and
  `retire_cleared` does not match that to `E1`. Measured pre-fix: ledger `[E1, E2]`. That
  leg is still RED pre-fix, but on the heading count (`2 != 1`: the forged heading becomes
  a second §6). The by-leg the brief intended, with a real retirement, is leg 3: the same
  `by` with a trailing `\n`, which pushes ` / <date>` off the forged row. Pre-fix it retires
  `E1` (ledger `['E2']`). I kept both, so the brief's exact value is still tested.

## Red → green (runner: `make check`'s command, `PYTHONPATH=src python3 -m unittest`, under `timeout`)

The bundle-scoped runner (`engine/scripts/run-verify.sh`) needs a bundle and gate context,
so I used the target's own `make check` invocation, scoped to the module and wrapped in
`timeout 300`.

- Post-fix: `Ran 9 tests … OK`. Full driver suite (`make check`): `Ran 2374 tests in 53.5s,
  OK (skipped=2)`.
- Pre-fix (production hunks reverted with `git apply -R prod-hunks-only.diff`, test kept):
  `FAILED (failures=15)`:
  - delta leg: `Lists differ: [] != ['E1', 'E2']`
  - by leg (brief value): `2 != 1 : ['## 6. NEEDS-HUMAN — items …', '## 6. NEEDS-HUMAN']`
  - by leg (trailing newline): `Lists differ: ['E2'] != ['E1', 'E2']`
  - the boundary test fails for each of the 12 boundary subtests (`2 != 1`)
  - positive control and the four #529 tests: pass (not in the failure list).

`prod-hunks-only.diff` in this bundle directory is the `template/src` part of `patch.diff`,
which I used for the revert. It is a scratch file and not needed for review.

## Self-refutation

- **(a) Genuine red?** Yes. With the production hunk reverted, the delta leg empties the
  ledger (`[]`), the trailing-newline by leg retires E1 (`['E2']`), and the brief's by leg
  shows two §6 headings. These are the exact failures listed above.
- **(b) Production path?** Yes. The forged legs call `cli._signoff` with the argparse
  namespace `pdca signoff` builds. That calls the real `signoff.record`, then
  `driver.run_issue` → `driver.advance` → `_retire_cleared_deferrals` →
  `assemble.collect_needs_human` + `autoiterate.retire_cleared`. Nothing is mocked. Leaves
  and gate commands are the stub/`true` ones the template suite uses.
- **(c) Fixture includes the fault?** Yes. The ledger holds both entries, both are open
  `- [ ]` rows in assemble's real §6, and the bundle has every Check artifact
  `collect_needs_human` reads. The positive control proves the retire step reaches and
  changes the ledger on this exact fixture. Without that, an exception in
  `_retire_cleared_deferrals` (which only prints, `driver.py:338-340`) would make the test pass
  vacuously.

## Commit-readiness

The target has no formatter or pre-commit config (no `.pre-commit-config.yaml`, and no ruff,
flake8 or black settings in the repo; only `.ruff_cache/` in a `.gitignore`). I checked by
hand: `git diff --check` is clean, every added line is ≤100 columns (the file's style), and
the test file has no unused imports. ` `/` ` are written as escapes, not raw
characters. My editor first put them in as raw bytes; I caught it with `od -c` and fixed it.

No external dependencies beyond the brief's list. No push, no PR.
