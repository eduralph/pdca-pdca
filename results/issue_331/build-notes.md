# Build notes — issue 331 / handoff-exit-contract

Target: eduralph/pdca-harness @ main (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l1`,
base `abd6f1e`). All citations below are against that tree.

## What was built (maps 1:1 to the brief's success criterion)

**(a) `/handoff <issue_id>`** — `template/.claude/commands/handoff.md.jinja` (new). The
command is a thin shell over the hook's vendor-neutral CLI mode
(`handoff_guard.py --check "$1"`), mirroring the cited peer pattern — `builder_guard.py`'s
second `--command` protocol (`template/.claude/hooks/builder_guard.py:15-17`) — so the
slash-command verdict and the Stop-hook verdict are single-sourced. The per-leaf contract
checks live in a new production module, `template/src/pdca_harness/handoff.py` (plain
Python, offline-unit-testable):

- **planner** — `check_planner` (handoff.py:98): authored brief (not a placeholder,
  `brief.is_placeholder`, brief.py:161), required fields read via `brief.whole_field`
  (brief.py:37 — the corpus trap: multi-line values read as empty by the line-based
  `parse_fields`), and the dependency clause reusing **340's probe verbatim**:
  `doctor.unregistered_dependencies` (doctor.py:325) + `doctor.failing_dependencies`
  (doctor.py:356). Required fields are only the three every template mandates AND the
  measured corpus satisfies (Slug / Success criterion / Repo + branch target —
  brief.md.tpl:8,10,17; design-proposal.md.tpl:15,18,24; plan-pointer.md.tpl:13,18,24).
  `Falsifiability` (absent 52/85) and `Test file` (legitimately empty in 7) are
  deliberately NOT required — the "checked against what the corpus actually satisfies"
  scope clause. The old-bundle trap ("never judged against a contract that postdates it")
  is closed by construction: ids are required and only the bundles the *current session*
  registered/named are ever judged — there is no scan.
- **signoff** — `check_signoff` (handoff.py:131): first line of `signoff-decision` one
  token from `VALID_DECISIONS` (leaves.py:73, read via `leaves.signoff_decision`,
  leaves.py:2594→:2605), rationale below the token REQUIRED for `iterate-*`/`discontinue`.
- **publisher** — `check_publisher` (handoff.py:152): both artifacts (`publish.COMMIT_MSG`
  / `publish.PR_BODY`) exist non-empty, then the instance's deterministic lint. I
  **extracted** the lint core of `cli._contribcheck` (cli.py:1043) into
  `cli.contribution_problems(d, no_issue=)` and made `_contribcheck` call it — the brief's
  "reuse the instance's deterministic lint … rather than the configured T4 row", with zero
  behavior change to the gate (its default-open patch/PR-absent early-outs stay in
  `_contribcheck`).
- **act** — `check_act` (handoff.py:169): the session must NAME its entry
  (`/handoff <entry-date>`); the entry must exist in `process/act-log.md`
  (`act.append_entry`, act.py:659-666) **and postdate the driver-supplied session-start
  baseline** (sha + length of the log at spawn) — authorship distinguished by the driver
  because an end-of-session command structurally cannot take a baseline (brief §Design).

**(b) the Stop hook** — `template/.claude/hooks/handoff_guard.py` (new), registered in
`template/.claude/settings.json` under `hooks.Stop` (project-level, so it covers every
interactive leaf session — they all run with `cfg.root` as cwd: `_invoke(cfg.<leaf>,
cfg.root, …)` at leaves.py:382/:520/:2530/:2571/:2655/:2712 pre-patch numbering). Inert
(`exit 0`) when `PDCA_HANDOFF_ROLE` is unset, so an ad-hoc human session is never
blocked. On a driver-spawned session it re-verifies the ARTIFACTS for every bundle
registered at spawn (a session that discharged its contract without typing `/handoff`
still ends cleanly — the contract is the artifacts, not the ceremony), blocks with exit 2
+ per-item feedback otherwise. Where the driver cannot know the work set at spawn (the
CSV-batch planner chooses ids mid-session, leaves.py:513-522; Act), the session names its
work via passing `/handoff` runs recorded in the session state.

**Escape hatch (open question — my proposal):** a *typed reason*, not an env var:
`python3 .claude/hooks/handoff_guard.py --abandon "<why>"` records the reason in the
driver's session-state file; the next Stop is allowed and the driver prints the reason
when it reaps the session (`handoff.session` finally-block). Chose this over an env var
because env is fixed at spawn — the human can't set it mid-session — and over a bare
touch-file because a reason is forced and lands in the driver's log.

**(c) ids required** — `argument-hint: <issue_id>` (no optional bracket), the command body
and the checker both refuse an empty id, `run_check`/`--check` take exactly one id;
no code path enumerates bundles.

**(d) no bundle artifact** — the verdict is exit status + printed report; the only state
is the driver's scratch file `.pdca-handoff-*.json` in the PROJECT root (gitignored,
`.gitignore.jinja`, pattern-tested), created and reaped by `handoff.session`. A test
asserts the bundle's file set is byte-identical across a `/handoff` run.

**(e) session carry-forward, registered + consumed together** — the live channel is the
rationale below the decision token, written *as each decision is made* (the batch prompt
already mandates write-as-decided, leaves.py:2586). Two halves shipped together:
- **register/capture:** `flow._apply_decision` (flow.py:192 pre-patch) unlinked
  `signoff-decision` right after flattening the rationale to ONE §9 line
  (`rationale = " ".join(...)`, flow.py:181) — destroying the only structured copy before
  the iterate transition could read it. The patch captures the FULL multi-line rationale
  into `state.SESSION_CARRY` (`session-carry-forward`) just before that unlink, for
  `iterate-do`/`iterate-plan`.
- **consume/merge:** `driver._carry_forward_into_brief` (driver.py:248) now merges the
  capture with the §9 delta it already extracts — deduped (a single-line capture identical
  to the flattened delta adds nothing), and the file is archived WITH its attempt via
  `state.DOWNSTREAM_OF_BRIEF` (state.py:45) so it never leaks into the next attempt.

**(f) derived from the render** — `handoff.interactive_roles` introspects the `Config`
dataclass for `LeafConfig` fields with `interactive=True` (config.py:485 reads the
rendered `interactive` key; pdca.toml.jinja:504/:518/:528/:544 set it for the four
leaves); `handoff.contracts` intersects with the roles that HAVE a check. Rendering a
leaf non-interactive sheds its contract; the interactive splitter (pdca.toml.jinja:419)
has no contract and is explicitly unchecked — tested.

**Spawn wiring** — every command-mode interactive spawn now runs inside
`handoff.session(cfg, role, bundles)` which supplies `PDCA_HANDOFF_ROLE` /
`PDCA_HANDOFF_STATE` env: `do_plan`, `do_plan_batch` (with `require_artifact=False` for
the id-seeded batch — its prompt documents "leave it UNPLANNED and say why" as
legitimate, so a wholly-absent brief passes at Stop while a malformed one never does),
`run_signoff`, `run_signoff_batch`, `run_publish` (merged over the existing `guard.shim_env`
dict), `run_act` (baseline captured under the act session lock). Stub modes untouched, so
the offline flow/CI is unchanged.

## What I ruled out, with costs

- **A `pdca handoff` CLI subcommand** as the command's entry point: needs the console
  script on PATH inside the leaf session (only true after `make install` + venv
  activation). The hook-CLI route (`python3 .claude/hooks/handoff_guard.py --check`) works
  in any rendered instance with zero install, and is the exact `builder_guard --command`
  peer pattern. Cost of the alternative: a cli.py subparser + dispatch (~25 lines) *plus*
  a PATH failure mode in the one place the check must never silently fail.
- **Per-agent frontmatter Stop hooks** (four copies in
  `.claude/agents/{planner,signoff,publisher,act}.md.jinja`): 4×6 frontmatter lines vs one
  settings.json entry, and those four files are copier-EXCLUDED when
  `interactive_family != 'claude'` (copier.yml:49-52) — the registration would vanish with
  them. The settings-level hook is one entry, env-gated, and survives every render shape.
- **A `handoff.json` bundle marker / verdict artifact**: rejected by the prototype
  (brief §Alternatives — "an artifact no role names, and a fourth write for a leaf whose
  contract is 'exactly three things'"); criterion (d) forbids it outright.
- **Reordering flow's unlink after the transition** instead of the capture file: the batch
  sweep defers `iterate-do` rebuilds to the NEXT pass (`apply_now=False`,
  flow.py:132-149), so the decision file would have to survive across passes — where the
  sweep re-reads it as a live decision (flow.py:151). A stale-decision guard for that
  costs more than the 5-line capture and re-introduces the exact class of bug #323 fixed
  for markers.

## Session-blocking behavior change, on purpose

Ending a sign-off session without decisions used to be silently tolerated (the flow
prints "recorded no decision"). With the hook, that now requires either the decisions or
a typed abandonment. That is the issue's point — "the human pressed Ctrl-D" and "the leaf
discharged its contract" must stop being the same event. Ctrl-C (SIGINT) still bypasses
the Stop hook by construction (no graceful stop), which keeps a hard human override.
Two existing tests asserting the publisher spawn env byte-exactly
(`test_publish_slice.PublisherGuard`) were updated to assert the shim key AND the new
session keys — the contract they pin (shim for codex, none for claude) is unchanged.

## Verification (all through the target's own runners)

- Green leg: `template/ $ make check` → `Ran 1408 tests … OK (skipped=2)` on the patched
  worktree; on a pristine `HEAD` + full patch: same, plus the repo-root suites
  `python -m unittest tests.test_render_and_run` (renders the template with copier and
  runs the generated project's own tests — this caught that the suite runs in rendered
  instances too, where `.jinja` suffixes are stripped; fixed via the `_first()` dual-name
  resolution test_seed_spill already uses) and `tests.test_update_compat`,
  `tests.test_render_cli_name` → OK.
- Red leg (the C4 shape — production reverted, test kept): `HEAD` +
  `git apply --include='template/tests/*' patch.diff` →
  `python -m unittest tests.test_handoff` → `FAILED (errors=1)`,
  `ImportError: cannot import name 'handoff' from 'pdca_harness'`.

## Forced self-refutation (recorded per the Do contract)

- **(a) Genuine red?** YES — with the production hunks reverted (tests kept), the run
  above fails: the module, hook and command do not exist on `main`, and the
  carry-forward-merge assertion targets code paths (`_session_carry_forward`,
  `flow`'s capture) that are absent pre-patch. Actually executed, not inferred:
  `FAILED (errors=1)` shown above.
- **(b) Production path?** YES — the tests drive `pdca_harness.handoff`,
  `flow._apply_decision`, `driver._carry_forward_into_brief`, `cli.contribution_problems`
  and `state.DOWNSTREAM_OF_BRIEF` directly (the modules the driver itself runs), plus the
  real hook file via `importlib` and the real rendered-artifact bytes
  (command/settings/gitignore). No re-implementation, no mocks of the units under test.
- **(c) Fixture includes the fault?** YES — the planner fixture carries the actual
  corpus trap (a MULTI-LINE Success criterion that line-based parsing reads as empty,
  and deliberately-absent Falsifiability/Test file); the dependency fixture registers a
  row whose detect cmd genuinely exits 3 (a real subprocess through
  `doctor.failing_dependencies`); the act fixture names an entry that pre-exists the
  baseline (the authorship fault); the carry-forward fixture holds a rationale whose
  structure §9 flattening actually destroys.

## For the human at sign-off

- Escape-hatch shape (typed `--abandon "<why>"` via the hook CLI, recorded in the
  driver's session channel) is my proposal for the brief's open question — judge it here.
- The Stop hook depends on Claude Code honoring project-level `hooks.Stop` in
  `settings.json` for driver-spawned REPL sessions. That is the documented hook surface
  (same file already carries `permissions`), but it is only exercisable interactively —
  the offline suites verify the registration + the verdict logic, not Claude Code's
  dispatch of it. A one-minute manual check on the next real `pdca flow`: end a sign-off
  session without writing the decision; the session must be blocked with the feedback
  text, then `--abandon "test"` must release it.
- Codex-family interactive leaves get the env + `/handoff`-able CLI but no Stop-hook
  equivalent (codex has no hook surface — same asymmetry `guard.py` documents for the
  builder). The contract still binds at the artifacts; only the *at-boundary* enforcement
  is claude-only. Wiring a codex-side equivalent would be its own slice.
