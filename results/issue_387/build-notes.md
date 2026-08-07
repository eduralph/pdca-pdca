# Build notes — issue 387 / single-source-the-brief-base-for-gate-scripts

Target: `eduralph/pdca-harness @ main` (worktree `/home/eddie/pdca/pdca-harness.pdca-wt-l0`,
detached at `5e655c2` == `origin/main`). All `path:line` below are **post-patch** lines in
that worktree; pre-patch anchors are named where they differ.

## What the defect actually is (and what the fix must therefore be)

The harness publishes a base-resolution ladder to every instance's C4 gate
(`template/engine/scripts/run-verify.sh:25-27` pre-patch) whose last rung — "the brief's
`Repo + branch target`" — the driver never supplies. The value exists in Python
(`publish._clean_ref` + `_resolve_target`, pre-patch `publish.py:531-559`) but is reachable
only from Python, so a shell gate has to re-derive an anchored parse from a comment that
states the ladder and not the rule. That is one bug in two languages: the same parse was got
wrong and fixed twice already (#235, #262), and the bash re-derivations still carry the
pre-#235 unanchored rule.

So the invariant to restore is **one parse, every consumer reads it** — not "make publish
correct" (it already is) and not "fix the one instance's bash" (out of scope, and it would
leave the next instance to re-derive it again). Concretely the fix has to do three things:
put the parse where a non-`publish` consumer can legitimately reach it, resolve it in the
driver, and export the resolved ref as the ladder's last rung.

## The change, file by file

