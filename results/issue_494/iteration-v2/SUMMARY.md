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

Task under review: admit exactly the intended primary checkout directories to all six interactive leaf spawns through each family’s grounding mechanism, without admitting lane worktrees or unrelated targets.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | PASS | The contract is mechanically decidable across six spawn sites, planner-only known-target fallback, exact-directory negatives, generic-family no-op, and unchanged spawn properties (`template/tests/test_leaf_workspace_admission.py:17`). |
| C2 Reproduction (red pre-fix) | PASS | Independently stashing the production hunk while retaining the regression module produced nine missing-`extra_argv` failures, while the restored tree ran all 12 tests green (`template/tests/test_leaf_workspace_admission.py:143`). |
| C3 Change | FAIL | Exact admission is violated: the shared resolver substitutes every known target when any non-planner session target is unresolved, and configured `*.pdca-wt*` paths pass through without filtering, widening access beyond the session (`template/src/pdca_harness/leaves.py:798`, `template/src/pdca_harness/leaves.py:813`). |
| C4 Verification (red→green) | PASS | The focused suite independently reproduced red→green and the complete offline driver discovery exited successfully; the exercised positive paths cover all six spawn sites (`template/tests/test_leaf_workspace_admission.py:161`). |
| C5 Causal adequacy | FAIL | Spawn argv is the correct causal seam, but the fallback/filter policy still permits unrelated or harness-owned targets, so the confinement invariant is not restored for resolution failures or configured lane-tree paths (`template/src/pdca_harness/leaves.py:803`, `template/src/pdca_harness/leaves.py:822`). |
| T1 Structure | FAIL | Planner-specific fallback semantics live inside a helper shared by sign-off, Act, and publish, erasing the role boundary that must prevent those leaves from falling back to instance-wide targets (`template/src/pdca_harness/leaves.py:813`). |
| T2 Shape | PASS | Diff checking and both frozen docs/host-CI lint-and-render audits are clean, and the call-site edits retain `cfg.root` and existing env while adding only `extra_argv` (`template/src/pdca_harness/leaves.py:3379`, `template/src/pdca_harness/leaves.py:3595`). |
| T3 Runtime | PASS | The complete offline suite passed independently, and the focused module verifies cwd/env preservation and generic-family argv behavior through production entry points (`template/tests/test_leaf_workspace_admission.py:308`). |
| T4 Contribution | N/A | `pr-description.md` is absent by design at Check; the frozen T4 log defers the substantive contribution-artifact audit to the mandatory publish rerun. |
| T5 Judgment | FAIL | The lane-tree test only traps `worktree.path()` selection and the absent-target test provides no other known target, so neither detects the two confirmed widening branches; the path-based GitHub audit found no open or closed-unmerged competing work (`template/tests/test_leaf_workspace_admission.py:265`, `template/tests/test_leaf_workspace_admission.py:298`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Confirm the real interactive CLI honors the grant without prompting or widening access: run `pdca-pdca try 494`, enter Plan and a bundle-bound sign-off/publish session, read the intended primary checkout, and verify no approval prompt while an unrelated sibling remains inaccessible—argv tests cannot observe the vendor permission UI (`template/src/pdca_harness/leaves.py:825`). |

### Advisory — code-review

# Check advisory — code review (issue #494)

## Findings

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/leaves.py:813-822` (`_admission_set`),
  used by every one of the six spawns via `_workspace_grant` (`:825-838`, called at
  `:895`, `:1088`, `:3380`, `:3427-3432`, `:3524-3528`, `:3593-3597`). The brief's
  criterion (ii) scopes the known-targets fallback to "the planner spawns, where no
  brief exists yet" (brief.md, Success criterion ii; Scope decision 3: "the answer to
  'what does the planner get before a brief exists'"). The shipped `_admission_set` is
  shared by all six and falls back to `_known_targets(cfg)` any time none of the given
  bundles' own primaries resolve — not only when the bundle list itself is empty. So a
  `run_signoff` / `run_signoff_batch` / `run_act` / `run_publish` session over a bundle
  whose brief names a repo not checked out on this host (or an otherwise-unresolvable
  target) does not admit nothing, as criterion (i)/(iv) requires for those five spawns —
  it silently falls through to the instance's *other*, unrelated known checkouts
  (`[publisher.checkouts]` ∪ what every other brief resolves to), which is exactly the
  over-admission the brief's invariant forbids for a session that already has a bundle
  to be about. `test_a_target_that_is_not_on_disk_is_not_admitted`
  (`template/tests/test_leaf_workspace_admission.py:510-517`) exercises this path for
  `run_signoff` but happens to pass only because that fixture's instance has no *other*
  known target either (empty `checkouts=`, and the one brief in the bundle_root is the
  unresolvable one itself) — it does not actually distinguish "admits nothing" from
  "falls back to known-targets, which is currently also empty." A fixture with a second,
  resolvable bundle/checkout present alongside the unresolvable one would show the
  fallback leaking that unrelated checkout into the sign-off/act/publish session. Worth
  a human/builder look: either gate the fallback on `not bundles` (true only for the
  CSV/default Plan-batch case) plus a separate "planner" flag, or split `_admission_set`
  into a resolve-only variant (signoff/act/publish/batch) and a
  resolve-or-known-targets variant (Plan single/batch only).

- `template/src/pdca_harness/leaves.py:756-767` (`_primary_checkout`) duplicates the
  resolve-primary logic already in `_plan_fallback_target`
  (`template/src/pdca_harness/leaves.py:3155-3161`, pre-existing) — both do
  `publish._resolve_target(d)` → `publish._checkout_path(cfg, repo_spec)` inside the
  same try/except-Exception shape, differing only in the existence test at the end
  (`p.is_dir()` vs `(primary / ".git").exists()`). Minor reuse opportunity, not a
  defect: `_plan_fallback_target` could call `_primary_checkout(d, cfg)` and layer its
  own `.git` check on top, dropping one of the two near-identical blocks. Non-blocking —
  flagging for awareness only, since the new function is what a future editor is more
  likely to find and reuse.

## Everything else checked clean

- All six call sites (`leaves.py:895`, `:1088`, `:3380`, `:3427-3432`, `:3524-3528`,
  `:3593-3597`) pass `extra_argv=` through the existing `_invoke` parameter
  (`:607-611`), landing before the interactive `--`/seed tail exactly as the headless
  grants do — no change to `cwd`, to the handoff env, or to the publish `gh`-shim
  merge (`run_publish` reuses its already-resolved `profile` rather than re-deriving
  it, `leaves.py:3583`/`:3597` — a good small reuse, not a duplicate call).
- `_workspace_grant` (`:825-838`) mirrors the reviewer's own
  `if not profile.grounding_flag: return []` / `[flag, str(p)]` shape exactly, so the
  `generic` family (empty `grounding_flag`) is spawned with `extra_argv=[]`, which
  `_invoke` folds into a byte-identical argv (`:611`) — criterion (v) holds.
  `_primary_checkout` never routes through `worktree.path()` / `_reviewer_target`
  (confirmed: it only calls `publish._resolve_target` + `publish._checkout_path`,
  the sibling/`[publisher.checkouts]` convention), so criterion (iii) — never a lane
  worktree — holds structurally, not just by the one test that exercises it.
  `publish._resolve_target`/`field()` raising on a missing `brief.md` (unplanned
  bundle) is caught by `_primary_checkout`'s broad `except Exception`, so `do_plan`'s
  pre-brief call site degrades correctly to the known-targets fallback rather than
  raising.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] Validation — fitness-to-purpose — Confirm the real interactive CLI honors the grant without prompting or widening access: run `pdca-pdca try 494`, enter Plan and a bundle-bound sign-off/publish session, read the intended primary checkout, and verify no approval prompt while an unrelated sibling remains inaccessible—argv tests cannot observe the vendor permission UI (`template/src/pdca_harness/leaves.py:825`).
- [ ] `template/src/pdca_harness/leaves.py:813-822` (`_admission_set`),
- [ ] leaf produced no usable verdict (needs a human) — plan-advisory leaf 'plan-reviewer' did not produce findings (produced no artifact); re-run it or adjudicate by hand.

## 7. Proven / not proven
- Proven by which oracle: gates overall = pass (stub oracles).
- Unproven / needs manual run: anything flagged in §6.

## 8. Ready-to-ship attachments
- patch.diff
- tracker-comment.md     (ALWAYS, every tracker item)
- build-notes.md         (builder rationale — for the human, not the reviewer)

## 9. Check sign-off                     ← human completes Check here
- Disposition confirmed / overridden:
- Outcome: iterated-to-Do
- Iteration delta (if iterating): Rejected on the defect both review lenses converged on (reviewer C3/C5/T1/T5 FAIL + advisory code-review NEEDS-HUMAN [impl]): `_admission_set`'s final `return dirs or _known_targets(cfg)` (leaves.py:889-898) applies the known-targets fallback to ALL SIX spawns, but the brief scopes it to the planner only — criterion (ii), "the planner spawns, where no brief exists yet", and Scope decision 3. As shipped, a run_signoff / run_signoff_batch / run_act / run_publish session over a bundle whose brief names a repo not checked out on this host does not admit nothing, as criteria (i)/(iv) require: it silently admits the instance's OTHER, unrelated checkouts ([publisher.checkouts] union every other brief's resolved primary). That is precisely the over-admission the invariant forbids for a session that already has a bundle to be about. What to change next: - Scope the fallback to Plan. Either gate it on `not bundles` plus an explicit planner flag, or split `_admission_set` into a resolve-only variant (signoff single/batch, act, publish) and a resolve-or-known-targets variant (do_plan, do_plan_batch). The second is preferable: it puts the role boundary in the type, which is the T1 finding. - Fix the blind fixture. `test_a_target_that_is_not_on_disk_is_not_admitted` (test_leaf_workspace_admission.py:510-517) passes by accident — its instance has no other known target either (empty `checkouts=`, and the single brief in the bundle_root is the unresolvable one), so it cannot distinguish "admits nothing" from "fell back to a known-targets list that happens to be empty". Add a second, RESOLVABLE bundle/checkout alongside the unresolvable one and assert the sign-off spawn admits nothing; that fixture is what turns this from a passing test into a real negative. Keep as-is — do not re-do this part: the seam is right and the slice is correctly sized. All six call sites are wired correctly through the existing `_invoke(extra_argv=)` parameter, landing before the interactive `--`/seed tail; cwd stays `cfg.root` and the handoff env is untouched (criterion vi). `_primary_checkout` deliberately avoids `_reviewer_target`/`worktree.path()`, so criterion (iii) — never a lane worktree — holds structurally rather than by one test. `_workspace_grant`'s empty-`grounding_flag` early return gives the `generic` family a byte-identical argv (criterion v). The `run_publish` profile reuse is good. This is one wrong conditional and one blind fixture, not a re-design.
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
