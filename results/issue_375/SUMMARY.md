# Result — issue 375 / cli-name-ci-regate

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: `template/.github/workflows/check-gates.yml.jinja:27` runs the merge
  re-gate as a literal `run: pdca gates --working-tree`, but the console script is
  installed under the copier answer `cli_name` (`template/pyproject.toml.jinja:16–17`,
  `[project.scripts]` → `{{ cli_name }} = "pdca_harness.cli:main"`). `copier.yml:92–97`
  explicitly recommends namespacing `cli_name` when several instances share a machine
  (e.g. "pdca-gramps") — any instance that follows that advice gets a CI re-gate that
  fails command-not-found on every PR, and the failure presents as a broken CI runner,
  not a render bug. Hit live by the self-hosting pdca-pdca instance
  (eduralph/pdca-harness → eduralph/pdca-pdca#1; its rendered workflow had to be
  hand-patched to `pdca-pdca gates --working-tree`). The same class — a `.jinja`
  source quoting the default command name literally — exists at ~50 more sites across
  ~10 other `.jinja` files (survey on origin/main: `template/pdca.toml.jinja` ×25
  comment sites, `template/agents/planner.md.jinja` ×7, `template/CLAUDE.md.jinja` ×7,
  `template/agents/publisher.md.jinja` ×3, `template/agents/splitter.md.jinja` ×2,
  `template/agents/signoff.md.jinja` ×2, `template/.claude/agents/publisher.md.jinja`,
  `template/CONTRIBUTING.md.jinja:24`, `template/docs/INTEGRATION.md.jinja`,
  `template/engine/README.md.jinja`, plus `check-gates.yml.jinja:2`). Several of those
  are instructions a model leaf or operator executes (the planner prompt says to run
  `pdca split <id>`), so they are functional under a namespaced render, not just prose.
- Success criterion: rendered with a namespaced `cli_name` (e.g. `pdca-nstest`):
  (a) the rendered `.github/workflows/check-gates.yml` invokes
  `pdca-nstest gates --working-tree` (no bare `pdca` invocation remains in it), and
  (b) a new render-check test renders the template with that namespaced answer and
  asserts that **no file rendered from a `template/**/*.jinja` source** still carries a
  bare `pdca <subcommand>` invocation (subcommands: gates, flow, run, status, signoff,
  publish, doctor, contribcheck, split, try, act, sweep, queue) — so the class stays
  caught. The default render (`cli_name = "pdca"`) keeps the docs' examples literal
  (the interpolation renders back to `pdca`), so existing single-instance renders are
  unchanged. Demonstrable by C4-verify in isolation (red leg below); the T3
  render/update suites are supplementary evidence only.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: replace the default-command-name **invocations** in `template/**/*.jinja`
  sources with `{{ cli_name }}` — the functional breakage is
  `check-gates.yml.jinja:27` (and its line-2 comment); the remaining sites listed in
  Defect are the same class and are exactly what the new render assertion enforces
  (the green leg fails until all are templated) — and ship the render-check regression
  test. The assertion must scope to files rendered from `.jinja` sources: enumerate
  `template/**/*.jinja` in the source tree and map each to its rendered path
  (strip the `.jinja` suffix) — do NOT scan all rendered files. The invocation pattern
  must not false-positive on `pdca.toml`, `pdca_harness`, `pdca-harness`, or the
  namespaced name itself (`pdca-nstest gates` is a pass). / out of scope: the
  verbatim-vendored model spec (`template/PCDA/**` — non-jinja, ships as-is; there
  `pdca` names the generic driver concept, and editing it is an INTEGRATION §4
  human-judgment category), non-jinja shipped files (`template/scripts/bootstrap-tools.sh`,
  `template/Makefile` — already name-agnostic, verified no bare invocations), and
  bare-`pdca` prose that is not invocation-shaped (e.g. "every `pdca` command" — the
  assertion does not cover it; do not chase it).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS: red without the fix, green with it
