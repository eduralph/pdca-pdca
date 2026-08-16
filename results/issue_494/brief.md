# Brief — issue 494 / admit-interactive-leaves-to-the-checkout-they-are-told-to-read

> The Plan artifact (docs 02 §PLAN). Do reads ONLY this file.

- **Slug:** admit-interactive-leaves-to-the-checkout-they-are-told-to-read
- **Defect:** The harness tells its **interactive** leaves to read the target checkout, then
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
- **Success criterion:** With the patch applied, **each of the six interactive spawns named
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
- **Falsifiability:** RED is reachable on the base toolchain, offline, in the target checkout Do
  is given. Every one of the six spawns funnels through `_invoke`, whose argv is fully determined
  by the leaf config and the family profile (`leaves.py:607-611` — `extra_argv` is appended to
  `argv` before the interactive `--`/seed tail), and the shipped offline suite already stubs
  `leaves._invoke` and inspects what was passed (`template/tests/test_leaf_resilience.py`,
  `test_do_confine.py`). A case asserting that the sign-off / publish / planner spawn carries the
  resolved checkout as an admitted directory **fails today, because nothing is passed at all** —
  that is the red. The companion negatives (iii)/(iv)/(v) keep a too-wide fix from passing.
  Gate-evaluability confirmed against the harness that will run it, not just the repo:
  `engine/scripts/run-verify.sh:214-218` reverts only the production hunks
  (`--exclude=tests/* --exclude=template/tests/*`), so a **new** module under `template/tests/`
  earns a genuine red; `run_tests` (`:173-192`) executes it as
  `cd template && PYTHONPATH=src python3 -m unittest tests.<module>` — plain stdlib, no `cfg`
  flag, no feature gate, no vendor CLI, so it cannot vacuously report `0 tests`. The previous
  attempt (`iteration-v1/`) empirically passed C4 with exactly this file shape.
  **What no automated gate can observe** is Claude Code's prompting behaviour — that the human is
  no longer asked. That is deliberately **not** the binding criterion; it is supplementary,
  human-observed evidence, and this cycle's own sign-off and publish sessions read
  `../pdca-harness`, so the human sees it directly (`pdca-pdca try 494` gives a patched worktree
  to check in).
