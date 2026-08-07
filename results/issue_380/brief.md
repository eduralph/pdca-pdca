# Brief — issue 380 / settings-write-env-deny-never-matches

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** settings-write-env-deny-never-matches
- **Defect:** the shipped Claude Code permission config declares two file-permission deny
  rules in a form the permission checker never matches. `template/.claude/settings.json:53-54`
  carries `"Write(.env)"` / `"Write(.env.*)"` beside the correct `"Edit(.env)"` /
  `"Edit(.env.*)"` (`:51-52`); the repo's own `.claude/settings.json:82-83` carries the
  identical pair. Claude Code matches file-permission rules only through `Edit(path)` — Edit
  rules cover all file-editing tools, Write included — so the two rows deny nothing the Edit
  rows do not already deny, and Claude Code prints two red validation warnings at the end of
  **every leaf session in every rendered instance**:
  `Permission deny rule (.claude/settings.json): Write(.env) is not matched by file permission
  checks — only Edit(path) rules are. Use Edit(.env) instead (Edit rules cover all file-editing
  tools).` (idem for `Write(.env.*)`). Introduced together with the correct rows in `0103877`
  ("Settings hygiene: drop gramps-specific perms; add generic guardrails to the template"),
  never removed since; observed on the pdca-pdca self-hosting instance during its first real
  cycles (eduralph/pdca-pdca#11, fixed locally by dropping the two rows).
- **Success criterion:** no `.claude/settings.json` this repo ships — the template's
  (`template/.claude/settings.json`) or the repo's own (`.claude/settings.json`) — contains a
  **file-path** permission rule written as `Write(<path>)` in any of its `allow` / `ask` /
  `deny` lists, while the `.env` protection is unchanged (the `Read(.env)`, `Read(.env.*)`,
  `Edit(.env)`, `Edit(.env.*)` rows all remain byte-identical). Demonstrable by C4-verify: the
  named test asserts this over the settings file(s) reachable from the suite and goes red on
  the pre-fix tree, green with the patch.
- **Falsifiability:** RED on the base toolchain, no services, on the target checkout Do is
  given. `cd template && PYTHONPATH=src python3 -m unittest tests.test_settings_permissions`
  fails on `origin/main` because `template/.claude/settings.json:53-54` are present, and passes
  with the patch. C4-verify earns a real red→green here: `*.json` is **not** in
  `engine/scripts/run-verify.sh:41-46`'s non-behavioral set (`docs/`, `.github/`, `*.md`,
  `*.md.jinja`, LICENSE/NOTICE/DCO), so the settings files classify as production hunks, the
  red leg reverts them, and the retained test goes red. The runtime symptom (the two red
  validation warnings) is additionally observable by starting any Claude Code leaf in a
  rendered instance before and after `copier update`, but the test above is the binding
  criterion.
- **Invariant to restore:** every file-path permission rule in a `.claude/settings.json` this
  repo ships is written in the form Claude Code's permission checker actually matches
  (`Read(path)` / `Edit(path)`) — a rule the checker cannot match is not a protection, it is a
  warning printed at the end of every session, and it invites the reader to believe a
  protection exists that does not. Quantified over the defect category: it holds for **every**
  settings file the repo ships and every rule in it, not only the two `.env` rows — a patch
  that dropped only `Write(.env)` while leaving another unmatchable file rule elsewhere
  visibly fails it. Source: Claude Code's own validation diagnostic, quoted verbatim above —
  authoritative (vendor runtime message stating the rule and the remedy). This instance's
  `docs/principles.md` §5/§6 catalogue is an unfilled scaffold, so no §6 category gate applies;
  this is an ordinary behavioural fix under §1.1.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Surfaces:** data
- **Difficulty:** low
- **Scope:** remove the unmatchable file-permission rules from every `.claude/settings.json`
  this repo ships, and pin the invariant with a test that runs in both the template checkout
  and a rendered instance. / out of scope: any change to *what* is protected (the `Read(...)`
  and `Edit(...)` rows stay exactly as they are); the `Bash(...)` deny rows and the `ask` list;
  the `.claude/settings.json` of any other instance (they converge on `copier update`); adding
  new guardrails of any kind.
- **Repro instruction:** on a clean checkout of the target base —
  `git -C ../pdca-harness show origin/main:template/.claude/settings.json | grep -n 'env'`
  → shows `Write(.env)` at 53 and `Write(.env.*)` at 54 beside the `Edit` pair at 51-52; the
  same grep on `origin/main:.claude/settings.json` → the same pair at 82-83. Runtime form:
  start any Claude Code leaf in a rendered instance (e.g. this project's planner) and read the
  two red validation warnings printed at session end. The named test automates the assertion →
  red pre-fix.
- **External dependencies:** none
- **Test file:** `template/tests/test_settings_permissions.py` (new file; top-level in
  `template/tests/` so `run-verify.sh:41-43`'s `template/tests/*.py` glob classifies it as the
  bundle's test). It must resolve the settings file in **both** postures the suite runs in —
  the template checkout and a rendered instance — using the idiom the suite already uses; and
  in the template checkout it must also cover the repo's own root `.claude/settings.json`
  (reachable as the template dir's parent there, absent in a rendered instance, so guard it the
  way `test_remote_control_docs.py` guards its rendered-only case).
- **Citations expected:** Do must cite path:line on the target branch for every change. This is
  a composition slice for the test only: mirror the template-vs-rendered path resolution the
  suite already uses — `template/tests/test_remote_control_docs.py:19-24` (`TEMPLATE =
  Path(__file__).resolve().parents[1]`, the `next(... for n in ("pdca.toml.jinja",
  "pdca.toml"))` pick and the derived `RENDERED` flag) and its `@unittest.skipUnless(RENDERED,
  …)` guard at `:45`. Do MAY open that one file to copy the composition. Note that
  `template/.claude/settings.json` is a plain JSON file, not a `.jinja` template, so the
  relative path `.claude/settings.json` is identical under `TEMPLATE` in both postures; and it
  is **unconditionally rendered** — `copier.yml`'s `_exclude` conditions only
  `.github/workflows/check-gates.yml*` and `.claude/hooks/builder_guard.py*`, never the settings
  file — so the test may require its presence rather than skipping when it is absent.
- **Prior-art check (triage cycles):** by affected file path —
  `git -C ../pdca-harness log --oneline origin/main -6 -- template/.claude/settings.json` →
  `900d638`, `d0456dc` (#277), `67ba7fb` (#261), `92a04d1`, `f7931d3`, `0103877`; `0103877` is
  where both the `Edit` and the dead `Write` rows were added, and no later commit removes them.
  `gh search issues --repo eduralph/pdca-harness "settings deny"` → no hits;
  `gh pr list -R eduralph/pdca-harness --state open` → empty. Closed/rejected work: none on this
  path. Not fixed, not in flight.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.