- C5 Causal adequacy: none — reviewer + human sign-off

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — render_site: link audit OK
- T3 runtime: render/update-compat + offline driver suites: fail — /tmp/tmpcm1hwp0e/results/issue_500/split-proposal.md
- T4 PR body has a user-impact opener + tracker id in both artifacts: pass — pdca-pdca contribcheck
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue #375: make every Jinja-rendered PDCA command honor the configured `cli_name`, especially the CI merge re-gate, and add a namespaced-render regression test.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The acceptance boundary is precise and testable because `cli_name` is the installed console script and is explicitly namespaceable (`template/pyproject.toml.jinja:16`, `copier.yml:90`). |
| C2 Reproduction (red pre-fix) | PASS | In a temporary target copy with every non-`tests/*` hunk reversed, Copier 9.17.0 rendered the old bare workflow command and the required namespaced assertion failed at `tests/test_render_cli_name.py:84`. |
| C3 Change | PASS | The patch stays within the accepted command-name class: the load-bearing CI invocation uses the configured name (`template/.github/workflows/check-gates.yml.jinja:27`) and the regression enumerates rendered Jinja sources rather than unrelated output (`tests/test_render_cli_name.py:94`). |
| C4 Verification (red→green) | PASS | The same namespaced-render test failed on the reconstructed pre-fix copy and passed on the target, with Copier present and the scan guarded against vacuous coverage (`tests/test_render_cli_name.py:121`). |
| C5 Causal adequacy | PASS | The configured command is now used at the source of the broken CI invocation, with no capability probe or runtime fallback masking the load-time cause (`template/.github/workflows/check-gates.yml.jinja:27`). |
| T1 Structure | N/A | This is a non-structural template-data correction; it changes neither component boundaries nor repository layout, and the regression remains in the established root render-test location (`tests/test_render_cli_name.py:1`). |
| T2 Shape | NEEDS-HUMAN | Human must decide whether the recorded docs/link-audit green is sufficient — the exact `./engine/scripts/run-docs-check.sh` runner is absent from the permitted target, so only the independently clean render suite at `tests/test_render_and_run.py:77` could be rerun. |
| T3 Runtime | PASS | The recorded transient `/tmp/.../split-proposal.md` red did not recur: the patched target passed all 7 render/update tests and all 1,308 direct offline-driver tests, including the name-agnostic prompt contract at `template/tests/test_split.py:1265`. |
| T4 Contribution | NEEDS-HUMAN | Human must confirm the deterministic contribution clearance from the gate record — its required bundle context/artifacts were not reviewer inputs, so the bundle-scoped `contribcheck` at `template/pdca.toml.jinja:850` could not be independently rerun. |
| T5 Judgment | NEEDS-HUMAN | Human must confirm the token substitutions preserve role-prompt meaning and that unavailable closed/rejected-work history contains no competing fix — these prompts direct consequential split/publish actions (`template/agents/planner.md.jinja:150`, `template/agents/publisher.md.jinja:6`); local `git log --all` was checked by every affected path and found no prior namespaced-command fix. |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must decide whether the exercised namespaced Copier render represents the real multi-instance CI deployment closely enough for release — acceptance determines whether the observed workflow result at `tests/test_render_cli_name.py:79` is fit for its operational purpose. |


## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] T2 Shape — Human must decide whether the recorded docs/link-audit green is sufficient — the exact `./engine/scripts/run-docs-check.sh` runner is absent from the permitted target, so only the independently clean render suite at `tests/test_render_and_run.py:77` could be rerun.
- [x] T4 Contribution — Human must confirm the deterministic contribution clearance from the gate record — its required bundle context/artifacts were not reviewer inputs, so the bundle-scoped `contribcheck` at `template/pdca.toml.jinja:850` could not be independently rerun.
- [x] T5 Judgment — Human must confirm the token substitutions preserve role-prompt meaning and that unavailable closed/rejected-work history contains no competing fix — these prompts direct consequential split/publish actions (`template/agents/planner.md.jinja:150`, `template/agents/publisher.md.jinja:6`); local `git log --all` was checked by every affected path and found no prior namespaced-command fix.
- [x] Validation — fitness-to-purpose — Human must decide whether the exercised namespaced Copier render represents the real multi-instance CI deployment closely enough for release — acceptance determines whether the observed workflow result at `tests/test_render_cli_name.py:79` is fit for its operational purpose.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: merged-wider
- Iteration delta (if iterating):
- By / date: Eduard Ralph / 2026-07-31

## 10. Act candidates (hints for the next Act review)
- (empty is the common case)
- Reviewer sandbox lacks the T2/T4 oracles (docs-check runner; bundle-scoped contribcheck inputs), so green gate records cannot be independently reproduced and recur as NEEDS-HUMAN — consider provisioning those oracles/inputs into the reviewer's permitted target.
- No preflight identifies leaf-sandbox dependency gaps — doctor checks the host, not the sandbox interior; gate additions (copier, docs runner) drift out of sandbox seeding (same class as #161/#163). Consider a sandbox-interior preflight or per-gate reviewer-reproducibility declaration — candidate for an upstream issue on eduralph/pdca-harness.
