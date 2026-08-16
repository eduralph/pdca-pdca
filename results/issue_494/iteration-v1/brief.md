# Brief — issue 494 / interactive-leaves-are-admitted-to-what-they-must-read

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** interactive-leaves-are-admitted-to-what-they-must-read
- **Defect:** The four interactive leaves are told to read directories the harness never admits
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
- **Success criterion:** With the patch, every interactive leaf the harness spawns
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
- **Falsifiability:** RED is reachable on the base toolchain — pure-stdlib Python ≥ 3.11, no
  network, no vendor CLI — in the target checkout Do is given: the interactive leaves are
  spawned through `_invoke`, whose argv is fully determined by the leaf config and the profile,
  and the offline suites already stub a leaf command with a plain Python interpreter and inspect
  what was passed (`test_leaf_resilience.py:26-40`, `test_do_confine.py`). A case asserting that
  the sign-off / publisher / planner spawn carries the target checkout as an admitted directory
  fails today (nothing is passed at all) — that is the red — and the companion case asserting an
  unnamed directory is absent keeps a too-wide fix from passing.
  **What no automated gate can observe** is Claude Code's prompting behaviour: that the human is
  no longer asked. That is deliberately **not** the binding criterion — it is supplementary,
  human-observed evidence, recorded as a Manual-verification note at sign-off (this cycle's own
  sign-off and publish sessions read `../pdca-harness`, so the human sees it directly, and
  `pdca-pdca try <id>` gives a patched worktree to check in). The binding criterion above is the
  one the deterministic gates can and do evaluate. C4's red leg reverts `leaves.py` and keeps
  every `template/tests/*.py` hunk (`engine/scripts/run-verify.sh:214-217`), so a new test module
  earns a genuine red.
