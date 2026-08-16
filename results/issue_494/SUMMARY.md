# Result — issue 494 / admit-interactive-leaves-to-the-checkout-they-are-told-to-read

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The harness tells its **interactive** leaves to read the target checkout, then
  spawns them without admitting that directory to their workspace — so the human approves the
  same out-of-workspace reads every session and the approvals never carry over.
  Verified on the target base (`eduralph/pdca-harness` @ `main`, `acb214a`):
  * **The headless leaves ARE admitted.** `do_build` passes the family's grounding flag for the
    worktree (`template/src/pdca_harness/leaves.py:1802`) and for the bundle dir (`:1816`); the
    reviewer (`:2499-2500`), the code-review advisory (`:2835-2836`) and the plan-advisory
    (`:3136-3137`) each pass it for their resolved target. Every one of them is conditional on
    `profile.grounding_flag` being non-empty.
  * **The interactive leaves are not.** All six spawns call `_invoke(<leaf>, cfg.root, …)` with
    **no `extra_argv` argument at all**: `do_plan` (`:781-783`), `do_plan_batch` (`:971-972`),
    `run_signoff` (`:3260-3261`), `run_signoff_batch` (`:3307-3309`), `run_act` (`:3399-3401`),
    `run_publish` (`:3463-3466`). Their cwd is `cfg.root`, so everything outside the instance
    root is outside the workspace.
  * **What they are told to read is outside it.** `_plan_prompt`'s citation line — "Cite the root
    cause against the target source with `git -C <checkout> log/show -- <file>` plus Read/Grep on
    the checkout" (`leaves.py`, `_plan_prompt`) — and `template/agents/planner.md.jinja:72-75`
    and `:214-215` both direct the planner at the target checkout; `publisher.md.jinja:65-66`
    directs the publisher at it. In this instance that checkout is the sibling `../pdca-harness`
    (a required `[[doctor.checks]]` row, `pdca.toml:1026-1031`); `[publisher.checkouts]` is empty
    (`pdca.toml:434-435`), so `publish._checkout_path` (`publish.py:579-587`) resolves it by the
    sibling convention. The bare `Read` rule in the shipped `template/.claude/settings.json` does
    not help: a path outside the workspace needs the **directory admitted**, which is what the
    grounding flag (`--add-dir` for claude and codex, `--include-directories` for gemini —
    `families.py:93`, `:112`, `:123`) does for the headless half.
  * **The approvals cannot close the gap.** The accumulated `.claude/settings.local.json` holds
    both `"Read(/home/eddie/pdca/**)"` (one leading slash — resolved *relative to the project
    root*, so it denotes `<project>/home/eddie/pdca/**` and matches nothing) and
    `"Read(//home/eddie/.claude/**)"` (two — the absolute form). The first sits in the file
    looking granted and never fires. This is inferred from the two forms coexisting in a file
    Claude Code itself writes, not from a controlled test — and **the fix does not depend on the
    inference**, because it admits the directory rather than rewriting a rule.
  * **Same root, second edge:** a grant that lives in the operator's local settings cannot work
    for the unattended band either. `lanes` covers Do+Check only (`pdca.toml:44`, `lanes = 2`),
    whose leaves run in lane worktrees (`worktree.py:104-112`); a git worktree materialises
    tracked files only, so the untracked `settings.local.json` (`.gitignore:19`;
    `template/.gitignore.jinja:11-12`) is invisible to every other lane and dies with the
    worktree — and a sandboxed leaf is further confined by `--setting-sources project`
    (`families.py:102`), which drops user *and* local scope by design (#288/#290). The durable
    channel is the spawn's argv, which is the channel the headless half already uses.
- Success criterion: With the patch applied, **each of the six interactive spawns named
  above** — `do_plan`, `do_plan_batch`, `run_signoff`, `run_signoff_batch`, `run_act`,
  `run_publish` — is launched with the family's grounding flag admitting exactly the
  **admission set** defined below, and nothing else changes about the spawn:
  (i) **the set is the resolved primary checkout of each bundle the session is about**, deduped,
  restricted to directories that exist on disk — resolved from that bundle's `brief.md` the same
  way `publish._resolve_target` + `publish._checkout_path` already resolve it;
  (ii) **when that set is empty** — the planner spawns, where no brief exists yet — it is the
  instance's known target set instead: the paths `[publisher.checkouts]` names, **union** the
  distinct primary checkouts the instance's existing briefs resolve to; same dedupe and
  existence restriction;
  (iii) **never a lane worktree** — a `*.pdca-wt*` directory is not admitted by any of the six,
  even when one exists on disk and `worktree.path()` would return it;
  (iv) **nothing wider** — a directory that neither the config nor a brief names (an unrelated
  sibling checkout, a parent like the operator's home) is **not** admitted; asserted as a
  negative case, not assumed;
  (v) **a family with no grounding mechanism** (`generic`, whose `grounding_flag` is `""` —
  `families.py:44`, `:126`) is spawned **byte-identically to today**: no flag, no directory, the
  grant skipped rather than faked;
  (vi) **no other spawn property changes** — cwd stays `cfg.root` (the claude family walks up
  from it to find `.claude/agents` and its hooks, `leaves.py:1795-1802`, `#136`), and the
  handoff/exit-contract env, the `gh` STOP shim for a non-native-guard publisher
  (`leaves.py:3459-3460`), and the seed-positional `--` contract (`_invoke:626-635`, `#396`)
  are untouched.
  Asserted mechanically over the argv the driver produces for each of the six spawns — which is
  the whole of what the harness controls.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The workspace admission of the six interactive leaf spawns — `do_plan`,
  `do_plan_batch`, `run_signoff`, `run_signoff_batch`, `run_act`, `run_publish`: compute the
  admission set defined in the success criterion from the configuration and the bundles' own
  briefs, and admit exactly it, per spawn, via the family's grounding flag.
  **Three Plan decisions Do must implement rather than re-derive** (they are why the previous
  attempt was returned; see the carry-forward below):
  1. **All six sites, no exceptions.** The previous brief enumerated five and omitted
     `do_plan_batch` while its criterion said "every interactive leaf"; that contradiction is
     what produced two defensible, opposing verdicts. `run_act` is **in**: with decision 2 its
     resolution is safe, and excluding it would reintroduce the same "which leaves?" ambiguity.
  2. **Resolve the primary checkout, never a lane worktree.** Do **not** route this through
     `_reviewer_target` (`:1972-2002`): it prefers `worktree.path()`, and the interactive leaves
     run **serially**, so `lane.current()` is `None` (`lane.py:26-28`) and `_wt_dir`
     (`worktree.py:107-112`) names the **unsuffixed** `<name>.pdca-wt`. That directory exists on
     this host right now — a live worktree at `645c315`, one commit behind `main`, carrying **no
     `.owner` marker** while the real lane trees are `…-l0.owner = issue_506` and
     `…-l1.owner = issue_494`. Routing through `_reviewer_target` would therefore admit a stale,
     unowned tree instead of the checkout the human actually has open, for every interactive
     leaf — not only for Act. Resolve the primary the way `_plan_fallback_target` does
     (`:3039-3045`: `publish._resolve_target` → `publish._checkout_path`, guarded), and do
     **not** `git fetch` it — `_reviewer_target:1996-1999` fetches for grounding freshness the
     interactive leaves do not need, and it touches the human's checkout on every spawn.
  3. **The empty-set fallback is the answer to "what does the planner get before a brief
     exists".** Pre-brief there is no `repo_spec` to resolve and batch Plan picks its ids
     mid-session (`:956-972`), so the set is the instance's *known* targets: `[publisher.checkouts]`
     ∪ the checkouts its existing briefs resolve to. This keeps every admitted directory one the
     config or an artifact already names — it never guesses, never derives a repo from the
     tracker URL, and never admits a parent.
  **Out of scope:** `template/.claude/settings.json` and everything under `template/.claude/`
  (issue 508 owns that file in run 3, and a tracked static file cannot carry instance-specific
  absolute paths anyway); the headless builder / reviewer / advisory / plan-advisory spawns,
  which already do this correctly and are the pattern to mirror — do not change them; the
  sandbox seeding path (`_seed_sandbox_settings`), whose allow-list must not be widened, and in
  particular do **not** start copying `permissions` from the project settings; the operator's
  `.claude/settings.local.json`, which is theirs and stays untouched; `--setting-sources` /
  sandbox confinement of the interactive leaves; `_reviewer_target`'s own behaviour (the reviewer
  needs its worktree preference — leave it alone and resolve separately); this instance's
  `pdca.toml` / `.claude/`, a different repo (`docs/INTEGRATION.md` §2).

## 2. Disposition claimed               ← sign-off confirms or overrides
- Outcome: likely-fix
- Confidence: medium
- Recommendation: (set by Do)

## 3. Correctness (Check — chain)
- C1 Spec: none — brief.md
- C2 Reproduction (red pre-fix): none — (no gate configured)
- C3 Change: none — patch.diff
- C4 fix verified: bundle test red pre-fix, green post-fix: pass — C4 PASS — red without the fix, green with it
- C5 added test exercises production, not a copy: pass — 1 added driver-suite test(s) import the production package 'pdca_harness'

## 4. Conformance (Check — stack)
- T1 Structure: none — (no gate configured)
- T2 shape: docs lint + site render link audit: pass — docs lint clean, site render + link audit clean
- T2 host CI parity: target docs-check.yml on the pushed tree: pass — host CI parity on the patched tree — docs lint clean, site render + link audit clean
- T3 runtime: render/update-compat + offline driver suites: pass — root suite OK, driver suite OK
- T4 PR body has a user-impact opener + tracker id in both artifacts: deferred — pr-description.md not drafted yet — the substantive T4 audit of the contribution artifacts runs at publish
- T5 Judgment: none — reviewer + human sign-off
- T5 judgment: → see §5.

## 5. Advisory review (artifact-only, decorrelated)
Reviewer ran without build-notes.md. Summary:

Reviewing issue #494: admit only the resolved primary target checkouts to all six interactive leaf spawns while preserving every other spawn property.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The six-site boundary is mechanically decidable: bundle-scoped primaries, Plan's pre-brief fallback, no lane/unrelated directories, and no fabricated generic-family grant (`docs/01-render-and-integrate.md:430`). |
| C2 Reproduction (red pre-fix) | PASS | With the new test retained and production hunks stashed, all 14 cases ran and 11 failed on the missing admission argument, directly reproducing the defect at `template/tests/test_leaf_workspace_admission.py:147`. |
| C3 Change | PASS | The patch centralizes primary-checkout resolution and family-specific argv shaping, then covers Plan single/batch, sign-off single/batch, Act, and publish without moving cwd or replacing env contracts (`template/src/pdca_harness/leaves.py:766`, `template/src/pdca_harness/leaves.py:922`, `template/src/pdca_harness/leaves.py:1115`, `template/src/pdca_harness/leaves.py:3408`, `template/src/pdca_harness/leaves.py:3458`, `template/src/pdca_harness/leaves.py:3555`, `template/src/pdca_harness/leaves.py:3624`). |
| C4 Verification (red→green) | PASS | Independent target rerun produced 11 pre-fix failures then 14/14 post-fix passes; the frozen gate records the same substantive transition (`gate-logs/C4-verify.log:10`, `gate-logs/C4-verify.log:175`). |
| C5 Causal adequacy | PASS | The missing workspace admission is repaired at the spawn boundary itself; no capability probe or capability-present runtime guard was added, and exclusion of unresolved/nonexistent paths is part of the stated confinement contract (`template/src/pdca_harness/leaves.py:766`, `template/src/pdca_harness/leaves.py:832`). |
| T1 Structure | PASS | Resolution, deduplication, fallback selection, and argv formatting are separated into small shared helpers, so the six call sites use one role-aware policy rather than duplicating it (`template/src/pdca_harness/leaves.py:766`, `template/src/pdca_harness/leaves.py:858`). |
| T2 Shape | PASS | Independent docs lint and site/link render passed, and frozen host-CI parity confirms the pushed-tree shape (`gate-logs/T2-docs.log:10`, `gate-logs/host-ci-docs.log:10`). |
| T3 Runtime | PASS | The driver suite completed locally; local root render cases skipped because `copier` is absent, while the readable frozen gate shows 7 root tests and 1,772 driver tests passing (`gate-logs/T3-suite.log:27`, `gate-logs/T3-suite.log:1123`). |
| T4 Contribution | N/A | The contribution artifacts do not exist at Check by design; the frozen row defers their substantive audit to the mandatory publish gate (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | PASS | Independent code review found no patch defect, and a live affected-path scan of merged history plus closed-unmerged and open PRs found no competing implementation; the negative cases exercise both lane-worktree and unrelated-directory over-admission (`template/tests/test_leaf_workspace_admission.py:314`, `template/tests/test_leaf_workspace_admission.py:331`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Human must run the patched instance's single and batch interactive flows, have each role read the named sibling checkout, and confirm no workspace-approval prompt appears and no `.pdca-wt`/unrelated directory is exposed — argv tests cannot observe the vendor CLI's actual prompting behavior (`docs/01-render-and-integrate.md:430`). |

### Advisory — code-review

# Advisory code review — issue #494

## Summary

Clean. No correctness bugs introduced by this patch, and no reuse/duplication/efficiency
issue within the diff's own scope.

## What I checked

- Grounded every call site against the target source (`template/src/pdca_harness/leaves.py`
  at the patched tree): `do_plan` (leaves.py:915-924), `do_plan_batch` (leaves.py:1097-1117),
  `run_signoff` (leaves.py:3401-3410), `run_signoff_batch` (leaves.py:3452-3462), `run_act`
  (leaves.py:3547-3558), `run_publish` (leaves.py:3609-3628) all pass `extra_argv=` through
  the new `_bundle_grant`/`_plan_grant` helpers (leaves.py:733-767 in the new block), landing
  ahead of `_invoke`'s interactive `--`/seed tail (leaves.py:611, :633-635) — matches the
  brief's citation and the existing reviewer/plan-advisory precedent it mirrors
  (leaves.py:2644-2645, :2980-2981, :3281-3282).
- Reran the new suite both on the patched tree (`template/tests/test_leaf_workspace_admission.py`,
  14/14 pass) and with `leaves.py`/the docs hunk reverted (11/14 fail, all on the same
  "spawn passed no extra_argv at all" assertion) — the red→green claimed by `C4-verify.log`
  is genuine and exercises the real call sites via a stubbed `leaves._invoke`, not a copy.
- Verified the fix for the defect the carry-forward names: `_bundle_grant` (leaves.py) has
  **no** known-targets fallback (`_grant_argv(_bundle_targets(bundles, cfg), profile)` only),
  so sign-off/Act/publish over a bundle whose brief resolves to a checkout not on disk now
  admits nothing, never the instance's other targets — confirmed both by reading the code and
  by `test_a_bundle_scoped_session_never_widens_to_the_known_targets` passing on a fixture
  built so the old bug would be visible (a resolvable known target exists, proven via Plan,
  and the four bundle-scoped spawns still admit nothing for the unresolvable bundle). The
  fallback lives only in `_plan_grant` (`_bundle_targets(...) or _known_targets(cfg)`), which
  is where criterion (ii) scopes it.
- Traced `_primary_checkout`'s resolution path (`publish._resolve_target` → guarded
  `publish._checkout_path`, `p.is_dir()` restricted) against `publish.py:548-587` — matches
  `_plan_fallback_target`'s own resolution (leaves.py:3184-3189) and deliberately does not
  reuse `_reviewer_target`/`worktree.path()`, so it structurally cannot admit a lane worktree
  (confirmed by `worktree.py`'s `_wt_dir`/`WT_SUFFIX` and `lane.py:26-28`'s serial
  `current() is None`, and by the passing `test_no_spawn_admits_a_lane_worktree`).
- Checked `_known_targets`'s two-source union (`cfg.repo_checkouts` then
  `bundle_root.glob("issue_*")` + `glob("completed/issue_*")`) against `config.py:161`
  (`repo_checkouts: dict[str, str]`) and the archive convention at `config.py:511` — the glob
  pattern and dedup-by-resolved-`Path` are consistent with how the rest of the module globs
  `issue_*` (e.g. `leaves.py:1073`, `:1095`, `:1102`, `:1129`; `publish.py:690`); no filesystem
  race or missing-`is_dir()` concern beyond what those existing call sites already accept.
- `_grant_argv`'s `if not profile.grounding_flag: return []` mirrors the existing headless
  grant sites' `if profile.grounding_flag` guard exactly, so criterion (v) (`generic` family
  byte-identical) holds by construction, not just by the one test — confirmed by
  `families.py:44/:126` (`grounding_flag: str = ""` on the generic profile) and by
  `test_generic_family_spawns_are_byte_identical` passing.
- `run_publish`'s pre-existing `profile = families.resolve(...)` (leaves.py:3615) is reused
  for the new `_bundle_grant([d], cfg, profile)` call rather than re-resolved — no duplicate
  work introduced.

## Reuse / duplication note (not a finding)

The five existing headless grant sites (`leaves.py:1947`, `:1961`, `:2644-2645`,
`:2980-2981`, `:3281-3282`) still each spell out `[flag, str(x)] if cond else None/[]` inline
rather than calling the new `_grant_argv` helper this patch adds. That is a
possible follow-on simplification, but the brief explicitly puts those five call sites out of
scope ("already do this correctly and are the pattern to mirror — do not change them"), so
retrofitting them here would be out-of-scope churn, not a defect of this diff. Not filing it
as a finding.

No other findings.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [x] Validation — fitness-to-purpose — Human must run the patched instance's single and batch interactive flows, have each role read the named sibling checkout, and confirm no workspace-approval prompt appears and no `.pdca-wt`/unrelated directory is exposed — argv tests cannot observe the vendor CLI's actual prompting behavior (`docs/01-render-and-integrate.md:430`).
- [x] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

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
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
