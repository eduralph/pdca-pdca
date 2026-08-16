## Summary
**User impact:** Every interactive session — planning, sign-off, publishing, act review — opened by asking you to approve reading the checkout it had just been instructed to read. The same paths, one prompt at a time, at the start of every session; and answering them never stuck, so the next session asked again. These are precisely the sessions a human is sitting in front of, so the interruption was paid every single time.

The driver now opens those checkouts for the session itself, exactly as it has always done for the automated builder and reviewer — the prompts stop, and nothing beyond the checkouts that session is genuinely about is opened up.

Reported in [#494](https://github.com/eduralph/pdca-harness/issues/494).

## What to look at
`template/src/pdca_harness/leaves.py` — one new block of small helpers near the top of the module, and one added argument at each of the six interactive spawn sites: `do_plan`, `do_plan_batch`, `run_signoff`, `run_signoff_batch`, `run_act`, `run_publish`. Nothing else about those spawns moves — same working directory, same environment, same seeded prompt.

To see the effect: in a rendered instance whose brief names a sibling checkout, start any interactive leaf (`pdca plan <id>`, `pdca signoff <id>`) with a Claude or Codex interactive family and have it read that checkout — no workspace-approval prompt. To check it without a vendor CLI, the new offline module asserts the exact command line the driver builds for each of the six sessions:

```
cd template && PYTHONPATH=src python3 -m unittest tests.test_leaf_workspace_admission
```

## Root cause
The six interactive spawns called `_invoke(<leaf>, cfg.root, …)` with no `extra_argv` at all, and their working directory is the instance root — so the target checkout their own prompts point at sat outside the session's workspace, while the headless leaves have always passed the family's grounding flag (`--add-dir`, `--include-directories`) for the directory they were told to read. Approving it by hand could not close the gap durably: the grant lands in the untracked `.claude/settings.local.json`, which a lane worktree never materializes and which `--setting-sources project` drops by design.

## Fix
Admission is derived from what the configuration and the bundles' own briefs already name, and which set a call site may use is a property of its role, so the boundary is visible in the code rather than in a flag:

- `_bundle_grant` — sign-off (single and batch), act, publish: strictly the primary checkouts the bundles *that session is about* resolve to, with **no** fallback. A session whose own bundle names a repo that is not checked out here admits nothing rather than widening to the instance's other checkouts.
- `_plan_grant` — planning only, the one session that runs before a brief exists to name a repo: the same resolution, falling back to the instance's known targets (`[publisher.checkouts]` plus what the existing briefs resolve to).
- Resolution goes through `publish._resolve_target` → `publish._checkout_path`, deliberately not the reviewer's worktree-preferring resolver, so a lane worktree can never be admitted and the human's checkout is never fetched on a spawn.
- `_grant_argv` emits the flag only when the family has one, so the `generic` family's command line is unchanged.

The `make setup` documentation is updated in the same change: the target checkout was its worked example, and that example is now the case the driver handles itself.

## Verification
- **Claim:** each of the six interactive spawns is launched admitting exactly the checkouts its session is about; planning falls back to the instance's known targets.
  **Checked:** `template/src/pdca_harness/leaves.py:924` and `:1117` (plan single/batch → `_plan_grant`), `:3409`, `:3460`, `:3557`, `:3626` (sign-off single/batch, act, publish → `_bundle_grant`); helpers at `:766-867`. On `main` @ `acb214a` the same six sites (`:782`, `:971`, `:3261`, `:3308`, `:3400`, `:3465`) pass no `extra_argv`, while the headless peers at `:1802`, `:1816` and `:2499-2500` do.
  **Test:** `template/tests/test_leaf_workspace_admission.py:180-258` — one positive per spawn site, batch cases admitting each distinct checkout exactly once.
- **Claim:** a session that already has a bundle never widens to the instance's other, unrelated checkouts.
  **Checked:** `leaves.py:846-855` — `_bundle_grant` has no fallback; `_known_targets` (`:805-829`) is reachable only from `_plan_grant` (`:858-867`).
  **Test:** `test_leaf_workspace_admission.py:279-311` — the fixture's known-target set is non-empty *and proven so through the production path* (planning admits it) before sign-off, batch sign-off, act and publish over an unresolvable bundle are asserted to admit nothing.
- **Claim:** never a lane worktree; never a directory neither the configuration nor a brief names.
  **Checked:** `leaves.py:766-791` — resolution never consults `worktree.path()`, so the exclusion is structural, not a filter.
  **Test:** `test_leaf_workspace_admission.py:314-328` creates a real `<repo>.pdca-wt`, asserts `worktree.path()` really returns it, then drives all six spawns; `:331-345` places a real unrelated checkout in the directory the sibling convention searches; `:347-357` covers a target that is not on this disk.
- **Claim:** a family with no grounding mechanism is spawned exactly as before.
  **Checked:** `leaves.py:832-843` — the flag is emitted only when the family profile has one, mirroring the existing headless grant sites.
  **Test:** `test_leaf_workspace_admission.py:359-374` — the `generic` family's argv is byte-identical.
- **Red → green:** with the production hunks reverted and the new module kept, 11 of its 14 cases fail on the missing admission argument; with the patch, 14/14 pass. The three that stay green pre-fix are the negatives whose expected outcome is "no grant" — they exist to catch a too-wide fix. The offline driver suite (1,772 tests), the render/update-compat suite and the docs lint + link audit are green on the patched tree.

Fixes #494
