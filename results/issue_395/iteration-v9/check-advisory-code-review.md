# Advisory code review — issue 395 / same-wave-conflict-refused-at-accept

I found no correctness bug that needs a fix before sign-off. I checked the parts most likely to break:

- The trial's condition at `template/src/pdca_harness/flow.py:3443-3446` matches the fold's own condition (`flow.py:3512-3533`: not the last wave, `do_publish`, stack mode, a non-dry `held_out`).
- The re-offer bound holds. After the first refusal, the open row makes C6 refuse before the trial runs again (`flow.py:203-205` comes before `:210`). So `_refuse` does not reset `sessions` to 0 on each later pass, and `_parked` (`flow.py:565`) parks the bundle after one session.
- `publish._checkout_base` (`publish.py:767`) gives the same result as the inline rule it replaces (`wave_stacked and bool(wave_tip)` with `wave_stacked = wave_mode != "merge" and bool(wave_base)`).
- Every exit path of the would-be build and the trial merges puts the tree back on the line (`integrate.py:826-835`, `_would_be`, `_back_on`). `_merge` resets after a conflict (`integrate.py:1967-1985`), so `_wave_holds` never stacks a merge on a half-merged tree.

The notes below are minor. None of them is a gate issue.

- `template/src/pdca_harness/flow.py:357-372` (`_refuse`) / `flow.py:396-424` (`_refusal_words`): the tick override only works if the next accept produces the same row text, byte for byte (after whitespace and case are normalised). `ensure_needs_human_item` matches on the whole text (`signoff.py:199-205`). For the `"unrun"` and `"tree"` kinds, that text includes the error cause (`_cause(exc)`, `flow.py:351`). If the second attempt fails at a different step, or with a different message, the human's ticked row no longer matches. A new unticked row is added, and the override the docs describe is refused again. This fails closed (no unsafe accept), but the human gets a confusing loop. The same happens for `"conflict"` if another sibling is accepted between the refusal and the override, which is arguably correct because the partner is new. A row key that leaves out the free-text cause would fix it. Leg (d) only covers the `"conflict"` kind.
- `template/src/pdca_harness/integrate.py:812` and `:828`: each accept on a wave that has accepted siblings does a fresh fetch (`_prepare_worktree`) and rebuilds the would-be commit of every accepted sibling. It then runs two full wave-merge simulations, and each one can call `_held_by` (several `_trial` merges). For a wave of n accepts that is O(n²) commit builds plus n fetches. That is fine at today's wave sizes. If waves grow, cache each sibling's would-be commit by (cut ref, patch hash) for the length of the run.
- `template/src/pdca_harness/flow.py:580-581` (`_parked`): this re-implements `ensure_needs_human_item`'s row matching (strip the box, collapse whitespace, casefold; `signoff.py:199-205`). It only checks `- [ ]`, which is right here, but there are now two copies of the normalisation rule. A small shared helper in `signoff` would keep them from drifting apart.
- `template/src/pdca_harness/flow.py:324-325` (`_refused_for_wave`): "already accepted" means COMPLETE at accept time, before any publish. If that sibling's publish later fails (T4 texts, push), the refused bundle was blocked by a PR that never opened, and the run ends with neither published. The run still exits 1 and the row names the partner, so this is a consequence of the design, not a bug. I'm noting it so the sign-off sees it.

No NEEDS-HUMAN items.

<!-- pdca:leaf-complete -->
