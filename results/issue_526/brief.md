# Brief — issue 526 / plan-advisory-truthful-when-sandbox-cannot-start

> The Plan artifact (docs 02 §PLAN). Human-authored. Do reads ONLY this file.

- **Slug:** plan-advisory-truthful-when-sandbox-cannot-start
- **Defect:** On a host that denies unprivileged user namespaces (Ubuntu's default
  `kernel.apparmor_restrict_unprivileged_userns = 1`), the `[[leaves.plan_advisory]]` leaf
  produces nothing, and its empty result is reported as a substantive failure. Three facts
  combine. (1) It is the only leaf the harness runs with the vendor sandbox turned ON and
  fail-closed: `_seed_plan_sandbox_settings`
  (`template/src/pdca_harness/leaves.py:2656-2688`) writes
  `{"sandbox": {"enabled": true, "allowUnsandboxedCommands": false, "failIfUnavailable": true}}`
  and the runner adds `--setting-sources project` (`leaves.py:3373-3378`). (2) On such a host the
  sandbox (bubblewrap) cannot start, so every Bash call fails, even `echo hello`. (3) Bash is the
  leaf's only way to write its file: the template argv grants `Read,Bash,Grep,Glob`
  (`template/pdca.toml.jinja:750`), the agent's frontmatter says `tools: Read, Bash, Grep, Glob`
  (`template/.claude/agents/plan-reviewer.md.jinja:8`), and the prompt requires writing
  `plan-advisory-<id>.md` (`leaves.py:3139-3160`). The leaf then exits 0 with no file, so the runner
  files "produced no artifact" (`leaves.py:3394`) at the default `_FAIL_SUBSTANTIVE`
  (`leaves.py:2768`, `:3407-3408`). `_unavailable_classification` (`leaves.py:2810-2840`) marks
  that as the needs-a-human class, and the §6 text tells the human it is "not an infra blip",
  which is the opposite of the truth. On top of that, `plan-advisory-benefit.json`
  (`leaves.py:3514-3520`) records only `findings`/`revised`, so an unavailable run is written as
  `findings: 0, revised: false`, the same record as a review that ran and found nothing. The
  issue counts nine such records in pdca-pdca, which would wrongly convict the feature at an
  Act review.
- **Success criterion:** With the plan-advisory runner driven through `leaves.run_plan_advisory`,
  on a leaf run where the vendor sandbox cannot start (the leaf exits 0, no Bash command ran):
  (a) the bundle's `plan-advisory-<id>.md` is not classified as the needs-a-human class. It carries
  an infra `pdca:leaf-status` marker, and its text names the unavailable vendor sandbox as the
  cause, so the operator can act on it; (b) `plan-advisory-benefit.json` records that this leaf's
  review did not complete, in a way `act` / an Act reader can tell apart from "ran, 0 findings";
  (c) the reviewer's findings still reach the bundle on such a host, by a delivery route that does
  not depend on Bash. When that works, the artifact is the leaf's real review, and it still states
  that Bash was unavailable. (d) The fail-closed boundary is unchanged: the seeded policy still
  has `enabled: true`, `allowUnsandboxedCommands: false`, `failIfUnavailable: true` and no Check
  grants, so `test_claude_plan_reviewer_gets_a_minimal_failclosed_sandbox`
  (`template/tests/test_plan_advisory.py:110-138`) stays green. The leaf still cannot modify the
  bundle's real `brief.md` or the pinned target. (e) A leaf that ran with a working sandbox and
  wrote nothing is still classified as it is today. The fix narrows the substantive class; it
  does not relabel every empty result as infra.
