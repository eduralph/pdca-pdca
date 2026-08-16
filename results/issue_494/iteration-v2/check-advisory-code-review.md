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