- **Invariant to restore:** Every directory the harness **instructs a leaf to read** must be
  admitted to that leaf's workspace **by the harness**, derived from what the configuration and
  the bundle's own artifacts already name — and nothing wider. Stated over the category, not the
  one prompt: it binds every leaf the driver spawns, headless and interactive alike, which is why
  this slice is a **composition** of a pattern the codebase already applies rather than an
  invention. It is one property with two edges, and both are live here: **under-admission** makes
  the harness ask the human for a decision that cannot take effect, on the one path that cannot
  be retried unattended; **over-admission** hands a leaf reach the config never granted — which
  is exactly how the hand-approved rules degenerated toward `/home/<user>/**`, and exactly what
  the codebase already refuses at `leaves.py:2495-2500` ("granting the real checkout too would
  hand a read+write family the shared lane worktree for no need") and at
  `_plan_fallback_target` (`:3023-3038`, #301 rounds 7/8). Self-test: it cannot be satisfied by
  guarding one leaf — the six spawns are six call sites and the rule is about all of them.
  Source: internal project invariant (Tier C) — the harness's own confinement doctrine
  (`families.py:100-102`, `leaves.py:2495-2500`, `:3029-3035`). `docs/principles.md` §5/§6 are
  unfilled scaffolds in this instance, so no §6 category gate applies.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Ordering note:** No `Depends on` / `Conflicts with`, on purpose. This bundle is one of the
  nine ids of run 2 of the 0.60 bug phase, sequenced by the human as a **single wave**
  (`plan-0.60-bug-order.md:51-61`): declaring an ordering field would split the run into waves,
  and a wave > 0 bundle in this instance is what issue 474 (also in this run) false-reds.
  Ordering lives in the run boundaries. Known same-file neighbours, accepted by that plan: 466
  and 506 also touch `leaves.py`, in distant regions from this slice's `:781`, `:971`, `:3260`,
  `:3307`, `:3399`, `:3463`. Issue 508 edits `template/.claude/`, which is why the run plan holds
  it to run 3 — that directory is out of scope below, so the boundary stays clean.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** The workspace admission of the six interactive leaf spawns — `do_plan`,
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
- **Repro instruction:** On a clean checkout of the target base (`origin/main` of
  eduralph/pdca-harness), offline:
  1. Read the two spawn shapes side by side — `template/src/pdca_harness/leaves.py:1795-1816`
     (`do_build`: cwd `cfg.root`, `extra` carries the grounding flag) and `:2491-2500` (the
     reviewer: the flag and its resolved target) **versus** `:781-783`, `:971-972`, `:3260-3261`,
     `:3307-3309`, `:3399-3401`, `:3463-3466` — six `_invoke(<leaf>, cfg.root, …)` calls with no
     `extra_argv` argument at all.
  2. `grep -rn "additionalDirectories" template/` → no match: the shipped settings file grants a
     bare `Read` and admits no directory.
  3. Live evidence in this instance: `../pdca-harness` is a required doctor row,
     `[publisher.checkouts]` is empty, `.claude/settings.local.json` carries both the one-slash
     rule (which cannot match an absolute path) and the two-slash rule, and
     `/home/eddie/pdca/pdca-harness.pdca-wt` is an unowned worktree at `645c315` — the directory
     a `_reviewer_target`-based fix would admit instead of the real checkout.
- **External dependencies:** none
  The spawn argv is asserted in-process with the leaves._invoke helper stubbed, so the slice
  builds and goes red→green on the base toolchain (pure-stdlib Python ≥ 3.11 + git), with no
  vendor CLI, no live service and no network.
- **Test file:** `template/tests/test_leaf_workspace_admission.py` (new). A new module is right:
  `test_settings_permissions.py` owns a different question (the *shape* of the rules the shipped
  settings file writes) and `test_do_confine.py` owns the builder's cwd confinement; this
  contract is about what every interactive spawn admits. C4's red leg keeps every
  `template/tests/*.py` hunk and reverts only `leaves.py`
  (`engine/scripts/run-verify.sh:214-218`), so a new file earns its red exactly as an appended
  one would. The module **must not import at module level any symbol this patch introduces**:
  the red leg reverts production first, and a module that then fails to import is recorded
  `PDCA-UNVERIFIABLE`, not red (`run-verify.sh:231-234`). Stub `leaves._invoke` and assert over
  the captured `extra_argv`, as the previous attempt did.
  Cover, at minimum: one positive per spawn site (all six); the batch cases admitting each
  distinct target exactly once; criterion (iii) with a `*.pdca-wt` directory present on disk;
  criterion (iv) with an unrelated existing checkout the config and briefs never name;
  criterion (v) on the `generic` family (argv byte-identical); criterion (vi) cwd stays
  `cfg.root`.
- **Citations expected:** Do must cite `path:line` on the target branch for every change.
  **Composition cues — this is a composition slice**: the codebase already solves both halves of
  this, and Do should mirror the peers rather than invent a mechanism.
  * `leaves.py:2491-2500` — the reviewer's grant: resolve the directory, then pass
    `[profile.grounding_flag, str(dir)]` **only when the profile has a grounding flag**. That
    conditional is the shape criterion (v) requires. Mirror it.
  * `leaves.py:3023-3045` (`_plan_fallback_target`) — the peer that already decided "never the
    lane worktree" for a non-Do leaf, and the guarded `publish._resolve_target` →
    `publish._checkout_path` resolution to copy. Its round-8 caveat (never expose the operator's
    primary checkout to a *sandboxed, unattended, read-WRITE* leaf) does **not** transfer here
    and must not be applied: these six leaves are interactive, run in the human's own terminal
    with the human present, and `publish` already runs `git -C <primary> checkout/apply/commit/push`
    against that very checkout (`publish.py:439-448`) — the primary checkout *is* the interactive
    band's working surface. Say so in `build-notes.md`; the reviewer will ask.
  * `leaves.py:1795-1816` — why cwd must stay `cfg.root` for a cwd-discovery family, and why the
    grant, not a cwd change, is the mechanism.
  * `leaves.py:607-611` and `:622-639` — where `extra_argv` lands in the argv and why it is safe
    ahead of the interactive `--`/seed tail (#396).
  * `worktree.py:104-112` (`WT_SUFFIX`, `_wt_dir`) and `lane.py:26-28` (`current()` is `None`
    serially) — the single source of a lane-worktree path, for criterion (iii)'s negative.
  * **One prior-attempt file you MAY open** (a narrow, deliberate exception to reading
    `brief.md` only): `$PDCA_BUNDLE/iteration-v1/patch.diff` — the previous attempt, rejected on
    slicing, not quality. Four of its five call sites and much of its test module are directly
    reusable. **Its `_target_grant` resolver is the part that must change**: it routes through
    `_reviewer_target` and so admits the stale unowned worktree (decision 2), and it covers five
    sites, not six (decision 1). Reuse the good half; do not re-ship the resolver.
- **Prior-art check (triage cycles):** By file path on `origin/main` @ `acb214a`.
  `template/src/pdca_harness/leaves.py` — the grounding grants for the headless leaves landed
  with `861ef22`/`684f556` (#136), `2ee991e`/`e991a71` (family profiles), `93cfcfb` (bundle dir
  for a sandboxed builder), `ed9bc91`/`915a1ab` (#301 rounds 7/8 — the plan-advisory's fallback
  target, "never a lane worktree"), `a1c9d7a` (#419, the writable reviewer target). **No commit
  extends a grant to any interactive leaf.** `template/.claude/settings.json` — `a7df381`,
  `900d638`, `d0456dc` (#277), `67ba7fb` (#261): tuned repeatedly for rule *shape* and sandbox
  *network* grants, never for directory admission; `grep -rn "additionalDirectories" template/`
  is empty. `gh pr list -R eduralph/pdca-harness --state open` → **no open PRs**. Related open
  issues: #508 (`/handoff`'s `!` block refused by the permission checker — a different defect in
  the same neighbourhood, held to run 3) and #388 (run the publisher inside the sign-off session
  — changes *which* sessions exist, not what they may read). Issue 494 itself is still OPEN.
  Not previously merged, not rejected — the one prior attempt is this bundle's own
  `iteration-v1/`, returned to Plan on slicing.
- **Disposition hint:** likely-fix

**Path convention in this brief:** every `template/…` and `docs/…` path is on the **target
branch** (eduralph/pdca-harness @ main) — those are the files Do reads and edits. Every
`engine/…`, `pdca.toml`, `plan-0.60-bug-order.md` and `results/…` path is in **this pdca-pdca
instance** (the verification engine and the bundles that run the cycle); they are cited to
explain how the gates will judge this patch, and Do must not edit them.

**One decision for sign-off to confirm** (recorded here rather than left silent): the previous
sign-off suggested a **three-way split**. It is authored as **one slice** instead, because its
own stated blocker — "policy belongs in a brief, not in a build" — was a Plan decision, and the
three decisions in Scope above make it. The sizer agreed the slice is one outcome
(`sizing.json`: `band: ok`, one independent outcome, confidence high), and the previous attempt
passed every gate at 14.6 KB across 2 files. If sign-off still prefers the split, the seam is
between decision 3 (the planner's pre-brief fallback) and the rest.

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 2 — carry-forward (from the previous attempt)
- Sign-off rationale: Rejected on the defect both review lenses converged on (reviewer C3/C5/T1/T5 FAIL + advisory code-review NEEDS-HUMAN [impl]): `_admission_set`'s final `return dirs or _known_targets(cfg)` (leaves.py:889-898) applies the known-targets fallback to ALL SIX spawns, but the brief scopes it to the planner only — criterion (ii), "the planner spawns, where no brief exists yet", and Scope decision 3. As shipped, a run_signoff / run_signoff_batch / run_act / run_publish session over a bundle whose brief names a repo not checked out on this host does not admit nothing, as criteria (i)/(iv) require: it silently admits the instance's OTHER, unrelated checkouts ([publisher.checkouts] union every other brief's resolved primary). That is precisely the over-admission the invariant forbids for a session that already has a bundle to be about. What to change next: - Scope the fallback to Plan. Either gate it on `not bundles` plus an explicit planner flag, or split `_admission_set` into a resolve-only variant (signoff single/batch, act, publish) and a resolve-or-known-targets variant (do_plan, do_plan_batch). The second is preferable: it puts the role boundary in the type, which is the T1 finding. - Fix the blind fixture. `test_a_target_that_is_not_on_disk_is_not_admitted` (test_leaf_workspace_admission.py:510-517) passes by accident — its instance has no other known target either (empty `checkouts=`, and the single brief in the bundle_root is the unresolvable one), so it cannot distinguish "admits nothing" from "fell back to a known-targets list that happens to be empty". Add a second, RESOLVABLE bundle/checkout alongside the unresolvable one and assert the sign-off spawn admits nothing; that fixture is what turns this from a passing test into a real negative. Keep as-is — do not re-do this part: the seam is right and the slice is correctly sized. All six call sites are wired correctly through the existing `_invoke(extra_argv=)` parameter, landing before the interactive `--`/seed tail; cwd stays `cfg.root` and the handoff env is untouched (criterion vi). `_primary_checkout` deliberately avoids `_reviewer_target`/`worktree.path()`, so criterion (iii) — never a lane worktree — holds structurally rather than by one test. `_workspace_grant`'s empty-`grounding_flag` early return gives the `generic` family a byte-identical argv (criterion v). The `run_publish` profile reuse is good. This is one wrong conditional and one blind fixture, not a re-design.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Rejected on the defect both review lenses converged on (reviewer C3/C5/T1/T5 FAIL +
  advisory code-review NEEDS-HUMAN [impl]): `_admission_set`'s final
  `return dirs or _known_targets(cfg)` (leaves.py:889-898) applies the known-targets
  fallback to ALL SIX spawns, but the brief scopes it to the planner only — criterion (ii),
  "the planner spawns, where no brief exists yet", and Scope decision 3. As shipped, a
  run_signoff / run_signoff_batch / run_act / run_publish session over a bundle whose brief
  names a repo not checked out on this host does not admit nothing, as criteria (i)/(iv)
  require: it silently admits the instance's OTHER, unrelated checkouts
  ([publisher.checkouts] union every other brief's resolved primary). That is precisely the
  over-admission the invariant forbids for a session that already has a bundle to be about.

  What to change next:
  - Scope the fallback to Plan. Either gate it on `not bundles` plus an explicit planner
    flag, or split `_admission_set` into a resolve-only variant (signoff single/batch, act,
    publish) and a resolve-or-known-targets variant (do_plan, do_plan_batch). The second is
    preferable: it puts the role boundary in the type, which is the T1 finding.
  - Fix the blind fixture. `test_a_target_that_is_not_on_disk_is_not_admitted`
    (test_leaf_workspace_admission.py:510-517) passes by accident — its instance has no other
    known target either (empty `checkouts=`, and the single brief in the bundle_root is the
    unresolvable one), so it cannot distinguish "admits nothing" from "fell back to a
    known-targets list that happens to be empty". Add a second, RESOLVABLE bundle/checkout
    alongside the unresolvable one and assert the sign-off spawn admits nothing; that fixture
    is what turns this from a passing test into a real negative.

  Keep as-is — do not re-do this part: the seam is right and the slice is correctly sized.
  All six call sites are wired correctly through the existing `_invoke(extra_argv=)`
  parameter, landing before the interactive `--`/seed tail; cwd stays `cfg.root` and the
  handoff env is untouched (criterion vi). `_primary_checkout` deliberately avoids
  `_reviewer_target`/`worktree.path()`, so criterion (iii) — never a lane worktree — holds
  structurally rather than by one test. `_workspace_grant`'s empty-`grounding_flag` early
  return gives the `generic` family a byte-identical argv (criterion v). The `run_publish`
  profile reuse is good. This is one wrong conditional and one blind fixture, not a
  re-design.
- Full previous attempt preserved in `iteration-v2/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
