# Advisory code review — issue 728 (flow-carry-through-patchless-finished-bundles)

Result: no correctness bugs found on either lens. Nothing needs a human decision. The notes below are optional cleanups and one coverage remark.

## Correctness (checked, no defect)

- `template/src/pdca_harness/flow.py:1182-1203` (`_reached`): the BFS (breadth-first walk) stops at the first `stops` id, goes on only through `through` ids, and its `seen` set guards against cycles. `found.setdefault` keeps the shortest path, so the `via` list in the reason text is stable. Same edge kind (`brief.depends_on`, plain only) as the code it replaces, so `Stacks on` / `(merged)` / `Conflicts with` stay unfollowed, as the brief's scope asks.
- `template/src/pdca_harness/flow.py:1219-1231` (`_cascade_not_clean`): when `through` is empty, `_reached` reduces to the old direct-edge filter, so existing callers and messages for direct edges are byte-identical (`via == []` takes the old `names …` wording). The fixed-point loop still covers chains of patched ids broken up by patchless ones, because each patched id's reach set now jumps over the patchless ones.
- `template/src/pdca_harness/flow.py:1386-1387` (final `held.update`): one pass is enough. Before this line `held` holds only fold candidates, and `_reached` already walks through every patchless id to the candidates, so no fixed point is needed. A dry-run never fills `held`, so no patchless id gets held there either. The existing, unchanged `_runnable` branch at `flow.py:803-806` then holds `D` because `issue_N` is in `held`. Test (2) is the one that needs this line: without it, `N` is COMPLETE with no fold candidate and `D` would run.
- Messages: the "is not carried" loop (`flow.py:1370-1382`) still runs over fold candidates only, so a patchless id prints no line of its own. `dependents` (`flow.py:1293-1295`) now lists `D` under `issue_A` when `D` reaches `A` through `N`, which is what the brief's "holding …" requirement needs.

## Reuse / simplification / efficiency (optional nits, not blocking)

- `template/src/pdca_harness/flow.py:1195`: `todo.pop(0)` on a list is O(n) per pop. A `collections.deque` with `popleft()` is the usual form. These graphs are tiny, so this is style only.
- `template/src/pdca_harness/flow.py:1294`, `:1219`, `:1387`: `_reached` re-reads and re-parses briefs on every call: once per drive-set bundle, once per candidate per target, and once per patchless id. That cost is negligible next to the git and `gh` work in the same function, so caching is not worth it.

## Tests

- `template/tests/test_flow_carried_prereq_bases.py:257-384`: the cases match brief criteria (1), (1b), (2), (3), (4a) and (4c). The (4c) variant with an earlier line already on origin also runs the `foreign_commit` check. The dry-run case is an extra. They drive the production `_drive_and_act` through the peer harness, with the publisher not stubbed (except in the dry-run case). Gate evidence agrees: `gate-logs/C4-verify.log` shows 5 of 8 red with the fix reverted ((1), (1b), (2), (3), dry-run) and all green with it, and `gate-logs/T3-suite.log` shows the driver suite OK.
- Coverage remark, not a defect: there is no diamond case, i.e. a drive-set bundle that reaches the same candidate both directly and through a patchless id, or two patchless paths to one candidate. Reading `_reached` (`flow.py:1199-1200`, `setdefault` plus `seen`), it handles this correctly, so a test would only guard against regressions.

## Scope note (informational, outside this diff)

- `template/src/pdca_harness/flow.py:1291`: `bare` is "finished and `not _has_patch`". A finished id that has a patch but no usable target is in neither `cands` nor `bare`, so an edge through it is still dropped. This is the same as before the patch and is rare. Mentioned only so the boundary is visible. It is not filed as a finding against this diff.

<!-- pdca:leaf-complete -->
