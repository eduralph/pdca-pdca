# PR description

## Summary
**User impact:** the automated review of a change kept handing checks back to the human
with "I could not reproduce this — decide by hand", even when the run's complete output
had already been recorded and saved with the change. Worse, it was inconsistent: in one
project's saved rounds the very same two checks were bounced back on seven changes and
accepted on an eighth, with nothing different between them. Every bounce cost a person a
manual re-run of something that had already run, and the noise made the genuinely
undecidable items harder to spot.

The cause was simply that the saved output was not put where the review could read it.
This PR copies the round's recorded check output into the review's working directory and
tells the reviewer to read it — so a check it cannot re-run itself is judged from the
evidence, and the escalation to a human is reserved for a check with no evidence at all.

Reported in [#403](https://github.com/eduralph/pdca-harness/issues/403).

## What to look at
The review runs in a throwaway directory that is deliberately given only a few files, so
it cannot be swayed by the author's own notes. That list was file names only, so the
`gate-logs/` folder — the recorded output of each check, which the results file points at
by name — never made it in. The change adds one small helper in
`template/src/pdca_harness/leaves.py` that copies that folder, calls it from both places
that build such a directory, and updates the reviewer's instructions (the driver prompt
and the shipped `template/agents/reviewer.md.jinja` role text) to match.

To try it: run a bundle through the checks so a `gate-logs/` folder exists next to
`check-gates.json`, then start a review — before this change, opening the path any result
row names fails inside the review's directory; after it, every one of them opens, and the
author's notes are still absent. Or run the suite:
`cd template && PYTHONPATH=src python3 -m unittest tests.test_driver_slice`.

## Root cause
The reviewer and advisory sandboxes were seeded from `REVIEWER_INPUTS`, a list of **file
names** copied with `shutil.copy2` (`template/src/pdca_harness/leaves.py:64`, `:1890` and
the advisory twin `:2203` on main), so a *directory* could never land. Every gate row
meanwhile carries `row["log"] = "gate-logs/<rule_id>.log"`
(`template/src/pdca_harness/gates.py:544` on main), written under the explicit promise
that "the verdict's whole basis … must be reconstructable from bundle files alone"
(`gates.py:535-537` on main) — a bundle-relative path that did not resolve one directory
away. The contract text sealed it: the prompt claimed "You have ONLY patch.diff, brief.md
and check-gates.json in this directory" (`leaves.py:1472-1476` on main) and the role body
routed any gate the leaf could not re-run straight to `NEEDS-HUMAN`
(`template/agents/reviewer.md.jinja:50-57` on main), never naming the frozen evidence, and
never saying that a row's `oracle` wrappers are instance-root / `$PDCA_WORKTREE`-scoped by
design and are not runnable from `$PDCA_TARGET` at all.

## Fix
- New `_seed_sandbox_gate_logs` (`template/src/pdca_harness/leaves.py:1601-1632`) copies
  `state.GATE_LOGS_DIR` into the sandbox with `shutil.copytree(dirs_exist_ok=True)`,
  mirroring the existing `_seed_sandbox_agents` seed (`:1573-1598`): a missing directory is a
  silent no-op and a `shutil.Error`/`OSError` degrades to a stderr note, so a copy failure
  can never abort a check round.
- Called from both sandbox builders, which the issue requires to stay in step:
  `_run_review_sandboxed` (`:1939`) and `_run_advisory_sandboxed` (`:2256`). The Plan-time
  advisory sandbox (`:2539`) is untouched — a plan round has no gate logs yet.
- `REVIEWER_INPUTS` is deliberately **not** extended (`:63-66`, comment only): it is also
  the public surface of the independence assert (`reviewer_input_paths`, `:1469`),
  whose callers expect files, and putting the evidence inside that list would leave a
  future edit one keystroke from a real leak.
- Contract text now matches reality and routes the leaf to the evidence: the driver prompt
  (`:1474-1486`), the advisory prompt (`:2136-2140`), the vendored role body
  (`template/agents/reviewer.md.jinja:17-22` and `:52-67`) and `docs/05-check.md:420-423`.
  They state that the wrappers are instance-root/`$PDCA_WORKTREE`-scoped — their absence
  from `$PDCA_TARGET` is expected, not a finding — and reserve `NEEDS-HUMAN` for a row with
  no `log` key, a `log_error`, or a missing log file.

## Verification
- **Claim:** every path a frozen `check-gates.json` row references resolves inside the
  leaf's own working directory. **Checked:** `template/src/pdca_harness/leaves.py:1601-1632`
  with its call sites at `:1939` and `:2256`, against the row key written at
  `template/src/pdca_harness/gates.py:544` on main — the same bundle-relative name is now
  seeded, not just referenced.
- **Claim:** the review's independence is unchanged. **Checked:** `REVIEWER_INPUTS`
  (`leaves.py:66`) is untouched and `build-notes.md` is still absent from both sandboxes;
  the existing independence assertion (`template/tests/test_driver_slice.py:59-65` on main)
  passes unmodified, and the new tests write `build-notes.md` into the bundle first so the
  exclusion is a real one rather than vacuous.
- **Claim:** the seed can never turn into a new failure mode. **Checked:**
  `leaves.py:1624-1632` — the copy is wrapped exactly like `_seed_sandbox_agents`
  (`:1591-1598`), and a bundle with no `gate-logs/` returns before touching the filesystem.
- **Claim:** the instructions no longer describe a sandbox that does not exist, and send an
  unrepeatable gate to its log. **Checked:** `leaves.py:1474-1486`, `:2136-2140`,
  `template/agents/reviewer.md.jinja:17-22`, `:52-67`, `docs/05-check.md:420-423` — the old
  "You have ONLY patch.diff, brief.md and check-gates.json" sentence is gone from both
  prompts.
- **Test:** `template/tests/test_driver_slice.py:415-531` — five cases appended to the
  existing sandbox/independence group. The binding one (`:444`) runs a **real** gate
  through `gates.run_gates`, so `check-gates.json` and `gate-logs/T3-log.log` are
  production artifacts rather than hand-written fixtures; a fake leaf command then reads
  the seeded `check-gates.json` from its own cwd and resolves *each row's own* `log` value
  there, reads the file back and asserts the header plus both output lines, and asserts
  `build-notes.md` is absent. The others cover the advisory sandbox (`:467`), an `OSError`
  from the copy degrading instead of aborting (`:484`), a bundle without `gate-logs/`
  behaving exactly as before (`:500`), and the contract text (`:515`, asserted the way
  `test_review_prompt_grounds_on_pdca_target` at `:257` on main does, and tolerant of the
  role body shipping as `.md.jinja` or rendered `.md`). Fails pre-fix — with the production
  hunks reverted and the tests kept, 3 of the 5 fail on `{'gate-logs/T3-log.log': False}`
  and on the stale prompt sentence — and passes post-fix (84 tests OK). Also green: the
  full template suite (1499 tests, including the rendered instance) and the docs lint plus
  link audit, which the `docs/05-check.md` and role-body edits touch.

Fixes #403
