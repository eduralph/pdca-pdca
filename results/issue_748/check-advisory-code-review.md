# Advisory code review — issue #748 (joint partners of a cross-wave fold clash)

Lenses: correctness bugs the patch adds, and reuse / simplification / efficiency. Lines are cited on `$PDCA_TARGET` (the patched tree).

**Result: no correctness bug found, nothing needs a human.** The notes below are minor and none blocks.

## Correctness

- `template/src/pdca_harness/integrate.py:1842-1856` — the new control flow in `_held_by_line` is sound. A `"batch"` result that `_explains` accepts returns as before. `"base"`, `"off"` and `"moved"` still return None. `"line"` and a failed `"batch"` fall through to `_together`. The check `set(joint) == set(partners)` skips re-running `_explains` on a set that already failed it. `partners` is a dict there, and `set()` of it gives its names, which is what we want. `IntegrationError` raised by the new trials still becomes None (a stop), and tree errors still raise. `_clash` itself (`:1969-2013`) is unchanged, as the brief requires.
- `template/src/pdca_harness/integrate.py:1944-1955` — the index checks are right. A single bundle is named only when `head` is the merge that fails (`at == len(lead) + 1`). A pair counts only when `head` fails after both (`len(lead) + 2`). If a candidate fails against `lead` itself, it is neither named nor put in a pair, which is the safe outcome. Only bundles that merge cleanly alone go into the pair search, which matches the brief's minimal-set rule.
- `template/src/pdca_harness/integrate.py:1940` — small edge case, safe. `lead` can hold several merge-bases, one per line bundle that `head` shares commits with. They are merged one after another, and two of them could in principle conflict with each other even though `head` reconciles them. `_trial` would then return an index below `len(lead)`, and `_together` returns `[]`, so the run stops. It never names the wrong bundle, so this only costs a hold that could have been made. Not worth a change unless it shows up in practice.
- `template/src/pdca_harness/integrate.py:1943` — a stacked line bundle (non-empty `under`) is named at size 1 from `partners`, which `_partners` worked out on the full head, not on the head's own change. This is the brief's stated limit ("judged as `_partners` judges it"), and `_partners` already keeps what the bundle was built on on both sides. It is a note, not a defect.

## Tests

- `template/tests/test_flow_cross_wave_joint_holds.py:797-825` (case 6) answers the iteration-1 finding. I traced it by hand: if `_own_change` returned `[]`, the size-1 trial `[X, H]` would conflict at index 1, so X would be named. `_explains` would then accept `{P, R, X}`, because L, W and H merge cleanly. The `unrelated=("L", "X", …)` check would then fail. So the helper is now tested in a way that can fail. The C4 gate (`gate-logs/C4-verify.log`) only reverts the whole fix: 5 of 6 tests go red, and case (5), the stop guard, stays green as expected. So the helper-only revert is my hand trace, not a gate result.
- The flipped child-1 guard (`template/tests/test_flow_cross_wave_fold_holds.py:363-400`) now checks the hold, the proposal and the exit code 3, and checks that K, W and V are not named. That is a real flip, not a weaker assertion.

## Reuse / efficiency

- `template/src/pdca_harness/integrate.py:1944-1951` vs `:2031-2033` — when `lead` is empty (a head cut from the base, as in cases 1-5), the size-1 loop in `_together` runs exactly the `[its, head]` trials onto `base_ref` that `_partners` has just run inside `_clash`. That is n repeated merges. They only run on the failure path, after a fold merge has already conflicted, so the cost is small. Sharing the results would mean changing `_partners`'s return shape, which the brief puts out of scope. Leave it.
- `template/src/pdca_harness/integrate.py:1859-1884` — moving rule (e) out into `_explains` so the single-bundle path and the joint path both call it is a good reuse. The logic is moved over unchanged from the old body of `_held_by_line`.

<!-- pdca:leaf-complete -->