- **Invariant to restore:** Every directory the harness **instructs a leaf to read** must be
  admitted to that leaf's workspace by the harness itself, derived from the configuration that
  names it — and nothing wider. Stated over the category, not the one prompt: it binds every
  leaf the driver spawns, headless and interactive alike (the headless half already satisfies
  it, which is why this slice is a composition, not an invention), and it is one property with
  two edges — under-admission makes the harness ask the human for a decision that cannot take
  effect, on the one path that cannot be retried unattended; over-admission hands a leaf reach
  the config never granted, which is how the hand-approved rules degenerated toward
  `/home/<user>/**` in the first place. Self-test: it cannot be satisfied by guarding one leaf —
  the sign-off, publish, plan and Act spawns are four call sites and the rule is about all of
  them. Source: internal project invariant (Tier C) — the harness's own confinement doctrine,
  `leaves.py:2189-2214` and `families.py:102` (a leaf loads only the settings the harness seeds,
  #288/#290), and the grounding-grant rule already applied at `leaves.py:2495-2500` ("the
  grounding grant is only needed for a target OUTSIDE the sandbox cwd… granting the real
  checkout too would hand a read+write family the shared lane worktree for no need").
  `docs/principles.md` §5/§6 are unfilled scaffolds in this instance, so no §6 category gate
  applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with` on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md`): declaring an ordering field would split the run into waves, and a
  wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds. Ordering
  lives in the run boundaries. Known same-file neighbours, accepted by that plan: 466 and 506
  also touch `leaves.py`, in distant regions (`:1594-1631` and `:647`/`:1740` versus this
  slice's `:782`, `:3261`, `:3308`, `:3400`, `:3465`). Issue 508 (`/handoff` unusable in rendered
  instances) edits `template/.claude/`, which is why the run plan holds it to **run 3**, after
  this merges — keep that file out of scope below and the boundary is clean.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** The workspace admission of the interactive leaf spawns — planner, sign-off (single
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
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline:
  1. Read the two spawn shapes side by side —
     `template/src/pdca_harness/leaves.py:1795-1826` (`do_build`: cwd `cfg.root`, `extra` carries
     the grounding flag and the worktree) and `:2495-2500` (the reviewer: the flag and the target
     checkout) versus `:782-783`, `:3261`, `:3308`, `:3400`, `:3465-3466` (planner, sign-off,
     sign-off batch, Act, publisher: `_invoke(<leaf>, cfg.root, …)`, no `extra_argv` argument at
     all).
  2. `grep -n "additionalDirectories" -r template/` → no match: the shipped
     `template/.claude/settings.json` grants a bare `Read` and admits no directory.
  3. Live evidence in this instance: the target checkout `../pdca-harness` is a required doctor
     row, `[publisher.checkouts]` is empty, and `.claude/settings.local.json` carries both the
     one-slash rule (which cannot match an absolute path) and the two-slash rule — the residue of
     re-approving the same reads.
- **External dependencies:** none — the spawn argv is asserted in-process with the leaf command
  stubbed, so the slice builds and goes red→green on the base toolchain, with no vendor CLI and
  no network.
- **Test file:** `template/tests/test_leaf_workspace_admission.py` (new). A new module is right:
  the existing `test_settings_permissions.py` owns a different question (the *shape* of the rules
  the shipped settings file writes) and `test_do_confine.py` owns the builder's cwd confinement;
  this contract is about what every interactive spawn admits. C4's red leg keeps every
  `template/tests/*.py` hunk and reverts only `leaves.py`, so a new file earns its red exactly as
  an appended one does.
- **Citations expected:** Do must cite path:line on the target branch for every change.
  Composition cues — this is a **composition slice**: the codebase already solves this for the
  headless leaves, and Do should mirror the peer rather than invent a mechanism.
  * `leaves.py:2495-2500` — the reviewer's grant: resolve the directory, then pass
    `[profile.grounding_flag, str(dir)]` **only when the profile has a grounding flag**, with the
    comment explaining why the grant is withheld when it is not needed. That conditional is the
    shape criterion (iii) requires.
  * `leaves.py:1795-1812` — why cwd must stay `cfg.root` for a cwd-discovery family, and why the
    grant is the mechanism instead of a cwd change.
  * `leaves.py:1972-1998` (`_reviewer_target`) and `publish._checkout_path` / `_resolve_target` —
    how a bundle's target checkout is resolved from the config today; reuse that resolution, do
    not re-derive it, and remember the batch sign-off session covers several bundles
    (`SIGNOFF_BATCH_SIZE`, `flow.py:73-75`).
  * `worktree.py:104-110` (`WT_SUFFIX`, `_wt_dir`) — the single source of a lane worktree's
    path, if lane trees are admitted at all.
  The new test must not import a symbol this patch introduces at module level: C4's red leg
  reverts production first, and a module that then fails to import is recorded
  `PDCA-UNVERIFIABLE`, not red (`engine/scripts/run-verify.sh:231-234`).

  **Path convention in this brief:** every `template/…`, `tests/…` and `docs/…` path is on the
  **target branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
  `engine/…`, `pdca.toml` and `results/…` path is in **this pdca-pdca instance** (the verification
  engine and the bundles that run the cycle); they are cited to explain how the gates will judge
  this patch, and Do must not edit them.
- **Prior-art check (triage cycles):** By file path on `origin/main`:
  `template/.claude/settings.json` — `a7df381` (drop permission rules the checker never
  matches), `900d638` (the interactive exit contract), `d0456dc` (#277), `67ba7fb` (#261): the
  file has been tuned repeatedly for rule *shape* and sandbox *network* grants, never for
  directory admission. `template/src/pdca_harness/leaves.py` — the grounding grants for the
  headless leaves landed with #75/#94/#230/#419; no commit extends them to an interactive leaf.
  `gh pr list -R eduralph/pdca-harness --state open` → **no open PRs**. Open issues searched for
  `permission`: #508 (`/handoff`'s `!` block is refused by the permission checker — a different
  defect in the same neighbourhood, held to run 3) and #388 (run the publisher serially inside
  the sign-off session — an enhancement that would change *which* sessions exist, not what they
  may read). Not previously attempted, not rejected.
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on SLICING, not on quality — four of the five patched call sites are correct, tested, and worth keeping. The bundle bundles two outcomes a single rebuild cannot merge into one, and one of them is blocked on a decision that has to be authored at Plan. WHY THIS IS NOT iterate-do The brief contradicts itself. Its defect section enumerates exactly five spawn sites (`do_plan`, `run_signoff`, `run_signoff_batch`, `run_publisher`, `run_act`) and does NOT list `do_plan_batch`; its success criterion says "every interactive leaf the harness spawns". The builder implemented the enumeration, the reviewer judged against the criterion, and both readings are defensible from the text. That is a Plan defect, so a rebuild against the same brief would re-litigate it every round. Worse, the missing site cannot be closed mechanically. `_target_grant` resolves through `_reviewer_target` -> the bundle's `brief.md`. Before a brief exists there is no target to resolve, and batch Plan chooses its ids MID-session (`leaves.py:965-972`). So admitting the batch planner requires first ANSWERING the open C1 question — grant all configured checkouts (weakens least privilege), grant nothing (status quo, the planner still cannot read target source it is told to read), or something narrower. That is a policy decision, and policy belongs in a brief, not in a build. SUGGESTED SPLIT (the child shape, for `pdca-pdca split`) 1. Post-brief interactive admission — `run_signoff` (single), `run_signoff_batch`, `run_publish`, and `do_plan` where the bundle already has a brief. The target IS resolvable at spawn; this is the mechanical half. THIS ATTEMPT'S patch and `test_leaf_workspace_admission.py` are a good starting point — do not throw them away. 2. Pre-brief planner admission model — `do_plan` before a brief exists, and `do_plan_batch`. The brief for this child must DECIDE the admission policy up front (the C1 question above) and state the least-privilege rationale, then assert it. Note the current resolver deliberately returns an empty grant pre-brief (`leaves.py:2017`), and the present tests encode that empty grant as an expected success — so the child must change the expectation deliberately, not incidentally. 3. `run_act` target resolution — separable and arguably its own defect. `_reviewer_target` prefers the lane worktree (`worktree.path`), and `_wt_dir` is keyed by (primary checkout, lane slot) NOT by bundle, while `worktree.py:10-19` documents that worktree as "reset and reused per cycle" and "a warm checkout cache, never a trusted content cache". That reuse is safe for the reviewer (same cycle, runs right after its own Do) but NOT for Act, which reviews bundles frozen over many prior cycles — by then the slot has been reset for later work, so the directory admitted "for bundle d" can hold an unrelated bundle's tree. No `worktree.owner_of` check gates the admission, and the new test never reaches this branch (its fixtures have no `.pdca-wt*` directory, so only the sibling-checkout fallback is covered). Either add an ownership check or resolve Act to the sibling checkout only. Whichever children are authored, each brief must be internally consistent about which spawn sites it covers — the "every interactive leaf" phrasing versus a five-site enumeration is exactly what produced this round's contradictory verdicts.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on SLICING, not on quality — four of the five patched call sites are correct,
  tested, and worth keeping. The bundle bundles two outcomes a single rebuild cannot merge
  into one, and one of them is blocked on a decision that has to be authored at Plan.

  WHY THIS IS NOT iterate-do

  The brief contradicts itself. Its defect section enumerates exactly five spawn sites
  (`do_plan`, `run_signoff`, `run_signoff_batch`, `run_publisher`, `run_act`) and does NOT
  list `do_plan_batch`; its success criterion says "every interactive leaf the harness
  spawns". The builder implemented the enumeration, the reviewer judged against the
  criterion, and both readings are defensible from the text. That is a Plan defect, so a
  rebuild against the same brief would re-litigate it every round.

  Worse, the missing site cannot be closed mechanically. `_target_grant` resolves through
  `_reviewer_target` -> the bundle's `brief.md`. Before a brief exists there is no target to
  resolve, and batch Plan chooses its ids MID-session (`leaves.py:965-972`). So admitting the
  batch planner requires first ANSWERING the open C1 question — grant all configured
  checkouts (weakens least privilege), grant nothing (status quo, the planner still cannot
  read target source it is told to read), or something narrower. That is a policy decision,
  and policy belongs in a brief, not in a build.

  SUGGESTED SPLIT (the child shape, for `pdca-pdca split`)

  1. Post-brief interactive admission — `run_signoff` (single), `run_signoff_batch`,
     `run_publish`, and `do_plan` where the bundle already has a brief. The target IS
     resolvable at spawn; this is the mechanical half. THIS ATTEMPT'S patch and
     `test_leaf_workspace_admission.py` are a good starting point — do not throw them away.

  2. Pre-brief planner admission model — `do_plan` before a brief exists, and
     `do_plan_batch`. The brief for this child must DECIDE the admission policy up front
     (the C1 question above) and state the least-privilege rationale, then assert it. Note
     the current resolver deliberately returns an empty grant pre-brief (`leaves.py:2017`),
     and the present tests encode that empty grant as an expected success — so the child
     must change the expectation deliberately, not incidentally.

  3. `run_act` target resolution — separable and arguably its own defect. `_reviewer_target`
     prefers the lane worktree (`worktree.path`), and `_wt_dir` is keyed by (primary
     checkout, lane slot) NOT by bundle, while `worktree.py:10-19` documents that worktree
     as "reset and reused per cycle" and "a warm checkout cache, never a trusted content
     cache". That reuse is safe for the reviewer (same cycle, runs right after its own Do)
     but NOT for Act, which reviews bundles frozen over many prior cycles — by then the slot
     has been reset for later work, so the directory admitted "for bundle d" can hold an
     unrelated bundle's tree. No `worktree.owner_of` check gates the admission, and the new
     test never reaches this branch (its fixtures have no `.pdca-wt*` directory, so only the
     sibling-checkout fallback is covered). Either add an ownership check or resolve Act to
     the sibling checkout only.

  Whichever children are authored, each brief must be internally consistent about which
  spawn sites it covers — the "every interactive leaf" phrasing versus a five-site
  enumeration is exactly what produced this round's contradictory verdicts.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
