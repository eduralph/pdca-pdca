# Build notes — issue 494 (iteration 3)

Target branch: `eduralph/pdca-harness` @ `main` (`acb214a`). All `path:line` citations below
are on the patched worktree `$PDCA_WORKTREE` = `/home/eddie/pdca/pdca-harness.pdca-wt-l0`
unless prefixed with "base:" (the unpatched base).

## 1. What the patch does

Six interactive spawns were launched with **no `extra_argv`** (base: `leaves.py:781-783`,
`:971-972`, `:3260-3261`, `:3307-3309`, `:3399-3401`, `:3463-3466`) while their prompts point
at the target checkout. Their cwd is `cfg.root`, so that checkout is outside the workspace and
the human is asked to approve the same out-of-workspace read every session — an approval that
cannot durably stick (untracked `.claude/settings.local.json`, which a lane worktree never
materialises, and `--setting-sources project` drops, `families.py:100-102`). The headless half
already solves this on the spawn's argv (`_do_build_command` at `leaves.py:1926`,
`_run_review_sandboxed` at `:2602`), so this is a composition of that pattern, not a new
mechanism.

New, in one block at `leaves.py:733-867`:

| symbol | line | role |
|---|---|---|
| `_primary_checkout` | `leaves.py:766` | one bundle's resolved primary checkout, or `None` — `publish._resolve_target` → `publish._checkout_path`, guarded, existence-restricted |
| `_bundle_targets` | `leaves.py:794` | the deduped, existence-restricted set for the bundles a session is about |
| `_known_targets` | `leaves.py:805` | `[publisher.checkouts]` ∪ what the instance's existing briefs (active + archived) resolve to |
| `_grant_argv` | `leaves.py:832` | dirs → `[flag, dir, …]`, **only** when `profile.grounding_flag` is non-empty (criterion v) |
| `_bundle_grant` | `leaves.py:846` | **resolve-only** — sign-off (single/batch), Act, publish |
| `_plan_grant` | `leaves.py:858` | **resolve-or-known-targets** — Plan (single/batch) only |

Call sites, all through the pre-existing `_invoke(extra_argv=)` parameter:
`leaves.py:924` (`do_plan`), `:1117` (`do_plan_batch`), `:3409` (`run_signoff`),
`:3460-3461` (`run_signoff_batch`), `:3557` (`run_act`), `:3626` (`run_publish`).

Nothing else about the spawns moves: cwd stays `cfg.root` at all six; the handoff env, the
`gh` STOP shim for a non-native-guard publisher (`leaves.py:3611-3616`) and the `--`/seed tail
(`_invoke`, base `:607-639`) are untouched — `extra_argv` is folded into `argv` **before** the
separator, which is what #396 requires.

## 2. The carry-forward — what changed since iteration 2 (and what I deliberately kept)

Sign-off rejected v2 on one conditional: `_admission_set`'s `return dirs or _known_targets(cfg)`
applied the known-targets fallback to **all six** spawns, so a sign-off / Act / publish session
over a bundle whose repo is not checked out here silently admitted the instance's *other*
checkouts. Criterion (ii) scopes that fallback to Plan.

I took the sign-off's **preferred** remedy — the role boundary in the type, not a flag:

- `_bundle_grant` (`leaves.py:846-855`) has **no fallback at all**. Reading the sign-off call
  site (`leaves.py:3409`) tells you the whole rule; you cannot reach `_known_targets` from it.
- `_plan_grant` (`leaves.py:858-867`) is the only caller of `_known_targets`, and only two call
  sites use it (`:924`, `:1117`).

The blind fixture is fixed and now actively refutes v2 —
`test_a_bundle_scoped_session_never_widens_to_the_known_targets`
(`template/tests/test_leaf_workspace_admission.py:279-311`): the instance has a **resolvable**
bundle (`issue_40` → `<tmp>/repo`) *and* a configured `[publisher.checkouts]` entry, so the
known-target set is demonstrably non-empty; the test **proves** that through production (Plan's
own spawn admits `<tmp>/repo`) before asserting that sign-off, batch sign-off, Act and publish
over an unresolvable bundle (`org/absent`) admit **nothing**. I verified the refutation
empirically: with `_bundle_grant` temporarily changed back to v2's
`_bundle_targets(...) or _known_targets(cfg)`, this test — and only this test — fails:

```
AssertionError: ['--add-dir', '/tmp/tmp0glr7t9g/repo'] is not false : run_signoff admitted
['--add-dir', '/tmp/tmp0glr7t9g/repo'] for a bundle whose target is not checked out here
```

(The temporary edit was reverted immediately; `git diff --stat` is back to the shipped 3 files.)

