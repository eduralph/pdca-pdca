# Build notes — issue 474 / base-export-reaches-only-the-per-fix-verifier

Target base: `eduralph/pdca-harness @ main`, `acb214a` (`Merge pull request #518 …`).
Worktree: `$PDCA_WORKTREE` (`/home/eddie/pdca/pdca-harness.pdca-wt-l0`), detached at that
commit.

## What changed, and why

`gates._run_one` (`template/src/pdca_harness/gates.py:525` pre-patch, `:554` post-patch)
gated the base-ladder export on `bundle is not None` alone. `run_gates`
(`gates.py:197`) passes `scopes=("repo", "bundle")` for *every* configured row of a
Check run, so any row — repo-scoped, bundle-scoped, verifier or not — that happened to
run under a bundle-scoped invocation got one of `PDCA_BASE` / `PDCA_VERIFY_BASE` /
`PDCA_BRIEF_BASE` in its subprocess environment. The brief's Invariant to restore is
that only the row that actually performs per-fix verification may observe the ladder.

I added one declared row-level key, `verifies_base`, and one helper,
`_verifies_base(chk)` (`gates.py:473-495`):

```python
def _verifies_base(chk: dict) -> bool:
    return bool(chk.get("verifies_base", chk.get("tier") == "C4"))
```

and gated the export on it: `if bundle is not None and _verifies_base(chk):`
(`gates.py:554`, was `if bundle is not None:` at old `:525`).

### Why `tier == "C4"` as the default, not scope

The brief explicitly rules out scope as the discriminator ("this instance's own T3 row
is bundle-scoped, so scope alone does not separate them") and asks for an *explicit,
declared* recognition, citing `_deferrable`'s `at_publish` as the pattern to mirror
(`gates.py:695-708`, its default `c.get("at_publish", c.get("scope", "repo") == "bundle")`
in `publish.publish_gates`, `publish.py:776-778`). I used the same two-part shape:
an explicit boolean key that wins in either direction, with a scope-independent default
for the undeclared case.

The default itself is `tier == "C4"` rather than a flat `False` (which would force every
existing instance to add the key) or scope-derived (which the brief rules out). `"C4"` is
already, by convention, reserved for exactly this row across the whole codebase I could
read from the brief + the one cited callsite:
- the skeleton's own comment: "C4 — the per-fix CORRECTNESS gate"
  (`template/pdca.toml.jinja:908`, pre-patch line, unchanged wording);
- the shipped example row in the same file: `id = "C4-verify", tier = "C4"`
  (`template/pdca.toml.jinja:912-917` pre-patch);
- the test module's own stub row, which is the artifact the brief's Falsifiability
  section anchors on: `_ECHO_BASES = {"id": "C4", "tier": "C4", ...}`
  (`template/tests/test_verify_base.py:47-51`, unmodified by this patch).

So a `tier == "C4"` default is not a new convention I invented — it is naming the
convention that was already implicit in every shipped C4 row, and it is what makes the
compatibility rule (Success criterion iii) hold for free: an instance's existing C4 row
already carries `tier = "C4"`, so it needs **zero** config edits to keep receiving the
base after this patch. Only a row that is bundle-scoped *without* being tier C4 (and
without an explicit `verifies_base = true`) loses the export — and per the brief's own
framing, such a row "never had a contractual claim to it in the first place."

### Composition cues followed

- `at_publish` / `_deferrable` (`gates.py:695-708`, `publish.py:736-778`) — the row-level
  declared-behaviour shape, mirrored above.
- `_run_checks` (`gates.py:388-400`, unedited — the row-level decision in `_run_one`
  itself is where I hooked in, per the brief's citation of `_run_checks` as "where
  per-row decisions are made with both the row and the config in hand"; `_verifies_base`
  needs only the row, so it lives in `_run_one` beside the export it gates, not in
  `_run_checks`).
- The ladder's resolution order and `<remote>/<branch>` shape (`gates.py:495-524`,
  wholly unedited) — only the *gating condition* around it changed (`:554`), never the
  resolution logic. Verified by the unchanged `test_wave_dependent_gets_the_folded_base`,
  `test_brief_base_*`, `test_onto_branch_wins_over_the_wave_base`, etc. (all pre-existing,
  all still pass unmodified).
