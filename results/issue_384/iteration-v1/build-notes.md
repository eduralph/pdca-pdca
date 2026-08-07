# Build notes — issue 384 / no-issue-mode-into-the-t4-gate

Target: eduralph/pdca-harness @ main (worktree base `0fbfa26`, edited in
`$PDCA_WORKTREE=/home/eddie/pdca/pdca-harness.pdca-wt-l0`; all `path:line` below are
against that tree with the patch applied unless marked "base").

## What changed and why

1. **The blanket relax branch is deleted outright** (base `publish.py:194-208`). A failed
   T4 now returns 1 in both modes; the FLAGGED-and-proceed print is gone
   (`template/src/pdca_harness/publish.py:197-210`). The `id_pending` recording and the
   "add the id and re-gate before ready" discipline are untouched
   (`publish.py:386,405,506,514`).

2. **The gate is told which mode it runs in.** `_t4_passes` gains
   `pending_id` (`publish.py:781`) and derives `$PDCA_PENDING_ID` per run: the ambient
   value is popped, then set to `"1"` only when this run's flag says so
   (`publish.py:798-801`). This mirrors the cited peer callsite — `gates._run_one`
   derives `PDCA_BRIEF_BASE`/`PDCA_LANE` from driver state, never inheriting them
   (`gates.py:490-541`) — which I opened per the brief's composition cue.
   `publish()` passes its own flag through (`publish.py:207`); `draft_texts` keeps the
   default (id-known) mode — the flow never publishes pending-id (`publish.py:108`), and
   the scrub now also protects that pre-pass from a stray ambient export.

3. **The checker consumes the mode.** `contribcheck` treats a non-empty
   `$PDCA_PENDING_ID` as `--no-issue` (`cli.py:1096-1102`), i.e. the narrow mode that
   already existed: `contribution_problems(d, no_issue=True)` drops *only* the tracker-id
   requirement (`cli.py:1131`). No lint rule changed (out of scope, and none needed).

4. **Restored pre-run announce, heartbeat label unprefixed** (`publish.py:823-834`):
   `· T4 gate <label> (this can take minutes)…` prints to stderr before
   `run_with_heartbeat`, whose label is now the bare `label or "T4 gate"` — the announce
   already says "T4 gate", per the brief. Same announce-then-heartbeat shape as the peer
   (`gates.py:548,558`).

5. Stale prose stating the deleted behaviour updated: `publish()`/`draft_texts`
   docstrings (`publish.py:88-92,134-142`), the `--no-issue` help (`cli.py:388-390`),
   the `[tracker]` and T4-row comments (`pdca.toml.jinja:306-308,959-966`), and
   `agents/publisher.md.jinja:21-25`.

## Deliberate deviation from one clause of the Success criterion — with evidence

The brief says "the shipped gate row consumes it as `contribcheck --no-issue`", and my
first implementation did exactly that:

```toml
cmd = "{{ cli_name }} contribcheck${PDCA_PENDING_ID:+ --no-issue}"
```