Also added, to bound the fallback from the other side:
`test_a_replan_over_an_existing_brief_stays_at_that_bundles_target` (`:268-277`) — a Plan
session over a bundle that *does* carry a brief resolves like any other session and does **not**
pick up the instance's other targets on top. Criterion (ii) is "when that set is empty", and now
both directions are asserted.

Kept as instructed (the sign-off said "do not re-do this part"): the six call sites through
`_invoke(extra_argv=)`, `cfg.root` cwd, `run_publish`'s reuse of the already-resolved `profile`
(bound at `leaves.py:3615`, used at `:3626`), the `generic` early return, and the deliberate
avoidance of `_reviewer_target`.

## 3. Decisions the brief made that I implemented rather than re-derived

1. **All six sites.** `do_plan_batch` (`:1117`) is in, `run_act` (`:3557`) is in.
2. **Never `_reviewer_target`.** It prefers `worktree.path()`; the interactive leaves run
   serially, so `lane.current()` is `None` (`lane.py:26-28`) and `worktree._wt_dir`
   (`worktree.py:107-112`) names the *unsuffixed* `<name>.pdca-wt` — which exists on this host
   right now (`/home/eddie/pdca/pdca-harness.pdca-wt`, unowned, one commit behind `main`). It
   also `git fetch`es the human's checkout on every spawn. `_primary_checkout` resolves the
   primary the way `_plan_fallback_target` does and does **not** fetch, so criterion (iii) holds
   *structurally*, not by a test — the test (`:314-328`) is the check on that claim: it creates
   a live `<repo>.pdca-wt`, asserts `worktree.path()` really returns it, then drives all six.
3. **The empty-set fallback is Plan's.** See §2.

## 4. The round-8 caveat, and why it does not transfer (the brief predicted the reviewer asks)