- `verifies_base` is declared as plain dict data in the stub config
  (`template/tests/test_verify_base.py:54-67`, `_echo_row`'s `verifies_base` kwarg
  written into the row dict), never imported as a module-level symbol — the brief's
  "gate-evaluability trap": C4's red leg reverts `gates.py` first, and a test module that
  then fails to import records `PDCA-UNVERIFIABLE`, not red.

### Documentation (Scope: "document the row-level contract")

- `template/pdca.toml.jinja:911-919` (post-patch numbering) — a new comment block right
  above the shipped `C4-verify` example row, stating the default, the override, and the
  "costs nothing for an existing instance" compatibility fact.
- `template/engine/scripts/run-verify.sh:15-19` — reworded "The driver sets EXACTLY ONE
  of these for every bundle-scoped gate" (stale after this patch — not every bundle-scoped
  gate anymore) to "for the PER-FIX VERIFIER row … and NONE for any other configured
  gate (issue #474)". I checked the Falsifiability gate-evaluability trap first: the two
  asserted substrings (`test_verify_base.py:326-328` pre-patch,
  `"$PDCA_BRIEF_BASE"` and `"Resolve as: $PDCA_BASE > $PDCA_VERIFY_BASE > your own
  override > $PDCA_BRIEF_BASE"`) are untouched verbatim — confirmed with
  `grep -n 'PDCA_BRIEF_BASE\|Resolve as:\|origin/<default>'` against the patched file
  before running any test.

## What I ruled out

- **A flat `verifies_base` boolean with no tier-based default** (i.e., every instance
  must opt in explicitly). Rejected: it fails Success criterion (iii) outright — every
  existing rendered instance's C4 row would silently stop receiving the base the moment
  this patch lands, which the brief calls "far worse than the leak." Cost of the
  alternative isn't a diff-size argument, it's a correctness one: it directly violates
  the stated Invariant's compatibility half.
- **Keying the decision on `chk is cfg.gates_checks[0]`** (i.e., "the first configured
  row is the verifier"), which would also achieve zero-edit compatibility for the common
  single-C4-row case. Rejected: nothing in the brief or the shipped config guarantees
  ordering, and a docs-lint or T3 row registered before C4-verify (a plausible ordering —
  nothing enforces it) would silently become "the verifier" instead, which is a *worse*
  failure mode than the one being fixed (a wrong row gets the base instead of no row).
- **A `_run_checks`-level pass computing "the one verifier row" up front** and threading
  it down as a parameter, per the brief's citation of `_run_checks` as where "per-row
  decisions are made with both the row and the config in hand." I considered this because
  it's the literal citation, but `_verifies_base` needs only the single row's own dict —
  no config-wide state — so building it at `_run_checks` and threading an extra
  parameter through `_run_one`'s existing eight-argument signature would be a larger,
  purely mechanical diff for no behavioural difference. I read the citation as pointing
  at the general pattern ("row-level decisions have a natural home near the row"), not
  as mandating that exact call site — `_deferrable(chk, cfg)` itself is called from
  *inside* `_run_one` (`gates.py:548` pre-patch) for the same reason, which is the more
  precise precedent.
- **Editing `_run_checks`'s `_applies` filter** to drop non-verifier rows from
  bundle-scoped runs entirely. Wrong altogether: the row must still *run* (it's a real
  configured gate, e.g. a repo-scoped T3 suite) — only its *environment* must not carry
  the ladder. Filtering it out of the run would silently stop executing rows that are
  supposed to execute, a different and much worse defect.

## Falsifiability — reproduced

Per the brief's exact recipe: added a second (and third, fourth) row to the stub config —
`T3-repo` (`scope="repo"`), `T4-other` (`scope="bundle"`), both non-`C4`-tier and with no
`verifies_base` key — and asserted they record `UNSET/UNSET/UNSET` while the real
`_ECHO_BASES` (`tier="C4"`) row in the same run still records the resolved base
(`test_only_the_verifier_row_receives_the_ladder`,
`template/tests/test_verify_base.py:326-345`). Also covered the specific "not just the
stacked-bundle symptom" callout: a bundle-scoped non-verifier row on an *ordinary*
wave-0 brief with no `Onto branch` / no stack-base marker still must not see the
unconditional rung-3 `PDCA_BRIEF_BASE`
(`test_the_unconditional_brief_base_rung_also_stays_off_non_verifier_rows`,
`:347-359`).

## Three questions, answered

**(a) Genuine red?** Yes — verified by literally reverting `gates.py` (the one file this
slice's fix lives in) via `git stash push -- template/src/pdca_harness/gates.py` while
keeping every `template/tests/*.py` hunk in place, then running
`PYTHONPATH=src python3 -m unittest tests.test_verify_base -v` from `template/`. Result:
`FAILED (failures=3)` —
`test_a_c4_row_can_opt_out_explicitly`,
`test_only_the_verifier_row_receives_the_ladder`,
`test_the_unconditional_brief_base_rung_also_stays_off_non_verifier_rows` all failed with
`['UNSET', 'UNSET', 'origin/main'] != ['UNSET', 'UNSET', 'UNSET']` — the exact defect the
brief describes (a non-verifier row observing the resolved base). The other two new tests
(`test_a_predating_c4_row_keeps_its_base_with_no_config_edit`,
`test_an_explicitly_declared_non_c4_verifier_still_receives_the_base`) are positive-case
compatibility/override assertions that hold both before and after this patch by design —
they document the *unaffected* half of the contract, not the defect, so they are not
expected to flip. Popped the stash afterwards (`git stash pop`) and reran: `OK` (27/27),
then `make check`: `Ran 1763 tests … OK (skipped=2)`, exit 0.

**(b) Production path?** Yes. The test drives `gates.run_gates` directly — the real
entry point `Check` calls for a bundle-scoped run (`gates.py:189-199`) — over a real
`Config` and a real subprocess (`progress.run_with_heartbeat`, `shell=True`); nothing in
the test module is mocked or re-implemented. `_verifies_base` itself is exercised only
through `_run_one`'s call to it, never called directly by the test.

**(c) Fixture includes the fault?** Yes. The fixture is the exact shape the brief's
Falsifiability section specifies: additional `[[gates.checks]]` rows declared as
non-verifier (one `scope="repo"`, one `scope="bundle"`) alongside the real verifier row,
run through the *unmodified* `run_gates`/`_run_checks`/`_applies` path — nothing is
curated out; the non-verifier rows are real rows that really run in the same Check
invocation as the verifier, which is precisely the scenario the defect occurs in.

## Test runner used

`make check` (`template/Makefile:73-74` → `python3 -m unittest discover -s tests`,
`PYTHONPATH=src`) from `$PDCA_WORKTREE/template` — the project's own offline suite entry
point, per `CONTRIBUTING.md` ("Keep the offline suite green: `cd template && PYTHONPATH=src
python3 -m unittest discover -s tests`") and the Makefile's own `.PHONY: test check`
targets. Also ran the single module directly
(`python3 -m unittest tests.test_verify_base -v`) for faster iteration; both agree.
No GUI/display dependency anywhere in this module — pure stdlib `unittest` + subprocess.

## Formatter / commit hooks

No `.pre-commit-config.yaml`, `ruff`, `black`, or `flake8` configuration found anywhere
under the target checkout (`$PDCA_WORKTREE`) — searched `pyproject.toml.jinja` and the
repo root for formatter tooling; none configured. `CONTRIBUTING.md`'s only stated gate
is the DCO sign-off (a commit trailer, not a file formatter) and the offline suite above,
both accounted for. Nothing further to run.

## External dependencies

None hit beyond what the brief already declared (pure-stdlib Python, no network, no
services) — confirmed by running the whole thing offline in the worktree with no
extra environment variables set.
