# Adversarial review — issue 395 (same-wave conflict caught before publish)

I re-ran the new test file on a copy of the patched tree (17 tests, OK). I ran probes against both the patched tree and the pre-fix tree (`git archive HEAD`), all inside my scratch folder. One concrete regression found; the rest held up.

- NEEDS-HUMAN [impl] — **One `Onto branch` bundle whose remote can't be fetched makes the whole trial fail, so siblings with no conflict are not published.** `template/src/pdca_harness/integrate.py:860` fetches the remote of every member in one `_prepare_worktree` step. `publish.cut_base` hands back the `Onto branch` remote (`template/src/pdca_harness/publish.py:821`). A failed fetch there raises for the whole target. After the two tries (`integrate.py:833`), the fallback at `integrate.py:838-839` publishes only the first bundle and holds the rest as unpushed. The fold never has this problem: it fetches only the remotes of bundles that actually pushed (`integrate.py:602`), and publish refuses the bad bundle alone at `_check_repo`. Probe (wave 0 = `10` and `11` with new files of their own, `12` with `- **Onto branch:** nosuch/pr-12`, `20` depending on `11`):
  - **Patched tree:** holds `{'11': 'unpushed', '12': 'unpushed'}`. 11 gets no branch and no PR, and 20 is never built. Stderr blames 11 with "could not fetch nosuch".
  - **Pre-fix tree:** holds `{'12': 'unpushed'}`. 10, 11 and 20 are all published.
  - **Bad bundle sorts first** (`09` with the bad remote): holds `{'09','10','11': 'unpushed'}`. Nothing in the wave is published, and the advice says to "check that its change merges with issue_09's", a bundle that can never publish as written.
  
  This is easy to trigger by accident: `brief.onto_branch` (`template/src/pdca_harness/brief.py:295`) reads `Onto branch: feature/foo` as remote `feature`. Fix: fetch each bundle's own non-origin/non-base remote separately, and treat a failure there as `_Unbuilt` for that bundle only. A test with one bad-remote bundle beside a clean pair would pin it down.

- NEEDS-HUMAN [human] — **The fail-closed fallback holds back bundles that cannot conflict at all.** When the trial can't run for a target (two failed fetches, a lock it can't take, a git step outside one bundle's commit), `integrate.py:838-839` publishes only `members[0]` and holds every other ready bundle and its dependents. That happens even when their patches touch files no sibling touches, so a textual conflict is impossible. The behaviour is documented (`docs/07-crosscutting.md:736`) and tested. But it means one network blip during the trial now costs N-1 PRs and their later waves on any non-final wave with 2+ bundles. Before this change the same blip cost nothing at publish time, and the fold's own later fetch may well succeed. Whether to accept that, or to publish bundles with no shared path (the footprint `_audit_wave_overlap` already computes, `template/src/pdca_harness/flow.py:1629`) when the trial can't run, is a trade-off for a human.

- **The brief's goal sentence overclaims; the patch itself doesn't.** The Goal says "a non-final wave no longer ends with two open PRs that conflict with each other." That isn't true when the earlier sibling A also conflicts with work already on the line. In `_same_wave_trial`, A fails to merge with `kept` empty, so it is neither kept nor held (`integrate.py:885-892`). B then merges cleanly, and both are published, even though A and B conflict with each other. The fold then holds A under #747. This matches the fold's rule and the brief's own scope ("conflicts with work already on the line … out of scope"), so I'm not filing it as a defect. The reviewer should just not read the Goal sentence as guaranteed.

- **The red→green evidence holds, with one caveat about what counts as red.** In `gate-logs/C4-verify.log` the red leg shows 12 of 17 new tests failing on assertions (for example `_not_published("11")` finds the branch on origin), plus 3 assertion failures in `test_flow_same_wave_conflict.py`. That is real evidence. The 24 "errors" in `test_flow_reissue_after_conflict_hold.py` are not: they are `AttributeError`s from `mock.patch.object(flow, "_held_before_publish", …)` at `template/tests/test_flow_reissue_after_conflict_hold.py:127`, which fail on any tree without the symbol. The 5 new tests that pass on the red tree are the guards (b), (c), (d) and both (f) cases, as expected. The tests go through the production `publish.publish` with real git and a bare origin, so C5's claim stands.

- **Attempts that did not refute the fix:**
  - **Same commit as publish:** the `_checkout_base` refactor keeps the old `wave_stacked and bool(wave_tip)` rule (`publish.py:251`, `:804`), and `_would_be` uses publish's own apply / `add --all` / commit steps.
  - **Same order:** the trial order (`to_publish`, name-sorted) matches the fold's `accepted` order within a wave.
  - **Same start point:** the trial starts at the fold's continue/fresh tip (`folded_tips`, seeded by the carry at `flow.py:1603`).
  - **Same gating:** the trial runs only when the fold does (`flow.py:3166` against the fold's `k < len(wave_list) - 1 and do_publish`, merge mode and stub publisher both excluded).
  - **Mutation test:** making the trial hold on any conflict, skipping `_held_by`, is caught by 8 cross-wave tests.
  - **Locks:** taken in sorted order on one ExitStack, with no outer lock held at that point.
  - **Re-issue path:** `merged.pr_state` never raises, so `_pr_closed` can't crash the carry.
  
  None of these turned up a failing case.

<!-- pdca:leaf-complete -->
