# Build notes — issue 311 / host-ci-gate

Target: eduralph/pdca-harness @ main (base `dfd0427`, built in `$PDCA_WORKTREE`
`pdca-harness.pdca-wt-l0`). All `path:line` cites below are `template/…` paths in that
tree; "base:" marks a pre-fix line, everything else is post-fix.

## What was built

`[gates] host_ci` — an instance-config list of host-only CI commands (the jobs the
host's CI runs on every PR but the delegated gate runner does not cover: `typos`, a docs
lint). Each declared command runs **from the reconstructed `base + patch.diff` worktree**
at two seams:

1. **Check leg** — `gates._run_checks` appends a gate row per declared command
   (`gates.py:328-357`), run with `cwd = wt` (the tree `worktree.for_gate` already
   resolved for the bundle gates at `gates.py:305`). The row lands in
   `check-gates.json`/`.md` and, because it defaults to `gating = true`, a red drives
   `overall = fail` and is routed into SUMMARY §6 by the **existing** #166 machinery
   (base: `assemble.py:364-368` — gating fail → §6 NEEDS-HUMAN → C6 blocks accept).
   That satisfies the brief's constraint "the record of a failure must land where
   sign-off/§6 can see it" with zero assemble/signoff changes.
2. **Publish pre-push leg** — `publish._host_ci_passes` (`publish.py:734-790`), called
   at `publish.py:192` after the target-resolution guard and **before** the publisher
   leaf, the T4 gate, and both push paths (new-PR and the `Onto branch` stacked path,
   which dispatches later at base: `publish.py:214`). It re-runs the same rows against a
   **freshly** reconstructed patched tree (`worktree.for_gate`, `publish.py:765`), so a
   base that advanced since Check is still what gets judged. A gating failure names the
   command on stderr, writes the rows to the bundle's `host-ci.json`
   (`publish.py:754-760`), and returns 1 with **nothing pushed and no PR opened**.

