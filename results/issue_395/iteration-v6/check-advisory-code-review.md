# Advisory code review — issue 395 (same-wave conflict refused at accept)

Lens: bugs the patch adds, plus reuse / simplification / efficiency. Advisory only. Line
numbers are on the patched target at `$PDCA_TARGET`.

Overall: no blocking correctness bug found. I traced the main risk, the "one more session"
count in leg (h), and it holds. After the first refusal, the trial's own §6 row is open, so
every later apply in that wave is stopped by C6 at `template/src/pdca_harness/flow.py:200-202`
before it reaches `_refused_for_wave`. So `_write_refusal(..., "sessions": 0)` at
`flow.py:322` runs once per refusal and does not reset the count that `_session_offered`
(`flow.py:2734`) raises. The `publish._checkout_base` refactor (`publish.py:767-776`) gives the
same result as the old inline rule (`wave_stacked = cfg.wave_mode != "merge" and
bool(wave_base)`, `publish.py:251`). The new `trial` condition (`flow.py:3246-3249`) matches
the fold's own guard (`flow.py:3307-3308`, where dry run means `publisher.mode == "stub"`).
Gates C4 (7 of 10 red before the fix, all green after) and T3 pass.

- NEEDS-HUMAN [impl] — `template/src/pdca_harness/flow.py:303` catches every
  `integrate.IntegrationError`, and that includes `IntegrationTreeError` and `_LineBroken`
  (both are subclasses, `integrate.py:104`, `integrate.py:113`). The fold treats those two as
  "the integration tree is in an unknown state, stop" (`integrate.py:675-676`,
  `flow.py:3220`). Here they are handled like a failed fetch: the code falls back to the
  shared-path rule and may go on to accept. The trial can raise them itself:
  `integrate.py:909` (`_would_be` could not return to the line) and `_back_on`
  (`integrate.py:947`). After that, the next trial and the fold each run `_prepare_worktree`
  and `checkout -B` again, so the damage is probably limited. Still, the stderr line and the
  §6 row only say "the check could not run", so a broken worktree is reported as a soft
  fallback. Suggested fix: re-raise these two (or at least name the tree state in the message)
  instead of falling back.
- `template/src/pdca_harness/integrate.py:916-919` and `:929-931`: a `_LineBroken` raised in a
  `finally` (in `_would_be` and in `same_wave_clash`'s `_back_on`) replaces the
  `IntegrationError` that started the unwind. The caller then reports "could not put … back"
  and loses the first cause (for example "its patch does not apply onto …"). This is minor
  because both are `IntegrationError` and are caught the same way. Chaining the first error
  (`raise … from`) would keep it.
- Efficiency, `template/src/pdca_harness/integrate.py:814-833`: each accept that gets past C6
  runs a full `_fetch` (origin, the base remote and any stack remotes), rebuilds the would-be
  commit of every already-accepted sibling on the same target, and replays the fold twice
  (`alone` and `held`). With n accepts in a wave, that is O(n²) apply/commit/merge steps plus
  n fetches, all while the sign-off sweep waits. Waves are small, so this is fine for now. If
  it starts to matter, cache the built commits and the `alone` result per wave (both depend
  only on the accepted set and `tip`).
- Reuse looks right. The trial reuses `_held_by`, `_merge`, `integ_lock`, `_integ_worktree`,
  `_prepare_worktree`, `signoff.ensure_needs_human_item` and `waves.diff_files`. It does not
  copy the fold's rule. `publish.cut_base` shares `_checkout_base` with `publish()`, so the
  base the trial builds on cannot drift from the base publish cuts from.
- Tests (`template/tests/test_flow_same_wave_accept_trial.py`): every leg goes through the real
  `_drive_wave` → `_apply_decision` path, as the brief asks. `_drive_wave` and
  `signoff.record` are not stubbed. I found no test that passes for the wrong reason. One gap:
  no test covers the `_LineBroken` / `IntegrationTreeError` path from the first bullet. Leg (e)
  only injects a failed `git apply` (`template/tests/test_flow_same_wave_accept_trial.py:313`).

<!-- pdca:leaf-complete -->
