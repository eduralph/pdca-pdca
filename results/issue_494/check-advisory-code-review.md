# Advisory code review — issue #494

## Summary

Clean. No correctness bugs introduced by this patch, and no reuse/duplication/efficiency
issue within the diff's own scope.

## What I checked

- Grounded every call site against the target source (`template/src/pdca_harness/leaves.py`
  at the patched tree): `do_plan` (leaves.py:915-924), `do_plan_batch` (leaves.py:1097-1117),
  `run_signoff` (leaves.py:3401-3410), `run_signoff_batch` (leaves.py:3452-3462), `run_act`
  (leaves.py:3547-3558), `run_publish` (leaves.py:3609-3628) all pass `extra_argv=` through
  the new `_bundle_grant`/`_plan_grant` helpers (leaves.py:733-767 in the new block), landing
  ahead of `_invoke`'s interactive `--`/seed tail (leaves.py:611, :633-635) — matches the
  brief's citation and the existing reviewer/plan-advisory precedent it mirrors
  (leaves.py:2644-2645, :2980-2981, :3281-3282).
- Reran the new suite both on the patched tree (`template/tests/test_leaf_workspace_admission.py`,
  14/14 pass) and with `leaves.py`/the docs hunk reverted (11/14 fail, all on the same
  "spawn passed no extra_argv at all" assertion) — the red→green claimed by `C4-verify.log`
  is genuine and exercises the real call sites via a stubbed `leaves._invoke`, not a copy.
- Verified the fix for the defect the carry-forward names: `_bundle_grant` (leaves.py) has
  **no** known-targets fallback (`_grant_argv(_bundle_targets(bundles, cfg), profile)` only),
  so sign-off/Act/publish over a bundle whose brief resolves to a checkout not on disk now
  admits nothing, never the instance's other targets — confirmed both by reading the code and
  by `test_a_bundle_scoped_session_never_widens_to_the_known_targets` passing on a fixture
  built so the old bug would be visible (a resolvable known target exists, proven via Plan,
  and the four bundle-scoped spawns still admit nothing for the unresolvable bundle). The
  fallback lives only in `_plan_grant` (`_bundle_targets(...) or _known_targets(cfg)`), which
  is where criterion (ii) scopes it.
- Traced `_primary_checkout`'s resolution path (`publish._resolve_target` → guarded
  `publish._checkout_path`, `p.is_dir()` restricted) against `publish.py:548-587` — matches
  `_plan_fallback_target`'s own resolution (leaves.py:3184-3189) and deliberately does not
  reuse `_reviewer_target`/`worktree.path()`, so it structurally cannot admit a lane worktree
  (confirmed by `worktree.py`'s `_wt_dir`/`WT_SUFFIX` and `lane.py:26-28`'s serial
  `current() is None`, and by the passing `test_no_spawn_admits_a_lane_worktree`).
- Checked `_known_targets`'s two-source union (`cfg.repo_checkouts` then
  `bundle_root.glob("issue_*")` + `glob("completed/issue_*")`) against `config.py:161`
  (`repo_checkouts: dict[str, str]`) and the archive convention at `config.py:511` — the glob
  pattern and dedup-by-resolved-`Path` are consistent with how the rest of the module globs
  `issue_*` (e.g. `leaves.py:1073`, `:1095`, `:1102`, `:1129`; `publish.py:690`); no filesystem
  race or missing-`is_dir()` concern beyond what those existing call sites already accept.
- `_grant_argv`'s `if not profile.grounding_flag: return []` mirrors the existing headless
  grant sites' `if profile.grounding_flag` guard exactly, so criterion (v) (`generic` family
  byte-identical) holds by construction, not just by the one test — confirmed by
  `families.py:44/:126` (`grounding_flag: str = ""` on the generic profile) and by
  `test_generic_family_spawns_are_byte_identical` passing.
- `run_publish`'s pre-existing `profile = families.resolve(...)` (leaves.py:3615) is reused
  for the new `_bundle_grant([d], cfg, profile)` call rather than re-resolved — no duplicate
  work introduced.

## Reuse / duplication note (not a finding)

The five existing headless grant sites (`leaves.py:1947`, `:1961`, `:2644-2645`,
`:2980-2981`, `:3281-3282`) still each spell out `[flag, str(x)] if cond else None/[]` inline
rather than calling the new `_grant_argv` helper this patch adds. That is a
possible follow-on simplification, but the brief explicitly puts those five call sites out of
scope ("already do this correctly and are the pattern to mirror — do not change them"), so
retrofitting them here would be out-of-scope churn, not a defect of this diff. Not filing it
as a finding.

No other findings.
