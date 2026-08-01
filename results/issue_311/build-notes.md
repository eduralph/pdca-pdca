# Build notes — issue 311 / host-ci-gate (iteration 2)

Target: eduralph/pdca-harness @ main (base `dfd0427`, built in `$PDCA_WORKTREE`
`pdca-harness.pdca-wt-l0`). All `path:line` cites are `template/…` paths in that tree;
"base:" marks a pre-fix line, everything else is post-fix. The v1 attempt (preserved in
`iteration-v1/`) was rejected on two advisory findings; this rebuild keeps its accepted
skeleton (config surface, Check-leg rows, pre-push refusal) and replaces exactly the two
defective mechanisms.

## Carry-forward: what was rejected, and what changed

### C5 — stale-base certification (the substantive defect)

**v1 defect:** the publish leg reused `worktree.for_gate`, whose lane reconstruction
deliberately does not fetch (base: `worktree.py:238-239` — "No fetch on the warm path")
while the push plan's first step fetches (base: `publish.py:252`) and `checkout -B`
re-resolves the moving `<remote>/<base>` ref (base: `publish.py:253`). The reviewer
reproduced host CI green on the stale base, red on fetched base + patch: the gate could
certify a tree other than the one pushed.

**v2 fix — fetch, pin, and build the push on the pinned commit:**

1. `_pinned_base` (`publish.py:762-781`) runs the SAME fetch the push plan runs, then
   resolves the push's base ref to a commit SHA. Unpinnable ⇒ fail closed
   (`publish.py:836-838`).
2. `worktree.for_publish` (`worktree.py:535-587`) materializes an **ephemeral** tree at
   that SHA + `patch.diff` — the #226 overflow shape, not the lane: the lane's no-fetch
   contract is *correct for Check* (attest what Do built against) and is left untouched;
   publish needs the opposite contract (attest what the push will build). Fail closed on
   non-git target / gitlink patch / patch-no-longer-applies (`worktree.py:555-582`),
   torn down synchronously (`publish.py:849`).
3. `_pin_checkout` (`publish.py:784-793`) rebases the push plan's `checkout -B` step
   onto the certified SHA — so even a base that advances *between* the gate and the
   push's own fetch cannot reopen the gap: certified tree == pushed tree **by
   construction**, not by timing. Wired on both push paths (`publish.py:324-330` new-PR,
   `publish.py:457-461` stacked/Onto) and recorded as `host_ci_base` in `publish.json`
   (`publish.py:368-371`, `:485-486`) so certified==pushed is auditable after the fact.

**Test coverage for the reviewer's requested case** (base-advanced-since-Check):
`test_base_advanced_since_check_blocks_the_push` advances the toy origin from a second
clone (the local checkout stays unfetched), proves the command green in the stale
checkout, and asserts publish refuses with nothing pushed and `host-ci.json.base` == the
advanced SHA. A second test, `test_push_builds_on_the_certified_commit_not_a_later_base`,
advances the origin *after* certification (hooked via `for_publish`) and asserts the
pushed commit's parent is the certified SHA and the late content is absent — binding the
pin itself, not just the fetch. Both were run red against a deliberately-broken variant
(see refutation below).

### C3 — non-zero bypasses (exit 77, `gating = false`)

**v1 defect:** `failed = [r for r in rows if r["gating"] and r["result"] == "fail"]`
published on exit 77 and on failing `gating = false` rows — carve-outs the human never
blessed, against the brief's literal criterion (a).

**v2 fix — the brief's letter, both layers:**

- Publish leg: `failed = [r for r in rows if r["result"] != "pass"]`
  (`publish.py:850`) — ANY non-pass (fail *or* unverifiable/77) blocks, and `gating` is
  not consulted at all. Bound by `test_exit_77_blocks_publish_too` and
  `test_hand_marked_non_gating_row_still_blocks` (the latter hand-builds a
  `gating: False` row bypassing the normalizer, so the publish leg's own indifference
  to the key is what's tested).
- Config layer: `_normalize_host_ci` **forces** `gating = True` and warns loudly when a
  row declares `gating = false` (`config.py:683-687`) — the key is a contract, not a
  default: the host's CI will fail the PR on every declared command regardless, so an
  advisory host-CI row is a contradiction of the feature. An instance that wants an
  advisory command registers a plain `[gates].checks` row instead.
- Surfaced for sign-off (not silently decided): the Check leg still routes exit 77 to
  §6 as `unverifiable` (`gates.py:340-350` — that is the gates framework's #46 channel,
  pre-accept, where a human adjudicates), while the publish leg blocks on it per the
  brief's letter. If the human *wants* a post-sign-off deferral carve-out at publish,
  that is a conscious follow-up decision — this build ships none.

### C4 / T3 notes from the carry-forward

The carry-forward records the reviewer's C4 FAIL as an oracle-path artifact (it ran the
target's template-skeleton `run-verify.sh` instead of the instance's configured gate).
Nothing to fix in the patch; this build re-ran the *instance's* configured C4 gate
(`engine/scripts/run-verify.sh`, the `pdca.toml` `[gates]` row) — PASS, see below. The
T3 "failing gate" line pointed at a `/tmp/...` reviewer artifact; both real T3 suites
are green here (1336 + 7).

