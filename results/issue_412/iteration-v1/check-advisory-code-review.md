# Advisory code review — issue 412 (merge-mode atomic merge group)

Lens: bugs the patch introduces, plus reuse / simplification. Advisory only; nothing here gates. All path:line refs are on the patched tree at `$PDCA_TARGET`.

## Correctness

- NEEDS-HUMAN [impl] — **A split mid-run breaks any group that spans driven and undriven waves.** `template/src/pdca_harness/flow.py:2386-2387` re-waves only `wave_list[k + 1:] + children` through `waves.partition_schedulable`. In merge mode that now runs `merge_group_refusals` on those survivors (`template/src/pdca_harness/waves.py:482-491`). Take fixture (a): if any wave-0 bundle splits, the re-wave set is `[B, C, children]`. B's `Merges with: A` names A, which has already been driven and is no longer a survivor, so B is refused as "a member outside the batch" and held, and C is held with it. A then stays a draft forever, and the run blames a group shape that was fine. Fix: judge the "outside" rule against the whole run's batch (or skip it in `_reschedule`), not the remaining tail. No test covers a split in a merge-mode run that has a group.

- NEEDS-HUMAN [impl] — **One-sided declarations get lost once the declaring bundle drops out of the set.** `waves._merges_with` (`template/src/pdca_harness/waves.py:180-191`) reads only the briefs of the bundles it is given. In the sweep, `flow.py:3393` replaces `bundles` with the schedulable survivors, and the drive then calls `waves.merge_groups(cfg, bundles)` (`flow.py:3116`, `flow.py:2957`) on that reduced list. Example: X declares `Merges with: A`, A's brief is silent, and X is held (say for an unresolved dependency). A is then in no group and merges alone at its boundary, which is exactly the half-landing the field exists to stop. The `while` loop's comment at `waves.py:479-481` ("a group one of whose members is held now names a bundle outside the survivors") is only true when the survivor's own brief makes the declaration. Fix: build the relation from the full input `bundles`, and hold any survivor whose group has a held member.

- NEEDS-HUMAN [human] — **Same gap with explicit ids.** `pdca flow A`, where an out-of-batch X declares `Merges with: A` and A says nothing: `check_dep_graph` only reads in-batch briefs (`waves.py:180`), so nothing is refused and A merges alone. Success criterion (f) says either side binds both, and (g) refuses an out-of-batch member. Catching this needs a scan of on-disk briefs beyond the batch. That is a scope call, not a simple fix.

- NEEDS-HUMAN [impl] — **The release does not check that every member can be merged before merging the first one.** Once all members are COMPLETE, `merge_wave` merges them one after another (`template/src/pdca_harness/merge.py:163-176`). `_merge_one` refuses, *after* an earlier member has already landed, in cases the code could have detected up front: no recorded PR (`merge.py:541-544`, e.g. the later member's publish texts failed T4 — `flow.py:3094-3097` still leaves it in `complete`), a `"stacked"` record (`merge.py:552-560`), or `cfg.expected_checks_error` (`merge.py:573-577`). `_back_to_back` puts earlier-wave members first, so the member that has been waiting (A) lands, then B is refused, and the group is half landed. The "landed only in part" message makes this visible, but these local, deterministic refusals could be checked for every member before the first `gh pr ready`, with the whole group held if any member fails. That would leave only true host-side failures (red checks, refused merge) as the remaining window, which is the window the brief's Impact section accepts.

- `template/src/pdca_harness/merge.py:146` — a member with no patch (close/no-fix) skips the hold, and so does any bundle that isn't COMPLETE, which is fine. But a no-patch member still counts as a member its partners wait for (`merge.py:148-149` only checks state). So a group where one member resolves as no-fix still merges the others together once it is COMPLETE. That matches the design; noted only so the behaviour is known.

## Tests

- NEEDS-HUMAN [impl] — `template/tests/test_merge_group.py` has no case for the two gaps above: a split during a merge-mode run with a group across waves, and a one-sided `Merges with` from a bundle that ends up held. It also has no case for a release where a later member has no PR (`merge_fails` only models a host refusal at `gh pr merge`, `test_merge_group.py:101`). One case for each would pin the fixes.

## Reuse / simplification

- `template/src/pdca_harness/merge.py:148-149` and `template/src/pdca_harness/flow.py:3230-3231` compute the same "members not COMPLETE" list in the same two lines. A small shared helper (e.g. in `merge`) would keep the hold line and the end-of-run line in step.
- `waves.merge_groups(cfg, bundles)` re-reads every brief at each wave start when anything is held (`flow.py:2957`), again at each merge boundary (`flow.py:3116`), and once more at the end (`flow.py:3192`). Briefs are small, so this is cheap, but one call per wave, reused at both spots, is simpler. The value has to be recomputed when a split adds children, so it can't be cached for the whole run.
- `template/src/pdca_harness/cli.py:726-729` — the docstring reflow left a dangling short line ("the map (PLANNED, for one not built" / "yet), …"). Cosmetic.

No other problems found: the `_runnable` group hold (`flow.py:801-803`) runs after the not-COMPLETE check and is kept separate from the #593 `held` set as the brief asks; `_back_to_back` keeps group members adjacent; `held.discard` on a successful merge keeps a clean run's `holds` empty; and the stack-mode path is untouched.

<!-- pdca:leaf-complete -->
