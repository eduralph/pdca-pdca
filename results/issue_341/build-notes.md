# Build notes — issue 341 / do-halt-on-unmet-dependency

Target: eduralph/pdca-harness @ main (worktree `pdca-harness.pdca-wt-l0`, base
`abd6f1e`). All `path:line` cites below are pre-change positions on that base unless
marked (new).

## What was built

A Do-exit halt seam at BUILT, exactly as the proposal's success criterion specifies:

1. **New module `template/src/pdca_harness/dependency_halt.py`** (new) — the
   deterministic adjudicator. It parses the builder-contract marker via the ONE existing
   parser (`assemble._declared_external_deps`, assemble.py:482 — local import so assemble
   can read the record back without a cycle), extracts each declared dependency name,
   resolves it to a `[[doctor.checks]]` row — **registered rows first**
   (`Config.current_doctor_checks()`, config.py:422, disk-not-snapshot for the same
   reason as #340), else the builder's **proposed fenced ```toml block** — and runs that
   row's detect `cmd` through `doctor.probe`. Verdicts: `confirmed` (cmd exits non-zero),
   `refuted` (exits 0), `unconfirmed` (no resolvable row; a malformed TOML block lands
   here — criterion (c), fail toward review).
2. **Routing in `driver.advance` at BUILT** (driver.py:75-92 pre-change) — the non-close
   branch now adjudicates first. Confirmed ⇒ the existing close fast path machinery one
   beat later: `gates.run_close_gates` (gates.py:152, the N/A matrix, no gate
   subprocess) + a blocked review stand-in mirroring `_close_review_note`
   (driver.py:197-216) whose `- NEEDS-HUMAN —` bullets parse into §6. Then
   CHECKED → assemble → AWAITING_SIGNOFF, so criterion (a) holds: §6 carries the
   `_declared_external_deps` item (assemble.py:199-202 already lifts it from
   build-notes) and the bundle halts at AWAITING_SIGNOFF, never DISCONTINUED
   (criterion (e): §9 outcomes remain the only route to terminal states, state.py:88-94).
3. **Adjudication record** `dependency-adjudication.json` (`state.DEPENDENCY_ADJUDICATION`,
   new constant beside `CLOSE_MARKER`, state.py:36) — written on BOTH outcomes and added
   to `DOWNSTREAM_OF_BRIEF` (state.py:45-64) so an iterate archives it and a rebuilt
   attempt is adjudicated fresh. Resumability is exactly the existing iterate-do
   machinery: the archive step (driver.py:308-343) moves the record, the blocked
   check-review.md and check-gates.json with the attempt, and the rebuild runs the full
   band — locked by `test_blocked_bundle_is_resumable_via_iterate_do`.
4. **Refutation → §6 for Act** (criterion (b)) — `assemble.collect_needs_human` lifts
   `dependency_halt.refuted_items(d)` as HUMAN-kind items right after the
   `_declared_external_deps` block (assemble.py:199-204). §6 is what `pdca act index`
   extracts (act.py:542 → `_extract` reads SUMMARY sections), so the refutation is
   visible across cycles without a new Act input channel. HUMAN, never IMPL: a rebuild
   cannot fix a mis-declaration, and IMPL would let auto-iterate (#264) spin on it.
5. **Config gate** `[driver].dependency_halt` (criterion (f)) — dataclass field beside
   `dependency_guard` (config.py:360), STRICT boolean in `Config.load` (the
   `[leaves.sandbox].network_access` lesson, config.py:517-525): this setting can skip
   the reviewer, so `dependency_halt = "false"` (a truthy string) must fail CLOSED to
   off, loudly. Off ⇒ `adjudicate` returns None before touching build-notes: no probe
   is spawned, no record written, the beat byte-identical — locked by
   `test_off_never_probes_and_writes_no_record`.
6. **`doctor.probe`** (new, doctor.py) — the brief's "340's probe helper" was an inline
   `subprocess.run(cmd, shell=True, capture_output=True, cwd=cfg.root)` repeated at
   doctor.py:395 (`failing_dependencies`) and doctor.py:539 (`run`). Extracted to one
   function, both callers refactored onto it, and #341 calls the same one — "what it
   means to probe a row" cannot drift. (Found and fixed a shadow in `doctor.run`: the
   local `probe = _auth_probe(...)` at doctor.py:454 collided with the new name →
   renamed the local to `auth`; caught by the existing doctor tests.)
7. **`pdca.toml.jinja`** — documents the key (commented, default off) in the [driver]
   tail, at the "add new keys here, away from the contested ones" anchor the file itself
   mandates (the size_guard placement note).

## Design decisions (incl. the proposal's open question)

**Sibling record, not `CLOSE_MARKER` verbatim.** The proposal leaves the choice to Do
with resumability as the constraint. Reusing `CLOSE_MARKER` (content e.g.
`blocked-dependency`) is not free — the marker is read as a *close* semantics carrier at
four other seams, each of which would need conditioning:
- `driver._close_class` (driver.py:160-167): an existing marker wins outright, so every
  subsequent BUILT pass would re-enter the close branch and `_close_review_note` would
  overwrite the blocked note with "Confirm the close disposition … (no patch was
  built)" — false on this bundle, which HAS a patch;
