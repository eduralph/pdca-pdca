# Build notes — issue 466 / stub-split-never-reaches-the-tracker

## Target base
`eduralph/pdca-harness @ main`, `acb214ac525bdf5a18e52be18c7036995d9fb55e`
(`Merge pull request #518 from eduralph/fix/507-shipped-suites-assert-only-sanctioned-postures`).
Blob hashes of the three touched files match the patch's pre-image index exactly
(`cli.py` `ca807d1`, `leaves.py` `1211604`, `split.py` `71b66be`), confirmed by
`git rev-parse origin/main:<path>`.

## What I changed and why

The brief's invariant is two-sided by its own "self-test": neither module alone can
restore it, because the two facts live in different processes.

1. **`leaves.py:1596-1602`** (`do_split`) — when `cfg.splitter.mode != "command"`, print
   an unconditional stderr notice **before** calling `_stub_split`, naming the mode and
   the consequence ("`--accept` without --ids will refuse to file its children"). This is
   criterion (d): the operator learns at the moment the stub branch is taken, not by
   eyeballing the proposal's fixture text afterward. Mirrors the existing
   `print(..., file=sys.stderr)` shape already used two lines above at `leaves.py:1580`
   for the no-brief refusal — no new pattern introduced.

2. **`leaves.py:1620-1622`** (`_stub_split`) — write a second HTML comment,
   `<!-- pdca:split-proposal-stub -->`, directly under the existing
   `<!-- pdca:split-proposal v1 -->` marker. This is criterion (a): the provenance is
   now **in the file itself**, so it survives the process boundary between `do_split`
   and a later `pdca split --accept` invocation — an in-memory flag could not have
   (the brief's own diagnosis at `leaves.py:1605-1631` pre-patch). Confirmed the real
   template (`templates/split-proposal.md.tpl:1`) carries no such marker, so a real
   splitter's filled-in proposal is never mistaken for a stub's.

3. **`split.py:52-56, 131-141`** — added `_STUB_RE` and `is_stub_proposal(text)`, a pure
   text predicate colocated with `_VERSION_RE`/`parse` (the module that already owns
   proposal-format parsing). This is the "self-identifying" reader: anyone holding the
   raw text — not an in-memory flag, not a slug-name sniff — can ask whether it came from
   the stub.

4. **`cli.py:767-790`** (`_split`, the filing branch) — captured the proposal text into a
   local (`proposal_text`) so it survives past `split.parse`, then inside `if not ids:`
   (the filing branch — `--ids` is untouched, keeping criterion (c)), check
   `split.is_stub_proposal(proposal_text)` **before** the `try: split.file_children(...)`
   that calls `split.can_file` internally. On a stub match: `split.advisory(...)` naming
   both the cause and the remedy (`[leaves.splitter] mode = "command"`) plus `return 1`
   — never a raise into the CLI, the exact shape of the neighbouring
   `except split.TrackerUnavailable` handler two lines below (cited in the brief).
   This is criteria (b) and (e): the refusal happens strictly before `can_file`, before
   any `gh issue create`, and before `split.accept` — so no bundle is created and the
   parent's `CLOSE_MARKER` is never written.

## Alternatives ruled out

- **Refuse in `split.preflight`.** The brief explicitly rules this out (composition cue,
  brief.md `Citations expected`): `preflight` is the ONE point both `--ids` and no-`--ids`
  acceptance converge on before anything irreversible, so a check there would also block
  `--ids` — breaking criterion (c), the #358 offline round-trip test the brief requires to
  keep working byte-identical. Cost of the rejected alternative: touching `preflight`
  would have been a *smaller* diff (one call site instead of a new predicate + a
  filing-branch check), but it fails the brief's own falsifiability requirement (c)
  outright, so minimalism does not apply — this is an "Invariant to restore" brief.
- **An in-memory flag threaded from `do_split` to `--accept`.** Explicitly the shape the
  brief's Invariant section rejects: "`--accept` runs in a different process from
  `do_split`, where an in-memory flag could not reach it." Not viable regardless of cost.
- **A slug-name sniff (checking for `stub-child-one`/`stub-child-two` literally).** Also
  explicitly rejected by the brief ("not a slug-name sniff"): it only catches THIS
  fixture's exact text, not the category the Invariant is stated over ("any placeholder
  any stub leaf writes").
- **A brand-new marker *constant* exported from `split.py` for the test to import
  directly** (e.g. `from pdca_harness.split import STUB_MARKER`). Rejected per the
  brief's `Citations expected` closing paragraph: a module-level import of a symbol the
  patch adds fails to *import* on C4's red leg (production reverted), which
  `engine/scripts/run-verify.sh:231-234` records as `PDCA-UNVERIFIABLE`, not red. The test
  instead calls `split.is_stub_proposal(...)` as an **attribute access inside a test
  method body** (not a top-level `from … import …`) — confirmed empirically below that
  this fails as a genuine `AttributeError` (a real test error, "Ran 6 tests… errors=1"),
  not a module import failure (no `unittest.loader._FailedTest` in the output).

## The three self-check questions

**(a) Genuine red?** Yes — verified by literally reproducing C4's red leg: staged the
full diff, ran `git apply -R --exclude=template/tests/* /tmp/full.diff` (the same
production-only revert `engine/scripts/run-verify.sh:214-217` performs), then
`PYTHONPATH=src python3 -m unittest tests.test_split_stub_guard -v` from `template/`.
Result: `Ran 6 tests … FAILED (failures=3, errors=1)` — 4 of 6 cases fail without the fix
(`test_accept_without_ids_refuses_before_filing_anything`,
`test_do_split_announces_the_stub_on_stderr_at_the_moment_it_runs`,
`test_the_refusal_does_not_depend_on_can_file_failing`,
`test_the_stub_proposal_is_self_identifying_on_disk`). No
`unittest.loader._FailedTest` appears in the output, so this is a real red, not an
import failure. Re-applied the production hunks
(`git apply --exclude=template/tests/* /tmp/full.diff`) and re-ran: `Ran 6 tests … OK`.
(Two cases — `test_ids_still_accept_a_stub_marked_proposal` and
`test_command_mode_prints_no_stub_notice` — pass on both legs by design: they assert
*unchanged* behaviour, criterion (c) and the "no false positive in command mode" check,
so their invariance across the revert is itself the point, not a gap in the red.)

**(b) Production path?** Yes. The test drives `leaves.do_split` / `leaves._stub_split`
(unmodified call sites, exist on both legs) to produce the actual on-disk proposal, then
drives `cli._split` (the real `pdca split --accept` entry point) with only `gh`
(`subprocess.run`/`shutil.which` inside `pdca_harness.split`) replaced — the same harness
shape `template/tests/test_split.py`'s `FilingChildIssues._patched` already uses, reused
rather than reinvented per the brief's citation. No copy or reimplementation of the
filing logic exists anywhere in the test.

**(c) Fixture includes the fault?** Yes. `test_accept_without_ids_refuses_before_filing_anything`
and `test_the_refusal_does_not_depend_on_can_file_failing` explicitly mock
`split.can_file` to return `(True, "acme/widgets")` — the tracker-IS-reachable case,
which is exactly the live-checkout condition the brief's Defect section describes
(`getwyrd/wyrd#708`/`#709` were filed because `can_file` succeeded and no `--ids` were
given). The fixture does not curate away the failing condition; it manufactures it on
purpose and then asserts `self.calls == []` (no `gh issue create` argv recorded) — the
"absence of the call" criterion (e) explicitly asks for, not merely a non-zero exit code.

## Full regression pass (post-fix)

From `template/`, `PYTHONPATH=src`:
- `python3 -m unittest tests.test_split_stub_guard tests.test_split -v` → `Ran 102 tests … OK`
- `python3 -m unittest tests.test_flow_adopt_split tests.test_plan_policy_split_child tests.test_sizing_split_child tests.test_split_convergence tests.test_split_lineage` → `Ran 95 tests … OK`
- `python3 -m unittest discover -s tests -p "test_*.py"` (the whole offline suite) →
  `Ran 1764 tests … OK (skipped=2)`

## Out of scope, confirmed untouched

Per the brief's Scope section: `split.validate`/`split.preflight`'s structural checks,
`split.py:580-607` (#467, run-3), `state.state`'s PLANNED derivation, `brief.is_placeholder`,
and `template/pdca.toml.jinja` — none of these files appear in `patch.diff`. Verified with
`git diff --stat` against the three production files plus the one new test file only.

## Commit-readiness

No formatter/pre-commit config exists in this target checkout (searched for
`pyproject.toml`, `.pre-commit-config.yaml`, and any `[tool.black]`/`[tool.ruff]` section —
none found), so there is no project-configured formatter step to run. New code matches the
surrounding file's existing style (line width, comment voice, `f-string` conventions,
`print(..., file=sys.stderr)` shape) by inspection.