## What was built (full shape, for a reader who skips v1)

`[gates] host_ci` — an instance-config list of host-only CI commands (jobs the host's
CI runs on every PR but the delegated gate runner does not cover: `typos`, a docs
lint). Root defect (brief-verified): publish consults only `_t4_passes`, which runs
`cwd=cfg.root` (base: `publish.py:703`) against the tree **before** `patch.diff` is
applied (base: `publish.py:101`, `:187-192`) — prose arriving in the patch is
structurally invisible → Check green, PR opens red (wyrd ×4).

- Config: `Config.host_ci_checks` (`config.py:141`), parsed at `config.py:434`,
  normalized by `_normalize_host_ci` (`config.py:658-696`; bare string ⇒ `{cmd}`,
  defaults `tier="T4"`, `scope="bundle"`, forced `gating=True`, id/label from the
  command; command-less rows dropped loudly — the #338 vacuous-pass class).
  `PDCA_GATES_MODE=stub` empties it like `checks` (`config.py:449-453`). Documented in
  `pdca.toml.jinja:854-880`.
- Check leg: gate rows appended in `gates._run_checks` (`gates.py:328-356`), run with
  `cwd = wt` (the lane tree the bundle gates already reconstructed, `gates.py:305`);
  a red is gating → `overall=fail` → the existing #166 routing lands it in SUMMARY §6
  (zero assemble/signoff changes). No patched tree ⇒ honest `unverifiable` → §6. No
  bundle (CI working-tree re-gate) ⇒ skipped — the host's own CI runs these there.
- Publish leg: `_host_ci_passes` (`publish.py:796-861`) as described above — fetch,
  pin, ephemeral tree, run rows via the same `gates._run_one` the cited peer callsite
  uses (base: `gates.py:354-420` → `progress.run_with_heartbeat` at base:
  `gates.py:409`), block on any non-pass, record `host-ci.json` naming command + base,
  clear it on pass (`publish.py:859`).
- Placement changed vs v1: the gate now runs in the mechanics section after
  `_check_repo` (`publish.py:316-330`), not before the publisher leaf. Reason: pinning
  needs the resolved push path (new-PR vs stacked vs wave-stack base), which is only
  known there. Cost of the trade: on a *direct* `pdca publish` whose host CI fails, one
  publisher-leaf call is spent drafting texts before the refusal — but texts are
  only-if-missing (base: `publish.py:45-55`), so a retry re-uses them; on the flow path
  they were prevalidated anyway. Dry-run prints the gate as a plan line instead of
  executing it (`publish.py:297-301`, `:431-435`) — a dry-run that fetched and ran
  instance CI commands would no longer be "dry".

## Alternatives ruled out (with cost)

- **Fetch-before-certify without the pin** (~8 fewer lines: no `_pin_checkout`, no
  `host_ci_base`): leaves a TOCTOU window — the push plan's own `fetch` re-resolves
  `<remote>/<base>` after certification, so a base advancing mid-publish reproduces C5
  exactly. The reviewer's fix instruction says "fetch/**pin** the same base commit the
  push will use"; the pin is what turns the race into a construction-time guarantee,
  and `test_push_builds_on_the_certified_commit_not_a_later_base` fails without it.
- **Teach `rebuild_for_gate` to fetch for the publish caller** (a `fetch=` flag, ~10
  lines in `worktree.py` + threading it through `for_gate`): mutates the *lane* to a
  fetched base, violating its documented contract ("the base ref must stay the one Do
  built against", base: `worktree.py:238-239`) for every Check reader that shares the
  lane, and still certifies a ref, not a commit — no pin. A wrong-contract reuse is how
  v1 got here; a separate 53-line `for_publish` with the opposite, documented contract
  is the honest shape.
- **Verify-then-refuse instead of pin** (after the push-path fetch, re-check that the
  base ref still equals the certified SHA, ~6 lines): turns a benign base advance into
  a publish failure the operator must retry, where the pin publishes the certified tree
  — strictly worse operator experience for zero extra safety.
- **Synthesize host_ci into `gates_checks` T4 rows** (~10 lines in config): publish's
  `_t4_passes` runs T4 rows `cwd=cfg.root` pre-apply (base: `publish.py:703`) — the
  exact blindness; fixing that inside `_t4_passes` would change worktree semantics for
  every existing T4 row of every instance (#339 walled this off).
- **Run host CI inside the steps loop after `git apply`** (between base: `publish.py:254`
  and `:264`): freshest tree, no worktree machinery — but it splits `steps` into two
  phases on both push paths (+ dry-run printing + stash/restore interplay, ~40 lines
  across `publish`/`_publish_stacked`), runs the commands in a tree that includes the
  operator's stash state on failure paths, and gives no Check-time record at all.

## Verification (project runners only; no hand-rolled invocations)

1. Configured C4 gate (`./engine/scripts/run-verify.sh`, `PDCA_BUNDLE=results/issue_311`,
   `PDCA_WORKTREE=<worktree>`): **"C4 PASS: red without the fix, green with it."**
   (run twice — before and after the refutation edits were restored).
2. New module alone: `cd template && PYTHONPATH=src python3 -m unittest
   tests.test_host_ci` → **22/22 OK**.
3. Full offline driver suite: **1336 tests OK** (2 pre-existing skips; 1314 base + 22).
4. Root render/update-compat suites (instance venv copier): **7 OK** — the
   `pdca.toml.jinja` edit still renders valid TOML.
5. Configured T2 docs gate (`./engine/scripts/run-docs-check.sh`): lint OK, 22-page
   site render + link audit OK.
6. `git apply -R --check patch.diff` clean against the built tree (tree == base +
   patch, the #296 property).

Target commit-readiness: the target repo has no pre-commit/formatter config (checked:
no `.pre-commit-config.yaml` / ruff / black; workflows are docs-check, docs,
render-check, require-linked-issue). Items 3–5 green over the working tree = the
target's own CI bar; require-linked-issue is satisfied by the publish trailer at
publish time.

## Forced refutation — the three questions

- **(a) Genuine red?** Yes — full revert plus three *mechanism-targeted* partial
  refutations (each edit made, test run, edit restored, full suite re-run green):
  1. Full revert (the C4 gate's red leg): module errors on import — the feature and
     its config surface don't exist on base. Weak alone, hence:
  2. **Fetch neutered** (`_pinned_base`'s `git fetch` swapped for `git status`):
     `test_base_advanced_since_check_blocks_the_push` **FAILED** — publish certified
     the stale base and pushed. This is precisely the reviewer's reproduced C5.
  3. **Pin disabled** (`if ci_base:` → `if False:` at `publish.py:329`):
     `test_push_builds_on_the_certified_commit_not_a_later_base` **FAILED** — the push
     built on the later base the gate never saw.
  4. **v1 carve-outs restored** (`failed` filter back to
     `r["gating"] and r["result"] == "fail"`): `test_exit_77_blocks_publish_too` and
     `test_hand_marked_non_gating_row_still_blocks` both **FAILED** with `0 != 1` —
     i.e. publish returned 0 and pushed, the exact rejected C3 behaviour.
- **(b) Production path?** Yes. The tests drive `publish.publish` (the real entry
  point), `gates.run_gates`/`run_working_tree`, `Config.load` + `_normalize_host_ci`,
  and — in `HostCiPatchedTree` — the real `_pinned_base` fetch, the real
  `worktree.for_publish` reconstruction, and real `git push` to a toy bare origin.
  Only host-external effects are stubbed in the offline class (git/gh subprocesses,
  the pin, the tree — the same seams `test_publish_slice` stubs); no logic is
  re-implemented in the test. The pin test wraps the *real* `for_publish` (calls it,
  then advances the origin) rather than replacing it.
- **(c) Fixture includes the fault?** Yes, all three fault shapes: the wyrd shape (the
  marker exists **only in patch.diff**; the test first proves the command green
  against the unpatched checkout), the C5 shape (the fault exists **only on the
  advanced remote base** the local checkout has not fetched; proven green in the stale
  checkout first), and the mid-publish advance (fault content pushed to origin
  **after** certification). Nothing is curated out: refusals are asserted via
  `git ls-remote` on the origin (no branch), and passes via the pushed branch's actual
  parent SHA and tree listing.

## Files in this bundle

- `patch.diff` — 992 lines vs base `dfd0427` (6 files).
- `test_host_ci.py` — copy of `template/tests/test_host_ci.py` (also inside the patch).
- `build-notes.md` — this file.