Config surface: `Config.host_ci_checks` (`config.py:140`), parsed at `config.py:433`,
normalized by `_normalize_host_ci` (`config.py:657-686` — bare string ⇒ `{cmd}`;
defaults `tier="T4"`, `gating=true`, `scope="bundle"`, id/label derived from the
command; a command-less row is dropped loudly, `config.py:673-677`, because
`subprocess.run("")` exits 0 — the #338 vacuous-pass class). `PDCA_GATES_MODE=stub`
empties it like `checks` (`config.py:448-452`). Documented for rendered instances in
`pdca.toml.jinja:854-876`.

## Why this shape

- **Root defect (brief-verified):** publish consults only `_t4_passes`, which runs
  `cwd=cfg.root` (base: `publish.py:703`) against the tree **before** `patch.diff` is
  applied (base: `publish.py:101`, `publish.py:187-192`). Prose arriving in the patch is
  structurally invisible → Check green, PR opens red (wyrd ×4). So the fix must run the
  commands against the *patched* tree at a point where a failure still blocks the push.
- **Seam choice — both legs, not one.** The brief's open question says "Default to
  Check-visible if both are cheap." Both are:
  - Check leg ≈ 30 lines in `_run_checks`, reusing `_run_one` (the cited peer callsite,
    base: `gates.py:354-420` → `progress.run_with_heartbeat` at base: `gates.py:409`)
    and the already-resolved worktree — no new run machinery, no new record format, §6
    routing for free.
  - Publish leg ≈ 57 lines, reusing `worktree.for_gate` (base: `worktree.py:535-587`)
    — the same reconstruction the bundle gates trust (#296).
  A Check-only seam fails the success criterion mechanically: publish runs on an
  already-COMPLETE bundle, so a human who accepted (or a base that drifted after Check)
  would still push a red tree — the brief's shipped test ("asserts publish refuses")
  cannot be satisfied without the publish leg. A publish-only seam satisfies (a) but
  leaves no §6-visible record at sign-off time; wiring one would mean teaching
  `assemble` to read a new file (≈25 lines in `assemble.py` + §6 dedup/C6 interplay)
  versus ~0 lines by letting the Check row ride #166.
- **Why the publish leg is NOT skipped under `texts_prevalidated`** (`publish.py:182-191`
  comment): the #339/#295 objection to publish-time re-gating is about *re-sampling a
  nondeterministic model gate after sign-off*. Host CI commands are tree-deterministic
  and their subject (base + patch) legitimately changes between the pre-pass and the
  push — re-running is the point, not a re-sample.
- **Fail closed when no patched tree exists** (`publish.py:766-772`; Check leg emits an
  `unverifiable` row instead, `gates.py:341-350`): running `typos` from `cfg.root` (the
  instance repo) or an unpatched primary can pass and produce a false green — the exact
  #296 lie. Check defers to the human (§6); publish refuses to push content the declared
  CI never saw.
- **`unverifiable` (exit 77 / marker) does not block publish** (`publish.py:783`):
  that channel already routed to §6 at Check where the human adjudicated; hard-blocking
  post-sign-off would contradict #46's contract.
- **Default `tier = "T4"`:** the issue frames this as "closing the T4 slot's pre-apply
  blindness" — the contribution as the host's CI will judge it. Per-row `tier`
  override kept for instances that see e.g. spell-check as T2.
- **Default `gating = true`**, unlike the usual advisory-first policy: the host's CI
  *will* fail the PR on these — an advisory default re-opens the observed gap
  (`config.py:661-666` docstring).

## Alternatives ruled out (with cost)

- **Synthesize host_ci into `gates_checks` T4 rows** (≈10 lines in config): publish's
  `_t4_passes` runs T4 rows `cwd=cfg.root` pre-apply (base: `publish.py:703`) — the
  exact blindness; fixing that inside `_t4_passes` would change worktree semantics for
  every existing T4 row of every instance (a behaviour change #339 explicitly walled
  off).
- **Run host CI inside the publish steps loop after `git apply`** (between base:
  `publish.py:254` and `:264`): freshest possible tree with no worktree dependency, but
  it splits the `steps` list into two phases on both push paths (+ dry-run printing,
  + stash/restore interplay ≈ 40 lines across `publish`/`_publish_stacked`), and gives
  no Check-time record at all. `for_gate` is also the machinery the brief names.
- **Extend the flow's `draft_texts` pre-pass** to run host CI wave-wide before any
  mechanics: adds a third run per bundle (worktree reconstruction ×2 at publish alone)
  for a marginal gain — a bundle still pushes nothing of its own when its mechanics-time
  gate fires. Deferred; noted as a possible follow-up if wave half-publish on host-CI
  reds is observed.

## What I tried / verification

Runner: the project's own gate + suite commands (pdca-pdca `pdca.toml` `[gates]` /
docs/INTEGRATION.md §3), never hand-rolled containers.

1. `./engine/scripts/run-verify.sh` (the configured C4 gate) with
   `PDCA_BUNDLE=results/issue_311`, `PDCA_WORKTREE=<worktree>`:
   **"C4 PASS: red without the fix, green with it."**
2. New test alone: `cd template && PYTHONPATH=src python3 -m unittest
   tests.test_host_ci` → 18/18 OK.
3. Full offline driver suite: 1332 tests, **OK** (2 pre-existing skips).
4. Root render/update-compat suites (venv copier): 7 tests, **OK** — proves the
   `pdca.toml.jinja` edit still renders valid TOML.
5. Partial-revert refutation (below).

Target commit-readiness: the target repo has no pre-commit/formatter config; its CI is
docs-check (no docs touched), render-check (item 4 above green), require-linked-issue
(publish trailer). Both test roots green over the working tree = the target's own bar.

## Forced refutation — the three questions

- **(a) Genuine red?** Yes, two ways. Full revert (the C4 gate's red leg): the suite
  fails — pre-fix `main` has neither `Config.host_ci_checks` nor `_normalize_host_ci`,
  so the module errors on import (the feature, including its config surface, does not
  exist). Because an import-red alone is weak evidence, I also did a **partial revert of
  `publish.py` only** (config+gates+test kept): 8/18 fail **behaviourally** — the run
  log shows `Draft PR prepared … fix/RG-my-fix` and the pushed branch present, i.e.
  publish pushed despite the declared failing host-CI command — exactly the defect, and
  proof the test binds the publish seam, not just the new symbols.
- **(b) Production path?** Yes. The tests drive `publish.publish` (the real entry
  point), `gates.run_gates`/`run_working_tree`, `Config.load` + `_normalize_host_ci`,
  and — in `HostCiPatchedTree` — the real `worktree.for_gate` reconstruction over a real
  git origin+clone. Only host-external effects are stubbed (git/gh subprocesses in the
  offline class, the same way `test_publish_slice` stubs them); no logic is
  re-implemented in the test.
- **(c) Fixture includes the fault?** Yes. `test_typo_arriving_in_the_patch_blocks_the_push`
  reproduces the wyrd shape end-to-end: the "typo" exists **only in patch.diff**, and the
  test first proves the check is *green against the unpatched checkout* (the pre-apply
  seam's blindness), then that publish refuses with `git ls-remote` showing **no branch
  pushed**. A wrong fix that runs the command pre-apply or from `cfg.root` stays green
  there and the test fails. The failure record (`host-ci.json` naming the command) is
  asserted in the same test.

## Files in this bundle

- `patch.diff` — 667 lines vs base `dfd0427`; `git apply -R --check` clean against the
  built tree (tree == base + patch, the #296 property).
- `test_host_ci.py` — copy of `template/tests/test_host_ci.py` (also inside the patch).
- `build-notes.md` — this file.