- **Falsifiability:** RED offline for (a) and (b): today a leaf that exits 0 without writing is
  filed at `_FAIL_SUBSTANTIVE` with the human marker, and the benefit record has no completion
  field. The test must fail on an assertion about the placeholder's marker/text and the benefit
  record. It must NOT fail only because it mocks or imports a symbol the fix adds; a red that comes
  from an AttributeError proves nothing. So create the "sandbox cannot start" condition at an
  outside boundary that already exists before the fix. Examples: a stand-in executable named in
  the leaf's `argv` that behaves as the vendor CLI does on such a host (exits 0, writes no
  artifact, prints the sandbox failure), or a host tool faked on `PATH`. Do not patch a function
  the fix introduces. If no such boundary fits the chosen mechanism, say so in build-notes; the
  human then weighs the C4 result knowing that. RED live for (a)-(c) on THIS planning host:
  `unshare -Ur true` → `write failed /proc/self/uid_map: Operation not permitted`, and
  `sysctl kernel.apparmor_restrict_unprivileged_userns` = 1, both checked during Plan. The issue's
  reproduction (seed the fail-closed settings in a temp dir, run
  `claude -p --agent plan-reviewer --permission-mode acceptEdits --allowedTools Read,Bash,Grep,Glob --setting-sources project …`)
  runs here. Offline, (c) can only be shown against Do's delivery mechanism (e.g. a faked leaf
  that uses the new route while Bash is dead), so the live run on this host is (c)'s real evidence.
  Record it in build-notes as a supplementary check. A code-read is not a substitute.
- **Invariant to restore:** A leaf's reported outcome matches what actually happened to it. An
  advisory result that the environment prevented is classified as infra, never as "substantive —
  do not assume an infra blip". A confinement the harness itself imposes may degrade what the
  leaf can do, but must not silently remove its only way to deliver its result. Source (internal,
  Tier C): the #278 rule in `_unavailable_classification`'s docstring (`leaves.py:2814-2818`: an
  infra failure must not present as a clean pass, and the operator must not have to hand-annotate
  "infra, not substance"), and the "degrade the feature, never the boundary" rule in
  `_seed_plan_sandbox_settings`'s docstring (`leaves.py:2670-2673`; there it is said about a failed seed write, and this brief applies the same rule to a seed that landed but cannot start). Self-test: fixing only the
  classification (a) leaves the feature dead on the default Ubuntu host and fails (c). Adding only
  a write route leaves a sandbox-less run silently degraded and fails (a)/(b). Neither alone passes.
- **Repo + branch target:** eduralph/pdca-harness @ main
- **Depends on:**
- **Conflicts with:**
- **Ordering note:** Run 4 of `plan-0.60-bug-order.md`, after #480's `do_plan` change (merged,
  60634b4). Its files (`leaves.py` plan-advisory runner, the plan-reviewer agent/prompt, the
  `pdca.toml.jinja` example row, `test_plan_advisory.py`) do not overlap with 481 / 508 / 528.
  Doctor preflight for "a configured leaf needs a sandbox this host cannot start" belongs to #452
  (0.61) and is not part of this slice.
