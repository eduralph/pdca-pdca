## Summary
**User impact:** publishing a contribution before its tracker ticket exists
(`pdca publish --no-issue`) could silently push broken work: a PR description or
commit message that would normally be rejected — say, one missing its required
user-impact opener — sailed through with only a printed notice, because the "no
ticket number yet" allowance excused *every* contribution check instead of just
the missing ticket number. On top of that, the publish step printed nothing while
its first contribution check ran, so for anyone watching the terminal it looked
hung for minutes.

This PR narrows the allowance to the one thing legitimately missing — the
not-yet-assigned ticket number — so every other contribution check blocks the
push in both modes, and makes the check announce itself before it starts.

Reported in [#384](https://github.com/eduralph/pdca-harness/issues/384).

## What to look at
The T4 contribution-gate handling in the publish step, and how the "pending id"
mode now reaches the checker: the publish run tells the checker which mode it is
in through the run's environment, so the shipped gate configuration keeps working
untouched — including for instances that update via the template. To try it:

```
cd template && PYTHONPATH=src python3 -m unittest \
  tests.test_publish_slice tests.test_t4_publish_gate
```

On `main` without this change, a dry-run pending-id publish over a bundle whose
PR body lacks the user-impact opener returns success and prints a FLAGGED notice;
with this change it is refused.

## Root cause
`publish()` relaxed a **failed** T4 gate to a printed flag whenever it ran under
`--no-issue` (`template/src/pdca_harness/publish.py:194-208` on `main` @
`0fbfa26`), but the gate was never told which mode it ran in — `_t4_passes`
exported only `PDCA_BUNDLE` (`publish.py:785`) — so the amnesty covered the whole
checker even though the narrow mode already existed
(`contribution_problems(d, no_issue=True)` drops only the tracker-id requirement,
`cli.py:1095`). Secondary: the immediate pre-run announce was dropped in favour
of the heartbeat alone in `a2c25ac1355ee4f1a5d839897239892d22c381f1` (#338), and
the first heartbeat tick is a full interval away (`publish.py:809-811` on base).

## Fix
- Delete the blanket relax branch: a failed T4 returns 1 in both modes
  (`template/src/pdca_harness/publish.py:197-210`).
- `_t4_passes` gains `pending_id` and derives `$PDCA_PENDING_ID` per run — the
  ambient value is popped, then set only when this run's flag says so
  (`publish.py:781,799-801`), mirroring how the Check gate runner derives
  per-gate env from driver state.
- `contribcheck` honours a non-empty `$PDCA_PENDING_ID` as `--no-issue`
  (`template/src/pdca_harness/cli.py:1096-1102`), so the registered
  `T4-contribution` row's cmd line stays byte-identical to base
  (`template/pdca.toml.jinja:979`) — rewriting that line in place breaks
  `copier update` for any instance that appended a row beside it
  (`tests/test_update_compat.py`).
- Restore the announce-before-heartbeat, with the heartbeat label unprefixed
  since the announce already says "T4 gate" (`publish.py:825-833`).
- Prose stating the deleted behaviour updated: docstrings, the `--no-issue`
  help text, the `pdca.toml.jinja` comments, and `agents/publisher.md.jinja`.

The `id_pending` recording and the "add the id and re-gate before marking the PR
ready" discipline are unchanged (`publish.py:386,405,506,514`).

## Verification
- **Claim:** under `--no-issue`, a T4 failure for any reason other than the
  missing tracker id refuses the publish (non-zero, nothing pushed); a bundle
  whose only problem is the absent id proceeds; the default mode still enforces
  the id.
  **Checked:** `template/src/pdca_harness/publish.py:197-210`;
  `template/tests/test_publish_slice.py:389-401` (the old relax-to-flag test,
  which encoded the defect, is replaced) and `:423-449` (end-to-end through the
  shipped `T4-contribution` row and the production `contribcheck`, driving the
  brief's exact repro: no opener + no trailer → refused; only-id-missing →
  proceeds; id-known → id enforced).
- **Claim:** the mode is derived from this run's flag, never inherited — a stray
  ambient `$PDCA_PENDING_ID` cannot relax a ticketed publish.
  **Checked:** `publish.py:799-801`; `template/tests/test_publish_slice.py:413-421`
  and `template/tests/test_t4_publish_gate.py:148-160`.
- **Claim:** the checker consumes the env form as exactly `--no-issue` (trailer
  waived, opener still enforced) without the shipped row's cmd changing.
  **Checked:** `cli.py:1096-1102`; `template/tests/test_publish_slice.py:983-996`;
  root render/update suite 7/7 with copier 9.17.0, including
  `tests/test_update_compat.py` — a `copier update` over an instance with an
  appended adjacent row merges cleanly.
- **Claim:** something reaches the terminal before the first heartbeat tick, and
  the heartbeat label is unprefixed.
  **Checked:** `publish.py:825-833`;
  `template/tests/test_t4_publish_gate.py:127-146`.
- **Test:** `template/tests/test_publish_slice.py` +
  `template/tests/test_t4_publish_gate.py` — with the production hunks reverted
  and the tests kept, both modules fail (e.g. `TypeError: _t4_passes() got an
  unexpected keyword argument 'pending_id'`; `'T4 gate' not found in '' : nothing
  announced before the run`); green with the patch. Full offline driver suite:
  1569 tests OK under both the instance venv and system Python.

Fixes #384