1. **`template/src/pdca_harness/brief.py:299-345`** — the parse moves here, unchanged in
   behaviour, appended after the other public per-field accessors (`test_files:181`,
   `depends_on:196`, `onto_branch:281` — all unshifted, the insert is below them):
   - `_clean_ref` (`brief.py:299-321`) — moved **verbatim** from `publish.py:531-545`
     (same regex, same `re.match` anchoring, same strip); its docstring gains a paragraph
     saying it is THE one parse and why (#387).
   - `repo_target` (`brief.py:324-334`) — `(repo_spec, base_branch)`; the `@` split that was
     inline in `publish._resolve_target`.
   - `base_branch` (`brief.py:337-345`) — the public per-field accessor: the brief's own base,
     or a caller-supplied default.
2. **`template/src/pdca_harness/publish.py:531-544`** — `_resolve_target` now *calls*
   `brief.repo_target`; `publish._clean_ref` is **deleted**, not duplicated or aliased. A
   re-export would be a second name for one implementation and invites the next reader to
   copy from `publish` again; nothing in the tree referenced it
   (`git grep -n "_clean_ref"` → only `publish.py:531,553,559` pre-patch). Publish's resolved
   values are byte-identical — `test_publish_slice.py:422-472` (#235/#262's own tests) pass
   untouched.
3. **`template/src/pdca_harness/gates.py:468-495`** — the third rung, composed **inside** the
   existing mutually-exclusive chain (the peer callsite the brief cited, pre-patch
   `gates.py:450-476`), not beside it:
   `Onto` → `PDCA_BASE`; else stack-base marker → `PDCA_VERIFY_BASE`; else
   `PDCA_BRIEF_BASE = f"{cfg.base_remote}/{brief.base_branch(bundle/'brief.md', cfg.default_branch)}"`.
   The block comment's contract goes from "these two exports" to "these three" (`gates.py:456`)
   and from "Neither applies ⇒ no export" to "Exactly one is set for every bundle-scoped gate
   invocation" (`gates.py:483`); the new rung itself is `gates.py:493-495`, documented at
   `gates.py:468-478`.
4. **`template/src/pdca_harness/gates.py:432`** — `_run_one` takes `cfg: Config` as a
   required keyword; the three callers all had it already: `gates.py:355`, `gates.py:384`,
   `publish.py:840`. Required, not `cfg=None`-optional, because an optional one silently
   restores the "no base exported" hole for any caller that forgets it — the exact hole this
   bundle closes.
5. **`template/engine/scripts/run-verify.sh:15-34`** — the published ladder now ends in
   `$PDCA_BRIEF_BASE` instead of instructing the instance to parse the brief, states that all
   three are already fully-qualified `<remote>/<branch>` refs ("never `origin/$VAR` — that
   doubles the remote", the `origin/origin/main` in the report), and says explicitly: do NOT
   re-derive this in shell, with the one-line statement of the anchored rule so a reader who
   ignores that at least has the right rule.

### Why `cfg.base_remote`, not a literal `origin/`

Scope says not to go fix `gates.py:492`'s inline `origin/` for the *wave* rung — I didn't
touch it (a stacked/integration branch genuinely lives on `origin`; `publish.py:244` composes
`f"origin/{stack_branch}"` for exactly that case). The *brief's* base is the other half of the
same line: `checkout_base = f"origin/{stack_branch}" if stack_branch else f"{base_remote}/{base}"`
(`publish.py:244`). Using `cfg.base_remote` is what makes the export equal to the ref publish
checks out — the whole point of #54's "test base must not diverge from deploy base". A literal
`origin/` would be *wrong under the fork model* (`config.py:122`: `base_remote` defaults to
`"upstream"`), i.e. it would ship a new divergence in the same commit that closes one. Under
the test's stub `Config` (`base_remote="origin"`) both spellings read identically, so
`test_brief_base_is_a_remote_tracking_ref_on_the_configured_remote` sets `base_remote="upstream"`
to bind it.

## Alternatives considered and rejected

- **Export the raw brief field and let the gate parse it.** Rejected: it re-publishes the
  parse to shell, which is the defect. Costs nothing less either — one export line either way.
- **Keep `_clean_ref` in `publish` and have `gates` import `publish._clean_ref`.** Same number
  of lines (a 1-line import vs. the 46-line move), but it leaves a private cross-module reach
  into `publish` from `gates` (which already only touches `publish` lazily, `gates.py:489`,
  to dodge the import cycle) and keeps the parse in the module whose *name* says "this is
  publish's". `brief.py` is where per-field accessors live and is imported by everyone.
- **Emit `PDCA_BRIEF_BASE` unconditionally, alongside `PDCA_BASE`/`PDCA_VERIFY_BASE`.**
  Rejected on the invariant, not on cost: criterion (a) and PR #282's rule are mutual
  exclusion. A gate that sees two set has to re-implement precedence — the same "the harness
  states a ladder, the instance implements it" failure one level up.
- **Generate a shell case-table from the Python tests** — explicitly out of scope, and it is a
  second implementation with a generator attached.
- **Also fix `getwyrd/wyrd-pdca`'s `engine/scripts/run-verify.sh:166-178`.** Out of scope
  (different repo, filed as getwyrd/wyrd-pdca#204). I read it read-only as evidence; nothing
  outside the target worktree was edited.

## Test — `template/tests/test_verify_base.py` (appended, per the brief)

Nine new cases + the module's existing eight, all driving `gates.run_gates` with a **real**
bundle-scoped gate command that `printf`s the three vars into the bundle
(`test_verify_base.py:34-38`) and reads them back — so what is asserted is what a gate process
actually received, not what a mock says. `_ECHO_BASES`/`_recorded_bases` extended from two
vars to three (`:34-38`, `:77-83`); every pre-existing case is otherwise untouched and passes.

New cases (`test_verify_base.py:168-280`): ordinary bundle gets the export; the anchored-parse
pair from the brief (`… @ main (feature branch \`feat/x-slice\`)` → `origin/main`;
`` @ `feat/x` `` → `origin/feat/x`); no target field → `cfg.default_branch` (set to `trunk` in
that test so it cannot pass by coincidence with `main`); `<remote>/<branch>` shape on a
configured `base_remote="upstream"`; **agreement with `publish._resolve_target`** over four
field styles (the one-parse invariant, stated as an equality between the two consumers);
`Onto` and the wave marker each suppress the new rung; exactly-one-of-three over all four
`(onto, marker)` combinations; and the skeleton's ladder text (criterion (e)).

### Forced refutation (the three questions)

- **(a) Genuine red?** Yes, actually reverted and re-run: `git stash push` of the four
  production files (`brief.py`, `gates.py`, `publish.py`, `engine/scripts/run-verify.sh`),
  keeping the test → `Ran 19 tests … FAILED (failures=11)` — every new case red, including all
  four subtests of the publish-agreement case and the `(onto=False, marker=False)` subtest of
  exactly-one. `git stash pop` → `Ran 19 tests … OK`.
- **(b) Production path?** Yes. The tests call `gates.run_gates(d, cfg)` — the production
  entry point — which runs a real shell command through `progress.run_with_heartbeat` and
  reads the environment the production `_run_one` built. The agreement case calls the
  production `publish._resolve_target`. No mock, stand-in, or copied parser anywhere in the
  module.
- **(c) Fixture includes the fault?** Yes. The fixtures are the exact briefs that break the
  unanchored parse — `getwyrd/wyrd @ main (feature branch \`feat/x-slice\`)` from the report
  (the case where Python said `main` and shell said `feat/x-slice`), plus a trailing-prose and
  a trailing-period variant — not a sanitised `owner/repo @ main` corpus. The exactly-one case
  includes the `(onto, marker)` combination that previously exported nothing at all.

## Runner / commit-readiness

- Red→green through the documented offline-suite command (docs/INTEGRATION.md §3 /
  CONTRIBUTING.md:26): `cd template && PYTHONPATH=src python3 -m unittest tests.test_verify_base`.
- Whole target suite through the instance's own T3 gate script,
  `PDCA_WORKTREE=… ./engine/scripts/run-suite.sh`: template-repo suite `Ran 7 … OK`, offline
  driver suite `Ran 1478 tests … OK (skipped=2)`. That covers the `_run_one` signature change
  at all three callsites.
- `bash -n template/engine/scripts/run-verify.sh` parses.
- The target repo configures no Python formatter/linter (no `.pre-commit-config.yaml`, no
  ruff/black/flake8 config; CI is `docs-check` — `docs/publishing/tools/lint_docs.py` over
  `docs/**.md`, which this patch does not touch — plus `render-check` and
  `require-linked-issue`, both exercised by the run-suite render leg). Added lines stay within
  the files' existing column conventions (longest added line 97 chars in `brief.py`, itself
  moved verbatim from `publish.py` where the file's max is 105).
- No PR opened, nothing pushed.

## Notes for sign-off

- The C4 red leg reverts `*.sh` as production (pdca-pdca `engine/scripts/run-verify.sh:41-46`
  classifies `.sh` into `PROD`), so criterion (e)'s skeleton-text case participates in the
  red→green rather than sitting outside it.
- `template/agents/planner.md.jinja:247-248` describes `$PDCA_BASE`/`$PDCA_VERIFY_BASE` to the
  planner (which bases *exist*), not the gate ladder. Left alone: the brief scopes criterion
  (e) to the C4 skeleton, and touching the role prompt would be a non-behavioural hunk the C4
  classifier ignores anyway.
- No external dependency was needed; nothing to declare.
