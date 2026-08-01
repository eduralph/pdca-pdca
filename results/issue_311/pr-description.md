## Summary
**User impact:** A project can run extra CI jobs on every pull request — a
spell-checker like `typos`, a docs lint — that the harness's delegated gate
runner does not cover. Today a contribution can pass every check the cycle runs
and still open a pull request that immediately fails one of those required
statuses, because the failing content (a misspelling, a lint violation) arrives
in the patch itself and nothing before the push ever examines the patched
files. This hit the wyrd instance four times, always on its `typos` job.

This PR adds an opt-in `[gates] host_ci` list: declare those commands and the
harness runs each one against the patched tree — once at Check, and again
immediately before pushing — and refuses to push on any failure. Declaring
nothing changes nothing.

Reported in [#311](https://github.com/eduralph/pdca-harness/issues/311).

## What to look at
The heart of the change is `_host_ci_passes` in
`template/src/pdca_harness/publish.py`: fetch the remote, pin the exact base
commit the push will build on, materialize base + patch in a throwaway
worktree at that commit (`worktree.for_publish`), run the declared commands
there, and either refuse (recording `host-ci.json`) or build the pushed branch
on that same certified commit. Supporting pieces: the config normalizer
`_normalize_host_ci` (`config.py`), the Check-time gate rows in
`gates._run_checks`, and the documented config block in
`template/pdca.toml.jinja`.

To try it: add `host_ci = ["typos"]` under `[gates]` in an instance's
pdca.toml, give a bundle a patch that introduces a typo, and run
`pdca publish <id>` — it refuses, names the command, and pushes nothing.
Remove the declaration and publish behaves exactly as before.

## Root cause
Publish's only CI-parity gate is `_t4_passes`, which runs its commands with
`cwd=cfg.root` against the tree before `patch.diff` is applied
(`template/src/pdca_harness/publish.py:101`, `:187-192`, cwd at `:703` on
`main`), so a job that judges file content structurally cannot see content
that arrives in the patch. The Check-side gate worktree cannot substitute as a
pre-push certifier either: its warm path deliberately never fetches
(`template/src/pdca_harness/worktree.py:238-239`) while the push fetches and
builds the branch on the current base, so it can certify a stale tree other
than the one being pushed.

## Fix
- **Config** (`config.py`): `[gates] host_ci` — bare strings or tables,
  normalized to gate-check-shaped rows (defaults tier `T4`, bundle scope,
  id/label from the command). `gating` is forced true, loudly — the host's CI
  will fail the PR on a declared command regardless, so an advisory row would
  re-open the exact gap; command-less rows are dropped loudly.
  `PDCA_GATES_MODE=stub` empties it like `checks`.
- **Check leg** (`gates.py`): the rows run from the reconstructed
  base + patch.diff lane worktree the bundle-scoped gates already trust; a red
  is gating, so it reaches check-gates and the sign-off summary. No patched
  tree ⇒ an honest "unverifiable" row, never a run against the wrong tree.
- **Publish leg** (`publish.py`, `worktree.py`): `_pinned_base` runs the same
  fetch the push plan runs and resolves the base ref to a commit SHA;
  `worktree.for_publish` materializes an ephemeral base + patch.diff tree at
  that SHA (fail-closed on a non-git target, a submodule-gitlink patch, or a
  patch that no longer applies); the commands run through the same machinery
  as configured gates. ANY non-pass — exit 77 included, `gating` not
  consulted — blocks the push and records `host-ci.json` naming the command
  and the base. On green, `_pin_checkout` rebases the push's `checkout -B`
  onto the certified SHA — certified tree == pushed tree by construction,
  even when the base advances mid-publish — and `publish.json` records it as
  `host_ci_base`. Both push paths (new PR and onto-branch) are gated;
  `--dry-run` prints the gate as a plan line instead of executing it.

## Verification
- **Claim:** a declared command that exits non-zero against the tree the push
  would publish blocks publish — no branch pushed, no PR opened — and the
  failure is recorded with the command named.
  **Checked:** `template/src/pdca_harness/publish.py:101`, `:187-192` on
  `main` — publish consults only `_t4_passes` before pushing, and it runs
  pre-apply with `cwd=cfg.root` (`:703`): no seam ever saw the patched tree.
  **Test:** `template/tests/test_host_ci.py` (fails pre-fix — the config
  surface does not exist on `main` and publish pushes regardless; passes
  post-fix): `test_failing_command_blocks_publish_and_names_it`, and
  end-to-end with real git `test_typo_arriving_in_the_patch_blocks_the_push`
  (the marker exists only in `patch.diff`; the test first proves the command
  green against the unpatched checkout — the exact pre-apply blindness).
- **Claim:** the gate certifies the very tree the push builds, even when the
  base advances after Check or mid-publish.
  **Checked:** `template/src/pdca_harness/worktree.py:238-239` on `main` —
  the gate lane's warm path never fetches, while the push plan fetches and its
  `checkout -B` re-resolves the moving base ref; hence fetch + pin + pinned
  `checkout -B`.
  **Test:** `test_base_advanced_since_check_blocks_the_push` (the origin
  advances from a second clone, the local checkout stays unfetched; publish
  refuses and `host-ci.json` records the advanced SHA) and
  `test_push_builds_on_the_certified_commit_not_a_later_base` (the origin
  advances after certification; the pushed commit's parent is the certified
  SHA and the late content is absent).
- **Claim:** "non-zero" is literal — exit 77 and a row hand-marked non-gating
  block too.
  **Test:** `test_exit_77_blocks_publish_too`,
  `test_hand_marked_non_gating_row_still_blocks`.
- **Claim:** a passing command leaves publish unchanged; an instance that
  declares nothing is byte-identical to today.
  **Test:** `test_passing_command_leaves_publish_unchanged`,
  `test_clean_patch_passes_and_publishes` (the pushed commit's parent is the
  certified base), `test_undeclared_is_byte_identical` (no fetch, no worktree,
  no record), `test_absent_key_is_empty`,
  `test_undeclared_keeps_the_stub_matrix`.
- **Suites:** the new module 22/22; full offline driver suite 1336 tests OK
  (2 pre-existing skips); render/update-compat 7 OK (the `pdca.toml.jinja`
  edit still renders valid TOML); docs lint + site render/link audit OK.

Fixes #311
