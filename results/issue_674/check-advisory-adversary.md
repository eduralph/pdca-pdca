# Adversarial review — issue 674 (same-wave conflict holds one bundle, not the run)

Verdict: I could not refute the fix on the paths the brief names. The red→green proof
holds, the test drives production code, and every attack scenario I ran came out right,
except one rare same-wave case that the patch deliberately stops on. Two items below are
for the human to decide. None is a defect the builder should rebuild for.

## Evidence I re-ran

- Green: `tests.test_flow_same_wave_conflict` on the patched tree at `$PDCA_TARGET`, with
  8/8 passing. Red: on a copy with `template/src`, `docs` and `template/PCDA` reverted,
  4 tests fail and 1 errors (the same result as `gate-logs/C4-verify.log`). The 3 that
  pass before the fix are the guard cases (criterion 3, the earlier-wave stop, and the
  stop on a base taken in mid-wave), which is what they should do.
- Production path: the test calls the real `flow._drive_and_act` and the real
  `integrate.fold` against real git (a bare origin). Only the build leaf, `_publish_bundle`,
  `draft_texts` and `gh` are stubbed, the same way the peer
  `test_flow_resume_stack_prereqs.py` does it. It is not a copy of the production code.

## Findings

- NEEDS-HUMAN [human] — `template/src/pdca_harness/integrate.py:541-544` (a gone branch,
  `head is None`, is never added to `kept`) together with the `kept` guard at `:531-532`:
  a real same-wave textual conflict still stops the run when the earlier bundle of the
  pair had its PR merged and its branch deleted between publish and fold. Concrete case
  (I ran it): wave 1 is `20` and `22`, which both change line 2 of `shared.txt`, plus `23`,
  with `30` depending on `23`. Right after the wave publishes, 20's PR merges and
  `fix/20` is deleted. The fold takes main in for 20, `kept` is empty, and 22 raises:
  "wave 1 did not integrate (issue_22's branch … — an undeclared cross-wave overlap)
  … STOPPING", and `30` is never built. The brief's Invariant says a same-wave conflict
  costs "never the run". The patch documents this as a deliberate stop
  (`docs/07-crosscutting.md:706-709`), following the round-2 guidance. A possible
  extension: add `(name, merged_head)` to `kept` for a gone bundle of the wave, so
  `_held_by` can name it as the partner. It needs a human to merge a just-opened draft PR
  within minutes, so it is rare. Decide whether the documented exception is acceptable.
- NEEDS-HUMAN [human] — `template/src/pdca_harness/cli.py:690` together with
  `flow.py:2490`: a run whose only problem is a held bundle with no dependents now exits 0.
  Concrete case (I ran it): batch `10`, `11`, `12`, `21` (`Depends on: 12`), where 10 and
  11 change the same line. Results are all COMPLETE, so `_results_rc` returns 0. The only
  signal is two stderr lines, while 11's open draft PR is known to conflict with 10's.
  Before the fix the same batch exited 1 (the fold stopped and 21 stayed PLANNED). This
  matches the existing #593 `held_unpushed` behaviour, so it is a policy choice, not a
  bug. Decide whether a conflict hold should fail the run's exit code.
- Out of this diff's scope, noted for context: re-issuing the same `pdca flow <ids>` after a
  hold (the recovery the docs recommend) keeps `20` held through the existing #646 carry,
  which is correct. But that carry's line (`flow.py:913`) calls the clash "an undeclared
  cross-wave overlap" (`integrate.py:630`). It also tells the user to "get issue_11's PR
  open … (re-open it, `pdca publish 11`, …)", though the PR is already open, and the #674
  end-of-run proposal is not repeated. The brief puts the fold's message out of scope, so
  this is not filed for rebuild.
- Minor test nit, not filed: `template/tests/test_flow_same_wave_conflict.py:329-339`
  calls `integrate.fold(..., held_out=..., wave=...)`, keywords the fix adds. With the fix
  reverted it fails with `TypeError` rather than on an assertion, so this one case cannot
  go red for the right reason. The other four red cases carry the proof, so C4's verdict
  stands.

## Refutation attempts that failed (the fix held)

- Three-way chain (40/41/42): only 41 is held, and 42 is judged against the bundles kept,
  not the held one. Covered by the test, and I confirmed the logic at `integrate.py:902-908`.
- Holds in two successive waves (11 in wave 0, 21 in wave 1): both stay off the final
  line, only 31 (which depends on 21) is skipped, and both appear in the end-of-run report.
- The hold lasts the whole run: later folds leave `held_conflict` out at `flow.py:2452-2453`.
  `carried` never records a held bundle, because `took` is only written in the `else` branch.
- A conflict with earlier-wave work, or only with a base taken in mid-wave, still stops
  the run (`_held_by`'s two `return None` paths). Both are tested.
- The "name every kept bundle" fallback at `integrate.py:908` rarely fires. Git treats
  edits on adjacent lines as a conflict (I checked: K1 line 3, K2 line 5, H line 4 conflicts
  pairwise with each), so the pairwise check finds the real partner.
- The tie-break between ids of different lengths: `waves.compute_waves` orients a
  `Conflicts with` pair by name (`waves.py:200-212`), the same order the fold uses. So the
  proposed `Conflicts with: 100` in issue_99's brief really does build 99 after 100.
- Integration tree state: `_trial` restores the branch tip or raises `_LineBroken`, and
  the test checks that the tree is clean and on the branch afterwards. No new git feature
  is used (`checkout --detach`, `merge`, `reset --hard` and `clean` are already relied on).
- The gate rows in `check-gates.json` (C4, C5, T2, T3) match their logs. I found no claim
  there that the evidence does not support.

<!-- pdca:leaf-complete -->
