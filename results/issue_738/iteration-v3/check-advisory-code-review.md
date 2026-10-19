# Advisory code review — issue #738 (hold a bundle whose own base cannot be built)

Lenses: bugs the patch introduces, and reuse / simplification. All anchors are on the patched target (`$PDCA_TARGET`).

I found no correctness bug in this diff. What I checked and found sound:

- The catch moved from the wave loop into `_bundle_bases` (`template/src/pdca_harness/flow.py:1040-1047`). A held bundle is never pointed, and the wave drops it before the build (`flow.py:2897-2900`). A wave left empty skips its fold the same way the existing empty-wave `continue` does.
- `held_base` is added to `_runnable`'s `held` set and to the `conflicts` trigger (`flow.py:2831-2843`). Dependents are skipped in every later wave, and `Conflicts with` partners are held (`flow.py:770-771`, `:863-871`). `waves.py:17-21` orients each conflict pair into separate waves, so a partner cannot share the held bundle's wave and slip past the check.
- The `_prepare_worktree` wrapper (`template/src/pdca_harness/integrate.py:859-873`) covers all three raise sites in that path: the missing checkout and the failed fetch (now `_NoCheckout` / `_FetchFailed`, both still `IntegrationError` subclasses, so existing `except` clauses still catch them), plus the worktree that cannot be made. `cause` is passed through, so `rewritten_carried`'s "unchecked" text is unchanged.
- `_report_stale_prs` (`flow.py:1092`) looks up names in `dirs = {accepted}`. Every name it looks up is accepted: owners come from `pushed`, which is a subset of `accepted`, and members come from `carried_heads`, which only the in-run fold of `accepted` fills (`_carry_finished` is not passed it). So no `KeyError`.
- `cli._results_rc` (`template/src/pdca_harness/cli.py:742-743`) excuses only bundles held as `"base"`. A dependent left PLANNED still gives exit 1, and `"rewritten"`/`"unchecked"` still win over 3.
- The existing tests that change (`test_flow_dependency_scoped_bases.py`, `test_integrate_carried_rewrite_late.py`) were moved from "STOPPING" to "held" and given exact `holds`/rc assertions. None of them was weakened. The new file asserts the holds map, the state and the rc in every case.

Small cleanups (optional, not blocking):

- `template/src/pdca_harness/integrate.py:1317` — `lost_now` repeats the per-branch read from `rewritten_carried` (`integrate.py:1240` onward): `_fold_candidates` → `_checkout_path` → `_fetch(attempts=2)` → `_rev` → `_carried_rewrite`. A small shared helper such as "read branch `ref` of `d` again and judge these heads" would keep the two end-of-run checks from drifting apart. Low priority, since both are short.
- `template/src/pdca_harness/flow.py:863-871` — the `unbuilt_partners` loop is a near copy of the #629 `partners` loop (`flow.py:848` onward) and the #674 `clashed` loop, with different wording. It is fine as written. If a fourth hold kind arrives, one table of (partner set → message) would be simpler than a fourth copy.
- `template/src/pdca_harness/flow.py:1131` — in the "unchecked" branch, `_report_stale_prs` lists every PR on a lost head, including ones the refusal already named (the `named` filter is applied only in the "rewritten" branch below it). This is harmless (one extra name on a line asking for a manual check) and arguably correct, since the branch could not be read again.

No NEEDS-HUMAN items from this lens.

<!-- pdca:leaf-complete -->