- `split.py:237` and `split.py:396` refuse to split a marker-bearing bundle with a
  close-specific message;
- `revalidate.py:40` re-gates it as a close bundle;
- `state.py:159` treats it as the patch stand-in, which this bundle does not need.
That is ~4 call sites of new `if marker-content == blocked` conditioning (~25-40 lines
plus their tests) to reuse one file name, versus 0 conditioned call sites for a sibling
record: the halt needs no persistent routing marker at all, because writing
`check-gates.json` in the same beat already advances state to CHECKED — the record is
purely audit + the §6/Act feed. `gates.run_close_gates` (the actual machinery worth
reusing) is reused as-is.

**Halting to DISCONTINUED — rejected**, per the proposal's own alternatives section:
wrong semantics (blocked-resume-when-provided, not deliberately-abandoned) and it would
have a leaf set a terminal state, which criterion (e) forbids; DISCONTINUED stays
reachable only via sign-off (state.py:27, :88-94).

**Any-confirmed halts.** With multiple declarations, one confirmed-absent dependency
makes the patch unverifiable regardless of how the others fared, so `confirmed()` is
`any()`. Refuted siblings still land in the record and §6.

**Registered row beats proposed row.** A builder must not out-vote the instance's own
registration with a bogus always-failing proposed row — the human-blessed row is probed
first (`test_a_registered_row_beats_the_builders_proposed_row`).

**Strict name matching, fail toward review.** The declared `<dependency>` token must
equal a row's `id` (default: its `cmd`) case-insensitively — mirroring
`doctor.registered_ids` (doctor.py:306-322). A fuzzy/substring match could let a crafted
declaration resolve to an unrelated failing row and skip review; a miss merely runs full
Check, which is the direction criterion (c) mandates.

## Refutation of my own test (forced, recorded)

- **(a) Genuine red?** YES, two ways. (1) The project's own C4 runner
  (`engine/scripts/run-verify.sh`, the configured `C4-verify` gate) run with
  `PDCA_BUNDLE=results/issue_341` / `PDCA_WORKTREE=…wt-l0`: green leg 13/13 OK, red leg
  (production hunks reverted) FAILED → **"C4 PASS: red without the fix, green with
  it"**. (2) Because the full revert reds via ImportError (the new module is production
  code), I additionally reverted **only `driver.py`'s routing** (git stash of that one
  file) and re-ran: 4 FAIL + 4 ERROR with assertion-level messages ("the reviewer leaf
  was invoked", missing adjudication record) — the exact falsifiability shape the
  proposal names (marker + failing detect cmd ⇒ reviewer NOT invoked fails on main).
  Restored afterwards; final tree green.
- **(b) Production path?** YES. The tests drive `driver.run_issue`/`advance` (the real
  control flow), the real `gates`/`assemble`/`signoff`/`cli._signoff` code, and
  `Config.load` on a real pdca.toml for the strict-boolean case. No copies, no mocks —
  the stub leaves are the harness's own production offline mode (`mode = "stub"`,
  the mode the proposal's falsifiability section prescribes), and the reviewer-ran /
  reviewer-skipped distinction is read from the artifact the production leaf writes.
- **(c) Fixture includes the fault?** YES. The fixture is a bundle whose build-notes.md
  carries the real builder-contract marker; the detect cmds genuinely run (`false`
  exits 1, `true` exits 0 — the proposal's own suggested probes) and side-effect
  markers prove execution both positively (gate cmd `touch` file exists on the
  full-Check path) and negatively (absent on the halt path; probe marker absent with
  the feature off). Nothing curates the failing element out.

## Verification summary

- New suite: 13/13 green (worktree, `PYTHONPATH=src python3 -m unittest
  tests.test_builder_dependency_halt`).
- Full offline driver suite: **1386 tests, OK (2 pre-existing skips)** — includes the
  regression the `probe` shadow would have shipped.
- Repo-root render/update suites (copier renders `pdca.toml.jinja`): 7 tests, OK — the
  documented key renders as valid TOML.
- C4 red→green via the project's own runner: PASS (see (a)).
- Commit-readiness: the target repo configures no pre-commit hooks or formatter
  (`.git/hooks` has samples only; no pre-commit/ruff/black config anywhere); its CI is
  docs lint + render-check + linked-issue, all covered by the green suites above.

## External dependencies

None hit — everything ran offline with stub leaves and `true`/`false` detect cmds, as
the proposal's falsifiability section requires.
