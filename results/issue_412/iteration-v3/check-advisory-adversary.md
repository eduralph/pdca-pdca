# Adversarial review — issue 412 (merge-mode atomic merge group), round 3

Verdict: the red→green evidence is real, but the fix breaks on four concrete inputs: three
`[impl]` and one `[human]`. Each was reproduced against the patched tree at `$PDCA_TARGET`
using the new test module's own harness (production `flow._drive_and_act` / `cli.main`, `gh`
stubbed, merge mode).

## Evidence

- Tried to refute C4's red→green and could not. In `gate-logs/C4-verify.log`, 28 of 31
  cases in `template/tests/test_merge_group.py` fail with the production change reverted.
  They fail on assertions, not on import errors. The 3 that pass both ways are the declared
  guards: `test_a_malformed_expected_checks_…` (`test_merge_group.py:381`), leg (e)
  `test_the_chained_group_runs_as_today_in_stack_mode` (`:476`, which should be green before
  the fix) and `test_a_finished_member_already_merged_holds_nothing` (`:742`). Re-run here:
  31/31 green. Only the build leaf, the publish texts and `gh` are stubbed, so C5's claim
  that the tests run production code, not a copy, holds.

## Refutations

- NEEDS-HUMAN [impl] — **The up-front "group waits for itself" check gets a conflict pair's
  build order wrong, so it misses a real deadlock.** `_wait_edges`
  (`template/src/pdca_harness/waves.py:362-367`) decides which side of a `Conflicts with`
  pair builds first from `Depends on` edges only (`ordered`). Otherwise it assumes name
  order. `compute_waves` (`waves.py:510-516`) also counts the conflict edges it already
  added for earlier pairs, so it can build the name-higher bundle first. Failing case:
  K `Merges with: L`; L `Depends on: H`; H `Depends on: G` and `Conflicts with: K`;
  G `Conflicts with: F`; F `Depends on: K`. The waves are [K] [F] [G] [H] [L], so H is built
  after K. `pdca flow F G H K L --no-act` is **not** refused. K is held at wave 0's boundary,
  F is held (its prerequisite K is held), H is held (it conflicts with the held K), and L is
  never built. The run exits 1 with K left as a draft, and the closing line says "Merge the
  group together once that is resolved", which no re-run can resolve. The docs say this
  shape is refused before anything builds (`docs/07-crosscutting.md:925-928`). Fix: take
  the conflict direction from the same loop `compute_waves` uses (one shared helper), not
  from a second derivation.

- NEEDS-HUMAN [impl] — **Same root cause, other direction: a batch that works is refused
  with rc 2.** H `Merges with: L` and `Depends on: G`; L `Depends on: K`; K
  `Conflicts with: H`; G `Conflicts with: F`; F `Depends on: K`. The scheduler builds K in
  wave 0 and H in wave 3 (waves [K] [F, L] [G] [H]), so no member waits for its own group.
  But `_wait_edges` (`waves.py:367-368`) assumes name order (H before K), and
  `pdca flow F G H K L --no-act` exits 2 with "issue_K `Conflicts with` issue_H and is built
  after it … the group would never complete". No test has a conflict pair that the scheduler
  orders against name order; one such test per direction would pin both cases.

- NEEDS-HUMAN [impl] — **A member an earlier run finished is readied and merged into
  whatever base its old PR targets, which can be another bundle's branch.** The release now
  merges PRs this run did not open (`flow.py:2979-2995` adds them to `group_finished`, and
  `merge._back_to_back` at `merge.py:256` pulls them in). That breaks the module's own rule
  at `merge.py:86`: "Merge mode readies and merges only a PR this run opened".
  `_unmergeable` (`merge.py:232-253`) checks `pr_url`, `"stacked"` mode and `repo`, but not
  the record's `base`. Merge mode's publish guard against run-made bases (`publish.py:293`,
  #411) never saw a PR that a stack-mode run opened. Such a PR records `"base": pr_base`
  (`publish.py:436`), which can be a parent's fix branch (`publish.py:282`). Stack mode is
  also the way out that this patch's own refusals print. Failing case: A finished earlier
  with `Merges with: B` and a publish record `{"mode": "stacked-pr", "base": "fix/P", …}`;
  B `Depends on: D`; C `Depends on: B`. `pdca flow A B C D --no-act` runs `gh pr ready` and
  `gh pr merge` on A's PR, which merges A into `fix/P`, not `main`. It merges B into `main`,
  counts the group as landed, and exits 0 with no warning. Fix: for a member this run did
  not publish, hold the group and say why, unless its recorded base is its brief's target
  and not a branch another bundle produced. `publish._merge_base_refusal` already applies
  that check.

- NEEDS-HUMAN [human] — **A group member that gets split lets its partner land alone, with
  no message.** A split parent is COMPLETE with no patch (`state.py:351`, `split.accept`).
  So `group_blocker` (`merge.py:211-225`) sees every member COMPLETE, and `_unmergeable`
  returns "" because there is no patch. The children do not inherit the field:
  `split.rewrite_ordering` carries only `Depends on` / `Conflicts with` (`split.py:66`).
  Failing case: A `Merges with: S`; S, D plain; C `Depends on: D`; S's build splits it into
  S1. At wave 0's boundary A is readied and merged, and S1 (S's real work) is built later, in
  wave 1. The run exits 0 with no group line on stderr. The brief makes "`pdca split` refuses
  to split across a group" a follow-up, so a human should decide whether this PR covers it.
  A cheap in-scope option: treat a split parent in a group as a blocker
  (`flow._is_split_parent`, `flow.py:1926`), so the partner is held and the split is named.
  That way it fails safe instead of half-landing.

## Tried and could not break

- A re-run after a stop, a member that ends DISCONTINUED, a member with no PR or an
  `Onto branch` record, one-sided declarations (including from held or dropped split
  children), the sweep, finished members already merged, and same-wave groups. Each behaved
  as the brief asks.
- Coverage note, no action asked: every case sets `merge_requires = "required"`
  (`test_merge_group.py:67`). Under the default `"all"`, each member after the first is
  behind its base once the first merges. `_merge_one` then runs `gh pr update-branch` and
  waits for a fresh green rollup (`merge.py:701-745`) while the group is half landed. That is
  the host-side window the brief's Impact section accepts, but no test runs a group release
  on that path.

<!-- pdca:leaf-complete -->