`_plan_fallback_target` (base `leaves.py:3023-3038`) refuses to expose the operator's primary
checkout because the grounding flag is read/**write** for codex and that leaf is a *sandboxed,
unattended* plan-advisory. None of that holds here: these six are **interactive**, they run in
the human's own terminal with the human present, and the deterministic half of publish already
runs `git -C <primary> fetch/checkout/apply/commit/push` against that very tree
(`publish.py:439-448`). The primary checkout *is* the interactive band's working surface; the
harness telling the leaf to read it while not admitting it is the defect, not the protection.
What still transfers from #301 rounds 7/8 is the *other* half — never the lane worktree — and
that is exactly what decision 2 preserves.

## 5. Alternatives considered, with their cost

- **Ship the grant in `template/.claude/settings.json`** (`additionalDirectories`). Rejected on
  correctness, not size: a *tracked* file cannot carry instance-specific absolute paths, and the
  brief holds that file for issue 508. Zero lines of it would work.
- **Widen `make setup`** (`template/Makefile:31-38`, which grants `Read(<parent-workspace>/**)`
  + `additionalDirectories: [ws, /tmp]`). Rejected: that is the over-admission edge of the
  invariant (a whole parent directory), it lives in the untracked local settings the unattended
  band cannot see, and it is not what the brief scopes.
- **One resolver with a `plan=True` parameter** instead of two functions. Same line count
  (±0: one function with a keyword vs. two 2-line wrappers over a shared `_grant_argv`), but it
  puts the role decision in an argument at the call site, where v2's defect was born. The
  sign-off asked for the type boundary; two named functions is that, for 10 lines
  (`leaves.py:846-867`).
- **Route through `_reviewer_target`** (v1's resolver, ~8 lines shorter — it reuses an existing
  function instead of adding `_primary_checkout`'s 26). Rejected in the brief and confirmed
  live: it would admit the unowned `pdca-harness.pdca-wt` instead of the checkout the human has
  open, on every interactive spawn, and `git fetch` their tree each time.
- **Do nothing for `generic`** vs. faking a flag: `_grant_argv` returns `[]`, and `_invoke` does
  `argv += list(extra_argv or [])`, so `[]` and "parameter absent" are the same command line —
  criterion (v) is satisfied by construction, and asserted at `tests/…:359-374`.

Cost of what shipped: `leaves.py` +167/-8 (of which 34 lines are the comment block and the six
call-site comments), the new test module 373 lines, docs +13/-2.

## 6. The docs hunk (`docs/01-render-and-integrate.md:424-438`)

`### make setup` told the reader that without that one-time grant "the interactive leaves …
prompt you file-by-file … e.g. **a sibling checkout your gates or briefs reference**". After
this patch that example is exactly the case the driver handles itself, so the sentence would
ship stale. The edit removes the now-wrong example, states what the driver admits (bundle-
resolved primaries; Plan's known targets; never a lane worktree, never an unnamed directory),
and re-points `make setup` at what genuinely remains outside. It changes no behaviour, and the
C4 classifier treats `docs/*` as non-behavioral (instance `engine/scripts/run-verify.sh:134`),
so the red leg is unaffected — verified by re-running C4 after adding it.

## 7. Forced self-refutation (the three questions)

**(a) Genuine red?** Yes — measured, not asserted. `./engine/scripts/run-verify.sh` reverts only
the production hunks (`--exclude=tests/*`, `--exclude=template/tests/*`) and re-runs:

```
== C4 green leg: … Ran 14 tests … OK
== C4 red leg:   … Ran 14 tests … FAILED (failures=11)
PDCA-EVIDENCE: C4 PASS — red without the fix, green with it
```

The 11 include every positive and the new `…never_widens_to_the_known_targets` (its Plan
fixture-check assertion fails when nothing is admitted). The 3 that stay green pre-fix are the
negatives whose expected outcome is "no grant" (`nothing_known`, `not_on_disk`, `generic`) —
they exist to stop a *too-wide* fix, and the module never imports a symbol this patch adds, so
the red leg loads cleanly (no `PDCA-UNVERIFIABLE`).

**(b) Production path?** Yes. The only stub is `leaves._invoke` — the process-spawn boundary,
the same seam `test_leaf_resilience.py` / `test_do_confine.py` use. Every test calls the real
`leaves.do_plan` / `do_plan_batch` / `run_signoff` / `run_signoff_batch` / `run_act` /
`run_publish` with a real `Config`, real bundle dirs and real `brief.md` files on disk, and the
admission set is produced by the real `publish._resolve_target` + `publish._checkout_path`,
`act.frozen_bundles`, `worktree.path` and `families.resolve`. Nothing about the resolution is
re-implemented in the test; it asserts over the argv the driver would have spawned. C5
(`run-prod-path.py`) confirms: "1 added driver-suite test(s) import the production package
'pdca_harness'".

**(c) Fixture includes the fault?** Yes, in all three negatives:
- (iii) the lane worktree is **really there** — `git init`'d at `<tmp>/repo.pdca-wt`, and the
  test asserts `worktree.path(probe, cfg) == wt` *before* driving the six, so the trap a
  `_reviewer_target`-based resolver would fall into is live (`:314-328`).
- (iv) `<tmp>/unrelated` is a real checkout sitting in the very directory the sibling convention
  searches, and the parent `<tmp>` is named explicitly (`:331-345`).
- the v2 regression: the known-target set is non-empty **and proven so through the production
  path** before the four bundle-scoped leaves are asserted to admit nothing (`:279-311`) — the
  precise blindness the sign-off identified in v2's `test_a_target_that_is_not_on_disk…`.

## 8. Gates run locally (the project's own runners, from the instance root)

| runner | result |
|---|---|
| `engine/scripts/run-verify.sh` (C4) | `PDCA-EVIDENCE: C4 PASS — red without the fix, green with it` |
| `engine/scripts/run-suite.sh` (T3) | `root suite OK, driver suite OK` (offline suite: `Ran 1772 tests … OK (skipped=2)`) |
| `engine/scripts/run-docs-check.sh` (T2) | docs lint clean, site render + link audit clean |
| `engine/scripts/run-prod-path.py` (C5) | 1 added test imports `pdca_harness` |

Commit-readiness: the target repo defines no pre-commit hooks (`.git/hooks` holds only samples,
no `core.hooksPath`) and no Python formatter/linter config (no `pyproject.toml`, `.flake8`,
`ruff.toml`, `.pre-commit-config.yaml` anywhere in the tree); CI is docs-check + render-check,
both covered above (render-check is `tests/test_render_and_run` + `test_update_compat`, which
the T3 root suite ran). Longest added line is 94 chars, within the file's own convention
(`leaves.py` max is 110; 290 lines in `template/tests/*.py` already exceed 95). Self-referential
line citations inside the new comments were replaced with **function names** (`_do_build_command`,
`run_review`, `_plan_fallback_target`), because inserting 136 lines at `:733` shifts every
absolute line number below it — a citation style that would have shipped stale.

## 9. External dependencies

None beyond the base toolchain (stdlib Python 3.11+ and `git`, both present). No NEEDS-HUMAN
external dependency. What no automated gate can observe is Claude Code's prompting behaviour —
that the human is no longer asked; per the brief that is supplementary and human-observed, and
this cycle's own sign-off / publish sessions read `../pdca-harness`, so the human sees it
directly (`pdca-pdca try 494` yields a patched worktree).

## 10. STOP discipline

Draft only: nothing pushed, no branch created, no PR opened or marked ready.
