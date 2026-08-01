# Design proposal — issue 331 / handoff-exit-contract

> Plan artifact (design-proposal form). Do reads ONLY this file.

- **Slug:** handoff-exit-contract
- **Kind:** enhancement (design proposal)
- **Goal:** the interactive leaves get a checked exit contract: a rendered `/handoff
  <issue_id>` command that verifies the current leaf's contract and reports PASS/FAIL, a
  `Stop` hook that makes it non-optional, and driver-side capture of the session's
  carry-forward. Today the driver's entire completion signal is process exit — the
  interactive branch discards the exit code and captures nothing
  (`template/src/pdca_harness/leaves.py:250-257`, `subprocess.run(argv + [seed], ...)`
  with no `check=`), so "the human pressed Ctrl-D" and "the leaf discharged its
  contract" are the same event, and a malformed/absent artifact is discovered later, far
  from the cause.
- **Success criterion:** in a rendered instance: (a) `/handoff <issue_id>` exists
  (`template/.claude/commands/handoff.md.jinja`) and checks the *current* leaf's
  contract — planner: `brief.md` structurally against the brief template **and** every
  backticked `External dependencies` token resolves to a registered `[[doctor.checks]]`
  row whose detect `cmd` exits 0 or is annotated exempt (the #340 clause); signoff:
  `signoff-decision` one token from `VALID_DECISIONS` (`leaves.py:73`) with rationale
  for `iterate-*`/`discontinue`; publisher: `commit-msg.txt` + `pr-description.md`;
  act: the session NAMES the act-log entry it wrote; (b) the `Stop` hook
  (`template/.claude/hooks/handoff_guard.py`) blocks a session ending with a missing or
  malformed contract artifact, with feedback and a deliberate-abandon escape hatch;
  (c) ids are REQUIRED — there is no scan mode, and no `argument-hint` advertises one;
  (d) no new artifact is written into the bundle — the gate's verdict is exit status +
  report; (e) the session's carry-forward is captured while the session is live and
  merged with what `driver._carry_forward_into_brief` already extracts on iterate
  transitions; the registering and the consuming of that channel ship together;
  (f) which contract applies is derived from the render (the `interactive = true`
  leaves and their agent names), not hardcoded. Demonstrable by C4-verify: the hook and
  the contract checks are plain Python, unit-testable offline; red on current `main`
  (no `handoff` command, hook, or session-capture channel exists —
  `ls template/.claude/` confirms).
- **Falsifiability:** the offline driver suite on this host. RED now: tests importing
  the hook module / asserting the rendered command exists fail on current `main`
  because neither file exists; the carry-forward-merge assertion fails against the
  current `_carry_forward_into_brief`, which reads recorded artifacts only.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:** 340
- **Conflicts with:** 332
- **Ordering note:** depends on 340 because the planner-contract dependency clause (its
  layer A) reuses 340's detect-cmd probe — 340 stays the authoritative deterministic
  hold; this is the at-the-terminal ergonomic half. Conflicts with 332: both rework the
  carry-forward channel around `driver._carry_forward_into_brief` (332 adds the
  deferred-findings ledger; this adds session-capture merge) — different waves.
- **Difficulty:** high
- **Scope:** the three items of the issue, shaped by the prototype findings
  (getwyrd/wyrd-pdca#166, four review rounds / 27 findings): required ids, no bundle
  artifact, contract-fields checked against what the *corpus* actually satisfies (a
  named/scanned distinction or template-version check so an old bundle is never judged
  against a contract that postdates it; note the four traps measured: `Test file`
  legitimately empty in 7 bundles, `Falsifiability` absent in 52/85, `**User impact:**`
  absent in 43, and multi-line values read as empty by line-based `brief.parse_fields`),
  reuse of the instance's deterministic lint (`cli._contribcheck`) for the publisher
  contract rather than the configured T4 row, and the Act check requiring the session
  to name its entry. Batch wrinkle honoured: `/handoff issue_<id>` gates one bundle;
  the driver supplies the session-start baseline where authorship must be
  distinguished. / out of scope: resuming sessions (considered and rejected in the
  issue — incompatible with the escalation ladder, re-anchors on failed reasoning,
  moves state out of the bundle); any change to the sign-off write set beyond reading.
- **External dependencies:** none
- **Test file:** template/tests/test_handoff.py
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Peer callsites: the mechanical-discipline pattern to mirror —
  `.claude/hooks/builder_guard.py` (PreToolUse) as rendered by the template; the
  interactive spawn — `leaves.py:250-257`; the decision-token validation —
  `leaves.py:73` and `:2605`; the artifact-side carry-forward —
  `driver._carry_forward_into_brief`; 340's probe helper for the dependency clause.
- **Prior-art check (triage cycles):** `git -C ../pdca-harness log --oneline origin/main
  -- 'template/.claude/*'` — builder_guard work only, no handoff/Stop-hook commits;
  commit grep `#331` empty. Prototype exists only in the instance
  (getwyrd/wyrd-pdca#166, plus open follow-ups #172). Not fixed upstream, not in flight.
- **Disposition hint:** new-feature

## Motivation

Every interactive leaf has a checkable contract and none is checked at the boundary; the
failure is discovered by artifact reads later, and what the session established but
never wrote down is lost entirely. The prototype validated demand and reshaped the
design (scan mode removed, no bundle artifact, corpus-checked fields) — carrying those
in avoids re-paying four review rounds.

## Design

See Scope/criterion. The hook is the enforcement (a slash command cannot terminate its
own session or be relied on to be typed); the command is the ergonomics; the driver owns
session-start baselines because an end-of-session command structurally cannot take one.

## Alternatives considered

- Session resume: rejected (see Scope / the issue's recorded rationale).
- `handoff.json` marker in the bundle: rejected by the prototype — an artifact no role
  names, and a fourth write for a leaf whose contract is "exactly three things".

## Impact & compatibility

Renders into every instance; instances see a new command + hook on `copier update`. The
escape hatch keeps deliberate abandonment possible. No bundle-artifact changes.

## Open questions

- Exact escape-hatch shape (env var vs typed token) — Do proposes, human judges at
  sign-off.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a draft PR
MAY happen during the cycle. The PR MUST NOT be marked ready before sign-off accepts.