- **Surfaces:** data
- **Difficulty:** medium
- **Scope:** Make the plan-advisory leaf's outcome truthful on a host where the vendor sandbox
  cannot start: the review is delivered when the model can still produce it, and when it cannot,
  the placeholder and the benefit record say "environment", not "substantive". The mechanism is
  Do's call; the issue lists options without choosing one. The only rule on the fix shape: the
  boundary in (d) stays. / out of scope: relaxing or dropping the fail-closed seed
  (`failIfUnavailable`, `allowUnsandboxedCommands`); Check-side leaves and their
  `_seed_sandbox_settings` path; the `doctor` preflight (#452); making `unshare` work on the host;
  back-filling the nine existing pdca-pdca placeholders.
- **Repro instruction:** On this host (userns restricted, verified above): in a temp dir, copy
  `<instance>/.claude/agents`, write the fail-closed `.claude/settings.json` shown in Defect, and
  run the issue's `claude -p --agent plan-reviewer …` command asking it to write
  `plan-advisory-plan-reviewer.md`. It exits 0, no file is written, and it reports that Bash is
  non-functional. Offline, run `leaves.run_plan_advisory` with a `command`-mode claude plan leaf
  whose run exits 0 without writing the artifact (the fixture shape of
  `test_plan_advisory.py:110-138`). The placeholder carries the human leaf-status marker and the
  benefit record says `findings: 0, revised: false`.
- **External dependencies:** none for the gates (offline suite). The supplementary live check needs a host with unprivileged user namespaces denied (this planning host qualifies) and the Claude CLI the instance already runs its leaves on.
- **Test file:** template/tests/test_plan_advisory.py (append; the peer tests are in the
  `PlanAdvisory` class, `:51`)
- **Citations expected:** Do must cite path:line on `origin/main` for every change. Peers to
  mirror: how `_failure_class` / `_unavailable_classification` (`leaves.py:2771-2840`) turn a
  failure into a leaf-status marker, which is the same signal `assemble` uses for §6, and how the
  existing test fakes the leaf and reads the seeded settings
  (`test_plan_advisory.py:110-138`).
- **Prior-art check (triage cycles):** by path,
  `git -C ../pdca-harness log --oneline origin/main -S _seed_plan_sandbox_settings -- template/src/pdca_harness/leaves.py`:
  915a1ab (#301 round 8, introduced the fail-closed seed); plan-reviewer agent history: b8174f7,
  ed0e585 (#301). The latest plan-advisory change, 5078c06 (#480), is about which briefs get
  reviewed, not the sandbox or classification. Closed-unmerged PRs touching `leaves.py`,
  `plan-reviewer.md.jinja`, `test_plan_advisory.py`: none. Open PRs: none. Related open issue:
  #452 (doctor preflight, 0.61).
- **Disposition hint:** likely-fix

## STOP discipline

Draft only until Check sign-off. Pushing to a feature/draft branch and opening a
draft PR MAY happen during the cycle (useful for CI feedback). The PR MUST NOT be
marked ready before sign-off accepts.

## Iteration 1 — carry-forward (from the previous attempt)
- Sign-off rationale: Put the "if Bash fails, use Write" condition into the prompt text itself — today it is a Python comment (leaves.py `_plan_advisory_prompt`), so the model never sees the condition and every run, healthy or not, is told to claim Bash was unavailable. Classify as sandbox-infra only on evidence the sandbox actually failed to start (tool-error text such as apply-seccomp / bwrap / uid_map / setgroups, or "sandbox ... could not start/initialize"), not the bare word "sandbox" — a healthy run saying "the sandbox is working normally" must stay classified as today (criterion e). Add a test for exactly that case. Make the red-before-fix test assert on the literal "sandbox-empty" / marker text and the benefit record, so pre-fix it fails a real assertion, not an AttributeError on the new LEAF_STATUS_SANDBOX constant (the brief's Falsifiability rule). Keep: the Write delivery route + agent frontmatter change, the `completed` benefit field, and the live-check evidence approach. Optional cleanup: share one artifact-status loop between `_plan_findings` and `_plan_advisory_completed`.
- Sign-off session carry-forward (captured live, before §9 flattened it):
  Put the "if Bash fails, use Write" condition into the prompt text itself — today it is a Python comment (leaves.py `_plan_advisory_prompt`), so the model never sees the condition and every run, healthy or not, is told to claim Bash was unavailable.
  Classify as sandbox-infra only on evidence the sandbox actually failed to start (tool-error text such as apply-seccomp / bwrap / uid_map / setgroups, or "sandbox ... could not start/initialize"), not the bare word "sandbox" — a healthy run saying "the sandbox is working normally" must stay classified as today (criterion e). Add a test for exactly that case.
  Make the red-before-fix test assert on the literal "sandbox-empty" / marker text and the benefit record, so pre-fix it fails a real assertion, not an AttributeError on the new LEAF_STATUS_SANDBOX constant (the brief's Falsifiability rule).
  Keep: the Write delivery route + agent frontmatter change, the `completed` benefit field, and the live-check evidence approach. Optional cleanup: share one artifact-status loop between `_plan_findings` and `_plan_advisory_completed`.
- Full previous attempt preserved in `iteration-v1/` (patch.diff, build-notes.md, SUMMARY.md, check-*).
- Address the above; do NOT re-attempt the rejected approach unchanged. Satisfy the brief's Success criterion (the end result).
