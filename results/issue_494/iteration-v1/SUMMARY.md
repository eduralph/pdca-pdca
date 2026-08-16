# Result — issue 494 / interactive-leaves-are-admitted-to-what-they-must-read

## 1. Spec (from brief.md)              ← Check verifies against THIS
- Defect / goal: The four interactive leaves are told to read directories the harness never admits
  to their workspace, so a human answering one approves the same reads **every session**, and
  the approvals never carry over. Verified on the target base:
  * the headless leaves ARE admitted — `do_build` passes the profile's grounding flag for the
    worktree (`template/src/pdca_harness/leaves.py:1802`, and `:1816` for the bundle dir), and
    the reviewer / advisory / plan-advisory leaves pass it for the target checkout
    (`:2499-2500`, `:2835-2836`, `:3136-3137`);
  * the interactive leaves are **not** — `do_plan` (`:782-783`), `run_signoff` (`:3261`),
    `run_signoff_batch` (`:3308`), `run_publisher` (`:3465-3466`) and `run_act` (`:3400`) all
    call `_invoke(<leaf>, cfg.root, …)` with **no** `extra_argv` at all. They run with cwd at
    the instance root, so everything outside it is outside the workspace.
  What they are asked to read is outside it. This instance's target is the sibling checkout
  `../pdca-harness` (a required `[[doctor.checks]]` row; `[publisher.checkouts]` is empty, so
  the sibling default resolves it): sign-off reading the target's source to understand a change,
  and publish reading the target's `docs/INTEGRATION.md`, are both out-of-workspace reads. The
  bare `Read` rule in the shipped `template/.claude/settings.json` does not cover them — a path
  outside the workspace needs the **directory admitted** (the settings form is
  `permissions.additionalDirectories`; the argv form is the family's grounding flag, already
  used above).
  The approvals the human grants do not close the gap, because of the rule form they land in.
  The accumulated `.claude/settings.local.json` holds both `"Read(/home/eddie/pdca/**)"` (one
  leading slash — resolved *relative to the project root*, so it denotes
  `<project>/home/eddie/pdca/**` and matches nothing) and `"Read(//home/eddie/.claude/**)"`
  (two — the absolute form). The first sits in the file looking like a granted permission and
  never fires. (Inferred from the two forms coexisting in a file Claude Code itself writes, plus
  the `Read(//path/**)` absolute form in its changelog — not from a controlled test; the fix
  below does not depend on that inference being right, because it admits the directory rather
  than rewriting a rule.)
  **Secondary, same root:** the headless band cannot persist a grant at all. `lanes` covers the
  unattended Do+Check band only, whose leaves run in lane worktrees
  (`worktree.py:104-110`, `<name>.pdca-wt-l<slot>`); a git worktree materialises tracked files
  only, so the untracked `settings.local.json` (`.gitignore:19`,
  `template/.gitignore.jinja:11-12`) is invisible to every other lane and dies with the
  worktree — and a sandboxed leaf is further confined by `--setting-sources project`
  (`families.py:102`, applied via `leaves._settings_scope_argv`, `:2214-2235`), which drops
  user *and* local scope by design (#290). Both halves say the same thing: a grant that depends
  on the operator's local settings file cannot work here.
- Success criterion: With the patch, every interactive leaf the harness spawns
  (planner, sign-off — single and batch, publisher, Act) is launched with the directories the
  **config already names** admitted to its workspace, derived at spawn from that config, exactly
  as the headless leaves already are:
  (i) the resolved target checkout(s) for the bundle(s) the session is about are admitted;
  (ii) **nothing wider** — a directory the config does not name (a parent like the operator's
  home, an unrelated sibling checkout, a lane worktree that this run did not create) is **not**
  admitted; the negative case is asserted, not assumed;
  (iii) a family with no grounding mechanism (the `generic` profile, whose grounding flag is
  empty) is spawned byte-identically to today — the grant is skipped, never faked;
  (iv) no other spawn property changes: cwd stays `cfg.root` (the claude family walks up from it
  to find `.claude/agents` and its hooks), the handoff/exit-contract environment, the `gh` STOP
  shim for a non-native-guard publisher, and the seed-positional contract (`--` separator, #396)
  are untouched.
  Asserted mechanically over the argv/settings the driver produces for each interactive leaf —
  which is the whole of what the harness controls.
- Repo + branch target: eduralph/pdca-harness @ main
- Scope (one logical fix) / out of scope: The workspace admission of the interactive leaf spawns — planner, sign-off (single
  and batch), publisher, Act: derive the directories from the configuration that already names
  them and admit exactly those, per spawn. **Out of scope:** `template/.claude/settings.json`
  and everything else under `template/.claude/` (issue 508 owns that file in run 3, and a
  tracked static file cannot carry instance-specific absolute paths anyway); the headless
  builder / reviewer / advisory / plan-advisory spawns, which already do this correctly and are
  the pattern to mirror; the sandbox seeding path (`_seed_sandbox_settings`, `:2239-…`), whose
  allow-list of network/exemption keys must not be widened — in particular do **not** start
  copying `permissions` from the project settings (`:2274-2281` says why); the operator's
  `.claude/settings.local.json`, which is theirs and stays untouched; `--setting-sources` /
  sandbox confinement of the interactive leaves; this instance's own `pdca.toml` or `.claude/`
  (a different repo — `docs/INTEGRATION.md` §2).

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

Review of issue 494: admit exactly the configured target checkout(s) needed by every interactive planner, sign-off, publisher, and Act leaf spawn.

| Item | Verdict | Basis |
|------|---------|-------|
| C1 Spec | NEEDS-HUMAN | Decide how a pre-brief single/batch planner identifies the exact target before spawn—granting all configured checkouts weakens least privilege, while the current resolver deliberately returns no grant until `brief.md` exists (`template/src/pdca_harness/leaves.py:2017`). |
| C2 Reproduction (red pre-fix) | PASS | The independently stashed production change leaves the new test in place and reproduces 8 failures, including absent target argv at sign-off, publish, Act, and a target-resolved planner (`gate-logs/C4-verify.log:16`). |
| C3 Change | FAIL | The batch Plan REPL remains an interactive `_invoke` with no `extra_argv`, so the promised “every interactive leaf” category is not implemented (`template/src/pdca_harness/leaves.py:972`). |
| C4 Verification (red→green) | PASS | The focused suite independently transitions from 8 failures with `leaves.py` stashed to 8 passes after `stash pop`; the frozen gate records the same red→green, but only for the covered paths (`gate-logs/C4-verify.log:100`). |
| C5 Causal adequacy | FAIL | The tests omit `do_plan_batch` and make the normal pre-brief planner’s empty grant an expected success, leaving a production planner path that is instructed to inspect target source without admission (`template/tests/test_leaf_workspace_admission.py:120`, `template/src/pdca_harness/leaves.py:972`). |
| T1 Structure | PASS | A single helper centralizes ordered, deduplicated target resolution and the patched call sites retain their existing cwd/environment contracts (`template/src/pdca_harness/leaves.py:2006`, `template/src/pdca_harness/leaves.py:3295`). |
| T2 Shape | PASS | For covered spawns, argv is target-only, ordered/deduplicated, and an empty grounding flag contributes no bytes because `_invoke` normalizes both `None` and `[]` to no extra argv (`template/src/pdca_harness/leaves.py:2026`, `template/src/pdca_harness/leaves.py:611`). |
| T3 Runtime | PASS | The full offline driver suite passed independently, and the frozen environment also reports both root and driver suites green (`gate-logs/T3-suite.log:1612`). |
| T4 Contribution | N/A | Contribution artifacts do not exist at Check by design; the substantive PR-body/tracker audit is mandatory at publish (`gate-logs/T4-contribution.log:10`). |
| T5 Judgment | NEEDS-HUMAN | Run the patched sign-off and publisher sessions against the sibling checkout and attempt the target reads; confirm Claude proceeds without a repeated permission prompt, the outcome argv tests cannot observe (`template/src/pdca_harness/leaves.py:3295`, `template/src/pdca_harness/leaves.py:3502`). |
| Validation — fitness-to-purpose | NEEDS-HUMAN | Decide whether the security/functionality tradeoff is acceptable only after resolving the pre-brief planner admission model and covering batch Plan—otherwise green covered paths still leave the stated operator workflow incomplete (`template/src/pdca_harness/leaves.py:972`). |

Prior-art evidence: exhaustive affected-path enumeration over open plus closed/merged GitHub PRs found no open or rejected attempt touching either changed path; merged history contains prior `leaves.py` work but no `test_leaf_workspace_admission.py` history.

### Advisory — code-review

# Check advisory — code review (issue #494)

Scope: correctness bugs the patch introduces, and reuse/simplification/efficiency —
distinct from the reviewer leaf's fix-adequacy lens. Grounded on
`$PDCA_TARGET/template/src/pdca_harness/{leaves.py,worktree.py,act.py,flow.py,lane.py}`.

## Findings

- NEEDS-HUMAN — `leaves.py:2006-2036` (`_target_grant`) reuses `_reviewer_target`
  (`leaves.py:1973-2003`) unchanged for `run_act` (`leaves.py:3428-3438`), but Act's
  usage is a materially different reuse context than the reviewer's. `_reviewer_target`
  prefers the **lane worktree** (`worktree.path`, `worktree.py:135-148`), and
  `worktree.py:10-19` documents that worktree as "**reset and reused** per cycle" and
  "a warm checkout cache, never a trusted **content** cache" — gate reads
  (`for_gate`) deliberately reconstruct `base + patch.diff` rather than trust what is
  on disk there. The reviewer's use of this resolution is safe because it runs
  synchronously right after that same bundle's Do (same cycle, no intervening reset).
  Act reviews `act_mod.frozen_bundles(cfg)` (`act.py:87-94`) — bundles that froze over
  **many prior cycles**, often long before the Act session runs. By the time Act's
  session is spawned, the same lane-slot worktree directory (`worktree.py:107-112`,
  keyed only by `(primary checkout, lane slot)`, not by bundle) has almost certainly
  been reset and rebuilt for other, later bundles targeting the same repo — so the
  directory `_target_grant` admits for a given frozen bundle `d` need not hold `d`'s
  patch at all; it can silently hold a different bundle's (possibly still-unreviewed,
  or even concurrently in-progress, since only the Act *session* is lock-serialized —
  `act.py`'s `act_session`/`act_due` — not Do in other lanes) tree state. No ownership
  check (`worktree.owner_of`, `worktree.py:124-132`) gates the admission. This isn't
  merely stale grounding text (as with `_reviewer_target`'s own best-effort fallback);
  it is a directory grant handed to a live interactive+human session, so the content
  the session actually reads for a historical bundle can be wrong or belong to
  unrelated work. The brief itself flags this as open ("`worktree.py:104-110` — the
  single source of a lane worktree's path, **if lane trees are admitted at all**"),
  so this is the architectural question that citation was gesturing at, now
  materialized as a concrete risk in `run_act`'s call path specifically (not
  `do_plan`/`run_signoff`/`run_publish`, which act on the SAME cycle's own bundle and
  so keep the reviewer's original same-cycle safety property). The new test
  (`test_leaf_workspace_admission.py:143-158`, `test_act_admits_the_resolved_target_checkouts`)
  does not exercise this: its fixture repos have no `.pdca-wt*` directory on disk at
  all, so `worktree.path` always misses and the test only covers the sibling-checkout
  fallback branch — the worktree-reuse path for Act is untested as well as unguarded.

- `leaves.py:2028-2032` — the loop in `_target_grant` calls `_reviewer_target(d, cfg)`
  once per bundle in `bundles` *before* checking `seen`, so for `run_signoff_batch` /
  `run_act` with several bundles resolving to the **same** target checkout, the
  worktree-less fallback branch of `_reviewer_target`
  (`leaves.py:1989-2001`) runs `git -C <p> fetch <base_remote>` once **per bundle**
  instead of once per unique resolved directory — e.g.
  `test_signoff_batch_dedupes_a_shared_target` (`test_leaf_workspace_admission.py:243-249`)
  exercises exactly this shape and would, against real repos, fire the fetch twice for
  one target. Harmless (best-effort, exit code ignored) but avoidable: resolving
  targets into a `dict[Path-or-None, ...]` keyed by the already-visited bundle's
  resolution, or simply checking `seen` before invoking `_reviewer_target`'s fetch,
  would cut the redundant network calls without changing the observable argv.

## Not flagged

- The five call sites (`do_plan`, `run_signoff`, `run_signoff_batch`, `run_act`,
  `run_publish`) all pass `bundles, cfg, profile` in the same order and reuse an
  already-resolved `profile` where one existed (`run_publish`, `leaves.py:3496,3504`)
  rather than re-resolving it — no duplicated `families.resolve` call introduced.
- `extra_argv` is threaded through the existing `_invoke` machinery unchanged
  (`leaves.py:611,619,635`): it lands ahead of the interactive seed separator/positional,
  so criterion (iv) (the `--` / seed-positional contract, #396) holds structurally, not
  just by inspection of this diff.
- The `generic`/no-grounding-flag skip (`leaves.py:2026-2027`) and the empty-grant
  path for an unresolvable target (`do_plan` pre-brief) both match the reviewer's own
  conditional shape the brief asked to mirror.

## 6. NEEDS-HUMAN — items the human must clear before sign-off
- [ ] C1 Spec — Decide how a pre-brief single/batch planner identifies the exact target before spawn—granting all configured checkouts weakens least privilege, while the current resolver deliberately returns no grant until `brief.md` exists (`template/src/pdca_harness/leaves.py:2017`).
- [ ] T5 Judgment — Run the patched sign-off and publisher sessions against the sibling checkout and attempt the target reads; confirm Claude proceeds without a repeated permission prompt, the outcome argv tests cannot observe (`template/src/pdca_harness/leaves.py:3295`, `template/src/pdca_harness/leaves.py:3502`).
- [ ] Validation — fitness-to-purpose — Decide whether the security/functionality tradeoff is acceptable only after resolving the pre-brief planner admission model and covering batch Plan—otherwise green covered paths still leave the stated operator workflow incomplete (`template/src/pdca_harness/leaves.py:972`).
- [ ] `leaves.py:2006-2036` (`_target_grant`) reuses `_reviewer_target`
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
- Outcome: iterated-to-Plan
- Iteration delta (if iterating): Rejected on SLICING, not on quality — four of the five patched call sites are correct, tested, and worth keeping. The bundle bundles two outcomes a single rebuild cannot merge into one, and one of them is blocked on a decision that has to be authored at Plan. WHY THIS IS NOT iterate-do The brief contradicts itself. Its defect section enumerates exactly five spawn sites (`do_plan`, `run_signoff`, `run_signoff_batch`, `run_publisher`, `run_act`) and does NOT list `do_plan_batch`; its success criterion says "every interactive leaf the harness spawns". The builder implemented the enumeration, the reviewer judged against the criterion, and both readings are defensible from the text. That is a Plan defect, so a rebuild against the same brief would re-litigate it every round. Worse, the missing site cannot be closed mechanically. `_target_grant` resolves through `_reviewer_target` -> the bundle's `brief.md`. Before a brief exists there is no target to resolve, and batch Plan chooses its ids MID-session (`leaves.py:965-972`). So admitting the batch planner requires first ANSWERING the open C1 question — grant all configured checkouts (weakens least privilege), grant nothing (status quo, the planner still cannot read target source it is told to read), or something narrower. That is a policy decision, and policy belongs in a brief, not in a build. SUGGESTED SPLIT (the child shape, for `pdca-pdca split`) 1. Post-brief interactive admission — `run_signoff` (single), `run_signoff_batch`, `run_publish`, and `do_plan` where the bundle already has a brief. The target IS resolvable at spawn; this is the mechanical half. THIS ATTEMPT'S patch and `test_leaf_workspace_admission.py` are a good starting point — do not throw them away. 2. Pre-brief planner admission model — `do_plan` before a brief exists, and `do_plan_batch`. The brief for this child must DECIDE the admission policy up front (the C1 question above) and state the least-privilege rationale, then assert it. Note the current resolver deliberately returns an empty grant pre-brief (`leaves.py:2017`), and the present tests encode that empty grant as an expected success — so the child must change the expectation deliberately, not incidentally. 3. `run_act` target resolution — separable and arguably its own defect. `_reviewer_target` prefers the lane worktree (`worktree.path`), and `_wt_dir` is keyed by (primary checkout, lane slot) NOT by bundle, while `worktree.py:10-19` documents that worktree as "reset and reused per cycle" and "a warm checkout cache, never a trusted content cache". That reuse is safe for the reviewer (same cycle, runs right after its own Do) but NOT for Act, which reviews bundles frozen over many prior cycles — by then the slot has been reset for later work, so the directory admitted "for bundle d" can hold an unrelated bundle's tree. No `worktree.owner_of` check gates the admission, and the new test never reaches this branch (its fixtures have no `.pdca-wt*` directory, so only the sibling-checkout fallback is covered). Either add an ownership check or resolve Act to the sibling checkout only. Whichever children are authored, each brief must be internally consistent about which spawn sites it covers — the "every interactive leaf" phrasing versus a five-site enumeration is exactly what produced this round's contradictory verdicts.
- By / date: Eduard Ralph / 2026-08-15

## 10. Act candidates (hints for the next Act review)
- Plan advisory: 0 finding(s); brief revised: no (plan-advisory-*.md)
- (empty is the common case)