That variant is **red on the target's own root render suite**: `tests/test_update_compat.py`
(#342) simulates the canonical instance shape — a row appended directly beside the shipped
`T4-contribution` row — and `copier update` from v0.56.0 then three-way-merges my edit of
that registered line against the instance's adjacent insertion. Reproduced (fixture built
with the suite's own helpers; merged `pdca.toml` lines 928-933):

```
<<<<<<< before updating
  { id = "T4-contribution", ... cmd = "pdca contribcheck", ... },
  { id = "instance-extra", ... },
=======
  { id = "T4-contribution", ... cmd = "pdca contribcheck${PDCA_PENDING_ID:+ --no-issue}", ... },
>>>>>>> after updating
```

→ syntactically invalid TOML; every `pdca` command in the updated instance dies at config
load (5 of the suite's 7 tests fail). The comment-block edits above the row merged
cleanly — it is precisely the registered *line* that cannot be rewritten in place. This is
not a cost trade-off I could quantify away: TOML inline tables are single-line, so there is
no diff shape that changes that row's `cmd` without touching the line an instance appends
against. The row-edit variant would therefore fail the target's CI (`render-check.yml`
runs this suite with full tags) and break every downstream instance's `copier update`.

So the mode reaches the shipped checker **through the registered row's run environment**
instead: the row line is byte-identical to base (`pdca.toml.jinja:979`), and the checker it
invokes honours `$PDCA_PENDING_ID` (`cli.py:1101`). The brief's *intent* — "a rendered
instance gets the behaviour without editing its own config" — is satisfied strictly more
broadly: a fresh render *and* a `copier update`d instance (whose row line never changes in
the merge) both get it with zero config edits. Every other clause of the Success criterion
holds as written, and the update-compat suite is green (7/7).

Scope note: this adds a 7-line hunk in `_contribcheck` (`cli.py:1096-1101`), near issue
401's territory (the default-open path at `cli.py:1088-1094` is untouched). The brief's
ordering note already has 401 declaring the conflict on its side.

## Verification (project runners only)

- **C4 gate** (`pdca-pdca` `pdca.toml:830` → `engine/scripts/run-verify.sh`, with
  `PDCA_BUNDLE`/`PDCA_WORKTREE` set): **C4 PASS** — green leg 66+11 OK; red leg
  (production hunks reverted, tests kept) fails with 5 failures in
  `tests.test_publish_slice` + 1 failure/1 error in `tests.test_t4_publish_gate`, all
  seven being the new/replaced tests (names captured in the run log; e.g.
  `test_no_issue_no_longer_relaxes_a_failing_t4_to_a_flag`,
  `test_shipped_row_gives_no_issue_only_the_tracker_id_amnesty`,
  `test_pending_id_mode_is_derived_per_run_never_inherited` — the last errors with
  `TypeError: _t4_passes() got an unexpected keyword argument 'pending_id'` on base).
- **Full offline driver suite** (`cd template && PYTHONPATH=src python3 -m unittest
  discover tests`, instance venv python): 1569 tests, OK (skipped=2) — no collateral
  damage from the announce/label change (the pre-existing announce test
  `test_the_gate_is_announced_before_it_runs` still passes with the unprefixed label).
- **Root render suite** (`python3 -m unittest discover tests` from the repo root, copier
  from the instance `.venv` per the brief's registered external dependency): 7 tests OK —
  including `test_update_compat` (clean `copier update` v0.56.0 → HEAD) and
  `test_render_and_run`, which re-runs the rendered instance's own 1569-test suite (this
  caught an earlier bug in my test helper: inside a rendered instance there is no
  `pdca.toml.jinja`, so `_shipped_t4_row_cmd` now falls back to the rendered `pdca.toml`,
  `test_publish_slice.py:30-46`).

## Forced self-refutation

- **(a) Genuine red?** Yes — the C4 red leg *is* the revert-and-rerun: with only the
  production hunks reverted (`run-verify.sh:70-81`), both test modules fail, and every
  failing test is one this patch added/replaced (list above). Notably each new test earns
  its own red — e.g. the pending-export test asserts `(rc, "FLAGGED" in stderr) ==
  (0, False)` so the base's relax-to-flag path cannot fake it green.
- **(b) Production path?** Yes — the tests drive `publish.publish` / `publish._t4_passes`
  / `cli._contribcheck` from the tree under test; the end-to-end test additionally spawns
  the real CLI (`python -m pdca_harness.cli` with `PYTHONPATH` pointed at the tree's
  `src`, `test_publish_slice.py:431-436`) and builds its gate cmd from the checker
  invocation the *shipped config* registers (read from `pdca.toml.jinja`/rendered
  `pdca.toml`, not re-declared). No stand-ins, no re-implementation.
- **(c) Fixture includes the fault?** Yes — the end-to-end bundle carries the exact
  repro artifacts the brief names: a `pr-description.md` with **no** `**User impact:**`
  opener and a `commit-msg.txt` with no tracker id (`test_publish_slice.py:437-450`);
  the refusal is asserted on that malformed body under `pending_id=True`, and the
  only-id-missing case is asserted to proceed. Nothing is curated out.

## Ruled out

- **`cmd = "{{ cli_name }} contribcheck${PDCA_PENDING_ID:+ --no-issue}"`** — see the
  deviation section: breaks `copier update` (reproduced conflict, 5/7 update-suite tests
  red); cost is unbounded downstream (every instance with an adjacent appended row gets
  unparseable TOML).
- **A second shipped row / publish rewriting the cmd string for contribcheck rows** —
  either duplicates the tracker-id enforcement in default mode (two rows both run; the
  flagless one still fails a pending-id publish) or couples publish to one project's
  checker, which `_t4_passes`' docstring explicitly forbids ("keeps publish decoupled from
  any one project's checker", `publish.py:783-784`).
- **Parsing `--no-issue` into `env` only when the row's cmd contains "contribcheck"** —
  same coupling, plus silently does nothing for delegated (`subcmd`) rows.

## Commit-readiness

The target repo configures no pre-commit hooks or formatter (no
`.pre-commit-config.yaml`, no non-sample `.git/hooks`; CONTRIBUTING.md's only mechanical
requirement is the offline suite green, which holds). New/edited lines follow the
surrounding style (≤ ~100 cols outside the jinja's pre-existing long comment lines).
CI parity: `render-check.yml` (root suite) green locally; `docs-check`/`docs` untouched
paths; `require-linked-issue` is a PR-body matter for publish.

No NEEDS-HUMAN items: all external dependencies the brief registered (`copier importable
(.venv)`) were present and used.
